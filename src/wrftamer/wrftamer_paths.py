import os
from pathlib import Path
from wrftamer import cfg


def wrftamer_paths():
    """
    Here, all paths used by wrftamer are read from the environmental variables. If these variables are not set,
    defauls values are used.

    Returns: home_path, run_path, db_path, archive_path

    """

    if cfg['wrftamer_paths']['relative_to_home']:
        home_path = Path(os.environ["HOME"])
        wrftamer_path = home_path / cfg['wrftamer_paths']['wrftamer_path']
        run_path      = home_path / cfg['wrftamer_paths']['run_path']
        archive_path  = home_path / cfg['wrftamer_paths']['archive_path']
        plot_path     = home_path / cfg['wrftamer_paths']['plot_path']
    else:
        wrftamer_path = Path(cfg['wrftamer_paths']['wrftamer_path'])
        run_path      = Path(cfg['wrftamer_paths']['run_path'])
        archive_path  = Path(cfg['wrftamer_paths']['archive_path'])
        plot_path     = Path(cfg['wrftamer_paths']['plot_path'])

    db_path = wrftamer_path / "db"

    # I may add more paths later on. These could include:
    # $HOME/wrftamer/src/wrf_essentials
    # $HOME/wrftamer/src/wrf_nonessentials
    # $HOME/wrftamer/bin/wrf_executables
    # This way, everything would be together at a single place.
    # Of course, the user may always set their own paths.

    try:
        os.makedirs(wrftamer_path, exist_ok=True)
        os.makedirs(db_path, exist_ok=True)
        os.makedirs(run_path, exist_ok=True)
        os.makedirs(archive_path, exist_ok=True)
        os.makedirs(plot_path, exist_ok=True)
    except PermissionError:
        raise PermissionError("Error: You do not have write permission for at least one of the WRFTAMER paths specified")

    return wrftamer_path, db_path, run_path, archive_path, plot_path
