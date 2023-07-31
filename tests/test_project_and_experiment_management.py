import pytest
import os
from pathlib import Path
import shutil
import pandas as pd
from wrftamer.main import project, list_projects, list_unassociated_exp, reassociate


# works

# -----------------------------------------------------------------------
# Trivial tests for nonexistent project
# -----------------------------------------------------------------------


def test_nonexisting_project(base_test_env):
    test = project("some_random_name")  # initialize class, no creation here

    # removal of project that does not exists should fail
    with pytest.raises(FileNotFoundError):
        test.remove(force=True)

    # renaming a project that does not exist should fail
    with pytest.raises(FileNotFoundError):
        test.rename("some_random_name2")

    # showing the size of a project that does not exist should fail
    with pytest.raises(FileNotFoundError):
        test.disk_use()

    # removing an experiment from a project that does not exist should fail
    with pytest.raises(FileNotFoundError):
        test.exp_remove("Some_Random_Exp_Name", force=True)

    # renaming an experiment of a project that does not exist should fail
    with pytest.raises(FileNotFoundError):
        test.exp_rename("Some_Random_Exp_Name", "Some_Random_Exp_Name2")

    # listing all experiments of a project that does not exist should fail.
    with pytest.raises(FileNotFoundError):
        test.list_exp()

    # adding an experiment to a project that does not exist should work (since the project is created on the fly!)
    configfile = os.path.split(os.path.realpath(__file__))[0] + "/resources/configure_test.yaml"
    test.exp_create("Some_Random_Exp_Name", "Some_Random_Comment", configfile)
    test.remove(force=True, verbose=False)


# -----------------------------------------------------------------------
# Function Tests
# -----------------------------------------------------------------------


def test_list_projects(testprojects):
    # listing all projects should work (even if no projects exist)
    list_projects(verbose=True)


def test_list_unassociated_exp(testprojects):
    # listing unassociated exps (if none exist) will just return an empty list
    res = list_unassociated_exp(verbose=True)
    assert len(res) == 0


# -----------------------------------------------------------------------
# Tests for real project
# -----------------------------------------------------------------------


def test_project(testprojects):
    testproject1 = testprojects[0]

    proj_name2 = "NEW_NAME"

    # creation of a project that already exists should fail
    with pytest.raises(FileExistsError):
        testproject1.create()

    # ------------------------------------------------------
    # renaming should work
    testproject1.rename(proj_name2)

    # check that testproject variables have been renamed (tests further down depend on this)
    if (
            testproject1.name == proj_name2
            and Path(testproject1.proj_path).stem == proj_name2
            and Path(testproject1.tamer_path).stem == proj_name2
    ):
        pass
    else:
        raise ValueError

    # check if the files with the expected new names really exist
    if os.path.isdir(testproject1.proj_path):
        pass
    else:
        raise FileNotFoundError

    if os.path.isdir(testproject1.tamer_path):
        pass
    else:
        raise FileNotFoundError

    # ------------------------------------------------------
    # showing the size of a project should work
    testproject1.disk_use()

    # ------------------------------------------------------
    # for now, I expect a NotImplementedError
    with pytest.raises(NotImplementedError):
        testproject1.runtimes()

    # ------------------------------------------------------
    # listing all experiments inside a project should work
    testproject1.list_exp()

    # Rewriting xls sheet should work (but won't do anything, since no experiments have been created)
    testproject1.rewrite_xls()

    # Case damaged project. proj_path missing, but tamer_path intact
    shutil.rmtree(testproject1.proj_path)
    with pytest.raises(FileNotFoundError):
        testproject1.rename(proj_name2)

    # Removal should work for broken project as well.
    testproject1.remove(force=True)
    # removing a project that does not exist should fail
    with pytest.raises(FileNotFoundError):
        testproject1.remove(force=True)

    # recreating project, otherwise, fixture fails.
    testproject1.create(proj_name2)


# -----------------------------------------------------------------------
# Project-Project Interaction
# -----------------------------------------------------------------------


def test_proj_rename3(testprojects):
    testproject1, testproject2 = testprojects
    with pytest.raises(FileExistsError):
        testproject1.rename(testproject2.name)


def test_reassociate(testprojects):
    testproject1, testproject2 = testprojects

    exp_name1 = "TEST1"
    exp_name2 = "TEST2"
    exp_name3 = "TEST3"
    configfile = (
            os.path.split(os.path.realpath(__file__))[0] + "/resources/configure_test.yaml"
    )

    # ------------------------------------------------------
    # adding an exp to a project should work fine.
    testproject1.exp_create(exp_name1, "First Experiment", configfile)
    testproject1.exp_create(exp_name3, "Third Experiment", configfile)

    testproject2.exp_create(exp_name1, "First Experiment", configfile)
    testproject2.exp_create(exp_name2, "Second Experiment", configfile)

    with pytest.raises(FileExistsError):
        reassociate(
            testproject1, testproject2, exp_name1
        )  # exp_name1 is already part of testproject2

    reassociate(testproject1, testproject2, exp_name3)

    list1 = testproject1.list_exp(verbose=False)
    list2 = testproject2.list_exp(verbose=False)
    assert len(list1) == 1
    assert len(list2) == 3

    if exp_name3 not in list2 or exp_name2 not in list2:
        raise ValueError


# =======================================================================
# Experiment Tests (with and without project)
# =======================================================================

# -----------------------------------------------------------------------
# Tests for experiment with and without project
# -----------------------------------------------------------------------
@pytest.mark.config_req
def test_experiment_creation_thoroughly(testprojects):
    """
    Also checks if all files linked and created are really there.
    """

    testproject1 = testprojects[0]

    proj_name1 = testproject1.name
    exp_name1 = "TEST1"

    configfile = os.path.split(os.path.realpath(__file__))[0] + "/resources/my_configure_test.yaml"

    proj = project(proj_name1)
    proj.exp_create(exp_name1, "some comment", configfile)

    # Test here that the whole experiment directory tree exists and that

    exp_path = proj.proj_path / exp_name1

    list_of_expected_dirs = [
        exp_path,
        exp_path / "log",
        exp_path / "out",
        exp_path / "plot",
        exp_path / "wrf",
    ]

    if proj.make_submit:
        list_of_expected_files = [
            exp_path / "submit_real.sh",
            exp_path / "submit_wrf.sh",
            exp_path / "configure.yaml",
        ]
    else:
        list_of_expected_files = [exp_path / "configure.yaml"]

    missing = []
    for tmp in list_of_expected_dirs:
        if not os.path.isdir(tmp):
            missing.append(tmp)
    for tmp in list_of_expected_files:
        if not os.path.isfile(tmp):
            missing.append(tmp)

    if len(missing) > 0:
        print("test_create: Missing files or directories!")
        for item in missing:
            print(item)
        raise FileNotFoundError

    # Tests that all links are established
    expected_links = [
        "g1print.exe",
        "g2print.exe",
        "geogrid.exe",
        "metgrid.exe",
        "ndown.exe",
        "real.exe",
        "tc.exe",
        "ungrib.exe",
        "wrf.exe",
        "GENPARM.TBL",
        "GEOGRID.TBL",
        "HLC.TBL",
        "LANDUSE.TBL",
        "METGRID.TBL",
        "MPTABLE.TBL",
        "SOILPARM.TBL",
        "URBPARM.TBL",
        "VEGPARM.TBL",
        "ozone.formatted",
        "ozone_lat.formatted",
        "ozone_plev.formatted",
        "RRTM_DATA",
        "RRTMG_LW_DATA",
        "RRTMG_SW_DATA",
        "aux_file.txt",
        "link_grib.csh",
        "namelist.wps",
        "tslist",
        "Vtable",
    ]

    missing = []
    for link in expected_links:
        if not os.path.exists(exp_path / f"wrf/{link}") or not os.path.islink(
                exp_path / f"wrf/{link}"
        ):
            missing.append(link)

    if len(missing) > 0:
        print("test_create: Problems encounterd with links")
        for item in missing:
            print(item)
        raise FileNotFoundError


def experiment_checks(proj_name1, exp_name1):
    exp_name2 = "TEST2"
    exp_name3 = "TEST3"
    configfile = os.path.split(os.path.realpath(__file__))[0] + '/resources/configure_test.yaml'

    proj = project(proj_name1)
    proj.exp_create(exp_name1, "some comment", configfile)

    # ------------------------------------------------------
    # creating the same experiment twice should fail
    with pytest.raises(FileExistsError):
        proj.exp_create(exp_name1, "some comment", configfile)

    # ------------------------------------------------------
    # reusing an experiment, that never has been created should fail
    with pytest.raises(FileNotFoundError):
        proj.exp_copy(
            "some random name", exp_name2, "some comment"
        )  # exp_name2 exists now

    # reusing an experiment should work fine
    workdir = proj.get_workdir(exp_name1)  # create a little testfile for code coverage
    with open(workdir / "wrf/OBS_DOMAIN101", "w") as f:
        f.write("data")

    proj.exp_copy(exp_name1, exp_name2, "some comment")  # exp_name2 exists now

    # ------------------------------------------------------
    # reusing an experiment with a name that alredy exists should fail.
    with pytest.raises(FileExistsError):
        proj.exp_copy(exp_name1, exp_name2, "some comment")  # exp_name2 exists now

    # renaming of an experiment should work fine.
    proj.exp_rename(exp_name1, exp_name3)

    # renaming of an experiment to an existing name should fail
    with pytest.raises(FileExistsError):
        proj.exp_rename(exp_name3, exp_name2)

    # Displaying runtimes should work.
    proj.exp_runtime(exp_name1)

    # Displaying disk use should work
    proj.exp_du(exp_name1, verbose=True)

    # Calculating start_end should work
    proj.exp_start_end(exp_name1, verbose=True)

    # listing of available locations should work
    proj.exp_list_tslocs(exp_name1, verbose=True)

    proj.exp_get_maxdom_from_config(exp_name1)

    # Updating the database should work
    proj.update_xlsx()

    # Should check the other branch.
    proj.rewrite_xls()

    # Removing an experiment should work
    proj.exp_remove(exp_name1, force=True)

    proj._determine_status(exp_name2)


def test_experiment_without_project(unassociated_exps):
    proj_name1 = None
    exp_name1 = "TEST1"

    # This should find no unassociate experiments.
    res = list_unassociated_exp(verbose=True)
    assert len(res) == 0

    experiment_checks(proj_name1, exp_name1)


def test_experiment_with_project(testprojects):
    testproject1 = testprojects[0]

    proj_name1 = testproject1.name
    exp_name1 = "TEST1"

    # ------------------------------------------------------
    # listing projects should work
    res = list_projects(verbose=True)
    assert len(res) == 2

    experiment_checks(proj_name1, exp_name1)


def test_experiment_with_project2(testprojects):
    # with make_submit=False
    testproject1 = testprojects[0]

    testproject1.make_submit = False
    proj_name1 = testproject1.name
    exp_name1 = "TEST1"

    # ------------------------------------------------------
    # listing projects should work
    res = list_projects(verbose=True)
    assert len(res) == 2

    experiment_checks(proj_name1, exp_name1)


def test_postprocessing(test_env2):
    test_proj, exp_name1 = test_env2

    # Tests associated with this test require an experiment, that has been created and run on the cluster
    # Data must be ready for moval, postprocessing, archiving, restarting and displaying runtimes.

    # moving data from an experiment should work
    test_proj.exp_move(exp_name1, verbose=True)

    # moving data from an experiment a second time will just trigger a message.
    test_proj.exp_move(exp_name1, verbose=True)

    # A fake restart file does the job for testing purposes.
    test_proj.exp_restart(exp_name1, "wrfrst_d01_2020-05-17_03:00:00")

    with pytest.raises(NameError):
        test_proj.exp_restart(exp_name1, "wrfrst_d01_2020-05-17_03_00_00")

    # postprocessing of tslist data should work
    test_proj.exp_process_tslist(
        exp_name1, None, None, ["10"], True
    )  # averaging does not work?

    # additional test, since now, I have a namelist.
    test_proj.exp_start_end(exp_name1, verbose=True)

    # providing info should work
    test_proj.exp_provide_info()
    test_proj.exp_provide_info(exp_name1)
    test_proj.exp_provide_all_info()
    test_proj.exp_provide_all_info(exp_name1)
    test_proj.exp_runtime(exp_name1, verbose=True)

    test_proj.exp_get_maxdom_from_config(exp_name1)

    test_proj.cleanup_db(verbose=True)

    # moving data to the archive should work
    test_proj.exp_archive(exp_name1, keep_log=False, verbose=True)

    # This will just return. Error catched internally.
    test_proj.exp_copy(
        exp_name1, "Some_Random_Name", "some random comment", verbose=True
    )

    test_proj.exp_rename(exp_name1, "Some_New_Name", verbose=True)

    test_proj.exp_runtime("Some_New_Name")

    # removing an archived experiment
    test_proj.exp_remove("Some_New_Name", force=True)

    # renaming a project which has some archived experiments should work
    test_proj.rename("some_random_new_name", verbose=True)


@pytest.mark.wip
def test_postprocessing2(test_env2):
    test_proj, exp_name1 = test_env2

    # configure.yaml does not contain ppp info, so this won't do anything.
    test_proj.exp_run_postprocessing_protocol("TEST1", verbose=True)

    cfg = dict()
    cfg["pp_protocol"] = dict()
    cfg["pp_protocol"]["move"] = 1
    cfg["pp_protocol"]["tslist_processing"] = 1
    cfg["pp_protocol"]["create_maps"] = 1
    test_proj.exp_run_postprocessing_protocol(
        "TEST1", verbose=True, cfg=cfg
    )  # use defaults


@pytest.mark.wip
def test_postprocessing3(test_env2):
    test_proj, exp_name1 = test_env2

    cfg = dict()
    cfg["pp_protocol"] = dict()
    cfg["pp_protocol"]["move"] = 1
    cfg["pp_protocol"]["tslist_processing"] = dict()
    cfg["pp_protocol"]["tslist_processing"]["location"] = "FINO"
    cfg["pp_protocol"]["tslist_processing"]["domain"] = "d01"
    cfg["pp_protocol"]["tslist_processing"]["timeavg"] = [10]
    cfg["pp_protocol"]["create_maps"] = dict()
    cfg["pp_protocol"]["create_maps"]["list_of_domains"] = ["d01"]
    cfg["pp_protocol"]["create_maps"]["list_of_model_levels"] = [5]
    cfg["pp_protocol"]["create_maps"]["list_of_variables"] = ["WSP"]
    cfg["pp_protocol"]["create_maps"]["store"] = ["False"]
    test_proj.exp_run_postprocessing_protocol("TEST1", verbose=True, cfg=cfg)


def test_remove_with_correct_input1(base_test_env, monkeypatch):
    # monkeypatch the "input" function, so that it returns "Yes".
    # This simulates the user entering "Yes" in the terminal:
    monkeypatch.setattr("builtins.input", lambda _: "Yes")

    testproject = project("WRFTAMER_TEST1")
    exp_name1 = "TEST1"

    # ------------------------------------------------------
    # adding an exp to a project should work fine.
    configfile = (
            os.path.split(os.path.realpath(__file__))[0] + "/resources/configure_test.yaml"
    )
    testproject.exp_create(exp_name1, "First Experiment", configfile, verbose=True)

    testproject.exp_remove(exp_name1)  # Expects Input
    testproject.remove()  # Expects Input


def test_remove_with_correct_input2(base_test_env, monkeypatch):
    # monkeypatch the "input" function, so that it returns "yes".
    # This simulates the user entering "Yes" in the terminal:
    monkeypatch.setattr("builtins.input", lambda _: "yes")

    testproject = project("WRFTAMER_TEST1")
    exp_name1 = "TEST1"

    # ------------------------------------------------------
    # adding an exp to a project should work fine.
    configfile = (
            os.path.split(os.path.realpath(__file__))[0] + "/resources/configure_test.yaml"
    )
    testproject.exp_create(exp_name1, "First Experiment", configfile, verbose=True)

    # These will just return (Yes must be capitalized)
    testproject.exp_remove(exp_name1)  # Expects Input
    testproject.remove()  # Expects Input

    testproject.remove(force=True)


def test_update_db(test_env2):
    test_proj, exp_name1 = test_env2

    test_proj.cleanup_db(verbose=True)  # this does nothing. File in goood state.

    # This environment contains a single experiment.
    # Simulate manual removal of a run directory by the user (but not the db entry).
    workdir = test_proj.get_workdir(exp_name1)
    shutil.rmtree(workdir)

    test_proj.cleanup_db(verbose=True)


def test_broken_db(test_env2):
    test_proj, exp_name1 = test_env2

    # This environment contains a single experiment.
    # Simulate manual removal of a run directory by the user (but not the db entry).
    workdir = test_proj.get_workdir(exp_name1)
    shutil.rmtree(workdir)

    # Creating a new exp should raise an error.
    with pytest.raises(FileExistsError):
        configfile = (
                os.path.split(os.path.realpath(__file__))[0]
                + "/resources/configure_test.yaml"
        )
        test_proj.exp_create(exp_name1, "First Experiment", configfile, verbose=True)

    # Create an experiment that can be copied.
    configfile = (
            os.path.split(os.path.realpath(__file__))[0] + "/resources/configure_test.yaml"
    )
    test_proj.exp_create("Another_Exp", "Second Experiment", configfile, verbose=True)

    # Copying this exp to exp_name1 should fail
    with pytest.raises(FileExistsError):
        test_proj.exp_copy("Another_Exp", exp_name1, "New Experiment", verbose=True)

    # Renaming should have the same issues.
    with pytest.raises(FileExistsError):
        test_proj.exp_rename("Another_Exp", exp_name1, verbose=True)

    with pytest.raises(FileNotFoundError):
        test_proj.exp_rename(exp_name1, "OtherName", verbose=True)

    # And archiving...
    with pytest.raises(FileNotFoundError):
        test_proj.exp_archive(exp_name1)

    test_proj.cleanup_db(verbose=True)

    # Simulate a manualy manipulated db and check failures.
    df = pd.read_excel(
        test_proj.filename,
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
    new_line = ["Manual_Test", 0, "manual edit", 0, 0, 0, 0, "created"]
    df.loc[len(df)] = new_line
    df.to_excel(test_proj.filename)

    with pytest.raises(FileExistsError):
        test_proj.exp_create(
            "Manual_Test", "Second Experiment", configfile, verbose=True
        )

    with pytest.raises(FileNotFoundError):
        test_proj.exp_rename("Manual_Test", "OtherName2")

# @pytest.mark.long
# def test_run_wps(testproject_exp):

# I need to think of an environment for this test...
# After all, this needs the whole setup to work. This may be an important test, but the environment
# is non-trivial...

# This test takes a while since wps is run completely. I may want to speed this process up in the future?

# running wps should work fine, if the testexp has been created properly. This is tested in test_create.
# testproject_exp.run_wps(configfile)

# Test that wps has been executed? That would be a little specific...
# -> Need well defined testcase


# TODO: für _determine_status wäre es gut, fake daten für alle Fälle zu haben.
#
# TODO: systematischer test von ppp für alle möglichen configure files wäre gut.
