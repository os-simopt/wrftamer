from WRFtamer.project_management import project, list_projects
import pytest
import os
from pathlib import Path
import pandas as pd

proj_name = 'TEST_PROJECT'
proj_name2 = 'TEST_PROJECT2'
exp_name = 'EXP1'
exp_name2 = 'EXP2'


@pytest.fixture()
def testproject():
    # creation and removal of a project should work

    test = project(proj_name)  # initialize class
    test.create(testing=True)

    yield test

    # check if expected dirs and files are really there
    if os.path.isdir(test.proj_path) and \
            os.path.isdir(test.tamer_path) and \
            os.path.isfile(test.tamer_path / 'List_of_Experiments.xlsx'):
        pass
    else:
        raise FileNotFoundError

    test.remove(force=True)

    # check if dirs and files have been removed sucessfully

    if os.path.isdir(test.proj_path) or os.path.isdir(test.tamer_path):
        raise FileExistsError
    else:
        pass


# -----------------------------------------------------------------------
# PROJECT Tests ---------------------------------------------------------
# -----------------------------------------------------------------------


def test_proj_removal():
    # check removal of project that does not exists fails
    with pytest.raises(FileNotFoundError):
        test = project(proj_name)  # initialize class
        test.remove(force=True)


def test_proj_create_twice(testproject):
    # creation of a project that already exists should fail
    with pytest.raises(FileExistsError):
        testproject.create(testing=True)


def test_proj_rename(testproject):
    # renaming should work
    testproject.rename(proj_name2, testing=True)

    # check that testproject variables have been renamed (tests further down depend on this)
    if testproject.name == proj_name2 and \
            Path(testproject.proj_path).stem == proj_name2 and \
            Path(testproject.tamer_path).stem == proj_name2:
        pass
    else:
        raise ValueError

    # check if the files with the expected new names really exist
    if os.path.isdir(testproject.proj_path):
        pass
    else:
        raise FileNotFoundError

    if os.path.isdir(testproject.tamer_path):
        pass
    else:
        raise FileNotFoundError


def test_proj_rename2():
    # renaming a project that does not exist should fail

    test = project(proj_name)  # no creation here!

    with pytest.raises(FileNotFoundError):
        test.rename(proj_name2, testing=True)


def test_proj_rename3(testproject):
    # renaming a project to a projectname that already exists should fail

    test2 = project(proj_name2)
    test2.create(testing=True)

    with pytest.raises(FileExistsError):
        testproject.rename(proj_name2, testing=True)

    test2.remove(force=True)


def test_list_projects():
    # listing all projects should work
    list_projects()


def test_list_projects2():
    # to make the function proj_list fail, I would have to delete the .WRFtamer directory in the
    # WRFtamer home. Since this directory could contain important data, I'm not gonna do that for testing.
    # I think it is fine, if this case goes untested.
    # Otherwise, may pass db_path as an argument?

    # with pytest.raises(FileNotFoundError):
    #        list_projects()

    pass


def test_proj_du(testproject):
    # showing the size of a project should work
    testproject.disk_use()


def test_proj_du2():
    # showing the size of a project that does not exist should fail

    test = project(proj_name)  # no creation here.

    with pytest.raises(FileNotFoundError):
        test.disk_use()


def test_proj_runtimes(testproject):
    # for now, I expect an NotImplementedError
    with pytest.raises(NotImplementedError):
        testproject.runtimes()


# -----------------------------------------------------------------------
# Experiment Tests ------------------------------------------------------
# -----------------------------------------------------------------------

def test_exp_add(testproject):
    # check if a line with the new experiment does not exist yet.
    filename = testproject.tamer_path / 'List_of_Experiments.xlsx'
    df = pd.read_excel(filename, index_col='index',
                       usecols=['index', 'Name', 'start', 'end', 'disk use',
                                'runtime', 'archived'])
    if exp_name in df.Name.values:
        raise ValueError  # not so sure which Error to raise here...

    # adding an experiment to an existing project should work if it does not exist yet.

    testproject.add_exp(exp_name, 'First Experiment')

    # check if a line with the new experiment exists now.
    df = pd.read_excel(filename, index_col='index',
                       usecols=['index', 'Name', 'start', 'end', 'disk use',
                                'runtime', 'archived'])
    if exp_name not in df.Name.values:
        raise ValueError  # not so sure which Error to raise here...


def test_exp_add2():
    # adding an experiment to a project that does not exist should fail

    test = project(proj_name)  # no creation here.

    with pytest.raises(FileNotFoundError):
        test.add_exp(exp_name, 'First Experiment')


def test_exp_add3(testproject):
    # adding an experiment to a project that already has an experiment with the same name should fail

    testproject.add_exp(exp_name, 'First Experiment')  # adding experiments is already tested above.

    with pytest.raises(FileExistsError):
        testproject.add_exp(exp_name, 'First Experiment')


def test_exp_remove(testproject):
    # removing an experiment from an existing project should work

    testproject.add_exp(exp_name, 'First Experiment')
    testproject.remove_exp(exp_name, force=True)

    # Checkt that experiment has been removed sucessfully
    filename = testproject.tamer_path / 'List_of_Experiments.xlsx'
    df = pd.read_excel(filename, index_col='index',
                       usecols=['index', 'Name', 'start', 'end', 'disk use',
                                'runtime', 'archived'])
    if exp_name in df.Name.values:
        raise ValueError  # not so sure which Error to raise here...


def test_exp_remove2():
    # removing an experiment from a project that does not exist should fail

    test = project(proj_name)  # no creation here.

    with pytest.raises(FileNotFoundError):
        test.remove_exp(exp_name, force=True)


def test_exp_remove3(testproject):
    # removing an experiment from a project that does not contain that experiment should fail

    with pytest.raises(FileNotFoundError):
        testproject.remove_exp(exp_name, force=True)


def test_exp_rename(testproject):
    # renaming an experiment should work, if it has been created in a valid way, should work

    testproject.add_exp(exp_name, 'First Experiment')
    testproject.rename_exp(exp_name, exp_name2)

    # Checkt that experiment has been renamed sucessfully
    filename = testproject.tamer_path / 'List_of_Experiments.xlsx'
    df = pd.read_excel(filename, index_col='index',
                       usecols=['index', 'Name', 'start', 'end', 'disk use',
                                'runtime', 'archived'])
    if exp_name not in df.Name.values and exp_name2 in df.Name.values:
        pass
    else:
        raise ValueError  # not so sure which Error to raise here...


def test_exp_rename2():
    # renaming an experiment of a project that does not exist should fail
    test = project(proj_name)  # no creation here.

    with pytest.raises(FileNotFoundError):
        test.rename_exp(exp_name, exp_name2)


def test_exp_rename3(testproject):
    # renaming an experiment to a name that alredy esists should fail

    testproject.add_exp(exp_name, 'First Experiment')
    testproject.add_exp(exp_name2, 'Second Experiment')

    with pytest.raises(FileExistsError):
        testproject.rename_exp(exp_name, exp_name2)


def test_exp_rename4(testproject):
    # renaming an experiment that is not part of the project should fail
    with pytest.raises(FileNotFoundError):
        testproject.rename_exp(exp_name, exp_name2)


def test_exp_list(testproject):
    # listing all experiments inside a project should work

    testproject.add_exp(exp_name, 'First Experiment')
    testproject.add_exp(exp_name2, 'Second Experiment')
    testproject.list_exp()


def test_exp_list2():
    # listing all experiments of a project that does not exist should fail.
    test = project(proj_name)  # no creation here.

    with pytest.raises(FileNotFoundError):
        test.list_exp()