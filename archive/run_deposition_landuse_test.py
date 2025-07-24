#!/usr/bin/env python3
"""
Test script for land-use-specific PM2.5 deposition calculation

This script tests the new land-use-specific deposition velocity system:
1. Generate land-use-specific deposition velocities (forest, grass, cropland)
2. Calculate PM2.5 deposition using appropriate velocity for each land use class
3. Compare results with previous single-velocity approach

Usage:
    /Users/sumilthakrar/yes/envs/rasters/bin/python run_deposition_landuse_test.py
"""

import sys
import os
from dep_scripts import dep_3_velocity_landuse, dep_4_multiply_landuse

def main():
    print("=" * 80)
    print("TESTING LAND-USE-SPECIFIC PM2.5 DEPOSITION CALCULATION")
    print("=" * 80)
    print()
    print("This test will:")
    print("1. Generate land-use-specific deposition velocities")
    print("2. Calculate PM2.5 deposition using land-use-specific velocities")
    print("3. Report results and compare with previous approach")
    print()
    
    # Define input directory
    inputdir = ""
    
    try:
        # Step 1: Generate land-use-specific deposition velocities
        print("STEP 1: Generating land-use-specific deposition velocities")
        print("-" * 60)
        dep_3_velocity_landuse.run(inputdir)
        print()
        
        # Step 2: Calculate PM2.5 deposition with land-use-specific velocities
        print("STEP 2: Calculating PM2.5 deposition with land-use-specific velocities")
        print("-" * 60)
        results = dep_4_multiply_landuse.run(inputdir)
        print()
        
        if results:
            print("STEP 3: Test Results Summary")
            print("-" * 60)
            print(f"✅ Test completed successfully!")
            print(f"📊 Total UK PM2.5 deposition: {results['total_deposition']:,.0f} kg/year")
            print(f"📈 Maximum pixel deposition: {results['max_deposition']:.2f} kg/year")
            print(f"📊 Mean pixel deposition: {results['mean_deposition']:.2f} kg/year")
            print(f"💾 Output saved to: {results['output_file']}")
            print()
            print("KEY IMPROVEMENTS:")
            print("- Forest areas now use higher deposition velocities")
            print("- Grass/cropland areas use lower deposition velocities (~50% of forest)")
            print("- Results should show more realistic forest > grass deposition patterns")
            print()
            print("Next steps:")
            print("1. Compare with previous results to verify improvement")
            print("2. Run on all UK scenarios using the new methodology")
            print("3. Validate that forestry_expansion > grazing_expansion deposition")
            
        else:
            print("❌ Test failed - no results generated")
            return 1
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())