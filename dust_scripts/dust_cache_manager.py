#!/usr/bin/env python3
"""
Dust Processing Cache Manager

Implements smart caching for meteorology and shared resources to dramatically
speed up multi-scenario processing.
"""

import os
import glob
import shutil
from pathlib import Path
from datetime import datetime
import hashlib

class DustProcessingCache:
    """
    Manages caching for dust processing to optimize multi-scenario runs
    """
    
    def __init__(self, cache_dir="cache/dust/"):
        self.cache_dir = Path(cache_dir)
        self.meteorology_cache = self.cache_dir / "meteorology"
        self.soil_cache = self.cache_dir / "soil"
        self.grid_cache = self.cache_dir / "grids"
        
        # Create cache directories
        for cache_path in [self.meteorology_cache, self.soil_cache, self.grid_cache]:
            cache_path.mkdir(parents=True, exist_ok=True)
    
    def get_meteorology_cache_key(self, year=2021):
        """Generate cache key for meteorology data"""
        return f"meteorology_{year}"
    
    def is_meteorology_cached(self, year=2021):
        """Check if meteorology for given year is fully cached"""
        
        cache_key = self.get_meteorology_cache_key(year)
        cache_path = self.meteorology_cache / cache_key
        
        if not cache_path.exists():
            return False
        
        # Check for expected number of files (daily files from May 2 - Dec 31)
        # That's 244 days × 2 files (wind + soil moisture) = 488 files minimum
        cached_files = list(cache_path.glob("*.tif"))
        expected_min_files = 400  # Conservative estimate
        
        return len(cached_files) >= expected_min_files
    
    def cache_meteorology(self, source_dir="intermediate/daily_meteorology/", year=2021):
        """Cache meteorology data for reuse across scenarios"""
        
        print(f"📦 Caching meteorology data for {year}...")
        
        cache_key = self.get_meteorology_cache_key(year)
        cache_path = self.meteorology_cache / cache_key
        cache_path.mkdir(exist_ok=True)
        
        # Find all meteorology files
        source_path = Path(source_dir)
        if not source_path.exists():
            print(f"  ❌ Source meteorology directory not found: {source_path}")
            return False
        
        # Cache wind speed files
        ws_files = list(source_path.glob("ws_aligned_*.tif"))
        sm_files = list(source_path.glob("sm_aligned*.tif"))
        
        cached_count = 0
        
        for file_list, file_type in [(ws_files, "wind"), (sm_files, "soil_moisture")]:
            for src_file in file_list:
                dst_file = cache_path / src_file.name
                if not dst_file.exists():
                    shutil.copy2(src_file, dst_file)
                    cached_count += 1
        
        print(f"  ✅ Cached {cached_count} meteorology files to: {cache_path}")
        return True
    
    def restore_cached_meteorology(self, target_dir="intermediate/", year=2021):
        """Restore cached meteorology to processing directory"""
        
        cache_key = self.get_meteorology_cache_key(year)
        cache_path = self.meteorology_cache / cache_key
        
        if not cache_path.exists():
            print(f"  ❌ No cached meteorology found for {year}")
            return False
        
        target_path = Path(target_dir)
        target_path.mkdir(exist_ok=True)
        
        cached_files = list(cache_path.glob("*.tif"))
        restored_count = 0
        
        for src_file in cached_files:
            dst_file = target_path / src_file.name
            if not dst_file.exists():
                shutil.copy2(src_file, dst_file)
                restored_count += 1
        
        print(f"  ✅ Restored {restored_count} cached meteorology files")
        return True
    
    def get_soil_cache_key(self):
        """Generate cache key for soil texture data"""
        return "global_soil_texture"
    
    def is_soil_cached(self):
        """Check if soil texture is cached"""
        cache_key = self.get_soil_cache_key()
        cache_path = self.soil_cache / f"{cache_key}.tif"
        return cache_path.exists()
    
    def cache_soil_texture(self, source_file="intermediate/aligned_soil_texture.tif"):
        """Cache aligned soil texture"""
        
        if not os.path.exists(source_file):
            return False
        
        cache_key = self.get_soil_cache_key()
        cache_path = self.soil_cache / f"{cache_key}.tif"
        
        shutil.copy2(source_file, cache_path)
        print(f"  ✅ Cached soil texture: {cache_path}")
        return True
    
    def restore_cached_soil_texture(self, target_file="intermediate/aligned_soil_texture.tif"):
        """Restore cached soil texture"""
        
        cache_key = self.get_soil_cache_key()
        cache_path = self.soil_cache / f"{cache_key}.tif"
        
        if not cache_path.exists():
            return False
        
        # Ensure target directory exists
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        
        shutil.copy2(cache_path, target_file)
        print(f"  ✅ Restored cached soil texture: {target_file}")
        return True
    
    def get_grid_cache_key(self, grid_file="grid.tif"):
        """Generate cache key based on grid file characteristics"""
        
        if not os.path.exists(grid_file):
            return None
        
        # Create hash based on grid file properties
        import pygeoprocessing.geoprocessing as geop
        
        try:
            grid_info = geop.get_raster_info(grid_file)
            properties = f"{grid_info['raster_size']}_{grid_info['pixel_size']}_{grid_info['bounding_box']}"
            cache_key = hashlib.md5(properties.encode()).hexdigest()[:16]
            return f"grid_{cache_key}"
        except:
            return None
    
    def cache_processing_setup(self, scenario_name, force=False):
        """Cache the current processing setup for a scenario"""
        
        cache_key = self.get_grid_cache_key()
        if not cache_key:
            return False
        
        scenario_cache = self.grid_cache / cache_key / scenario_name
        scenario_cache.mkdir(parents=True, exist_ok=True)
        
        # Cache key files
        files_to_cache = {
            "grid.tif": "grid.tif",
            "inputs/gblulcg20_10000.tif": "gblulcg20_10000.tif",
            "intermediate/z0_effect_dust.tif": "z0_effect_dust.tif",
            "intermediate/aligned_z0.tif": "aligned_z0.tif"
        }
        
        cached_count = 0
        for src_path, cache_name in files_to_cache.items():
            if os.path.exists(src_path):
                cache_file = scenario_cache / cache_name
                if force or not cache_file.exists():
                    shutil.copy2(src_path, cache_file)
                    cached_count += 1
        
        if cached_count > 0:
            print(f"  ✅ Cached {cached_count} setup files for {scenario_name}")
        
        return True
    
    def restore_processing_setup(self, scenario_name):
        """Restore cached processing setup for a scenario"""
        
        cache_key = self.get_grid_cache_key("cache/dust/grids/*/grid.tif")  # Find any cached grid
        if not cache_key:
            # Try to find any cached scenario
            grid_dirs = list(self.grid_cache.glob("grid_*"))
            if not grid_dirs:
                return False
            cache_key = grid_dirs[0].name
        
        scenario_cache = self.grid_cache / cache_key / scenario_name
        
        if not scenario_cache.exists():
            return False
        
        # Restore files
        files_to_restore = {
            "grid.tif": "grid.tif",
            "gblulcg20_10000.tif": "inputs/gblulcg20_10000.tif",
            "z0_effect_dust.tif": "intermediate/z0_effect_dust.tif",
            "aligned_z0.tif": "intermediate/aligned_z0.tif"
        }
        
        restored_count = 0
        for cache_name, target_path in files_to_restore.items():
            cache_file = scenario_cache / cache_name
            if cache_file.exists():
                # Ensure target directory exists
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(cache_file, target_path)
                restored_count += 1
        
        if restored_count > 0:
            print(f"  ✅ Restored {restored_count} setup files for {scenario_name}")
        
        return restored_count > 0
    
    def clear_cache(self, cache_type="all"):
        """Clear specified cache type"""
        
        if cache_type in ["all", "meteorology"]:
            shutil.rmtree(self.meteorology_cache, ignore_errors=True)
            self.meteorology_cache.mkdir(parents=True, exist_ok=True)
            print("  🗑️  Cleared meteorology cache")
        
        if cache_type in ["all", "soil"]:
            shutil.rmtree(self.soil_cache, ignore_errors=True)
            self.soil_cache.mkdir(parents=True, exist_ok=True)
            print("  🗑️  Cleared soil cache")
        
        if cache_type in ["all", "grid"]:
            shutil.rmtree(self.grid_cache, ignore_errors=True)
            self.grid_cache.mkdir(parents=True, exist_ok=True)
            print("  🗑️  Cleared grid cache")
    
    def get_cache_stats(self):
        """Get cache statistics"""
        
        stats = {
            "meteorology_files": len(list(self.meteorology_cache.rglob("*.tif"))),
            "soil_files": len(list(self.soil_cache.rglob("*.tif"))),
            "grid_scenarios": len(list(self.grid_cache.rglob("*"))),
            "cache_size_mb": self._get_directory_size(self.cache_dir)
        }
        
        return stats
    
    def _get_directory_size(self, directory):
        """Calculate directory size in MB"""
        total = 0
        try:
            for path in Path(directory).rglob("*"):
                if path.is_file():
                    total += path.stat().st_size
        except:
            pass
        return round(total / (1024 * 1024), 1)

def main():
    """Test cache functionality"""
    
    cache = DustProcessingCache()
    
    print("Dust Processing Cache Manager")
    print("=" * 40)
    
    # Cache statistics
    stats = cache.get_cache_stats()
    print(f"Cache statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Check meteorology cache
    if cache.is_meteorology_cached():
        print("✅ Meteorology is cached")
    else:
        print("❌ Meteorology not cached")
    
    # Check soil cache
    if cache.is_soil_cached():
        print("✅ Soil texture is cached")
    else:
        print("❌ Soil texture not cached")

if __name__ == "__main__":
    main()