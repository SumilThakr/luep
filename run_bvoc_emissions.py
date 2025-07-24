#!/usr/bin/env python3
"""
Main script for running bVOC emissions processing

This script estimates bVOC emissions for a given land use scenario by:
1. Loading baseline bVOC emissions by land use type
2. Estimating counterfactual emissions for the scenario
3. Saving results to outputs folder
"""

import os
import sys
from datetime import datetime

def run(inputdir="inputs"):
    """Run bVOC emissions processing"""
    
    print("=" * 60)
    print("bVOC EMISSIONS PROCESSING")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Input land use file (should be in Simple 4-class format)
    landuse_path = os.path.join(inputdir, "gblulcg20_10000.tif")
    
    if not os.path.exists(landuse_path):
        print(f"Error: Land use file not found: {landuse_path}")
        print("Make sure to run UK scenario setup first if processing UK scenarios")
        return False
    
    # Output path
    output_path = "outputs/bvoc_emissions.nc"
    os.makedirs("outputs", exist_ok=True)
    
    print(f"Input land use: {landuse_path}")
    print(f"Output: {output_path}")
    
    try:
        # Import and run the counterfactual calculator
        sys.path.append('bvoc_scripts')
        from bvoc_counterfactual import main as calc_main
        
        # Override sys.argv to pass arguments
        original_argv = sys.argv
        sys.argv = ['bvoc_counterfactual.py', landuse_path, output_path]
        
        # Run the calculation
        calc_main()
        
        # Restore original argv
        sys.argv = original_argv
        
        print(f"\n✅ bVOC emissions processing completed successfully!")
        print(f"Results saved to: {output_path}")
        return True
        
    except Exception as e:
        print(f"\n❌ bVOC emissions processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    # Allow override of input directory via command line
    if len(sys.argv) > 1:
        inputdir = sys.argv[1]
    else:
        inputdir = "inputs"
    
    success = run(inputdir)
    sys.exit(0 if success else 1)