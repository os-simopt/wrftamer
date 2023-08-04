import pytest
import os
import shutil
import pandas as pd
from pathlib import Path
import xarray as xr
import numpy as np

os.environ['wrftamer_test_mode'] = 'True'

from wrftamer.main import Project
from wrftamer import test_res_path


@pytest.fixture
def base_test_env():
    """
    Creates a directory for testing purposes. This directory is removed after tests are completed.
    """

    test_env = Path(os.environ['HOME']) / 'wrftamer_test_tmpdir'

    if test_env.is_dir():
        shutil.rmtree(test_env)
    os.mkdir(test_env)

    os.environ["OBSERVATIONS_PATH"] = str(test_res_path / "observations_data/")

    yield test_env

    shutil.rmtree(test_env)


@pytest.fixture()
def testprojects(base_test_env):
    # I am assuming, that create and remove always work. If not, this fixture will fail (and all tests using it).
    # Create project and experiment

    proj_name1 = "WRFTAMER_TEST1"
    proj_name2 = "WRFTAMER_TEST2"
    test1 = Project(proj_name1)
    test2 = Project(proj_name2)

    test1.create(verbose=True)
    test2.create(verbose=True)

    yield test1, test2

    test1.remove(force=True, verbose=True)
    test2.remove(force=True, verbose=True)


@pytest.fixture()
def unassociated_exps(base_test_env):
    # I am assuming, that create and remove always work. If not, this fixture will fail (and all tests using it).

    # Create Project and experiment
    proj_name = None
    test = Project(proj_name)

    # checks itself for files being created. Raises FileNotFoundError on failure
    test.create(verbose=True)

    yield test

    test.remove(force=True, verbose=True)


@pytest.fixture()
def test_env2(testprojects):
    testproject1 = testprojects[0]

    exp_name1 = "TEST1"

    # ------------------------------------------------------
    # adding an exp to a project should work fine.
    configfile = test_res_path / 'configure_test.yaml'

    testproject1.exp_create(exp_name1, "First Experiment", configfile, verbose=True)

    # copy dummy data
    source = test_res_path / 'dummy_data'

    target = testproject1.proj_path / exp_name1 / "wrf"
    for item in source.glob("*"):
        shutil.copy(item, target)

    yield testproject1, exp_name1


@pytest.fixture
def link_environment(base_test_env):
    os.makedirs(base_test_env / "wrf")
    os.makedirs(base_test_env / "out")

    # create some "leftover" GRIBFILES in the wrf dir.
    with open(base_test_env / "wrf/GRIBFILE.AAA", "w") as f:
        f.write("somedata\n")

    driving_data = test_res_path / "driving_data"

    yield driving_data, base_test_env


# ----------------------------------------------------------------------------------------------------------------------


@pytest.fixture()
def tslist_environment(base_test_env):
    # This function creates directories, links test data and yields
    # The fixture ensures that the environment will always be torn down after tests.
    # However, if the code in the fixture reaches an error, this is no longer the case.
    # For this reason, test project and experiment first!

    # Create project and experiment
    proj_name = "WRFTAMER_TEST"
    exp_name = "TEST1"
    configfile = test_res_path / "configure_test.yaml"

    test = Project(proj_name)  # initialize class
    test.create(verbose=False)
    test.exp_create(exp_name, "First Experiment", configfile, verbose=False)
    workdir = test.get_workdir(exp_name)

    # Processing of data takes a while, so just link.
    # For plot tests, this is fine
    os.symlink(
        test_res_path / "model_data/tsfiles_20211206_094418",
        workdir / "out/tsfiles_20211206_094418",
    )

    os.symlink(
        test_res_path / "model_data/tsfiles_20211206_194418",
        workdir / "out/tsfiles_20211206_194418",
    )

    yield test, exp_name

    # Teardown of test
    test.remove(force=True, verbose=False)


# ----------------------------------------------------------------------------------------------------------------------
# wrftamer_functions environment

@pytest.fixture
def functions_environment(base_test_env):
    test_exp_path = base_test_env / "Test_Experiment"

    os.makedirs(test_exp_path / "wrf")
    os.makedirs(test_exp_path / "out")
    os.makedirs(test_exp_path / "log")

    wrf_path = base_test_env / "WRF_WPS_PARENT/WRF/test/em_real"
    wps_path = base_test_env / "WRF_WPS_PARENT/WPS"

    os.makedirs(wrf_path)
    os.makedirs(wps_path)
    os.makedirs(wps_path / "geogrid")
    os.makedirs(wps_path / "ungrib")
    os.makedirs(wps_path / "ungrib/Variable_Tables")
    os.makedirs(wps_path / "metgrid")

    # create fake data:
    with open(wps_path / "geogrid.exe", "w") as f:
        f.write("")
    with open(wps_path / "geogrid/GEOGRID.TBL", "w") as f:
        f.write("")
    with open(wps_path / "link_grib.csh", "w") as f:
        f.write("")
    with open(wps_path / "ungrib/Variable_Tables/Vtable.test", "w") as f:
        f.write("")
    with open(wps_path / "ungrib.exe", "w") as f:
        f.write("")
    with open(wps_path / "metgrid/METGRID.TBL", "w") as f:
        f.write("")
    with open(wps_path / "metgrid.exe", "w") as f:
        f.write("")
    with open(wrf_path / "wrf.exe", "w") as f:
        f.write("")
    with open(wrf_path / "Some.TBL", "w") as f:
        f.write("")
    with open(wrf_path / "ozone.Somefile", "w") as f:
        f.write("")
    with open(wrf_path / "RRTM.Somefile", "w") as f:
        f.write("")

    yield test_exp_path


# ----------------------------------------------------------------------------------------------------------------------
# statistics_data
@pytest.fixture()
def statistics_pd():
    test_pd = pd.read_csv(test_res_path / "testdata.csv")
    expect_pd = pd.read_csv(test_res_path / "testres.csv", index_col=0)

    yield test_pd, expect_pd


@pytest.fixture()
def statistics_xa(statistics_pd):
    test_pd, expect_pd = statistics_pd

    test_xa = xr.Dataset(
        coords={
            'time': test_pd['index'].values,
            'station_name': ['Station1'],
        },
        data_vars={
            'model': (['station_name', 'time'], np.expand_dims(test_pd.model.values, axis=0)),
            'Obs': (['station_name', 'time'], np.expand_dims(test_pd.obs.values, axis=0)),
        }
    )

    test_xa.attrs = {'var': 'wsp'}

    # ------------------------------------------------------------------------------------------------------------------
    expect_xa = xr.Dataset(
        coords={
            'mod_name': ['model'],
            'station_name': ['Station1'],
        },
        data_vars={
            'bias': (['mod_name', 'station_name'], np.expand_dims(expect_pd.BIAS.values, axis=0)),
            'std': (['mod_name', 'station_name'], np.expand_dims(expect_pd['STD(ERR)'].values, axis=0)),
            'mae': (['mod_name', 'station_name'], np.expand_dims(expect_pd.MAE.values, axis=0)),
            'CorCo': (['mod_name', 'station_name'], np.expand_dims(expect_pd.CorCo.values, axis=0)),
            'mape': (['mod_name', 'station_name'], np.expand_dims(expect_pd.MAPE.values, axis=0)),
            'rmse': (['mod_name', 'station_name'], np.expand_dims(expect_pd.RMSE.values, axis=0)),
        }
    )
    # ------------------------------------------------------------------------------------------------------------------

    return test_xa, expect_xa
