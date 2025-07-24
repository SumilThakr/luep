#!/usr/bin/env python3
"""
Prepare UK Scenario Outputs for InMAP

This script converts emission and deposition files from UK land use scenarios 
into InMAP-compatible NetCDF-3 (classic) format with proper variable names and units.

InMAP Requirements:
- NetCDF-3 (classic) format
- Variable names: "PM2_5", "NOx", "NH3", or "VOC"
- No NaN or NaNf values
- Units in kg or kg/year

Usage:
    python prepare_inmap_inputs.py
"""

import os
import sys
import numpy as np
import xarray as xr
import rasterio
from pathlib import Path
from netCDF4 import Dataset
import warnings

def create_inmap_netcdf(data_array, lons, lats, var_name, units, output_path, scenario_name, emission_type):
    """
    Create InMAP-compatible NetCDF-3 file
    
    Args:
        data_array: 2D numpy array of emission data
        lons, lats: 2D coordinate arrays
        var_name: InMAP variable name (PM2_5, NOx, NH3, VOC)
        units: Data units
        output_path: Output NetCDF file path
        scenario_name: Scenario name for metadata
        emission_type: Original emission type for metadata
    """
    
    # Ensure no NaN values (replace with 0.0)
    data_clean = np.nan_to_num(data_array, nan=0.0, posinf=0.0, neginf=0.0)
    
    # Double-check for any remaining NaN values and replace them
    if hasattr(data_clean, 'mask'):
        # Handle masked arrays
        data_clean = np.ma.filled(data_clean, 0.0)
    
    # Final NaN check and replacement
    data_clean = np.where(np.isnan(data_clean), 0.0, data_clean)
    data_clean = np.where(np.isinf(data_clean), 0.0, data_clean)
    
    # Get unique coordinate arrays for NetCDF dimensions
    if lons.ndim == 2:
        lon_1d = lons[0, :]  # First row
        lat_1d = lats[:, 0]  # First column
    else:
        lon_1d = lons
        lat_1d = lats
    
    # Create NetCDF-3 file
    with Dataset(output_path, 'w', format='NETCDF3_CLASSIC') as nc:
        
        # Create dimensions
        nc.createDimension('lon', len(lon_1d))
        nc.createDimension('lat', len(lat_1d))
        
        # Create coordinate variables
        lon_var = nc.createVariable('lon', 'f8', ('lon',))
        lat_var = nc.createVariable('lat', 'f8', ('lat',))
        
        # Create data variable (no fill value to avoid NaN issues)
        data_var = nc.createVariable(var_name, 'f8', ('lat', 'lon'))
        
        # Set coordinate data
        lon_var[:] = lon_1d
        lat_var[:] = lat_1d
        data_var[:, :] = data_clean
        
        # Set variable attributes
        lon_var.units = 'degrees_east'
        lon_var.long_name = 'longitude'
        lon_var.standard_name = 'longitude'
        
        lat_var.units = 'degrees_north'
        lat_var.long_name = 'latitude'
        lat_var.standard_name = 'latitude'
        
        data_var.units = units
        data_var.long_name = f'{var_name} emissions'
        data_var.standard_name = f'{var_name.lower()}_emissions'
        
        # Global attributes
        nc.title = f'UK {scenario_name} {emission_type} for InMAP'
        nc.source = 'UK Land Use Emissions Processor (LUEP)'
        nc.scenario = scenario_name
        nc.emission_type = emission_type
        nc.conventions = 'CF-1.6'
        nc.institution = 'Generated for InMAP air quality modeling'
        
        # Summary statistics
        total_emissions = np.sum(data_clean)
        mean_emissions = np.mean(data_clean[data_clean > 0]) if np.any(data_clean > 0) else 0.0
        
        nc.total_emissions_kg = float(total_emissions)
        nc.mean_nonzero_emissions = float(mean_emissions)
        nc.valid_pixels = int(np.sum(data_clean > 0))
        nc.total_pixels = int(data_clean.size)
    
    print(f"  Created: {output_path}")
    print(f"    Total emissions: {total_emissions:.2e} {units}")
    print(f"    Valid pixels: {np.sum(data_clean > 0):,} / {data_clean.size:,}")


def load_emission_data(file_path):
    """
    Load emission data from various formats (GeoTIFF or NetCDF)
    
    Returns:
        tuple: (data_array, lons, lats, original_units)
    """
    
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    print(f"  Loading: {file_path}")
    
    if file_path.suffix in ['.tiff', '.tif']:
        # Load GeoTIFF with rasterio
        with rasterio.open(file_path) as src:
            data = src.read(1)
            
            # Get coordinate arrays
            height, width = data.shape
            cols, rows = np.meshgrid(np.arange(width), np.arange(height))
            lons, lats = rasterio.transform.xy(src.transform, rows, cols)
            lons, lats = np.array(lons), np.array(lats)
            
            # Mask nodata values
            if src.nodata is not None:
                data = np.where(data == src.nodata, np.nan, data)
            
    elif file_path.suffix == '.nc':
        # Load NetCDF with xarray
        ds = xr.open_dataset(file_path)
        
        # Get the main data variable
        data_vars = [var for var in ds.data_vars if var not in ['lat', 'lon']]
        if not data_vars:
            raise ValueError(f"No data variables found in {file_path}")
        
        main_var = data_vars[0]
        data_da = ds[main_var]
        
        # Extract data and coordinates
        data = data_da.values
        if data.ndim > 2:
            data = data[0]  # Take first time slice
            
        lats = ds.lat.values
        lons = ds.lon.values
        
        # Create 2D coordinate grids if needed
        if lons.ndim == 1 and lats.ndim == 1:
            lons, lats = np.meshgrid(lons, lats)
        
        ds.close()
        
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")
    
    return data, lons, lats


def get_inmap_variable_name(emission_type):
    """Map emission types to InMAP variable names"""
    mapping = {
        'dust_sum': 'PM2_5',          # Dust emissions -> PM2.5
        'pm25_deposition': 'PM2_5',   # PM2.5 deposition -> PM2.5 (negative for removal)
        'nox_emissions': 'NOx',       # NOx emissions -> NOx
        'nh3_emissions': 'NH3',       # NH3 emissions -> NH3  
        'bvoc_emissions': 'VOC'       # BVOC emissions -> VOC
    }
    return mapping.get(emission_type, emission_type.upper())


def get_target_units(emission_type):
    """Get target units for InMAP (kg or kg/year)"""
    # All should be in kg/year for annual emissions
    return 'kg year-1'


def process_scenario(scenario_name, base_dir, output_dir):
    """
    Process all emission types for a single scenario
    
    Args:
        scenario_name: Name of scenario
        base_dir: Base results directory  
        output_dir: Output directory for InMAP files
    """
    
    print(f"\n{'='*60}")
    print(f"PROCESSING SCENARIO: {scenario_name}")
    print(f"{'='*60}")
    
    scenario_dir = base_dir / scenario_name
    
    if not scenario_dir.exists():
        print(f"❌ Scenario directory not found: {scenario_dir}")
        return False
    
    # Define emission types and their file mappings
    # Use UK-clipped versions where available
    emission_files = {
        'dust_sum': 'dust_sum.tiff',
        'pm25_deposition': 'pm25_deposition.nc',
        'nox_emissions': 'nox_emissions_uk.tif',  # Use UK-clipped version
        'nh3_emissions': 'nh3_emissions.nc',
        'bvoc_emissions': 'bvoc_emissions.tif'
    }
    
    success_count = 0
    
    for emission_type, filename in emission_files.items():
        
        print(f"\n🔄 Processing {emission_type}...")
        
        # Input file path
        input_path = scenario_dir / filename
        
        if not input_path.exists():
            print(f"  ⚠️  File not found: {input_path}")
            continue
        
        try:
            # Load data
            data, lons, lats = load_emission_data(input_path)
            
            # Get InMAP variable name and units
            var_name = get_inmap_variable_name(emission_type)
            units = get_target_units(emission_type)
            
            # Handle PM2.5 deposition (keep positive values)
            if emission_type == 'pm25_deposition':
                # Deposition should be positive values (representing PM2.5 removal mass)
                data = np.abs(data)
                print(f"  📈 Keeping deposition as positive values (PM2.5 removal mass)")
            
            # Create output filename
            output_filename = f"{scenario_name}_{emission_type}_inmap.nc"
            output_path = output_dir / output_filename
            
            # Create InMAP NetCDF file
            create_inmap_netcdf(data, lons, lats, var_name, units, 
                              output_path, scenario_name, emission_type)
            
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ Error processing {emission_type}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n✅ Successfully processed {success_count}/5 emission types for {scenario_name}")
    return success_count == 5


def main():
    """Main function to process all scenarios"""
    
    print("🇬🇧 UK SCENARIOS → InMAP CONVERSION")
    print("="*60)
    
    # Define paths
    base_dir = Path("outputs/uk_results")
    output_dir = Path("outputs/uk_results/for_inmap")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Define scenarios to process
    scenarios = [
        "grazing_expansion",
        "forestry_expansion", 
        "sustainable_current"
    ]
    
    emission_types = [
        "dust_sum",
        "pm25_deposition",
        "nox_emissions", 
        "nh3_emissions",
        "bvoc_emissions"
    ]
    
    print(f"Scenarios: {scenarios}")
    print(f"Emission types: {emission_types}")
    print(f"Total files to convert: {len(scenarios)} × {len(emission_types)} = {len(scenarios) * len(emission_types)}")
    print(f"Output directory: {output_dir.absolute()}")
    
    # Process all scenarios
    successful_scenarios = 0
    total_files = 0
    
    for scenario in scenarios:
        success = process_scenario(scenario, base_dir, output_dir)
        if success:
            successful_scenarios += 1
        total_files += 5  # 5 emission types per scenario
    
    # Final summary
    print(f"\n{'='*60}")
    print("🎯 CONVERSION COMPLETE")
    print(f"{'='*60}")
    print(f"✅ Successful scenarios: {successful_scenarios}/{len(scenarios)}")
    
    # List created files
    inmap_files = list(output_dir.glob("*.nc"))
    print(f"📁 Created {len(inmap_files)} InMAP files:")
    
    for nc_file in sorted(inmap_files):
        file_size = nc_file.stat().st_size / 1024  # KB
        print(f"  📄 {nc_file.name} ({file_size:.1f} KB)")
    
    print(f"\n🚀 Files ready for InMAP in: {output_dir.absolute()}")
    
    # InMAP usage note
    print(f"\n📋 InMAP Usage Notes:")
    print(f"  - All files are NetCDF-3 (classic) format")
    print(f"  - Variable names: PM2_5, NOx, NH3, VOC")
    print(f"  - Units: kg year-1 (annual emissions)")
    print(f"  - No NaN values (replaced with 0.0)")
    print(f"  - PM2.5 deposition kept as positive values (removal mass)")


if __name__ == "__main__":
    main()