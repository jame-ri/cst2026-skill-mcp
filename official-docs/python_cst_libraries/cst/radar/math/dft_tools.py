# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

"""
Tools for analysis of Fourier Transformed Data
"""

import numpy as np
from scipy.signal import czt


def zero_pad_right(y, Ntotal):
    r"""zero padd y right to length Ntotal

    expected order y[-f],...,y[f]
    """
    if Ntotal <= 0:
        return y
    return np.pad(y, (0, Ntotal - len(y)), mode='constant', constant_values=(0, 0))


def zero_padd(y, N):
    r"""zero padd y by N time len(y) at lower and upper bound, respectively

    expected order y[-f],...,y[f]
    """
    if N == 0:
        return y
    ly = len(y)
    return np.pad(y, (N*ly, N*ly), mode='constant', constant_values=(0, 0))


def axis_extension(f, N):
    r"""linear extent sorted and homogeneous space array f by N time it length at lower and upper bound, respectively"""
    if N == 0:
        return f
    ly = len(f)
    df = f[1] - f[0]
    return np.arange(f[0] - df*N*ly, f[-1] + df*(N*ly+0.5), df)


def calculate_amplitude_corrected_window(awin):
    r"""
    calculates the amplitude corrected window


    Parameters:
    -----------
        awin: np.array((n,) )
            window values

    Returns:
    --------
        corrected_win: float
            the window correction factor
    """
    inverse_factor = np.sum(awin)/len(awin)
    corrected_win = awin / inverse_factor
    return corrected_win


def calculate_power_corrected_window(awin):
    r"""
    calculates the power corrected window

    Parameters:
    -----------
        awin: np.array((n,))
            window values

    Returns:
    --------
        corrected_win: float
            the window correction factor
    """
    a = np.sum(awin)
    factor = len(awin)*np.sum(awin*awin)/(a*a)
    corrected_win = factor*awin
    return corrected_win


def ft_by_chirpz(h, dt, f0, df, f1=None, axis=0):
    r"""
    Calculates the discrete fourier transform

    Parameters:
    -----------
        h: numpy array
            time domain signal of length N
        dt: float
            time step
        f0: float
            start frequency
        df: float
            frequency step
        f1: end frequency


    Returns:
    --------
    tuple: (h, t)
    h: array
        Fourier Transform of h
    f: float
        frequency


    .. math::
        h(f) = \sum_{i=0}^{N-1} e^{-j 2\pi f t_i} h_i
        t_i = i dt



    Calculation of the Fourier Transform by the chirpz transformation.
    The time of the input signal starts at t=0 and ends at t=(N-1)*dt with
    homogeneous time spacing dt. The output signal is sampled starting at f=f0
    with the arbitrary time step df, ending at f=f0 + Tf. The unambiguous range Tf 
    is calculate automatically and only depends on the time spacing of the input
    signal Tf = 1/dt.
    """
    Tp = 1.0/df  # valid range of result
    w = np.exp(-1j*2*np.pi*df*dt)
    a = np.exp(1j*2*np.pi*dt*f0)
    m = int(Tp/dt)
    if f1:
        m = int((f1 - f0)/df)
    h = czt(h, m, w, a, axis=axis)
    len_h = h.shape[axis]
    f = np.linspace(f0, f0 + (len_h - 1)*df, len_h)
    return (h, f)


def ift_by_chirpz(H, df, t0, dt, t1=None, axis=0):
    r"""
    Calculates the inverse discrete fourier transform

    Parameters:
    -----------
        H: numpy array
            frequency domain signal of length N
        df: float
            frequency spacing in Hz
        t0: start time
        dt: time step
        t1: end time

    Returns:
    --------
    tuple: (h, t)
    h: array
        inverse Fourier Transform of H
    t: float
        time


    .. math::
        h(t) = 1/N \sum_{i=0}^{N-1} e^{j 2\pi t f_i} H_i
        f_i = i df



    Calculation of the inverse Fourier Transform by the chirpz transformation.
    The frequency of the input signal starts at f=0 and ends at f=(N-1)*df with
    homogeneous frequency spacing df. The output signal is sampled starting at t=t0
    with the arbitrary time step dt, ending at t=t0 + Tp. The unambiguous range Tp 
    is calculate automatically and only depends on the frequency spacing of the input
    signal Tp = 1/df.
    """
    Tp = 1.0/df  # valid range of result
    w = np.exp(1j*2*np.pi*df*dt)
    a = np.exp(-1j*2*np.pi*df*t0)
    m = 1 + int(Tp/dt)  # non periodic length
    if t1:
        m = int((t1 - t0)/dt)
    h = czt(H, m, w, a, axis=axis)
    h = h/H.shape[axis]
    len_h = h.shape[axis]
    t = np.linspace(t0, t0 + (len_h - 1)*dt, len_h)
    return (h, t)
