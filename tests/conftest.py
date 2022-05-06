import pytest
import os
from pathlib import Path
import shutil
import datetime as dt
from wrftamer.plotting.load_and_prepare import load_obs_data, load_mod_data
from wrftamer.main import project


@pytest.fixture
def base_test_env():
    """
    Creates a directory for testing purposes. This directory is removed aftet tests are completed.
    """

    test_env = Path(
        os.path.split(os.path.realpath(__file__))[0] + "/resources/test_environment"
    )
    os.mkdir(test_env)

    os.environ["WRFTAMER_HOME_PATH"] = str(test_env / "wrftamer")
    os.environ["WRFTAMER_RUN_PATH"] = str(test_env / "wrftamer/run/")
    os.environ["WRFTAMER_ARCHIVE_PATH"] = str(test_env / "wrftamer/archive/")
    os.environ["WRFTAMER_PLOT_PATH"] = str(test_env / "wrftamer/plots/")
    os.environ["OBSERVATIONS_PATH"] = str(test_env.parent / "observations_data/")

    yield test_env

    shutil.rmtree(test_env)


# test_class fixtures
@pytest.fixture
def map_env(base_test_env):
    testdir = base_test_env / "class_tests"

    dummy_data_path = Path(
        os.path.split(os.path.realpath(__file__))[0] + "/resources/dummy_data"
    )
    testfile = dummy_data_path / "wrfout_d01_2020-05-17_00:00:00"

    os.mkdir(testdir)

    yield testfile, testdir

    shutil.rmtree(testdir)


@pytest.fixture()
def ts_env(base_test_env):
    obs_path = base_test_env.parent / "observations_data/"
    os.environ["OBSERVATIONS_PATH"] = str(obs_path)

    non_conform_file = obs_path / "Nonconform/Nonconform_20200101_20210101.nc"

    yield non_conform_file


@pytest.fixture()
def testprojects(base_test_env):
    # I am assuming, that create and remove always work. If not, this fixture will fail (and all tests using it).
    # Create project and experiment

    proj_name1 = "WRFTAMER_TEST1"
    proj_name2 = "WRFTAMER_TEST2"
    test1 = project(proj_name1)
    test2 = project(proj_name2)

    test1.create(verbose=True)
    test2.create(verbose=True)

    yield test1, test2

    test1.remove(force=True, verbose=True)
    test2.remove(force=True, verbose=True)


@pytest.fixture()
def unassociated_exps(base_test_env):
    # I am assuming, that create and remove always work. If not, this fixture will fail (and all tests using it).

    # Create project and experiment
    proj_name = None
    test = project(proj_name)

    test.create(
        verbose=True
    )  # checks itself for files being created. Raises FileNotFoundError on failure

    yield test

    test.remove(force=True, verbose=True)


@pytest.fixture()
def test_env2(testprojects):
    testproject1 = testprojects[0]

    exp_name1 = "TEST1"

    # ------------------------------------------------------
    # adding an exp to a project should work fine.
    configfile = (
        os.path.split(os.path.realpath(__file__))[0] + "/resources/configure_test.yaml"
    )
    testproject1.exp_create(exp_name1, "First Experiment", configfile, verbose=True)

    # copy dummy data
    source = Path(
        os.path.split(os.path.realpath(__file__))[0] + "/resources/dummy_data"
    )
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

    data_path = Path(os.path.split(os.path.realpath(__file__))[0] + "/resources/")
    driving_data = data_path / "driving_data"

    yield driving_data, base_test_env


# plotting fixtures


@pytest.fixture()
def plot_environment(base_test_env):
    # This function creates directories, links test data and yields
    # The fixture ensures that the environment will always be torn down after tests.
    # However, if the code in the fixture reaches an error, this is no longer the case.
    # For this reason, test project and experiment first!

    test_res_path = Path(os.path.split(os.path.realpath(__file__))[0] + "/resources")

    # Create project and experiment
    proj_name = "WRFTAMER_TEST"
    exp_name = "TEST1"
    configfile = test_res_path / "configure_test.yaml"

    test = project(proj_name)  # initialize class
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
    os.symlink(
        test_res_path / "model_data/Ave10Min_tslist_d01.nc",
        workdir / "out/Ave10Min_tslist_d01.nc",
    )
    os.symlink(
        test_res_path / "model_data/raw_tslist_d01.nc",
        workdir / "out/raw_tslist_d01.nc",
    )

    yield proj_name, exp_name

    # Teardown of test
    test.remove(force=True, verbose=False)
    shutil.rmtree(base_test_env / "wrftamer")


# -----------------------------------------------------------------------------------------------------------------------


@pytest.fixture()
def infos(plot_environment):
    proj_name, exp_name = plot_environment

    infos1 = dict()
    infos1["proj_name"] = proj_name
    infos1["Expvec"] = [exp_name]
    infos1["dom"] = "d01"
    infos1["var"] = "WSP"
    infos1["lev"] = "82"
    infos1["loc"] = "FINO"
    infos1["AveChoice_WRF"] = "10"
    infos1["verbose"] = True
    infos1["anemometer"] = "Sonic"
    infos1["Obsvec"] = ["Testset"]
    infos1["time_to_plot"] = dt.datetime(2020, 5, 17, 12, 0, 0)

    infos2 = infos1.copy()
    infos2["var"] = "DIR"

    yield [infos1, infos2]


@pytest.fixture
def mod_data(infos):
    all_data = []
    for info_item in infos:
        exp_name = info_item["Expvec"][0]

        data = dict()
        load_mod_data(data, exp_name, **info_item)
        all_data.append(data)

    yield all_data


@pytest.fixture
def obs_data(infos):
    all_data = []
    for info_item in infos:
        obs = info_item["Obsvec"][0]
        dataset = "Testset"

        data = dict()
        load_obs_data(data, obs, dataset, **info_item)
        all_data.append(data)

    yield all_data


# ------------------------------------


@pytest.fixture()
def tslist_environment(base_test_env):
    # This function creates directories, links test data and yields
    # The fixture ensures that the environment will always be torn down after tests.
    # However, if the code in the fixture reaches an error, this is no longer the case.
    # For this reason, test project and experiment first!

    test_res_path = Path(os.path.split(os.path.realpath(__file__))[0] + "/resources")

    # Create project and experiment
    proj_name = "WRFTAMER_TEST"
    exp_name = "TEST1"
    configfile = test_res_path / "configure_test.yaml"

    test = project(proj_name)  # initialize class
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
