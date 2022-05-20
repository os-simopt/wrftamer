import os
from pathlib import Path, PosixPath
import xarray as xr
import panel as pn
import datetime as dt
import pandas as pd
from wrftamer.main import project
import yaml


def get_available_obs() -> (dict, list):
    """
    This little function looks in OBSERVATIONS_PATH for directories (which should contain netcdf files with
    cf-conform observations (TimeSeries).

    If looks for station names in all files and return a list of all stations and returns a list of stations
    and a dictionary mapping a station to the correct directory.

    Pitfall: Station names may not appear in multiple datasets!

    Returns:
        dict with mapping of station to dataset
        list of all available stations
    """
    list_of_dirs = list(Path(os.environ["OBSERVATIONS_PATH"]).glob("*"))
    datasets = [item.stem for item in list_of_dirs]

    dataset_dict = dict()
    list_of_obs = []
    for idx, mydir in enumerate(list_of_dirs):

        one_file = list(mydir.glob("*.nc"))[0]
        xa = xr.open_dataset(one_file)

        if xa.station_name.values.size == 1:
            list_of_stations = [str(xa.station_name.values)]
        else:
            list_of_stations = list(xa.station_name.values)

        xa.close()

        for station in list_of_stations:
            dataset_dict[station] = datasets[idx]
            list_of_obs.append(station)

        list_of_obs = list(set(list_of_obs))
        list_of_obs.sort()

    # Add option to select no obs
    dataset_dict[''] = None
    tmp = ['']
    tmp.extend(list_of_obs)
    list_of_obs = tmp

    return dataset_dict, list_of_obs


def get_available_tvec(proj_name, exp_name):
    proj = project(proj_name)
    start, end = proj.exp_start_end(exp_name)

    diff = end - start

    if diff > dt.timedelta(days=365 * 10):
        freq = 'A'
    elif diff > dt.timedelta(days=365):
        freq = '1m'
    elif diff >= dt.timedelta(days=28):
        freq = '7d'
    elif diff >= dt.timedelta(days=5):
        freq = '1d'
    elif diff >= dt.timedelta(days=1):
        freq = '3h'
    elif diff >= dt.timedelta(hours=6):
        freq = '1h'
    elif diff >= dt.timedelta(hours=1):
        freq = '10min'
    else:
        freq = '1min'

    timevec = pd.date_range(start, end, freq=freq)
    timevec = list(timevec.to_pydatetime())

    return timevec


def get_available_doms(proj_name):
    max_dom = 1
    proj = project(proj_name)
    list_of_proj = proj.list_exp(False)
    for exp_name in list_of_proj:
        max_dom = proj.exp_get_maxdom_from_config(exp_name)
        if max_dom is not None:
            max_dom = max(1, max_dom)
        else:
            max_dom = 0

    list_of_doms = ["d" + str(i).zfill(2) for i in range(1, max_dom + 1)]
    return list_of_doms


def get_vars_per_plottype() -> dict:
    """
    I am assuming here standard wrf and meteorological variables to be present. This way, I do not have to
    open and read a file to gather information I expect anyway (i.e. from tslists)

    Returns: a dict of variables for each plot type.

    """

    standard_list = ["WSP", "DIR", "T", "PT", 'PRES']
    map_list = ["WSP", "DIR", "PT", "PRES", "PSFC", "U", "V", "W", "HFX", "GRDFLX", "LH", "HGT"]

    vars_per_plottype = dict()
    vars_per_plottype["Profiles"] = standard_list
    vars_per_plottype["zt-Plot"] = standard_list
    vars_per_plottype["Obs vs Mod"] = standard_list
    vars_per_plottype["Timeseries"] = standard_list
    vars_per_plottype["Map"] = map_list
    vars_per_plottype["MapSequence"] = map_list
    vars_per_plottype["Diff Map"] = map_list
    vars_per_plottype["CS"] = map_list
    vars_per_plottype["Diff CS"] = map_list
    vars_per_plottype["Histogram"] = standard_list
    vars_per_plottype["Windrose"] = ["WSP"]

    return vars_per_plottype


def get_lev_per_plottype_and_var(levs_per_vars_file: str) -> dict:
    standard_list = ["WSP", "DIR", "T", "PT", 'PRES']
    empty_dict = dict()
    for item in standard_list:
        empty_dict[item] = []

    with open(levs_per_vars_file) as f:
        cfg = yaml.safe_load(f)

    ts_dict = cfg['timeseries-like']
    map_dict = cfg['map-like']

    lev_per_plottype_and_var = dict()
    lev_per_plottype_and_var["Profiles"] = empty_dict
    lev_per_plottype_and_var["zt-Plot"] = empty_dict

    lev_per_plottype_and_var["Obs vs Mod"] = ts_dict
    lev_per_plottype_and_var["Timeseries"] = ts_dict
    lev_per_plottype_and_var["Map"] = map_dict
    lev_per_plottype_and_var["MapSequence"] = map_dict
    lev_per_plottype_and_var["Diff Map"] = map_dict
    lev_per_plottype_and_var["CS"] = map_dict
    lev_per_plottype_and_var["Diff CS"] = map_dict

    lev_per_plottype_and_var["Histogram"] = ts_dict
    lev_per_plottype_and_var["Windrose"] = ts_dict

    return lev_per_plottype_and_var


def get_newfilename_from_old(current_filename: PosixPath, delta_t: int):
    """
    Takes a filename of the form path/to/Map_d0X_VAR_YYYYMMDD_HHMMSS_mlY.png and creates a new
    filename (with increased or decreased time.

    current_filename: PosixPath of the current file
    delta_t: increase or decrease of time in minutes (may be negative)

    returns: new_filename ( if the file exists, otherwise current_filename)
    """

    timestamp = "_".join(current_filename.stem.split("_")[3:5])
    dtobj = dt.datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
    dtobj = dtobj + dt.timedelta(minutes=delta_t)
    timestamp2 = dtobj.strftime("%Y%m%d_%H%M%S")

    parts = current_filename.stem.split("_")
    parts[3] = timestamp2.split("_")[0]
    parts[4] = timestamp2.split("_")[1]
    new_filename = current_filename.parent / ("_".join(parts) + current_filename.suffix)

    if new_filename.is_file():
        return new_filename
    else:
        return current_filename


def error_message(message):
    md_pane = pn.pane.Markdown(
        f"""
        **Plot cannot be created.**

        Select parameters and click *Load data*.

        Error: {message}
        """,
        width=600,
    )
    return md_pane


def error_message2(filename):
    md_pane = pn.pane.Markdown(
        f"""
        **Not able to find file**.

        {filename}
        """,
        width=600,
    )
    return md_pane
