def run(inputdir=""):
    """
    UK-optimized PM2.5 deposition calculation with land-use-specific deposition velocities
    
    This version processes UK-cropped data with land-use-specific deposition velocities:
    - UK-cropped PM2.5 concentration data
    - UK-only leaf area data (from ESA-CCI scenarios)
    - Land-use-specific deposition velocity data (forest, grass, cropland)
    - Applies appropriate deposition velocity based on land use class at each pixel
    
    Args:
        inputdir: Base input directory (typically "")
    """
    import xarray as xr
    import numpy as np
    import pandas as pd
    import rasterio
    import os

    print("=" * 70)
    print("UK PM2.5 DEPOSITION CALCULATION - LAND-USE-SPECIFIC VELOCITIES")
    print("=" * 70)

    # Define directories and patterns for UK-optimized data
    pm25_dir = "inputs/uk_cropped/concentrations"  # UK-cropped PM2.5 data
    leaf_area_dir = "intermediate"                 # UK leaf area files (from ESA-CCI)
    dep_velocity_dir = "intermediate"              # Land-use-specific deposition velocity files
    output_dir = "outputs"                         # Directory for saving the results

    # Check if UK-cropped PM2.5 data exists
    if not os.path.exists(pm25_dir):
        print(f"❌ UK-cropped PM2.5 data not found at: {pm25_dir}")
        print("Please run the meteorological data preprocessor first:")
        print("   /Users/sumilthakrar/yes/envs/rasters/bin/python utils/crop_met_data_uk.py")
        raise FileNotFoundError(f"UK-cropped PM2.5 data directory not found: {pm25_dir}")

    print(f"Using UK-cropped PM2.5 data from: {pm25_dir}")
    print(f"Using UK leaf area data from: {leaf_area_dir}")
    print(f"Using land-use-specific deposition velocity data from: {dep_velocity_dir}")

    # Load land use scenario to determine which deposition velocity to use at each pixel
    land_use_file = "inputs/scenario_landuse_esa_cci.tif"
    if not os.path.exists(land_use_file):
        print(f"❌ Land use scenario file not found: {land_use_file}")
        raise FileNotFoundError(f"Land use scenario file not found: {land_use_file}")

    # Load ESA-CCI to Simple class mapping
    mapping_file = "inputs/UK_ESA_CCI_to_Simple_mapping.csv"
    if not os.path.exists(mapping_file):
        print(f"❌ ESA-CCI mapping file not found: {mapping_file}")
        raise FileNotFoundError(f"ESA-CCI mapping file not found: {mapping_file}")

    print(f"Loading land use scenario: {land_use_file}")
    esa_cci_mapping_df = pd.read_csv(mapping_file)
    esa_cci_to_simple = dict(zip(esa_cci_mapping_df['ESA_CCI_Code'], esa_cci_mapping_df['Simple_Class']))

    # Load land use data and convert to Simple classes
    with rasterio.open(land_use_file) as src:
        land_use_esa = src.read(1)
        land_use_transform = src.transform
        
        # Get coordinate arrays
        height, width = land_use_esa.shape
        rows, cols = np.meshgrid(np.arange(height), np.arange(width), indexing='ij')
        land_use_lon, land_use_lat = rasterio.transform.xy(land_use_transform, rows, cols)
        land_use_lat_array = np.array(land_use_lat)
        land_use_lon_array = np.array(land_use_lon)

    # Convert ESA-CCI to Simple classes
    land_use_simple = np.vectorize(lambda x: esa_cci_to_simple.get(x, 0))(land_use_esa)
    
    # Flip to standard orientation
    land_use_simple = np.flipud(land_use_simple)
    land_use_lat_array = np.flipud(land_use_lat_array)
    land_use_lon_array = np.flipud(land_use_lon_array)

    print(f"Land use classes found: {np.unique(land_use_simple)}")
    for class_id in np.unique(land_use_simple):
        count = np.sum(land_use_simple == class_id)
        class_name = {0: 'Other', 1: 'Cropland', 2: 'Grass', 3: 'Forest'}.get(class_id, 'Unknown')
        print(f"   Class {class_id} ({class_name}): {count:,} pixels")

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
        
        # Land-use-specific deposition velocity files
        dep_velocity_files = {
            1: os.path.join(dep_velocity_dir, f"deposition_velocity_cropland_{year}_{month:02d}.nc"),  # Cropland
            2: os.path.join(dep_velocity_dir, f"deposition_velocity_grass_{year}_{month:02d}.nc"),     # Grass
            3: os.path.join(dep_velocity_dir, f"deposition_velocity_forest_{year}_{month:02d}.nc")    # Forest
        }

        # Check if all required files exist
        missing_files = []
        if not os.path.exists(pm25_file):
            missing_files.append(f"PM2.5: {pm25_file}")
        if not os.path.exists(leaf_area_file):
            missing_files.append(f"Leaf Area: {leaf_area_file}")
        
        for land_use_class, dep_file in dep_velocity_files.items():
            if not os.path.exists(dep_file):
                missing_files.append(f"Deposition Velocity (Class {land_use_class}): {dep_file}")

        if missing_files:
            print(f"⚠️  Skipping month {month:02d} - missing files:")
            for missing in missing_files:
                print(f"   - {missing}")
            continue

        # Load datasets
        print(f"   Loading datasets for month {month:02d}...")
        pm25_ds = xr.open_dataset(pm25_file)
        leaf_area_ds = xr.open_dataset(leaf_area_file)
        
        # Load land-use-specific deposition velocity datasets
        dep_velocity_datasets = {}
        for land_use_class, dep_file in dep_velocity_files.items():
            dep_velocity_datasets[land_use_class] = xr.open_dataset(dep_file)

        # Retrieve PM2.5 data as DataArray, applying scale factor if available
        pm25_data = pm25_ds['PM2.5'] * pm25_ds['PM2.5'].attrs.get('scale_factor', 1)
        fill_value = pm25_ds['PM2.5'].attrs.get('_FillValue', pm25_ds['PM2.5'].attrs.get('missing_value', None))
        if fill_value is not None:
            pm25_data = pm25_data.where(pm25_data != fill_value, np.nan)

        # Use leaf area as the target grid (highest resolution)
        target_grid = leaf_area_ds['leaf_area']
        target_lat = target_grid.lat.values
        target_lon = target_grid.lon.values

        print(f"   Target grid shape: {target_grid.shape}")
        print(f"   PM2.5 shape: {pm25_data.shape}")

        # Interpolate PM2.5 to target grid
        print(f"   Interpolating PM2.5 to target grid...")
        pm25_interp = pm25_data.interp(lat=target_lat, lon=target_lon, method='linear')

        # Create land use mask on target grid
        print(f"   Creating land use mask on target grid...")
        land_use_interp = xr.DataArray(
            land_use_simple,
            dims=['lat', 'lon'],
            coords={'lat': land_use_lat_array[:, 0], 'lon': land_use_lon_array[0, :]}
        ).interp(lat=target_lat, lon=target_lon, method='nearest')

        # Initialize monthly deposition array
        monthly_deposition = xr.zeros_like(target_grid)

        # Process each land use class separately
        for land_use_class in [1, 2, 3]:  # Cropland, Grass, Forest
            class_name = {1: 'Cropland', 2: 'Grass', 3: 'Forest'}[land_use_class]
            print(f"   Processing {class_name} (Class {land_use_class})...")
            
            # Create mask for this land use class
            class_mask = (land_use_interp == land_use_class)
            class_pixels = class_mask.sum().item()
            
            if class_pixels == 0:
                print(f"     No {class_name} pixels found, skipping...")
                continue
                
            print(f"     Found {class_pixels:,} {class_name} pixels")
            
            # Load deposition velocity for this class
            dep_velocity_data = dep_velocity_datasets[land_use_class]['__xarray_dataarray_variable__']
            
            # Interpolate deposition velocity to target grid
            dep_velocity_interp = dep_velocity_data.interp(lat=target_lat, lon=target_lon, method='linear')
            
            # Calculate deposition for this land use class
            # Formula: Deposition = PM2.5 × Leaf_Area × Deposition_Velocity (with unit conversion)
            class_deposition = pm25_interp * target_grid * dep_velocity_interp * class_mask
            
            # Add to monthly total
            monthly_deposition += class_deposition
            
            # Report statistics for this class
            class_total = class_deposition.sum().item()
            class_mean = class_deposition.where(class_mask).mean().item()
            print(f"     Total {class_name} deposition: {class_total:,.1f} µg")
            print(f"     Mean {class_name} deposition: {class_mean:.3f} µg/pixel")

        print(f"   ✅ Month {month:02d} deposition calculated")

        # Accumulate annual deposition
        if annual_deposition is None:
            annual_deposition = monthly_deposition.copy()
            print(f"   Initialized annual deposition accumulator")
        else:
            annual_deposition += monthly_deposition
            print(f"   Added to annual deposition total")

        # Close datasets
        pm25_ds.close()
        leaf_area_ds.close()
        for ds in dep_velocity_datasets.values():
            ds.close()

    # Final processing and output
    if annual_deposition is not None:
        print(f"\n🎉 Annual deposition calculation completed!")
        
        # Correct latitude axis orientation if needed
        if annual_deposition.lat[0] > annual_deposition.lat[1]:
            annual_deposition = annual_deposition.isel(lat=slice(None, None, -1))
            print("   Applied latitude axis correction: North-to-South → South-to-North")

        # Convert units from µg to kg and calculate annual totals
        # µg → kg: divide by 1e9
        annual_deposition_kg = annual_deposition / 1e9
        
        # Add metadata
        annual_deposition_kg.attrs = {
            'long_name': 'Annual PM2.5 deposition with land-use-specific velocities',
            'units': 'kg/year',
            'description': 'PM2.5 deposition calculated using land-use-specific deposition velocities',
            'methodology': 'Modified Nowak et al. (2013) with land-use-specific scaling factors',
            'forest_velocity': 'Original Nowak values',
            'grass_velocity': '50% of forest values',
            'cropland_velocity': '50% of forest values',
            'temporal_scope': f'{year} annual (12 months)',
            'spatial_extent': 'UK (ESA-CCI scenario extent)',
            'formula': 'Deposition = PM2.5 × Leaf_Area × Deposition_Velocity_by_LandUse'
        }

        # Create output dataset
        annual_deposition_ds = xr.Dataset({
            'pm25_deposition': annual_deposition_kg
        })

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Save results
        output_file = os.path.join(output_dir, f"pm25_annual_deposition_landuse_uk_{year}.nc")
        annual_deposition_ds.to_netcdf(output_file)
        print(f"   💾 Saved: {output_file}")

        # Calculate and display summary statistics
        total_deposition = annual_deposition_kg.sum().item()
        max_deposition = annual_deposition_kg.max().item()
        mean_deposition = annual_deposition_kg.mean().item()
        valid_pixels = (~np.isnan(annual_deposition_kg)).sum().item()

        print(f"\n📊 SUMMARY STATISTICS")
        print(f"=" * 50)
        print(f"Total UK PM2.5 deposition: {total_deposition:,.0f} kg/year")
        print(f"Maximum pixel deposition: {max_deposition:.2f} kg/year")
        print(f"Mean pixel deposition: {mean_deposition:.2f} kg/year")
        print(f"Valid pixels: {valid_pixels:,}")
        print(f"Methodology: Land-use-specific deposition velocities")
        print(f"   - Forest: Original Nowak et al. (2013) values")
        print(f"   - Grass: 50% of forest values")
        print(f"   - Cropland: 50% of forest values")

        return {
            'total_deposition': total_deposition,
            'max_deposition': max_deposition,
            'mean_deposition': mean_deposition,
            'valid_pixels': valid_pixels,
            'output_file': output_file
        }
    else:
        print("❌ No valid data processed. Check input files and try again.")
        return None