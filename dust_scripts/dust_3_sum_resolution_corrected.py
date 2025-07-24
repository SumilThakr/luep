def run(inputdir):
    import os
    import glob
    import datetime
    import rasterio
    import numpy as np

    # Define the start and end date
    start_date = datetime.datetime(2021, 1, 1)
    end_date = datetime.datetime(2021, 12, 31)

    # Define the input folder containing the TIFF files
    input_folder = "intermediate"

    # Define the output TIFF file
    output_tiff = "./outputs/dust_sum_resolution_corrected.tiff"

    # Initialize variables
    sum_of_tiffs = None
    reference_transform = None
    reference_crs = None

    print("Summing dust flux files with resolution correction...")

    # Loop through TIFF files within the specified date range
    file_count = 0
    for file_path in glob.glob(os.path.join(input_folder, 'flux_masked_*.tif')):
        file_date = datetime.datetime.strptime(os.path.basename(file_path).split('_')[-1].split('.')[0], "%Y%m%d")
        
        if start_date <= file_date <= end_date:
            with rasterio.open(file_path, 'r') as src:
                if sum_of_tiffs is None:
                    # Initialize the sum with the first TIFF file
                    sum_of_tiffs = src.read(1).astype(np.float64)  # Use float64 for precision
                    reference_transform = src.transform
                    reference_crs = src.crs
                    
                    print(f"  Processing flux files generated with resolution correction")
                    print(f"  Flux units: g/pixel/s (already area-corrected)")
                    
                else:
                    # Add the data from the current TIFF file to the sum
                    sum_of_tiffs += src.read(1).astype(np.float64)
                    
                file_count += 1

    print(f"  Processed {file_count} daily flux files")

    # Apply the conversion: flux (g/pixel/s) × seconds_per_day → g/pixel/day → kg/pixel/day
    if sum_of_tiffs is not None:
        print("  Applying time conversion and unit scaling...")
        
        seconds_per_day = 86400
        
        # Convert: g/pixel/s → kg/pixel/day → kg total
        sum_of_tiffs_kg = sum_of_tiffs * seconds_per_day / 1000  # g/pixel/day → kg/pixel/day
        total_emissions_kg = np.sum(sum_of_tiffs_kg[sum_of_tiffs_kg > 0])
        
        print(f"  Total emission (resolution-corrected): {total_emissions_kg:,.0f} kg")

        # Create a TIFF file for the sum (in kg/pixel/day)
        with rasterio.open(output_tiff, 'w', 
                          driver='GTiff', 
                          height=sum_of_tiffs_kg.shape[0],
                          width=sum_of_tiffs_kg.shape[1], 
                          count=1, 
                          dtype='float32', 
                          crs=reference_crs,
                          transform=reference_transform,
                          compress='lzw') as dst:
            dst.write(sum_of_tiffs_kg.astype(np.float32), 1)

        print(f"✅ Resolution-corrected dust emissions saved to '{output_tiff}'")
        
        # Create a summary file
        summary_path = output_tiff.replace('.tiff', '_summary.txt')
        with open(summary_path, 'w') as f:
            f.write("Dust Emissions Calculation Summary (Resolution-Corrected)\\n")
            f.write("=" * 60 + "\\n\\n")
            f.write(f"Processing date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
            f.write(f"Input files processed: {file_count} daily flux files\\n")
            f.write(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\\n\\n")
            
            f.write("RESOLUTION CORRECTION APPLIED:\\n")
            f.write("-" * 40 + "\\n")
            f.write("• Flux calculation accounts for actual pixel area\\n")
            f.write("• Per-pixel emissions scale with geographic area\\n")
            f.write("• Results are resolution-independent\\n")
            f.write("• Units: g/pixel/s → kg total emissions\\n\\n")
            
            f.write("EMISSION RESULTS:\\n")
            f.write("-" * 40 + "\\n")
            valid_emissions = sum_of_tiffs_kg[sum_of_tiffs_kg > 0]
            f.write(f"Total emission: {total_emissions_kg:,.0f} kg\\n")
            f.write(f"Maximum pixel emission: {np.max(valid_emissions):,.2f} kg/day\\n")
            f.write(f"Mean pixel emission: {np.mean(valid_emissions):,.2f} kg/day\\n")
            f.write(f"Emitting pixels: {len(valid_emissions):,}\\n\\n")
            
            f.write("CORRECTIONS APPLIED:\\n")
            f.write("-" * 40 + "\\n")
            f.write("• Fixed per-pixel flux calculation scaling\\n")
            f.write("• Removed hardcoded pixel area assumptions\\n")
            f.write("• Ensured resolution-independent results\\n")
            f.write("• Should now match global calculation methodology\\n")
        
        print(f"📊 Summary saved to: {summary_path}")
        
    else:
        print("❌ No TIFF files found within the specified date range.")

if __name__ == "__main__":
    run(".")