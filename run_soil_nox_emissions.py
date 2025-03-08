# run_soil_nox_emissions.py
from soil_nox_scripts import soil_nox_1_time_varying
from soil_nox_scripts import soil_nox_2_time_varying_sum
from soil_nox_scripts import soil_nox_3_constant
from soil_nox_scripts import soil_nox_4_gblulc
from soil_nox_scripts import soil_nox_5_align

# inputdir = "/Users/sumilthakrar/UMN/Projects/landd2/pkg" # sumil local
inputdir = "G:/Shared drives/NatCapTEEMs/Files/base_data/submissions/air_quality" # teems drive

def main():
    print("Calculating time-dependent parameters for soil NOx emissions estimation")
    soil_nox_1_time_varying.run(inputdir)
    print("Completed.\n")
    
    print("Summing time-dependent parameters for soil NOx emissions estimation")
    soil_nox_2_time_varying_sum.run(inputdir)
    print("Completed.\n")
    
    print("Calculating constant parameters for soil NOx emissions estimation")
    soil_nox_3_constant.run(inputdir)
    print("Completed.\n")
    
    print("Reprojecting and aligning parameters and calculating soil NOx emissions")
    soil_nox_4_gblulc.run(inputdir)
    soil_nox_5_align.run(inputdir)
    print("Completed.\n")

if __name__ == '__main__':
    main()
