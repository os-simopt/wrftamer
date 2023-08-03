import pytest
import os
from pathlib import Path
from wrftamer.wrftamer_functions import (
    writeLogFile,
    make_executable_dir,
    make_essential_data_dir,
    make_non_essential_data_dir,
    make_submitfiles,
    make_call_wd_file_from_template,
)
from wrftamer import res_path, test_res_path


# rename_dirs: test with ignore_submit = False
# copy_dirs: create fake files to link.

# works

def test_writeLogFile(functions_environment):
    test_exp_path = functions_environment

    message = "test"
    program = "test.exe"
    log_levels = [0, 1, 2]
    logfile = test_exp_path / "log/test.log"

    for log_level in log_levels:
        writeLogFile(logfile, program, log_level, message)

    with pytest.raises(ValueError):
        writeLogFile(logfile, program, -1, message)
    with pytest.raises(ValueError):
        writeLogFile(logfile, program, 3, message)


def test_make_executable_dir(functions_environment):
    test_env_path = functions_environment.parent

    exe_dir = test_env_path / "executables"
    wrf_and_wsp_parent_dir = test_env_path / "WRF_WPS_PARENT"

    make_executable_dir(exe_dir, wrf_and_wsp_parent_dir)


def test_make_essential_data_dir(functions_environment):
    test_env_path = functions_environment.parent

    wrf_and_wsp_parent_dir = test_env_path / "WRF_WPS_PARENT"
    essentials_dir = test_env_path / "essentials_dir"
    vtable = "Vtable.test"

    make_essential_data_dir(wrf_and_wsp_parent_dir, essentials_dir, vtable)


def test_make_non_essential_data_dir(functions_environment):
    test_env_path = functions_environment.parent
    non_essentials_dir = test_env_path / "non_essentials_dir"

    make_non_essential_data_dir(non_essentials_dir)


def test_make_submitfiles(base_test_env):
    exp_path = base_test_env
    configfile = test_res_path / "configure_test.yaml"
    templatefile = res_path / "submit.template"

    make_submitfiles(exp_path, configfile, templatefile=None)
    make_submitfiles(exp_path, configfile, templatefile=templatefile)


def test_make_call_wd_file_from_template(base_test_env):
    miniconda_path = "dummy_path"
    condaenv_name = "dummy_name"
    templatefile = res_path / "call_watchdog.template"

    expected_file = base_test_env / "call_watchdog.bash"

    make_call_wd_file_from_template(miniconda_path, condaenv_name, templatefile=None)
    make_call_wd_file_from_template(miniconda_path, condaenv_name, templatefile)
    if not expected_file.is_file():
        raise FileNotFoundError
    else:
        expected_file.unlink()
