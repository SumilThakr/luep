#!/usr/bin/env python3
"""
Process All UK Scenarios for Soil NOx Emissions

This script processes all 15 UK scenarios using the simplified soil NOx approach
that integrates scenario-specific nitrogen application data.

IMPORTANT: Run with the rasters conda environment:
/Users/sumilthakrar/yes/envs/rasters/bin/python process_all_uk_soil_nox.py
"""

import os
import sys
import traceback
from datetime import datetime

# Add the soil_nox_scripts directory to the path
sys.path.append('soil_nox_scripts')

from soil_nox_uk_simplified import process_uk_scenario_simplified

def get_uk_scenarios():
    """Get list of all UK scenarios"""
    return [
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

def process_all_scenarios():
    """Process all UK scenarios for soil NOx emissions"""
    
    scenarios = get_uk_scenarios()
    
    print("UK Soil NOx Emissions - Batch Processing")
    print("=" * 60)
    print("Using simplified approach with scenario-specific nitrogen data")
    print(f"Processing {len(scenarios)} scenarios...")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    successful = []
    failed = []
    
    for i, scenario in enumerate(scenarios, 1):
        
        print(f"[{i}/{len(scenarios)}] Processing: {scenario}")
        print("=" * 60)
        
        try:
            success = process_uk_scenario_simplified(scenario, "inputs")
            
            if success:
                successful.append(scenario)
                print(f"✅ SUCCESS: {scenario}")
            else:
                failed.append(scenario)
                print(f"❌ FAILED: {scenario}")
                
        except Exception as e:
            failed.append(scenario)
            print(f"❌ FAILED: {scenario}")
            print(f"   Error: {str(e)}")
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
        for scenario in failed:
            print(f"   - {scenario}")
        print()
    
    # Generate overall summary file
    summary_path = "outputs/uk_results/soil_nox_batch_summary.txt"
    save_batch_summary(successful, failed, summary_path)
    print(f"Batch summary saved to: {summary_path}")

def save_batch_summary(successful, failed, output_path):
    """Save batch processing summary to file"""
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write("UK Soil NOx Emissions - Batch Processing Summary\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Processing date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Processing method: Simplified with scenario-specific nitrogen data\n")
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
                f.write(f"   New files: nox_emissions.tif, soil_nox_summary.txt\n\n")
        
        if failed:
            f.write("FAILED SCENARIOS:\n")
            f.write("-" * 30 + "\n")
            for scenario in failed:
                f.write(f"❌ {scenario}\n\n")
        
        f.write("OUTPUT STRUCTURE:\n")
        f.write("-" * 30 + "\n")
        f.write("outputs/uk_results/{scenario}/\n")
        f.write("├── nh3_emissions.nc          # NH3 emissions (existing)\n")
        f.write("├── n_application.nc          # N application input (existing)\n")
        f.write("├── nox_emissions.tif         # NEW: Soil NOx emissions\n")
        f.write("└── soil_nox_summary.txt      # NEW: Summary statistics\n\n")
        
        f.write("SOIL NOx MODEL (SIMPLIFIED):\n")
        f.write("-" * 30 + "\n")
        f.write("Model: Yan et al. (2005) process-based soil NOx emissions\n")
        f.write("Equation: NOx = SOC × pH × exp(climate) × exp(-1.8327) × LU × exp(-0.11×T0) × TS_SM × N\n")
        f.write("Nitrogen effect: 1.0 + (0.03545 × N_rate × 122/365)\n")
        f.write("Time-varying effect: Simplified (constant = 1.0)\n")
        f.write("Key improvement: Scenario-specific nitrogen application instead of global uniform data\n\n")
        
        f.write("TECHNICAL NOTES:\n")
        f.write("-" * 30 + "\n")
        f.write("• Uses simplified constant time-varying effects due to issues with original time-series processing\n")
        f.write("• Focuses on scenario-specific nitrogen fertilization effects\n")
        f.write("• Maintains all other Yan et al. (2005) model components (soil, climate, land use)\n")
        f.write("• Suitable for comparative analysis between land use scenarios\n")

def main():
    """Main function"""
    
    print("UK Soil NOx Emissions - Batch Processing")
    print("=" * 60)
    print("This script processes all UK scenarios using scenario-specific")
    print("nitrogen application data with the Yan et al. (2005) soil NOx model.")
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage:")
        print("  python process_all_uk_soil_nox.py    # Process all scenarios")
        return
    
    process_all_scenarios()

if __name__ == "__main__":
    main()