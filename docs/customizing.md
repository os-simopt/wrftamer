# Customizing WRFtamer

This secion explains how to customize WRFtamer to your needs.

Each experiment created with WRFtamer is configured using the following files:

1. **configure.yaml**,
   where an experiment is configured by defining variables diverging from the namelist.template.
   This will, most likely, be different for each experiment. 
2. **namelist.template**, 
   where the standard settings of your namelist are defined. 
   This file will propably not change once it has been adapted to your needs.
3. **submit.template**, defining the standard submit file (optional)
   most likely, you won't have to change this file, once it has been customized for your cluster. 
   
## configure.yaml
is a yaml file collecting settings for each experiment. It has five sections:

- paths
- namelist_vars
- submit_file
- link_grib
- pp_protocol

In *paths*, the four main paths are defined, namelist vars lists all lines in your namelist that diverge
from the namelist.template, under *submit_file*, you may change the number of nodes and the walltime for
your submit files and *link_grib* modifies the script that links your gribfile to the wrf-run directory.
By default it is set to 3 and you do not need to make any changes. If the number of grib-files you want 
to link exceeds 26³=17576 files, you need to add another letter to the GRIBFILE.XXX names. This option 
allows to do that. However, make sure that you make appropriate changes in the WPS/ungrib code as well.

The section *pp_protocol* defines the postprocessing protocol that should be executed after a run is finished. 
The execution is done automatically if the [watchdog](command_line_tools.md#start-watchdog) is set or manually via
the commandline or the gui.

Example:
```yaml
pp_protocol:
  move: 1
  tslist_processing:
    timeavg: [5,10]
  create_maps:
    list_of_model_levels: [5]
    list_of_variables: ['WSP']
    list_of_domains: ['d01']
    poi_file: '/path/to/poi_file'
    store: True
```

Here, data is moved after completition of the run. Then, tslists are processed and time averages over 5 and 10 minutes
are calculated. Finally, maps for WSP of domain 1 and the 5th model level are created and stored (as an intermediate file,
for dynamic map plots). Set store to false to plot maps as png for static plots.

## namelist.template

This is a combined file for namelist.input and namelist.wps. Variables in curly brackets will be set by
WRFtamer and need no changes. All the other variables should be set to the values you are using most
by default. WRFtamer will compare the variables set in configure.yaml with this template and replace 
any lines that are different from the template. This approach keeps your configure.yaml fiels as
concise as possible.

## submit.template

This is a template for a SLURM submit file for your cluster. As of now, WRFtamer is only able to create
SLURM submit files, and only with the build-in template. 

**If there is a demand by the userbase, more options will be added to WRFtamer later on.**

Right now, your SLURM template must include the followning lines (unmodified).

```bash
#SBATCH --job-name={name}
#SBATCH --output={slurm_log}
#SBATCH -N {nodes}
#SBATCH --time={time}
```

## Optional environmental variables

This program uses six environmental variables to set important paths and options. Setting these variables is optional,
as default default directories are defined or variables are not used if they are not set.

| env variable          | default                |
| --------------------- | -----------------------|
| WRFTAMER_HOME_PATH    | $HOME/wrftamer         |
| WRFTAMER_RUN_PATH     | $HOME/wrftamer/run     |
| WRFTAMER_ARCHIVE_PATH | $HOME/wrftamer/archive |
| WRFTAMER_make_submit  | False                  |
| OBSERVATIONS_PATH     | N/A                    |
| WRFTAMER_DEFAULT_POI_FILE | N/A                |
| WRFTAMER_DEFAULT_LEVS_PER_VAR_FILE | N/A                |

### OBSERVATIONS_PATH

must be set abd point to the directory with the observations you want to display with WRFplotter. See
[WRFplotter](wrfplotter.md#preparing-your-observations).

### WRFTAMER_DEFAULT_POI_FILE
should point to a csv-file, containing locations you want to indicate in your map plots. The following structure is 
expected:
  
```text
Name,lat,lon
Station1, 54.015, 8.545
Station2, 53.154, 9.123
...
```

It will be used by map plots of WRFplotter. If this variable is not set, no points will be plotted.

### WRFTAMER_DEFAULT_LEVS_PER_VAR_FILE
should point to a yaml-file. It is used to tell wrfplotter at which levels the observations can be found. Typically,
these vary for different parameters, for which reason this information must be provided by the used. 

The expected structure of the yaml-file (used as default):
  
```yaml
timeseries-like:
    WSP_Analog: ["41", "51", "61", "71", "81", "91", "102"]
    DIR_Analog: ["34", "51", "71", "91"]
    WSP_Sonic: ["42", "62", "82"]
    DIR_Sonic: ["42", "62", "82"]
    PT: ["34", "42", "52", "72", "101"]
    T: ["34", "42", "52", "72", "101"]
    PRES": ["21", "92"]
map-like:
    WSP: ["5"]
    DIR: ["5"]
    PT: ["5"]
    PRES: ["5"]
    PSFC: ["0"]
    U: ["5"]
    V: ["5"]
    W: ["5"]
    HFX: ["0"]
    GRDFLX: ["0"]
    LH: ["0"]
    HGT: ["0"]
```

### Setting environmental variables with conda

You may set and unset these variables in the environment. If these files don't exist, just create them.

In the file:
```~/.conda/envs/<env_name>/etc/conda/activate.d/env_vars.sh``` put the lines

```bash
set env WRFTAMER_HOME_PATH <your/desired/path/>
set env WRFTAMER_RUN_PATH <your/desired/path/>
set env WRFTAMER_ARCHIVE_PATH <your/desired/path/>
set env WRFTAMER_make_submit <False or True>
set env OBSERVATIONS_PATH <your/desired/path/>
set env WRFTAMER_DEFAULT_POI_FILE </absolute/path/to/poi_file.csv>
set env WRFTAMER_DEFAULT_LEVS_PER_VAR_FILE </absolute/path/to/levs_per_var_file.yaml>
```

In the file
```~/.conda/envs/<env_name>/etc/conda/deactivate.d/env_vars.sh``` add

```bash
unset env WRFTAMER_HOME_PATH
unset env WRFTAMER_RUN_PATH
unset env WRFTAMER_ARCHIVE_PATH
unset env WRFTAMER_make_submit
unset env OBSERVATIONS_PATH
unset env WRFTAMER_DEFAULT_POI_FILE
unset env WRFTAMER_DEFAULT_LEVS_PER_VAR_FILE
```

This way, these variables are set each time you load your conda environment and are unset on deactivation.