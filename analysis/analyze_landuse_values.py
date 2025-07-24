#!/usr/bin/env python3
"""
Analyze land use values in global and UK scenario files to identify
potential problematic values beyond water (0).
"""

import numpy as np
import pygeoprocessing.geoprocessing as geop
import os
import glob

def analyze_raster_values(raster_path, description=""):
    """Analyze unique values in a raster file"""
    print(f"\n🔍 Analyzing {description}: {raster_path}")
    
    if not os.path.exists(raster_path):
        print(f"   ❌ File not found: {raster_path}")
        return None
    
    try:
        # Use pygeoprocessing to read raster data
        raster_info = geop.get_raster_info(raster_path)
        print(f"   📋 Raster info: {raster_info['raster_size']} pixels, NoData: {raster_info['nodata']}")
        
        # Read the raster data
        def get_unique_values(array):
            unique_vals = np.unique(array)
            # Filter out NoData values
            if raster_info['nodata'] is not None:
                unique_vals = unique_vals[unique_vals != raster_info['nodata']]
            # Filter out NaN values
            unique_vals = unique_vals[~np.isnan(unique_vals)]
            return unique_vals
        
        # Use raster_calculator to get unique values
        unique_values = None
        value_counts = {}
        
        def collect_values(array):
            nonlocal unique_values, value_counts
            flat_array = array.flatten()
            # Filter valid values
            if raster_info['nodata'] is not None:
                valid_array = flat_array[flat_array != raster_info['nodata']]
            else:
                valid_array = flat_array
            valid_array = valid_array[~np.isnan(valid_array)]
            
            if len(valid_array) > 0:
                unique_vals = np.unique(valid_array)
                unique_values = unique_vals
                
                # Count occurrences
                for val in unique_vals:
                    count = np.sum(valid_array == val)
                    value_counts[int(val)] = count
            
            return array  # Return unchanged array
        
        # Process the raster
        temp_output = "temp_analysis.tif"
        geop.raster_calculator(
            base_raster_path_band_const_list=[(raster_path, 1)],
            local_op=collect_values,
            target_raster_path=temp_output,
            datatype_target=raster_info['datatype'],
            nodata_target=raster_info['nodata']
        )
        
        # Clean up temp file
        if os.path.exists(temp_output):
            os.remove(temp_output)
        
        if unique_values is not None and len(unique_values) > 0:
            print(f"   📊 Range: {unique_values.min():.0f} to {unique_values.max():.0f}")
            print(f"   📊 Unique values ({len(unique_values)}): {sorted(unique_values.astype(int))}")
            
            print(f"   📊 Value counts (top 10):")
            sorted_counts = sorted(value_counts.items(), key=lambda x: x[1], reverse=True)
            for val, count in sorted_counts[:10]:
                print(f"      Value {val}: {count:,} pixels")
            
            # Check for problematic values
            problematic = []
            for val in unique_values:
                if val < 0 or val > 23:  # Expected range is 0-23
                    problematic.append(int(val))
            
            if problematic:
                print(f"   ⚠️  PROBLEMATIC VALUES (outside 0-23 range): {problematic}")
            else:
                print(f"   ✅ All values within expected range (0-23)")
            
            return {
                'unique_values': unique_values.astype(int),
                'value_counts': value_counts,
                'problematic': problematic,
                'nodata': raster_info['nodata']
            }
        else:
            print(f"   ❌ No valid data found in raster")
            return None
        
    except Exception as e:
        print(f"   ❌ Error analyzing {raster_path}: {e}")
        return None

def main():
    print("🌍 Land Use Value Analysis")
    print("=" * 50)
    
    # Analyze global land use file
    global_lu = "inputs/gblulcg20_10000.tif"
    global_results = analyze_raster_values(global_lu, "Global Land Use")
    
    # Analyze UK scenario files
    uk_scenario_pattern = "scenarios/UKNatureFrontierWithAir/United Kingdom/ScenarioMaps/*.tif"
    uk_files = glob.glob(uk_scenario_pattern)
    
    if uk_files:
        print(f"\n🇬🇧 Found {len(uk_files)} UK scenario files")
        for uk_file in sorted(uk_files)[:5]:  # Analyze first 5 files
            scenario_name = os.path.basename(uk_file).replace('.tif', '')
            uk_results = analyze_raster_values(uk_file, f"UK Scenario: {scenario_name}")
    else:
        print(f"\n🇬🇧 No UK scenario files found matching: {uk_scenario_pattern}")
    
    # Check if we have any land use files in the current directory
    current_lu_files = glob.glob("*.tif")
    landuse_files = [f for f in current_lu_files if 'landuse' in f.lower() or 'lulc' in f.lower() or 'gblulcg' in f.lower()]
    
    if landuse_files:
        print(f"\n📁 Found additional land use files in current directory:")
        for lu_file in landuse_files:
            analyze_raster_values(lu_file, f"Additional Land Use: {lu_file}")
    
    print("\n" + "=" * 50)
    print("🎯 ANALYSIS SUMMARY")
    print("=" * 50)
    
    # Provide recommendations
    print("\n🔧 RECOMMENDATIONS:")
    print("1. Values 0 (water) are handled by the water masking script")
    print("2. Values 1-4 are mapped in the z0() function (Urban, Cropland, Grassland, Forest)")
    print("3. Values outside 0-23 range would trigger the fall-through case (_)")
    print("4. The fall-through case treats unknown values as 'Barren/Other' with high dust potential")
    print("5. Consider extending the water masking script to handle other problematic values")
    
    # Check for the dust emission output to see if we have generated problematic emissions
    print("\n🔍 Checking for existing dust emission outputs...")
    flux_files = glob.glob("intermediate/flux_*.tif")
    if flux_files:
        print(f"   Found {len(flux_files)} flux files in intermediate/")
        sample_flux = flux_files[0]
        analyze_raster_values(sample_flux, f"Sample Flux Output: {os.path.basename(sample_flux)}")
    else:
        print("   No flux files found in intermediate/")

if __name__ == "__main__":
    main()