#!/usr/bin/env python3
"""
MERRA2 Data Cleaning Utility

This script removes unused variables from MERRA2 NetCDF files to save storage space.
Based on analysis of the land use emissions processor (LUEP) codebase, only three
variables are actually used:
- U10M: 10-meter eastward wind (dust emissions, deposition velocity)
- V10M: 10-meter northward wind (dust emissions, deposition velocity)  
- TS: Surface skin temperature (soil NOx emissions)

The script processes files one at a time to minimize memory usage and creates
cleaned versions with only the required variables.

Usage:
    python utils/clean_merra2_data.py <input_directory> <output_directory>
    python utils/clean_merra2_data.py inputs/MERRA2 inputs/MERRA2_cleaned

Requirements:
    - netCDF4 library
    - Original MERRA2 files in NetCDF format
    - NCO tools (ncks) installed for efficient variable extraction

Author: Generated for LUEP codebase
Date: December 2024
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import tempfile
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Required MERRA2 variables for LUEP
REQUIRED_VARS = ['U10M', 'V10M', 'TS']

def check_dependencies():
    """Check if required tools are available."""
    try:
        subprocess.run(['ncks', '--version'], capture_output=True, check=True)
        logger.info("NCO tools (ncks) found")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("NCO tools not found. Falling back to Python-only method.")
        return False

def get_file_variables(filepath):
    """Get list of variables in a NetCDF file using ncdump."""
    try:
        result = subprocess.run(
            ['ncdump', '-h', filepath], 
            capture_output=True, text=True, check=True
        )
        variables = []
        in_variables = False
        for line in result.stdout.split('\n'):
            if 'variables:' in line:
                in_variables = True
                continue
            if in_variables and line.strip().startswith('//'):
                break
            if in_variables and '(' in line and ')' in line:
                var_name = line.strip().split('(')[0].strip()
                if var_name and not var_name.startswith('//'):
                    variables.append(var_name)
        return variables
    except subprocess.CalledProcessError as e:
        logger.error(f"Error getting variables from {filepath}: {e}")
        return []

def clean_file_with_nco(input_file, output_file):
    """Clean MERRA2 file using NCO tools for efficient processing."""
    try:
        # Create variable list string for ncks
        var_list = ','.join(REQUIRED_VARS)
        
        # Use ncks to extract only required variables
        cmd = ['ncks', '-v', var_list, input_file, output_file]
        
        logger.info(f"Cleaning {os.path.basename(input_file)} with NCO...")
        subprocess.run(cmd, check=True, capture_output=True)
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"NCO cleaning failed for {input_file}: {e}")
        return False

def clean_file_with_python(input_file, output_file):
    """Clean MERRA2 file using Python netCDF4 library (fallback method)."""
    try:
        from netCDF4 import Dataset
        import numpy as np
        
        logger.info(f"Cleaning {os.path.basename(input_file)} with Python...")
        
        # Open input file
        with Dataset(input_file, 'r') as src:
            # Create output file
            with Dataset(output_file, 'w', format='NETCDF4') as dst:
                
                # Copy global attributes
                dst.setncatts(src.__dict__)
                
                # Copy dimensions
                for name, dimension in src.dimensions.items():
                    dst.createDimension(
                        name, len(dimension) if not dimension.isunlimited() else None
                    )
                
                # Copy coordinate variables (lat, lon, time, etc.)
                coord_vars = []
                for name, variable in src.variables.items():
                    if name in src.dimensions or name.lower() in ['lat', 'lon', 'time', 'lev']:
                        coord_vars.append(name)
                        
                        var_out = dst.createVariable(
                            name, variable.datatype, variable.dimensions
                        )
                        var_out.setncatts(variable.__dict__)
                        var_out[:] = variable[:]
                
                # Copy only required data variables
                for var_name in REQUIRED_VARS:
                    if var_name in src.variables:
                        variable = src.variables[var_name]
                        
                        var_out = dst.createVariable(
                            var_name, variable.datatype, variable.dimensions
                        )
                        var_out.setncatts(variable.__dict__)
                        
                        # Copy data in chunks to manage memory
                        var_out[:] = variable[:]
                        
                        logger.info(f"  Copied variable: {var_name}")
                    else:
                        logger.warning(f"  Required variable {var_name} not found in {input_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"Python cleaning failed for {input_file}: {e}")
        return False

def get_file_size_mb(filepath):
    """Get file size in MB."""
    return os.path.getsize(filepath) / (1024 * 1024)

def clean_merra2_directory(input_dir, output_dir, use_nco=True):
    """Clean all MERRA2 files in a directory."""
    
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    if not input_path.exists():
        logger.error(f"Input directory does not exist: {input_dir}")
        return False
    
    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all NetCDF files
    nc_files = list(input_path.glob("*.nc4")) + list(input_path.glob("*.nc"))
    
    if not nc_files:
        logger.error(f"No NetCDF files found in {input_dir}")
        return False
    
    logger.info(f"Found {len(nc_files)} NetCDF files to process")
    
    total_size_before = 0
    total_size_after = 0
    successful_files = 0
    
    for nc_file in nc_files:
        input_file = str(nc_file)
        output_file = str(output_path / nc_file.name)
        
        # Skip if output file already exists
        if os.path.exists(output_file):
            logger.info(f"Skipping {nc_file.name} - output already exists")
            continue
        
        # Get original file size
        size_before = get_file_size_mb(input_file)
        total_size_before += size_before
        
        # Show variables in first file for verification
        if successful_files == 0:
            logger.info("Checking variables in first file...")
            variables = get_file_variables(input_file)
            logger.info(f"Original variables: {variables}")
            logger.info(f"Will keep only: {REQUIRED_VARS}")
        
        # Clean the file
        success = False
        if use_nco:
            success = clean_file_with_nco(input_file, output_file)
        
        if not success:
            logger.info("Falling back to Python method...")
            success = clean_file_with_python(input_file, output_file)
        
        if success:
            size_after = get_file_size_mb(output_file)
            total_size_after += size_after
            reduction = ((size_before - size_after) / size_before) * 100
            
            logger.info(
                f"✅ {nc_file.name}: {size_before:.1f}MB → {size_after:.1f}MB "
                f"({reduction:.1f}% reduction)"
            )
            successful_files += 1
        else:
            logger.error(f"❌ Failed to clean {nc_file.name}")
    
    # Summary
    if successful_files > 0:
        total_reduction = ((total_size_before - total_size_after) / total_size_before) * 100
        logger.info(f"\n🎉 Processing complete!")
        logger.info(f"Files processed: {successful_files}/{len(nc_files)}")
        logger.info(f"Total size reduction: {total_size_before:.1f}MB → {total_size_after:.1f}MB")
        logger.info(f"Space saved: {total_size_before - total_size_after:.1f}MB ({total_reduction:.1f}%)")
    
    return successful_files > 0

def main():
    """Main function."""
    if len(sys.argv) != 3:
        print("Usage: python utils/clean_merra2_data.py <input_directory> <output_directory>")
        print("\nExample:")
        print("  python utils/clean_merra2_data.py inputs/MERRA2 inputs/MERRA2_cleaned")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    logger.info("MERRA2 Data Cleaning Utility")
    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Required variables: {REQUIRED_VARS}")
    
    # Check dependencies
    use_nco = check_dependencies()
    
    if not use_nco:
        try:
            import netCDF4
        except ImportError:
            logger.error("Neither NCO tools nor netCDF4 Python library found!")
            logger.error("Please install either:")
            logger.error("  - NCO tools: conda install nco  or  apt-get install nco")
            logger.error("  - netCDF4: pip install netCDF4")
            sys.exit(1)
    
    # Clean the directory
    success = clean_merra2_directory(input_dir, output_dir, use_nco)
    
    if not success:
        logger.error("Cleaning process failed!")
        sys.exit(1)
    
    logger.info("All done! 🎉")

if __name__ == "__main__":
    main()