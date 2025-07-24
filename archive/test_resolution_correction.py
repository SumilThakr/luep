#!/usr/bin/env python3
"""
Test script to validate resolution correction logic
"""

import math

def test_resolution_correction():
    print("=== DUST EMISSIONS RESOLUTION CORRECTION TEST ===")
    print()
    
    # Test parameters
    ustar = 0.3  # m/s (typical friction velocity)
    soiltype = 0  # Mixed Sand (MS)
    
    # Original flux calculation (resolution-dependent)
    def flux_original(ustar, soiltype):
        if soiltype == 0:  # MS
            return 1.243*(10.0 **(-7)) * ustar ** 2.64  # g cm-2 s-1
        return 0.0
    
    # Corrected flux calculation (resolution-independent)
    def flux_corrected(ustar, soiltype, pixel_area_cm2):
        flux_per_cm2 = flux_original(ustar, soiltype)  # g cm-2 s-1
        return flux_per_cm2 * pixel_area_cm2  # g/pixel/s
    
    # Test different resolutions
    resolutions = [
        (0.05, "Global/Coarse"),
        (0.002778, "UK High-Res"),
        (0.001, "Very High-Res")
    ]
    
    print("Testing flux calculations at different resolutions:")
    print("(Same geographic area, different pixel sizes)")
    print()
    
    # Geographic area: 1 degree x 1 degree
    area_deg2 = 1.0  # square degrees
    
    for pixel_size_deg, description in resolutions:
        print(f"--- {description} ({pixel_size_deg}°) ---")
        
        # Calculate pixel area in cm²
        center_lat = 55.0  # UK center
        lat_to_cm = 111000 * 100  # m to cm conversion
        lon_to_cm = 111000 * 100 * math.cos(math.radians(center_lat))
        pixel_area_cm2 = (pixel_size_deg * lon_to_cm) * (pixel_size_deg * lat_to_cm)
        
        # Calculate number of pixels in test area
        pixels_per_degree2 = (1.0 / pixel_size_deg) ** 2
        
        # Original method (resolution-dependent)
        flux_per_cm2 = flux_original(ustar, soiltype)
        total_flux_original = flux_per_cm2 * pixels_per_degree2  # g/s per degree²
        
        # Corrected method (resolution-independent) 
        flux_per_pixel = flux_corrected(ustar, soiltype, pixel_area_cm2)
        total_flux_corrected = flux_per_pixel * pixels_per_degree2  # g/s per degree²
        
        # Geographic area in cm²
        geographic_area_cm2 = (1.0 * lon_to_cm) * (1.0 * lat_to_cm)
        expected_flux = flux_per_cm2 * geographic_area_cm2  # g/s per degree²
        
        print(f"  Pixel size: {pixel_size_deg}°")
        print(f"  Pixel area: {pixel_area_cm2:,.0f} cm²")
        print(f"  Pixels per degree²: {pixels_per_degree2:,.0f}")
        print(f"  Original method: {total_flux_original:.2e} g/s per degree²")
        print(f"  Corrected method: {total_flux_corrected:.2e} g/s per degree²")
        print(f"  Expected (geographic): {expected_flux:.2e} g/s per degree²")
        print(f"  Original vs Expected ratio: {total_flux_original/expected_flux:.1f}x")
        print(f"  Corrected vs Expected ratio: {total_flux_corrected/expected_flux:.3f}x")
        print()
    
    print("INTERPRETATION:")
    print("• Original method gives different results for different resolutions")
    print("• Corrected method gives same result regardless of resolution")
    print("• Resolution-independent results match geographic expectation")

if __name__ == "__main__":
    test_resolution_correction()