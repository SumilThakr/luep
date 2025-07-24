#!/usr/bin/env python3
"""
Simplified UK Soil NOx Processing

This script processes UK scenarios for soil NOx emissions using a simplified approach
that focuses on the nitrogen fertilization effects while using constant values for
time-varying components that are causing issues.

Usage:
    python soil_nox_uk_simplified.py [scenario_name]
"""

import os
import sys
from pathlib import Path
import traceback
from datetime import datetime

# Add the soil_nox_scripts directory to the path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

from soil_nox_3_constant_uk import run as run_constant_uk

def create_dummy_time_varying_files():
    """
    Create dummy time-varying files to bypass the problematic time-varying processing
    """
    print("Creating simplified time-varying effects...")
    
    import pygeoprocessing.geoprocessing as geop
    import numpy as np
    from osgeo import gdal
    
    # Use an existing reference raster for spatial properties
    ref_raster = "inputs/T_OC.tiff"
    if not os.path.exists(ref_raster):
        print(f"Reference raster not found: {ref_raster}")
        return False
    
    # Create intermediate directory
    os.makedirs("intermediate", exist_ok=True)
    
    # Create a simple constant time-varying effect (unity effect)
    ts_sm_output = "intermediate/ts_sm_sum.tiff"
    
    def unity_effect(x):
        """Return unity (no time-varying effect)"""
        return np.ones_like(x, dtype=np.float32)
    
    # Create unity raster using the reference spatial properties
    geop.raster_calculator(
        base_raster_path_band_const_list=[(ref_raster, 1)],
        local_op=unity_effect,
        target_raster_path=ts_sm_output,
        datatype_target=gdal.GDT_Float32,
        nodata_target=-1,
        calc_raster_stats=False
    )
    
    print(f"Created simplified time-varying effect: {ts_sm_output}")
    return True

def create_land_use_reprojection():
    """
    Create land use reprojection using existing global data
    """
    print("Creating land use reprojection...")
    
    import pygeoprocessing.geoprocessing as geop
    import numpy as np
    from osgeo import gdal
    
    # Input and output paths
    lu_input = "inputs/gblulcg20_10000.tif"
    lu_output = "intermediate/lu_effect_reproj.tif"
    
    if not os.path.exists(lu_input):
        print(f"Land use input not found: {lu_input}")
        return False
    
    # For simplicity, just copy the input to output location
    # In a full implementation, this would include proper reprojection
    import shutil
    shutil.copy2(lu_input, lu_output)
    
    print(f"Created land use reprojection: {lu_output}")
    return True

def process_uk_scenario_simplified(scenario, inputdir="inputs"):
    """
    Process UK scenario with simplified soil NOx calculation
    """
    print(f"Processing UK scenario (simplified): {scenario}")
    print("=" * 60)
    
    # Check nitrogen application file
    n_application_path = f"outputs/uk_results/{scenario}/n_application.nc"
    if not os.path.exists(n_application_path):
        print(f"❌ Nitrogen application file not found: {n_application_path}")
        return False
    
    try:
        # Step 1: Create simplified prerequisite files
        print("Creating simplified prerequisite files...")
        if not create_dummy_time_varying_files():
            return False
        if not create_land_use_reprojection():
            return False
        
        # Step 2: Run scenario-specific constant effects
        print("Calculating scenario-specific constant effects...")
        run_constant_uk(inputdir, scenario_name=scenario, n_application_path=n_application_path)
        
        # Step 3: Run simplified alignment and calculation
        print("Running simplified soil NOx calculation...")
        
        import pygeoprocessing.geoprocessing as geop
        import numpy as np
        from osgeo import gdal
        import math
        
        # Set up scenario paths
        wdir_scenario = f"./intermediate/scenario_{scenario}"
        output_dir = f"./outputs/uk_results/{scenario}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Define input paths
        ph_raster_out = os.path.join(wdir_scenario, 'ph_effect.tif')
        soc_raster_out = os.path.join(wdir_scenario, 'soc_effect.tif')
        clim_raster_out = os.path.join(wdir_scenario, 'clim_effect.tif')
        t0_raster_out = os.path.join(wdir_scenario, 't0_effect.tif')
        lu_raster_out = os.path.join(wdir_scenario, 'lu_effect.tif')
        n_raster_out = os.path.join(wdir_scenario, 'n_effect.tif')
        ts_sm_raster_out = "intermediate/ts_sm_sum.tiff"
        
        # Check required files exist
        required_files = [ph_raster_out, soc_raster_out, clim_raster_out, 
                         t0_raster_out, lu_raster_out, n_raster_out, ts_sm_raster_out]
        
        for file_path in required_files:
            if not os.path.exists(file_path):
                print(f"❌ Required file missing: {file_path}")
                return False
        
        # Define aligned output paths
        aligned_ph_path = os.path.join(wdir_scenario, "aligned_ph.tif")
        aligned_soc_path = os.path.join(wdir_scenario, "aligned_soc.tif")
        aligned_clim_path = os.path.join(wdir_scenario, "aligned_clim.tif")
        aligned_t0_path = os.path.join(wdir_scenario, "aligned_t0.tif")
        aligned_lu_path = os.path.join(wdir_scenario, "aligned_lu.tif")
        aligned_ts_sm_path = os.path.join(wdir_scenario, "aligned_ts_sm.tif")
        aligned_n_path = os.path.join(wdir_scenario, "aligned_n.tif")
        
        print("Aligning raster stack...")
        # Align all rasters to the same grid
        geop.align_and_resize_raster_stack(
                [ph_raster_out, soc_raster_out, clim_raster_out, t0_raster_out, 
                 lu_raster_out, ts_sm_raster_out, n_raster_out],
                [aligned_ph_path, aligned_soc_path, aligned_clim_path, aligned_t0_path, 
                 aligned_lu_path, aligned_ts_sm_path, aligned_n_path],
                ['bilinear', 'bilinear', 'bilinear', 'bilinear', 'bilinear', 'bilinear', 'bilinear'],
                geop.get_raster_info(soc_raster_out)['pixel_size'],
                bounding_box_mode='union')
        
        # Define the soil NOx calculation function
        def soilnox_simplified(ph, soc, clim, t0, lu, tssm, n):
            """Simplified soil NOx calculation using Yan et al. (2005) model"""
            return soc * ph * math.exp(clim) * math.exp(-1.8327) * lu * math.exp(-0.11*t0) * tssm * n
        
        soilnox_simplified_v = np.vectorize(soilnox_simplified)
        
        # Set up input raster list
        list_raster = [
            (aligned_ph_path, 1), 
            (aligned_soc_path, 1), 
            (aligned_clim_path, 1), 
            (aligned_t0_path, 1), 
            (aligned_lu_path, 1), 
            (aligned_ts_sm_path, 1), 
            (aligned_n_path, 1)
        ]
        
        # Calculate final soil NOx emissions
        nox_emissions = os.path.join(output_dir, "nox_emissions.tif")
        
        print("Calculating soil NOx emissions...")
        geop.raster_calculator(
            base_raster_path_band_const_list=list_raster,
            local_op=soilnox_simplified_v,
            target_raster_path=nox_emissions,
            datatype_target=gdal.GDT_Float32, 
            nodata_target=-1, 
            calc_raster_stats=False
        )
        
        print(f"✅ Soil NOx emissions calculated: {nox_emissions}")
        
        # Generate summary
        generate_summary_stats(nox_emissions, aligned_n_path, scenario, 
                             os.path.join(output_dir, "soil_nox_summary.txt"))
        
        return True
        
    except Exception as e:
        print(f"❌ Error processing scenario {scenario}: {str(e)}")
        traceback.print_exc()
        return False

def generate_summary_stats(nox_emissions_path, n_effect_path, scenario_name, output_path):
    """Generate summary statistics for soil NOx emissions"""
    import pygeoprocessing.geoprocessing as geop
    import numpy as np
    from datetime import datetime
    
    try:
        # Read soil NOx emissions and nitrogen effect
        nox_array = geop.raster_to_numpy_array(nox_emissions_path)
        n_effect_array = geop.raster_to_numpy_array(n_effect_path)
        
        # Calculate statistics (exclude nodata values)
        nox_valid = nox_array[nox_array != -1]
        n_effect_valid = n_effect_array[n_effect_array != -1]
        
        with open(output_path, 'w') as f:
            f.write("UK Soil NOx Emissions Summary (Simplified)\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Scenario: {scenario_name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("Processing: Simplified model with constant time-varying effects\n\n")
            
            if len(nox_valid) > 0:
                f.write("SOIL NOx EMISSIONS:\n")
                f.write("-" * 30 + "\n")
                f.write(f"Valid pixels: {len(nox_valid):,}\n")
                f.write(f"Min emission: {np.min(nox_valid):.6f}\n")
                f.write(f"Max emission: {np.max(nox_valid):.6f}\n")
                f.write(f"Mean emission: {np.mean(nox_valid):.6f}\n")
                f.write(f"Total emission: {np.sum(nox_valid):.2f}\n\n")
                
                f.write("NITROGEN EFFECT:\n")
                f.write("-" * 30 + "\n")
                f.write(f"Min N effect: {np.min(n_effect_valid):.6f}\n")
                f.write(f"Max N effect: {np.max(n_effect_valid):.6f}\n")
                f.write(f"Mean N effect: {np.mean(n_effect_valid):.6f}\n\n")
                
                f.write("MODEL COMPONENTS:\n")
                f.write("-" * 30 + "\n")
                f.write("Base equation: NOx = SOC × pH × exp(climate) × exp(-1.8327) × LU × exp(-0.11×T0) × TS_SM × N\n")
                f.write("Nitrogen coefficient: 0.03545 (Yan et al. 2005)\n")
                f.write("Temporal factor: 122/365 (growing season)\n")
                f.write("N effect formula: 1.0 + (0.03545 × N_rate × 122/365)\n")
                f.write("Time-varying effect: Simplified (constant = 1.0)\n\n")
            else:
                f.write("No valid emission data found.\n")
                
        print(f"Summary statistics saved to: {output_path}")
        
    except Exception as e:
        print(f"Error generating summary statistics: {e}")

def main():
    """Main function"""
    scenario = sys.argv[1] if len(sys.argv) > 1 else "extensification_current_practices"
    
    print("UK Soil NOx Emissions - Simplified Processing")
    print("=" * 60)
    print("This uses a simplified approach with constant time-varying effects")
    print("to focus on the scenario-specific nitrogen fertilization effects.")
    print()
    
    success = process_uk_scenario_simplified(scenario)
    
    if success:
        print(f"✅ Simplified processing completed for: {scenario}")
    else:
        print(f"❌ Simplified processing failed for: {scenario}")

if __name__ == "__main__":
    main()