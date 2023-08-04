import numpy as np
from wrftamer.statistics import statistics, Statistics_xarray


def test_stats1(statistics_pd):
    test_pd, expect_pd = statistics_pd

    infos = dict()
    infos['proj_name'] = 'test'
    infos['loc'] = 'loc'
    infos['var'] = 'WSP'
    infos['lev'] = '5'
    infos['anemometer'] = 'USA'
    infos['expvec'] = ['model']
    infos['obsvec'] = ['obs']

    res = statistics(test_pd, **infos)

    if max(abs(res.values[0, 5::] - expect_pd.values[0, 5::])) > 1e-10:
        raise ValueError


def test_stats2(statistics_pd):
    test_pd, expect_pd = statistics_pd

    infos = dict()
    infos['proj_name'] = 'test'
    infos['loc'] = 'loc'
    infos['var'] = 'DIR'
    infos['lev'] = '5'
    infos['anemometer'] = 'USA'
    infos['expvec'] = ['model']
    infos['obsvec'] = ['obs']

    res = statistics(test_pd, **infos)

    if max(abs(res.values[0, 5:8] - expect_pd.values[0, 5:8])) > 1e-10:
        raise ValueError


def test_xa_stats1(statistics_xa):
    test_xa1, expect_xa1 = statistics_xa

    # Test for WSP data (testset1)
    res1 = Statistics_xarray(test_xa1)
    diff = expect_xa1 - res1
    for item in diff:
        if np.max(abs(diff[item])) > 1e-10:
            raise ValueError


def test_xa_stats2(statistics_xa):
    test_xa2, expect_xa2 = statistics_xa
    test_xa2.attrs['var'] = 'dir'

    # Test for DIR data (testset2)
    res2 = Statistics_xarray(test_xa2)
    diff = expect_xa2 - res2
    for item in diff:
        if np.max(abs(diff[item])) > 1e-10:
            raise ValueError


def test_xa_stats3(statistics_xa):
    test_xa3, expect_xa3 = statistics_xa

    ramp_marker = np.ones(test_xa3.Obs.shape)
    ramp_marker[0, 0] = 0
    ramp_marker = ramp_marker.astype(bool)
    test_xa3 = test_xa3.assign(ramp_marker=(['station_name', 'time'], ramp_marker))

    # Test for WRF data (testset3)
    res3 = Statistics_xarray(test_xa3)
    diff = expect_xa3 - res3
    for item in diff:
        if np.max(abs(diff[item])) > 1e-10:
            raise ValueError


def test_xa_stats4(statistics_xa):
    test_xa3, expect_xa3 = statistics_xa

    ramp_marker = np.ones(test_xa3.Obs.shape)
    #ramp_marker[0, 0] = 0 # otherwise, I need different results...
    ramp_marker = ramp_marker.astype(bool)
    test_xa3 = test_xa3.assign(ramp_marker=(['station_name', 'time'], ramp_marker))

    # Test for WRF data (testset3)
    res3 = Statistics_xarray(test_xa3, calc_for_ramp=1)
    diff = expect_xa3 - res3
    for item in diff:
        if np.max(abs(diff[item])) > 1e-10:
            raise ValueError


def test_xa_stats5(statistics_xa):
    test_xa3, expect_xa3 = statistics_xa

    # Test for WRF data (ramp-marker removed)
    res3 = Statistics_xarray(test_xa3, calc_for_ramp=1)
    diff = expect_xa3 - res3
    for item in diff:
        if np.max(abs(diff[item])) > 1e-10:
            raise ValueError
