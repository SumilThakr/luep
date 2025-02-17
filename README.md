# Land use emissions processor

Process-based models for estimating net pollutant emissions tied to land use, with submodules for:
- windblown dust
- soil NOx
- biogenic VOCs
- deposition of primary PM2.5 from vegetation.

TODO:
- agricultural NH3
- biomass burning
- land clearing

These models explicitly take (harmonized) land use as inputs, to facilitate understanding how
changes in land use affect changes in emissions.

For now, run scripts for each submodule are in the main directory, which call and run scripts
sequentially in the subfolders (e.g., "soil_nox_scripts/").

There are three other folders: inputs, intermediate, and outputs.
- The input directory path is set for each run script. The files are currently not public
(please contact me to request it).

- The intermediate directory is where intermediate outputs are saved by the run scripts. This
means that running the scripts requires some storage space. The intermediate outputs are not
automatically deleted and can be used for diagnostics. Future versions of this will likely reduce
the size of intermediate outputs.

- The output directory is where the ultimate output (changes in emissions) are saved out. More
processing may still be needed to run these outputs in an air quality model.
