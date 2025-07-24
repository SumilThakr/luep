#!/usr/bin/env python3
"""
Run remaining UK dust scenarios in parallel (2 at a time)
"""
import subprocess
import os
import shutil
import rasterio
import numpy as np
from datetime import datetime
import concurrent.futures
import threading

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

# Lock for thread-safe printing
print_lock = threading.Lock()

def safe_print(message):
    """Thread-safe printing"""
    with print_lock:
        print(message)

def run_scenario(scenario_name):
    """Run dust emissions for a single scenario"""
    try:
        safe_print(f"\n🌍 STARTING: {scenario_name}")
        
        # 1. Setup scenario
        safe_print(f"📋 Setting up scenario: {scenario_name}")
        result = subprocess.run([
            '/Users/sumilthakrar/yes/envs/rasters/bin/python', 
            'setup_uk_scenario.py', 
            scenario_name
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            safe_print(f"❌ Setup failed for {scenario_name}: {result.stderr}")
            return False, scenario_name, "Setup failed"
        
        safe_print(f"✅ Setup completed for {scenario_name}")
        
        # 2. Run dust emissions calculation (NO TIMEOUT)
        safe_print(f"🌪️ Running dust emissions calculation for {scenario_name}...")
        result = subprocess.run([
            '/Users/sumilthakrar/yes/envs/rasters/bin/python',
            'run_dust_emissions.py'
        ], capture_output=True, text=True)  # No timeout!
        
        if result.returncode != 0:
            safe_print(f"❌ Dust calculation failed for {scenario_name}: {result.stderr}")
            return False, scenario_name, "Dust calculation failed"
        
        safe_print(f"✅ Dust calculation completed for {scenario_name}")
        
        # 3. Create output directory and save results
        output_dir = f"outputs/uk_results/{scenario_name}"
        os.makedirs(output_dir, exist_ok=True)
        
        if os.path.exists('outputs/dust_sum.tiff'):
            # Copy main output with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            shutil.copy('outputs/dust_sum.tiff', f'{output_dir}/dust_emissions_corrected_{timestamp}.tiff')
            shutil.copy('outputs/dust_sum.tiff', f'{output_dir}/dust_emissions.tiff')  # Also keep standard name
            
            # Quick validation
            with rasterio.open('outputs/dust_sum.tiff') as src:
                data = src.read(1)
                
            total_emissions = np.sum(data[data > 0])
            negative_pixels = np.sum(data < 0)
            
            safe_print(f"📊 {scenario_name} COMPLETED: {total_emissions/1e9:.1f} Gg, {negative_pixels} negative pixels")
            
            return True, scenario_name, f"{total_emissions/1e9:.1f} Gg"
        else:
            safe_print(f"❌ Output file not found for {scenario_name}")
            return False, scenario_name, "No output file"
            
    except Exception as e:
        safe_print(f"❌ Exception in {scenario_name}: {str(e)}")
        return False, scenario_name, f"Exception: {str(e)}"

def main():
    """Run scenarios in parallel (2 at a time)"""
    safe_print("🚀 STARTING PARALLEL PROCESSING OF REMAINING UK DUST SCENARIOS")
    safe_print(f"Scenarios to process: {len(remaining_scenarios)}")
    safe_print("Running 2 scenarios in parallel, NO TIMEOUT")
    
    successful = []
    failed = []
    
    # Process 2 scenarios at a time
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        # Submit all scenarios
        future_to_scenario = {
            executor.submit(run_scenario, scenario): scenario 
            for scenario in remaining_scenarios
        }
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_scenario):
            scenario = future_to_scenario[future]
            try:
                success, scenario_name, message = future.result()
                if success:
                    successful.append((scenario_name, message))
                    safe_print(f"✅ SUCCESS: {scenario_name} - {message}")
                else:
                    failed.append((scenario_name, message))
                    safe_print(f"❌ FAILED: {scenario_name} - {message}")
                    
            except Exception as e:
                failed.append((scenario, f"Future exception: {str(e)}"))
                safe_print(f"❌ FUTURE FAILED: {scenario} - {str(e)}")
    
    # Final summary
    safe_print(f"\n{'='*60}")
    safe_print("🎯 PARALLEL PROCESSING COMPLETE")
    safe_print(f"{'='*60}")
    safe_print(f"✅ Successful: {len(successful)}/{len(remaining_scenarios)}")
    safe_print(f"❌ Failed: {len(failed)}/{len(remaining_scenarios)}")
    
    if successful:
        safe_print(f"\nSuccessful scenarios:")
        for scenario, message in successful:
            safe_print(f"  ✅ {scenario}: {message}")
    
    if failed:
        safe_print(f"\nFailed scenarios:")
        for scenario, message in failed:
            safe_print(f"  ❌ {scenario}: {message}")
    
    safe_print(f"\n📁 All results saved in: outputs/uk_results/")
    safe_print(f"⏱️  Processing complete at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()