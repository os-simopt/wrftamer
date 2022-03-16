import datetime as dt
import xarray as xr
import pandas as pd
import numpy as np

def uv_to_FFDD(u, v):

    ff = np.sqrt(u ** 2 + v ** 2)
    dd = 180. / np.pi * np.arctan2(-u, -v)
    dd = np.mod(dd, 360)

    return ff, dd

########################################################################################################################
#                                                  Load Data
########################################################################################################################

def load_obs_data(obs_data: dict, obs: str, dataset: str, **kwargs):
    """
    This function just loads observations from a single location and stores everything in the obs_data dict.
    """

    from wrftamer.wrfplotter_classes import Timeseries

    startdate = kwargs['startdate']
    enddate = kwargs['enddate']

    dtstart, dtend = dt.datetime.strptime(startdate, '%Y%m%d'), dt.datetime.strptime(enddate, '%Y%m%d')
    cls = Timeseries(dataset, dtstart, dtend, calc_pt=True)

    if 'station' in cls.data.dims:
        for stat in cls.data.station:
            tmp = cls.data.isel(station=stat)
            if tmp['station_name'].values == obs:
                obs_data[obs] = tmp
                break
    else:
        obs_data[obs] = cls.data


def load_mod_data(mod_data: dict, exp_name: str, **kwargs):

    """
    This function just loads model data from a single location and stores everything in the mod_data dict.
    """

    from wrftamer.experiment_management import experiment
    from wrftamer.project_management import project

    try:
        proj_name = kwargs['proj_name']
    except KeyError:
        proj_name = None

    dom = kwargs['dom']
    ave_window = kwargs['AveChoice_WRF']

    if ave_window in [0, 'raw']:
        prefix = 'raw'
    elif ave_window in [-10, 'ten']:
        prefix = 'ten'
    else:
        prefix = 'Ave' + str(ave_window) + 'Min'

    exp = experiment(proj_name, exp_name)
    list_of_locs = exp.list_tslocs(verbose=False)
    file2load = f'{exp.workdir}/out/{prefix}_tslist_{dom}.nc'
    tmp_xa = xr.open_dataset(file2load)

    tslist_data = dict()
    for dim in range(0, tmp_xa.dims['station']):
        tmp = tmp_xa.isel(station=dim)

        # TODO: got an error for Ave10 and Ave 5 files. station_name, lat, lon, elevation became f(t)
        # -> this forces me to do this try/except.
        # Solve this issue and simplifiy this piece.
        try:
            loc = tmp.station_name.values[0]
        except IndexError:
            loc = str(tmp.station_name.values)

        if loc in list_of_locs:
            tslist_data[loc] = tmp

        if bool(tslist_data):
            mod_data[exp_name] = tslist_data
        else:
            print('No data for Experiment', exp_name)
            pass  # do not add empty dicts


########################################################################################################################
#                                                Data Preparation
########################################################################################################################

def prep_profile_data(obs_data, mod_data, infos: dict, verbose=False) -> list:
    """
    Takes the data coming from my classes, selects the right data and puts everyting in a list.
    In this proj_name, I cannot concat everything into a single dataframe, because the the Z-vectors are different.

    obs_data: dict of observations
    mod_data: dict of model data
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
        myobs = myobs.where(myobs.time == ttp, drop=True)

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

        df = pd.DataFrame({'ALT': zvec, loc: data})
        data2plot.append(df)

    for exp in expvec:
        try:
            mymod = mod_data[exp][loc]
            mymod = mymod.where(mymod.time == ttp, drop=True)
            mymod = mymod.to_dataframe()
            mymod = mymod.set_index('ALT')
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


def prep_zt_data(mod_data, infos: dict) -> xr.Dataset:
    var = infos['var']
    loc = infos['loc']

    key = list(mod_data.keys())[0]
    data2plot = mod_data[key][loc]

    # new_z
    new_z = mod_data[key][loc]['ALT'].mean(axis=0, keep_attrs=True)
    data2plot = data2plot.drop_vars('ALT')
    data2plot = data2plot.rename_vars({'zdim': 'ALT'})

    data2plot['ALT'] = new_z
    data2plot = data2plot.swap_dims({'zdim': 'ALT'})
    data2plot = data2plot.drop('zdim')

    return data2plot[var]


def prep_ts_data(obs_data, mod_data, infos: dict, verbose=False):
    plttype = infos['plttype']
    anemometer = infos['anemometer']
    loc = infos['loc']
    expvec = infos['Expvec']
    obsvec = infos['Obsvec']

    if plttype == 'Timeseries 2':
        var1, var2 = infos['var1'], infos['var2']
        lev1, lev2 = infos['lev1'], infos['lev2']
        data2plot1, units1, description1 = _prep_ts_data(obs_data, mod_data, expvec, obsvec, loc, var1, lev1, anemometer, verbose)
        data2plot2, units2, description2 = _prep_ts_data(obs_data, mod_data, expvec, obsvec, loc, var2, lev2, anemometer, verbose)
        return data2plot1, data2plot2, units1, units2, description1, description2
    else:
        var = infos['var']
        lev = infos['lev']
        data2plot, units, description = _prep_ts_data(obs_data, mod_data, expvec, obsvec, loc, var, lev, anemometer, verbose)
        return data2plot, units, description


def _prep_ts_data(obs_data, mod_data, expvec: list, obsvec: list, loc: str, var: str, lev: str, anemometer: str,
                  verbose=False) -> pd.DataFrame:
    """
    Takes the data coming from my classes, selects the right data and concats
    everything into a single dataframe for easy plotting with hvplot.

    obs_data: dict of observations
    mod_data: dict of model data
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
                    # will be overwritten if mod data exists
                    units = obs_data[obs][f'P_{lev}'].units
                    description = 'air pressure'
                else:
                    tmp = myobs[f'{var}{device}_{lev}']
                    # will be overwritten if mod data exists
                    units = obs_data[obs][f'{var}{device}_{lev}'].units
                    description = var
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

            units = mymod[var].units
            description = mymod[var].standard_name

            zvec = mymod.ALT[0, :].values
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
        data2plot = pd.DataFrame({'time': [dt.datetime(1970, 1, 1), dt.datetime(2020, 1, 1)], 'data': [np.nan, np.nan]})
        data2plot = data2plot.set_index('time')

    data2plot.variable = var
    data2plot.level = lev
    data2plot.anemometer = anemometer

    return data2plot, units, description
