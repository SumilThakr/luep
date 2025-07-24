# run_dust_emissions_land_use_dependent_only.py
from dust_scripts import dust_2_flux_calc
from dust_scripts import dust_3_sum

# inputdir = "/Users/sumilthakrar/UMN/Projects/landd2/pkg" # sumil local
# inputdir = "G:/Shared drives/NatCapTEEMs/Files/base_data/submissions/air_quality" # teems drive
inputdir = "." # current directory (contains inputs folder)

def main():
    print("=== LAND USE DEPENDENT DUST EMISSIONS CALCULATION ===")
    print("Skipping soil texture (already processed - not land-use dependent)")
    print("Running only the land-use dependent components:\n")
    
    print("Calculating dust fluxes (ESA-CCI land use → dust parameters → daily fluxes)")
    dust_2_flux_calc.run(inputdir)
    print("Completed.\n")
    
    print("Calculating total dust emissions (summing daily fluxes)")
    dust_3_sum.run(inputdir)
    print("Completed.\n")
    
    print("=== DUST EMISSIONS CALCULATION COMPLETE ===")
    print("Output: outputs/dust_sum.tiff")
    
if __name__ == '__main__':
    main()