#!/usr/bin/env python3

"""
This script plots the WPS/WRF Domains from the namelists.
helper-functions orginiate from https://github.com/lucas-uw/WRF-tools
"""

import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import matplotlib as mpl

from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from cartopy.feature import OCEAN, LAKES, BORDERS, LAND
import cartopy.crs as ccrs
import shapely.geometry as sgeom

import os
from copy import copy
import re
import netCDF4 as nc
import numpy as np


# from wrftamer.domainsetup.domain_from_namelist import lambert_xticks, lambert_yticks_left, calc_wps_domain_info, \
#    reproject_corners, calc_wps_projection_info, check_domain


def get_wps_param_value(wps_file, param_name, noutput, vartype):
    with open(wps_file, 'r') as file:
        for line in file.readlines():
            words = re.split(r'=|\s+|,|\'', line)
            while '' in words:
                words.remove('')
            if param_name in words:
                if noutput == 1:
                    if vartype == 'float':
                        output = float(words[1])
                    elif vartype == 'int':
                        output = int(words[1])
                    else:
                        output = words[1]
                if noutput > 1:
                    if vartype == 'float':
                        output = np.ones((noutput, 1)) * 1.1
                        for i in np.arange(noutput):
                            output[i] = float(words[1 + i])
                    elif vartype == 'int':
                        output = np.ones((noutput, 1))
                        for i in np.arange(noutput):
                            output[i] = int(words[1 + i])
                    else:
                        output = words[1:(1 + noutput)]

    return output


def get_proj_lcc(wps_file):
    ref_lat = get_wps_param_value(wps_file, 'ref_lat', 1, 'float')
    ref_lon = get_wps_param_value(wps_file, 'ref_lon', 1, 'float')
    par_lat1 = get_wps_param_value(wps_file, 'truelat1', 1, 'float')
    par_lat2 = get_wps_param_value(wps_file, 'truelat2', 1, 'float')
    standard_lon = get_wps_param_value(wps_file, 'stand_lon', 1, 'float')

    lccproj = ccrs.LambertConformal(central_longitude=ref_lon, central_latitude=ref_lat,
                                    standard_parallels=(par_lat1, par_lat2),
                                    globe=ccrs.Globe(ellipse=None, semimajor_axis=6370000, semiminor_axis=6370000))
    return lccproj


def calc_corner_point_latlon(center_lat, center_lon, e_we, e_ns, dx, dy, wpsproj, latlonproj, loc):
    center_x, center_y = wpsproj.transform_point(center_lon, center_lat, latlonproj)
    if loc == 'll':
        xpt = center_x - dx * (e_we - 2) / 2.0
        ypt = center_y - dy * (e_ns - 2) / 2.0
    elif loc == 'lr':
        xpt = center_x + dx * (e_we - 2) / 2.0
        ypt = center_y - dy * (e_ns - 2) / 2.0
    elif loc == 'ul':
        xpt = center_x - dx * (e_we - 2) / 2.0
        ypt = center_y + dy * (e_ns - 2) / 2.0
    elif loc == 'ur':
        xpt = center_x + dx * (e_we - 2) / 2.0
        ypt = center_y + dy * (e_ns - 2) / 2.0
    corner_lon, corner_lat = latlonproj.transform_point(xpt, ypt, wpsproj)

    return corner_lon, corner_lat


def calc_center_point_latlon(corner_lat_parent, corner_lon_parent, dx_parent, dy_parent, e_we, e_ns,
                             dx, dy, i, j, wpsproj, latlonproj):
    corner_x_parent, corner_y_parent = wpsproj.transform_point(corner_lon_parent, corner_lat_parent,
                                                               latlonproj)
    center_x_child = corner_x_parent + dx_parent * i + dx * e_we / 2.0
    center_y_child = corner_y_parent + dy_parent * j + dy * e_ns / 2.0
    center_lon_child, center_lat_child = latlonproj.transform_point(center_x_child, center_y_child,
                                                                    wpsproj)

    return center_lon_child, center_lat_child


def calc_wps_domain_info(wps_file):
    ndomain = get_wps_param_value(wps_file, 'max_dom', 1, 'int')
    proj_name = get_wps_param_value(wps_file, 'map_proj', 1, '')

    grid_ratios = get_wps_param_value(wps_file, 'parent_grid_ratio', ndomain, 'int')
    i_parent_start_array = get_wps_param_value(wps_file, 'i_parent_start', ndomain, 'int')
    j_parent_start_array = get_wps_param_value(wps_file, 'j_parent_start', ndomain, 'int')
    e_we_array = get_wps_param_value(wps_file, 'e_we', ndomain, 'int')
    e_ns_array = get_wps_param_value(wps_file, 'e_sn', ndomain, 'int')
    dx_d01 = get_wps_param_value(wps_file, 'dx', 1, 'float')
    dy_d01 = get_wps_param_value(wps_file, 'dy', 1, 'float')
    cen_lat_d01 = get_wps_param_value(wps_file, 'ref_lat', 1, 'float')
    cen_lon_d01 = get_wps_param_value(wps_file, 'ref_lon', 1, 'float')

    center_lat_full = np.zeros((ndomain, 1))
    center_lon_full = np.zeros((ndomain, 1))
    half_size_ns_full = np.zeros((ndomain, 1))
    half_size_we_full = np.zeros((ndomain, 1))
    corner_lat_full = np.zeros((ndomain, 4))  # ll, lr, uf, ur
    corner_lon_full = np.zeros((ndomain, 4))  # ll, lr, uf, ur
    dx_full = np.zeros((ndomain, 1))
    dy_full = np.zeros((ndomain, 1))
    length_x = np.zeros((ndomain, 1))
    length_y = np.zeros((ndomain, 1))

    # get WPS projection info
    # LCC
    if proj_name == 'lambert':
        wpsproj = get_proj_lcc(wps_file)

    # Geodetic, for lat/lon projection
    latlonproj = ccrs.Geodetic()  # ccrs.Globe(ellipse=None, semimajor_axis=6370000, semiminor_axis=6370000))

    # d01
    dx_full[0] = dx_d01
    dy_full[0] = dy_d01
    center_lat_full[0] = cen_lat_d01
    center_lon_full[0] = cen_lon_d01
    if ndomain > 1:
        e_we = int(e_we_array[0])
        e_ns = int(e_ns_array[0])
    else:
        e_we = e_we_array
        e_ns = e_ns_array
        length_x[0] = dx_full[0] * e_we_array
        length_y[0] = dy_full[0] * e_ns_array

    corner_lon_full[0, 0], corner_lat_full[0, 0] = calc_corner_point_latlon(float(center_lat_full[0]),
                                                                            float(center_lon_full[0]),
                                                                            e_we, e_ns,
                                                                            float(dx_full[0]), float(dy_full[0]),
                                                                            wpsproj, latlonproj,
                                                                            'll')
    corner_lon_full[0, 1], corner_lat_full[0, 1] = calc_corner_point_latlon(center_lat_full[0],
                                                                            center_lon_full[0],
                                                                            e_we, e_ns,
                                                                            dx_full[0], dy_full[0],
                                                                            wpsproj, latlonproj,
                                                                            'lr')
    corner_lon_full[0, 2], corner_lat_full[0, 2] = calc_corner_point_latlon(center_lat_full[0],
                                                                            center_lon_full[0],
                                                                            e_we, e_ns,
                                                                            dx_full[0], dy_full[0],
                                                                            wpsproj, latlonproj,
                                                                            'ul')
    corner_lon_full[0, 3], corner_lat_full[0, 3] = calc_corner_point_latlon(center_lat_full[0],
                                                                            center_lon_full[0],
                                                                            e_we, e_ns,
                                                                            dx_full[0], dy_full[0],
                                                                            wpsproj, latlonproj,
                                                                            'ur')

    if ndomain > 1:
        for i in np.arange(1, ndomain):
            dx_full[i] = dx_full[i - 1] / float(grid_ratios[i])
            dy_full[i] = dy_full[i - 1] / float(grid_ratios[i])
            length_x[i] = dx_full[i] * e_we_array[i]
            length_y[i] = dy_full[i] * e_ns_array[i]
            center_lon_full[i], center_lat_full[i] = calc_center_point_latlon(
                corner_lat_full[i - 1, 0], corner_lon_full[i - 1, 0],
                dx_full[i - 1], dy_full[i - 1],
                e_we_array[i], e_ns_array[i],
                dx_full[i], dy_full[i],
                i_parent_start_array[i], j_parent_start_array[i],
                wpsproj, latlonproj)
            corner_lon_full[i, 0], corner_lat_full[i, 0] = calc_corner_point_latlon(
                center_lat_full[i], center_lon_full[i],
                e_we_array[i], e_ns_array[i],
                dx_full[i], dy_full[i],
                wpsproj, latlonproj, 'll')
            corner_lon_full[i, 1], corner_lat_full[i, 1] = calc_corner_point_latlon(
                center_lat_full[i], center_lon_full[i],
                e_we_array[i], e_ns_array[i],
                dx_full[i], dy_full[i],
                wpsproj, latlonproj, 'lr')
            corner_lon_full[i, 2], corner_lat_full[i, 2] = calc_corner_point_latlon(
                center_lat_full[i], center_lon_full[i],
                e_we_array[i], e_ns_array[i],
                dx_full[i], dy_full[i],
                wpsproj, latlonproj, 'ul')
            corner_lon_full[i, 3], corner_lat_full[i, 3] = calc_corner_point_latlon(
                center_lat_full[i], center_lon_full[i],
                e_we_array[i], e_ns_array[i],
                dx_full[i], dy_full[i],
                wpsproj, latlonproj, 'ur')

    return wpsproj, latlonproj, corner_lat_full, corner_lon_full, length_x, length_y


def reproject_corners(corner_lons, corner_lats, wpsproj, latlonproj):
    corner_x = np.zeros((4, 1))
    corner_y = np.zeros((4, 1))
    corner_x[0], corner_y[0] = wpsproj.transform_point(corner_lons[0], corner_lats[0], latlonproj)
    corner_x[1], corner_y[1] = wpsproj.transform_point(corner_lons[1], corner_lats[1], latlonproj)
    corner_x[2], corner_y[2] = wpsproj.transform_point(corner_lons[2], corner_lats[2], latlonproj)
    corner_x[3], corner_y[3] = wpsproj.transform_point(corner_lons[3], corner_lats[3], latlonproj)

    return corner_x, corner_y


# all these functions are necessary only when LCC projection is used.
def find_side(ls, side):
    """
    Given a shapely LineString which is assumed to be rectangular, return the
    line corresponding to a given side of the rectangle.

    """
    minx, miny, maxx, maxy = ls.bounds
    points = {'left': [(minx, miny), (minx, maxy)],
              'right': [(maxx, miny), (maxx, maxy)],
              'bottom': [(minx, miny), (maxx, miny)],
              'top': [(minx, maxy), (maxx, maxy)], }
    return sgeom.LineString(points[side])


def lambert_xticks(ax, ticks, size):
    """Draw ticks on the bottom x-axis of a Lambert Conformal projection."""
    te = lambda xy: xy[0]
    lc = lambda t, n, b: np.vstack((np.zeros(n) + t, np.linspace(b[2], b[3], n))).T
    xticks, xticklabels = _lambert_ticks(ax, ticks, 'bottom', lc, te)
    ax.xaxis.tick_bottom()
    ax.set_xticks(xticks)
    ax.set_xticklabels([ax.xaxis.get_major_formatter()(xtick) for xtick in xticklabels], size=size)


def lambert_yticks_left(ax, ticks, size):
    """Draw ricks on the left y-axis of a Lamber Conformal projection."""
    te = lambda xy: xy[1]
    lc = lambda t, n, b: np.vstack((np.linspace(b[0], b[1], n), np.zeros(n) + t)).T
    yticks, yticklabels = _lambert_ticks(ax, ticks, 'left', lc, te)
    ax.yaxis.tick_left()
    ax.set_yticks(yticks)
    ax.set_yticklabels([ax.yaxis.get_major_formatter()(ytick) for ytick in yticklabels], size=size)


def lambert_yticks_right(ax, ticks, size):
    """Draw ricks on the left y-axis of a Lamber Conformal projection."""
    te = lambda xy: xy[1]
    lc = lambda t, n, b: np.vstack((np.linspace(b[0], b[1], n), np.zeros(n) + t)).T
    yticks, yticklabels = _lambert_ticks(ax, ticks, 'right', lc, te)
    ax.yaxis.tick_right()
    ax.set_yticks(yticks)
    ax.set_yticklabels([ax.yaxis.get_major_formatter()(ytick) for ytick in yticklabels], size=size)


def _lambert_ticks(ax, ticks, tick_location, line_constructor, tick_extractor):
    """Get the tick locations and labels for an axis of a Lambert Conformal projection."""
    outline_patch = sgeom.LineString(ax.outline_patch.get_path().vertices.tolist())
    axis = find_side(outline_patch, tick_location)
    n_steps = 30
    extent = ax.get_extent(ccrs.PlateCarree())
    _ticks = []
    for t in ticks:
        xy = line_constructor(t, n_steps, extent)
        proj_xyz = ax.projection.transform_points(ccrs.Geodetic(), xy[:, 0], xy[:, 1])
        xyt = proj_xyz[..., :2]
        ls = sgeom.LineString(xyt.tolist())
        locs = axis.intersection(ls)
        if not locs:
            tick = [None]
        else:
            tick = tick_extractor(locs.xy)
        _ticks.append(tick[0])
    # Remove ticks that aren't visible:
    ticklabels = copy(ticks)
    while True:
        try:
            index = _ticks.index(None)
        except ValueError:
            break
        _ticks.pop(index)
        ticklabels.pop(index)
    return _ticks, ticklabels


def location_windpark(file):
    list_of_lons = []
    list_of_lats = []
    with open(file) as f:
        for line in f:
            inner_list = [elt.strip() for elt in line.split(';')]
            list_of_lons.append(np.float(inner_list[2]))
            list_of_lats.append(np.float(inner_list[1]))

    return list_of_lats, list_of_lons


def calc_wps_projection_info(wps_file):
    cen_lat_d01 = get_wps_param_value(wps_file, 'ref_lat', 1, 'float')
    cen_lon_d01 = get_wps_param_value(wps_file, 'ref_lon', 1, 'float')
    truelat1_d01 = get_wps_param_value(wps_file, 'truelat1', 1, 'float')
    truelat2_d01 = get_wps_param_value(wps_file, 'truelat2', 1, 'float')
    stand_lon_d01 = get_wps_param_value(wps_file, 'stand_lon', 1, 'float')

    return cen_lon_d01, cen_lat_d01, truelat1_d01, truelat2_d01, stand_lon_d01


def check_domain(wps_file):
    """
    Helper function to find problems in the namelist.
    If these parameters are not correct, WPS will through an MPI error.
    """
    ndomain = get_wps_param_value(wps_file, 'max_dom', 1, 'int')
    i_parent_start_array = get_wps_param_value(wps_file, 'i_parent_start', ndomain, 'int')
    j_parent_start_array = get_wps_param_value(wps_file, 'j_parent_start', ndomain, 'int')
    e_we = get_wps_param_value(wps_file, 'e_we', ndomain, 'int')
    e_sn = get_wps_param_value(wps_file, 'e_sn', ndomain, 'int')
    parent_grid_ratio = get_wps_param_value(wps_file, 'parent_grid_ratio', ndomain, 'int')
    parent_id = get_wps_param_value(wps_file, 'parent_id', ndomain, 'int')

    if ndomain > 1:
        for doms in range(1, ndomain):
            # check whether domains are far enough from each other
            pointwe = (e_we[doms] - 1.) / parent_grid_ratio[doms]
            pointsn = (e_sn[doms] - 1.) / parent_grid_ratio[doms]
            gridwe = e_we[int(parent_id[doms]) - 1] - (pointwe + i_parent_start_array[doms])
            gridsn = e_sn[int(parent_id[doms]) - 1] - (pointsn + j_parent_start_array[doms])
            if i_parent_start_array[doms] < 5:
                raise ValueError(
                    f"Western edge of d{doms} is less than 5 points away from mother domain or outside mother domain")
            if j_parent_start_array[doms] < 5:
                raise ValueError(
                    f"Southern edge of d{doms} is less than 5 points away from mother domain or outside mother domain")
            if gridwe < 5:
                raise ValueError(
                    f"Easter edge of d{doms} is less than 5 points away from mother domain or outside mother domain")
            if gridsn < 5:
                raise ValueError(
                    f"Northern edge of d{doms} is less than 5 points away from mother domain or outside mother domain")

            # check whether domains are fully nested in mother domain
            mod_we = (e_we[doms] - 1.) % parent_grid_ratio[doms]
            mod_sn = (e_sn[doms] - 1.) % parent_grid_ratio[doms]
            if mod_we != 0:
                raise ValueError(
                    f"D{doms} does not have a multiple (X-1) number of  D{int(parent_id[doms]) - 1} gridpoints. Stopping Program!")
            if mod_sn != 0:
                raise ValueError(
                    f"D{doms} does not have a multiple (X-1) number of  D{int(parent_id[doms]) - 1} gridpoints.Stopping Program!")
    return True


def plot_wrf_domains_namelist(infile, geodir, use_dem, hires, plotfile):
    # topographic dataset
    etopo1file = geodir + '/etopo1.nc'
    rootgroup = nc.Dataset(etopo1file, 'r', format='NETCDF4')
    dem = rootgroup.variables['Band1'][:]
    dem_lat = rootgroup.variables['lat'][:]
    dem_lon = rootgroup.variables['lon'][:]
    rootgroup.close()
    dem_lons, dem_lats = np.meshgrid(dem_lon, dem_lat)

    dem = dem.clip(0, np.inf)

    # quality check, whether data points are correct:
    if check_domain(infile):
        wpsproj, latlonproj, corner_lat_full, corner_lon_full, length_x, length_y = calc_wps_domain_info(infile)

        scale = '50m'
        fig1 = plt.figure(figsize=(10, 8))
        ax1 = plt.axes(projection=wpsproj)
        if use_dem:
            ax1.pcolormesh(dem_lons, dem_lats, dem, cmap='terrain', vmin=10, vmax=1000, alpha=1,
                           transform=ccrs.PlateCarree(globe=GLOBE))
        else:
            ax1.add_feature(LAND.with_scale(scale))

        ax1.coastlines(scale, linewidth=0.8)
        ax1.add_feature(OCEAN.with_scale(scale))
        ax1.add_feature(LAKES.with_scale(scale))
        ax1.add_feature(BORDERS.with_scale(scale), edgecolor='k', facecolor='None', lw=0.5)

        font0 = FontProperties()
        font0.set_weight('bold')

        for no_corners in range(len(corner_lon_full[:, 0])):
            print(no_corners)

            corner_x, corner_y = reproject_corners(corner_lon_full[no_corners, :], corner_lat_full[no_corners, :],
                                                   wpsproj,
                                                   latlonproj)
            if no_corners == 0:
                ax1.add_patch(mpl.patches.Rectangle((corner_x[0], corner_y[0]), length_x[0], length_y[0],
                                                    fill=None, lw=3, edgecolor='white', zorder=10))
                ax1.text(corner_x[0] + length_x[0] * 0.05, corner_y[0] + length_y[0] * 0.9, f'D{no_corners + 1}',
                         fontproperties=font0, size=15, color='white', zorder=10)
                ax1.set_xlim([corner_x[0] - length_x[0] / 15, corner_x[3] + length_x[0] / 15])
                ax1.set_ylim([corner_y[0] - length_y[0] / 15, corner_y[3] + length_y[0] / 15])
            elif no_corners == 1:
                ax1.add_patch(mpl.patches.Rectangle((corner_x[0], corner_y[0]), length_x[1], length_y[1],
                                                    fill=None, lw=3, edgecolor='gold', zorder=10))
                ax1.text(corner_x[0] + length_x[1] * 0.05, corner_y[0] + length_y[1] * 1.1, f'D{no_corners + 1}',
                         fontproperties=font0, size=15, color='gold', zorder=10)
            elif no_corners == 2:
                ax1.add_patch(mpl.patches.Rectangle((corner_x[0], corner_y[0]), length_x[2], length_y[2],
                                                    fill=None, lw=3, edgecolor='red', zorder=10))
                ax1.text(corner_x[0] + length_x[2] * 0.1, corner_y[0] + length_y[2] * 0.8, f'D{no_corners + 1}',
                         fontproperties=font0, size=15, color='red', zorder=10)
            else:
                print("Cannot plot more than 3 boxes. Please define more")

        fig1.canvas.draw()

        ax1.scatter(6.6, 54.01, marker='o', c='g', transform=ccrs.PlateCarree())
        xticks = list(np.arange(0, 20, 1))
        yticks = list(np.arange(0, 90, 1))
        ax1.gridlines(xlocs=xticks, ylocs=yticks)
        ax1.xaxis.set_major_formatter(LONGITUDE_FORMATTER)
        ax1.yaxis.set_major_formatter(LATITUDE_FORMATTER)
        lambert_xticks(ax1, xticks, 14)
        lambert_yticks_left(ax1, yticks, 14)

        ax1.set_title('WRF domains', size=20)

        if use_dem:
            cbar_ax = fig1.add_axes([0.92, 0.2, 0.02, 0.6])
            cb1 = mpl.colorbar.ColorbarBase(cbar_ax, cmap='terrain', ticks=[np.arange(0, 1.01, 0.25)],
                                            orientation='vertical')
            cb1.set_ticks(np.arange(0, 1.01, 0.25))
            cb1.set_ticklabels(['0', '200', '400', '600', '800'])
            cbar_ax.tick_params(labelsize=12)
            cbar_ax.text(1.9, -0.01, ' m', size=12)

        if plotfile:
            plt.savefig(os.path.dirname(indir) + '/../plot/' + plotfile, dpi=300)
        else:
            plt.show()


if __name__ == '__main__':
    plot_wrf_domains_namelist()
