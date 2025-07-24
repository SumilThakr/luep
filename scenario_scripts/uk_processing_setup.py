#!/usr/bin/env python3
"""
UK Processing Setup Utility

Sets up the processing environment for UK-only emissions calculations by:
1. Creating UK-only grid.tif from scenario extent
2. Converting and copying UK scenario to expected land use input location
3. Preserving global input data (MERRA2, SMOPS, etc.) - pygeoprocessing will auto-crop
"""

import rasterio
import numpy as np
from pathlib import Path
import shutil
from .esa_to_simple_converter import convert_esa_to_simple, load_uk_esa_mapping

def create_uk_grid_reference(uk_scenario_path, output_grid_path="grid.tif"):
    """
    Create UK-only grid.tif from UK scenario extent
    
    This becomes the reference raster that all processing will align to.
    
    Args:
        uk_scenario_path: Path to any UK scenario file
        output_grid_path: Path for output grid.tif (default: "grid.tif")
    """
    
    print(f"Creating UK-only grid reference from {Path(uk_scenario_path).name}...")
    
    with rasterio.open(uk_scenario_path) as src:
        # Get spatial properties from UK scenario
        profile = src.profile.copy()
        
        # Create a simple reference grid (all zeros)
        # This grid defines the processing extent and resolution
        reference_data = np.zeros((src.height, src.width), dtype=np.uint8)
        
        # Update profile for reference grid
        profile.update({
            'dtype': 'uint8',
            'nodata': 0,
            'compress': 'lzw',
            'count': 1
        })
        
        # Write reference grid
        with rasterio.open(output_grid_path, 'w', **profile) as dst:
            dst.write(reference_data, 1)
            dst.set_band_description(1, "UK Processing Reference Grid")
            dst.update_tags(1, **{
                'purpose': 'Reference grid for UK emissions processing',
                'extent': 'UK only',
                'created_from': str(uk_scenario_path)
            })
    
    print(f"  ✓ UK grid reference saved to: {output_grid_path}")
    print(f"    Dimensions: {src.width} x {src.height}")
    print(f"    CRS: {src.crs}")
    print(f"    Bounds: {src.bounds}")
    
    return output_grid_path

def setup_uk_scenario_for_processing(uk_scenario_path, target_lulc_path="inputs/gblulcg20_10000.tif"):
    """
    Convert UK scenario to Simple classification and place in expected location
    Also save original ESA-CCI file for dust emission calculations
    
    Args:
        uk_scenario_path: Path to UK scenario (ESA-CCI format)
        target_lulc_path: Where emission scripts expect land use file
    """
    
    print(f"Setting up UK scenario for processing...")
    print(f"  Input: {Path(uk_scenario_path).name}")
    print(f"  Target: {target_lulc_path}")
    
    # Ensure target directory exists
    Path(target_lulc_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Save original ESA-CCI file for dust emission calculations (preserves detailed land use codes)
    esa_cci_target = "inputs/scenario_landuse_esa_cci.tif"
    shutil.copy2(uk_scenario_path, esa_cci_target)
    print(f"  ✓ Original ESA-CCI file saved for dust calculations: {esa_cci_target}")
    
    # Convert ESA-CCI to Simple classification and save to target location (for other modules)
    convert_esa_to_simple(uk_scenario_path, target_lulc_path)
    
    print(f"  ✓ UK scenario ready for processing at: {target_lulc_path}")
    print(f"  ✓ Dust emissions will use detailed ESA-CCI parameters")
    
    return target_lulc_path

def backup_original_files():
    """Backup original global files before UK processing"""
    
    files_to_backup = [
        "grid.tif",
        "inputs/gblulcg20_10000.tif",
        "inputs/scenario_landuse_esa_cci.tif"
    ]
    
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    
    print("Backing up original files...")
    
    for file_path in files_to_backup:
        if Path(file_path).exists():
            backup_path = backup_dir / Path(file_path).name
            shutil.copy2(file_path, backup_path)
            print(f"  ✓ Backed up: {file_path} → {backup_path}")
        else:
            print(f"  ⚠️  File not found: {file_path}")

def restore_original_files():
    """Restore original global files after UK processing"""
    
    backup_dir = Path("backups")
    
    if not backup_dir.exists():
        print("No backup directory found")
        return
    
    files_to_restore = [
        ("grid.tif", "grid.tif"),
        ("gblulcg20_10000.tif", "inputs/gblulcg20_10000.tif"),
        ("scenario_landuse_esa_cci.tif", "inputs/scenario_landuse_esa_cci.tif")
    ]
    
    print("Restoring original files...")
    
    for backup_name, target_path in files_to_restore:
        backup_path = backup_dir / backup_name
        if backup_path.exists():
            shutil.copy2(backup_path, target_path)
            print(f"  ✓ Restored: {backup_path} → {target_path}")
        else:
            print(f"  ⚠️  Backup not found: {backup_path}")

def setup_uk_processing_environment(uk_scenario_path, backup_originals=True):
    """
    Complete setup for UK-only processing
    
    Args:
        uk_scenario_path: Path to UK scenario file
        backup_originals: Whether to backup original global files
        
    Returns:
        dict: Paths to created files
    """
    
    print("\n🌍 Setting up UK-only processing environment")
    print("=" * 50)
    
    scenario_name = Path(uk_scenario_path).stem
    print(f"Scenario: {scenario_name}")
    print(f"Input: {uk_scenario_path}")
    
    # Step 1: Backup original files
    if backup_originals:
        backup_original_files()
    
    # Step 2: Create UK-only grid reference
    grid_path = create_uk_grid_reference(uk_scenario_path)
    
    # Step 3: Setup scenario for processing
    lulc_path = setup_uk_scenario_for_processing(uk_scenario_path)
    
    print(f"\n✅ UK processing environment ready!")
    print(f"   Grid reference: {grid_path}")
    print(f"   Land use input: {lulc_path}")
    print(f"   Global input data: Will be auto-cropped to UK extent")
    
    result = {
        'scenario_name': scenario_name,
        'grid_reference': grid_path,
        'land_use_input': lulc_path,
        'original_scenario': uk_scenario_path
    }
    
    return result

def verify_uk_setup():
    """Verify that UK processing setup is correct"""
    
    print("\n🔍 Verifying UK processing setup...")
    
    required_files = [
        "grid.tif",
        "inputs/gblulcg20_10000.tif"
    ]
    
    all_good = True
    
    for file_path in required_files:
        if Path(file_path).exists():
            with rasterio.open(file_path) as src:
                print(f"  ✓ {file_path}: {src.width}x{src.height}, CRS: {src.crs}")
        else:
            print(f"  ❌ Missing: {file_path}")
            all_good = False
    
    # Check that both files have same extent
    if all([Path(f).exists() for f in required_files]):
        with rasterio.open("grid.tif") as grid_src, \
             rasterio.open("inputs/gblulcg20_10000.tif") as lulc_src:
            
            if (grid_src.bounds == lulc_src.bounds and 
                grid_src.width == lulc_src.width and 
                grid_src.height == lulc_src.height):
                print(f"  ✓ Grid and land use extents match")
            else:
                print(f"  ⚠️  Grid and land use extents don't match")
                print(f"     Grid: {grid_src.bounds}")
                print(f"     LULC: {lulc_src.bounds}")
    
    if all_good:
        print(f"  🎉 Setup verification passed!")
    else:
        print(f"  ❌ Setup verification failed!")
    
    return all_good

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python uk_processing_setup.py <uk_scenario.tif>")
        print("\nExample:")
        print('  python scenario_scripts/uk_processing_setup.py "scenarios/.../extensification_current_practices.tif"')
        sys.exit(1)
    
    scenario_file = sys.argv[1]
    
    if not Path(scenario_file).exists():
        print(f"Error: Scenario file not found: {scenario_file}")
        sys.exit(1)
    
    # Setup UK processing
    result = setup_uk_processing_environment(scenario_file)
    
    # Verify setup
    verify_uk_setup()
    
    print(f"\n🚀 Ready to run UK emissions processing!")
    print(f"   You can now run: python run_dust_emissions.py")
    print(f"   Or: python run_soil_nox_emissions.py")
    print(f"   Or: python run_deposition_calculation.py")