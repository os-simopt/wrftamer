# Command line tools

The following commands can be run from the command line.

## Project related commands

The help of these commands may be displayed using 

```bash
wt <command> --help
```

### create project

Create a new project. Project names must be unique. The project name may only contain alphabetic characters, numbers, dashes and underscores.

```bash
wt create_project [PROJ_NAME]
```

- Creates a directory *PROJ_NAME* in the WRFTAMER_RUN_PATH
- Creates a directory WRFTAMER_HOME_PATH/.wrftamer/*PROJ_NAME* and a file *List_of_Experiments.xlsx* within this directory
- The files *namelist.template* and *Template.conf* are created in the project directory

### rename project

```bash
wt rename_project [OLD_NAME] [NEW_NAME]
```

Renames an existing project. All directories are renamed accordingly. All paths are updated.

### remove project

```bash
wt remove_project [PROJ_NAME]
```

Deletes the entire directory tree in WRFTAMER_RUN_PATH/*PROJ_NAME* and WRFTAMER_HOME_PATH/.wrftamer/*PROJ_NAME*.

**WARNING: This option may cause massive loss of data.** A clear warning is displayed and "Yes" (capitalized) must be typed to confirm.

### list projects

```bash
wt list_projects
```

Displays a list of projects managed with WRFtamer

### display disk use of a project

```bash
wt du_project [PROJ_NAME]
```

Displays the disk usage of a project. This includes all files, both in the WRFTAMER_RUN_PATH as well as in the WRFTAMER_ARCHIVE_PATH.

### display runtimes

```bash
wt runtimes_project [PROJ_NAME]
```

Display the runtimes of all experiments in *PROJ_NAME*.

TODO: how to update these numbers?  

### update database

```bash
wt update_db [PROJ_NAME]
```

Not yet implemented. TODO: implement.

---

## Experiment related commands

All commands below have the option --proj_name [PROJ_NAME].

*PROJ_NAME*: the name of the project EXP_NAME belongs to. Omit this option if EXP_NAME is not part of a project.


### create

```bash
wt create [EXP_NAME.yaml] --namelisttemplate [namelist.template] --run_wps [BOOL] --comment [STRING] --proj_name [PROJ_NAME]
```

Create a new experiment. Each experiment name may only be used once per project. The creation of 
an experiment includes the following steps:

- Create a directory structure

```bash
├─ EXP_NAME
        ├─ wrf
        ├─ out
        ├─ log
        ├─ plots
```

- link relevant files to the wrf-subdirectory
- create namelist files
- (optional) run WPS
- create submit scripts if the environment variable WRFTAMER_make_submit is set to True.
- copy the file *EXP_NAME.yaml* to the EXP_NAME directory as configure.yaml.

Required: 

A configure file named EXP_NAME.yaml.

Options:

-- namelisttemplate. The namelist template that is used to create the namelist files. Default: built-in.

-- run_wps: True or False

-- comment: A short comment that describes what the experiment does.

### run wps

```bash
wt run_wps [EXP_NAME] --proj_name [PROJ_NAME]
```

Run WPS for an existing experiment. The configure file used to create the experiment is required as an argument.

### rename

```bash
wt rename [EXP_NAME] [NEW_EXP_NAME] --proj_name [PROJ_NAME]
```

Changes the name of an experiment.

### remove

Removes all data and all references to *EXP_NAME*. To avoid loss of data, this must be confirmed by typing 'Yes' (capitalized).

```bash
wt remove [EXP_NAME] --proj_name [PROJ_NAME]
```

### copy

An experiment is copied to a new experiment directory. Large data, i.e. wrfinput_d0X and wrfbdy_d0X files are only linked to the new directory. This option is intended for the creation of experiments that use the same input data, for example comparing the impact of different boundary layer schemes. Apply changes in the *NEW_EXP*, and run the experiment.

```bash
wt copy [EXP_NAME] [NEW_EXP] --proj_name [PROJ_NAME] 
```

### restart

```bash
wt restart [restart_file] --proj_name [PROJ_NAME]
```

restartfile: /path/to/a/wrfrst-file

The timestamp used in the filename of the wrfrst file is used to determine starting time. Starting date and time, runtime and restart = .true. are set in the namelist.input file. You still need to submit the run as usual. Use [move] bevor re-submitting the run to avoid tslist files to be overwritten. [process_tslist] can combine multiple tslists to a single file.

### postprocessing

Move wrfout, wrfaux and tslist files from the wrf to the out-directory. logfiles are moved to the log-directory. wrfrst files remain in the wrf directory.

```bash
wt move [EXP_NAME] --proj_name [PROJ_NAME]
```

Process tslist files that have been moved to the out-directory.  

```bash
wt process_tslists [EXP_NAME] --location [LOC] --domain [DOM] --timeavg [avg] --proj_name [PROJ_NAME]
```

Options:

*LOC*: the shortname of a tslist point as stated in the column named 'pfx' in the tslist file. All locations are processed if this option is not used.

*DOM*: the domain (i.e. d0X) that should be processed. All domains are processed if this option is not used.

*AVG*: a list of averaging windows lenghts in minutes. The tslist data is averaged over the required periods and data is written to seperate files. Example: --timeavg [5,10] for 5 minute and 10 minute averages.

### archive 
Move an experiment directory to the WRFTAMER_ARCHIVE_PATH. Deletes all files in the wrf-directory expect exept the namelist.input file and auxillary files.

```bash
wt archive [EXP_NAME] --proj_name [PROJ_NAME] --keep_log [BOOL]
```

*BOOL*: if false, log directory is deleted as well. Default: *True*.


### display runtime

```bash
wt wrf_timing [EXP_NAME] --proj_name [PROJ_NAME]
```

Display the time an experiment took. Data is extracted from the xlsx file for speed. Run [update_db] to update this data.


## Utilities

### first steps

```bash
wt first_steps [wrf_and_wps_parent_dir] --exe_dir [exe_dir] --essential_data_dir [ess_dir] --non_essential_data_dir [ness_dir] --vtable [Vtable]
```

This command combines the make_essential_data_dir and make_executable_dir and provides default values to the options. The function creates the directories listed and copies files to the right directories.

Default values:
```bash
exe_dir  = $HOME/wrftamer/bin/wrf_executables
ess_dir  = $HOME/wrftamer/src/wrf_essentials
ness_dir = $HOME/wrftamer/src/wrf_nonessentials
vtable = 'Vtable.ECMWF'
```

### make executalbes dir
```bash
wt make_executable_dir [wrf_and_wps_parent_dir] [exe_dir]
```

Creates directory *exe_dir* and copies executables from wrf and wps to this directory.

### make essentials dir

```bash
wt make_essential_data_dir [wrf_and_wps_parent_dir] --essential_data_dir [ess_dir] --vtable [Vtable]
```

Creates directory *ess_dir* and copies all files that need to be present in the run directory to *ess_dir*

### cleanup database

```bash
wt cleanup_db --proj_name [PROJ_NAME]
```

If you delete an experiment or a project using `rm -r` instead of `wt remove` and `wt remove_project`, 
entries remain in the database, causing problems with other commands. This command removes these entries.

### start watchdog 

```bash
wt start_watchdog [wd_script] [PERIOD]
```

Add a cronjob to the crontab that will be executed every [PERIOD] hours. The command to be executed is defined
in the [wd_script]. Refer to [create watchdog script](command_line_tools#create-watchdog-script) for more information.

Be aware that [wd_script] must contain the absolute path to the script.

### stop watchdog

```bash
wt start_watchdog [wd_script]
```

Removes the cronjob defined by [wd_script] from the crontab.


### create watchdog script
The watchdog, a simple crontab checks every [PERIOD] hours for runs that are complete. For those that are, 
the postprocessing protocol, as defined in the configure.yaml file is performed. However, cron must know a 
few parameters in order to be able to call the script. Therefore, the command

```bash
wt create_wd_script [MINICONDA_PATH] [CONDAENV_NAME] --template [template_file]
```

Creates an appropriate bash script to be executed by cron.

**MINICONDA_PATH:** the path to your miniconda installation. Check that MINICONDA_PATH/bin/activate exists.

**CONDAENV_NAME:** the name of your conda environment.

Options:
**template_file:** a template file to create the bash script. You may create your own with variables "miniconda_path",
"HOME" and "condaenv_name".
