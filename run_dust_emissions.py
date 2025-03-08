# run_dust_emissions.py
from dust_scripts import dust_1_soil_texture
from dust_scripts import dust_2_flux_calc
from dust_scripts import dust_3_sum

# inputdir = "/Users/sumilthakrar/UMN/Projects/landd2/pkg" # sumil local
inputdir = "G:/Shared drives/NatCapTEEMs/Files/base_data/submissions/air_quality" # teems drive

def main():
    print("Finding soil texture")
    dust_1_soil_texture.run(inputdir)
    print("Completed.\n")
    
    print("Calculating dust fluxes")
    dust_2_flux_calc.run(inputdir)
    print("Completed.\n")
    
    print("Calculating total dust emissions")
    dust_3_sum.run(inputdir)
    print("Completed.\n")
    
if __name__ == '__main__':
    main()
