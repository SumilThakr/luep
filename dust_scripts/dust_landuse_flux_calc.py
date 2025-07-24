def run(inputdir):
    """
    Calculate dust fluxes using pre-processed meteorology + current land use (LAND USE DEPENDENT)
    Much faster since meteorology is already processed
    """
    import pygeoprocessing.geoprocessing as geop
    from osgeo import gdal
    import math
    import os
    import numpy as np
    from datetime import datetime, timedelta
    
    print("Calculating dust fluxes with current land use...")
    
    wdir = "./"
    
    # Get reference grid info
    soc_raster_out = os.path.join(wdir,'grid.tif')
    grid_info = geop.get_raster_info(soc_raster_out)
    
    # Full year 2021
    start_date = datetime(2021, 1, 1)
    end_date = datetime(2021, 12, 31)
    
    # Load pre-aligned soil texture
    aligned_soil_texture = "intermediate/aligned_soil_texture.tif"
    if not os.path.exists(aligned_soil_texture):
        soil_texture_path = "intermediate/soil_texture.tif"
        geop.align_and_resize_raster_stack(
            [soil_texture_path],
            [aligned_soil_texture],
            ['bilinear'],
            geop.get_raster_info(soc_raster_out)['pixel_size'],
            bounding_box_mode=geop.get_raster_info(soc_raster_out)['bounding_box'],
            target_projection_wkt=geop.get_raster_info(soc_raster_out)['projection_wkt'])
    
    # Emission flux equations (units: g cm-2 s-1)
    def flux(ustar, soiltype):
        if soiltype == 0: #MS
            return 1.243*(10.0 **(-7)) * ustar ** 2.64
        elif soiltype == 1: #NA
            return 0.0
        elif soiltype == 2: #FSS
            return 2.45*(10.0 ** (-6)) * ustar ** 3.97
        elif soiltype == 3: #FS
            return 9.33*(10.0 ** (-7)) * ustar ** 2.44
        elif soiltype == 4: #CS
            return 1.243*(10.0 ** (-7)) * ustar ** 3.44
        elif soiltype == -1:
            return 0.0
        else:
            raise ValueError("soil type not recognized")
    
    flux_v = np.vectorize(flux)
    
    def multiply_raster(x,y):
        return x * y
    
    multiply_raster_v = np.vectorize(multiply_raster)
    
    ############################################################
    # Calculate land use effects (LAND USE DEPENDENT)
    ############################################################
    
    lu_raster = [(os.path.join(inputdir,'inputs', 'gblulcg20_10000.tif'),1)]
    lu_raster_out = os.path.join(wdir,'intermediate','z0_effect_dust.tif')
    
    # Land use to surface roughness mapping
    # Updated to handle Simple 4-class classification system used by UK scenarios:
    # 0 = Other (water, urban, bare), 1 = Cropland, 2 = Grass, 3 = Forest
    def z0(lu):
        k = 100.0
        fdtf = 0.0
        match lu:
            case 0: # Other (water, urban, bare) - Conservative: no dust emissions
                # Since Simple "Other" includes water and urban (no dust) but also 
                # bare areas (high dust), we conservatively assign no dust to avoid
                # overestimation over water/urban areas
                k = 100.0
                fdtf = 0.0
            case 1: # Cropland - moderate dust emissions
                k = 0.0310
                fdtf = 0.75
            case 2: # Grass - moderate dust emissions  
                k = 0.1000
                fdtf = 0.75
            case 3: # Forest - no dust emissions
                k = 50.0
                fdtf = 0.0
            case _: # Any unexpected values - no dust (conservative)
                k = 100.0
                fdtf = 0.0
        
        # Convert to surface roughness effect
        result = fdtf / (2.5 * math.log(1000.0/k))
        return result
    
    z0_v = np.vectorize(z0)
    
    # Calculate z0 effect from current land use
    geop.raster_calculator(base_raster_path_band_const_list=lu_raster,
                          local_op=z0_v, 
                          target_raster_path=lu_raster_out,
                          datatype_target=gdal.GDT_Float32,
                          nodata_target=-1,
                          calc_raster_stats=False)
    
    # Align z0 with grid
    aligned_z0_path = os.path.join(wdir, 'intermediate', 'aligned_z0.tif')
    geop.align_and_resize_raster_stack(
        [lu_raster_out],
        [aligned_z0_path],
        ['bilinear'],
        geop.get_raster_info(soc_raster_out)['pixel_size'],
        bounding_box_mode=geop.get_raster_info(soc_raster_out)['bounding_box'],
        target_projection_wkt=geop.get_raster_info(soc_raster_out)['projection_wkt'])
    
    ############################################################
    # Process each day using pre-processed meteorology
    ############################################################
    
    print(f"Processing {(end_date - start_date).days + 1} days of dust fluxes...")
    
    for date in [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]:
        date_str = date.strftime('%Y%m%d')
        
        # Load pre-processed meteorology
        aligned_ws_path = f'intermediate/daily_meteorology/ws_aligned_{date_str}.tif'
        sm_raster_aligned = f'intermediate/daily_meteorology/sm_aligned_{date_str}.tif'
        
        if not os.path.exists(aligned_ws_path) or not os.path.exists(sm_raster_aligned):
            print(f"Warning: Missing meteorology for {date_str}, skipping...")
            continue
        
        # Calculate ustar (friction velocity)
        ustar_path = f'intermediate/ustar_{date_str}.tif'
        listraster_uri = [(aligned_ws_path,1),(aligned_z0_path,1)]
        geop.raster_calculator(base_raster_path_band_const_list=listraster_uri,
                              local_op=multiply_raster_v, 
                              target_raster_path=ustar_path,
                              datatype_target=gdal.GDT_Float32,
                              nodata_target=-1,
                              calc_raster_stats=False)
        
        # Calculate flux
        flux_path = f'intermediate/flux_{date_str}.tif'
        listraster_ura = [(ustar_path,1),(aligned_soil_texture,1)]
        geop.raster_calculator(base_raster_path_band_const_list=listraster_ura,
                              local_op=flux_v, 
                              target_raster_path=flux_path,
                              datatype_target=gdal.GDT_Float32,
                              nodata_target=-1,
                              calc_raster_stats=False)
        
        # Apply soil moisture mask
        flux_masked_path = f'intermediate/flux_masked_{date_str}.tif'
        listraster_urp = [(sm_raster_aligned,1),(flux_path,1)]
        geop.raster_calculator(base_raster_path_band_const_list=listraster_urp,
                              local_op=multiply_raster_v, 
                              target_raster_path=flux_masked_path,
                              datatype_target=gdal.GDT_Float32,
                              nodata_target=-1,
                              calc_raster_stats=False)
    
    print("✅ Land use flux calculation completed")