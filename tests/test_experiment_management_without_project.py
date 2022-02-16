from wrftamer.experiment_management import experiment
import pytest
import os

exp_name1 = 'TEST1'
exp_name2 = 'TEST2'
exp_name3 = 'TEST3'
postprocexp_name = 'POSTPROC_TEST'

try:
    # this is my testfile; not part of the repo
    configfile = os.path.split(os.path.realpath(__file__))[0] + '/resources/configure_test.yaml'
except FileNotFoundError:
    configfile = os.path.split(os.path.realpath(__file__))[0] + '/configure_test.yaml'


@pytest.fixture()
def testexp():
    exp = experiment(None, exp_name1)

    exp.create(configfile)

    yield exp

    exp.remove(force=True)

    # Test that the directory has been removed


@pytest.fixture()
def postprocexp():
    # Tests associated with this test require an experiment, that has already been created and run on the cluster
    # Data must be ready to move, postprocessing, archiving, restarting and displaying runtimes.
    # After the test, everything is put back into the initial state.

    exp = experiment(None, postprocexp_name)

    yield exp


# -----------------------------------------------------------------------
# Experiment Tests ------------------------------------------------------
# -----------------------------------------------------------------------

def test_remove():
    exp = experiment(None, exp_name1)

    # removal of an experiment that does not exist should fail
    with pytest.raises(FileNotFoundError):
        exp.remove(force=True)


def test_create(testexp):
    # creating a new experiment should work fine.
    # (Ths experiment is created in the fixture. Here is just the test if all files exist as expected)

    # Test here that the whole experiment directory tree exists and that
    # submit scripts and conf file have been created.
    list_of_expected_dirs = [
        testexp.exp_path,
        testexp.exp_path / 'log',
        testexp.exp_path / 'out',
        testexp.exp_path / 'plot',
        testexp.exp_path / 'wrf'
    ]
    list_of_expected_files = [
        testexp.exp_path / 'submit_real.sh',
        testexp.exp_path / 'submit_wrf.sh',
        testexp.exp_path / 'configure.yaml'
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
        print(missing)
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
        if not os.path.exists(testexp.exp_path / f'wrf/{link}') \
                or not os.path.islink(testexp.exp_path / f'wrf/{link}'):
            missing.append(link)

    if len(missing) > 0:
        print('test_create: Problems encounterd with links')
        for item in missing:
            print(item)
        raise FileNotFoundError


@pytest.mark.long
def test_run_wps(testexp):
    # This test takes a while since wps is run completely. I may want to speed this process up in the future?

    # running wps should work fine, if the testexp has been created properly. This is tested in test_create.
    testexp.run_wps(configfile)

    # Test that wps has been executed? That would be a little specific...
    # -> Need well defined testcase


def test_create2(testexp):
    # creating the same experiment twice should fail
    with pytest.raises(FileExistsError):
        testexp.create(configfile)


def test_copy(testexp):
    # copy an experiment should work fine
    testexp.copy(exp_name2)

    # now, remove exp_name2 as well. Otherwise the test environment is not in a clean state.
    exp2 = experiment(None, exp_name2)
    exp2.remove(force=True)


def test_copy2():
    # copy an experiment that does not exist should fail

    with pytest.raises(FileNotFoundError):
        exp = experiment(None, exp_name3)
        exp.copy(exp_name2)


def test_reuse3(testexp):
    # copy an experiment with a name that alredy exists should fail.
    with pytest.raises(FileExistsError):
        testexp.copy(exp_name1)


def test_rename(testexp):
    # renaming of an experiment should work fine.
    testexp.rename(exp_name2)


def test_rename2(testexp):
    # renaming of an experiment to an existing name should fail
    with pytest.raises(FileExistsError):
        testexp.rename(exp_name1)


def test_runtime(testexp):
    # showing the runtime should work
    testexp.runtime()


# Tests marked postproc require a test that already has been run.
# This test is destructive. The postproc directory will be removed after the test.

@pytest.mark.postproc
def test_restart(postprocexp):
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

    # displaying the runtime should work
    postprocexp.runtime()

    # finally, removing the project should work at the
    # archive position as well.
    postprocexp.remove(force=True)


@pytest.mark.postproc
def test_process_tslist2():
    # processing tslists of an experiment that does not exists should fail
    with pytest.raises(FileNotFoundError):
        exp = experiment(None, exp_name1)
        exp.process_tslist(None, None, ['10'], False)


@pytest.mark.postproc
def test_archive2():
    # archiving a run that does not exist should fail.
    with pytest.raises(FileNotFoundError):
        exp = experiment(None, exp_name1)
        exp.process_tslist(None, None, ['10'], False)


