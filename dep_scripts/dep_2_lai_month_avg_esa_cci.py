def run(inputdir):
    import os
    import rasterio
    import xarray as xr
    import pandas as pd
    import numpy as np
    from rasterio.warp import transform
    from pyproj import CRS

    # Load the ESA-CCI to Simple_ID mapping for UK scenarios
    esa_cci_mapping_df = pd.read_csv(os.path.join("inputs", 'UK_ESA_CCI_to_Simple_mapping.csv'))
    esa_cci_to_simple = dict(zip(esa_cci_mapping_df['ESA_CCI_Code'], esa_cci_mapping_df['Simple_Class']))

    # Load the UK scenario land-use data (ESA-CCI format)
    with rasterio.open(os.path.join("inputs","scenario_landuse_esa_cci.tif")) as src:
        land_use = src.read(1)
        transform = src.transform
        crs = CRS.from_wkt(src.crs.wkt)
        
        # Get actual coordinate arrays for UK extent first
        height, width = land_use.shape
        rows, cols = np.meshgrid(np.arange(height), np.arange(width), indexing='ij')
        uk_lon, uk_lat = rasterio.transform.xy(transform, rows, cols)
        uk_lat_array = np.array(uk_lat)
        uk_lon_array = np.array(uk_lon)
        
        print(f"UK coordinate ranges: lat {uk_lat_array.min():.3f} to {uk_lat_array.max():.3f}, lon {uk_lon_array.min():.3f} to {uk_lon_array.max():.3f}")

        # Calculate pixel area properly (degrees to meters conversion)
        # At UK latitude (~55°N), 1 degree longitude ≈ 63,500 m, 1 degree latitude ≈ 111,000 m
        uk_center_lat = (uk_lat_array.min() + uk_lat_array.max()) / 2  # ~55°N
        deg_to_m_lat = 111000  # meters per degree latitude (constant)
        deg_to_m_lon = 111000 * np.cos(np.radians(uk_center_lat))  # meters per degree longitude (latitude-dependent)
        
        pixel_size_deg_lat = abs(transform[4])  # degrees per pixel in latitude
        pixel_size_deg_lon = abs(transform[0])  # degrees per pixel in longitude
        
        pixel_size_m_lat = pixel_size_deg_lat * deg_to_m_lat
        pixel_size_m_lon = pixel_size_deg_lon * deg_to_m_lon
        pixel_area_m2 = pixel_size_m_lat * pixel_size_m_lon

        # Print pixel area for verification
        print(f"Pixel size: {pixel_size_deg_lat:.6f}° lat × {pixel_size_deg_lon:.6f}° lon")
        print(f"Pixel size: {pixel_size_m_lat:.1f} m lat × {pixel_size_m_lon:.1f} m lon")
        print(f"Pixel area: {pixel_area_m2:.1f} m² ({pixel_area_m2/10000:.3f} hectares)")

        # Flip the latitude axis to match standard orientation
        land_use = np.flipud(land_use)
        uk_lat_array = np.flipud(uk_lat_array)
        uk_lon_array = np.flipud(uk_lon_array)

        # Reclassify ESA-CCI land use data to Simple_IDs, replacing None with -1 to avoid NoneType issues
        simple_land_use = np.vectorize(lambda x: esa_cci_to_simple.get(x, -1))(land_use)

    # Load the LAI data and compute monthly averages
    lai_ds = xr.open_dataset('./intermediate/coarse_averaged_LAI_SimpleID.nc')

    # Calculate monthly average for each Simple_ID class
    # Convert time from minutes to days and group by month
    lai_ds['time'] = xr.cftime_range(start="2020-01-01", periods=len(lai_ds.time), freq="8D")
    monthly_lai_ds = lai_ds.resample(time="M").mean()

    # Prepare output arrays for each month
    for month in range(1, 13):
        # Initialize an array for this month's LAI result
        lai_result = np.zeros_like(simple_land_use, dtype=np.float32)

        # Loop through each unique Simple_ID (excluding -1) and apply monthly LAI from corresponding Simple_ID
        for simple_id in [sid for sid in np.unique(simple_land_use) if sid != -1]:
            # Access LAI data for the specific month and Simple_ID, selecting only the 2D spatial data
            lai_for_id = monthly_lai_ds[f"LAI_SimpleID_{int(simple_id)}"].sel(time=f"2020-{month:02d}").squeeze()

            # Resample LAI data to match the UK land-use coordinates
            lai_resampled = lai_for_id.interp(
                lat=uk_lat_array[:, 0],  # Use actual UK latitudes (1D from the first column)
                lon=uk_lon_array[0, :],  # Use actual UK longitudes (1D from the first row)
                method="nearest"
            )

            # Generate a mask for where this Simple_ID matches in the land-use data
            mask = (simple_land_use == simple_id)

            # Apply mask to LAI and multiply by pixel area
            masked_lai = lai_resampled.values * mask * pixel_area_m2

            # Assign the masked and area-scaled LAI values to the output array
            lai_result[mask] = masked_lai[mask]

        # Convert the result to an xarray DataArray and save as a NetCDF file for each month
        lai_data_array = xr.DataArray(
            lai_result,
            dims=("lat", "lon"),
            coords={
                "lat": uk_lat_array[:, 0],  # Use actual UK latitudes
                "lon": uk_lon_array[0, :]   # Use actual UK longitudes
            },
            name=f"leaf_area"
        )

        # Save monthly LAI to a separate NetCDF file
        lai_data_array.to_netcdf(f"./intermediate/leaf_area_{month:02d}.nc")