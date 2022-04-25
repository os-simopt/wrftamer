# Graphical User Interface

First, follow the steps described in [Installation](getting_started.md#installation) and [First Steps](getting_started.md#first-steps-to-use-wrftamer).

Start the GUI by typing wrftamer.gui in the commandline. The GUI starts as a browser window.

The GUI provides four tabs. 

- **Project** for the management of projects.
- **Experiment** for the management of experiments
- **WRFtamer** to plot data from your experiments.
- **About** Shows the version number and your WRFtamer paths.

The GUI should be quite intuitive, for which reason the documentation is kept short.

**Caveat on using the GUI:**
The GUI runs in a browser window. If you cannot open a browser from your cluster you may access cluster harddrives from your local machine. If this is not an option for you, you are limited to the use of command line tools.

## Project

To create a project, type a project name in the text box and click *create Project*. You can now select you project in the selector field. To rename a selected project, type the new name in the textbox and click *Rename Project*. Project names must be unique. To remove a project, select it, click *Remove Project* and then *Confirm Deletion*. If you change your mind, click *Cancel*.

**Reassociate Experiments**

To (re)associate one or multiple experiments with a project, selcet the experiments in the table, type the project name in the text field and click *Reassociate Experiments*. The displayed table is dynamic, i.e. you may click in the red cross, and then on the checkbox. A green checkmark now appears to mark a selected experiment.

## Experiment

You may want to select a project before switching to the experiment tab. If you do not, you will manage standalone experiments.

To create a new experiment, click *Choose File* to select a previously created Exp_Name.conf file. You may add a comment, edit the configure file and change the new experiment name in the textbox. Then, click *Create Experiment*. You may now select your experiment and any other previously created experiments in the selector field.

Renaming and removing an experiment follows the same pattern as for projects. An experiment can be copied if only small (manual) changes are desired and recomputing wrfinput and wrfbdy files is not required. The button *Postprocessing* moves data from completed runs to the respective out folders and processes tslists with default option timeavg=[5,10] for all domains and locations. The button *Archive* moves selected experiments to the archive destination.

## WRFtamer

A GUI to create interactive plots for timeseries, profiles, scatterplots, zt-plots and maps. You find more information [here](wrfplotter.md) 

## About 

Shows the version number of the WRFtamer GUI and the relevant WRFtamer paths. You may select a poi (points of interest) file here,
which can be used by WRFtamers Map plots to mark certain locations on your maps. 

