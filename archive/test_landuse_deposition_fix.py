#!/usr/bin/env python3
"""
Test the land-use-specific deposition fix on key UK scenarios

This script tests the new land-use-specific deposition velocity system on:
1. forestry_expansion (should have high forest deposition)
2. grazing_expansion (should have high grass deposition) 
3. all_urban (should have very low deposition)

Usage:
    /Users/sumilthakrar/yes/envs/rasters/bin/python test_landuse_deposition_fix.py
"""

import sys
import os
import subprocess
from dep_scripts import dep_2_lai_month_avg_esa_cci, dep_4_multiply_landuse_simple

def setup_scenario(scenario_name):
    """Set up a UK scenario for processing"""
    print(f"\n🌍 Setting up scenario: {scenario_name}")
    print("-" * 50)
    
    result = subprocess.run([
        "/Users/sumilthakrar/yes/envs/rasters/bin/python", 
        "setup_uk_scenario.py", 
        scenario_name
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ Scenario {scenario_name} setup completed")
        return True
    else:
        print(f"❌ Failed to setup scenario {scenario_name}")
        print(f"Error: {result.stderr}")
        return False

def run_deposition_calculation():
    """Run the land-use-specific deposition calculation"""
    print("   Running LAI calculation...")
    dep_2_lai_month_avg_esa_cci.run("")
    
    print("   Running land-use-specific deposition calculation...")
    results = dep_4_multiply_landuse_simple.run("")
    
    return results

def main():
    print("=" * 80)
    print("TESTING LAND-USE-SPECIFIC DEPOSITION FIX")
    print("=" * 80)
    print()
    print("This test will verify that the land-use-specific velocity scaling fixes")
    print("the forest vs grass deposition issue across different UK scenarios.")
    print()
    
    # Test scenarios that should show different patterns
    test_scenarios = [
        "forestry_expansion",    # Should have high forest deposition
        "grazing_expansion",     # Should have high grass deposition  
        "all_urban"             # Should have very low total deposition
    ]
    
    results = {}
    
    for scenario in test_scenarios:
        print(f"\n{'='*60}")
        print(f"TESTING SCENARIO: {scenario.upper()}")
        print(f"{'='*60}")
        
        # Setup scenario
        if not setup_scenario(scenario):
            print(f"❌ Skipping {scenario} due to setup failure")
            continue
            
        try:
            # Run deposition calculation
            result = run_deposition_calculation()
            
            if result:
                results[scenario] = result
                print(f"\n✅ {scenario} completed successfully!")
                print(f"   Total deposition: {result['total_deposition']:,.0f} kg/year")
                print(f"   Max deposition: {result['max_deposition']:.2f} kg/year")
                print(f"   Mean deposition: {result['mean_deposition']:.2f} kg/year")
            else:
                print(f"❌ {scenario} calculation failed")
                
        except Exception as e:
            print(f"❌ Error processing {scenario}: {e}")
            continue
    
    # Summary comparison
    if results:
        print(f"\n{'='*80}")
        print("SUMMARY - LAND-USE-SPECIFIC DEPOSITION RESULTS")
        print(f"{'='*80}")
        print()
        print("Scenario                    Total Deposition (kg/year)")
        print("-" * 60)
        
        sorted_results = sorted(results.items(), key=lambda x: x[1]['total_deposition'], reverse=True)
        
        for scenario, result in sorted_results:
            print(f"{scenario:<25} {result['total_deposition']:>15,.0f}")
        
        print()
        print("EXPECTED PATTERNS:")
        print("- forestry_expansion should rank high (lots of forest)")
        print("- grazing_expansion should rank medium (lots of grass at 50% velocity)")  
        print("- all_urban should rank lowest (urban areas at 25% velocity)")
        print()
        
        # Check if patterns are correct
        forest_total = results.get('forestry_expansion', {}).get('total_deposition', 0)
        grass_total = results.get('grazing_expansion', {}).get('total_deposition', 0)
        urban_total = results.get('all_urban', {}).get('total_deposition', 0)
        
        print("PATTERN VERIFICATION:")
        if forest_total > grass_total:
            print("✅ forestry_expansion > grazing_expansion (CORRECT)")
        else:
            print("❌ forestry_expansion < grazing_expansion (INCORRECT)")
            
        if grass_total > urban_total:
            print("✅ grazing_expansion > all_urban (CORRECT)")
        else:
            print("❌ grazing_expansion < all_urban (INCORRECT)")
            
        if forest_total > urban_total:
            print("✅ forestry_expansion > all_urban (CORRECT)")
        else:
            print("❌ forestry_expansion < all_urban (INCORRECT)")
        
        print()
        print("🎉 Land-use-specific deposition fix testing completed!")
        
        if forest_total > grass_total and grass_total > urban_total:
            print("✅ ALL PATTERNS CORRECT - Fix is working!")
            return 0
        else:
            print("❌ Some patterns still incorrect - needs further investigation")
            return 1
    else:
        print("❌ No scenarios completed successfully")
        return 1

if __name__ == "__main__":
    sys.exit(main())