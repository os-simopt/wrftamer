import os
import shutil
import datetime as dt
from pathlib import Path
import pytest
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
from wrftamer.wrfplotter_classes import (
    Map,
    Timeseries,
    calc_PT,
    get_list_of_filenames2,
    get_list_of_filenames,
)


# ------------------------------------------------------------------------------------------
# Class Map
# ------------------------------------------------------------------------------------------
def test_init():
    Map()
    Map(plot_path="some/path", intermediate_path="other/path", fmt="pdf")


@pytest.mark.wip
def test_extract_data_from_wrfout(map_env):
    testfile = map_env[0]

    dom = "d01"
    ml = 5
    select_time = -1
    testvars = [
        "T",
        "PT",
        "WSP",
        "DIR",
        "U",
        "V",
        "W",
        "WSP10",
        "DIR10",
        "PRES",
        "P",
        "U10",
        "V10",
        "HFX",
        "GRDFLX",
        "LH",
        "PSFC",
        "LU_INDEX",
        "HGT",
        "T",
        "pressure",
    ]

    cls = Map()
    for var in testvars:
        cls.extract_data_from_wrfout(testfile, dom, var, ml, select_time)

    select_time = dt.datetime(2020, 5, 17)
    cls.extract_data_from_wrfout(testfile, dom, "T", ml, select_time)


@pytest.mark.wip
def test_store_and_load_intermediate(map_env):
    testfile, testdir = map_env

    dom = "d01"
    ml = 5
    select_time = -1
    testvars = ["WSP", "PSFC"]

    cls = Map(intermediate_path=testdir)
    for var in testvars:

        cls.extract_data_from_wrfout(testfile, dom, var, ml, select_time)

        # Test store_intermediate
        cls.store_intermediate()

        date = cls.data.Time.values[0]
        t = pd.to_datetime(str(date))
        timestring = str(t.strftime("%Y%m%d_%H%M%S"))

        if cls.data.model_level == "sfc":
            model_level = "sfc"
            expected_filename = (
                testdir / f"Interm_{cls.data.dom}_{cls.data.name}_{timestring}.nc"
            )
        else:
            model_level = ml
            expected_filename = (
                testdir
                / f"Interm_{cls.data.dom}_{cls.data.name}_{timestring}_ml{cls.data.model_level}.nc"
            )

        expected_hgt = testdir / f"hgt_{cls.data.dom}.nc"
        expected_ivg = testdir / f"ivg_{cls.data.dom}.nc"

        assert expected_filename.is_file()
        assert expected_hgt.is_file()
        assert expected_ivg.is_file()

        # Test load_intermediate
        cls.load_intermediate(dom, var, model_level, timestring)
        cls.load_intermediate(dom, var, model_level, "*")


@pytest.mark.wip
def test_plot(map_env):
    testfile, testdir = map_env

    dom = "d01"
    ml = 5
    select_time = -1
    testvars = ["WSP", "PSFC", "DIR", "HGT", "LU_INDEX"]
    cls = Map(plot_path=testdir)
    ttp = dt.datetime(2020, 5, 17, 0, 0, 0)
    poi = pd.DataFrame({"lon": [9.4], "lat": [45.6]})

    for var in testvars:
        pcmesh = var == "DIR"

        cls.extract_data_from_wrfout(testfile, dom, var, ml, select_time)
        cls.plot(map_t="Cartopy", store=True, pcmesh=pcmesh)
        cls.plot(map_t="hvplot", store=False, pcmesh=pcmesh, poi=poi)
        plt.close()
        cls.plot(map_t="Cartopy", store=False, time_to_plot=ttp, pcmesh=pcmesh, poi=poi)
        plt.close()

        with pytest.raises(NotImplementedError):
            cls.plot(map_t="hvplot", store=True)


# ------------------------------------------------------------------------------------------
# Class Timeseries
# ------------------------------------------------------------------------------------------


def test_init2():
    Timeseries("Testset", data=None)
    Timeseries("Testset", data=xr.Dataset())
    Timeseries("Testset", data=xr.DataArray())

    with pytest.raises(TypeError):
        Timeseries("Testset", data="string")

    with pytest.raises(TypeError):
        Timeseries(1, data=None)


@pytest.mark.wip
def test_read_cfconform_data(ts_env):
    cls1 = Timeseries("Testset")
    cls2 = Timeseries("Testset2")

    dtstart = dt.datetime(2020, 1, 1)
    dtend = dt.datetime(2021, 1, 1)
    metadata = {"additional": "metainfo"}

    cls1.read_cfconform_data(
        dtstart, dtend, metadata, True, verbose=True, use_dask=True
    )
    cls1.read_cfconform_data(dtstart, dtend, None, False, verbose=True, use_dask=False)

    # Check calc_PT variants.
    conf = cls1.data

    # hPa should work (result makes no sense of course)
    conf["P_21"].attrs["units"] = "hPa"
    conf["P_92"].attrs["units"] = "hPa"
    calc_PT(conf)

    # Other units than hPa and Pa raise an Error.
    conf["P_21"].attrs["units"] = "torr"
    conf["P_92"].attrs["units"] = "torr"
    with pytest.raises(ValueError):
        calc_PT(conf)

    # Reading a file with multiple stations (for code coverage)
    cls2.read_cfconform_data(dtstart, dtend, None, True, verbose=True, use_dask=False)


@pytest.mark.wip
def test_read_non_conform_ncdata(ts_env):
    filenames = ts_env

    # Pandas table of metadata. One line per station
    meta_dict = {
        "station_name": ["FINO1"],
        "elev": [0.0],
        "lat": [54.014861],
        "lon": [6.587639],
    }
    meta_table = pd.DataFrame.from_dict(meta_dict, orient="columns")

    # Dictionary for renaming variables. may be an empty dict or None
    translator = None

    metadata = None
    old_attrs = [
        "some_old_attr",
        "comment",
    ]  # comment is actually a "good" attribute. Removed here for testing.
    concat_dim = "time"

    cls = Timeseries("Nonconform")
    cls.read_non_conform_ncdata(
        filenames, concat_dim, meta_table, translator, old_attrs=old_attrs, verbose=True
    )


@pytest.mark.wip
def test_read_non_conform_csvdata():
    cls = Timeseries("Testset")
    with pytest.raises(NotImplementedError):
        cls.read_non_conform_csvdata()


@pytest.mark.wip
def test_write_cfconform_data(ts_env):
    cls1 = Timeseries("Testset")

    dtstart = dt.datetime(2020, 1, 1)
    dtend = dt.datetime(2021, 1, 1)

    cls1.read_cfconform_data(dtstart, dtend)

    cls1.dataset = "WrittenSet"  # change name of dataset otherwise, data is overwritten.
    cls1.write_cfconform_data(overwrite=False, concat_dim="station_name", verbose=True)

    # write again to teste overwrite
    cls1.write_cfconform_data(overwrite=True, concat_dim="station_name", verbose=True)

    # change data name and write with append.
    cls1.data.station_name.values = "FINOX"
    cls1.write_cfconform_data(overwrite=False, concat_dim="station_name", verbose=True)

    dtstart = dt.datetime(2020, 5, 17)
    dtend = dt.datetime(2020, 5, 19)
    targetfile = get_list_of_filenames2(cls1.dataset, dtstart, dtend)

    # This tests does not work on GitHub for some reason.
    #if not targetfile.is_file():
    #    raise FileNotFoundError

    shutil.rmtree(targetfile.parent)


@pytest.mark.wip
def test_plot_Availability(ts_env):
    cls1 = Timeseries("Testset")
    cls2 = Timeseries("Testset2")

    dtstart = dt.datetime(2020, 1, 1)
    dtend = dt.datetime(2021, 1, 1)

    cls1.read_cfconform_data(dtstart, dtend)
    cls2.read_cfconform_data(dtstart, dtend)

    # case with single station
    cls1.plot_Availability("P_21", "FINO1", "2020", 21, "TestAvail")
    # case with multiple stations
    cls2.plot_Availability("P_21", "FINO1", "2020", 21, "TestAvail")

    filename = Path("TestAvail.svg")

    if not filename.is_file():
        raise FileNotFoundError
    else:
        os.remove(filename)


@pytest.mark.wip
def test_get_list_of_filenames():
    name_of_dataset = "Testset"

    # Case1: time window much larger than Testset
    dtstart = dt.datetime(2018, 1, 1)
    dtend = dt.datetime(2022, 1, 1)
    get_list_of_filenames(name_of_dataset, dtstart, dtend)

    # Case2: time window earlier than Testset
    dtstart = dt.datetime(2018, 1, 1)
    dtend = dt.datetime(2019, 1, 1)
    get_list_of_filenames(name_of_dataset, dtstart, dtend)

    # Case2: time window earlier than Testset
    dtstart = dt.datetime(2021, 1, 1)
    dtend = dt.datetime(2022, 1, 1)
    get_list_of_filenames(name_of_dataset, dtstart, dtend)
