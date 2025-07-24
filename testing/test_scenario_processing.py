#!/usr/bin/env python3
"""
Test script for UK scenario processing
Tests ESA CCI to Simple conversion with a single scenario
"""

import sys
from pathlib import Path

# Test the ESA conversion first
def test_esa_conversion():
    """Test ESA CCI to Simple classification conversion"""
    
    print("🧪 Testing ESA CCI to Simple conversion...")
    
    # Use first available scenario
    scenarios_dir = Path("scenarios/UKNatureFrontierWithAir/United Kingdom/ScenarioMaps")
    scenario_files = list(scenarios_dir.glob("*.tif"))
    
    if not scenario_files:
        print("❌ No scenario files found")
        return False
    
    # Test with first scenario
    test_scenario = scenario_files[0]
    output_dir = Path("test_outputs")
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"{test_scenario.stem}_simple_test.tif"
    
    print(f"Input scenario: {test_scenario.name}")
    print(f"Output file: {output_file}")
    
    try:
        # Import and run conversion
        from scenario_scripts.esa_to_simple_converter import convert_esa_to_simple, verify_conversion
        
        # Convert
        convert_esa_to_simple(test_scenario, output_file)
        
        # Verify
        success = verify_conversion(test_scenario, output_file)
        
        if success:
            print("✅ ESA conversion test PASSED")
            return True
        else:
            print("❌ ESA conversion test FAILED")
            return False
            
    except Exception as e:
        print(f"❌ ESA conversion test ERROR: {e}")
        return False

def test_preprocessing():
    """Test scenario preprocessing"""
    
    print("\n🧪 Testing scenario preprocessing...")
    
    scenarios_dir = Path("scenarios/UKNatureFrontierWithAir/United Kingdom/ScenarioMaps")
    scenario_files = list(scenarios_dir.glob("*.tif"))
    
    if not scenario_files:
        print("❌ No scenario files found")
        return False
    
    test_scenario = scenario_files[0]
    output_dir = Path("test_outputs/preprocessing")
    
    print(f"Testing with: {test_scenario.name}")
    
    try:
        from scenario_scripts.uk_scenario_preprocessor import preprocess_uk_scenario
        
        result = preprocess_uk_scenario(
            test_scenario,
            output_dir,
            f"test_{test_scenario.stem}",
            baseline_lulc_path=None  # Skip global embedding for test
        )
        
        print("✅ Preprocessing test PASSED")
        print("Generated files:")
        for key, path in result.items():
            print(f"  {key}: {Path(path).name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Preprocessing test ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run tests"""
    
    print("🌍 UK Scenario Processing Tests")
    print("=" * 40)
    
    # Check if conda environment is active
    try:
        import numpy
        import rasterio
        print("✅ Required libraries available")
    except ImportError as e:
        print(f"❌ Missing required libraries: {e}")
        print("Please run with: conda activate luep-analysis")
        sys.exit(1)
    
    # Test 1: ESA conversion
    test1_passed = test_esa_conversion()
    
    # Test 2: Preprocessing (only if test 1 passed)
    if test1_passed:
        test2_passed = test_preprocessing()
    else:
        test2_passed = False
    
    # Summary
    print(f"\n📊 Test Results:")
    print(f"ESA Conversion: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"Preprocessing: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print(f"\n🎉 All tests passed! Ready for full scenario processing.")
        return True
    else:
        print(f"\n❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)