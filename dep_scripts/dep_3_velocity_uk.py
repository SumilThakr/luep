def run(inputdir=""):
    """
    UK-optimized deposition velocity calculation
    
    This version processes UK-cropped MERRA2 data for dramatic performance improvement.
    Uses pre-cropped wind data from inputs/uk_cropped/MERRA2/ instead of global data.
    
    Args:
        inputdir: Base input directory (typically "")
    """
    import xarray as xr
    import pandas as pd
    import numpy as np
    from glob import glob
    import os

    print("=" * 60)
    print("UK-OPTIMIZED DEPOSITION VELOCITY CALCULATION")
    print("=" * 60)

    # Load the deposition velocity data from CSV
    print("Loading deposition velocity data from CSV...")
    dep_df = pd.read_csv(os.path.join("inputs", 'dep_v.csv'))
    dep_df['Effective_dep'] = dep_df['Avg_dep'] * (dep_df['Resusp'] / 100.0)  # Calculate effective deposition
    print("Deposition data loaded.")

    # Function to get deposition velocity based on wind speed
    def get_effective_dep_velocity(wind_speed):
        # Interpolate based on wind speed
        return np.interp(wind_speed, dep_df['Wind_speed'], dep_df['Effective_dep'])

    # Define the period of interest
    year = 2021
    months = range(1, 13)  # Process all 12 months for UK scenarios

    # Directory where UK-cropped daily NetCDF files are stored
    data_dir = "inputs/uk_cropped/MERRA2/"
    
    # Check if UK-cropped data exists
    if not os.path.exists(data_dir):
        print(f"❌ UK-cropped MERRA2 data not found at: {data_dir}")
        print("Please run the meteorological data preprocessor first:")
        print("   /Users/sumilthakrar/yes/envs/rasters/bin/python utils/crop_met_data_uk.py")
        raise FileNotFoundError(f"UK-cropped MERRA2 data directory not found: {data_dir}")

    print(f"Using UK-cropped MERRA2 data from: {data_dir}")

    # Loop through each month and calculate the monthly average deposition velocity
    for month in months:
        print(f"\nProcessing month {month:02d} of {year}...")
        monthly_deposition_list = []

        # Get list of UK-cropped daily files for this month
        month_files = sorted(glob(os.path.join(data_dir, f'MERRA2_uk_{year}{month:02d}*.nc')))
        print(f"Found {len(month_files)} UK-cropped daily files for month {month:02d}.")

        if len(month_files) == 0:
            print(f"⚠️  No UK-cropped files found for month {month:02d}")
            continue

        # Process each daily file
        for day, daily_file in enumerate(month_files, start=1):
            print(f"Processing file {day}/{len(month_files)}: {os.path.basename(daily_file)}")
            if os.path.isfile(daily_file):
                with xr.open_dataset(daily_file) as ds:
                    # Load eastward and northward wind components
                    if 'U10M' in ds.variables and 'V10M' in ds.variables:
                        east_wind = ds['U10M']
                        north_wind = ds['V10M']
                        print(f" - Loaded UK wind data (eastward and northward) for {os.path.basename(daily_file)}")
                    else:
                        print(" - Skipping file, missing U10M or V10M variables.")
                        continue

                    # Calculate wind speed as the magnitude of east and north components
                    wind_speed = np.sqrt(np.square(east_wind) + np.square(north_wind))

                    # Note: No need to flip latitude axis for UK-cropped data (already handled during cropping)
                    print(" - Wind speed calculated for UK region.")

                    # Calculate effective deposition velocity based on wind speed
                    effective_dep_velocity = xr.apply_ufunc(
                        get_effective_dep_velocity, wind_speed, vectorize=True
                    )
                    print(" - Effective deposition velocity calculated for UK region.")

                    # Append hourly deposition velocities for averaging
                    monthly_deposition_list.append(effective_dep_velocity)
                    print(f" - Added UK deposition velocity data for day {day}.")

        # Stack hourly values and calculate monthly mean deposition velocity
        if monthly_deposition_list:
            print(f"Calculating monthly average deposition velocity for UK month {month:02d}...")
            monthly_deposition_velocity = xr.concat(monthly_deposition_list, dim="time").mean(dim="time")
            
            # Save to NetCDF for each month (UK-specific filename)
            output_filename = f'intermediate/deposition_velocity_uk_{year}_{month:02d}.nc'
            monthly_deposition_velocity.to_netcdf(output_filename)
            print(f"✅ UK monthly average deposition velocity saved to {output_filename}")
            
            # Print data size information
            file_size = os.path.getsize(output_filename)
            print(f"   File size: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
            
        else:
            print(f"❌ No data processed for month {month:02d}, skipping output.")

    print(f"\n🎉 UK deposition velocity calculation complete!")
    print(f"📁 UK-specific outputs saved with '_uk_' prefix")
    print(f"💾 Processing UK-only data dramatically reduces computation time")