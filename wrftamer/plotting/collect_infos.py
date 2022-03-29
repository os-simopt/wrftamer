import datetime as dt


def set_infos(proj_name=None, domain=None, ave=None, observation=None, device=None,
              time_to_plot=None, location=None, plottype=None, ftype=None, run=None, variable=None,
              level=None, poi=None):

    infos = dict()
    infos['proj_name'] = proj_name
    if run is None:
        infos['Expvec'] = []
    else:
        infos['Expvec'] = run

    infos['dom'] = domain
    infos['loc'] = location
    infos['anemometer'] = device
    infos['Obsvec'] = [observation]

    if ave is None:
        infos['AveChoice_WRF'] = None
        infos['AveChoice_OBS'] = None
    else:
        translate = {'raw': 0, '5 min Ave': 5, '10 min Ave': 10, '30 min Ave': 30}
        infos['AveChoice_WRF'] = translate[ave]
        infos['AveChoice_OBS'] = translate[ave]

    infos['time_to_plot'] = time_to_plot
    infos['var'] = variable
    infos['poi'] = poi
    infos['lev'] = level
    infos['ftype'] = ftype
    infos['poi'] = poi
    infos['plttype'] = plottype

    infos = derive_additional_infos(infos)

    return infos


def derive_additional_infos(infos: dict) -> dict:
    # must be called AFTER collect_information_from_XX
    plttype = infos['plttype']
    var = infos['var']
    lev = infos['lev']
    time_to_plot = infos['time_to_plot']

    # Multi timeseries
    if plttype == 'Timeseries 2':
        var1, var2 = var.split(' and ')
        lev1, lev2 = lev.split(' and ')
    else:
        var1, var2 = None, None
        lev1, lev2 = None, None

    # For FINO1. I only load 1 year. May need more at some point.
    dtstart = dt.datetime(time_to_plot.year, 1, 1)
    dtend = dt.datetime(time_to_plot.year + 1, 1, 1)

    infos['var1'] = var1
    infos['lev1'] = lev1
    infos['var2'] = var2
    infos['lev2'] = lev2

    infos['obs_load_from_to'] = (dtstart, dtend)

    return infos
