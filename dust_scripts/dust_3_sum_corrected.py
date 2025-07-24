def run(inputdir):
    import os
    import glob
    import datetime
    import rasterio
    import numpy as np
    import math

    # Define the start and end date
    start_date = datetime.datetime(2021, 1, 1)
    end_date = datetime.datetime(2021, 12, 31)

    # Define the input folder containing the TIFF files
    input_folder = "intermediate"

    # Define the output TIFF file
    output_tiff = "./outputs/dust_sum.tiff"

    # Initialize variables
    sum_of_tiffs = None
    reference_transform = None
    reference_crs = None

    print("Summing dust flux files with dynamic pixel area calculation...")

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
                    
                    # Calculate actual pixel area from geotransform
                    pixel_width = abs(reference_transform[0])  # degrees
                    pixel_height = abs(reference_transform[4])  # degrees
                    
                    print(f"  Detected pixel size: {pixel_width:.6f}° × {pixel_height:.6f}°")
                    
                    # Calculate pixel area in cm²
                    # Convert degrees to meters first, then to cm
                    center_lat = 55.0  # Approximate center latitude for UK
                    
                    # Conversion factors: degrees to meters
                    lat_to_m = 111000  # meters per degree latitude
                    lon_to_m = 111000 * math.cos(math.radians(center_lat))  # longitude varies by latitude
                    
                    # Pixel area in m², then convert to cm²
                    pixel_area_m2 = (pixel_width * lon_to_m) * (pixel_height * lat_to_m)
                    pixel_area_cm2 = pixel_area_m2 * 10000  # m² to cm²
                    
                    print(f"  Calculated pixel area: {pixel_area_m2:,.0f} m² ({pixel_area_cm2:,.0f} cm²)")
                    
                    # Time conversion: seconds per day
                    seconds_per_day = 86400
                    
                    # Full conversion factor: g cm⁻² s⁻¹ × cm² × s day⁻¹ × day → g → kg
                    conversion_factor = pixel_area_cm2 * seconds_per_day / 1000  # grams to kg
                    
                    print(f"  Conversion factor (g cm⁻² s⁻¹ to kg day⁻¹): {conversion_factor:,.0f}")
                    
                else:
                    # Add the data from the current TIFF file to the sum
                    sum_of_tiffs += src.read(1).astype(np.float64)
                    
                file_count += 1

    print(f"  Processed {file_count} daily flux files")

    # Apply the dynamically calculated conversion factor
    if sum_of_tiffs is not None:
        print("  Applying area normalization and unit conversion...")
        
        # Apply conversion: flux (g cm⁻² s⁻¹) → total emission (kg)
        sum_of_tiffs = sum_of_tiffs * conversion_factor
        
        print(f"  Total emission before conversion: sum of raw flux values")
        print(f"  Total emission after conversion: {np.sum(sum_of_tiffs[sum_of_tiffs > 0]):,.0f} kg")

        # Create a TIFF file for the sum
        with rasterio.open(output_tiff, 'w', 
                          driver='GTiff', 
                          height=sum_of_tiffs.shape[0],
                          width=sum_of_tiffs.shape[1], 
                          count=1, 
                          dtype='float32', 
                          crs=reference_crs,
                          transform=reference_transform,
                          compress='lzw') as dst:
            dst.write(sum_of_tiffs.astype(np.float32), 1)

        print(f"✅ Corrected dust emissions saved to '{output_tiff}'")
        
        # Create a summary file
        summary_path = output_tiff.replace('.tiff', '_summary.txt')
        with open(summary_path, 'w') as f:
            f.write("Dust Emissions Calculation Summary (Corrected)\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Processing date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Input files processed: {file_count} daily flux files\n")
            f.write(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n\n")
            
            f.write("PIXEL AREA CALCULATION:\n")
            f.write("-" * 30 + "\n")
            f.write(f"Pixel size: {pixel_width:.6f}° × {pixel_height:.6f}°\n")
            f.write(f"Pixel area: {pixel_area_m2:,.0f} m² ({pixel_area_cm2:,.0f} cm²)\n")
            f.write(f"Conversion factor: {conversion_factor:,.0f} (g cm⁻² s⁻¹ to kg day⁻¹)\n\n")
            
            f.write("EMISSION RESULTS:\n")
            f.write("-" * 30 + "\n")
            valid_emissions = sum_of_tiffs[sum_of_tiffs > 0]
            f.write(f"Total emission: {np.sum(valid_emissions):,.0f} kg\n")
            f.write(f"Maximum pixel emission: {np.max(valid_emissions):,.0f} kg\n")
            f.write(f"Mean pixel emission: {np.mean(valid_emissions):,.0f} kg\n")
            f.write(f"Emitting pixels: {len(valid_emissions):,}\n\n")
            
            f.write("CORRECTION APPLIED:\n")
            f.write("-" * 30 + "\n")
            f.write("• Fixed hardcoded pixel area assumption\n")
            f.write("• Dynamic pixel area calculation from geotransform\n")
            f.write("• Proper unit conversion: g cm⁻² s⁻¹ → kg total\n")
            f.write("• Should now match global calculation methodology\n")
        
        print(f"📊 Summary saved to: {summary_path}")
        
    else:
        print("❌ No TIFF files found within the specified date range.")

if __name__ == "__main__":
    run(".")