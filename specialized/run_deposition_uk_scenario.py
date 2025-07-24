#!/usr/bin/env python3
"""
UK Scenario Deposition Processing

This script processes deposition calculations for UK land use scenarios using:
1. ESA-CCI land use scenario maps
2. The new dep_2_lai_month_avg_esa_cci.py for better LAI mapping
3. Saves results in outputs/uk_results/<scenario_name>/

Key features:
- Uses ESA-CCI inputs for detailed land use classification
- Follows same output structure as other UK emission modules
- Generates deposition_summary.txt for validation

Usage:
    python run_deposition_uk_scenario.py <scenario_name>

Example:
    python run_deposition_uk_scenario.py extensification_current_practices

Important: Run with the rasters conda environment:
    /Users/sumilthakrar/yes/envs/rasters/bin/python run_deposition_uk_scenario.py <scenario>
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import shutil

def print_header(scenario_name):
    """Print header information"""
    print("=" * 80)
    print("UK DEPOSITION PROCESSING")
    print("=" * 80)
    print()
    print(f"Processing deposition for UK scenario: {scenario_name}")
    print()
    print("This script calculates PM2.5 deposition by vegetation using:")
    print("• ESA-CCI land use scenario map for detailed vegetation classification")
    print("• Enhanced LAI mapping (dep_2_lai_month_avg_esa_cci.py)")
    print("• Land-use-specific deposition velocities (Nowak et al. 2013 with scaling)")
    print("  - Forest: 100% velocity scaling (highest capture)")
    print("  - Grass/Cropland: 50% velocity scaling (moderate capture)")
    print("  - Urban/Other: 25% velocity scaling (low capture)")
    print("• PM2.5 concentration data (GHAP)")
    print()
    print("Formula: Deposition = PM2.5_concentration × Leaf_Area × (Velocity × LandUse_Scaling)")
    print()
    print("=" * 80)
    print()

def check_scenario_setup(scenario_name):
    """Check that the UK scenario is properly set up"""
    print("Checking UK scenario setup...")
    
    required_files = [
        "inputs/scenario_landuse_esa_cci.tif",  # ESA-CCI scenario file
        "grid.tif",  # UK-only grid reference
        "inputs/ESA_CCI_to_Simple_mapping.csv"  # ESA-CCI mapping
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required setup files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        print()
        print("Please run UK scenario setup first:")
        print(f"   python setup_uk_scenario.py {scenario_name}")
        print()
        return False
    
    # Check that this is the correct scenario
    original_scenario = f"scenarios/UKNatureFrontierWithAir/United Kingdom/ScenarioMaps/{scenario_name}.tif"
    if not os.path.exists(original_scenario):
        print(f"❌ Scenario not found: {original_scenario}")
        return False
    
    print("✅ UK scenario setup validated!")
    print(f"✅ Using ESA-CCI land use with detailed LAI mapping")
    print()
    return True

def ensure_uk_met_cache():
    """Ensure UK meteorological cache exists before processing"""
    print("Checking UK meteorological data cache...")
    
    # Import cache checking function
    sys.path.append('utils')
    try:
        from crop_met_data_uk import check_uk_met_cache
        cache_valid, missing_files, cache_info = check_uk_met_cache()
        
        if cache_valid:
            print("✅ UK meteorological cache is ready!")
            if cache_info:
                print(f"   Created: {cache_info.get('Created', 'Unknown')}")
                print(f"   Files: {cache_info.get('Files', 'Unknown')}")
            return True
        else:
            print(f"⚠️  UK meteorological cache incomplete: {len(missing_files)} missing files")
            print()
            print("Creating UK meteorological cache (one-time setup)...")
            print("This will take ~30-45 minutes but speeds up all future UK processing")
            
            # Run the cache creation
            print("   Running: /Users/sumilthakrar/yes/envs/rasters/bin/python utils/crop_met_data_uk.py")
            import subprocess
            result = subprocess.run([
                "/Users/sumilthakrar/yes/envs/rasters/bin/python", 
                "utils/crop_met_data_uk.py"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ UK meteorological cache created successfully!")
            else:
                print(f"❌ Cache creation failed: {result.stderr}")
                return False
            
            # Verify cache was created successfully
            cache_valid, missing_files, cache_info = check_uk_met_cache()
            return cache_valid
            
    except ImportError as e:
        print(f"❌ Error importing UK cache utilities: {e}")
        return False
    except Exception as e:
        print(f"❌ Error with UK meteorological cache: {e}")
        return False

def check_prerequisites():
    """Check that required deposition input files exist"""
    print("Checking deposition prerequisites...")
    
    required_files = [
        "intermediate/coarse_averaged_LAI_SimpleID.nc",  # From dep_1 (should exist)
        "inputs/dep_v.csv"  # Deposition velocity lookup
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required deposition input files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        print()
        print("Please ensure:")
        print("   - LAI preprocessing completed (dep_1_lai_reclass.py)")
        print()
        return False
    
    print("✅ All deposition prerequisites satisfied!")
    print()
    return True

def run_deposition_steps_uk(inputdir=""):
    """Run the UK-optimized deposition calculation steps with land-use-specific velocities"""
    
    print("Running UK-optimized deposition calculation with land-use-specific velocity scaling...")
    print()
    
    # Import the UK-optimized deposition modules
    from dep_scripts import dep_2_lai_month_avg_esa_cci, dep_4_multiply_landuse_simple
    
    try:
        # Step 2: Calculate monthly LAI using ESA-CCI inputs
        print("Step 2: Calculating monthly LAI from ESA-CCI land use...")
        dep_2_lai_month_avg_esa_cci.run(inputdir)
        print("✅ Monthly LAI calculation completed")
        print()
        
        # Step 3: Skip separate velocity calculation - now integrated in Step 4
        print("Step 3: Using existing UK deposition velocities with land-use-specific scaling...")
        print("✅ Land-use-specific velocity scaling will be applied in Step 4")
        print()
        
        # Step 4: Calculate final UK PM2.5 deposition with land-use-specific velocities
        print("Step 4: Calculating UK PM2.5 deposition with land-use-specific velocity scaling...")
        print("   Forest areas: 100% velocity scaling (highest capture)")
        print("   Grass/Cropland areas: 50% velocity scaling (moderate capture)")
        print("   Urban/Other areas: 25% velocity scaling (low capture)")
        result = dep_4_multiply_landuse_simple.run(inputdir)
        
        if result:
            print("✅ UK PM2.5 deposition calculation completed")
            print(f"   Total deposition: {result['total_deposition']:,.0f} kg/year")
            print(f"   Max pixel deposition: {result['max_deposition']:.2f} kg/year")
            print()
            return True
        else:
            print("❌ UK PM2.5 deposition calculation failed")
            return False
        
    except Exception as e:
        print(f"❌ Error during UK deposition calculation: {e}")
        import traceback
        traceback.print_exc()
        return False

def organize_outputs(scenario_name):
    """Move UK deposition outputs to UK results directory"""
    
    output_dir = f"outputs/uk_results/{scenario_name}"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Organizing outputs in: {output_dir}")
    
    # Define files to move/copy (UK-specific filenames)
    files_to_organize = [
        ("outputs/pm25_annual_deposition_landuse_scaled_uk_2021.nc", "pm25_deposition.nc"),
    ]
    
    # Move/copy the main deposition output
    for source, target in files_to_organize:
        if os.path.exists(source):
            target_path = os.path.join(output_dir, target)
            shutil.copy2(source, target_path)
            print(f"  ✓ Copied: {source} → {target_path}")
        else:
            print(f"  ⚠️  Output file not found: {source}")
    
    # Create a summary file
    create_deposition_summary(scenario_name, output_dir)
    
    print(f"✅ Outputs organized in: {output_dir}")
    return output_dir

def create_deposition_summary(scenario_name, output_dir):
    """Create a summary file with deposition processing information"""
    
    summary_path = os.path.join(output_dir, "deposition_summary.txt")
    
    with open(summary_path, 'w') as f:
        f.write("UK Deposition Processing Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Scenario: {scenario_name}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("Processing Details:\n")
        f.write("• Land use input: ESA-CCI scenario map\n")
        f.write("• LAI calculation: Enhanced ESA-CCI to Simple mapping\n")
        f.write("• Deposition model: Nowak et al. (2013)\n")
        f.write("• Temporal scope: 2021 annual\n\n")
        
        f.write("Input Files:\n")
        f.write("• Land use: inputs/scenario_landuse_esa_cci.tif\n")
        f.write("• PM2.5 data: inputs/concentrations/GHAP_PM2.5_*.nc\n")
        f.write("• Wind data: inputs/MERRA2/MERRA2_*.nc4\n")
        f.write("• LAI data: inputs/LAI/Yuan_proc_MODIS_XLAI.025x025.2020.nc\n\n")
        
        f.write("Output Files:\n")
        f.write("• pm25_deposition.nc - Annual PM2.5 deposition (kg/year)\n")
        f.write("• deposition_summary.txt - This summary file\n\n")
        
        f.write("Methodology:\n")
        f.write("1. ESA-CCI land use converted to Simple classification\n")
        f.write("2. LAI values mapped by Simple class and month\n")
        f.write("3. Deposition velocities calculated from wind speeds\n")
        f.write("4. Final deposition = PM2.5 × LAI × Velocity\n\n")
        
        # Add file size information if available
        deposition_file = os.path.join(output_dir, "pm25_deposition.nc")
        if os.path.exists(deposition_file):
            file_size = os.path.getsize(deposition_file)
            f.write(f"Output file size: {file_size:,} bytes\n")
    
    print(f"  ✓ Created summary: {summary_path}")

def main():
    """Main function"""
    
    if len(sys.argv) != 2:
        print("Usage: python run_deposition_uk_scenario.py <scenario_name>")
        print("\nAvailable scenarios:")
        scenarios_dir = Path("scenarios/UKNatureFrontierWithAir/United Kingdom/ScenarioMaps")
        if scenarios_dir.exists():
            for tif_file in scenarios_dir.glob("*.tif"):
                print(f"  - {tif_file.stem}")
        sys.exit(1)
    
    scenario_name = sys.argv[1]
    
    print_header(scenario_name)
    
    # Check that UK scenario is set up
    if not check_scenario_setup(scenario_name):
        print("❌ UK scenario setup failed. Exiting.")
        sys.exit(1)
    
    # Check prerequisites
    if not check_prerequisites():
        print("❌ Prerequisites not met. Exiting.")
        sys.exit(1)
    
    # Check if we can proceed with existing velocity files
    velocity_files_exist = all(
        os.path.exists(f"intermediate/deposition_velocity_uk_2021_{month:02d}.nc") 
        for month in range(1, 13)
    )
    
    if velocity_files_exist:
        print("✅ UK deposition velocity files exist, can proceed without meteorological cache")
    else:
        # Ensure UK meteorological cache exists for velocity calculation
        if not ensure_uk_met_cache():
            print("❌ UK meteorological cache setup failed and no velocity files exist. Exiting.")
            sys.exit(1)
    
    print("Starting UK deposition processing...")
    print()
    
    # Run UK-optimized deposition calculations
    if not run_deposition_steps_uk():
        print("❌ UK deposition calculation failed. Exiting.")
        sys.exit(1)
    
    # Organize outputs
    output_dir = organize_outputs(scenario_name)
    
    print()
    print("🎉 UK deposition processing completed successfully!")
    print(f"📁 Results saved to: {output_dir}")
    print("📄 Check deposition_summary.txt for processing details")
    print()

if __name__ == "__main__":
    main()