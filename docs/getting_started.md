# Getting Started

## Installation

First, create a new conda environment and install the required packages. These are:

- click, numpy, pandas, matplotlib, openpyxl 
- pathlib, xarray, cartopy, shapely, netCDF4
- tqdm, pyyaml, pytest, panel 

Then, install the package. Change to the main directory of the repository and run
```bash
python setup.py install
```
If you do so, don't forget to reinstall after any changes.

During development, a better way is to install using editable mode with pip
```bash
pip install -e .
```



## First Steps to use WRFtamer

### 1. (optional) Set environment Variables

This program uses four environmental variables to set important paths and options. Setting these variables is optional, as default default directories are defined.

| env variable          | default                |
| --------------------- | -----------------------|
| WRFTAMER_HOME_PATH    | $HOME/wrftamer         |
| WRFTAMER_RUN_PATH     | $HOME/wrftamer/run     |
| WRFTAMER_ARCHIVE_PATH | $HOME/wrftamer/archive |
| WRFTAMER_make_submit  | False                  |

With conda, you may set and unset these variables in the environment. If these files don't exist, just create them.

In the file:
```~/.conda/envs/<env_name>/etc/conda/activate.d/env_vars.sh``` put the lines

```bash
set env WRFTAMER_HOME_PATH <your/desired/path/>
set env WRFTAMER_RUN_PATH <your/desired/path/>
set env WRFTAMER_ARCHIVE_PATH <your/desired/path/>
set env WRFTAMER_make_submit <False or True>
```

In the file
```~/.conda/envs/<env_name>/etc/conda/deactivate.d/env_vars.sh``` add

```bash
unset env WRFTAMER_HOME_PATH
unset env WRFTAMER_RUN_PATH
unset env WRFTAMER_ARCHIVE_PATH
unset env WRFTAMER_make_submit
```

This way, these variables are set each time you load your conda environment and are unset on deactivation.

### 2. (required) Prepare WRF and WPS

**These steps only need to be repeated if you change your WRF or WPS installation.**

WRFtamer requires that the directories WRF and WPS are in the same directory. Let us call it `WRF_and_WPS_parent_dir`.

```bash
├─ WRF_and_WPS_parent_dir
        ├─ WRF
                ├─ main
                ├─ ...
        ├─ WPS
                ├─ geogrid
                ├─ ...
```

Use the commands
```bash
wt first_steps <WRF_and_WPS_parent_dir>
```

to create directories and copy executables as well as important files to these directories. This command uses default options. If you are using a different Vtable than Vtable.ecmwf, or you want to use different locations, you can add this information using options. Refer to the command [first_steps](command_line_tools.md#first-steps) for further details.

## Example usage of WRFtamer

This exaple shows how to use WRFtamer to create a project *Test_Proj*, an experiment *Test_Exp*, run the experiment, and performe postprocessing.

*Important:* do not remove the directories created by WRFtamer manually. Instead, use
[wt remove_project](command_line_tools.md#remove-project) and [wt remove](command_line_tools.md#remove).
If you happen to remove such a directory anyway, use the command [wt cleanup_db](command_line_tools.md#cleanup-database)
to get rid of database entries that are no longer valid.

**0.(optional) create a project**.
You may skip this step and not use the option --proj_name in the commands below. In this case, the experiment will be created in WRFTAMER_RUN_PATH.

```bash
wt create_project Test_Proj
```
This command creates a project folder with the same name as the project and copies the files *namelist.template* and *Template.conf* to this folder.

**1a. Prepare configure file for an experiment**

```bash
cd $WRFTAMER_RUN_PATH/Test_Proj
cp configure_template.yaml Test_Exp.yaml
```

Edit *Test_Exp.yaml* accoding to your needs.

In the section *paths*
- set the path *wrf_executables* to `<EXE_DIR>`
- set the path *wrf_essentials* to `<ESSENTIALS_DIR>`
- set the path *wrf_nonessentials* to `<NONESSENTIALS_DIR>`
- set the path *driving_data* to the directory containing your driving data for this experiment 
  (typically grib or nc files from a global model).
  
in the secion *namelist_vars*:

- State the modifications of the namelist.template file. Refer to the namelist.template that has been 
  copied to your working directory or to the one [here](https://github.com/user/repo/blob/branch/namelist_template)
  to find out which variables must be changed. You may write your own template file to fit your needs.
  WRFtamer creates a namelist.input file based on these changes. This will be a combined namelist 
  used by both WPS and WRF. 

in the secion *link_grib*:

- keep suffix_len: 3. Most likely you want to keep this option unchanged. Find more information
  [here](customizing.md#configure.yaml).
  
in the secton *submit_file*:

- You may change the number of nodes and the walltime for your slurm job.


You may re-use this configure-file to create similar experiments. Also, th file will serve as a documentation
of your experiment as WRFtamer can re-create the experiment using this file.

**1b. Create Experiment and run WPS**

This command will create a folder structure for experiment *Test_Exp*, link relevant files, run WPS 
and creates submit-files.

```bash
wt create Test_Exp.yaml --proj_name Test_Proj --run_wps True --comment 'This is a short comment to describe this experiment.'
```

**2. Run wrf.exe**
```bash
cd Test_Exp
sbatch submit_real.sh
sbatch submit_wrf.sh # once real.exe is complete
```

If you do not use slurm, you need to write your own submit-scripts and submit the files using the scheduler installed on your machine.

Wait for the run to finish.

**3. Postprocessing**

The command *move* will move wrfout*, wrfaux*, and tslist-files to the out-folder of the experiment directory. 

```bash
wt move Test_Exp --proj_name Test_Proj
```

If the tslist feature of WRF was used, you may run

```bash
wt tslist_processing Test_Exp --proj_name Test_Proj --timeavg=[10]
```

This will combine the txt files created by the tslist feature and put the data in a netcdf file. 
Furthermore, 10 minute averages are calculated and a netcdf file of these time series is created as
well. You find these files in the out-directory.
