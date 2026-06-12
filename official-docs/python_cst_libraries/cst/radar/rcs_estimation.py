# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

import numpy as np
from scipy.signal import windows
from cst.radar.physical_constants import c0, Z0, freqHz_to_k0
from cst.radar.math.dft_tools import ift_by_chirpz, calculate_amplitude_corrected_window


def windowed_amplitude_corrected_signal(input_signal):
    """
    using an amplitude corrected Hann window for accurate peak location and height detection
    """
    hwin = calculate_amplitude_corrected_window(
        windows.hann(len(input_signal)))
    return input_signal*hwin


def rcs_calculation_from_radar_equation(h, dist, lambda0, Gr=1, Gt=1):
    """
    Parameters:
        h: array
            F-parameter in time domain
        dist: float
            distance of object in m
        lambda0: float
            wavelength at center frequency in m
        Gr: float
            antenna gain receiver
        Gt: float
            antenna gain transmitter
    """
    Pr = abs(np.power(h, 2))  # received power
    Pt = 1.0  # transmitted power
    sigma = Pr/Pt*(np.power(4*np.pi, 3))*np.power(dist, 4) / \
        (np.power(lambda0, 2)*Gt*Gr)
    return sigma


def rcs_vs_distance_calculation_from_radar_equation(H, freq_Hz, dist, Gr=1, Gt=1, start_range=0.0):
    """
    Parameters:
        H: array
            F-parameter in frequency domain
        freq_Hz: array
            solver frequency in Hz
        dist: float
            distance of object in m
        lambda0: float
            wavelength at center frequency in m
        Gr: float
            antenna gain receiver
        Gt: float
            antenna gain transmitter
    """
    # automatically calculate sufficiently fine sampling in time domain
    df = freq_Hz[1] - freq_Hz[0]
    fc = 0.5*(freq_Hz[1] + freq_Hz[-1])
    lambda0 = c0/fc
    dt = 0.1/fc
    # window the result
    Hw = windowed_amplitude_corrected_signal(H)
    # calculate time domain response
    t0 = 2*start_range/c0
    ht, t = ift_by_chirpz(Hw, df, t0, dt)
    dist = t*c0/2
    rcs = rcs_calculation_from_radar_equation(ht, dist, lambda0, Gr, Gt)
    return (dist, rcs)


def rcs_vs_distance_calculaton_from_antenna_pattern(H, freq_Hz, tx_field, rx_field, start_range=0.0):
    """
    Parameters:
    -----------
    H: array
        F-parameter in frequency domain
    freq_Hz: array
        solver frequency in Hz
    tx_field: array dim 3
        transmitting antenna farfield E pattern value in direction of object at center frequency
    rx_field: array dim 3
        receiving antenna farfield E pattern value in direction of object at center frequency

    Output:
    -------
    tuple - (dist, rcs)
        dist - distance
        rcs  - rcs parameter
    """
    k0 = freqHz_to_k0*freq_Hz
    g = -H*k0*Z0/(2*np.pi)*np.sqrt(4*np.pi)/np.dot(tx_field, rx_field)
    # automatically calculate sufficiently fine sampling in time domain
    df = freq_Hz[1] - freq_Hz[0]
    fc = 0.5*(freq_Hz[1] + freq_Hz[-1])
    dt = 0.1/fc
    # window the result
    g = windowed_amplitude_corrected_signal(g)
    # calculate time domain response
    t0 = 2*start_range/c0
    G, t = ift_by_chirpz(g, df, t0, dt)
    dist = t*c0/2
    # distance scaling only works with windowing in order to suppress side lobes sufficiently
    # as the signals are "amplified" with dist^4
    dist_pow2 = dist*dist
    return (dist, np.power(dist_pow2*np.abs(G), 2))
