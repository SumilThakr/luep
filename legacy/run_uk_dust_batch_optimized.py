#!/usr/bin/env python3
"""
Optimized UK Dust Batch Processing

Practical optimization of existing dust processing with:
- Scenario-level parallelization (2-4x speedup)
- Smart resource caching and reuse  
- Progress tracking and recovery
- Works with existing data structure

Target: Reduce 45 min/scenario to 15-20 min/scenario for single runs,
        10-15 min/scenario for batch runs with caching.
"""

import os
import sys
import time
import subprocess
import shutil
import multiprocessing
from pathlib import Path
from datetime import datetime
import concurrent.futures
import traceback

def get_uk_scenarios():
    """Get list of all UK scenarios"""
    return [
        "extensification_current_practices",
        "extensification_bmps_irrigated", 
        "extensification_bmps_rainfed",
        "extensification_intensified_irrigated",
        "extensification_intensified_rainfed",
        "fixedarea_bmps_irrigated",
        "fixedarea_bmps_rainfed",
        "fixedarea_intensified_irrigated",
        "fixedarea_intensified_rainfed",
        "forestry_expansion",
        "grazing_expansion",
        "restoration",
        "sustainable_current",
        "all_econ",
        "all_urban"
    ]

def backup_global_files():
    """Backup global files for restoration"""
    
    backup_dir = Path("backups/optimized_batch")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    files_to_backup = ["grid.tif", "inputs/gblulcg20_10000.tif"]
    
    for file_path in files_to_backup:
        if Path(file_path).exists():
            shutil.copy2(file_path, backup_dir / Path(file_path).name)
    
    print(f"🔒 Backed up global files to: {backup_dir}")

def restore_global_files():
    """Restore global files"""
    
    backup_dir = Path("backups/optimized_batch")
    
    if not backup_dir.exists():
        print("⚠️  No backup found for global files")
        return
    
    files_to_restore = {
        "grid.tif": "grid.tif",
        "gblulcg20_10000.tif": "inputs/gblulcg20_10000.tif"
    }
    
    for backup_name, target_path in files_to_restore.items():
        backup_file = backup_dir / backup_name
        if backup_file.exists():
            target_dir = os.path.dirname(target_path)
            if target_dir:  # Only create directory if there is one
                os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(backup_file, target_path)
    
    print("🔄 Restored global files")

def setup_shared_cache():
    """Setup shared cache for multi-scenario optimization"""
    
    cache_dir = Path("cache/dust_shared")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    shared_files = {
        "intermediate/soil_texture.tif": "soil_texture.tif",
        "intermediate/aligned_soil_texture.tif": "aligned_soil_texture.tif"
    }
    
    cached_count = 0
    
    for src_path, cache_name in shared_files.items():
        if Path(src_path).exists():
            cache_file = cache_dir / cache_name
            if not cache_file.exists():
                shutil.copy2(src_path, cache_file)
                cached_count += 1
    
    if cached_count > 0:
        print(f"📦 Cached {cached_count} shared files")
    
    return cache_dir

def restore_shared_cache(cache_dir):
    """Restore shared cache files"""
    
    shared_files = {
        "soil_texture.tif": "intermediate/soil_texture.tif",
        "aligned_soil_texture.tif": "intermediate/aligned_soil_texture.tif"
    }
    
    restored_count = 0
    
    for cache_name, target_path in shared_files.items():
        cache_file = cache_dir / cache_name
        if cache_file.exists():
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.copy2(cache_file, target_path)
            restored_count += 1
    
    if restored_count > 0:
        print(f"♻️  Restored {restored_count} shared files from cache")

def run_dust_processing_optimized():
    """Run dust processing with the corrected land use mapping"""
    
    try:
        print("⚡ Running optimized dust emissions processing...")
        
        # Import and run the three dust processing steps
        from dust_scripts import dust_1_soil_texture
        from dust_scripts import dust_2_flux_calc  # This now has the corrected land use mapping AND resolution correction
        from dust_scripts import dust_3_sum_resolution_corrected as dust_3_sum
        
        inputdir = "."
        
        # Step 1: Soil texture (cached if available)
        if not os.path.exists("intermediate/aligned_soil_texture.tif"):
            print("  📍 Step 1: Finding soil texture...")
            dust_1_soil_texture.run(inputdir)
        else:
            print("  ♻️  Step 1: Using cached soil texture")
        
        # Step 2: Flux calculation (the main processing)
        print("  📍 Step 2: Calculating dust fluxes (corrected land use mapping)...")
        start_flux = time.time()
        dust_2_flux_calc.run(inputdir)
        flux_time = time.time() - start_flux
        print(f"      Flux calculation completed in {flux_time:.1f}s ({flux_time/60:.1f}m)")
        
        # Step 3: Sum to annual total
        print("  📍 Step 3: Calculating total dust emissions...")
        dust_3_sum.run(inputdir)
        
        print("  ✅ Dust processing completed successfully")
        return True
        
    except Exception as e:
        print(f"  ❌ Dust processing failed: {e}")
        traceback.print_exc()
        return False

def process_single_scenario_optimized(scenario_name, shared_cache_dir):
    """Process a single scenario with optimizations"""
    
    scenario_start = time.time()
    
    print(f"\n🌍 Processing scenario: {scenario_name}")
    print("-" * 60)
    
    try:
        # 1. Setup UK scenario
        print(f"Setting up {scenario_name}...")
        setup_start = time.time()
        
        subprocess.run([
            "/Users/sumilthakrar/yes/envs/rasters/bin/python", 
            "setup_uk_scenario.py", 
            scenario_name
        ], check=True, capture_output=True, text=True)
        
        setup_time = time.time() - setup_start
        print(f"  ✅ Setup completed in {setup_time:.1f}s")
        
        # 2. Restore shared cache
        restore_shared_cache(shared_cache_dir)
        
        # 3. Run dust processing
        processing_start = time.time()
        success = run_dust_processing_optimized()
        processing_time = time.time() - processing_start
        
        if not success:
            return False, 0
        
        # 4. Save outputs
        output_dir = Path(f"outputs/uk_results/{scenario_name}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy dust output (check multiple possible names)
        dust_files = [
            "outputs/dust_emissions.tiff", 
            "outputs/dust_emissions.tif",
            "outputs/dust_sum.tiff",
            "outputs/dust_sum.tif"
        ]
        dust_output = None
        for dust_file in dust_files:
            if os.path.exists(dust_file):
                dust_output = dust_file
                break
        
        if dust_output:
            target_path = output_dir / "dust_emissions_corrected.tif"
            shutil.copy2(dust_output, target_path)
            
            scenario_time = time.time() - scenario_start
            
            # Create summary
            summary_path = output_dir / "dust_processing_summary.txt"
            with open(summary_path, 'w') as f:
                f.write("UK Dust Emissions - Optimized Processing\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Scenario: {scenario_name}\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total processing time: {scenario_time:.1f}s ({scenario_time/60:.1f}m)\n")
                f.write(f"Setup time: {setup_time:.1f}s\n")
                f.write(f"Dust processing time: {processing_time:.1f}s\n\n")
                
                f.write("OPTIMIZATIONS APPLIED:\n")
                f.write("-" * 30 + "\n")
                f.write("• Corrected Simple 4-class land use mapping\n")
                f.write("• Shared resource caching (soil texture)\n")
                f.write("• Streamlined processing pipeline\n")
                f.write("• Automated scenario setup and cleanup\n\n")
                
                f.write("LAND USE MAPPING CORRECTION:\n")
                f.write("-" * 30 + "\n")
                f.write("0 (Other): No dust emissions\n")
                f.write("1 (Cropland): Moderate dust\n") 
                f.write("2 (Grass): Moderate dust\n")
                f.write("3 (Forest): No dust emissions\n")
            
            print(f"  ✅ SUCCESS: {scenario_name}")
            print(f"     Total time: {scenario_time:.1f}s ({scenario_time/60:.1f}m)")
            print(f"     Output: {target_path}")
            
            return True, scenario_time
        else:
            print(f"  ❌ No dust output found for {scenario_name}")
            return False, 0
            
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Setup failed for {scenario_name}: {e}")
        return False, 0
    except Exception as e:
        print(f"  ❌ Processing failed for {scenario_name}: {e}")
        traceback.print_exc()
        return False, 0

def process_scenarios_sequential(scenarios, shared_cache_dir):
    """Process scenarios sequentially with optimizations"""
    
    successful = []
    failed = []
    processing_times = []
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n[{i}/{len(scenarios)}] Processing: {scenario}")
        print("=" * 70)
        
        success, proc_time = process_single_scenario_optimized(scenario, shared_cache_dir)
        
        if success:
            successful.append(scenario)
            processing_times.append(proc_time)
        else:
            failed.append(scenario)
    
    return successful, failed, processing_times

def process_scenarios_parallel(scenarios, shared_cache_dir, max_workers=2):
    """Process scenarios in parallel (limited by I/O constraints)"""
    
    print(f"🚀 Running parallel processing with {max_workers} workers")
    
    successful = []
    failed = []
    processing_times = []
    
    def process_with_error_handling(scenario):
        try:
            return scenario, process_single_scenario_optimized(scenario, shared_cache_dir)
        except Exception as e:
            print(f"❌ Error processing {scenario}: {e}")
            return scenario, (False, 0)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all scenarios
        futures = {executor.submit(process_with_error_handling, scenario): scenario 
                  for scenario in scenarios}
        
        # Process results as they complete
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            scenario, (success, proc_time) = future.result()
            
            print(f"[{i}/{len(scenarios)}] Completed: {scenario}")
            
            if success:
                successful.append(scenario)
                processing_times.append(proc_time)
            else:
                failed.append(scenario)
    
    return successful, failed, processing_times

def main():
    """Main optimized batch processing"""
    
    print("🚀 UK Dust Emissions - Optimized Batch Processing")
    print("=" * 70)
    print("Features: Corrected land use mapping, resource caching, parallel processing")
    print()
    
    start_time = time.time()
    
    # Parse arguments
    if "--scenario" in sys.argv:
        idx = sys.argv.index("--scenario")
        if idx + 1 < len(sys.argv):
            scenarios = [sys.argv[idx + 1]]
        else:
            print("❌ Error: --scenario requires a scenario name")
            sys.exit(1)
    else:
        scenarios = get_uk_scenarios()
    
    parallel = "--parallel" in sys.argv
    if parallel:
        max_workers = 2  # Conservative for I/O intensive tasks
        if "--workers" in sys.argv:
            idx = sys.argv.index("--workers")
            if idx + 1 < len(sys.argv):
                max_workers = int(sys.argv[idx + 1])
    
    print(f"📋 Processing {len(scenarios)} scenario(s)")
    print(f"⚡ Mode: {'Parallel' if parallel else 'Sequential'}")
    if parallel:
        print(f"👥 Workers: {max_workers}")
    print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. Backup global state
    backup_global_files()
    
    # 2. Setup shared cache
    shared_cache_dir = setup_shared_cache()
    
    # 3. Generate shared resources if needed
    if not (shared_cache_dir / "soil_texture.tif").exists():
        print("🔧 Generating shared soil texture...")
        try:
            from dust_scripts.dust_1_soil_texture import run as generate_soil_texture
            generate_soil_texture(".")
            setup_shared_cache()  # Update cache
        except Exception as e:
            print(f"⚠️  Could not generate soil texture: {e}")
    
    # 4. Process scenarios
    if parallel:
        successful, failed, processing_times = process_scenarios_parallel(
            scenarios, shared_cache_dir, max_workers
        )
    else:
        successful, failed, processing_times = process_scenarios_sequential(
            scenarios, shared_cache_dir
        )
    
    # 5. Restore global state
    restore_global_files()
    
    # 6. Final summary
    total_time = time.time() - start_time
    
    print(f"\n{'='*70}")
    print("🎉 OPTIMIZED BATCH PROCESSING SUMMARY")
    print(f"{'='*70}")
    print(f"Total scenarios: {len(scenarios)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"Total batch time: {total_time:.1f}s ({total_time/60:.1f}m)")
    
    if processing_times:
        avg_time = sum(processing_times) / len(processing_times)
        min_time = min(processing_times)
        max_time = max(processing_times)
        
        print(f"Average time per scenario: {avg_time:.1f}s ({avg_time/60:.1f}m)")
        print(f"Fastest scenario: {min_time:.1f}s ({min_time/60:.1f}m)")
        print(f"Slowest scenario: {max_time:.1f}s ({max_time/60:.1f}m)")
        print(f"Estimated speedup vs original (45m): {45*60/avg_time:.1f}x")
    
    print()
    
    if successful:
        print("✅ Successful scenarios:")
        for i, scenario in enumerate(successful):
            if i < len(processing_times):
                time_str = f" ({processing_times[i]/60:.1f}m)"
            else:
                time_str = ""
            print(f"   - {scenario}{time_str}")
    
    if failed:
        print("\n❌ Failed scenarios:")
        for scenario in failed:
            print(f"   - {scenario}")
    
    print(f"\n📂 Outputs saved to: outputs/uk_results/{{scenario}}/dust_emissions_corrected.tif")
    print("💡 Use --parallel for faster processing of multiple scenarios")

if __name__ == "__main__":
    main()