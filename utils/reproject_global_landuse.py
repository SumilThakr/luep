#!/usr/bin/env python3
"""
Reproject Global Land Use to WGS84

This script reprojects the global IGBP land use data from Interrupted Goode Homolosine
to WGS84 geographic coordinates to avoid PROJ library conflicts.

Usage:
    cd /Users/sumilthakrar/Desktop/UK/luep
    source ~/.bashrc && /Users/sumilthakrar/yes/envs/luep-analysis/bin/python utils/reproject_global_landuse.py

Input:  inputs/gblulcg20_10000.tif (Interrupted Goode Homolosine)
Output: inputs/gblulcg20_10000_wgs84.tif (WGS84 Geographic)
"""

import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.crs import CRS
import numpy as np
from pathlib import Path
import os

def reproject_to_wgs84():
    """
    Reproject global land use data from Interrupted Goode Homolosine to WGS84.
    This avoids complex projection transformations that cause PROJ library conflicts.
    """
    
    # Ensure we're in the project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    input_file = "inputs/gblulcg20_10000.tif"
    output_file = "inputs/gblulcg20_10000_wgs84.tif" 
    backup_file = "inputs/gblulcg20_10000_goode.tif"
    
    print(f"🌍 Reprojecting global land use data to WGS84")
    print(f"   Working directory: {os.getcwd()}")
    print(f"   Input:  {input_file} (Interrupted Goode Homolosine)")
    print(f"   Output: {output_file} (WGS84 Geographic)")
    
    # Check input file exists
    if not Path(input_file).exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Backup original file
    if not Path(backup_file).exists():
        print(f"   Backing up original to: {backup_file}")
        import shutil
        shutil.copy2(input_file, backup_file)
    
    # Define target CRS (WGS84)
    dst_crs = CRS.from_epsg(4326)  # WGS84 Geographic
    
    with rasterio.open(input_file) as src:
        print(f"\n📊 Source data properties:")
        print(f"   CRS: {src.crs}")
        print(f"   Dimensions: {src.width} x {src.height}")
        print(f"   Bounds: {src.bounds}")
        print(f"   Data type: {src.dtypes[0]}")
        
        # Calculate transform and dimensions for WGS84
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds)
        
        print(f"\n📊 Target data properties:")
        print(f"   CRS: {dst_crs}")
        print(f"   Dimensions: {width} x {height}")
        print(f"   Transform: {transform}")
        
        # Create output profile
        kwargs = src.profile.copy()
        kwargs.update({
            'crs': dst_crs,
            'transform': transform,
            'width': width,
            'height': height,
            'compress': 'lzw',
            'tiled': False
        })
        
        # Perform reprojection
        print(f"\n🔄 Reprojecting data...")
        with rasterio.open(output_file, 'w', **kwargs) as dst:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=dst_crs,
                resampling=Resampling.nearest  # Use nearest neighbor for categorical land use data
            )
            
            # Add metadata
            dst.set_band_description(1, "IGBP Land Use - WGS84 Reprojection")
            dst.update_tags(1, **{
                'title': 'Global IGBP Land Use (WGS84)',
                'description': 'Global land use reprojected from Interrupted Goode Homolosine to WGS84',
                'original_projection': str(src.crs),
                'target_projection': str(dst_crs),
                'resampling_method': 'nearest_neighbor',
                'created_by': 'utils/reproject_global_landuse.py',
                'source_file': input_file
            })
    
    print(f"\n✅ Reprojection completed successfully!")
    print(f"   Output saved to: {output_file}")
    print(f"   File size: {Path(output_file).stat().st_size / 1024 / 1024:.1f} MB")
    
    # Verify WGS84 extent
    with rasterio.open(output_file) as reprojected:
        bounds = reprojected.bounds
        print(f"\n🌍 WGS84 extent:")
        print(f"   Longitude: {bounds.left:.2f}° to {bounds.right:.2f}°")
        print(f"   Latitude: {bounds.bottom:.2f}° to {bounds.top:.2f}°")
        
        # Check if it covers most of the globe
        lon_range = bounds.right - bounds.left
        lat_range = bounds.top - bounds.bottom
        
        if lon_range > 350 and lat_range > 170:
            print(f"   ✅ Global coverage confirmed")
        else:
            print(f"   ⚠️  Coverage: {lon_range:.1f}° longitude x {lat_range:.1f}° latitude")
    
    return output_file

def update_landuse_file():
    """
    Replace the original land use file with the WGS84 version for processing.
    """
    
    original_file = "inputs/gblulcg20_10000.tif"
    wgs84_file = "inputs/gblulcg20_10000_wgs84.tif"
    
    if Path(wgs84_file).exists():
        print(f"\n🔄 Updating land use file for processing:")
        print(f"   Replacing: {original_file}")
        print(f"   With: {wgs84_file}")
        
        import shutil
        shutil.copy2(wgs84_file, original_file)
        
        print(f"   ✅ Land use file updated to WGS84 version")
        
        # Also update grid.tif to match
        shutil.copy2(original_file, "grid.tif")
        print(f"   ✅ Grid reference updated to match")
    else:
        print(f"   ❌ WGS84 file not found: {wgs84_file}")

if __name__ == "__main__":
    try:
        # Reproject to WGS84
        output_file = reproject_to_wgs84()
        
        # Update files for processing
        update_landuse_file()
        
        print(f"\n🚀 Ready for dust processing with WGS84 coordinates!")
        print(f"   No more PROJ library conflicts expected")
        print(f"   Next step: python run_dust_emissions_land_use_dependent_only.py")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()