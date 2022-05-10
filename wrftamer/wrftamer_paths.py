import os
from pathlib import Path


def wrftamer_paths():
    """
    Here, all paths used by wrftamer are read from the environmental variables. If these variables are not set,
    defauls values are used.

    Returns: home_path, run_path, db_path, archive_path

    """

    try:
        home_path = Path(os.environ["WRFTAMER_HOME_PATH"])
        db_path = home_path / "db"
    except KeyError:
        home_path = Path(os.environ["HOME"]) / "wrftamer"
        db_path = Path(os.environ["HOME"]) / "wrftamer/db"

    try:
        run_path = Path(os.environ["WRFTAMER_RUN_PATH"])
    except KeyError:
        run_path = Path(os.environ["HOME"]) / "wrftamer/run"

    try:
        archive_path = Path(os.environ["WRFTAMER_ARCHIVE_PATH"])
    except KeyError:
        archive_path = Path(os.environ["HOME"]) / "wrftamer/archive"

    try:
        plot_path = Path(os.environ["WRFTAMER_PLOT_PATH"])
    except KeyError:
        plot_path = Path(os.environ["HOME"]) / "wrftamer/plots"

    # I may add more paths later on. These include:
    # $HOME/wrftamer/src/wrf_essentials
    # $HOME/wrftamer/src/wrf_nonessentials
    # $HOME/wrftamer/bin/wrf_executables
    # This way, everything would be together at a single place.
    # Of course, the user may always set their own paths.

    try:
        os.makedirs(home_path, exist_ok=True)
        os.makedirs(db_path, exist_ok=True)
        os.makedirs(run_path, exist_ok=True)
        os.makedirs(archive_path, exist_ok=True)
        os.makedirs(plot_path, exist_ok=True)
    except PermissionError:
        raise PermissionError("Error: You do not have write permission for at least one of the WRFTAMER paths you "
                              "specified.")

    return home_path, db_path, run_path, archive_path, plot_path


def get_make_submit():
    try:
        make_submit = bool(os.environ["WRFTAMER_make_submit"])
    except KeyError:
        make_submit = False

    return make_submit
