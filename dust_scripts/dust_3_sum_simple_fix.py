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
    output_tiff = "./outputs/dust_sum.tiff"

    # Initialize variables
    sum_of_tiffs = None
    reference_transform = None
    reference_crs = None

    # Loop through TIFF files within the specified date range
    for file_path in glob.glob(os.path.join(input_folder, 'flux_masked_*.tif')):
        file_date = datetime.datetime.strptime(os.path.basename(file_path).split('_')[-1].split('.')[0], "%Y%m%d")
        
        if start_date <= file_date <= end_date:
            with rasterio.open(file_path, 'r') as src:
                if sum_of_tiffs is None:
                    # Initialize the sum with the first TIFF file
                    sum_of_tiffs = src.read(1).astype(np.float64)
                    reference_transform = src.transform
                    reference_crs = src.crs
                else:
                    # Add the data from the current TIFF file to the sum
                    sum_of_tiffs += src.read(1).astype(np.float64)

    if sum_of_tiffs is not None:
        # SIMPLE FIX: Calculate actual pixel area instead of using hardcoded 0.05°
        pixel_width_deg = abs(reference_transform[0])  # degrees longitude
        pixel_height_deg = abs(reference_transform[4])  # degrees latitude
        
        print(f"Detected pixel size: {pixel_width_deg:.6f}° × {pixel_height_deg:.6f}°")
        
        # Convert to area in cm² (using same approach as original but with correct pixel size)
        # Original: 0.05*0.05*11100000.0*11100000.0*86400/1000
        # Fixed: pixel_width * pixel_height * 11100000.0 * 11100000.0 * 86400 / 1000
        conversion_factor = pixel_width_deg * pixel_height_deg * 11100000.0 * 11100000.0 * 86400 / 1000
        
        print(f"Original conversion factor (0.05° pixels): {0.05*0.05*11100000.0*11100000.0*86400/1000:,.0f}")
        print(f"Corrected conversion factor ({pixel_width_deg:.6f}° pixels): {conversion_factor:,.0f}")
        print(f"Ratio (should be ~324): {conversion_factor / (0.05*0.05*11100000.0*11100000.0*86400/1000):.1f}")

        # Apply the conversion: g cm⁻² s⁻¹ → kg total
        sum_of_tiffs_kg = sum_of_tiffs * conversion_factor
        
        # Calculate total emissions
        total_emissions = np.sum(sum_of_tiffs_kg[sum_of_tiffs_kg > 0])
        print(f"Total dust emissions: {total_emissions:,.0f} kg")

        # Create a TIFF file for the sum
        with rasterio.open(output_tiff, 'w', 
                          driver='GTiff', 
                          height=sum_of_tiffs_kg.shape[0],
                          width=sum_of_tiffs_kg.shape[1], 
                          count=1, 
                          dtype='float32', 
                          crs=reference_crs,
                          transform=reference_transform) as dst:
            dst.write(sum_of_tiffs_kg.astype(np.float32), 1)

        print(f"✅ Sum of TIFF files saved to '{output_tiff}'")
    else:
        print("No TIFF files found within the specified date range.")