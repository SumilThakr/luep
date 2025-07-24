def run(inputdir, scenario_name=None):
    """
    Modified soil_nox_5_align.py for UK scenarios
    
    Args:
        inputdir: Base input directory path
        scenario_name: UK scenario name (e.g., 'extensification_current_practices')
    """
    import pygeoprocessing.geoprocessing as geop
    import numpy as np
    import os
    from osgeo import gdal
    import math

    # Set up working and output directories based on scenario
    if scenario_name:
        wdir_scenario = f"./intermediate/scenario_{scenario_name}"
        output_dir = f"./outputs/uk_results/{scenario_name}"
        os.makedirs(output_dir, exist_ok=True)
        print(f"Aligning and calculating soil NOx for UK scenario: {scenario_name}")
        print(f"Using scenario data from: {wdir_scenario}")
        print(f"Output directory: {output_dir}")
    else:
        wdir_scenario = "./intermediate"
        output_dir = "./outputs"
        print("Processing global soil NOx data")

    wdir = "./"

    # Define input paths - use scenario-specific intermediate files where available
    ph_raster_out = os.path.join(wdir_scenario, 'ph_effect.tif')
    lu_raster_out = os.path.join(wdir_scenario, 'lu_effect_reproj.tif')
    soc_raster_out = os.path.join(wdir_scenario, 'soc_effect.tif')
    clim_raster_out = os.path.join(wdir_scenario, 'clim_effect.tif')
    t0_raster_out = os.path.join(wdir_scenario, 't0_effect.tif')
    n_raster_out = os.path.join(wdir_scenario, 'n_effect.tif')  # Scenario-specific N effect
    
    # Time-varying temperature/soil moisture effects (shared across scenarios)
    ts_sm_raster_out = os.path.join(wdir, 'intermediate', 'ts_sm_sum.tiff')

    # Check that required files exist
    required_files = [ph_raster_out, soc_raster_out, clim_raster_out, t0_raster_out, n_raster_out]
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"Warning: Required file not found: {file_path}")
            if scenario_name:
                # Fall back to global intermediate files for missing scenario files
                fallback_path = file_path.replace(f'scenario_{scenario_name}/', '')
                if os.path.exists(fallback_path):
                    print(f"  Using fallback: {fallback_path}")
                    # Update the path
                    if 'ph_effect' in file_path:
                        ph_raster_out = fallback_path
                    elif 'soc_effect' in file_path:
                        soc_raster_out = fallback_path
                    elif 'clim_effect' in file_path:
                        clim_raster_out = fallback_path
                    elif 't0_effect' in file_path:
                        t0_raster_out = fallback_path
                    # N effect must be scenario-specific!
                else:
                    raise FileNotFoundError(f"Required file not found: {file_path}")

    # Special handling for land use reprojection (use global data)
    lu_raster_out_global = os.path.join(wdir, 'intermediate', 'lu_effect_reproj.tif')
    if os.path.exists(lu_raster_out_global):
        lu_raster_out = lu_raster_out_global
    elif not os.path.exists(lu_raster_out):
        # Need to create lu_effect_reproj.tif from global data
        print("Land use reprojection file not found, using global land use data")
        lu_raster_out = os.path.join(wdir, 'intermediate', 'lu_effect_reproj.tif')

    # Define aligned output paths
    aligned_ph_path = os.path.join(wdir_scenario, "aligned_ph.tif")
    aligned_lu_path = os.path.join(wdir_scenario, "aligned_lu.tif")
    aligned_soc_path = os.path.join(wdir_scenario, "aligned_soc.tif")
    aligned_clim_path = os.path.join(wdir_scenario, "aligned_clim.tif")
    aligned_t0_path = os.path.join(wdir_scenario, "aligned_t0.tif")
    aligned_ts_sm_path = os.path.join(wdir_scenario, "aligned_ts_sm.tif")
    aligned_n_path = os.path.join(wdir_scenario, "aligned_n.tif")

    print("Aligning raster stack...")
    print(f"Reference raster: {soc_raster_out}")

    # Align all rasters to the same grid
    geop.align_and_resize_raster_stack(
            [ph_raster_out, soc_raster_out, clim_raster_out, t0_raster_out, 
             lu_raster_out, ts_sm_raster_out, n_raster_out],
            [aligned_ph_path, aligned_soc_path, aligned_clim_path, aligned_t0_path, 
             aligned_lu_path, aligned_ts_sm_path, aligned_n_path],
            ['bilinear', 'bilinear', 'bilinear', 'bilinear', 'bilinear', 'bilinear', 'bilinear'],
            geop.get_raster_info(soc_raster_out)['pixel_size'],
            bounding_box_mode='union')

    print("Raster alignment completed.")

    # Define the soil NOx calculation function (Yan et al. 2005 model)
    def soilnox_fixed_params(ph, soc, clim, t0, lu, tssm, n):
        """
        Soil NOx emissions calculation using Yan et al. (2005) model
        
        Args:
            ph: Soil pH effect
            soc: Soil organic carbon effect  
            clim: Climate effect
            t0: Temperature offset effect
            lu: Land use effect
            tssm: Temperature/soil moisture time-series effect
            n: Nitrogen fertilization effect (scenario-specific)
            
        Returns:
            Soil NOx emissions
        """
        return soc * ph * math.exp(clim) * math.exp(-1.8327) * lu * math.exp(-0.11*t0) * tssm * n

    soilnox_fixed_params_v = np.vectorize(soilnox_fixed_params)

    # Set up input raster list for final calculation
    list_raster = [
        (aligned_ph_path, 1), 
        (aligned_soc_path, 1), 
        (aligned_clim_path, 1), 
        (aligned_t0_path, 1), 
        (aligned_lu_path, 1), 
        (aligned_ts_sm_path, 1), 
        (aligned_n_path, 1)  # Scenario-specific nitrogen effect
    ]

    # Define output path
    if scenario_name:
        nox_emissions = os.path.join(output_dir, "nox_emissions.tif")
    else:
        nox_emissions = os.path.join(output_dir, "nox_emissions.tif")

    print("Calculating soil NOx emissions...")
    print(f"Output file: {nox_emissions}")

    # Calculate final soil NOx emissions
    geop.raster_calculator(
        base_raster_path_band_const_list=list_raster,
        local_op=soilnox_fixed_params_v,
        target_raster_path=nox_emissions,
        datatype_target=gdal.GDT_Float32, 
        nodata_target=-1, 
        calc_raster_stats=False
    )

    print(f"Soil NOx emissions calculation completed!")
    print(f"Results saved to: {nox_emissions}")
    
    # Generate summary statistics
    if scenario_name:
        summary_path = os.path.join(output_dir, "soil_nox_summary.txt")
        generate_summary_stats(nox_emissions, aligned_n_path, scenario_name, summary_path)
    
    return nox_emissions

def generate_summary_stats(nox_emissions_path, n_effect_path, scenario_name, output_path):
    """
    Generate summary statistics for soil NOx emissions
    """
    import numpy as np
    from datetime import datetime
    
    print(f"Generating summary statistics...")
    
    try:
        # Read soil NOx emissions
        nox_array = geop.raster_to_numpy_array(nox_emissions_path)
        n_effect_array = geop.raster_to_numpy_array(n_effect_path)
        
        # Calculate statistics (exclude nodata values)
        nox_valid = nox_array[nox_array != -1]
        n_effect_valid = n_effect_array[n_effect_array != -1]
        
        with open(output_path, 'w') as f:
            f.write("UK Soil NOx Emissions Summary\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Scenario: {scenario_name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
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
                f.write(f"N effect formula: 1.0 + (0.03545 × N_rate × 122/365)\n\n")
            else:
                f.write("No valid emission data found.\n")
                
        print(f"Summary statistics saved to: {output_path}")
        
    except Exception as e:
        print(f"Error generating summary statistics: {e}")