#!/usr/bin/env python3

import glob
import os
import sys
from itertools import product
from pathlib import Path, PosixPath

doc = """
A simple replacement for link_grib.sh. Links all grib files in the driving_data
 directory to the exp_path/wrf/ directory
"""


def link_grib(driving_data: PosixPath, exp_path: PosixPath, SUFFIX_LEN=3):

    """

    Args:
        driving_data: path to the driving data, as stated in the config file
        exp_path: path to the exeriment directory
        SUFFIX_LEN: the length of the GRIBFILE Suffix (AAA-ZZZ)

        For a maximum of 26*3 = 78 files, the standard lenght of 3 is sufficient.
        If you want to use more files, set suffix_len to 4 or 5 and modify the
        relevant file in WPS-ungrib accordingly.

        Please refer to the documentation for details.

    Returns: None

    """

    TARGET_TPL = "GRIBFILE."
    inpath = driving_data

    char_list = [f"{65 + i:c}" for i in range(26)]

    files = sorted(inpath.rglob("*.grib?"))

    if len(files) >= 26 ** SUFFIX_LEN:
        print(f"Suffix of len {SUFFIX_LEN} is too short for {len(files)} files!")
        sys.exit(1)

    # remove GRIBFILES if they exist.
    filelist = glob.glob(f"{exp_path}/wrf/{TARGET_TPL}*")
    for filepath in filelist:
        os.remove(filepath)

    for fname, suffix in zip(files, product(char_list, repeat=SUFFIX_LEN)):
        Path(f"{exp_path}/wrf/" + TARGET_TPL + "".join(suffix)).symlink_to(fname)
