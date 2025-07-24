def run(inputdir=""):
    """
    UK-optimized PM2.5 deposition calculation
    
    This version processes UK-cropped data for all components:
    - UK-cropped PM2.5 concentration data
    - UK-only leaf area data (from ESA-CCI scenarios)
    - UK-only deposition velocity data
    
    Args:
        inputdir: Base input directory (typically "")
    """
    import xarray as xr
    import numpy as np
    import os

    print("=" * 60)
    print("UK-OPTIMIZED PM2.5 DEPOSITION CALCULATION")
    print("=" * 60)

    # Define directories and patterns for UK-optimized data
    pm25_dir = "inputs/uk_cropped/concentrations"  # UK-cropped PM2.5 data
    leaf_area_dir = "intermediate"                 # UK leaf area files (from ESA-CCI)
    dep_velocity_dir = "intermediate"              # UK deposition velocity files
    output_dir = "outputs"                         # Directory for saving the results

    # Check if UK-cropped PM2.5 data exists
    if not os.path.exists(pm25_dir):
        print(f"❌ UK-cropped PM2.5 data not found at: {pm25_dir}")
        print("Please run the meteorological data preprocessor first:")
        print("   /Users/sumilthakrar/yes/envs/rasters/bin/python utils/crop_met_data_uk.py")
        raise FileNotFoundError(f"UK-cropped PM2.5 data directory not found: {pm25_dir}")

    print(f"Using UK-cropped PM2.5 data from: {pm25_dir}")
    print(f"Using UK leaf area data from: {leaf_area_dir}")
    print(f"Using UK deposition velocity data from: {dep_velocity_dir}")

    # Define year and months of interest
    year = 2021
    months = range(1, 13)  # Process all 12 months for UK scenarios

    # Initialize variable to accumulate annual deposition
    annual_deposition = None

    # Loop over each month
    for month in months:
        print(f"\nProcessing month {month:02d} of {year}...")
        
        # Define file paths for each dataset (UK-specific)
        pm25_file = os.path.join(pm25_dir, f"GHAP_PM2.5_uk_{year}{month:02d}.nc")
        leaf_area_file = os.path.join(leaf_area_dir, f"leaf_area_{month:02d}.nc")
        dep_velocity_file = os.path.join(dep_velocity_dir, f"deposition_velocity_uk_{year}_{month:02d}.nc")

        # Check if all required files exist
        missing_files = []
        for file_path, file_type in [(pm25_file, "PM2.5"), (leaf_area_file, "Leaf Area"), (dep_velocity_file, "Deposition Velocity")]:
            if not os.path.exists(file_path):
                missing_files.append(f"{file_type}: {file_path}")

        if missing_files:
            print(f"⚠️  Skipping month {month:02d} - missing files:")
            for missing in missing_files:
                print(f"   - {missing}")
            continue

        # Open datasets for the month
        with xr.open_dataset(pm25_file) as pm25_ds, \
             xr.open_dataset(leaf_area_file) as leaf_area_ds, \
             xr.open_dataset(dep_velocity_file) as dep_velocity_ds:
            
            print(f"   Loaded datasets for month {month:02d}")
            
            # Retrieve PM2.5 data as DataArray, applying scale factor if available
            pm25_data = pm25_ds['PM2.5'] * pm25_ds['PM2.5'].attrs.get('scale_factor', 1)
            fill_value = pm25_ds['PM2.5'].attrs.get('_FillValue', pm25_ds['PM2.5'].attrs.get('missing_value', None))
            if fill_value is not None:
                pm25_data = pm25_data.where(pm25_data != fill_value, np.nan)

            # Print dataset shapes for debugging
            print(f"   PM2.5 shape: {pm25_data.shape}")
            print(f"   Leaf area shape: {leaf_area_ds['leaf_area'].shape}")
            print(f"   Deposition velocity shape: {dep_velocity_ds['__xarray_dataarray_variable__'].shape}")

            # Determine smallest resolution grid based on lat/lon interval sizes
            pm25_res = abs(pm25_data.lat.diff(dim="lat").mean().item()), abs(pm25_data.lon.diff(dim="lon").mean().item())
            leaf_area_res = abs(leaf_area_ds.lat.diff(dim="lat").mean().item()), abs(leaf_area_ds.lon.diff(dim="lon").mean().item())
            dep_velocity_res = abs(dep_velocity_ds.lat.diff(dim="lat").mean().item()), abs(dep_velocity_ds.lon.diff(dim="lon").mean().item())

            print(f"   PM2.5 resolution: {pm25_res}")
            print(f"   Leaf area resolution: {leaf_area_res}")
            print(f"   Deposition velocity resolution: {dep_velocity_res}")

            # Set target grid with the smallest resolution
            target_grid = pm25_data
            if leaf_area_res < pm25_res and leaf_area_res < dep_velocity_res:
                target_grid = leaf_area_ds['leaf_area']
                print("   Using leaf area as target grid (highest resolution)")
            elif dep_velocity_res < pm25_res:
                target_grid = dep_velocity_ds['__xarray_dataarray_variable__']
                print("   Using deposition velocity as target grid (highest resolution)")
            else:
                print("   Using PM2.5 as target grid")

            # Interpolate all data to the target grid as DataArrays
            print("   Interpolating datasets to common grid...")
            pm25_resampled = pm25_data.interp_like(target_grid)
            leaf_area_resampled = leaf_area_ds['leaf_area'].interp_like(target_grid)
            dep_velocity_resampled = dep_velocity_ds['__xarray_dataarray_variable__'].interp_like(target_grid)

            # Calculate monthly deposition as DataArray
            print("   Calculating monthly deposition...")
            monthly_deposition = pm25_resampled * leaf_area_resampled * dep_velocity_resampled

            # Accumulate into the annual total
            if annual_deposition is None:
                annual_deposition = monthly_deposition
                print("   Initialized annual deposition accumulator")
            else:
                annual_deposition += monthly_deposition
                print("   Added to annual deposition total")

    # Convert units and finalize calculation
    if annual_deposition is not None:
        print(f"\nFinalizing annual deposition calculation...")
        
        # Convert units
        # leaf area: m2; deposition velocity: cm/s; concentration: ug/m3
        # we want kg/year, so divide by 10^11 and multiply by 60*60*24*365
        annual_deposition = annual_deposition * 60.0 * 60.0 * 24.0 * 365.0 / (10.0 ** 11)
        print("   Applied unit conversion to kg/year")

        # Convert the annual deposition to a Dataset with a clear variable name
        annual_deposition_ds = xr.Dataset({"annual_PM2.5_deposition": annual_deposition})

        # Sort coordinates to ensure standard South-to-North latitude ordering
        if annual_deposition_ds.lat[0] > annual_deposition_ds.lat[1]:
            # If latitude is decreasing (North-to-South), flip to standard South-to-North
            annual_deposition_ds = annual_deposition_ds.isel(lat=slice(None, None, -1))
            print("   Applied latitude axis correction: North-to-South → South-to-North")
        else:
            print("   Latitude axis already in standard South-to-North order")

        # Save the annual total deposition as a single NetCDF file (UK-specific filename)
        os.makedirs(output_dir, exist_ok=True)
        output_filename = os.path.join(output_dir, f"PM2.5_annual_deposition_uk_{year}.nc")
        annual_deposition_ds.to_netcdf(output_filename)
        
        # Print file information
        file_size = os.path.getsize(output_filename)
        print(f"✅ UK annual PM2.5 deposition for {year} saved to {output_filename}")
        print(f"   File size: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
        
        # Print basic statistics
        total_deposition = float(annual_deposition_ds['annual_PM2.5_deposition'].sum().values)
        max_deposition = float(annual_deposition_ds['annual_PM2.5_deposition'].max().values)
        mean_deposition = float(annual_deposition_ds['annual_PM2.5_deposition'].mean().values)
        
        print(f"   Total UK PM2.5 deposition: {total_deposition:,.0f} kg/year")
        print(f"   Maximum pixel deposition: {max_deposition:.6f} kg/year")
        print(f"   Mean pixel deposition: {mean_deposition:.6f} kg/year")
        
    else:
        print(f"❌ No monthly deposition data was processed - check input files")
        raise RuntimeError("No deposition data could be calculated")

    print(f"\n🎉 UK PM2.5 deposition calculation complete!")
    print(f"📁 UK-specific output saved with '_uk_' prefix")
    print(f"💾 Processing UK-only data provides significant performance improvement")