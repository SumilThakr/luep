#!/usr/bin/env python3
"""
Examine the UK land use data after processing
"""
import rasterio
import numpy as np

print("=== Original UK Land Use ===")
with rasterio.open('inputs/gblulcg20_10000.tif') as src:
    uk_data = src.read(1)
    print(f"Shape: {uk_data.shape}")
    print(f"Bounds: {src.bounds}")
    print(f"CRS: {src.crs}")
    print(f"Land use classes: {sorted(set(uk_data.flatten()))}")
    for lc in [0, 1, 2, 3]:
        count = np.sum(uk_data == lc)
        pct = count / uk_data.size * 100
        print(f"  Class {lc}: {count:,} pixels ({pct:.1f}%)")

print("\n=== Aligned Land Use (if exists) ===")
aligned_path = "intermediate/aligned_scenario_landuse.tif"
try:
    with rasterio.open(aligned_path) as src:
        aligned_data = src.read(1)
        print(f"Shape: {aligned_data.shape}")
        print(f"Bounds: {src.bounds}")
        print(f"CRS: {src.crs}")
        print(f"Land use classes: {sorted(set(aligned_data.flatten()))}")
        for lc in [0, 1, 2, 3]:
            count = np.sum(aligned_data == lc)
            pct = count / aligned_data.size * 100
            print(f"  Class {lc}: {count:,} pixels ({pct:.1f}%)")
        
        # Check where UK data ended up in global grid
        uk_pixels = np.sum((aligned_data == 1) | (aligned_data == 2) | (aligned_data == 3))
        print(f"Total UK land use pixels in global grid: {uk_pixels}")
        
except Exception as e:
    print(f"Could not read aligned file: {e}")