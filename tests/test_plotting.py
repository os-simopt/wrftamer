import pytest
from wrftamer.plotting.load_and_prepare import (
    load_obs_data,
    load_mod_data,
    load_all_mod_data,
    load_all_obs_data,
    prep_ts_data,
    prep_zt_data,
    prep_profile_data,
    get_limits_and_labels,
    prep_windrose_data
)
from wrftamer.plotting.mpl_plots import create_mpl_plot, Profile, TimeSeries, Obs_vs_Mod, Histogram
from wrftamer.plotting.hv_plots import create_hv_plot


def test_load_obs_data2(infos):
    for info_item in infos:
        obs = "FINO1"
        dataset = "Testset2"

        data = dict()
        load_obs_data(data, obs, dataset, **info_item)


def test_load_all_obs(infos):
    for info_item in infos:
        load_all_obs_data("Testset", **info_item)


def test_load_all_mod(infos):
    for info_item in infos:
        load_all_mod_data(**info_item)

    info_item = infos[0]
    info_item["AveChoice_WRF"] = "raw"
    load_all_mod_data(**info_item)


def test_mod_data(infos):
    for info_item in infos:
        exp_name = info_item["Expvec"][0]
        info_item["AveChoice_WRF"] = "raw"

        data = dict()
        load_mod_data(data, exp_name, **info_item)

        info_item["AveChoice_WRF"] = "10"
        info_item["Expvec"] = [exp_name, "TEST2"]


def test_mpl_timeseries(infos, obs_data, mod_data):
    maxnum = len(infos)

    for ii in range(0, maxnum):
        var = infos[ii]["var"]
        plottype = "Timeseries"
        infos[ii]["plottype"] = plottype

        data, units, description = prep_ts_data(obs_data[ii], mod_data[ii], infos[ii])
        plot_infos = get_limits_and_labels(plottype, var, data, units=units, description=description)

        create_mpl_plot(data, plot_infos)

        TimeSeries(data, label="somelabel", **plot_infos)


def test_hv_timeseries(infos, obs_data, mod_data):
    maxnum = len(infos)

    for ii in range(0, maxnum):
        var = infos[ii]["var"]
        plottype = "Timeseries"
        infos[ii]["plottype"] = plottype

        data, units, description = prep_ts_data(obs_data[ii], mod_data[ii], infos[ii])
        plot_infos = get_limits_and_labels(plottype, var, data, units=units, description=description)

        plot_infos["Expvec"] = infos[ii]["Expvec"]
        plot_infos["Obsvec"] = infos[ii]["Obsvec"]
        plot_infos['proj_name'] = infos[ii]['proj_name']
        plot_infos['loc'] = infos[ii]['loc']
        plot_infos['lev'] = infos[ii]['lev']
        plot_infos['anemometer'] = infos[ii]['anemometer']

        create_hv_plot(plot_infos, data=data)


def test_mpl_histogram(infos, obs_data, mod_data):
    maxnum = len(infos)

    for ii in range(0, maxnum):
        var = infos[ii]["var"]
        plottype = "Histogram"
        infos[ii]["plottype"] = plottype

        data, units, description = prep_ts_data(obs_data[ii], mod_data[ii], infos[ii])
        plot_infos = get_limits_and_labels(plottype, var, data, units=units, description=description)

        plot_infos["Expvec"] = infos[ii]["Expvec"]
        plot_infos["Obsvec"] = infos[ii]["Obsvec"]
        plot_infos['proj_name'] = infos[ii]['proj_name']
        plot_infos['loc'] = infos[ii]['loc']
        plot_infos['lev'] = infos[ii]['lev']
        plot_infos['anemometer'] = infos[ii]['anemometer']

        create_mpl_plot(data, plot_infos)

        Histogram(data=data, **plot_infos)


def test_hv_histogram(infos, obs_data, mod_data):
    maxnum = len(infos)

    for ii in range(0, maxnum):
        var = infos[ii]["var"]
        plottype = "Histogram"
        infos[ii]["plottype"] = plottype

        data, units, description = prep_ts_data(obs_data[ii], mod_data[ii], infos[ii])
        plot_infos = get_limits_and_labels(plottype, var, data, units=units, description=description)

        plot_infos["Expvec"] = infos[ii]["Expvec"]
        plot_infos["Obsvec"] = infos[ii]["Obsvec"]
        plot_infos['proj_name'] = infos[ii]['proj_name']
        plot_infos['loc'] = infos[ii]['loc']
        plot_infos['lev'] = infos[ii]['lev']
        plot_infos['anemometer'] = infos[ii]['anemometer']

        create_hv_plot(plot_infos, data=data)


def test_mpl_profiles(infos, obs_data, mod_data):
    maxnum = len(infos)

    for ii in range(0, maxnum):
        var = infos[ii]["var"]
        plottype = "Profiles"
        infos[ii]["plottype"] = plottype

        data, units, description = prep_profile_data(obs_data[ii], mod_data[ii], infos[ii])
        plot_infos = get_limits_and_labels(plottype, var, data, units=units, description=description)

        create_mpl_plot(data, plot_infos)

        Profile(data, **plot_infos)


def test_hv_profiles(infos, obs_data, mod_data):
    maxnum = len(infos)

    for ii in range(0, maxnum):
        var = infos[ii]["var"]
        plottype = "Profiles"
        infos[ii]["plottype"] = plottype

        data, units, description = prep_profile_data(
            obs_data[ii], mod_data[ii], infos[ii]
        )
        plot_infos = get_limits_and_labels(
            plottype, var, data, units=units, description=description
        )

        create_hv_plot(plot_infos, data=data)


def test_mpl_ztPlot(infos, mod_data):
    maxnum = len(infos)

    for ii in range(0, maxnum):
        var = infos[ii]["var"]
        plottype = "zt-Plot"
        infos[ii]["plottype"] = plottype
        data = prep_zt_data(mod_data[ii], infos[ii])

        plot_infos = get_limits_and_labels(plottype, var, data)
        create_mpl_plot(data=data, infos=plot_infos)


def test_hv_ztPlot(infos, mod_data):
    maxnum = len(infos)

    for ii in range(0, maxnum):
        var = infos[ii]["var"]
        plottype = "zt-Plot"
        infos[ii]["plottype"] = plottype
        data = prep_zt_data(mod_data[ii], infos[ii])

        plot_infos = get_limits_and_labels(plottype, var, data)
        create_hv_plot(data=data, infos=plot_infos)


def test_mpl_obs_vs_mod(infos, obs_data, mod_data):
    maxnum = len(infos)

    for ii in range(0, maxnum):
        var = infos[ii]["var"]
        plottype = "Obs vs Mod"
        infos[ii]["plottype"] = plottype

        data, units, description = prep_ts_data(obs_data[ii], mod_data[ii], infos[ii])
        plot_infos = get_limits_and_labels(
            plottype, var, data, units=units, description=description
        )

        create_mpl_plot(data, plot_infos)

        Obs_vs_Mod(data, label="somelabel", **plot_infos)


def test_hv_obs_vs_mod(infos, obs_data, mod_data):
    maxnum = len(infos)

    for ii in range(0, maxnum):
        var = infos[ii]["var"]
        plottype = "Obs vs Mod"
        infos[ii]["plottype"] = plottype

        data, units, description = prep_ts_data(obs_data[ii], mod_data[ii], infos[ii])
        plot_infos = get_limits_and_labels(
            plottype, var, data, units=units, description=description
        )

        plot_infos["Expvec"] = infos[ii]["Expvec"]
        plot_infos["Obsvec"] = infos[ii]["Obsvec"]
        plot_infos['proj_name'] = infos[ii]['proj_name']
        plot_infos['loc'] = infos[ii]['loc']
        plot_infos['lev'] = infos[ii]['lev']
        plot_infos['anemometer'] = infos[ii]['anemometer']

        create_hv_plot(data=data, infos=plot_infos)


def test_mpl_not_implemented():
    plot_infos = {"plottype": "Some Random Plot"}
    data = [0]

    with pytest.raises(NotImplementedError):
        create_mpl_plot(data, plot_infos)

    plot_infos = {"plottype": "Map", "var": "WSP"}  # will just inform user
    create_mpl_plot(data, plot_infos)


def test_hv_not_implemented():
    plot_infos = {"plottype": "Some Random Plot", "var": "WSP"}
    data = [0]

    # with pytest.raises(NotImplementedError):
    create_hv_plot(plot_infos, data)  # this one just drops a message...

    plot_infos = {"plottype": "Map", "var": "WSP"}  # will just inform user
    create_hv_plot(plot_infos, map_data=None)

def test_mpl_windrose(infos, obs_data, mod_data):

    maxnum = len(infos)

    for ii in range(0, maxnum):

        var = 'WSP'
        plottype = "Windrose"
        infos[ii]["plottype"] = plottype

        data, units, description = prep_windrose_data(obs_data[ii], mod_data[ii], infos[ii])
        plot_infos = get_limits_and_labels(plottype, var, data, units=units, description=description)

        plot_infos["Expvec"] = infos[ii]["Expvec"]
        plot_infos["Obsvec"] = infos[ii]["Obsvec"]
        plot_infos['proj_name'] = infos[ii]['proj_name']
        plot_infos['loc'] = infos[ii]['loc']
        plot_infos['lev'] = infos[ii]['lev']
        plot_infos['anemometer'] = infos[ii]['anemometer']

        create_mpl_plot(data=data, infos=plot_infos)