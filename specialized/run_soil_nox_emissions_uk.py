#!/usr/bin/env python3
"""
UK Soil NOx Emissions Processing

Main script to run soil NOx emissions calculations for UK scenarios using
scenario-specific nitrogen application data.

This script integrates the existing Yan et al. (2005) soil NOx model with
our UK nitrogen application maps to generate land-use-dependent soil NOx emissions.

Usage:
    python run_soil_nox_emissions_uk.py                    # Process all UK scenarios
    python run_soil_nox_emissions_uk.py --single [name]    # Process single scenario
    python run_soil_nox_emissions_uk.py --no-prereq        # Skip prerequisite steps

Important: Run with the rasters conda environment:
    /Users/sumilthakrar/yes/envs/rasters/bin/python run_soil_nox_emissions_uk.py
"""

import sys
import os
from pathlib import Path

# Add the soil_nox_scripts directory to the path
sys.path.append('soil_nox_scripts')

from soil_nox_uk_scenarios import main as run_uk_scenarios

def print_header():
    """Print header information"""
    print("=" * 80)
    print("UK SOIL NOx EMISSIONS PROCESSING")
    print("=" * 80)
    print()
    print("This script generates soil NOx emissions for UK land use scenarios using:")
    print("• Yan et al. (2005) process-based soil NOx model")
    print("• Scenario-specific nitrogen application data")
    print("• UK-specific land use and agricultural patterns")
    print()
    print("Key model equation:")
    print("NOx = SOC × pH × exp(climate) × exp(-1.8327) × LU × exp(-0.11×T0) × TS_SM × N")
    print()
    print("Where N effect = 1.0 + (0.03545 × N_rate × 122/365)")
    print("N_rate comes from scenario-specific nitrogen application maps")
    print()
    print("=" * 80)
    print()

def check_prerequisites():
    """Check that required input files and nitrogen data exist"""
    print("Checking prerequisites...")
    
    # Check that nitrogen application data exists for UK scenarios
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
    
    missing_scenarios = []
    for scenario in scenarios:
        n_app_path = f"outputs/uk_results/{scenario}/n_application.nc"
        if not os.path.exists(n_app_path):
            missing_scenarios.append(scenario)
    
    if missing_scenarios:
        print("❌ Missing nitrogen application data for scenarios:")
        for scenario in missing_scenarios:
            print(f"   - {scenario}")
        print()
        print("Please run the nitrogen emissions mapping first:")
        print("   /Users/sumilthakrar/yes/envs/rasters/bin/python nitrogen_scripts/process_all_scenarios.py")
        print()
        return False
    
    # Check basic soil NOx input files
    required_files = [
        "inputs/T_PH_H2O.tiff",
        "inputs/T_OC.tiff", 
        "inputs/Beck_KG_V1_present_0p5.tif",
        "inputs/gblulcg20_10000.tif",
        "inputs/LAI/out_sum.tiff"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required soil NOx input files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        print()
        return False
    
    print("✅ All prerequisites satisfied!")
    print(f"✅ Found nitrogen data for {len(scenarios) - len(missing_scenarios)}/{len(scenarios)} scenarios")
    print()
    return True

def main():
    """Main function"""
    
    print_header()
    
    # Check prerequisites
    if not check_prerequisites():
        print("❌ Prerequisites not met. Exiting.")
        sys.exit(1)
    
    print("Starting UK soil NOx emissions processing...")
    print()
    
    # Pass through command line arguments to the scenario processor
    run_uk_scenarios()

if __name__ == "__main__":
    main()