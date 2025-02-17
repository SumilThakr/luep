import os
import numpy as np

path = "./"
files = ["PFT.nc"]

#[print(f) for f in files]

import netCDF4

out = netCDF4.Dataset('mtpa-factor.nc', 'w', format='NETCDF3_64BIT_OFFSET', clobber=True)

varnames = ["PFT1","PFT2","PFT3","PFT4","PFT5","PFT6","PFT7","PFT8","PFT9","PFT10","PFT11","PFT12","PFT13","PFT14","PFT15"]
# MTPA is APIN, BPIN, SABI, and CARE, so these EFs need to be added to each other.
scale_factors = [1030,1030,830,840,610,840,610,610,380,620,380,4.5,4.5,4.5,4.5]


secondsToHours = 60.0 * 60.0
kgToUg = 1000.0 * 1000.0 * 1000.0



rootgrp2 = netCDF4.Dataset("./copy_MEGAN2020.nc", "r")
isop = rootgrp2["MTPA_MEGAN"][0,:,:] * secondsToHours * kgToUg


for f in files:
    print(f)
    filepath = os.path.join(path, f)
    rootgrp = netCDF4.Dataset(filepath, "r")

    if len(out.dimensions) == 0:
        for vname in ["lat", "lon"]:
            dim = rootgrp.dimensions[vname]
            out.createDimension(vname,size=dim.size)
        for vname in ["lat", "lon"]:
            rootvar = rootgrp.variables[vname]
            x = out.createVariable(vname, rootvar.datatype, rootvar.dimensions)
            x[:] = rootvar[:]
            x.setncatts(rootvar.__dict__)
        pm_out = out.createVariable("factor", 'f8', rootgrp.variables["PFT1"].dimensions)
        pm_out.units = "µg m−2 h −1"
        pm_out.long_name = "MTPA factor"
        pm_out[:] = 0.0

    for i, name in enumerate(varnames):
        data = rootgrp[name][:]
        data = data * scale_factors[i] / 100.0
        pm_out[:] = pm_out[:] + data

tdat = np.divide(isop,pm_out[:],out=np.ones_like(pm_out[:]),where=pm_out[:]!=0.0)
print(np.average(tdat))
# Set numbers above 10 to the global average
tdat[tdat >= 10.0] = 0.27442
print(np.average(tdat))
pm_out[:] = tdat
#    data[data==np.empty] = 0.0
#    print(np.amax(data))
#print(pm_out[:].sum()/1000000000)
out.close()
