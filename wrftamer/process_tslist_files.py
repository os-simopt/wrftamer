#!/usr/bin/env python3
import glob
import pandas as pd
import datetime as dt
import xarray as xr
import numpy as np
import os
import itertools
from wrftamer.wrfplotter_classes import assign_cf_attributes_tslist


def uv_to_FFDD(u, v):
    ff = np.sqrt(u ** 2 + v ** 2)
    dd = 180.0 / np.pi * np.arctan2(-u, -v)
    dd = np.mod(dd, 360)

    return ff, dd


def read_files(fiile, var_element, version: str):
    # TS files have surface variables, all other files vertical levels. Thus columns and names need to specified

    if version == "old":
        use_cols = [1, 7, 8, 9, 10, 11, 12, 13, 14] if var_element == "TS" else None
        names = (
            ["Time", "U10", "V10", "PSFC", "GLW", "GSW", "HFX", "LH", "TSK"]
            if var_element == "TS"
            else None
        )
    elif version == "new":
        use_cols = (
            [1, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14] if var_element == "TS" else None
        )
        names = (
            ["Time", "T2", "Q2", "U10", "V10", "PSFC", "GLW", "GSW", "HFX", "LH", "TSK"]
            if var_element == "TS"
            else None
        )
    else:
        print("version unknown")
        raise IndexError

    with open(fiile, "r") as myfile:
        head = myfile.readline().rstrip(
            "\n"
        )  # contains information like station height, station name, startdate
        # this adds the timezone info. DLeuk, 30.08.2021
        startdate = dt.datetime.strptime(
            head.split(" ")[-1] + "-+0000", "%Y-%m-%d_%H:%M:%S-%z"
        )
        data = pd.read_csv(
            myfile, sep=r"\s+", header=None, index_col=0, usecols=use_cols, names=names
        )

        # Make a new index for the dataframe, by taking the starttime into account.

        seconds = np.round(data.index * 3600 + startdate.timestamp()).astype(int)
        # I am converting the index to datetime64, since xarray will do this anyway when writing to a netcdf
        # This way, it is cleaner and I can use the same cf_table.
        seconds = seconds.to_numpy()
        seconds = seconds.astype("datetime64[s]")
        data.index = seconds
        data.index.name = None

        # olc code:
        # data.index = np.round(data.index * 3600 + startdate.timestamp()).astype(int)
        # data.index.name = None

        return data


def read_headinfo(tsfile1):
    with open(tsfile1, "r") as myfile:
        head = myfile.readline().rstrip(
            "\n"
        )  # contains information like station height, station name, startdate
        head_elements = [x for x in head.split(" ") if x]
        hgt = head_elements[-3]

        if len(head_elements) == 18:
            lat = head_elements[7].strip(",")
            lon = head_elements[8].strip(")")
            version = "new"
        elif len(head_elements) == 17:
            lat = head_elements[6].strip(",")
            lon = head_elements[7].strip(")")
            version = "old"
        else:
            print("The Version of the tslist-file is unknown")
            raise IndexError

        return {"hgt": hgt, "lat": lat, "lon": lon}, version


def merge_tslist_files(
    indir, outdir, location, domain, proj_name: str, exp_name: str, institution="-"
):
    """
    This function will take all ts-files and merge all variables belonging one domain into a ncdf.
    This is done for all stations (locations). These files are concated together.

    Args:
        indir: a generator object creating a list of tslist* folders in which the ts-files are located, or a
        list of folders with the same content. Files in the indir have the format: {Location}.{domain}.{variables}
        outdir: The output directory is the folder in which the ncdf files are written out.
        location: Name of the Station or Datapoint, as specified in the textfile tslist
        domain: WRF-domain to process.
        proj_name: name of the project. May be None. For metadata
        exp_name: name of the experiment. For metadata
        institution: for metadata.

    Returns: None.
    Ncdf is written to outdir
    """

    # TODO: the way I select my data and the directories is clumsy at best. I should have indir and outdir be
    #  specified as posixPath objects and to the selection here.
    #  also, this would mean that I do not need two paths anymore.
    #  however, as of now, the function works, so YNGNI

    # Entry for improvement in the future:
    # let outdir be a PosixPath
    # domain = domain if isinstance(domain, str) else '*'
    # location = location if isinstance(location, str) else '*'
    # ts_files = list(outdir.glob(f'tsfiles*/{location}.{domain}.*'))
    # loclist = list(set([item.name.split('.')[0] for item in ts_files]))
    # domlist = list(set([item.name.split('.')[1] for item in ts_files]))
    # varlist = list(set([item.name.split('.')[2] for item in ts_files]))

    cf_table = (
        os.path.split(os.path.realpath(__file__))[0]
        + "/../wrftamer/resources/cf_table_wrfdata.yaml"
    )

    # check if indir is one folder or a list of folders
    indir = indir if isinstance(indir, list) else list(indir)
    if len(indir) == 0:
        return

    # find all files in given folder
    ts_files = [glob.glob(f"{directory}/*") for directory in indir]
    ts_files = list(itertools.chain(*ts_files))  # put these files into a list
    loclist = (
        [f.split("/")[-1].split(".")[0] for f in ts_files]
        if location is None
        else [location]
    )
    loclist = list(set(loclist))
    domainlist = (
        [f.split("/")[-1].split(".")[1] for f in ts_files]
        if domain is None
        else [domain]
    )
    domainlist = list(set(domainlist))

    varlist = ["UU", "VV", "PH", "WW", "TH", "TS", "PR", "QV"]

    # initialize empty dictionary to write data to
    all_xxr = {}
    attrs_dict = {}
    for loc in loclist:
        # read one file for header information
        fi = str(indir[0]) + f"/{loc}.d01.UU"
        attrs_dict[f"{loc}"], version = read_headinfo(fi)

        for dom in domainlist:
            all_xxr[f"{loc}.{dom}"] = {
                "UU": None,
                "VV": None,
                "PH": None,
                "WW": None,
                "TH": None,
                "QV": None,
                "PR": None,
                "U10": None,
                "V10": None,
                "PSFC": None,
                "GLW": None,
                "GSW": None,
                "HFX": None,
                "LH": None,
                "TSK": None,
            }

            # now read all files belonging to the same loc+dom and write into the dictionary
            for var_element in varlist:
                all_files = [
                    f"{directory}/{loc}.{dom}.{var_element}" for directory in indir
                ]
                data_df = pd.concat(
                    [read_files(i, var_element, version) for i in all_files]
                )
                data_df = data_df[~data_df.index.duplicated(keep="first")].sort_index()
                all_xxr[f"{loc}.{dom}"][var_element] = data_df
                if (
                    var_element == "TS"
                ):  # for surface file: variables are written into columns
                    for col in data_df.columns:
                        all_xxr[f"{loc}.{dom}"][col] = data_df[col]

                    all_xxr[f"{loc}.{dom}"].pop(
                        "TS"
                    )  # drop the TS, because it has been splitted

    # writing out ncdf for all combinations of location and domain.

    for dom in domainlist:

        metadata = dict()
        metadata["Conventions"] = "CF-1.8"
        metadata["featureType"] = "timeSeriesProfile"

        metadata["title"] = "time series extracted from model"
        metadata["institution"] = institution
        metadata["source"] = "WRF-Model"
        metadata[
            "references"
        ] = f"Project {proj_name}, Experiment {exp_name}, domain {dom}"
        metadata["comment"] = "raw data"

        all_xxa = []
        for loc in loclist:

            metadata["station_name"] = loc
            metadata["lat"] = float(attrs_dict[f"{loc}"]["lat"])
            metadata["lon"] = float(attrs_dict[f"{loc}"]["lon"])
            metadata["station_elevation"] = float(attrs_dict[f"{loc}"]["hgt"])

            xxa = xr.Dataset(all_xxr[f"{loc}.{dom}"])
            if "UU" in xxa and "VV" in xxa:
                ff, dd = uv_to_FFDD(xxa["UU"], xxa["VV"])
                xxa = xxa.assign({"WSP": ff})
                xxa = xxa.assign({"DIR": dd})

            if "U10" in xxa and "V10" in xxa:
                ff10, dd10 = uv_to_FFDD(xxa["U10"], xxa["V10"])
                xxa = xxa.assign({"WSP10": ff10})
                xxa = xxa.assign({"DIR10": dd10})

            xxa = xxa.rename(
                {
                    "UU": "U",
                    "VV": "V",
                    "PH": "ALT",
                    "PR": "PRES",
                    "WW": "W",
                    "TH": "PT",
                    "dim_0": "time",
                    "dim_1": "model_level",
                }
            )

            xxa = assign_cf_attributes_tslist(xxa, metadata, cf_table)
            all_xxa.append(xxa)

        all_data = xr.concat(all_xxa, dim="station_name")
        all_data = all_data.set_index({"station_name": "station_name"})
        all_data = all_data.set_coords(
            ["lat", "lon", "station_elevation", "station_name"]
        )

        all_data.to_netcdf(f"{outdir}/raw_tslist_{dom}.nc", mode="w")

    return


def average_ts_files(infile: str, timeavg: list):
    """
    Averaging of the raw-files. Closed is right, but labels are left.
    This works since the raw*file usually miss the very first value.
    I.e. raw file from 00:00:03 to 00:15:00. Then the 5 min. mean
    takes from 00:00:03 to 00:04:59 and labels this to 00:00:00.
    Be careful when the first value is available!
    Args:
        infile: raw_tslist_dXX.nc file
        timeavg: list of times in minutes

    Returns:
        netcdf with averaged data.
    """

    if len(timeavg) > 0:
        for time in timeavg:
            xxa = xr.open_dataset(infile)
            xxatme = xxa.resample(time=f"{time}Min", label="left", closed="right").mean(
                keep_attrs=True
            )
            xxatme.attrs = xxa.attrs
            xxatme.attrs["comment"] = f"{time}-minute averaged data"
            xxatme.time.attrs = {"standard_name": "time", "long_name": "time"}
            xxatme.to_netcdf(infile.replace("raw", f"Ave{time}Min"), mode="w")
            xxa.close()

    return
