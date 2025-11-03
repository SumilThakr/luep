#!/usr/bin/env python3
"""
Plot UK Scenario Difference Maps

This script creates difference maps comparing UK land use scenarios against 
the "sustainable current" baseline for various emission and deposition types.

Usage:
    python plot_scenario_difference.py <scenario_name> <emission_type>

Example:
    python plot_scenario_difference.py grazing_expansion dust_sum
    python plot_scenario_difference.py forestry_expansion pm25_deposition

Supported emission types:
    - dust_sum (dust_sum.tiff)
    - pm25_deposition (pm25_deposition.nc)  
    - nox_emissions (nox_emissions.tif)
    - nh3_emissions (nh3_emissions.nc)
    - bvoc_emissions (bvoc_emissions.tif)
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from pathlib import Path
import rasterio
import xarray as xr
from matplotlib.colors import TwoSlopeNorm
import cartopy.crs as ccrs
import cartopy.feature as cfeature

def load_emission_data(scenario_path, emission_type):
    """
    Load emission/deposition data based on file type
    
    Args:
        scenario_path: Path to scenario directory
        emission_type: Type of emission data to load
        
    Returns:
        tuple: (data_array, lons, lats, units)
    """
    
    # Define file mappings
    file_mappings = {
        'dust_sum': 'dust_sum.tiff',
        'pm25_deposition': 'pm25_deposition.nc',
        'nox_emissions': 'nox_emissions.tif', 
        'nh3_emissions': 'nh3_emissions.nc',
        'bvoc_emissions': 'bvoc_emissions.tif'
    }
    
    if emission_type not in file_mappings:
        raise ValueError(f"Unsupported emission type: {emission_type}")
    
    file_path = scenario_path / file_mappings[emission_type]
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    print(f"Loading {emission_type} from {file_path}")
    
    # Load data based on file extension
    if file_path.suffix in ['.tiff', '.tif']:
        # Load GeoTIFF files with rasterio
        with rasterio.open(file_path) as src:
            data = src.read(1)
            
            # Get coordinate arrays efficiently
            height, width = data.shape
            transform = src.transform
            x_coords = np.array([transform[2] + transform[0] * (j + 0.5) for j in range(width)])
            y_coords = np.array([transform[5] + transform[4] * (i + 0.5) for i in range(height)])
            lons, lats = np.meshgrid(x_coords, y_coords)
            
            # Get units from metadata or set defaults
            units = _get_units_for_emission_type(emission_type)
            
    elif file_path.suffix == '.nc':
        # Load NetCDF files with xarray
        ds = xr.open_dataset(file_path)
        
        # Get the main data variable (first non-coordinate variable)
        data_vars = [var for var in ds.data_vars if var not in ['lat', 'lon']]
        if not data_vars:
            raise ValueError(f"No data variables found in {file_path}")
        
        main_var = data_vars[0]
        data_da = ds[main_var]
        
        # Extract data and coordinates
        data = data_da.values
        if data.ndim > 2:
            data = data[0]  # Take first time slice if time dimension exists
            
        lats = ds.lat.values
        lons = ds.lon.values
        
        # Create 2D coordinate grids
        if lons.ndim == 1 and lats.ndim == 1:
            lons, lats = np.meshgrid(lons, lats)
        
        # Get units
        units = getattr(data_da, 'units', _get_units_for_emission_type(emission_type))
        
        ds.close()
    
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")
    
    # Handle nodata values
    if hasattr(data, 'mask'):
        data = np.ma.masked_invalid(data)
    else:
        data = np.ma.masked_invalid(data)
    
    return data, lons, lats, units

def _get_units_for_emission_type(emission_type):
    """Get default units for emission types"""
    units_map = {
        'dust_sum': 'kg yr⁻¹',
        'pm25_deposition': 'kg ha⁻¹ yr⁻¹', 
        'nox_emissions': 'kg N ha⁻¹ yr⁻¹',
        'nh3_emissions': 'kg N ha⁻¹ yr⁻¹',
        'bvoc_emissions': 'kg yr⁻¹'
    }
    return units_map.get(emission_type, 'units')

def create_difference_map(scenario_data, baseline_data, lons, lats,
                         scenario_name, emission_type, units, output_path, show_textbox=False):
    """
    Create a difference map comparing scenario to baseline

    Args:
        scenario_data: Scenario emission data
        baseline_data: Baseline emission data
        lons, lats: Coordinate arrays
        scenario_name: Name of scenario
        emission_type: Type of emission
        units: Data units
        output_path: Output PNG path
        show_textbox: Whether to show statistics text box (default: False)
    """
    
    # Calculate difference
    difference = scenario_data - baseline_data
    
    # Remove areas where either dataset has no data
    valid_mask = ~(scenario_data.mask | baseline_data.mask)
    difference = np.ma.masked_where(~valid_mask, difference)
    
    # Set up the plot with UK-focused projection
    fig = plt.figure(figsize=(12, 10))
    
    # Use a projection centered on the UK
    proj = ccrs.PlateCarree()
    ax = plt.axes(projection=proj)
    
    # Set UK extent (approximate)
    uk_extent = [-8.5, 2.0, 49.5, 61.0]  # [west, east, south, north]
    ax.set_extent(uk_extent, crs=ccrs.PlateCarree())
    
    # Add map features
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8, color='black')
    ax.add_feature(cfeature.BORDERS, linewidth=0.5, color='gray')
    ax.add_feature(cfeature.OCEAN, color='lightblue', alpha=0.3)
    ax.add_feature(cfeature.LAND, color='lightgray', alpha=0.1)
    
    # Calculate colormap range (symmetric around zero)
    abs_diff = np.abs(difference[~difference.mask]) if hasattr(difference, 'mask') else np.abs(difference)
    if len(abs_diff) > 0:
        vmax = np.nanpercentile(abs_diff, 95)  # Use 95th percentile to avoid outliers
        vmin = -vmax
        
        # Ensure we have a valid range
        if vmax == 0 or np.isnan(vmax):
            vmax = 1.0
            vmin = -1.0
    else:
        vmax = 1.0
        vmin = -1.0
    
    # Create diverging colormap (green = beneficial, red = detrimental)
    # For dust emissions: negative difference (less dust) = good = green
    # For dust emissions: positive difference (more dust) = bad = red
    norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
    cmap = plt.cm.RdYlGn_r  # Red-Yellow-Green reversed (green = negative/beneficial, red = positive/detrimental)
    
    # Plot the difference data
    im = ax.pcolormesh(lons, lats, difference, 
                      transform=ccrs.PlateCarree(),
                      cmap=cmap, norm=norm, 
                      shading='nearest', alpha=0.8)
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, orientation='horizontal', 
                       pad=0.05, shrink=0.8, aspect=30)
    cbar.set_label(f'Difference in {emission_type.replace("_", " ").title()} ({units})', 
                   fontsize=12, fontweight='bold')
    cbar.ax.tick_params(labelsize=10)
    
    # Add gridlines
    gl = ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False,
                     linewidth=0.5, color='gray', alpha=0.7)
    gl.top_labels = False
    gl.right_labels = False
    
    # Create title
    title = f'{scenario_name.replace("_", " ").title()} vs Sustainable Current\n{emission_type.replace("_", " ").title()}'
    plt.title(title, fontsize=14, fontweight='bold', pad=20)
    
    # Add summary statistics as text (optional)
    if show_textbox:
        mean_diff = np.nanmean(difference)
        total_diff = np.nansum(difference)

        stats_text = f'Mean difference: {mean_diff:.2e} {units}\nTotal difference: {total_diff:.2e} {units}'
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
               verticalalignment='top', fontsize=10,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Save the plot
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', 
               facecolor='white', edgecolor='none')
    plt.close()
    
    # Calculate and print statistics regardless of textbox setting
    mean_diff = np.nanmean(difference)
    total_diff = np.nansum(difference)

    print(f"Saved plot: {output_path}")
    print(f"  Mean difference: {mean_diff:.2e} {units}")
    print(f"  Total difference: {total_diff:.2e} {units}")

def plot_scenario_difference(scenario_name, emission_type, show_textbox=False):
    """
    Main function to create scenario difference plot

    Args:
        scenario_name: Name of scenario to compare
        emission_type: Type of emission to plot
        show_textbox: Whether to show statistics text box (default: False)
    """
    
    # Define paths
    baseline_name = "sustainable_current"
    results_dir = Path("outputs/uk_results")
    plots_dir = Path("outputs/uk_results/plots")
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    scenario_path = results_dir / scenario_name
    baseline_path = results_dir / baseline_name
    
    # Verify paths exist
    if not scenario_path.exists():
        raise FileNotFoundError(f"Scenario directory not found: {scenario_path}")
    if not baseline_path.exists():
        raise FileNotFoundError(f"Baseline directory not found: {baseline_path}")
    
    print(f"Creating difference plot: {scenario_name} vs {baseline_name}")
    print(f"Emission type: {emission_type}")
    
    # Load data
    scenario_data, lons, lats, units = load_emission_data(scenario_path, emission_type)
    baseline_data, _, _, _ = load_emission_data(baseline_path, emission_type)
    
    # Verify data shapes match
    if scenario_data.shape != baseline_data.shape:
        raise ValueError(f"Data shape mismatch: {scenario_data.shape} vs {baseline_data.shape}")
    
    # Create output filename
    output_filename = f"{scenario_name}_vs_{baseline_name}_{emission_type}.png"
    output_path = plots_dir / output_filename
    
    # Create the plot
    create_difference_map(scenario_data, baseline_data, lons, lats,
                         scenario_name, emission_type, units, output_path, show_textbox)

def main():
    """Main function for command line usage"""

    import argparse

    parser = argparse.ArgumentParser(description='Plot scenario difference maps for UK scenarios')
    parser.add_argument('scenario_name', help='Name of scenario to plot (e.g., grazing_expansion)')
    parser.add_argument('emission_type', help='Type of emission to plot (e.g., dust_sum)')
    parser.add_argument('--show-textbox', action='store_true',
                       help='Show statistics text box on plots (default: hidden)')

    args = parser.parse_args()

    try:
        plot_scenario_difference(args.scenario_name, args.emission_type, args.show_textbox)
        print("✅ Plot created successfully!")

    except Exception as e:
        print(f"❌ Error creating plot: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()