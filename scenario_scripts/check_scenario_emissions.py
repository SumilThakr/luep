#!/usr/bin/env python3
"""
UK Scenario Emissions Checker

This script checks for the existence of emission result files across all UK land-use scenarios
and provides summary statistics for each emission type.

Expected files per scenario:
- dust_emissions.tiff (or dust_emissions.tif)
- nox_emissions_uk.tif  
- nh3_emissions.nc
- bvoc_emissions.nc

Author: Generated for LUEP project
"""

import os
import sys
import numpy as np
import rasterio
import xarray as xr
from pathlib import Path
import pandas as pd

def get_uk_scenarios():
    """Get list of UK scenarios from CLAUDE.md documentation"""
    scenarios = [
        'extensification_current_practices',
        'extensification_bmps_irrigated',
        'extensification_bmps_rainfed', 
        'extensification_intensified_irrigated',
        'extensification_intensified_rainfed',
        'fixedarea_bmps_irrigated',
        'fixedarea_bmps_rainfed',
        'fixedarea_intensified_irrigated',
        'fixedarea_intensified_rainfed',
        'forestry_expansion',
        'grazing_expansion',
        'restoration',
        'sustainable_current',
        'all_econ',
        'all_urban'
    ]
    return scenarios

def check_file_exists(scenario_dir, filename_options):
    """Check if any of the filename options exist in the scenario directory"""
    for filename in filename_options:
        file_path = scenario_dir / filename
        if file_path.exists():
            return file_path
    return None

def get_raster_stats(file_path):
    """Get basic statistics for raster files"""
    try:
        with rasterio.open(file_path) as src:
            data = src.read(1, masked=True)
            # Remove masked/nodata values
            valid_data = data[~data.mask] if hasattr(data, 'mask') else data[~np.isnan(data)]
            
            if len(valid_data) == 0:
                return {'min': np.nan, 'max': np.nan, 'mean': np.nan, 'sum': np.nan, 'count': 0}
            
            return {
                'min': float(np.min(valid_data)),
                'max': float(np.max(valid_data)),
                'mean': float(np.mean(valid_data)),
                'sum': float(np.sum(valid_data)),
                'count': len(valid_data)
            }
    except Exception as e:
        print(f"Error reading raster {file_path}: {e}")
        return {'min': np.nan, 'max': np.nan, 'mean': np.nan, 'sum': np.nan, 'count': 0, 'error': str(e)}

def get_netcdf_stats(file_path):
    """Get basic statistics for NetCDF files"""
    try:
        with xr.open_dataset(file_path) as ds:
            # Get the main data variable (usually the first one or look for common names)
            data_vars = list(ds.data_vars.keys())
            if not data_vars:
                return {'min': np.nan, 'max': np.nan, 'mean': np.nan, 'sum': np.nan, 'count': 0, 'variables': []}
            
            # Use the first data variable
            main_var = data_vars[0]
            data = ds[main_var].values
            
            # Handle different dimensions
            if data.ndim > 2:
                data = data.sum(axis=0)  # Sum over time or other dimensions
            
            # Remove NaN values
            valid_data = data[~np.isnan(data)]
            
            if len(valid_data) == 0:
                return {'min': np.nan, 'max': np.nan, 'mean': np.nan, 'sum': np.nan, 'count': 0, 'variables': data_vars}
            
            return {
                'min': float(np.min(valid_data)),
                'max': float(np.max(valid_data)), 
                'mean': float(np.mean(valid_data)),
                'sum': float(np.sum(valid_data)),
                'count': len(valid_data),
                'variables': data_vars,
                'main_variable': main_var
            }
    except Exception as e:
        print(f"Error reading NetCDF {file_path}: {e}")
        return {'min': np.nan, 'max': np.nan, 'mean': np.nan, 'sum': np.nan, 'count': 0, 'error': str(e)}

def main():
    """Main function to check scenario emissions"""
    
    # Define paths
    base_dir = Path.cwd()
    outputs_dir = base_dir / "outputs" / "uk_results"
    
    if not outputs_dir.exists():
        print(f"Error: UK results directory not found at {outputs_dir}")
        sys.exit(1)
    
    # Get scenarios
    scenarios = get_uk_scenarios()
    
    # Define expected files with alternative names
    expected_files = {
        'dust_emissions': ['dust_emissions.tiff', 'dust_emissions.tif'],
        'nox_emissions': ['nox_emissions_uk.tif'],
        'nh3_emissions': ['nh3_emissions.nc'],
        'bvoc_emissions': ['bvoc_emissions.nc']
    }
    
    # Results storage
    results = {
        'scenario': [],
        'dust_emissions_exists': [],
        'dust_emissions_path': [],
        'dust_emissions_min': [],
        'dust_emissions_max': [],
        'dust_emissions_sum': [],
        'nox_emissions_exists': [],
        'nox_emissions_path': [],
        'nox_emissions_min': [],
        'nox_emissions_max': [],
        'nox_emissions_sum': [],
        'nh3_emissions_exists': [],
        'nh3_emissions_path': [],
        'nh3_emissions_min': [],
        'nh3_emissions_max': [],
        'nh3_emissions_sum': [],
        'bvoc_emissions_exists': [],
        'bvoc_emissions_path': [],
        'bvoc_emissions_min': [],
        'bvoc_emissions_max': [],
        'bvoc_emissions_sum': [],
        'all_files_present': []
    }
    
    emission_stats = {emission_type: [] for emission_type in expected_files.keys()}
    
    print("=== UK Scenario Emissions File Checker ===\n")
    print(f"Checking {len(scenarios)} scenarios in: {outputs_dir}\n")
    
    # Check each scenario
    for scenario in scenarios:
        scenario_dir = outputs_dir / scenario
        
        print(f"Checking scenario: {scenario}")
        
        if not scenario_dir.exists():
            print(f"  WARNING: Scenario directory not found: {scenario_dir}")
            results['scenario'].append(scenario)
            for emission_type in expected_files.keys():
                results[f'{emission_type}_exists'].append(False)
                results[f'{emission_type}_path'].append('')
                results[f'{emission_type}_min'].append(np.nan)
                results[f'{emission_type}_max'].append(np.nan)
                results[f'{emission_type}_sum'].append(np.nan)
                emission_stats[emission_type].append({})
            results['all_files_present'].append(False)
            continue
        
        # Check each emission type
        all_present = True
        scenario_stats = {}
        
        for emission_type, filenames in expected_files.items():
            file_path = check_file_exists(scenario_dir, filenames)
            exists = file_path is not None
            
            results[f'{emission_type}_exists'].append(exists)
            results[f'{emission_type}_path'].append(str(file_path) if exists else '')
            
            if exists:
                print(f"  ✓ {emission_type}: {file_path.name}")
                
                # Get statistics
                if emission_type in ['dust_emissions', 'nox_emissions']:
                    stats = get_raster_stats(file_path)
                else:  # NetCDF files
                    stats = get_netcdf_stats(file_path)
                
                emission_stats[emission_type].append(stats)
                scenario_stats[emission_type] = stats
                
                # Add min/max/sum to results
                results[f'{emission_type}_min'].append(stats.get('min', np.nan))
                results[f'{emission_type}_max'].append(stats.get('max', np.nan))
                results[f'{emission_type}_sum'].append(stats.get('sum', np.nan))
            else:
                print(f"  ✗ {emission_type}: NOT FOUND (expected: {', '.join(filenames)})")
                emission_stats[emission_type].append({})
                results[f'{emission_type}_min'].append(np.nan)
                results[f'{emission_type}_max'].append(np.nan)
                results[f'{emission_type}_sum'].append(np.nan)
                all_present = False
        
        results['scenario'].append(scenario)
        results['all_files_present'].append(all_present)
        print()
    
    # Create summary DataFrame
    df = pd.DataFrame(results)
    
    # Print summary table
    print("=== FILE EXISTENCE SUMMARY ===")
    print(df[['scenario', 'dust_emissions_exists', 'nox_emissions_exists', 'nh3_emissions_exists', 'bvoc_emissions_exists', 'all_files_present']].to_string(index=False))
    
    # Print min/max/sum summary table  
    print("\n=== MIN/MAX/SUM VALUES SUMMARY ===")
    summary_cols = ['scenario']
    for emission_type in expected_files.keys():
        summary_cols.extend([f'{emission_type}_min', f'{emission_type}_max', f'{emission_type}_sum'])
    
    # Format the dataframe for better display
    display_df = df[summary_cols].copy()
    
    # Format scientific notation for better readability
    for col in summary_cols[1:]:  # Skip scenario column
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"{x:.2e}" if not pd.isna(x) and x != 0 else str(x))
    
    print(display_df.to_string(index=False))
    print()
    
    # Calculate completion rates
    total_scenarios = len(scenarios)
    completion_rates = {}
    for emission_type in expected_files.keys():
        completed = sum(results[f'{emission_type}_exists'])
        completion_rates[emission_type] = completed / total_scenarios * 100
    
    print("=== COMPLETION RATES ===")
    for emission_type, rate in completion_rates.items():
        print(f"{emission_type:15}: {rate:5.1f}% ({sum(results[f'{emission_type}_exists'])}/{total_scenarios})")
    
    overall_complete = sum(results['all_files_present'])
    print(f"{'all_complete':15}: {overall_complete/total_scenarios*100:5.1f}% ({overall_complete}/{total_scenarios})")
    print()
    
    # Print statistics summary for each emission type
    print("=== EMISSION STATISTICS SUMMARY ===")
    
    for emission_type in expected_files.keys():
        print(f"\n{emission_type.upper()} EMISSIONS:")
        print("-" * 50)
        
        # Collect valid statistics
        valid_stats = [s for s in emission_stats[emission_type] if s and 'error' not in s]
        
        if not valid_stats:
            print("No valid data found")
            continue
        
        # Extract min/max values across scenarios
        mins = [s['min'] for s in valid_stats if not np.isnan(s['min'])]
        maxs = [s['max'] for s in valid_stats if not np.isnan(s['max'])]
        means = [s['mean'] for s in valid_stats if not np.isnan(s['mean'])]
        sums = [s['sum'] for s in valid_stats if not np.isnan(s['sum'])]
        
        if mins:
            print(f"Minimum values across scenarios:")
            print(f"  Lowest:  {min(mins):12.4e}")
            print(f"  Highest: {max(mins):12.4e}")
        
        if maxs:
            print(f"Maximum values across scenarios:")
            print(f"  Lowest:  {min(maxs):12.4e}")
            print(f"  Highest: {max(maxs):12.4e}")
        
        if means:
            print(f"Mean values across scenarios:")
            print(f"  Lowest:  {min(means):12.4e}")
            print(f"  Highest: {max(means):12.4e}")
        
        if sums:
            print(f"Total emissions across scenarios:")
            print(f"  Lowest:  {min(sums):12.4e}")
            print(f"  Highest: {max(sums):12.4e}")
        
        # Show scenario-specific details
        print(f"\nPer-scenario details:")
        for i, scenario in enumerate(scenarios):
            if i < len(emission_stats[emission_type]) and emission_stats[emission_type][i]:
                stats = emission_stats[emission_type][i]
                if 'error' in stats:
                    print(f"  {scenario:35}: ERROR - {stats['error']}")
                elif not np.isnan(stats.get('sum', np.nan)):
                    print(f"  {scenario:35}: total={stats['sum']:12.4e}, max={stats['max']:12.4e}")
                else:
                    print(f"  {scenario:35}: No valid data")
            else:
                print(f"  {scenario:35}: File not found")
    
    # Save detailed results to CSV
    output_file = outputs_dir / "emission_files_summary.csv"
    df.to_csv(output_file, index=False)
    print(f"\nDetailed results saved to: {output_file}")
    
    # Check for any missing scenarios
    missing_scenarios = [s for s in scenarios if not (outputs_dir / s).exists()]
    if missing_scenarios:
        print(f"\nMISSING SCENARIO DIRECTORIES:")
        for scenario in missing_scenarios:
            print(f"  - {scenario}")

if __name__ == "__main__":
    main()