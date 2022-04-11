import pandas as pd
import os
import shutil
import datetime as dt
import numpy as np
from wrftamer.experiment_management import experiment
from wrftamer.wrftamer_paths import wrftamer_paths

"""
A management tool for WRF Projects.
Each Project is associated with several experiments.
For each project, a directory is create in the run directory and anoter one in the .wrftamer directory

Tools:
project
    create
    remove
    rename
    list
    du
    runtimes
    
experiments
    add (or create?)
    remove
    rename
    list
    du
    runtimes    
"""

# ---------------------------------------------------------------------

# These paths will be used by the tamer and can be changed in the cond environment
# The defaults are $HOME/.wrtfaner and $HOME/run


home_path, db_path, run_path, archive_path, disc = wrftamer_paths()


def reassociate(proj_old, proj_new, exp_name: str):
    """
    Associate <exp_name> with <proj_new>. Unassociate this exp with <proj_old>

    Args:
        proj_old: the old project <exp_name> belongs to
        proj_new: the new project the experiment should be associated with
        exp_name: experiment name
    """

    df = proj_old.provide_all_info(exp_name)

    name, time, comment, start, end, du, rt, status = tuple(df.to_numpy()[0])

    proj_new.add_exp(exp_name, comment=comment, start=start, end=end, time=time, verbose=False)

    exp_old = experiment(proj_old.name, exp_name)
    exp_new = experiment(proj_new.name, exp_name)

    exp_old.workdir.rename(exp_new.workdir)

    proj_old.remove_exp(exp_name, verbose=False, force=True)


def list_projects(verbose=True):
    """
    Lists all projects that exist.

    Args:
        verbose: can be silent for testing

    """

    list_of_projects = [name for name in os.listdir(db_path) if
                        os.path.isdir(os.path.join(db_path, name))]

    if verbose:
        for item in list_of_projects:
            print(item)

    return list_of_projects


def list_unassociated_exp(verbose=True):
    filename = db_path / 'List_of_unassociated_Experiments.xlsx'

    df = pd.read_excel(filename, index_col='index', usecols=['index', 'Name', 'time'])

    if verbose:
        print(df.Name)

    mylist = [item for item in df.Name]

    return mylist


class project:

    def __init__(self, name):

        self.name = name

        if name is None:  # do not use the project feature. However, unassociated experiments are being tracked.
            self.proj_path = run_path
            self.tamer_path = db_path
            self.filename = self.tamer_path / 'List_of_unassociated_Experiments.xlsx'
        else:
            self.proj_path = run_path / name
            self.tamer_path = db_path / name
            self.filename = self.tamer_path / 'List_of_Experiments.xlsx'

    # Project related methods
    def create(self, testing=False, verbose=True):
        """
        Creates a hidden directory and an empty xls file named List_of_Experiments.xls
        Creates a directory in run_path named proj_name. Runs should be created there

        Drops an error if proj_name already exists.
        """

        if self.name is None:
            return  # this feature may not be used without a project name.

        # reserved names. Do not let user use these names, as the directories are destroyed
        # during tests. Do I need this?
        if not testing and self.name in ['TEST_PROJECT', 'TEST_PROJECT2']:
            print('The project names TEST_PROJECT and TEST_PROJECT2 are reserved for testing')
            print('Please use a different name')
            return

        if os.path.isdir(self.tamer_path) or os.path.isdir(self.proj_path):
            raise FileExistsError
        else:
            if verbose:
                print('Creating Project', self.name)

            os.mkdir(self.proj_path)
            os.mkdir(self.tamer_path)

            df = pd.DataFrame(columns=['index', 'Name', 'time', 'comment', 'start', 'end', 'disk use', 'runtime',
                                       'status'])
            df.set_index('index')
            df.to_excel(self.tamer_path / 'List_of_Experiments.xlsx')

        namelist_template = os.path.split(os.path.realpath(__file__))[0] + '/resources/namelist.template'
        wrftamer_conf = os.path.split(os.path.realpath(__file__))[0] + '/resources/configure_template.yaml'

        newfile = self.proj_path / 'namelist.template'
        new_conf = self.proj_path / 'configure_template.yaml'

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

        if self.name is None:
            return  # this feature may not be used without a project name.

        if force:
            val = 'Yes'
        else:
            print('=============================================================')
            print('                       DANGER ZONE                           ')
            print('Warning! ALL DATA of project', self.name, 'will be lost!')
            print('=============================================================')
            val = input("Proceed? Yes/[No]")

        if val in ['Yes']:

            if verbose:
                print('Removing', self.proj_path)
                print('Removing', self.tamer_path)

            shutil.rmtree(self.proj_path)  # raises FileNotFoundError on failure
            shutil.rmtree(self.tamer_path)

        else:
            print('Abort. (Yes must be capitalized)')

    def rename(self, new_name: str, testing=False, verbose=True):
        """
        Renames the directory that is associated with a project
        """

        if self.name is None:
            return  # this feature may not be used without a project name.

        # reserved names. Do not let user use these names, as the directories are destroyed
        # during tests. Do I need this?
        if not testing and new_name in ['TEST_PROJECT', 'TEST_PROJECT2']:
            print('The project names TEST_PROJECT and TEST_PROJECT2 are reserved for testing')
            print('Please use a different name')
            return

        old_proj_path = self.proj_path
        new_proj_path = run_path / new_name

        old_tamer_path = self.tamer_path
        new_tamer_path = db_path / new_name

        if not os.path.isdir(old_proj_path) or not os.path.isdir(old_tamer_path):
            raise FileNotFoundError

        if os.path.isdir(new_proj_path) or os.path.isdir(new_tamer_path):
            raise FileExistsError

        os.rename(old_proj_path, new_proj_path)
        os.rename(old_tamer_path, new_tamer_path)

        self.name = new_name
        self.proj_path = new_proj_path
        self.tamer_path = new_tamer_path

    def disk_use(self, verbose=True):
        """
        Show the size of all experiments of project <proj_name>

        Args:
            verbose: can be silent for testing

        Returns: None

        """

        if not os.path.isdir(self.proj_path):
            if verbose:
                print('This project does not exist')
            raise FileNotFoundError

        proj_size1 = sum(os.path.getsize(f) for f in self.proj_path.rglob('**')
                         if (os.path.isfile(f) and not os.path.islink(f)))

        proj_size2 = sum(os.path.getsize(f) for f in (archive_path / self.name).rglob('**')
                         if (os.path.isfile(f) and not os.path.islink(f)))

        proj_size = proj_size1 + proj_size2

        if verbose:
            print('Size of the project', self.name, ': ', proj_size, 'bytes')

        return proj_size

    def runtimes(self, verbose=True):
        raise NotImplementedError

    # Experiment related methods
    def add_exp(self, exp_name: str, comment: str, start=dt.datetime(1971, 1, 1), end=dt.datetime(1971, 1, 1),
                time=None, verbose=True):
        """
        Add all relevant information regarding a certain
        experiment to the xls file.
        Relevant Information includes:

        - The Run-ID will equal the index. Makes things a lot easier.

        - Name of the Run (does not have to be unique???)
        - datetime the experiment was created
        - either a copy (better) or, for now, the path and name to the config file
        - Optional, but recommended: A comment on what the run does.
        - A path where plots will be found
        - A path where output will be found

        This function should be called by wt create or for adding runs to the database after they have been created.
        This function does not create a run directory!
        """

        # first, read xlsx to pandas dataframe.
        # if this failes, then the project does not exist or is damaged -> FileNotFoundError
        df = pd.read_excel(self.filename, index_col='index',
                           usecols=['index', 'Name', 'time', 'comment', 'start', 'end', 'disk use', 'runtime',
                                    'status'])

        # Check if name is unique, otherwise cannot add an experiment of the same name
        if exp_name in df.Name.values:
            raise FileExistsError

        # Now, add new line with information.
        now = dt.datetime.utcnow().strftime('%Y.%m.%d %H:%M:%S')
        if time is None:
            time = now

        du = np.nan
        rt = np.nan

        new_line = [exp_name, time, comment, start, end, du, rt, 'added']

        df.loc[len(df)] = new_line
        df.to_excel(self.filename)

    def remove_exp(self, exp_name: str, verbose=True, force=False):
        """
        Searches for the experiment <exp_name> in Project <proj_name> and
        removes it from the list.

        Does not remove the run directory! This is only for the management of the database.
        It is important that the associated run directories are not deleted. This way I can
        use this function to remove erros in the database.

        Args:
            exp_name: name of the experiment
            verbose: speak with user
            force: circumvent user interface for testing

        Returns: None

        """

        # if this failes, then the project does not exist or is damaged -> FileNotFoundError
        df = pd.read_excel(self.filename, index_col='index',
                           usecols=['index', 'Name', 'time', 'comment', 'start', 'end', 'disk use', 'runtime',
                                    'status'])

        if exp_name in df.Name.values:

            if force:
                val = 'Yes'
            else:
                print('=============================================================')
                print('                       DANGER ZONE                           ')
                print('Warning, all data of experiment', exp_name, ' in the database will be lost!')
                print('=============================================================')
                val = input("Proceed? Yes/[No]")

            if val in ['Yes']:
                idx = df.index[df.Name == exp_name].values
                df = df.drop(idx)
                df.to_excel(self.filename)
        else:
            if verbose:
                print('Experiment not part of the Project', self.name)
            raise FileNotFoundError

    def rename_exp(self, old_exp_name: str, new_exp_name: str, verbose=True):
        """
        Changes the name of an experiment to a new one. All references in the database are changed as well,
        but the run-directory is not! For this reason, exp_rename should be called by wt rename or used to
        correct errors in the database.

        Args:
            old_exp_name: old experiment name
            new_exp_name: new experiment name
            verbose: speak with user

        Returns: None

        """

        # if this failes, then the project does not exist or is damaged -> FileNotFoundError
        df = pd.read_excel(self.filename, index_col='index',
                           usecols=['index', 'Name', 'time', 'comment', 'start', 'end', 'disk use', 'runtime',
                                    'status'])

        if old_exp_name not in df.Name.values:
            raise FileNotFoundError
        elif new_exp_name in df.Name.values:
            raise FileExistsError
        else:
            idx = df.index[df.Name == old_exp_name].values
            df.Name[idx] = new_exp_name

            df.to_excel(self.filename)

    def list_exp(self, verbose=True):

        # Fails with a FileNotFoundError if project does not exist.
        df = pd.read_excel(self.filename, index_col='index', usecols=['index', 'Name'])

        if verbose:
            print(df.Name)

        return df.Name.to_list()

    def rewrite_xls(self):
        """
        Sometimes, when I edit the xls shet manually, It happens that it is stored with tousands of lines, all containing
        just nans. This makes the wrftamer and especially the GUI extremely slow. An xlsx sheet like this must be reead
        and rewritten. This function does exactly that.
        """

        df = pd.read_excel(self.filename, index_col='index',
                           usecols=['index', 'Name', 'time', 'comment', 'start', 'end', 'disk use', 'runtime',
                                    'status'])
        df = df[np.isfinite(df.index)]
        df.to_excel(self.filename)

    def update_xlsx(self):
        """
        Calculation of rt, du etc is rather slow, so instead of calling this in the GUI, just call it from time to
        time and write the data into the xlsx sheet.
        """

        df = pd.read_excel(self.filename, index_col='index',
                           usecols=['index', 'Name', 'time', 'comment', 'start', 'end', 'disk use', 'runtime',
                                    'status'])

        exp_list = df.Name.to_list()

        for idx, exp_name in enumerate(exp_list):
            exp = experiment(self.name, exp_name)

            start, end = exp.start_end(verbose=False)
            du = exp.du(verbose=False)
            rt = exp.runtime(verbose=False)

            time = df.time[idx]
            comment = df.comment[idx]
            status = df.status[idx]

            new_line = [exp.name, time, comment, start, end, du, rt, status]
            df.loc[idx] = new_line

        df.to_excel(self.filename)

    def provide_info(self, exp_name=None):

        df = pd.read_excel(self.filename, index_col='index',
                           usecols=['index', 'Name', 'start', 'end', 'disk use', 'runtime', 'status'])

        select = [False for idx in range(len(df))]
        df['select'] = select

        if exp_name is not None:
            df = df[df.Name == exp_name]

        # Change datatypes of start and end to string, since the GUI-Tabulator widget throws an error with timestamps!
        df['start'] = df['start'].astype(str)
        df['end'] = df['end'].astype(str)

        return df

    def provide_all_info(self, exp_name=None):

        df = pd.read_excel(self.filename, index_col='index',
                           usecols=['index', 'Name', 'time', 'comment', 'start', 'end', 'disk use', 'runtime',
                                    'status'])

        if exp_name is not None:
            df = df[df.Name == exp_name]

        return df

    def cleanup_db(self, verbose=True):

        df = pd.read_excel(self.filename, index_col='index',
                           usecols=['index', 'Name', 'time', 'comment', 'start', 'end', 'disk use', 'runtime',
                                    'status'])

        for exp_name in df['Name']:
            if (self.proj_path / exp_name).is_dir():
                if verbose:
                    print('Experiment', exp_name, 'exists')
            else:
                if verbose:
                    print('Experiment', exp_name, 'does not exist and is removed from db')
                idx = df.index[df.Name == exp_name].values
                df = df.drop(idx)

        df.to_excel(self.filename)
