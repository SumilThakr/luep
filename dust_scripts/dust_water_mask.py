#!/usr/bin/env python3
"""
Post-processing script to mask water areas in dust emission outputs.

This script should ONLY be run if dust emissions are non-zero over water areas due to 
the land use mapping bug that was fixed in dust_landuse_flux_calc.py.

The script:
1. Identifies water areas (land use value 0) in the land use raster
2. Sets dust emissions to 0.0 in all water pixels
3. Creates corrected output files

Usage:
    python dust_scripts/dust_water_mask.py <dust_emission_file> [output_file]

Arguments:
    dust_emission_file: Path to dust emission TIFF file to correct
    output_file: Optional output path (defaults to adding '_water_masked' suffix)

Example:
    python dust_scripts/dust_water_mask.py outputs/dust_emissions.tiff
    python dust_scripts/dust_water_mask.py outputs/dust_emissions.tiff outputs/dust_emissions_corrected.tiff
"""

def run(dust_emission_path, output_path=None, inputdir="."):
    """
    Mask water areas in dust emission raster
    
    Args:
        dust_emission_path: Path to dust emission TIFF file
        output_path: Optional output path (auto-generated if None)
        inputdir: Directory containing inputs folder
    """
    import os
    import pygeoprocessing.geoprocessing as geop
    from osgeo import gdal
    import numpy as np
    from pathlib import Path
    
    print(f"🌊 Masking water areas in dust emissions: {dust_emission_path}")
    
    # Check if input file exists
    if not os.path.exists(dust_emission_path):
        raise FileNotFoundError(f"Dust emission file not found: {dust_emission_path}")
    
    # Generate output path if not provided
    if output_path is None:
        input_path = Path(dust_emission_path)
        output_path = str(input_path.parent / f"{input_path.stem}_water_masked{input_path.suffix}")
    
    # Land use raster path
    lu_raster_path = os.path.join(inputdir, 'inputs', 'gblulcg20_10000.tif')
    if not os.path.exists(lu_raster_path):
        # Try alternative path
        lu_raster_path = os.path.join(inputdir, 'inputs', 'gblulcg20.tif')
        if not os.path.exists(lu_raster_path):
            raise FileNotFoundError(f"Land use raster not found. Tried: gblulcg20_10000.tif and gblulcg20.tif")
    
    print(f"  📍 Using land use raster: {lu_raster_path}")
    print(f"  💾 Output will be saved to: {output_path}")
    
    # Get dust emission raster info for alignment
    dust_info = geop.get_raster_info(dust_emission_path)
    
    # Align land use raster to match dust emission raster
    aligned_lu_path = "intermediate/aligned_landuse_for_water_mask.tif"
    print(f"  🔧 Aligning land use to dust emission grid...")
    geop.align_and_resize_raster_stack(
        [lu_raster_path],
        [aligned_lu_path],
        ['near'],  # Nearest neighbor for categorical data
        dust_info['pixel_size'],
        bounding_box_mode=dust_info['bounding_box'],
        target_projection_wkt=dust_info['projection_wkt']
    )
    
    # Create water mask function
    def apply_water_mask(dust_value, landuse_value):
        """Set dust to 0 where land use is water (value 0), otherwise keep original"""
        if landuse_value == 0:  # Water
            return 0.0
        else:
            return dust_value
    
    apply_water_mask_v = np.vectorize(apply_water_mask)
    
    # Apply water mask
    print(f"  🎯 Applying water mask...")
    listraster = [(dust_emission_path, 1), (aligned_lu_path, 1)]
    geop.raster_calculator(
        base_raster_path_band_const_list=listraster,
        local_op=apply_water_mask_v, 
        target_raster_path=output_path,
        datatype_target=gdal.GDT_Float32,
        nodata_target=-1,
        calc_raster_stats=False
    )
    
    # Clean up temporary file
    if os.path.exists(aligned_lu_path):
        os.remove(aligned_lu_path)
        print(f"  🧹 Cleaned up temporary alignment file")
    
    print(f"  ✅ Water masking completed: {output_path}")
    return output_path

def main():
    """Command line interface"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python dust_scripts/dust_water_mask.py <dust_emission_file> [output_file]")
        print("\nExample:")
        print("  python dust_scripts/dust_water_mask.py outputs/dust_emissions.tiff")
        sys.exit(1)
    
    dust_emission_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        result_path = run(dust_emission_path, output_path)
        print(f"\n🎉 Successfully created water-masked dust emissions: {result_path}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()