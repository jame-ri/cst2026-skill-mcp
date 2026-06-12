# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

"""This module contains the one-dimensional (pseudo) spectral angle-of-arrival finding algorithms
and some helper routines.
"""

import numpy as np
from scipy.fftpack import ifft, fftfreq, fftshift, ifftshift
from scipy.signal import windows
from .coordinate_systems import SphericalCoordinateSystem
from .math import omp


def create_virtual_antenna_matrix(tx_dict, rx_dict, channel_dict, scale=1):
    """
    Create matrix of virtual antenna array positions consistent with the enumeration of the channels
    in the channel tensor.

    Parameters
    ----------
    tx_dict : dict(str,np.array(3))
            Dictionary mapping antenna names to antenna positions
    rx_dict : dict(str,np.array(3))
            Dictionary mapping antenna names to antenna positions
    channel_dict : dict((str,str),int)
            Dictionary mapping the pair of Rx/Tx name to the channel number as obtained from the channel tensor
    scale : float
            Scale the resulting positions to take possible units into account

    Returns
    -------
    antenna_matrix : float array
                   Height = 3, Width = number channels
                   the column vectors are the virtual antenna position for a specific channel
    """

    NTx = len(tx_dict)
    NRx = len(rx_dict)
    dvirt = np.zeros((NTx * NRx, 3), dtype=np.complex128)
    for k, v in channel_dict.items():
        strRx = v[0]
        strTx = v[1]
        rTx = tx_dict[strTx] * scale
        rRx = rx_dict[strRx] * scale
        dvirt[k, :] = rTx + rRx
    return dvirt


def assemble_covariancematrix_single_frequency(channel_tensor, ifreq=0):
    """
    Calculate the covariance matrix for a single frequency of the channel tensor

    Parameters
    ----------
    channel_tensor : class ChannelTensor
            Channel tensor object from a simulation
    ifreq : int
            Frequency index

    Returns
    -------
    Rhat : np.array((2, 2), float)
           covariance matrix estimated from channel tensor
    """
    X = channel_tensor.get_tensor()
    number_channels = channel_tensor.get_number_of_channels()
    Rhat = np.zeros((number_channels, number_channels), dtype=np.complex128)
    for isnap in range(0, channel_tensor.get_number_of_snapshots()):
        xx = X[isnap, :, ifreq]
        Rhat += np.outer(xx, xx.T.conjugate())
    Rhat = Rhat / channel_tensor.get_number_of_snapshots()
    return Rhat


class CSSingleSnapshot:
    @staticmethod
    def sparse_policy_all(sample_size: int) -> int:
        """max number of targets equals number of channels"""
        return sample_size

    @staticmethod
    def sparse_policy_save(sample_size: int) -> int:
        """max number of targets equals about half the number of channels"""
        return max(1, int(sample_size / 2 - 1))

    def __init__(
        self,
        kind: str,
        vmin: float,
        vmax: float,
        nsamples: int,
        virtual_array_positions,
        k0: float,
        second_dim_angle: float,
        coordinate_system=SphericalCoordinateSystem(),
        sparse_policy=sparse_policy_save,
    ):
        """
        Parameters
        ----------
        algorithm_name : string
                name of algorithm that will be used
        kind: string
                "theta" or "phi"
        vmin : float
                minimal scan angle in rad
        vmax : float
                maximal scan angle in rad
        nsamples : int
                number of angles
        virtual_array_positions : 2Darray(float)
                position vectors of virtual array consistent with setup used
                for calculation of correlation matrix
        k0 : float
                base frequency for RADAR
        second_dim_angle : float
                value of second angle of line along which scan is conducted.
                This angle is kept constant during the scan.
        coordinate_system : Coordinate system object
                Coordinate system used for definition of scan angles.
        sparse_policy : function
                Estimate sparseness based on number of samples, this is the
                maximal number of targets that can be detected
        """

        self.scan_var = kind
        self.scan_var_min = vmin
        self.scan_var_max = vmax
        self.scan_var_samples = nsamples
        self.virtual_array_positions = k0 * virtual_array_positions
        self.second_dim_angle = second_dim_angle
        # coordinate system
        self.Uhat = coordinate_system.Uhat
        self.Vhat = coordinate_system.Vhat
        self.What = coordinate_system.What
        self.coordinate_system = coordinate_system
        self.sparse_policy = sparse_policy
        self.compile()

    def get_algorithm_name(self):
        return "compressed sensing OMP"

    def get_number_virtual_channels(self):
        return len(self.virtual_array_positions)

    def get_number_of_angles(self):
        return self.scan_var_samples

    def get_scan_vars_degree(self):
        return self.angles * 360.0 / (2.0 * np.pi)

    def compile(self):
        """
        Compile scan angles and scan directions according to the specified information in construcor.
        """
        self.angles = np.linspace(
            self.scan_var_min, self.scan_var_max, self.scan_var_samples
        )
        if self.scan_var == "phi":
            theta = self.second_dim_angle
            self.scan_vector = lambda phi: self.coordinate_system.get_unit_vector(
                theta, phi
            )
            phi = self.angles
            U = self.coordinate_system.get_unit_vector_component(0, theta, phi)
            V = self.coordinate_system.get_unit_vector_component(1, theta, phi)
            W = self.coordinate_system.get_unit_vector_component(2, theta, phi)
            scan_direction_matrix = (
                np.outer(self.Uhat, U) + np.outer(self.Vhat, V) + np.outer(self.What, W)
            )
            self.scan_matrix = np.exp(
                1j * np.dot(self.virtual_array_positions, scan_direction_matrix)
            )
        elif self.scan_var == "theta":
            phi = self.second_dim_angle
            self.scan_vector = lambda theta: self.coordinate_system.get_unit_vector(
                theta, phi
            )
            theta = self.angles
            U = self.coordinate_system.get_unit_vector_component(0, theta, phi)
            V = self.coordinate_system.get_unit_vector_component(1, theta, phi)
            W = self.coordinate_system.get_unit_vector_component(2, theta, phi)
            scan_direction_matrix = (
                np.outer(self.Uhat, U) + np.outer(self.Vhat, V) + np.outer(self.What, W)
            )
            self.scan_matrix = np.exp(
                1j * np.dot(self.virtual_array_positions, scan_direction_matrix)
            )
        else:
            raise ValueError("kind != phi or theta")

    def execute(self, channel_snapshot):
        """
        calculate the angle spectrum from a channel snapshot
        """
        max_targets = self.sparse_policy(self.scan_matrix.shape[0])
        eps = np.linalg.norm(channel_snapshot) * 1e-1
        spectrum, _, _ = omp.solve(self.scan_matrix, channel_snapshot, max_targets, eps)
        spectrum = spectrum + 1e-20
        return spectrum


class SpectralAlgorithm:
    def __init__(
        self,
        algorithm_name,
        kind,
        vmin,
        vmax,
        nsamples,
        virtual_array_positions,
        k0,
        second_dim_angle,
        coordinate_system=SphericalCoordinateSystem(),
        spectral_loading=0.0,
    ):
        """
        Parameters
        ----------
        algorithm_name : string
                name of algorithm that will be used
        kind: string
                "theta" or "phi"
        vmin : float
                minimal scan angle in rad
        vmax : float
                maximal scan angle in rad
        nsamples : int
                number of angles
        virtual_array_positions : 2Darray(float)
                position vectors of virtual array consistent with setup used for calculation of correlation matrix
        k0 : float
                base frequency for RADAR
        second_dim_angle : float
                value of second angle of line along which scan is conducted.
                This angle is kept constant during the scan.
        coordinate_system : Coordinate system object
                Coordinate system used for definition of scan angles.
        spectral_loading : float
                diagonal loading factor of covariance matrix for algorithm
        """
        # coordinate system
        self.Uhat = coordinate_system.Uhat
        self.Vhat = coordinate_system.Vhat
        self.What = coordinate_system.What
        self.coordinate_system = coordinate_system
        #
        self.algorithm_name = algorithm_name
        self.scan_var = kind
        self.scan_var_min = vmin
        self.scan_var_max = vmax
        self.scan_var_samples = nsamples
        self.virtual_array_positions = k0 * virtual_array_positions
        self.second_dim_angle = second_dim_angle
        self.spectral_loading = None
        self.sigma = 0
        if isinstance(spectral_loading, float):
            self.sigma = spectral_loading
        else:
            raise ValueError("Unrecognised diagonal loading argument")

    def get_algorithm_name(self):
        return self.algorithm_name

    def get_number_virtual_channels(self):
        return len(self.virtual_array_positions)

    def get_number_of_angles(self):
        return self.scan_var_samples

    def get_scan_vars_degree(self):
        return self.angles * 360.0 / (2.0 * np.pi)

    def get_sigma_regularization_factor(self):
        """Factor for regularizing the covariance matrix"""
        return self.sigma

    def set_sigma_regularization_factor(self, sigma):
        """Set factor for regularizing the covariance matrix"""
        self.sigma = sigma

    def set_second_dim_angle(self, angle):
        """Set vaue of angle coordinate of second dimension (along which no scan is conducted)"""
        self.second_dim_angle = angle


class FourierSingleSnapshot:
    def __init__(
        self,
        kind: str,
        vmin: float,
        vmax: float,
        nsamples: int,
        virtual_array_positions,
        k0: float,
        second_dim_angle: float,
        coordinate_system=SphericalCoordinateSystem(),
    ):
        """
        Parameters
        ----------
        kind: string
                "theta" or "phi"
        vmin : float
                minimal scan angle in rad
        vmax : float
                maximal scan angle in rad
        nsamples : int
                number of angles
        virtual_array_positions : 2Darray(float)
                position vectors of virtual array consistent with setup used for calculation of correlation matrix
        k0 : float
                base frequency for RADAR
        second_dim_angle : float
                value of second angle of line along which scan is conducted.
                This angle is kept constant during the scan.
        coordinate_system : Coordinate system object
                Coordinate system used for definition of scan angles.
        """

        self.scan_var = kind
        self.scan_var_min = -90
        self.scan_var_max = 90
        self.scan_var_samples = nsamples
        self.lambda0 = 2 * np.pi / k0
        self.virtual_array_positions = k0 * virtual_array_positions
        self.delta = np.linalg.norm(
            virtual_array_positions[1] - virtual_array_positions[0]
        )
        self.second_dim_angle = second_dim_angle
        self.angles_deg = None
        # coordinate system
        self.Uhat = coordinate_system.Uhat
        self.Vhat = coordinate_system.Vhat
        self.What = coordinate_system.What
        self.coordinate_system = coordinate_system

    def get_algorithm_name(self):
        return "Fourier"

    def get_number_virtual_channels(self):
        return len(self.virtual_array_positions)

    def get_number_of_angles(self):
        return self.scan_var_samples

    def get_scan_vars_degree(self):
        return self.angles_deg

    def execute(self, channel_snapshot):
        """
        calculate the angle spectrum from a channel snapshot
        """
        ws = channel_snapshot * windows.hann(len(channel_snapshot))
        nbins = self.scan_var_samples
        pad = int(((nbins - len(ws)) / 2))
        wsp = np.pad(ws, ((pad, nbins - pad - len(ws))), mode="constant")
        angle_spectrum = ifftshift(ifft(wsp))
        iangle = fftshift(fftfreq(len(wsp), d=1.0 / len(wsp)))
        if self.angles_deg is None:
            self.angles_deg = -np.rad2deg(
                np.arcsin(self.lambda0 / self.delta * iangle / len(iangle))
            )
        return angle_spectrum


class BartlettAlgorithm(SpectralAlgorithm):
    def __init__(
        self,
        kind,
        vmin,
        vmax,
        nsamples,
        virtual_array_positions,
        k0,
        second_dim_angle,
        coordinate_system=SphericalCoordinateSystem(),
    ):
        """
        Parameters
        ----------
        kind: string
                "theta" or "phi"
        vmin : float
                minimal scan angle in rad
        vmax : float
                maximal scan angle in rad
        nsamples : int
                number of angles
        virtual_array_positions : 2Darray(float)
                position vectors of virtual array consistent with setup used for calculation of correlation matrix
        k0 : float
                base frequency for RADAR
        second_dim_angle : float
                value of second angle of line along which scan is conducted.
                This angle is kept constant during the scan.
        coordinate_system : Coordinate system object
                Coordinate system used for definition of scan angles.
        """
        super().__init__(
            "Bartlett",
            kind,
            vmin,
            vmax,
            nsamples,
            virtual_array_positions,
            k0,
            second_dim_angle,
            coordinate_system,
        )
        #
        self.compile()

    def compile(self):
        """
        Compile scan angles and scan directions according to the specified information in construcor.
        """
        self.angles = np.linspace(
            self.scan_var_min, self.scan_var_max, self.scan_var_samples
        )
        if self.scan_var == "phi":
            theta = self.second_dim_angle
            self.scan_vector = lambda phi: self.coordinate_system.get_unit_vector(
                theta, phi
            )
            phi = self.angles
            U = self.coordinate_system.get_unit_vector_component(0, theta, phi)
            V = self.coordinate_system.get_unit_vector_component(1, theta, phi)
            W = self.coordinate_system.get_unit_vector_component(2, theta, phi)
            scan_direction_matrix = (
                np.outer(self.Uhat, U) + np.outer(self.Vhat, V) + np.outer(self.What, W)
            )
            self.scan_matrix = np.exp(
                1j * np.dot(self.virtual_array_positions, scan_direction_matrix)
            )
        elif self.scan_var == "theta":
            phi = self.second_dim_angle
            self.scan_vector = lambda theta: self.coordinate_system.get_unit_vector(
                theta, phi
            )
            theta = self.angles
            U = self.coordinate_system.get_unit_vector_component(0, theta, phi)
            V = self.coordinate_system.get_unit_vector_component(1, theta, phi)
            W = self.coordinate_system.get_unit_vector_component(2, theta, phi)
            scan_direction_matrix = (
                np.outer(self.Uhat, U) + np.outer(self.Vhat, V) + np.outer(self.What, W)
            )
            self.scan_matrix = np.exp(
                1j * np.dot(self.virtual_array_positions, scan_direction_matrix)
            )
        else:
            raise ValueError("kind != phi or theta")

    def execute(self, Rhat):
        """
        loop version for debugging and verification
        """
        Rhat += self.sigma * np.identity(Rhat.shape[0], dtype=np.complex128)
        res = np.zeros(self.scan_var_samples, dtype=np.complex128)
        for iangle, angle in enumerate(self.angles):
            tmp = np.dot(self.virtual_array_positions, self.scan_vector(angle))
            a = np.exp(1j * tmp)
            res[iangle] = np.dot(a.conjugate().T, np.dot(Rhat, a)) / np.dot(
                a.conjugate().T, a
            )
        return res

    def executev(self, Rhat):
        """
        vectorized version for performance
        """
        return self.execute(Rhat)
        #  Rhat +=  self.sigma*np.identity(Rhat.shape[0], dtype=np.complex128)
        #  tmp = np.dot(Rhat,self.scan_matrix)
        #  res = np.einsum('ij,ij->j', self.scan_matrix.conjugate(), tmp)
        #  return res


class MVDRAlgorithm(SpectralAlgorithm):

    def __init__(
        self,
        kind,
        vmin,
        vmax,
        nsamples,
        virtual_array_positions,
        k0,
        second_dim_angle,
        coordinate_system=SphericalCoordinateSystem(),
    ):
        """
        Parameters
        ----------
        kind: string
                "theta" or "phi"
        vmin : float
                minimal scan angle in rad
        vmax : float
                maximal scan angle in rad
        nsamples : int
                number of angles
        virtual_array_positions : 2Darray(float)
                position vectors of virtual array consistent with setup used for calculation of correlation matrix
        k0 : float
                base frequency for RADAR
        second_dim_angle : float
                value of second angle of line along which scan is conducted.
                This angle is kept constant during the scan.
        coordinate_system : coordinate_system object
                Coordinate system used for definition of scan angles
        """
        super().__init__(
            "MVDR",
            kind,
            vmin,
            vmax,
            nsamples,
            virtual_array_positions,
            k0,
            second_dim_angle,
            coordinate_system,
        )
        #
        self.compile()

    def compile(self):
        """
        Compile scan angles and scan directions according to the specified information in construcor.
        """
        self.angles = np.linspace(
            self.scan_var_min, self.scan_var_max, self.scan_var_samples
        )
        if self.scan_var == "phi":
            theta = self.second_dim_angle
            self.scan_vector = lambda phi: self.coordinate_system.get_unit_vector(
                theta, phi
            )
            phi = self.angles
            U = self.coordinate_system.get_unit_vector_component(0, theta, phi)
            V = self.coordinate_system.get_unit_vector_component(1, theta, phi)
            W = self.coordinate_system.get_unit_vector_component(2, theta, phi)
            scan_direction_matrix = (
                np.outer(self.coordinate_system.Uhat, U)
                + np.outer(self.coordinate_system.Vhat, V)
                + np.outer(self.coordinate_system.What, W)
            )
            self.scan_matrix = np.exp(
                1j * np.dot(self.virtual_array_positions, scan_direction_matrix)
            )
        elif self.scan_var == "theta":
            phi = self.second_dim_angle
            self.scan_vector = lambda theta: self.coordinate_system.get_unit_vector(
                theta, phi
            )
            theta = self.angles
            U = self.coordinate_system.get_unit_vector_component(0, theta, phi)
            V = self.coordinate_system.get_unit_vector_component(1, theta, phi)
            W = self.coordinate_system.get_unit_vector_component(2, theta, phi)
            scan_direction_matrix = (
                np.outer(self.coordinate_system.Uhat, U)
                + np.outer(self.coordinate_system.Vhat, V)
                + np.outer(self.coordinate_system.What, W)
            )
            self.scan_matrix = np.exp(
                1j * np.dot(self.virtual_array_positions, scan_direction_matrix)
            )
        else:
            raise ValueError("kind != phi or theta")

    def execute_loop(self, Rhat):
        """
        loop version
        """
        Rhat += self.sigma * np.identity(Rhat.shape[0], dtype=np.complex128)
        res = np.zeros(self.scan_var_samples, dtype=np.complex128)
        Rinv = np.linalg.inv(Rhat)
        for iangle, angle in enumerate(self.angles):
            tmp = np.dot(self.virtual_array_positions, self.scan_vector(angle))
            a = np.exp(1j * tmp)
            res[iangle] = np.vdot(a, a) / np.dot(a.conjugate().T, np.dot(Rinv, a))
        return res

    def execute_vectorized(self, Rhat):
        """
        vectorized version
        """
        Rhat += self.sigma * np.identity(Rhat.shape[0], dtype=np.complex128)
        RhatInv = np.linalg.inv(Rhat)
        tmp = np.dot(RhatInv, self.scan_matrix)
        res = 1.0 / np.einsum("ij,ij->j", self.scan_matrix.conjugate(), tmp)
        return res

    def execute(self, Rhat):
        return self.execute_loop(Rhat)


class MUSICAlgorithm(SpectralAlgorithm):
    """
    Implemetation of MUSIC spectral algorithm in order to determine pseudo spectrum of objects' locations by calculating
    spectra using a sub-space method.
    """

    def __init__(
        self,
        kind,
        vmin,
        vmax,
        nsamples,
        virtual_array_positions,
        k0,
        second_dim_angle,
        number_objects,
        threshhold=0,
        coordinate_system=SphericalCoordinateSystem(),
    ):
        """
        Parameters
        ----------
        kind: string
                "theta" or "phi"
        vmin : float
                minimal scan angle in rad
        vmax : float
                maximal scan angle in rad
        nsamples : int
                number of angles
        virtual_array_positions : 2Darray(float)
                position vectors of virtual array consistent with setup used for calculation of correlation matrix
        k0 : float
                base frequency for RADAR
        second_dim_angle : float
                value of second angle of line along which scan is conducted.
                This angle is kept constant during the scan.
        number_objects : int
                number of objects the algorithm shall detect
        coordinate_system : Coordinate system object
                Coordinate system used for definition of scan angles.
        """
        super().__init__(
            "MUSIC",
            kind,
            vmin,
            vmax,
            nsamples,
            virtual_array_positions,
            k0,
            second_dim_angle,
            coordinate_system,
        )
        #
        self.number_objects = number_objects
        self.threshhold = threshhold
        self.compile()

    def compile(self):
        """
        Compile scan angles and scan directions according to the specified information in construcor.
        """
        self.angles = np.linspace(
            self.scan_var_min, self.scan_var_max, self.scan_var_samples
        )
        if self.scan_var == "phi":
            theta = self.second_dim_angle
            self.scan_vector = lambda phi: self.coordinate_system.get_unit_vector(
                theta, phi
            )
            phi = self.angles
        elif self.scan_var == "theta":
            phi = self.second_dim_angle
            self.scan_vector = lambda theta: self.coordinate_system.get_unit_vector(
                theta, phi
            )
            theta = self.angles
        else:
            raise ValueError("kind != phi or theta")

    def execute_loop_svd(self, Rhat):
        """
        loop version for debugging and verification - SVD based
        """
        u, s, vh = np.linalg.svd(Rhat, full_matrices=True)
        s[0 : self.number_objects + 1] = 0e-6
        s[self.number_objects :] = 1.0
        G = np.dot(u, np.dot(np.diag(s), vh))
        res = np.zeros(self.scan_var_samples, dtype=np.complex128)
        if np.linalg.norm(Rhat) < self.threshhold:
            return self.threshhold * np.ones(self.scan_var_samples, dtype=np.complex128)
        for iangle, angle in enumerate(self.angles):
            tmp = np.dot(self.virtual_array_positions, self.scan_vector(angle))
            a = np.exp(1j * tmp)
            res[iangle] = np.dot(a.conjugate().T, a) / np.dot(
                a.conjugate().T, np.dot(G, a)
            )
        return res

    def execute_loop(self, Rhat):
        """
        loop version for debugging and verification
        """
        eval, evec = np.linalg.eigh(Rhat)
        nsort = np.argsort(eval)[::-1]  # get indices that would sort the array
        # projector matrix to noise space
        evec = evec[:, nsort[self.number_objects :]].conjugate().T
        res = np.zeros(self.scan_var_samples, dtype=np.complex128)
        if np.linalg.norm(Rhat) < self.threshhold:
            return self.threshhold * np.ones(self.scan_var_samples, dtype=np.complex128)
        for iangle, angle in enumerate(self.angles):
            tmp = np.dot(self.virtual_array_positions, self.scan_vector(angle))
            a = np.exp(1j * tmp)
            res[iangle] = np.dot(a.conjugate().T, a) / np.power(
                np.linalg.norm(evec @ a), 2
            )
        return res

    def execute_vectorized(self, Rhat):
        """
        vectorized version for performance
        """
        # TODO implement
        return self.execute_loop(Rhat)

    def execute(self, Rhat):
        return self.execute_loop(Rhat)
