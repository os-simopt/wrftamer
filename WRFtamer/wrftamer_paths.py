import os
from pathlib import Path


def wrftamer_paths():
    """
    Here, all paths used by WRFtamer are read from the environmental variables. If these variables are not set,
    defauls values are used.

    Returns: home_path, run_path, db_path, archive_path

    """

    try:
        home_path = Path(os.environ['WRFTAMER_HOME_PATH'])
        db_path = home_path / 'db'
    except KeyError:
        home_path = Path(os.environ['HOME']) / 'WRFtamer'
        db_path = Path(os.environ['HOME']) / 'WRFtamer/db'

    try:
        run_path = Path(os.environ['WRFTAMER_RUN_PATH'])
    except KeyError:
        run_path = Path(os.environ['HOME']) / 'WRFtamer/run'

    try:
        archive_path = Path(os.environ['WRFTAMER_ARCHIVE_PATH'])
    except KeyError:
        archive_path = Path(os.environ['HOME']) / 'WRFtamer/archive'

    try:
        plot_path = Path(os.environ['WRFTAMER_PLOT_PATH'])
    except KeyError:
        plot_path = Path(os.environ['HOME']) / 'WRFtamer/plots'


    # I may add more paths later on. These include:
    # $HOME/WRFtamer/src/wrf_essentials
    # $HOME/WRFtamer/src/wrf_nonessentials
    # $HOME/WRFtamer/bin/wrf_executables
    # This way, everything would be together at a single place.
    # Of course, the user may always set their own paths.

    os.makedirs(home_path, exist_ok=True)
    os.makedirs(db_path, exist_ok=True)
    os.makedirs(run_path, exist_ok=True)
    os.makedirs(archive_path, exist_ok=True)
    os.makedirs(plot_path, exist_ok=True)

    return home_path, db_path, run_path, archive_path, plot_path
