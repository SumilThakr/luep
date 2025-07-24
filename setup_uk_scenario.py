#!/usr/bin/env python3
"""
Simple script to setup UK scenario for processing

Usage:
    python setup_uk_scenario.py <scenario_name>

Example:
    python setup_uk_scenario.py extensification_current_practices

This will:
1. Create UK-only grid.tif from the scenario extent
2. Convert scenario to Simple classification and place in inputs/gblulcg20_10000.tif
3. Ready the system for running: python run_dust_emissions.py (etc.)
"""

import sys
from pathlib import Path

def main():
    if len(sys.argv) != 2:
        print("Usage: python setup_uk_scenario.py <scenario_name>")
        print("\nAvailable scenarios:")
        
        scenarios_dir = Path("scenarios/UKNatureFrontierWithAir/United Kingdom/ScenarioMaps")
        if scenarios_dir.exists():
            for tif_file in scenarios_dir.glob("*.tif"):
                print(f"  - {tif_file.stem}")
        else:
            print(f"  Error: {scenarios_dir} not found")
        
        sys.exit(1)
    
    scenario_name = sys.argv[1]
    scenarios_dir = Path("scenarios/UKNatureFrontierWithAir/United Kingdom/ScenarioMaps")
    scenario_file = scenarios_dir / f"{scenario_name}.tif"
    
    if not scenario_file.exists():
        print(f"Error: Scenario file not found: {scenario_file}")
        print(f"\nAvailable scenarios:")
        for tif_file in scenarios_dir.glob("*.tif"):
            print(f"  - {tif_file.stem}")
        sys.exit(1)
    
    print(f"🌍 Setting up UK scenario: {scenario_name}")
    print("=" * 50)
    
    try:
        # Import the setup utility
        from scenario_scripts.uk_processing_setup import setup_uk_processing_environment, verify_uk_setup
        
        # Setup the processing environment
        result = setup_uk_processing_environment(scenario_file, backup_originals=True)
        
        # Verify setup
        success = verify_uk_setup()
        
        if success:
            print(f"\n🎉 Setup complete! Ready to process scenario: {scenario_name}")
            print(f"\nNext steps:")
            print(f"  python run_dust_emissions.py")
            print(f"  python run_soil_nox_emissions.py") 
            print(f"  python run_deposition_calculation.py")
            print(f"\nOutput will be saved to: outputs/")
            print(f"To restore original global files: python restore_global_setup.py")
        else:
            print(f"\n❌ Setup failed - please check errors above")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Setup error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()