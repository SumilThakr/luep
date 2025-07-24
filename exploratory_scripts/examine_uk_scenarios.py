#!/usr/bin/env python3
"""
Exploratory script to examine UK scenario maps and determine:
1. What classification system they use (pixel values)
2. Spatial extent and projection information
3. Any metadata or legend information
"""

import os
import sys
import numpy as np
import rasterio
from pathlib import Path

def examine_scenario_file(filepath):
    """Examine a single scenario TIFF file"""
    print(f"\n=== Examining: {filepath.name} ===")
    
    try:
        with rasterio.open(filepath) as src:
            # Basic info
            print(f"Dimensions: {src.width} x {src.height}")
            print(f"Bands: {src.count}")
            print(f"Data type: {src.dtypes[0]}")
            print(f"CRS: {src.crs}")
            print(f"Transform: {src.transform}")
            
            # Spatial bounds
            bounds = src.bounds
            print(f"Bounds: {bounds}")
            print(f"  West: {bounds.left:.6f}")
            print(f"  East: {bounds.right:.6f}")
            print(f"  South: {bounds.bottom:.6f}")
            print(f"  North: {bounds.top:.6f}")
            
            # Read data and examine unique values
            data = src.read(1)
            
            # Basic stats
            print(f"Data range: {data.min()} to {data.max()}")
            print(f"Data shape: {data.shape}")
            print(f"No-data value: {src.nodata}")
            
            # Unique values (sample if too many)
            unique_vals = np.unique(data[~np.isnan(data)])
            print(f"Number of unique values: {len(unique_vals)}")
            
            if len(unique_vals) <= 50:
                print(f"Unique values: {unique_vals}")
            else:
                print(f"Sample unique values: {unique_vals[:20]}...")
                print(f"Value range summary:")
                print(f"  Min 10 values: {unique_vals[:10]}")
                print(f"  Max 10 values: {unique_vals[-10:]}")
            
            # Check for metadata
            print(f"Metadata: {src.tags()}")
            
            return {
                'bounds': bounds,
                'crs': src.crs,
                'unique_values': unique_vals,
                'shape': data.shape,
                'data_type': src.dtypes[0]
            }
            
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

def main():
    # Path to UK scenarios
    scenario_dir = Path("scenarios/UKNatureFrontierWithAir/United Kingdom/ScenarioMaps")
    
    if not scenario_dir.exists():
        print(f"Error: {scenario_dir} does not exist")
        return
    
    # Get all TIFF files
    tiff_files = list(scenario_dir.glob("*.tif"))
    
    if not tiff_files:
        print(f"No TIFF files found in {scenario_dir}")
        return
    
    print(f"Found {len(tiff_files)} scenario files:")
    for f in tiff_files:
        print(f"  - {f.name}")
    
    # Examine first few files in detail
    results = []
    for i, tiff_file in enumerate(tiff_files[:3]):  # Examine first 3 files
        result = examine_scenario_file(tiff_file)
        if result:
            results.append(result)
    
    # Summary comparison
    if results:
        print(f"\n=== SUMMARY COMPARISON ===")
        print(f"All files have same CRS: {len(set(str(r['crs']) for r in results)) == 1}")
        print(f"All files have same bounds: {len(set(str(r['bounds']) for r in results)) == 1}")
        print(f"All files have same shape: {len(set(str(r['shape']) for r in results)) == 1}")
        
        # Combined unique values
        all_unique = set()
        for r in results:
            all_unique.update(r['unique_values'])
        
        all_unique = sorted(list(all_unique))
        print(f"\nCombined unique values across all examined files:")
        print(f"Total unique values: {len(all_unique)}")
        if len(all_unique) <= 50:
            print(f"Values: {all_unique}")
        else:
            print(f"Sample values: {all_unique[:20]}...")
    
    # Look for any legend or metadata files
    print(f"\n=== LOOKING FOR METADATA FILES ===")
    scenario_parent = scenario_dir.parent
    
    # Common metadata file patterns
    metadata_patterns = ["*.txt", "*.csv", "*.xml", "*.json", "*.yml", "*.yaml", "*legend*", "*metadata*"]
    
    for pattern in metadata_patterns:
        files = list(scenario_parent.rglob(pattern))
        if files:
            print(f"\nFound {pattern} files:")
            for f in files[:10]:  # Limit to first 10
                print(f"  - {f.relative_to(scenario_parent)}")
    
    # Check if there's a current_lulc file to compare against
    input_rasters_dir = scenario_dir.parent / "InputRasters"
    if input_rasters_dir.exists():
        current_lulc = input_rasters_dir / "current_lulc.tif"
        if current_lulc.exists():
            print(f"\n=== EXAMINING CURRENT LULC FOR COMPARISON ===")
            examine_scenario_file(current_lulc)

if __name__ == "__main__":
    main()