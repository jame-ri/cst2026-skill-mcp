# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

# Copyright 1998-2023 Dassault Systemes Deutschland GmbH.

""" This module contains routines for plotting range-angle and range-doppler maps. """

from numpy import pi, meshgrid
import matplotlib.pyplot as plt
from matplotlib import cm
import matplotlib.colors as colors


def visualize_map(X, Y, Z, xname='range m', yname='velocity m/s', log_scale=False):
    """
    Plot 2D heat map of spectrum returned by radar post-processing algorithm (i.e MVDR, MUSICS etc.)

    Parameters
    ----------
    X : array(float)
            grid positions along first axis
    Y : array(float)
            grid positions along second axis
    Z : 2D array(float)
            output of radar algorithm on two-dimensional scan grid
    xname : string
            label on x-axis
    yname : string
            label on y-axis
    log_scale : bool
            Choose if log-scale should be used in plot. Log scale used if "True", linear scale if "False"
    """
    if log_scale:
        plt.pcolormesh(X, Y, Z, norm=colors.LogNorm(
            vmin=1e-8, vmax=Z.max()), cmap='PuBu_r')
    else:
        plt.pcolormesh(X, Y, Z)
    plt.xlabel(xname)
    plt.ylabel(yname)
    # plt.xlim(0, X.max())
    plt.xlim(X.min(), X.max())
    plt.ylim(Y.min(), Y.max())
    plt.colorbar()
    # plt.show()


def visualize_map3d(X, Y, Z, xlabel='range', ylabel='angle', showPlotImmediately=True):
    """
    Plot 3D surface plot of spectrum returned by radar post-processing algorithm (i.e MVDR, MUSICS etc.)

    Parameters
    ----------
    X : array(float)
            grid positions along first axis
    Y : array(float)
            grid positions along second axis
    Z : 2D array(float)
            output of radar algorithm on two-dimensional scan grid
    """
    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    fig.set_figheight(10)
    fig.set_figwidth(10)
    ax.plot_surface(X, Y, Z, cmap=cm.coolwarm, linewidth=0, antialiased=False)
    ax.set_xlim(0, X.max())
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    if showPlotImmediately:
        plt.show()


def map3d(X, Y, Z):
    """
    Returns plt and axis for 3D surface plot of spectrum returned by radar post-processing algorithm (i.e MVDR, MUSICS etc.)

    Parameters
    ----------
    X : array(float)
            grid positions along first axis
    Y : array(float)
            grid positions along second axis
    Z : 2D array(float)
            output of radar algorithm on two-dimensional scan grid
    """
    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    fig.set_figheight(10)
    fig.set_figwidth(10)
    ax.plot_surface(X, Y, Z, cmap=cm.coolwarm, linewidth=0,
                    antialiased=False, rstride=1, cstride=1)
    ax.set_xlim(0, X.max())
    return plt, ax


def visualize_map_polar(ranges, angles, values, angle_in_deg=True):
    """
    Plot 2D heat map of spectrum returned by radar post-processing algorithm (i.e MVDR, MUSICS etc.)

    Parameters
    ----------
    ranges : array(float)
            grid positions along radial axis
    angles : array(float)
            grid positions along angle axis in radians
    values : 2D array(float)
            output of radar algorithm on two-dimensional scan grid
    angle_in_deg : bool
            Choose if angle should be displayed in degrees pr in radians in plot.
            Degrees used if "True", radians if "False"
    """
    if (angle_in_deg):
        angles = 2*pi/360*angles  # convert to radian
    # Using linspace so that the endpoint of 360 is included
    rm, thetam = meshgrid(ranges, angles)
    fig, ax = plt.subplots(subplot_kw=dict(projection='polar'))
    ax.set_theta_direction(-1)  # theta increases in clockwise direction
    ax.set_theta_offset(pi / 2.0)
    ax.set_thetalim(angles.min(), angles.max())
    contourf_ = ax.contourf(thetam, rm, values, levels=500, extend='max')
    fig.colorbar(contourf_)
    plt.title("RADAR Demo")
    plt.show()
