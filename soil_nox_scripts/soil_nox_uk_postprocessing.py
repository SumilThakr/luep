#!/usr/bin/env python3
"""
UK Soil NOx Post-Processing: Crop Global Outputs to UK Extent

This script crops global soil NOx emissions to UK extents, matching the spatial
domain of the UK land-use scenario inputs.

Usage:
    python soil_nox_uk_postprocessing.py <scenario_name>
    python soil_nox_uk_postprocessing.py extensification_current_practices
    
IMPORTANT: Run with the rasters conda environment:
/Users/sumilthakrar/yes/envs/rasters/bin/python soil_nox_scripts/soil_nox_uk_postprocessing.py
"""

import os
import sys
import numpy as np
import pygeoprocessing.geoprocessing as geop
from osgeo import gdal
from datetime import datetime
from pathlib import Path

def get_uk_scenario_reference(scenario_name):
    """
    Get the UK scenario land-use map to use as spatial reference
    
    Args:
        scenario_name: Name of the UK scenario
        
    Returns:
        str: Path to the reference raster file
    """
    
    # Try the standard UK scenario path
    scenario_path = f"scenarios/UKNatureFrontierWithAir/United Kingdom/ScenarioMaps/{scenario_name}.tif"
    
    if os.path.exists(scenario_path):
        return scenario_path
    
    # Alternative: look for any UK scenario file as reference
    scenario_dir = "scenarios/UKNatureFrontierWithAir/United Kingdom/ScenarioMaps"
    if os.path.exists(scenario_dir):
        scenario_files = [f for f in os.listdir(scenario_dir) if f.endswith('.tif')]
        if scenario_files:
            fallback_path = os.path.join(scenario_dir, scenario_files[0])
            print(f"Warning: Specific scenario not found. Using {fallback_path} as spatial reference.")
            return fallback_path
    
    raise FileNotFoundError(f"No UK scenario reference found for {scenario_name}")

def crop_global_to_uk_extent(global_raster_path, uk_reference_path, output_path):
    """
    Crop global raster to UK extent using a UK reference raster
    
    Args:
        global_raster_path: Path to global soil NOx emissions
        uk_reference_path: Path to UK scenario map (spatial reference)
        output_path: Path for UK-cropped output
        
    Returns:
        bool: Success status
    """
    
    print(f"Cropping global raster to UK extent...")
    print(f"  Input: {global_raster_path}")
    print(f"  Reference: {uk_reference_path}")
    print(f"  Output: {output_path}")
    
    try:
        # Get spatial properties of UK reference
        uk_raster_info = geop.get_raster_info(uk_reference_path)
        uk_bbox = uk_raster_info['bounding_box']
        uk_pixel_size = uk_raster_info['pixel_size']
        uk_projection = uk_raster_info['projection_wkt']
        
        print(f"  UK bounding box: {uk_bbox}")
        print(f"  UK pixel size: {uk_pixel_size}")
        
        # Create output directory
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Use warp_raster to crop to UK extent
        geop.warp_raster(
            base_raster_path=global_raster_path,
            target_pixel_size=uk_pixel_size,
            target_raster_path=output_path,
            resample_method='bilinear',
            target_bb=uk_bbox,
            target_projection_wkt=uk_projection
        )
        
        print(f"  ✅ Successfully cropped to UK extent: {output_path}")
        return True
        
    except Exception as e:
        print(f"  ❌ Error cropping raster: {str(e)}")
        return False

def generate_uk_statistics(uk_raster_path, scenario_name, output_stats_path):
    """
    Generate statistics for UK-cropped soil NOx emissions
    
    Args:
        uk_raster_path: Path to UK-cropped soil NOx emissions
        scenario_name: Name of the scenario
        output_stats_path: Path for statistics output
    """
    
    print(f"Generating UK-specific statistics...")
    
    try:
        # Read UK soil NOx data
        uk_nox_array = geop.raster_to_numpy_array(uk_raster_path)
        uk_raster_info = geop.get_raster_info(uk_raster_path)
        
        # Calculate pixel area in hectares
        pixel_size = uk_raster_info['pixel_size']
        pixel_width = abs(pixel_size[0])
        pixel_height = abs(pixel_size[1])
        
        # Check if coordinates are in degrees (WGS84)
        projection_wkt = uk_raster_info['projection_wkt']
        if 'degree' in projection_wkt.lower() or 'GEOGCS' in projection_wkt:
            # Geographic coordinates - convert to hectares
            bbox = uk_raster_info['bounding_box']
            center_lat = (bbox[1] + bbox[3]) / 2
            lat_to_m = 111000  # meters per degree latitude
            lon_to_m = 111000 * np.cos(np.radians(center_lat))  # meters per degree longitude
            pixel_area_m2 = (pixel_width * lon_to_m) * (pixel_height * lat_to_m)
        else:
            # Projected coordinates (assumed meters)
            pixel_area_m2 = pixel_width * pixel_height
        
        pixel_area_ha = pixel_area_m2 / 10000  # Convert to hectares
        
        # Calculate statistics (exclude nodata values)
        valid_mask = (uk_nox_array != -1) & (~np.isnan(uk_nox_array))
        uk_nox_valid = uk_nox_array[valid_mask]
        
        # UK geographic bounds for reference
        uk_bbox = uk_raster_info['bounding_box']
        
        with open(output_stats_path, 'w') as f:
            f.write("UK Soil NOx Emissions Summary (UK Extent)\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Scenario: {scenario_name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("Processing: Cropped from global output to UK extent\n\n")
            
            f.write("SPATIAL EXTENT:\n")
            f.write("-" * 30 + "\n")
            f.write(f"Longitude range: {uk_bbox[0]:.3f} to {uk_bbox[2]:.3f}\n")
            f.write(f"Latitude range: {uk_bbox[1]:.3f} to {uk_bbox[3]:.3f}\n")
            f.write(f"Total pixels: {uk_nox_array.size:,}\n")
            f.write(f"Valid pixels: {len(uk_nox_valid):,}\n")
            f.write(f"Pixel area: {pixel_area_ha:.6f} hectares per pixel\n")
            f.write(f"Total area: {len(uk_nox_valid) * pixel_area_ha:,.1f} hectares\n\n")
            
            if len(uk_nox_valid) > 0:
                f.write("UK SOIL NOx EMISSIONS:\n")
                f.write("-" * 30 + "\n")
                f.write(f"Min emission: {np.min(uk_nox_valid):.6f}\n")
                f.write(f"Max emission: {np.max(uk_nox_valid):.6f}\n")
                f.write(f"Mean emission: {np.mean(uk_nox_valid):.6f}\n")
                f.write(f"Median emission: {np.median(uk_nox_valid):.6f}\n")
                f.write(f"Std deviation: {np.std(uk_nox_valid):.6f}\n")
                f.write(f"Total UK emission: {np.sum(uk_nox_valid):.2f}\n\n")
                
                # Percentile analysis
                percentiles = [10, 25, 75, 90, 95, 99]
                f.write("EMISSION PERCENTILES:\n")
                f.write("-" * 30 + "\n")
                for p in percentiles:
                    value = np.percentile(uk_nox_valid, p)
                    f.write(f"{p}th percentile: {value:.6f}\n")
                f.write("\n")
                
            else:
                f.write("No valid emission data found in UK extent.\n\n")
                
            f.write("MODEL INFORMATION:\n")
            f.write("-" * 30 + "\n")
            f.write("Base equation: NOx = SOC × pH × exp(climate) × exp(-1.8327) × LU × exp(-0.11×T0) × TS_SM × N\n")
            f.write("Nitrogen coefficient: 0.03545 (Yan et al. 2005)\n")
            f.write("Temporal factor: 122/365 (growing season)\n")
            f.write("N effect formula: 1.0 + (0.03545 × N_rate × 122/365)\n")
            f.write("Processing: Global calculation cropped to UK extent\n\n")
                
        print(f"  ✅ UK statistics saved to: {output_stats_path}")
        
        # Return key statistics for validation
        return {
            'total_pixels': uk_nox_array.size,
            'valid_pixels': len(uk_nox_valid),
            'total_emission': np.sum(uk_nox_valid) if len(uk_nox_valid) > 0 else 0,
            'mean_emission': np.mean(uk_nox_valid) if len(uk_nox_valid) > 0 else 0,
            'bbox': uk_bbox
        }
        
    except Exception as e:
        print(f"  ❌ Error generating UK statistics: {str(e)}")
        return None

def compare_global_vs_uk(global_stats_path, uk_stats_path, output_comparison_path):
    """
    Generate comparison between global and UK statistics
    
    Args:
        global_stats_path: Path to global statistics file
        uk_stats_path: Path to UK statistics file  
        output_comparison_path: Path for comparison output
    """
    
    try:
        print(f"Generating global vs UK comparison...")
        
        # Read key values from both files
        global_total = None
        uk_total = None
        
        if os.path.exists(global_stats_path):
            with open(global_stats_path, 'r') as f:
                for line in f:
                    if 'Total emission:' in line:
                        global_total = float(line.split(':')[1].strip())
                        break
        
        if os.path.exists(uk_stats_path):
            with open(uk_stats_path, 'r') as f:
                for line in f:
                    if 'Total UK emission:' in line:
                        uk_total = float(line.split(':')[1].strip())
                        break
        
        with open(output_comparison_path, 'w') as f:
            f.write("Global vs UK Soil NOx Emissions Comparison\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            if global_total is not None and uk_total is not None:
                uk_fraction = (uk_total / global_total) * 100 if global_total > 0 else 0
                f.write("EMISSION TOTALS:\n")
                f.write("-" * 20 + "\n")
                f.write(f"Global total: {global_total:,.2f}\n")
                f.write(f"UK total: {uk_total:,.2f}\n")
                f.write(f"UK fraction: {uk_fraction:.3f}% of global\n\n")
            else:
                f.write("Could not extract emission totals for comparison.\n\n")
            
            f.write("PROCESSING NOTES:\n")
            f.write("-" * 20 + "\n")
            f.write("• Global emissions calculated using Yan et al. (2005) model\n")
            f.write("• UK emissions are cropped subset of global results\n")
            f.write("• Scenario-specific nitrogen fertilization applied\n")
            f.write("• UK extent approximately -8.17 to 1.77°E, 49.91 to 60.85°N\n")
        
        print(f"  ✅ Comparison saved to: {output_comparison_path}")
        
    except Exception as e:
        print(f"  ❌ Error generating comparison: {str(e)}")

def process_scenario_uk_cropping(scenario_name, validate=True):
    """
    Process a single scenario for UK cropping
    
    Args:
        scenario_name: Name of the UK scenario
        validate: Whether to generate validation outputs
        
    Returns:
        bool: Success status
    """
    
    print(f"Processing UK cropping for scenario: {scenario_name}")
    print("=" * 60)
    
    # Define file paths
    global_nox_path = f"outputs/uk_results/{scenario_name}/nox_emissions.tif"
    uk_nox_path = f"outputs/uk_results/{scenario_name}/nox_emissions_uk.tif"
    global_stats_path = f"outputs/uk_results/{scenario_name}/soil_nox_summary.txt"
    uk_stats_path = f"outputs/uk_results/{scenario_name}/soil_nox_summary_uk.txt"
    comparison_path = f"outputs/uk_results/{scenario_name}/global_vs_uk_comparison.txt"
    
    # Check if global emissions file exists
    if not os.path.exists(global_nox_path):
        print(f"❌ Global soil NOx file not found: {global_nox_path}")
        return False
    
    try:
        # Step 1: Get UK reference raster
        uk_reference_path = get_uk_scenario_reference(scenario_name)
        print(f"Using UK spatial reference: {uk_reference_path}")
        
        # Step 2: Crop global emissions to UK extent
        success = crop_global_to_uk_extent(global_nox_path, uk_reference_path, uk_nox_path)
        if not success:
            return False
        
        # Step 3: Generate UK-specific statistics
        uk_stats = generate_uk_statistics(uk_nox_path, scenario_name, uk_stats_path)
        if uk_stats is None:
            return False
        
        # Step 4: Generate comparison (if validation requested)
        if validate:
            compare_global_vs_uk(global_stats_path, uk_stats_path, comparison_path)
        
        print(f"✅ UK cropping completed successfully for: {scenario_name}")
        print(f"   UK emissions file: {uk_nox_path}")
        print(f"   UK statistics: {uk_stats_path}")
        if validate:
            print(f"   Comparison: {comparison_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error processing scenario {scenario_name}: {str(e)}")
        return False

def main():
    """Main function"""
    
    if len(sys.argv) < 2:
        print("Usage: python soil_nox_uk_postprocessing.py <scenario_name>")
        print("Example: python soil_nox_uk_postprocessing.py extensification_current_practices")
        sys.exit(1)
    
    scenario_name = sys.argv[1]
    validate = "--validate" in sys.argv or "--val" in sys.argv
    
    print("UK Soil NOx Post-Processing")
    print("=" * 60)
    print("Cropping global soil NOx emissions to UK extent")
    print(f"Scenario: {scenario_name}")
    print(f"Validation: {'Enabled' if validate else 'Disabled'}")
    print()
    
    success = process_scenario_uk_cropping(scenario_name, validate)
    
    if success:
        print(f"\n✅ UK post-processing completed successfully for: {scenario_name}")
    else:
        print(f"\n❌ UK post-processing failed for: {scenario_name}")
        sys.exit(1)

if __name__ == "__main__":
    main()