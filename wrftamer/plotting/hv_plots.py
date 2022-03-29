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
    plottype = infos['plttype']
    var = infos['var']

    if plottype == 'Timeseries':
        data, units, description = prep_ts_data(obs_data, mod_data, infos)
        stats = Statistics(data, infos)

        xlim = [data.index[0], data.index[-1]]
        size = 5

        xlabel = f'time (UTC)'
        ylabel = f'{var} ({units})'

        for idx, item in enumerate(data):
            if idx == 0:
                if var == 'DIR':
                    figure = data[item].dropna().hvplot.scatter(xlim=xlim, size=size, xlabel=xlabel, ylabel=ylabel)
                else:
                    figure = data[item].dropna().hvplot(xlim=xlim, xlabel=xlabel, ylabel=ylabel)
            else:
                if var == 'DIR':
                    figure = figure * data[item].dropna().hvplot.scatter(xlim=xlim, size=size,
                                                                         xlabel=xlabel, ylabel=ylabel)
                else:
                    figure = figure * data[item].dropna().hvplot(xlim=xlim, xlabel=xlabel, ylabel=ylabel)

        figure.opts(legend_position='bottom_right')
        figure = pn.Column(figure, stats)

    elif plottype == 'Profiles':

        size = 10
        width = 400
        height = 600
        data, units, description = prep_profile_data(obs_data, mod_data, infos)

        xlabel = f'{var} ({units})'
        ylabel = f'height (m)'

        for num, item in enumerate(data):
            if num == 0:
                if var == 'DIR':
                    figure = item.hvplot.scatter(y='ALT', x=item.columns[1], size=size,
                                                 xlabel=xlabel, ylabel=ylabel,
                                                 width=width, height=height, label=item.columns[1])
                else:
                    figure = item.hvplot(y='ALT', x=item.columns[1], xlabel=xlabel,
                                         width=width, height=height, label=item.columns[1])
            else:
                if var == 'DIR':
                    figure = figure * item.hvplot.scatter(y='ALT', x=item.columns[1], size=size,
                                                          xlabel=xlabel, ylabel=ylabel,
                                                          width=width, height=height, label=item.columns[1])
                else:
                    figure = figure * item.hvplot(y='ALT', x=item.columns[1],
                                                  xlabel=xlabel, ylabel=ylabel,
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
        xlabel, ylabel = f'Obserbvation ({units})', f'Model ({units})'

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
        figure = data.hvplot.quadmesh(x='time (UTC)', y='ALT', ylabel='z (m)',
                                      title=data.standard_name + ' (' + data.units + ')')
        stats = None

    else:
        print('Not yet implemented 01')
        figure = None
        stats = None

    return figure, stats
