#!/usr/bin/env python3
"""
Test Multi-Scenario UK Deposition Processing

Quick test script to process a few UK scenarios for validation before running
the full batch processing.

Usage:
    python test_multi_scenarios.py

This will process 3 representative scenarios:
- sustainable_current (already done)
- forestry_expansion  
- all_urban

Important: Run with the rasters conda environment:
    /Users/sumilthakrar/yes/envs/rasters/bin/python test_multi_scenarios.py
"""

import sys
import os
import subprocess
from datetime import datetime
import time

def main():
    print("=" * 60)
    print("TESTING MULTI-SCENARIO UK DEPOSITION PROCESSING")
    print("=" * 60)
    print()
    
    # Test scenarios - representative sample
    test_scenarios = [
        "sustainable_current",  # Already processed
        "forestry_expansion",   # Forest scenario
        "all_urban"            # Urban scenario
    ]
    
    print(f"Testing {len(test_scenarios)} representative scenarios:")
    for scenario in test_scenarios:
        print(f"  - {scenario}")
    print()
    
    start_time = datetime.now()
    
    for i, scenario in enumerate(test_scenarios):
        print(f"[{i+1}/{len(test_scenarios)}] Processing: {scenario}")
        print("-" * 40)
        
        scenario_start = time.time()
        
        try:
            # Check if already processed
            result_file = f"outputs/uk_results/{scenario}/pm25_deposition.nc"
            if os.path.exists(result_file):
                print(f"   ✅ {scenario} already processed - skipping")
                continue
            
            # Run the UK deposition processing for this scenario
            result = subprocess.run([
                "/Users/sumilthakrar/yes/envs/rasters/bin/python", 
                "run_deposition_uk_scenario.py", 
                scenario
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                scenario_time = time.time() - scenario_start
                print(f"   ✅ {scenario} completed in {scenario_time:.1f} seconds")
                
                # Quick result check
                if os.path.exists(result_file):
                    file_size = os.path.getsize(result_file)
                    print(f"   📁 Output: {file_size/1024/1024:.1f} MB")
                else:
                    print(f"   ⚠️  Output file not found: {result_file}")
            else:
                print(f"   ❌ {scenario} failed:")
                print(f"      {result.stderr}")
        
        except Exception as e:
            print(f"   ❌ Error processing {scenario}: {e}")
        
        print()
    
    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds() / 60
    
    print("=" * 60)
    print(f"Test completed in {total_time:.1f} minutes")
    
    # Quick comparison
    print()
    print("Quick Results Comparison:")
    for scenario in test_scenarios:
        result_file = f"outputs/uk_results/{scenario}/pm25_deposition.nc"
        if os.path.exists(result_file):
            try:
                import xarray as xr
                with xr.open_dataset(result_file) as ds:
                    total_dep = float(ds['annual_PM2.5_deposition'].sum().values)
                    print(f"  {scenario:<25}: {total_dep:>12,.0f} kg/year")
            except:
                print(f"  {scenario:<25}: Error reading results")
        else:
            print(f"  {scenario:<25}: Not processed")
    
    print()
    print("✅ Multi-scenario test complete!")
    print("Ready to run full batch processing with:")
    print("   /Users/sumilthakrar/yes/envs/rasters/bin/python process_all_uk_deposition.py")

if __name__ == "__main__":
    main()