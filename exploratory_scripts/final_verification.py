#!/usr/bin/env python3
"""
Final verification that complete mapping covers all UK scenario codes
"""

from create_complete_uk_mapping import create_complete_uk_mapping

def main():
    # Codes found in UK scenarios 
    uk_scenario_codes = [0, 10, 11, 12, 30, 34, 35, 39, 40, 44, 49, 60, 65, 70, 75, 80, 85, 90, 95, 100, 104, 105, 109, 110, 114, 115, 119, 120, 124, 130, 134, 150, 154, 180, 184, 190, 200, 201, 202, 204, 205, 206, 210]
    
    # Our complete mapping
    complete_mapping = create_complete_uk_mapping()
    
    print("Final Verification of UK Scenario Code Coverage")
    print("=" * 55)
    print(f"Total codes in UK scenarios: {len(uk_scenario_codes)}")
    print(f"Total codes in complete mapping: {len(complete_mapping)}")
    
    # Check coverage
    mapped_codes = set(complete_mapping.keys())
    uk_codes = set(uk_scenario_codes)
    
    covered = uk_codes.intersection(mapped_codes)
    missing = uk_codes - mapped_codes
    
    print(f"\nCodes covered: {len(covered)}/{len(uk_codes)}")
    print(f"Coverage: {len(covered)/len(uk_codes)*100:.1f}%")
    
    if missing:
        print(f"\nSTILL MISSING:")
        for code in sorted(missing):
            print(f"  {code}")
    else:
        print("\n✓ ALL UK SCENARIO CODES ARE NOW COVERED!")
    
    # Final distribution
    simple_names = {0: "Other", 1: "Cropland", 2: "Grass", 3: "Forest"}
    class_counts = {0: 0, 1: 0, 2: 0, 3: 0}
    
    for code in uk_scenario_codes:
        simple_class = complete_mapping[code]
        class_counts[simple_class] += 1
    
    print(f"\nFinal Simple Class Distribution for UK:")
    print("-" * 40)
    for simple_id, count in class_counts.items():
        percentage = count / len(uk_scenario_codes) * 100
        print(f"{simple_names[simple_id]:>8} ({simple_id}): {count:2d} codes ({percentage:4.1f}%)")
    
    print(f"\nMapping is ready for UK scenario processing! 🎉")

if __name__ == "__main__":
    main()