import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.dates import DateFormatter
from windrose import WindroseAxes
import xarray as xr

try:
    # Taken from mpl_plots
    import cartopy.crs as crs
    from cartopy.feature import NaturalEarthFeature
    from wrf import get_cartopy, cartopy_xlim, cartopy_ylim

    enable_maps = True
except ModuleNotFoundError:
    enable_maps = False


########################################################################################################################
#                                                 Call Plots
########################################################################################################################


def create_mpl_plot(data, infos: dict):
    # ===================================================================
    # General Stuff
    # ===================================================================

    plottype = infos["plottype"]

    cols = ["b", "k", "r", "g", "m", "b", "k", "r", "g", "m"]
    stys = ["-", "-", "-", "-", "-", "--", "--", "--", "--", "--"]
    stys2 = ["+", "+", "+", "+", "+", "x", "x", "x", "x", "x"]

    if plottype == "Profiles":
        figure = Profile(data, col=cols, sty=stys, **infos)

    elif plottype == "Obs vs Mod":
        figure = Obs_vs_Mod(data, col=cols, sty=stys2, **infos)

    elif plottype == "Timeseries":
        figure = TimeSeries(data, col=cols, sty=stys, **infos)

    elif plottype == "zt-Plot":
        figure = zt(data, **infos)

    elif plottype == "Map":
        print("Use Class")
        figure = None

    else:
        print("not yet implemented. 02")
        raise NotImplementedError

    return figure


########################################################################################################################
#                                                 Create Plots
########################################################################################################################

"""
def CrossSection(dat_CS, xmat_CS, zmat_CS, xvec_CS, hgt_CS, PT_CS, hgt_ivg_CS, unit, descr,
                 vmin, vmax, cmap, xmin, xmax, zmin, zmax, pcmesh=False):
    '''
    General Routine to Plot and interploated cross section
    '''

    factor = 1.5
    figure = plt.figure(
        num=None, figsize=(5.8 * factor, 3.6 * factor), facecolor="w", edgecolor="k"
    )

    ax = dict()
    ax[0] = figure.add_axes([0.090, 0.1, 0.8, 0.8])
    ax[1] = figure.add_axes([0.90, 0.1, 0.025, 0.8])

    # Cross Section
    if pcmesh:
        ax[0].pcolormesh(xmat_CS, zmat_CS, dat_CS, cmap=cmap, vmin=vmin, vmax=vmax)
    else:
        ax[0].contourf(xmat_CS, zmat_CS, dat_CS, 100, cmap=cmap, vmin=vmin, vmax=vmax)

    # pt contours
    ptmin = np.floor(PT_CS.min())
    ptmax = np.ceil(PT_CS.max())
    pt_step = 0.5
    ptlevs = np.arange(ptmin, ptmax + pt_step, pt_step)
    ax[0].contour(xmat_CS, zmat_CS, PT_CS, ptlevs, colors="k")

    # Color bar
    mpl.colorbar.ColorbarBase(ax[1], cmap=cmap, norm=mpl.colors.Normalize(vmin=vmin, vmax=vmax))

    # Topography
    ax[0].plot(xvec_CS, hgt_CS, "k", lw=2)
    d = np.zeros(len(hgt_CS))
    ax[0].fill_between(
        xvec_CS, hgt_CS, where=hgt_CS >= d, interpolate=True, color="grey"
    )

    # Forest
    # this is NaN for no-F Experiments
    ax[0].plot(xvec_CS, hgt_ivg_CS + 5 / 1000.0, "g", lw=5)

    # Limits and Labels.
    # Be aware that I am assuming km here!!!
    ax[0].set_xlim([xmin, xmax])
    ax[0].set_ylim([zmin, zmax])
    ax[0].set_ylabel("z (km)")
    ax[0].set_xlabel("hor. distance (km)")
    ax[0].set_title(descr + " " + r" (" + unit + ")")

    return figure
"""


# -----------------------------------------------------------------------------------------------------------------------
def Profile(data: list, col=None, sty=None, **kwargs):
    """
    # Update 4.3.2022
    # Changes to the code to work with pandas dataframes in order to work with the same data preparation methods I am
    # using for the hvplots.
    """

    font_size = kwargs.get("font_size", 15)
    xlim = kwargs.get("xlim", (0, 1))
    ylim = kwargs.get("ylim", (0, 1))
    xlabel = kwargs.get("xlabel", "")
    ylabel = kwargs.get("ylabel", "")

    mpl.rcParams.update({"font.size": font_size})

    factor = 0.8
    figure = plt.figure(figsize=(8 * factor, 8 * factor), facecolor="w", edgecolor="k")
    ax = figure.add_axes([0.15, 0.15, 0.80, 0.80])

    if sty is None:
        sty = list(np.repeat("-", len(data)))
    if col is None:
        col = list(np.repeat("k", len(data)))

    for n, item in enumerate(data):
        ax.plot(
            item.iloc[:, 1],
            item.iloc[:, 0],
            linestyle=sty[n],
            color=col[n],
            label=item.iloc[:, 1].name,
            lw=2,
        )

    # Limits and Labels.
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)

    h, ll = ax.get_legend_handles_labels()  # this should automatically add new labels.
    plt.legend(h, ll)

    return figure


# -----------------------------------------------------------------------------------------------------------------------
def TimeSeries(data, col=None, sty=None, label=None, **kwargs):
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

    font_size = kwargs.get("font_size", 10)
    tlim = kwargs.get("tlim", (0, 1))
    ylim = kwargs.get("ylim", (0, 1))
    xlabel = kwargs.get("xlabel", "")
    ylabel = kwargs.get("ylabel", "")

    mpl.rcParams.update({"font.size": font_size})

    factor = 0.75
    figure, ax = plt.subplots(
        1, 1, figsize=(5.5 * factor, 4.5 * factor), facecolor="w", edgecolor="k"
    )

    list_of_keys = list(data.keys())

    if sty is None:
        sty = list(np.repeat("-", len(list_of_keys)))
    if col is None:
        col = list(np.repeat("k", len(list_of_keys)))
    if label is None:
        label = list_of_keys

    for n, key in enumerate(data):
        ax.plot(
            data[key].dropna(), color=col[n], linestyle=sty[n], lw=2, label=label[n]
        )

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    ax.set_ylim(ylim)
    ax.set_xlim(tlim)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=40)

    formatter = DateFormatter("%H:%M")
    ax.xaxis.set_major_formatter(formatter)

    # legend only in the right plot.
    h, ll = ax.get_legend_handles_labels()  # this should automatically add new labels.
    plt.legend(h, ll)

    return figure


# -----------------------------------------------------------------------------------------------------------------------
def zt(data, **kwargs):
    font_size = kwargs.get("font_size", 10)
    clim = kwargs.get("clim", (0, 1))
    tlim = kwargs.get("tlim", (0, 1))
    ylim = kwargs.get("ylim", (0, 1))
    xlabel = kwargs.get("xlabel", "")
    ylabel = kwargs.get("ylabel", "")

    mpl.rcParams.update({"font.size": font_size})

    factor = 0.75
    figure, ax = plt.subplots(
        1, 1, figsize=(5.5 * factor, 4.5 * factor), facecolor="w", edgecolor="k"
    )

    plt.contourf(data.time, data.ALT, data.T, 20, vmin=clim[0], vmax=clim[1])

    cbar = plt.colorbar()
    cbar.set_label("(" + data.units + ")")

    ax.set_xlim(tlim)
    ax.set_ylim(ylim)

    plt.setp(ax.xaxis.get_majorticklabels(), rotation=40)

    formatter = DateFormatter("%H:%M")
    ax.xaxis.set_major_formatter(formatter)

    plt.title(data.standard_name)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    return figure


"""
def Windrose(dirvec: np.ndarray, wspvec: np.ndarray, wspmax=10.0, savename=None, title=None) -> None:
    '''
    Create a windrose plot. NaN are removed if present. cmap: Hot
    Args:
        dirvec: vector of wind dir data
        wspvec: vector of wind speed data
        wspmax: greatest displayed wsp bin
        savename: name of the file for storage. If None: just display plot.
        title: title of the plot

    Returns: None

    DLeuk, 09.02.2021

    '''

    # remove nans from the data, for this is problematic
    mask = np.isnan(dirvec) | np.isnan(wspvec)
    dirvec = dirvec[~mask]
    wspvec = wspvec[~mask]

    num = np.ceil(wspmax / 10.0)
    bins = np.arange(0, wspmax + num, num)

    ax = WindroseAxes.from_ax()

    ax.contourf(dirvec, wspvec, bins=bins, cmap=mpl.cm.hot, normed=True, nsector=32)
    ax.contour(dirvec, wspvec, bins=bins, colors="black", normed=True, nsector=32)
    ax.set_xticklabels(["E", "NE", "N", "NW", "W", "SW", "S", "SE"])
    ax.set_legend()

    if isinstance(title, str):
        plt.title(title)

    if isinstance(savename, str):
        plt.savefig(savename, bbox_inches="tight", dpi=400)
        plt.close()
"""


# ----------------------------------------------------------------------------------------------------------------------
def Obs_vs_Mod(data, sty=None, col=None, label=None, **kwargs):
    font_size = kwargs.get("font_size", 10)
    xlim = kwargs.get("xlim", (0, 1))
    ylim = kwargs.get("ylim", (0, 1))
    xlabel = kwargs.get("xlabel", "")
    ylabel = kwargs.get("ylabel", "")

    mpl.rcParams.update({"font.size": font_size})

    factor = 0.75
    figure, ax = plt.subplots(
        1, 1, figsize=(5.5 * factor, 5.5 * factor), facecolor="w", edgecolor="k"
    )

    list_of_keys = list(data.keys())

    obs_key = list_of_keys[0]  # assuming that obs is always the first key!
    list_of_keys = list_of_keys[1::]

    if sty is None:
        sty = list(np.repeat(".", len(list_of_keys)))
    if col is None:
        col = list(np.repeat("k", len(list_of_keys)))
    if label is None:
        label = list_of_keys

    for n, key in enumerate(list_of_keys):
        ax.plot(
            data[obs_key],
            data[key],
            color=col[n],
            ls="",
            marker=sty[n],
            ms=5,
            mew=1,
            label=label[n],
        )

    ax.plot(xlim, xlim, "grey", lw=2)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    ax.set_xlim(xlim)
    ax.set_ylim(ylim)

    h, ll = ax.get_legend_handles_labels()
    plt.legend(h, ll)

    return figure


# ----------------------------------------------------------------------------------------------------------------------
def Map_Cartopy(data: xr.DataArray, hgt=None, ivg=None, pcmesh=False, **kwargs):
    if not enable_maps:
        print('You must install Cartopy to use this feature.')
        return

    font_size = kwargs.get("font_size", 10)
    clim = kwargs.get("clim", (0, 1))
    xlabel = kwargs.get("xlabel", "")
    ylabel = kwargs.get("ylabel", "")
    title = kwargs.get("title", "")
    factor = kwargs.get("size_factor", 1.0)
    cmap = kwargs.get("cmapname", "viridis")
    myticks = kwargs.get("myticks", np.linspace(clim[0], clim[1], 10))
    points_to_mark = kwargs.get("poi", None)

    lat = data.XLAT.values
    lon = data.XLONG.values
    var = data.name

    mpl.rcParams.update({"font.size": font_size})

    fig = plt.figure(
        num=None, figsize=(5.5 * factor, 4.5 * factor), facecolor="w", edgecolor="k"
    )

    cart_proj = get_cartopy(hgt)
    ax = plt.axes(projection=cart_proj)

    states = NaturalEarthFeature(
        category="cultural", scale="50m", facecolor="none", name="admin_0_countries"
    )  # admin_1_states_provinces_shp
    ax.add_feature(states, linewidth=0.5, edgecolor="black")
    ax.coastlines("50m", linewidth=0.8)

    if pcmesh:
        cs = plt.pcolormesh(
            lon,
            lat,
            data.values,
            vmin=clim[0],
            vmax=clim[1],
            cmap=cmap,
            transform=crs.PlateCarree(),
        )
    else:
        cs = plt.contourf(
            lon,
            lat,
            data.values,
            25,
            vmin=clim[0],
            vmax=clim[1],
            cmap=cmap,
            transform=crs.PlateCarree(),
        )

    # Colorbar
    plt.clim(clim)
    plt.colorbar(
        cs, ax=ax, orientation="vertical", pad=0.02, ticks=myticks, shrink=0.83
    )

    # Topography overlay.
    if hgt is not None:
        # Add topography
        hlines = np.arange(0, 1050, 50)
        plt.contour(
            lon,
            lat,
            hgt.values,
            levels=hlines,
            colors="grey",
            transform=crs.PlateCarree(),
            alpha=0.5,
        )

    if ivg is not None:
        plt.contourf(
            lon,
            lat,
            ivg.values,
            hatches=["."],
            colors="none",
            transform=crs.PlateCarree(),
        )

    # Marking the position of points of interest
    if points_to_mark is not None:  # TODO: This needs some cleanup
        for index in points_to_mark.index:
            plt.plot(
                points_to_mark.lon[index],
                points_to_mark.lat[index],
                "+",
                ms=10,
                mew=2,
                color="k",
                transform=crs.PlateCarree(),
            )

    # Set the map bounds
    ax.set_xlim(cartopy_xlim(data))
    ax.set_ylim(cartopy_ylim(data))
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    gl = ax.gridlines(
        transform=crs.PlateCarree(),
        draw_labels=True,
        linewidth=1,
        x_inline=False,
        y_inline=False,
        ls="--",
    )

    gl.top_labels = False
    gl.right_labels = False
    plt.title(title)

    return fig


# ----------------------------------------------------------------------------------------------------------------------
def Availability(
        Avail: np.ndarray, zz: float, var: str, year: str, savename=None
) -> None:
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

    xvec = np.arange(1, 33)
    yvec = np.arange(1, 14)
    xticks = np.arange(5.5, 35.5, 5)
    yticks = np.arange(2.5, 14.5, 2)

    xtick_labels = np.arange(5, 35, 5)
    ytick_labels = np.arange(2, 14, 2)

    factor = 4.5
    plt.figure(num=None, figsize=(2.583 * factor, factor), facecolor="w", edgecolor="k")
    ax1 = plt.subplot(111)

    ax1.set_xticks(xticks)
    ax1.set_yticks(yticks)

    ax1.set_xticklabels(xtick_labels, fontsize=15)
    ax1.set_yticklabels(ytick_labels, fontsize=15)

    plt.pcolor(xvec, yvec, Avail, cmap="RdYlGn", vmin=0, vmax=100)
    plt.colorbar()
    plt.xlabel("day", fontsize=20)
    plt.ylabel("month", fontsize=20)
    plt.title(
        "Data Availability (%), " + var + " at z=" + str(zz) + ", " + year, fontsize=15
    )

    if savename is None:
        plt.show()
    else:
        plt.savefig(savename + ".svg", bbox_inches="tight")
        plt.close()
