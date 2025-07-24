#!/usr/bin/env python3
"""
Debug the alignment process step by step
"""
import rasterio
import numpy as np
import netCDF4
import os
import pygeoprocessing.geoprocessing as geop
from rasterio.transform import from_bounds

# Load reference emissions data
print("=== Loading Reference Emissions ===")
with netCDF4.Dataset('inputs/grass-bvoc.nc', 'r') as nc:
    ref_lat = nc.variables['lat'][:]
    ref_lon = nc.variables['lon'][:]
    ref_data = nc.variables['bvoc'][:]

print(f"Reference grid: {len(ref_lat)} x {len(ref_lon)}")
print(f"Lat: {ref_lat.min():.3f} to {ref_lat.max():.3f}")
print(f"Lon: {ref_lon.min():.3f} to {ref_lon.max():.3f}")

# Create the reference raster exactly as in our code
print("\n=== Creating Reference Raster ===")
temp_ref_path = "debug_reference_grid.tif"
ref_transform = from_bounds(
    ref_lon.min(), ref_lat.min(), 
    ref_lon.max(), ref_lat.max(),
    len(ref_lon), len(ref_lat)
)

with rasterio.open(temp_ref_path, 'w', 
                  driver='GTiff', 
                  height=len(ref_lat), 
                  width=len(ref_lon),
                  count=1, 
                  dtype='float32',
                  crs='EPSG:4326',
                  transform=ref_transform) as dst:
    dst.write(np.ones((len(ref_lat), len(ref_lon)), dtype=np.float32), 1)

# Check what we created
print("Created reference raster:")
with rasterio.open(temp_ref_path) as src:
    print(f"  Bounds: {src.bounds}")
    print(f"  Transform: {src.transform}")
    print(f"  Shape: {src.shape}")

# Align the UK data to this reference
print("\n=== Aligning UK Data ===")
aligned_path = "debug_aligned_landuse.tif"
scenario_path = "inputs/gblulcg20_10000.tif"

geop.align_and_resize_raster_stack(
    [scenario_path],
    [aligned_path],
    ['near'],
    geop.get_raster_info(temp_ref_path)['pixel_size'],
    bounding_box_mode=geop.get_raster_info(temp_ref_path)['bounding_box'],
    target_projection_wkt=geop.get_raster_info(temp_ref_path)['projection_wkt']
)

# Check the aligned result
print("Aligned result:")
with rasterio.open(aligned_path) as src:
    aligned_data = src.read(1)
    print(f"  Bounds: {src.bounds}")
    print(f"  Transform: {src.transform}")
    print(f"  Shape: {src.shape}")
    
    # Find where land use pixels ended up
    uk_pixels = (aligned_data == 1) | (aligned_data == 2) | (aligned_data == 3)
    if np.any(uk_pixels):
        uk_indices = np.where(uk_pixels)
        rows = uk_indices[0]
        cols = uk_indices[1]
        print(f"  UK pixels found at rows {rows.min()}-{rows.max()}, cols {cols.min()}-{cols.max()}")
        
        # Convert to geographic coordinates
        lons, lats = rasterio.transform.xy(src.transform, rows, cols)
        lats = np.array(lats)
        lons = np.array(lons)
        print(f"  Geographic range: Lat {lats.min():.1f} to {lats.max():.1f}, Lon {lons.min():.1f} to {lons.max():.1f}")
    else:
        print("  No UK pixels found!")

# Cleanup
os.remove(temp_ref_path)
os.remove(aligned_path)