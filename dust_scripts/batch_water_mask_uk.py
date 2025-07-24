#!/usr/bin/env python3
"""
Batch Water Masking for UK Dust Emissions

This script applies water masking to all UK dust emission scenarios to ensure
dust emissions are set to 0.0 over water areas (land use value 0).

Usage:
    python dust_scripts/batch_water_mask_uk.py            # Process all scenarios
    python dust_scripts/batch_water_mask_uk.py --validate # Include validation
    python dust_scripts/batch_water_mask_uk.py --help     # Show help

IMPORTANT: Run with the rasters conda environment:
/Users/sumilthakrar/yes/envs/rasters/bin/python dust_scripts/batch_water_mask_uk.py

Background:
A land use mapping bug was fixed in dust_landuse_flux_calc.py that previously
caused water areas to receive dust-producing parameters instead of fdtf=0.0.
This script corrects existing dust emission outputs by masking water areas.
"""

import os
import sys
from pathlib import Path
import traceback
from datetime import datetime

# Add the dust_scripts directory to the path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

from dust_water_mask import run as apply_water_mask

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

def check_prerequisites():
    """Check that UK dust emissions exist for scenarios"""
    
    scenarios = get_uk_scenarios()
    missing_dust = []
    
    for scenario in scenarios:
        dust_path = f"outputs/uk_results/{scenario}/dust_emissions.tif"
        if not os.path.exists(dust_path):
            missing_dust.append(scenario)
    
    if missing_dust:
        print("❌ Missing dust emissions for scenarios:")
        for scenario in missing_dust:
            print(f"   - {scenario}")
        print("\nPlease run dust emissions processing first.")
        return False
    
    print(f"✅ Found dust emissions for all {len(scenarios)} scenarios")
    return True

def check_existing_water_masked():
    """Check if any scenarios already have water-masked files"""
    
    scenarios = get_uk_scenarios()
    existing_masked = []
    
    for scenario in scenarios:
        masked_path = f"outputs/uk_results/{scenario}/dust_emissions_water_masked.tif"
        if os.path.exists(masked_path):
            existing_masked.append(scenario)
    
    if existing_masked:
        print(f"⚠️  Found {len(existing_masked)} scenarios with existing water-masked files:")
        for scenario in existing_masked:
            print(f"   - {scenario}")
        
        response = input("\nOverwrite existing files? (y/N): ").strip().lower()
        return response in ['y', 'yes']
    
    return True

def validate_water_masking(original_path, masked_path):
    """
    Validate that water masking was applied correctly
    
    Args:
        original_path: Path to original dust emissions
        masked_path: Path to water-masked dust emissions
        
    Returns:
        dict: Validation statistics
    """
    import pygeoprocessing.geoprocessing as geop
    import numpy as np
    
    try:
        # Read both rasters
        original_array = geop.raster_to_numpy_array(original_path)
        masked_array = geop.raster_to_numpy_array(masked_path)
        
        # Calculate statistics
        original_valid = original_array[original_array != -1]
        masked_valid = masked_array[masked_array != -1]
        
        original_zeros = np.sum(original_valid == 0)
        masked_zeros = np.sum(masked_valid == 0)
        zero_increase = masked_zeros - original_zeros
        
        # Check for any changes
        pixels_changed = np.sum(original_array != masked_array)
        
        return {
            'original_total': np.sum(original_valid),
            'masked_total': np.sum(masked_valid),
            'original_zeros': original_zeros,
            'masked_zeros': masked_zeros,
            'zero_increase': zero_increase,
            'pixels_changed': pixels_changed,
            'reduction_percentage': ((np.sum(original_valid) - np.sum(masked_valid)) / np.sum(original_valid)) * 100 if np.sum(original_valid) > 0 else 0
        }
        
    except Exception as e:
        print(f"   ⚠️  Validation failed: {e}")
        return None

def process_scenario_water_masking(scenario, validate=False):
    """
    Process water masking for a single scenario
    
    Args:
        scenario: Name of the UK scenario
        validate: Whether to run validation checks
        
    Returns:
        bool: Success status
    """
    
    print(f"Processing water masking for scenario: {scenario}")
    print("=" * 60)
    
    # Define file paths
    original_path = f"outputs/uk_results/{scenario}/dust_emissions.tif"
    masked_path = f"outputs/uk_results/{scenario}/dust_emissions_water_masked.tif"
    
    # Check if original file exists
    if not os.path.exists(original_path):
        print(f"❌ Dust emissions file not found: {original_path}")
        return False
    
    try:
        # Apply water masking
        print(f"Applying water mask to: {original_path}")
        result_path = apply_water_mask(original_path, masked_path, inputdir=".")
        
        if result_path != masked_path:
            # Move file if needed
            os.rename(result_path, masked_path)
        
        print(f"✅ Water masking completed: {masked_path}")
        
        # Validation if requested
        if validate:
            print("Running validation...")
            validation_stats = validate_water_masking(original_path, masked_path)
            
            if validation_stats:
                print(f"   📊 Original total emissions: {validation_stats['original_total']:,.2f}")
                print(f"   📊 Masked total emissions: {validation_stats['masked_total']:,.2f}")
                print(f"   📊 Pixels changed: {validation_stats['pixels_changed']:,}")
                print(f"   📊 Zero pixels increase: {validation_stats['zero_increase']:,}")
                print(f"   📊 Emission reduction: {validation_stats['reduction_percentage']:.3f}%")
                
                # Save validation report
                validation_path = f"outputs/uk_results/{scenario}/dust_water_mask_validation.txt"
                save_validation_report(scenario, validation_stats, validation_path)
                print(f"   📄 Validation report: {validation_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error processing scenario {scenario}: {str(e)}")
        return False

def save_validation_report(scenario, stats, output_path):
    """Save water masking validation report"""
    
    with open(output_path, 'w') as f:
        f.write("Dust Emissions Water Masking Validation\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Scenario: {scenario}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("Processing: Applied water mask to set dust emissions to 0.0 over water areas\n\n")
        
        f.write("VALIDATION STATISTICS:\n")
        f.write("-" * 30 + "\n")
        f.write(f"Original total emissions: {stats['original_total']:,.2f}\n")
        f.write(f"Masked total emissions: {stats['masked_total']:,.2f}\n")
        f.write(f"Emission reduction: {stats['reduction_percentage']:.3f}%\n")
        f.write(f"Pixels modified: {stats['pixels_changed']:,}\n")
        f.write(f"Original zero pixels: {stats['original_zeros']:,}\n")
        f.write(f"Masked zero pixels: {stats['masked_zeros']:,}\n")
        f.write(f"Additional zero pixels: {stats['zero_increase']:,}\n\n")
        
        f.write("PROCESSING DETAILS:\n")
        f.write("-" * 30 + "\n")
        f.write("• Water areas identified using land use value 0\n")
        f.write("• Dust emissions set to 0.0 in all water pixels\n")
        f.write("• Non-water areas remain unchanged\n")
        f.write("• Fixes land use mapping bug in dust calculations\n")

def process_all_water_masking(validate=False):
    """
    Process water masking for all UK scenarios
    
    Args:
        validate: Whether to generate validation outputs
    """
    
    scenarios = get_uk_scenarios()
    
    print("UK Dust Emissions - Batch Water Masking")
    print("=" * 60)
    print("Applying water masks to set dust emissions to 0.0 over water areas")
    print(f"Processing {len(scenarios)} scenarios...")
    print(f"Validation: {'Enabled' if validate else 'Disabled'}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    successful = []
    failed = []
    
    for i, scenario in enumerate(scenarios, 1):
        
        print(f"[{i}/{len(scenarios)}] Processing: {scenario}")
        print("-" * 60)
        
        try:
            success = process_scenario_water_masking(scenario, validate)
            
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
    print("BATCH WATER MASKING SUMMARY")
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
    summary_path = "outputs/uk_results/dust_water_mask_summary.txt"
    save_batch_summary(successful, failed, summary_path, validate)
    print(f"Batch summary saved to: {summary_path}")

def save_batch_summary(successful, failed, output_path, validate):
    """Save batch processing summary to file"""
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write("UK Dust Emissions - Batch Water Masking Summary\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Processing date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Processing type: Apply water mask to dust emissions\n")
        f.write(f"Validation: {'Enabled' if validate else 'Disabled'}\n")
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
                files = ["dust_emissions_water_masked.tif"]
                if validate:
                    files.append("dust_water_mask_validation.txt")
                f.write(f"   New files: {', '.join(files)}\n\n")
        
        if failed:
            f.write("FAILED SCENARIOS:\n")
            f.write("-" * 30 + "\n")
            for scenario in failed:
                f.write(f"❌ {scenario}\n\n")
        
        f.write("OUTPUT STRUCTURE:\n")
        f.write("-" * 30 + "\n")
        f.write("outputs/uk_results/{scenario}/\n")
        f.write("├── dust_emissions.tif                # Original dust emissions (preserved)\n")
        f.write("├── dust_emissions_water_masked.tif   # NEW: Water-masked dust emissions\n")
        if validate:
            f.write("└── dust_water_mask_validation.txt    # NEW: Validation report\n")
        f.write("\n")
        
        f.write("PROCESSING DETAILS:\n")
        f.write("-" * 30 + "\n")
        f.write("• Water areas identified using land use value 0 from gblulcg20_10000.tif\n")
        f.write("• Dust emissions set to 0.0 in all water pixels\n")
        f.write("• Non-water areas remain unchanged\n")
        f.write("• Fixes land use mapping bug that caused dust over water bodies\n")
        f.write("• Original files preserved for reference\n")

def main():
    """Main function"""
    
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("UK Dust Emissions Batch Water Masking")
        print("=" * 40)
        print("This script applies water masking to all UK dust emission scenarios.")
        print("Water areas (land use value 0) are set to zero dust emissions.")
        print()
        print("Usage:")
        print("  python batch_water_mask_uk.py           # Basic water masking")
        print("  python batch_water_mask_uk.py --validate # Include validation outputs")
        print("  python batch_water_mask_uk.py --help     # Show this help")
        print()
        print("Prerequisites:")
        print("  • UK dust emissions must exist for all scenarios")
        print("  • Land use raster (gblulcg20_10000.tif) in inputs/ folder") 
        print("  • Run with rasters conda environment")
        print()
        print("Background:")
        print("  A land use mapping bug was fixed that caused water areas to receive")
        print("  dust-producing parameters. This script corrects existing outputs.")
        return
    
    validate = "--validate" in sys.argv or "--val" in sys.argv
    
    print("UK Dust Emissions - Batch Water Masking")
    print("=" * 60)
    print("This script applies water masking to dust emissions for all")
    print("UK scenarios to ensure emissions are 0.0 over water areas.")
    print()
    
    # Check prerequisites
    if not check_prerequisites():
        print("❌ Prerequisites not met. Exiting.")
        sys.exit(1)
    
    # Check for existing files
    if not check_existing_water_masked():
        print("❌ User chose not to overwrite existing files. Exiting.")
        sys.exit(1)
    
    print()
    print("Starting batch water masking...")
    print()
    
    # Process all scenarios
    process_all_water_masking(validate)

if __name__ == "__main__":
    main()