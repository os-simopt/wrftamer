import os
import shutil
import datetime as dt
from pathlib import Path, PosixPath
import glob
import pandas as pd
import numpy as np
from collections import defaultdict

from wrftamer.utility import printProgressBar
from wrftamer.process_tslist_files import merge_tslist_files, average_ts_files
from wrftamer.wrftamer_paths import wrftamer_paths
import wrftamer.wrftamer_functions as wtfun
from wrftamer.wrfplotter_classes import Map
import yaml

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

# TODO: check if run is archived by seaching for the actual directory, instead of checking the status.
#  This way, I can perform ppp on archived runs. Right now, this is only possible if I force ppp or manualy
#  change the xls sheet.

# ---------------------------------------------------------------------
# These paths will be used by the tamer and can be changed in the cond environment

home_path, db_path, run_path, archive_path, disc = wrftamer_paths()

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
            df = pd.read_excel(self.filename, index_col='index', usecols=['index', 'Name', 'status'])

            try:
                self.status = df[df.Name == exp_name].status.values[0]
                # TODO: this may cause trouble with the POSTPROC_TEST...
            except IndexError:
                self.status = 'uncreated'

        except FileNotFoundError:
            self.status = 'project uncreated'

        # TODO This causes trouble with split runs.
        #  I need a way to deal with splitruns, special snowflake or not!
        #  DLeuk, 17.01.2022

        if self.archive_path.is_dir(): # archived.
            self.workdir = self.archive_path
        else:
            self.workdir = self.exp_path

        self.max_dom = self._get_maxdom_from_config()

    #-------------------------------------------------------------------------------------------------------------------
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

        self.status = 'created'
        self._update_db_entry({'status': 'created'})

    def run_wps(self, verbose=True):

        # may require a check that all files needed are really there.

        if verbose:
            print('Running WPS (geogrid, ungrib, metgrid)')

        wtfun.run_wps_command(self.exp_path, 'geogrid')
        wtfun.run_wps_command(self.exp_path, 'ungrib')
        wtfun.run_wps_command(self.exp_path, 'metgrid')

    def copy(self, new_exp_name, verbose=True):

        new_exp_path = self.exp_path.parent / new_exp_name

        if self.status == 'archived':
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
        Initialize this class with status = archived in this case

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
            if self.status == 'archived':
                shutil.rmtree(self.archive_path)  # raises FileNotFoundError on failure
            else:
                shutil.rmtree(self.exp_path)  # raises FileNotFoundError on failure

    def rename(self, new_exp_name, verbose=True):

        if verbose:
            print("---------------------------------------")
            print(f'Renaming Experiment {self.name} to {new_exp_name}')
            print("---------------------------------------")

        if self.status == 'archived':
            new_workdir = self.archive_path.parent / new_exp_name
        else:
            new_workdir = self.exp_path.parent / new_exp_name

        if os.path.isdir(new_workdir):
            raise FileExistsError

        wtfun.rename_dirs(self.workdir, new_workdir, make_submit)

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

        print(namelistfile)
        print(restartfile)

        wtfun.update_namelist_for_rst(restartfile, namelistfile, outfile)

        self.status = 'restarted'
        self._update_db_entry({'status': 'restarted'})

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

            self.status = 'moved'
            self._update_db_entry({'status': 'moved'})

        else:
            if verbose:
                print('No files to move')

    def process_tslist(self, location, domain, timeavg: list, verbose=True):

        # TODO: merge_tslist_files take quite a lot of time.
        #  Put here some code to preform this task only if the files do not exist
        #  And add a force option to do it anyway.

        outdir = self.workdir / 'out'
        idir = (self.workdir / 'out').glob('tsfiles*')

        if not idir:
            if verbose:
                print(f"the directory {self.workdir}/out/tsfiles*' does not exist")
            raise FileNotFoundError

        merge_tslist_files(idir, outdir, location, domain, self.proj_name, self.name)

        # if tslists exists
        rawlist = list(outdir.glob('raw*'))

        total = len(rawlist)
        printProgressBar(0, total, prefix='Progress:', suffix='Complete', length=50)
        for i, rawfile in enumerate(rawlist):
            average_ts_files(str(rawfile), timeavg)
            printProgressBar(i + 1, total, prefix='Progress:', suffix='Complete', length=50)

        self.status = 'post processed'
        self._update_db_entry({'status': 'post processed'})

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
        self.status = 'archived'
        self._update_db_entry({'status': 'archived'})

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

    def run_postprocessing_protocol(self, verbose=True):

        configure_file = self.workdir / 'configure.yaml'

        with open(configure_file) as f:
            cfg = yaml.safe_load(f)

        try:
            ppp = cfg['pp_protocol']
        except KeyError:
            print('Cannot perform post processing protocol. No valid enty found in configure.yaml')
            return

        for item in ppp:
            print(item)
            if item == 'move':
                if ppp[item] == 1:
                    self.move(verbose)

            elif item == 'tslist_processing':
                if ppp[item] == 0:
                    pass
                else:
                    if ppp[item] == 1:
                        # no options found. perform Raw processing of all files without any averaging.
                        location = None
                        domain = None
                        timeavg = None
                    else:
                        # found some options
                        try:
                            location = ppp[item]['location']
                        except KeyError:
                            location = None
                        try:
                            domain = ppp[item]['domain']
                        except KeyError:
                            domain = None
                        try:
                            timeavg = ppp[item]['timeavg']
                        except KeyError:
                            timeavg = None

                    self.process_tslist(location, domain, timeavg, verbose)

            elif item == 'create_maps':

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

                if ppp[item] == 0:
                    pass
                else:
                    if ppp[item] == 1:
                        # Only perform standard map plotting (i.e., ml=5, var=WSP, poi=None
                        list_of_mls = [5]
                        list_of_vars = ['WSP']
                        list_of_doms = ['d01']
                        poi = pd.DataFrame()
                        store = True

                    else:
                        # found some options
                        try:
                            list_of_doms = ppp[item]['list_of_domains']
                        except KeyError:
                            list_of_doms = ['d01']
                        try:
                            list_of_mls = ppp[item]['list_of_model_levels']
                        except KeyError:
                            list_of_mls = [5]
                        try:
                            list_of_vars = ppp[item]['list_of_variables']
                        except KeyError:
                            list_of_vars = ['WSP']
                        try:
                            poi_file = ppp[item]['poi_file']
                            poi = pd.read_csv(poi_file, delimiter=';')  # points of interest
                        except KeyError:
                            poi = pd.DataFrame()
                        try:
                            store = bool(ppp[item]['store'])
                        except:
                            store = True

                    plot_path = self.exp_path / 'plot'
                    intermediate_path = self.exp_path / 'out'
                    fmt = 'png'

                    cls = Map(poi=poi, plot_path=plot_path, intermediate_path=intermediate_path, fmt=fmt)

                    for dom in list_of_doms:
                        inpath = self.exp_path / 'out'
                        filenames = list(sorted(inpath.glob(f'wrfout_{dom}*')))
                        for filename in filenames:
                            for ml in list_of_mls:
                                for var in list_of_vars:
                                    cls.extract_data_from_wrfout(filename, dom, var, ml, select_time=-1)

                                    if store:
                                        cls.store_intermediate()
                                    else:
                                        cls.plot()

        self.status = 'post processed'
        self._update_db_entry({'status': 'post processed'})

    #-------------------------------------------------------------------------------------------------------------------
    def _update_db_entry(self, updates: dict):
        """
        A small helper function to update the data base entries. may go to another file at some point.
        """

        df = pd.read_excel(self.filename, index_col='index', usecols=['index', 'Name', 'time', 'comment',
                                                                      'start', 'end', 'disk use', 'runtime',
                                                                      'status'])

        line = df[df.Name == self.name]

        new_line = []
        for item in ['Name', 'time', 'comment', 'start', 'end', 'disk use', 'runtime', 'status']:

            if item in updates:
                new_line.append(updates[item])
            else:
                new_line.append(line[item].values[0])

        df[df.Name == self.name] = new_line
        df.to_excel(self.filename)

    def _determine_status(self):

        self.status = 'unknown'

        if self.exp_path.exists():
            self.status = 'created'

            list1 = np.sort(list((self.workdir / 'wrf/').glob('rsl.error*')))
            list2 = np.sort(list((self.workdir / 'log/').glob('rsl.error*')))

            if len(list1) > 0 and len(list2) == 0:
                rsl_file = list1[0]
                with open(rsl_file, 'r') as f:
                    lines = f.readlines()
                    if 'SUCCESS COMPLETE WRF' in lines[-1]:
                        self.status = 'run complete'
                    else:
                        self.status = 'running or failed'

            elif len(list1) == 0 and len(list2) > 0:
                rsl_file = list2[0]
                with open(rsl_file, 'r') as f:
                    lines = f.readlines()
                    if 'SUCCESS COMPLETE WRF' in lines[-1]:
                        self.status = 'moved'
                    else:
                        self.status = 'moved prematurely?'
            elif len(list1) > 0 and len(list2) > 0:
                self.status = 'rerunning?'

        if not (self.workdir / 'out').exists():
            self.status = 'damaged'
        else:
            if len(list((self.workdir / 'out').iterdir())) > 0:
                self.status = 'moved'

            if len(list((self.workdir / 'out').glob('*.nc'))) > 0:
                self.status = 'postprocessed'

        if self.archive_path.exists():
            self.status = 'archived'

        self._update_db_entry({'status': self.status})

    def _get_maxdom_from_config(self):

        configure_file = self.workdir / 'configure.yaml'

        with open(configure_file) as f:
            try:
                cfg = yaml.safe_load(f)
            except FileNotFoundError:
                return None

        try:
            max_dom = cfg['namelist_vars']['max_dom']
        except KeyError:
            max_dom = 1

        return max_dom