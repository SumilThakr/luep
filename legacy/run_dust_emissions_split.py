#!/usr/bin/env python3
"""
Optimized dust emissions processing with meteorology preprocessing split
"""
from dust_scripts import dust_1_soil_texture
from dust_scripts import dust_meteorology_preprocessing  
from dust_scripts import dust_landuse_flux_calc
from dust_scripts import dust_3_sum
import os

inputdir = "." # current directory (contains inputs folder)

def main():
    # Step 1: Soil texture (land-use independent, run once)
    soil_texture_path = "intermediate/soil_texture.tif"
    if not os.path.exists(soil_texture_path):
        print("Creating soil texture classification (one-time setup)...")
        dust_1_soil_texture.run(inputdir)
        print("Completed.\n")
    else:
        print("Using existing soil texture classification...")
        print("Completed.\n")
    
    # Step 2: Meteorology preprocessing (land-use independent, run once)
    meteorology_dir = "intermediate/daily_meteorology"
    if not os.path.exists(meteorology_dir) or len(os.listdir(meteorology_dir)) < 700:  # ~365 days × 2 files
        print("Preprocessing meteorology for full year 2021 (one-time setup)...")
        dust_meteorology_preprocessing.run(inputdir)
        print("Completed.\n")
    else:
        print("Using existing meteorological preprocessing...")
        print("Completed.\n")
    
    # Step 3: Land use flux calculation (land-use dependent, run per scenario)
    print("Calculating dust fluxes with current land use (land-use dependent)")
    dust_landuse_flux_calc.run(inputdir)
    print("Completed.\n")
    
    # Step 4: Sum fluxes (run per scenario)
    print("Calculating total dust emissions")
    dust_3_sum.run(inputdir)
    print("Completed.\n")
    
if __name__ == '__main__':
    main()