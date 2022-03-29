import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import cartopy.crs as ccrs
from cartopy.feature import NaturalEarthFeature
from wrf import (to_np, get_basemap, latlon_coords, get_cartopy, cartopy_xlim, cartopy_ylim)
import pandas as pd
import xarray as xr
import hvplot.pandas
import hvplot.xarray


def basic_infos(data, **kwargs):
    descr = data.description
    unit = data.units
    ml = data.model_level

    if 'title_str' in kwargs:
        title_str = kwargs['title_str']
    else:
        if unit is None or unit == '':
            unit_str = ''
        else:
            unit_str = f' ({unit})'
        if ml is None:
            ml_str = ''
        else:
            ml_str = f' at model level {ml}'

        title_str = f'{descr}{unit_str}{ml_str}'

    if 'size_factor' in kwargs:
        factor = kwargs['size_factor']
    else:
        factor = 1.5

    return title_str, factor


def Map_Basemap(data: xr.DataArray, hgt: xr.DataArray, ivg: xr.DataArray, vmin, vmax, cmap, myticks,
                points_to_mark: pd.DataFrame, pcmesh=False, add_topo=False, **kwargs):
    var = data.name

    if 'resolution' in kwargs:
        resolution = kwargs['resolution']
    else:
        resolution = 'h'
        # resolution 'h' is a good compromise between speed and qualtiy.

    title_str, factor = basic_infos(data, **kwargs)

    fig = plt.figure(num=None, figsize=(5.5 * factor, 4.5 * factor), facecolor='w', edgecolor='k')

    lats, lons = latlon_coords(hgt)

    if 'bm' in kwargs.keys():
        bm = kwargs['bm']
    else:
        bm = get_basemap(hgt, resolution=resolution)

    x, y = bm(to_np(lons), to_np(lats))
    bm.drawcoastlines(linewidth=0.25)
    bm.drawstates(linewidth=0.25)
    bm.drawcountries(linewidth=0.25)

    if pcmesh:
        bm.pcolormesh(x, y, to_np(data), vmin=vmin, vmax=vmax, cmap=cmap)
    else:
        bm.contourf(x, y, to_np(data), 25, vmin=vmin, vmax=vmax, cmap=cmap)

    # Colorbar
    if var != 'LU_INDEX':
        bm.colorbar(location='right', ticks=myticks)
    else:
        names = ['Urban', 'Forest', 'Other']
        bm.clim(vmin - 0.5, vmax + 0.5)  # works?
        formatter = plt.FuncFormatter(lambda val, loc: names[val - 1])
        bm.colorbar(ticks=myticks, format=formatter)

    # Topography ovverlay.
    if var != 'HGT' and add_topo:
        # Add topography
        hlines = np.arange(0, 1050, 50)
        bm.contour(x, y, to_np(hgt), levels=hlines, colors='grey', alpha=0.5)

    # Marking the position of points of interest
    for index in points_to_mark.index:
        # one could add different colors and styles into the dict points_to_mark
        x1, y1 = bm(to_np(points_to_mark.lon[index]), to_np(points_to_mark.lat[index]))
        bm.plot(x1, y1, '+', ms=10, mew=2, color='k')

    # Ivg as hatches
    bm.contourf(x, y, to_np(ivg), hatches=['.'], colors='none')

    # Gridlines
    clat = np.floor(lats.values.min()), np.ceil(lats.values.max())
    clon = np.floor(lons.values.min()), np.ceil(lons.values.max())
    dlon = 0.5
    dlat = 0.25

    parallels = np.arange(clat[0], clat[1], dlat)
    meridians = np.arange(clon[0], clon[1], dlon)

    bm.drawparallels(parallels, labels=[True, False, True, False])
    bm.drawmeridians(meridians, labels=[True, False, False, True])

    # Title
    plt.title(title_str)

    return fig


def Map_Cartopy(data: xr.DataArray, hgt: xr.DataArray, ivg: xr.DataArray, vmin, vmax, cmap,
                myticks, points_to_mark: pd.DataFrame, pcmesh=False, add_topo=False, **kwargs):
    lat = data.XLAT
    lon = data.XLONG
    var = data.name

    mpl.rcParams.update({'font.size': 15})

    title_str, factor = basic_infos(data, **kwargs)

    fig = plt.figure(num=None, figsize=(5.5 * factor, 4.5 * factor), facecolor='w', edgecolor='k')

    cart_proj = get_cartopy(hgt)
    ax = plt.axes(projection=cart_proj)

    states = NaturalEarthFeature(category="cultural", scale="50m",
                                 facecolor="none", name="admin_0_countries")  # admin_1_states_provinces_shp
    ax.add_feature(states, linewidth=0.5, edgecolor="black")
    ax.coastlines('50m', linewidth=0.8)

    if pcmesh:
        cs = plt.pcolormesh(to_np(lon), to_np(lat), to_np(data), vmin=vmin, vmax=vmax,
                            cmap=cmap, transform=ccrs.PlateCarree())
    else:
        cs = plt.contourf(to_np(lon), to_np(lat), to_np(data), 25, vmin=vmin, vmax=vmax,
                          cmap=cmap, transform=ccrs.PlateCarree())

    # Colorbar
    if var != 'LU_INDEX':
        plt.clim(vmin, vmax)
        plt.colorbar(cs, ax=ax, orientation="vertical", pad=.05, ticks=myticks)
    else:
        names = ['Urban', 'Forest', 'Other']
        plt.clim(vmin - 0.5, vmax + 0.5)
        formatter = plt.FuncFormatter(lambda val, loc: names[val - 1])
        plt.colorbar(ticks=myticks, format=formatter)

    # Topography overlay.
    if var != 'HGT' and add_topo:
        # Add topography
        hlines = np.arange(0, 1050, 50)
        plt.contour(to_np(lon), to_np(lat), to_np(hgt), levels=hlines, colors='grey', transform=ccrs.PlateCarree(),
                    alpha=0.5)

    # add ivg as hatch
    plt.contourf(to_np(lon), to_np(lat), to_np(ivg), hatches=['.'], colors='none', transform=ccrs.PlateCarree())

    # Marking the position of points of interest
    for index in points_to_mark.index:
        plt.plot(to_np(points_to_mark.lon[index]), to_np(points_to_mark.lat[index]), '+', ms=10, mew=2, color='k',
                 transform=ccrs.PlateCarree())

    # Set the map bounds
    ax.set_xlim(cartopy_xlim(hgt))
    ax.set_ylim(cartopy_ylim(hgt))

    gl = ax.gridlines(transform=ccrs.PlateCarree(), draw_labels=True, linewidth=1, x_inline=False, y_inline=False,
                      ls='--')

    gl.top_labels = False
    gl.right_labels = False
    plt.title(title_str)

    return fig


def Map_hvplots(data: xr.DataArray, vmin, vmax, cmap, points_to_mark: pd.DataFrame, ):
    xlim = np.min(data.XLONG.values), np.max(data.XLONG.values)
    ylim = np.min(data.XLAT.values), np.max(data.XLAT.values)
    clim = (vmin, vmax)

    # TODO: fix hvplot for maps. Make projections work.
    #  -> Projekt for Moritz. I am almost there.

    """
    # This command no longer works with the current version of the packages. 
    # I need a major cleanup, find a workaround and/or change the packages.
    # Affected packages are most likely shapely, cartopy and maybe others.
    """

    # Problem: hvplots cannot deal with latex as matplotlib can. Solution:
    # Translate units (back again :/ )
    # I may want two kind of units or a general translator.
    unit_sty = dict()
    unit_sty['N/A'] = 'N/A'
    unit_sty['m'] = 'm'
    unit_sty['m s$^{-1}$'] = 'm/s'
    unit_sty['Pa'] = 'Pa'
    unit_sty['kg kg$^{-1}$'] = 'kg / kg'
    unit_sty['K'] = 'K'
    unit_sty['W m$^{-2}$'] = 'W/s^2'

    new_units = unit_sty[data.units]

    mycrs = ccrs.LambertConformal(central_longitude=6.5, central_latitude=54.0099983215332)

    figure = data.hvplot.contourf(
        x='XLONG', y='XLAT', projection=mycrs,
        xlim=xlim, ylim=ylim, clim=clim, frame_width=600, cmap=cmap, levels=25,
        coastline='10m', geo=True, xlabel='lon (°)', ylabel='lat (°)',
        title=data.description + ' (' + data.units + ')'
    )

    if 'lat' in points_to_mark:
        figure = figure*points_to_mark.hvplot.scatter(x='lon', y='lat', frame_width=600)

    return figure
