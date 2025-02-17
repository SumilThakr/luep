import pygeoprocessing.geoprocessing as geop
import numpy as np
import os
from osgeo import gdal
import math
from datetime import datetime, timedelta

############################################################
###################### Deposition ##########################
############################################################

# Following Nowak et al. (2013)
# Hourly pollution removal, F (mg m-2 hr-1 leaf-1) is estimated as:
# F = Vd * C
# where:
# Vd        deposition velocity of the pollutant to the leaf
#           surface (m hr-1)
# C         pollutant concentration (ug m-3)

# Vd varies with wind speed and tree species
# Some percentage of resuspension occurs, which is also assumed
# to vary with wind speed (and tree species?)
# Note that the percentage resuspended is a percentage of the
# cumulative amount that was deposited since the last big rainfall
# event. So you have to keep track of the stock, not just the flow.
# Resuspension only happens when it's not raining.
# The threshold size for big rainfall events is 0.2 * LAI.
# Also modelled are evaporation rates to see how the water on the
# leaves changes over time (evaporation is based on meteorological
# conditions.)
# [how is evaporation calculated? It doesn't say.]
# The total flux to leaves = pollution on leaves + washed off

# Pollutant removal per land area is estimated by multiplying
# F by the total leaf surface area (m2).

# The only reason why you need to model the water is ultimately
# to estimate the resuspension. For now, consider applying a flat
# percentage to the resuspension. That greatly simplifies the modelling.

# In that case, the only data needed are the following:
# - concentrations of pollutants (PM2.5)
#       This is available from here:
#       https://zenodo.org/records/10800980
# - deposition velocities by wind speed
#       The Nowak paper should have these
# - land-use-derived maps of vegetation
#       I think these can be made consistent with bVOC or something
#       Note that we can use average deposition velocities across species
# - wind speeds
#       I think I have these from MERRA2
# - total leaf surface area (related to LAI?)

wdir                = "./"


#Table 3
#Deposition velocities and percent resuspension by wind speed per unit leaf area.
#Wind speed (m/s)   Deposition velocity (cm s-1)    Resuspension (%)
#                    Avg     Max     Min             
#0                   0.00    0.000   0.000           0
#1                   0.03    0.006   0.042           1.5
#2                   0.09    0.012   0.163           3
#3                   0.15    0.018   0.285           4.5
#4                   0.17    0.022   0.349           6
#5                   0.19    0.025   0.414           7.5
#6                   0.20    0.029   0.478           9
#7                   0.56    0.056   1.506           10
#8                   0.92    0.082   2.534           11
#9                   0.92    0.082   2.534           12
#10                  2.11    0.570   7.367           13
#11                  2.11    0.570   7.367           16
#12                  2.11    0.570   7.367           20
#13                  2.11    0.570   7.367           23
# (Shouldn't max and min be swapped?)

############################################################
# 1         PM2.5 Concentrations
############################################################

# Read from data
# The inputs are of the format: 'GHAP_PM2.5_M1K_YYYYMM_V1.nc'
# Read all the inputs
'/inputs/concentrations/GHAP_PM2.5_M1K_202101_V1.nc'
# Note that these are monthly

############################################################
# 2         Wind Speeds
############################################################

# Read from data (see run_dust script)
# These are hourly

# Calculate deposition velocities and resuspension per unit
# leaf area at each time step
# multiply these by the concentrations at each time step
# that gets you the deposition per LAI

############################################################
# 3         Leaf Area Index
############################################################

# I have another script, lai_for_dep.py, that calculates the
# LAI averages for 1x1 degree tiles globally (replacing with
# the global average where there are none of that land-use)
# for 4 simple land-use classes: other, crops, grasslands, and
# forest.

lu_raster      = [(os.path.join(wdir,'inputs', 'test_data', 'gblulcg20.tif'),1)]

# Then, the land-use can be read and the derived LAI can be
# multiplied to get the total deposition.
