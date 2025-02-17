def run(inputdir):
    import xarray as xr
    import pandas as pd
    import numpy as np
    from glob import glob
    import os

    # Load the deposition velocity data from CSV
    print("Loading deposition velocity data from CSV...")
    dep_df = pd.read_csv(os.path.join(inputdir,'inputs','dep_v.csv'))
    dep_df['Effective_dep'] = dep_df['Avg_dep'] * (dep_df['Resusp'] / 100.0)  # Calculate effective deposition
    print("Deposition data loaded.")

    # Function to get deposition velocity based on wind speed
    def get_effective_dep_velocity(wind_speed):
        # Interpolate based on wind speed
        return np.interp(wind_speed, dep_df['Wind_speed'], dep_df['Effective_dep'])

    # Define the period of interest
    year = 2021
#    months = range(6, 13)
    months = range(1, 2)

    # Directory where daily NetCDF files are stored
    data_dir = os.path.join(inputdir,"inputs",'MERRA2/')

    # Loop through each month and calculate the monthly average deposition velocity
    for month in months:
        print(f"\nProcessing month {month:02d} of {year}...")
        monthly_deposition_list = []

        # Get list of daily files for this month
        month_files = sorted(glob(os.path.join(data_dir, f'MERRA2_*{year}{month:02d}*.nc4')))
        print(f"Found {len(month_files)} daily files for month {month:02d}.")

        # Process each daily file
        for day, daily_file in enumerate(month_files, start=1):
            print(f"Processing file {day}/{len(month_files)}: {os.path.basename(daily_file)}")
            if os.path.isfile(daily_file):
                with xr.open_dataset(daily_file) as ds:
                    # Load eastward and northward wind components
                    if 'U10M' in ds.variables and 'V10M' in ds.variables:
                        east_wind = ds['U10M']
                        north_wind = ds['V10M']
                        print(f" - Loaded wind data (eastward and northward) for {os.path.basename(daily_file)}")
                    else:
                        print(" - Skipping file, missing U10M or V10M variables.")
                        continue

                    # Calculate wind speed as the magnitude of east and north components
                    wind_speed = np.sqrt(np.square(east_wind) + np.square(north_wind))

                    # Flip the latitude axis to correct orientation
                    wind_speed = wind_speed[:, ::-1, :]
                    print(" - Wind speed calculated and latitude flipped.")

                    # Calculate effective deposition velocity based on wind speed
                    effective_dep_velocity = xr.apply_ufunc(
                        get_effective_dep_velocity, wind_speed, vectorize=True
                    )
                    print(" - Effective deposition velocity calculated for current file.")

                    # Append hourly deposition velocities for averaging
                    monthly_deposition_list.append(effective_dep_velocity)
                    print(f" - Added effective deposition velocity data for day {day}.")

        # Stack hourly values and calculate monthly mean deposition velocity
        if monthly_deposition_list:
            print(f"Calculating monthly average deposition velocity for month {month:02d}...")
            monthly_deposition_velocity = xr.concat(monthly_deposition_list, dim="time").mean(dim="time")
            
            # Save to NetCDF for each month
            output_filename = f'intermediate/deposition_velocity_{year}_{month:02d}.nc'
            monthly_deposition_velocity.to_netcdf(output_filename)
            print(f"Monthly average deposition velocity saved to {output_filename}")
        else:
            print(f"No data processed for month {month:02d}, skipping output.")
