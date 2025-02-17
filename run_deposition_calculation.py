# run_deposition_calculation.py
from dep_scripts import dep_1_lai_reclass
from dep_scripts import dep_2_lai_month_avg
from dep_scripts import dep_3_velocity
from dep_scripts import dep_4_multiply

inputdir = "/Users/sumilthakrar/UMN/Projects/landd2/pkg"

def main():
    print("Reclassifying leaf area index")
    dep_1_lai_reclass.run(inputdir)
    print("Completed.\n")
    
    print("Calculating monthly averages for leaf area index")
    dep_2_lai_month_avg.run(inputdir)
    print("Completed.\n")
    
    print("Calculating deposition velocities")
    dep_3_velocity.run(inputdir)
    print("Completed.\n")
    
    print("Calculating total PM2.5 deposited from land use")
    dep_4_multiply.run(inputdir)
    print("Completed.\n")

if __name__ == '__main__':
    main()
