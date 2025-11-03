#!/usr/bin/env python3
"""
Create Devegetated Counterfactual Scenario

This script reads the global IGBP land use data and creates a counterfactual
scenario where all vegetation (trees, grassland, shrubland) is converted to
barren land. This allows estimation of dust emissions in a completely
devegetated world.

Usage:
    python create_devegetated_scenario.py

Input:  inputs/gblulcg20_reprojected_10000.tif (global IGBP land use)
Output: inputs/gblulcg20_10000_devegetated.tif (counterfactual scenario)
"""

import rasterio
import numpy as np
from pathlib import Path

def create_devegetated_scenario():
    """
    Convert all vegetation (trees, grassland, shrubland) to barren land.
    
    IGBP codes to convert to barren (19):
    - Trees/Forest: 11, 12, 13, 14, 15
    - Grassland: 7  
    - Shrubland: 8, 9, 20
    
    All other land uses (urban, water, crops, etc.) remain unchanged.
    """
    
    input_file = "../inputs/gblulcg20_reprojected_10000.tif"
    output_file = "../inputs/gblulcg20_10000_devegetated.tif"
    
    print(f"🌍 Creating devegetated counterfactual scenario")
    print(f"   Input:  {input_file}")
    print(f"   Output: {output_file}")
    
    # Check input file exists
    if not Path(input_file).exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Define vegetation codes to convert to barren
    vegetation_codes = {
        # Forest types
        11: "Deciduous Broadleaf Forest",
        12: "Deciduous Needleleaf Forest", 
        13: "Evergreen Broadleaf Forest",
        14: "Evergreen Needleleaf Forest",
        15: "Mixed Forest",
        
        # Grassland
        7: "Grassland",
        
        # Shrubland types
        8: "Shrubland",
        9: "Mixed Shrubland/Grassland", 
        20: "Herbaceous Tundra"
    }
    
    barren_code = 19  # "Barren or Sparsely Vegetated"
    
    print(f"\n📋 Converting vegetation to barren land (code {barren_code}):")
    for code, name in vegetation_codes.items():
        print(f"   {code:2d} → {barren_code} : {name}")
    
    # Read input raster
    with rasterio.open(input_file) as src:
        # Read the land use data
        land_use = src.read(1)
        profile = src.profile.copy()
        
        print(f"\n📊 Input data statistics:")
        print(f"   Dimensions: {src.width} x {src.height}")
        print(f"   CRS: {src.crs}")
        print(f"   Data type: {src.dtypes[0]}")
        
        # Get original statistics
        unique_orig, counts_orig = np.unique(land_use, return_counts=True)
        total_pixels = land_use.size
        
        print(f"   Original unique values: {len(unique_orig)}")
        
        # Count vegetation pixels before conversion
        vegetation_pixels = 0
        vegetation_stats = {}
        
        for veg_code in vegetation_codes.keys():
            veg_mask = (land_use == veg_code)
            veg_count = np.sum(veg_mask)
            if veg_count > 0:
                vegetation_pixels += veg_count
                vegetation_stats[veg_code] = veg_count
                pct = veg_count / total_pixels * 100
                print(f"   Code {veg_code:2d} ({vegetation_codes[veg_code]}): {pct:.2f}% ({veg_count:,} pixels)")
        
        print(f"   Total vegetation pixels: {vegetation_pixels:,} ({vegetation_pixels/total_pixels*100:.1f}%)")
        
        # Create output array (copy of input)
        land_use_devegetated = land_use.copy()
        
        # Convert vegetation to barren
        for veg_code in vegetation_codes.keys():
            vegetation_mask = (land_use == veg_code)
            land_use_devegetated[vegetation_mask] = barren_code
        
        # Verify conversion
        converted_pixels = np.sum(land_use_devegetated == barren_code) - np.sum(land_use == barren_code)
        print(f"\n✅ Conversion complete:")
        print(f"   Pixels converted to barren: {converted_pixels:,}")
        print(f"   Original barren pixels: {np.sum(land_use == barren_code):,}")
        print(f"   Total barren pixels now: {np.sum(land_use_devegetated == barren_code):,}")
        
        # Get final statistics
        unique_final, counts_final = np.unique(land_use_devegetated, return_counts=True)
        print(f"   Final unique values: {len(unique_final)}")
        
        # Create clean profile for output to avoid TIFF field conflicts
        profile = {
            'driver': 'GTiff',
            'height': src.height,
            'width': src.width,
            'count': 1,
            'dtype': src.dtypes[0],
            'crs': src.crs,
            'transform': src.transform,
            'compress': 'lzw',
            'tiled': False,
            'interleave': 'band'
        }
        
        # Write output raster
        with rasterio.open(output_file, 'w', **profile) as dst:
            dst.write(land_use_devegetated, 1)
            
            # Add metadata
            dst.set_band_description(1, "IGBP Land Use - Devegetated Counterfactual")
            dst.update_tags(1, **{
                'title': 'Devegetated Counterfactual Land Use Scenario',
                'description': 'All vegetation (forests, grassland, shrubland) converted to barren land',
                'vegetation_converted': f'{converted_pixels} pixels',
                'conversion_percent': f'{converted_pixels/total_pixels*100:.1f}%',
                'created_by': 'create_devegetated_scenario.py',
                'source_file': input_file
            })
    
    print(f"\n🎉 Devegetated scenario created successfully!")
    print(f"   Output saved to: {output_file}")
    print(f"   File size: {Path(output_file).stat().st_size / 1024 / 1024:.1f} MB")
    
    return output_file

def verify_conversion(original_file, devegetated_file):
    """
    Verify that the conversion was applied correctly by comparing files.
    """
    
    print(f"\n🔍 Verifying conversion...")
    
    with rasterio.open(original_file) as orig_src, \
         rasterio.open(devegetated_file) as deveg_src:
        
        orig_data = orig_src.read(1)
        deveg_data = deveg_src.read(1)
        
        # Check dimensions match
        if orig_data.shape != deveg_data.shape:
            print(f"   ❌ Dimension mismatch!")
            return False
        
        # Count differences
        differences = np.sum(orig_data != deveg_data)
        total_pixels = orig_data.size
        
        print(f"   Changed pixels: {differences:,} ({differences/total_pixels*100:.1f}%)")
        
        # Check that only vegetation codes were changed
        vegetation_codes = [11, 12, 13, 14, 15, 7, 8, 9, 20]
        barren_code = 19
        
        changed_mask = (orig_data != deveg_data)
        
        # All changed pixels should have been vegetation in original
        changed_orig_values = orig_data[changed_mask]
        valid_changes = np.all(np.isin(changed_orig_values, vegetation_codes))
        
        # All changed pixels should be barren in new version
        changed_new_values = deveg_data[changed_mask]
        all_barren = np.all(changed_new_values == barren_code)
        
        if valid_changes and all_barren:
            print(f"   ✅ Conversion verified: Only vegetation codes converted to barren")
            return True
        else:
            print(f"   ❌ Conversion error: Invalid changes detected")
            return False

if __name__ == "__main__":
    try:
        # Create devegetated scenario
        output_file = create_devegetated_scenario()
        
        # Verify the conversion
        verify_conversion("../inputs/gblulcg20_reprojected_10000.tif", output_file)
        
        print(f"\n🚀 Ready to run dust emissions with devegetated scenario!")
        print(f"   To use: Copy {output_file} to inputs/gblulcg20_10000.tif")
        print(f"   Then run: python run_dust_emissions.py")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
