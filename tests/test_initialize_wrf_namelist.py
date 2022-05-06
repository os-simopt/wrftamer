import os
import shutil
from pathlib import Path
import yaml
import pytest
from wrftamer.initialize_wrf_namelist import initialize_wrf_namelist

test_res_path = Path(os.path.split(os.path.realpath(__file__))[0] + "/resources/")
exp_path = test_res_path / "test_run"

templatefile = Path(
    os.path.split(os.path.realpath(__file__))[0]
    + "/../wrftamer/resources/namelist.template"
)

namelistfile = exp_path / "wrf/namelist.test"
configure1 = test_res_path / "configure_test.yaml"
configure2 = test_res_path / "configure_test2.yaml"

with open(configure1, "r") as fid:
    conf1 = yaml.safe_load(fid)

with open(configure2, "r") as fid:
    conf2 = yaml.safe_load(fid)

namelist_vars1 = conf1["namelist_vars"]
namelist_vars2 = conf2["namelist_vars"]


@pytest.fixture
def environment():
    os.makedirs(exp_path / "wrf")
    os.makedirs(exp_path / "out")

    yield

    shutil.rmtree(exp_path)


def test_initialize_wrf_namelist1(environment):
    initialize_wrf_namelist(namelist_vars1, namelistfile, templatefile)
    namelistfile.unlink()


def test_initialize_wrf_namelist2(environment):
    initialize_wrf_namelist(namelist_vars2, namelistfile, templatefile)
    namelistfile.unlink()


def test_initialize_wrf_namelist3(environment):
    initialize_wrf_namelist(namelist_vars1, namelistfile, None)
    namelistfile.unlink()
