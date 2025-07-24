#!/usr/bin/env python3
"""
Restore original global setup after UK processing

This restores the original grid.tif and land use files
"""

import sys
from pathlib import Path

def main():
    print("🔄 Restoring original global setup...")
    
    try:
        from scenario_scripts.uk_processing_setup import restore_original_files
        
        restore_original_files()
        
        print("✅ Original global setup restored!")
        print("You can now run global processing or setup a different UK scenario.")
        
    except Exception as e:
        print(f"❌ Restore error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()