import pytest
import pandas as pd
import os
import xarray as xr
import numpy as np
from wrftamer.Statistics import Statistics, Statistics_xarray

# fails

data_path = os.path.split(os.path.realpath(__file__))[0] + "/resources/"
test_pd = pd.read_csv(data_path + "testdata.csv")
expect_pd = pd.read_csv(data_path + "testres.csv", index_col=0)


# test_xa1 = xr.load_dataset(data_path + "testset1.nc")
# test_xa2 = xr.load_dataset(data_path + "testset2.nc")
# test_xa3 = xr.load_dataset(data_path + "testset3.nc")
# test_xa4 = test_xa3.drop_vars("ramp_marker")
# expect_xa1 = xr.load_dataset(data_path + "testres1.nc")
# expect_xa2 = xr.load_dataset(data_path + "testres2.nc")
# expect_xa3 = xr.load_dataset(data_path + "testres3.nc")
# expect_xa4 = xr.load_dataset(data_path + "testres4.nc")


@pytest.mark.wip
def test_stats1():
    infos = dict()
    infos['proj_name'] = 'test'
    infos['loc'] = 'loc'
    infos['var'] = 'WSP'
    infos['lev'] = '5'
    infos['anemometer'] = 'USA'
    infos['Expvec'] = ['model']
    infos['Obsvec'] = ['obs']

    res = Statistics(test_pd, **infos)

    if max(abs(res.values[0, 5::] - expect_pd.values[0, 5::])) > 1e-10:
        raise ValueError


@pytest.mark.wip
def test_stats2():
    infos = dict()
    infos['proj_name'] = 'test'
    infos['loc'] = 'loc'
    infos['var'] = 'DIR'
    infos['lev'] = '5'
    infos['anemometer'] = 'USA'
    infos['Expvec'] = ['model']
    infos['Obsvec'] = ['obs']

    res = Statistics(test_pd, **infos)

    if max(abs(res.values[0, 5:8] - expect_pd.values[0, 5:8])) > 1e-10:
        raise ValueError


@pytest.mark.wip
def test_xa_stats1():
    # Test for WSP data (testset1)
    res1 = Statistics_xarray(test_xa1)
    diff = expect_xa1 - res1
    for item in diff:
        if np.max(abs(diff[item])) > 1e-10:
            raise ValueError


@pytest.mark.wip
def test_xa_stats2():
    # Test for DIR data (testset2)
    res2 = Statistics_xarray(test_xa2)
    diff = expect_xa2 - res2
    for item in diff:
        if np.max(abs(diff[item])) > 1e-10:
            raise ValueError


@pytest.mark.wip
def test_xa_stats3():
    # Test for WRF data (testset3)
    res3 = Statistics_xarray(test_xa3)
    diff = expect_xa3 - res3
    for item in diff:
        if np.max(abs(diff[item])) > 1e-10:
            raise ValueError


@pytest.mark.wip
def test_xa_stats4():
    # Test for WRF data (ramp-marker code)
    res4 = Statistics_xarray(test_xa3, calc_for_ramp=1)
    diff = expect_xa4 - res4
    for item in diff:
        if np.max(abs(diff[item])) > 1e-10:
            raise ValueError


@pytest.mark.wip
def test_xa_stats5():
    # Test for WRF data (ramp-marker removed)
    res4 = Statistics_xarray(test_xa4, calc_for_ramp=1)
    diff = expect_xa3 - res4
    for item in diff:
        if np.max(abs(diff[item])) > 1e-10:
            raise ValueError
