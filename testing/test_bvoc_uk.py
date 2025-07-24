#!/usr/bin/env python3
"""
Test bVOC processing with UK scenarios

This script tests the bVOC counterfactual estimation system with UK land use scenarios.
"""

import sys
import os
from pathlib import Path

def test_bvoc_files():
    """Test that bVOC input files are available"""
    
    print("🧪 Testing bVOC input files...")
    
    required_files = [
        "inputs/ag-bvoc.nc",
        "inputs/forest-bvoc.nc", 
        "inputs/grass-bvoc.nc"
    ]
    
    missing_files = []
    for filepath in required_files:
        if not os.path.exists(filepath):
            missing_files.append(filepath)
        else:
            print(f"✅ Found: {filepath}")
    
    if missing_files:
        print(f"❌ Missing bVOC files: {missing_files}")
        return False
    
    print("✅ All bVOC input files found")
    return True

def test_uk_scenario_bvoc():
    """Test bVOC processing with a UK scenario"""
    
    print("\n🧪 Testing UK scenario bVOC processing...")
    
    # Check if UK scenario is set up
    landuse_file = "inputs/gblulcg20_10000.tif"
    if not os.path.exists(landuse_file):
        print(f"❌ UK scenario not set up - {landuse_file} not found")
        print("Run: python setup_uk_scenario.py <scenario_name> first")
        return False
    
    try:
        # Test the bVOC counterfactual calculator directly
        sys.path.append('bvoc_scripts')
        from bvoc_counterfactual import load_bvoc_emissions, align_landuse_to_emissions
        
        print("Loading baseline bVOC emissions...")
        baseline_emissions = load_bvoc_emissions()
        
        # Check if we have at least one emission dataset
        valid_datasets = sum(1 for v in baseline_emissions.values() if v is not None)
        if valid_datasets == 0:
            print("❌ No valid bVOC emission datasets found")
            return False
        
        print(f"✅ Loaded {valid_datasets} bVOC emission datasets")
        
        print("Testing land use alignment...")
        landuse_data, landuse_transform, aligned_path = align_landuse_to_emissions(
            landuse_file, baseline_emissions
        )
        
        print(f"✅ Aligned land use data: {landuse_data.shape}")
        print(f"Land use classes found: {sorted(set(landuse_data.flatten()))}")
        
        # Cleanup
        if os.path.exists(aligned_path):
            os.remove(aligned_path)
        
        print("✅ UK scenario bVOC processing test passed")
        return True
        
    except Exception as e:
        print(f"❌ UK scenario bVOC test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_bvoc_run():
    """Test full bVOC run script"""
    
    print("\n🧪 Testing full bVOC run...")
    
    try:
        from run_bvoc_emissions import run
        
        # Run bVOC processing
        success = run("inputs")
        
        if success:
            # Check output file
            output_file = "outputs/bvoc_emissions.nc"
            if os.path.exists(output_file):
                print(f"✅ Full bVOC run completed - output: {output_file}")
                return True
            else:
                print(f"❌ Full bVOC run completed but no output file: {output_file}")
                return False
        else:
            print("❌ Full bVOC run failed")
            return False
            
    except Exception as e:
        print(f"❌ Full bVOC run test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run bVOC tests"""
    
    print("🌿 UK bVOC Processing Tests")
    print("=" * 40)
    
    # Check if required libraries are available
    try:
        import numpy
        import rasterio
        import netCDF4
        import scipy
        print("✅ Required libraries available")
    except ImportError as e:
        print(f"❌ Missing required libraries: {e}")
        print("Please install: numpy, rasterio, netCDF4, scipy")
        sys.exit(1)
    
    # Test 1: bVOC input files
    test1_passed = test_bvoc_files()
    
    if not test1_passed:
        print("\n❌ Cannot proceed without bVOC input files")
        sys.exit(1)
    
    # Test 2: UK scenario processing
    test2_passed = test_uk_scenario_bvoc()
    
    # Test 3: Full run (only if previous tests passed)
    test3_passed = False
    if test1_passed and test2_passed:
        test3_passed = test_full_bvoc_run()
    
    # Summary
    print(f"\n📊 Test Results:")
    print(f"bVOC Files: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"UK Scenario: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    print(f"Full Run: {'✅ PASS' if test3_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed and test3_passed:
        print(f"\n🎉 All bVOC tests passed!")
        print(f"\nYou can now run bVOC processing:")
        print(f"  python run_bvoc_emissions.py")
        print(f"\nTo process different scenarios:")
        print(f"  python setup_uk_scenario.py <scenario_name>")
        print(f"  python run_bvoc_emissions.py")
        return True
    else:
        print(f"\n❌ Some bVOC tests failed. Check errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)