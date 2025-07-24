#!/usr/bin/env python3
"""
Run remaining UK dust scenarios SEQUENTIALLY to avoid intermediate file conflicts
"""
import subprocess
import os
import shutil
import rasterio
import numpy as np
from datetime import datetime

# Scenarios that need to be rerun with corrected code
remaining_scenarios = [
    'extensification_bmps_irrigated',
    'extensification_bmps_rainfed', 
    'extensification_intensified_irrigated',
    'extensification_intensified_rainfed',
    'fixedarea_bmps_irrigated',
    'fixedarea_bmps_rainfed',
    'fixedarea_intensified_irrigated',
    'fixedarea_intensified_rainfed',
    'forestry_expansion',
    'grazing_expansion',
    'restoration',
    'sustainable_current'
]

def run_scenario(scenario_name):
    """Run dust emissions for a single scenario"""
    print(f"\n{'='*60}")
    print(f"🌍 PROCESSING SCENARIO {scenario_name}")
    print(f"{'='*60}")
    print(f"⏰ Started at: {datetime.now().strftime('%H:%M:%S')}")
    
    try:
        # 1. Setup scenario
        print(f"📋 Setting up scenario: {scenario_name}")
        result = subprocess.run([
            '/Users/sumilthakrar/yes/envs/rasters/bin/python', 
            'setup_uk_scenario.py', 
            scenario_name
        ], capture_output=False, text=True)  # Show output directly
        
        if result.returncode != 0:
            print(f"❌ Setup failed for {scenario_name}")
            return False, f"Setup failed: {result.returncode}"
        
        print(f"✅ Setup completed for {scenario_name}")
        
        # 2. Run dust emissions calculation
        print(f"🌪️ Running dust emissions calculation...")
        print(f"⚠️  This will take ~20 minutes...")
        result = subprocess.run([
            '/Users/sumilthakrar/yes/envs/rasters/bin/python',
            'run_dust_emissions.py'
        ], capture_output=False, text=True)  # Show output directly
        
        if result.returncode != 0:
            print(f"❌ Dust calculation failed for {scenario_name}")
            return False, f"Dust calculation failed: {result.returncode}"
        
        print(f"✅ Dust calculation completed for {scenario_name}")
        
        # 3. Create output directory and save results
        output_dir = f"outputs/uk_results/{scenario_name}"
        os.makedirs(output_dir, exist_ok=True)
        
        if os.path.exists('outputs/dust_sum.tiff'):
            # Copy main output with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            shutil.copy('outputs/dust_sum.tiff', f'{output_dir}/dust_emissions_corrected_{timestamp}.tiff')
            shutil.copy('outputs/dust_sum.tiff', f'{output_dir}/dust_emissions.tiff')
            
            # Analyze results
            with rasterio.open('outputs/dust_sum.tiff') as src:
                data = src.read(1)
                
            total_emissions = np.sum(data[data > 0])
            max_emission = np.max(data)
            negative_pixels = np.sum(data < 0)
            emitting_pixels = np.sum(data > 0)
            
            # Create summary
            summary = f"""Dust Emissions Summary - {scenario_name}
================================================================

Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Scenario: {scenario_name}
Land Use Source: ESA-CCI high-resolution data (0.002778° pixels)
Processing Period: Full year 2021 (365 days)
Resolution Correction: APPLIED ✅

EMISSION RESULTS:
================
Total Dust Emissions: {total_emissions:,.0f} kg
Total Dust Emissions: {total_emissions/1e9:.3f} Gg
Max Pixel Emission: {max_emission:,.0f} kg
Emitting Pixels: {emitting_pixels:,}
Negative Values: {negative_pixels:,} (should be 0)

VALIDATION:
==========
Negative values: {'✅ PASS' if negative_pixels == 0 else '❌ FAIL'}
Max pixel reasonable: {'✅ PASS' if max_emission < 1e7 else '❌ FAIL'} 
Total in expected range: {'✅ PASS' if 1e7 < total_emissions < 1e12 else '❌ FAIL'}

COMPARISON:
==========
Reference (extensification_current_practices): 69.8 Gg
Current scenario ratio: {total_emissions/69760139264:.2f}x

FILES GENERATED:
===============
dust_emissions.tiff - Spatial dust emission map (kg/pixel/year)
dust_emissions_corrected_{timestamp}.tiff - Timestamped backup
dust_emissions_summary.txt - This summary file
"""
            
            # Save summary
            with open(f'{output_dir}/dust_emissions_summary.txt', 'w') as f:
                f.write(summary)
            
            print(f"📊 RESULTS for {scenario_name}:")
            print(f"   Total emissions: {total_emissions/1e9:.1f} Gg")
            print(f"   Max pixel: {max_emission:,.0f} kg")
            print(f"   Negative pixels: {negative_pixels:,}")
            print(f"   Status: {'✅ PASS' if negative_pixels == 0 else '❌ FAIL'}")
            print(f"⏰ Completed at: {datetime.now().strftime('%H:%M:%S')}")
            
            return True, f"{total_emissions/1e9:.1f} Gg"
        else:
            print(f"❌ Output file not found for {scenario_name}")
            return False, "No output file"
            
    except Exception as e:
        print(f"❌ Exception in {scenario_name}: {str(e)}")
        return False, f"Exception: {str(e)}"

def main():
    """Run all remaining scenarios sequentially"""
    print("🚀 STARTING SEQUENTIAL PROCESSING OF REMAINING UK DUST SCENARIOS")
    print(f"📊 Scenarios to process: {len(remaining_scenarios)}")
    print(f"⏱️  Estimated time: {len(remaining_scenarios) * 20} minutes (~{len(remaining_scenarios) * 20 / 60:.1f} hours)")
    print("⚠️  Running SEQUENTIALLY to avoid intermediate file conflicts")
    
    successful = []
    failed = []
    start_time = datetime.now()
    
    for i, scenario in enumerate(remaining_scenarios, 1):
        print(f"\n🔄 Progress: {i}/{len(remaining_scenarios)} scenarios")
        elapsed = datetime.now() - start_time
        print(f"⏱️  Elapsed time: {elapsed}")
        
        success, message = run_scenario(scenario)
        if success:
            successful.append((scenario, message))
        else:
            failed.append((scenario, message))
    
    # Final summary
    total_time = datetime.now() - start_time
    print(f"\n{'='*60}")
    print("🎯 SEQUENTIAL PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"⏱️  Total processing time: {total_time}")
    print(f"✅ Successful: {len(successful)}/{len(remaining_scenarios)}")
    print(f"❌ Failed: {len(failed)}/{len(remaining_scenarios)}")
    
    if successful:
        print(f"\nSuccessful scenarios:")
        for scenario, message in successful:
            print(f"  ✅ {scenario}: {message}")
    
    if failed:
        print(f"\nFailed scenarios:")
        for scenario, message in failed:
            print(f"  ❌ {scenario}: {message}")
    
    print(f"\n📁 All results saved in: outputs/uk_results/")

if __name__ == "__main__":
    main()