def run(inputdir):
    import pygeoprocessing.geoprocessing as geop
    from osgeo import gdal
    import math
    import os
    import numpy as np
    from netCDF4 import Dataset
    import rasterio
    from rasterio.transform import from_origin
    from rasterio.warp import reproject, Resampling
    from datetime import datetime, timedelta
    import numpy

    wdir                = "./"

    # Get reference grid info for dynamic sizing
    soc_raster_out       = os.path.join(wdir,'grid.tif')
    grid_info = geop.get_raster_info(soc_raster_out)
    grid_height, grid_width = grid_info['raster_size'][1], grid_info['raster_size'][0]

    # Define the start and end dates in YYYYMMDD format
    start_date = datetime(2020, 12, 31)
    end_date = datetime(2021, 12, 31)  # Adjust this date to your desired end date

    # Create a list to store consecutive dry days for each grid cell (dynamic sizing)
    dry_days = np.zeros((grid_height, grid_width), dtype=int)  # Dynamic grid size

    current_dry_days = np.zeros((grid_height, grid_width), dtype=int)

    pulse = np.zeros((grid_height, grid_width), dtype=int)
    tot_pulse = np.zeros((grid_height, grid_width), dtype=int)

    for date in [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]:
        print(date)
        file_path = os.path.join(inputdir, "inputs", "SMOPS", f"NPR_SMOPS_CMAP_D{date.strftime('%Y%m%d')}.nc")

        if os.path.isfile(file_path):
            # Open the NetCDF file
            with Dataset(file_path, 'r') as ncfile:
                blended_sm = ncfile.variables['Blended_SM'][:]

        # We also want to read the previous day to check for wetting events
        prev_date = date - timedelta(days=1)
        prev_day_path = os.path.join(inputdir, "inputs", "SMOPS", f"NPR_SMOPS_CMAP_D{prev_date.strftime('%Y%m%d')}.nc")
        if os.path.isfile(prev_day_path):
            # Open the NetCDF file
            with Dataset(prev_day_path, 'r') as ncfile:
                prev_day_sm = ncfile.variables['Blended_SM'][:]

        # Check for dry conditions *in the previous day*
        dry_mask = prev_day_sm < 0.175
        current_dry_days[dry_mask] += 1
        current_dry_days[~dry_mask] = 1 # this could be 0 but we want the numpy.log
        # to not throw an error. So long as it is <3 the dry_days_mask will mask
        # out the result.

        # Update dry_days where *previous* consecutive dry days >= 3
        # assign the number of dry days
    #        dry_days[current_dry_days >= 3] = current_dry_days[current_dry_days >= 3]
        dry_days_mask = current_dry_days >= 3

        # Check for wetting events
        change_sm   = blended_sm - prev_day_sm
        wet_mask = change_sm > 0.5 # this should be 0.5 in the 6 hour context.
        # Consider changing to a larger number when you use more days than in this test data.

        # If there is a wetting event and the previous dry days >=3
        # then that triggers a pulse, which is a function of the
        # number of previous dry days (current_dry_days)
    #        pulse[wet_mask] = 13.01 * current_dry_days[wet_mask]
        pulse = 13.01 * numpy.log(current_dry_days*24.0) - 53.6
        pulse[~wet_mask] = 1.0
        pulse[~dry_days_mask] = 1.0

        # Add the pulses together, only if we're reporting the sm without ts
        # tot_pulse = tot_pulse + pulse

        # Make an intermediate raster
        output_sm = 'intermediate/sm.tif'
        rows, cols = pulse.shape
        transform = from_origin(-180, 90, 0.25, 0.25)  # Adjust the resolution as needed

        with rasterio.open(output_sm, 'w', driver='GTiff', height=rows, width=cols, count=1, dtype='uint8', crs='+proj=latlong', transform=transform) as dst:
            dst.write(pulse, 1)

        # We also want to open the soil temperature data, which is hourly rather than daily,
        # and the resolution is 0.625 x 0.5 rather than 0.25 x 0.25, and the latitude order
        # is flipped.
#        merra_path = f'../pkg/inputs/MERRA2/MERRA2_400.tavg1_2d_slv_Nx.{date.strftime("%Y%m%d")}.nc4'
#        merra_path_2 = f'../pkg/inputs/MERRA2/MERRA2_401.tavg1_2d_slv_Nx.{date.strftime("%Y%m%d")}.nc4'
        merra_path = os.path.join(inputdir, "inputs", "MERRA2", f"MERRA2_400.tavg1_2d_slv_Nx.{date.strftime('%Y%m%d')}.nc4")
        merra_path_2 = os.path.join(inputdir, "inputs", "MERRA2", f"MERRA2_401.tavg1_2d_slv_Nx.{date.strftime('%Y%m%d')}.nc4")

        if os.path.isfile(merra_path):
            # Open the NetCDF file
            with Dataset(merra_path, 'r') as ncfile:
                soiltemp = ncfile.variables['TS'][:]
        else:
            with Dataset(merra_path_2, 'r') as ncfile:
                soiltemp = ncfile.variables['TS'][:]

        # Note that we are subtracting the reference temperature
        # for the cold climate zone. The effect of the other climate zones is taken
        # into account separately (it is temporally fixed).
        temperature_exponent = np.exp(0.11 * (soiltemp - 286.69))
        # Sum the exponents across the time dimension
        temperature_day_exponent = temperature_exponent.sum(axis=0)
        # Flip the latitudes
        temperature_day_exponent = np.flip(temperature_day_exponent, axis=0)

        # Make an intermediate raster
        output_ts = 'intermediate/ts.tif'
        rows, cols = temperature_day_exponent.shape
        transform = from_origin(-180, 90, 0.625, 0.5)  # Adjust the resolution as needed

        with rasterio.open(output_ts, 'w', driver='GTiff', height=rows, width=cols, count=1, dtype='uint8', crs='+proj=latlong', transform=transform) as dst:
            dst.write(temperature_day_exponent, 1)

        # For each day, we can combine the effects of soil moisture and temperature
        # First, align and resize the data.

        aligned_ts_path      = os.path.join(wdir, 'intermediate', "aligned_ts.tif")
        aligned_sm_path      = os.path.join(wdir, 'intermediate', "aligned_sm.tif")
        geop.align_and_resize_raster_stack(
            [output_ts, output_sm],
            [aligned_ts_path, aligned_sm_path],
            ['bilinear', 'bilinear'],
            geop.get_raster_info(soc_raster_out)['pixel_size'],
            bounding_box_mode='union')
        # Then, make a function to sum the results properly. Note that although the soil
        # moisture pulse is daily rather than hourly, because it is multiplicative rather
        # than additive, you do not multiply it by 24.
        def ts_sm(ts,sm):
            return sm * ts

        ts_sm_v = np.vectorize(ts_sm)

        list_raster = [(aligned_ts_path,1), (aligned_sm_path,1)]
        # This is where the result is saved for each day
        ts_sm_raster_out       = f'intermediate/ts_sm_effect_{date.strftime("%Y%m%d")}.tif'
        # ts_sm_raster_out       = os.path.join(wdir, 'intermediate', 'ts_sm_effect.tif')
        
        # Then, we generate the result for each day
        geop.raster_calculator(base_raster_path_band_const_list=list_raster,
                                       local_op=ts_sm, 
                                       target_raster_path=ts_sm_raster_out,
                                       datatype_target=gdal.GDT_Float32,
                                       nodata_target=-1,
                                       calc_raster_stats=False)


    """
    # Create a TIFF file to represent the dry areas
    if np.any(tot_pulse):
        # Specify output file and parameters
        output_tiff = 'intermediate/pulse.tif'
        rows, cols = pulse.shape
        transform = from_origin(-180, 90, 0.25, 0.25)  # Adjust the resolution as needed

        # Create a raster with the dry_days array
        with rasterio.open(output_tiff, 'w', driver='GTiff', height=rows, width=cols, count=1, dtype='uint8', crs='+proj=latlong', transform=transform) as dst:
            dst.write(tot_pulse, 1)

        print(f"Consecutive dry days between {start_date.strftime('%Y%m%d')} and {end_date.strftime('%Y%m%d')} have been saved to '{output_tiff}'.")
    else:
        print(f"No consecutive dry days found within the specified date range ({start_date.strftime('%Y%m%d')} - {end_date.strftime('%Y%m%d')}).")
    """

