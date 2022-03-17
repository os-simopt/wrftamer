import pandas as pd
import xarray as xr
import panel as pn
import datetime as dt
import numpy as np
import holoviews as hv
import hvplot.xarray
import hvplot.pandas
import cartopy.crs as ccrs
from wrfplotter.Statistics import Statistics
from wrftamer.plotting.load_and_prepare import prep_profile_data, prep_ts_data, prep_zt_data

########################################################################################################################
#                                                      Plots
########################################################################################################################
def create_hv_plot(infos: dict, obs_data=None, mod_data=None, map_data=None):
    # TODO: obs-labels are missing. Reason: * operator removes labels. It seems not be possible to manually add
    #  more than one label, but since most likely there is only 1 obs, I quick fix this. Mod-lables are fine.

    plottype = infos['plttype']
    var = infos['var']

    if plottype == 'Timeseries':
        data, units, description = prep_ts_data(obs_data, mod_data, infos)
        stats = Statistics(data, infos)

        xlim = [data.index[0], data.index[-1]]
        size = 5

        for idx, item in enumerate(data):
            if idx == 0:
                if var == 'DIR':
                    figure = data[item].dropna().hvplot.scatter(xlim=xlim, size=size, ylabel=var)
                else:
                    figure = data[item].dropna().hvplot(xlim=xlim, ylabel=var)
            else:
                if var == 'DIR':
                    figure = figure * data[item].dropna().hvplot.scatter(xlim=xlim, size=size, ylabel=var)
                else:
                    figure = figure * data[item].dropna().hvplot(xlim=xlim, ylabel=var)

        figure.opts(legend_position='bottom_right')
        figure = pn.Column(figure, stats)

    elif plottype == 'Profiles':

        size = 10
        width = 400
        height = 600
        data, units, description = prep_profile_data(obs_data, mod_data, infos)

        for num, item in enumerate(data):
            if num == 0:
                if var == 'DIR':
                    figure = item.hvplot.scatter(y='ALT', x=item.columns[1], size=size, xlabel=var,
                                                 width=width, height=height, label=item.columns[1])
                else:
                    figure = item.hvplot(y='ALT', x=item.columns[1], xlabel=var,
                                         width=width, height=height, label=item.columns[1])
            else:
                if var == 'DIR':
                    figure = figure * item.hvplot.scatter(y='ALT', x=item.columns[1], size=size, xlabel=var,
                                                          width=width, height=height, label=item.columns[1])
                else:
                    figure = figure * item.hvplot(y='ALT', x=item.columns[1], xlabel=var,
                                                  width=width, height=height, label=item.columns[1])

        figure.opts(legend_position='bottom_right')
        stats = None

    elif plottype == 'Obs vs Mod':

        mods = infos['Expvec']
        obs = infos['Obsvec'][0]

        data, units, description = prep_ts_data(obs_data, mod_data, infos)
        stats = Statistics(data, infos)

        # For the plot.
        xlim = [0, data.max().max()]
        size = 5
        height, width = 500, 650
        xlabel, ylabel = 'OBS', 'MOD'

        figure = hv.Curve([[0, 0], [xlim[1], xlim[1]]]).opts(color='grey')
        for mod in mods:
            figure = figure * data.hvplot.scatter(x=obs, y=mod, xlim=xlim, ylim=xlim, size=size, width=width,
                                                  height=height, label=mod, xlabel=xlabel, ylabel=ylabel)

        figure.opts(legend_position='bottom_right')

        figure = pn.Column(figure, stats)

    elif plottype in ['Map', 'Diff Map']:

        print('Use Map class for plotting')
        raise DeprecationWarning
        figure = None
        stats = None

    elif plottype in ['CS', 'Diff CS']:
        print('Not yet implemented')
        figure = None
        stats = None

    elif plottype == 'zt-Plot':
        data = prep_zt_data(mod_data, infos)
        figure = data.hvplot.quadmesh(x='time', y='ALT', ylabel='z (m)',
                                      title=data.standard_name + ' (' + data.units + ')')
        stats = None

    else:
        print('Not yet implemented 01')
        figure = None
        stats = None

    return figure, stats
