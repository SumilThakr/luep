#!/usr/bin/env python3
"""
Fix PROJ Library Conflicts and Run Dust Processing

This script sets the correct PROJ environment variables to resolve database conflicts,
then runs the dust processing with global extent.

Usage:
    source ~/.bashrc && /Users/sumilthakrar/yes/envs/luep-analysis/bin/python utils/fix_proj_and_run_dust.py
"""

import os
import sys
from pathlib import Path

def fix_proj_environment():
    """Set correct PROJ environment variables to avoid database conflicts."""
    
    # Get the conda environment path
    luep_analysis_path = "/Users/sumilthakrar/yes/envs/luep-analysis"
    
    # Set PROJ environment variables to use the conda environment's PROJ database
    proj_lib = f"{luep_analysis_path}/share/proj"
    gdal_data = f"{luep_analysis_path}/share/gdal"
    
    print(f"🔧 Fixing PROJ library configuration:")
    print(f"   Setting PROJ_LIB: {proj_lib}")
    print(f"   Setting GDAL_DATA: {gdal_data}")
    
    # Check if paths exist
    if not Path(proj_lib).exists():
        print(f"   ⚠️  Warning: PROJ_LIB path does not exist: {proj_lib}")
    if not Path(gdal_data).exists():
        print(f"   ⚠️  Warning: GDAL_DATA path does not exist: {gdal_data}")
    
    # Set environment variables
    os.environ['PROJ_LIB'] = proj_lib
    os.environ['GDAL_DATA'] = gdal_data
    
    # Also try these additional environment variables
    os.environ['PROJ_DATA'] = proj_lib
    os.environ['PROJ_NETWORK'] = 'OFF'  # Disable network access for PROJ
    
    print(f"   ✅ Environment variables set")

def run_dust_processing():
    """Run the dust processing after fixing PROJ environment."""
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print(f"\n🌍 Running dust processing from: {os.getcwd()}")
    
    # Import dust processing modules (after setting environment)
    try:
        from dust_scripts import dust_2_flux_calc
        from dust_scripts import dust_3_sum
        
        print("=== GLOBAL DUST EMISSIONS CALCULATION ===")
        print("Skipping soil texture (already processed - not land-use dependent)")
        print("Running only the land-use dependent components:\n")
        
        inputdir = "."
        
        print("Calculating dust fluxes (IGBP land use → dust parameters → daily fluxes)")
        dust_2_flux_calc.run(inputdir)
        print("Completed.\n")
        
        print("Calculating total dust emissions (summing daily fluxes)")
        dust_3_sum.run(inputdir)
        print("Completed.\n")
        
        print("=== GLOBAL DUST EMISSIONS CALCULATION COMPLETE ===")
        print("Output: outputs/dust_sum.tiff")
        
    except Exception as e:
        print(f"❌ Error during dust processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        # Fix PROJ environment before importing any geospatial libraries
        fix_proj_environment()
        
        # Run dust processing
        run_dust_processing()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()