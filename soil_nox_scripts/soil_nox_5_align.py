def run(inputdir):
    import pygeoprocessing.geoprocessing as geop
    import numpy as np
    import os
    from osgeo import gdal
    import math

    wdir                = "./"

    ph_raster      = [(os.path.join(inputdir, 'inputs', 'T_PH_H2O.tiff'),1)]
    ph_raster_out       = os.path.join(wdir, 'intermediate', 'ph_effect.tif')

    lu_raster      = [(os.path.join(inputdir,'inputs', 'gblulcg20_10000.tif'),1)]
    lu_raster_out       = os.path.join(wdir,'intermediate','lu_effect_reproj.tif')

    soc_raster           = [(os.path.join(inputdir,'inputs', 'T_OC.tiff'),1)]
    soc_raster_out       = os.path.join(wdir,'intermediate','soc_effect.tif')

    clim_raster      = [(os.path.join(inputdir,'inputs', 'Beck_KG_V1_present_0p5.tif'),1)]
    clim_raster_out       = os.path.join(wdir, 'intermediate', 'clim_effect.tif')

    t0_raster_out       = os.path.join(wdir, 'intermediate', 't0_effect.tif')

    ts_sm_raster_out       = os.path.join(wdir, 'intermediate', 'ts_sm_sum.tiff')
    n_raster_out       = os.path.join(wdir, 'intermediate', 'n_effect.tif')

    aligned_ph_path      = os.path.join(wdir, 'intermediate', "aligned_ph.tif")
    aligned_lu_path      = os.path.join(wdir, 'intermediate', "aligned_lu.tif")
    aligned_soc_path      = os.path.join(wdir, 'intermediate', "aligned_soc.tif")
    aligned_clim_path      = os.path.join(wdir, 'intermediate', "aligned_clim.tif")
    aligned_t0_path      = os.path.join(wdir, 'intermediate', "aligned_t0.tif")
    aligned_ts_sm_path  = os.path.join(wdir, 'intermediate', "aligned_ts_sm.tif")
    aligned_n_path  = os.path.join(wdir, 'intermediate', "aligned_n.tif")

    geop.align_and_resize_raster_stack(
            [ph_raster_out, soc_raster_out, clim_raster_out, t0_raster_out, lu_raster_out, ts_sm_raster_out, n_raster_out],
            [aligned_ph_path, aligned_soc_path, aligned_clim_path, aligned_t0_path, aligned_lu_path, aligned_ts_sm_path, aligned_n_path],
            ['bilinear', 'bilinear', 'bilinear', 'bilinear','bilinear', 'bilinear','bilinear'],
            geop.get_raster_info(soc_raster_out)['pixel_size'],
            bounding_box_mode='union')

    '''
    geop.align_and_resize_raster_stack(
            [lu_raster_out],
            [aligned_lu_path],
            ['bilinear'],
            geop.get_raster_info(soc_raster_out)['pixel_size'],
            bounding_box_mode='union')

    def soilnox_fixed_params(ph,soc,clim):
    #    return math.exp(-1.8327+clim-(0.11*t0))*soc*ph
        return soc*ph*math.exp(clim)*math.exp(-1.8327)
    '''
    def soilnox_fixed_params(ph,soc,clim,t0,lu,tssm,n):
        return soc*ph*math.exp(clim)*math.exp(-1.8327)*lu*math.exp(-0.11*t0)*tssm*n


    soilnox_fixed_params_v = np.vectorize(soilnox_fixed_params)

    #list_raster = [(aligned_ph_path,1), (aligned_soc_path,1), (aligned_clim_path,1)]
    list_raster = [(aligned_ph_path,1), (aligned_soc_path,1), (aligned_clim_path,1), (aligned_t0_path,1), (aligned_lu_path,1), (aligned_ts_sm_path,1), (aligned_n_path,1)]

    nox_emissions      = os.path.join(wdir, 'outputs', "nox_emissions.tif")

    geop.raster_calculator(base_raster_path_band_const_list=list_raster,
            local_op=soilnox_fixed_params_v,
            target_raster_path=nox_emissions,
            datatype_target=gdal.GDT_Float32, nodata_target=-1, calc_raster_stats=False)
