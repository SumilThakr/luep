#!/usr/bin/env python3
"""
Debug SMOPS Ocean Values

This script examines a SMOPS input file to understand:
1. What fill values are used for ocean areas
2. What the actual data values are over ocean pixels
3. How the dry mask logic behaves with these values

This will help diagnose why sm_*.tif files show value 1 over ocean areas.
"""

import numpy as np
from netCDF4 import Dataset
import os
from pathlib import Path

def debug_smops_file():
    """Debug SMOPS file to understand ocean fill values"""
    
    # Find a SMOPS file to examine
    smops_dir = Path("inputs/SMOPS")
    if not smops_dir.exists():
        print(f"❌ SMOPS directory not found: {smops_dir}")
        return
    
    # Get first available SMOPS file
    smops_files = list(smops_dir.glob("NPR_SMOPS_CMAP_D*.nc"))
    if not smops_files:
        print(f"❌ No SMOPS files found in {smops_dir}")
        return
    
    smops_file = smops_files[0]
    print(f"🔍 Examining SMOPS file: {smops_file.name}")
    print("=" * 60)
    
    try:
        with Dataset(smops_file, 'r') as ncfile:
            
            # 1. Examine the Blended_SM variable metadata
            sm_var = ncfile.variables['Blended_SM']
            print(f"📊 SMOPS Variable Info:")
            print(f"   Variable name: Blended_SM")
            print(f"   Shape: {sm_var.shape}")
            print(f"   Data type: {sm_var.dtype}")
            
            # Check for fill value attributes
            attrs_to_check = ['_FillValue', 'missing_value', 'fill_value', 'invalid_range']
            for attr in attrs_to_check:
                if hasattr(sm_var, attr):
                    print(f"   {attr}: {getattr(sm_var, attr)}")
            
            # Check for valid range
            if hasattr(sm_var, 'valid_min') and hasattr(sm_var, 'valid_max'):
                print(f"   Valid range: {sm_var.valid_min} to {sm_var.valid_max}")
            
            print()
            
            # 2. Read the actual data
            print(f"📥 Reading soil moisture data...")
            sm_data = sm_var[:]
            
            print(f"   Data shape: {sm_data.shape}")
            print(f"   Data type: {sm_data.dtype}")
            print(f"   Data range: {np.nanmin(sm_data)} to {np.nanmax(sm_data)}")
            
            # 3. Check for special values
            print(f"\n🔍 Special Value Analysis:")
            
            # Count NaN values
            nan_count = np.sum(np.isnan(sm_data))
            total_pixels = sm_data.size
            print(f"   NaN values: {nan_count:,} / {total_pixels:,} ({nan_count/total_pixels*100:.1f}%)")
            
            # Check for negative values
            negative_count = np.sum(sm_data < 0)
            print(f"   Negative values: {negative_count:,}")
            
            # Check for values > 1 (soil moisture should be 0-1)
            high_count = np.sum(sm_data > 1)
            print(f"   Values > 1.0: {high_count:,}")
            
            # Check for exact zero values
            zero_count = np.sum(sm_data == 0.0)
            print(f"   Exact zero values: {zero_count:,}")
            
            # 4. Sample specific pixels (likely ocean areas)
            print(f"\n🌊 Sample Pixel Values (likely ocean areas):")
            
            # Top-left corner (likely ocean for global data)
            sample_regions = [
                ("Top-left (0:5, 0:5)", sm_data[0:5, 0:5]),
                ("Top-right (0:5, -5:)", sm_data[0:5, -5:]),
                ("Bottom-left (-5:, 0:5)", sm_data[-5:, 0:5]),
                ("Center (around mid-point)", sm_data[sm_data.shape[0]//2:sm_data.shape[0]//2+3, 
                                                    sm_data.shape[1]//2:sm_data.shape[1]//2+3])
            ]
            
            for region_name, region_data in sample_regions:
                print(f"\n   {region_name}:")
                print(f"   Values: {region_data.flatten()}")
                
                # Test dry mask logic on these values
                dry_mask_sample = region_data < 0.1
                print(f"   Dry mask (< 0.1): {dry_mask_sample.flatten()}")
            
            # 5. Test the actual dry mask logic from the dust script
            print(f"\n🎯 Testing Full Dry Mask Logic:")
            dry_mask = sm_data < 0.1
            dry_pixels = np.sum(dry_mask)
            print(f"   Pixels marked as 'dry' (< 0.1): {dry_pixels:,} / {total_pixels:,} ({dry_pixels/total_pixels*100:.1f}%)")
            
            # Check unique values in the dry mask
            unique_in_mask = np.unique(dry_mask)
            print(f"   Unique values in dry mask: {unique_in_mask}")
            
            # 6. Geographic context (if coordinate info available)
            if 'lat' in ncfile.variables and 'lon' in ncfile.variables:
                lats = ncfile.variables['lat'][:]
                lons = ncfile.variables['lon'][:]
                print(f"\n🗺️  Geographic Info:")
                print(f"   Latitude range: {np.min(lats):.2f} to {np.max(lats):.2f}")
                print(f"   Longitude range: {np.min(lons):.2f} to {np.max(lons):.2f}")
                
                # Sample ocean coordinates (e.g., Atlantic Ocean)
                ocean_lat_idx = np.where((lats >= 40) & (lats <= 50))[0]
                ocean_lon_idx = np.where((lons >= -40) & (lons <= -20))[0]
                
                if len(ocean_lat_idx) > 0 and len(ocean_lon_idx) > 0:
                    ocean_sample = sm_data[ocean_lat_idx[0]:ocean_lat_idx[0]+3, 
                                          ocean_lon_idx[0]:ocean_lon_idx[0]+3]
                    print(f"   Sample Atlantic Ocean area: {ocean_sample.flatten()}")
            
    except Exception as e:
        print(f"❌ Error reading SMOPS file: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🌊 SMOPS Ocean Fill Value Debug")
    print("=" * 60)
    debug_smops_file()