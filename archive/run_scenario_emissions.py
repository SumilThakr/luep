#!/usr/bin/env python3
"""
UK Scenario Emissions Processor

Process UK land use scenarios through all emission models:
- Dust emissions
- Soil NOx emissions  
- Deposition calculations
- BVOC emissions (if implemented)

This script handles:
1. Scenario preprocessing (ESA CCI → Simple classification)
2. Batch processing of multiple scenarios
3. Running all emission modules for each scenario
4. Organizing outputs by scenario
"""

import os
import sys
import time
from pathlib import Path
import multiprocessing as mp
from datetime import datetime
import logging

# Import emission modules
from dep_scripts import dep_1_lai_reclass, dep_2_lai_month_avg, dep_3_velocity, dep_4_multiply
from dust_scripts import dust_1_soil_texture, dust_2_flux_calc, dust_3_sum
from soil_nox_scripts import (soil_nox_1_time_varying, soil_nox_2_time_varying_sum, 
                             soil_nox_3_constant, soil_nox_4_gblulc, soil_nox_5_align)

# Import scenario processing utilities
from scenario_scripts.uk_scenario_preprocessor import preprocess_uk_scenario, batch_preprocess_scenarios
from scenario_scripts.esa_to_simple_converter import convert_esa_to_simple

# Configuration
SCENARIOS_DIR = "scenarios/UKNatureFrontierWithAir/United Kingdom/ScenarioMaps"
OUTPUTS_DIR = "outputs/scenarios"
INTERMEDIATE_DIR = "intermediate/scenarios"
INPUTDIR = "inputs"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scenario_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ScenarioEmissionsProcessor:
    """Main class for processing UK scenarios through emissions models"""
    
    def __init__(self, scenarios_dir=SCENARIOS_DIR, outputs_dir=OUTPUTS_DIR, 
                 intermediate_dir=INTERMEDIATE_DIR, inputdir=INPUTDIR):
        self.scenarios_dir = Path(scenarios_dir)
        self.outputs_dir = Path(outputs_dir)
        self.intermediate_dir = Path(intermediate_dir)
        self.inputdir = inputdir
        
        # Create directories
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.intermediate_dir.mkdir(parents=True, exist_ok=True)
        
        # Find scenarios
        self.scenario_files = list(self.scenarios_dir.glob("*.tif"))
        logger.info(f"Found {len(self.scenario_files)} scenario files")
        
        if not self.scenario_files:
            raise ValueError(f"No scenario files found in {self.scenarios_dir}")
    
    def preprocess_scenario(self, scenario_path):
        """
        Preprocess a single scenario for emissions processing
        
        Args:
            scenario_path: Path to scenario TIFF file
            
        Returns:
            dict: Paths to preprocessed files
        """
        scenario_name = scenario_path.stem
        scenario_output_dir = self.intermediate_dir / scenario_name
        
        logger.info(f"Preprocessing scenario: {scenario_name}")
        
        try:
            # Use baseline LULC if available
            baseline_lulc = self.find_baseline_lulc()
            
            result = preprocess_uk_scenario(
                scenario_path,
                scenario_output_dir,
                scenario_name,
                baseline_lulc
            )
            
            logger.info(f"✓ Preprocessing complete for {scenario_name}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Preprocessing failed for {scenario_name}: {e}")
            raise
    
    def find_baseline_lulc(self):
        """Find baseline global LULC file for embedding UK scenarios"""
        
        # Look for baseline LULC in inputs
        potential_files = [
            "inputs/gblulcg20.tif",
            "inputs/current_lulc.tif",
            "inputs/test_data/gblulcg20.tif"
        ]
        
        for filepath in potential_files:
            if Path(filepath).exists():
                logger.info(f"Using baseline LULC: {filepath}")
                return filepath
        
        logger.warning("No baseline global LULC found - scenarios will not be embedded in global grid")
        return None
    
    def run_dust_emissions(self, scenario_name, global_lulc_path):
        """Run dust emissions calculation for a scenario"""
        
        logger.info(f"  Running dust emissions for {scenario_name}")
        
        # Set up scenario-specific intermediate directory
        original_cwd = os.getcwd()
        scenario_intermediate = self.intermediate_dir / scenario_name / "dust"
        scenario_intermediate.mkdir(parents=True, exist_ok=True)
        
        try:
            # Copy/link the scenario LULC file to expected location
            # This assumes the dust scripts read from a specific file name
            # We may need to modify dust scripts to accept dynamic LULC paths
            
            # For now, run with existing approach
            dust_1_soil_texture.run(self.inputdir)
            dust_2_flux_calc.run(self.inputdir)  
            dust_3_sum.run(self.inputdir)
            
            # Move outputs to scenario-specific location
            dust_output_dir = self.outputs_dir / scenario_name / "dust"
            dust_output_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy relevant outputs (this will need to be customized based on actual output files)
            logger.info(f"    ✓ Dust emissions complete for {scenario_name}")
            
        except Exception as e:
            logger.error(f"    ❌ Dust emissions failed for {scenario_name}: {e}")
            raise
        finally:
            os.chdir(original_cwd)
    
    def run_soil_nox_emissions(self, scenario_name, global_lulc_path):
        """Run soil NOx emissions calculation for a scenario"""
        
        logger.info(f"  Running soil NOx emissions for {scenario_name}")
        
        try:
            soil_nox_1_time_varying.run(self.inputdir)
            soil_nox_2_time_varying_sum.run(self.inputdir)
            soil_nox_3_constant.run(self.inputdir)
            soil_nox_4_gblulc.run(self.inputdir)
            soil_nox_5_align.run(self.inputdir)
            
            # Move outputs to scenario-specific location
            soil_nox_output_dir = self.outputs_dir / scenario_name / "soil_nox"
            soil_nox_output_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"    ✓ Soil NOx emissions complete for {scenario_name}")
            
        except Exception as e:
            logger.error(f"    ❌ Soil NOx emissions failed for {scenario_name}: {e}")
            raise
    
    def run_deposition_calculation(self, scenario_name, global_lulc_path):
        """Run deposition calculation for a scenario"""
        
        logger.info(f"  Running deposition calculation for {scenario_name}")
        
        try:
            dep_1_lai_reclass.run(self.inputdir)
            dep_2_lai_month_avg.run(self.inputdir)
            dep_3_velocity.run(self.inputdir)
            dep_4_multiply.run(self.inputdir)
            
            # Move outputs to scenario-specific location
            dep_output_dir = self.outputs_dir / scenario_name / "deposition"
            dep_output_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"    ✓ Deposition calculation complete for {scenario_name}")
            
        except Exception as e:
            logger.error(f"    ❌ Deposition calculation failed for {scenario_name}: {e}")
            raise
    
    def run_bvoc_emissions(self, scenario_name, global_lulc_path):
        """Run BVOC emissions calculation for a scenario (if implemented)"""
        
        logger.info(f"  BVOC emissions not yet implemented for {scenario_name}")
        # TODO: Implement BVOC processing when ready
        pass
    
    def process_single_scenario(self, scenario_path):
        """
        Process a single scenario through all emission models
        
        Args:
            scenario_path: Path to scenario TIFF file
            
        Returns:
            dict: Processing results and output paths
        """
        
        scenario_name = scenario_path.stem
        start_time = time.time()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"PROCESSING SCENARIO: {scenario_name}")
        logger.info(f"{'='*60}")
        
        try:
            # Step 1: Preprocess scenario
            preprocessed = self.preprocess_scenario(scenario_path)
            global_lulc_path = preprocessed['global']
            
            # Step 2: Run emission models
            logger.info("Running emission models...")
            
            # Run each emission model
            self.run_dust_emissions(scenario_name, global_lulc_path)
            self.run_soil_nox_emissions(scenario_name, global_lulc_path) 
            self.run_deposition_calculation(scenario_name, global_lulc_path)
            self.run_bvoc_emissions(scenario_name, global_lulc_path)
            
            # Step 3: Generate summary
            processing_time = time.time() - start_time
            
            result = {
                'scenario_name': scenario_name,
                'status': 'success',
                'processing_time': processing_time,
                'preprocessed_files': preprocessed,
                'output_dir': self.outputs_dir / scenario_name
            }
            
            logger.info(f"✓ SCENARIO COMPLETE: {scenario_name} ({processing_time:.1f}s)")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            logger.error(f"❌ SCENARIO FAILED: {scenario_name} ({processing_time:.1f}s)")
            logger.error(f"Error: {e}")
            
            result = {
                'scenario_name': scenario_name,
                'status': 'failed',
                'processing_time': processing_time,
                'error': str(e)
            }
            
            return result
    
    def run_batch_processing(self, max_workers=2):
        """
        Run batch processing of all scenarios
        
        Args:
            max_workers: Maximum number of parallel workers
        """
        
        logger.info(f"\n🚀 STARTING BATCH PROCESSING")
        logger.info(f"Scenarios: {len(self.scenario_files)}")
        logger.info(f"Max workers: {max_workers}")
        logger.info(f"Output directory: {self.outputs_dir}")
        
        start_time = time.time()
        results = []
        
        # Process scenarios (sequentially for now to avoid conflicts)
        for scenario_file in self.scenario_files:
            result = self.process_single_scenario(scenario_file)
            results.append(result)
        
        # TODO: Implement parallel processing when emission scripts are thread-safe
        # with mp.Pool(max_workers) as pool:
        #     results = pool.map(self.process_single_scenario, self.scenario_files)
        
        # Generate batch summary
        total_time = time.time() - start_time
        successful = [r for r in results if r['status'] == 'success']
        failed = [r for r in results if r['status'] == 'failed']
        
        logger.info(f"\n📊 BATCH PROCESSING COMPLETE")
        logger.info(f"Total time: {total_time:.1f}s")
        logger.info(f"Successful: {len(successful)}/{len(results)}")
        logger.info(f"Failed: {len(failed)}/{len(results)}")
        
        if failed:
            logger.info(f"\nFailed scenarios:")
            for result in failed:
                logger.info(f"  - {result['scenario_name']}: {result.get('error', 'Unknown error')}")
        
        # Save summary
        self.save_processing_summary(results, total_time)
        
        return results
    
    def save_processing_summary(self, results, total_time):
        """Save processing summary to file"""
        
        summary_file = self.outputs_dir / "processing_summary.txt"
        
        with open(summary_file, 'w') as f:
            f.write(f"UK Scenario Emissions Processing Summary\n")
            f.write(f"{'='*50}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total scenarios: {len(results)}\n")
            f.write(f"Total processing time: {total_time:.1f}s\n\n")
            
            successful = [r for r in results if r['status'] == 'success']
            failed = [r for r in results if r['status'] == 'failed']
            
            f.write(f"Successful scenarios: {len(successful)}\n")
            for result in successful:
                f.write(f"  ✓ {result['scenario_name']} ({result['processing_time']:.1f}s)\n")
            
            f.write(f"\nFailed scenarios: {len(failed)}\n")
            for result in failed:
                f.write(f"  ❌ {result['scenario_name']}: {result.get('error', 'Unknown error')}\n")
        
        logger.info(f"Summary saved to: {summary_file}")

def main():
    """Main entry point"""
    
    print("🌍 UK Scenario Emissions Processor")
    print("=" * 50)
    
    try:
        # Initialize processor
        processor = ScenarioEmissionsProcessor()
        
        # Run batch processing
        results = processor.run_batch_processing(max_workers=1)  # Start with 1 worker
        
        print(f"\n✅ Processing complete! Check outputs in: {processor.outputs_dir}")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()