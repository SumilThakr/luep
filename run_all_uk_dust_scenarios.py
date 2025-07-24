#!/usr/bin/env python3
"""
Run dust emissions calculations for all UK scenarios
"""
import subprocess
import os
import shutil
import rasterio
import numpy as np
from datetime import datetime

# List of all UK scenarios
scenarios = [
    'all_econ',
    'all_urban', 
    'extensification_bmps_irrigated',
    'extensification_bmps_rainfed',
    'extensification_current_practices',
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
    print(f"🌍 PROCESSING SCENARIO: {scenario_name}")
    print(f"{'='*60}")
    
    # 1. Setup scenario
    print(f"📋 Setting up scenario: {scenario_name}")
    result = subprocess.run([
        '/Users/sumilthakrar/yes/envs/rasters/bin/python', 
        'setup_uk_scenario.py', 
        scenario_name
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Setup failed for {scenario_name}")
        print(f"Error: {result.stderr}")
        return False
    
    print(f"✅ Setup completed for {scenario_name}")
    
    # 2. Run dust emissions calculation
    print(f"🌪️ Running dust emissions calculation...")
    result = subprocess.run([
        '/Users/sumilthakrar/yes/envs/rasters/bin/python',
        'run_dust_emissions.py'
    ], capture_output=True, text=True, timeout=1800)  # 30 minute timeout
    
    if result.returncode != 0:
        print(f"❌ Dust calculation failed for {scenario_name}")
        print(f"Error: {result.stderr}")
        return False
    
    print(f"✅ Dust calculation completed for {scenario_name}")
    
    # 3. Create output directory
    output_dir = f"outputs/uk_results/{scenario_name}"
    os.makedirs(output_dir, exist_ok=True)
    
    # 4. Copy and analyze results
    if os.path.exists('outputs/dust_sum.tiff'):
        # Copy main output
        shutil.copy('outputs/dust_sum.tiff', f'{output_dir}/dust_emissions.tiff')
        
        # Analyze results
        with rasterio.open('outputs/dust_sum.tiff') as src:
            data = src.read(1)
            
        total_emissions = np.sum(data[data > 0])
        max_emission = np.max(data)
        emitting_pixels = np.sum(data > 0)
        negative_pixels = np.sum(data < 0)
        
        # Create summary
        summary = f"""Dust Emissions Summary - {scenario_name}
================================================================

Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Scenario: {scenario_name}
Land Use Source: ESA-CCI high-resolution data (0.002778° pixels)
Processing Period: Full year 2021 (365 days)

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

FILES GENERATED:
===============
dust_emissions.tiff - Spatial dust emission map (kg/pixel/year)
dust_emissions_summary.txt - This summary file

COMPARISON WITH EXTENSIFICATION_CURRENT_PRACTICES:
================================================
Reference scenario total: 69,760,139,264 kg (69.8 Gg)
Current scenario ratio: {total_emissions/69760139264:.2f}x
"""
        
        # Save summary
        with open(f'{output_dir}/dust_emissions_summary.txt', 'w') as f:
            f.write(summary)
        
        print(f"📊 Results saved to: {output_dir}")
        print(f"   Total emissions: {total_emissions/1e9:.1f} Gg")
        print(f"   Max pixel: {max_emission:,.0f} kg")
        print(f"   Negative pixels: {negative_pixels:,}")
        
        return True
    else:
        print(f"❌ Output file not found for {scenario_name}")
        return False

def main():
    """Run all scenarios"""
    print("🚀 STARTING BATCH PROCESSING OF ALL UK DUST SCENARIOS")
    print(f"Total scenarios to process: {len(scenarios)}")
    
    successful = []
    failed = []
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n🔄 Progress: {i}/{len(scenarios)} scenarios")
        
        try:
            if run_scenario(scenario):
                successful.append(scenario)
                print(f"✅ {scenario} completed successfully")
            else:
                failed.append(scenario)
                print(f"❌ {scenario} failed")
        except Exception as e:
            failed.append(scenario)
            print(f"❌ {scenario} failed with exception: {e}")
    
    # Final summary
    print(f"\n{'='*60}")
    print("🎯 BATCH PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"✅ Successful: {len(successful)}/{len(scenarios)}")
    print(f"❌ Failed: {len(failed)}/{len(scenarios)}")
    
    if successful:
        print(f"\nSuccessful scenarios:")
        for scenario in successful:
            print(f"  ✅ {scenario}")
    
    if failed:
        print(f"\nFailed scenarios:")
        for scenario in failed:
            print(f"  ❌ {scenario}")
    
    print(f"\n📁 All results saved in: outputs/uk_results/")

if __name__ == "__main__":
    main()