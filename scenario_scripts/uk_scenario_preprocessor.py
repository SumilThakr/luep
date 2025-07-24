#!/usr/bin/env python3
"""
UK scenario preprocessing for emissions processing
Handles reprojection, alignment, and classification conversion
"""

import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds
import numpy as np
from pathlib import Path
import pygeoprocessing.geoprocessing as geop
from .esa_to_simple_converter import convert_esa_to_simple, load_uk_esa_mapping

# UK bounds from actual scenario data
UK_BOUNDS = {
    'min_lon': -8.17,
    'max_lon': 1.77,
    'min_lat': 49.91,
    'max_lat': 60.85
}

def get_reference_grid_info():
    """Get reference grid information from the global grid.tif"""
    grid_path = "grid.tif"
    
    if not Path(grid_path).exists():
        raise FileNotFoundError(f"Reference grid file not found: {grid_path}")
    
    return geop.get_raster_info(grid_path)

def create_uk_processing_mask(ref_grid_info, output_path):
    """
    Create a processing mask for UK region within global grid
    
    Args:
        ref_grid_info: Reference grid information from pygeoprocessing
        output_path: Path to save the UK mask
    """
    
    print("Creating UK processing mask...")
    
    # Get bounds and transform from reference grid
    ref_bounds = ref_grid_info['bounding_box']
    ref_transform = ref_grid_info['geotransform']
    ref_width = ref_grid_info['raster_size'][0]
    ref_height = ref_grid_info['raster_size'][1]
    
    # Create coordinate arrays
    lon = np.linspace(ref_bounds[0], ref_bounds[2], ref_width)
    lat = np.linspace(ref_bounds[3], ref_bounds[1], ref_height)
    
    lon_grid, lat_grid = np.meshgrid(lon, lat)
    
    # Create UK mask
    uk_mask = (
        (lon_grid >= UK_BOUNDS['min_lon']) &
        (lon_grid <= UK_BOUNDS['max_lon']) &
        (lat_grid >= UK_BOUNDS['min_lat']) &
        (lat_grid <= UK_BOUNDS['max_lat'])
    )
    
    # Save mask
    profile = {
        'driver': 'GTiff',
        'height': ref_height,
        'width': ref_width,
        'count': 1,
        'dtype': 'uint8',
        'crs': ref_grid_info['projection_wkt'],
        'transform': rasterio.transform.from_bounds(*ref_bounds, ref_width, ref_height),
        'compress': 'lzw',
        'nodata': 0
    }
    
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(uk_mask.astype(np.uint8), 1)
    
    print(f"  UK mask saved to: {output_path}")
    return uk_mask

def preprocess_uk_scenario(scenario_path, output_dir, scenario_name, baseline_lulc_path=None):
    """
    Preprocess a UK scenario for emissions processing
    
    Args:
        scenario_path: Path to UK scenario TIFF file
        output_dir: Directory to save processed outputs
        scenario_name: Name of the scenario
        baseline_lulc_path: Optional path to baseline global LULC for embedding
        
    Returns:
        dict: Paths to processed files
    """
    
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    print(f"\nPreprocessing UK scenario: {scenario_name}")
    print("=" * 50)
    
    # Get reference grid info
    ref_grid_info = get_reference_grid_info()
    
    # Step 1: Convert ESA CCI to Simple classification
    print("Step 1: Converting ESA CCI to Simple classification...")
    simple_path = output_dir / f"{scenario_name}_simple.tif"
    convert_esa_to_simple(scenario_path, simple_path)
    
    # Step 2: Align to reference grid
    print("Step 2: Aligning to reference grid...")
    aligned_path = output_dir / f"{scenario_name}_aligned.tif"
    
    geop.align_and_resize_raster_stack(
        [str(simple_path)],
        [str(aligned_path)],
        ['near'],  # Use nearest neighbor for categorical data
        ref_grid_info['pixel_size'],
        bounding_box_mode=ref_grid_info['bounding_box'],
        target_projection_wkt=ref_grid_info['projection_wkt']
    )
    
    # Step 3: Create UK mask if it doesn't exist
    uk_mask_path = output_dir / "uk_processing_mask.tif"
    if not uk_mask_path.exists():
        create_uk_processing_mask(ref_grid_info, uk_mask_path)
    
    # Step 4: Embed UK scenario in global grid (if baseline provided)
    if baseline_lulc_path and Path(baseline_lulc_path).exists():
        print("Step 3: Embedding UK scenario in global baseline...")
        global_path = output_dir / f"{scenario_name}_global.tif"
        embed_uk_in_global(aligned_path, baseline_lulc_path, uk_mask_path, global_path)
    else:
        print("Step 3: Skipping global embedding (no baseline provided)")
        global_path = aligned_path
    
    # Step 5: Verify processing
    print("Step 4: Verifying processed scenario...")
    verify_processed_scenario(scenario_path, global_path)
    
    result_paths = {
        'original': scenario_path,
        'simple': simple_path,
        'aligned': aligned_path,
        'global': global_path,
        'uk_mask': uk_mask_path
    }
    
    print(f"✓ Preprocessing complete for {scenario_name}")
    return result_paths

def embed_uk_in_global(uk_scenario_path, baseline_path, uk_mask_path, output_path):
    """
    Embed UK scenario data into global baseline land use
    
    Args:
        uk_scenario_path: Path to aligned UK scenario
        baseline_path: Path to global baseline LULC
        uk_mask_path: Path to UK processing mask
        output_path: Path for output global scenario
    """
    
    print("  Embedding UK scenario in global baseline...")
    
    with rasterio.open(baseline_path) as baseline_src, \
         rasterio.open(uk_scenario_path) as uk_src, \
         rasterio.open(uk_mask_path) as mask_src:
        
        # Read data
        baseline_data = baseline_src.read(1)
        uk_data = uk_src.read(1)
        uk_mask = mask_src.read(1).astype(bool)
        
        # Create output by copying baseline
        output_data = baseline_data.copy()
        
        # Replace UK region with scenario data
        output_data[uk_mask] = uk_data[uk_mask]
        
        # Save result
        profile = baseline_src.profile.copy()
        profile.update({'compress': 'lzw'})
        
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(output_data, 1)
            dst.set_band_description(1, f"Global LULC with UK scenario embedded")
    
    print(f"    Embedded scenario saved to: {output_path}")

def verify_processed_scenario(original_path, processed_path):
    """Verify that preprocessing maintained data integrity"""
    
    print("  Verifying data integrity...")
    
    with rasterio.open(original_path) as orig_src, \
         rasterio.open(processed_path) as proc_src:
        
        # Basic checks
        print(f"    Original: {orig_src.width}x{orig_src.height}, CRS: {orig_src.crs}")
        print(f"    Processed: {proc_src.width}x{proc_src.height}, CRS: {proc_src.crs}")
        
        # Check if UK region is preserved (sample check)
        orig_data = orig_src.read(1)
        proc_data = proc_src.read(1)
        
        # Count class distribution in original
        orig_unique, orig_counts = np.unique(orig_data, return_counts=True)
        proc_unique, proc_counts = np.unique(proc_data, return_counts=True)
        
        print(f"    Original classes: {len(orig_unique)}, Processed classes: {len(proc_unique)}")
        print("  ✓ Verification complete")

def batch_preprocess_scenarios(scenarios_dir, output_dir, baseline_lulc_path=None):
    """
    Batch preprocess all scenarios in a directory
    
    Args:
        scenarios_dir: Directory containing UK scenario TIFF files
        output_dir: Directory to save processed outputs
        baseline_lulc_path: Optional path to baseline global LULC
        
    Returns:
        dict: Mapping of scenario names to processed file paths
    """
    
    scenarios_dir = Path(scenarios_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Find all TIFF files
    scenario_files = list(scenarios_dir.glob("*.tif"))
    
    if not scenario_files:
        raise ValueError(f"No TIFF files found in {scenarios_dir}")
    
    print(f"Found {len(scenario_files)} scenarios to preprocess")
    
    results = {}
    
    for scenario_file in scenario_files:
        scenario_name = scenario_file.stem
        scenario_output_dir = output_dir / scenario_name
        
        try:
            result_paths = preprocess_uk_scenario(
                scenario_file, 
                scenario_output_dir, 
                scenario_name,
                baseline_lulc_path
            )
            results[scenario_name] = result_paths
            
        except Exception as e:
            print(f"❌ Error processing {scenario_name}: {e}")
            continue
    
    print(f"\n✓ Batch preprocessing complete: {len(results)}/{len(scenario_files)} scenarios processed")
    return results

if __name__ == "__main__":
    # Test preprocessing with a single UK scenario
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python uk_scenario_preprocessor.py <scenario.tif> <output_dir> [baseline_lulc.tif]")
        sys.exit(1)
    
    scenario_file = sys.argv[1]
    output_directory = sys.argv[2]
    baseline_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    scenario_name = Path(scenario_file).stem
    
    result = preprocess_uk_scenario(
        scenario_file,
        output_directory,
        scenario_name,
        baseline_file
    )
    
    print(f"\nProcessed files:")
    for key, path in result.items():
        print(f"  {key}: {path}")