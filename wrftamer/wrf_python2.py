"""
This litte class replaces wrf-python, since wrf-python is not able to work with dask and turned out to be a bottle-
neck.

Right now, it has only a very limited functionality, but I will add more of wrf-pythons features as they are required.

wrf2 works based on xarray so it sould be much faster than wrf-python.

First tests of a single wrfout file (containing 1 GB of data) show that wrf-pyhton takes 27.3 s to load data, unstagger
and unrotate wind variables while this class only needs 4.5 s. (2. Versuch 9.4 s)

Equality of the results have been tested for:
destagger:
    U,V,W: exact
combine_basevars:
    P,PB: exact
    PH,PHB: difference O(10^-3 m)
unrotate_uv:
    wsp: O(10^-6 m/s)
    dir: O(0.08 degrees)

Author: Daniel Leukauf

# Speedtest and maximum performance

Results from access to multiple files:
    Both variants lead to a crash once python tries to access the data. It is simply too much.
    For 3 files: wrf: 1min20, wrf2: 26-40 s
    For 2 files: wrf: 54.1s wrf2: 11.7s

Conclusio:
A limitation to x,y indices is really important. Unfortunately, wrf-python does not seem to allow for that.

Limited to a single level, but loading all files:
    takes 2min 20s for MayCase, Ref
    In comparison to intermediate files: 204 ms.

Conclusio: for the WRF-plotter, I cannot live without intermediate files. However, the new functions should speed up
the creation of these intermediate files.

I need:
    Selection by lat,lon,z,time (not indices)
"""

import xarray as xr
import numpy as np
from pathlib import PosixPath
from typing import Union
import cartopy.crs as crs


class wrf2:

    def __init__(self):
        pass


def get_standard_vars(filename: Union[PosixPath, list], ignore_warn=False, **kwargs) -> xr.Dataset:
    """
    This is a shorthand. May write a getvar function at some point.
    """

    vars_i_seek = ['U', 'V', 'W', 'U10', 'V10', 'T', 'PT', 'P', 'PB', 'PH', 'PHB', 'HFX', 'GRDFLX', 'LH', 'PSFC',
                   'LU_INDEX', 'HGT', 'COSALPHA', 'SINALPHA']

    if isinstance(filename, list):
        if not ignore_warn:
            if len(filename) > 3:
                print('Warning! You are potentially trying to read a LOT of data, which may cause python to crash.')
                print('If you want to proceed, call this function again with the argument "ignore_warn=True".')
                return xr.Dataset()

        data = xr.open_mfdataset(filename, concat_dim='Time', combine='nested')
    else:
        data = xr.open_dataset(filename)

    vars2drop = []
    for item in data.data_vars:
        if item not in vars_i_seek:
            vars2drop.append(item)

    data = data.drop_vars(vars2drop)
    attrs = data.attrs

    # first, check for subselection, as it is faster to subselect before doing the other calculations.
    new_data = subselect_by_idx(data, **kwargs)
    new_data = subselect_every_nth_tidx(new_data, **kwargs)

    # Then, do some calculations
    new_data = unstagger(new_data)
    new_data = combine_basevars(new_data)
    new_data = unrotate_uv(new_data)
    new_data = get_uvmet(new_data)
    new_data.attrs = attrs

    # for item in new_data:
    #    new_data.attrs['projection']=

    data.close()

    return new_data


def get_timevector(filename: Union[PosixPath, list]):
    if isinstance(filename, list):
        data = xr.open_mfdataset(filename, concat_dim='Time', combine='nested')
    else:
        data = xr.open_dataset(filename)

    return data.XTIME.values


def subselect_every_nth_tidx(data: xr.Dataset, **kwargs) -> xr.Dataset:
    if 'select_every' in kwargs:
        n = kwargs['select_every']
    else:
        return data

    all_xa = dict()
    for item in data:
        all_xa[item] = data[item][::n]
        # I know that the first dimension is always time. This will fail otherwise

    data = xr.Dataset().assign(all_xa)
    return data


def subselect_by_idx(data: xr.Dataset, **kwargs) -> xr.Dataset:
    if 'tindices' in kwargs:
        tidx1, tidx2 = kwargs['tindices']
    else:
        tidx1, tidx2 = 0, data.dims['Time']

    if 'xindices' in kwargs:
        xidx1, xidx2 = kwargs['xindices']
    else:
        xidx1, xidx2 = 0, data.dims['west_east']

    if 'yindices' in kwargs:
        yidx1, yidx2 = kwargs['yindices']
    else:
        yidx1, yidx2 = 0, data.dims['south_north']

    if 'zindices' in kwargs:
        zidx1, zidx2 = kwargs['zindices']
    else:
        zidx1, zidx2 = 0, data.dims['bottom_top']

    # Sanity checks.
    expected = ['tindices', 'xindices', 'yindices', 'zindices']
    if all(x not in expected for x in kwargs):
        return data  # nothing to do.

    if tidx2 <= tidx1 or xidx2 <= xidx1 or yidx2 <= yidx1 or zidx2 <= zidx1:
        print('Second index must be greater than first index')
        return xr.Dataset()
    # --------------------------------------------------

    all_xa = dict()
    for item in data:
        if data[item].dims == ('Time', 'bottom_top', 'south_north', 'west_east'):
            all_xa[item] = data[item][tidx1:tidx2, zidx1:zidx2, yidx1:yidx2, xidx1:xidx2]
        if data[item].dims == ('Time', 'south_north', 'west_east'):
            all_xa[item] = data[item][tidx1:tidx2, yidx1:yidx2, xidx1:xidx2]
        if data[item].dims == ('Time', 'bottom_top', 'south_north_stag', 'west_east'):
            all_xa[item] = data[item][tidx1:tidx2, zidx1:zidx2, yidx1:yidx2 + 1, xidx1:xidx2]
        if data[item].dims == ('Time', 'bottom_top', 'south_north', 'west_east_stag'):
            all_xa[item] = data[item][tidx1:tidx2, zidx1:zidx2, yidx1:yidx2, xidx1:xidx2 + 1]
        if data[item].dims == ('Time', 'south_north_stag', 'west_east'):
            all_xa[item] = data[item][tidx1:tidx2, yidx1:yidx2 + 1, xidx1:xidx2]
        if data[item].dims == ('Time', 'south_north', 'west_east_stag'):
            all_xa[item] = data[item][tidx1:tidx2, yidx1:yidx2, xidx1:xidx2 + 1]
        if data[item].dims == ('Time', 'bottom_top_stag', 'south_north', 'west_east'):
            all_xa[item] = data[item][tidx1:tidx2, zidx1:zidx2 + 1, yidx1:yidx2, xidx1:xidx2]
        if data[item].dims == 'Time':
            all_xa[item] = data[item][tidx1:tidx2]

    data = xr.Dataset().assign(all_xa)
    return data


def subselect_by_value(lower_left: tuple, upper_right: tuple, vertical_range: tuple):
    # calculated xindices, yindices, zdindices and call subselect_by_idx()
    # requires for me to calculate z on all data...

    raise NotImplementedError

    pass


def unstagger(data: xr.Dataset) -> xr.Dataset:
    # TODO: this function is very slow for some reason. Investigate...

    for var in data:

        xlat = data['XLAT']
        xlon = data['XLONG']
        XTIME = data['XTIME']
        Time = data['Time']

        if 'stagger' in data[var].attrs:

            if data[var].stagger == 'X':
                tmp_data = data[var].values
                tmp_data = (tmp_data[:, :, :, 0:-1] + tmp_data[:, :, :, 1::]) / 2.
                change = True
            elif data[var].stagger == 'Y':
                tmp_data = data[var].values
                tmp_data = (tmp_data[:, :, 0:-1, :] + tmp_data[:, :, 1::, :]) / 2.
                change = True
            elif data[var].stagger == 'Z':
                tmp_data = data[var].values
                tmp_data = (tmp_data[:, 0:-1, :, :] + tmp_data[:, 1::, :, :]) / 2.
                change = True
            else:
                tmp_data = None
                change = False

            if change:
                attrs = data[var].attrs

                data = data.drop_vars(var)
                new_da = xr.DataArray(data=tmp_data, coords={'XLAT': xlat, 'XLONG': xlon, 'XTIME': XTIME, 'Time': Time},
                                      dims=('Time', 'bottom_top', 'south_north', 'west_east'))
                new_da.attrs = attrs
                data = data.assign({var: new_da})

    for var in ['XLAT_U', 'XLAT_V', 'XLONG_U', 'XLONG_V']:
        if var in data:
            data = data.drop_vars(var)

    for var in data:
        if 'stagger' in data[var].attrs:
            del data[var].attrs['stagger']

    return data


def combine_basevars(data: xr.Dataset) -> xr.Dataset:
    if 'P' in data.data_vars and 'PB' in data.data_vars:
        p = data['P'] + data['PB']
        attrs = data['P'].attrs
        attrs['description'] = 'pressure'
        p.attrs = attrs
        data = data.drop_vars(['P', 'PB'])
        data = data.assign({'P': p})

    if 'PH' in data.data_vars and 'PHB' in data.data_vars:
        z = (data['PH'] + data['PHB']) / 9.81
        attrs = data['PH'].attrs
        attrs['description'] = 'model height - [MSL] (mass grid)'
        attrs['units'] = 'm'
        z.attrs = attrs
        data = data.drop_vars(['PH', 'PHB'])
        data = data.assign({'Z': z})

    return data


def unrotate_uv(data: xr.Dataset) -> xr.Dataset:
    if 'COSALPHA' not in data.data_vars or 'SINALPHA' not in data.data_vars:
        return data

    # ------------------------------------------------------------------------
    cosalpha = data['COSALPHA'].values
    sinalpha = data['SINALPHA'].values

    if 'U10' in data.data_vars and 'V10' in data.data_vars:
        Uearth = data['U10'] * cosalpha - data['V10'] * sinalpha
        Vearth = data['V10'] * cosalpha + data['U10'] * sinalpha
        attrs1 = data['U10'].attrs
        attrs2 = data['V10'].attrs
        attrs1['description'] = 'earth rotated u10'
        attrs2['description'] = 'earth rotated v10'

        data = data.drop_vars(['U10', 'V10'])
        new_da1 = xr.DataArray(data=Uearth,
                               coords={'XLAT': data['XLAT'], 'XLONG': data['XLONG'], 'XTIME': data['XTIME'],
                                       'Time': data['Time']},
                               dims=('Time', 'south_north', 'west_east'))
        new_da2 = xr.DataArray(data=Vearth,
                               coords={'XLAT': data['XLAT'], 'XLONG': data['XLONG'], 'XTIME': data['XTIME'],
                                       'Time': data['Time']},
                               dims=('Time', 'south_north', 'west_east'))
        new_da1.attrs = attrs1
        new_da2.attrs = attrs2

        data = data.assign({'U10': new_da1, 'V10': new_da2})

    if 'U' in data.data_vars and 'V' in data.data_vars:
        zdim = data.dims['bottom_top']

        cosalpha = np.tile(cosalpha, [zdim, 1, 1, 1])
        cosalpha = np.moveaxis(cosalpha, 0, 1)

        sinalpha = np.tile(sinalpha, [zdim, 1, 1, 1])
        sinalpha = np.moveaxis(sinalpha, 0, 1)

        Uearth = data['U'] * cosalpha - data['V'] * sinalpha
        Vearth = data['V'] * cosalpha + data['U'] * sinalpha

        attrs1 = data['U'].attrs
        attrs2 = data['V'].attrs
        attrs1['description'] = 'earth rotated u'
        attrs2['description'] = 'earth rotated v'

        data = data.drop_vars(['U', 'V'])
        new_da1 = xr.DataArray(data=Uearth,
                               coords={'XLAT': data['XLAT'], 'XLONG': data['XLONG'], 'XTIME': data['XTIME'],
                                       'Time': data['Time']},
                               dims=('Time', 'bottom_top', 'south_north', 'west_east'))
        new_da2 = xr.DataArray(data=Vearth,
                               coords={'XLAT': data['XLAT'], 'XLONG': data['XLONG'], 'XTIME': data['XTIME'],
                                       'Time': data['Time']},
                               dims=('Time', 'bottom_top', 'south_north', 'west_east'))
        new_da1.attrs = attrs1
        new_da2.attrs = attrs2

        data = data.assign({'U': new_da1, 'V': new_da2})

    data = data.drop_vars(['COSALPHA', 'SINALPHA'])

    return data


def get_uvmet(data: xr.Dataset) -> xr.Dataset:
    def uv_to_FFDD(u, v):
        # Calculates meteorological wind speed and -direction from u and v.

        wspd = np.sqrt(u ** 2 + v ** 2)
        wdir = 180. / np.pi * np.arctan2(-u, -v)
        wdir = np.mod(wdir, 360)

        return wspd, wdir

    if 'U10' in data.data_vars and 'V10' in data.data_vars:
        ff10, dd10 = uv_to_FFDD(data['U10'], data['V10'])

        ff10.attrs = data['U10'].attrs
        dd10.attrs = data['V10'].attrs
        ff10.attrs['description'] = '10m earth rotated wspd'
        ff10.attrs['units'] = 'm s-1'
        dd10.attrs['description'] = '10m earth rotated wdir'
        dd10.attrs['units'] = 'degree'

        data = data.assign({'WSP10': ff10})
        data = data.assign({'DIR10': dd10})

    if 'U' in data.data_vars and 'V' in data.data_vars:
        ff, dd = uv_to_FFDD(data['U'], data['V'])
        ff.attrs = data['U'].attrs
        dd.attrs = data['V'].attrs
        ff.attrs['description'] = 'earth rotated wspd'
        ff.attrs['units'] = 'm s-1'
        dd.attrs['description'] = 'earth rotated wdir'
        dd.attrs['units'] = 'degree'

        data = data.assign({'WSP': ff})
        data = data.assign({'DIR': dd})

    return data


def old_method_to_compare(filename: Union[PosixPath, list], tidx: int, ignore_warn=False) -> xr.Dataset:
    """
    This is the old method I used to read the contents of a wrfout-file.
    This function is here as a reference.
    """
    from netCDF4 import Dataset
    import wrf

    if isinstance(filename, list):
        if not ignore_warn:
            if len(filename) > 3:
                print('Warning! You are potentially trying to read a LOT of data, which may cause python to crash.')
                print('If you want to proceed, call this function again with the argument "ignore_warn=True".')
                return xr.Dataset()

        fid = [Dataset(f, 'r') for f in filename]
    else:
        fid = Dataset(filename, 'r')

    data = xr.Dataset()

    for var in ['U', 'V', 'W', 'Z', 'WSP_WDIR', 'WSP_WDIR10', 'T', 'PT', 'P', 'QV', 'HFX', 'GRDFLX', 'LH', 'PSFC',
                'LU_INDEX', 'HGT']:
        if var == 'WSP_WDIR':

            tmp = wrf.getvar(fid, 'uvmet_wspd_wdir', units="m s-1", timeidx=tidx, squeeze=False)
            data01 = tmp[0][:, :, :, :]
            data02 = tmp[1][:, :, :, :]

            data01.name = 'WSP'
            data01 = data01.drop_vars('wspd_wdir')
            data01.attrs['description'] = 'earth rotated wspd'
            data01.attrs['units'] = 'm s-1'

            data02.name = 'DIR'
            data02 = data02.drop_vars('wspd_wdir')
            data02.attrs['description'] = 'earth rotated wdir'
            data02.attrs['units'] = 'degrees'

            data = data.assign({'WSP': data01, 'DIR': data02})
        elif var == 'WSP_WDIR10':

            tmp = wrf.getvar(fid, 'uvmet10_wspd_wdir', units="m s-1", timeidx=tidx, squeeze=False)
            data01 = tmp[0]
            data01.name = 'WSP10'
            data01 = data01.drop_vars('wspd_wdir')
            data01.attrs['units'] = 'm s-1'
            data02 = tmp[1]
            data02.name = 'DIR10'
            data02 = data02.drop_vars('wspd_wdir')
            data02.attrs['units'] = 'degrees'

            data = data.assign({'WSP10': data01, 'DIR10': data02})

        elif var in ['U', 'V', 'W']:
            data01 = wrf.getvar(fid, var.lower() + 'a', units="m s-1", timeidx=tidx, squeeze=False)
            data = data.assign({var: data01})
        elif var in ['T', 'HFX', 'GRDFLX', 'LH', 'PSFC']:
            data01 = wrf.getvar(fid, var, timeidx=tidx, squeeze=False)
            data = data.assign({var: data01})
        elif var in ['PRES', 'P']:
            data01 = wrf.getvar(fid, 'p', units="Pa", timeidx=tidx, squeeze=False)
            data = data.assign({'P': data01})
        elif var == 'PT':
            data01 = wrf.getvar(fid, 'theta', units="K", timeidx=tidx, squeeze=False)
            data = data.assign({var: data01})
        elif var == 'LU_INDEX':
            data01 = wrf.getvar(fid, 'LU_INDEX', timeidx=0, squeeze=True)
            data = data.assign({var: data01})
        elif var == 'HGT':
            data01 = wrf.getvar(fid, 'ter', units='m', timeidx=0, squeeze=True)
            data = data.assign({var: data01})
        elif var == 'Z':
            data01 = wrf.getvar(fid, 'z', units="m", timeidx=tidx, squeeze=False)
            data = data.assign({var: data01})
        else:
            pass

    return data


class projection:

    def __init__(self, filename: Union[PosixPath, list]):

        # first, get parameters from wrfout-file
        if isinstance(filename, list):
            xa = xr.open_dataset(filename[0], 'r')
        else:
            xa = xr.open_dataset(filename, 'r')

        self.wrf_earth_radius = 6370000

        self.map_proj = xa.attrs.get("MAP_PROJ", None)

        self.stand_lon = xa.attrs.get('STAND_LON', None)
        self.moad_cen_lat = xa.attrs.get('MOAD_CEN_LAT', None)
        self.truelat1 = xa.attrs.get('TRUELAT1', None)
        self.truelat2 = xa.attrs.get('TRUELAT2', None)

        self.dx = xa.attrs.get("DX", None)
        self.dy = xa.attrs.get("DY", None)
        self.pole_lat = xa.attrs.get("POLE_LAT", None)
        self.pole_lon = xa.attrs.get("POLE_LON", None)

        # std_parallels = [map_cls.data.attrs['TRUELAT1'], map_cls.data.attrs['TRUELAT2']]

    # In wrf-python, they have multiple sub-classes and routines for cartopy, basemap and others.
    # I limit myself to the bare minimum, but keep the structure for easy extension in the future.
    # Also, need to check the wrf-python licence to check what code I may re-use...

    def _cf_params(self):
        return None

    def _cartopy(self):
        return None

    def cartopy_xlim(self):
        # do I need this?
        pass

    def cartopy_ylim(self):
        # do I need this?
        pass

    def _calc_extends(self):
        # do I need this?
        pass

    def _cart_extends(self):
        # do I need this?
        pass

    def __repr__(self):
        # do I need this?
        pass

    def _globe(self):
        return crs.Globe(ellipse=None,
                         semimajor_axis=self.wrf_earth_radius,
                         semiminor_axis=self.wrf_earth_radius,
                         nadgrids="@null")

    def cartopy(self):
        return self._cartopy()

    def cf(self):
        return self._cf_params()

    """
    class LambertConformal(Proj):
    class Mercator(Proj):
    class PolarStereographic(Proj)
    class LatLon():
        
    def getproj(self):
    """
