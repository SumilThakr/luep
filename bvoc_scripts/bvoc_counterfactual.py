#!/usr/bin/env python3
"""
bVOC Counterfactual Emissions Calculator

Estimates changes in bVOC emissions for counterfactual land use scenarios.
Handles resolution differences and missing land use types through spatial interpolation.

Usage:
    python bvoc_counterfactual.py <scenario_landuse_path> <output_path>
    
This script:
1. Loads baseline bVOC emissions by land use type (ag, forest, grass)
2. Aligns counterfactual land use map to baseline emissions
3. For each pixel, estimates emissions based on:
   - Direct lookup if same land use exists at location
   - Spatial average for resolution differences  
   - Nearest neighbor interpolation for new land use types
"""

import os
import sys
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds
import pygeoprocessing.geoprocessing as geop
from scipy.spatial.distance import cdist
from scipy.ndimage import distance_transform_edt
import netCDF4
from pathlib import Path

def load_bvoc_emissions(inputdir="inputs"):
    """Load baseline bVOC emissions by land use class"""
    emissions = {}
    
    # Simple land use mapping: 0=Other, 1=Cropland, 2=Grass, 3=Forest
    landuse_files = {
        1: "ag-bvoc.nc",      # Cropland
        2: "grass-bvoc.nc",   # Grassland  
        3: "forest-bvoc.nc"   # Forest
    }
    
    for landuse_class, filename in landuse_files.items():
        filepath = os.path.join(inputdir, filename)
        if not os.path.exists(filepath):
            print(f"Warning: {filepath} not found, using zero emissions for class {landuse_class}")
            emissions[landuse_class] = None
            continue
            
        print(f"Loading {filename} for land use class {landuse_class}")
        with netCDF4.Dataset(filepath, 'r') as nc:
            data = nc.variables['bvoc'][:]
            lat = nc.variables['lat'][:]
            lon = nc.variables['lon'][:]
            
            # Check if latitude is in ascending order (south to north)
            if lat[1] > lat[0]:
                print(f"  Flipping latitude order for {filename}")
                # Flip latitude and data to match rasterio convention (north to south)
                lat = lat[::-1]
                data = data[::-1, :]
            
            # Create transform for this dataset
            transform = from_bounds(lon.min(), lat.min(), lon.max(), lat.max(), 
                                  len(lon), len(lat))
            
            emissions[landuse_class] = {
                'data': data,
                'lat': lat,
                'lon': lon, 
                'transform': transform,
                'shape': data.shape
            }
    
    return emissions

def align_emissions_to_landuse(scenario_path, reference_emissions):
    """Align baseline emissions to native land use resolution (opposite of before)"""
    
    print(f"Reading native land use resolution from {scenario_path}...")
    
    # Read the land use file to get its native resolution and extent
    with rasterio.open(scenario_path) as src:
        landuse_data = src.read(1)
        landuse_transform = src.transform
        landuse_crs = src.crs
        landuse_bounds = src.bounds
        
    print(f"Native land use shape: {landuse_data.shape}")
    print(f"Native pixel size: {abs(landuse_transform.a):.6f}° x {abs(landuse_transform.e):.6f}°")
    print(f"Native bounds: {landuse_bounds}")
    
    # Now align each baseline emission dataset to this high-resolution grid
    aligned_emissions = {}
    
    for landuse_class, emissions_data in reference_emissions.items():
        if emissions_data is None:
            aligned_emissions[landuse_class] = None
            continue
            
        print(f"Upsampling emissions for land use class {landuse_class}...")
        
        # Create temporary raster from the baseline emissions data
        temp_emissions_path = f"intermediate/temp_emissions_{landuse_class}.tif"
        os.makedirs("intermediate", exist_ok=True)
        
        ref_lat = emissions_data['lat']
        ref_lon = emissions_data['lon']
        ref_data = emissions_data['data']
        
        # Create transform for emissions data
        emissions_transform = from_bounds(
            ref_lon.min(), ref_lat.min(),
            ref_lon.max(), ref_lat.max(),
            len(ref_lon), len(ref_lat)
        )
        
        # Write baseline emissions to temporary file
        with rasterio.open(temp_emissions_path, 'w',
                          driver='GTiff',
                          height=len(ref_lat),
                          width=len(ref_lon),
                          count=1,
                          dtype='float64',
                          crs='EPSG:4326',
                          transform=emissions_transform) as dst:
            dst.write(ref_data.astype(np.float64), 1)
        
        # Align emissions to land use grid using bilinear interpolation
        aligned_emissions_path = f"intermediate/aligned_emissions_{landuse_class}.tif"
        
        geop.align_and_resize_raster_stack(
            [temp_emissions_path],
            [aligned_emissions_path],
            ['bilinear'],  # Use bilinear for continuous emission data
            (abs(landuse_transform.a), abs(landuse_transform.e)),
            bounding_box_mode=landuse_bounds,
            target_projection_wkt=str(landuse_crs)
        )
        
        # Read the aligned emissions
        with rasterio.open(aligned_emissions_path) as src:
            aligned_data = src.read(1)
            
        aligned_emissions[landuse_class] = {
            'data': aligned_data,
            'shape': aligned_data.shape
        }
        
        print(f"  Upsampled from {ref_data.shape} to {aligned_data.shape}")
        
        # Clean up temporary files
        os.remove(temp_emissions_path)
        os.remove(aligned_emissions_path)
    
    return landuse_data, landuse_transform, aligned_emissions

def find_nearest_emissions(target_coords, source_coords, source_data, max_distance_km=50):
    """
    Find nearest emissions for pixels with new land use types
    
    Args:
        target_coords: (N, 2) array of (lat, lon) coordinates needing emissions
        source_coords: (M, 2) array of (lat, lon) coordinates with known emissions  
        source_data: (M,) array of emission values at source coordinates
        max_distance_km: Maximum search distance in kilometers
        
    Returns:
        emissions: (N,) array of interpolated emission values
    """
    
    if len(source_coords) == 0:
        return np.zeros(len(target_coords))
    
    # Calculate distances (approximate using lat/lon degrees)
    # 1 degree ≈ 111 km
    distances = cdist(target_coords, source_coords) * 111  # Convert to km
    
    # Find nearest neighbor for each target point
    nearest_idx = np.argmin(distances, axis=1)
    nearest_distances = distances[np.arange(len(target_coords)), nearest_idx]
    
    # Get emissions from nearest neighbors
    emissions = source_data[nearest_idx]
    
    # Set to zero if distance exceeds maximum
    emissions[nearest_distances > max_distance_km] = 0.0
    
    return emissions

def get_pixel_area_m2(transform, center_lat):
    """
    Calculate pixel area in m² with latitude correction
    
    Args:
        transform: Rasterio transform object
        center_lat: Center latitude in degrees
        
    Returns:
        float: Area of each pixel in m²
    """
    pixel_width_deg = abs(transform.a)   # longitude step
    pixel_height_deg = abs(transform.e)  # latitude step
    
    # Convert to meters with latitude correction
    lat_to_m = 111000  # meters per degree latitude (constant)
    lon_to_m = 111000 * np.cos(np.radians(center_lat))  # latitude-corrected longitude
    
    pixel_width_m = pixel_width_deg * lon_to_m
    pixel_height_m = pixel_height_deg * lat_to_m
    
    return pixel_width_m * pixel_height_m

def estimate_counterfactual_emissions(landuse_data, aligned_emissions, landuse_transform, landuse_bounds, search_radius_km=500):
    """
    Estimate bVOC emissions for counterfactual land use
    
    Args:
        landuse_data: 2D array of land use classes (0=Other, 1=Crop, 2=Grass, 3=Forest)
        aligned_emissions: Dict of upsampled emissions by land use class  
        landuse_transform: Rasterio transform for the land use data
        landuse_bounds: Bounds of the land use data (left, bottom, right, top)
        search_radius_km: Search radius for spatial interpolation (not used with upsampled data)
        
    Returns:
        emissions: 2D array of estimated bVOC emissions in kg yr⁻¹ at native land use resolution
    """
    
    print("Estimating counterfactual bVOC emissions at native resolution...")
    print(f"Land use data shape: {landuse_data.shape}")
    
    # Calculate pixel area for unit conversion (kg m⁻² yr⁻¹ → kg yr⁻¹)
    center_lat = (landuse_bounds[1] + landuse_bounds[3]) / 2  # Average latitude
    pixel_area_m2 = get_pixel_area_m2(landuse_transform, center_lat)
    
    print(f"Center latitude: {center_lat:.2f}°")
    print(f"Pixel area: {pixel_area_m2:.0f} m² ({pixel_area_m2/10000:.4f} hectares)")
    print("Converting emissions from kg m⁻² yr⁻¹ to kg yr⁻¹")
    
    # Initialize output emissions array
    emissions = np.zeros_like(landuse_data, dtype=np.float64)
    
    # Process each land use class  
    for landuse_class in [1, 2, 3]:  # Crop, Grass, Forest
        
        if aligned_emissions[landuse_class] is None:
            print(f"Skipping land use class {landuse_class} - no baseline data")
            continue
            
        baseline_data = aligned_emissions[landuse_class]['data']
        
        # Find pixels that should have this land use class
        target_mask = (landuse_data == landuse_class)
        target_count = np.sum(target_mask)
        
        if target_count == 0:
            print(f"No pixels found for land use class {landuse_class}")
            continue
            
        print(f"Processing {target_count} pixels for land use class {landuse_class}")
        
        # Since emissions are already upsampled to match land use resolution,
        # we can directly assign emissions where land use matches
        # Convert from kg m⁻² yr⁻¹ to kg yr⁻¹ by multiplying by pixel area
        emissions[target_mask] = baseline_data[target_mask] * pixel_area_m2
        
        # Report statistics
        assigned_emissions = emissions[target_mask]
        nonzero_count = np.sum(assigned_emissions > 0)
        if nonzero_count > 0:
            print(f"  {nonzero_count} pixels assigned emissions")
            print(f"  Emission range: {assigned_emissions[assigned_emissions > 0].min():.2e} to {assigned_emissions[assigned_emissions > 0].max():.2e}")
        else:
            print(f"  No emissions assigned (all zero in baseline)")
    
    return emissions

def save_emissions(emissions, landuse_transform, landuse_bounds, output_path):
    """Save estimated emissions as GeoTIFF file at native resolution"""
    
    print(f"Saving emissions to {output_path}")
    
    # Save as GeoTIFF to preserve the native resolution and coordinate system
    output_tif = output_path.replace('.nc', '.tif')
    
    with rasterio.open(output_tif, 'w',
                      driver='GTiff',
                      height=emissions.shape[0],
                      width=emissions.shape[1], 
                      count=1,
                      dtype='float64',
                      crs='EPSG:4326',
                      transform=landuse_transform) as dst:
        dst.write(emissions.astype(np.float64), 1)
        
        # Set metadata
        dst.update_tags(
            units='kg yr-1',
            description='Counterfactual bVOC emissions at native land use resolution (total emissions per pixel)'
        )
    
    print(f"Emissions saved as GeoTIFF: {output_tif}")
    
    # Also create a NetCDF version with coordinate arrays for compatibility
    print(f"Creating NetCDF version: {output_path}")
    
    # Create coordinate arrays from the transform
    height, width = emissions.shape
    x_coords = np.array([landuse_transform * (i, 0) for i in range(width)])[:, 0]
    y_coords = np.array([landuse_transform * (0, j) for j in range(height)])[:, 1]
    
    with netCDF4.Dataset(output_path, 'w', format='NETCDF4') as out:
        # Create dimensions
        out.createDimension('lat', height)
        out.createDimension('lon', width)
        
        # Create coordinate variables
        lat_var = out.createVariable('lat', 'f8', ('lat',))
        lat_var[:] = y_coords
        lat_var.units = 'degrees_north'
        lat_var.long_name = 'latitude'
        
        lon_var = out.createVariable('lon', 'f8', ('lon',))
        lon_var[:] = x_coords
        lon_var.units = 'degrees_east'
        lon_var.long_name = 'longitude'
        
        # Create emissions variable
        emissions_var = out.createVariable('bvoc', 'f8', ('lat', 'lon'))
        emissions_var[:] = emissions
        emissions_var.units = 'kg yr-1'
        emissions_var.long_name = 'Counterfactual bVOC emissions'
        emissions_var.description = 'Estimated total bVOC emissions for counterfactual land use scenario at native resolution (kg per pixel per year)'

def main():
    """Main processing function"""
    
    if len(sys.argv) != 3:
        print("Usage: python bvoc_counterfactual.py <scenario_landuse_path> <output_path>")
        print("\nExample:")
        print("  python bvoc_counterfactual.py inputs/gblulcg20_10000.tif outputs/counterfactual_bvoc.nc")
        sys.exit(1)
    
    scenario_path = sys.argv[1]
    output_path = sys.argv[2]
    
    if not os.path.exists(scenario_path):
        print(f"Error: Scenario file not found: {scenario_path}")
        sys.exit(1)
    
    # Create output directory
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print("=== bVOC Counterfactual Emissions Calculator ===")
    print(f"Scenario: {scenario_path}")
    print(f"Output: {output_path}")
    
    try:
        # Load baseline emissions
        baseline_emissions = load_bvoc_emissions()
        
        # Get land use bounds for pixel area calculation
        with rasterio.open(scenario_path) as src:
            landuse_bounds = src.bounds
        
        # Align emissions to native land use resolution (new approach!)
        landuse_data, landuse_transform, aligned_emissions = align_emissions_to_landuse(
            scenario_path, baseline_emissions
        )
        
        # Estimate counterfactual emissions
        emissions = estimate_counterfactual_emissions(landuse_data, aligned_emissions, landuse_transform, landuse_bounds)
        
        # Save results at native resolution
        save_emissions(emissions, landuse_transform, landuse_bounds, output_path)
        
        # Summary statistics
        total_emissions = np.sum(emissions)
        max_emissions = np.max(emissions)
        nonzero_pixels = np.sum(emissions > 0)
        
        print(f"\n=== Results Summary ===")
        print(f"Total emissions: {total_emissions:.2e} kg/yr")
        print(f"Maximum emissions per pixel: {max_emissions:.2e} kg/yr")
        print(f"Pixels with emissions: {nonzero_pixels}")
        print(f"Output saved to: {output_path}")
        print(f"Note: Output units changed from kg m⁻² yr⁻¹ to kg yr⁻¹ (total emissions per pixel)")
        
        # Cleanup intermediate files
        intermediate_files = [
            "intermediate/reference_grid.tif",
            "intermediate/aligned_scenario_landuse.tif"
        ]
        for filepath in intermediate_files:
            if os.path.exists(filepath):
                os.remove(filepath)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()