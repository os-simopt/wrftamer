import pytest
from wrftamer.process_tslist_files import merge_tslist_files, average_ts_files


# TODO: I should add tests for other variant of tsfiles...
#  Also, test the Failure if the format of the tsfiles is wrong...


def test_tslist_processing(tslist_environment):
    proj, exp_name = tslist_environment
    proj_name = proj.name
    workdir = proj.get_workdir(exp_name)

    indir = workdir / "out"
    outdir = workdir / "out"

    indir2 = [str(item) for item in list(indir.glob("tsfiles*"))]

    rawfile = outdir / "raw_tslist_d01.nc"
    avefile1 = outdir / "Ave10Min_tslist_d01.nc"
    avefile2 = outdir / "Ave5Min_tslist_d01.nc"

    merge_tslist_files(
        indir2,
        outdir,
        location=None,
        domain=None,
        proj_name=proj_name,
        exp_name=exp_name,
    )
    if not rawfile.is_file():
        raise FileNotFoundError

    average_ts_files(str(rawfile), [5, 10])

    if not avefile1.is_file() or not avefile2.is_file():
        raise FileNotFoundError

    rawfile.unlink()
    avefile1.unlink()
    avefile2.unlink()
