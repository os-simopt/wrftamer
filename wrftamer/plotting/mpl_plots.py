from wrftamer.plotting.load_and_prepare import prep_profile_data, prep_ts_data, prep_zt_data
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.dates import DateFormatter
import matplotlib.cm as cm
from windrose import WindroseAxes


########################################################################################################################
#                                                 Call Plots
########################################################################################################################

def create_mpl_plot(obs_data, mod_data, infos: dict, vmin=0, vmax=30):
    # ===================================================================
    # General Stuff
    # ===================================================================
    plttype = infos['plttype']
    var = infos['var']
    Expvec = infos['Expvec']
    loc = infos['loc']

    cols = ['b', 'k', 'r', 'g', 'm', 'b', 'k', 'r', 'g', 'm']
    stys = ['-', '-', '-', '-', '-', '--', '--', '--', '--', '--']
    stys2 = ['+', '+', '+', '+', '+', 'x', 'x', 'x', 'x', 'x']

    dtmin, dtmax = infos['starttime'], infos['endtime']

    if plttype == 'Profiles':
        zmax = mod_data[Expvec[0]][loc].Z.values.max()
        zmin = mod_data[Expvec[0]][loc].Z.values.min()

        data, units, description = prep_profile_data(obs_data, mod_data, infos)

        figure = Profile(data, vmin, vmax, zmin, zmax, label=None, unit=units,
                         zunit='m', descr=description, col=cols, sty=stys)

    elif plttype == 'Obs vs Mod':
        data, units, description = prep_ts_data(obs_data, mod_data, infos)
        figure = Obs_vs_Mod(data, vmin=vmin, vmax=vmax, col=cols, sty=stys2, unit=units)

    elif plttype == 'Timeseries 1':
        data, units, description = prep_ts_data(obs_data, mod_data, infos)
        figure = TimeSeries(data, vmin, vmax, dtmin=dtmin, dtmax=dtmax, col=cols, sty=stys,
                            descr=description, unit=units)

    elif plttype == 'Timeseries 2':
        zmin, zmax = 0, 360
        data1, data2, units1, units2, description1, description2 = prep_ts_data(obs_data, mod_data, infos)
        figure = TimeSeries2(data1, data2, vmin=[vmin, zmin], vmax=[vmax, zmax], dtmin=dtmin,
                             dtmax=dtmax, col=cols, sty1=stys, sty2=None,
                             descr=[description1, description2], unit=[units1,units2])

    elif plttype == 'zt-Plot':

        data = prep_zt_data(mod_data, infos)
        zmin, zmax = data.ALT.values.min(), data.ALT.values.max()
        figure = zt(data, vmin, vmax, zmin, zmax)

    else:
        print('not yet implemented. 02')
        raise NotImplementedError

    return figure


########################################################################################################################
#                                                 Create Plots
########################################################################################################################

def CrossSection(dat_CS, xmat_CS, zmat_CS, xvec_CS, hgt_CS, PT_CS, hgt_ivg_CS,
                 unit, descr, vmin, vmax, cmap, xmin, xmax, zmin, zmax, pcmesh=False):
    """
    General Routine to Plot and interploated cross section
    """

    factor = 1.5
    figure = plt.figure(num=None, figsize=(5.8 * factor, 3.6 * factor),
                        facecolor='w', edgecolor='k')

    ax = dict()
    ax[0] = figure.add_axes([0.090, 0.1, 0.8, 0.8])
    ax[1] = figure.add_axes([0.90, 0.1, 0.025, 0.8])

    # Cross Section
    if pcmesh:
        cs = ax[0].pcolormesh(xmat_CS, zmat_CS, dat_CS, cmap=cmap, vmin=vmin, vmax=vmax)
    else:
        cs = ax[0].contourf(xmat_CS, zmat_CS, dat_CS, 100, cmap=cmap, vmin=vmin, vmax=vmax)

    # pt contours
    ptmin = np.floor(PT_CS.min())
    ptmax = np.ceil(PT_CS.max())
    pt_step = 0.5
    ptlevs = np.arange(ptmin, ptmax + pt_step, pt_step)
    ax[0].contour(xmat_CS, zmat_CS, PT_CS, ptlevs, colors='k')

    # Color bar
    cbar = mpl.colorbar.ColorbarBase(ax[1], cmap=cmap, norm=mpl.colors.Normalize(vmin=vmin, vmax=vmax))

    # Topography
    ax[0].plot(xvec_CS, hgt_CS, 'k', lw=2)
    d = np.zeros(len(hgt_CS))
    ax[0].fill_between(xvec_CS, hgt_CS, where=hgt_CS >= d, interpolate=True, color='grey')

    # Forest
    # this is NaN for no-F Experiments
    ax[0].plot(xvec_CS, hgt_ivg_CS + 5 / 1000., 'g', lw=5)

    # Limits and Labels.
    # Be aware that I am assuming km here!!!
    ax[0].set_xlim([xmin, xmax])
    ax[0].set_ylim([zmin, zmax])
    ax[0].set_ylabel('z (km)')
    ax[0].set_xlabel('hor. distance (km)')
    ax[0].set_title(descr + ' ' + r' (' + unit + ')')

    return figure


# -----------------------------------------------------------------------------------------------------------------------
def Profile(data: list, vmin, vmax, zmin, zmax, label=None, unit='', zunit='', descr='',
            figure=None, col='k', sty='-'):
    """
    # Update 4.3.2022
    # Changes to the code to work with pandas dataframes in order to work with the same data preparation methods I am
    # using for the hvplots.

    """

    # jupyterlab calls plt.show() and plt.close()
    # automatically. for this reason, it is not possible to
    # add lines to the plot by calling Plot.Profile multiple times.

    # This option works, however, from the console/program!

    mpl.rcParams.update({'font.size': 15})

    if figure is None:  # figure does not exist-> create!
        factor = 0.8
        figure = plt.figure(figsize=(8 * factor, 8 * factor), facecolor='w', edgecolor='k')
        ax = figure.add_axes([0.15, 0.15, 0.80, 0.80])
    else:
        ax = figure.gca()  # there is only one axis.

    if sty is None:
        sty = ['-' for i in range(len(data))]
    if col is None:
        col = ['k' for i in range(len(data))]

    zlabel = 'z (' + zunit + ')'
    for n, item in enumerate(data):
        ax.plot(item.iloc[:, 1], item.iloc[:, 0], linestyle=sty[n], color=col[n], label=item.iloc[:, 1].name, lw=2)

    # Limits and Labels.
    ax.set_xlim([vmin, vmax])
    ax.set_ylim([zmin, zmax])
    ax.set_ylabel(zlabel)
    ax.set_xlabel(descr + ' ' + r' (' + unit + ')')

    h, l = ax.get_legend_handles_labels()  # this should automatically add new labels.
    plt.legend(h, l)

    return figure


# -----------------------------------------------------------------------------------------------------------------------
def TimeSeries(data, vmin, vmax, dtmin, dtmax, figure=None, col=None, sty=None, label=None, descr='', unit=''):
    """
    This function plots multiple time series in a single plots.

    dtvec: dict of n datetime objects. Each may have a different lenght.
    data: dict of n data vecors to be plotted. Each may have a different lenght.

    data may contain up to n sigma_data vectors with data of the standard deviation. May plot any one of them if
    add_std is true.

    descr: list of two strings, for the titles
    unit: list of two strings, for the units
    labels: list of ndim strings, for the legend
    col: list of colors. If none: default colors
    sty: list of styles for the plot. If none: default styles

    # Improvement for the future: allow data to be of a more general type, so the whole thing works for a
    single entry as well. Otherwise, I have to convert my data to a dict for a single line plot...

    DLeuk, 25.02.2021

    # Update 04.03.2022
    # Changed to work with the same data preparation methods I am using for hvplots.

    """

    mpl.rcParams.update({'font.size': 15})

    # I may not need this anymore. Anyway: keep for now.
    if figure is None:  # figure does not exist -> create!
        factor = 1.2
        figure, ax = plt.subplots(1, 1, figsize=(5.5 * factor, 4.5 * factor), facecolor='w', edgecolor='k')
    else:
        ax = figure.gca()  # there is only one axis.

    list_of_keys = list(data.keys())

    if sty is None:
        sty = ['-' for key in list_of_keys]
    if col is None:
        col = ['k' for key in list_of_keys]
    if label is None:
        label = list_of_keys

    for n, key in enumerate(data):
        ax.plot(data[key], color=col[n], linestyle=sty[n], lw=2, label=label[n])

    ax.set_xlabel('time (UTC)')
    ax.set_ylabel(descr + ' (' + unit + ')')

    ax.set_ylim([vmin, vmax])
    ax.set_xlim([dtmin, dtmax])
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=40)

    formatter = DateFormatter('%H:%M')
    ax.xaxis.set_major_formatter(formatter)

    # legend only in the right plot.
    h, l = ax.get_legend_handles_labels()  # this should automatically add new labels.
    plt.legend(h, l)

    return figure


# -----------------------------------------------------------------------------------------------------------------------
def TimeSeries2(data1, data2, vmin, vmax, dtmin, dtmax, figure=None,
                col=None, sty1=None, sty2=None, label=None, descr=None, unit=None):
    """
    This function plots multiple time series in two plots. The time vector of the two plots is assumed to be the same

    dtvec: dict of n datetime objects. Each may have a different lenght.
    data1: dict of n data vecors to be plotted in the first panel. Each may have a different lenght.
    data2: dict of n data vecors to be plotted in the second panel. Each may have a different lenght.

    data1 and 2 may contain up to n sigma_data vectors with data of the standard deviation. May plot any one of them if
    add_std is true.

    descr: list of two strings, for the titles
    unit: list of two strings, for the units
    labels: list of ndim strings, for the legend
    col: list of colors. If none: default colors
    sty1: list of styles for the fist plot. If none: default styles
    sty2: list of styles for the second plot. If none: default styles

    # Improvement for the future: allow data to be of a more general type, so the whole thing works for a
    single entry as well. Otherwise, I have to convert my data to a dict for a single line plot...

    DLeuk, 25.02.2021

    """

    if unit is None:
        unit = ['', '']
    if descr is None:
        descr = ['', '']

    mpl.rcParams.update({'font.size': 15})

    # I may not need this anymore. Anyway: keep for now.
    if figure is None:  # figure does not exist -> create!
        factor = 1.2  # 1.4
        figure, ax = plt.subplots(1, 2, figsize=(10.5 * factor, 4.5 * factor), facecolor='w', edgecolor='k')
    else:
        ax = figure.axes

    list_of_keys = list(data1.keys())

    if sty1 is None:
        sty1 = ['-' for key in list_of_keys]
    if sty2 is None:
        sty2 = [' ' for key in list_of_keys]
    if col is None:
        col = ['k' for key in list_of_keys]
    if label is None:
        label = list_of_keys

    for n, key in enumerate(list_of_keys):
        ax[0].plot(data1[key], color=col[n], linestyle=sty1[n], lw=2)
        ax[1].plot(data2[key], color=col[n], linestyle=sty2[n], marker='.', ms=5, lw=2, label=label[n])
        # maybe I want to improve here. The second plot always has a marker.

    for ii in [0, 1]:
        ax[ii].set_xlabel('time (UTC)')
        ax[ii].set_ylabel(descr[ii] + ' (' + unit[ii] + ')')

        ax[ii].set_ylim([vmin[ii], vmax[ii]])
        ax[ii].set_xlim([dtmin, dtmax])
        plt.setp(ax[ii].xaxis.get_majorticklabels(), rotation=40)

        formatter = DateFormatter('%H:%M')
        ax[ii].xaxis.set_major_formatter(formatter)

    # legend only in the right plot.
    h, l = ax[1].get_legend_handles_labels()  # this should automatically add new labels.
    plt.legend(h, l)

    return figure


# -----------------------------------------------------------------------------------------------------------------------
def zt(data, vmin, vmax, zmin, zmax, figure=None):
    mpl.rcParams.update({'font.size': 15})

    if figure is None:  # figure does not exist-> create!
        factor = 1.2
        figure, ax = plt.subplots(1, 1, figsize=(5.5 * factor, 4.5 * factor), facecolor='w', edgecolor='k')
    else:
        ax = figure.gca()  # there is only one axis.

    zlabel = 'z (' + data.ALT.units + ')'

    plt.contourf(data.time, data.ALT, data.T, 20, vmin=vmin, vmax=vmax)

    cbar = plt.colorbar()
    cbar.set_label('(' + data.units + ')')

    ax.set_xlim([data.time[0], data.time[-1]])
    ax.set_ylim([zmin, zmax])

    plt.setp(ax.xaxis.get_majorticklabels(), rotation=40)

    formatter = DateFormatter('%H:%M')
    ax.xaxis.set_major_formatter(formatter)

    plt.title(data.standard_name)

    ax.set_xlabel('time (UTC)')
    ax.set_ylabel(zlabel)

    return figure


def Windrose(dirvec: np.ndarray, wspvec: np.ndarray, wspmax=10., savename=None, title=None, lab=None) -> None:
    """
    Create a windrose plot. NaN are removed if present. cmap: Hot
    Args:
        dirvec: vector of wind dir data
        wspvec: vector of wind speed data
        wspmax: greatest displayed wsp bin
        savename: name of the file for storage. If None: just display plot.
        title: title of the plot
        lab: label for the legend.

    Returns: None

    DLeuk, 09.02.2021

    """

    # remove nans from the data, for this is problematic
    mask = np.isnan(dirvec) | np.isnan(wspvec)
    dirvec = dirvec[~mask]
    wspvec = wspvec[~mask]

    num = np.ceil(wspmax / 10.)
    bins = np.arange(0, wspmax + num, num)

    ax = WindroseAxes.from_ax()

    ax.contourf(dirvec, wspvec, bins=bins, cmap=cm.hot, normed=True, nsector=32, edgecolor='white')
    ax.contour(dirvec, wspvec, bins=bins, colors='black', normed=True, nsector=32, edgecolor='white')
    ax.set_xticklabels(['E', 'NE', 'N', 'NW', 'W', 'SW', 'S', 'SE'])
    ax.set_legend()

    if isinstance(title, str):
        plt.title(title)

    if isinstance(savename, str):
        plt.savefig(savename, bbox_inches='tight', dpi=400)
        plt.close()


# -----------------------------------------------------------------------------------------------------------------------
def Obs_vs_Mod(data, vmin, vmax, sty=None, col=None, label=None, unit=None, figure=None):
    mpl.rcParams.update({'font.size': 15})

    # I may not need this anymore. Anyway: keep for now.
    if figure is None:  # figure does not exist -> create!
        factor = 1.2
        figure, ax = plt.subplots(1, 1, figsize=(5.5 * factor, 5.5 * factor), facecolor='w', edgecolor='k')
    else:
        ax = figure.gca()  # there is only one axis.

    list_of_keys = list(data.keys())

    obs_key = list_of_keys[0]  # assuming that obs is always the first key!
    list_of_keys = list_of_keys[1::]

    if sty is None:
        sty = ['.' for key in list_of_keys]
    if col is None:
        col = ['k' for key in list_of_keys]
    if label is None:
        label = list_of_keys
    if unit is None:
        unit = '-'

    for n, key in enumerate(list_of_keys):
        ax.plot(data[obs_key], data[key], color=col[n], ls='', marker=sty[n], ms=5, mew=1, label=label[n])

    ax.plot([vmin, vmax], [vmin, vmax], 'grey', lw=2)

    ax.set_xlabel('Obs (' + unit + ')')
    ax.set_ylabel('Mod (' + unit + ')')

    ax.set_xlim([vmin, vmax])
    ax.set_ylim([vmin, vmax])

    # legend only in the right plot.
    h, l = ax.get_legend_handles_labels()  # this should automatically add new labels.
    plt.legend(h, l)

    return figure


# -----------------------------------------------------------------------------------------------------------------------
def Availability(Avail: np.ndarray, zz: float, var: str, year: str, savename=None) -> None:
    """
    Plot data availability
    Args:
        Avail: Matrix that contains the availability data
        zz: height of the instrument
        var: variable
        year: year
        savename: if None: just display. Otherwise: save under the given name.

    Returns: None

    DLeuk, 09.02.2021

    """

    factor = 4.5
    plt.figure(num=None, figsize=(2.583 * factor, factor),
               facecolor='w', edgecolor='k')

    plt.pcolor(Avail, cmap='RdYlGn')
    plt.colorbar()
    plt.xlabel('day')
    plt.ylabel('month')
    plt.title('Data Availability (%), ' + var + ' at z=' + str(zz) + ', ' + year)

    if savename is None:
        plt.show()
    else:
        plt.savefig(savename, bbox_inches='tight', dpi=400)
        plt.close()
