#!/usr/bin/env python3
"""
Plot Total Economic Value for UK Scenarios

This script creates plots comparing total economic value across UK land use scenarios.
It sums cropland, grazing, and forestry economic values to show overall economic impact.

Usage:
    python plotting_scripts/plot_total_economic_value.py <scenario_name>
    python plotting_scripts/plot_total_economic_value.py <scenario_name> --vs-baseline
    python plotting_scripts/plot_total_economic_value.py <scenario_name> --show-textbox

Examples:
    python plotting_scripts/plot_total_economic_value.py grazing_expansion
    python plotting_scripts/plot_total_economic_value.py forestry_expansion --vs-baseline
    python plotting_scripts/plot_total_economic_value.py grazing_expansion --show-textbox
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from pathlib import Path
import rasterio
from matplotlib.colors import TwoSlopeNorm
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import argparse

def load_economic_data(scenario_name):
    """
    Load and sum economic value data for cropland, grazing, and forestry
    
    Args:
        scenario_name: Name of scenario (e.g., 'grazing_expansion')
        
    Returns:
        tuple: (total_economic_data, lons, lats, component_data_dict)
    """
    
    # Define the path to the ecosystem services data
    model_results_dir = Path("scenarios/UKNatureFrontierWithAir/United Kingdom/ModelResults")
    
    # Economic value components to sum
    economic_components = ['cropland_value', 'grazing_value', 'forestry_value']
    component_data = {}
    lons = None
    lats = None

    print(f"Loading economic value components for {scenario_name}:")

    # Load each component
    for component in economic_components:
        file_path = model_results_dir / f"{scenario_name}_{component}.tif"
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        print(f"  - Loading {component} from {file_path}")
        
        with rasterio.open(file_path) as src:
            data = src.read(1)

            # Get coordinate arrays (only once)
            if lons is None:
                height, width = data.shape
                # Create coordinate arrays properly
                transform = src.transform
                x_coords = np.array([transform[2] + transform[0] * (j + 0.5) for j in range(width)])
                y_coords = np.array([transform[5] + transform[4] * (i + 0.5) for i in range(height)])
                lons, lats = np.meshgrid(x_coords, y_coords)
        
        # Handle nodata values
        data = np.ma.masked_invalid(data)
        component_data[component] = data
    
    # Sum all economic components
    total_economic_value = np.zeros_like(component_data['cropland_value'])
    
    for component, data in component_data.items():
        # Replace masked values with 0 for summation
        data_filled = np.ma.filled(data, 0)
        total_economic_value += data_filled
    
    # Mask pixels where all components were invalid
    all_masked = np.all([data.mask for data in component_data.values()], axis=0)
    total_economic_value = np.ma.masked_where(all_masked, total_economic_value)
    
    print(f"Total economic value statistics:")
    print(f"  - Min: {np.ma.min(total_economic_value):.2f} £ ha⁻¹ yr⁻¹")
    print(f"  - Max: {np.ma.max(total_economic_value):.2f} £ ha⁻¹ yr⁻¹")
    print(f"  - Mean: {np.ma.mean(total_economic_value):.2f} £ ha⁻¹ yr⁻¹")
    print(f"  - Total: {np.ma.sum(total_economic_value):.2e} £ yr⁻¹")
    
    return total_economic_value, lons, lats, component_data

def create_total_economic_value_map(economic_data, lons, lats, scenario_name, output_path, show_textbox=False):
    """
    Create a map showing total economic value for a scenario

    Args:
        economic_data: Total economic value data
        lons, lats: Coordinate arrays
        scenario_name: Name of scenario
        output_path: Output PNG path
        show_textbox: Whether to show statistics text box (default: False)
    """
    
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
    
    # Calculate colormap range
    valid_data = economic_data[~economic_data.mask] if hasattr(economic_data, 'mask') else economic_data
    if len(valid_data) > 0:
        vmin = np.nanpercentile(valid_data, 5)   # Use 5th percentile to avoid outliers
        vmax = np.nanpercentile(valid_data, 95)  # Use 95th percentile to avoid outliers
        
        # Ensure we have a valid range
        if vmax == vmin or np.isnan(vmax) or np.isnan(vmin):
            vmax = np.nanmax(valid_data)
            vmin = np.nanmin(valid_data)
            if vmax == vmin:
                vmax = vmin + 1.0
    else:
        vmax = 1.0
        vmin = 0.0
    
    # Use a colormap that shows economic value (green = high value)
    cmap = plt.cm.RdYlGn
    
    # Plot the economic data
    im = ax.pcolormesh(lons, lats, economic_data, 
                      transform=ccrs.PlateCarree(),
                      cmap=cmap, vmin=vmin, vmax=vmax,
                      shading='nearest', alpha=0.8)
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, orientation='horizontal', 
                       pad=0.05, shrink=0.8, aspect=30)
    cbar.set_label('Total Economic Value (£ ha⁻¹ yr⁻¹)', 
                   fontsize=12, fontweight='bold')
    cbar.ax.tick_params(labelsize=10)
    
    # Add gridlines
    gl = ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False,
                     linewidth=0.5, color='gray', alpha=0.7)
    gl.top_labels = False
    gl.right_labels = False
    
    # Create title
    title = f'{scenario_name.replace("_", " ").title()}\nTotal Economic Value (Cropland + Grazing + Forestry)'
    plt.title(title, fontsize=14, fontweight='bold', pad=20)
    
    # Add summary statistics as text (optional)
    if show_textbox:
        mean_value = np.ma.mean(economic_data)
        total_value = np.ma.sum(economic_data)

        stats_text = f'Mean: {mean_value:.1f} £ ha⁻¹ yr⁻¹\nTotal: {total_value:.2e} £ yr⁻¹'

        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
               verticalalignment='top', fontsize=10,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Save the plot
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', 
               facecolor='white', edgecolor='none')
    plt.close()
    
    print(f"Saved plot: {output_path}")

def create_total_economic_difference_map(scenario_data, baseline_data, lons, lats,
                                       scenario_name, baseline_name, output_path, show_textbox=False):
    """
    Create a difference map comparing scenario to baseline for total economic value

    Args:
        scenario_data: Scenario total economic data
        baseline_data: Baseline total economic data
        lons, lats: Coordinate arrays
        scenario_name: Name of scenario
        baseline_name: Name of baseline scenario
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
    
    # Create diverging colormap (green = positive change, red = negative change)
    norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
    cmap = plt.cm.RdYlGn  # Green = positive (economic gain), Red = negative (economic loss)
    
    # Plot the difference data
    im = ax.pcolormesh(lons, lats, difference, 
                      transform=ccrs.PlateCarree(),
                      cmap=cmap, norm=norm, 
                      shading='nearest', alpha=0.8)
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, orientation='horizontal', 
                       pad=0.05, shrink=0.8, aspect=30)
    cbar.set_label('Difference in Total Economic Value (£ ha⁻¹ yr⁻¹)', 
                   fontsize=12, fontweight='bold')
    cbar.ax.tick_params(labelsize=10)
    
    # Add gridlines
    gl = ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False,
                     linewidth=0.5, color='gray', alpha=0.7)
    gl.top_labels = False
    gl.right_labels = False
    
    # Create title
    title = f'{scenario_name.replace("_", " ").title()} vs {baseline_name.replace("_", " ").title()}\nTotal Economic Value Difference'
    plt.title(title, fontsize=14, fontweight='bold', pad=20)
    
    # Add summary statistics as text (optional)
    if show_textbox:
        mean_diff = np.ma.mean(difference)
        total_diff = np.ma.sum(difference)

        interpretation = "Green = economic gain, Red = economic loss"
        stats_text = f'Mean difference: {mean_diff:.1f} £ ha⁻¹ yr⁻¹\nTotal difference: {total_diff:.2e} £ yr⁻¹\n{interpretation}'

        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
               verticalalignment='top', fontsize=10,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Save the plot
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', 
               facecolor='white', edgecolor='none')
    plt.close()
    
    # Calculate and print statistics regardless of textbox setting
    mean_diff = np.ma.mean(difference)
    total_diff = np.ma.sum(difference)

    print(f"Saved plot: {output_path}")
    print(f"  Mean difference: {mean_diff:.1f} £ ha⁻¹ yr⁻¹")
    print(f"  Total difference: {total_diff:.2e} £ yr⁻¹")

def plot_total_economic_value(scenario_name, vs_baseline=False, show_textbox=False):
    """
    Main function to create total economic value plots

    Args:
        scenario_name: Name of scenario to plot
        vs_baseline: If True, create difference plot vs sustainable_current
        show_textbox: If True, show statistics text box on plots
    """
    
    # Define paths
    plots_dir = Path("outputs/uk_results/plots")
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Creating total economic value plot for: {scenario_name}")
    if vs_baseline:
        print("Including comparison to sustainable_current baseline")
    
    # Load scenario data
    scenario_data, lons, lats, scenario_components = load_economic_data(scenario_name)
    
    # Create absolute value plot
    output_filename = f"{scenario_name}_total_economic_value.png"
    output_path = plots_dir / output_filename
    create_total_economic_value_map(scenario_data, lons, lats, scenario_name, output_path, show_textbox)
    
    # Create difference plot if requested
    if vs_baseline:
        baseline_name = "sustainable_current"
        print(f"\nLoading baseline data: {baseline_name}")
        baseline_data, _, _, baseline_components = load_economic_data(baseline_name)
        
        # Verify data shapes match
        if scenario_data.shape != baseline_data.shape:
            raise ValueError(f"Data shape mismatch: {scenario_data.shape} vs {baseline_data.shape}")
        
        # Create difference plot
        diff_filename = f"{scenario_name}_vs_{baseline_name}_total_economic_difference.png"
        diff_output_path = plots_dir / diff_filename
        create_total_economic_difference_map(scenario_data, baseline_data, lons, lats,
                                           scenario_name, baseline_name, diff_output_path, show_textbox)

def main():
    """Main function for command line usage"""
    
    parser = argparse.ArgumentParser(description='Plot total economic value for UK scenarios')
    parser.add_argument('scenario_name', help='Name of scenario to plot (e.g., grazing_expansion)')
    parser.add_argument('--vs-baseline', action='store_true',
                       help='Also create difference plot vs sustainable_current')
    parser.add_argument('--show-textbox', action='store_true',
                       help='Show statistics text box on plots (default: hidden)')
    
    args = parser.parse_args()
    
    try:
        plot_total_economic_value(args.scenario_name, args.vs_baseline, args.show_textbox)
        print("✅ Total economic value plots created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating plots: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()