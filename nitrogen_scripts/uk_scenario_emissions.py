#!/usr/bin/env python3
"""
UK Scenario Nitrogen Emissions Mapping

This script processes ESA-CCI land use scenario maps and generates:
1. NH3 emissions maps (NetCDF format)
2. N application maps for soil NOx module input

Key features:
- Pixel-area-aware emission factor conversion
- Direct ESA-CCI class to emission mapping
- Proper handling of pasture (ESA-CCI code 130 only)
- NetCDF output with 0.0 null values (not NaN)
"""

import numpy as np
import pandas as pd
import os
import sys
from pathlib import Path
import pygeoprocessing.geoprocessing as geop
from osgeo import gdal
import netCDF4 as nc
from datetime import datetime

def get_pixel_area_hectares(raster_path):
    """
    Extract pixel size from raster and convert to hectares per pixel
    
    Args:
        raster_path: Path to raster file
        
    Returns:
        float: Area of each pixel in hectares
    """
    print(f"Analyzing pixel area for: {raster_path}")
    
    # Get raster info using pygeoprocessing
    raster_info = geop.get_raster_info(raster_path)
    
    # Extract pixel size and check if it's in degrees or meters
    pixel_size = raster_info['pixel_size']
    pixel_width = abs(pixel_size[0])   # x-direction
    pixel_height = abs(pixel_size[1])  # y-direction
    
    # Check if coordinates are in degrees (WGS84) or meters
    projection_wkt = raster_info['projection_wkt']
    
    if 'degree' in projection_wkt.lower() or 'GEOGCS' in projection_wkt:
        # Geographic coordinates (degrees) - need to convert to meters
        # For UK, approximate conversion: 1 degree ≈ 111,000m latitude, varies by longitude
        # At UK latitude (~55°N), 1 degree longitude ≈ 63,000m
        
        # Get bounding box to estimate latitude
        bbox = raster_info['bounding_box']
        center_lat = (bbox[1] + bbox[3]) / 2  # Average latitude
        
        # Convert degrees to meters using approximate conversion
        lat_to_m = 111000  # meters per degree latitude
        lon_to_m = 111000 * np.cos(np.radians(center_lat))  # meters per degree longitude at this latitude
        
        pixel_width_m = pixel_width * lon_to_m
        pixel_height_m = pixel_height * lat_to_m
        
        print(f"Geographic coordinates detected (degrees)")
        print(f"Center latitude: {center_lat:.2f}°")
        print(f"Pixel size in degrees: {pixel_width:.6f}° x {pixel_height:.6f}°")
        print(f"Pixel size in meters: {pixel_width_m:.1f}m x {pixel_height_m:.1f}m")
        
    else:
        # Projected coordinates (assumed to be in meters)
        pixel_width_m = pixel_width
        pixel_height_m = pixel_height
        print(f"Projected coordinates detected")
        print(f"Pixel size in meters: {pixel_width_m:.1f}m x {pixel_height_m:.1f}m")
    
    # Calculate area per pixel
    pixel_area_m2 = pixel_width_m * pixel_height_m
    pixel_area_hectares = pixel_area_m2 / 10000  # Convert m² to hectares
    
    print(f"Pixel area: {pixel_area_m2:.0f} m² = {pixel_area_hectares:.4f} hectares per pixel")
    
    return pixel_area_hectares

def get_emission_factors_per_hectare():
    """
    Define emission factors per hectare based on calculated UK averages
    
    Returns:
        dict: ESA-CCI class code -> {nh3: kg/ha, n_app: kg/ha}
    """
    
    # From our nitrogen calculations:
    # Cropland: 18.23 kg NH3/ha, 211.67 kg N/ha
    # Pasture (ESA-CCI 130 only): 9.83 kg NH3/ha, 101.11 kg N/ha
    
    # Load ESA-CCI mapping to identify cropland classes
    esa_mapping_path = Path("inputs/UK_ESA_CCI_to_Simple_mapping.csv")
    if not esa_mapping_path.exists():
        print(f"Warning: ESA-CCI mapping file not found at {esa_mapping_path}")
        print("Using default cropland class assignments")
    
    # Define emission factors
    factors = {}
    
    # Cropland classes (all ESA-CCI codes with Simple_Class = 1)
    cropland_classes = [10, 20, 30, 34, 35, 39]  # Common cropland ESA-CCI codes
    for esa_class in cropland_classes:
        factors[esa_class] = {
            'nh3': 18.23,      # kg NH3/ha
            'n_app': 211.67    # kg N/ha
        }
    
    # Pasture - ESA-CCI codes for livestock grazing areas only
    pasture_classes = [130, 134, 140, 141, 151, 152, 153]  # Grassland codes with livestock (including 134 grassland variant)
    for esa_class in pasture_classes:
        factors[esa_class] = {
            'nh3': 9.83,       # kg NH3/ha  
            'n_app': 101.11    # kg N/ha
        }
    
    # All other classes get 0.0 emissions
    # (forests, shrublands, urban, water, etc.)
    
    return factors

def convert_emission_factors_to_per_pixel(per_hectare_factors, pixel_area_ha):
    """
    Convert per-hectare emission factors to per-pixel values
    
    Args:
        per_hectare_factors: dict of emission factors per hectare
        pixel_area_ha: area of each pixel in hectares
        
    Returns:
        dict: ESA-CCI class code -> {nh3: kg/pixel, n_app: kg/pixel}
    """
    per_pixel_factors = {}
    
    for esa_class, factors in per_hectare_factors.items():
        per_pixel_factors[esa_class] = {
            'nh3': factors['nh3'] * pixel_area_ha,
            'n_app': factors['n_app'] * pixel_area_ha
        }
    
    return per_pixel_factors

def validate_pixel_conversion(pixel_area_ha, per_hectare_factors, per_pixel_factors):
    """
    Print validation information for pixel area conversion
    """
    print(f"\n{'='*60}")
    print("PIXEL AREA CONVERSION VALIDATION")
    print(f"{'='*60}")
    print(f"Pixel area: {pixel_area_ha:.6f} hectares per pixel")
    print(f"\nSample conversions:")
    
    for esa_class, ha_factors in per_hectare_factors.items():
        px_factors = per_pixel_factors[esa_class]
        
        if esa_class == 130:
            land_type = "Pasture (ESA-CCI 130)"
        elif esa_class in [10, 20, 30]:
            land_type = f"Cropland (ESA-CCI {esa_class})"
        else:
            land_type = f"ESA-CCI {esa_class}"
            
        print(f"\n{land_type}:")
        print(f"  NH3: {ha_factors['nh3']:.2f} kg/ha × {pixel_area_ha:.6f} ha = {px_factors['nh3']:.6f} kg/pixel")
        print(f"  N:   {ha_factors['n_app']:.2f} kg/ha × {pixel_area_ha:.6f} ha = {px_factors['n_app']:.6f} kg/pixel")
    
    print(f"{'='*60}")

def process_scenario_map(scenario_map_path, output_dir):
    """
    Process a single ESA-CCI scenario map to generate NH3 and N application grids
    
    Args:
        scenario_map_path: Path to ESA-CCI scenario map
        output_dir: Directory to save output NetCDF files
    """
    
    print(f"\nProcessing scenario: {scenario_map_path}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Step 1: Get pixel area
    pixel_area_ha = get_pixel_area_hectares(scenario_map_path)
    
    # Step 2: Get emission factors
    per_hectare_factors = get_emission_factors_per_hectare()
    per_pixel_factors = convert_emission_factors_to_per_pixel(per_hectare_factors, pixel_area_ha)
    
    # Step 3: Validation output
    validate_pixel_conversion(pixel_area_ha, per_hectare_factors, per_pixel_factors)
    
    # Step 4: Load land use map
    print(f"\nLoading land use map...")
    land_use_array = geop.raster_to_numpy_array(scenario_map_path)
    
    print(f"Land use map shape: {land_use_array.shape}")
    print(f"Land use classes found: {np.unique(land_use_array)}")
    
    # Step 5: Initialize emission arrays
    nh3_emissions = np.zeros_like(land_use_array, dtype=np.float32)
    n_application = np.zeros_like(land_use_array, dtype=np.float32)
    
    # Step 6: Apply emission factors pixel by pixel
    print(f"\nApplying emission factors...")
    
    emission_stats = {}
    
    for esa_class, factors in per_pixel_factors.items():
        mask = (land_use_array == esa_class)
        pixel_count = np.sum(mask)
        
        if pixel_count > 0:
            nh3_emissions[mask] = factors['nh3']
            n_application[mask] = factors['n_app']
            
            total_nh3 = factors['nh3'] * pixel_count
            total_n = factors['n_app'] * pixel_count
            
            land_type = "Pasture" if esa_class == 130 else "Cropland"
            emission_stats[esa_class] = {
                'land_type': land_type,
                'pixel_count': pixel_count,
                'area_ha': pixel_count * pixel_area_ha,
                'total_nh3_kg': total_nh3,
                'total_n_kg': total_n
            }
            
            print(f"  ESA-CCI {esa_class} ({land_type}): {pixel_count:,} pixels = {pixel_count * pixel_area_ha:,.1f} ha")
    
    # Step 7: Save as NetCDF files
    raster_info = geop.get_raster_info(scenario_map_path)
    
    nh3_output_path = os.path.join(output_dir, 'nh3_emissions.nc')
    n_app_output_path = os.path.join(output_dir, 'n_application.nc')
    
    save_emissions_netcdf(nh3_emissions, raster_info, nh3_output_path, 
                         'NH3', 'kg per pixel', 'NH3 emissions from agriculture')
    
    save_emissions_netcdf(n_application, raster_info, n_app_output_path,
                         'N_application', 'kg per pixel', 'Nitrogen application for soil NOx module')
    
    # Step 8: Generate summary statistics
    stats_path = os.path.join(output_dir, 'nitrogen_summary.txt')
    save_summary_stats(emission_stats, pixel_area_ha, stats_path)
    
    print(f"\nOutputs saved to: {output_dir}")
    print(f"  - NH3 emissions: {nh3_output_path}")
    print(f"  - N application: {n_app_output_path}")
    print(f"  - Summary stats: {stats_path}")

def save_emissions_netcdf(data_array, raster_info, output_path, var_name, units, description):
    """
    Save emissions array as NetCDF file with proper formatting matching bVOC format
    
    Args:
        data_array: 2D numpy array with emission values
        raster_info: Raster information from pygeoprocessing
        output_path: Path for output NetCDF file
        var_name: Variable name (e.g., 'NH3', 'N_application')
        units: Units string (e.g., 'kg per pixel')
        description: Variable description
    """
    
    print(f"Saving {var_name} to NetCDF: {output_path}")
    
    # Get georeference info
    geotransform = raster_info['geotransform']
    
    # Calculate coordinate arrays
    height, width = data_array.shape
    lon_origin = geotransform[0]
    lat_origin = geotransform[3]
    lon_pixel_size = geotransform[1]
    lat_pixel_size = geotransform[5]
    
    # Create coordinate arrays (pixel centers) - note lat/lon not x/y
    lon_coords = np.arange(lon_origin + lon_pixel_size/2, lon_origin + width*lon_pixel_size, lon_pixel_size)
    lat_coords = np.arange(lat_origin + lat_pixel_size/2, lat_origin + height*lat_pixel_size, lat_pixel_size)
    
    # Create NetCDF file matching bVOC format
    with nc.Dataset(output_path, 'w', format='NETCDF4', clobber=True) as ncfile:
        
        # Create dimensions (lat, lon like bVOC)
        ncfile.createDimension('lat', height)
        ncfile.createDimension('lon', width)
        
        # Create coordinate variables (double precision like bVOC)
        lat_var = ncfile.createVariable('lat', 'f8', ('lat',))
        lon_var = ncfile.createVariable('lon', 'f8', ('lon',))
        
        lat_var[:] = lat_coords
        lon_var[:] = lon_coords
        
        # Set coordinate attributes matching bVOC format
        lat_var.units = 'degrees_north'
        lon_var.units = 'degrees_east'
        lat_var.long_name = 'latitude'
        lon_var.long_name = 'longitude'
        
        # Create emission variable (double precision, no fill_value like bVOC)
        # Use 'f8' for NH3 (double), 'f4' for N_application (float)
        dtype = 'f8' if var_name == 'NH3' else 'f8'  # Actually use double for both
        emission_var = ncfile.createVariable(var_name, dtype, ('lat', 'lon'), 
                                           zlib=True, complevel=6)
        
        # Ensure no NaN values - replace with 0.0
        emission_data = np.where(np.isnan(data_array), 0.0, data_array)
        emission_var[:] = emission_data
        
        # Set variable attributes matching bVOC style
        emission_var.units = units
        emission_var.long_name = description
        
        # Add description for NH3
        if var_name == 'NH3':
            emission_var.description = "NH3 emissions from agriculture for land use scenario"
        else:
            emission_var.description = "Nitrogen application for soil NOx module input"

def save_summary_stats(emission_stats, pixel_area_ha, output_path):
    """
    Save summary statistics to text file
    """
    
    with open(output_path, 'w') as f:
        f.write("UK Nitrogen Emissions Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Pixel area: {pixel_area_ha:.6f} hectares per pixel\n\n")
        
        total_nh3 = 0
        total_n = 0
        total_area = 0
        
        for esa_class, stats in emission_stats.items():
            f.write(f"ESA-CCI Class {esa_class} ({stats['land_type']}):\n")
            f.write(f"  Pixels: {stats['pixel_count']:,}\n")
            f.write(f"  Area: {stats['area_ha']:,.1f} hectares\n")
            f.write(f"  Total NH3: {stats['total_nh3_kg']:,.1f} kg\n")
            f.write(f"  Total N: {stats['total_n_kg']:,.1f} kg\n")
            f.write(f"  NH3 rate: {stats['total_nh3_kg']/stats['area_ha']:.2f} kg/ha\n")
            f.write(f"  N rate: {stats['total_n_kg']/stats['area_ha']:.2f} kg/ha\n\n")
            
            total_nh3 += stats['total_nh3_kg']
            total_n += stats['total_n_kg']
            total_area += stats['area_ha']
        
        f.write("TOTALS:\n")
        f.write(f"  Agricultural area: {total_area:,.1f} hectares\n")
        f.write(f"  Total NH3 emissions: {total_nh3:,.1f} kg\n")
        f.write(f"  Total N application: {total_n:,.1f} kg\n")
        
        if total_area > 0:
            f.write(f"  Average NH3 rate: {total_nh3/total_area:.2f} kg/ha\n")
            f.write(f"  Average N rate: {total_n/total_area:.2f} kg/ha\n")

def main():
    """
    Main function for testing with a single scenario
    """
    
    # Test with one scenario
    scenario_name = "extensification_current_practices"
    scenario_path = f"scenarios/UKNatureFrontierWithAir/United Kingdom/ScenarioMaps/{scenario_name}.tif"
    output_dir = f"outputs/uk_results/{scenario_name}"
    
    if not os.path.exists(scenario_path):
        print(f"Error: Scenario file not found: {scenario_path}")
        return
    
    print("UK Scenario Nitrogen Emissions Mapping")
    print("=" * 50)
    
    process_scenario_map(scenario_path, output_dir)
    
    print("\nProcessing completed successfully!")

if __name__ == "__main__":
    main()