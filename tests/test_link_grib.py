import pytest
from wrftamer.link_grib import link_grib


# works

def test_link_grib1(link_environment):
    driving_data, exp_path = link_environment

    link_grib(driving_data, exp_path, SUFFIX_LEN=3)

    if len(list((exp_path / "wrf").glob("GRIBFILE*"))) != 10:
        raise ValueError
    for item in (exp_path / "wrf").glob("GRIBFILE*"):
        if not item.is_symlink():
            raise TypeError
        else:
            item.unlink()


def test_link_grib2(link_environment):
    driving_data, exp_path = link_environment

    with pytest.raises(SystemExit):
        link_grib(driving_data, exp_path, SUFFIX_LEN=0)
