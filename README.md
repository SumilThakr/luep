# luep

Soil NOx
"soil_nox_1_time_varying.py": this reads SMOPS for soil moisture and MERRA2 for soil temperature
Then it saves out the effect of these things
it has a start and end date (for 2021)
then ts_sm_sum.py sums the intermediate outputs into a total effect that can be read by the next script.
soil_nox_3_constant.py: this saves out all the constant effects relevant to soil nox.
soil_nox_4_align.py: this actually finally saves out the soil nox emissions by reading the inputs from the previous scripts.
