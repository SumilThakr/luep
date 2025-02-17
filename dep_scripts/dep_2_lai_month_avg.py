def run(inputdir):
    import os
    import rasterio
    import xarray as xr
    import pandas as pd
    import numpy as np
    from rasterio.warp import transform
    from pyproj import CRS

    # Load the USGS to Simple_ID mapping
    usgs_mapping_df = pd.read_csv(os.path.join(inputdir, "inputs", 'USGS_to_simple_mapping.csv'))
    usgs_to_simple = dict(zip(usgs_mapping_df['Value'], usgs_mapping_df['Simple_ID']))

    # Load the global land-use data (USGS format)
    with rasterio.open(os.path.join(inputdir,"inputs","gblulcg20.tif")) as src:
        land_use = src.read(1)
        transform = src.transform
        crs = CRS.from_wkt(src.crs.wkt)
        pixel_area_m2 = abs(transform[0] * transform[4])  # Calculate area of each pixel
        avg_pixel_area_m2 = np.mean(pixel_area_m2)

        # Print average pixel area for verification
        print("Average pixel area in m^2:", avg_pixel_area_m2) # 1,000,000 m2 apparently, but it should be 10km2 (100x)

        # Flip the latitude axis to match standard orientation
        land_use = np.flipud(land_use)

        # Reclassify land use data to Simple_IDs, replacing None with -1 to avoid NoneType issues
        simple_land_use = np.vectorize(lambda x: usgs_to_simple.get(x, -1))(land_use)

    # Load the LAI data and compute monthly averages
    lai_ds = xr.open_dataset('./intermediate/coarse_averaged_LAI_SimpleID.nc')

    # Calculate monthly average for each Simple_ID class
    # Convert time from minutes to days and group by month
    lai_ds['time'] = xr.cftime_range(start="2020-01-01", periods=len(lai_ds.time), freq="8D")
    monthly_lai_ds = lai_ds.resample(time="M").mean()

    # Prepare output arrays for each month
#    for month in range(1, 13):
    for month in range(1, 2):
        # Initialize an array for this month's LAI result
        lai_result = np.zeros_like(simple_land_use, dtype=np.float32)

        # Loop through each unique Simple_ID (excluding -1) and apply monthly LAI from corresponding Simple_ID
        for simple_id in [sid for sid in np.unique(simple_land_use) if sid != -1]:
            # Access LAI data for the specific month and Simple_ID, selecting only the 2D spatial data
            lai_for_id = monthly_lai_ds[f"LAI_SimpleID_{int(simple_id)}"].sel(time=f"2020-{month:02d}").squeeze()

            # Resample LAI data to match the resolution of the land-use data
            lai_resampled = lai_for_id.interp(
                lat=np.linspace(-90, 90, land_use.shape[0]),
                lon=np.linspace(-180, 180, land_use.shape[1]),
                method="nearest"
            )

            # Generate a mask for where this Simple_ID matches in the land-use data
            mask = (simple_land_use == simple_id)

            # Convert mask to an xarray.DataArray to match the lai_resampled dimensions
            mask_array = xr.DataArray(mask, dims=("lat", "lon"), coords={"lat": lai_resampled.lat, "lon": lai_resampled.lon})

            # Apply mask to LAI, without dropping values, and multiply by pixel area
            masked_lai = lai_resampled.where(mask_array) * pixel_area_m2

            # Assign the masked and area-scaled LAI values to the output array, matching the mask locations
            lai_result[mask] = masked_lai.values[mask]  # Direct mask assignment ensures 1:1 compatibility

        # Convert the result to an xarray DataArray and save as a NetCDF file for each month
        lai_data_array = xr.DataArray(
            lai_result,
            dims=("lat", "lon"),
            coords={
                "lat": np.linspace(-90, 90, land_use.shape[0]),
                "lon": np.linspace(-180, 180, land_use.shape[1])
            },
            name=f"leaf_area"
        )

        # Save monthly LAI to a separate NetCDF file
        lai_data_array.to_netcdf(f"./intermediate/leaf_area_{month:02d}.nc")
