#!/usr/bin/env python
"""
Check the current UK scenario to understand land use distribution
and potential LAI assignment issues.
"""

import rasterio
import numpy as np
import pandas as pd
import os
import xarray as xr

def check_current_landuse():
    """Check what land use file is currently being used"""
    
    # Check if there's a UK scenario set up
    scenario_file = "inputs/scenario_landuse_esa_cci.tif"
    global_file = "inputs/gblulcg20.tif"
    
    print("=== Current Land Use Configuration ===")
    
    if os.path.exists(scenario_file):
        print(f"UK scenario land use file found: {scenario_file}")
        
        # Load ESA CCI mapping
        mapping_file = "inputs/UK_ESA_CCI_to_Simple_mapping.csv"
        if os.path.exists(mapping_file):
            esa_mapping = pd.read_csv(mapping_file)
            esa_to_simple = dict(zip(esa_mapping['ESA_CCI_Code'], esa_mapping['Simple_Class']))
            
            with rasterio.open(scenario_file) as src:
                land_use = src.read(1)
                print(f"UK scenario shape: {land_use.shape}")
                print(f"UK scenario bounds: {src.bounds}")
                
                # Get unique land use values
                unique_values = np.unique(land_use[land_use != src.nodata])
                print(f"Unique ESA CCI values: {sorted(unique_values)}")
                
                # Convert to Simple classes and count pixels
                simple_classes = {}
                for esa_code in unique_values:
                    simple_class = esa_to_simple.get(esa_code, -1)
                    simple_classes[simple_class] = simple_classes.get(simple_class, 0) + np.sum(land_use == esa_code)
                
                print(f"\nSimple class distribution:")
                class_names = {0: 'Other', 1: 'Cropland', 2: 'Grassland', 3: 'Forest'}
                for simple_id, count in sorted(simple_classes.items()):
                    class_name = class_names.get(simple_id, f'Unknown({simple_id})')
                    percentage = (count / land_use.size) * 100
                    print(f"  Class {simple_id} ({class_name}): {count:,} pixels ({percentage:.1f}%)")
                    
        else:
            print(f"ESA CCI mapping file not found: {mapping_file}")
            
    elif os.path.exists(global_file):
        print(f"Global land use file found: {global_file}")
        
        # Load USGS mapping
        mapping_file = "inputs/USGS_to_simple_mapping.csv"
        if os.path.exists(mapping_file):
            usgs_mapping = pd.read_csv(mapping_file)
            usgs_to_simple = dict(zip(usgs_mapping['Value'], usgs_mapping['Simple_ID']))
            
            with rasterio.open(global_file) as src:
                land_use = src.read(1)
                print(f"Global land use shape: {land_use.shape}")
                print(f"Global land use bounds: {src.bounds}")
                
                # Sample UK region approximately
                uk_sample = land_use[7200:7600, 16800:17600]  # Rough UK coordinates
                unique_values = np.unique(uk_sample[uk_sample != src.nodata])
                print(f"Unique USGS values in UK region sample: {sorted(unique_values)}")
                
                # Convert to Simple classes and count pixels
                simple_classes = {}
                for usgs_code in unique_values:
                    simple_class = usgs_to_simple.get(usgs_code, -1)
                    simple_classes[simple_class] = simple_classes.get(simple_class, 0) + np.sum(uk_sample == usgs_code)
                
                print(f"\nSimple class distribution in UK sample:")
                class_names = {0: 'Other', 1: 'Cropland', 2: 'Grassland', 3: 'Forest'}
                for simple_id, count in sorted(simple_classes.items()):
                    class_name = class_names.get(simple_id, f'Unknown({simple_id})')
                    percentage = (count / uk_sample.size) * 100
                    print(f"  Class {simple_id} ({class_name}): {count:,} pixels ({percentage:.1f}%)")
                    
        else:
            print(f"USGS mapping file not found: {mapping_file}")
    else:
        print("No land use file found!")

def check_leaf_area_files():
    """Check the generated leaf area files"""
    
    print(f"\n=== Leaf Area Files ===")
    
    # Check if monthly leaf area files exist
    for month in [1, 6, 12]:
        leaf_file = f"intermediate/leaf_area_{month:02d}.nc"
        if os.path.exists(leaf_file):
            print(f"\nLeaf area file for month {month}: {leaf_file}")
            
            try:
                ds = xr.open_dataset(leaf_file)
                leaf_area = ds['leaf_area']
                
                # Get statistics on leaf area values
                non_zero_mask = leaf_area > 0
                non_zero_values = leaf_area.where(non_zero_mask)
                
                if non_zero_values.count() > 0:
                    print(f"  Shape: {leaf_area.shape}")
                    print(f"  Coordinate ranges: lat {float(leaf_area.lat.min()):.3f} to {float(leaf_area.lat.max()):.3f}")
                    print(f"                     lon {float(leaf_area.lon.min()):.3f} to {float(leaf_area.lon.max()):.3f}")
                    print(f"  Non-zero pixels: {int(non_zero_values.count()):,}")
                    print(f"  Min (non-zero): {float(non_zero_values.min()):.0f}")
                    print(f"  Max: {float(non_zero_values.max()):.0f}")
                    print(f"  Mean (non-zero): {float(non_zero_values.mean()):.0f}")
                    print(f"  Total leaf area: {float(non_zero_values.sum()):.0f} m²")
                else:
                    print(f"  No non-zero leaf area values found!")
                    
                ds.close()
                
            except Exception as e:
                print(f"  Error reading file: {e}")
        else:
            print(f"Leaf area file for month {month} not found: {leaf_file}")

def check_deposition_results():
    """Check deposition results if they exist"""
    
    print(f"\n=== Deposition Results ===")
    
    # Check for UK deposition results
    output_files = [
        "outputs/PM2.5_annual_deposition_2021.nc",
        "outputs/PM2.5_annual_deposition_uk_2021.nc"
    ]
    
    for output_file in output_files:
        if os.path.exists(output_file):
            print(f"\nDeposition result file: {output_file}")
            
            try:
                ds = xr.open_dataset(output_file)
                deposition = ds['annual_PM2.5_deposition']
                
                non_zero_mask = deposition > 0
                non_zero_values = deposition.where(non_zero_mask)
                
                if non_zero_values.count() > 0:
                    print(f"  Shape: {deposition.shape}")
                    print(f"  Coordinate ranges: lat {float(deposition.lat.min()):.3f} to {float(deposition.lat.max()):.3f}")
                    print(f"                     lon {float(deposition.lon.min()):.3f} to {float(deposition.lon.max()):.3f}")
                    print(f"  Non-zero pixels: {int(non_zero_values.count()):,}")
                    print(f"  Min (non-zero): {float(non_zero_values.min()):.6f}")
                    print(f"  Max: {float(non_zero_values.max()):.6f}")
                    print(f"  Mean (non-zero): {float(non_zero_values.mean()):.6f}")
                    print(f"  Total deposition: {float(non_zero_values.sum()):.3f} kg/year")
                else:
                    print(f"  No non-zero deposition values found!")
                    
                ds.close()
                
            except Exception as e:
                print(f"  Error reading file: {e}")
        else:
            print(f"Deposition result file not found: {output_file}")

if __name__ == "__main__":
    check_current_landuse()
    check_leaf_area_files()
    check_deposition_results()