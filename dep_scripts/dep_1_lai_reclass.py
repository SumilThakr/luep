def run(inputdir):
    import xarray as xr
    import pandas as pd
    import numpy as np
    import os
    
    wdir = "./"

    # Load the mapping file
    mapping_df = pd.read_csv(os.path.join(inputdir, "inputs", "Olson_to_USGS_mapping.csv"))

    # Group by 'Simple_ID' and collect all Olson classes (IDs) under each Simple_ID
    simple_id_to_olson = mapping_df.groupby('Simple_ID')['Olson_ID'].apply(list).to_dict()

    # Open the LAI NetCDF file
    ds = xr.open_dataset(os.path.join(inputdir, "inputs", "LAI", "Yuan_proc_MODIS_XLAI.025x025.2020.nc"))

    # Initialize a dictionary to store results for each Simple_ID
    simple_id_data = {}

    # Step 1: Sum the LAI variables for each Simple_ID class
    for simple_id, olson_ids in simple_id_to_olson.items():
        lai_vars = [f"XLAI{str(olson_id).zfill(2)}" for olson_id in olson_ids if f"XLAI{str(olson_id).zfill(2)}" in ds]
        if lai_vars:
            # Sum across all matched LAI variables for this Simple_ID without needing a "variable" dimension
            simple_id_data[simple_id] = sum(ds[var] for var in lai_vars)

    # Step 2: Average the LAI for each Simple_ID over 1°x1° tiles
    #lat_bins = np.arange(-90, 90 + 1, 1)
    #lon_bins = np.arange(-180, 180 + 1, 1)

    # Step 3: Calculate global averages and fill missing values before coarsening
    for simple_id, data in simple_id_data.items():
        global_avg = data.mean(dim=["lat", "lon"], skipna=True)
        # Replace zeros with NaN, then fill NaNs with the global average
        data = data.where(data != 0, np.nan)
        data = data.fillna(global_avg)

        # Now coarsen, ignoring NaNs (since they've already been filled with global_avg as needed)
        simple_id_data[simple_id] = (
            data.coarsen(lat=4, lon=4, boundary="trim").mean(skipna=True)
        )

    # Step 4: Save as NetCDF
    output_ds = xr.Dataset({f"LAI_SimpleID_{simple_id}": data for simple_id, data in simple_id_data.items()})
    output_ds.to_netcdf("./intermediate/coarse_averaged_LAI_SimpleID.nc")
