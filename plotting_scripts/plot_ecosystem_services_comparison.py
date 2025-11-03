#!/usr/bin/env python3
"""
Plot UK Scenario Ecosystem Services Comparison

This script creates difference maps comparing UK land use scenarios against 
the "sustainable current" baseline for various ecosystem services.

Usage:
    python plot_ecosystem_services_comparison.py <scenario_name> [ecosystem_service] [--show-textbox]

Example:
    python plot_ecosystem_services_comparison.py grazing_expansion
    python plot_ecosystem_services_comparison.py forestry_expansion biodiversity
    python plot_ecosystem_services_comparison.py grazing_expansion all
    python plot_ecosystem_services_comparison.py forestry_expansion carbon --show-textbox

Supported ecosystem services:
    - biodiversity (biodiversity index)
    - carbon (carbon storage)
    - cropland_value (economic value of cropland)
    - forestry_value (economic value of forestry)
    - grazing_methane (methane emissions from grazing)
    - grazing_value (economic value of grazing)
    - ground_noxn (ground nitrogen oxide)
    - nitrate_cancer_cases (nitrate-related cancer cases)
    - noxn_in_drinking_water (nitrogen oxide in drinking water)
    - surface_noxn (surface nitrogen oxide) 
    - transition_cost (cost of land use transition)
    - all (generate plots for all services)
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
import time

def load_ecosystem_service_data(scenario_name, service_name):
    """
    Load ecosystem service data for a specific scenario and service
    
    Args:
        scenario_name: Name of scenario (e.g., 'grazing_expansion')
        service_name: Name of service (e.g., 'biodiversity')
        
    Returns:
        tuple: (data_array, lons, lats, units)
    """
    
    # Define the path to the ecosystem services data
    model_results_dir = Path("scenarios/UKNatureFrontierWithAir/United Kingdom/ModelResults")
    file_path = model_results_dir / f"{scenario_name}_{service_name}.tif"
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    print(f"Loading {service_name} for {scenario_name} from {file_path}")
    
    # Load GeoTIFF file with rasterio
    with rasterio.open(file_path) as src:
        data = src.read(1)
        
        # Get coordinate arrays properly
        height, width = data.shape
        # Create coordinate arrays properly
        transform = src.transform
        x_coords = np.array([transform[2] + transform[0] * (j + 0.5) for j in range(width)])
        y_coords = np.array([transform[5] + transform[4] * (i + 0.5) for i in range(height)])
        lons, lats = np.meshgrid(x_coords, y_coords)
        
        # Get units from metadata or set defaults
        units = _get_units_for_service(service_name)
    
    # Handle nodata values
    if hasattr(data, 'mask'):
        data = np.ma.masked_invalid(data)
    else:
        data = np.ma.masked_invalid(data)
    
    return data, lons, lats, units

def _get_units_for_service(service_name):
    """Get default units for ecosystem services"""
    units_map = {
        'biodiversity': 'index',
        'carbon': 'Mg C ha⁻¹',
        'cropland_value': '£ ha⁻¹ yr⁻¹',
        'forestry_value': '£ ha⁻¹ yr⁻¹',
        'grazing_methane': 'kg CH₄ ha⁻¹ yr⁻¹',
        'grazing_value': '£ ha⁻¹ yr⁻¹',
        'ground_noxn': 'kg N ha⁻¹ yr⁻¹',
        'nitrate_cancer_cases': 'cases per 100,000',
        'noxn_in_drinking_water': 'mg N L⁻¹',
        'surface_noxn': 'kg N ha⁻¹ yr⁻¹',
        'transition_cost': '£ ha⁻¹'
    }
    return units_map.get(service_name, 'units')

def _get_service_info(service_name):
    """Get plotting information for each service"""
    service_info = {
        'biodiversity': {
            'title': 'Biodiversity Index',
            'cmap': 'RdYlGn',
            'positive_is_good': True
        },
        'carbon': {
            'title': 'Carbon Storage', 
            'cmap': 'RdYlGn',
            'positive_is_good': True
        },
        'cropland_value': {
            'title': 'Cropland Economic Value',
            'cmap': 'RdYlGn', 
            'positive_is_good': True
        },
        'forestry_value': {
            'title': 'Forestry Economic Value',
            'cmap': 'RdYlGn',
            'positive_is_good': True
        },
        'grazing_methane': {
            'title': 'Grazing Methane Emissions',
            'cmap': 'RdYlGn_r',
            'positive_is_good': False
        },
        'grazing_value': {
            'title': 'Grazing Economic Value',
            'cmap': 'RdYlGn',
            'positive_is_good': True
        },
        'ground_noxn': {
            'title': 'Ground Nitrogen Oxide',
            'cmap': 'RdYlGn_r', 
            'positive_is_good': False
        },
        'nitrate_cancer_cases': {
            'title': 'Nitrate Cancer Cases',
            'cmap': 'RdYlGn_r',
            'positive_is_good': False
        },
        'noxn_in_drinking_water': {
            'title': 'NOx in Drinking Water',
            'cmap': 'RdYlGn_r',
            'positive_is_good': False
        },
        'surface_noxn': {
            'title': 'Surface Nitrogen Oxide',
            'cmap': 'RdYlGn_r',
            'positive_is_good': False
        },
        'transition_cost': {
            'title': 'Transition Cost',
            'cmap': 'RdYlGn_r',
            'positive_is_good': False
        }
    }
    return service_info.get(service_name, {
        'title': service_name.replace('_', ' ').title(),
        'cmap': 'RdBu_r',
        'positive_is_good': None
    })

def create_ecosystem_service_difference_map(scenario_data, baseline_data, lons, lats,
                                          scenario_name, service_name, units, output_path, show_textbox=False):
    """
    Create a difference map comparing scenario to baseline for ecosystem services

    Args:
        scenario_data: Scenario service data
        baseline_data: Baseline service data
        lons, lats: Coordinate arrays
        scenario_name: Name of scenario
        service_name: Name of ecosystem service
        units: Data units
        output_path: Output PNG path
        show_textbox: Whether to show statistics text box (default: False)
    """
    
    # Calculate difference
    difference = scenario_data - baseline_data
    
    # Remove areas where either dataset has no data
    valid_mask = ~(scenario_data.mask | baseline_data.mask)
    difference = np.ma.masked_where(~valid_mask, difference)
    
    # Get service-specific information
    service_info = _get_service_info(service_name)
    
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
    
    # Create diverging colormap based on whether positive is good or bad
    norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
    
    # Choose colormap based on service type
    if service_info['positive_is_good'] is True:
        cmap = plt.cm.RdYlGn  # Green = positive (good), Red = negative (bad)
    elif service_info['positive_is_good'] is False:
        cmap = plt.cm.RdYlGn_r  # Red = positive (bad), Green = negative (good)
    else:
        cmap = plt.cm.RdBu_r  # Neutral: Red = positive, Blue = negative
    
    # Plot the difference data
    im = ax.pcolormesh(lons, lats, difference, 
                      transform=ccrs.PlateCarree(),
                      cmap=cmap, norm=norm, 
                      shading='nearest', alpha=0.8)
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, orientation='horizontal', 
                       pad=0.05, shrink=0.8, aspect=30)
    cbar.set_label(f'Difference in {service_info["title"]} ({units})', 
                   fontsize=12, fontweight='bold')
    cbar.ax.tick_params(labelsize=10)
    
    # Add gridlines
    gl = ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False,
                     linewidth=0.5, color='gray', alpha=0.7)
    gl.top_labels = False
    gl.right_labels = False
    
    # Create title
    title = f'{scenario_name.replace("_", " ").title()} vs Sustainable Current\n{service_info["title"]}'
    plt.title(title, fontsize=14, fontweight='bold', pad=20)
    
    # Add summary statistics as text (optional)
    if show_textbox:
        mean_diff = np.nanmean(difference)
        total_diff = np.nansum(difference) if service_name not in ['nitrate_cancer_cases', 'noxn_in_drinking_water'] else np.nanmean(difference)

        # Create interpretation text based on service type
        if service_info['positive_is_good'] is True:
            interpretation = "Green = improvement, Red = degradation"
        elif service_info['positive_is_good'] is False:
            interpretation = "Green = reduction (good), Red = increase (bad)"
        else:
            interpretation = "Red = increase, Green = decrease"

        stats_text = f'Mean difference: {mean_diff:.2e} {units}\n{interpretation}'
        if service_name not in ['nitrate_cancer_cases', 'noxn_in_drinking_water']:
            stats_text = f'Mean difference: {mean_diff:.2e} {units}\nTotal difference: {total_diff:.2e} {units}\n{interpretation}'

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
    total_diff = np.nansum(difference) if service_name not in ['nitrate_cancer_cases', 'noxn_in_drinking_water'] else np.nanmean(difference)

    print(f"Saved plot: {output_path}")
    print(f"  Mean difference: {mean_diff:.2e} {units}")
    if service_name not in ['nitrate_cancer_cases', 'noxn_in_drinking_water']:
        print(f"  Total difference: {total_diff:.2e} {units}")

def plot_ecosystem_service_comparison(scenario_name, service_name, show_textbox=False):
    """
    Main function to create ecosystem service comparison plot

    Args:
        scenario_name: Name of scenario to compare
        service_name: Name of ecosystem service to plot
        show_textbox: Whether to show statistics text box (default: False)
    """
    
    # Define paths
    baseline_name = "sustainable_current"
    plots_dir = Path("outputs/uk_results/plots")
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Creating ecosystem service difference plot: {scenario_name} vs {baseline_name}")
    print(f"Service: {service_name}")
    
    # Load data
    scenario_data, lons, lats, units = load_ecosystem_service_data(scenario_name, service_name)
    baseline_data, _, _, _ = load_ecosystem_service_data(baseline_name, service_name)
    
    # Verify data shapes match
    if scenario_data.shape != baseline_data.shape:
        raise ValueError(f"Data shape mismatch: {scenario_data.shape} vs {baseline_data.shape}")
    
    # Create output filename
    output_filename = f"{scenario_name}_vs_{baseline_name}_{service_name}_ecosystem_service.png"
    output_path = plots_dir / output_filename
    
    # Create the plot
    create_ecosystem_service_difference_map(scenario_data, baseline_data, lons, lats,
                                          scenario_name, service_name, units, output_path, show_textbox)

def process_all_services(scenario_name, show_textbox=False):
    """
    Process all ecosystem services for a given scenario

    Args:
        scenario_name: Name of scenario to compare
        show_textbox: Whether to show statistics text box (default: False)
    """
    
    # Define all available ecosystem services
    services = [
        'biodiversity',
        'carbon', 
        'cropland_value',
        'forestry_value',
        'grazing_methane',
        'grazing_value',
        'ground_noxn',
        'nitrate_cancer_cases',
        'noxn_in_drinking_water',
        'surface_noxn',
        'transition_cost'
    ]
    
    print(f"🌿 Processing all ecosystem services for {scenario_name}")
    print(f"Services to process: {len(services)}")
    
    successful = 0
    failed = []
    
    start_time = time.time()
    
    for i, service in enumerate(services, 1):
        print(f"\n📊 Processing {i}/{len(services)}: {service}")
        
        try:
            plot_ecosystem_service_comparison(scenario_name, service, show_textbox)
            successful += 1
            print(f"  ✅ Success")
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            failed.append(service)
    
    duration = time.time() - start_time
    
    print(f"\n{'='*60}")
    print(f"🎯 ECOSYSTEM SERVICES PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"✅ Successful: {successful}/{len(services)}")
    print(f"❌ Failed: {len(failed)}/{len(services)}")
    print(f"⏱️  Duration: {duration/60:.1f} minutes")
    
    if failed:
        print(f"\nFailed services:")
        for service in failed:
            print(f"  ❌ {service}")

def main():
    """Main function for command line usage"""

    import argparse

    parser = argparse.ArgumentParser(description='Plot ecosystem services comparison for UK scenarios')
    parser.add_argument('scenario_name', help='Name of scenario to plot (e.g., grazing_expansion)')
    parser.add_argument('service_name', nargs='?', default='all',
                       help='Ecosystem service to plot (default: all)')
    parser.add_argument('--show-textbox', action='store_true',
                       help='Show statistics text box on plots (default: hidden)')

    args = parser.parse_args()

    try:
        if args.service_name == "all":
            process_all_services(args.scenario_name, args.show_textbox)
        else:
            plot_ecosystem_service_comparison(args.scenario_name, args.service_name, args.show_textbox)

        print("✅ Ecosystem service plots created successfully!")

    except Exception as e:
        print(f"❌ Error creating plots: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()