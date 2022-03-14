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


########################################################################################################################
#                                                Data Preparation
########################################################################################################################

def prep_profile_data2(obs_data, mod_data, infos: dict, verbose=False) -> list:
    """
    Takes the data coming from my classes, selects the right data and puts everyting in a list.
    In this proj_name, I cannot concat everything into a single dataframe, because the the Z-vectors are different.

    obs_data: dict of observations (usually of the towerdata class)
    mod_data: dict of model data (usually wrf_zt)
    """

    anemometer = infos['anemometer']
    var = infos['var']
    loc = infos['loc']
    time_to_plot = infos['time_to_plot']
    expvec = infos['Expvec']
    obsvec = infos['Obsvec']

    # change a few parameter Names to fit the
    translator = {'WSP': {'Sonic': '_USA', 'Analog': '_CUP'}, 'DIR': {'Sonic': '_USA', 'Analog': '_VANE'}}
    if var in ['WSP', 'DIR']:
        device = translator.get(var, '').get(anemometer, '')
    else:
        device = ''

    data2plot = []
    for obs in obsvec:
        zvec, data = [], []
        myobs = obs_data[obs]
        ttp = np.datetime64(time_to_plot)
        myobs = myobs.where(myobs.Time == ttp, drop=True)

        for key in myobs.keys():
            if var in key and 'std' not in key:
                if device == '':
                    if 'CUP' not in key and 'USA' not in key and 'VANE' not in key and key.startswith(var + '_'):
                        zvec.append(float(key.split('_')[1]))
                        data.append(myobs[key].values[0])

                elif device in key:
                    zvec.append(float(key.rsplit('_', 1)[1]))
                    data.append(myobs[key].values[0])
                    units = myobs[key].units
                    description = var #  (standard_name contains height)

        df = pd.DataFrame({'Z': zvec, loc: data})
        data2plot.append(df)

    for exp in expvec:
        try:
            mymod = mod_data[exp][loc]
            mymod = mymod.where(mymod.Time == ttp, drop=True)
            mymod = mymod.to_dataframe()
            mymod = mymod.set_index('Z')
            mymod = pd.DataFrame(mymod[var])
            mymod = mymod.rename(columns={var: exp})
            mymod = mymod.reset_index()
            data2plot.append(mymod)

            units = mod_data[exp][loc][var].units
            description = mod_data[exp][loc][var].standard_name

        except KeyError:
            if verbose:
                print(f'No data found for experiment {exp}')
        except IndexError:
            if verbose:
                print(f'No data found at this time: {time_to_plot}')

    return data2plot, units, description


def prep_zt_data2(mod_data, infos: dict) -> xr.Dataset:
    var = infos['var']
    loc = infos['loc']

    key = list(mod_data.keys())[0]
    data2plot = mod_data[key][loc]
    new_z = np.mean(mod_data[key][loc]['Z'], axis=0)

    # new_z
    data2plot = data2plot.drop_vars('Z')
    data2plot = data2plot.rename_vars({'zdim': 'Z'})

    data2plot['Z'] = new_z
    data2plot = data2plot.swap_dims({'zdim': 'Z'})
    data2plot = data2plot.drop('zdim')

    return data2plot[var]


def prep_ts_data2(obs_data, mod_data, infos: dict, verbose=False):
    plttype = infos['plttype']
    anemometer = infos['anemometer']
    loc = infos['loc']
    expvec = infos['Expvec']
    obsvec = infos['Obsvec']

    if plttype == 'Timeseries 2':
        var1, var2 = infos['var1'], infos['var2']
        lev1, lev2 = infos['lev1'], infos['lev2']
        data2plot1 = _prep_ts_data2(obs_data, mod_data, expvec, obsvec, loc, var1, lev1, anemometer, verbose)
        data2plot2 = _prep_ts_data2(obs_data, mod_data, expvec, obsvec, loc, var2, lev2, anemometer, verbose)
        return data2plot1, data2plot2
    else:
        var = infos['var']
        lev = infos['lev']
        data2plot = _prep_ts_data2(obs_data, mod_data, expvec, obsvec, loc, var, lev, anemometer, verbose)
        return data2plot


def _prep_ts_data2(obs_data, mod_data, expvec: list, obsvec: list, loc: str, var: str, lev: str, anemometer: str,
                   verbose=False) -> pd.DataFrame:
    """
    Takes the data coming from my classes, selects the right data and concats
    everything into a single dataframe for easy plotting with hvplot.

    obs_data: dict of observations (usually of the towerdata class)
    mod_data: dict of model data (usually wrf_zt)
    expvec: list of experiments to plot
    obsvec: list of observations to plot
    loc: location of the time series
    var: variable to plot
    lev: level at which the varialbe is valid
    anemometer: device used for observation
    """

    if len(mod_data) > 0:
        tmp = mod_data[list(mod_data.keys())[0]][loc].to_dataframe()
        tlim1, tlim2 = tmp.index[0][0], tmp.index[-1][0]

    # change a few parameter Names to fit the name of the obs-files
    translator = {'WSP': {'Sonic': '_USA', 'Analog': '_CUP'}, 'DIR': {'Sonic': '_USA', 'Analog': '_VANE'}}
    if var in ['WSP', 'DIR']:
        device = translator.get(var, '').get(anemometer, '')
    else:
        device = ''

    all_df = []

    for obs in obsvec:
        myobs = obs_data[obs].to_dataframe()
        try:
            if obs == 'FINO1':
                if var == 'PRES':
                    tmp = myobs[f'P_{lev}']
                else:
                    tmp = myobs[f'{var}{device}_{lev}']
            else:  # AV01-12
                tmp = myobs[var]  # WSP, DIR, POW, GEN_SPD

            tmp = tmp.rename(obs)

        except KeyError:
            tmp = pd.DataFrame()
            tmp.name = 'Data Missing'

        if len(mod_data) > 0:
            tmp = tmp[tlim1:tlim2]

        all_df.append(tmp)

    for exp in expvec:
        try:
            mymod = mod_data[exp][loc]

            # interpolate data to desired level
            #  TODO: this may fail for DIR- write a proper function somewhere and call!
            zvec = mymod.Z[0, :].values
            idx = (np.abs(zvec - float(lev))).argmin()
            xa1 = mymod.isel(zdim=idx)
            xa2 = mymod.isel(zdim=idx + 1)
            w1 = abs(zvec[idx] - float(lev)) / abs(zvec[idx + 1] - zvec[idx])
            w2 = abs(zvec[idx + 1] - float(lev)) / abs(zvec[idx + 1] - zvec[idx])
            mymod = (xa1 * w2 + xa2 * w1)

            mymod = mymod.to_dataframe()

            tmp = mymod[var]
            tmp = tmp.rename(exp)
            all_df.append(tmp)
        except KeyError:
            if verbose:
                print(f'No Data for Experiment {exp}')

    if len(all_df) > 0:
        data2plot = pd.concat(all_df, axis=1)
    else:
        data2plot = pd.DataFrame({'Time': [dt.datetime(1970, 1, 1), dt.datetime(2020, 1, 1)], 'data': [np.nan, np.nan]})
        data2plot = data2plot.set_index('Time')

    data2plot.variable = var
    data2plot.level = lev
    data2plot.anemometer = anemometer

    return data2plot


########################################################################################################################
#                                                      Plots
########################################################################################################################
def create_hv_plot(infos: dict, obs_data=None, mod_data=None, map_data=None):
    # TODO: obs-labels are missing. Reason: * operator removes labels. It seems not be possible to manually add
    #  more than one label, but since most likely there is only 1 obs, I quick fix this. Mod-lables are fine.

    plottype = infos['plttype']
    var = infos['var']

    if plottype == 'Timeseries':
        data = prep_ts_data2(obs_data, mod_data, infos)
        stats = Statistics(data, infos)

        xlim = [data.index[0], data.index[-1]]
        size = 5

        if var == 'DIR':
            figure = data[infos['Obsvec']].dropna().hvplot.scatter(xlim=xlim, size=size, ylabel=var,
                                                                   label=infos['Obsvec'][0]) * \
                     data[infos['Expvec']].dropna().hvplot.scatter(xlim=xlim, size=size, ylabel=var)
        else:
            figure = data[infos['Obsvec']].dropna().hvplot(xlim=xlim, ylabel=var,
                                                           label=infos['Obsvec'][0]) * \
                     data[infos['Expvec']].dropna().hvplot(xlim=xlim, ylabel=var)

        figure.opts(legend_position='bottom_right')
        figure = pn.Column(figure, stats)

    elif plottype == 'Timeseries 2':

        # TODO: when figure1 and figure 2 are combined in the last line, the y-limits change.
        #  I do not know how to fix that...
        #  Shared_axes=False does not help.

        var1, var2 = var.split(' and ')

        data1, data2 = prep_ts_data2(obs_data, mod_data, infos)
        stats1 = Statistics(data1, infos)
        stats2 = Statistics(data2, infos)
        stats = pd.concat([stats1, stats2])

        xlim = [data1.index[0], data1.index[-1]]
        ylim1 = [data1.min().min(), data1.max().max()]
        ylim2 = [data2.min().min(), data2.max().max()]

        size = 5
        if var1 == 'DIR':
            figure1 = data1[infos['Obsvec']].dropna().hvplot.scatter(xlim=xlim, ylim=ylim1, size=size,
                                                                     shared_axes=False, ylabel=var1,
                                                                     label=infos['Obsvec'][0]) * \
                      data1[infos['Expvec']].dropna().hvplot.scatter(xlim=xlim, ylim=ylim1, size=size,
                                                                     shared_axes=False, ylabel=var1)
        else:
            figure1 = data1[infos['Obsvec']].dropna().hvplot(xlim=xlim, ylim=ylim1, shared_axes=False, ylabel=var1,
                                                             label=infos['Obsvec'][0]) * \
                      data1[infos['Expvec']].dropna().hvplot(xlim=xlim, ylim=ylim1, shared_axes=False, ylabel=var1)

        if var2 == 'DIR':
            figure2 = data2[infos['Obsvec']].dropna().hvplot.scatter(xlim=xlim, ylim=ylim2, size=size,
                                                                     shared_axes=False, ylabel=var2,
                                                                     label=infos['Obsvec'][0]) * \
                      data2[infos['Expvec']].dropna().hvplot.scatter(xlim=xlim, ylim=ylim2, size=size,
                                                                     shared_axes=False, ylabel=var2)
        else:
            figure2 = data2[infos['Obsvec']].dropna().hvplot(xlim=xlim, ylim=ylim2, shared_axes=False, ylabel=var2,
                                                             label=infos['Obsvec'][0]) * \
                      data2[infos['Expvec']].dropna().hvplot(xlim=xlim, ylim=ylim2, shared_axes=False, ylabel=var2)

        figure1.opts(legend_position='bottom_right')
        figure2.opts(legend_position='bottom_right')
        figure = pn.Column(figure1, figure2, stats)

    elif plottype == 'Profiles':

        size = 10
        width = 400
        height = 600
        data, units, description = prep_profile_data2(obs_data, mod_data, infos)

        for num, item in enumerate(data):
            if num == 0:
                if var == 'DIR':
                    figure = item.hvplot.scatter(y='Z', x=item.columns[1], size=size, xlabel=var,
                                                 width=width, height=height, label=item.columns[1])
                else:
                    figure = item.hvplot(y='Z', x=item.columns[1], xlabel=var,
                                         width=width, height=height, label=item.columns[1])
            else:
                if var == 'DIR':
                    figure = figure * item.hvplot.scatter(y='Z', x=item.columns[1], size=size, xlabel=var,
                                                          width=width, height=height, label=item.columns[1])
                else:
                    figure = figure * item.hvplot(y='Z', x=item.columns[1], xlabel=var,
                                                  width=width, height=height, label=item.columns[1])

        figure.opts(legend_position='bottom_right')
        stats = None

    elif plottype == 'Obs vs Mod':

        mods = infos['Expvec']
        obs = infos['Obsvec'][0]

        data = prep_ts_data2(obs_data, mod_data, infos)
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
        data = prep_zt_data2(mod_data, infos)
        figure = data.hvplot.quadmesh(x='Time', y='Z', ylabel='z (m)',
                                      title=data.standard_name + ' (' + data.units + ')')
        stats = None

    else:
        print('Not yet implemented 01')
        figure = None
        stats = None

    return figure, stats
