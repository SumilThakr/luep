#!/usr/bin/env python3
"""
Verify that our ESA mapping covers all codes found in UK scenarios
"""

from create_esa_mapping import create_esa_to_simple_mapping

def main():
    # Codes found in UK scenarios (from our examination)
    uk_scenario_codes = [0, 10, 11, 12, 30, 34, 35, 39, 40, 44, 49, 60, 65, 70, 75, 80, 85, 90, 95, 100, 104, 105, 109, 110, 114, 115, 119, 120, 124, 130, 134, 150, 154, 180, 184, 190, 200, 201, 202, 204, 205, 206, 210]
    
    # Our mapping
    esa_to_simple, esa_codes = create_esa_to_simple_mapping()
    
    print("Verification of UK Scenario Code Coverage")
    print("=" * 50)
    print(f"Total codes in UK scenarios: {len(uk_scenario_codes)}")
    print(f"Total codes in our mapping: {len(esa_to_simple)}")
    
    # Check coverage
    mapped_codes = set(esa_to_simple.keys())
    uk_codes = set(uk_scenario_codes)
    
    covered = uk_codes.intersection(mapped_codes)
    missing = uk_codes - mapped_codes
    
    print(f"\nCodes covered by our mapping: {len(covered)}/{len(uk_codes)}")
    print(f"Coverage percentage: {len(covered)/len(uk_codes)*100:.1f}%")
    
    if missing:
        print(f"\nMISSING CODES IN UK SCENARIOS:")
        print("-" * 30)
        for code in sorted(missing):
            print(f"  {code}: (Unknown - not in standard ESA CCI)")
    else:
        print("\n✓ All UK scenario codes are covered by our mapping!")
    
    # Show distribution of Simple classes for UK codes
    print(f"\nSimple Class Distribution for UK Scenario Codes:")
    print("-" * 50)
    
    simple_names = {0: "Other", 1: "Cropland", 2: "Grass", 3: "Forest"}
    class_counts = {0: 0, 1: 0, 2: 0, 3: 0}
    
    for code in covered:
        simple_class = esa_to_simple[code]
        class_counts[simple_class] += 1
    
    for simple_id, count in class_counts.items():
        percentage = count / len(covered) * 100
        print(f"{simple_names[simple_id]:>8} ({simple_id}): {count:2d} codes ({percentage:4.1f}%)")
    
    # Show which specific codes fall into each category
    print(f"\nDetailed Code Assignment:")
    print("-" * 30)
    
    for simple_id in [0, 1, 2, 3]:
        uk_codes_for_class = [code for code in covered if esa_to_simple[code] == simple_id]
        uk_codes_for_class.sort()
        print(f"{simple_names[simple_id]} ({simple_id}): {uk_codes_for_class}")

if __name__ == "__main__":
    main()