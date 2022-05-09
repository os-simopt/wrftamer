import os
import shutil
import datetime as dt
import yaml
import pandas as pd
from pathlib import Path, PosixPath
import re
import subprocess
from wrftamer.initialize_wrf_namelist import initialize_wrf_namelist
from wrftamer.link_grib import link_grib
from wrftamer.wrftamer_paths import wrftamer_paths

"""
Here, I translated the old shell scripts to python scripts.

These functions are the "meat" of the wrftamer. These commands create directories, create links, run wps and keep
a logfile.

"""


def writeLogFile(logfile: str, program: str, log_level: int, message: str):
    """
    Appends a string to the log file
    Args:
        logfile: name of the logfile
        program: the program writing the message
        log_level: 0=INFO, 1=WARNING or 2=ERROR
        message: the message to write
    """

    if log_level < 0 or log_level > 2:
        raise ValueError

    levels = ["INFO", "WARNING", "ERROR"]
    level = levels[log_level]

    datestr = dt.datetime.now().strftime("%Y.%m.%d %H:%M:%S")

    full_message = f"{datestr} {level} {program} {message}\n"

    with open(logfile, "a") as fid:
        fid.write(full_message)


def make_executable_dir(exe_dir: PosixPath, wrf_and_wsp_parent_dir: PosixPath):
    """
    Creates a directory for the copies of the executables of WRF and WPS and copies these files" \
    """

    os.makedirs(exe_dir, exist_ok=True)

    # copy executables
    list1 = list(wrf_and_wsp_parent_dir.glob("WPS/*.exe"))
    list2 = list(wrf_and_wsp_parent_dir.glob("WRF/test/em_real/*.exe"))
    list1.extend(list2)

    for item in list1:
        shutil.copy(str(item), exe_dir)


def make_essential_data_dir(
    wrf_and_wsp_parent_dir: PosixPath, essentials_dir: PosixPath, vtable: str
):
    """
    Creates a directory for the copies of the essential data of WRF and WPS; copies the data.
    """

    os.makedirs(essentials_dir, exist_ok=True)

    # copy essentials
    shutil.copy(f"{wrf_and_wsp_parent_dir}/WPS/geogrid/GEOGRID.TBL", essentials_dir)
    shutil.copy(f"{wrf_and_wsp_parent_dir}/WPS/link_grib.csh", essentials_dir)
    shutil.copy(
        f"{wrf_and_wsp_parent_dir}/WPS/ungrib/Variable_Tables/{vtable}", essentials_dir
    )
    shutil.copy(f"{wrf_and_wsp_parent_dir}/WPS/metgrid/METGRID.TBL", essentials_dir)

    os.rename(f"{essentials_dir}/{vtable}", f"{essentials_dir}/Vtable")

    list1 = list(wrf_and_wsp_parent_dir.glob("WRF/test/em_real/*.TBL"))
    list2 = list(wrf_and_wsp_parent_dir.glob("WRF/test/em_real/ozone*"))
    list3 = list(wrf_and_wsp_parent_dir.glob("WRF/test/em_real/RRTM*"))

    list1.extend(list2)
    list1.extend(list3)

    for item in list1:
        shutil.copy(str(item), essentials_dir)


def make_non_essential_data_dir(non_essentials_dir: str):
    os.makedirs(non_essentials_dir, exist_ok=True)

    # noting to copy for non-essentials (for now)


def create_rundir(
    exp_path: PosixPath, configure_file: str, namelist_template: str, verbose=False
):
    """
    Creating directory structure for an experiment, linking files, copying configure files.

    exp_path: absolute path to the run_path of an experiment
    configure_file: the configure file that contains the paths

    """

    with open(configure_file) as f:
        cfg = yaml.safe_load(f)

    exe_dir = Path(cfg["paths"]["wrf_executables"])
    essentials_dir = Path(cfg["paths"]["wrf_essentials"])
    non_essentials_dir = Path(cfg["paths"]["wrf_nonessentials"])
    namelist_vars = cfg["namelist_vars"]
    driving_data = Path(cfg["paths"]["driving_data"])
    suffix_len = cfg["link_grib"]["suffix_len"]

    if verbose:
        print(f"Building the exp_path directory {exp_path}")
        print("Relevant config_file and directories:")
        print(configure_file)
        print(exe_dir)
        print(essentials_dir)
        print(non_essentials_dir)
        print("=======================================")
        print("")

    # Create directories
    os.makedirs(exp_path / "log", exist_ok=True)
    os.makedirs(exp_path / "out", exist_ok=True)
    os.makedirs(exp_path / "plot", exist_ok=True)
    os.makedirs(exp_path / "wrf", exist_ok=True)

    # create empty logfile
    with open(exp_path / "log/wrftamer.log", "w") as f:
        f.write("")

    # now, link files
    list1 = list(exe_dir.glob("*"))
    list2 = list(essentials_dir.glob("*"))
    list3 = list(non_essentials_dir.glob("*"))

    list1.extend(list2)
    list1.extend(list3)

    for item in list1:
        filename = item.name
        os.symlink(item, exp_path / "wrf" / filename)

    # generate the namelist
    namelist_to_create = f"{exp_path}/wrf/namelist.input"
    initialize_wrf_namelist(namelist_vars, namelist_to_create, namelist_template)

    # link namelist
    namelist_to_link = exp_path / "wrf/namelist.wps"
    os.symlink(namelist_to_create, namelist_to_link)

    # link GRIB files
    link_grib(driving_data, exp_path, suffix_len)

    # copy configure (yaml) file for later reference. It is always called configure_template.yaml
    shutil.copyfile(configure_file, f"{exp_path}/configure.yaml")


def copy_dirs(old_run_path: PosixPath, new_run_path: PosixPath, ignore_submit=False):
    """
    Creating directory structure for an experiment, linking files, copying configure files.

    old_wrf_run: the absolute path to the exp_path directory to copy
    new_wrf_run: the absolute path to the epx_path directory of the new experiment

    """

    # Create directories
    os.makedirs(new_run_path / "log", exist_ok=True)
    os.makedirs(new_run_path / "out", exist_ok=True)
    os.makedirs(new_run_path / "plot", exist_ok=True)
    os.makedirs(new_run_path / "wrf", exist_ok=True)

    # create empty logfile
    with open(new_run_path / "log/wrftamer.log", "w") as f:
        f.write("")

    # copy configure file, get paths
    configure_file = f"{new_run_path}/configure.yaml"
    shutil.copyfile(f"{old_run_path}/configure.yaml", configure_file)

    with open(configure_file) as f:
        cfg = yaml.safe_load(f)

    exe_dir = Path(cfg["paths"]["wrf_executables"])
    essentials_dir = Path(cfg["paths"]["wrf_essentials"])
    non_essentials_dir = Path(cfg["paths"]["wrf_nonessentials"])

    # link files
    # now, link files
    list1 = list(exe_dir.glob("*"))
    list2 = list(essentials_dir.glob("*"))
    list3 = list(non_essentials_dir.glob("*"))

    list1.extend(list2)
    list1.extend(list3)

    for item in list1:
        filename = item.name
        os.symlink(item, f"{new_run_path}/wrf/{filename}")

    # create list of files to link:
    list1 = []
    list1.extend(list(old_run_path.glob("wrf/OBS_DOMAIN*")))
    list1.extend(list(old_run_path.glob("wrf/wrfinput_*")))
    list1.extend(list(old_run_path.glob("wrf/wrfbdy*")))
    list1.extend(list(old_run_path.glob("wrf/met_em*")))

    for item in list1:
        filename = item.name
        os.symlink(item, new_run_path / "wrf" / filename)

    # copy namelist.input
    shutil.copyfile(
        f"{old_run_path}/wrf/namelist.input", f"{new_run_path}/wrf/namelist.input"
    )

    # link namelist.wps
    os.symlink(new_run_path / "wrf/namelist.input", new_run_path / "wrf/namelist.wps")

    # copy submit files and change paths as is appropriate
    if not ignore_submit:
        shutil.copyfile(
            f"{old_run_path}/submit_wrf.sh", f"{new_run_path}/submit_wrf.sh"
        )
        shutil.copyfile(
            f"{old_run_path}/submit_real.sh", f"{new_run_path}/submit_real.sh"
        )

        file1 = f"{new_run_path}/submit_wrf.sh"
        file2 = f"{new_run_path}/submit_real.sh"

        old_name = old_run_path.name
        new_name = new_run_path.name

        # danger! if old_name is in old_run_path, the order is important!!
        replace = dict()
        replace[str(old_run_path)] = str(new_run_path)
        replace[old_name] = new_name

        _update_submitfile(file1, replace)
        _update_submitfile(file2, replace)


def rename_dirs(old_run_path: PosixPath, new_run_path: PosixPath, make_submit=False):
    os.rename(old_run_path, new_run_path)
    # re-link the wps-file
    os.remove(new_run_path / "wrf/namelist.wps")  # remove dangling link
    os.symlink(f"{new_run_path}/wrf/namelist.input", f"{new_run_path}/wrf/namelist.wps")

    if make_submit:
        file1 = f"{new_run_path}/submit_wrf.sh"
        file2 = f"{new_run_path}/submit_real.sh"

        old_name = Path(old_run_path).name
        new_name = Path(new_run_path).name

        # danger! if old_name is in old_run_path, the order is important!!
        replace = dict()
        replace[str(old_run_path)] = str(new_run_path)
        replace[old_name] = new_name

        _update_submitfile(file1, replace)
        _update_submitfile(file2, replace)


def _update_submitfile(submitfile: str, replace: dict):
    """
    I am updating the submitfiles instead of re-creating them when copying or renaming an
    experiment. Reason: the user may have made changes of his own.
    """

    # read in the file
    with open(submitfile, "r") as file:
        filedata = file.read()

    for item in replace:
        filedata = filedata.replace(item, replace[item])

    # Write the file out again
    with open(submitfile, "w") as file:
        file.write(filedata)


def make_call_wd_file_from_template(miniconda_path, condaenv_name, templatefile=None):
    wd_vars = dict()
    wd_vars["miniconda_path"] = str(miniconda_path)
    wd_vars["condaenv_name"] = condaenv_name
    wd_vars["HOME"] = os.environ["HOME"]

    home_path, db_path, run_path, archive_path, plot_path = wrftamer_paths()

    if templatefile is None:
        myfile = (
            os.path.split(os.path.realpath(__file__))[0]
            + "/resources/call_watchdog.template"
        )
    else:
        myfile = templatefile

    with open(myfile, "r") as f:
        tpl = f.read()
        filedata = tpl.format(**wd_vars)

    outfile = home_path / "call_watchdog.bash"

    print("writing file:", outfile)

    # Write the file out again
    with open(outfile, "w") as file:
        file.write(filedata)


def _make_submitfile_from_template(submit_vars: dict, templatefile=None):
    # read template and configuration
    if templatefile is None:
        myfile = (
            os.path.split(os.path.realpath(__file__))[0] + "/resources/submit.template"
        )
    else:
        myfile = templatefile

    program = submit_vars["program"].split(".")[0]
    exp_path = submit_vars["exp_path"]
    outfile = f"{exp_path}/submit_{program}.sh"

    with open(myfile, "r") as f:
        tpl = f.read()
        filedata = tpl.format(**submit_vars)

    # Write the file out again
    with open(outfile, "w") as file:
        file.write(filedata)


def make_submitfiles(exp_path: str, configure_file: str, templatefile=None):
    with open(configure_file) as f:
        cfg = yaml.safe_load(f)

    submit_vars = dict()
    submit_vars["exp_path"] = exp_path
    submit_vars["SLURM_CPUS_PER_TASK"] = "${SLURM_CPUS_PER_TASK}"
    submit_vars["name"] = Path(exp_path).name
    submit_vars["slurm_log"] = f"{exp_path}/log/slurm.log"
    submit_vars["time"] = cfg["submit_file"]["time"]
    submit_vars["nodes"] = 1
    submit_vars["program"] = "real.exe"

    # for real.exe
    _make_submitfile_from_template(submit_vars, templatefile)

    # changes for wrf.exe
    submit_vars["nodes"] = cfg["submit_file"]["Nodes"]
    submit_vars["program"] = "wrf.exe"
    _make_submitfile_from_template(submit_vars, templatefile)


def run_wps_command(exp_path: PosixPath, program: str):
    """
    # this function combines the old geogrid.sh, ungrib.sh and metgrid.sh files to a single function.

    Args:
        exp_path: the path to the experiment folder
        program: geogrid, ungrib or metgrid

    Returns: None

    """

    wrfpath = exp_path / "wrf"
    wt_log = f"{exp_path}/log/wrftamer.log"
    prog_log = f"{exp_path}/log/{program}.log"

    cmd = f"{wrfpath}/{program}.exe"

    writeLogFile(wt_log, "run_wps_command", 0, f"Running command {cmd}")

    p = subprocess.Popen(cmd, cwd=wrfpath)
    p.wait()

    (wrfpath / f"{program}.log").rename(prog_log)

    # write to wrftamer.log file
    with open(prog_log, "r") as f:  # This may be slow is logfile is huge.
        lines = f.read().splitlines()
        if len(lines) > 0:
            last_line = lines[-1]
            if "Successful" in last_line:
                writeLogFile(
                    wt_log, "run_wps_command", 0, f": {cmd} completed successfully"
                )
            else:
                writeLogFile(wt_log, "run_wps_command", 2, f": {cmd} exited with error")


def move_output(exp_path: PosixPath):
    inpath = exp_path / "wrf"
    logpath = exp_path / "log"
    outpath = exp_path / "out"

    # log-files
    loglist = list(inpath.glob("*.log"))
    loglist.extend(list(inpath.glob("rsl*")))
    outlist = list(inpath.glob("wrfout*"))
    outlist.extend(list(inpath.glob("wrfaux*")))

    for item in loglist:
        shutil.move(str(item), str(logpath))

    for item in outlist:
        shutil.move(str(item), str(outpath))

    tslist = []
    tslist.extend(list(inpath.glob("*.TS")))
    tslist.extend(list(inpath.glob("*.UU")))
    tslist.extend(list(inpath.glob("*.VV")))
    tslist.extend(list(inpath.glob("*.WW")))
    tslist.extend(list(inpath.glob("*.TH")))
    tslist.extend(list(inpath.glob("*.QV")))
    tslist.extend(list(inpath.glob("*.PR")))
    tslist.extend(list(inpath.glob("*.PT")))
    tslist.extend(list(inpath.glob("*.PH")))

    if len(tslist) > 0:
        datestr = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        target_dir = outpath / f"tsfiles_{datestr}"

        os.makedirs(target_dir)  # will cause error if directory exists.

        for item in tslist:
            shutil.move(str(item), str(target_dir))


def update_namelist_for_rst(restart_file: str, namelistfile: str, outfile: str):
    """

    Args:

        restart_file: must have the format: wrfrst_dXX_yyyy-mm-dd_HH:MM:SS
        namelistfile: the namelist that should be updated
        outfile: usually, the same as namelistfile, but can be different for testing.

    Returns: None

    """

    # gather information
    restart_file = Path(restart_file).name  # remove path if there is one.
    rst_time = dt.datetime.strptime(restart_file[11::], "%Y-%m-%d_%H:%M:%S")

    with open(namelistfile, "r") as f:
        for line in f:
            if "max_dom" in line:
                print(line)
                break

    max_dom = int(re.sub(r"\D", "", line))  # strips string from everythin but numbers.

    cfg = dict()
    cfg["max_dom"] = max_dom
    cfg["restart"] = ".true."
    cfg["start_year"] = rst_time.year
    cfg["start_month"] = rst_time.month  # zfill?
    cfg["start_day"] = rst_time.day
    cfg["start_hour"] = rst_time.hour
    cfg["start_minute"] = rst_time.minute
    cfg["start_second"] = rst_time.second

    # Update namelist
    dom_keys = (
        "start_year start_month start_day start_hour "
        "end_year end_month end_day end_hour"
    )

    key_dict = {}

    with open(namelistfile, "r") as f:
        namelist = f.read().split("\n")

        # loop over all lines in the namelist template and reconstruct each one
        # using proper formatting and the corresponding values from the config file
        for line_nb, line in enumerate(namelist):
            if "=" not in line:
                continue
            key_full, val = line.split("=")
            key = key_full.strip()
            if key in cfg:
                if key in [
                    "start_month",
                    "start_day",
                    "start_hour",
                    "start_minute",
                    "start_second",
                ]:
                    val = (
                        str(cfg[key]).zfill(2) + ","
                    )  # bugfix, as yaml.safe_load drops leading zeros.
                else:
                    val = str(cfg[key]) + ","

                if key in dom_keys:
                    val = " ".join(
                        [str(val)] * cfg["max_dom"]
                    )  # repeat the values with number of domains
            namelist[line_nb] = " ".join([key, " " * (15 - len(key)), "=", str(val)])

            val = val.split(",")[0]
            if key in dom_keys:
                key_dict[
                    key
                ] = (
                    val.strip()
                )  # write these values in dict for calculation of run_hours
            if (
                key == "run_hours"
            ):  # this line could appear before all dom_keys, thus save this linenumber
                rh_line_nb = line_nb

        dtbeg = pd.Timestamp(
            "{start_year}-{start_month}-{start_day}-{start_hour}".format(**key_dict)
        )
        dtend = pd.Timestamp(
            "{end_year}-{end_month}-{end_day}-{end_hour}".format(**key_dict)
        )

        val = (dtend - dtbeg).total_seconds() // 3600
        val = f"{val:02.0f},"
        namelist[rh_line_nb] = " ".join(
            ["run_hours", " " * (15 - len(key)), "=", str(val)]
        )

    with open(outfile, "w") as f:
        f.write("\n".join(namelist))
