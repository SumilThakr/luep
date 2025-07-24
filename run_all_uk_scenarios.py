#!/usr/bin/env python3
"""
Process all UK land use scenarios through all emission models

This script:
1. Iterates through all UK scenarios
2. Runs all emission models (dust, soil NOx, deposition, bVOC) for each scenario
3. Saves organized results
4. Creates summary reports

Usage:
    python run_all_uk_scenarios.py
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
import time

# Available UK scenarios
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

# Emission models to run
EMISSION_MODELS = [
    ("dust", "run_dust_emissions.py"),
    ("soil_nox", "run_soil_nox_emissions.py"), 
    ("deposition", "run_deposition_calculation.py"),
    ("bvoc", "run_bvoc_emissions.py")
]

def setup_directories():
    """Create organized output directories"""
    
    # Create main results directory
    results_dir = Path("uk_scenario_results")
    results_dir.mkdir(exist_ok=True)
    
    # Create subdirectories for each emission type
    for emission_type, _ in EMISSION_MODELS:
        (results_dir / emission_type).mkdir(exist_ok=True)
        
    # Create logs directory
    (results_dir / "logs").mkdir(exist_ok=True)
    
    return results_dir

def run_scenario_setup(scenario_name):
    """Setup a UK scenario"""
    
    print(f"\n{'='*60}")
    print(f"🌍 Setting up scenario: {scenario_name}")
    print(f"{'='*60}")
    
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

def run_emission_model(emission_type, script_name, scenario_name, results_dir):
    """Run a single emission model"""
    
    print(f"\n  📊 Running {emission_type} emissions...")
    
    cmd = ["/Users/sumilthakrar/yes/envs/luep-analysis/bin/python", script_name]
    
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    end_time = time.time()
    
    duration = end_time - start_time
    
    if result.returncode != 0:
        print(f"    ❌ {emission_type} failed ({duration:.1f}s)")
        print(f"    Error: {result.stderr}")
        return False, duration
    else:
        print(f"    ✅ {emission_type} completed ({duration:.1f}s)")
        
        # Move outputs to organized location
        move_outputs(emission_type, scenario_name, results_dir)
        return True, duration

def move_outputs(emission_type, scenario_name, results_dir):
    """Move outputs to organized directory structure"""
    
    # Define output file patterns for each emission type
    output_patterns = {
        "dust": ["outputs/*dust*.tif", "outputs/*dust*.nc"],
        "soil_nox": ["outputs/*nox*.tif", "outputs/*nox*.nc"],
        "deposition": ["outputs/*dep*.tif", "outputs/*dep*.nc"],
        "bvoc": ["outputs/*bvoc*.tif", "outputs/*bvoc*.nc"]
    }
    
    target_dir = results_dir / emission_type / scenario_name
    target_dir.mkdir(exist_ok=True)
    
    # Move outputs directory contents
    outputs_path = Path("outputs")
    if outputs_path.exists():
        for file_path in outputs_path.glob("*"):
            if file_path.is_file() and file_path.name != "txt":
                # Rename with scenario prefix
                new_name = f"{scenario_name}_{file_path.name}"
                target_path = target_dir / new_name
                
                # Copy file (don't move to avoid conflicts)
                import shutil
                shutil.copy2(file_path, target_path)
                print(f"      Saved: {target_path}")

def create_summary_report(results_dir, processing_log):
    """Create a summary report of all processing"""
    
    print(f"\n📋 Creating summary report...")
    
    report_path = results_dir / "processing_summary.txt"
    
    with open(report_path, 'w') as f:
        f.write("UK LAND USE SCENARIOS - EMISSIONS PROCESSING SUMMARY\n")
        f.write("=" * 60 + "\n")
        f.write(f"Processing completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Overall statistics
        total_scenarios = len(UK_SCENARIOS)
        total_models = len(EMISSION_MODELS)
        total_runs = total_scenarios * total_models
        
        f.write(f"Total scenarios processed: {total_scenarios}\n")
        f.write(f"Emission models per scenario: {total_models}\n")
        f.write(f"Total processing runs: {total_runs}\n\n")
        
        # Processing log
        f.write("DETAILED PROCESSING LOG\n")
        f.write("-" * 30 + "\n")
        
        for entry in processing_log:
            f.write(f"{entry}\n")
        
        # File structure
        f.write(f"\nOUTPUT FILE STRUCTURE\n")
        f.write("-" * 20 + "\n")
        f.write(f"uk_scenario_results/\n")
        for emission_type, _ in EMISSION_MODELS:
            f.write(f"  {emission_type}/\n")
            for scenario in UK_SCENARIOS:
                f.write(f"    {scenario}/\n")
                f.write(f"      {scenario}_*.tif\n")
                f.write(f"      {scenario}_*.nc\n")
        
    print(f"📄 Summary report saved: {report_path}")

def main():
    """Main processing loop"""
    
    print("🇬🇧 UK LAND USE SCENARIOS - EMISSIONS PROCESSING")
    print("=" * 60)
    print(f"Processing {len(UK_SCENARIOS)} scenarios with {len(EMISSION_MODELS)} emission models")
    print(f"Total runs: {len(UK_SCENARIOS) * len(EMISSION_MODELS)}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Setup directories
    results_dir = setup_directories()
    processing_log = []
    
    # Track overall progress
    total_runs = len(UK_SCENARIOS) * len(EMISSION_MODELS)
    completed_runs = 0
    start_time = time.time()
    
    # Process each scenario
    for i, scenario in enumerate(UK_SCENARIOS, 1):
        
        print(f"\n{'='*60}")
        print(f"SCENARIO {i}/{len(UK_SCENARIOS)}: {scenario}")
        print(f"{'='*60}")
        
        # Setup scenario
        if not run_scenario_setup(scenario):
            processing_log.append(f"FAILED SETUP: {scenario}")
            continue
            
        processing_log.append(f"SCENARIO: {scenario}")
        scenario_start = time.time()
        scenario_success = 0
        
        # Run all emission models for this scenario
        for emission_type, script_name in EMISSION_MODELS:
            
            success, duration = run_emission_model(emission_type, script_name, scenario, results_dir)
            completed_runs += 1
            
            # Log result
            status = "SUCCESS" if success else "FAILED"
            processing_log.append(f"  {emission_type}: {status} ({duration:.1f}s)")
            
            if success:
                scenario_success += 1
            
            # Progress update
            elapsed = time.time() - start_time
            avg_time = elapsed / completed_runs if completed_runs > 0 else 0
            remaining = total_runs - completed_runs
            eta = avg_time * remaining
            
            print(f"\n    Progress: {completed_runs}/{total_runs} ({completed_runs/total_runs*100:.1f}%)")
            print(f"    ETA: {eta/60:.1f} minutes")
        
        # Scenario summary
        scenario_duration = time.time() - scenario_start
        print(f"\n  📊 Scenario {scenario} completed:")
        print(f"    Success: {scenario_success}/{len(EMISSION_MODELS)} models")
        print(f"    Duration: {scenario_duration/60:.1f} minutes")
        
        processing_log.append(f"  SCENARIO TOTAL: {scenario_success}/{len(EMISSION_MODELS)} models, {scenario_duration:.1f}s")
        processing_log.append("")
    
    # Final summary
    total_duration = time.time() - start_time
    
    print(f"\n🎉 ALL PROCESSING COMPLETED!")
    print(f"📊 Total duration: {total_duration/60:.1f} minutes")
    print(f"📁 Results saved in: {results_dir.absolute()}")
    
    # Create summary report
    processing_log.append(f"TOTAL PROCESSING TIME: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    create_summary_report(results_dir, processing_log)
    
    # Restore global setup
    print(f"\n🔄 Restoring global setup...")
    try:
        subprocess.run(["/Users/sumilthakrar/yes/envs/luep-analysis/bin/python", 
                       "restore_global_setup.py"], check=True)
        print(f"✅ Global setup restored")
    except subprocess.CalledProcessError:
        print(f"⚠️  Failed to restore global setup")

if __name__ == "__main__":
    main()