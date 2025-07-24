#!/usr/bin/env python3
"""
Run bVOC emissions processing for all UK scenarios

This script:
1. Iterates through all 15 UK scenarios
2. Runs bVOC emissions processing for each scenario  
3. Saves organized results with proper naming
4. Creates summary report

Usage:
    python run_all_bvoc_scenarios.py
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
import time
import shutil

# All UK scenarios
UK_SCENARIOS = [
    "all_econ",
    "all_urban", 
    "extensification_bmps_irrigated",
    "extensification_bmps_rainfed",
    "extensification_current_practices",
    "extensification_intensified_irrigated",
    "extensification_intensified_rainfed",
    "fixedarea_bmps_irrigated",
    "fixedarea_bmps_rainfed",
    "fixedarea_intensified_irrigated",
    "fixedarea_intensified_rainfed",
    "forestry_expansion",
    "grazing_expansion",
    "restoration",
    "sustainable_current"
]

def setup_directories():
    """Create organized output directories"""
    
    # Create main results directory
    results_dir = Path("uk_bvoc_results")
    results_dir.mkdir(exist_ok=True)
    
    # Create logs directory
    (results_dir / "logs").mkdir(exist_ok=True)
    
    print(f"📁 Results will be saved to: {results_dir.absolute()}")
    
    return results_dir

def run_scenario_setup(scenario_name):
    """Setup a UK scenario"""
    
    print(f"🌍 Setting up scenario: {scenario_name}")
    
    cmd = ["/Users/sumilthakrar/yes/envs/rasters/bin/python", 
           "setup_uk_scenario.py", scenario_name]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  ❌ Failed to setup {scenario_name}")
        print(f"  Error: {result.stderr}")
        return False
    else:
        print(f"  ✅ Successfully setup {scenario_name}")
        return True

def run_bvoc_processing(scenario_name):
    """Run bVOC emissions processing"""
    
    print(f"  📊 Running bVOC emissions processing...")
    
    cmd = ["/Users/sumilthakrar/yes/envs/rasters/bin/python", "run_bvoc_emissions.py"]
    
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    end_time = time.time()
    
    duration = end_time - start_time
    
    if result.returncode != 0:
        print(f"    ❌ bVOC processing failed ({duration:.1f}s)")
        print(f"    Error: {result.stderr[:300]}...")  # First 300 chars
        return False, duration, None
    else:
        print(f"    ✅ bVOC processing completed ({duration:.1f}s)")
        
        # Parse output for statistics
        stats = parse_bvoc_output(result.stdout)
        return True, duration, stats

def parse_bvoc_output(stdout):
    """Parse bVOC processing output for statistics"""
    
    stats = {}
    lines = stdout.split('\n')
    
    for line in lines:
        if "Total emissions:" in line:
            # Extract total emissions value
            parts = line.split(":")
            if len(parts) > 1:
                stats['total_emissions'] = parts[1].strip()
        elif "Maximum emissions:" in line:
            parts = line.split(":")
            if len(parts) > 1:
                stats['max_emissions'] = parts[1].strip()
        elif "Pixels with emissions:" in line:
            parts = line.split(":")
            if len(parts) > 1:
                stats['pixels_with_emissions'] = parts[1].strip()
    
    return stats

def save_scenario_results(scenario_name, stats):
    """Save results to existing UK results structure"""
    
    # Use existing UK results directory structure
    scenario_dir = Path("outputs/uk_results") / scenario_name
    scenario_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy and rename bVOC output files to overwrite existing ones
    outputs_path = Path("outputs")
    saved_files = []
    
    if outputs_path.exists():
        # Map output files to standard names
        file_mapping = {
            "bvoc_emissions.nc": "bvoc_emissions.nc",
            "bvoc_emissions.tif": "bvoc_emissions.tif"
        }
        
        for output_file, target_name in file_mapping.items():
            source_path = outputs_path / output_file
            if source_path.exists():
                target_path = scenario_dir / target_name
                # Overwrite existing file
                shutil.copy2(source_path, target_path)
                saved_files.append(target_name)
                print(f"      Saved: {target_name} (overwriting existing)")
    
    # Save scenario statistics
    stats_file = scenario_dir / "bvoc_stats.txt"
    with open(stats_file, 'w') as f:
        f.write(f"bVOC Emissions Statistics - {scenario_name}\n")
        f.write("=" * 50 + "\n")
        f.write(f"Processing completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("Units: kg yr⁻¹ (total emissions per pixel)\n")
        f.write("Note: Updated from kg m⁻² yr⁻¹ using latitude-corrected pixel area\n\n")
        
        for key, value in stats.items():
            f.write(f"{key}: {value}\n")
        
        f.write(f"\nOutput files:\n")
        for filename in saved_files:
            f.write(f"  {filename}\n")
    
    return len(saved_files)

def create_summary_report(results_dir, processing_log, scenario_stats):
    """Create comprehensive summary report"""
    
    print(f"\n📋 Creating summary report...")
    
    report_path = results_dir / "bvoc_processing_summary.md"
    
    with open(report_path, 'w') as f:
        f.write("# UK Land Use Scenarios - bVOC Emissions Processing Results\n\n")
        f.write(f"**Processing completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**Total scenarios processed:** {len(UK_SCENARIOS)}  \n\n")
        
        # Summary statistics
        successful_scenarios = sum(1 for entry in processing_log if "SUCCESS" in entry)
        f.write(f"## Processing Summary\n\n")
        f.write(f"- ✅ **Successful scenarios:** {successful_scenarios}/{len(UK_SCENARIOS)}\n")
        f.write(f"- 📊 **High-resolution outputs:** 308m pixel size\n")
        f.write(f"- 📁 **Output format:** GeoTIFF + NetCDF\n\n")
        
        # Individual scenario results
        f.write(f"## Scenario Results\n\n")
        f.write("| Scenario | Status | Duration | Total Emissions | Files |\n")
        f.write("|----------|--------|----------|-----------------|-------|\n")
        
        for entry in processing_log:
            if "SCENARIO:" in entry:
                scenario = entry.split(":")[1].strip()
                continue
            elif "SUCCESS" in entry or "FAILED" in entry:
                parts = entry.split()
                status = "✅" if "SUCCESS" in entry else "❌"
                duration = parts[-1].replace("(", "").replace(")", "")
                
                # Get stats if available
                stats = scenario_stats.get(scenario, {})
                total_emissions = stats.get('total_emissions', 'N/A')
                files = "2" if status == "✅" else "0"
                
                f.write(f"| {scenario} | {status} | {duration} | {total_emissions} | {files} |\n")
        
        f.write(f"\n## File Structure\n\n")
        f.write("```\n")
        f.write("uk_bvoc_results/\n")
        for scenario in UK_SCENARIOS:
            f.write(f"  {scenario}/\n")
            f.write(f"    {scenario}_bvoc_emissions.tif      # High-res GeoTIFF\n")
            f.write(f"    {scenario}_bvoc_emissions.nc       # NetCDF format\n")
            f.write(f"    {scenario}_bvoc_stats.txt          # Processing stats\n")
        f.write("```\n\n")
        
        f.write(f"## Processing Details\n\n")
        for entry in processing_log:
            f.write(f"- {entry}\n")
    
    print(f"📄 Summary report saved: {report_path}")

def main():
    """Main processing loop"""
    
    print("🇬🇧 UK LAND USE SCENARIOS - bVOC EMISSIONS PROCESSING")
    print("=" * 65)
    print(f"Processing {len(UK_SCENARIOS)} scenarios")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Use existing UK results directory
    results_dir = Path("outputs/uk_results")
    results_dir.mkdir(parents=True, exist_ok=True)
    processing_log = []
    scenario_stats = {}
    
    print(f"📁 Using existing UK results directory: {results_dir.absolute()}")
    
    # Track overall progress
    start_time = time.time()
    successful_scenarios = 0
    
    # Process each scenario
    for i, scenario in enumerate(UK_SCENARIOS, 1):
        
        print(f"\n{'='*65}")
        print(f"SCENARIO {i}/{len(UK_SCENARIOS)}: {scenario}")
        print(f"{'='*65}")
        
        scenario_start = time.time()
        
        # Setup scenario
        if not run_scenario_setup(scenario):
            processing_log.append(f"SCENARIO: {scenario}")
            processing_log.append(f"  FAILED SETUP")
            processing_log.append("")
            continue
        
        # Run bVOC processing
        success, duration, stats = run_bvoc_processing(scenario)
        
        if success:
            # Save results
            num_files = save_scenario_results(scenario, stats)
            successful_scenarios += 1
            scenario_stats[scenario] = stats
            
            # Log success
            processing_log.append(f"SCENARIO: {scenario}")
            processing_log.append(f"  SUCCESS ({duration:.1f}s) - {num_files} files saved")
            processing_log.append("")
            
            print(f"  📁 Results saved to: outputs/uk_results/{scenario}")
            
        else:
            # Log failure
            processing_log.append(f"SCENARIO: {scenario}")
            processing_log.append(f"  FAILED ({duration:.1f}s)")
            processing_log.append("")
        
        # Progress update
        scenario_duration = time.time() - scenario_start
        elapsed = time.time() - start_time
        remaining_scenarios = len(UK_SCENARIOS) - i
        avg_time = elapsed / i
        eta = avg_time * remaining_scenarios
        
        print(f"\n  📊 Progress: {i}/{len(UK_SCENARIOS)} scenarios ({i/len(UK_SCENARIOS)*100:.1f}%)")
        print(f"  ⏱️  ETA: {eta/60:.1f} minutes remaining")
    
    # Final summary
    total_duration = time.time() - start_time
    
    print(f"\n🎉 ALL bVOC PROCESSING COMPLETED!")
    print(f"📊 Success rate: {successful_scenarios}/{len(UK_SCENARIOS)} scenarios ({successful_scenarios/len(UK_SCENARIOS)*100:.1f}%)")
    print(f"⏱️  Total duration: {total_duration/60:.1f} minutes")
    print(f"📁 Results saved in: {results_dir.absolute()}")
    
    # Create comprehensive report
    processing_log.append(f"TOTAL PROCESSING TIME: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    processing_log.append(f"SUCCESS RATE: {successful_scenarios}/{len(UK_SCENARIOS)} scenarios")
    create_summary_report(results_dir, processing_log, scenario_stats)
    
    # Restore global setup
    print(f"\n🔄 Restoring global setup...")
    try:
        subprocess.run(["/Users/sumilthakrar/yes/envs/rasters/bin/python", 
                       "restore_global_setup.py"], check=True)
        print(f"✅ Global setup restored")
    except subprocess.CalledProcessError:
        print(f"⚠️  Failed to restore global setup")
    
    print(f"\n🌿 bVOC processing complete! Check {results_dir}/bvoc_processing_summary.md for full results.")

if __name__ == "__main__":
    main()