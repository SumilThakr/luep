#!/usr/bin/env python3
"""
Create All UK Scenario Difference Plots

This script generates difference plots for all combinations of scenarios 
and emission types, comparing against the "sustainable current" baseline.

Usage:
    python create_all_scenario_plots.py
"""

import subprocess
import sys
from pathlib import Path
import time

def run_plot_script(scenario_name, emission_type):
    """
    Run the plotting script for a specific scenario and emission type
    
    Args:
        scenario_name: Name of scenario
        emission_type: Type of emission
        
    Returns:
        bool: True if successful, False if failed
    """
    
    print(f"\n🎨 Creating plot: {scenario_name} - {emission_type}")
    
    cmd = [
        '/Users/sumilthakrar/yes/envs/rasters/bin/python',
        'plotting_scripts/plot_scenario_difference.py',
        scenario_name,
        emission_type
    ]
    
    try:
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"  ✅ Success ({duration:.1f}s)")
            return True
        else:
            print(f"  ❌ Failed ({duration:.1f}s)")
            print(f"  Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  ❌ Timeout (>300s)")
        return False
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return False

def main():
    """Main function to create all plots"""
    
    print("🇬🇧 UK SCENARIO DIFFERENCE PLOTS - BATCH CREATION")
    print("=" * 60)
    
    # Define scenarios and emission types
    scenarios = [
        "grazing_expansion",
        "forestry_expansion"
    ]
    
    emission_types = [
        "dust_sum",
        "pm25_deposition", 
        "nox_emissions",
        "nh3_emissions",
        "bvoc_emissions"
    ]
    
    baseline = "sustainable_current"
    
    print(f"Scenarios to process: {scenarios}")
    print(f"Emission types: {emission_types}")
    print(f"Baseline: {baseline}")
    print(f"Total plots to create: {len(scenarios)} × {len(emission_types)} = {len(scenarios) * len(emission_types)}")
    
    # Verify baseline exists
    baseline_path = Path("outputs/uk_results") / baseline
    if not baseline_path.exists():
        print(f"❌ Baseline directory not found: {baseline_path}")
        print("   Please ensure 'sustainable_current' scenario has been processed.")
        sys.exit(1)
    
    # Verify scenario directories exist
    for scenario in scenarios:
        scenario_path = Path("outputs/uk_results") / scenario
        if not scenario_path.exists():
            print(f"❌ Scenario directory not found: {scenario_path}")
            print(f"   Please ensure '{scenario}' scenario has been processed.")
            sys.exit(1)
    
    # Create plots directory
    plots_dir = Path("outputs/uk_results/plots")
    plots_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Plots will be saved to: {plots_dir.absolute()}")
    
    # Track progress
    total_plots = len(scenarios) * len(emission_types)
    successful_plots = 0
    failed_plots = []
    
    start_time = time.time()
    
    # Create all plots
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'='*60}")
        print(f"SCENARIO {i}/{len(scenarios)}: {scenario}")
        print(f"{'='*60}")
        
        for j, emission_type in enumerate(emission_types, 1):
            plot_num = (i-1) * len(emission_types) + j
            print(f"\n📊 Plot {plot_num}/{total_plots}: {scenario} - {emission_type}")
            
            success = run_plot_script(scenario, emission_type)
            
            if success:
                successful_plots += 1
            else:
                failed_plots.append((scenario, emission_type))
    
    # Final summary
    total_duration = time.time() - start_time
    
    print(f"\n{'='*60}")
    print("🎯 BATCH PLOTTING COMPLETE")
    print(f"{'='*60}")
    print(f"✅ Successful plots: {successful_plots}/{total_plots}")
    print(f"❌ Failed plots: {len(failed_plots)}/{total_plots}")
    print(f"⏱️  Total duration: {total_duration/60:.1f} minutes")
    print(f"📁 All plots saved in: {plots_dir.absolute()}")
    
    if failed_plots:
        print(f"\nFailed plots:")
        for scenario, emission_type in failed_plots:
            print(f"  ❌ {scenario} - {emission_type}")
    
    # List created files
    if successful_plots > 0:
        print(f"\nCreated plots:")
        for plot_file in sorted(plots_dir.glob("*.png")):
            file_size = plot_file.stat().st_size / 1024  # KB
            print(f"  📄 {plot_file.name} ({file_size:.1f} KB)")
    
    print(f"\n🌿 Batch plotting complete!")

if __name__ == "__main__":
    main()