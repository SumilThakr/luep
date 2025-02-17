import os
import numpy as np
import netCDF4

# I want to read sumf.nc
#rootgrp = netCDF4.Dataset("./sumf.nc", "r")
#sumf = rootgrp["factor"]

# I want to read isopf, mtpo, and mtpa separately.
rootgrp = netCDF4.Dataset("./isop-factor.nc", "r")
isopf = rootgrp["factor"]

mtpagrp = netCDF4.Dataset("./mtpa-factor.nc", "r")
mtpaf = mtpagrp["factor"]

mtpogrp = netCDF4.Dataset("./mtpo-factor.nc", "r")
mtpof = mtpogrp["factor"]

# Read PFT.nc, specifically the grass and shrubland (PFTs 9-14)
tgrp = netCDF4.Dataset("./PFT.nc", "r")

pft15 = tgrp["PFT15"]

# Isoprene scale factors:
# isop_scale_factors = [600, 3000, 1, 7000, 10000, 7000, 10000, 11000, 2000, 4000, 4000, 1600, 800, 200, 1]
# MTPA scale factors:
# mtpa_scale_factors = [1130, 1130, 960, 920, 690, 920, 690, 690, 440, 720, 440, 5.2, 5.2, 5.2, 5.2]
# MTPO scale factors:
# mtpo_scale_factors = [180, 180, 170, 150, 150, 150, 150, 150, 110, 200, 110, 5, 5, 5, 5]

# Isoprene, Sabinene, Limonene, 3-Carene, β-Pinene, α-Pinene,Other Monoterpenes
# For EF1, EF2, ... the EFs are:
# scale_factors = [1910, 4310, 1131, 8070, 10840, 8070, 10840, 11840, 2550, 4920, 4550, 1610.2, 810.2, 210.2, 11.2]
# We only want E1-E8 here.
# Multiply PFTs by the EFs for all the bVOC precursors (sum):
# Convert from µg m−2 h −1 to kg m-2 yr-1
HoursToYears = 24.0 * 365.0
kgToUg = 1000.0 * 1000.0 * 1000.0
conversion = HoursToYears / kgToUg


# ISOP
isopResult = 1.0 * isopf[:] * conversion 
isopResult.set_fill_value(0.0)
isopResult = isopResult.filled(fill_value=0.0)

# MTPA
mtpaResult = 5.2 * mtpaf[:] * conversion 
mtpaResult.set_fill_value(0.0)
mtpaResult = mtpaResult.filled(fill_value=0.0)

# MTPO
mtpoResult = 5.0 * mtpof[:] * conversion 
mtpoResult.set_fill_value(0.0)
mtpoResult = mtpoResult.filled(fill_value=0.0)

result = isopResult + mtpaResult + mtpoResult

out = netCDF4.Dataset('ag-bvoc.nc', 'w', format='NETCDF3_64BIT_OFFSET', clobber=True)

if len(out.dimensions) == 0:
    for vname in ["lat", "lon"]:
        dim = rootgrp.dimensions[vname]
        out.createDimension(vname,size=dim.size)
    for vname in ["lat", "lon"]:
        rootvar = rootgrp.variables[vname]
        x = out.createVariable(vname, rootvar.datatype, rootvar.dimensions)
        x[:] = rootvar[:]
        x.setncatts(rootvar.__dict__)
    pm_out = out.createVariable("bvoc", 'f8', rootgrp.variables["factor"].dimensions)
    pm_out.units = "kg m-2 yr-1"
    pm_out.long_name = "bVOC emissions from crops"
    pm_out[:] = 0.0

pm_out[:] = pm_out[:] + result
out.close()




