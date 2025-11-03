#!/usr/bin/env python3
"""
Create Global Grid Reference for Dust Processing

This script creates a grid.tif reference file that matches the extent and resolution
of the global land use data, replacing the UK-specific grid that was limiting processing
to UK extent.

Usage:
    python create_global_grid.py

Input:  inputs/gblulcg20_10000.tif (global IGBP land use)
Output: grid.tif (global grid reference for dust processing)
"""

import rasterio
import numpy as np
from pathlib import Path

def create_global_grid():
    """
    Create a global grid reference file from the global land use data.
    This ensures dust processing covers the full global extent.
    """
    
    input_file = "inputs/gblulcg20_10000.tif"
    output_file = "grid.tif"
    backup_file = "grid_uk_backup.tif"
    
    print(f"🌍 Creating global grid reference for dust processing")
    print(f"   Input:  {input_file}")
    print(f"   Output: {output_file}")
    
    # Check input file exists
    if not Path(input_file).exists():
        raise FileNotFoundError(f"Global land use file not found: {input_file}")
    
    # Backup existing grid if it exists
    if Path(output_file).exists():
        print(f"   Backing up existing grid to: {backup_file}")
        import shutil
        shutil.copy2(output_file, backup_file)
    
    # Read global land use data to get extent/resolution
    with rasterio.open(input_file) as src:
        print(f"\n📊 Global land use data properties:")
        print(f"   Dimensions: {src.width} x {src.height}")
        print(f"   CRS: {src.crs}")
        print(f"   Bounds: {src.bounds}")
        print(f"   Transform: {src.transform}")
        print(f"   Data type: {src.dtypes[0]}")
        
        # Get profile for output
        profile = src.profile.copy()
        
        # Create a simple grid (all pixels = 1) with same properties
        grid_data = np.ones((src.height, src.width), dtype=np.uint8)
        
        # Update profile for grid file
        profile.update({
            'dtype': 'uint8',
            'count': 1,
            'compress': 'lzw',
            'driver': 'GTiff',
            'tiled': False,
            'interleave': 'band'
        })
        
        # Write grid reference file
        with rasterio.open(output_file, 'w', **profile) as dst:
            dst.write(grid_data, 1)
            
            # Add metadata
            dst.set_band_description(1, "Global Grid Reference for Dust Processing")
            dst.update_tags(1, **{
                'title': 'Global Grid Reference',
                'description': 'Grid reference file matching global land use extent for dust emissions processing',
                'created_by': 'create_global_grid.py',
                'source_file': input_file,
                'purpose': 'Spatial reference for pygeoprocessing alignment in dust calculations'
            })
    
    print(f"\n✅ Global grid reference created successfully!")
    print(f"   Output saved to: {output_file}")
    print(f"   File size: {Path(output_file).stat().st_size / 1024:.1f} KB")
    
    # Verify global extent
    with rasterio.open(output_file) as grid:
        bounds = grid.bounds
        width_deg = bounds.right - bounds.left
        height_deg = bounds.top - bounds.bottom
        print(f"\n🌍 Grid covers global extent:")
        print(f"   Longitude: {bounds.left:.2f}° to {bounds.right:.2f}° ({width_deg:.1f}° wide)")
        print(f"   Latitude: {bounds.bottom:.2f}° to {bounds.top:.2f}° ({height_deg:.1f}° tall)")
        
        if width_deg > 350 and height_deg > 170:
            print(f"   ✅ Confirmed: Global coverage achieved")
        else:
            print(f"   ⚠️  Warning: Coverage may not be fully global")
    
    return output_file

if __name__ == "__main__":
    try:
        # Create global grid reference
        output_file = create_global_grid()
        
        print(f"\n🚀 Ready for global dust processing!")
        print(f"   Grid reference: {output_file}")
        print(f"   Next step: Run dust processing with global extent")
        print(f"   Command: python run_dust_emissions.py")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()