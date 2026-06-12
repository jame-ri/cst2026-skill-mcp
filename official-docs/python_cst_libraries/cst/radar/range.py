# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

""" This module contains algorithms for calculating the range map. """


import numpy as np
import scipy
from scipy.fftpack import fft, ifft, fftfreq, fftshift, ifftshift
import scipy.signal.windows as windows
from cst.radar.physical_constants import c0
# fmcw
from scipy.signal import fftconvolve, convolve
from scipy.interpolate import interp1d
from cst.radar.fmcw_radar import FMCWRadar, distance_from_beat_frequency, uchirp_complex_centered
from cst.radar.math.dft_tools import ift_by_chirpz, zero_padd, calculate_amplitude_corrected_window, axis_extension, zero_pad_right


import typing
import numpy.typing as npt
import inspect
import os
import pathlib
import matplotlib.pyplot as plt
from functools import partial


def apply_range_transformation(channel_tensor, range_transformation):
    """transform the frequency dimension of the channel_tensor into a range dimension

        Parameters
        ----------
        channel_tensor : ChannelTensor object
                channel tensor carrying the information and correlatons of the received signal
        range_transformation: callable object, function
                performs the 1d range transformation

        Returns
        -------
        tuple : (array, 3D array)
            first array contains range axis, second array contains range tensor[isweep, ichannel, irange]

    """
    # assume equispaced frequency points !!!
    f = channel_tensor.get_frequencies()
    #
    Nbins = range_transformation.get_number_bins()
    ranges = np.zeros(range_transformation.get_number_bins())
    tensor = channel_tensor.get_tensor()
    range_tensor = np.zeros((tensor.shape[0],
                             tensor.shape[1],
                             Nbins),
                            dtype=np.complex128)
    for isw in range(0, tensor.shape[0]):  # sweeps
        for ic in range(0, tensor.shape[1]):  # channels
            F = tensor[isw, ic, :]
            ranges, range_tensor[isw, ic, :] = range_transformation(f, F)
    return (ranges, range_tensor)


class PulsedRadarRangeEstimator:
    def __init__(self):
        # default settings
        self.min_range = 0
        self.max_range = np.finfo(np.float64).max
        self.number_bins = 1024
        self.window_function = windows.hann
        self.window_amplitude_correction = True

    def get_min_range(self):
        return self.min_range

    def get_max_range(self):
        return self.max_range

    def get_number_bins(self):
        return self.number_bins

    def get_window_function(self):
        return self.window_function

    def get_amplitude_correction(self):
        return self.get_amplitude_correction

    def set_min_range(self, min_range: float):
        self.min_range = min_range

    def set_max_range(self, max_range: float):
        self.max_range = max_range

    def set_window_function(self, window_function: typing.Callable[[int], npt.ArrayLike]):
        self.window_function = window_function

    def set_window_correction_factor(self, amplitude_correction: bool):
        self.window_amplitude_correction = amplitude_correction

    def set_number_range_bins(self, number_range_bins: int):
        self.number_bins = number_range_bins

    def __call__(self, frequencies, Fpara):
        """calculate the range map for a given set of F-parameters by an windowed impulse

            Parameters
            ----------
            frequencies : array(float)
                frequencies for F-parameters, expect a homogeneous spacing
            Fparameters : array(complex)
                F-parameters, same order as frequencies

            Returns
            -------
            tuple : (array, array)
                first array contains range axis, second array contains information to fill range tensor for specific
                sweep and specific channel
        """
        # ensure odd number of samples
        NfreqA = len(Fpara)
        NfreqA = NfreqA if np.mod(NfreqA, 2) != 0 else NfreqA - 1
        frequencies = frequencies[0:NfreqA]
        Fpara = Fpara[0:NfreqA]
        # center frequency
        imid = int(np.floor(NfreqA/2))
        f_asolver_mid = frequencies[imid]
        # demodulate spectrum by f_asolver_mid
        frequencies = frequencies - f_asolver_mid
        # windowing
        if self.window_function:
            wndw = self.window_function(len(Fpara))
        else:
            wndw = np.ones(len(Fpara))
        if self.window_amplitude_correction:
            wndw = calculate_amplitude_corrected_window(wndw)
        Fpara = wndw*Fpara
        df = frequencies[1] - frequencies[0]
        dt = 2*self.max_range/c0/4096
        ht, t_asolver = ift_by_chirpz(Fpara, df, 0, dt)
        range = c0*t_asolver/2
        # limit range to radar range
        brange = (range >= self.min_range) & (range <= self.max_range)
        range = range[brange]
        ht = ht[brange]
        t = t_asolver[brange]
        # binning by integration
        filter_size = int(np.ceil(len(ht)/self.number_bins))
        filter_size = filter_size + \
            1 if np.mod(
                filter_size, 2) == 0 else filter_size  # ensure odd number
        ht_conv = np.convolve(np.ones(filter_size)/filter_size,
                              ht, mode='valid')  # integration by convolution
        start = int(filter_size/2)  # offset
        t_conv = t[start:len(ht_conv)+start]  # shifted time, for mode='valid'
        # restrict to strided array with required data
        ht_conv = ht_conv[0:-1:filter_size]
        t_conv = t_conv[0:-1:filter_size]
        # ensure exact Nbins data size
        # linear interpolate to bin positions
        range_bins = np.linspace(
            self.min_range, self.max_range, self.number_bins)
        range_conv = c0*t_conv/2
        ht_binned = np.interp(range_bins, range_conv, ht_conv)
        return (range_bins, ht_binned)


class FMCWRadarRangeEstimator:
    def __init__(self, fmcw_radar):
        # default settings
        self.fmcw_radar = fmcw_radar
        self.min_range = 0
        self.max_range = np.finfo(np.float64).max
        self.number_bins = 1024
        self.window_function = windows.hann
        self.window_amplitude_correction = True
        self.raw_output = False

    def get_raw_output(self):
        return self.raw_output

    def get_min_range(self):
        return self.min_range

    def get_max_range(self):
        return self.max_range

    def get_number_bins(self):
        return self.number_bins

    def get_window_function(self):
        return self.window_function

    def get_amplitude_correction(self):
        return self.get_amplitude_correction

    def set_raw_output(self, raw_output: bool):
        self.raw_output = raw_output

    def set_min_range(self, min_range: float):
        self.min_range = min_range

    def set_max_range(self, max_range: float):
        self.max_range = max_range

    def set_window_function(self, window_function: typing.Callable[[int], npt.ArrayLike]):
        self.window_function = window_function

    def set_window_correction_factor(self, amplitude_correction: bool):
        self.window_amplitude_correction = amplitude_correction

    def set_number_range_bins(self, number_range_bins: int):
        self.number_bins = number_range_bins

    def __call__(self, frequencies, Fpara):
        # ensure odd number of samples
        NfreqA = len(Fpara)
        NfreqA = NfreqA if np.mod(NfreqA, 2) != 0 else NfreqA - 1
        frequencies = frequencies[0:NfreqA]
        Fpara = Fpara[0:NfreqA]
        # center frequency
        imid = int(np.floor(NfreqA/2))
        f_asolver_mid = frequencies[imid]
        # demodulate spectrum by f_asolver_mid
        frequencies = frequencies - f_asolver_mid
        # windowing
        if self.window_function:
            wndw = self.window_function(len(Fpara))
        else:
            wndw = np.ones(len(Fpara))
        if self.window_amplitude_correction:
            wndw = calculate_amplitude_corrected_window(wndw)
        Fpara = wndw*Fpara
        df = frequencies[1] - frequencies[0]
        dt = 0.05/self.fmcw_radar.get_chirp_band_width()
        ht, t_asolver = ift_by_chirpz(Fpara, df, 0, dt)
        total_time = 2*self.fmcw_radar.get_chirp_length()
        nt = 1 + int(total_time/dt)
        # zero pad to total time
        t_asolver = np.linspace(0, total_time, nt)
        ht = np.pad(ht, (0, nt - len(ht)), 'constant')
        #
        fchirp_shift = self.fmcw_radar.get_chirp_inst_freq_fc() - f_asolver_mid
        B = self.fmcw_radar.get_chirp_band_width()
        chirpt = uchirp_complex_centered(
            t_asolver, fchirp_shift, B, self.fmcw_radar.get_chirp_length())
        yt = fftconvolve(ht, chirpt, mode='same')
        # formulation for IF data for mixer
        # spectrum > 2*f_asolver_mid already removed by analytical means
        yif = 0.5*np.conjugate(yt)*chirpt
        if (self.fmcw_radar.is_complex_mixer()):
            yif = 0.5*np.conjugate(yt)*chirpt  # complex quadrature mixer
        else:
            yif = 0.5*np.real(np.conjugate(yt)*chirpt)  # real quadrature mixer
        Yif = fftshift(fft(yif))
        fif = fftshift(fftfreq(len(Yif), dt))
        if self.raw_output:
            # raw unfiltered high resolution output
            dist = self.fmcw_radar.distance_from_beat_frequency(fif)
            return (dist, Yif)
        # idealized low pass filtering of yif
        Yif[np.abs(fif) >= self.fmcw_radar.get_low_pass_fmax()] = 0
        yif_low_pass = ifft(ifftshift(Yif))
        # resampling modeling ADC
        Tc = self.fmcw_radar.get_chirp_length()
        adc_dt = self.fmcw_radar.get_adc_sampling_rate()
        yif_t, _ = ift_by_chirpz(Yif, df, 0, adc_dt)
        Yif = fftshift(fft(yif_t))
        fif = fftshift(fftfreq(len(Yif), adc_dt))
        dist = distance_from_beat_frequency(fif, Tc, B)
        return (dist, Yif)


def range_map_pulsed_radar(frequencies, Fpara, max_range, min_range=0, Nbins=256, window_order=16, Noversample=5, amplitude_correction=False):
    """calculate the range map for a given set of F-parameters by an windowed impulse

        Parameters
        ----------
        frequencies : array(float)
            frequencies for F-parameters, expect a homogeneous spacing
        Fparameters : array(complex)
            F-parameters, same order as frequencies
        max_range : float > 0
            maximum range
        min_range : float > 0 and min_range < max_range
            minimum range
        Nbins : int > 0
            number of range bins
        window_order : int >= 0
            order of Kaiser filter
        Noversample : int >= 1
            zero padding the F-parameter frequency data as [Noversample*len(Fpara),Fpara,Noversample*len(Fpara)]

        Returns
        -------
        tuple : (array, array)
            first array contains range axis, second array contains information to fill range tensor for specific
            sweep and specific channel
    """
    # ensure odd number of samples
    NfreqA = len(Fpara)
    NfreqA = NfreqA if np.mod(NfreqA, 2) != 0 else NfreqA - 1
    frequencies = frequencies[0:NfreqA]
    Fpara = Fpara[0:NfreqA]
    # center frequency
    imid = int(np.floor(NfreqA/2))
    f_asolver_mid = frequencies[imid]
    # demodulate spectrum by f_asolver_mid
    frequencies = frequencies - f_asolver_mid
    # windowing
    wndw = windows.kaiser(len(Fpara), window_order)
    if amplitude_correction:
        wndw = calculate_amplitude_corrected_window(wndw)
    Fpara = wndw*Fpara
    # zero padding to increase TD resolution
    Fpara = zero_padd(Fpara, Noversample)
    frequencies = axis_extension(frequencies, Noversample)
    # transform data to time domain
    ht = fftshift(ifft(ifftshift(Fpara)))
    t_asolver = fftshift(
        fftfreq(len(frequencies), frequencies[1] - frequencies[0]))
    range = c0*t_asolver/2
    # limit range to radar range
    brange = (range >= min_range) & (range <= max_range)
    range = range[brange]
    ht = ht[brange]
    t = t_asolver[brange]
    # binning by integration
    filter_size = int(np.ceil(len(ht)/Nbins))
    filter_size = filter_size + \
        1 if np.mod(filter_size, 2) == 0 else filter_size  # ensure odd number
    ht_conv = np.convolve(np.ones(filter_size)/filter_size,
                          ht, mode='valid')  # integration by convolution
    start = int(filter_size/2)  # offset
    t_conv = t[start:len(ht_conv)+start]  # shifted time, for mode='valid'
    # restrict to strided array with required data
    ht_conv = ht_conv[0:-1:filter_size]
    t_conv = t_conv[0:-1:filter_size]
    # ensure exact Nbins data size
    if len(ht_conv) != Nbins:
        if len(ht_conv) > Nbins:
            ht_conv = ht_conv[0:Nbins]
            t_conv = t_conv[0:Nbins]
        else:
            # zero padd
            Npad = Nbins - len(ht_conv)
            ht_conv = np.pad(ht_conv, (0, Npad),
                             mode='constant', constant_values=(0, 0))
            dt_conv = t_conv[1] - t_conv[0]
            t_conv = np.arange(t_conv[0], t_conv[-1] +
                               (Npad+0.5)*dt_conv, dt_conv)
    range_bins = c0*t_conv/2
    return (range_bins, ht_conv)


def range_map_from_channeltensor_pulsed_radar(channel_tensor, max_range,
                                              min_range=0, Nbins=256, window_order=16, Noversample=5, amplitude_correction=False):
    """transform the frequency dimension of the channel_tensor into a range dimension

        Parameters
        ----------
        channel_tensor : ChannelTensor object
                channel tensor carrying the information and correlatons of the received signal
        max_range : float > 0
                maximum range
        min_range : float > 0 and min_range < max_range
                minimum range
        Nbins : int > 0
                number of range bins
        window_order : int >= 0
                order of Kaiser filter
        Noversample : int >= 1
                zero padding the F-parameter frequency data as [Noversample*len(Fpara),Fpara,Noversample*len(Fpara)]

        Returns
        -------
        tuple : (array, 3D array)
            first array contains range axis, second array contains range tensor[isweep, ichannel, irange]

    """
    # assume equispaced frequency points !!!
    f = channel_tensor.get_frequencies()
    #
    ranges = np.zeros(Nbins)
    tensor = channel_tensor.get_tensor()
    range_tensor = np.zeros((tensor.shape[0],
                             tensor.shape[1],
                             Nbins),
                            dtype=np.complex128)
    for isw in range(0, tensor.shape[0]):  # sweeps
        for ic in range(0, tensor.shape[1]):  # channels
            F = tensor[isw, ic, :]
            ranges, range_tensor[isw, ic, :] = range_map_pulsed_radar(f, F, max_range, min_range, Nbins,
                                                                      window_order, Noversample, amplitude_correction)
    return (ranges, range_tensor)


def compute_analog_digital_converter(t, y, adc_t0, adc_t1, adc_dt, kind='linear'):
    """simple analog to digtial converter model for time samples using interpolation to calculate ADC signal

        Parameters
        ----------
        t: array(float)
            time axis data to sample by adc
        y: array(complex)
            signal to sample by adc
        adc_t0: float
            start time adc
        adc_t1: float
            end time adc
        kind: categorical str
            linear, quadratic, cubic

        Returns
        -------
        tuple: (t_adc, y_adc)
        t_adc: array(float)
            time axis adc
        y_adc:
            sampled signal

    """
    # restricted to relevant interval
    t0 = adc_t0 - 3*adc_dt
    t1 = adc_t1 + 3*adc_dt
    time_mask = np.logical_and(t >= t0, t <= t1)
    t_restricted = t[time_mask]
    y_restricted = y[time_mask]
    # prepare interpolation
    # note: interpol1d can't deal with complex data, hence, split into real and imag part
    ip_y_restricted_real = interp1d(
        t_restricted, np.real(y_restricted), kind=kind)
    ip_y_restricted_imag = interp1d(
        t_restricted, np.imag(y_restricted), kind=kind)
    # calculate signal at t_adc by point sampling
    t_adc = np.arange(adc_t0, adc_t1, adc_dt)
    y_adc = ip_y_restricted_real(t_adc) + 1j*ip_y_restricted_imag(t_adc)
    return (t_adc, y_adc)


def range_map_fmcw_radar(frequencies,
                         Fpara,
                         f0c,
                         f1c,
                         Tc,
                         adc_dt,
                         f_IF_cutoff=np.finfo(np.float64).max,
                         complex_mixer=True,
                         window_type='kaiser',
                         window_order=16,
                         Noversample=1,
                         raw_output=False,
                         oversample_type='zeropadding',
                         dumpFparaDataDir='',
                         amplitude_correction=False
                         ):
    # ensure odd number of samples
    NfreqA = len(Fpara)
    NfreqA = NfreqA if np.mod(NfreqA, 2) != 0 else NfreqA - 1
    frequencies = frequencies[0:NfreqA]
    Fpara = Fpara[0:NfreqA]
    # center frequency
    imid = int(np.floor(NfreqA/2))
    f_asolver_mid = frequencies[imid]
    # demodulate spectrum by f_asolver_mid
    frequencies = frequencies - f_asolver_mid
    # windowing
    if window_type == 'kaiser':
        wndw = windows.kaiser(len(Fpara), window_order)
    elif window_type == 'hann':
        wndw = windows.hann(len(Fpara))
    elif window_type == 'hamming':
        wndw = windows.hamming(len(Fpara))
    elif window_type == 'chebyshev':
        wndw = windows.chebwin(len(Fpara), at=100)
    else:
        print("Unknown window type. Fallback to kaiser")
        wndw = windows.kaiser(len(Fpara), window_order)
    if amplitude_correction:
        wndw = calculate_amplitude_corrected_window(wndw)

    FparaWndw = Fpara*wndw

    if oversample_type == 'zeropadding':
        # zero padding to increase TD resolution
        FparaInterp = zero_padd(FparaWndw, Noversample)
        frequencies = axis_extension(frequencies, Noversample)
    elif oversample_type == 'linear' or oversample_type == 'quadratic' or oversample_type == 'cubic':
        FparaRealInterpolator = interp1d(
            frequencies, np.real(FparaWndw), kind=oversample_type)
        FparaImagInterpolator = interp1d(
            frequencies, np.imag(FparaWndw), kind=oversample_type)
        frequencies = np.linspace(
            frequencies[0], frequencies[-1], (2*Noversample+1)*len(frequencies))
        FparaInterp = FparaRealInterpolator(
            frequencies) + 1j*FparaImagInterpolator(frequencies)
    else:
        print("Unknown oversampling type. Fallback to zero-padding")
        FparaInterp = zero_padd(FparaWndw, Noversample)
        frequencies = axis_extension(frequencies, Noversample)

    if dumpFparaDataDir:
        thebasepath = dumpFparaDataDir
        dumpFilesList = [filename for filename in os.listdir(
            thebasepath) if filename.startswith("dumpFparaPreWindow")]
        dumpFilesListLatestCount = max([int(filename[filename.find(
            "w")+1: filename.find(".")]) for filename in dumpFilesList])
        np.savetxt(thebasepath+"/dumpFparaPreWindow" +
                   str(dumpFilesListLatestCount)+".txt", Fpara.view(np.double))
        np.savetxt(thebasepath+"/dumpFparaPostWindow" +
                   str(dumpFilesListLatestCount)+".txt", FparaWndw.view(np.double))
        np.savetxt(thebasepath+"/dumpFparaInterp" +
                   str(dumpFilesListLatestCount)+".txt", FparaInterp.view(np.double))

    Fpara = FparaInterp
    # transform data to time domain
    ht = fftshift(ifft(ifftshift(Fpara)))
    t_asolver = fftshift(
        fftfreq(len(frequencies), frequencies[1] - frequencies[0]))
    t0_asolver = t_asolver[0]
    tend_asolver = t_asolver[-1]
    dt_asolver = t_asolver[1] - t_asolver[0]
    n_ext = 1*(int(Tc/(tend_asolver - t0_asolver)))+1
    #
    ht = zero_padd(ht, n_ext)
    t_asolver = axis_extension(t_asolver, n_ext)
    #
    fchirp_shift = (f0c + f1c)/2 - f_asolver_mid
    B = f1c - f0c
    chirpt = uchirp_complex_centered(t_asolver, fchirp_shift, B, Tc)
    yt = fftconvolve(ht, chirpt, mode='same')
    # formulation for IF data for mixer
    # spectrum > 2*f_asolver_mid already removed by analytical means
    yif = 0.5*np.conjugate(yt)*chirpt
    if (complex_mixer):
        yif = 0.5*np.conjugate(yt)*chirpt  # complex quadrature mixer
    else:
        yif = 0.5*np.real(np.conjugate(yt)*chirpt)  # real quadrature mixer
    Yif = fftshift(fft(yif))
    fif = fftshift(fftfreq(len(Yif), dt_asolver))

    # idealized low pass filtering of yif
    Yif[np.abs(fif) >= f_IF_cutoff] = 0
    yif_low_pass = ifft(ifftshift(Yif))
    if raw_output:
        # raw unfiltered high resolution output
        dist = distance_from_beat_frequency(fif, Tc, B)
        return (dist, Yif)
    # resampling modeling ADC
    t, yif_t = compute_analog_digital_converter(
        t_asolver, yif_low_pass, -Tc/2, Tc/2, adc_dt)
    Yif = fftshift(fft(yif_t))
    fif = fftshift(fftfreq(len(Yif), adc_dt))
    dist = distance_from_beat_frequency(fif, Tc, B)
    return (dist, Yif)


def range_map_from_channeltensor_fmcw_radar(channel_tensor, fmcw_radar, window_type='kaiser', window_order=16, Noversample=5, raw_output=False, oversample_type='zeropadding', dumpFparaDataDir='', amplitude_correction=False):
    """transform the frequency dimension of the channel_tensor into a range dimension

        Parameters
        ----------
        channel_tensor : ChannelTensor object
                channel tensor carrying the information and correlatons of the received signal
        fmcw_radar : FMCWRadar
                fmcw radar model parameters
        Noversample : int >= 1
                zero padding the F-parameter frequency data as [Noversample*len(Fpara),Fpara,Noversample*len(Fpara)]

        Returns
        -------
        tuple : (array, 3D array)
            first array contains range axis, second array contains range tensor[isweep, ichannel, irange]

    """
    # assume equispaced frequency points !!!
    f = channel_tensor.get_frequencies()
    #
    tensor = channel_tensor.get_tensor()
    f0c = fmcw_radar.get_chirp_inst_freq_f0()
    f1c = fmcw_radar.get_chirp_inst_freq_f1()
    Tc = fmcw_radar.get_chirp_length()
    adc_dt = fmcw_radar.get_adc_sampling_rate()
    f_IF_cutoff = fmcw_radar.get_low_pass_fmax()
    complex_mixer = fmcw_radar.is_complex_mixer()
    # preallocate tensor
    Nbins = len(np.arange(-Tc/2, Tc/2, adc_dt))

    if raw_output == False:
        range_tensor = np.zeros((tensor.shape[0],
                                tensor.shape[1],
                                Nbins),
                                dtype=np.complex128)
    else:
        # Make a single preliminary run to get the length of the range tensor with raw output
        F_tmp = tensor[0, 0, :]
        ranges_tmp, range_tensor_tmp = range_map_fmcw_radar(f,
                                                            F_tmp,
                                                            f0c,
                                                            f1c,
                                                            Tc,
                                                            adc_dt,
                                                            f_IF_cutoff,
                                                            complex_mixer,
                                                            window_type,
                                                            window_order,
                                                            Noversample=Noversample,
                                                            raw_output=False,
                                                            oversample_type=oversample_type,
                                                            dumpFparaDataDir=dumpFparaDataDir,
                                                            amplitude_correction=amplitude_correction)
        range_tensor = np.zeros((tensor.shape[0],
                                tensor.shape[1],
                                len(range_tensor_tmp)),
                                dtype=np.complex128)

    if dumpFparaDataDir:
        thebasepath = dumpFparaDataDir
        dumpFilesList = [filename for filename in os.listdir(
            thebasepath) if filename.startswith("dumpFpara")]
        for filename in dumpFilesList:
            os.remove(thebasepath+"/"+filename)

    counter = 0
    # apply the FMCW RADAR algorithm to estimate the distances from the IF signal
    for isw in range(0, tensor.shape[0]):  # sweeps
        for ic in range(0, tensor.shape[1]):  # channels
            if dumpFparaDataDir:
                open(thebasepath+"/"+"dumpFparaPreWindow" +
                     str(counter)+".txt", mode='w').close()
                open(thebasepath+"/"+"dumpFparaPostWindow" +
                     str(counter)+".txt", mode='w').close()
                open(thebasepath+"/"+"dumpFparaInterp" +
                     str(counter)+".txt", mode='w').close()

            counter += 1
            F = tensor[isw, ic, :]
            ranges, range_tensor[isw, ic, :] = range_map_fmcw_radar(f,
                                                                    F,
                                                                    f0c,
                                                                    f1c,
                                                                    Tc,
                                                                    adc_dt,
                                                                    f_IF_cutoff,
                                                                    complex_mixer,
                                                                    window_type,
                                                                    window_order,
                                                                    Noversample=Noversample,
                                                                    raw_output=raw_output,
                                                                    oversample_type=oversample_type,
                                                                    dumpFparaDataDir=dumpFparaDataDir,
                                                                    amplitude_correction=amplitude_correction
                                                                    )

    return (ranges, range_tensor)


def range_map_from_channeltensor_fmcw_radar_legacy(radar, channel_tensor, filter={}, debug=False):
    """
    transform the frequency dimension of the channel_tensor into a range dimension

    Parameters
    ----------
    radar : radar object
        radar object containing setup used for data generation as well as relevant parameters
    channel_tensor : ChannelTensor object
        channel tensor containing correlation information between the signals received at antennas

    Returns
    -------
    range_axis_vals : array(float)
        new nodes of range axis obtaining throgh transformation from frequency axis
    range_tensor : 3D-array(complex)
        new channel tensor with transformed range domain instead of frequency domain
    """
    tslow = radar.get_time()
    freq_slow = radar.get_freq()
    uslowt = radar.get_uslowt()
    uslowf = radar.get_uslowf()
    fMaxLowPass = radar.get_low_pass_fmax()
    f_asolver = channel_tensor.get_frequencies()
    # shift A-solver frequency
    freqA = f_asolver - radar.get_chirp_inst_freq_fc()
    # check chirp frequencies are within range of A-solver frequencies
    if (freqA[0] > freq_slow[0]):
        raise ValueError('lower frequency range mismatch {} vs {}'.format(
            freqA[0], freq_slow[0]))
    if (freqA[-1] < freq_slow[-1]):
        raise ValueError('upper frequency range mismatch {} vs {}'.format(
            freqA[-1], freq_slow[-1]))
    #
    #
    tensor = channel_tensor.get_tensor()
    range_tensor = np.zeros((tensor.shape[0],
                             tensor.shape[1],
                             radar.get_adc_time_samples().shape[0]),
                            dtype=np.complex128)
    for isweep in range(0, tensor.shape[0]):
        for ichannel in range(0, tensor.shape[1]):
            Fpara = tensor[isweep, ichannel, :]
            # interpolate shifted F-parameter to chirp frequencies
            # order the fft data
            wndw = windows.kaiser(
                len(freqA), filter['order_tf']) if filter else np.ones(len(freqA))
            ip_H_re = interp1d(freqA, wndw*np.real(Fpara), kind='cubic')
            ip_H_im = interp1d(freqA, wndw*np.imag(Fpara), kind='cubic')
            ipH = ip_H_re(freq_slow) + 1j*ip_H_im(freq_slow)
            Ys = ipH*uslowf
            # revert order for FFT
            Ys = fftshift(Ys)
            ys = ifft(Ys)
            # calculate mixer signal already rejecting 2*fc parts of spectrum
            if (radar.is_complex_mixer()):
                yif = 0.5*np.conjugate(ys)*uslowt  # complex quadrature mixer
            else:
                # real quadrature mixer
                yif = 0.5*np.real(np.conjugate(ys)*uslowt)
            wndw = windows.kaiser(
                len(yif), filter['order_prod']) if filter else np.ones(len(yif))
            Yif = fft(wndw*yif)
            f = fftfreq(len(Yif), tslow[1] - tslow[0])
            # ideal low pass of mixer signal
            Yif[np.abs(f) > fMaxLowPass] = 0
            # transform back to time domain and resample
            filtered_yif = ifft(Yif)
            ip_filtered_yif = interp1d(tslow, filtered_yif, kind='cubic')
            sampled_yif = ip_filtered_yif(radar.get_adc_time_samples())
            # now fourier transform
            wndw = windows.hamming(len(yif)) if filter else np.ones(len(yif))
            sampled_Yif = fftshift(fft(sampled_yif))
            f_map = fftshift(
                fftfreq(len(sampled_Yif), radar.get_adc_sampling_rate()))
            range_tensor[isweep, ichannel, :] = sampled_Yif
    range_axis_vals = radar.distance_from_beat_frequency(f_map)
    return (range_axis_vals, np.conjugate(range_tensor))


def range_map_from_channeltensor_fmcw_radar_legacy_v2(radar, channel_tensor, filter={}, debug=False):
    """
    transform the frequency dimension of the channel_tensor into a range dimension

    Parameters
    ----------
    radar : radar object
        radar object containing setup used for data generation as well as relevant parameters
    channel_tensor : ChannelTensor object
        channel tensor containing correlation information between the signals received at antennas

    Returns
    -------
    range_axis_vals : array(float)
        new nodes of range axis obtaining throgh transformation from frequency axis
    range_tensor : 3D-array(complex)
        new channel tensor with transformed range domain instead of frequency domain
    """
    #
    fMaxLowPass = radar.get_low_pass_fmax()
    Tc = radar.get_chirp_length()
    B = radar.get_chirp_band_width()

    def chirp(t):
        return uchirp_complex_centered(t, 0.0, B, Tc)

    # assume equispaced frequency points !!!
    f_asolver = channel_tensor.get_frequencies()
    freqA = f_asolver - radar.get_chirp_inst_freq_fc()
    #
    #
    tensor = channel_tensor.get_tensor()
    range_tensor = np.zeros((tensor.shape[0],
                             tensor.shape[1],
                             radar.get_adc_time_samples().shape[0]),
                            dtype=np.complex128)
    for isweep in range(0, tensor.shape[0]):
        for ichannel in range(0, tensor.shape[1]):
            Fpara = tensor[isweep, ichannel, :]
            # calculate padding
            dfA = freqA[1] - freqA[0]
            tA = fftfreq(len(Fpara), dfA)
            dtA = tA[1] - tA[0]
            NLength = 2*(len(Fpara) + int(Tc/dtA)) + 1
            Npad = NLength - len(Fpara)
            # interpolate windowed impulse response
            wndw = windows.kaiser(
                len(freqA), filter['order_tf']) if filter else np.ones(len(freqA))
            ht = ifft(wndw*Fpara)
            ht = np.pad(ht, (0, Npad), mode='constant', constant_values=(0, 0))
            # sample excitation signal
            t = fftfreq(len(ht), dfA)
            yt = chirp(t)
            dt = t[1] - t[0]
            # convolution via FFT
            yt_conv_ht = fftconvolve(ht, yt, mode='same')*dt
            # calculate mixer signal already rejecting 2*fc parts of spectrum
            if (radar.is_complex_mixer()):
                # complex quadrature mixer
                yif = 0.5*np.conjugate(yt_conv_ht)*chirp(t)
            else:
                yif = 0.5*np.real(np.conjugate(yt_conv_ht) *
                                  chirp(t))  # real quadrature mixer
            # transform if signal back to FD
            wndw = windows.kaiser(
                len(yif), filter['order_prod']) if filter else np.ones(len(yif))
            Yif = fft(wndw*yif)
            fif = fftfreq(len(Yif), t[1] - t[0])
            # ideal low pass of mixer signal
            Yif[np.abs(fif) > fMaxLowPass] = 0
            # back to TD
            filtered_yif = ifft(Yif)
            # interpolate data
            ip_filtered_yif = interp1d(t, filtered_yif, kind='cubic')
            sampled_yif = ip_filtered_yif(radar.get_adc_time_samples())
            # now fourier transform
            wndw = windows.hamming(len(yif)) if filter else np.ones(len(yif))
            sampled_Yif = fftshift(fft(sampled_yif))
            f_map = fftshift(
                fftfreq(len(sampled_Yif), radar.get_adc_sampling_rate()))
            range_tensor[isweep, ichannel, :] = sampled_Yif
    range_axis_vals = radar.distance_from_beat_frequency(f_map)
    return (range_axis_vals, np.conjugate(range_tensor))


###################################################################################################


def if_signal_fmcw_radar_chirp_cpugpu(frequencies,
                                      H,
                                      f0c,
                                      f1c,
                                      Tc,
                                      adc_dt,
                                      adc_t0=None,
                                      adc_nbins=None,
                                      f_IF_cutoff=np.finfo(np.float64).max,
                                      complex_mixer=True,
                                      plot_intermediate_results=False
                                      ):
    """ Calculates the ADC sampled IF signal

    Parameters
    ----------
    frequencies: array(float)
       transfer function frequencies > 0, sorted in ascending order in Hz
    H: array(complex)
       transfer function for positive spectrum
    f0c: float
       chirp lowest frequency
    f1c: float
       chirp highest frequency
    Tc: float
       chirp rise time
    adc_dt: float
       analog to digital converter sampling time step
    adc_t0: float
       start time adc sampling
    adc_nbins: int > 0
       number of sampling bins
    f_IF_cutoff: float
        ideal low pass cut off frequency in Hz
    complex_mixer: bool
        mixer architecture

    Out: tuple(array(float), array(complex))
       t time
       yif_t sampled IF signal at time t
    """

    xp = np
    xpx = scipy
    Ha = 2*H # factor 2 for analytical signal
    f_base = frequencies[0]  # lowest frequency solver
    B_solver = frequencies[-1] - frequencies[1]  # solver bandwidth
    # demodulate spectrum by f_base
    # all calculations are performend in baseband of transferfunction H
    frequencies = frequencies - f_base
    dfH = frequencies[1] - frequencies[0]  # frequency spacing discrete H
    HTmax = 1.0/dfH  # transfer function periode
    # internal sampling frequency of TD signal based on Chirp bandwidth
    B_chirp = f1c - f0c
    # internal sampling rate based on Chirp and Solver bandwidth
    dt_internal = min(1.0/(5*B_chirp), 1.0/(5*B_solver))
    # sampling chirp
    DT = 0.05*Tc  # extension beyond Chirp support to suppress artefacts in convolution
    t_chirp = xp.arange(-Tc/2-DT, Tc/2 + DT, dt_internal)
    fchirp_shift = (f0c + f1c)/2 - f_base  # bring chirp to baseband of H

    chirpta = uchirp_complex_centered(t_chirp, fchirp_shift, B_chirp, Tc)

    # sampling causal transfer function
    # no scaling required as 1/N in ift takes care
    hta, t_h = ift_by_chirpz(Ha, dfH, 0, dt_internal, t1=HTmax, axis=-1)
    hta = B_solver*hta  # B/N = df for the integral approximation

    yta = dt_internal * \
        xpx.signal.convolve(hta, chirpta, mode='full')

    t_Rx = t_chirp[0]+dt_internal*xp.linspace(0, len(yta), len(yta))

    chirpta = zero_pad_right(chirpta, yta.shape[-1])

    # formulation for IF data for mixer
    # spectrum > 2*f_asolver_mid already removed by analytical means
    # zero pad chirp to match dimension with yt
    if (complex_mixer):
        # complex quadrature mixer + high freq rejection
        yif = 0.5*np.conjugate(yta)*chirpta
    else:
        # real quadrature mixer + high freq rejection
        yif = 0.5*np.real(np.conjugate(yta)*chirpta)
    #
    # idealized low pass filtering of yif
    #
    Yif = xp.fft.fft(yif, axis=-1)
    fif = xp.fft.fftfreq(Yif.shape[-1], t_Rx[1] - t_Rx[0])
    idx = xp.argwhere(np.abs(fif) >= f_IF_cutoff).flatten()
    Yif[idx] = 0
    #
    # model ADC by evaluating the signal at the adc time samples via InvChirpZ
    #
    filtered_yif = xp.fft.ifft(Yif)
    if (adc_t0):
        t = adc_t0 + adc_dt*xp.linspace(0, adc_nbins-1, adc_nbins)
    else:
        t = t_chirp[0] + adc_dt*xp.linspace(0, adc_nbins-1, adc_nbins)
    if (t[0] < t_Rx[0]):
        t[0] = t_Rx[0]
    
    if (t[-1] > t_Rx[-1]):
        t[-1] = t_Rx[-1]
    ip_filtered_yif = xpx.interpolate.RegularGridInterpolator([t_Rx], filtered_yif, method='linear')
    yif = ip_filtered_yif(t)
    return t, yif


class CalculateFMCWRange:
    def __init__(self,
                 frequencies,
                 f0c,
                 f1c,
                 Tc,
                 adc_dt,
                 adc_t0=None,
                 adc_nbins=None,
                 f_IF_cutoff=np.finfo(np.float64).max,
                 complex_mixer=True,
                 if_signal_window=None):
        self.frequencies = frequencies
        self.f0c = f0c
        self.f1c = f1c
        self.Tc = Tc
        self.adc_dt = adc_dt
        self.adc_t0 = adc_t0
        self.adc_nbins = adc_nbins
        self.f_IF_cutoff = f_IF_cutoff
        self.complex_mixer = complex_mixer
        self.if_signal_window = if_signal_window
        self.distance = None

    def get_distance(self):
        return self.distance

    def calculate_range(self, H):
        """ Calculates the range from an FMCW RADAR chirp
        Parameters
        ----------
        frequencies: array(float)
        transfer function frequencies > 0, sorted in ascending order
        H: array(complex)
        transfer function
        f0c: float
        chirp lowest frequency
        f1c: float
        chirp highest frequency
        Tc: float
        chirp rise time
        adc_dt: float
        analog to digital converter sampling time step
        adc_t0: float
        start time adc sampling
        adc_nbins: int > 0
        number of sampling bins
        f_IF_cutoff: float
            ideal low pass cut off frequency in Hz
        complex_mixer: bool
            mixer architecture
        if_signal_window:  function(int)
            windowing function applied to time domain IF signal before DFT

        Out: tuple(array(float), array(complex))
        t time
        yif_t sampled IF signal at time t
        """
        n_adc_signal_bins = self.adc_nbins
        t, if_signal = if_signal_fmcw_radar_chirp_cpugpu(self.frequencies,
                                                         H,
                                                         self.f0c,
                                                         self.f1c,
                                                         self.Tc,
                                                         self.adc_dt,
                                                         self.adc_t0,
                                                         n_adc_signal_bins,
                                                         self.f_IF_cutoff,
                                                         self.complex_mixer
                                                         )
        if (self.if_signal_window):
            if_signal = self.if_signal_window(len(if_signal))*if_signal
        # Y = fftshift(fft(if_signal))#[self.adc_nbins+1:]
        # f = fftshift(fftfreq(len(if_signal), t[1] - t[0]))#[self.adc_nbins+1:]
        Y = fft(if_signal)
        n = if_signal.shape[0]
        f = 1.0/(n*(t[1] - t[0]))*np.arange(0, n, 1) # only positive frequency content
        # f = fftshift(fftfreq(len(if_signal), t[1] - t[0]))#[self.adc_nbins+1:]

        
        B = (self.f1c - self.f0c)  # chirp bandwidth
        self.distance = distance_from_beat_frequency(f, self.Tc, B)
        return Y


def range_map_from_channeltensor_fmcw_radar_new(channel_tensor, fmcw_radar, nbins, if_signal_window=None):
    """transform the frequency dimension of the channel_tensor into a range dimension

        Parameters
        ----------
        channel_tensor : ChannelTensor object
                channel tensor carrying the information and correlatons of the received signal
        fmcw_radar : FMCWRadar
                fmcw radar model parameters

        Returns
        -------
        tuple : (array, 3D array)
            first array contains range axis, second array contains range tensor[isweep, ichannel, irange]

    """
    # assume equispaced frequency points !!!
    f = channel_tensor.get_frequencies()
    tensor = channel_tensor.get_tensor()
    f0c = fmcw_radar.get_chirp_inst_freq_f0()
    f1c = fmcw_radar.get_chirp_inst_freq_f1()
    Tc = fmcw_radar.get_chirp_length()
    adc_dt = fmcw_radar.get_adc_sampling_rate()
    f_IF_cutoff = fmcw_radar.get_low_pass_fmax()
    complex_mixer = fmcw_radar.is_complex_mixer()
    # fmcw
    range_estimator1d = CalculateFMCWRange(
        frequencies=f,
        f0c=f0c,
        f1c=f1c,
        Tc=Tc,
        adc_dt=adc_dt,
        adc_t0=-Tc/2,
        adc_nbins=nbins,
        f_IF_cutoff=f_IF_cutoff,
        complex_mixer=complex_mixer,
        if_signal_window=if_signal_window)


    range_tensor = np.zeros((tensor.shape[0],
                            tensor.shape[1],
                            nbins),
                            dtype=np.complex128)
    # apply the FMCW RADAR algorithm to estimate the distances from the IF signal
    for isweep in range(0, tensor.shape[0]):  # sweeps
        for ichannel in range(0, tensor.shape[1]):  # channels
            F = tensor[isweep, ichannel, :]
            range_tensor[isweep, ichannel, :] = range_estimator1d.calculate_range(F)
    ranges = range_estimator1d.get_distance()
    return (ranges, range_tensor)


def calculate_velocity(tensor, fc, T_frame, axis=0):
    vtensor = fftshift(fft(tensor, axis=axis), axes=axis)
    freqs = fftshift(fftfreq(vtensor.shape[axis], T_frame))
    vradial = freqs/(2*fc)*c0
    return vradial, vtensor
