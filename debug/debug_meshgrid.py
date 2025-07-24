#!/usr/bin/env python3
"""
Debug meshgrid usage
"""
import numpy as np
import netCDF4

print("=== Loading bVOC coordinates ===")
with netCDF4.Dataset('inputs/grass-bvoc.nc', 'r') as nc:
    lat = nc.variables['lat'][:]
    lon = nc.variables['lon'][:]

print(f"Lat array: {lat.shape}, {lat.min():.1f} to {lat.max():.1f}")
print(f"Lon array: {lon.shape}, {lon.min():.1f} to {lon.max():.1f}")

# Test meshgrid
lat_grid, lon_grid = np.meshgrid(lat, lon, indexing='ij')
print(f"Meshgrid shapes: lat_grid {lat_grid.shape}, lon_grid {lon_grid.shape}")

# Check specific UK region coordinates
uk_rows = np.arange(117, 160)  # From debug output
uk_cols = np.arange(550, 582)

print(f"\nUK region rows: {uk_rows[0]} to {uk_rows[-1]}")
print(f"UK region cols: {uk_cols[0]} to {uk_cols[-1]}")

# Extract UK coordinates
uk_lats = lat_grid[uk_rows[0]:uk_rows[-1]+1, uk_cols[0]:uk_cols[-1]+1]
uk_lons = lon_grid[uk_rows[0]:uk_rows[-1]+1, uk_cols[0]:uk_cols[-1]+1]

print(f"UK region lat range: {uk_lats.min():.1f} to {uk_lats.max():.1f}")
print(f"UK region lon range: {uk_lons.min():.1f} to {uk_lons.max():.1f}")

# Test specific pixel
test_row, test_col = 130, 565  # Should be in UK
test_lat = lat_grid[test_row, test_col]
test_lon = lon_grid[test_row, test_col]
print(f"Test pixel ({test_row}, {test_col}): {test_lat:.1f}°N, {test_lon:.1f}°E")

# Compare with direct array access
direct_lat = lat[test_row]
direct_lon = lon[test_col]
print(f"Direct access: {direct_lat:.1f}°N, {direct_lon:.1f}°E")