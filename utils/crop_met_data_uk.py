#!/usr/bin/env python3
"""
UK Meteorological Data Preprocessor

This script crops global meteorological data (MERRA2 and GHAP PM2.5) to UK extent
for efficient deposition processing. The cropped data is cached and reused across
all UK scenarios.

Key features:
- One-time preprocessing for all UK scenarios
- Preserves original global data
- Validates cache completeness
- Dramatic performance improvement for UK processing

Usage:
    python utils/crop_met_data_uk.py                    # Process all data
    python utils/crop_met_data_uk.py --force-rebuild   # Force recreation
    python utils/crop_met_data_uk.py --check-only      # Only validate cache

Important: Run with the rasters conda environment:
    /Users/sumilthakrar/yes/envs/rasters/bin/python utils/crop_met_data_uk.py
"""

import os
import sys
import xarray as xr
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import shutil
from glob import glob
import hashlib
import pygeoprocessing.geoprocessing as geop

def get_uk_bounds():
    """
    Get UK extent from grid.tif reference file
    
    Returns:
        dict: UK bounding box coordinates
    """
    
    grid_file = "grid.tif"
    if not os.path.exists(grid_file):
        raise FileNotFoundError(f"UK grid reference file not found: {grid_file}")
    
    grid_info = geop.get_raster_info(grid_file)
    bbox = grid_info['bounding_box']
    
    uk_bounds = {
        'lon_min': bbox[0],  # left
        'lat_min': bbox[1],  # bottom  
        'lon_max': bbox[2],  # right
        'lat_max': bbox[3]   # top
    }
    
    print(f"UK bounds: {uk_bounds['lon_min']:.3f}°W to {uk_bounds['lon_max']:.3f}°E, "
          f"{uk_bounds['lat_min']:.3f}°N to {uk_bounds['lat_max']:.3f}°N")
    
    return uk_bounds

def create_cache_directories():
    """Create cache directory structure if it doesn't exist"""
    
    cache_dirs = [
        "inputs/uk_cropped",
        "inputs/uk_cropped/MERRA2", 
        "inputs/uk_cropped/concentrations"
    ]
    
    for cache_dir in cache_dirs:
        os.makedirs(cache_dir, exist_ok=True)
        print(f"Created cache directory: {cache_dir}")

def get_expected_files():
    """
    Get lists of expected MERRA2 and PM2.5 files for 2021
    
    Returns:
        tuple: (merra2_files, pm25_files)
    """
    
    # Generate expected daily MERRA2 files for 2021 (both 400 and 401 patterns)
    start_date = datetime(2021, 1, 1)
    end_date = datetime(2021, 12, 31)
    
    merra2_files = []
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        # Check for both MERRA2_400 and MERRA2_401 patterns
        for version in ["400", "401"]:
            expected_file = f"inputs/MERRA2/MERRA2_{version}.tavg1_2d_slv_Nx.{date_str}.nc4"
            if os.path.exists(expected_file):
                merra2_files.append(expected_file)
                break  # Use first one found
        current_date += timedelta(days=1)
    
    # Generate expected monthly PM2.5 files for 2021
    pm25_files = []
    for month in range(1, 13):
        expected_file = f"inputs/concentrations/GHAP_PM2.5_M1K_2021{month:02d}_V1.nc"
        pm25_files.append(expected_file)
    
    return merra2_files, pm25_files

def check_uk_met_cache():
    """
    Check if UK meteorological cache is complete and up-to-date
    
    Returns:
        tuple: (cache_valid, missing_files, cache_info)
    """
    
    print("Checking UK meteorological data cache...")
    
    # Check if cache directories exist
    cache_base = "inputs/uk_cropped"
    if not os.path.exists(cache_base):
        return False, ["Cache directory missing"], {}
    
    # Get expected files
    merra2_files, pm25_files = get_expected_files()
    
    # Check MERRA2 cache files
    missing_files = []
    for original_file in merra2_files:
        if os.path.exists(original_file):
            date_str = os.path.basename(original_file).split('.')[3]  # Extract YYYYMMDD
            cache_file = f"inputs/uk_cropped/MERRA2/MERRA2_uk_{date_str}.nc"
            if not os.path.exists(cache_file):
                missing_files.append(f"MERRA2_uk_{date_str}.nc")
    
    # Check PM2.5 cache files  
    for original_file in pm25_files:
        if os.path.exists(original_file):
            month_str = os.path.basename(original_file).split('_')[3]  # Extract 202101
            cache_file = f"inputs/uk_cropped/concentrations/GHAP_PM2.5_uk_{month_str}.nc"
            if not os.path.exists(cache_file):
                missing_files.append(f"GHAP_PM2.5_uk_{month_str}.nc")
    
    # Read cache info if available
    cache_info = {}
    cache_info_file = f"{cache_base}/.cache_info.txt"
    if os.path.exists(cache_info_file):
        with open(cache_info_file, 'r') as f:
            for line in f:
                if ':' in line:
                    key, value = line.strip().split(':', 1)
                    cache_info[key.strip()] = value.strip()
    
    cache_valid = len(missing_files) == 0
    
    if cache_valid:
        print(f"✅ UK meteorological cache is complete")
        if cache_info:
            print(f"   Created: {cache_info.get('Created', 'Unknown')}")
            print(f"   Files: {cache_info.get('Files', 'Unknown')}")
    else:
        print(f"⚠️  UK meteorological cache incomplete: {len(missing_files)} missing files")
        if len(missing_files) <= 5:
            for missing in missing_files:
                print(f"   - {missing}")
        else:
            print(f"   - {missing_files[0]} ... and {len(missing_files)-1} more")
    
    return cache_valid, missing_files, cache_info

def crop_merra2_to_uk(uk_bounds, force_rebuild=False):
    """
    Crop all MERRA2 files to UK extent
    
    Args:
        uk_bounds: UK bounding box coordinates
        force_rebuild: Force recreation of cache files
    """
    
    print("\n" + "="*60)
    print("CROPPING MERRA2 DATA TO UK EXTENT")
    print("="*60)
    
    # Get list of available MERRA2 files (single-level data with wind components)
    # Include both MERRA2_400 and MERRA2_401 patterns
    merra2_patterns = [
        "inputs/MERRA2/MERRA2_400.tavg1_2d_slv_Nx.*.nc4",
        "inputs/MERRA2/MERRA2_401.tavg1_2d_slv_Nx.*.nc4"
    ]
    available_files = []
    for pattern in merra2_patterns:
        available_files.extend(glob(pattern))
    available_files = sorted(available_files)
    
    if not available_files:
        print(f"❌ No MERRA2 files found matching patterns: {merra2_patterns}")
        return False
    
    print(f"Found {len(available_files)} MERRA2 files to process")
    
    output_dir = "inputs/uk_cropped/MERRA2"
    os.makedirs(output_dir, exist_ok=True)
    
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    for i, input_file in enumerate(available_files):
        try:
            # Extract date from filename: MERRA2_400.tavg1_2d_slv_Nx.YYYYMMDD.nc4
            filename = os.path.basename(input_file)
            parts = filename.split('.')
            if len(parts) >= 4:
                date_str = parts[2]  # YYYYMMDD is at index 2
            else:
                print(f"  ⚠️  Unexpected filename format: {filename}")
                continue
            output_file = os.path.join(output_dir, f"MERRA2_uk_{date_str}.nc")
            
            # Skip if output exists and not forcing rebuild
            if os.path.exists(output_file) and not force_rebuild:
                skipped_count += 1
                if (i + 1) % 50 == 0:  # Progress every 50 files
                    print(f"  Progress: {i+1}/{len(available_files)} files ({skipped_count} skipped)")
                continue
            
            # Open and crop the file
            with xr.open_dataset(input_file) as ds:
                # Check if latitude is decreasing (North to South) and adjust slicing accordingly
                if ds.lat[0] > ds.lat[1]:
                    # Latitude decreases from North to South (90 to -90)
                    uk_cropped = ds.sel(
                        lat=slice(uk_bounds['lat_max'], uk_bounds['lat_min']),  # Reversed for decreasing lat
                        lon=slice(uk_bounds['lon_min'], uk_bounds['lon_max'])
                    )
                else:
                    # Latitude increases from South to North (-90 to 90)
                    uk_cropped = ds.sel(
                        lat=slice(uk_bounds['lat_min'], uk_bounds['lat_max']),
                        lon=slice(uk_bounds['lon_min'], uk_bounds['lon_max'])
                    )
                
                # Save cropped data
                uk_cropped.to_netcdf(output_file, 
                                   encoding={'U10M': {'zlib': True, 'complevel': 6},
                                           'V10M': {'zlib': True, 'complevel': 6}})
            
            processed_count += 1
            
            # Progress reporting
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i+1}/{len(available_files)} files ({processed_count} processed, {skipped_count} skipped)")
                
        except Exception as e:
            print(f"  ❌ Error processing {filename}: {e}")
            error_count += 1
            continue
    
    print(f"\nMERRA2 processing complete:")
    print(f"  ✅ Processed: {processed_count} files")
    print(f"  ⏭️  Skipped: {skipped_count} files")
    if error_count > 0:
        print(f"  ❌ Errors: {error_count} files")
    
    return error_count == 0

def crop_pm25_to_uk(uk_bounds, force_rebuild=False):
    """
    Crop all GHAP PM2.5 files to UK extent
    
    Args:
        uk_bounds: UK bounding box coordinates  
        force_rebuild: Force recreation of cache files
    """
    
    print("\n" + "="*60)
    print("CROPPING PM2.5 DATA TO UK EXTENT")
    print("="*60)
    
    # Get list of available PM2.5 files
    pm25_pattern = "inputs/concentrations/GHAP_PM2.5_*.nc"
    available_files = sorted(glob(pm25_pattern))
    
    if not available_files:
        print(f"❌ No PM2.5 files found matching pattern: {pm25_pattern}")
        return False
    
    print(f"Found {len(available_files)} PM2.5 files to process")
    
    output_dir = "inputs/uk_cropped/concentrations"
    os.makedirs(output_dir, exist_ok=True)
    
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    for i, input_file in enumerate(available_files):
        try:
            # Extract month from filename
            filename = os.path.basename(input_file)
            month_str = filename.split('_')[3]  # 202101, 202102, etc.
            output_file = os.path.join(output_dir, f"GHAP_PM2.5_uk_{month_str}.nc")
            
            # Skip if output exists and not forcing rebuild
            if os.path.exists(output_file) and not force_rebuild:
                skipped_count += 1
                continue
            
            # Open and crop the file
            with xr.open_dataset(input_file) as ds:
                # Check if latitude is decreasing (North to South) and adjust slicing accordingly
                if ds.lat[0] > ds.lat[1]:
                    # Latitude decreases from North to South (90 to -90)
                    uk_cropped = ds.sel(
                        lat=slice(uk_bounds['lat_max'], uk_bounds['lat_min']),  # Reversed for decreasing lat
                        lon=slice(uk_bounds['lon_min'], uk_bounds['lon_max'])
                    )
                else:
                    # Latitude increases from South to North (-90 to 90)
                    uk_cropped = ds.sel(
                        lat=slice(uk_bounds['lat_min'], uk_bounds['lat_max']),
                        lon=slice(uk_bounds['lon_min'], uk_bounds['lon_max'])
                    )
                
                # Save cropped data
                uk_cropped.to_netcdf(output_file,
                                   encoding={'PM2.5': {'zlib': True, 'complevel': 6}})
            
            processed_count += 1
            print(f"  ✅ Processed: {filename} → GHAP_PM2.5_uk_{month_str}.nc")
                
        except Exception as e:
            print(f"  ❌ Error processing {filename}: {e}")
            error_count += 1
            continue
    
    print(f"\nPM2.5 processing complete:")
    print(f"  ✅ Processed: {processed_count} files")
    print(f"  ⏭️  Skipped: {skipped_count} files")
    if error_count > 0:
        print(f"  ❌ Errors: {error_count} files")
    
    return error_count == 0

def create_cache_info(uk_bounds):
    """Create cache information file"""
    
    cache_info_file = "inputs/uk_cropped/.cache_info.txt"
    
    # Count cache files
    merra2_cache_files = glob("inputs/uk_cropped/MERRA2/MERRA2_uk_*.nc")
    pm25_cache_files = glob("inputs/uk_cropped/concentrations/GHAP_PM2.5_uk_*.nc")
    total_files = len(merra2_cache_files) + len(pm25_cache_files)
    
    with open(cache_info_file, 'w') as f:
        f.write("UK Meteorological Data Cache\n")
        f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"UK Bounds: {uk_bounds['lon_min']:.2f}, {uk_bounds['lat_min']:.2f}, {uk_bounds['lon_max']:.2f}, {uk_bounds['lat_max']:.2f}\n")
        f.write(f"Files: {len(merra2_cache_files)} MERRA2 + {len(pm25_cache_files)} PM2.5 = {total_files} total\n")
        f.write(f"Status: Complete\n")
        f.write(f"MERRA2 files: {len(merra2_cache_files)}\n")
        f.write(f"PM2.5 files: {len(pm25_cache_files)}\n")
    
    print(f"✅ Created cache info: {cache_info_file}")

def main():
    """Main function"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Crop meteorological data to UK extent")
    parser.add_argument("--force-rebuild", action="store_true", 
                       help="Force recreation of cache files")
    parser.add_argument("--check-only", action="store_true",
                       help="Only check cache status, don't process")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("UK METEOROLOGICAL DATA PREPROCESSOR")
    print("=" * 80)
    print()
    
    try:
        # Get UK bounds
        uk_bounds = get_uk_bounds()
        
        # Create cache directories
        create_cache_directories()
        
        # Check current cache status
        cache_valid, missing_files, cache_info = check_uk_met_cache()
        
        if args.check_only:
            print(f"\nCache status check complete.")
            if cache_valid:
                print("✅ Cache is complete and ready for use")
            else:
                print(f"⚠️  Cache needs {len(missing_files)} files")
            return
        
        # Skip processing if cache is valid and not forcing rebuild
        if cache_valid and not args.force_rebuild:
            print("\n✅ UK meteorological cache is already complete!")
            print("Use --force-rebuild to recreate cache files")
            return
        
        print(f"\nStarting UK meteorological data preprocessing...")
        if args.force_rebuild:
            print("🔄 Force rebuild enabled - recreating all cache files")
        
        # Process MERRA2 data
        merra2_success = crop_merra2_to_uk(uk_bounds, args.force_rebuild)
        
        # Process PM2.5 data
        pm25_success = crop_pm25_to_uk(uk_bounds, args.force_rebuild)
        
        # Create cache info file
        if merra2_success and pm25_success:
            create_cache_info(uk_bounds)
            
            print(f"\n🎉 UK meteorological data preprocessing complete!")
            print(f"📁 Cache location: inputs/uk_cropped/")
            print(f"💾 This one-time preprocessing will speed up all UK scenario processing")
            
            # Final validation
            cache_valid, missing_files, cache_info = check_uk_met_cache()
            if cache_valid:
                print(f"✅ Cache validation successful")
            else:
                print(f"⚠️  Cache validation found {len(missing_files)} missing files")
        else:
            print(f"\n❌ Preprocessing completed with errors")
            print(f"Some files may not have been processed correctly")
    
    except Exception as e:
        print(f"\n❌ Preprocessing error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()