# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

# -*- coding: utf-8 -*-
r"""This module encapsulates the Frequency Modulated Continues Waveform (FMCW) RADAR model"""

import numpy as np
from scipy.fftpack import fft, fftfreq, fftshift
from .physical_constants import c0
from copy import deepcopy
from scipy.special import fresnel


def uchirp_complex_centered(t, fc, B, Tc):
    r""" linear chirp
    Parameters
    ----------
    t: float
       time
    fc: float
       center frequency
    Tc: float
        rise time
    B: float
       band width

    Out: complex
       complex chirp signal

    :math:`s(t)=\exp[j (2\pi f_0 + 0.5 B/T_c t^2)],\quad t \in [-T_c/2,T_c/2]`
    :math:`s(t)=0` else
    """
    wndw = np.heaviside(1 - 2*np.abs(t)/Tc, 1.0)
    freq = fc + 0.5*B/Tc*t  # instant freq
    return wndw*np.exp(1j*2.0*np.pi*freq*t)


def instanteneous_chirp_frequency(t, fc, B, Tc):
    r"""Instantenous frequency of linear chirp
        Parameters
        ----------
        t: float
        time
        fc: float
        center frequency
        Tc: float
            rise time
        B: float
        band width

        Out: float
        instanteneous chirp frequency
    """
    freq = fc + 0.5*B*(t/Tc)  # instant freq
    return freq


def Uchirp_complex_centered(f, fc, B, Tc):
    r""" Analytical Fourier transform of the chirp_complex_centered
    Parameters
    ----------
    f: float
       frequency
    fc: float
       center frequency
    Tc: float
        rise time
    B: float
       band width

    Out: complex
       complex chirp signal

    :math:`S(f)=\int \mathrm{d}t\, \exp[-1j 2\pi f t] s(t)`
    """
    omega = 2*np.pi*f
    domega = 2*np.pi*B
    delta = omega - domega
    w = np.sqrt(np.pi*domega/Tc)
    x1 = (domega/2 + delta)/w
    x2 = (domega/2 - delta)/w
    Cx1, Sx1 = fresnel(x1)
    Cx2, Sx2 = fresnel(x2)
    y = (omega - domega)*(omega - domega)*Tc/(2*domega)
    Sf = (np.exp(-1j*y))*(Cx1 + 1j*Sx1 + Cx2 + 1j*Sx2)/np.sqrt(np.pi*Tc/domega)
    return Sf


"""
utility functions
"""


def time_delay_from_beat_frequency(fbeat, Tc, B):
    """
    valid for linear chirp
    """
    return fbeat*Tc/B


def distance_from_beat_frequency(fbeat, Tc, B):
    """
    distance of scatterer from radar (neglecting Tx-Rx distance)
    """
    return time_delay_from_beat_frequency(fbeat, Tc, B)*c0/2


def velocity_from_frame_frequency(fframe, fc):
    return fframe/fc*c0/2


def calculate_band_if_signal(f0, tslow, yt_complex, uslowt):
    """
    calculates the band width B frequency component part of the IF signal
    """
    ytslow = np.exp(-1j*2*np.pi*f0*tslow)*yt_complex
    if_sig_slow = 0.5*np.real(uslowt*np.conjugate(ytslow))
    return if_sig_slow






"""
FMCW Class
"""
##############################################################################

##############################################################################
##############################################################################
##############################################################################




class FMCWRadar:
    r"""Model for a linear FMCW Radar sensor"""

    def __init__(self, f0, f1, Tc, low_pass_fmax, TsAdc, complex_mixer=False):
        r"""RADAR Model Input

        f0 : float
            lowest  instanteneous frequency of chirp
        f1 : float
            highest instanteneous frequency of chirp
        Tc : float
            duration of chirp
        TsAdc : float
            analog digital converter sampling rate
        low_pass_fmax : float
            cut off frequency of ideal low pass after mixer
        """
        # characterize the chirp signal
        self.f0 = f0  # lowest linear chirp inst frequency
        self.f1 = f1  # highest linear chirp inst frequency
        self.B = f1 - f0  # bandwidth inst freq
        self.fc = 0.5*(f0 + f1)  # center frequency
        self.Tc = Tc  # chirp length
        # calculate FFT of chirp
        self.low_pass_fmax = low_pass_fmax  # max frequency of ideal low pass
        over_sampling_factor = 4  # use at least 2 to ensure Nyquist sampling theorem
        # internal sampling rate of chirp
        self.Ts = 1.0/(over_sampling_factor*self.B)
        isamples = int(Tc/self.Ts)  # ensure that we sample at -/+ TcHalf
        # ensure odd number samples
        isamples = isamples + 1 if np.mod(isamples, 2) == 0 else isamples
        self.tslow = np.linspace(-self.Tc/2, self.Tc/2, isamples)
        # self.tslow = np.linspace(-self.Tc, self.Tc, 2*isamples+1)
        self.Ts = self.tslow[1] - self.tslow[0]
        # self.uslowt = uchirp_complex_centered(self.tslow, 0.0, self.B, self.Tc)
        self.uslowt = uchirp_complex_centered(self.tslow, 0.0, self.B, self.Tc)
        self.uslowf = fftshift(fft(self.uslowt))
        self.freq_slow = fftshift(
            fftfreq(len(self.uslowf), self.tslow[1]-self.tslow[0]))
        # calculate required cir spectral interval
        self.f_min_cir = self.fc + self.uslowf[0]
        self.f_max_cir = self.fc + self.uslowf[-1]
        # calculate adc time samples
        self.TsAdc = TsAdc  # sampling rate analog digital converter
        self.t_adc = np.arange(self.tslow[1], self.tslow[-1], self.TsAdc)
        # specify the mixer model
        self.complex_mixer = complex_mixer  # real or complex mixer type
        # dicts for mimo position definitions
        self.Tx = {}
        self.Rx = {}
        self.channel_dict = None

    def get_number_Tx(self):
        return len(self.Tx)

    def get_number_Rx(self):
        return len(self.Rx)

    def add_Tx_location(self, name, position):
        self.Tx[name] = np.array(position)

    def get_Tx_locations(self):
        return self.Tx

    def add_Rx_location(self, name, position):
        self.Rx[name] = np.array(position)

    def get_Rx_locations(self):
        return self.Rx

    def get_time(self):
        """
        sample values for sampling complex base band part of chirp
        """
        return self.tslow

    def get_uslowt(self):
        """
        sampled complex base band part of chirp
        """
        return self.uslowt

    def get_freq(self):
        """
        dft frequencies
        """
        return self.freq_slow

    def get_uslowf(self):
        """
        dft of uslow
        """
        return self.uslowf

    def get_chirp_inst_freq_f0(self):
        return self.f0

    def get_chirp_inst_freq_f1(self):
        return self.f1

    def get_chirp_inst_freq_fc(self):
        return self.fc

    def get_chirp_band_width(self):
        """
        band width of instanteneous chirp frequency
        """
        return self.B

    def get_chirp_length(self):
        return self.Tc

    def get_low_pass_fmax(self):
        """
        cut off frequency of ideal low pass before sampling
        """
        return self.low_pass_fmax

    def get_adc_sampling_rate(self):
        """
        adc samping rate after low pass
        """
        return self.TsAdc

    def get_cir_f_min(self):
        """
        lower frequency of required channel impulse response
        """
        return self.f_min_cir

    def get_cir_f_max(self):
        """
        upper frequency of required channel impulse response
        """
        return self.f_max_cir

    def get_chirp_lambda0(self):
        return c0/self.get_chirp_inst_freq_f0()

    def get_chirp_k0(self):
        return 2.0*np.pi*self.get_chirp_inst_freq_f0()/c0

    def get_cir_sampling_rate_from_delay(self, max_delay, min_samples_per_delay=4):
        """
        suggest frequency sampling step of solver in Hz
        from maximal expected time delay at receiver
        """
        df = 1.0/(min_samples_per_delay*max_delay)  # at least 4 samples
        return df

    def get_cir_sampling_rate_from_range(self, max_distance):
        """suggest frequency sampling step of solver in Hz from maximal expected object distance"""
        max_delay = 2.0*max_distance/c0
        df = self.get_cir_sampling_rate_from_delay(max_delay)
        # calcuate df that is a fraction of simulation interval
        DfSimulation = self.f_max_cir - self.f_min_cir
        Nsteps = np.ceil(DfSimulation/df)
        return DfSimulation/(Nsteps-1)

    def distance_from_beat_frequency(self, fbeat):
        """converts beat frquency of IF signal to a range"""
        return distance_from_beat_frequency(fbeat, self.Tc, self.B)

    def velocity_from_frame_frequency(self, fframe):
        """converts frame frequency to a velocity"""
        return velocity_from_frame_frequency(fframe, self.f0)

    def get_max_range(self):
        """maximal unambiguous range for specified chirp"""
        return self.low_pass_fmax*c0/(self.B/self.Tc)

    def get_range_resolution(self):
        """range resolution for specified chirp"""
        return c0/(2*self.B)

    def get_adc_time_samples(self):
        """time instances for analog to digital converter"""
        return self.t_adc

    def is_complex_mixer(self):
        """complex or real mixer architecture"""
        return self.complex_mixer

    def get_chirp_function(self):
        """return the used chirp function for evaluation"""
        def chirp_funtion(t):
            freq = self.fc + 0.5*self.B/self.Tc*t  # instant freq
            return np.exp(1j*2.0*np.pi*freq*t)
        return chirp_funtion

    def get_demodulated_chirp_function(self, f):
        """return the demodulated chirp function"""
        def chirp_funtion(t):
            freq = self.fc - f + 0.5*self.B/self.Tc*t  # instant freq
            return np.exp(1j*2.0*np.pi*freq*t)
        return chirp_funtion

    def build_channel_dictionary(self):
        """ create channel dictionary"""
        self.channel_dict = {}
        ichannel = 0
        for arx in self.Rx:
            for atx in self.Tx:
                self.channel_dict[ichannel] = (arx, atx)
                ichannel += 1
        return self.channel_dict

    def get_channel_dictionary(self):
        if self.channel_dict:
            return self.channel_dict
        else:
            return self.build_channel_dictionary()

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result
