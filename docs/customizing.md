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
is a yaml file collecting settings for each experiment. It has four sections:

- paths
- namelist_vars
- submit_file
- link_grib

In *paths*, the four main paths are defined, namelist vars lists all lines in your namelist that diverge
from the namelist.template, under *submit_file*, you may change the number of nodes and the walltime for
your submit files and *link_grib* modifies the script that links your gribfile to the wrf-run directory.
By default it is set to 3 and you do not need to make any changes. If the number of grib-files you want 
to link exceeds 26³=17576 files, you need to add another letter to the GRIBFILE.XXX names. This option 
allows to do that. However, make sure that you make appropriate changes in the WPS/ungrib code as well. 

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

```
#SBATCH --job-name={name}
#SBATCH --output={slurm_log}
#SBATCH -N {nodes}
#SBATCH --time={time}
```