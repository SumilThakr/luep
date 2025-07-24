#!/usr/bin/env python
"""
Analyze LAI values by Simple_Class to understand PM2.5 deposition differences
between grassland and forest scenarios.

Simple_Class mapping:
1 = Cropland
2 = Grassland  
3 = Forest
"""

import xarray as xr
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def analyze_lai_by_class():
    """Analyze LAI values by Simple_Class"""
    
    # Load the LAI dataset
    lai_file = 'intermediate/coarse_averaged_LAI_SimpleID.nc'
    print(f"Loading LAI dataset: {lai_file}")
    
    try:
        ds = xr.open_dataset(lai_file)
        print(f"Dataset loaded successfully")
        print(f"Dataset variables: {list(ds.data_vars)}")
        print(f"Dataset dimensions: {dict(ds.dims)}")
        print(f"Dataset coordinates: {list(ds.coords)}")
        
        # Dataset has LAI_SimpleID variables instead of Simple_Class
        # LAI_SimpleID_0, LAI_SimpleID_1, LAI_SimpleID_2, LAI_SimpleID_3
        # Based on Simple classification: 1=Cropland, 2=Grassland, 3=Forest
        # So LAI_SimpleID_1=Cropland, LAI_SimpleID_2=Grassland, LAI_SimpleID_3=Forest
        
        lai_mapping = {
            'LAI_SimpleID_1': 'Cropland',
            'LAI_SimpleID_2': 'Grassland', 
            'LAI_SimpleID_3': 'Forest'
        }
        
        # Sample a few months to check LAI values
        months_to_check = [0, 5, 11] if len(ds.time) >= 12 else [0, len(ds.time)//2, len(ds.time)-1]
        
        for month_idx in months_to_check:
            print(f"\n=== Month {month_idx + 1} ===")
            
            for lai_var, class_name in lai_mapping.items():
                if lai_var in ds.data_vars:
                    lai_data = ds[lai_var].isel(time=month_idx)
                    
                    # Get valid (non-NaN, non-zero) LAI values
                    valid_mask = (~np.isnan(lai_data)) & (lai_data > 0)
                    valid_values = lai_data.where(valid_mask)
                    
                    if valid_values.count() > 0:
                        lai_stats = {
                            'min': float(valid_values.min()),
                            'max': float(valid_values.max()),
                            'mean': float(valid_values.mean()),
                            'median': float(valid_values.median()),
                            'std': float(valid_values.std()),
                            'count': int(valid_values.count())
                        }
                        
                        print(f"  {class_name} ({lai_var}):")
                        print(f"    Count: {lai_stats['count']:,} pixels")
                        print(f"    Mean: {lai_stats['mean']:.3f}")
                        print(f"    Median: {lai_stats['median']:.3f}")
                        print(f"    Min: {lai_stats['min']:.3f}")
                        print(f"    Max: {lai_stats['max']:.3f}")
                        print(f"    Std: {lai_stats['std']:.3f}")
                    else:
                        print(f"  {class_name} ({lai_var}): No valid data found")
                else:
                    print(f"  {lai_var} not found in dataset")
        
        # Also check annual averages
        print(f"\n=== Annual Averages ===")
        for lai_var, class_name in lai_mapping.items():
            if lai_var in ds.data_vars:
                lai_data = ds[lai_var]
                
                # Calculate annual mean
                annual_mean = lai_data.mean(dim='time')
                
                # Get valid (non-NaN, non-zero) LAI values
                valid_mask = (~np.isnan(annual_mean)) & (annual_mean > 0)
                valid_values = annual_mean.where(valid_mask)
                
                if valid_values.count() > 0:
                    lai_stats = {
                        'min': float(valid_values.min()),
                        'max': float(valid_values.max()),
                        'mean': float(valid_values.mean()),
                        'median': float(valid_values.median()),
                        'std': float(valid_values.std()),
                        'count': int(valid_values.count())
                    }
                    
                    print(f"  {class_name} ({lai_var}) - Annual Mean:")
                    print(f"    Count: {lai_stats['count']:,} pixels")
                    print(f"    Mean: {lai_stats['mean']:.3f}")
                    print(f"    Median: {lai_stats['median']:.3f}")
                    print(f"    Min: {lai_stats['min']:.3f}")
                    print(f"    Max: {lai_stats['max']:.3f}")
                    print(f"    Std: {lai_stats['std']:.3f}")
                else:
                    print(f"  {class_name} ({lai_var}): No valid annual data found")
        
        ds.close()
        
    except Exception as e:
        print(f"Error loading or analyzing LAI dataset: {e}")
        return

def check_UK_scenario_lai():
    """Check LAI values in a processed UK scenario"""
    
    # Look for UK scenario folders
    import os
    scenario_folders = []
    intermediate_path = 'intermediate'
    
    if os.path.exists(intermediate_path):
        for item in os.listdir(intermediate_path):
            if item.startswith('scenario_') and os.path.isdir(os.path.join(intermediate_path, item)):
                scenario_folders.append(item)
    
    print(f"\nFound UK scenario folders: {scenario_folders}")
    
    if scenario_folders:
        # Check the first scenario folder
        scenario_path = os.path.join(intermediate_path, scenario_folders[0])
        print(f"\nChecking scenario: {scenario_path}")
        
        # Look for LAI files in the scenario folder
        lai_files = []
        if os.path.exists(scenario_path):
            for file in os.listdir(scenario_path):
                if 'lai' in file.lower() or 'leaf' in file.lower():
                    lai_files.append(file)
        
        print(f"LAI files in scenario: {lai_files}")
        
        # Try to analyze one of the LAI files
        if lai_files:
            lai_file_path = os.path.join(scenario_path, lai_files[0])
            print(f"Analyzing: {lai_file_path}")
            
            try:
                if lai_file_path.endswith('.nc'):
                    ds = xr.open_dataset(lai_file_path)
                    print(f"Dataset variables: {list(ds.data_vars)}")
                    print(f"Dataset dimensions: {dict(ds.dims)}")
                    ds.close()
                else:
                    print(f"File format not supported for analysis: {lai_file_path}")
            except Exception as e:
                print(f"Error analyzing scenario LAI file: {e}")

if __name__ == "__main__":
    print("=== LAI Analysis for PM2.5 Deposition Investigation ===")
    print("Investigating why grassland shows higher deposition than forest")
    
    # Analyze main LAI dataset
    analyze_lai_by_class()
    
    # Check UK scenario LAI values
    check_UK_scenario_lai()
    
    print("\n=== Analysis Complete ===")