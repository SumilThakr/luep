#!/usr/bin/env python3
"""
Test dust emissions processing for UK scenarios

Saves results in: outputs/uk_results/scenario_name/dust_emissions.nc
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
import time
import shutil

# UK scenarios to test with (subset)
UK_SCENARIOS = [
    "extensification_current_practices",
    "forestry_expansion"
]

def setup_directories():
    """Create proper output directories following: outputs/uk_results/scenario/"""
    
    # Create proper directory structure
    results_dir = Path("outputs/uk_results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Results will be saved to: {results_dir.absolute()}")
    return results_dir

def run_scenario_setup(scenario_name):
    """Setup a UK scenario"""
    
    print(f"🌍 Setting up scenario: {scenario_name}")
    
    cmd = ["/Users/sumilthakrar/yes/envs/luep-analysis/bin/python", 
           "setup_uk_scenario.py", scenario_name]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  ❌ Failed to setup {scenario_name}")
        return False
    else:
        print(f"  ✅ Successfully setup {scenario_name}")
        return True

def run_dust_processing():
    """Run dust emissions processing"""
    
    print(f"  📊 Running dust emissions processing...")
    
    cmd = ["/Users/sumilthakrar/yes/envs/luep-analysis/bin/python", "run_dust_emissions.py"]
    
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    end_time = time.time()
    
    duration = end_time - start_time
    
    if result.returncode != 0:
        print(f"    ❌ Dust processing failed ({duration:.1f}s)")
        print(f"    Error: {result.stderr}")
        return False, duration
    else:
        print(f"    ✅ Dust processing completed ({duration:.1f}s)")
        return True, duration

def save_scenario_results(scenario_name, results_dir):
    """Save results with PROPER folder organization"""
    
    # Create scenario directory: outputs/uk_results/scenario_name/
    scenario_dir = results_dir / scenario_name
    scenario_dir.mkdir(exist_ok=True)
    
    # Move and rename files according to proper structure
    outputs_path = Path("outputs")
    saved_files = []
    
    if outputs_path.exists():
        for file_path in outputs_path.glob("*"):
            if file_path.is_file() and file_path.name != "txt":
                if "dust" in file_path.name:
                    # Rename to proper format: dust_emissions.nc (no scenario prefix)
                    if file_path.suffix == ".nc":
                        new_name = "dust_emissions.nc"
                    elif file_path.suffix == ".tif":
                        new_name = "dust_emissions.tif"
                    else:
                        continue
                    
                    target_path = scenario_dir / new_name
                    
                    # Move file
                    shutil.move(str(file_path), str(target_path))
                    saved_files.append(new_name)
                    print(f"      Saved: {scenario_name}/{new_name}")
    
    return len(saved_files)

def main():
    """Test dust processing for UK scenarios"""
    
    print("🧪 TESTING DUST EMISSIONS FOR UK SCENARIOS")
    print("=" * 50)
    print("Structure: outputs/uk_results/scenario_name/dust_emissions.nc")
    
    # Setup directories
    results_dir = setup_directories()
    
    for i, scenario in enumerate(UK_SCENARIOS, 1):
        
        print(f"\n{'='*50}")
        print(f"SCENARIO {i}/{len(UK_SCENARIOS)}: {scenario}")
        print(f"{'='*50}")
        
        # Setup scenario
        if not run_scenario_setup(scenario):
            continue
        
        # Run dust processing
        success, duration = run_dust_processing()
        
        if success:
            # Save results with proper organization
            num_files = save_scenario_results(scenario, results_dir)
            print(f"  📁 Saved {num_files} files to: outputs/uk_results/{scenario}/")
        else:
            print(f"  ❌ Processing failed")
    
    print(f"\n✅ Testing completed!")
    print(f"📁 Check structure: outputs/uk_results/")

if __name__ == "__main__":
    main()