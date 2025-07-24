def run(inputdir):
    """
    Preprocess meteorological data for dust emissions (LAND USE INDEPENDENT)
    Run once for full year 2021, reuse for all scenarios
    """
    import pygeoprocessing.geoprocessing as geop
    from osgeo import gdal
    import os
    import numpy as np
    from netCDF4 import Dataset
    import rasterio
    from rasterio.transform import from_origin
    from datetime import datetime, timedelta
    
    print("Processing meteorology for full year 2021 (land-use independent)...")
    
    wdir = "./"
    
    # Get reference grid info for dynamic sizing
    soc_raster_out = os.path.join(wdir,'grid.tif')
    grid_info = geop.get_raster_info(soc_raster_out)
    grid_height, grid_width = grid_info['raster_size'][1], grid_info['raster_size'][0]
    
    # Define FULL YEAR 2021
    start_date = datetime(2021, 1, 1)
    end_date = datetime(2021, 12, 31)
    
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Total days: {(end_date - start_date).days + 1}")
    
    # Create output directory for daily meteorology
    os.makedirs("intermediate/daily_meteorology", exist_ok=True)
    
    # Process each day's meteorology
    for date in [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]:
        date_str = date.strftime('%Y%m%d')
        print(f"Processing meteorology for {date_str}")
        
        # Process wind speed data
        merra_path = os.path.join(inputdir, "inputs", "MERRA2", f"MERRA2_400.tavg1_2d_slv_Nx.{date_str}.nc4")
        merra_path_2 = os.path.join(inputdir, "inputs", "MERRA2", f"MERRA2_401.tavg1_2d_slv_Nx.{date_str}.nc4")
        
        if os.path.isfile(merra_path):
            with Dataset(merra_path, 'r') as ncfile:
                east_wind = ncfile.variables['U10M'][:]
                north_wind = ncfile.variables['V10M'][:]
        else:
            with Dataset(merra_path_2, 'r') as ncfile:
                east_wind = ncfile.variables['U10M'][:]
                north_wind = ncfile.variables['V10M'][:]
        
        wind_speed = np.sqrt(np.square(east_wind) + np.square(north_wind))
        wind_speed = wind_speed.mean(axis=0)  # Average over day
        wind_speed = np.flip(wind_speed, axis=0)  # Flip latitudes
        
        # Save wind speed raster
        ws_raster_out = f'intermediate/daily_meteorology/ws_{date_str}.tif'
        rows, cols = wind_speed.shape
        transform = from_origin(-180, 90, 0.625, 0.5)
        
        with rasterio.open(ws_raster_out, 'w', driver='GTiff', height=rows, width=cols, 
                          count=1, dtype='float32', crs='+proj=latlong', transform=transform) as dst:
            dst.write(wind_speed, 1)
        
        # Align wind speed with grid
        aligned_ws_path = f'intermediate/daily_meteorology/ws_aligned_{date_str}.tif'
        geop.align_and_resize_raster_stack(
            [ws_raster_out],
            [aligned_ws_path],
            ['bilinear'],
            geop.get_raster_info(soc_raster_out)['pixel_size'],
            bounding_box_mode=geop.get_raster_info(soc_raster_out)['bounding_box'],
            target_projection_wkt=geop.get_raster_info(soc_raster_out)['projection_wkt'])
        
        # Process soil moisture data
        sm_path = os.path.join(inputdir, "inputs", "SMOPS", f"NPR_SMOPS_CMAP_D{date_str}.nc")
        if os.path.isfile(sm_path):
            with Dataset(sm_path, 'r') as ncfile:
                sm_data = ncfile.variables['Blended_SM'][:]
        
        # Check for dry conditions
        dry_mask = sm_data < 0.1
        
        # Save soil moisture raster
        sm_raster_out = f'intermediate/daily_meteorology/sm_{date_str}.tif'
        rows, cols = dry_mask.shape
        transform = from_origin(-180, 90, 0.25, 0.25)
        
        with rasterio.open(sm_raster_out, 'w', driver='GTiff', height=rows, width=cols, 
                          count=1, dtype='uint8', crs='+proj=latlong', transform=transform) as dst:
            dst.write(dry_mask, 1)
        
        # Align soil moisture with grid
        sm_raster_aligned = f'intermediate/daily_meteorology/sm_aligned_{date_str}.tif'
        geop.align_and_resize_raster_stack(
            [sm_raster_out],
            [sm_raster_aligned],
            ['bilinear'],
            geop.get_raster_info(soc_raster_out)['pixel_size'],
            bounding_box_mode=geop.get_raster_info(soc_raster_out)['bounding_box'],
            target_projection_wkt=geop.get_raster_info(soc_raster_out)['projection_wkt'])
        
        # Clean up temporary files to save space
        os.remove(ws_raster_out)
        os.remove(sm_raster_out)
    
    print(f"✅ Meteorological preprocessing completed for {(end_date - start_date).days + 1} days")
    print("Saved aligned meteorology to: intermediate/daily_meteorology/")