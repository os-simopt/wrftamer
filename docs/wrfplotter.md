# WRFplotter

You find the WRFplotter on the third tab of the [GUI](GUI.md).

WRFplotter creates interactive plots (hvplots) as well as static plots of your model data as well as observations.

The following plot types are available as of now:
- Timeseries
- Profiles
- Observation vs Model scatter plots
- Altitude-time plots
- Maps

All plots except the maps plots are based timeseries (tslist) data, processed with WRFtamer. Map plots are based on
wrfout-files. Map data is extracted from wrfout files during postprocessing to improve the responsiveness of WRFplotter.

## Preparing your observations

Observations in the form of timeseries can be displayed by WRFplotter and compared with model results. The observations
must be located in the directory defined by the environment variable OBSERVATIONS_PATH. For each dataset, create a 
subdirectory here and place cf-conform netcdf files of your observations these directories. These files must be named
<Name_of_Dataset>_start_end.nc, where *start* and *end* are formatted as YYYYMMDD. For the time variable, we recommend
numpy.datetime64. For the time zone, UTC is assumed by WRFplotter.

Example:
```bash
OBSERVATIONS_PATH=/path/to/obs/
/path/to/obs/Dataset1/Dataset1_20200101_20210101.nc #contains 5 stations
/path/to/obs/Dataset1/Dataset1_20210101_20220101.nc #contains 5 stations
/path/to/obs/Dataset2/Dataset2_20000101_20220731.nc #contains 1 station
```

These files may contain multiple stations with the same data structure. Each times series must be identifiable by a 
variable 'station_name'. These timeseries must be concatenated along a dimension 'station'. In addtion, WRFplotter 
expects for each station the variables 'lat', 'lon' and 'station_elevation' as well as the attributes 'long_name' and 
'units' for each variable.

WRFplotter will check these files for heights and times to display as timesieres, profiles etc.

## Usage

Select a project in the "Chose Project" selector, or leave it empty to plot experiments not associated with any project.
Select one or multiple experiments. WRFplotter detects domains and locations for which timeseries data exists. Select
a domain and a location and click 'Load Data'. WRFtamer is now able to display plots for timeseries data. Click on the 
resplective tabs to display them. You may select the variable to display as well as the height of the time series in 
the menu above the plots. Finally, you may export the tables with statistical data shown below the plot in markdown or
csv format.

For maps and zt-plots, only the first experiment is plotted since multiple experiments cannot be displayed in such
plots.

WRFplotter displays warnings if the selected variables do not match the variables loaded. 


