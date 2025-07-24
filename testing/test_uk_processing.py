#!/usr/bin/env python3
"""
Test UK-only processing with a single scenario

This script:
1. Sets up one UK scenario
2. Tests that the setup works correctly
3. Optionally runs a quick test of one emission module
"""

import sys
from pathlib import Path

def test_setup():
    """Test the UK setup process"""
    
    print("🧪 Testing UK scenario setup...")
    
    # Get first available scenario
    scenarios_dir = Path("scenarios/UKNatureFrontierWithAir/United Kingdom/ScenarioMaps")
    scenario_files = list(scenarios_dir.glob("*.tif"))
    
    if not scenario_files:
        print("❌ No scenario files found")
        return False
    
    test_scenario = scenario_files[0]  # Use first scenario for testing
    print(f"Testing with: {test_scenario.name}")
    
    try:
        # Import required modules
        from scenario_scripts.uk_processing_setup import setup_uk_processing_environment, verify_uk_setup
        
        print("\n1. Setting up UK processing environment...")
        result = setup_uk_processing_environment(test_scenario, backup_originals=True)
        
        print("\n2. Verifying setup...")
        success = verify_uk_setup()
        
        if success:
            print("✅ UK setup test PASSED")
            return True
        else:
            print("❌ UK setup test FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Setup test ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dust_preprocessing():
    """Test just the preprocessing part of dust emissions"""
    
    print("\n🧪 Testing dust emissions preprocessing...")
    
    try:
        # Import dust module
        from dust_scripts import dust_1_soil_texture
        
        print("Running dust soil texture preprocessing...")
        dust_1_soil_texture.run("inputs")
        
        # Check if output was created
        soil_texture_output = Path("intermediate/soil_texture.tif")
        if soil_texture_output.exists():
            print(f"✅ Dust preprocessing test PASSED")
            print(f"   Created: {soil_texture_output}")
            return True
        else:
            print(f"❌ Dust preprocessing test FAILED - no output created")
            return False
            
    except Exception as e:
        print(f"❌ Dust preprocessing test ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run tests"""
    
    print("🌍 UK Processing Tests")
    print("=" * 30)
    
    # Check if required libraries are available
    try:
        import numpy
        import rasterio
        import pygeoprocessing.geoprocessing as geop
        print("✅ Required libraries available")
    except ImportError as e:
        print(f"❌ Missing required libraries: {e}")
        print("Please run with conda environment: conda activate luep-analysis")
        sys.exit(1)
    
    # Test 1: Setup
    test1_passed = test_setup()
    
    # Test 2: Preprocessing (only if setup passed)
    if test1_passed:
        test2_passed = test_dust_preprocessing()
    else:
        test2_passed = False
    
    # Summary
    print(f"\n📊 Test Results:")
    print(f"UK Setup: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"Dust Preprocessing: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print(f"\n🎉 All tests passed!")
        print(f"\nYou can now run full emissions processing:")
        print(f"  python run_dust_emissions.py")
        print(f"  python run_soil_nox_emissions.py")
        print(f"  python run_deposition_calculation.py")
        print(f"\nTo restore global setup: python restore_global_setup.py")
        return True
    else:
        print(f"\n❌ Some tests failed. Check errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)