import pandas as pd
import datetime as dt

##########################################################################################
def get_coords(loc: str) -> (float, float):

    # TODO: this must be generalized as well.
    standorte = pd.read_csv('/inf/windfarms/all_windparks_nr_daniel.csv')
    AV = standorte[standorte.windpark == 'Alpha ventus']

    coords = {'FINO': (54.014861, 6.587639),
              'CSPoint1': (54.008333, 6.552019),
              'CSPoint2': (54.008333, 6.624653),
              'N/A': (-999., -999.),
              '': (-999., -999.)}

    for idx in range(0, 12):
        coords['AV' + str(idx).zfill(2)] = (AV.breitengrad[idx], AV.laengengrad[idx])

    return coords[loc]


def set_infos(proj_name=None, domain=None, ave=None, observation=None, dataset_dict = None, device=None,
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
    loc = infos['loc']
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

    # Points connected to loc and CS
    if loc == 'Default CS':
        P1 = get_coords('CSPoint1')
        P2 = get_coords('CSPoint2')
        ll = 4840.
    else:
        P1 = -999.
        P2 = -999.
        ll = -999.

    if loc is None:
        P = None
    else:
        P = get_coords(loc)

    # For FINO1. I only load 1 year. May need more at some point.
    #startdate = str(time_to_plot.year) + '0101'
    #enddate = str(time_to_plot.year + 1) + '0101'
    dtstart = dt.datetime(time_to_plot.year,1,1)
    dtend = dt.datetime(time_to_plot.year+1,1,1)

    infos['var1'] = var1
    infos['lev1'] = lev1
    infos['var2'] = var2
    infos['lev2'] = lev2
    infos['P'] = P
    infos['P1'] = P1
    infos['P2'] = P2
    infos['ll'] = ll
    #infos['startdate'] = startdate  # this is needed to load FINO-data
    #infos['enddate'] = enddate

    infos['obs_load_from_to'] = (dtstart, dtend)

    return infos

