import matplotlib.pyplot as plt
from netCDF4 import Dataset
import numpy as np
import matplotlib as mpl
import pandas as pd
import wrf
import xarray as xr
import datetime as dt
from pathlib import PosixPath, Path
from wrftamer.wrfplotter_functions import Map_Basemap, Map_Cartopy, Map_hvplots
import os
from wrftamer.plotting.mpl_plots import Availability
import yaml
import typing


class Map:
    """
    Management of wrfdata for Map plotting. Loads data, manages units, cmaps and vlims.
    """

    def __init__(self, poi=pd.DataFrame(), **kwargs):

        self.poi = poi

        self.data = xr.DataArray()
        self.hgt = xr.DataArray()
        self.ivg = xr.DataArray()
        self.fig = None

        # have a default plot path
        if 'plot_path' in kwargs:
            self.plot_path = Path(kwargs['plot_path'])
        else:
            self.plot_path = Path('./')

        if 'intermediate_path' in kwargs:
            self.intermediate_path = Path(kwargs['intermediate_path'])
        else:
            self.intermediate_path = Path('./')

        if 'fmt' in kwargs:
            self.fmt = kwargs['fmt']
        else:
            self.fmt = 'png'

    # ----------------------------------------------------------------------
    def extract_data_from_wrfout(self, filename: PosixPath, dom: str, var: str, ml: int, select_time=-1) -> None:
        """

        This function is basically a wrapper to the wrf.getvar function. It loads the required data and
        sets metadata accordingly

        filename: a wrfout file
        dom: domain of the wrfoutfile (could be extracted from filename)
        var: the variable to load
        select_time: the time to load. If all times of a file should be loaded, set select_time == -1
        ml: model level
        """

        fid = Dataset(filename, 'r')
        time = wrf.getvar(fid, 'times', wrf.ALL_TIMES)

        if select_time == -1:
            idx = wrf.ALL_TIMES
        else:
            now = np.datetime64(select_time)
            idx = np.where(time == now)[0][0]

        if var == 'T':
            data = wrf.getvar(fid, 'tk', timeidx=idx, squeeze=False)[:, ml, :, :]
            data.attrs['model_level'] = ml
        elif var == 'PT':
            data = wrf.getvar(fid, 'theta', units="K", timeidx=idx, squeeze=False)[:, ml, :, :]
            data.attrs['model_level'] = ml
        elif var == 'WSP':
            data = wrf.getvar(fid, 'uvmet_wspd_wdir', units="m s-1", timeidx=idx, squeeze=False)[0][:, ml, :, :]
            data.name = 'WSP'
            data = data.drop('wspd_wdir')
            data.attrs['description'] = 'earth rotated wspd'
            data.attrs['units'] = 'm s$^{-1}$'
            data.attrs['model_level'] = ml
        elif var == 'DIR':
            data = wrf.getvar(fid, 'uvmet_wspd_wdir', units="m s-1", timeidx=idx, squeeze=False)[1][:, ml, :, :]
            data.name = 'DIR'
            data = data.drop('wspd_wdir')
            data.attrs['description'] = 'earth rotated wdir'
            data.attrs['units'] = '$\degree$'
            data.attrs['model_level'] = ml
        elif var in ['U', 'V', 'W']:
            data = wrf.getvar(fid, var.lower() + 'a', units="m s-1", timeidx=idx, squeeze=False)[:, ml, :, :]
            data.attrs['model_level'] = ml
        elif var == 'WSP10':
            data = wrf.getvar(fid, 'wspd_wdir10', units="m s-1", timeidx=idx, squeeze=False)[0][:, :, :]
            data.name = 'WSP10'
            data = data.drop('wspd_wdir')
            data.attrs['units'] = 'm s$^{-1}$'
            data.attrs['model_level'] = None
        elif var == 'DIR10':
            data = wrf.getvar(fid, 'wspd_wdir10', units="m s-1", timeidx=idx, squeeze=False)[1][:, :, :]
            data.name = 'DIR10'
            data = data.drop('wspd_wdir')
            data.attrs['description'] = 'earth rotated wdir at 10 m'
            data.attrs['units'] = '$\degree$'
            data.attrs['model_level'] = None
        elif var in ['PRES', 'P']:
            data = wrf.getvar(fid, 'p', units="Pa", timeidx=idx, squeeze=False)[:, ml, :, :]
            data.attrs['model_level'] = ml
        elif var in ['QV', 'QVAPOR']:
            data = wrf.getvar(fid, 'QVAPOR', timeidx=idx, squeeze=False)[:, ml, :, :]
            data.attrs['model_level'] = ml
        elif var == 'U10':
            data = wrf.getvar(fid, 'uvmet10', units="m s-1", timeidx=idx, squeeze=False)[0][:, :, :]
            data.attrs['units'] = 'm s$^{-1}$'
            data.attrs['model_level'] = None
        elif var == 'V10':
            data = wrf.getvar(fid, 'uvmet10', units="m s-1", timeidx=idx, squeeze=False)[1][:, :, :]
            data.attrs['units'] = 'm s$^{-1}$'
            data.attrs['model_level'] = None
        elif var in ['HFX', 'GRDFLX', 'LH', 'PSFC']:
            data = wrf.getvar(fid, var, timeidx=idx, squeeze=False)[:, :, :]
            data.attrs['model_level'] = None
        else:
            data = wrf.getvar(fid, var, timeidx=idx, squeeze=False)[:, ml, :, :]
            data.attrs['model_level'] = ml

        self.hgt = wrf.getvar(fid, 'ter', units='m', timeidx=0, squeeze=True)
        self.ivg = wrf.getvar(fid, 'LU_INDEX', timeidx=0, squeeze=True)

        try:  # LU_index might be missing in files
            # Set everything but forest to Nan, for highlighting only forest in Maps.
            tmp1 = (self.ivg.values > 1) & (self.ivg.values < 11)  # other
            tmp2 = (self.ivg.values > 10) & (self.ivg.values < 16)  # Forest
            tmp3 = (self.ivg.values > 15)  # Other
            self.ivg.values[tmp1] = 0
            self.ivg.values[tmp2] = 1
            self.ivg.values[tmp3] = 0
            tmp4 = self.ivg.values == 0
            self.ivg.values[tmp4] = np.nan
        except:
            # No changes to ivg on error
            self.ivg = wrf.getvar(fid, 'LU_INDEX', timeidx=0, squeeze=True)

        self.data = data
        self.data.attrs['dom'] = dom

    def store_intermediate(self):
        """
        Extraction a subsample of Data from the full WRF Model output seems to be the best option to deal
        with the ploblem of large datasets and wrf-python being unable to use dask (creating a bottleneck).
        """

        # I need to replace the attribute 'projection' before I can store it as netcdf.

        def replace_proj(data_array: xr.DataArray):

            proj = data_array.projection
            new_attrs = dict()
            new_attrs['stand_lon'] = proj.stand_lon
            new_attrs['moad_cen_lat'] = proj.moad_cen_lat
            new_attrs['truelat1'] = proj.truelat1
            new_attrs['truelat2'] = proj.truelat2
            new_attrs['pole_lat'] = proj.pole_lat
            new_attrs['pole_lon'] = proj.pole_lon

            del data_array.attrs['projection']

            data_array = data_array.assign_attrs(new_attrs)

            return data_array

        self.data = replace_proj(self.data)
        self.hgt = replace_proj(self.hgt)
        self.ivg = replace_proj(self.ivg)

        date = self.data.Time.values[0]
        t = pd.to_datetime(str(date))
        timestring = t.strftime('%Y%m%d_%H%M%S')

        if self.data.model_level is None:
            savename = self.intermediate_path / f'Interm_{self.data.dom}_{self.data.name}_{timestring}.nc'
        else:
            savename = self.intermediate_path / f'Interm_{self.data.dom}_{self.data.name}_{timestring}_ml{self.data.model_level}.nc'

        self.data.to_netcdf(savename)
        self.hgt.to_netcdf(self.intermediate_path / f'hgt_{self.data.dom}.nc')
        self.ivg.to_netcdf(self.intermediate_path / f'ivg_{self.data.dom}.nc')

    def load_intermediate(self, dom: str, var: str, model_level, timestring: str):

        def replace_proj2(data_array: xr.DataArray):

            proj = wrf.projection.LambertConformal(stand_lon=data_array.stand_lon, moad_cen_lat=data_array.moad_cen_lat,
                                                   truelat1=data_array.truelat1, truelat2=data_array.truelat2,
                                                   pole_lat=data_array.pole_lat, pole_lon=data_array.pole_lon)

            new_attrs = dict()
            new_attrs['projection'] = proj
            del data_array.attrs['stand_lon']
            del data_array.attrs['moad_cen_lat']
            del data_array.attrs['truelat1']
            del data_array.attrs['truelat2']
            del data_array.attrs['pole_lat']
            del data_array.attrs['pole_lon']

            data_array = data_array.assign_attrs(new_attrs)

            return data_array

        if model_level is None:
            savename = self.intermediate_path / f'Interm_{dom}_{var}_{timestring}.nc'
        else:
            savename = self.intermediate_path / f'Interm_{dom}_{var}_{timestring}_ml{model_level}.nc'

        if timestring == '*':
            xa = xr.open_mfdataset(str(savename))
            self.data = xa[var]
        else:
            self.data = xr.open_dataarray(savename)

        self.hgt = xr.open_dataarray(self.intermediate_path / f'hgt_{dom}.nc')
        self.ivg = xr.open_dataarray(self.intermediate_path / f'ivg_{dom}.nc')

        self.data = replace_proj2(self.data)
        self.hgt = replace_proj2(self.hgt)
        self.ivg = replace_proj2(self.ivg)

    def plot(self, map_t='Basemap', vmin=None, vmax=None, store=True, **kwargs) -> None:
        """
        This methods prepares the data for plotting using basemap or cartopy. Limits are set, cmaps
        are prepared, for IVGTYP, a simplification is applied.
        """

        if self.data.name == 'WSP':
            if vmin is None and vmax is None:
                vmin, vmax = np.floor(self.data.min().values), np.ceil(self.data.max().values)

            if self.data.description.split(' ')[-1] == 'Difference':
                cmapname = 'seismic'
            else:
                cmapname = 'viridis'

            myticks = np.linspace(vmin, vmax, 10)
            pcmesh = False

        elif self.data.name in ['U', 'V']:
            if vmin is None and vmax is None:
                vmin, vmax = np.floor(self.data.min().values), np.ceil(self.data.max().values)
            cmapname = 'hsv'
            myticks = np.linspace(vmin, vmax, 10)
            pcmesh = False

        elif self.data.name in ['DIR']:
            if vmin is None and vmax is None:
                vmin, vmax = 0, 360
            cmapname = 'hsv'
            vdel = 10
            myticks = np.arange(vmin, vmax + vdel, vdel)
            pcmesh = False

        elif self.data.name in ['HGT']:
            cmapname = 'terrain'
            if vmin is None and vmax is None:
                vmin, vmax = self.hgt.min().values, self.hgt.max.values()

            vmin = int(25 * round(float(vmin) / 25.))
            vmax = int(25 * round(float(vmax) / 25.))
            myticks = np.linspace(vmin, vmax, 10)
            # myticks = np.arange(vmin, vmax, int(25 * round((vmax - vmin) / 250.)))
            pcmesh = False

        elif self.data.name == 'IVGTYP':
            if vmin is None and vmax is None:
                vmin, vmax = 1, 3
            cmap = mpl.colors.ListedColormap(['#8B0000', '#013220', '#D3D3D3'])
            bounds = range(1, vmax + 1)
            norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
            names = ['Urban', 'Forest', 'Other']
            myticks = range(1, vmax + 1)
            self.data[(self.data > 1) & (self.data < 11)] = 3  # Other
            self.data[(self.data > 10) & (self.data < 16)] = 2  # Forest
            self.data[self.data > 15] = 3  # Other
            pcmesh = False
            cmapname = 'jet'  # TODO: must find a workaround.
        else:
            cmapname = 'viridis'
            myticks = np.arange(vmin, vmax, int(25 * round((vmax - vmin) / 250.)))
            pcmesh = True

        cmap = plt.cm.get_cmap(cmapname)

        if store:  # loop over all indices and save files
            tdim = self.data.shape[0]
            for tidx in range(0, tdim):

                tmp_data = self.data[tidx, :, :]

                if map_t == 'Basemap':
                    figure = Map_Basemap(tmp_data, self.hgt, self.ivg, vmin, vmax, cmap,
                                         myticks, self.poi, pcmesh=pcmesh, add_topo=False, **kwargs)
                elif map_t == 'Cartopy':
                    figure = Map_Cartopy(tmp_data, self.hgt, self.ivg, vmin, vmax, cmap,
                                         myticks, self.poi, pcmesh=pcmesh, add_topo=False)
                else:
                    figure = Map_hvplots(tmp_data, vmin, vmax, cmapname, self.poi)

                date = tmp_data.Time.values
                t = pd.to_datetime(str(date))
                timestring = t.strftime('%Y%m%d_%H%M%S')

                if self.data.model_level is None:
                    savename = f'{self.plot_path}/Map_{self.data.dom}_{self.data.name}_{timestring}.{self.fmt}'
                else:
                    savename = f'{self.plot_path}/Map_{self.data.dom}_{self.data.name}_{timestring}_ml{self.data.model_level}.{self.fmt}'

                figure.savefig(savename, dpi=400)
                plt.close(figure)

        else:  # display only required tidx and return figure
            if 'tidx' in kwargs:
                tidx = kwargs['tidx']
            else:
                tidx = 0

            tmp_data = self.data[tidx, :, :]

            if map_t == 'Basemap':
                figure = Map_Basemap(tmp_data, self.hgt, self.ivg, vmin, vmax, cmap,
                                     myticks, self.poi, pcmesh=pcmesh, add_topo=False, **kwargs)
            elif map_t == 'Cartopy':
                figure = Map_Cartopy(tmp_data, self.hgt, self.ivg, vmin, vmax, cmap,
                                     myticks, self.poi, pcmesh=pcmesh, add_topo=False)
            else:
                figure = Map_hvplots(tmp_data, vmin, vmax, cmapname, self.poi)

            return figure


# -----------------------------------------------------------------------------------------------------------------------

# some helperfunctions
def get_list_of_filenames(name_of_dataset: str, search_str: str, dtstart: dt.datetime, dtend: dt.datetime):
    # The user provides an observation path and a stationname to be read in.
    # i.e. the structure is
    # obs_path/name_of_dataset1/<search_str1_start1_end1.nc>
    # obs_path/name_of_dataset1/<search_str1_start2_end2.nc>
    # obs_path/name_of_dataset1/...
    # obs_path/name_of_dataset2/<search_str1_start1_end1.nc>
    # obs_path/...

    # All of them must be in the CF-conform filetpye

    # The WRFplotter can provide startdate_enddate. The Stationname can be selected.

    #############################################################################
    # CONVENTION: Each file must be named Stationname_starttime_endtime.nc
    # Starttime and endtime on the day-basis should be fine for now
    # Can do an update later on.
    #############################################################################

    filepath = Path(os.environ['OBSERVATIONS_PATH']) / f'{name_of_dataset}/'
    list_of_files = list(filepath.glob(f'{search_str}*.nc'))
    list_of_files.sort()

    list_of_starts = [item.stem.split('_')[1] for item in list_of_files]
    list_of_ends = [item.stem.split('_')[2] for item in list_of_files]

    starts = np.asarray([dt.datetime.strptime(item, '%Y%m%d') for item in list_of_starts])
    ends = np.asarray([dt.datetime.strptime(item, '%Y%m%d') for item in list_of_ends])

    try:
        idx1 = np.argmax(starts[starts <= dtstart])
    except ValueError:
        idx1 = 0
    try:
        idx2 = np.argmax(ends[ends <= dtend])
    except ValueError:
        idx2= 0

    filenames = list_of_files[idx1:idx2+1]

    return filenames


def assign_cf_attributes_tslist(data: xr.Dataset, metadata: dict, cf_table: typing.Union[str, bytes, os.PathLike],
                                old_attrs=None, verbose=False):
    """
    Required metadata:
    - Conventions (i.e. CF-1.8)
    - featureType (point,timeSeries,trajectory,profile,timeSeriesProfile,trajectoryProfile)
    - station_name
    - lat, lon, station_altitude

    Suggestion for good metadata:
    - title, institution, source, history, references, comment (root level)
    - level, platform_name, platform_id, (root level)
    - description, Flags, altitude, _FillValue, missing_value, (variable level), calendar (time)
    """
    if old_attrs is None:
        old_attrs = []

    # Check for minimal amout of metadata
    minimal_set = ['Conventions', 'featureType', 'station_name', 'lat', 'lon', 'station_elevation']
    for item in minimal_set:
        if item not in metadata:
            print(f'Required entry {item} not found in metadata. Aborting')
            return

    recommended_set = ['title', 'institution', 'source', 'history', 'references', 'comment']
    for item in recommended_set:
        if item not in metadata:
            if verbose:
                print(f'Consider putting {item} into the metadata')

    if 'lat' not in data:  # assuming all are missing if one are missing.
        lat = xr.DataArray(metadata['lat'])
        lon = xr.DataArray(metadata['lon'])
        alt = xr.DataArray(metadata['station_elevation'])

        data = data.assign({'lat': lat, 'lon': lon, 'station_elevation': alt})

    if 'station_name' not in data:
        name = xr.DataArray(metadata['station_name'])  # maybe I have to assign stationname in a different way?
        data = data.assign({'station_name': name})

    with open(cf_table, 'r') as fid:
        cf_con = yaml.safe_load(fid)

    # set attributes of variables according to cf table
    for item in data:
        if item in ['station_name', 'station_elevation', 'GEN_SPD']:
            var = item.lower()
        else:
            var = item.split('_')[0].lower()

        data[item] = data[item].assign_attrs(cf_con[var])

    data.time.attrs = cf_con['time']

    # Set attributes
    for item in metadata:
        if item in ['lat', 'lon', 'station_elevation', 'station_name']:
            pass  # created above
        else:
            # non-dicts are written to the root level.
            data.attrs[item] = metadata[item]

    # Remove old attributes:
    for item in old_attrs:
        try:
            del data.attrs[item]
        except KeyError:
            pass

    return data


def calc_PT(data):
    """
    Calculate PT from P and T if these variables exists.
    This function assumes the name of the variables to be P_level and T_level.
    This may not be general enough!
    """

    # TODO: I need to generalize this code to work for a dataset with multiple stations.
    # For now, this works fine, since P_ and T_ do not exist for AV datasets.

    tmp1 = [i for i in list(data.variables) if i.startswith('P_')]
    tmp2 = [i for i in list(data.variables) if i.startswith('T_')]

    hgt = data['station_elevation'].values

    if len(tmp1) > 1 and len(tmp2) > 0:
        zp = [int(item.split('_')[1]) for item in tmp1]
        zlow, zhigh = min(zp), max(zp)

        if data['P_' + str(zlow)].units == 'hPa':
            factor = 100
        elif data['P_' + str(zlow)].units == 'Pa':
            factor = 100  # TODO: in Future: 1 right now, I got an error in the data.
        else:
            raise ValueError

        plow  = data['P_' + str(zlow) ].values.T * factor
        phigh = data['P_' + str(zhigh)].values.T * factor

        ztarget = np.asarray([int(item.split('_')[1]) for item in tmp2])

        # z amsl
        zlow    = float(zlow) + hgt
        zhigh   = float(zhigh) + hgt
        ztarget = ztarget.astype(float) + hgt

        # Transform T in PT
        # Calculate pressure at each Height.
        # This is based on the pressure measurements at two levels.
        # The expontential Formula is p=p0*exp(-z/H)
        # 1) calc H; 2) calc p0; 3) calc p(all relevant z)

        H = (zhigh - zlow) / np.log(plow / phigh)
        p0 = phigh / np.exp(-zhigh / H)

        for zlev in ztarget:

            ptarget = p0 * np.exp(-zlev / H)
            ##############################################
            kappa = 2. / 7.  # R/cp
            p00 = 10 ** 5    # Pa
            ##############################################

            pt = (data['T_' + str(int(zlev))][:] + 273.15) * (p00 / ptarget) ** kappa
            pt = pt.assign_attrs(units='K')
            pt = pt.assign_attrs(standard_name='potential_temperature')
            pt = pt.assign_attrs(long_name='potential temperature')
            data = data.assign({'PT_' + str(int(zlev)): pt})
        ####################################################################################

    return data


class Timeseries:
    """
    For reading, checking and writing timeseries data.

    Files must follow the following convention:
    1. they must follow this structure:
        OBSERVATIONS_PATH/<Stationname>/<Stationname_startdate_enddate.nc>
        OBSERVATIONS_PATH: environment variable (the absolute path)
        Stationname: Name of the Station or whatever the source of the Timeseries
        startdate, enddate: Format YYYYMMDD (== %Y%m%d)
    2. the files must be netcdf files that can be read by xarray
    3. Multiple files can be read at once.

    Data stored by this calss is stored in a netcdf file that follows the CF-Conventions.

    This class should be able to:
    - Read and write CF-conform ncfiles.
    - Accept data from outside sources along with metadata to write into a CF conform file
    - make some simple calculations (like calc PT)

    ****
    Be aware that right now, ds.to_netcdf is not able to write cf-conform netcdf files.
    One issue is, that a string variable, as used for the station name has a variable length (VLEN),
    which is not allowed by the CF standard (and the cf-checker complains)

    This may be resolved with future version of either ds.to_netcdf or a less strict CF-convention.
    ****


    Daniel Leukauf, 07.03.2022
    """

    # I have removed plots for profiles and timeseries as such basic plots won't be used anyway.
    # The methods of hvplot.xarray take care of that and more sophisticated plots
    # are done by the plotter. I keep the availability plot though as this is quite useful.

    def __init__(self, name_of_dataset: str, stationname: str, dtstart: dt.datetime, dtend: dt.datetime,
                 calc_pt=False, data=None, metadata=None, verbose=False):

        if metadata is None:
            metadata = dict()

        self.metadata = metadata
        self.filenames = get_list_of_filenames(name_of_dataset, stationname, dtstart, dtend)

        if data is None:
            try:
                self.data = self._read_cfconform_data(calc_pt, verbose)
            except Exception as e:
                print(e)
                self.data = None
        else:
            if isinstance(data, xr.Dataset) or isinstance(data, xr.DataArray):
                self.data = data
            else:
                print('data must be of type xarray.Dataset of xarray.DataArray.')
                return

    # ----------------------------------------------------------------------
    #  Getters
    # ----------------------------------------------------------------------
    def _read_cfconform_data(self, calc_pt=False, verbose=False):

        if verbose:
            for filename in self.filenames:
                print(f'Loading File {filename}')

        data = xr.open_mfdataset(self.filenames)

        if calc_pt:
            # This will only do something if T_X and P_Y exists.
            try:
                data = calc_PT(data)
            except:
                pass

        # CF Conform data already has attributes
        # Add more medadata. If these already exist, they are overwritten.
        data = data.assign_attrs(self.metadata)
        return data

    # ----------------------------------------------------------------------
    #  Selectors # Im not even sure I need these....
    # ----------------------------------------------------------------------
    def select_profile(self, dtobj: dt.datetime) -> None:
        xa = self.data
        xa = xa.where(xa.time == np.datetime64(dtobj), drop=True)

        tmp_time = xa.time[0].values
        xa = xa.squeeze(drop=True)
        xa = xa.assign_attrs({'time': tmp_time})

        return xa

    def select_timeseries(self, var: str, zz: float) -> None:

        xa = self.data
        xa = xa[var].where(xa[var]['Z_' + var] == zz, drop=True)
        xa = xa.squeeze(drop=True)
        xa = xa.assign_attrs({'Z': zz})

        return xa

    # ----------------------------------------------------------------------
    #  Writers
    # ----------------------------------------------------------------------
    def write_cfconform_data(self, targetfile, metadata, old_attrs=None, overwrite=False, verbose=False):

        cf_table = os.path.split(os.path.realpath(__file__))[0] + '../wrftamer/resources/cf_table_wrfdata.yaml'
        self.data = assign_cf_attributes_tslist(self.data, metadata, cf_table, old_attrs, verbose)

        if os.path.exists(targetfile) and not overwrite:
            print(f'merging into {targetfile}')
            old_data = xr.open_dataset(targetfile)
            all_data = xr.concat([old_data, self.data], dim='station')
            old_data.close()
            all_data.to_netcdf(targetfile, mode='w', unlimited_dims='time')
            all_data.close()
        else:
            print(f'Write new file {targetfile}')
            self.data.to_netcdf(targetfile, mode='w', unlimited_dims='time')

    # ----------------------------------------------------------------------
    #  Plotters
    # ----------------------------------------------------------------------

    def plot_Availability(self, var: str, year: str, zz: float):

        """
        Creates a plot of the data availability.

        Args:
            var: short name of the variable
            year: the year for which the plot should be shown
            zz: the height. Only used for labeling.

        Returns: None

        DLeuk, 21.05.2021

        """

        # first, get timeseries of the chosen variable and dtvec
        data = self.data[var].values
        dtvec = self.data.time.values

        dtvec_dt = []
        for dt64 in dtvec:
            ts = (dt64 - np.datetime64('1970-01-01T00:00:00')) / np.timedelta64(1, 's')
            dtvec_dt.append(dt.datetime.utcfromtimestamp(ts))

        # now, calculate the Availability Matrix for each day of the year [0-100 %]
        Avail = np.zeros([12, 31]) * np.nan
        for mon in np.arange(1, 13):
            for day in np.arange(1, 32):
                mask = [item.day == day and item.month == mon for item in dtvec_dt]
                tmp_data = data[mask]

                tmp_dtvec = np.asarray(dtvec_dt)
                tmp_dtvec = tmp_dtvec[mask]
                if len(tmp_dtvec) > 0:
                    Avail[mon - 1, day - 1] = (1 - sum(np.isnan(tmp_data)) / len(tmp_data)) * 100.

        Availability(Avail, zz, var, year)
