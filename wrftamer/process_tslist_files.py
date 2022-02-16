#!/usr/bin/env python3
import glob
import pandas as pd
import datetime as dt
import xarray as xr
import numpy as np
import yaml
import os
import itertools


def make_new_index(df, startdate):
    """
    This function makes a new index for the dataframe, by taking the starttime into account.
    Args:
        df: dataframe with time as index: Hours since startdate
        startdate: datetime.object from start of simulation
    Returns:
        Dataframe with index time (seconds since 1970-01-01)
    """

    df.index = np.round(df.index * 3600 + startdate.timestamp()).astype(int)
    df.index.name = None
    return df


def read_files(fiile, var_element, version: str):
    # TS files have surface variables, all other files vertical levels. Thus columns and names need to specified

    if version == 'old':
        use_cols = [1, 7, 8, 9, 10, 11, 12, 13, 14] if var_element == "TS" else None
        names = ["Time", "U10", "V10", "PSFC", "GLW", "GSW", "HFX", "LH", "TSK"] if var_element == "TS" else None
    elif version == 'new':
        use_cols = [1, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14] if var_element == "TS" else None
        names = ["Time", "T2", "Q2", "U10", "V10", "PSFC", "GLW", "GSW", "HFX", "LH",
                 "TSK"] if var_element == "TS" else None
    else:
        print('version unknown')
        raise IndexError

    with open(fiile, "r") as myfile:
        head = myfile.readline().rstrip("\n")  # contains information like station height, station name, startdate
        # startdate = dt.datetime.strptime(head.split(" ")[-1], "%Y-%m-%d_%H:%M:%S")
        startdate = dt.datetime.strptime(head.split(" ")[-1] + '-+0000',
                                         "%Y-%m-%d_%H:%M:%S-%z")  # this adds the timezone info. DLeuk, 30.08.2021
        data = pd.read_csv(myfile, sep=r"\s+", header=None, index_col=0, usecols=use_cols, names=names)

        return make_new_index(data, startdate)


def read_headinfo(tsfile1):
    with open(tsfile1, "r") as myfile:
        head = myfile.readline().rstrip("\n")  # contains information like station height, station name, startdate
        head_elements = [x for x in head.split(" ") if x]
        hgt = head_elements[-3]

        if len(head_elements) == 18:
            lat = head_elements[7].strip(',')
            lon = head_elements[8].strip(")")
            version = 'new'
        elif len(head_elements) == 17:
            lat = head_elements[6].strip(',')
            lon = head_elements[7].strip(")")
            version = 'old'
        else:
            print('The Version of the tslist-file is unknown')
            raise IndexError

        return {"hgt": hgt, "lat": lat, "lon": lon}, version


def assign_attributes(xxarray):
    mypath = os.path.split(os.path.realpath(__file__))[
                 0] + '/../wrftamer/resources/write_ncdf.yaml'
    with open(mypath, "r") as f:
        dict_from_yaml = yaml.safe_load(f)

    for v in xxarray.variables:
        xxarray[v].attrs["standard_name"] = dict_from_yaml[v].get("standard_name")
        xxarray[v].attrs["units"] = dict_from_yaml[v].get("units")
        if dict_from_yaml[v].get("long_name"):
            xxarray[v].attrs["long_name"] = dict_from_yaml[v]["long_name"]
        if dict_from_yaml[v].get("calendar"):
            xxarray[v].attrs["calendar"] = dict_from_yaml[v]["calendar"]

    return xxarray


def merge_tslist_files(indir, outdir, location, domain):
    """
        This function will take all ts-files and merge all variables belonging to one station and one domain into a ncdf.
        Args:
            indir: The input directory is the folder in which the ts-files are located
            or a list of folders, i.e. /parent/folder* . Files in the indir have the format: {Location}.{domain}.{variables}
            outdir: The output directory is the folder in which the ncdf files are written out.
            location: Name of the file, i.e. specified in tslists
            domain: Domain to process.
        Returns: Ncdf written out to outdir
    """

    indir = list(indir) if not isinstance(indir, list) else indir  # check if indir is one folder or a list of folders
    ts_files = [glob.glob(f'{dir}/*') for dir in indir]  # find all files in given folder
    ts_files = list(itertools.chain(*ts_files))  # put these files into a list
    loclist = [f.split("/")[-1].split(".")[0] for f in ts_files] if location is None else [location]
    domainlist = [f.split("/")[-1].split(".")[1] for f in ts_files] if domain is None else [domain]
    varlist = ['UU', 'VV', 'PH', 'WW', 'TH', 'TS', 'PR', 'QV']

    # initialize empty dictionary to write data to
    all_xxr = {}
    attrs_dict = {}
    for loc_element in list(set(loclist)):
        # read one file for header information
        fi = str(indir[0]) + f'/{loc_element}.d01.UU'
        attrs_dict[f'{loc_element}'], version = read_headinfo(fi)

        for dom_element in list(set(domainlist)):
            all_xxr[f'{loc_element}.{dom_element}'] = {
                'UU': None, 'VV': None, "PH": None, "WW": None, "TH": None, "QV": None, "PR": None, "U10": None,
                "V10": None, "PSFC": None, "GLW": None, "GSW": None, "HFX": None, "LH": None, "TSK": None
            }

            # now read all files belonging to the same loc+dom and write into the dictionary
            for var_element in varlist:
                all_files = [f'{dir}/{loc_element}.{dom_element}.{var_element}' for dir in indir]
                data_df = pd.concat([read_files(i, var_element, version) for i in all_files])
                data_df = data_df[~data_df.index.duplicated(keep='first')].sort_index()
                all_xxr[f'{loc_element}.{dom_element}'][var_element] = data_df
                if var_element == "TS":  # for surface file: variables are written into columns
                    for col in data_df.columns:
                        all_xxr[f'{loc_element}.{dom_element}'][col] = data_df[col]
                    all_xxr[f'{loc_element}.{dom_element}'].pop("TS")  # drop the TS, because it has been splitted

    # writing out ncdf for all combinations of location and domain.
    for loc in list(set(loclist)):
        for dom in list(set(domainlist)):
            # remove TS key from dict
            all_xxr[f'{loc}.{dom}'].pop("TS", None)
            # do calculations for wind.
            if all_xxr[f'{loc}.{dom}']['UU'] is not None and all_xxr[f'{loc}.{dom}']['VV'] is not None:
                all_xxr[f'{loc}.{dom}']['WSP'] = np.sqrt(
                    all_xxr[f'{loc}.{dom}'].get('UU', np.nan) ** 2 + all_xxr[f'{loc}.{dom}'].get('VV',
                                                                                                 np.nan) ** 2)
            if all_xxr[f'{loc}.{dom}']['U10'] is not None:
                all_xxr[f'{loc}.{dom}']['WSP10'] = np.sqrt(
                    all_xxr[f'{loc}.{dom}'].get('U10', np.nan) ** 2 + all_xxr[f'{loc}.{dom}'].get('V10',
                                                                                                  np.nan) ** 2)
            xxa = xr.Dataset(all_xxr[f'{loc}.{dom}'])
            xxa = xxa.rename({"UU": "U", "VV": "V", "PH": "Z", "PR": "PRES",
                              "WW": "W", "TH": "PT",
                              "dim_0": "time", "dim_1": "zdim"})
            # xxa['time'] = pd.to_datetime(xxa['time'].values, unit='s')
            # assign attributes to ncdf
            xxa = assign_attributes(xxa)
            xxa.attrs['description'] = 'raw ts-list data'
            xxa.attrs['domain'] = dom
            xxa.attrs['lat'] = attrs_dict[f'{loc}']['lat']
            xxa.attrs['lon'] = attrs_dict[f'{loc}']['lon']
            xxa.attrs['hgt'] = attrs_dict[f'{loc}']['hgt']

            xxa.to_netcdf(f'{outdir}/raw_tslist_{loc}_{dom}.nc', mode='w')
    return


def average_ts_files(infile, timeavg):
    """
    Averaging of the raw-files. Closed is right, but labels are left.
    This works since the raw*file usually miss the very first value.
    I.e. raw file from 00:00:03 to 00:15:00. Then the 5 min. mean
    takes from 00:00:03 to 00:04:59 and labels this to 00:00:00.
    Be careful when the first value is available!
    Args:
        infile: raw* file as ncfd
        timeavg: list of times in minutes

    Returns:
        netcdf with averaged data.
    """

    if len(timeavg) > 0:
        for time in timeavg:
            xxa = xr.load_dataset(infile)
            xxa['time'] = pd.to_datetime(xxa['time'].values, unit='s')
            xxatme = xxa.resample(time=f'{time}Min', label='left', closed='right').mean(keep_attrs=True)
            xxatme.attrs = xxa.attrs
            xxatme.attrs['description'] = f'{time}-minute averaged data'
            xxatme['time'] = xxatme['time'].astype("M8[s]").astype(int) / 1e9  # this deletes all attributes from time
            xxatme = assign_attributes(xxatme)  # this line needs to follow after the one before
            print(infile)
            print(time)
            xxatme.to_netcdf(infile.replace("raw", f"Ave{time}Min"), mode='w')

    return
