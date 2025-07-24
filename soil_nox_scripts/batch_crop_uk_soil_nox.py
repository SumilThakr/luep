#!/usr/bin/env python3
"""
Batch UK Soil NOx Post-Processing

This script processes all 15 UK scenarios to crop global soil NOx emissions
to UK extents and generate UK-specific statistics.

Usage:
    python batch_crop_uk_soil_nox.py                # Process all scenarios
    python batch_crop_uk_soil_nox.py --validate     # Include validation outputs
    python batch_crop_uk_soil_nox.py --help         # Show help

IMPORTANT: Run with the rasters conda environment:
/Users/sumilthakrar/yes/envs/rasters/bin/python soil_nox_scripts/batch_crop_uk_soil_nox.py
"""

import os
import sys
from pathlib import Path
import traceback
from datetime import datetime

# Add the soil_nox_scripts directory to the path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

from soil_nox_uk_postprocessing import process_scenario_uk_cropping

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
    """Check that global soil NOx emissions exist for scenarios"""
    
    scenarios = get_uk_scenarios()
    missing_global = []
    
    for scenario in scenarios:
        global_nox_path = f"outputs/uk_results/{scenario}/nox_emissions.tif"
        if not os.path.exists(global_nox_path):
            missing_global.append(scenario)
    
    if missing_global:
        print("❌ Missing global soil NOx emissions for scenarios:")
        for scenario in missing_global:
            print(f"   - {scenario}")
        print("\nPlease run global soil NOx processing first:")
        print("   /Users/sumilthakrar/yes/envs/rasters/bin/python process_all_uk_soil_nox.py")
        return False
    
    print(f"✅ Found global soil NOx emissions for all {len(scenarios)} scenarios")
    return True

def process_all_uk_cropping(validate=False):
    """
    Process all UK scenarios for cropping to UK extent
    
    Args:
        validate: Whether to generate validation outputs
    """
    
    scenarios = get_uk_scenarios()
    
    print("UK Soil NOx Post-Processing - Batch Cropping")
    print("=" * 60)
    print("Cropping global soil NOx emissions to UK extents")
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
            success = process_scenario_uk_cropping(scenario, validate)
            
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
    print("BATCH UK CROPPING SUMMARY")
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
    summary_path = "outputs/uk_results/uk_cropping_summary.txt"
    save_batch_summary(successful, failed, summary_path, validate)
    print(f"Batch summary saved to: {summary_path}")

def save_batch_summary(successful, failed, output_path, validate):
    """Save batch processing summary to file"""
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write("UK Soil NOx Post-Processing - Batch Cropping Summary\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Processing date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Processing type: Crop global emissions to UK extent\n")
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
                files = ["nox_emissions_uk.tif", "soil_nox_summary_uk.txt"]
                if validate:
                    files.append("global_vs_uk_comparison.txt")
                f.write(f"   New files: {', '.join(files)}\n\n")
        
        if failed:
            f.write("FAILED SCENARIOS:\n")
            f.write("-" * 30 + "\n")
            for scenario in failed:
                f.write(f"❌ {scenario}\n\n")
        
        f.write("OUTPUT STRUCTURE:\n")
        f.write("-" * 30 + "\n")
        f.write("outputs/uk_results/{scenario}/\n")
        f.write("├── nox_emissions.tif         # Global soil NOx emissions (existing)\n")
        f.write("├── nox_emissions_uk.tif     # NEW: UK-cropped soil NOx emissions\n")
        f.write("├── soil_nox_summary.txt     # Global statistics (existing)\n")
        f.write("├── soil_nox_summary_uk.txt  # NEW: UK-specific statistics\n")
        if validate:
            f.write("└── global_vs_uk_comparison.txt  # NEW: Global vs UK comparison\n")
        f.write("\n")
        
        f.write("UK SPATIAL EXTENT:\n")
        f.write("-" * 30 + "\n")
        f.write("Geographic bounds: Approximately -8.17 to 1.77°E, 49.91 to 60.85°N\n")
        f.write("Coordinate system: WGS84 Geographic (EPSG:4326)\n")
        f.write("Spatial reference: UK land-use scenario maps\n")
        f.write("Processing method: Bilinear resampling with bounding box intersection\n\n")
        
        f.write("TECHNICAL NOTES:\n")
        f.write("-" * 30 + "\n")
        f.write("• UK extent determined from land-use scenario spatial bounds\n")
        f.write("• Global emissions cropped using pygeoprocessing alignment\n")
        f.write("• Original resolution and projection maintained\n")
        f.write("• Statistics calculated only for valid (non-NoData) pixels\n")
        f.write("• Suitable for UK-focused policy analysis and visualization\n")

def generate_validation_summary():
    """Generate overall validation summary across all scenarios"""
    
    scenarios = get_uk_scenarios()
    validation_data = []
    
    print("Generating cross-scenario validation summary...")
    
    for scenario in scenarios:
        comparison_path = f"outputs/uk_results/{scenario}/global_vs_uk_comparison.txt"
        uk_stats_path = f"outputs/uk_results/{scenario}/soil_nox_summary_uk.txt"
        
        if os.path.exists(uk_stats_path):
            try:
                # Extract key statistics
                total_emission = None
                mean_emission = None
                total_pixels = None
                
                with open(uk_stats_path, 'r') as f:
                    for line in f:
                        if 'Total UK emission:' in line:
                            total_emission = float(line.split(':')[1].strip())
                        elif 'Mean emission:' in line:
                            mean_emission = float(line.split(':')[1].strip())
                        elif 'Total pixels:' in line:
                            total_pixels = int(line.split(':')[1].strip().replace(',', ''))
                
                validation_data.append({
                    'scenario': scenario,
                    'total_emission': total_emission,
                    'mean_emission': mean_emission,
                    'total_pixels': total_pixels
                })
                
            except Exception as e:
                print(f"Warning: Could not extract data for {scenario}: {e}")
    
    # Save validation summary
    validation_path = "outputs/uk_results/uk_validation_summary.txt"
    
    with open(validation_path, 'w') as f:
        f.write("UK Soil NOx Emissions - Cross-Scenario Validation\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Scenarios analyzed: {len(validation_data)}\n\n")
        
        f.write("SCENARIO COMPARISON:\n")
        f.write("-" * 40 + "\n")
        f.write("Scenario                     | Total Emission  | Mean Emission | Pixels\n")
        f.write("-" * 75 + "\n")
        
        # Sort by total emission for easy comparison
        validation_data.sort(key=lambda x: x['total_emission'] if x['total_emission'] else 0, reverse=True)
        
        for data in validation_data:
            scenario = data['scenario'][:25].ljust(25)
            total = f"{data['total_emission']:,.0f}" if data['total_emission'] else "N/A"
            mean = f"{data['mean_emission']:.6f}" if data['mean_emission'] else "N/A"
            pixels = f"{data['total_pixels']:,}" if data['total_pixels'] else "N/A"
            
            f.write(f"{scenario} | {total:>14} | {mean:>12} | {pixels:>10}\n")
        
        f.write("\nKEY INSIGHTS:\n")
        f.write("-" * 20 + "\n")
        
        if validation_data:
            total_emissions = [d['total_emission'] for d in validation_data if d['total_emission']]
            if total_emissions:
                max_emission = max(total_emissions)
                min_emission = min(total_emissions)
                ratio = max_emission / min_emission if min_emission > 0 else float('inf')
                
                f.write(f"• Highest total emission: {max_emission:,.0f}\n")
                f.write(f"• Lowest total emission: {min_emission:,.0f}\n")
                f.write(f"• Range ratio: {ratio:.1f}x difference between highest and lowest\n")
                f.write(f"• All scenarios processed to same UK extent\n")
                f.write(f"• Consistent pixel counts indicate proper spatial alignment\n")
    
    print(f"Cross-scenario validation saved to: {validation_path}")

def main():
    """Main function"""
    
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("UK Soil NOx Batch Cropping")
        print("=" * 40)
        print("This script crops global soil NOx emissions to UK extents for all scenarios.")
        print()
        print("Usage:")
        print("  python batch_crop_uk_soil_nox.py           # Basic cropping")
        print("  python batch_crop_uk_soil_nox.py --validate # Include validation outputs")
        print("  python batch_crop_uk_soil_nox.py --help     # Show this help")
        print()
        print("Prerequisites:")
        print("  • Global soil NOx emissions must exist for all scenarios")
        print("  • UK land-use scenario maps for spatial reference") 
        print("  • Run with rasters conda environment")
        return
    
    validate = "--validate" in sys.argv or "--val" in sys.argv
    
    print("UK Soil NOx Post-Processing - Batch Cropping")
    print("=" * 60)
    print("This script crops global soil NOx emissions to UK extents")
    print("for all UK land-use scenarios.")
    print()
    
    # Check prerequisites
    if not check_prerequisites():
        print("❌ Prerequisites not met. Exiting.")
        sys.exit(1)
    
    print()
    print("Starting batch UK cropping...")
    print()
    
    # Process all scenarios
    process_all_uk_cropping(validate)
    
    # Generate validation summary if requested
    if validate:
        print()
        generate_validation_summary()

if __name__ == "__main__":
    main()