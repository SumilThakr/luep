#!/usr/bin/env python3
"""
Create ESA CCI to Simple classification mapping based on the actual codes found in UK scenarios
"""

def create_esa_to_simple_mapping():
    """
    Create mapping from ESA CCI codes to Simple 4-class system:
    0 = Other (water, urban, bare, ice, no data)
    1 = Cropland (all agricultural/crop types)  
    2 = Grass (grassland, shrubland, sparse vegetation, wetlands)
    3 = Forest (all tree cover types)
    """
    
    # ESA CCI codes found in UK scenarios with their descriptions
    esa_codes = {
        0: "No Data",
        10: "Cropland, rainfed",
        11: "Herbaceous cover", 
        12: "Tree or shrub cover",
        20: "Cropland, irrigated or post‐flooding",
        30: "Mosaic cropland (>50%) / natural vegetation (<50%)",
        40: "Mosaic natural vegetation (>50%) / cropland (<50%)",
        50: "Tree cover, broadleaved, evergreen, closed to open (>15%)",
        60: "Tree cover, broadleaved, deciduous, closed to open (>15%)",
        61: "Tree cover, broadleaved, deciduous, closed (>40%)",
        62: "Tree cover, broadleaved, deciduous, open (15‐40%)",
        70: "Tree cover, needleleaved, evergreen, closed to open (>15%)",
        71: "Tree cover, needleleaved, evergreen, closed (>40%)",
        72: "Tree cover, needleleaved, evergreen, open (15‐40%)",
        80: "Tree cover, needleleaved, deciduous, closed to open (>15%)",
        81: "Tree cover, needleleaved, deciduous, closed (>40%)",
        82: "Tree cover, needleleaved, deciduous, open (15‐40%)",
        90: "Tree cover, mixed leaf type (broadleaved and needleleaved)",
        100: "Mosaic tree and shrub (>50%) / herbaceous cover (<50%)",
        110: "Mosaic herbaceous cover (>50%) / tree and shrub (<50%)",
        120: "Shrubland",
        121: "Evergreen shrubland",
        122: "Deciduous shrubland",
        130: "Grassland",
        140: "Lichens and mosses",
        150: "Sparse vegetation (tree, shrub, herbaceous cover) (<15%)",
        151: "Sparse tree (<15%)",
        152: "Sparse shrub (<15%)",
        153: "Sparse herbaceous cover (<15%)",
        160: "Tree cover, flooded, fresh or brakish water",
        170: "Tree cover, flooded, saline water",
        180: "Shrub or herbaceous cover, flooded, fresh/saline/brakish water",
        190: "Urban areas",
        200: "Bare areas",
        201: "Consolidated bare areas", 
        202: "Unconsolidated bare areas",
        210: "Water bodies",
        220: "Permanent snow and ice"
    }
    
    # Mapping to Simple 4-class system
    esa_to_simple = {
        # No Data / Other
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
        
        # Grass/Shrubland (2) - herbaceous, shrub, sparse, wetlands
        11: 2,   # Herbaceous cover
        40: 2,   # Mosaic natural vegetation (>50%) / cropland (<50%) - more natural
        110: 2,  # Mosaic herbaceous cover (>50%) / tree and shrub (<50%)
        120: 2,  # Shrubland
        121: 2,  # Evergreen shrubland
        122: 2,  # Deciduous shrubland
        130: 2,  # Grassland
        140: 2,  # Lichens and mosses
        150: 2,  # Sparse vegetation (tree, shrub, herbaceous cover) (<15%)
        152: 2,  # Sparse shrub (<15%)
        153: 2,  # Sparse herbaceous cover (<15%)
        180: 2,  # Shrub or herbaceous cover, flooded
        
        # Forest (3) - all tree cover types
        12: 3,   # Tree or shrub cover (assuming more tree than shrub)
        50: 3,   # Tree cover, broadleaved, evergreen, closed to open (>15%)
        60: 3,   # Tree cover, broadleaved, deciduous, closed to open (>15%)
        61: 3,   # Tree cover, broadleaved, deciduous, closed (>40%)
        62: 3,   # Tree cover, broadleaved, deciduous, open (15‐40%)
        70: 3,   # Tree cover, needleleaved, evergreen, closed to open (>15%)
        71: 3,   # Tree cover, needleleaved, evergreen, closed (>40%)
        72: 3,   # Tree cover, needleleaved, evergreen, open (15‐40%)
        80: 3,   # Tree cover, needleleaved, deciduous, closed to open (>15%)
        81: 3,   # Tree cover, needleleaved, deciduous, closed (>40%)
        82: 3,   # Tree cover, needleleaved, deciduous, open (15‐40%)
        90: 3,   # Tree cover, mixed leaf type
        100: 3,  # Mosaic tree and shrub (>50%) / herbaceous cover (<50%)
        151: 3,  # Sparse tree (<15%)
        160: 3,  # Tree cover, flooded, fresh or brakish water
        170: 3,  # Tree cover, flooded, saline water
    }
    
    return esa_to_simple, esa_codes

def print_mapping_summary():
    """Print a summary of the mapping for verification"""
    mapping, codes = create_esa_to_simple_mapping()
    
    print("ESA CCI to Simple Classification Mapping")
    print("=" * 50)
    
    # Group by Simple class
    simple_classes = {0: "Other", 1: "Cropland", 2: "Grass", 3: "Forest"}
    
    for simple_id in [0, 1, 2, 3]:
        print(f"\n{simple_classes[simple_id]} ({simple_id}):")
        print("-" * 20)
        
        esa_codes_for_class = [esa for esa, simple in mapping.items() if simple == simple_id]
        esa_codes_for_class.sort()
        
        for esa_code in esa_codes_for_class:
            description = codes.get(esa_code, "Unknown")
            print(f"  {esa_code:3d}: {description}")
    
    print(f"\nTotal ESA codes mapped: {len(mapping)}")
    print(f"Total ESA codes available: {len(codes)}")
    
    # Check for unmapped codes
    unmapped = set(codes.keys()) - set(mapping.keys())
    if unmapped:
        print(f"\nUnmapped ESA codes: {sorted(unmapped)}")
        for code in sorted(unmapped):
            print(f"  {code}: {codes[code]}")

def save_mapping_csv():
    """Save the mapping to a CSV file"""
    import csv
    
    mapping, codes = create_esa_to_simple_mapping()
    
    filename = "inputs/ESA_CCI_to_Simple_mapping.csv"
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['ESA_CCI_Code', 'ESA_Description', 'Simple_Class', 'Simple_Description'])
        
        simple_names = {0: "Other", 1: "Cropland", 2: "Grass", 3: "Forest"}
        
        for esa_code in sorted(codes.keys()):
            esa_desc = codes[esa_code]
            simple_class = mapping.get(esa_code, -1)  # -1 for unmapped
            simple_desc = simple_names.get(simple_class, "Unmapped")
            
            writer.writerow([esa_code, esa_desc, simple_class, simple_desc])
    
    print(f"\nMapping saved to: {filename}")

if __name__ == "__main__":
    print_mapping_summary()
    save_mapping_csv()