def run(inputdir):
    import geopandas as gpd
    import pandas as pd
    import rasterio
    from rasterio.features import rasterize
    from rasterio.transform import from_origin
    import numpy as np
    import pygeoprocessing
    import os

    # Load the shapefile
    shapefile = gpd.read_file(os.path.join(inputdir,"inputs","soil_mapping_statsgo_fao","DSMW","DSMW.shp"))

    # Load the CSV mapping file
    mapping_df = pd.read_csv(os.path.join(inputdir,"inputs","soil_mapping_statsgo_fao","map.csv"))

    # Merge shapefile with the CSV to create a new attribute based on the mapping
    shapefile = shapefile.merge(mapping_df, on="DOMSOI", how="left")

    # Fill unmatched values with 'NA'
    shapefile['Class'] = shapefile['Class'].fillna('NA')

    # Define raster specifications
    pixel_size = 0.5
    xmin, ymin, xmax, ymax = -180.0, -90.0, 180.0, 90.0
    width = int((xmax - xmin) / 0.625)
    height = int((ymax - ymin) / 0.5)
    transform = from_origin(xmin, ymax, 0.625, 0.5)

    # Create an empty raster array with 'NA' as the default value
    raster_data = np.full((height, width), -1, dtype=np.int32)

    # Convert 'Class' to categorical integer values (needed for rasterization)
    class_values = {value: idx for idx, value in enumerate(shapefile['Class'].unique())}
    # print(shapefile['Class'].unique()) # Note: these are the assignments [0 = 'MS', 1 = 'NA', 2 = 'FSS', 3 = 'FS', 4 = 'CS']
    shapefile['Class_idx'] = shapefile['Class'].map(class_values)

    # Rasterize the shapefile, with each polygon getting the value of 'Class_idx'
    rasterized = rasterize(
        [(geom, value) for geom, value in zip(shapefile.geometry, shapefile.Class_idx)],
        out_shape=raster_data.shape,
        transform=transform,
        fill=-1,  # fill value for areas with no data
        all_touched=True,
        dtype=raster_data.dtype
    )

    # Create a function to calculate majority within each polygon
    def majority_class(rasterized_array):
        unique, counts = np.unique(rasterized_array, return_counts=True)
        majority_value = unique[np.argmax(counts)]
        return majority_value

    # Zonal statistics using pygeoprocessing
    def calculate_zonal_statistics(shapefile, rasterized, transform, height, width):
        # Output raster array to store results
        output_raster = np.full((height, width), -1, dtype=np.int32)

        # Loop through each polygon and calculate the majority value
        for idx, row in shapefile.iterrows():
            geom_mask = rasterize(
                [(row.geometry, 1)],
                out_shape=(height, width),
                transform=transform,
                fill=0,
                all_touched=True,
                dtype=np.uint8
            )

            masked_raster = rasterized[geom_mask == 1]
            if len(masked_raster) > 0:
                majority_value = majority_class(masked_raster)
                output_raster[geom_mask == 1] = majority_value

        return output_raster

    # Calculate zonal statistics (majority class)
    output_raster = calculate_zonal_statistics(shapefile, rasterized, transform, height, width)

    # Save the raster to a GeoTIFF file
    with rasterio.open(
        "./intermediate/soil_texture.tif",
        "w",
        driver="GTiff",
        height=output_raster.shape[0],
        width=output_raster.shape[1],
        count=1,
        dtype=output_raster.dtype,
        crs="EPSG:4326",  # CRS for WGS84
        transform=transform,
    ) as dst:
        dst.write(output_raster, 1)

    print("Raster saved as ./intermediate/soil_texture.tif")
