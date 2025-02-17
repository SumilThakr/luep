import pygeoprocessing.geoprocessing as geop
import numpy as np
import os
from osgeo import gdal
import math

############################################################
############### Windblown dust emissions ###################
############################################################

# We want to implement the model of Mansell et al. (2006),
# described in:
# https://www.wrapair2.org/pdf/Memo6_Dust_Mar11_2013review_draft.pdf

# This takes as inputs:
# Land use/ Land cover from 2000 NLCD
#   This should be harmonized with the soilnox inputs and user inputs eventually
# Soil texture from STATSGO soils database (Penn State)
#   This is just available for the US. Let's use some global soil type data
# Meteorology from Penn State/NCAR MM5 model simulations
#   We just want wind speed at 10m.
#       [Something I'm wondering: If you change the surface roughness through changing
#       the land use, then will the UZ change as well? i.e. is this the right way to
#       parameterize the land use through the surface roughness?]
# Fugitive dust transport fractions from Pace et al. 2005

# I want to implement this globally, for different land use types.

# Using IGBP inputs (same as with soil NOx), we can make a mapping.
#Value  Code        Class Name                                      Map
#1      100         Urban and Built-Up Land                         Urban
#2      211         Dryland Cropland and Pasture                    Agricultural
#3      212         Irrigated Cropland and Pasture                  Agricultural
#4      213         Mixed Dryland/Irrigated Cropland and Pasture    Agricultural
#5      280         Cropland/Grassland Mosaic                       Agricultural
#6      290         Cropland/Woodland Mosaic                        Agricultural
#7      311         Grassland                                       Grassland
#8      321         Shrubland                                       Scrubland
#9      330         Mixed Shrubland/Grassland                       Scrubland
#10     332         Savanna                                         Barren
#11     411         Deciduous Broadleaf Forest                      Forest
#12     412         Deciduous Needleleaf Forest                     Forest
#13     421         Evergreen Broadleaf Forest                      Forest
#14     422         Evergreen Needleleaf Forest                     Forest
#15     430         Mixed Forest                                    Forest
#16     500         Water Bodies                                    NA
#17     620         Herbaceous Wetland                              NA
#18     610         Wooded Wetland                                  NA
#19     770         Barren or Sparsely Vegetated                    Barren
#20     820         Herbaceous Tundra                               Scrubland
#21     810         Wooded Tundra                                   Scrubland
#22     850         Mixed Tundra                                    Scrubland
#23     830         Bare Ground Tundra                              Barren
#24     900         Snow or Ice                                     NA
#100                NO DATA                                         NA



# The following table is used to parameterise the model for
# each land use classification:
# LULC          FDTF        DISTURBED       Z0 (CM)
# Barren        1.0         Undisturbed     0.0020
# Agricultural  0.75        Disturbed       0.0310
# Grassland     0.75        Undisturbed     0.1000
# Scrubland     0.75        Undisturbed     0.0500
# Forest        0.0         Undisturbed     50.0
# Urban         0.0         Undisturbed     50.0

# The disturbance levels would affect things (I think through the surface
# roughness and threshold surface friction velocities?) but we don't consider
# that here.

# FDTF: fugitive dust transport factors

# uz/ustar = (1/k) * ln(z/z0)
# where:
# uz    = wind speed at height z (m/s)
# k     = von Kármán's constant (0.4)
# ustar = friction velocity (m/s)
# z     = height above ground (m) This is usually 10m
# z0    = aerodynamic roughness height (m)

# We want the Ustar (surface friction velocity) and the soil texture,
# which combined will give us the emission fluxes
# FSS: silt
# FS: sandy silt
# silty sand: MS
# sand: CS
# Here are the emission flux equations (units: g cm-2 s-1)
# FFS:F = 2.45 *10^-6 * ustar^3.97
# FS: F = 9.33 *10^-7 * ustar^2.44
# MS: F = 1.243 *10^-7 * ustar^2.64
# CS: F = 1.24 *10^-7 * ustar^3.44

# The STATSGO soil texture groupings are as follows
# Sand:             CS
# Loamy Sad:        CS
# Sandy Loam:       MS
# Silt Loam:        FS
# Silt:             FSS
# Loam:             MS
# Sandy Clay Loam:  MS
# Silty Clay Loam:  FSS
# Clay Loam:        MS
# Sandy Clay:       MS
# Silty Clay:       FFS
# Clay:             FS

# Precipitation over 2 inches will delay the emissions of dust,
# after a certain time threshold (dependent on soil type), as
# parameterized by Barnard (2003).
# Table 3-1 Number of days after precipitation event to re-initiate
# wind erosion for rainfall amounts (constant) exceeding 2 inches.
# Soil type         Spring/Fall     Summer      Winter      Avg
# Sand              3               2.1         4.2         3.1
# Sandy Loam        3               2.1         4.2         3.1
# Fine Sand Loam    3               2.1         4.2         3.1
# Loam              4               2.9         3.8         3.6
# Silt Loam         4               2.9         3.8         3.6
# Sandy Clay Loam   4               2.9         3.8         3.6
# Clay Loam         5               3.6         7.2         5.3
# Silty Clay Loam   6               4.3         8.6         6.3
# Clay              7               5           10          7.3

# Table 3-2 Number of days after precipitation event to re-initiate
# wind erosion for rainfall amounts (constant) less than or equal to
# 2 inches.
# Soil type         Spring/Fall     Summer      Winter      Avg
# Sand              1               0.7         1.4         1.0
# Sandy Loam        1               0.7         1.4         1.0
# Fine Sand Loam    1               0.7         1.4         1.0
# Loam              2               1.4         2.8         2.1
# Silt Loam         2               1.4         2.8         2.1
# Sandy Clay Loam   2               1.4         2.8         2.1
# Clay Loam         3               2           4           3
# Silty Clay Loam   4               2.8         5.6         4.1
# Clay              5               3.6         7.2         5.3


# 0.78 = PM2.5:PM10 ratio.

# Here are the coefficients used (Table 3)
#Variables	Effect	Standard Error	t Value	Pr > |t|
#Constant	-1.8327	0.1148	-15.97	<.0001
#Nrate	0.03545	0.01407	2.52	0.0135
#Land covera				
#    1	1.1526	0.6767	1.7	0.0919
#    2	0.1245	0.4554	0.27	0.7852
#    4	0.1681	0.5272	0.32	0.7505
#    5	0.3378	0.9537	0.35	0.724
#    6	-0.9765	0.4708	-2.07	0.0409
#    9	0.2532	0.3591	0.71	0.4825
#   10	-0.02383	0.3344	-0.07	0.9434
#   11	-0.8936	1.1932	-0.75	0.4558
#   12	0.6214	0.3418	1.82	0.0724
#   16	-0.3035	0.9738	-0.31	0.756
#Climate				
# Tropics	0.2932	0.2224	1.32	0.1908
# Dry	0.9352	0.2945	3.18	0.002
# Temperate	0.4774	0.2583	1.85	0.0679
# Cold	-0.09843	0.353	-0.28	0.781
#SOC				
#  <0.6%	-0.4376	0.7424	-0.59	0.557
#  >0.6-1.2%	-0.2734	0.1374	-1.86	0.0391
#  >1.2-2%	-0.2334	0.2891	-0.81	0.4216
#  >2%	-0.06834	0.3083	-0.22	0.8251

#aIGBP land-cover type: 1, evergreen needleleaf forest;
# 2, evergreen broadleaf forest; 4, deciduous broadleaf forest;
# 5, mixed forest; 6, closed shrublands; 9, savannas;
# 10, Grasslands; 11, permanent wetlands; 12, croplands;
# 16, barren or sparsely vegetated.
