#!/usr/bin/env python3
"""
Optimized dust emissions processing - only runs land-use dependent steps
"""
from dust_scripts import dust_1_soil_texture
from dust_scripts import dust_2_flux_calc
from dust_scripts import dust_3_sum
import os

inputdir = "." # current directory (contains inputs folder)

def main():
    # Check if soil texture already exists (land-use independent)
    soil_texture_path = "intermediate/soil_texture.tif"
    
    if not os.path.exists(soil_texture_path):
        print("Creating soil texture classification (one-time setup)...")
        dust_1_soil_texture.run(inputdir)
        print("Completed.\n")
    else:
        print("Using existing soil texture classification...")
        print("Completed.\n")
    
    print("Calculating dust fluxes (land-use dependent)")
    dust_2_flux_calc.run(inputdir)
    print("Completed.\n")
    
    print("Calculating total dust emissions (land-use dependent)")
    dust_3_sum.run(inputdir)
    print("Completed.\n")
    
if __name__ == '__main__':
    main()