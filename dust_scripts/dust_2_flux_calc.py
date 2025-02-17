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

    ############################################################
    ############### Windblown dust emissions ###################
    ############################################################

    wdir                = "./"

    # just for the pixel size
    soc_raster_out       = os.path.join(wdir,'grid.tif')
    print(geop.get_raster_info(soc_raster_out))

    # Define the start and end dates in YYYYMMDD format
    start_date = datetime(2021, 5, 2)
    end_date = datetime(2021, 12, 31)  # Adjust this date to your desired end date
    # end_date = datetime(2021, 12, 31)  # Adjust this date to your desired end date

    # Load the soil texture data, generated from soil_texture.py, and align it
    soil_texture_path           = "intermediate/soil_texture.tif"
    aligned_soil_texture        = "intermediate/aligned_soil_texture.tif"

    geop.align_and_resize_raster_stack(
            [soil_texture_path],
            [aligned_soil_texture],
            ['bilinear'],
            geop.get_raster_info(soc_raster_out)['pixel_size'],
            bounding_box_mode=geop.get_raster_info(soc_raster_out)['bounding_box'],
            target_projection_wkt=geop.get_raster_info(soc_raster_out)['projection_wkt'])

    # Note: these are the assignments [0 = 'MS', 1 = 'NA', 2 = 'FSS', 3 = 'FS', 4 = 'CS']
    # Create a functional that specifies a flux(ustar) dependent on the soil type
    # Here are the emission flux equations (units: g cm-2 s-1)
    def flux(ustar, soiltype):
        # MS: F = 1.243 *10^-7 * ustar^2.64
        if soiltype == 0: #MS
            return 1.243*(10.0 **(-7)) * ustar ** 2.64
        elif soiltype == 1: #NA
            return 0.0
        # FFS:F = 2.45 *10^-6 * ustar^3.97
        elif soiltype == 2: #FSS
            return 2.45*(10.0 ** (-6)) * ustar ** 3.97
        # FS: F = 9.33 *10^-7 * ustar^2.44
        elif soiltype == 3: #FS
            return 9.33*(10.0 ** (-7)) * ustar ** 2.44
        # CS: F = 1.24 *10^-7 * ustar^3.44
        elif soiltype == 4: #CS
            return 1.243*(10.0 ** (-7)) * ustar ** 3.44
        elif soiltype == -1: #CS
            return 0.0
        else:
            raise ValueError("soil type not recognized")

    flux_v = np.vectorize(flux)

    # Create a function that multiplies two rasters together
    def multiply_raster(x,y):
        return x * y

    multiply_raster_v = np.vectorize(multiply_raster)

    ############################################################
    # 1         Effect of land cover
    ############################################################

    # This is a test clip of India at full resolution:
    #lu_raster      = [(os.path.join(wdir,'inputs', 'test_data', 'clip.tif'),1)]

    # This is the global data at full resolution:
    #lu_raster      = [(os.path.join(wdir,'inputs', 'gblulcg20.tif'),1)]

    # And this is the global data at 10km resolution:
    lu_raster      = [(os.path.join(inputdir,'inputs', 'test_data', 'gblulcg20.tif'),1)]
    lu_raster_out       = os.path.join(wdir,'intermediate','z0_effect_dust.tif')


    # Using IGBP inputs (same as with soil NOx), we can make a mapping.
    #Value  Code        Class Name                                      Map
    #1      100         Urban and Built-Up Land                         Urban
    #2      211         Dryland Cropland and Pasture                    Agricultural
    #3      212         Irrigated Cropland and Pasture                  Agricultural
    #4      213         Mixed Dryland/Irrigated Cropland and Pasture    Agricultural
    #5      280         Cropland/Grassland Mosaic                       Agricultural
    #6      290         Cropland/Woodland Mosaic                        Agricultural
    #7      311         Grassland                                       Grassland
    #8      321         Shrubland                                       Scrubland
    #9      330         Mixed Shrubland/Grassland                       Scrubland
    #10     332         Savanna                                         Barren
    #11     411         Deciduous Broadleaf Forest                      Forest
    #12     412         Deciduous Needleleaf Forest                     Forest
    #13     421         Evergreen Broadleaf Forest                      Forest
    #14     422         Evergreen Needleleaf Forest                     Forest
    #15     430         Mixed Forest                                    Forest
    #16     500         Water Bodies                                    NA
    #17     620         Herbaceous Wetland                              NA
    #18     610         Wooded Wetland                                  NA
    #19     770         Barren or Sparsely Vegetated                    Barren
    #20     820         Herbaceous Tundra                               Scrubland
    #21     810         Wooded Tundra                                   Scrubland
    #22     850         Mixed Tundra                                    Scrubland
    #23     830         Bare Ground Tundra                              Barren
    #24     900         Snow or Ice                                     NA
    #100                NO DATA                                         NA



    # The following table is used to parameterise the model for
    # each land use classification:
    # LULC          FDTF        DISTURBED       Z0 (CM)
    # Barren        1.0         Undisturbed     0.0020
    # Agricultural  0.75        Disturbed       0.0310
    # Grassland     0.75        Undisturbed     0.1000
    # Scrubland     0.75        Undisturbed     0.0500
    # Forest        0.0         Undisturbed     50.0
    # Urban         0.0         Undisturbed     50.0

    # We want the following.
    def z0(lu):
        k = 100.0
        fdtf = 0.0
        match lu:
            case 1:
                k = 50.0
                fdtf = 0.0
            case 2:
                k = 0.0310
                fdtf = 0.75
            case 3:
                k = 0.0310
                fdtf = 0.75
            case 4:
                k = 0.0310
                fdtf = 0.75
            case 5:
                k = 0.0310
                fdtf = 0.75
            case 6:
                k = 0.0310
                fdtf = 0.75
            case 7:
                k = 0.1000
                fdtf = 0.75
            case 8:
                k = 0.0500
                fdtf = 0.75
            case 9:
                k = 0.0500
                fdtf = 0.75
            case 10:
                k = 0.0020
                fdtf = 0.75
            case 11:
                k = 50.0
                fdtf = 0.0
            case 12:
                k = 50.0
                fdtf = 0.0
            case 13:
                k = 50.0
                fdtf = 0.0
            case 14:
                k = 50.0
                fdtf = 0.0
            case 15:
                k = 50.0
                fdtf = 0.0
            case 19:
                k = 0.0020
                fdtf = 1.0
            case 20:
                k = 0.0500
                fdtf = 0.75
            case 21:
                k = 0.0500
                fdtf = 0.75
            case 22:
                k = 0.0500
                fdtf = 0.75
            case 23:
                k = 0.0020
                fdtf = 1.0
        # Remember to change units: z is 10.0 meters = 1000 cm
        result          = fdtf / (2.5 * math.log(1000.0/k))
        # This can be multiplied by the wind speed to get u*
        return result

    z0_v = np.vectorize(z0)

    geop.raster_calculator(base_raster_path_band_const_list=lu_raster,
                                       local_op=z0_v, 
                                       target_raster_path=lu_raster_out,
                                       datatype_target=gdal.GDT_Float32,
                                       nodata_target=-1,
                                       calc_raster_stats=False)

    # Align with MERRA2 data.
    aligned_z0_path      = os.path.join(wdir, 'intermediate', 'aligned_z0.tif')
    #merratif             = os.path.join(wdir, 'inputs', 'MERRA2', 'ws_20201231.tif')

    # Note: units are in m not degrees. So resizing this to (0.625,0.5) assumes meters!
    # You need to set the target_projection_wkt and bounding_box as well.
    '''
    geop.align_and_resize_raster_stack(
            [lu_raster_out],
            [aligned_z0_path],
            ['bilinear'],
            geop.get_raster_info(merratif)['pixel_size'],
            bounding_box_mode=geop.get_raster_info(merratif)['bounding_box'],
            target_projection_wkt=geop.get_raster_info(merratif)['projection_wkt'])

    '''
    # This works, but I wanted to align it to MERRA2 instead of soc_raster_out
    geop.align_and_resize_raster_stack(
            [lu_raster_out],
            [aligned_z0_path],
            ['bilinear'],
            geop.get_raster_info(soc_raster_out)['pixel_size'],
            bounding_box_mode=geop.get_raster_info(soc_raster_out)['bounding_box'],
            target_projection_wkt=geop.get_raster_info(soc_raster_out)['projection_wkt'])

    ############################################################
    # 2         Effect of Wind Speed 
    ############################################################

    # Create a list to store consecutive dry days for each grid cell
    # (This is to set up the precipitation effect)
    dry_days = np.zeros((720, 1440), dtype=int)  # Assuming a 0.5x0.5 degree grid

    current_dry_days = np.zeros((720, 1440), dtype=int)

    # Calculate total wind speed

    for date in [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]:
        print(date)

        # We want to open the wind speed data, which is hourly rather than daily,
        # and the resolution is 0.625 x 0.5, and the latitude order is flipped.
        merra_path = os.path.join(inputdir, "inputs", "MERRA2", f"MERRA2_400.tavg1_2d_slv_Nx.{date.strftime('%Y%m%d')}.nc4")
        merra_path_2 = os.path.join(inputdir, "inputs", "MERRA2", f"MERRA2_401.tavg1_2d_slv_Nx.{date.strftime('%Y%m%d')}.nc4")
#        merra_path = f'inputs/MERRA2/MERRA2_400.tavg1_2d_slv_Nx.{date.strftime("%Y%m%d")}.nc4'
#        merra_path_2 = f'inputs/MERRA2/MERRA2_401.tavg1_2d_slv_Nx.{date.strftime("%Y%m%d")}.nc4'

        if os.path.isfile(merra_path):
            # Open the NetCDF file
            with Dataset(merra_path, 'r') as ncfile:
                east_wind = ncfile.variables['U10M'][:]
                north_wind = ncfile.variables['V10M'][:]
        else:
            with Dataset(merra_path_2, 'r') as ncfile:
                east_wind = ncfile.variables['U10M'][:]
                north_wind = ncfile.variables['V10M'][:]

        wind_speed = np.sqrt(np.square(east_wind) + np.square(north_wind))

        # Flip the latitudes
        wind_speed = wind_speed.mean(axis=0) #this averages wind speed over the day, which we do for now as a simplification
        wind_speed = np.flip(wind_speed, axis=0) #if you don't average, the axis should be '1' I think
    #    wind_speed = np.flip(wind_speed, axis=1)

        # Make an intermediate raster
        ws_raster_out       = f'intermediate/ws_{date.strftime("%Y%m%d")}.tif'
        rows, cols = wind_speed.shape
        transform = from_origin(-180, 90, 0.625, 0.5)  # Adjust the resolution as needed

        with rasterio.open(ws_raster_out, 'w', driver='GTiff', height=rows, width=cols, count=1, dtype='uint8', crs='+proj=latlong', transform=transform) as dst:
            dst.write(wind_speed, 1)

        # align with aligned_z0_path and multiply to get u*. This would have to be changed to make it hourly (#TODO)
        aligned_ws_path          = f'intermediate/ws_align_{date.strftime("%Y%m%d")}.tif'
        geop.align_and_resize_raster_stack(
                [ws_raster_out],
                [aligned_ws_path],
                ['bilinear'],
                geop.get_raster_info(soc_raster_out)['pixel_size'],
                bounding_box_mode=geop.get_raster_info(soc_raster_out)['bounding_box'],
                target_projection_wkt=geop.get_raster_info(soc_raster_out)['projection_wkt'])

        # Multiply with the z0 function to get ustar
        ustar_path               = f'intermediate/ustar_{date.strftime("%Y%m%d")}.tif'
        listraster_uri = [(aligned_ws_path,1),(aligned_z0_path,1)]
        geop.raster_calculator(base_raster_path_band_const_list=listraster_uri,
                                           local_op=multiply_raster_v, 
                                           target_raster_path=ustar_path,
                                           datatype_target=gdal.GDT_Float32,
                                           nodata_target=-1,
                                           calc_raster_stats=False)
        
        # The ustar and soil texture should be aligned, and so you should be able to get the flux
        flux_path                = f'intermediate/flux_{date.strftime("%Y%m%d")}.tif'
        listraster_ura = [(ustar_path,1),(aligned_soil_texture,1)]
        geop.raster_calculator(base_raster_path_band_const_list=listraster_ura,
                                           local_op=flux_v, 
                                           target_raster_path=flux_path,
                                           datatype_target=gdal.GDT_Float32,
                                           nodata_target=-1,
                                           calc_raster_stats=False)

        # do the soil moisture mask to update the ustar to zero when the soil is wet
        # sum it in another script

        ############################################################
        # 2         Soil moisture mask
        ############################################################
        # We model the effect of precipitation by resetting to 0.0 the wind speed
        # (thereby making the emissions flux null) on days when the soil moisture is
        # above 2%, using a figure from this paper: doi.org/10.1016/j.partic.2016.03.001
        # (Resetting the wind speed is kind of annoying. Won't you then
        # have to align all the SMOPS with the MERRA data?)

        # We want to read the soil moisture data for the same day
        sm_path = os.path.join(inputdir, "inputs", "SMOPS", f"NPR_SMOPS_CMAP_D{date.strftime('%Y%m%d')}.nc")
        if os.path.isfile(sm_path):
            # Open the NetCDF file
            with Dataset(sm_path, 'r') as ncfile:
                sm_data = ncfile.variables['Blended_SM'][:]

        # Check for dry conditions
        dry_mask = sm_data < 0.1

        # Make an intermediate raster
        sm_raster_out       = f'intermediate/sm_{date.strftime("%Y%m%d")}.tif'
        rows, cols = dry_mask.shape
        transform = from_origin(-180, 90, 0.25, 0.25)  # Adjust the resolution as needed

        with rasterio.open(sm_raster_out, 'w', driver='GTiff', height=rows, width=cols, count=1, dtype='uint8', crs='+proj=latlong', transform=transform) as dst:
            dst.write(dry_mask, 1)

        # Align the sm_raster_out with the flux
        sm_raster_aligned   = f'intermediate/sm_aligned{date.strftime("%Y%m%d")}.tif'
        geop.align_and_resize_raster_stack(
                [sm_raster_out],
                [sm_raster_aligned],
                ['bilinear'],
                geop.get_raster_info(soc_raster_out)['pixel_size'],
                bounding_box_mode=geop.get_raster_info(soc_raster_out)['bounding_box'],
                target_projection_wkt=geop.get_raster_info(soc_raster_out)['projection_wkt'])

        # Multiply the flux
        flux_masked_path               = f'intermediate/flux_masked_{date.strftime("%Y%m%d")}.tif'
        listraster_urp = [(sm_raster_aligned,1),(flux_path,1)]
        geop.raster_calculator(base_raster_path_band_const_list=listraster_urp,
                                           local_op=multiply_raster_v, 
                                           target_raster_path=flux_masked_path,
                                           datatype_target=gdal.GDT_Float32,
                                           nodata_target=-1,
                                           calc_raster_stats=False)

    '''
        # Make an intermediate raster
        ws_raster_out       = f'intermediate/ws_{date.strftime("%Y%m%d")}.tif'
        rows, cols = wind_speed.shape
        transform = from_origin(-180, 90, 0.625, 0.5)  # Adjust the resolution as needed

        with rasterio.open(ws_raster_out, 'w', driver='GTiff', height=rows, width=cols, count=1, dtype='uint8', crs='+proj=latlong', transform=transform) as dst:
            dst.write(wind_speed, 1)
    '''
