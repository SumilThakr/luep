def run(inputdir):
    """
    Calculate land-use-specific deposition velocities for PM2.5
    
    This script generates separate deposition velocity files for different land use types:
    - Forest (Simple_Class 3): Uses original Nowak et al. (2013) values
    - Grass (Simple_Class 2): Uses halved values (~50% of forest)
    - Cropland (Simple_Class 1): Uses halved values (~50% of forest)
    
    Based on literature showing forest deposition velocities are roughly 
    double those of grassland and cropland.
    """
    import xarray as xr
    import pandas as pd
    import numpy as np
    from glob import glob
    import os

    print("Loading land-use-specific deposition velocity data...")
    
    # Load deposition velocity data for each land use type
    land_use_configs = {
        'forest': {
            'csv_file': os.path.join(inputdir, 'inputs', 'dep_v_forest.csv'),
            'simple_class': 3,
            'description': 'Forest (broadleaved, needleleaved, mixed)'
        },
        'grass': {
            'csv_file': os.path.join(inputdir, 'inputs', 'dep_v_grass.csv'),
            'simple_class': 2,
            'description': 'Grassland, shrubland, sparse vegetation'
        },
        'cropland': {
            'csv_file': os.path.join(inputdir, 'inputs', 'dep_v_cropland.csv'),
            'simple_class': 1,
            'description': 'Cropland (rainfed, irrigated, mosaic)'
        }
    }
    
    # Load data for each land use type
    land_use_data = {}
    for land_use, config in land_use_configs.items():
        if os.path.exists(config['csv_file']):
            df = pd.read_csv(config['csv_file'])
            df['Effective_dep'] = df['Avg_dep'] * (df['Resusp'] / 100.0)
            land_use_data[land_use] = df
            print(f"✅ Loaded {land_use} deposition data: {config['description']}")
        else:
            print(f"❌ Missing {land_use} deposition data: {config['csv_file']}")
            raise FileNotFoundError(f"Required deposition velocity file not found: {config['csv_file']}")

    # Create interpolation functions for each land use type
    def get_effective_dep_velocity(wind_speed, land_use_type):
        """Get effective deposition velocity based on wind speed and land use type"""
        if land_use_type not in land_use_data:
            raise ValueError(f"Unknown land use type: {land_use_type}")
        
        df = land_use_data[land_use_type]
        return np.interp(wind_speed, df['Wind_speed'], df['Effective_dep'])

    # Define the period of interest
    year = 2021
    months = range(1, 13)  # Process all 12 months

    # Directory where daily NetCDF files are stored
    data_dir = os.path.join(inputdir, "inputs", 'uk_cropped', 'meteorology')
    
    # Check if UK-cropped meteorological data exists
    if not os.path.exists(data_dir):
        print(f"❌ UK-cropped meteorological data not found at: {data_dir}")
        print("Please run the meteorological data preprocessor first:")
        print("   /Users/sumilthakrar/yes/envs/rasters/bin/python utils/crop_met_data_uk.py")
        raise FileNotFoundError(f"UK-cropped meteorological data directory not found: {data_dir}")

    print(f"Using UK-cropped meteorological data from: {data_dir}")

    # Loop through each month and calculate monthly average deposition velocity for each land use
    for month in months:
        print(f"\nProcessing month {month:02d} of {year}...")
        
        # Get UK-cropped meteorological file for this month
        met_file = os.path.join(data_dir, f"MERRA2_uk_{year}{month:02d}.nc")
        
        if not os.path.exists(met_file):
            print(f"❌ Missing UK meteorological file: {met_file}")
            continue
            
        print(f"Loading UK meteorological data: {os.path.basename(met_file)}")
        
        with xr.open_dataset(met_file) as ds:
            # Load eastward and northward wind components
            if 'U10M' in ds.variables and 'V10M' in ds.variables:
                east_wind = ds['U10M']
                north_wind = ds['V10M']
                print(f"   Loaded wind components (U10M, V10M)")
            else:
                print(f"   ❌ Missing wind variables in {met_file}")
                continue

            # Calculate wind speed as the magnitude of east and north components
            wind_speed = np.sqrt(np.square(east_wind) + np.square(north_wind))
            
            # Calculate monthly mean wind speed
            monthly_wind_speed = wind_speed.mean(dim="time")
            print(f"   Calculated monthly mean wind speed")

            # Generate deposition velocity for each land use type
            for land_use, config in land_use_configs.items():
                print(f"   Calculating {land_use} deposition velocity...")
                
                # Calculate effective deposition velocity for this land use type
                effective_dep_velocity = xr.apply_ufunc(
                    lambda ws: get_effective_dep_velocity(ws, land_use),
                    monthly_wind_speed,
                    vectorize=True
                )
                
                # Add metadata
                effective_dep_velocity.attrs = {
                    'long_name': f'PM2.5 deposition velocity for {land_use}',
                    'units': 'cm/s',
                    'description': config['description'],
                    'simple_class': config['simple_class'],
                    'methodology': 'Modified Nowak et al. (2013) with land-use-specific scaling',
                    'wind_speed_source': 'MERRA2 U10M, V10M monthly average'
                }
                
                # Save to NetCDF file
                output_filename = f'intermediate/deposition_velocity_{land_use}_{year}_{month:02d}.nc'
                effective_dep_velocity.to_netcdf(output_filename)
                print(f"   ✅ Saved: {output_filename}")

    print(f"\n🎉 Land-use-specific deposition velocity calculation completed!")
    print(f"Generated files for {len(months)} months × {len(land_use_configs)} land use types")
    print(f"Files saved to: intermediate/deposition_velocity_[landuse]_YYYY_MM.nc")