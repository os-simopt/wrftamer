import pytest
import os
from pathlib import Path
import shutil
from wrftamer.main import Project


@pytest.fixture
def base_test_env():
    """
    Creates a directory for testing purposes. This directory is removed after tests are completed.
    """

    test_env = Path(
        os.path.split(os.path.realpath(__file__))[0] + "/resources/test_environment"
    )

    if test_env.is_dir():
        shutil.rmtree(test_env)

    os.mkdir(test_env)

    os.environ["WRFTAMER_HOME_PATH"] = str(test_env / "wrftamer")
    os.environ["WRFTAMER_RUN_PATH"] = str(test_env / "wrftamer/run/")
    os.environ["WRFTAMER_ARCHIVE_PATH"] = str(test_env / "wrftamer/archive/")
    os.environ["WRFTAMER_PLOT_PATH"] = str(test_env / "wrftamer/plots/")
    os.environ["OBSERVATIONS_PATH"] = str(test_env.parent / "observations_data/")
    os.environ["WRFTAMER_make_submit"] = 'True'

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


# -----------------------------------------------------------------------------------------------------------------------


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
