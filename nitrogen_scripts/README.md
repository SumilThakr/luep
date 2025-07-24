# Nitrogen Emissions Calculator

This script calculates nitrogen-related emissions for the UK using FAOSTAT data.

## Input Data
- `pasture_crop_areas_UK.csv` - Land use areas (cropland and permanent pastures)
- `manure_data_UK.csv` - Livestock manure N content data
- `nitrogen_use_data_UK.csv` - Synthetic nitrogen fertilizer application rates
- `EMEP-efs.xlsx` - Emission factors (currently using literature values)

## Methodology

### Data Processing
- All calculations use the average of the 5 most recent years of available data
- Areas are converted from 1000 ha to ha
- Manure data is processed by livestock type with specific emission factors

### Emission Factors Used
**Synthetic Fertilizer:**
- NH3-N emission factor: 4.636% of applied N (UK-specific from IFA data)
- Converted to NH3 mass using factor 17/14

**Manure (Literature-based emission factors):**
- Cattle, dairy: 20% (applied), 10% (pasture)
- Cattle, non-dairy: 18% (applied), 9% (pasture)
- Pigs: 25% (applied), 12.5% (pasture)
- Poultry: 30% (applied), 15% (pasture)
- Sheep/Goats: 15% (applied), 7.5% (pasture)

### Calculations

1. **Land Areas:**
   - Cropland area: Average from "Cropland" category
   - Pasture area: Average from "Perm. meadows & pastures - Cultivated"

2. **Synthetic Fertilizer:**
   - N application rate: Direct from FAOSTAT "Use per area of cropland"
   - NH3 emissions = N rate × 0.0464 × (17/14)

3. **Manure:**
   - Total manure N by category summed across all livestock types
   - Per-hectare values calculated using respective land areas
   - NH3 emissions calculated using livestock-specific emission factors

## Results
The script produces the following metrics (all in kg/ha):

- NH3 emissions from pasture land: **9.83 kg/ha**
- N left on pasture: **101.11 kg/ha**
- N applied to cropland (total): **211.67 kg/ha**
  - Synthetic fertilizer: 129.56 kg/ha
  - Manure: 82.11 kg/ha
- NH3 emissions from cropland (total): **18.23 kg/ha**
  - From synthetic fertilizer: 0.07 kg/ha
  - From manure: 18.16 kg/ha

## Output
Results are saved to `intermediate/nitrogen_emissions_uk.csv`

## Usage
```bash
cd /path/to/luep
python nitrogen_scripts/calculate_nitrogen_emissions.py
```

## Notes
- The EMEP emission factors file was not accessible, so literature-based values were used
- All emission factors convert NH3-N to NH3 mass using the molecular weight ratio (17/14)
- Pasture manure typically has lower volatilization rates than applied manure