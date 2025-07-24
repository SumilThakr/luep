#!/usr/bin/env python3
"""
OPTIMIZED dust emissions processing for UK scenarios
Meteorology processed once for full year 2021, land use effects per scenario

Saves results in: outputs/uk_results/scenario_name/dust_emissions.tif
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
import time
import shutil

# All UK scenarios
UK_SCENARIOS = [
    "all_econ",
    "all_urban", 
    "extensification_bmps_irrigated",
    "extensification_bmps_rainfed",
    "extensification_current_practices",
    "extensification_intensified_irrigated",
    "extensification_intensified_rainfed",
    "fixedarea_bmps_irrigated",
    "fixedarea_bmps_rainfed",
    "fixedarea_intensified_irrigated",
    "fixedarea_intensified_rainfed",
    "forestry_expansion",
    "grazing_expansion",
    "restoration",
    "sustainable_current"
]

def setup_directories():
    """Create proper output directories"""
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
    """Run OPTIMIZED dust emissions processing"""
    print(f"  📊 Running OPTIMIZED dust emissions processing...")
    
    # Check optimization status
    soil_texture_exists = os.path.exists("intermediate/soil_texture.tif")
    meteorology_exists = os.path.exists("intermediate/daily_meteorology") and \
                        len(os.listdir("intermediate/daily_meteorology")) > 700
    
    if soil_texture_exists:
        print(f"    ♻️  Reusing soil texture (land-use independent)")
    else:
        print(f"    🔧 Creating soil texture (one-time setup)")
        
    if meteorology_exists:
        print(f"    ♻️  Reusing meteorology for full year 2021 (land-use independent)")
    else:
        print(f"    🌦️  Processing meteorology for full year 2021 (one-time setup)")
    
    cmd = ["/Users/sumilthakrar/yes/envs/luep-analysis/bin/python", "run_dust_emissions_split.py"]
    
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
    """Save results with proper folder organization"""
    scenario_dir = results_dir / scenario_name
    scenario_dir.mkdir(exist_ok=True)
    
    outputs_path = Path("outputs")
    saved_files = []
    
    if outputs_path.exists():
        for file_path in outputs_path.glob("*"):
            if file_path.is_file() and file_path.name != "txt":
                if "dust" in file_path.name:
                    if file_path.suffix == ".tiff":
                        new_name = "dust_emissions.tif"
                        target_path = scenario_dir / new_name
                        shutil.move(str(file_path), str(target_path))
                        saved_files.append(new_name)
                        print(f"      Saved: {scenario_name}/{new_name}")
    
    return len(saved_files)

def main():
    """Process dust emissions for UK scenarios with MAXIMUM optimization"""
    
    print("🚀 MAXIMUM OPTIMIZATION: DUST EMISSIONS FOR UK SCENARIOS")
    print("=" * 70)
    print("OPTIMIZATIONS:")
    print("  🔧 Soil texture: Created once, reused for all scenarios")
    print("  🌦️  Meteorology: Full year 2021 processed once, reused for all scenarios")
    print("  🌱 Land use effects: Calculated per scenario (FDTF + surface roughness)")
    print("  📅 Date range: Full year 2021 (365 days vs previous 243 days)")
    print("Structure: outputs/uk_results/scenario_name/dust_emissions.tif")
    
    results_dir = setup_directories()
    
    total_start_time = time.time()
    successful_scenarios = 0
    
    for i, scenario in enumerate(UK_SCENARIOS, 1):
        print(f"\n{'='*60}")
        print(f"SCENARIO {i}/{len(UK_SCENARIOS)}: {scenario}")
        print(f"{'='*60}")
        
        if not run_scenario_setup(scenario):
            continue
        
        success, duration = run_dust_processing()
        
        if success:
            num_files = save_scenario_results(scenario, results_dir)
            print(f"  📁 Saved {num_files} files to: outputs/uk_results/{scenario}/")
            successful_scenarios += 1
        else:
            print(f"  ❌ Processing failed")
    
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    print(f"\n🎉 OPTIMIZATION RESULTS:")
    print(f"  ✅ Successful scenarios: {successful_scenarios}/{len(UK_SCENARIOS)}")
    print(f"  ⏱️  Total processing time: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    print(f"  📁 Check results: outputs/uk_results/")
    print(f"  🚀 Subsequent scenarios will be MUCH faster (meteorology pre-processed)")

if __name__ == "__main__":
    main()