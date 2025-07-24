#!/usr/bin/env python3
"""
Create complete mapping for UK scenarios including the non-standard codes
"""

def create_complete_uk_mapping():
    """
    Create mapping that covers ALL codes found in UK scenarios.
    For non-standard codes, make reasonable assumptions based on similar standard codes.
    """
    
    # Start with standard ESA CCI mapping
    standard_mapping = {
        # Other (0)
        0: 0,    # No Data
        190: 0,  # Urban areas 
        200: 0,  # Bare areas
        201: 0,  # Consolidated bare areas
        202: 0,  # Unconsolidated bare areas
        210: 0,  # Water bodies
        220: 0,  # Permanent snow and ice
        
        # Cropland (1)
        10: 1,   # Cropland, rainfed
        20: 1,   # Cropland, irrigated or post‐flooding
        30: 1,   # Mosaic cropland (>50%) / natural vegetation (<50%)
        
        # Grass/Shrubland (2)
        11: 2,   # Herbaceous cover
        40: 2,   # Mosaic natural vegetation (>50%) / cropland (<50%)
        110: 2,  # Mosaic herbaceous cover (>50%) / tree and shrub (<50%)
        120: 2,  # Shrubland
        130: 2,  # Grassland
        140: 2,  # Lichens and mosses
        150: 2,  # Sparse vegetation
        180: 2,  # Shrub or herbaceous cover, flooded
        
        # Forest (3)
        12: 3,   # Tree or shrub cover
        50: 3,   # Tree cover, broadleaved, evergreen
        60: 3,   # Tree cover, broadleaved, deciduous
        70: 3,   # Tree cover, needleleaved, evergreen
        80: 3,   # Tree cover, needleleaved, deciduous
        90: 3,   # Tree cover, mixed leaf type
        100: 3,  # Mosaic tree and shrub (>50%)
        160: 3,  # Tree cover, flooded, fresh water
        170: 3,  # Tree cover, flooded, saline water
    }
    
    # Add reasonable assumptions for non-standard codes found in UK scenarios
    custom_mapping = {
        # Likely variants of cropland/agriculture (30s range)
        34: 1,   # Assumed: Cropland variant
        35: 1,   # Assumed: Cropland variant  
        39: 1,   # Assumed: Cropland variant
        
        # Likely variants of mixed vegetation (40s range)  
        44: 2,   # Assumed: Mixed vegetation variant (more grassland)
        49: 2,   # Assumed: Mixed vegetation variant
        
        # Likely variants of forest types (60s, 70s, 80s, 90s ranges)
        65: 3,   # Assumed: Forest variant (near 60 - broadleaved deciduous)
        75: 3,   # Assumed: Forest variant (near 70 - needleleaved evergreen)  
        85: 3,   # Assumed: Forest variant (near 80 - needleleaved deciduous)
        95: 3,   # Assumed: Forest variant (near 90 - mixed)
        
        # Likely variants of mosaic vegetation (100s range)
        104: 3,  # Assumed: Tree/shrub mosaic variant (near 100)
        105: 3,  # Assumed: Tree/shrub mosaic variant
        109: 2,  # Assumed: Herbaceous mosaic variant (near 110)
        114: 2,  # Assumed: Herbaceous/shrub variant
        115: 2,  # Assumed: Herbaceous/shrub variant
        119: 2,  # Assumed: Shrubland variant (near 120)
        
        # Likely variants of shrubland/grassland (120s, 130s range)
        124: 2,  # Assumed: Shrubland variant (near 120)
        134: 2,  # Assumed: Grassland variant (near 130)
        
        # Likely variants of sparse vegetation (150s range)
        154: 2,  # Assumed: Sparse vegetation variant (near 150)
        
        # Likely variants of wetlands (180s range)  
        184: 2,  # Assumed: Wetland variant (near 180)
        
        # Likely variants of bare areas (200s range)
        204: 0,  # Assumed: Bare area variant (near 200)
        205: 0,  # Assumed: Bare area variant  
        206: 0,  # Assumed: Bare area variant
    }
    
    # Combine mappings
    complete_mapping = {**standard_mapping, **custom_mapping}
    
    return complete_mapping

def create_mapping_descriptions():
    """Create descriptions for the complete mapping"""
    
    descriptions = {
        # Standard codes (abbreviated)
        0: "No Data",
        10: "Cropland, rainfed", 
        11: "Herbaceous cover",
        12: "Tree or shrub cover",
        20: "Cropland, irrigated",
        30: "Mosaic cropland (>50%)",
        40: "Mosaic natural vegetation (>50%)",
        50: "Tree cover, broadleaved, evergreen",
        60: "Tree cover, broadleaved, deciduous", 
        70: "Tree cover, needleleaved, evergreen",
        80: "Tree cover, needleleaved, deciduous",
        90: "Tree cover, mixed leaf type",
        100: "Mosaic tree and shrub (>50%)",
        110: "Mosaic herbaceous cover (>50%)",
        120: "Shrubland",
        130: "Grassland", 
        140: "Lichens and mosses",
        150: "Sparse vegetation",
        160: "Tree cover, flooded, fresh water",
        170: "Tree cover, flooded, saline water",
        180: "Shrub/herbaceous cover, flooded",
        190: "Urban areas",
        200: "Bare areas",
        201: "Consolidated bare areas",
        202: "Unconsolidated bare areas", 
        210: "Water bodies",
        220: "Permanent snow and ice",
        
        # Custom codes (assumptions)
        34: "Cropland variant",
        35: "Cropland variant",
        39: "Cropland variant", 
        44: "Mixed vegetation variant",
        49: "Mixed vegetation variant",
        65: "Forest variant (broadleaved)",
        75: "Forest variant (needleleaved evergreen)",
        85: "Forest variant (needleleaved deciduous)", 
        95: "Forest variant (mixed)",
        104: "Tree/shrub mosaic variant",
        105: "Tree/shrub mosaic variant",
        109: "Herbaceous mosaic variant", 
        114: "Herbaceous/shrub variant",
        115: "Herbaceous/shrub variant",
        119: "Shrubland variant",
        124: "Shrubland variant",
        134: "Grassland variant",
        154: "Sparse vegetation variant",
        184: "Wetland variant", 
        204: "Bare area variant",
        205: "Bare area variant",
        206: "Bare area variant"
    }
    
    return descriptions

def print_complete_mapping():
    """Print the complete mapping summary"""
    
    mapping = create_complete_uk_mapping()
    descriptions = create_mapping_descriptions()
    
    print("Complete UK Scenario ESA CCI Mapping")
    print("=" * 50)
    
    simple_classes = {0: "Other", 1: "Cropland", 2: "Grass", 3: "Forest"}
    
    for simple_id in [0, 1, 2, 3]:
        print(f"\n{simple_classes[simple_id]} ({simple_id}):")
        print("-" * 30)
        
        codes_for_class = [esa for esa, simple in mapping.items() if simple == simple_id]
        codes_for_class.sort()
        
        for esa_code in codes_for_class:
            desc = descriptions.get(esa_code, "Unknown")
            marker = " *" if esa_code in [34,35,39,44,49,65,75,85,95,104,105,109,114,115,119,124,134,154,184,204,205,206] else ""
            print(f"  {esa_code:3d}: {desc}{marker}")
    
    print(f"\nTotal codes mapped: {len(mapping)}")
    print("* = Non-standard code (assumption-based mapping)")

def save_complete_mapping():
    """Save complete mapping to CSV"""
    import csv
    
    mapping = create_complete_uk_mapping()
    descriptions = create_mapping_descriptions()
    
    filename = "inputs/UK_ESA_CCI_to_Simple_mapping.csv"
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['ESA_CCI_Code', 'Description', 'Simple_Class', 'Simple_Name', 'Notes'])
        
        simple_names = {0: "Other", 1: "Cropland", 2: "Grass", 3: "Forest"}
        custom_codes = [34,35,39,44,49,65,75,85,95,104,105,109,114,115,119,124,134,154,184,204,205,206]
        
        for esa_code in sorted(mapping.keys()):
            desc = descriptions.get(esa_code, "Unknown")
            simple_class = mapping[esa_code]
            simple_name = simple_names[simple_class]
            notes = "Non-standard code (assumption-based)" if esa_code in custom_codes else "Standard ESA CCI"
            
            writer.writerow([esa_code, desc, simple_class, simple_name, notes])
    
    print(f"\nComplete mapping saved to: {filename}")

if __name__ == "__main__":
    print_complete_mapping()
    save_complete_mapping()