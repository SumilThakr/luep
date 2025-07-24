#!/usr/bin/env python3
"""
Quick script to examine bVOC baseline data
"""
import netCDF4
import numpy as np

# Examine each bVOC file
files = ['inputs/ag-bvoc.nc', 'inputs/grass-bvoc.nc', 'inputs/forest-bvoc.nc']

for filename in files:
    print(f"\n=== {filename} ===")
    try:
        with netCDF4.Dataset(filename, 'r') as nc:
            print(f"Variables: {list(nc.variables.keys())}")
            
            bvoc_data = nc.variables['bvoc'][:]
            lat = nc.variables['lat'][:]
            lon = nc.variables['lon'][:]
            
            print(f"Shape: {bvoc_data.shape}")
            print(f"Data type: {bvoc_data.dtype}")
            print(f"Lat range: {lat.min():.3f} to {lat.max():.3f}")
            print(f"Lon range: {lon.min():.3f} to {lon.max():.3f}")
            
            # Statistics
            print(f"Min value: {bvoc_data.min():.2e}")
            print(f"Max value: {bvoc_data.max():.2e}")
            print(f"Mean value: {bvoc_data.mean():.2e}")
            print(f"Non-zero pixels: {np.sum(bvoc_data > 0)} / {bvoc_data.size}")
            
            # Check for UK region (rough bounds)
            uk_lat_mask = (lat >= 49) & (lat <= 61)
            uk_lon_mask = (lon >= -9) & (lon <= 2)
            
            uk_lat_indices = np.where(uk_lat_mask)[0]
            uk_lon_indices = np.where(uk_lon_mask)[0]
            
            if len(uk_lat_indices) > 0 and len(uk_lon_indices) > 0:
                uk_data = bvoc_data[np.ix_(uk_lat_indices, uk_lon_indices)]
                print(f"UK region shape: {uk_data.shape}")
                print(f"UK region non-zero: {np.sum(uk_data > 0)} / {uk_data.size}")
                if np.sum(uk_data > 0) > 0:
                    print(f"UK region max: {uk_data.max():.2e}")
                    print(f"UK region mean (non-zero): {uk_data[uk_data > 0].mean():.2e}")
            else:
                print("No UK region found in this grid")
                
    except Exception as e:
        print(f"Error reading {filename}: {e}")