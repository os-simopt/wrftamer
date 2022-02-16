import os
import shutil
import datetime as dt
from pathlib import Path
import glob
import pandas as pd
import numpy as np
from collections import defaultdict

from wrftamer.utility import printProgressBar
from wrftamer.process_tslist_files import merge_tslist_files, average_ts_files
from wrftamer.wrftamer_paths import wrftamer_paths
import wrftamer.wrftamer_functions as wtfun

# from wrftamer.wrf_timing import wrf_timing
"""
A management tool for WRF Experiments
A WRF Experiment is a directory with a certain structure of subfolders in which a WRF run is set up and run.
This includes: 
WPS (geogrid, ungrib, metgrid)
WRF (real, wrf)
linking of all relevant data
postprocessing of data

Author: Daniel Leukauf
Date: 22.11.2021
"""

# ---------------------------------------------------------------------
# These paths will be used by the tamer and can be changed in the cond environment

home_path, db_path, run_path, archive_path = wrftamer_paths()

try:
    make_submit = bool(os.environ['WRFTAMER_make_submit'])
except KeyError:
    make_submit = False


class experiment:

    def __init__(self, proj_name, exp_name):
        """

        Class to hande experiments

        Args:
            proj_name: The name of a project this run is associated with. May be None
            exp_name: The name of this experiment
        """

        self.name = exp_name
        self.proj_name = proj_name

        if proj_name is None:
            self.exp_path = run_path / exp_name
            self.archive_path = archive_path / exp_name
            tamer_path = db_path
            self.filename = tamer_path / 'List_of_unassociated_Experiments.xlsx'
        else:
            self.exp_path = run_path / proj_name / exp_name
            self.archive_path = archive_path / proj_name / exp_name
            tamer_path = db_path / proj_name
            self.filename = tamer_path / 'List_of_Experiments.xlsx'

        # Check if file is archived. If the experiment has not yet been created, this will fail.
        try:
            df = pd.read_excel(self.filename, index_col='index', usecols=['index', 'Name', 'archived'])
            series = df[df.Name == exp_name].archived
            if len(series) > 0:
                self.is_archived = bool(int(series))
            else:
                self.is_archived = False

        except FileNotFoundError:
            self.is_archived = False

        # TODO This causes trouble with split runs.
        #  I need a way to deal with splitruns, special snowflake or not!
        #  DLeuk, 17.01.2022

        if self.is_archived:
            self.workdir = self.archive_path
        else:
            self.workdir = self.exp_path

    def create(self, configfile: str, namelisttemplate=None, verbose=True):

        """
        Create the directory structure of an experiment.

        Args:
            configfile: a yaml file that contains all information to create an experiment.
            namelisttemplate: the template of the namelist to use
            verbose: speak with user

        Returns: None
        """

        if os.path.isdir(self.exp_path):
            raise FileExistsError

        if verbose:
            print("---------------------------------------")
            print(f'Creating Experiment {self.name}')
            print(f' in directory {self.exp_path}')
            print("---------------------------------------")

        # create run directory, link files
        wtfun.create_rundir(self.exp_path, configfile, namelisttemplate)

        # make submit-files
        if make_submit:
            wtfun.make_submitfiles(self.exp_path, configfile)

    def run_wps(self, verbose=True):

        # may require a check that all files needed are really there.

        if verbose:
            print('Running WPS (geogrid, ungrib, metgrid)')

        wtfun.run_wps_command(self.exp_path, 'geogrid')
        wtfun.run_wps_command(self.exp_path, 'ungrib')
        wtfun.run_wps_command(self.exp_path, 'metgrid')

    def copy(self, new_exp_name, verbose=True):

        new_exp_path = self.exp_path.parent / new_exp_name

        if self.is_archived:
            if verbose:
                print('This run has already been archived and may not be copied.')
            return

        if not os.path.isdir(self.exp_path):
            raise FileNotFoundError

        if os.path.isdir(new_exp_path):
            raise FileExistsError

        if verbose:
            print("---------------------------------------")
            print(f'Reusing Experiment {self.name}')
            print(f' as experiment {new_exp_name}')
            print("---------------------------------------")

        wtfun.copy_dirs(self.exp_path, new_exp_path)

    def remove(self, verbose=True, force=False):
        """

        This method is a clean way to remove a project. The project may already be archived.
        Initialize this class with is_archived = True in this case

        Args:
            verbose: Speak with user
            force: forced removal for testing

        Returns: None

        """

        if verbose:
            print("---------------------------------------")
            print(f'Removing Experiment {self.name}')
            print("---------------------------------------")

        if force:
            val = 'Yes'
        else:
            print('=============================================================')
            print('                       DANGER ZONE                           ')
            print(f'Warning, all data of experiment {self.name} will be lost!   ')
            print('=============================================================')
            val = input("Proceed? Yes/[No]")

        if val in ['Yes']:
            if self.is_archived:
                shutil.rmtree(self.archive_path)  # raises FileNotFoundError on failure
            else:
                shutil.rmtree(self.exp_path)  # raises FileNotFoundError on failure

    def rename(self, new_exp_name, verbose=True):

        if verbose:
            print("---------------------------------------")
            print(f'Renaming Experiment {self.name} to {new_exp_name}')
            print("---------------------------------------")

        if self.is_archived:
            new_workdir = self.archive_path.parent / new_exp_name
        else:
            new_workdir = self.exp_path.parent / new_exp_name

        if os.path.isdir(new_workdir):
            raise FileExistsError

        wtfun.rename_dirs(self.workdir, new_workdir, make_submit)  # make submit should be bool.

        self.name = new_exp_name
        self.exp_path = self.exp_path.parent / new_exp_name
        self.archive_path = self.archive_path.parent / new_exp_name
        self.workdir = new_workdir

    def restart(self, restartfile, verbose=True):

        if verbose:
            print("---------------------------------------")
            print(f'Restarting Experiment {self.name} with restart file {restartfile}')
            print("---------------------------------------")

        try:
            date_string = Path(restartfile).name[11::]
            dt.datetime.strptime(date_string, '%Y-%m-%d_%H:%M:%S')
        except ValueError:
            if verbose:
                print(f'File {restartfile} does not have the format %Y-%m-%d_%H:%M:%S')
                print('A Path in front of the filename is fine')
            raise NameError

        wtfun.move_output(self.exp_path)

        namelistfile = self.exp_path / 'wrf' / 'namelist.input'
        outfile = namelistfile

        wtfun.update_namelist_for_rst(restartfile, namelistfile, outfile)

    def move(self, verbose=True):

        if verbose:
            print("---------------------------------------")
            print("Moving model output to out and log dirs")
            print(f"Source: {self.workdir}/wrf/")
            print("---------------------------------------")

        if any([len(list((self.workdir / 'wrf').glob('*.log'))) > 0,
                len(list((self.workdir / 'wrf').glob('*.rsl'))) > 0,
                len(list((self.workdir / 'wrf').glob('wrfout*'))) > 0,
                len(list((self.workdir / 'wrf').glob('wrfaux*'))) > 0,
                len(list((self.workdir / 'wrf').glob('*.UU'))) > 0]):

            wtfun.move_output(self.workdir)

        else:
            if verbose:
                print('No files to move')

    def process_tslist(self, location, domain, timeavg: list, verbose=True):

        outdir = self.workdir / 'out'
        idir = (self.workdir / 'out').glob('tsfiles*')
        if not idir:
            if verbose:
                print(f"the directory {self.workdir}/out/tsfiles*' does not exist")
            raise FileNotFoundError

        merge_tslist_files(idir, outdir, location, domain)

        # if tslists exists
        rawlist = list(outdir.glob('raw*'))

        total = len(rawlist)
        printProgressBar(0, total, prefix='Progress:', suffix='Complete', length=50)
        for i, rawfile in enumerate(rawlist):

            average_ts_files(str(rawfile), timeavg)
            printProgressBar(i + 1, total, prefix='Progress:', suffix='Complete', length=50)

    def archive(self, keep_log=False, verbose=True):

        """

        The run directory of this experiment will be moved to the archive directory set
        in the environement variable WRFTAMER_ARCHIVE_PATH.

        Files that are no longer needed will be deleted. This includes:
        - the whole log directory (unlsee keep_log = True)
        - all linked files, wrf-specific filse, files generatred by WPS or real.exe

        """

        if not os.path.isdir(self.exp_path):
            raise FileNotFoundError

        if not keep_log:
            shutil.rmtree(self.exp_path / 'log', ignore_errors=True)

        filelist = []
        filelist.extend(list((self.exp_path / 'wrf').glob('GRIBFILE.*')))
        filelist.extend(list((self.exp_path / 'wrf').glob('FILE*')))
        filelist.extend(list((self.exp_path / 'wrf').glob('PFILE*')))
        filelist.extend(list((self.exp_path / 'wrf').glob('*.TBL')))
        filelist.extend(list((self.exp_path / 'wrf').glob('*.exe')))
        filelist.extend(list((self.exp_path / 'wrf').glob('ozone*')))
        filelist.extend(list((self.exp_path / 'wrf').glob('Vtable')))
        filelist.extend(list((self.exp_path / 'wrf').glob('RRTM*')))
        filelist.extend(list((self.exp_path / 'wrf').glob('wrfbdy*')))
        filelist.extend(list((self.exp_path / 'wrf').glob('wrfinput*')))
        filelist.extend(list((self.exp_path / 'wrf').glob('geo_em*')))
        filelist.extend(list((self.exp_path / 'wrf').glob('met_em*')))
        filelist.extend(list((self.exp_path / 'wrf').glob('*.log')))
        filelist.extend(list((self.exp_path / 'wrf').glob('link_grib.csh')))
        filelist.extend(list((self.exp_path / 'wrf').glob('namelist.output')))

        for myfile in filelist:
            os.remove(myfile)

        if verbose:
            print("---------------------------------------")
            print("Archiving model output")
            print(f"Source: {self.exp_path}")
            print(f"Target: {self.archive_path}")
            print("---------------------------------------")

        self.exp_path.rename(self.archive_path)
        self.is_archived = True

        # update xls sheet.
        df = pd.read_excel(self.filename, index_col='index', usecols=['index', 'Name', 'start', 'end', 'disk use',
                                                                      'runtime', 'archived'])
        line = df[df.Name == self.name]
        new_line = [line.Name[0], line.start[0], line.end[0], line['disk use'][0], line.runtime[0], True]
        df[df.Name == self.name] = new_line
        df.to_excel(self.filename)

    def du(self, verbose=True):

        exp_size = sum(os.path.getsize(f) for f in self.workdir.rglob('**')
                       if (os.path.isfile(f) and not os.path.islink(f))) / (1024 * 1024)

        if verbose:
            print('Size of the experiment', self.name, ': ', exp_size, 'megabytes')

        return exp_size

    def runtime(self, verbose=True):

        infile1 = self.workdir / 'wrf/rsl.error.0000'
        infile2 = self.workdir / 'log/rsl.error.0000'
        if os.path.isfile(infile1):
            infile = infile1
        elif os.path.isfile(infile2):
            infile = infile2
        else:
            if verbose:
                print('logfile rsl.error.0000 not found. Cannot calculate wrf timing')
            total_time = np.nan
            return total_time

        domains = defaultdict(list)
        domains_w = defaultdict(list)
        with open(infile, 'r') as f:
            for line in f:
                if line.startswith('Timing for main:'):
                    dom = int(line.split()[7][:-1])
                    time = float(line.split()[8])
                    domains[dom].append(time)
                elif line.startswith('Timing for Writing'):
                    dom = int(line.split()[6][:-1])
                    time = float(line.split()[7])
                    domains_w[dom].append(time)

        if verbose:
            print('Average/median WRF timing [seconds]:')
            print('|        |           mean           |          median          |')
            print('| domain | calc time | writing time | calc time | writing time |')
            for i in range(7):
                if i in domains:
                    print(f'|   {i:2d}   | {np.mean(domains[i]):9.3f} |'
                          f'  {np.mean(domains_w[i]):11.3f} | {np.median(domains[i]):9.3f} |'
                          f'  {np.median(domains_w[i]):11.3f} |')

            print('\n\nMaximum WRF timing [seconds]:')
            print('| domain | calc time | writing time |')
            for i in range(7):
                if i in domains:
                    print(f'|   {i:2d}   | {np.max(domains[i]):9.3f} |'
                          f'  {np.max(domains_w[i]):11.3f} |')

            print('\n\nTotal WRF timing [days]:')
            print('| domain | calc time | writing time | total')
            for i in range(7):
                if i in domains:
                    print(f'|   {i:2d}   | {np.sum(domains[i]) / 3600 / 24:9.3f} |'
                          f'  {np.sum(domains_w[i]) / 3600 / 24:11.3f} |'
                          f'  {(np.sum(domains[i]) + np.sum(domains_w[i])) / 3600 / 24:11.3f} |'
                          )

        total_time = 0
        for dom in domains:
            total_time += sum(domains[dom] + domains_w[dom])

        return total_time

    def start_end(self, verbose=True):

        # defaults
        start = dt.datetime(1971, 1, 1)
        end = dt.datetime(1971, 1, 1)

        namelist = self.workdir / 'wrf/namelist.input'
        if not os.path.isfile(namelist):
            return start, end

        with open(namelist, 'r') as fid:

            for line in fid:
                if line.startswith('start_date'):
                    tmp = line.split(',')[0]
                    tmp = tmp.split('=')[1].strip()
                    start = dt.datetime.strptime(tmp, "'%Y-%m-%d_%H:%M:%S'")
                elif line.startswith('end_date'):
                    tmp = line.split(',')[0]
                    tmp = tmp.split('=')[1].strip()
                    end = dt.datetime.strptime(tmp, "'%Y-%m-%d_%H:%M:%S'")

        if verbose:
            print('Model start and end:', start, end)

        return start, end

    def list_tslocs(self, verbose=True):
        """
        get list of location for which tsfiles are available.
        retuns a sorted list.
        """

        mylist = glob.glob(str(self.workdir) + '/out/tsfiles*/*')
        loc_list = list(set([item.rsplit('/', 1)[1].split('.')[0] for item in mylist]))
        loc_list.sort()

        if verbose:
            print(loc_list)

        return loc_list
