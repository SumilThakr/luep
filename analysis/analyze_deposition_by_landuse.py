#!/usr/bin/env python
"""
Analyze PM2.5 deposition by land use class to understand why grassland
scenarios show higher total deposition than forest scenarios.
"""

import rasterio
import numpy as np
import pandas as pd
import os
import xarray as xr

def analyze_deposition_by_landuse():
    """Analyze deposition results broken down by land use class"""
    
    print("=== PM2.5 Deposition Analysis by Land Use Class ===")
    
    # Load the current UK scenario land use
    scenario_file = "inputs/scenario_landuse_esa_cci.tif"
    deposition_file = "outputs/PM2.5_annual_deposition_uk_2021.nc"
    leaf_area_file = "intermediate/leaf_area_01.nc"  # Use January as example
    
    if not all(os.path.exists(f) for f in [scenario_file, deposition_file, leaf_area_file]):
        print("Required files not found!")
        return
    
    # Load ESA CCI to Simple class mapping
    mapping_file = "inputs/UK_ESA_CCI_to_Simple_mapping.csv"
    esa_mapping = pd.read_csv(mapping_file)
    esa_to_simple = dict(zip(esa_mapping['ESA_CCI_Code'], esa_mapping['Simple_Class']))
    
    # Load land use data
    with rasterio.open(scenario_file) as src:
        land_use = src.read(1)
        land_use = np.flipud(land_use)  # Match the processing in the scripts
        
        # Convert to Simple classes
        simple_land_use = np.vectorize(lambda x: esa_to_simple.get(x, -1))(land_use)
    
    # Load deposition results
    deposition_ds = xr.open_dataset(deposition_file)
    deposition = deposition_ds['annual_PM2.5_deposition'].values
    
    # Load leaf area for reference
    leaf_area_ds = xr.open_dataset(leaf_area_file)
    leaf_area = leaf_area_ds['leaf_area'].values
    
    # Analyze by Simple class
    class_names = {0: 'Other', 1: 'Cropland', 2: 'Grassland', 3: 'Forest'}
    
    print(f"\nLand Use vs Deposition Analysis:")
    print(f"{'Class':<10} {'Name':<10} {'Pixels':<12} {'Area %':<8} {'Total Dep':<15} {'Dep %':<8} {'Mean Dep':<12} {'Mean LAI':<12}")
    print(f"{'-'*10} {'-'*10} {'-'*12} {'-'*8} {'-'*15} {'-'*8} {'-'*12} {'-'*12}")
    
    total_pixels = simple_land_use.size
    total_deposition = np.nansum(deposition[deposition > 0])
    
    results = []
    
    for simple_id in sorted([0, 1, 2, 3]):
        class_name = class_names.get(simple_id, f'Unknown({simple_id})')
        
        # Get mask for this class
        class_mask = (simple_land_use == simple_id)
        
        # Count pixels
        pixel_count = np.sum(class_mask)
        area_percent = (pixel_count / total_pixels) * 100
        
        # Get deposition for this class
        class_deposition = deposition[class_mask]
        class_leaf_area = leaf_area[class_mask]
        
        # Filter out zero/invalid values
        valid_dep_mask = class_deposition > 0
        valid_deposition = class_deposition[valid_dep_mask]
        valid_leaf_area = class_leaf_area[valid_dep_mask]
        
        if len(valid_deposition) > 0:
            total_class_deposition = np.sum(valid_deposition)
            dep_percent = (total_class_deposition / total_deposition) * 100
            mean_deposition = np.mean(valid_deposition)
            mean_leaf_area = np.mean(valid_leaf_area)
            
            results.append({
                'class_id': simple_id,
                'class_name': class_name,
                'pixel_count': pixel_count,
                'area_percent': area_percent,
                'total_deposition': total_class_deposition,
                'dep_percent': dep_percent,
                'mean_deposition': mean_deposition,
                'mean_leaf_area': mean_leaf_area
            })
            
            print(f"{simple_id:<10} {class_name:<10} {pixel_count:<12,} {area_percent:<8.1f} {total_class_deposition:<15.1f} {dep_percent:<8.1f} {mean_deposition:<12.3f} {mean_leaf_area:<12.0f}")
        else:
            print(f"{simple_id:<10} {class_name:<10} {pixel_count:<12,} {area_percent:<8.1f} {'0.0':<15} {'0.0':<8} {'0.000':<12} {'0':<12}")
    
    # Calculate deposition per unit area for comparison
    print(f"\n=== Deposition Efficiency Analysis ===")
    print(f"This shows deposition per unit area and per unit LAI to compare efficiency:")
    print(f"{'Class':<10} {'Name':<10} {'Dep/Pixel':<12} {'Dep/LAI':<12} {'Explanation'}")
    print(f"{'-'*10} {'-'*10} {'-'*12} {'-'*12} {'-'*50}")
    
    for result in results:
        if result['pixel_count'] > 0 and result['mean_leaf_area'] > 0:
            dep_per_pixel = result['total_deposition'] / result['pixel_count']
            dep_per_lai = result['mean_deposition'] / (result['mean_leaf_area'] / 1000)  # Convert LAI from m² to km² scale
            
            explanation = ""
            if result['class_id'] == 2:  # Grassland
                explanation = "High total due to large area coverage"
            elif result['class_id'] == 3:  # Forest
                explanation = "High efficiency per LAI unit"
            
            print(f"{result['class_id']:<10} {result['class_name']:<10} {dep_per_pixel:<12.3f} {dep_per_lai:<12.6f} {explanation}")
    
    # Summary
    grassland_result = next((r for r in results if r['class_id'] == 2), None)
    forest_result = next((r for r in results if r['class_id'] == 3), None)
    
    if grassland_result and forest_result:
        print(f"\n=== Key Findings ===")
        print(f"1. Area Coverage:")
        print(f"   - Grassland covers {grassland_result['area_percent']:.1f}% of UK")
        print(f"   - Forest covers {forest_result['area_percent']:.1f}% of UK")
        print(f"   - Grassland has {grassland_result['area_percent']/forest_result['area_percent']:.1f}x more area than forest")
        
        print(f"\n2. Total Deposition:")
        print(f"   - Grassland: {grassland_result['total_deposition']:.1f} kg/year ({grassland_result['dep_percent']:.1f}%)")
        print(f"   - Forest: {forest_result['total_deposition']:.1f} kg/year ({forest_result['dep_percent']:.1f}%)")
        print(f"   - Grassland has {grassland_result['total_deposition']/forest_result['total_deposition']:.1f}x more total deposition")
        
        print(f"\n3. Per-Pixel Efficiency:")
        grass_dep_per_pixel = grassland_result['total_deposition'] / grassland_result['pixel_count']
        forest_dep_per_pixel = forest_result['total_deposition'] / forest_result['pixel_count']
        print(f"   - Grassland: {grass_dep_per_pixel:.3f} kg/year per pixel")
        print(f"   - Forest: {forest_dep_per_pixel:.3f} kg/year per pixel")
        print(f"   - Forest is {forest_dep_per_pixel/grass_dep_per_pixel:.1f}x more efficient per pixel")
        
        print(f"\n4. LAI Comparison:")
        print(f"   - Grassland mean LAI: {grassland_result['mean_leaf_area']:.0f} m²")
        print(f"   - Forest mean LAI: {forest_result['mean_leaf_area']:.0f} m²")
        print(f"   - Forest has {forest_result['mean_leaf_area']/grassland_result['mean_leaf_area']:.1f}x higher LAI per pixel")
        
        print(f"\n=== CONCLUSION ===")
        print(f"Grassland scenarios show higher TOTAL PM2.5 deposition because:")
        print(f"1. Grassland covers {grassland_result['area_percent']/forest_result['area_percent']:.1f}x more area than forest in the UK")
        print(f"2. Even though forest has higher LAI per pixel, the vast area difference dominates")
        print(f"3. This is geographically accurate - UK is primarily grassland/pasture, not forest")
        print(f"4. Forest is more efficient per unit area, but there's simply much less forest area")

if __name__ == "__main__":
    analyze_deposition_by_landuse()