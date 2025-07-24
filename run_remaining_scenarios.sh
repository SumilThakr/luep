#!/bin/bash

# Script to run remaining UK dust scenarios sequentially
# Run with: bash run_remaining_scenarios.sh

PYTHON_PATH="/Users/sumilthakrar/yes/envs/rasters/bin/python"

# Scenarios that need to be rerun with corrected code
scenarios=(
    "extensification_bmps_irrigated"
    "extensification_bmps_rainfed" 
    "extensification_intensified_irrigated"
    "extensification_intensified_rainfed"
    "fixedarea_bmps_irrigated"
    "fixedarea_bmps_rainfed"
    "fixedarea_intensified_irrigated"
    "fixedarea_intensified_rainfed"
    "forestry_expansion"
    "grazing_expansion"
    "restoration"
    "sustainable_current"
)

echo "========================================================"
echo "UK Dust Scenarios - Sequential Processing"
echo "========================================================"
echo "Total scenarios: ${#scenarios[@]}"
echo "Estimated time: ~4 hours (20 min per scenario)"
echo "Started at: $(date)"
echo ""

successful=0
failed=0

for i in "${!scenarios[@]}"; do
    scenario="${scenarios[$i]}"
    progress=$((i + 1))
    
    echo ""
    echo "=========================================="
    echo "[$progress/${#scenarios[@]}] Processing: $scenario"
    echo "=========================================="
    echo "Started at: $(date)"
    
    # Setup scenario
    echo "📋 Setting up scenario..."
    if $PYTHON_PATH setup_uk_scenario.py "$scenario"; then
        echo "✅ Setup completed"
    else
        echo "❌ Setup failed for $scenario"
        ((failed++))
        continue
    fi
    
    # Run dust emissions
    echo "🌪️ Running dust emissions calculation..."
    if $PYTHON_PATH run_dust_emissions.py; then
        echo "✅ Dust calculation completed"
    else
        echo "❌ Dust calculation failed for $scenario"
        ((failed++))
        continue
    fi
    
    # Save results
    echo "💾 Saving results..."
    output_dir="outputs/uk_results/$scenario"
    mkdir -p "$output_dir"
    
    if [ -f "outputs/dust_sum.tiff" ]; then
        # Copy results with timestamp
        timestamp=$(date +"%Y%m%d_%H%M%S")
        cp "outputs/dust_sum.tiff" "$output_dir/dust_emissions_corrected_$timestamp.tiff"
        cp "outputs/dust_sum.tiff" "$output_dir/dust_emissions.tiff"
        
        # Quick validation using Python
        validation_result=$($PYTHON_PATH -c "
import rasterio
import numpy as np

with rasterio.open('outputs/dust_sum.tiff') as src:
    data = src.read(1)
    
total_emissions = np.sum(data[data > 0])
negative_pixels = np.sum(data < 0)
status = 'PASS' if negative_pixels == 0 else 'FAIL'
print(f'{total_emissions/1e9:.1f} Gg, {negative_pixels} negative pixels, {status}')
")
        
        echo "📊 Results: $validation_result"
        ((successful++))
        
        # Create summary file
        cat > "$output_dir/dust_emissions_summary.txt" << EOF
Dust Emissions Summary - $scenario
================================================================

Processing Date: $(date)
Scenario: $scenario
Land Use Source: ESA-CCI high-resolution data (0.002778° pixels)
Processing Period: Full year 2021 (365 days)
Resolution Correction: APPLIED ✅

RESULTS: $validation_result

FILES GENERATED:
===============
dust_emissions.tiff - Spatial dust emission map (kg/pixel/year)
dust_emissions_corrected_$timestamp.tiff - Timestamped backup
dust_emissions_summary.txt - This summary file
EOF
        
    else
        echo "❌ Output file not found for $scenario"
        ((failed++))
    fi
    
    echo "Completed at: $(date)"
done

echo ""
echo "========================================================"
echo "PROCESSING COMPLETE"
echo "========================================================"
echo "Finished at: $(date)"
echo "✅ Successful: $successful/${#scenarios[@]}"
echo "❌ Failed: $failed/${#scenarios[@]}"
echo ""
echo "📁 All results saved in: outputs/uk_results/"
echo ""

if [ $failed -gt 0 ]; then
    echo "⚠️  Some scenarios failed. Check output above for details."
    exit 1
else
    echo "🎉 All scenarios completed successfully!"
    exit 0
fi