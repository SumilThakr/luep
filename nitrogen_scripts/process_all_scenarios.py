#!/usr/bin/env python3
"""
Process All UK Scenarios for Nitrogen Emissions

This script processes all 15 UK scenarios to generate NH3 emissions and N application maps.

IMPORTANT: Run with the rasters conda environment:
/Users/sumilthakrar/yes/envs/rasters/bin/python nitrogen_scripts/process_all_scenarios.py
"""

import os
import sys
from pathlib import Path
import traceback

# Add the nitrogen_scripts directory to the path so we can import
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

from uk_scenario_emissions import process_scenario_map

def get_uk_scenarios():
    """
    Get list of all UK scenarios available
    
    Returns:
        list: Scenario names
    """
    scenarios = [
        "extensification_current_practices",
        "extensification_bmps_irrigated", 
        "extensification_bmps_rainfed",
        "extensification_intensified_irrigated",
        "extensification_intensified_rainfed",
        "fixedarea_bmps_irrigated",
        "fixedarea_bmps_rainfed",
        "fixedarea_intensified_irrigated",
        "fixedarea_intensified_rainfed",
        "forestry_expansion",
        "grazing_expansion",
        "restoration",
        "sustainable_current",
        "all_econ",
        "all_urban"
    ]
    
    return scenarios

def process_all_uk_scenarios():
    """
    Process all UK scenarios for nitrogen emissions mapping
    """
    
    scenarios = get_uk_scenarios()
    scenario_base_path = "scenarios/UKNatureFrontierWithAir/United Kingdom/ScenarioMaps"
    output_base_path = "outputs/uk_results"
    
    print("UK Nitrogen Emissions - Batch Processing")
    print("=" * 60)
    print(f"Processing {len(scenarios)} scenarios...")
    print()
    
    successful = []
    failed = []
    
    for i, scenario in enumerate(scenarios, 1):
        
        print(f"[{i}/{len(scenarios)}] Processing: {scenario}")
        print("-" * 50)
        
        # Define paths
        scenario_path = os.path.join(scenario_base_path, f"{scenario}.tif")
        output_dir = os.path.join(output_base_path, scenario)
        
        # Check if scenario file exists
        if not os.path.exists(scenario_path):
            print(f"  ❌ SKIP: Scenario file not found: {scenario_path}")
            failed.append((scenario, "File not found"))
            continue
        
        try:
            # Process scenario
            process_scenario_map(scenario_path, output_dir)
            print(f"  ✅ SUCCESS: {scenario}")
            successful.append(scenario)
            
        except Exception as e:
            print(f"  ❌ FAILED: {scenario}")
            print(f"     Error: {str(e)}")
            failed.append((scenario, str(e)))
            
            # Print traceback for debugging
            print("     Traceback:")
            traceback.print_exc()
        
        print()
    
    # Summary
    print("=" * 60)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Total scenarios: {len(scenarios)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print()
    
    if successful:
        print("✅ Successful scenarios:")
        for scenario in successful:
            print(f"   - {scenario}")
        print()
    
    if failed:
        print("❌ Failed scenarios:")
        for scenario, error in failed:
            print(f"   - {scenario}: {error}")
        print()
    
    # Generate overall summary file
    summary_path = os.path.join(output_base_path, "batch_processing_summary.txt")
    save_batch_summary(successful, failed, summary_path)
    print(f"Batch summary saved to: {summary_path}")

def save_batch_summary(successful, failed, output_path):
    """
    Save batch processing summary to file
    """
    
    from datetime import datetime
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write("UK Nitrogen Emissions - Batch Processing Summary\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Processing date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total scenarios: {len(successful) + len(failed)}\n")
        f.write(f"Successful: {len(successful)}\n")
        f.write(f"Failed: {len(failed)}\n\n")
        
        if successful:
            f.write("SUCCESSFUL SCENARIOS:\n")
            f.write("-" * 30 + "\n")
            for scenario in successful:
                f.write(f"✅ {scenario}\n")
                output_dir = f"outputs/uk_results/{scenario}"
                f.write(f"   Output directory: {output_dir}\n")
                f.write(f"   Files: nh3_emissions.nc, n_application.nc, nitrogen_summary.txt\n\n")
        
        if failed:
            f.write("FAILED SCENARIOS:\n")
            f.write("-" * 30 + "\n")
            for scenario, error in failed:
                f.write(f"❌ {scenario}\n")
                f.write(f"   Error: {error}\n\n")
        
        f.write("OUTPUT STRUCTURE:\n")
        f.write("-" * 30 + "\n")
        f.write("outputs/uk_results/{scenario}/\n")
        f.write("├── nh3_emissions.nc          # NH3 emissions (kg per pixel)\n")
        f.write("├── n_application.nc          # N for soil NOx module (kg per pixel)\n")
        f.write("└── nitrogen_summary.txt      # Summary statistics\n\n")
        
        f.write("EMISSION FACTORS USED:\n")
        f.write("-" * 30 + "\n")
        f.write("Cropland (ESA-CCI 10,20,30,etc): 18.23 kg NH3/ha, 211.67 kg N/ha\n")
        f.write("Pasture (ESA-CCI 130 only):      9.83 kg NH3/ha, 101.11 kg N/ha\n")
        f.write("All other land uses:             0.0 kg/ha (no emissions)\n\n")

def main():
    """
    Main function
    """
    
    if len(sys.argv) > 1 and sys.argv[1] == "--single":
        # Process single scenario for testing
        from uk_scenario_emissions import main as single_main
        single_main()
    else:
        # Process all scenarios
        process_all_uk_scenarios()

if __name__ == "__main__":
    main()