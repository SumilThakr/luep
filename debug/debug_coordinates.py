#!/usr/bin/env python3
"""
Debug coordinate system issues
"""
import netCDF4
import rasterio
import numpy as np
from rasterio.transform import from_bounds

print("=== UK Input File ===")
with rasterio.open('inputs/gblulcg20_10000.tif') as src:
    print(f"Bounds: {src.bounds}")
    print(f"Transform: {src.transform}")
    print(f"CRS: {src.crs}")
    print(f"Shape: {src.shape}")

print("\n=== bVOC Reference Grid ===")
with netCDF4.Dataset('inputs/grass-bvoc.nc', 'r') as nc:
    lat = nc.variables['lat'][:]
    lon = nc.variables['lon'][:]
    print(f"Lat: {lat.min():.3f} to {lat.max():.3f}")
    print(f"Lon: {lon.min():.3f} to {lon.max():.3f}")
    print(f"Shape: {len(lat)} x {len(lon)}")
    
    # Create transform like we do in the code
    ref_transform = from_bounds(
        lon.min(), lat.min(), 
        lon.max(), lat.max(),
        len(lon), len(lat)
    )
    print(f"Created transform: {ref_transform}")
    
    # Test coordinate conversion
    test_row, test_col = 360, 575  # Approximate center
    test_lon, test_lat = ref_transform * (test_col, test_row)
    print(f"Test pixel ({test_row}, {test_col}) -> ({test_lat:.3f}, {test_lon:.3f})")
    
    # Compare with direct lookup
    direct_lat = lat[test_row]
    direct_lon = lon[test_col]
    print(f"Direct lookup: ({direct_lat:.3f}, {direct_lon:.3f})")

print("\n=== Check UK region in bVOC grid ===")
# Find indices for UK region
uk_lat_indices = np.where((lat >= 49) & (lat <= 61))[0]
uk_lon_indices = np.where((lon >= -9) & (lon <= 2))[0]

if len(uk_lat_indices) > 0 and len(uk_lon_indices) > 0:
    print(f"UK lat indices: {uk_lat_indices[0]} to {uk_lat_indices[-1]}")
    print(f"UK lon indices: {uk_lon_indices[0]} to {uk_lon_indices[-1]}")
    print(f"UK lat values: {lat[uk_lat_indices[0]]:.3f} to {lat[uk_lat_indices[-1]]:.3f}")
    print(f"UK lon values: {lon[uk_lon_indices[0]]:.3f} to {lon[uk_lon_indices[-1]]:.3f}")
else:
    print("No UK region found!")