#!/usr/bin/env python3
"""
Reprocess UK Dust Emissions with Corrected Land Use Mapping

This script processes all UK scenarios with the corrected dust emission mapping
that properly handles Simple 4-class land use classification.

Usage:
    python process_corrected_uk_dust.py                # Process all scenarios
    python process_corrected_uk_dust.py --scenario <name>  # Process single scenario

IMPORTANT: Run with the rasters conda environment:
/Users/sumilthakrar/yes/envs/rasters/bin/python process_corrected_uk_dust.py
"""

import os
import sys
import shutil
from pathlib import Path
import traceback
from datetime import datetime

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

def backup_existing_outputs():
    """Backup existing dust outputs before reprocessing"""
    
    backup_dir = Path("backups/dust_outputs_old")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    scenarios = get_uk_scenarios()
    backed_up = []
    
    print("Backing up existing dust outputs...")
    
    for scenario in scenarios:
        original_dir = Path(f"outputs/uk_results/{scenario}")
        backup_scenario_dir = backup_dir / scenario
        
        if original_dir.exists():
            # Check for dust files
            dust_files = list(original_dir.glob("dust_emissions*.tif"))
            if dust_files:
                backup_scenario_dir.mkdir(exist_ok=True)
                for dust_file in dust_files:
                    shutil.copy2(dust_file, backup_scenario_dir)
                    print(f"  ✓ Backed up {dust_file.name} for {scenario}")
                backed_up.append(scenario)
    
    print(f"Backed up dust outputs for {len(backed_up)} scenarios to: {backup_dir}")
    return backup_dir

def setup_scenario(scenario_name):
    """Setup UK processing environment for a scenario"""
    
    print(f"Setting up scenario: {scenario_name}")
    
    try:
        from scenario_scripts.uk_processing_setup import setup_uk_processing_environment
        
        # Build path to scenario file
        scenario_file = Path(f"scenarios/UKNatureFrontierWithAir/United Kingdom/ScenarioMaps/{scenario_name}.tif")
        
        if not scenario_file.exists():
            print(f"  ❌ Scenario file not found: {scenario_file}")
            return False
        
        setup_uk_processing_environment(scenario_file, backup_originals=True)
        print(f"  ✓ UK processing environment ready for {scenario_name}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to setup {scenario_name}: {e}")
        return False

def run_dust_processing():
    """Run dust emissions processing"""
    
    print("Running dust emissions processing...")
    
    try:
        # Import and run dust processing modules
        from dust_scripts import dust_1_soil_texture
        from dust_scripts import dust_2_flux_calc
        from dust_scripts import dust_3_sum
        
        inputdir = "."
        
        print("  📍 Step 1: Finding soil texture...")
        dust_1_soil_texture.run(inputdir)
        print("  ✓ Soil texture completed")
        
        print("  📍 Step 2: Calculating dust fluxes (with corrected land use mapping)...")
        dust_2_flux_calc.run(inputdir)
        print("  ✓ Dust flux calculation completed")
        
        print("  📍 Step 3: Calculating total dust emissions...")
        dust_3_sum.run(inputdir)
        print("  ✓ Total dust emissions completed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Dust processing failed: {e}")
        traceback.print_exc()
        return False

def save_corrected_outputs(scenario_name):
    """Save corrected dust outputs to UK results"""
    
    output_dir = Path(f"outputs/uk_results/{scenario_name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Expected dust output file
    dust_output = Path("outputs/dust_emissions.tiff")
    if not dust_output.exists():
        dust_output = Path("outputs/dust_emissions.tif")
    
    if dust_output.exists():
        # Copy to UK results directory
        target_path = output_dir / "dust_emissions_corrected.tif"
        shutil.copy2(dust_output, target_path)
        print(f"  ✓ Saved corrected dust emissions: {target_path}")
        
        # Create processing summary
        summary_path = output_dir / "dust_correction_summary.txt"
        with open(summary_path, 'w') as f:
            f.write("UK Dust Emissions - Corrected Land Use Mapping\\n")
            f.write("=" * 60 + "\\n\\n")
            f.write(f"Scenario: {scenario_name}\\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
            f.write("Processing: Corrected dust emissions with proper Simple 4-class mapping\\n\\n")
            
            f.write("LAND USE MAPPING CORRECTION:\\n")
            f.write("-" * 40 + "\\n")
            f.write("Fixed land use classification mismatch between:\\n")
            f.write("• UK scenarios: Simple 4-class (0=Other, 1=Cropland, 2=Grass, 3=Forest)\\n")
            f.write("• Dust model: Previous mapping expected IGBP codes\\n\\n")
            
            f.write("CORRECTED MAPPING:\\n")
            f.write("-" * 20 + "\\n")
            f.write("0 (Other): No dust emissions (water, urban, bare)\\n")
            f.write("1 (Cropland): Moderate dust (k=0.0310, fdtf=0.75)\\n")
            f.write("2 (Grass): Moderate dust (k=0.1000, fdtf=0.75)\\n")
            f.write("3 (Forest): No dust emissions (k=50.0, fdtf=0.0)\\n\\n")
            
            f.write("TECHNICAL NOTES:\\n")
            f.write("-" * 20 + "\\n")
            f.write("• Fixed file path: dust_2_flux_calc.py now reads gblulcg20_10000.tif\\n")
            f.write("• Added dual classification support (IGBP + Simple 4-class)\\n")
            f.write("• Conservative approach: Other class assigned no dust\\n")
            f.write("• Should produce much more realistic emission estimates\\n")
        
        print(f"  ✓ Saved processing summary: {summary_path}")
        return target_path
    else:
        print(f"  ❌ Dust output file not found: {dust_output}")
        return None

def process_scenario(scenario_name):
    """Process dust emissions for a single scenario"""
    
    print(f"\\n{'='*60}")
    print(f"PROCESSING SCENARIO: {scenario_name}")
    print(f"{'='*60}")
    
    # Step 1: Setup scenario
    if not setup_scenario(scenario_name):
        return False
    
    # Step 2: Run dust processing
    if not run_dust_processing():
        return False
    
    # Step 3: Save outputs
    output_path = save_corrected_outputs(scenario_name)
    if output_path:
        print(f"✅ SUCCESS: {scenario_name}")
        print(f"   Corrected emissions: {output_path}")
        return True
    else:
        print(f"❌ FAILED: {scenario_name}")
        return False

def restore_global_setup():
    """Restore global processing environment"""
    
    print("Restoring global processing environment...")
    try:
        from scenario_scripts.uk_processing_setup import restore_original_files
        restore_original_files()
        print("  ✓ Global environment restored")
    except Exception as e:
        print(f"  ⚠️  Could not restore global environment: {e}")

def main():
    """Main processing function"""
    
    print("UK Dust Emissions - Corrected Land Use Processing")
    print("=" * 60)
    print("This script reprocesses UK dust emissions with corrected")
    print("Simple 4-class land use mapping.")
    print()
    
    # Parse command line arguments
    if "--scenario" in sys.argv:
        idx = sys.argv.index("--scenario")
        if idx + 1 < len(sys.argv):
            scenarios = [sys.argv[idx + 1]]
        else:
            print("❌ Error: --scenario requires a scenario name")
            sys.exit(1)
    else:
        scenarios = get_uk_scenarios()
    
    print(f"Processing {len(scenarios)} scenario(s)...")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Backup existing outputs
    backup_dir = backup_existing_outputs()
    print()
    
    successful = []
    failed = []
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\\n[{i}/{len(scenarios)}] Processing: {scenario}")
        print("-" * 60)
        
        try:
            success = process_scenario(scenario)
            if success:
                successful.append(scenario)
            else:
                failed.append(scenario)
        except Exception as e:
            failed.append(scenario)
            print(f"❌ FAILED: {scenario}")
            print(f"   Error: {str(e)}")
            traceback.print_exc()
    
    # Restore global environment
    print()
    restore_global_setup()
    
    # Final summary
    print(f"\\n{'='*60}")
    print("PROCESSING SUMMARY")
    print(f"{'='*60}")
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
    
    print(f"Original dust outputs backed up to: {backup_dir}")
    print("Corrected dust emissions saved with '_corrected.tif' suffix")

if __name__ == "__main__":
    main()