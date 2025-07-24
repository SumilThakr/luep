#!/usr/bin/env python3
"""
UK Soil NOx Emissions Batch Processing

This script processes all 15 UK scenarios to generate soil NOx emissions using
scenario-specific nitrogen application data.

IMPORTANT: Run with the rasters conda environment:
/Users/sumilthakrar/yes/envs/rasters/bin/python soil_nox_scripts/soil_nox_uk_scenarios.py
"""

import os
import sys
from pathlib import Path
import traceback
from datetime import datetime

# Add the soil_nox_scripts directory to the path so we can import
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

# Import the modified soil NOx modules
from soil_nox_3_constant_uk import run as run_constant_uk
from soil_nox_5_align_uk import run as run_align_uk

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

def run_prerequisites(inputdir):
    """
    Run prerequisite soil NOx processing steps (global data)
    
    These steps generate time-varying effects and land use reprojection
    that are shared across all scenarios.
    """
    print("Running prerequisite soil NOx processing steps...")
    print("=" * 60)
    
    try:
        # Import global soil NOx modules
        from soil_nox_scripts import soil_nox_1_time_varying
        from soil_nox_scripts import soil_nox_2_time_varying_sum  
        from soil_nox_scripts import soil_nox_4_gblulc
        
        print("Step 1: Calculating time-dependent parameters...")
        soil_nox_1_time_varying.run(inputdir)
        print("✅ Time-dependent parameters completed.\n")
        
        print("Step 2: Summing time-dependent parameters...")
        soil_nox_2_time_varying_sum.run(inputdir)
        print("✅ Time-dependent parameter summation completed.\n")
        
        print("Step 3: Reprojecting land use data...")
        soil_nox_4_gblulc.run(inputdir)
        print("✅ Land use reprojection completed.\n")
        
        print("Prerequisites completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error in prerequisites: {str(e)}")
        traceback.print_exc()
        return False

def process_single_scenario(scenario, inputdir, run_prerequisites_flag=True):
    """
    Process a single UK scenario for soil NOx emissions
    
    Args:
        scenario: Scenario name
        inputdir: Base input directory
        run_prerequisites_flag: Whether to run prerequisite steps
        
    Returns:
        bool: Success status
    """
    
    print(f"Processing scenario: {scenario}")
    print("-" * 50)
    
    # Define paths
    n_application_path = f"outputs/uk_results/{scenario}/n_application.nc"
    
    # Check if nitrogen application file exists
    if not os.path.exists(n_application_path):
        print(f"  ❌ SKIP: Nitrogen application file not found: {n_application_path}")
        return False
    
    try:
        # Step 1: Generate scenario-specific constant effects (including nitrogen)
        print(f"  Calculating constant effects with scenario nitrogen data...")
        run_constant_uk(inputdir, scenario_name=scenario, n_application_path=n_application_path)
        print(f"  ✅ Constant effects completed for {scenario}")
        
        # Step 2: Align and calculate final soil NOx emissions
        print(f"  Aligning and calculating soil NOx emissions...")
        nox_output = run_align_uk(inputdir, scenario_name=scenario)
        print(f"  ✅ Soil NOx calculation completed for {scenario}")
        print(f"     Output: {nox_output}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ FAILED: {scenario}")
        print(f"     Error: {str(e)}")
        traceback.print_exc()
        return False

def process_all_uk_scenarios(inputdir="inputs", run_prerequisites_flag=True):
    """
    Process all UK scenarios for soil NOx emissions
    
    Args:
        inputdir: Base input directory
        run_prerequisites_flag: Whether to run prerequisite steps
    """
    
    scenarios = get_uk_scenarios()
    
    print("UK Soil NOx Emissions - Batch Processing")
    print("=" * 60)
    print(f"Processing {len(scenarios)} scenarios...")
    print(f"Input directory: {inputdir}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run prerequisites if requested
    if run_prerequisites_flag:
        if not run_prerequisites(inputdir):
            print("❌ Prerequisites failed. Aborting batch processing.")
            return
        print()
    
    successful = []
    failed = []
    
    for i, scenario in enumerate(scenarios, 1):
        
        print(f"[{i}/{len(scenarios)}] Processing: {scenario}")
        print("=" * 60)
        
        success = process_single_scenario(scenario, inputdir, run_prerequisites_flag=False)
        
        if success:
            successful.append(scenario)
        else:
            failed.append(scenario)
        
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
        for scenario in failed:
            print(f"   - {scenario}")
        print()
    
    # Generate overall summary file
    summary_path = "outputs/uk_results/soil_nox_batch_summary.txt"
    save_batch_summary(successful, failed, summary_path)
    print(f"Batch summary saved to: {summary_path}")

def save_batch_summary(successful, failed, output_path):
    """
    Save batch processing summary to file
    """
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write("UK Soil NOx Emissions - Batch Processing Summary\n")
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
                f.write(f"   Files: nox_emissions.tif, soil_nox_summary.txt\n\n")
        
        if failed:
            f.write("FAILED SCENARIOS:\n")
            f.write("-" * 30 + "\n")
            for scenario in failed:
                f.write(f"❌ {scenario}\n\n")
        
        f.write("OUTPUT STRUCTURE:\n")
        f.write("-" * 30 + "\n")
        f.write("outputs/uk_results/{scenario}/\n")
        f.write("├── nh3_emissions.nc          # NH3 emissions (kg per pixel)\n")
        f.write("├── n_application.nc          # N application input (kg per pixel)\n")
        f.write("├── nox_emissions.tif         # NEW: Soil NOx emissions\n")
        f.write("└── soil_nox_summary.txt      # NEW: Summary statistics\n\n")
        
        f.write("SOIL NOx MODEL:\n")
        f.write("-" * 30 + "\n")
        f.write("Model: Yan et al. (2005) process-based soil NOx emissions\n")
        f.write("Equation: NOx = SOC × pH × exp(climate) × exp(-1.8327) × LU × exp(-0.11×T0) × TS_SM × N\n")
        f.write("Nitrogen effect: 1.0 + (0.03545 × N_rate × 122/365)\n")
        f.write("Key improvement: Scenario-specific nitrogen application instead of global uniform data\n\n")

def main():
    """
    Main function
    """
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--single":
            # Process single scenario for testing
            scenario = sys.argv[2] if len(sys.argv) > 2 else "extensification_current_practices"
            print(f"Processing single scenario: {scenario}")
            
            # Run prerequisites first
            if run_prerequisites("inputs"):
                success = process_single_scenario(scenario, "inputs", run_prerequisites_flag=False)
                if success:
                    print(f"✅ Single scenario processing completed: {scenario}")
                else:
                    print(f"❌ Single scenario processing failed: {scenario}")
            else:
                print("❌ Prerequisites failed. Cannot process scenario.")
        elif sys.argv[1] == "--no-prereq":
            # Skip prerequisites (useful if already run)
            process_all_uk_scenarios("inputs", run_prerequisites_flag=False)
        else:
            print("Usage:")
            print("  python soil_nox_uk_scenarios.py                    # Process all scenarios")
            print("  python soil_nox_uk_scenarios.py --single [name]    # Process single scenario")
            print("  python soil_nox_uk_scenarios.py --no-prereq        # Skip prerequisite steps")
    else:
        # Process all scenarios
        process_all_uk_scenarios("inputs")

if __name__ == "__main__":
    main()