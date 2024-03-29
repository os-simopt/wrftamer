import pandas as pd
import os
import glob
import shutil
import datetime as dt
import numpy as np
from pathlib import Path
import yaml
from collections import defaultdict
from tqdm import tqdm
from typing import Union
import re

from wrftamer.wrftamer_paths import wrftamer_paths
import wrftamer.wrftamer_functions as wtfun
from wrftamer.process_tslist_files import merge_tslist_files, average_ts_files

from wrftamer import res_path, cfg

home_path, db_path, run_path, arch_path, disc = wrftamer_paths()


def list_projects(verbose=True) -> list:
    """
    Lists all projects that exist.

    Args:
        verbose: can be silent

    """

    list_of_projects = [
        name
        for name in os.listdir(db_path)
        if os.path.isdir(os.path.join(db_path, name))
    ]

    if 'Unassociated_Experiments' in list_of_projects:
        list_of_projects.remove('Unassociated_Experiments')

    if verbose:  # pragma: no cover
        for item in list_of_projects:
            print(item)

    return list_of_projects


def get_csv(filename):
    df = pd.read_csv(
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
    df = get_csv(proj_new.filename)
    # Check if name is unique, otherwise cannot add an experiment of the same name
    if exp_name in df.Name.values:
        raise FileExistsError

    # Add to new db
    new_line = [exp_name, time_of_creation, comment, start, end, du, rt, "created"]
    df.loc[len(df)] = new_line
    df.to_csv(proj_new.filename)

    # remove from old db
    df = get_csv(proj_old.filename)
    idx = df.index[df.Name == exp_name].values
    df = df.drop(idx)
    df.to_csv(proj_old.filename)

    # move actual experiment
    old_workdir = proj_old.get_workdir(exp_name)
    new_workdir = proj_new.get_workdir(exp_name)
    old_workdir.rename(new_workdir)


class Project:
    def __init__(self, name: Union[str, None] = None):

        self.make_submit = cfg['wrftamer_make_submit']

        if name is None:
            name = "Unassociated_Experiments"

        if not re.match(r"^[A-Za-z0-9_-]+$", name):
            raise ValueError('Project name must contain only alphanumeric values, underscores and dashes.')

        self.name = name

    @property
    def tamer_path(self):
        tamer_path = db_path / self.name
        return tamer_path

    @property
    def proj_path(self):
        proj_path = run_path / self.name
        return proj_path

    @property
    def archive_path(self):
        archive_path = arch_path / self.name
        return archive_path

    @property
    def filename(self):
        filename = self.tamer_path / "List_of_Experiments.csv"
        return filename

    # ------------------------------------------------------------------------------------------------------------------
    # Project related methods
    def create(self, verbose=True):
        """
        Creates a directory and an empty csv file named List_of_Experiments.csv
        Creates a directory in run_path named proj_name. Runs should be created there

        Drops an error if proj_name already exists.
        """

        if os.path.isdir(self.tamer_path) or os.path.isdir(self.proj_path):
            raise FileExistsError
        else:
            if verbose:  # pragma: no cover
                print("Creating Project", self.name)

            self.proj_path.mkdir(parents=True)
            self.tamer_path.mkdir(parents=True)

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
            df.to_csv(self.tamer_path / "List_of_Experiments.csv")

        namelist_template = res_path / 'namelist.template'
        wrftamer_conf = res_path / 'configure_template.yaml'
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

        if self.name == "Unassociated_Experiments":
            if verbose:
                print('Default project cannot be removed.')
            return

        if force:
            val = "Yes"
        else:
            print("=============================================================")
            print("                       DANGER ZONE                           ")
            print("Warning! ALL DATA of project", self.name, "will be lost!")
            print("=============================================================")
            val = input("Proceed? Yes/[No]")

        if val in ["Yes"]:

            if verbose:  # pragma: no cover
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

        if not old_tamer_path.is_dir():
            raise FileNotFoundError

        if not old_proj_path.is_dir() and not old_archive_path.is_dir():
            raise FileNotFoundError  # neither on archive nor in run place

        if (
                new_proj_path.is_dir()
                or new_tamer_path.is_dir()
                or new_archive_path.is_dir()
        ):
            raise FileExistsError

        os.rename(old_tamer_path, new_tamer_path)

        if old_proj_path.is_dir():
            os.rename(old_proj_path, new_proj_path)

        if old_archive_path.is_dir():
            os.rename(old_archive_path, new_archive_path)

        self.name = new_name

    def disk_use(self, verbose=True):
        """
        Show the size of all experiments of project <proj_name>

        Args:
            verbose: can be silent

        Returns: None

        """

        if not self.proj_path.is_dir():
            if verbose:  # pragma: no cover
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

        if verbose:  # pragma: no cover
            print("Size of the project", self.name, ": ", proj_size, "bytes")

        return proj_size

    def runtimes(self, verbose=True):
        raise NotImplementedError

    def list_exp(self, verbose=True):

        # Fails with a FileNotFoundError if project does not exist.
        df = get_csv(self.filename)

        if verbose:
            print(df.Name)

        return df.Name.to_list()

    def update_csv(self):
        """
        Calculation of rt, du etc is rather slow, so instead of calling this in the GUI, just call it from time to
        time and write the data into the csv file.
        """

        df = get_csv(self.filename)

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

        df.to_csv(self.filename)

    def cleanup_db(self, verbose=True):

        df = get_csv(self.filename)

        for exp_name in df["Name"]:
            if (self.proj_path / exp_name).is_dir():
                if verbose:  # pragma: no cover
                    print("Experiment", exp_name, "exists")
            else:
                if verbose:  # pragma: no cover
                    print("Experiment", exp_name, "does not exist and is removed from db")
                idx = df.index[df.Name == exp_name].values
                df = df.drop(idx)

        df.to_csv(self.filename)

    # ------------------------------------------------------------------------------------------------------------------
    def exp_create(
            self,
            exp_name,
            comment: str,
            configfile: Union[str, Path],
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

        if not re.match(r"^[A-Za-z0-9_-]+$", exp_name):
            raise ValueError('Experiment name must contain only alphanumeric values, underscores and dashes.')

        # Check if proj_name exists. If no, create
        if not self.proj_path.is_dir():
            self.create()  # always create a project, even if proj_name is None.

        # Check Database
        df = get_csv(self.filename)

        # Check if name is unique, otherwise cannot add an experiment of the same name
        if exp_name in df.Name.values:
            if verbose:  # pragma: no cover
                print("Directories of the experiment do not exist, but an entry in the database does.")
                print("This can happen, if a folder has been removed manually.")
                print("Run cleanup_db to resolve this issue.")
            raise FileExistsError

        # Check folders
        exp_path = self.proj_path / exp_name

        if exp_path.is_dir():
            raise FileExistsError

        if verbose:  # pragma: no cover
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
        df.to_csv(self.filename)

    def exp_copy(self, old_exp_name: str, new_exp_name: str, comment: str, verbose=True):
        """

        Args:
            old_exp_name: the name of the experiment which will be copied
            new_exp_name: the name of the experiment which will be created
            comment: a short entry to descripe the experiment
            verbose: speak with user

        Returns: None

        """

        if not re.match(r"^[A-Za-z0-9_-]+$", new_exp_name):
            raise ValueError('Experiment name must contain only alphanumeric values, underscores and dashes.')

        old_exp_path = self.proj_path / old_exp_name
        new_exp_path = self.proj_path / new_exp_name
        df = get_csv(self.filename)

        status = self.exp_get_status(old_exp_name)
        if status == "archived":
            if verbose:  # pragma: no cover
                print("This run has already been archived and may not be copied.")
            return

        if not old_exp_path.is_dir():
            raise FileNotFoundError

        if new_exp_path.is_dir():
            raise FileExistsError

        # check Database
        # Check if name is unique, otherwise cannot add an experiment of the same name
        if new_exp_name in df.Name.values:
            if verbose:  # pragma: no cover
                print("Directories of the new experiment do not exist, but an entry in the database does.")
                print("This can happen, if a folder has been removed manually.")
                print("Run cleanup_db to resolve this issue.")
            raise FileExistsError

        if verbose:  # pragma: no cover
            print("---------------------------------------")
            print(f"Reusing Experiment {old_exp_name}")
            print(f" as experiment {new_exp_name}")
            print("---------------------------------------")

        wtfun.copy_dirs(old_exp_path, new_exp_path, make_submit=self.make_submit)

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
        df.to_csv(self.filename)

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

        df = get_csv(self.filename)

        if exp_path.is_dir() or archive_path.is_dir():
            remove_dirs = True
        else:
            if verbose:  # pragma: no cover
                print("Directories of experiment not found.")
            remove_dirs = False

        if exp_name in df.Name.values:
            remove_db_entry = True
        else:
            if verbose:  # pragma: no cover
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
            if verbose:  # pragma: no cover
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
                df.to_csv(self.filename)
        else:
            print("Abort. (Yes must be capitalized)")
            return

    def exp_rename(self, old_exp_name: str, new_exp_name: str, verbose=True):

        if not re.match(r"^[A-Za-z0-9_-]+$", new_exp_name):
            raise ValueError('Experiment name must contain only alphanumeric values, underscores and dashes.')

        old_workdir = self.get_workdir(old_exp_name)
        new_workdir = old_workdir.parent / new_exp_name
        # I do not call get_workdir (because this one would be a run dir, so it would fail with archived runs)
        df = get_csv(self.filename)

        if new_workdir.is_dir():
            if verbose:  # pragma: no cover
                print(f"Cannot rename, experiment {new_exp_name} exists.")
            raise FileExistsError

        if old_exp_name not in df.Name.values:
            print(
                f"Directories of the experiment {old_exp_name} do not exist, but an entry in the database does."
            )
            print("This can happen, if a folder has been removed manually.")
            print("Run cleanup_db to resolve this issue.")
            raise FileNotFoundError
        elif new_exp_name in df.Name.values:  # pragma: no cover
            print(f"Directories of the experiment {new_exp_name} do not exist, but an entry in the database does.")
            print("This can happen, if a folder has been removed manually.")
            print("Run cleanup_db to resolve this issue.")
            raise FileExistsError

        if verbose:  # pragma: no cover
            print("---------------------------------------")
            print(f"Renaming Experiment {old_exp_name} to {new_exp_name}")
            print("---------------------------------------")

        wtfun.rename_dirs(old_workdir, new_workdir, self.make_submit)

        # --------------------------------------------------------------------------------------------------------------
        # Database update
        idx = df.index[df.Name == old_exp_name].values
        df.Name.values[idx] = new_exp_name

        df.to_csv(self.filename)

    def exp_run_wps(self, exp_name, verbose=True):

        exp_path = self.proj_path / exp_name

        if verbose:  # pragma: no cover
            print("Running WPS (geogrid, ungrib, metgrid)")

        wtfun.run_wps_command(exp_path, "geogrid")
        wtfun.run_wps_command(exp_path, "ungrib")
        wtfun.run_wps_command(exp_path, "metgrid")

    def exp_restart(self, exp_name: str, restartfile: str, verbose=True):

        exp_path = self.proj_path / exp_name

        if verbose:  # pragma: no cover
            print("---------------------------------------")
            print(f"Restarting Experiment {exp_name} with restart file {restartfile}")
            print("---------------------------------------")

        try:
            date_string = Path(restartfile).name[11::]
            dt.datetime.strptime(date_string, "%Y-%m-%d_%H:%M:%S")
        except ValueError:
            if verbose:  # pragma: no cover
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

        if verbose:  # pragma: no cover
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
            if verbose:  # pragma: no cover
                print("No files to move")

    def exp_process_tslist(
            self, exp_name: str, location: str, domain: str, timeavg: list, verbose=True
    ):

        workdir = self.get_workdir(exp_name)

        outdir = workdir / "out"
        idir = list((workdir / "out").glob("tsfiles*"))

        if len(idir) == 0 or not outdir.is_dir():
            if verbose:  # pragma: no cover
                print(f"Cannot process tslists.")
                print(f"The directory {workdir}/out/tsfiles*' does not exist")
            return

        merge_tslist_files(idir, outdir, location, domain, self.name, exp_name)

        # if tslists exists
        rawlist = list(outdir.glob("raw*"))

        total = len(rawlist)
        for i, rawfile in tqdm(enumerate(rawlist)):
            average_ts_files(str(rawfile), timeavg)

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

        if not exp_path.is_dir():
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

        if verbose:  # pragma: no cover
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
            print("Cannot perform post processing protocol. No valid enty found in configure.yaml")
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
                pass
                print('Map plotting capability removed.')

        self._update_db_entry(exp_name, {"status": "post processed"})

    def exp_du(self, exp_name: str, verbose=True):

        workdir = self.get_workdir(exp_name)

        exp_size = sum(
            os.path.getsize(f)
            for f in workdir.rglob("**")
            if (os.path.isfile(f) and not os.path.islink(f))
        ) / (1024 * 1024)

        if verbose:  # pragma: no cover
            print("Size of the experiment", exp_name, ": ", exp_size, "megabytes")

        return exp_size

    def exp_runtime(self, exp_name: str, verbose=True):

        workdir = self.get_workdir(exp_name)

        infile1 = workdir / "wrf/rsl.error.0000"
        infile2 = workdir / "log/rsl.error.0000"
        if infile1.is_file():
            infile = infile1
        elif infile2.is_file():
            infile = infile2
        else:
            if verbose:  # pragma: no cover
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

        if verbose:  # pragma: no cover
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

        df = get_csv(self.filename)

        select = list(np.repeat(False, len(df)))
        df["select"] = select

        if exp_name is not None:
            df = df[df.Name == exp_name]

        # Change datatypes of start and end to string, since the GUI-Tabulator widget throws an error with timestamps!
        df["start"] = df["start"].astype(str)
        df["end"] = df["end"].astype(str)

        return df

    def exp_provide_all_info(self, exp_name=None):

        df = get_csv(self.filename)

        if exp_name is not None:
            df = df[df.Name == exp_name]

        return df

    def exp_get_status(self, exp_name):

        df = get_csv(self.filename)
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

        if verbose:  # pragma: no cover
            print(loc_list)

        return loc_list

    def exp_start_end(self, exp_name, verbose=True):

        # defaults
        start = dt.datetime(1971, 1, 1)
        end = dt.datetime(1971, 1, 1)

        workdir = self.get_workdir(exp_name)

        namelist = workdir / "wrf/namelist.input"
        if not namelist.is_file():
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

        if verbose:  # pragma: no cover
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

        df = get_csv(self.filename)

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
        df.to_csv(self.filename)

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

        self._update_db_entry(exp_name, {"status": status})
