# Copyright 1998-2023 Dassault Systemes Deutschland GmbH.

""" This module specifies useful physical constants and conversion factors. """

from math import pi
from math import sqrt

""" Electromagnetic Constants SI Units """
mu0 = 4*pi*1E-7  # vacuum permeability
c0 = 299792458  # speed of light in meters per second
eps0 = 1.0/(c0*c0*mu0)  # vacuum permittivity
Z0 = sqrt(mu0/eps0)  # free space impedance
Y0 = 1.0/Z0  # free space admittance

""" Conversion Factors """
freqHz_to_k0 = 2*pi/c0  # convert frequency to wave number k0 in vacuum
