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
    output_tiff = "./intermediate/ts_sm_sum.tiff"

    # Initialize variables
    sum_of_tiffs = None

    # Loop through TIFF files within the specified date range
    for file_path in glob.glob(os.path.join(input_folder, 'ts_sm_effect_*.tif')):
        file_date = datetime.datetime.strptime(os.path.basename(file_path).split('_')[-1].split('.')[0], "%Y%m%d")
        
        if start_date <= file_date <= end_date:
            with rasterio.open(file_path, 'r') as src:
                if sum_of_tiffs is None:
                    # Initialize the sum with the first TIFF file
                    sum_of_tiffs = src.read(1)
                else:
                    # Add the data from the current TIFF file to the sum
                    sum_of_tiffs += src.read(1)

    # Apparently, the model time step is 6 hours rather than 1 hour, so divide by 6
    # Actually, I want the daily average across the time horizon.
    sum_of_tiffs = sum_of_tiffs / (24.0 * 365)

    # Create a TIFF file for the sum
    if sum_of_tiffs is not None:
        with rasterio.open(output_tiff, 'w', driver='GTiff', height=sum_of_tiffs.shape[0],
                           width=sum_of_tiffs.shape[1], count=1, dtype='float32', crs='EPSG:4326',
                           transform=src.transform) as dst:
            dst.write(sum_of_tiffs, 1)

        print(f"Sum of TIFF files saved to '{output_tiff}'")
    else:
        print("No TIFF files found within the specified date range.")
