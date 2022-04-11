import os
import shutil
import pytest

from wrftamer.experiment_management import experiment
from wrftamer.project_management import project

proj_name = 'WRFTAMER_TEST'
proj_name2 = 'WRFTAMER_TEST2'

exp_name1 = 'TEST1'
exp_name2 = 'TEST2'
exp_name3 = 'TEST3'
postprocexp_name = 'POSTPROC_TEST'

try:
    # this is my testfile; not part of the repo
    configfile = os.path.split(os.path.realpath(__file__))[0] + '/resources/configure_test.yaml'
except FileNotFoundError:
    configfile = os.path.split(os.path.realpath(__file__))[0] + '/configure_test.yaml'


# test experiment management with project

@pytest.fixture()
def testproject_exp():
    # creation and removal of a project should work

    test = project(proj_name)  # initialize class
    test.create(testing=True)
    test.add_exp(exp_name1, 'First Experiment')

    exp = experiment(proj_name, exp_name1)
    exp.create(configfile)

    yield exp
    # check if expected dirs and files are really there

    exp.remove(force=True)
    test.remove(force=True)

    # check if dirs and files have been removed sucessfully
    # if removal fails, I may have something to remove manually...


@pytest.fixture()
def postprocexp():
    # Tests associated with this test require an experiment, that has been created and run on the cluster
    # Data must be ready for moval, postprocessing, archiving, restarting and displaying runtimes.

    test = project(proj_name2)  # initialize class
    test.create(testing=True)
    test.add_exp(postprocexp_name, 'First Experiment')

    # manually move a pre-prepared directory into the project directory.
    src = test.proj_path.parent / postprocexp_name
    tgt = test.proj_path

    shutil.move(src, tgt)

    exp = experiment(proj_name2, postprocexp_name)

    yield exp

    #test.remove(force=True) # do not remove the test directory


# -----------------------------------------------------------------------
# Experiment Tests ------------------------------------------------------
# -----------------------------------------------------------------------

def test_remove():
    exp = experiment(proj_name, exp_name1)

    # removal of an experiment that does not exist should fail
    with pytest.raises(FileNotFoundError):
        exp.remove(force=True)


def test_create(testproject_exp):
    # creating a new experiment should work fine.
    # (Ths experiment is created in the fixture. Here is just the test if all files exist as expected)

    # Test here that the whole experiment directory tree exists and that

    list_of_expected_dirs = [
        testproject_exp.exp_path,
        testproject_exp.exp_path / 'log',
        testproject_exp.exp_path / 'out',
        testproject_exp.exp_path / 'plot',
        testproject_exp.exp_path / 'wrf'
    ]
    list_of_expected_files = [
        testproject_exp.exp_path / 'submit_real.sh',
        testproject_exp.exp_path / 'submit_wrf.sh',
        testproject_exp.exp_path / 'configure.yaml'
    ]

    missing = []
    for tmp in list_of_expected_dirs:
        if not os.path.isdir(tmp):
            missing.append(tmp)
    for tmp in list_of_expected_files:
        if not os.path.isfile(tmp):
            missing.append(tmp)

    if len(missing) > 0:
        print('test_create: Missing files or directories!')
        for item in missing:
            print(item)
        raise FileNotFoundError

    # Tests that all links are established
    expected_links = [
        'g1print.exe', 'g2print.exe', 'geogrid.exe', 'metgrid.exe', 'ndown.exe',
        'real.exe', 'tc.exe', 'ungrib.exe', 'wrf.exe',
        'GENPARM.TBL', 'GEOGRID.TBL', 'HLC.TBL', 'LANDUSE.TBL', 'METGRID.TBL',
        'MPTABLE.TBL', 'SOILPARM.TBL', 'URBPARM.TBL', 'VEGPARM.TBL',
        'ozone.formatted', 'ozone_lat.formatted', 'ozone_plev.formatted',
        'RRTM_DATA', 'RRTMG_LW_DATA', 'RRTMG_SW_DATA',
        'aux_file.txt', 'link_grib.csh', 'namelist.wps', 'tslist', 'Vtable']

    missing = []
    for link in expected_links:
        if not os.path.exists(testproject_exp.exp_path / f'wrf/{link}') or not os.path.islink(
                testproject_exp.exp_path / f'wrf/{link}'):
            missing.append(link)

    if len(missing) > 0:
        print('test_create: Problems encounterd with links')
        for item in missing:
            print(item)
        raise FileNotFoundError


@pytest.mark.long
def test_run_wps(testproject_exp):
    # This test takes a while since wps is run completely. I may want to speed this process up in the future?

    # running wps should work fine, if the testexp has been created properly. This is tested in test_create.
    testproject_exp.run_wps(configfile)

    # Test that wps has been executed? That would be a little specific...
    # -> Need well defined testcase


def test_create2(testproject_exp):
    # creating the same experiment twice should fail
    with pytest.raises(FileExistsError):
        testproject_exp.create(configfile)


def test_copy(testproject_exp):
    # reusing an experiment should work fine
    testproject_exp.copy(exp_name2)

    # now, remove exp_name2 as well. Otherwise the test environment is not in a clean state.
    exp2 = experiment(proj_name, exp_name2)
    exp2.remove(force=True)


def test_copy2():
    # reusing an experiment that does not exist should fail

    with pytest.raises(FileNotFoundError):
        exp = experiment(proj_name, exp_name3)
        exp.copy(exp_name2)


def test_copy3(testproject_exp):
    # reusing an experiment with a name that alredy exists should fail.
    with pytest.raises(FileExistsError):
        testproject_exp.copy(exp_name1)


def test_rename(testproject_exp):
    # renaming of an experiment should work fine.
    testproject_exp.rename(exp_name2)


def test_rename2(testproject_exp):
    # renaming of an experiment to an existing name should fail
    with pytest.raises(FileExistsError):
        testproject_exp.rename(exp_name1)


def test_runtime(testproject_exp):
    # Displaying runtimes should work.
    testproject_exp.runtime()


# Tests marked postproc require a test that already has been run.
# This test is destructive. The postproc directory will be removed after the test.

@pytest.mark.postproc
def test_restart():
    # Restart still needs manual testing.
    pass


@pytest.mark.postproc
def test_fullpostprocessing(postprocexp):
    # moving data from an exeperiment should work
    postprocexp.move()
    # postprocessing of tslist data should work
    postprocexp.process_tslist(None, None, ['10'])

    # moving data to the archive should work
    # question: should I an argument to add wrfrst removal to the archive method?
    postprocexp.archive(keep_log=True)

    # displaying the runtimes should work
    # postprocexp.runtimes() will raise a not yet implemented error as of now.

    # finally, removing the project should work at the
    # archive position as well.
    postprocexp.remove(force=True)


@pytest.mark.postproc
def test_process_tslist2():
    # processing tslists of an experiment that does not exists should fail
    with pytest.raises(FileNotFoundError):
        exp = experiment(proj_name, exp_name1)
        exp.process_tslist(None, None, ['10'], False)


@pytest.mark.postproc
def test_archive2():
    # archiving a run that does not exist should fail.
    with pytest.raises(FileNotFoundError):
        exp = experiment(proj_name, exp_name1)
        exp.process_tslist(None, None, ['10'], False)
