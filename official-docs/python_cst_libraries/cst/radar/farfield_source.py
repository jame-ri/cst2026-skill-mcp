# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

"""
Module for the processing of far field source related data
"""

from __future__ import annotations
from typing import Union, Tuple
import numpy as np


class FarFieldSource:
    """
    FarFieldSource class for loading far field source data from file in
    (.ffs) format and access derived data.
    """
    @classmethod
    def fromfile(self, file_name: str) -> FarFieldSource:
        from _cst_radar import FarfSource
        return FarFieldSource(farf=FarfSource.fromfile(file_name))

    def __init__(self, farf=None):
        if (farf):
            self._farf = farf
        else:
            raise TypeError(
                "Cannot create 'FarFieldSource' instances. Please use the 'from_file' class method instead.")

    def __str__(self):
        return 'origin {}\n U {} V {} W {}\n frequencies {} Hz'.format(
            self.coordinate_system_origin(),
            self.coordinate_system_U(),
            self.coordinate_system_V(),
            self.coordinate_system_W(),
            self.frequencies())

    def coordinate_system_origin(self) -> np.ndarray:
        """
        position of far field source that is the origin of the local coordiante system
        """
        return self._farf.coordinate_system_origin()

    def coordinate_system_U(self) -> np.ndarray:
        """
        U axis of far field source local coordiante system
        """
        return self._farf.coordinate_system_U()

    def coordinate_system_V(self) -> np.ndarray:
        """
        V axis of far field source local coordiante system
        """
        return self._farf.coordinate_system_V()

    def coordinate_system_W(self) -> np.ndarray:
        """
        W axis of far field source local coordiante system
        """
        return self._farf.coordinate_system_W()

    def frequencies(self) -> np.ndarray:
        """
        Frequencies at which the far field source is defined
        """
        return self._farf.frequencies()

    def compute_E(self, position: np.ndarray) -> np.ndarray:
        """
        Electric field strength at position for each defined frequency

        Parameters
        ----------
        position: np.ndarray((3),dtype=float)

        Returns:
        --------
        np.ndarray((nfreq, 3), dtype=np.complex128)
            electric field strength
        """
        return self._farf.compute_E(position)

    def compute_H(self, position: np.ndarray) -> np.ndarray:
        """
        Magnetic field strength at position for each defined frequency

        Parameters
        ----------
        position: np.ndarray((3),dtype=float)

        Returns:
        --------
        np.ndarray((nfreq, 3), dtype=np.complex128)
            magnetic field strength
        """
        return self._farf. compute_H(position)

    def compute_EH(self, position: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Elecric and Magnetic field strength at position for each defined frequency

        Parameters
        ----------
        position: np.ndarray((3),dtype=float)

        Returns:
        --------
        List[np.ndarray((nfreq, 3), dtype=np.complex128), np.ndarray((nfreq, 3), dtype=np.complex128)]
            magnetic field strength
        """
        return self._farf.compute_EH(position)

    def compute_pattern_angles_E(self, thetas: np.ndarray,
                                 phis: np.ndarray,
                                 apply_translation: bool = False) -> np.ndarray:
        """
        Elecric field strength pattern at direction given in local coordinate system via angles

        Parameters
        ----------
        thetas: np.ndarray((ntheta),dtype=float)
            theta angles in local coordinate system
        phis: np.ndarray((nphi),dtype=float)
            phi angles in local coordinate system
        Returns:
        --------
        np.ndarray((ifreq, nthetea, nphi, l)
            field pattern tensor[ifrequency, itheta, iphi, l]
            ifrequency: frequency index
            itheta: theta index
            iphi: phi index
            l: Eth for l=0, Ephi for l=1
        """
        return self._farf.compute_pattern_angles_E(thetas, phis,
                                                   apply_translation)

    def compute_pattern_dirs_E(self, dirs: np.ndarray,
                               apply_translation: bool = False) -> np.ndarray:
        """
        Elecric field strength pattern at direction given in local coordinate system via direction vector

        Parameters
        ----------
        dirs: np.ndarray((nobs, 3),dtype=float)
            tensor of direction vectors
        Returns:
        --------
        np.ndarray(()
            field pattern tensor[ifrequency, iobs, l]
            ifrequency: frequency index
            iobs: direction vector index
            l: Eth for l=0, Ephi for l=1
        """
        return self._farf.compute_pattern_dirs_E()

    def get_radiated_powers(self) -> np.ndarray:
        """
        Radiated Power

        Returns:
        --------
        np.ndarray((nfreq),dtype=np.float)
            Radiated power for each frequency
        """
        return self._farf.get_radiated_powers()

    def get_accepted_powers(self) -> Union[np.ndarray, None]:
        """
        Accepted Power

        Returns:
        --------
        np.ndarray((nfreq),dtype=np.float) or None
            If defined accepted power for each frequency otherwise None
        """
        return self._farf.get_accepted_powers()

    def get_stimulated_powers(self) -> Union[np.ndarray, None]:
        """
        Stimulated Power

        Returns:
        --------
        np.ndarray((nfreq),dtype=np.float) or None
            If defined stimulated power for each frequency otherwise None
        """
        return self._farf.get_stimulated_powers()

    def scale(self, factor: complex) -> None:
        """
        Scale the far field source pattern

        Parameter
        ---------
        scale: complex
            Scales field by scale
        """
        return self._farf.scale(factor)

    def translate_origin(self, shift: np.ndarray) -> None:
        """
        Translate the origin of the far field source

        Parameter
        ---------
        shift: np.ndarray((3), dtype=np.float)
            Translates the origin of the far field source by shift
        """
        return self._farf.translate_origin(shift)

    def rotate_pattern(self, axes: np.ndarray, angle: float) -> None:
        """
        Rotates the local far field source coordinate system

        Parameter
        ---------
        axes: np.ndarray((3), dtype=np.float)
            Rotation axis
        angle: float
            Rotation angles around axis in radian
        """
        return self._farf.rotate_pattern(axes, angle)
