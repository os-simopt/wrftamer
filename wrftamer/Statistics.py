import numpy as np
import pandas as pd
import xarray as xr


def _StatCalc(obs, mod):
    bias = np.nanmean(mod - obs)
    std_err = np.nanstd(mod - obs)
    mae = np.nanmean(abs(mod - obs))
    # mape = np.nanmean(abs((obs - mod) / mod)) * 100. # old def. leads to inf if mod==0.

    tmp = abs((obs - mod) / mod)
    tmp[np.isinf(tmp)] = np.nan
    mape = np.nanmean(tmp) * 100

    # both obs and mod time series may contain Nan.
    # For correlation calculation, sett all data to NaN that is NaN in either timeseries.

    tmp_obs = np.copy(obs)
    tmp_mod = np.copy(mod)

    tmp_obs[np.isnan(tmp_mod)] = np.nan
    tmp_mod[np.isnan(tmp_obs)] = np.nan

    a = np.nansum((tmp_mod - np.nanmean(tmp_mod)) * (tmp_obs - np.nanmean(tmp_obs)))
    b = np.sqrt(np.nansum((tmp_mod - np.nanmean(tmp_mod)) ** 2))
    c = np.sqrt(np.nansum((tmp_obs - np.nanmean(tmp_obs)) ** 2))

    r = a / (b * c) * 100.0  # Pearson correlation coeff.

    rmse = np.sqrt(np.nanmean((tmp_obs - tmp_mod) ** 2))

    return bias, std_err, mae, r, mape, rmse


def _StatCalc_dir(obs, mod):
    tmp = mod - obs
    tmp[tmp > 180] -= 360.0
    tmp[tmp < -180] += 360.0
    bias = np.nanmean(tmp)
    std_err = np.nanstd(tmp)
    mae = np.nanmean(abs(tmp))

    mape = np.nan
    r = np.nan

    rmse = np.sqrt(np.nanmean((obs - mod) ** 2))

    return bias, std_err, mae, r, mape, rmse


##########################################################################
def Statistics(input_dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    The new Statistics Function. It takes the same data as the obs_vs_mod plot
    and calculates statistics. Attention! Assumes that the first column is the OBS!

    input_dataframe: a pandas DataFrame with Observations and Model data for a given Case, run, location and
    observation level. Future versions of this function should be able to deal with variations. Right now,
    there is little reason to add this functionality though.

    DLeuk, 30.09.2021
    """

    # Metadata bound to dataframe.
    proj_name = input_dataframe.proj_name
    loc = input_dataframe.location
    var = input_dataframe.variable
    lev = input_dataframe.level
    Obs_device = input_dataframe.anemometer
    Expvec = input_dataframe.Expvec
    Obsvec = input_dataframe.Obsvec

    # Calculation
    obsname = Obsvec[0]
    modnames = Expvec

    Stats = np.zeros([6, len(modnames)])

    obs = input_dataframe[obsname]

    for mm, modname in enumerate(modnames):
        mod = input_dataframe[modname]
        if var == "DIR":
            Stats[:, mm] = _StatCalc_dir(obs, mod)
        else:
            Stats[:, mm] = _StatCalc(obs, mod)

    d = {
        "Mod": Expvec,
        "Obs": [loc for x in range(len(modnames))],
        "Device": [Obs_device for x in range(len(modnames))],
        "Variable": [var for x in range(len(modnames))],
        "zlev": lev,
        "BIAS": Stats[0, :],
        "STD(ERR)": Stats[1, :],
        "MAE": Stats[2, :],
        "CorCo": Stats[3, :],
        "MAPE": Stats[4, :],
        "RMSE": Stats[5, :],
    }

    Stats = pd.DataFrame(d)

    # Here is metadata that typically does not vary.
    Stats.case = proj_name
    Stats.device = Obs_device

    return Stats

    ##########################################################################


def Statistics_xarray(input_ds: xr.Dataset, calc_for_ramp=0) -> xr.Dataset:
    """
    This statistics function calculates the usual statistics for a dataset consisting of
    a number timeseries at station_name locations. These time series represent model runs.
    One of these timeseries MUST contain Observation data, taken as truth for the statistics.
    It must be called "Obs" and be a function of time and station_name as well.

    Optional: if one of the data variables is called ramp_marker and calc_for_ramp=True, the statistics are
    calculated for ramp events.
    """

    if "exp_name" in input_ds.dims and "station_name" not in input_ds.dims:
        input_ds = input_ds.rename({"exp_name": "station_name"})
        rename = True
    else:
        rename = False

    is_dir = input_ds.attrs["var"] in ["dir", "wdir", "DIR", "dd"]

    obsname = "Obs"
    mod_names = list(input_ds.data_vars.keys())
    mod_names.remove(obsname)
    if "ramp_marker" in mod_names:
        ramp = input_ds["ramp_marker"]
        mod_names.remove("ramp_marker")
    elif calc_for_ramp:
        print("ramp_marker not found in dataset. Setting for_ramp to false.")
        calc_for_ramp = 0

    station_names = input_ds.station_name.values

    Stats = np.zeros([6, len(mod_names), len(station_names)])

    for ss, station_name in enumerate(station_names):

        if calc_for_ramp:
            obs = input_ds[obsname][ss, :][ramp[ss, :]].values
        else:
            obs = input_ds[obsname][ss, :].values

        for mm, modname in enumerate(mod_names):

            if calc_for_ramp:
                mod = input_ds[modname][ss, :][ramp[ss, :]].values
            else:
                mod = input_ds[modname][ss, :].values

            if is_dir:
                Stats[:, mm, ss] = _StatCalc_dir(obs, mod)
            else:
                Stats[:, mm, ss] = _StatCalc(obs, mod)

    dims = ["mod_name", "station_name"]

    Stats = xr.Dataset(
        {
            "bias": (dims, Stats[0, :, :]),
            "std": (dims, Stats[1, :, :]),
            "mae": (dims, Stats[2, :, :]),
            "CorCo": (dims, Stats[3, :, :]),
            "mape": (dims, Stats[4, :, :]),
            "rmse": (dims, Stats[5, :, :]),
        },
        coords={"mod_name": mod_names, "station_name": station_names},
    )

    Stats.attrs = input_ds.attrs
    Stats.attrs["calc_for_ramp"] = calc_for_ramp

    if rename:
        Stats = Stats.rename({"station_name": "exp_name"})

    return Stats
