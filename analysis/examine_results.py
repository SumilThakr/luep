#!/usr/bin/env python3
"""
Examine the bVOC results
"""
import netCDF4
import numpy as np

print("=== bVOC Results ===")
with netCDF4.Dataset('outputs/bvoc_emissions.nc', 'r') as nc:
    print(f"Variables: {list(nc.variables.keys())}")
    
    emissions = nc.variables['bvoc'][:]
    lat = nc.variables['lat'][:]
    lon = nc.variables['lon'][:]
    
    print(f"Shape: {emissions.shape}")
    print(f"Lat range: {lat.min():.3f} to {lat.max():.3f}")
    print(f"Lon range: {lon.min():.3f} to {lon.max():.3f}")
    
    # Find non-zero emissions
    nonzero_mask = emissions > 0
    nonzero_count = np.sum(nonzero_mask)
    
    print(f"Non-zero emissions: {nonzero_count} pixels")
    if nonzero_count > 0:
        print(f"Emission range: {emissions[nonzero_mask].min():.2e} to {emissions[nonzero_mask].max():.2e}")
        print(f"Total emissions: {emissions.sum():.2e} kg/yr")
        
        # Find where these emissions are located
        nonzero_indices = np.where(nonzero_mask)
        emission_lats = lat[nonzero_indices[0]]
        emission_lons = lon[nonzero_indices[1]]
        
        print(f"Emission locations:")
        print(f"  Lat range: {emission_lats.min():.2f} to {emission_lats.max():.2f}")
        print(f"  Lon range: {emission_lons.min():.2f} to {emission_lons.max():.2f}")
        
        # Check if these are in the UK region
        uk_mask = (emission_lats >= 49) & (emission_lats <= 61) & (emission_lons >= -9) & (emission_lons <= 2)
        uk_emissions = np.sum(uk_mask)
        print(f"Emissions in UK region: {uk_emissions} / {nonzero_count}")
    else:
        print("No emissions found")