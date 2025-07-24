#!/usr/bin/env python3
"""
Test processing with just a few scenarios first
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
import time

# Test with just 3 scenarios
TEST_SCENARIOS = [
    "extensification_current_practices",  # Already tested
    "forestry_expansion",                 # Forest-heavy
    "sustainable_current"                 # Mixed
]

# All emission models
EMISSION_MODELS = [
    ("dust", "run_dust_emissions.py"),
    ("soil_nox", "run_soil_nox_emissions.py"), 
    ("deposition", "run_deposition_calculation.py"),
    ("bvoc", "run_bvoc_emissions.py")
]

def run_scenario_setup(scenario_name):
    """Setup a UK scenario"""
    
    print(f"\n🌍 Setting up scenario: {scenario_name}")
    
    cmd = ["/Users/sumilthakrar/yes/envs/luep-analysis/bin/python", 
           "setup_uk_scenario.py", scenario_name]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Failed to setup {scenario_name}")
        print(f"Error: {result.stderr}")
        return False
    else:
        print(f"✅ Successfully setup {scenario_name}")
        return True

def run_emission_model(emission_type, script_name):
    """Run a single emission model"""
    
    print(f"  📊 Running {emission_type} emissions...")
    
    cmd = ["/Users/sumilthakrar/yes/envs/luep-analysis/bin/python", script_name]
    
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    end_time = time.time()
    
    duration = end_time - start_time
    
    if result.returncode != 0:
        print(f"    ❌ {emission_type} failed ({duration:.1f}s)")
        print(f"    Error: {result.stderr[:200]}...")  # First 200 chars
        return False, duration
    else:
        print(f"    ✅ {emission_type} completed ({duration:.1f}s)")
        return True, duration

def main():
    """Test processing"""
    
    print("🧪 TESTING UK SCENARIOS PROCESSING")
    print("=" * 50)
    print(f"Testing {len(TEST_SCENARIOS)} scenarios with {len(EMISSION_MODELS)} emission models")
    
    start_time = time.time()
    
    for i, scenario in enumerate(TEST_SCENARIOS, 1):
        
        print(f"\n{'='*50}")
        print(f"TEST SCENARIO {i}/{len(TEST_SCENARIOS)}: {scenario}")
        print(f"{'='*50}")
        
        # Setup scenario
        if not run_scenario_setup(scenario):
            print(f"❌ Skipping {scenario} due to setup failure")
            continue
        
        scenario_start = time.time()
        scenario_success = 0
        
        # Run all emission models for this scenario
        for emission_type, script_name in EMISSION_MODELS:
            
            success, duration = run_emission_model(emission_type, script_name)
            
            if success:
                scenario_success += 1
        
        # Scenario summary
        scenario_duration = time.time() - scenario_start
        print(f"\n  📊 Scenario {scenario} results:")
        print(f"    Success: {scenario_success}/{len(EMISSION_MODELS)} models")
        print(f"    Duration: {scenario_duration/60:.1f} minutes")
    
    # Final summary
    total_duration = time.time() - start_time
    
    print(f"\n🎉 TEST PROCESSING COMPLETED!")
    print(f"📊 Total duration: {total_duration/60:.1f} minutes")
    
    # Check what outputs we have
    outputs_path = Path("outputs")
    if outputs_path.exists():
        output_files = list(outputs_path.glob("*"))
        print(f"📁 Output files: {len(output_files)}")
        for f in output_files[:5]:  # Show first 5
            print(f"    {f.name}")
        if len(output_files) > 5:
            print(f"    ... and {len(output_files)-5} more")

if __name__ == "__main__":
    main()