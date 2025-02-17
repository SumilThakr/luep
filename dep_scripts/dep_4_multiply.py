def run(inputdir):
    import xarray as xr
    import numpy as np
    import os

    # Define directories and patterns
    pm25_dir = os.path.join(inputdir, "inputs", "concentrations") # Directory for PM2.5 concentration files
    leaf_area_dir = "intermediate"     # Directory for leaf area files
    dep_velocity_dir = "intermediate" # Directory for deposition velocity files
    output_dir = "outputs"                 # Directory for saving the results

    # Define year and months of interest
    year = 2021
#    months = range(1, 13)
    months = range(1, 2)

    # Initialize variable to accumulate annual deposition
    annual_deposition = None

    # Loop over each month
    for month in months:
        # Define file paths for each dataset
        pm25_file = os.path.join(pm25_dir, f"GHAP_PM2.5_M1K_{year}{month:02d}_V1.nc")
        leaf_area_file = os.path.join(leaf_area_dir, f"leaf_area_{month:02d}.nc")
        dep_velocity_file = os.path.join(dep_velocity_dir, f"deposition_velocity_{year}_{month:02d}.nc")

        # Open datasets for the month
        with xr.open_dataset(pm25_file) as pm25_ds, \
             xr.open_dataset(leaf_area_file) as leaf_area_ds, \
             xr.open_dataset(dep_velocity_file) as dep_velocity_ds:
            
            # Retrieve PM2.5 data as DataArray, applying scale factor if available
            pm25_data = pm25_ds['PM2.5'] * pm25_ds['PM2.5'].attrs.get('scale_factor', 1)
            fill_value = pm25_ds['PM2.5'].attrs.get('_FillValue', pm25_ds['PM2.5'].attrs.get('missing_value', None))
            if fill_value is not None:
                pm25_data = pm25_data.where(pm25_data != fill_value, np.nan)

            # Determine smallest resolution grid based on lat/lon interval sizes
            pm25_res = abs(pm25_data.lat.diff(dim="lat").mean().item()), abs(pm25_data.lon.diff(dim="lon").mean().item())
            leaf_area_res = abs(leaf_area_ds.lat.diff(dim="lat").mean().item()), abs(leaf_area_ds.lon.diff(dim="lon").mean().item())
            dep_velocity_res = abs(dep_velocity_ds.lat.diff(dim="lat").mean().item()), abs(dep_velocity_ds.lon.diff(dim="lon").mean().item())

            # Set target grid with the smallest resolution
            target_grid = pm25_data
            if leaf_area_res < pm25_res and leaf_area_res < dep_velocity_res:
                target_grid = leaf_area_ds
            elif dep_velocity_res < pm25_res:
                target_grid = dep_velocity_ds

            # Interpolate all data to the target grid as DataArrays
            pm25_resampled = pm25_data.interp_like(target_grid)
            leaf_area_resampled = leaf_area_ds['leaf_area'].interp_like(target_grid)
            dep_velocity_resampled = dep_velocity_ds['__xarray_dataarray_variable__'].interp_like(target_grid)

            # Calculate monthly deposition as DataArray
            monthly_deposition = pm25_resampled * leaf_area_resampled * dep_velocity_resampled

            # Accumulate into the annual total
            if annual_deposition is None:
                annual_deposition = monthly_deposition
            else:
                annual_deposition += monthly_deposition

            # Convert units
            # leaf area: m2; deposition velocity: cm/s; concentration: ug/m3
            # we want kg/year, so divide by 10^11 and multiply by 60*60*24*365
            annual_deposition = annual_deposition * 60.0 * 60.0 * 24.0 * 365.0 / (10.0 ** 11)

    # Convert the annual deposition to a Dataset with a clear variable name
    annual_deposition_ds = xr.Dataset({"annual_PM2.5_deposition": annual_deposition})

    # Flip the latitude axis in the DataArray within the Dataset
    annual_deposition_ds['annual_PM2.5_deposition'] = annual_deposition_ds['annual_PM2.5_deposition'].isel(lat=slice(None, None, -1))

    # Save the annual total deposition as a single NetCDF file
    output_filename = os.path.join(output_dir, f"PM2.5_annual_deposition_{year}.nc")
    annual_deposition_ds.to_netcdf(output_filename)
    print(f"Saved annual PM2.5 deposition for {year} to {output_filename}")
