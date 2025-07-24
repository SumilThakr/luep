#!/usr/bin/env python
"""
Debug the LAI assignment process to understand why grassland shows higher
LAI per pixel than forest in the final processed data.
"""

import rasterio
import numpy as np
import pandas as pd
import os
import xarray as xr

def debug_lai_assignment():
    """Debug the LAI assignment process step by step"""
    
    print("=== Debugging LAI Assignment Process ===")
    
    # 1. Check original LAI values from coarse_averaged_LAI_SimpleID.nc
    print("\n1. Original LAI values from global dataset:")
    lai_ds = xr.open_dataset('./intermediate/coarse_averaged_LAI_SimpleID.nc')
    
    lai_mapping = {
        'LAI_SimpleID_1': 'Cropland',
        'LAI_SimpleID_2': 'Grassland', 
        'LAI_SimpleID_3': 'Forest'
    }
    
    # Get January values (month 0)
    for lai_var, class_name in lai_mapping.items():
        if lai_var in lai_ds.data_vars:
            lai_data = lai_ds[lai_var].isel(time=0)  # January
            
            # Get valid (non-NaN, non-zero) LAI values
            valid_mask = (~np.isnan(lai_data)) & (lai_data > 0)
            valid_values = lai_data.where(valid_mask)
            
            if valid_values.count() > 0:
                print(f"  {class_name}: mean={float(valid_values.mean()):.3f}, median={float(valid_values.median()):.3f}")
    
    lai_ds.close()
    
    # 2. Check how LAI gets resampled to UK coordinates
    print("\n2. LAI resampling to UK coordinates:")
    
    # Load UK land use to get coordinates
    scenario_file = "inputs/scenario_landuse_esa_cci.tif"
    with rasterio.open(scenario_file) as src:
        land_use = src.read(1)
        transform = src.transform
        
        # Get UK coordinate arrays
        height, width = land_use.shape
        rows, cols = np.meshgrid(np.arange(height), np.arange(width), indexing='ij')
        uk_lon, uk_lat = rasterio.transform.xy(transform, rows, cols)
        uk_lat_array = np.array(uk_lat)
        uk_lon_array = np.array(uk_lon)
        
        # Flip to match processing
        land_use = np.flipud(land_use)
        uk_lat_array = np.flipud(uk_lat_array)
        uk_lon_array = np.flipud(uk_lon_array)
        
        print(f"  UK extent: lat {uk_lat_array.min():.3f} to {uk_lat_array.max():.3f}")
        print(f"             lon {uk_lon_array.min():.3f} to {uk_lon_array.max():.3f}")
    
    # 3. Test the resampling process for each LAI class
    print("\n3. Testing LAI resampling for UK region:")
    
    lai_ds = xr.open_dataset('./intermediate/coarse_averaged_LAI_SimpleID.nc')
    lai_ds['time'] = xr.cftime_range(start="2020-01-01", periods=len(lai_ds.time), freq="8D")
    monthly_lai_ds = lai_ds.resample(time="M").mean()
    
    for lai_var, class_name in lai_mapping.items():
        if lai_var in monthly_lai_ds.data_vars:
            # Get January data
            lai_for_id = monthly_lai_ds[lai_var].sel(time="2020-01").squeeze()
            
            # Resample to UK coordinates using the same method as the script
            lai_resampled = lai_for_id.interp(
                lat=uk_lat_array[:, 0],  # Use actual UK latitudes (1D from the first column)
                lon=uk_lon_array[0, :],  # Use actual UK longitudes (1D from the first row)
                method="nearest"
            )
            
            print(f"  {class_name} resampled to UK:")
            print(f"    Shape: {lai_resampled.shape}")
            print(f"    Min: {float(lai_resampled.min()):.3f}")
            print(f"    Max: {float(lai_resampled.max()):.3f}")
            print(f"    Mean: {float(lai_resampled.mean()):.3f}")
            
            # Sample a few specific locations
            mid_lat_idx = len(uk_lat_array) // 2
            mid_lon_idx = len(uk_lon_array[0]) // 2
            sample_value = lai_resampled.values[mid_lat_idx, mid_lon_idx]
            print(f"    Sample value at center UK: {sample_value:.3f}")
    
    lai_ds.close()
    
    # 4. Check the pixel area multiplication effect
    print("\n4. Pixel area multiplication effect:")
    
    # Calculate pixel area the same way as the script
    uk_center_lat = (uk_lat_array.min() + uk_lat_array.max()) / 2  # ~55°N
    deg_to_m_lat = 111000  # meters per degree latitude (constant)
    deg_to_m_lon = 111000 * np.cos(np.radians(uk_center_lat))  # meters per degree longitude (latitude-dependent)
    
    pixel_size_deg_lat = abs(transform[4])  # degrees per pixel in latitude
    pixel_size_deg_lon = abs(transform[0])  # degrees per pixel in longitude
    
    pixel_size_m_lat = pixel_size_deg_lat * deg_to_m_lat
    pixel_size_m_lon = pixel_size_deg_lon * deg_to_m_lon
    pixel_area_m2 = pixel_size_m_lat * pixel_size_m_lon
    
    print(f"  Pixel area: {pixel_area_m2:.1f} m²")
    print(f"  This means LAI values get multiplied by {pixel_area_m2:.0f}")
    print(f"  So an LAI of 0.1 becomes {0.1 * pixel_area_m2:.0f} m² of leaf area per pixel")
    
    # 5. Check final leaf area file values
    print("\n5. Final leaf area file analysis:")
    
    leaf_area_ds = xr.open_dataset("intermediate/leaf_area_01.nc")
    leaf_area = leaf_area_ds['leaf_area']
    
    # Load ESA CCI to Simple class mapping
    mapping_file = "inputs/UK_ESA_CCI_to_Simple_mapping.csv"
    esa_mapping = pd.read_csv(mapping_file)
    esa_to_simple = dict(zip(esa_mapping['ESA_CCI_Code'], esa_mapping['Simple_Class']))
    
    # Convert land use to Simple classes
    simple_land_use = np.vectorize(lambda x: esa_to_simple.get(x, -1))(land_use)
    
    class_names = {1: 'Cropland', 2: 'Grassland', 3: 'Forest'}
    
    for simple_id, class_name in class_names.items():
        class_mask = (simple_land_use == simple_id)
        class_leaf_area = leaf_area.values[class_mask]
        
        # Get non-zero values
        non_zero_mask = class_leaf_area > 0
        non_zero_values = class_leaf_area[non_zero_mask]
        
        if len(non_zero_values) > 0:
            # Convert back to LAI by dividing by pixel area
            lai_values = non_zero_values / pixel_area_m2
            
            print(f"  {class_name}:")
            print(f"    Pixels with data: {len(non_zero_values):,}")
            print(f"    Mean leaf area: {np.mean(non_zero_values):.0f} m²")
            print(f"    Mean LAI (calc): {np.mean(lai_values):.3f}")
            print(f"    Min LAI: {np.min(lai_values):.3f}")
            print(f"    Max LAI: {np.max(lai_values):.3f}")
    
    leaf_area_ds.close()
    
    # 6. Cross-check with expected values
    print("\n6. Cross-check with expected LAI values:")
    print("  From our earlier analysis of the global LAI dataset:")
    print("    Cropland: 0.044")
    print("    Grassland: 0.143") 
    print("    Forest: 0.307")
    print("\n  If the processing is correct, the final LAI values should match these!")

if __name__ == "__main__":
    debug_lai_assignment()