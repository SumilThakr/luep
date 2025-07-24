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

    # Loop through TIFF files within the specified date range
    for file_path in glob.glob(os.path.join(input_folder, 'flux_masked_*.tif')):
        file_date = datetime.datetime.strptime(os.path.basename(file_path).split('_')[-1].split('.')[0], "%Y%m%d")
        
        if start_date <= file_date <= end_date:
            with rasterio.open(file_path, 'r') as src:
                if sum_of_tiffs is None:
                    # Initialize the sum with the first TIFF file
                    sum_of_tiffs = src.read(1)
                    reference_transform = src.transform
                else:
                    # Add the data from the current TIFF file to the sum
                    sum_of_tiffs += src.read(1)

    # Calculate actual pixel area instead of hardcoded 0.05 degrees
    pixel_width_deg = abs(reference_transform[0])  # degrees longitude
    pixel_height_deg = abs(reference_transform[4])  # degrees latitude
    
    # The flux units are g / cm2-s. So multiply by the cell area in cm2 and seconds per day, and divide by 1000 to get kg
    sum_of_tiffs = sum_of_tiffs * pixel_width_deg*pixel_height_deg*11100000.0*11100000.0*86400/1000

    # Create a TIFF file for the sum
    if sum_of_tiffs is not None:
        with rasterio.open(output_tiff, 'w', driver='GTiff', height=sum_of_tiffs.shape[0],
                           width=sum_of_tiffs.shape[1], count=1, dtype='float32', crs='EPSG:4326',
                           transform=src.transform) as dst:
            dst.write(sum_of_tiffs, 1)

        print(f"Sum of TIFF files saved to '{output_tiff}'")
    else:
        print("No TIFF files found within the specified date range.")
