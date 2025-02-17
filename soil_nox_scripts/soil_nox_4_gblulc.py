def run(inputdir):
    import sys
    from osgeo import gdal
    # Input and output file paths:
    input_file = ("./intermediate/lu_effect.tif")
    output_file = ("./intermediate/lu_effect_reproj.tif")
    
    # Define the source spatial reference system as used by QGIS.
    source_srs = (
        'PROJCRS["Interrupted_Goode_Homolosine",'
        'BASEGEOGCRS["GCS_Normal_Sphere_r_6370997",'
        'DATUM["D_unknown",'
        'ELLIPSOID["sphere",6370997,0,LENGTHUNIT["metre",1,ID["EPSG",9001]]]],'
        'PRIMEM["Greenwich",0,ANGLEUNIT["Degree",0.0174532925199433]]],'
        'CONVERSION["unnamed",'
        'METHOD["Interrupted Goode Homolosine"],'
        'PARAMETER["Longitude of natural origin",0,ANGLEUNIT["Degree",0.0174532925199433],ID["EPSG",8802]],'
        'PARAMETER["False easting",0,LENGTHUNIT["metre",1],ID["EPSG",8806]],'
        'PARAMETER["False northing",0,LENGTHUNIT["metre",1],ID["EPSG",8807]]],'
        'CS[Cartesian,2],'
        'AXIS["(E)",east,ORDER[1],LENGTHUNIT["metre",1,ID["EPSG",9001]]],'
        'AXIS["(N)",north,ORDER[2],LENGTHUNIT["metre",1,ID["EPSG",9001]]]]'
    )
    
    # Define the target spatial reference system (EPSG:4326).
    target_srs = 'EPSG:4326'
    
    # Create warp options matching the QGIS parameters:
    # - srcSRS: The source projection (as above)
    # - dstSRS: The target projection (EPSG:4326)
    # - resampleAlg: Nearest neighbor resampling ('near')
    # - format: Output format (GeoTIFF)
    warp_options = gdal.WarpOptions(
        srcSRS=source_srs,
        dstSRS=target_srs,
        resampleAlg=gdal.GRA_NearestNeighbour,
        format='GTiff'
    )
    
    print("Reprojecting:")
    print("  Input:  ", input_file)
    print("  Output: ", output_file)
    print("  Source SRS:", source_srs)
    print("  Target SRS:", target_srs)
    
    # Run the warp (reprojection)
    output = gdal.Warp(destNameOrDestDS=output_file, srcDSOrSrcDSTab=input_file, options=warp_options)
    
    if output is None:
        print("Error: Reprojection failed.", file=sys.stderr)
        sys.exit(1)
    else:
        print("Reprojection completed successfully.")
    
    # Close the output dataset to flush to disk.
    output = None
