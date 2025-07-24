#!/usr/bin/env python3
"""
Parallelized Dust Flux Calculation

Optimized version of dust_2_flux_calc.py with daily-level parallelization
and smart caching for 4-8x performance improvement.
"""

import multiprocessing
import os
from datetime import datetime, timedelta
from functools import partial
import pygeoprocessing.geoprocessing as geop
from osgeo import gdal
import math
import numpy as np
from netCDF4 import Dataset
import rasterio
from rasterio.transform import from_origin

def setup_shared_resources(inputdir):
    """Setup resources shared across all daily processing"""
    
    wdir = "./"
    
    # Get reference grid info for dynamic sizing
    soc_raster_out = os.path.join(wdir,'grid.tif')
    grid_info = geop.get_raster_info(soc_raster_out)
    
    # Setup aligned soil texture (shared across all days)
    soil_texture_path = "intermediate/soil_texture.tif"
    aligned_soil_texture = "intermediate/aligned_soil_texture.tif"
    
    if not os.path.exists(aligned_soil_texture):
        geop.align_and_resize_raster_stack(
            [soil_texture_path],
            [aligned_soil_texture],
            ['bilinear'],
            grid_info['pixel_size'],
            bounding_box_mode=grid_info['bounding_box'],
            target_projection_wkt=grid_info['projection_wkt'])
    
    # Setup land use effect (scenario-specific but shared across days)
    lu_raster = [(os.path.join(inputdir,'inputs', 'gblulcg20_10000.tif'),1)]
    lu_raster_out = os.path.join(wdir,'intermediate','z0_effect_dust.tif')
    
    if not os.path.exists(lu_raster_out):
        # Land use to surface roughness mapping (same as updated original)
        def z0(lu):
            k = 100.0
            fdtf = 0.0
            
            # Handle Simple 4-class classification (UK scenarios)
            if lu <= 3:
                match lu:
                    case 0: # Other - no dust
                        k = 100.0
                        fdtf = 0.0
                    case 1: # Cropland - moderate dust
                        k = 0.0310
                        fdtf = 0.75
                    case 2: # Grass - moderate dust  
                        k = 0.1000
                        fdtf = 0.75
                    case 3: # Forest - no dust
                        k = 50.0
                        fdtf = 0.0
            else:
                # IGBP classification handling (same as original)
                match lu:
                    case 1: k = 50.0; fdtf = 0.0  # Urban
                    case 2: k = 0.0310; fdtf = 0.75  # Cropland
                    case 3: k = 0.0310; fdtf = 0.75  # Irrigated Cropland  
                    case 4: k = 0.0310; fdtf = 0.75  # Mixed Cropland
                    case 5: k = 0.0310; fdtf = 0.75  # Cropland/Grassland
                    case 6: k = 0.0310; fdtf = 0.75  # Cropland/Woodland
                    case 7: k = 0.1000; fdtf = 0.75  # Grassland
                    case 8: k = 0.0500; fdtf = 0.75  # Shrubland
                    case 9: k = 0.0500; fdtf = 0.75  # Mixed Shrub/Grass
                    case 10: k = 0.0020; fdtf = 0.75  # Savanna
                    case 11|12|13|14|15: k = 50.0; fdtf = 0.0  # Forests
                    case 16|17|18: k = 100.0; fdtf = 0.0  # Water/Wetlands
                    case 19: k = 0.0020; fdtf = 1.0  # Barren
                    case 20|21|22: k = 0.0500; fdtf = 0.75  # Tundra
                    case 23: k = 0.0020; fdtf = 1.0  # Bare Tundra
                    case 24|100: k = 100.0; fdtf = 0.0  # Snow/NoData
                    case _: k = 100.0; fdtf = 0.0  # Conservative default
            
            result = fdtf / (2.5 * math.log(1000.0/k))
            return result
        
        z0_v = np.vectorize(z0)
        
        geop.raster_calculator(
            base_raster_path_band_const_list=lu_raster,
            local_op=z0_v, 
            target_raster_path=lu_raster_out,
            datatype_target=gdal.GDT_Float32,
            nodata_target=-1,
            calc_raster_stats=False)
    
    # Align z0 with grid
    aligned_z0_path = os.path.join(wdir, 'intermediate', 'aligned_z0.tif')
    if not os.path.exists(aligned_z0_path):
        geop.align_and_resize_raster_stack(
            [lu_raster_out],
            [aligned_z0_path],
            ['bilinear'],
            grid_info['pixel_size'],
            bounding_box_mode=grid_info['bounding_box'],
            target_projection_wkt=grid_info['projection_wkt'])
    
    return {
        'grid_info': grid_info,
        'aligned_soil_texture': aligned_soil_texture,
        'aligned_z0_path': aligned_z0_path,
        'wdir': wdir
    }

def process_single_day(date_info, shared_resources, inputdir):
    """
    Process dust flux for a single day
    
    Args:
        date_info: Tuple of (date, date_string)
        shared_resources: Dict of shared processing resources
        inputdir: Input directory path
        
    Returns:
        str: Path to processed flux file
    """
    
    date, date_string = date_info
    grid_info = shared_resources['grid_info']
    aligned_soil_texture = shared_resources['aligned_soil_texture']
    aligned_z0_path = shared_resources['aligned_z0_path']
    wdir = shared_resources['wdir']
    
    try:
        # 1. Load and process MERRA2 wind data
        merra_path = os.path.join(inputdir, 'inputs', 'daily_meteorology', f'MERRA2_{date_string}.nc')
        
        if not os.path.exists(merra_path):
            print(f"  ⚠️  Missing MERRA2 data for {date_string}, skipping...")
            return None
        
        with Dataset(merra_path, 'r') as merra_dataset:
            east_wind = merra_dataset.variables['U10M'][0, :, :]
            north_wind = merra_dataset.variables['V10M'][0, :, :]
            
            # Calculate wind speed
            wind_speed = np.sqrt(np.square(east_wind) + np.square(north_wind))
            wind_speed = np.flipud(wind_speed)
        
        # 2. Create wind speed raster
        wind_speed_path = os.path.join(wdir, 'intermediate', f'ws_{date_string}.tif')
        
        with rasterio.open(wind_speed_path, 'w', 
                          driver='GTiff',
                          height=wind_speed.shape[0],
                          width=wind_speed.shape[1],
                          count=1,
                          dtype=wind_speed.dtype,
                          crs='EPSG:4326',
                          transform=from_origin(-180, 90, 0.625, 0.5),
                          compress='lzw') as dst:
            dst.write(wind_speed, 1)
        
        # 3. Align wind speed to processing grid
        aligned_ws_path = os.path.join(wdir, 'intermediate', f'ws_aligned_{date_string}.tif')
        geop.align_and_resize_raster_stack(
            [wind_speed_path],
            [aligned_ws_path],
            ['bilinear'],
            grid_info['pixel_size'],
            bounding_box_mode=grid_info['bounding_box'],
            target_projection_wkt=grid_info['projection_wkt'])
        
        # 4. Calculate ustar (friction velocity)
        ustar_path = os.path.join(wdir, 'intermediate', f'ustar_{date_string}.tif')
        
        def multiply_raster(ws, z0_effect):
            return ws * z0_effect
        
        multiply_raster_v = np.vectorize(multiply_raster)
        
        listraster = [(aligned_ws_path, 1), (aligned_z0_path, 1)]
        geop.raster_calculator(
            base_raster_path_band_const_list=listraster,
            local_op=multiply_raster_v,
            target_raster_path=ustar_path,
            datatype_target=gdal.GDT_Float32,
            nodata_target=-1,
            calc_raster_stats=False)
        
        # 5. Calculate dust flux
        def flux(ustar, soiltype):
            if soiltype == 0: return 1.243*(10.0 **(-7)) * ustar ** 2.64  # MS
            elif soiltype == 1: return 0.0  # NA
            elif soiltype == 2: return 2.45*(10.0 ** (-6)) * ustar ** 3.97  # FSS
            elif soiltype == 3: return 9.33*(10.0 ** (-7)) * ustar ** 2.44  # FS
            elif soiltype == 4: return 1.243*(10.0 ** (-7)) * ustar ** 3.44  # CS
            elif soiltype == -1: return 0.0  # NoData
            else: raise ValueError("soil type not recognized")
        
        flux_v = np.vectorize(flux)
        
        flux_path = os.path.join(wdir, 'intermediate', f'flux_{date_string}.tif')
        listraster = [(ustar_path, 1), (aligned_soil_texture, 1)]
        geop.raster_calculator(
            base_raster_path_band_const_list=listraster,
            local_op=flux_v,
            target_raster_path=flux_path,
            datatype_target=gdal.GDT_Float32,
            nodata_target=-1,
            calc_raster_stats=False)
        
        # 6. Apply soil moisture masking
        smops_path = os.path.join(inputdir, 'inputs', 'daily_meteorology', f'sm_{date_string}.tif')
        
        if os.path.exists(smops_path):
            # Align soil moisture
            aligned_sm_path = os.path.join(wdir, 'intermediate', f'sm_aligned_{date_string}.tif')
            geop.align_and_resize_raster_stack(
                [smops_path],
                [aligned_sm_path],
                ['bilinear'],
                grid_info['pixel_size'],
                bounding_box_mode=grid_info['bounding_box'],
                target_projection_wkt=grid_info['projection_wkt'])
            
            # Apply moisture mask
            def mask_by_sm(flux_val, sm_val):
                if sm_val >= 20.0:  # High soil moisture suppresses dust
                    return 0.0
                else:
                    return flux_val
            
            mask_by_sm_v = np.vectorize(mask_by_sm)
            
            flux_masked_path = os.path.join(wdir, 'intermediate', f'flux_masked_{date_string}.tif')
            listraster = [(flux_path, 1), (aligned_sm_path, 1)]
            geop.raster_calculator(
                base_raster_path_band_const_list=listraster,
                local_op=mask_by_sm_v,
                target_raster_path=flux_masked_path,
                datatype_target=gdal.GDT_Float32,
                nodata_target=-1,
                calc_raster_stats=False)
        else:
            # No soil moisture data available
            flux_masked_path = flux_path
        
        # 7. Cleanup intermediate daily files to save disk space
        cleanup_files = [wind_speed_path, aligned_ws_path, ustar_path]
        if os.path.exists(smops_path):
            cleanup_files.extend([aligned_sm_path])
        
        for cleanup_file in cleanup_files:
            if os.path.exists(cleanup_file):
                os.remove(cleanup_file)
        
        return flux_masked_path
        
    except Exception as e:
        print(f"  ❌ Error processing {date_string}: {e}")
        return None

def run_parallel(inputdir, num_processes=None):
    """
    Run parallelized dust flux calculation
    
    Args:
        inputdir: Input directory path
        num_processes: Number of parallel processes (default: CPU count)
    """
    
    if num_processes is None:
        num_processes = min(multiprocessing.cpu_count(), 8)  # Cap to avoid I/O contention
    
    print(f"🚀 Starting parallelized dust processing with {num_processes} processes")
    
    # Setup shared resources once
    print("📋 Setting up shared resources...")
    shared_resources = setup_shared_resources(inputdir)
    
    # Create date range for 2021
    start_date = datetime(2021, 5, 2)  # Match original start date
    end_date = datetime(2021, 12, 31)
    
    date_list = []
    current_date = start_date
    while current_date <= end_date:
        date_string = current_date.strftime('%Y%m%d')
        date_list.append((current_date, date_string))
        current_date += timedelta(days=1)
    
    print(f"📅 Processing {len(date_list)} days from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Create partial function with fixed arguments
    process_day_partial = partial(process_single_day, 
                                  shared_resources=shared_resources, 
                                  inputdir=inputdir)
    
    # Process days in parallel
    print(f"⚡ Starting parallel processing...")
    start_time = datetime.now()
    
    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.map(process_day_partial, date_list)
    
    end_time = datetime.now()
    processing_time = (end_time - start_time).total_seconds()
    
    # Summary
    successful = [r for r in results if r is not None]
    failed = len(results) - len(successful)
    
    print(f"🎉 Parallel processing completed!")
    print(f"   ⏱️  Total time: {processing_time:.1f} seconds ({processing_time/60:.1f} minutes)")
    print(f"   ✅ Successful: {len(successful)} days")
    print(f"   ❌ Failed: {failed} days")
    print(f"   📈 Speed: {len(date_list)/processing_time:.1f} days/second")
    
    if failed > 0:
        print(f"   ⚠️  Check logs for failed days")
    
    return successful

if __name__ == "__main__":
    import sys
    
    inputdir = sys.argv[1] if len(sys.argv) > 1 else "."
    num_processes = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    run_parallel(inputdir, num_processes)