# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL: Python Environment Setup

**ALWAYS use the rasters conda environment when running Python scripts in this project:**

```bash
# Use rasters conda environment
/Users/sumilthakrar/yes/envs/rasters/bin/python
```

This environment contains all required dependencies including rasterio, xarray, pygeoprocessing, geopandas, etc.

## CRITICAL: Process Execution and File Validation Rules

**ALWAYS follow these rules when running processes and checking outputs:**

### 1. File Existence ≠ Process Completion
**NEVER assume that because a file exists, the process that generates it has completed successfully.**
- Always check file timestamps against when you started the process
- Check file sizes for reasonableness 
- Verify file contents when possible
- Look for process completion messages or status indicators

### 2. Timeout Management
**NEVER implement arbitrary timeouts (e.g., 10 minutes) without explicit user approval.**
- Long-running scientific calculations (dust emissions, meteorology processing) can take hours
- Ask the user before adding any timeout limits to bash commands
- If a process appears to be stalling, describe what you observe and ask for guidance
- Use `timeout=600000` (10 minutes) only when explicitly requested by the user

### 3. Process Monitoring
- Monitor intermediate files to assess progress
- Check for error messages in process output
- Verify expected file generation patterns
- Report progress indicators to the user

## Project Overview

This is a land use emissions processor with process-based models for estimating net pollutant emissions tied to land use. The system has four main emission modules:
- **Windblown dust** - dust emissions from different soil types and land uses
- **Soil NOx** - nitrogen oxide emissions from soils
- **Biogenic VOCs** - volatile organic compound emissions from vegetation
- **Deposition** - PM2.5 deposition from vegetation

## Known Issues / TODOs

### Pixel Area Calculation Inconsistency
**TODO**: Standardize pixel area calculations across all emission modules. Currently:
- **Dust emissions**: Uses simple method (308.4m × 308.4m = 9.51 ha/pixel)
- **NH3 emissions**: Uses latitude-corrected method (175.2m × 308.4m = 5.40 ha/pixel at 55°N)

The NH3 method is more geographically accurate but creates inconsistency. Either:
1. Update dust to use latitude correction, OR
2. Update NH3 to use simple method for consistency

Impact: Creates ~43% difference in emission totals between modules for same land area.

## Architecture

The codebase follows a modular structure with:
- **Main run scripts**: `run_deposition_calculation.py`, `run_dust_emissions.py`, `run_soil_nox_emissions.py` (BVOC scripts exist but no main runner)
- **Module folders**: Each emission type has its own folder (`dep_scripts/`, `dust_scripts/`, `soil_nox_scripts/`, `bvoc_scripts/`) containing sequential processing steps
- **Data flow**: `inputs/` → `intermediate/` → `outputs/`

### Processing Pattern
Each module follows a sequential step pattern:
1. Data preprocessing/reclassification  
2. Calculations with meteorological data
3. Aggregation/summation
4. Final output generation

Scripts within each module are numbered sequentially (e.g., `dep_1_lai_reclass.py`, `dep_2_lai_month_avg.py`).

## Key Dependencies

The system primarily uses:
- `pygeoprocessing` - geospatial raster processing
- `xarray` - multidimensional array processing (NetCDF files)
- `rasterio` - geospatial raster I/O
- `numpy` - numerical computing
- `pandas` - data manipulation
- `osgeo` (GDAL) - geospatial data processing
- `netCDF4` - NetCDF file handling

## Data Structure

- **Input data**: Local `inputs/` folder contains meteorological (MERRA2), soil moisture (SMOPS, SMAP), concentration (GHAP PM2.5), land use (LULC), and vegetation (LAI) data files
- **Scenarios**: `scenarios/` folder contains model scenarios and optimization results (e.g., UKNatureFrontierWithAir with various land use scenarios and ecosystem service outputs)
- **Input data path**: Configured in each main run script via `inputdir` variable (can be set to local `inputs/` or external drive paths)
- **Grid reference**: `grid.tif` in root directory used for spatial alignment
- **Intermediate outputs**: Saved to `intermediate/` folder for diagnostics and debugging
- **Final outputs**: Saved to `outputs/` folder

### Key Input Data Types
- **MERRA2**: Daily meteorological data (wind speeds, precipitation) for 2021
- **SMOPS**: Daily soil moisture data for 2021
- **GHAP**: Monthly PM2.5 concentration data
- **LAI**: Leaf Area Index data by plant functional types
- **Land Use**: Global land use/land cover classifications (IGBP, USGS mappings)

## Running the Models

Execute the main run scripts:
```bash
python run_deposition_calculation.py
python run_dust_emissions.py  
python run_soil_nox_emissions.py
python run_bvoc_emissions.py
```

Each script imports and runs its module steps sequentially, with progress messages printed to console.

## Configuration

The main configuration point is the `inputdir` variable in each run script, which points to the base data directory. Scripts currently default to local `inputs/` folder.

To use local data, the `inputdir` variable in run scripts is set to:
```python
inputdir = "inputs"  # Use local inputs/ folder
```

## UK Scenario Processing

The system includes utilities for processing UK land use scenarios with ESA CCI classification:

### Setup UK Scenario
```bash
python setup_uk_scenario.py <scenario_name>
```

Available scenarios in `scenarios/UKNatureFrontierWithAir/United Kingdom/ScenarioMaps/`:
- extensification_current_practices
- extensification_bmps_irrigated  
- extensification_bmps_rainfed
- extensification_intensified_irrigated
- extensification_intensified_rainfed
- fixedarea_bmps_irrigated
- fixedarea_bmps_rainfed
- fixedarea_intensified_irrigated
- fixedarea_intensified_rainfed
- forestry_expansion
- grazing_expansion
- restoration
- sustainable_current
- all_econ
- all_urban

### Process UK Emissions
After setup, run emission calculations:
```bash
python run_dust_emissions.py
python run_soil_nox_emissions.py  
python run_deposition_calculation.py
python run_bvoc_emissions.py
```

### Restore Global Setup
```bash
python restore_global_setup.py
```

### Test UK Processing
```bash
python test_uk_processing.py
python test_bvoc_uk.py
```

## bVOC Counterfactual Processing

The system includes advanced bVOC emission estimation for counterfactual land use scenarios:

### Baseline bVOC Data
- `ag-bvoc.nc` - Agricultural/cropland emissions  
- `forest-bvoc.nc` - Forest emissions
- `grass-bvoc.nc` - Grassland emissions

### Spatial Interpolation Method
For counterfactual scenarios, bVOC emissions are estimated using:
1. **Direct lookup**: Same land use at same location uses baseline emissions
2. **Resolution handling**: Averages overlapping non-zero emissions for different resolutions
3. **Spatial interpolation**: Nearest neighbor search for new land use types (default 50km radius)

### Usage
```bash
# Direct calculation
python bvoc_scripts/bvoc_counterfactual.py <landuse_file> <output_file>

# Via main script (uses inputs/gblulcg20_10000.tif)
python run_bvoc_emissions.py
```

## UK Processing Features

- **Dynamic grid sizing**: Fixed hardcoded array dimensions in emission scripts
- **ESA CCI conversion**: Converts UK scenarios from ESA CCI to Simple 4-class system
- **UK-only processing**: No need to crop global input data - pygeoprocessing handles extent automatically
- **Geographic bounds**: UK extent (-8.17 to 1.77 lon, 49.91 to 60.85 lat)
- **Backup/restore**: Automatically backs up original files before UK processing
- **bVOC counterfactual**: Spatial interpolation for missing emission data in new land use locations