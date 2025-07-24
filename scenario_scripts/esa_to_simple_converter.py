#!/usr/bin/env python3
"""
ESA CCI to Simple classification converter for UK scenarios
"""

import numpy as np
import rasterio
from pathlib import Path
import csv

def load_uk_esa_mapping():
    """Load the UK ESA CCI to Simple classification mapping"""
    
    # UK-specific mapping covering all codes found in scenarios
    uk_mapping = {
        # Other (0) - No data, urban, bare, water, ice
        0: 0,    # No Data
        190: 0,  # Urban areas
        200: 0,  # Bare areas
        201: 0,  # Consolidated bare areas
        202: 0,  # Unconsolidated bare areas
        204: 0,  # Bare area variant
        205: 0,  # Bare area variant
        206: 0,  # Bare area variant
        210: 0,  # Water bodies
        220: 0,  # Permanent snow and ice
        
        # Cropland (1) - All agricultural/crop types
        10: 1,   # Cropland, rainfed
        20: 1,   # Cropland, irrigated
        30: 1,   # Mosaic cropland (>50%)
        34: 1,   # Cropland variant
        35: 1,   # Cropland variant
        39: 1,   # Cropland variant
        
        # Grass (2) - Grassland, shrubland, wetlands, sparse vegetation
        11: 2,   # Herbaceous cover
        40: 2,   # Mosaic natural vegetation (>50%)
        44: 2,   # Mixed vegetation variant
        49: 2,   # Mixed vegetation variant
        109: 2,  # Herbaceous mosaic variant
        110: 2,  # Mosaic herbaceous cover (>50%)
        114: 2,  # Herbaceous/shrub variant
        115: 2,  # Herbaceous/shrub variant
        119: 2,  # Shrubland variant
        120: 2,  # Shrubland
        124: 2,  # Shrubland variant
        130: 2,  # Grassland
        134: 2,  # Grassland variant
        140: 2,  # Lichens and mosses
        150: 2,  # Sparse vegetation
        154: 2,  # Sparse vegetation variant
        180: 2,  # Shrub/herbaceous cover, flooded
        184: 2,  # Wetland variant
        
        # Forest (3) - All tree cover types
        12: 3,   # Tree or shrub cover
        50: 3,   # Tree cover, broadleaved, evergreen
        60: 3,   # Tree cover, broadleaved, deciduous
        65: 3,   # Forest variant (broadleaved)
        70: 3,   # Tree cover, needleleaved, evergreen
        75: 3,   # Forest variant (needleleaved evergreen)
        80: 3,   # Tree cover, needleleaved, deciduous
        85: 3,   # Forest variant (needleleaved deciduous)
        90: 3,   # Tree cover, mixed leaf type
        95: 3,   # Forest variant (mixed)
        100: 3,  # Mosaic tree and shrub (>50%)
        104: 3,  # Tree/shrub mosaic variant
        105: 3,  # Tree/shrub mosaic variant
        160: 3,  # Tree cover, flooded, fresh water
        170: 3,  # Tree cover, flooded, saline water
    }
    
    return uk_mapping

def convert_esa_to_simple(input_path, output_path, mapping=None):
    """
    Convert ESA CCI raster to Simple 4-class classification
    
    Args:
        input_path: Path to ESA CCI raster file
        output_path: Path for output Simple classification raster
        mapping: Optional custom mapping dict, uses UK mapping if None
    """
    
    if mapping is None:
        mapping = load_uk_esa_mapping()
    
    print(f"Converting {Path(input_path).name} to Simple classification...")
    
    with rasterio.open(input_path) as src:
        # Read the ESA data
        esa_data = src.read(1)
        
        # Create output array initialized to 0 (Other/No Data)
        simple_data = np.zeros_like(esa_data, dtype=np.uint8)
        
        # Apply mapping
        for esa_code, simple_code in mapping.items():
            mask = (esa_data == esa_code)
            simple_data[mask] = simple_code
        
        # Copy metadata and update
        profile = src.profile.copy()
        profile.update({
            'dtype': 'uint8',
            'nodata': 0,
            'compress': 'lzw'
        })
        
        # Write output
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(simple_data, 1)
            
            # Add descriptions
            dst.set_band_description(1, "Simple Land Use Classification")
            dst.update_tags(1, **{
                'class_0': 'Other (water, urban, bare, no data)',
                'class_1': 'Cropland',
                'class_2': 'Grass (grassland, shrubland, wetlands)',
                'class_3': 'Forest'
            })
    
    print(f"  Converted to: {output_path}")
    
    # Report conversion statistics
    unique_esa, esa_counts = np.unique(esa_data, return_counts=True)
    unique_simple, simple_counts = np.unique(simple_data, return_counts=True)
    
    total_pixels = esa_data.size
    
    print(f"  Input ESA codes: {len(unique_esa)} unique values")
    print(f"  Output Simple classes: {len(unique_simple)} unique values")
    
    simple_names = {0: "Other", 1: "Cropland", 2: "Grass", 3: "Forest"}
    print(f"  Class distribution:")
    for simple_val, count in zip(unique_simple, simple_counts):
        percentage = count / total_pixels * 100
        class_name = simple_names.get(simple_val, f"Class_{simple_val}")
        print(f"    {class_name}: {percentage:.1f}% ({count:,} pixels)")
    
    return simple_data

def verify_conversion(esa_path, simple_path, mapping=None):
    """
    Verify that conversion was applied correctly by checking some sample pixels
    """
    
    if mapping is None:
        mapping = load_uk_esa_mapping()
    
    print(f"\nVerifying conversion...")
    
    with rasterio.open(esa_path) as esa_src, rasterio.open(simple_path) as simple_src:
        # Read both datasets
        esa_data = esa_src.read(1)
        simple_data = simple_src.read(1)
        
        # Check that all ESA codes were properly mapped
        unique_esa = np.unique(esa_data)
        unmapped_codes = []
        
        for esa_code in unique_esa:
            if esa_code not in mapping:
                unmapped_codes.append(esa_code)
        
        if unmapped_codes:
            print(f"  ⚠️  WARNING: Unmapped ESA codes found: {unmapped_codes}")
            return False
        else:
            print(f"  ✓ All ESA codes properly mapped")
        
        # Sample verification - check 100 random pixels
        total_pixels = esa_data.size
        sample_indices = np.random.choice(total_pixels, min(100, total_pixels), replace=False)
        
        correct_mappings = 0
        for idx in sample_indices:
            flat_idx = np.unravel_index(idx, esa_data.shape)
            esa_val = esa_data[flat_idx]
            simple_val = simple_data[flat_idx]
            expected_simple = mapping.get(esa_val, 0)
            
            if simple_val == expected_simple:
                correct_mappings += 1
        
        accuracy = correct_mappings / len(sample_indices) * 100
        print(f"  ✓ Sample verification: {accuracy:.1f}% accuracy ({correct_mappings}/{len(sample_indices)} pixels)")
        
        return accuracy == 100.0

if __name__ == "__main__":
    # Test conversion with a UK scenario
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python esa_to_simple_converter.py <input_esa.tif> <output_simple.tif>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not Path(input_file).exists():
        print(f"Error: Input file {input_file} does not exist")
        sys.exit(1)
    
    # Convert
    convert_esa_to_simple(input_file, output_file)
    
    # Verify
    verify_conversion(input_file, output_file)
    
    print(f"\nConversion complete! ✓")