#!/usr/bin/env python3
"""
Test script to validate dust land use mapping
"""

import pygeoprocessing.geoprocessing as geop
import numpy as np
import math

# Test the z0 function with Simple 4-class values
def z0(lu):
    k = 100.0
    fdtf = 0.0
    
    # Handle Simple 4-class classification (UK scenarios): 0=Other, 1=Cropland, 2=Grass, 3=Forest
    if lu <= 3:
        match lu:
            case 0: # Other (water, urban, bare) - Conservative: no dust emissions
                k = 100.0
                fdtf = 0.0
            case 1: # Cropland - moderate dust emissions
                k = 0.0310
                fdtf = 0.75
            case 2: # Grass - moderate dust emissions  
                k = 0.1000
                fdtf = 0.75
            case 3: # Forest - no dust emissions
                k = 50.0
                fdtf = 0.0
    else:
        # IGBP codes would be handled here
        k = 100.0
        fdtf = 0.0
    
    # Convert to surface roughness effect
    result = fdtf / (2.5 * math.log(1000.0/k))
    return result

# Test mapping for each Simple class
print("Testing dust land use mapping for Simple 4-class:")
print("=" * 50)

classes = {
    0: "Other (water, urban, bare)",
    1: "Cropland", 
    2: "Grass",
    3: "Forest"
}

for code, name in classes.items():
    z0_effect = z0(code)
    print(f"Class {code} ({name}): z0_effect = {z0_effect:.6f}")

print("\nReading current land use data:")
lu_array = geop.raster_to_numpy_array('inputs/gblulcg20_10000.tif')
unique_values, counts = np.unique(lu_array, return_counts=True)

print(f"Land use distribution:")
for val, count in zip(unique_values, counts):
    if val in classes:
        name = classes[val]
        percent = (count / lu_array.size) * 100
        z0_val = z0(val)
        print(f"  {val} ({name}): {count:,} pixels ({percent:.1f}%) -> z0_effect = {z0_val:.6f}")

print(f"\nTotal pixels: {lu_array.size:,}")
print("Land use mapping test completed successfully!")