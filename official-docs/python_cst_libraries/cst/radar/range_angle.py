# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

"""This module contains the relevant functions to execute the angle of arrival algorithms
based on covariance matrices and the range tensor.
"""

import numpy as np


def angle_range_map(algorithm, range_tensor, sigma=1e-22):
    """
    Method which executes the spectral algorithm on each range bin given in the range tensor. The resulting tensor
    represents a 2D map of the range-angle distribution of the targets.

    Parameters
    ----------
    algorithm : SpectralAlgorithm object
            SpectralAlgorithm object (carrying specifications and parameters) that is used to calculate the
            (pseudo) spectrum of the angular position of the targets
    range_tensor : 3D array(complex float)
            Range tensor obtained from range tensor calculations, used as input to algorithm
    sigma : float
            Diagonal loading factor for covariance matrix preventing singularities
    Returns
    -------
    2D array
            Tensor containing information on targets' angular and range locations

    """
    Nvir = algorithm.get_number_virtual_channels()  # virtual array
    Nc = range_tensor.shape[0]  # number chirps
    Nr = range_tensor.shape[2]  # number range bins
    #
    # assemble covariance matrix for each range bin
    #
    Rhat = np.zeros((Nvir, Nvir, Nr), dtype=np.complex128)
    sigmaId = sigma*np.identity(Nvir, dtype=np.complex128)
    for ir in range(0, Nr):
        for kc in range(0, Nc):
            Xx = range_tensor[kc, :, ir].reshape((Nvir, 1))
            Rhat[:, :, ir] += np.outer(Xx, Xx.T.conjugate())
        Rhat[:, :, ir] = (1.0/Nc)*Rhat[:, :, ir] + sigmaId
    # execute the angle of arrival algorithm on the covariance matrix of the range bin
    Ntheta = algorithm.get_number_of_angles()
    Zz = np.zeros((Ntheta, Nr), dtype=np.complex128)
    for ir in range(0, Nr):
        Zz[:, ir] = algorithm.execute(Rhat[:, :, ir])
    return Zz


def angle_range_map_limited_range(algorithm, range_tensor, arange, max_range=10, sigma=1e-22):
    """
    Method which executes the spectral algorithm on each range bin given in the range tensor up to the maximum range
    specified as a parameter. The resulting tensor represents a 2D map of the range-angle distribution of the targets.

    Parameters
    ----------
    algorithm : SpectralAlgorithm object
            SpectralAlgorithm object (carrying specifications and parameters) that is used to calculate the
            likelihood of the angular position of the targets
    range_tensor : 3D array(complex float)
            Range tensor obtained from range tensor calculations, used as input to algorithm
    max_range : float
            maximum range up to which the range bins should be considered
    sigma : float
            Diagonal loading factor for covariance matrix preventing singularities

    Returns
    -------
    tuple : (array, 2D array)
            First entry contains new range axis after cutting the range information for ranges higher than max_range.
            Second entry is tensor containing information on targets' angular and range locations.

    """
    new_range = []
    ir_max = 0
    for m in arange:
        if m > max_range:
            break
        new_range.append(m)
        ir_max = ir_max + 1
    Nvir = algorithm.get_number_virtual_channels()  # virtual array
    Nc = range_tensor.shape[0]  # number chirps
    Nr = ir_max  # number range bins
    #
    # assemble correlation matrix for each range bin
    #
    Rhat = np.zeros((Nvir, Nvir, Nr), dtype=np.complex128)
    sigmaId = sigma*np.identity(Nvir, dtype=np.complex128)
    for ir in range(0, Nr):
        for kc in range(0, Nc):
            Xx = range_tensor[kc, :, ir].reshape((Nvir, 1))
            Rhat[:, :, ir] += np.outer(Xx, Xx.T.conjugate())
        Rhat[:, :, ir] = (1.0/Nc)*Rhat[:, :, ir] + sigmaId
    # execute the angle of arrival algorithm on the covariance matrix of the range bin
    Ntheta = algorithm.get_number_of_angles()
    Zz = np.zeros((Ntheta, Nr), dtype=np.complex128)
    for ir in range(0, Nr):
        Zz[:, ir] = algorithm.execute(Rhat[:, :, ir])
    return new_range, Zz


def angle_range_map_limited_range_single_snapshot(algorithm, range_tensor, arange, max_range=10, isnapshot=0):
    """
    Method which executes the spectral algorithm on each range bin given in the range tensor up to the maximum range
    specified as a parameter. The resulting tensor represents a 2D map of the range-angle distribution of the targets.

    Parameters
    ----------
    algorithm : SpectralAlgorithm object
            SpectralAlgorithm object (carrying specifications and parameters) that is used to calculate the
            likelihood of the angular position of the targets
    range_tensor : 3D array(complex float)
            Range tensor obtained from range tensor calculations, used as input to algorithm
    max_range : float
            maximum range up to which the range bins should be considered
    sigma : float
            Diagonal loading factor for covariance matrix preventing singularities

    Returns
    -------
    tuple : (array, 2D array)
            First entry contains new range axis after cutting the range information for ranges higher than max_range.
            Second entry is tensor containing information on targets' angular and range locations.

    """
    new_range = []
    ir_max = 0
    for m in arange:
        if m > max_range:
            break
        new_range.append(m)
        ir_max = ir_max + 1
    Nvir = algorithm.get_number_virtual_channels()  # virtual array
    Nc = range_tensor.shape[0]  # number chirps
    Nr = ir_max  # number range bins
    #
    # assemble correlation matrix for each range bin
    #
    Ntheta = algorithm.get_number_of_angles()
    Zz = np.zeros((Ntheta, Nr), dtype=np.complex128)
    for ir in range(0, Nr):
        Avrg = np.sum(range_tensor[:, :, ir], axis=0)
        Zz[:, ir] = algorithm.execute(Avrg)
    return new_range, Zz


def velocity_angle_range_map_limited_range_single_snapshot(algorithm, range_tensor, arange, max_range=None, isnapshot=0):
    """
    Method which executes the spectral algorithm on each range bin given in the range tensor up to the maximum range
    specified as a parameter. The resulting tensor represents a 2D map of the range-angle distribution of the targets.

    Parameters
    ----------
    algorithm : SpectralAlgorithm object
            SpectralAlgorithm object (carrying specifications and parameters) that is used to calculate the
            likelihood of the angular position of the targets
    range_tensor : 3D array(complex float)
            Range tensor obtained from range tensor calculations, used as input to algorithm
    max_range : float
            maximum range up to which the range bins should be considered
    sigma : float
            Diagonal loading factor for covariance matrix preventing singularities

    Returns
    -------
    tuple : (array, 2D array)
            First entry contains new range axis after cutting the range information for ranges higher than max_range.
            Second entry is tensor containing information on targets' angular and range locations.

    """
    if max_range:
        new_range = []
        ir_max = 0
        for m in arange:
            if m > max_range:
                break
            new_range.append(m)
            ir_max = ir_max + 1
        new_range = np.array(new_range)
    else:
        new_range = arange
        ir_max = arange.shape[0]
    Nvir = algorithm.get_number_virtual_channels()  # virtual array
    Nc = range_tensor.shape[0]  # number chirps
    Nr = ir_max  # number range bins
    #
    # assemble correlation matrix for each range bin
    #
    Nvelocity = Nc
    Ntheta = algorithm.get_number_of_angles()
    Zz = np.zeros((Nvelocity, Ntheta, Nr), dtype=np.complex128)
    for ir in range(0, Nr):
        for ic in range(0, Nc):
            A = range_tensor[ic, :, ir]
            Zz[ic, :, ir] = algorithm.execute(A)
    return new_range, Zz
