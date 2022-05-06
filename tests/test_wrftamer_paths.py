import pytest
import os
from wrftamer.wrftamer_paths import wrftamer_paths, get_make_submit
import shutil

wtres_path = os.path.split(os.path.realpath(__file__))[0] + "/resources/"


def test_environment_paths():
    os.environ["WRFTAMER_HOME_PATH"] = wtres_path + "/wrftamer"
    os.environ["WRFTAMER_RUN_PATH"] = wtres_path + "/wrftamer/run/"
    os.environ["WRFTAMER_ARCHIVE_PATH"] = wtres_path + "/wrftamer/archive/"
    os.environ["WRFTAMER_PLOT_PATH"] = wtres_path + "/wrftamer/plots/"

    home_path, db_path, run_path, archive_path, plot_path = wrftamer_paths()
    shutil.rmtree(plot_path)
    shutil.rmtree(archive_path)
    shutil.rmtree(run_path)
    shutil.rmtree(db_path)
    shutil.rmtree(home_path)


def test_default_paths():
    for key in [
        "WRFTAMER_HOME_PATH",
        "WRFTAMER_RUN_PATH",
        "WRFTAMER_ARCHIVE_PATH",
        "WRFTAMER_PLOT_PATH",
    ]:
        if key in os.environ:
            del os.environ[key]

    home_path, db_path, run_path, archive_path, plot_path = wrftamer_paths()
    shutil.rmtree(plot_path)
    shutil.rmtree(archive_path)
    shutil.rmtree(run_path)
    shutil.rmtree(db_path)
    shutil.rmtree(home_path)


def test_no_access_paths():
    os.environ["WRFTAMER_HOME_PATH"] = wtres_path + "/no_access/wrftamer"
    os.environ["WRFTAMER_RUN_PATH"] = wtres_path + "/no_access/wrftamer/run/"
    os.environ["WRFTAMER_ARCHIVE_PATH"] = wtres_path + "/no_access/wrftamer/archive/"
    os.environ["WRFTAMER_PLOT_PATH"] = wtres_path + "/no_access/wrftamer/plots/"

    with pytest.raises(PermissionError):
        wrftamer_paths()


def test_get_make_submit():
    get_make_submit()

    del os.environ["WRFTAMER_make_submit"]

    get_make_submit()
