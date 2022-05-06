import pandas as pd
import os
import glob
import shutil
import datetime as dt
import numpy as np
from pathlib import Path
import yaml
from collections import defaultdict

from wrftamer.wrftamer_paths import wrftamer_paths, get_make_submit
import wrftamer.wrftamer_functions as wtfun
from wrftamer.utility import printProgressBar
from wrftamer.process_tslist_files import merge_tslist_files, average_ts_files
from wrftamer.wrfplotter_classes import Map


def list_projects(verbose=True):
    """
    Lists all projects that exist.

    Args:
        verbose: can be silent

    """

    home_path, db_path, run_path, archive_path, disc = wrftamer_paths()

    list_of_projects = [
        name
        for name in os.listdir(db_path)
        if os.path.isdir(os.path.join(db_path, name))
    ]

    if verbose:
        for item in list_of_projects:
            print(item)

    return list_of_projects


def list_unassociated_exp(verbose=True):
    home_path, db_path, run_path, archive_path, disc = wrftamer_paths()

    try:
        filename = db_path / "Unassociated_Experiments/List_of_Experiments.xlsx"
        df = get_xls(filename)

        if verbose:
            print(df.Name)

        mylist = [item for item in df.Name]
    except FileNotFoundError:
        if verbose:
            print("No unassociates Experiments found.")
        mylist = []

    return mylist


def get_xls(filename):
    df = pd.read_excel(
        filename,
        index_col="index",
        usecols=[
            "index",
            "Name",
            "time",
            "comment",
            "start",
            "end",
            "disk use",
            "runtime",
            "status",
        ],
    )
    return df


def reassociate(proj_old, proj_new, exp_name: str):
    """
    Associate <exp_name> with <proj_new>. Unassociate this exp with <proj_old>

    Args:
        proj_old: the old project <exp_name> belongs to
        proj_new: the new project the experiment should be associated with
        exp_name: experiment name
    """

    # --------------------------------------------------------------------------------------------------------------
    # from old project
    df = proj_old.exp_provide_all_info(exp_name)
    name, time_of_creation, comment, start, end, du, rt, status = tuple(
        df.to_numpy()[0]
    )

    # Database update
    df = get_xls(proj_new.filename)
    # Check if name is unique, otherwise cannot add an experiment of the same name
    if exp_name in df.Name.values:
        raise FileExistsError

    # Add to new db
    new_line = [exp_name, time_of_creation, comment, start, end, du, rt, "created"]
    df.loc[len(df)] = new_line
    df.to_excel(proj_new.filename)

    # remove from old db
    df = get_xls(proj_old.filename)
    idx = df.index[df.Name == exp_name].values
    df = df.drop(idx)
    df.to_excel(proj_old.filename)

    # move actual experiment
    old_workdir = proj_old.get_workdir(exp_name)
    new_workdir = proj_new.get_workdir(exp_name)
    old_workdir.rename(new_workdir)


class project:
    def __init__(self, name):

        self.wrftamer_paths = (
            wrftamer_paths()
        )  # home_path, db_path, run_path, archive_path, some_other_path
        self.make_submit = get_make_submit()

        if name is None:
            name = "Unassociated_Experiments"

        self.name = name

    @property
    def tamer_path(self):
        tamer_path = self.wrftamer_paths[1] / self.name
        return tamer_path

    @property
    def proj_path(self):
        proj_path = self.wrftamer_paths[2] / self.name
        return proj_path

    @property
    def archive_path(self):
        archive_path = self.wrftamer_paths[3] / self.name
        return archive_path

    @property
    def filename(self):
        filename = self.tamer_path / "List_of_Experiments.xlsx"
        return filename

    # ------------------------------------------------------------------------------------------------------------------
    # Project related methods
    def create(self, verbose=True):
        """
        Creates a directory and an empty xls file named List_of_Experiments.xls
        Creates a directory in run_path named proj_name. Runs should be created there

        Drops an error if proj_name already exists.
        """

        if os.path.isdir(self.tamer_path) or os.path.isdir(self.proj_path):
            raise FileExistsError
        else:
            if verbose:
                print("Creating Project", self.name)

            os.mkdir(self.proj_path)
            os.mkdir(self.tamer_path)

            df = pd.DataFrame(
                columns=[
                    "index",
                    "Name",
                    "time",
                    "comment",
                    "start",
                    "end",
                    "disk use",
                    "runtime",
                    "status",
                ]
            )
            df.set_index("index")
            df.to_excel(self.tamer_path / "List_of_Experiments.xlsx")

        namelist_template = (
            os.path.split(os.path.realpath(__file__))[0]
            + "/resources/namelist.template"
        )
        wrftamer_conf = (
            os.path.split(os.path.realpath(__file__))[0]
            + "/resources/configure_template.yaml"
        )

        newfile = self.proj_path / "namelist.template"
        new_conf = self.proj_path / "configure_template.yaml"

        # copy namelist.template and configure_template to project folder for easy reference and transparancy.
        shutil.copyfile(namelist_template, newfile)
        shutil.copyfile(wrftamer_conf, new_conf)

    def remove(self, force=False, verbose=True):
        """
        This function removes a whole project and everything that is associated with it, including the
        run directories. Handle with EXTREME care or face massive loss of data.

        Args:
            verbose: speak with user.
            force: set to true for testing. Circumvents the user interface. DANGER!

        Returns: None
        """

        if force:
            val = "Yes"
        else:
            print("=============================================================")
            print("                       DANGER ZONE                           ")
            print("Warning! ALL DATA of project", self.name, "will be lost!")
            print("=============================================================")
            val = input("Proceed? Yes/[No]")

        if val in ["Yes"]:

            if verbose:
                print("Removing", self.proj_path)
                print("Removing", self.tamer_path)
                print("Removing", self.archive_path)

            shutil.rmtree(self.tamer_path)
            if self.proj_path.is_dir():
                shutil.rmtree(self.proj_path)
            if self.archive_path.is_dir():
                shutil.rmtree(self.archive_path)

        else:
            print("Abort. (Yes must be capitalized)")
            return

    def rename(self, new_name: str, verbose=True):

        """
        Renames the directory that is associated with a project
        """

        old_proj_path = self.proj_path
        new_proj_path = self.proj_path.parent / new_name

        old_tamer_path = self.tamer_path
        new_tamer_path = self.tamer_path.parent / new_name

        old_archive_path = self.archive_path
        new_archive_path = self.archive_path.parent / new_name

        if not os.path.isdir(old_tamer_path):
            raise FileNotFoundError

        if not os.path.isdir(old_proj_path) and not os.path.isdir(old_archive_path):
            raise FileNotFoundError  # neither on archive nor in run place

        if (
            os.path.isdir(new_proj_path)
            or os.path.isdir(new_tamer_path)
            or os.path.isdir(new_archive_path)
        ):
            raise FileExistsError

        os.rename(old_tamer_path, new_tamer_path)

        if os.path.isdir(old_proj_path):
            os.rename(old_proj_path, new_proj_path)

        if os.path.isdir(old_archive_path):
            os.rename(old_archive_path, new_archive_path)

        self.name = new_name

    def disk_use(self, verbose=True):
        """
        Show the size of all experiments of project <proj_name>

        Args:
            verbose: can be silent

        Returns: None

        """

        if not os.path.isdir(self.proj_path):
            if verbose:
                print("This project does not exist")
            raise FileNotFoundError

        proj_size1 = sum(
            os.path.getsize(f)
            for f in self.proj_path.rglob("**")
            if (os.path.isfile(f) and not os.path.islink(f))
        )

        proj_size2 = sum(
            os.path.getsize(f)
            for f in self.archive_path.rglob("**")
            if (os.path.isfile(f) and not os.path.islink(f))
        )

        proj_size = proj_size1 + proj_size2

        if verbose:
            print("Size of the project", self.name, ": ", proj_size, "bytes")

        return proj_size

    def runtimes(self, verbose=True):
        raise NotImplementedError

    def list_exp(self, verbose=True):

        # Fails with a FileNotFoundError if project does not exist.
        df = get_xls(self.filename)

        if verbose:
            print(df.Name)

        return df.Name.to_list()

    def rewrite_xls(self):
        """
        Sometimes, when I edit the xls shet manually, It happens that it is stored with tousands of lines, all containing
        just nans. This makes the wrftamer and especially the GUI extremely slow. An xlsx sheet like this must be reead
        and rewritten. This function does exactly that.
        """

        df = get_xls(self.filename)
        if len(df) == 0:
            return

        df = df[np.isfinite(df.index)]
        df.to_excel(self.filename)

    def update_xlsx(self):
        """
        Calculation of rt, du etc is rather slow, so instead of calling this in the GUI, just call it from time to
        time and write the data into the xlsx sheet.
        """

        df = get_xls(self.filename)

        exp_list = df.Name.to_list()

        for idx, exp_name in enumerate(exp_list):
            start, end = self.exp_start_end(exp_name, verbose=False)
            du = self.exp_du(exp_name, False)
            rt = self.exp_runtime(exp_name, verbose=False)

            time = df.time[idx]
            comment = df.comment[idx]
            status = df.status[idx]

            new_line = [exp_name, time, comment, start, end, du, rt, status]
            df.loc[idx] = new_line

        df.to_excel(self.filename)

    def cleanup_db(self, verbose=True):

        df = get_xls(self.filename)

        for exp_name in df["Name"]:
            if (self.proj_path / exp_name).is_dir():
                if verbose:
                    print("Experiment", exp_name, "exists")
            else:
                if verbose:
                    print(
                        "Experiment", exp_name, "does not exist and is removed from db"
                    )
                idx = df.index[df.Name == exp_name].values
                df = df.drop(idx)

        df.to_excel(self.filename)

    # ------------------------------------------------------------------------------------------------------------------
    def exp_create(
        self,
        exp_name,
        comment: str,
        configfile: str,
        namelisttemplate=None,
        submittemplate=None,
        verbose=True,
    ):

        """
        Create the directory structure of an experiment. Create a database entry for the experiment.

        Args:
            exp_name: the name of the experiment to be created
            comment: a short entry to descripe the experiment
            configfile: a yaml file that contains all information to create an experiment.
            namelisttemplate: the template of the namelist to use
            submittemplate: the template of the submitfile to use
            verbose: speak with user

        Returns: None
        """

        # First, check if proj_name exists. If no, create
        if not self.proj_path.is_dir():
            self.create()  # always create a project, even if proj_name is None.

        # Check Database
        df = get_xls(self.filename)

        # Check if name is unique, otherwise cannot add an experiment of the same name
        if exp_name in df.Name.values:
            if verbose:
                print(
                    "Directories of the experiment do not exist, but an entry in the database does."
                )
                print("This can happen, if a folder has been removed manually.")
                print("Run cleanup_db to resolve this issue.")
            raise FileExistsError

        # Check folders
        exp_path = self.proj_path / exp_name

        if os.path.isdir(exp_path):
            raise FileExistsError

        if verbose:
            print("---------------------------------------")
            print(f"Creating Experiment {exp_name}")
            print(f" in directory {exp_path}")
            print("---------------------------------------")

        # Create run directory, link files
        wtfun.create_rundir(exp_path, configfile, namelisttemplate, verbose=verbose)

        # make submit-files
        if self.make_submit:
            wtfun.make_submitfiles(exp_path, configfile, submittemplate)

        # --------------------------------------------------------------------------------------------------------------
        # Database update

        # Now, add new line with information.
        time_of_creation = dt.datetime.utcnow().strftime("%Y.%m.%d %H:%M:%S")

        du, rt = np.nan, np.nan
        start, end = self.exp_start_end(exp_name, verbose=False)

        new_line = [exp_name, time_of_creation, comment, start, end, du, rt, "created"]

        df.loc[len(df)] = new_line
        df.to_excel(self.filename)

    def exp_copy(
        self, old_exp_name: str, new_exp_name: str, comment: str, verbose=True
    ):
        """

        Args:
            old_exp_name: the name of the experiment which will be copied
            new_exp_name: the name of the experiment which will be created
            comment: a short entry to descripe the experiment
            verbose: speak with user

        Returns: None

        """

        old_exp_path = self.proj_path / old_exp_name
        new_exp_path = self.proj_path / new_exp_name
        df = get_xls(self.filename)

        status = self.exp_get_status(old_exp_name)
        if status == "archived":
            if verbose:
                print("This run has already been archived and may not be copied.")
            return

        if not os.path.isdir(old_exp_path):
            raise FileNotFoundError

        if os.path.isdir(new_exp_path):
            raise FileExistsError

        # check Database
        # Check if name is unique, otherwise cannot add an experiment of the same name
        if new_exp_name in df.Name.values:
            if verbose:
                print(
                    "Directories of the new experiment do not exist, but an entry in the database does."
                )
                print("This can happen, if a folder has been removed manually.")
                print("Run cleanup_db to resolve this issue.")
            raise FileExistsError

        if verbose:
            print("---------------------------------------")
            print(f"Reusing Experiment {old_exp_name}")
            print(f" as experiment {new_exp_name}")
            print("---------------------------------------")

        wtfun.copy_dirs(old_exp_path, new_exp_path)

        # --------------------------------------------------------------------------------------------------------------
        # Database update

        # Now, add new line with information.
        time_of_creation = dt.datetime.utcnow().strftime("%Y.%m.%d %H:%M:%S")

        du, rt = np.nan, np.nan
        start, end = self.exp_start_end(new_exp_path, verbose=False)

        new_line = [
            new_exp_name,
            time_of_creation,
            comment,
            start,
            end,
            du,
            rt,
            "added",
        ]

        df.loc[len(df)] = new_line
        df.to_excel(self.filename)

        self._update_db_entry(new_exp_name, {"status": "created"})

    def exp_remove(self, exp_name: str, verbose=True, force=False):
        """

        This method is a clean way to remove a project. The project may already be archived.
        Initialize this class with status = archived in this case

        Args:
            exp_name: name of the experiment
            verbose: Speak with user
            force: forced removal for testing

        Returns: None

        """

        exp_path = self.proj_path / exp_name
        archive_path = self.archive_path / exp_name
        status = self.exp_get_status(exp_name)

        df = get_xls(self.filename)

        if exp_path.is_dir() or archive_path.is_dir():
            remove_dirs = True
        else:
            if verbose:
                print("Directories of experiment not found.")
            remove_dirs = False

        if exp_name in df.Name.values:
            remove_db_entry = True
        else:
            if verbose:
                print("Database entry of experiment not found.")
            remove_db_entry = False

        # --------------------------------------------------------------------------------------------------------------
        if force:
            val = "Yes"
        else:
            print("=============================================================")
            print("                       DANGER ZONE                           ")
            print(f"Warning, all data of experiment {exp_name} will be lost!   ")
            print("=============================================================")
            val = input("Proceed? Yes/[No]")

        if val in ["Yes"]:
            if verbose:
                print("---------------------------------------")
                print(f"Removing Experiment {exp_name}")
                print("---------------------------------------")

            if remove_dirs:
                if status == "archived":
                    shutil.rmtree(archive_path)  # raises FileNotFoundError on failure
                else:
                    shutil.rmtree(exp_path)  # raises FileNotFoundError on failure

            if remove_db_entry:
                idx = df.index[df.Name == exp_name].values
                df = df.drop(idx)
                df.to_excel(self.filename)
        else:
            print("Abort. (Yes must be capitalized)")
            return

    def exp_rename(self, old_exp_name: str, new_exp_name: str, verbose=True):

        old_workdir = self.get_workdir(old_exp_name)
        new_workdir = old_workdir.parent / new_exp_name
        # I do not call get_workdir (because this one would be a run dir, so it would fail with archived runs)
        df = get_xls(self.filename)

        if os.path.isdir(new_workdir):
            if verbose:
                print(f"Cannot rename, experiment {new_exp_name} exists.")
            raise FileExistsError

        if old_exp_name not in df.Name.values:
            print(
                f"Directories of the experiment {old_exp_name} do not exist, but an entry in the database does."
            )
            print("This can happen, if a folder has been removed manually.")
            print("Run cleanup_db to resolve this issue.")
            raise FileNotFoundError
        elif new_exp_name in df.Name.values:
            print(
                f"Directories of the experiment {new_exp_name} do not exist, but an entry in the database does."
            )
            print("This can happen, if a folder has been removed manually.")
            print("Run cleanup_db to resolve this issue.")
            raise FileExistsError

        if verbose:
            print("---------------------------------------")
            print(f"Renaming Experiment {old_exp_name} to {new_exp_name}")
            print("---------------------------------------")

        wtfun.rename_dirs(old_workdir, new_workdir, self.make_submit)

        # --------------------------------------------------------------------------------------------------------------
        # Database update
        idx = df.index[df.Name == old_exp_name].values
        df.Name.values[idx] = new_exp_name

        df.to_excel(self.filename)

    def exp_run_wps(self, exp_name, verbose=True):

        exp_path = self.proj_path / exp_name

        if verbose:
            print("Running WPS (geogrid, ungrib, metgrid)")

        wtfun.run_wps_command(exp_path, "geogrid")
        wtfun.run_wps_command(exp_path, "ungrib")
        wtfun.run_wps_command(exp_path, "metgrid")

    def exp_restart(self, exp_name: str, restartfile: str, verbose=True):

        exp_path = self.proj_path / exp_name

        if verbose:
            print("---------------------------------------")
            print(f"Restarting Experiment {exp_name} with restart file {restartfile}")
            print("---------------------------------------")

        try:
            date_string = Path(restartfile).name[11::]
            dt.datetime.strptime(date_string, "%Y-%m-%d_%H:%M:%S")
        except ValueError:
            if verbose:
                print(f"File {restartfile} does not have the format %Y-%m-%d_%H:%M:%S")
                print("A Path in front of the filename is fine")
            raise NameError

        wtfun.move_output(exp_path)

        namelistfile = exp_path / "wrf" / "namelist.input"
        outfile = namelistfile

        wtfun.update_namelist_for_rst(restartfile, namelistfile, outfile)

        self._update_db_entry(exp_name, {"status": "restarted"})

    def exp_move(self, exp_name: str, verbose=True):

        workdir = self.get_workdir(exp_name)

        if verbose:
            print("---------------------------------------")
            print("Moving model output to out and log dirs")
            print(f"Source: {workdir}/wrf/")
            print("---------------------------------------")

        if any(
            [
                len(list((workdir / "wrf").glob("*.log"))) > 0,
                len(list((workdir / "wrf").glob("*.rsl"))) > 0,
                len(list((workdir / "wrf").glob("wrfout*"))) > 0,
                len(list((workdir / "wrf").glob("wrfaux*"))) > 0,
                len(list((workdir / "wrf").glob("*.UU"))) > 0,
            ]
        ):

            wtfun.move_output(workdir)

            self._update_db_entry(exp_name, {"status": "moved"})

        else:
            if verbose:
                print("No files to move")

    def exp_process_tslist(
        self, exp_name: str, location: str, domain: str, timeavg: list, verbose=True
    ):

        workdir = self.get_workdir(exp_name)

        outdir = workdir / "out"
        idir = (workdir / "out").glob("tsfiles*")

        if len(list(idir)) == 0 or not outdir.is_dir():
            if verbose:
                print(f"Cannot process tslists.")
                print(f"The directory {workdir}/out/tsfiles*' does not exist")
            return

        Path(outdir / f"raw_tslist_{domain}")
        merge_tslist_files(idir, outdir, location, domain, self.name, exp_name)

        # if tslists exists
        rawlist = list(outdir.glob("raw*"))

        total = len(rawlist)
        printProgressBar(0, total, prefix="Progress:", suffix="Complete", length=50)
        for i, rawfile in enumerate(rawlist):
            average_ts_files(str(rawfile), timeavg)
            printProgressBar(
                i + 1, total, prefix="Progress:", suffix="Complete", length=50
            )

        self._update_db_entry(exp_name, {"status": "post processed"})

    def exp_archive(self, exp_name: str, keep_log=False, verbose=True):

        """

        The run directory of this experiment will be moved to the archive directory set
        in the environement variable WRFTAMER_ARCHIVE_PATH.

        Files that are no longer needed will be deleted. This includes:
        - the whole log directory (unlsee keep_log = True)
        - all linked files, wrf-specific filse, files generatred by WPS or real.exe

        """

        exp_path = self.proj_path / exp_name
        archive_path = self.archive_path / exp_name

        if not os.path.isdir(exp_path):
            raise FileNotFoundError

        if not keep_log:
            shutil.rmtree(exp_path / "log", ignore_errors=True)

        filelist = []
        filelist.extend(list((exp_path / "wrf").glob("GRIBFILE.*")))
        filelist.extend(list((exp_path / "wrf").glob("FILE*")))
        filelist.extend(list((exp_path / "wrf").glob("PFILE*")))
        filelist.extend(list((exp_path / "wrf").glob("*.TBL")))
        filelist.extend(list((exp_path / "wrf").glob("*.exe")))
        filelist.extend(list((exp_path / "wrf").glob("ozone*")))
        filelist.extend(list((exp_path / "wrf").glob("Vtable")))
        filelist.extend(list((exp_path / "wrf").glob("RRTM*")))
        filelist.extend(list((exp_path / "wrf").glob("wrfbdy*")))
        filelist.extend(list((exp_path / "wrf").glob("wrfinput*")))
        filelist.extend(list((exp_path / "wrf").glob("geo_em*")))
        filelist.extend(list((exp_path / "wrf").glob("met_em*")))
        filelist.extend(list((exp_path / "wrf").glob("*.log")))
        filelist.extend(list((exp_path / "wrf").glob("link_grib.csh")))
        filelist.extend(list((exp_path / "wrf").glob("namelist.output")))

        for myfile in filelist:
            os.remove(myfile)

        if verbose:
            print("---------------------------------------")
            print("Archiving model output")
            print(f"Source: {exp_path}")
            print(f"Target: {archive_path}")
            print("---------------------------------------")

        shutil.move(exp_path, archive_path)

        self._update_db_entry(exp_name, {"status": "archived"})

    def exp_run_postprocessing_protocol(self, exp_name: str, verbose=True, cfg=None):

        workdir = self.get_workdir(exp_name)

        if cfg is None:
            configure_file = workdir / "configure.yaml"

            with open(configure_file) as f:
                cfg = yaml.safe_load(f)

        try:
            ppp = cfg["pp_protocol"]
        except KeyError:
            print(
                "Cannot perform post processing protocol. No valid enty found in configure.yaml"
            )
            return

        for item in ppp:
            if item == "move":
                if ppp[item] == 1:
                    self.exp_move(exp_name, verbose)

            elif item == "tslist_processing":
                if ppp[item]:
                    if isinstance(ppp[item], dict):
                        location = ppp[item].get("location", None)
                        domain = ppp[item].get("domain", None)
                        timeavg = ppp[item].get("timeavg", None)
                    else:
                        location, domain, timeavg = None, None, None

                    self.exp_process_tslist(
                        exp_name, location, domain, timeavg, verbose
                    )

            elif item == "create_maps":

                """
                Warning: potentially, these are a LOT of maps, which may require a lot of space!
                Specifically: ntime * nvars * nlevs * ndomains
                If I can speedup the read and plot process, I might be able to plot the data with
                WRFplotter after all.
                I want to be able ot click through my maps.
                """

                # Insead of plotting everything, I may want to creat a smaller subset of my wrfoutput
                # I.e. some map-data,
                # And during post processing, all wrfout-data is read and only a small fraction
                # (as specified) is cut out to reduce the time it takes to load the data.
                # Right now, I have two bottlenecks:
                # 1) Loading the data. With wrf-python, since it does not use dask but netCDF4, it is very slow.
                # However, I need the nice features of WRF.

                # 2) cartopy/basemap. Here, specifically highres coastline data with basemap is very slow (15 s!)
                # Time check: Loading a single timeframe: ~2 s
                # Time check: Loading 18 timeframes at a time: 18.8 s
                # Cartopy plot: 7.27 s
                # Basemap plot: 4.02 s (res='h')
                # Basemap plot: 980 ms/4.02 s (res='c','h') (but c is really ugly.)

                # Loading data of a whole (2day run/16 GB), single VAR and ml: ~6min
                # Loading all data with xarray and concating: Kernel dies
                # Using open_mfdataset (dask): 6.83 s
                # Now, the problem is that my nice wrf-python routines do not work anymore and I am left
                # with raw WRF output. This is a hard stop, since both cartopy and basemap are using attributes
                # provided by wrf-python
                # wrf-python is not able to run with dask, and I cannot change that.
                #
                # Options:
                # Write own code that interpolates and calculates diagnostics (like wrf-python)
                # - this will take forever and is prone to errors! I may be able to do it with
                # limited functionality.
                # - Subsample data, i.e, extract required variables and levels, put into single file and store
                # as netcdf. Then, load should be MUCH faster.
                # Plotting MAY be much fast as well, if I have to calculate the basemape only once and just replace
                # the field(s) plotted.

                if ppp[item]:
                    if isinstance(ppp[item], dict):
                        list_of_mls = ppp[item].get("list_of_mls", [5])
                        list_of_vars = ppp[item].get("list_of_vars", ["WSP"])
                        list_of_doms = ppp[item].get("list_of_doms", ["d01"])
                        poi = ppp[item].get("poi", None)
                        store = bool(ppp[item].get("store", True))
                    else:
                        list_of_mls = [5]
                        list_of_vars = ["WSP"]
                        list_of_doms = ["d01"]
                        poi = None
                        store = True

                    plot_path = workdir / "plot"
                    intermediate_path = workdir / "out"
                    fmt = "png"

                    cls = Map(
                        plot_path=plot_path,
                        intermediate_path=intermediate_path,
                        fmt=fmt,
                    )

                    for dom in list_of_doms:
                        inpath = workdir / "out"
                        filenames = list(sorted(inpath.glob(f"wrfout_{dom}*")))
                        for filename in filenames:
                            for ml in list_of_mls:
                                for var in list_of_vars:
                                    cls.extract_data_from_wrfout(
                                        filename, dom, var, ml, select_time=-1
                                    )

                                    if store:
                                        cls.store_intermediate()
                                    else:
                                        cls.plot(map_t="Cartopy", store=True, poi=poi)

        self._update_db_entry(exp_name, {"status": "post processed"})

    def exp_du(self, exp_name: str, verbose=True):

        workdir = self.get_workdir(exp_name)

        exp_size = sum(
            os.path.getsize(f)
            for f in workdir.rglob("**")
            if (os.path.isfile(f) and not os.path.islink(f))
        ) / (1024 * 1024)

        if verbose:
            print("Size of the experiment", exp_name, ": ", exp_size, "megabytes")

        return exp_size

    def exp_runtime(self, exp_name: str, verbose=True):

        workdir = self.get_workdir(exp_name)

        infile1 = workdir / "wrf/rsl.error.0000"
        infile2 = workdir / "log/rsl.error.0000"
        if os.path.isfile(infile1):
            infile = infile1
        elif os.path.isfile(infile2):
            infile = infile2
        else:
            if verbose:
                print("logfile rsl.error.0000 not found. Cannot calculate wrf timing")
            total_time = np.nan
            return total_time

        domains = defaultdict(list)
        domains_w = defaultdict(list)
        with open(infile, "r") as f:
            for line in f:
                if line.startswith("Timing for main:"):
                    dom = int(line.split()[7][:-1])
                    time = float(line.split()[8])
                    domains[dom].append(time)
                elif line.startswith("Timing for Writing"):
                    dom = int(line.split()[6][:-1])
                    time = float(line.split()[7])
                    domains_w[dom].append(time)

        if verbose:
            print("Average/median WRF timing [seconds]:")
            print("|        |           mean           |          median          |")
            print("| domain | calc time | writing time | calc time | writing time |")
            for i in range(7):
                if i in domains:
                    print(
                        f"|   {i:2d}   | {np.mean(domains[i]):9.3f} |"
                        f"  {np.mean(domains_w[i]):11.3f} | {np.median(domains[i]):9.3f} |"
                        f"  {np.median(domains_w[i]):11.3f} |"
                    )

            print("\n\nMaximum WRF timing [seconds]:")
            print("| domain | calc time | writing time |")
            for i in range(7):
                if i in domains:
                    print(
                        f"|   {i:2d}   | {np.max(domains[i]):9.3f} |"
                        f"  {np.max(domains_w[i]):11.3f} |"
                    )

            print("\n\nTotal WRF timing [days]:")
            print("| domain | calc time | writing time | total")
            for i in range(7):
                if i in domains:
                    print(
                        f"|   {i:2d}   | {np.sum(domains[i]) / 3600 / 24:9.3f} |"
                        f"  {np.sum(domains_w[i]) / 3600 / 24:11.3f} |"
                        f"  {(np.sum(domains[i]) + np.sum(domains_w[i])) / 3600 / 24:11.3f} |"
                    )

        total_time = 0
        for dom in domains:
            total_time += sum(domains[dom] + domains_w[dom])

        return total_time

    def exp_get_maxdom_from_config(self, exp_name):

        workdir = self.get_workdir(exp_name)
        configure_file = workdir / "configure.yaml"
        if configure_file.is_file() is False:
            return None

        with open(configure_file) as f:
            cfg = yaml.safe_load(f)

        try:
            max_dom = cfg["namelist_vars"]["max_dom"]
        except KeyError:
            max_dom = 1

        return max_dom

    # ------------------------------------------------------------------------------------------------------------------
    # Helpers

    def exp_provide_info(self, exp_name=None):

        df = get_xls(self.filename)

        select = list(np.repeat(False, len(df)))
        df["select"] = select

        if exp_name is not None:
            df = df[df.Name == exp_name]

        # Change datatypes of start and end to string, since the GUI-Tabulator widget throws an error with timestamps!
        df["start"] = df["start"].astype(str)
        df["end"] = df["end"].astype(str)

        return df

    def exp_provide_all_info(self, exp_name=None):

        df = get_xls(self.filename)

        if exp_name is not None:
            df = df[df.Name == exp_name]

        return df

    def exp_get_status(self, exp_name):

        df = get_xls(self.filename)
        df = df[df.Name == exp_name]

        try:
            status = df.status.values[0]
        except IndexError:
            status = "Uncreated"

        return status

    def exp_list_tslocs(self, exp_name: str, verbose=True):
        """
        get list of location for which tsfiles are available.
        retuns a sorted list.
        """

        workdir = self.get_workdir(exp_name)

        mylist = glob.glob(str(workdir) + "/out/tsfiles*/*")
        loc_list = list(set([item.rsplit("/", 1)[1].split(".")[0] for item in mylist]))
        loc_list.sort()

        if verbose:
            print(loc_list)

        return loc_list

    def exp_start_end(self, exp_name, verbose=True):

        # defaults
        start = dt.datetime(1971, 1, 1)
        end = dt.datetime(1971, 1, 1)

        workdir = self.get_workdir(exp_name)

        namelist = workdir / "wrf/namelist.input"
        if not os.path.isfile(namelist):
            return start, end

        with open(namelist, "r") as fid:

            for line in fid:
                if line.startswith("start_date"):
                    tmp = line.split(",")[0]
                    tmp = tmp.split("=")[1].strip()
                    start = dt.datetime.strptime(tmp, "'%Y-%m-%d_%H:%M:%S'")
                elif line.startswith("end_date"):
                    tmp = line.split(",")[0]
                    tmp = tmp.split("=")[1].strip()
                    end = dt.datetime.strptime(tmp, "'%Y-%m-%d_%H:%M:%S'")

        if verbose:
            print("Model start and end:", start, end)

        return start, end

    def get_workdir(self, exp_name):
        exp_path = self.proj_path / exp_name
        archive_path = self.archive_path / exp_name

        if archive_path.exists():  # status='archived'!
            workdir = archive_path
        else:
            workdir = exp_path

        return workdir

    def _update_db_entry(self, exp_name: str, updates: dict):
        """
        A small helper function to update the data base entries. may go to another file at some point.
        """

        df = get_xls(self.filename)

        line = df[df.Name == exp_name]

        new_line = []
        for item in [
            "Name",
            "time",
            "comment",
            "start",
            "end",
            "disk use",
            "runtime",
            "status",
        ]:
            if item in updates:
                new_line.append(updates[item])
            else:
                new_line.append(line[item].values[0])

        df[df.Name == exp_name] = new_line
        df.to_excel(self.filename)

    def _determine_status(self, exp_name):

        status = "unknown"

        exp_path = self.proj_path / exp_name
        archive_path = self.archive_path / exp_name
        workdir = self.get_workdir(exp_name)

        if exp_path.exists():
            status = "created"

            list1 = np.sort(list((workdir / "wrf/").glob("rsl.error*")))
            list2 = np.sort(list((workdir / "log/").glob("rsl.error*")))

            if len(list1) > 0 and len(list2) == 0:
                rsl_file = list1[0]
                with open(rsl_file, "r") as f:
                    lines = f.readlines()
                    if "SUCCESS COMPLETE WRF" in lines[-1]:
                        status = "run complete"
                    else:
                        status = "running or failed"

            elif len(list1) == 0 and len(list2) > 0:
                rsl_file = list2[0]
                with open(rsl_file, "r") as f:
                    lines = f.readlines()
                    if "SUCCESS COMPLETE WRF" in lines[-1]:
                        status = "moved"
                    else:
                        status = "moved prematurely?"
            elif len(list1) > 0 and len(list2) > 0:
                status = "rerunning?"

        if not (workdir / "out").exists():
            status = "damaged"
        else:
            if len(list((workdir / "out").iterdir())) > 0:
                status = "moved"

            if len(list((workdir / "out").glob("*.nc"))) > 0:
                status = "postprocessed"

        if archive_path.exists():
            status = "archived"

        if not exp_path.exists() and not archive_path.exists():
            status = "uncreated"
        else:
            self._update_db_entry(exp_name, {"status": status})
