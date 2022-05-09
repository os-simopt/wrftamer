import datetime as dt
import xarray as xr
import pandas as pd
import numpy as np


########################################################################################################################
#                                                  Load Data
########################################################################################################################


def load_obs_data(obs_data: dict, obs: str, dataset: str, **kwargs):
    """
    This function just loads observations from a single location and stores everything in the obs_data dict.
    """

    from wrftamer.wrfplotter_classes import Timeseries

    try:
        dtstart, dtend = kwargs["obs_load_from_to"]
    except KeyError:
        ttp = kwargs["time_to_plot"]
        dtstart = dt.datetime(ttp.year, 1, 1)
        dtend = dt.datetime(ttp.year + 1, 1, 1)

    ts = Timeseries(dataset)
    ts.read_cfconform_data(dtstart, dtend, calc_pt=True)

    if "station_name" in ts.data.dims:
        for stat in ts.data.station_name.values:
            tmp = ts.data.sel({"station_name": stat})
            if tmp["station_name"].values == obs:
                obs_data[obs] = tmp
                break
    else:
        obs_data[obs] = ts.data


def load_mod_data(mod_data: dict, exp_name: str, verbose=False, **kwargs):
    """
    This function just loads model data from a single location and stores everything in the mod_data dict.
    """

    from wrftamer.main import project

    try:
        proj_name = kwargs["proj_name"]
    except KeyError:
        proj_name = None

    dom = kwargs["dom"]
    ave_window = kwargs["AveChoice_WRF"]

    if ave_window in [0, "raw"]:
        prefix = "raw"
    else:
        prefix = "Ave" + str(ave_window) + "Min"

    proj = project(proj_name)
    workdir = proj.get_workdir(exp_name)
    list_of_locs = proj.exp_list_tslocs(exp_name, verbose=False)

    file2load = workdir / f"out/{prefix}_tslist_{dom}.nc"

    if verbose:
        print("Searching for file ", file2load)

    if file2load.is_file():
        tmp_xa = xr.open_dataset(file2load)

        tslist_data = dict()
        for dim in range(0, tmp_xa.dims["station_name"]):
            tmp = tmp_xa.isel(station_name=dim)

            loc = str(tmp.station_name.values)

            if loc in list_of_locs:
                tslist_data[loc] = tmp

            if bool(tslist_data):
                mod_data[exp_name] = tslist_data
            else:
                print("No data for Experiment ", exp_name)
                pass  # do not add empty dicts
    else:
        print("No data for Experiment", exp_name)


def load_all_obs_data(dataset, **kwargs):
    from wrftamer.wrfplotter_classes import Timeseries

    try:
        dtstart, dtend = kwargs["obs_load_from_to"]
    except KeyError:
        ttp = kwargs["time_to_plot"]

        dtstart = dt.datetime(ttp.year, 1, 1)
        dtend = dt.datetime(ttp.year + 1, 1, 1)

    ts = Timeseries(dataset)

    use_dask = kwargs.get("use_dask", True)

    ts.read_cfconform_data(dtstart, dtend, calc_pt=True, use_dask=use_dask)

    return ts.data


def load_all_mod_data(**kwargs):
    """
    Loads all data (all experiments in <list_of_exps>) for all locations and concats the data to a single dataset.

    Args:
        **kwargs:

    Returns:

    """

    from wrftamer.main import project

    try:
        proj_name = kwargs["proj_name"]
    except KeyError:
        proj_name = None

    dom = kwargs["dom"]
    ave_window = kwargs.get("AveChoice_WRF", None)
    pred_window = kwargs.get("Prediction_Range", None)

    if ave_window in [0, "raw"]:
        prefix = "raw"
    else:
        prefix = "Ave" + str(ave_window) + "Min"

    proj = project(proj_name)
    all_xa = []
    for exp_name in kwargs["Expvec"]:

        workdir = proj.get_workdir(exp_name)

        if pred_window is None:
            file2load = f"{workdir}/out/{prefix}_tslist_{dom}.nc"
        else:
            file2load = f"{workdir}/out/{pred_window}_{dom}.nc"

        tmp_xa = xr.open_dataset(file2load)
        all_xa.append(tmp_xa)
        tmp_xa.close()

    all_xa = xr.concat(all_xa, dim="time")

    return all_xa


########################################################################################################################
#                                                Data Preparation
########################################################################################################################
def get_limits_and_labels(
    plottype: str, var: str, data=None, map_data=None, units=None, description=None
):
    infos = dict()
    infos["plottype"] = plottype
    infos["var"] = var

    if plottype == "Profiles":

        infos["ylim"] = [0, np.nanmax([item.ALT.max() for item in data])]
        infos["xlim"] = [
            np.nanmin([item.iloc[:, 1].min() for item in data]),
            np.nanmax([item.iloc[:, 1].max() for item in data]),
        ]

        infos["xlabel"] = f"{description} ({units})"
        infos["ylabel"] = "z (m)"
        infos["title"] = ""
        infos["font_size"] = 15

    elif plottype == "Timeseries":

        infos["ylim"] = [
            np.floor(np.nanmin(data.min())),
            np.ceil(np.nanmax(data.max())),
        ]
        infos["tlim"] = [data.index.min(), data.index.max()]

        infos["xlabel"] = "time (UTC)"
        infos["ylabel"] = f"{description} ({units})"
        infos["title"] = ""
        infos["font_size"] = 15

    elif plottype == "Obs vs Mod":

        vmin = np.floor(np.nanmin(data.min()))
        vmax = np.ceil(np.nanmax(data.max()))

        infos["ylim"] = [vmin, vmax]
        infos["xlim"] = [vmin, vmax]

        infos["xlabel"] = f"Observation ({units})"
        infos["ylabel"] = f"Model ({units})"
        infos["title"] = ""
        infos["font_size"] = 15

    elif plottype == "zt-Plot":

        infos["clim"] = [np.floor(data.values.min()), np.ceil(data.values.max())]
        infos["ylim"] = [
            np.floor(data.indexes["ALT"].min()),
            np.ceil(data.indexes["ALT"].max()),
        ]
        infos["tlim"] = [data.indexes["time"].min(), data.indexes["time"].max()]

        infos["xlabel"] = "time (UTC)"
        infos["ylabel"] = f"z ({data.ALT.units})"
        infos["title"] = f"{data.long_name} ({data.units})"
        infos["font_size"] = 15

    elif plottype in ["Map", "MapSequence"]:

        vmin, vmax = np.floor(map_data.values.min()), np.ceil(map_data.values.max())
        cmapname = "viridis"  # standard colormap

        if map_data.name in ["DIR", "dir", "dd"]:
            vmin, vmax = 0, 360
            cmapname = "hsv"
        elif map_data.name in ["HGT", "hgt", "terrain"]:
            vmin = int(25 * round(float(vmin) / 25.0))
            vmax = int(25 * round(float(vmax) / 25.0))
            cmapname = "terrain"
        elif map_data.name == "LU_INDEX":
            vmin, vmax = 1, 3
            cmapname = "jet"

        infos["clim"] = [vmin, vmax]
        infos["xlim"] = [map_data.XLONG.values.min(), map_data.XLONG.values.max()]
        infos["ylim"] = [map_data.XLAT.values.min(), map_data.XLAT.values.max()]
        infos["xlabel"] = "longitude (°)"
        infos["ylabel"] = "latitude (°)"
        infos[
            "title"
        ] = f"{map_data.description} ({map_data.units}) at model level {map_data.model_level}"
        infos["font_size"] = 15
        infos["ticks"] = np.linspace(vmin, vmax, 10)
        infos["cmapname"] = cmapname

    return infos


# TODO: these preperation data routines have some hardcoded stuff and is strongly dependent the FINO station.
#  Need to make variable selection dynamic; need to define variable name convention
#  Need to improve these readers.
#  Also, is it really nessecary to load everything into these dicts?
#  The prep routines should be able to extract data on demand just as easily.


def prep_profile_data(
    obs_data, mod_data, infos: dict, verbose=False
) -> (list, str, str):
    """
    Takes the data coming from my classes, selects the right data and puts everyting in a list.
    In this proj_name, I cannot concat everything into a single dataframe, because the the Z-vectors are different.

    obs_data: dict of observations
    mod_data: dict of model data
    """

    # TODO: Needs some cleanup. See TODO for timeseries.

    anemometer = infos["anemometer"]
    var = infos["var"]
    loc = infos["loc"]
    time_to_plot = infos["time_to_plot"]
    ttp = np.datetime64(time_to_plot)
    expvec = infos["Expvec"]
    obsvec = infos["Obsvec"]

    # change a few parameter Names to fit the
    translator = {
        "WSP": {"Sonic": "_USA", "Analog": "_CUP"},
        "DIR": {"Sonic": "_USA", "Analog": "_VANE"},
    }
    if var in ["WSP", "DIR"]:
        device = translator.get(var, "").get(anemometer, "")
    else:
        device = ""

    data2plot = []
    for obs in obsvec:
        zvec, data = [], []
        myobs = obs_data[obs]
        myobs = myobs.where(myobs.time == ttp, drop=True)

        for key in myobs.keys():
            if var in key and "std" not in key:
                if device == "":
                    if (
                        "CUP" not in key
                        and "USA" not in key
                        and "VANE" not in key
                        and key.startswith(var + "_")
                    ):
                        zvec.append(float(key.split("_")[1]))
                        data.append(myobs[key].values[0])

                elif device in key:
                    zvec.append(float(key.rsplit("_", 1)[1]))
                    data.append(myobs[key].values[0])
                    units = myobs[key].units
                    description = var  # (standard_name contains height)

        df = pd.DataFrame({"ALT": zvec, loc: data})
        data2plot.append(df)

    for exp in expvec:
        try:
            mymod = mod_data[exp][loc]
            mymod = mymod.where(mymod.time == ttp, drop=True)
            mymod = mymod.to_dataframe()
            mymod = mymod.set_index("ALT")
            mymod = pd.DataFrame(mymod[var])
            mymod = mymod.rename(columns={var: exp})
            mymod = mymod.reset_index()
            data2plot.append(mymod)

            units = mod_data[exp][loc][var].units
            description = mod_data[exp][loc][var].standard_name

        except KeyError:
            if verbose:
                print(f"No data found for experiment {exp}")
        except IndexError:
            if verbose:
                print(f"No data found at this time: {time_to_plot}")

    return data2plot, units, description


def prep_zt_data(mod_data, infos: dict) -> xr.Dataset:
    var = infos["var"]
    loc = infos["loc"]

    key = list(mod_data.keys())[0]
    data2plot = mod_data[key][loc]

    # new_z
    new_z = mod_data[key][loc]["ALT"].mean(axis=0, keep_attrs=True)
    data2plot = data2plot.drop_vars("ALT")
    data2plot = data2plot.rename_vars({"model_level": "ALT"})

    data2plot["ALT"] = new_z
    data2plot = data2plot.swap_dims({"model_level": "ALT"})
    data2plot = data2plot.drop_vars("model_level")

    return data2plot[var]


def prep_ts_data(
    obs_data, mod_data, infos: dict, verbose=False
) -> (pd.DataFrame, str, str):
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

    # TODO:
    #  Need some cleanup with regards to description, units and what happens if I have only obs or only mods.
    #  Collect all units, and check if they are consistent; write a description which equals the one from dataset
    #  if no additional data is here, otherwise something like "var???"

    anemometer = infos["anemometer"]
    loc = infos["loc"]
    expvec = infos["Expvec"]
    obsvec = infos["Obsvec"]

    var = infos["var"]
    lev = infos["lev"]

    if len(mod_data) > 0:
        tmp_t = mod_data[list(mod_data.keys())[0]][loc].time.values
        tlim1 = pd.Timestamp(tmp_t.min())
        tlim2 = pd.Timestamp(tmp_t.max())

    # change a few parameter Names to fit the name of the obs-files
    translator = {
        "WSP": {"Sonic": "_USA", "Analog": "_CUP"},
        "DIR": {"Sonic": "_USA", "Analog": "_VANE"},
    }
    if var in ["WSP", "DIR"]:
        device = translator.get(var, "").get(anemometer, "")
    else:
        device = ""

    all_df = []

    for obs in obsvec:
        myobs = obs_data[obs].to_dataframe()
        try:
            if obs in [
                "FINO1",
                "Testset",
            ]:  # TODO: this is rather specific! Must find a way to generalize!
                if var == "PRES":
                    tmp = myobs[f"P_{lev}"]
                    # will be overwritten if mod data exists
                    units = obs_data[obs][f"P_{lev}"].units
                    description = "air pressure"
                else:
                    tmp = myobs[f"{var}{device}_{lev}"]
                    # will be overwritten if mod data exists
                    units = obs_data[obs][f"{var}{device}_{lev}"].units
                    description = var
            else:  # AV01-12
                tmp = myobs[var]  # WSP, DIR, POW, GEN_SPD

            tmp = tmp.rename(obs)

        except KeyError:
            tmp = pd.DataFrame()
            tmp.name = "Data Missing"
            units = ""
            description = "No Data"

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
            xa1 = mymod.isel(model_level=idx)
            xa2 = mymod.isel(model_level=idx + 1)
            w1 = abs(zvec[idx] - float(lev)) / abs(zvec[idx + 1] - zvec[idx])
            w2 = abs(zvec[idx + 1] - float(lev)) / abs(zvec[idx + 1] - zvec[idx])
            mymod = xa1 * w2 + xa2 * w1
            mymod = mymod.to_dataframe()

            tmp = mymod[var]
            tmp = tmp.rename(exp)
            all_df.append(tmp)

        except KeyError:
            if verbose:
                print(f"No Data for Experiment {exp}")

    if len(all_df) > 0:
        data2plot = pd.concat(all_df, axis=1)
    else:
        data2plot = pd.DataFrame(
            {
                "time": [dt.datetime(1970, 1, 1), dt.datetime(2020, 1, 1)],
                "data": [np.nan, np.nan],
            }
        )
        data2plot = data2plot.set_index("time")

    data2plot.variable = var
    data2plot.level = lev
    data2plot.anemometer = anemometer

    data2plot.proj_name = infos["proj_name"]
    data2plot.location = loc
    data2plot.Expvec = expvec
    data2plot.Obsvec = obsvec

    return data2plot, units, description
