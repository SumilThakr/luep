def run(inputdir=""):
    """
    UK PM2.5 deposition calculation with land-use-specific scaling factors
    
    This version applies land-use-specific scaling to existing deposition velocities:
    - Forest (Simple_Class 3): 100% of base velocity (no scaling)
    - Grass (Simple_Class 2): 50% of base velocity  
    - Cropland (Simple_Class 1): 50% of base velocity
    - Other (Simple_Class 0): 25% of base velocity
    
    Uses existing UK deposition velocity files and applies scaling during calculation.
    
    Args:
        inputdir: Base input directory (typically "")
    """
    import xarray as xr
    import numpy as np
    import pandas as pd
    import rasterio
    import os

    print("=" * 70)
    print("UK PM2.5 DEPOSITION - LAND-USE-SPECIFIC VELOCITY SCALING")
    print("=" * 70)

    # Define directories
    pm25_dir = "inputs/uk_cropped/concentrations"  
    leaf_area_dir = "intermediate"                 
    dep_velocity_dir = "intermediate"              
    output_dir = "outputs"                         

    # Check if UK-cropped PM2.5 data exists
    if not os.path.exists(pm25_dir):
        print(f"❌ UK-cropped PM2.5 data not found at: {pm25_dir}")
        raise FileNotFoundError(f"UK-cropped PM2.5 data directory not found: {pm25_dir}")

    print(f"Using UK-cropped PM2.5 data from: {pm25_dir}")
    print(f"Using UK leaf area data from: {leaf_area_dir}")
    print(f"Using UK deposition velocity data from: {dep_velocity_dir}")

    # Load land use scenario
    land_use_file = "inputs/scenario_landuse_esa_cci.tif"
    mapping_file = "inputs/UK_ESA_CCI_to_Simple_mapping.csv"
    
    for file_path in [land_use_file, mapping_file]:
        if not os.path.exists(file_path):
            print(f"❌ Required file not found: {file_path}")
            raise FileNotFoundError(f"Required file not found: {file_path}")

    print(f"Loading land use scenario: {land_use_file}")
    esa_cci_mapping_df = pd.read_csv(mapping_file)
    esa_cci_to_simple = dict(zip(esa_cci_mapping_df['ESA_CCI_Code'], esa_cci_mapping_df['Simple_Class']))

    # Load and process land use data
    with rasterio.open(land_use_file) as src:
        land_use_esa = src.read(1)
        land_use_transform = src.transform
        
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

    # Define land-use-specific scaling factors
    velocity_scaling = {
        0: 0.25,  # Other (urban, water, bare) - very low
        1: 0.50,  # Cropland - moderate
        2: 0.50,  # Grass - moderate  
        3: 1.00   # Forest - high (baseline)
    }

    print(f"Land use distribution and velocity scaling:")
    for class_id in np.unique(land_use_simple):
        count = np.sum(land_use_simple == class_id)
        class_name = {0: 'Other', 1: 'Cropland', 2: 'Grass', 3: 'Forest'}.get(class_id, 'Unknown')
        scaling = velocity_scaling.get(class_id, 1.0)
        print(f"   Class {class_id} ({class_name}): {count:,} pixels, {scaling:.0%} velocity scaling")

    # Process all months
    year = 2021
    months = range(1, 13)
    annual_deposition = None

    for month in months:
        print(f"\nProcessing month {month:02d} of {year}...")
        
        # File paths
        pm25_file = os.path.join(pm25_dir, f"GHAP_PM2.5_uk_{year}{month:02d}.nc")
        leaf_area_file = os.path.join(leaf_area_dir, f"leaf_area_{month:02d}.nc")
        dep_velocity_file = os.path.join(dep_velocity_dir, f"deposition_velocity_uk_{year}_{month:02d}.nc")

        # Check files exist
        missing_files = []
        for file_path, file_type in [(pm25_file, "PM2.5"), (leaf_area_file, "Leaf Area"), (dep_velocity_file, "Deposition Velocity")]:
            if not os.path.exists(file_path):
                missing_files.append(f"{file_type}: {file_path}")

        if missing_files:
            print(f"⚠️  Skipping month {month:02d} - missing files:")
            for missing in missing_files:
                print(f"   - {missing}")
            continue

        # Load datasets
        with xr.open_dataset(pm25_file) as pm25_ds, \
             xr.open_dataset(leaf_area_file) as leaf_area_ds, \
             xr.open_dataset(dep_velocity_file) as dep_velocity_ds:
            
            print(f"   Loaded datasets for month {month:02d}")
            
            # Process PM2.5 data
            pm25_data = pm25_ds['PM2.5'] * pm25_ds['PM2.5'].attrs.get('scale_factor', 1)
            fill_value = pm25_ds['PM2.5'].attrs.get('_FillValue', pm25_ds['PM2.5'].attrs.get('missing_value', None))
            if fill_value is not None:
                pm25_data = pm25_data.where(pm25_data != fill_value, np.nan)

            # Use leaf area as target grid (highest resolution)
            target_grid = leaf_area_ds['leaf_area']
            target_lat = target_grid.lat.values
            target_lon = target_grid.lon.values

            print(f"   Target grid shape: {target_grid.shape}")

            # Interpolate PM2.5 and deposition velocity to target grid
            print(f"   Interpolating datasets to target grid...")
            pm25_interp = pm25_data.interp(lat=target_lat, lon=target_lon, method='linear')
            dep_velocity_interp = dep_velocity_ds['__xarray_dataarray_variable__'].interp(
                lat=target_lat, lon=target_lon, method='linear'
            )

            # Create land use mask on target grid
            land_use_interp = xr.DataArray(
                land_use_simple,
                dims=['lat', 'lon'],
                coords={'lat': land_use_lat_array[:, 0], 'lon': land_use_lon_array[0, :]}
            ).interp(lat=target_lat, lon=target_lon, method='nearest')

            # Create velocity scaling array based on land use
            scaling_array = xr.zeros_like(land_use_interp)
            for class_id, scaling_factor in velocity_scaling.items():
                class_mask = (land_use_interp == class_id)
                scaling_array = scaling_array.where(~class_mask, scaling_factor)

            print(f"   Applying land-use-specific velocity scaling...")

            # Calculate monthly deposition with land-use-specific scaling
            # Formula: Deposition = PM2.5 × Leaf_Area × (Base_Velocity × Land_Use_Scaling)
            # PM2.5 units: µg/m³, Leaf_Area units: m², Velocity units: cm/s
            # Need to convert velocity from cm/s to m/s and add time conversion
            velocity_scaled_ms = (dep_velocity_interp * scaling_array) / 100.0  # cm/s to m/s
            
            # Calculate deposition: µg/m³ × m² × m/s × time_factor
            # For monthly calculation: assume 30.44 days/month × 24 hours/day × 3600 seconds/hour
            seconds_per_month = 30.44 * 24 * 3600  # Average seconds per month
            
            monthly_deposition = pm25_interp * target_grid * velocity_scaled_ms * seconds_per_month

            # Report class-specific statistics
            for class_id in [0, 1, 2, 3]:
                class_name = {0: 'Other', 1: 'Cropland', 2: 'Grass', 3: 'Forest'}[class_id]
                class_mask = (land_use_interp == class_id)
                class_pixels = class_mask.sum().item()
                
                if class_pixels > 0:
                    class_deposition = monthly_deposition.where(class_mask)
                    class_total = class_deposition.sum().item()
                    class_mean = class_deposition.mean().item()
                    scaling_factor = velocity_scaling[class_id]
                    print(f"     {class_name}: {class_pixels:,} pixels, {class_total:,.1f} µg total, {scaling_factor:.0%} velocity")

            print(f"   ✅ Month {month:02d} completed")

            # Accumulate annual total
            if annual_deposition is None:
                annual_deposition = monthly_deposition.copy()
                print(f"   Initialized annual accumulator")
            else:
                annual_deposition += monthly_deposition
                print(f"   Added to annual total")

    # Final processing
    if annual_deposition is not None:
        print(f"\n🎉 Annual deposition calculation completed!")
        
        # Correct latitude orientation if needed
        if annual_deposition.lat[0] > annual_deposition.lat[1]:
            annual_deposition = annual_deposition.isel(lat=slice(None, None, -1))
            print("   Applied latitude axis correction")

        # Convert µg to kg
        annual_deposition_kg = annual_deposition / 1e9
        
        # Add metadata
        annual_deposition_kg.attrs = {
            'long_name': 'Annual PM2.5 deposition with land-use velocity scaling',
            'units': 'kg/year',
            'description': 'PM2.5 deposition with land-use-specific velocity scaling factors',
            'methodology': 'Nowak et al. (2013) with land-use scaling',
            'velocity_scaling': 'Forest: 100%, Grass/Cropland: 50%, Other: 25%',
            'temporal_scope': f'{year} annual (12 months)',
            'spatial_extent': 'UK (ESA-CCI scenario extent)',
            'formula': 'Deposition = PM2.5 × Leaf_Area × (Base_Velocity × LandUse_Scaling)'
        }

        # Save results
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"pm25_annual_deposition_landuse_scaled_uk_{year}.nc")
        
        annual_deposition_ds = xr.Dataset({'pm25_deposition': annual_deposition_kg})
        annual_deposition_ds.to_netcdf(output_file)
        print(f"   💾 Saved: {output_file}")

        # Calculate summary statistics
        total_deposition = annual_deposition_kg.sum().item()
        max_deposition = annual_deposition_kg.max().item()
        mean_deposition = annual_deposition_kg.mean().item()

        print(f"\n📊 FINAL RESULTS")
        print(f"=" * 50)
        print(f"Total UK PM2.5 deposition: {total_deposition:,.0f} kg/year")
        print(f"Maximum pixel deposition: {max_deposition:.2f} kg/year")
        print(f"Mean pixel deposition: {mean_deposition:.2f} kg/year")
        print(f"Methodology: Land-use velocity scaling")
        
        # Class-specific totals
        print(f"\nDeposition by land use class:")
        land_use_interp_final = xr.DataArray(
            land_use_simple,
            dims=['lat', 'lon'],
            coords={'lat': land_use_lat_array[:, 0], 'lon': land_use_lon_array[0, :]}
        ).interp(lat=annual_deposition_kg.lat.values, lon=annual_deposition_kg.lon.values, method='nearest')
        
        for class_id in [0, 1, 2, 3]:
            class_name = {0: 'Other', 1: 'Cropland', 2: 'Grass', 3: 'Forest'}[class_id]
            class_mask = (land_use_interp_final == class_id)
            class_total = annual_deposition_kg.where(class_mask).sum().item()
            class_pixels = class_mask.sum().item()
            if class_pixels > 0:
                scaling_factor = velocity_scaling[class_id]
                print(f"   {class_name}: {class_total:,.0f} kg/year ({scaling_factor:.0%} velocity scaling)")

        return {
            'total_deposition': total_deposition,
            'max_deposition': max_deposition,
            'mean_deposition': mean_deposition,
            'output_file': output_file
        }
    else:
        print("❌ No valid data processed")
        return None