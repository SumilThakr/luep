def run(inputdir):
    import pygeoprocessing.geoprocessing as geop
    import numpy as np
    import os
    from osgeo import gdal
    import math
    from datetime import datetime, timedelta

    ############################################################
    ################## Soil NOx emissions ######################
    ############################################################

    # We want to implement the model of Yan et al. (2005)
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

    wdir                = "./"

    ############################################################
    # 1         Effect of soil pH
    ############################################################

    ph_raster      = [(os.path.join(inputdir, 'inputs', 'T_PH_H2O.tiff'),1)]
    ph_raster_out       = os.path.join(wdir, 'intermediate', 'ph_effect.tif')

    def kpH(pH):
        k = 0.0
        match [pH < 4.5, pH <= 5.5, pH <= 7.2, pH <= 8.5]:
            case [True, True, True, True]:
                k = 2.912
            case [False, True, True, True]:
                k = 1.9451
            case [False, False, True, True]:
                k = 2.0198
            case [False, False, False, True]:
                k = -0.396
            case [False, False, False, False]:
                k = -0.3096
        result          = math.exp(k)
        return result
    kpHv = np.vectorize(kpH)

    geop.raster_calculator(base_raster_path_band_const_list=ph_raster,
                                       local_op=kpHv, 
                                       target_raster_path=ph_raster_out,
                                       datatype_target=gdal.GDT_Float32,
                                       nodata_target=-1,
                                       calc_raster_stats=False)

    ############################################################
    # 2         Effect of land cover
    ############################################################

    # This is a test clip of India at full resolution:
    #lu_raster      = [(os.path.join(inputdir,'inputs', 'test_data', 'clip.tif'),1)]

    # This is the global data at full resolution:
    #lu_raster      = [(os.path.join(inputdir,'inputs', 'gblulcg20.tif'),1)]

    # And this is the global data at 10km resolution:
    lu_raster      = [(os.path.join(inputdir,'inputs', 'gblulcg20_10000.tif'),1)]
    lu_raster_out       = os.path.join(wdir,'intermediate','lu_effect.tif')

    #Value  Code        Class Name                                      USGS
    #1      100         Urban and Built-Up Land                         13
    #2      211         Dryland Cropland and Pasture                    12
    #3      212         Irrigated Cropland and Pasture                  12
    #4      213         Mixed Dryland/Irrigated Cropland and Pasture    12
    #5      280         Cropland/Grassland Mosaic                       14
    #6      290         Cropland/Woodland Mosaic                        14
    #7      311         Grassland                                       10
    #8      321         Shrubland                                       6
    #9      330         Mixed Shrubland/Grassland                       7
    #10     332         Savanna                                         9
    #11     411         Deciduous Broadleaf Forest                      4
    #12     412         Deciduous Needleleaf Forest                     3
    #13     421         Evergreen Broadleaf Forest                      2
    #14     422         Evergreen Needleleaf Forest                     1
    #15     430         Mixed Forest                                    5
    #16     500         Water Bodies                                    17
    #17     620         Herbaceous Wetland                              11
    #18     610         Wooded Wetland                                  11
    #19     770         Barren or Sparsely Vegetated                    16
    #20     820         Herbaceous Tundra                               16
    #21     810         Wooded Tundra                                   16
    #22     850         Mixed Tundra                                    16
    #23     830         Bare Ground Tundra                              16
    #24     900         Snow or Ice                                     15
    #100                NO DATA                                         X

    #IGBP land-cover type: 1, evergreen needleleaf forest;
    # 2, evergreen broadleaf forest; 4, deciduous broadleaf forest;
    # 5, mixed forest; 6, closed shrublands; 9, savannas;
    # 10, Grasslands; 11, permanent wetlands; 12, croplands;
    # 16, barren or sparsely vegetated.
    # Here it says "sparsely vegetated areas includes tundra":
    # https://inspire.ec.europa.eu/documents/Data_Specifications/INSPIRE_DataSpecification_LC_v3.0.pdf

    # klu expects the USGS Land Use/Land Cover classification (Modified Level 2), even though the coefficients from Yan et al. refer to the (perhaps older?) IGBP land cover classification. A mapping between the classifications is provided above
    def klu_usgs(lu):
        k = 0.0
        match lu:
            case 14:
                k = 1.1526
            case 13:
                k = 0.1245
            case 11:
                k = 0.1681
            case 15:
                k = 0.3378
            case 8:
                k = -0.9765
            case 10:
                k = 0.2532
            case 7:
                k = -0.02383
            case 17:
                k = -0.8936
            case 18:
                k = -0.8936
            case 2:
                k = 0.6214
            case 3:
                k = 0.6214
            case 4:
                k = 0.6214
            case 19:
                k = -0.3035
            case 20:
                k = -0.3035
            case 21:
                k = -0.3035
            case 22:
                k = -0.3035
            case 23:
                k = -0.3035
        result          = math.exp(k)
        return result

    klu_usgs_v = np.vectorize(klu_usgs)

    geop.raster_calculator(base_raster_path_band_const_list=lu_raster,
                                       local_op=klu_usgs_v, 
                                       target_raster_path=lu_raster_out,
                                       datatype_target=gdal.GDT_Float32,
                                       nodata_target=-1,
                                       calc_raster_stats=False)

    ############################################################
    # 3         Effect of soil carbon
    ############################################################

    #SOC				
    #  <0.6%	    -0.4376
    #  >0.6-1.2%	-0.2734
    #  >1.2-2%	    -0.2334
    #  >2%	        -0.06834


    soc_raster           = [(os.path.join(inputdir,'inputs', 'T_OC.tiff'),1)]
    soc_raster_out       = os.path.join(wdir,'intermediate','soc_effect.tif')
    def kSOC(SOC):
        k = 0.0
        match [SOC > 0.6, SOC > 1.2, SOC > 2.0]:
            case [False, False, False]:
                k = -0.4376
            case [True, False, False]:
                k = -0.2734
            case [True, True, False]:
                k = -0.2334
            case [True, True, True]:
                k = -0.06834
        result      = math.exp(k)
        return(result)

    kSOC_v = np.vectorize(kSOC)

    geop.raster_calculator(base_raster_path_band_const_list=soc_raster,
                                       local_op=kSOC_v, 
                                       target_raster_path=soc_raster_out,
                                       datatype_target=gdal.GDT_Float32,
                                       nodata_target=-1,
                                       calc_raster_stats=False)

    ############################################################
    # 4         Effect of climate
    ############################################################
    # Köppen-Geiger Climate Classification available from:
    #    Beck, H.E., N.E. Zimmermann, T.R. McVicar, N. Vergopolan, A. Berg, E.F. Wood:
    #    Present and future Köppen-Geiger climate classification maps at 1-km resolution,
    #    Nature Scientific Data, 2018.
    #https://www.gloh2o.org/koppen/

    # Shapefile (different data) here:
    # https://datacatalog.worldbank.org/search/dataset/0042325/World-Maps-of-the-K-ppen-Geiger-Climate-Classification http://koeppen-geiger.vu-wien.ac.at/shifts.htm http://koeppen-geiger.vu-wien.ac.at/data/legend.txt
    #    1:  Af   Tropical, rainforest                  [0 0 255]
    #    2:  Am   Tropical, monsoon                     [0 120 255]
    #    3:  Aw   Tropical, savannah                    [70 170 250]
    #    4:  BWh  Arid, desert, hot                     [255 0 0]
    #    5:  BWk  Arid, desert, cold                    [255 150 150]
    #    6:  BSh  Arid, steppe, hot                     [245 165 0]
    #    7:  BSk  Arid, steppe, cold                    [255 220 100]
    #    8:  Csa  Temperate, dry summer, hot summer     [255 255 0]
    #    9:  Csb  Temperate, dry summer, warm summer    [200 200 0]
    #    10: Csc  Temperate, dry summer, cold summer    [150 150 0]
    #    11: Cwa  Temperate, dry winter, hot summer     [150 255 150]
    #    12: Cwb  Temperate, dry winter, warm summer    [100 200 100]
    #    13: Cwc  Temperate, dry winter, cold summer    [50 150 50]
    #    14: Cfa  Temperate, no dry season, hot summer  [200 255 80]
    #    15: Cfb  Temperate, no dry season, warm summer [100 255 80]
    #    16: Cfc  Temperate, no dry season, cold summer [50 200 0]
    #    17: Dsa  Cold, dry summer, hot summer          [255 0 255]
    #    18: Dsb  Cold, dry summer, warm summer         [200 0 200]
    #    19: Dsc  Cold, dry summer, cold summer         [150 50 150]
    #    20: Dsd  Cold, dry summer, very cold winter    [150 100 150]
    #    21: Dwa  Cold, dry winter, hot summer          [170 175 255]
    #    22: Dwb  Cold, dry winter, warm summer         [90 120 220]
    #    23: Dwc  Cold, dry winter, cold summer         [75 80 180]
    #    24: Dwd  Cold, dry winter, very cold winter    [50 0 135]
    #    25: Dfa  Cold, no dry season, hot summer       [0 255 255]
    #    26: Dfb  Cold, no dry season, warm summer      [55 200 255]
    #    27: Dfc  Cold, no dry season, cold summer      [0 125 125]
    #    28: Dfd  Cold, no dry season, very cold winter [0 70 95]
    #    29: ET   Polar, tundra                         [178 178 178]
    #    30: EF   Polar, frost                          [102 102 102]

    clim_raster      = [(os.path.join(inputdir,'inputs', 'Beck_KG_V1_present_0p5.tif'),1)]
    clim_raster_out       = os.path.join(wdir, 'intermediate', 'clim_effect.tif')

    #Climate				
    # Tropics	0.2932	0.2224	1.32	0.1908
    # Dry	0.9352	0.2945	3.18	0.002
    # Temperate	0.4774	0.2583	1.85	0.0679
    # Cold	-0.09843	0.353	-0.28	0.781

    def kClim(clim):
        k = 0.0
        match [clim < 4, clim < 8, clim < 17, clim < 29]:
            case [True, True, True, True]:
                k = 0.2932
            case [False, True, True, True]:
                k = 0.9352
            case [False, False, False, True]:
                k = -0.09843
        return k

    kClim_v = np.vectorize(kClim)

    geop.raster_calculator(base_raster_path_band_const_list=clim_raster,
                                       local_op=kClim_v, 
                                       target_raster_path=clim_raster_out,
                                       datatype_target=gdal.GDT_Float32,
                                       nodata_target=-1,
                                       calc_raster_stats=False)

    # Also, assign T0 based on climate zones.
    # Note that when we assign T (in ts_sm.py) we subtract a reference T0
    # for 'cold' climates. So to adjust for that, we actually want this T0'
    # to be T0 - 286.69.
    # Zone          T (K)   T0' (K)
    # Tropical      298.87  12.18
    # Temperate     290.67   3.98
    # Dry           295.76   9.07
    # Cold          286.69   0.0

    t0_raster_out       = os.path.join(wdir, 'intermediate', 't0_effect.tif')

    def kT0(clim):
        k = 0.0
        match [clim < 4, clim < 8, clim < 17, clim < 29]:
            case [True, True, True, True]:
                k = 12.18
            case [False, True, True, True]:
                k = 3.98
            case [False, False, True, True]:
                k = 9.07
            case [False, False, False, True]:
                k = 0.0
        return k

    kT0_v = np.vectorize(kT0)

    geop.raster_calculator(base_raster_path_band_const_list=clim_raster,
                                       local_op=kT0_v, 
                                       target_raster_path=t0_raster_out,
                                       datatype_target=gdal.GDT_Float32,
                                       nodata_target=-1,
                                       calc_raster_stats=False)

    ############################################################
    # 5         Nitrogen fertilization
    ############################################################
    # For now, let's add the effect of N fertilization in a way
    # that does not depend on land use. (Later, we will make this
    # vary based on whether land is agricultural/grassland.)

    # N_crop/N_grass is the total N application to crops/pasture.
    # EN_rate = N_crop * 122/365 * LAI_m+1 / LAI_avg
    # EN_rate = N_grass * 122/365
    # For now, we assume that both N_crop and N_grass are applied
    # evenly in a year (so we omit LAI-dependence).
    # N_eff = 0.03545

    # Load the total N application data (derived from other work)
    # The final N fertilization dependence is given by:
    # 1 + (N_eff * N_rate * 122/365)

    # This is totN manure:
    # /Users/sumilthakrar/UMN/Projects/GlobalAg/manureNH3/totN/totalmanureN.nc
    # This is totN synthetic (for major crops):
    # /Users/sumilthakrar/UMN/Projects/GlobalAg/FertilizerCropSpecific_Geotiff/sumtiffsfertN/output/totsynthN.tif
    # These were summed to make totN.tif
    #n_manure_raster    = [(os.path.join(inputdir, 'inputs', 'manure_spreading.tiff'),1)]
    n_manure_raster    = [(os.path.join(inputdir, 'inputs', 'totN.tif'),1)]

    n_raster_out       = os.path.join(wdir, 'intermediate', 'n_effect.tif')

    def kN(N_rate):
        return 1.0 + (0.03545 * N_rate * 122.0/365.0)

    kN_v = np.vectorize(kN)

    geop.raster_calculator(base_raster_path_band_const_list=n_manure_raster,
                                       local_op=kN_v, 
                                       target_raster_path=n_raster_out,
                                       datatype_target=gdal.GDT_Float32,
                                       nodata_target=-1,
                                       calc_raster_stats=False)


    ############################################################
    # 6         Temperature
    ############################################################
    # ECMWF data is NOT open source in general, so we do not use this.

    # Another script, ts_sm.py, generates intermediate files for
    # each day, e.g. ts_sm_effect_20210125.tiff. These represent
    # the effect of temperature and soil moisture.
    # These are summed in another script, 'ts_sm_sum.py'.
    # This saves out './intermediate/ts_sm_sum.tiff'



    ############################################################
    # 7         Moisture
    ############################################################
    # p_peak        = 13:01 * ln(t_dry) - 53.6
    # t_dry is the length of time (in hours) when the soil moisture
    # is below 17.5% (v/v) in the ECMWF dataset.
    # (European Centre for Medium-Range Weather Forecasts)
    # p             = p_peak * exp(-0.068t)
    # Note that the data is every 6 hours.

    # THis also uses ECMWF data, which is not open source.
    # We could use SMAP data instead, which is daily rather than
    # on a 6-hour time-step.

    ############################################################
    # 8         Canopy Reduction Function
    ############################################################
    # For now, we only consider dependence on LAI (not SAI).
    # The CRF is then given by CRF = exp(-0.32 * LAI)
    lai_raster          = [(os.path.join(inputdir, 'inputs', 'LAI', 'out_sum.tiff'),1)]
    crf_raster_out       = os.path.join(wdir, 'intermediate', 'crf_effect.tif')

    def kCRF(lai):
        return math.exp(-0.32 * lai)

    kCRF_v = np.vectorize(kCRF)

    geop.raster_calculator(base_raster_path_band_const_list=lai_raster,
                                       local_op=kCRF_v, 
                                       target_raster_path=crf_raster_out,
                                       datatype_target=gdal.GDT_Float32,
                                       nodata_target=-1,
                                       calc_raster_stats=False)

    ############################################################
    # 9         Fire
    ############################################################
    # Ignore fire for now (small effect)

    ############################################################
    # 10         Soil NOx estimation
    ############################################################
    # This is done in the next script, soil_nox_5_align.py
