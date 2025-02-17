Input files are PFT.nc and copy_MEGAN2020.nc
The PFT file is regridded from mksrf_landuse_rc2000_c110913.nc, which is here:
~/Projects/landd/AQ-land/bVOCs/PFTmap/
This is the map of the plant functional types, and the MEGAN file is the emissions saved out

The Python scripts isoprene-factor.py, mtpa-factor.py and mtpo-factor.py divide
the emissions by the weighted sum of the emission factors in each grid cell.
The idea is to generate maps of which areas are more or less emissive,
regardless of the PFT emission factors.
