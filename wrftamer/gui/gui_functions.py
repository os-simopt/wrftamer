from pathlib import PosixPath
import panel as pn
import datetime as dt


def get_vars_per_plottype() -> dict:
    vars_per_plottype = dict()
    vars_per_plottype['Profiles'] = ['WSP', 'DIR', 'PT', 'U', 'V', 'W']
    vars_per_plottype['zt-Plot'] = ['WSP', 'DIR', 'PT', 'U', 'V', 'W']
    vars_per_plottype['Obs vs Mod'] = ['WSP', 'DIR']
    vars_per_plottype['Timeseries'] = ['WSP', 'DIR', 'PT', 'PRES']
    vars_per_plottype['Timeseries 2'] = ['WSP and DIR', 'WSP and PT']
    vars_per_plottype['Map'] = ['WSP', 'DIR', 'PT', 'PRES', 'PSFC', 'U', 'V', 'W', 'HFX', 'GRDFLX', 'LH']
    vars_per_plottype['Diff Map'] = ['WSP', 'DIR', 'PT', 'PRES', 'PSFC', 'U', 'V', 'W', 'HFX', 'GRDFLX', 'LH']
    vars_per_plottype['CS'] = ['WSP', 'DIR', 'PT', 'PRES', 'PSFC', 'U', 'V', 'W', 'HFX', 'GRDFLX', 'LH']
    vars_per_plottype['Diff CS'] = ['WSP', 'DIR', 'PT', 'PRES', 'PSFC', 'U', 'V', 'W', 'HFX', 'GRDFLX', 'LH']

    return vars_per_plottype


def get_lev_per_plottype_and_var() -> dict:
    lev_per_plottype_and_var = dict()
    lev_per_plottype_and_var['Profiles'] = {'WSP': [], 'DIR': [], 'PT': [], 'U': [], 'V': [], 'W': []}
    lev_per_plottype_and_var['zt-Plot'] = lev_per_plottype_and_var['Profiles']
    lev_per_plottype_and_var['Obs vs Mod'] = {'WSP_Analog': ['41', '51', '61', '71', '81', '91', '102'],
                                              'DIR_Anlog': ['34', '51', '71', '91'],
                                              'WSP_Sonic': ['42', '62', '82'],
                                              'DIR_Sonic': ['42', '62', '82']}
    lev_per_plottype_and_var['Timeseries'] = {'WSP_Analog': ['41', '51', '61', '71', '81', '91', '102'],
                                              'DIR_Analog': ['34', '51', '71', '91'],
                                              'WSP_Sonic': ['42', '62', '82'],
                                              'DIR_Sonic': ['42', '62', '82'],
                                              'PT': ['34', '42', '52', '72', '101'],
                                              'T': ['34', '42', '52', '72', '101'],
                                              'PRES': ['21', '92']}
    lev_per_plottype_and_var['Timeseries 2'] = {'WSP and DIR_Sonic': ['42 and 42', '62 and 62', '82 and 82'],
                                                'WSP and DIR_Analog': ['41 and 34', '51 and 51', '71 and 71',
                                                                       '91 and 91'],
                                                'WSP and PT_Sonic': ['42 and 42', '62 and 52', '82 and 72'],
                                                'WSP and PT_Analog': ['41 and 42', '51 and 52', '71 and 72']}
    lev_per_plottype_and_var['Map'] = {'WSP': ['5'], 'DIR': ['5'], 'PT': ['5'], 'PRES': ['5'], 'PSFC': ['0'],
                                       'U': ['5'], 'V': ['5'], 'W': ['5'], 'HFX': ['0'], 'GRDFLX': ['0'], 'LH': ['0']}
    lev_per_plottype_and_var['Diff Map'] = lev_per_plottype_and_var['Map']
    lev_per_plottype_and_var['CS'] = lev_per_plottype_and_var['Profiles']
    lev_per_plottype_and_var['Diff CS'] = lev_per_plottype_and_var['Profiles']

    return lev_per_plottype_and_var


def get_newfilename_from_old(current_filename: PosixPath, delta_t: int):
    """
    Takes a filename of the form path/to/Map_d0X_VAR_YYYYMMDD_HHMMSS_mlY.png and creates a new
    filename (with increased or decreased time.

    current_filename: PosixPath of the current file
    delta_t: increase or decrease of time in minutes (may be negative)

    returns: new_filename ( if the file exists, otherwise current_filename)
    """

    timestamp = '_'.join(current_filename.stem.split('_')[3:5])
    dtobj = dt.datetime.strptime(timestamp, '%Y%m%d_%H%M%S')
    dtobj = dtobj + dt.timedelta(minutes=delta_t)
    timestamp2 = dtobj.strftime('%Y%m%d_%H%M%S')

    parts = current_filename.stem.split('_')
    parts[3] = timestamp2.split('_')[0]
    parts[4] = timestamp2.split('_')[1]
    new_filename = current_filename.parent / ('_'.join(parts) + current_filename.suffix)

    print(current_filename)
    print(new_filename)

    if new_filename.is_file():
        return new_filename
    else:
        return current_filename


def error_message(message):
    md_pane = pn.pane.Markdown(
        f"""
        **Plot cannot be created.**

        Select parameters and click *Load data*.

        Error: {message}
        """
        , width=600)
    return md_pane


def error_message2(filename):
    md_pane = pn.pane.Markdown(
        f"""
        **Not able to find file**.

        {filename}
        """
        , width=600)
    return md_pane
