# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

r"""
MIMO RADAR
"""

import typing
import pickle
from abc import ABC, abstractmethod
from pathlib import Path
import warnings
import math
import numpy as np
import numpy.typing as npt
import scipy as sc

try:
    # import cupyx as cpx
    import cupyx.scipy as spx
    import cupy as cp
    import cupyx.signal as cpsignal  # workaround making signal module available

    _ = cp.array([1.0])  # trigger potential error when no GPU available
    xp_backend = "cupy"
except ImportError as error:
    # CPU fallback
    import numpy as cp
    import scipy as cpx

    xp_backend = "numpy"
    warnings.warn(
        "Failed importing CuPy. Falling back to NumPy/SciPy. GPU not available"
    )
from scipy.signal import windows as wd
from .physical_constants import c0
from .channel_tensor import ChannelTensor
from .coordinate_systems import (
    CoordinateSystem,
    ElOverAzCoordinateSystem,
    SensorCoordinateSystem1,
)
from .spectral_algorithms import (
    create_virtual_antenna_matrix,
    CSSingleSnapshot,
    FourierSingleSnapshot,
    MVDRAlgorithm,
)
from cst.interface import DesignEnvironment, get_current_project
from cst.interface import get_current_project


class AntennaEntry:
    id_counter: typing.ClassVar[int] = 0

    def __init__(
        self,
        source_name: str,
        ffs_file_name: str,
        position: npt.NDArray[np.float64],
        orientation_U: npt.NDArray[np.float64] = np.array([1, 0, 0]),
        orientation_W: npt.NDArray[np.float64] = np.array([0, 0, 1]),
        ffs_id: int = None,
    ):
        self.source_name = source_name
        self.ffs_file_name = ffs_file_name
        self.position = position
        self.orientation_U = orientation_U
        self.orientation_W = orientation_W
        if ffs_id:
            self.id = ffs_id
        else:
            self.id = AntennaEntry.id_counter
            AntennaEntry.id_counter += 1

    def get_source_name(self) -> str:
        return self.source_name

    def get_ffs_file_name(self) -> str:
        return self.ffs_file_name

    def get_position(self) -> npt.NDArray[np.float64]:
        return self.position

    def get_orientation_U(self) -> npt.NDArray[np.float64]:
        return self.orientation_U

    def get_orientation_W(self) -> npt.NDArray[np.float64]:
        return self.orientation_W

    def get_id(self) -> int:
        return self.id

    def __hash__(self):
        return hash(
            (
                self.source_name,
                self.ffs_file_name,
                str(self.position),
                str(self.orientation_U),
                str(self.orientation_W),
                id,
            )
        )


class MIMOAntennaArray:
    r"""
    Basic MIMO Class
    """

    def __init__(
        self,
        Txs: typing.List[AntennaEntry],
        Rxs: typing.List[AntennaEntry],
        k0design: float,
        coordinate_system: CoordinateSystem,
    ):
        self.Txs = Txs
        self.Rxs = Rxs
        self.k0desgin = k0design
        self.channel_dict = dict()
        self.txrx_to_channel_dict = dict()
        NTx = len(Txs)
        NRx = len(Rxs)
        #
        virtual_antenna_matrix = np.zeros((NTx * NRx, 3), dtype=np.complex128)
        ichannel = 0
        for tx in Txs:
            for rx in Rxs:
                self.channel_dict[ichannel] = (tx, rx)
                self.txrx_to_channel_dict[(tx, rx)] = ichannel
                virtual_antenna_matrix[ichannel, :] = (
                    tx.get_position() + rx.get_position()
                )
                ichannel += 1
        self.virtual_antenna_matrix = virtual_antenna_matrix
        #
        self.coordinate_system = coordinate_system

    @staticmethod
    def __virtual_array_center_point(Txs, Rxs):
        r_center_mass = np.array([0, 0, 0])
        icnt = 0
        for atx in Txs:
            for arx in Rxs:
                r_virtual = atx.get_position() + arx.get_position()
                r_center_mass = r_center_mass + r_virtual
                icnt += 1
        return r_center_mass / icnt

    @staticmethod
    def __virtual_array_directions(Txs, Rxs, k0):
        ntx = len(Txs)
        nrx = len(Rxs)
        nvirt = ntx * nrx
        pnts = np.zeros((3, nvirt))
        ivirt = 0
        for atx in Txs:
            for arx in Rxs:
                pnts[ivirt, :] = k0 * (atx.get_position() + arx.get_position())
                ivirt += 1
        U, S, Vt = np.linalg.svd(pnts)
        if np.linalg.norm(S) < 1e-9:
            raise ValueError("antenna array seems to be zero dimensional")
        S = S / S[0]
        dirs = []
        dirs.append(U[:, 0])
        if S[1] > 0.01:
            dirs.append(U[:, 1])
        if S[2] > 0.01:
            dirs.append(U[:, 2])
        return dirs

    @classmethod
    def from_pickled(cls, file_name: typing.Union[str, Path]):
        r"""accesses the currently open *.cst project"""
        file_name = Path(file_name)
        if not file_name.exists():
            raise FileExistsError("file `{}` does not exists".format(file_name))
        try:
            with open(file_name, "rb") as f:
                obj = pickle.load(f)
            if not isinstance(obj, cls):
                raise TypeError(
                    f"Expected instance of {cls.__name__}, got {type(obj).__name__}"
                )
            return obj
        except (pickle.PickleError, IOError, EOFError) as e:
            raise ValueError("error reading file: {}", e)

    def save_pickled(self, file_name: typing.Union[str, Path]):
        with open(file_name, "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)

    def get_txs(self) -> typing.List[AntennaEntry]:
        return self.Txs

    def get_rxs(self) -> typing.List[AntennaEntry]:
        return self.Rxs

    def get_channel_dict(self):
        return self.channel_dict

    def get_txrx_from_channel(self, channel: int):
        return self.channel_dict[channel]

    def get_txrx_dict(self):
        return self.txrx_to_channel_dict

    def get_channel_from_txrx(self, txrx: typing.Tuple[AntennaEntry, AntennaEntry]):
        return self.txrx_to_channel_dict[txrx]

    def get_k0design(self) -> float:
        r"""wave number k0 for which the array is designed"""
        return self.k0desgin

    def get_coordinate_system(self) -> CoordinateSystem:
        r"""coordinate system associated with the mimo array"""
        return self.coordinate_system

    def get_virtual_antenna_matrix(self) -> npt.NDArray[np.complex128]:
        return self.virtual_antenna_matrix

    @classmethod
    def from_cst_file(cst_file):
        raise NotImplementedError("feature not implemented")

    @classmethod
    def from_layout(
        cls,
        design_frequency_Hz: float,
        tx_ffs_files: typing.List[str],
        rx_ffs_files: typing.List[str],
        tx_positions: typing.List[npt.NDArray[np.float64]],
        rx_positions: typing.List[npt.NDArray[np.float64]],
        coordinate_system: typing.Union[CoordinateSystem, None] = None,
    ):
        """
        Arbitrary Layout
        """
        if len(tx_ffs_files) < 1:
            raise ValueError("tx_ffs_files list is empty")
        if len(rx_ffs_files) < 1:
            raise ValueError("rx_ffs_files list is empty")
        if len(tx_positions) < 1:
            raise ValueError("tx_positions list is empty")
        if len(rx_positions) < 1:
            raise ValueError("rx_positions list is empty")

        Tx = []
        for itx, ffs_file in enumerate(tx_ffs_files):
            Tx.append(AntennaEntry("Tx{}".format(itx), ffs_file, tx_positions[itx]))
        Rx = []
        for irx, ffs_file in enumerate(rx_ffs_files):
            Rx.append(AntennaEntry("Rx{}".format(irx), ffs_file, rx_positions[irx]))
        k0design = 2 * np.pi * c0 / design_frequency_Hz
        return cls(Tx, Rx, k0design, coordinate_system)

    @classmethod
    def from_general_homogeneous_1d_layout(
        cls,
        design_frequency_Hz: float,
        tx_ffs_files: typing.List[str],
        rx_ffs_files: typing.List[str],
        origin: npt.NDArray[np.float64],
        array_axis: npt.NDArray[np.float64],
        radiation_axis: npt.NDArray[np.float64],
        tx_rx_gap_in_wavelength: float = 1.0,
        coordinate_system_class=ElOverAzCoordinateSystem,
    ):
        """
        Classical lambda/2 design 1d layout
        +  +  +   ++++

        """
        if len(tx_ffs_files) < 1:
            raise ValueError("tx_ffs_files list is empty")
        if len(rx_ffs_files) < 1:
            raise ValueError("tx_ffs_files list is empty")
        if np.abs(np.linalg.norm(array_axis) - 1) < 1e-5:
            raise ValueError("direction has to be a unit vector")

        # labeling Tx
        lambda_half = 0.5 * c0 / design_frequency_Hz
        Tx = []
        nRx = len(rx_ffs_files)
        tx_pos = None
        itx = 0

        for ffs_file in tx_ffs_files:
            tx_pos = origin + itx * (nRx - 0.5) * lambda_half * array_axis
            Tx.append(AntennaEntry("Tx{}".format(itx), ffs_file, tx_pos))
            itx += 1
        Rx = []
        irx = 0
        rx_pos_start = tx_pos + 2 * lambda_half * tx_rx_gap_in_wavelength * array_axis
        for ffs_file in rx_ffs_files:
            rx_pos = rx_pos_start + irx * lambda_half * array_axis
            Rx.append(AntennaEntry("Rx{}".format(irx), ffs_file, rx_pos))
            irx += 1
        k0design = 2 * np.pi * c0 / design_frequency_Hz
        What = radiation_axis / np.linalg.norm(radiation_axis)
        Uhat = array_axis / np.linalg.norm(array_axis)
        Vhat = np.cross(radiation_axis, array_axis)
        Vhat = Vhat / np.linalg.norm(Vhat)
        coordinate_system = coordinate_system_class(
            origin=origin, Uhat=Uhat, Vhat=Vhat, What=What
        )
        return cls(Tx, Rx, k0design, coordinate_system)

    @classmethod
    def from_homogeneous_1d_layout(
        cls,
        design_frequency_Hz: float,
        ffs_file: str,
        tx_number: int,
        rx_number: int,
        origin: npt.NDArray[np.float64],
        array_axis: npt.NDArray[np.float64],
        radiation_axis: npt.NDArray[np.float64],
        tx_rx_gap_in_wavelength: float = 1.0,
        coordinate_system_class=ElOverAzCoordinateSystem,
    ):
        """
        Classical lambda/2 design 1d layout
        +  +  +   ++++

        """
        if tx_number < 1:
            raise ValueError("tx_number > 0 required")
        if rx_number < 1:
            raise ValueError("rx_number > 0 required")
        if np.abs(np.linalg.norm(radiation_axis) - 1) > 1e-5:
            raise ValueError("radiation_axis has to be a unit vector")
        if np.abs(np.linalg.norm(array_axis) - 1) > 1e-5:
            raise ValueError("array_axis has to be a unit vector")
        # if (not Path.exists(ffs_file)):
        #     print("file {} not found".format(ffs_file))

        # labeling Tx
        lambda_half = 0.5 * c0 / design_frequency_Hz
        Tx = []
        nRx = rx_number
        tx_pos = None
        for itx in range(0, tx_number):
            tx_pos = origin + itx * (nRx - 0.5) * lambda_half * array_axis
            Tx.append(AntennaEntry("Tx{}".format(itx), ffs_file, tx_pos))
        Rx = []
        rx_pos_start = tx_pos + 2 * lambda_half * tx_rx_gap_in_wavelength * array_axis
        for irx in range(0, rx_number):
            rx_pos = rx_pos_start + irx * lambda_half * array_axis
            Rx.append(AntennaEntry("Rx{}".format(irx), ffs_file, rx_pos))
        k0design = 2 * np.pi * design_frequency_Hz / c0
        What = radiation_axis
        Uhat = array_axis
        Vhat = np.cross(radiation_axis, array_axis)
        Vhat = Vhat / np.linalg.norm(Vhat)
        coordinate_system = coordinate_system_class(
            origin=origin, Uhat=Uhat, Vhat=Vhat, What=What
        )
        return cls(Tx, Rx, k0design, coordinate_system)


class Radar(ABC):
    """
    Basic RADAR Class
    """

    @abstractmethod
    def get_solver_fmin_Hz(self) -> float:
        pass

    @abstractmethod
    def get_solver_fmax_Hz(self) -> float:
        pass

    @abstractmethod
    def get_solver_max_range_m(self) -> float:
        pass

    @abstractmethod
    def get_radar_max_range_m(self) -> float:
        pass

    @abstractmethod
    def get_radar_range_resolution_m(self) -> float:
        pass

    @abstractmethod
    def get_radar_max_velocity_mps(self) -> float:
        pass

    @abstractmethod
    def get_radar_velocity_resolution_mps(self) -> float:
        pass

    @abstractmethod
    def get_simulation_time_parameters(self) -> npt.NDArray[np.float64]:
        pass

    @abstractmethod
    def get_parametersweep_cpi_indices(self) -> typing.List[typing.List[int]]:
        pass

    @abstractmethod
    def get_MIMO(self) -> MIMOAntennaArray:
        pass


class PulsedMimoRadar(Radar):

    def __init__(
        self,
        pulse_fmin_Hz: float,
        pulse_fmax_Hz: float,
        pulse_window: typing.Callable[[int], npt.ArrayLike],
        pulse_repetition_rate_Hz: float,
        frame_number_waveforms_in_frame: int,
        frame_time_s: float,
        frames_requested: npt.ArrayLike,
    ):
        if pulse_fmin_Hz <= pulse_fmax_Hz:
            raise ValueError("pulse_fmin_Hz <= pulse_fmax_Hz")
        self.pulse_fmin = pulse_fmin_Hz
        self.pulse_fmax = pulse_fmax_Hz
        self.pulse_window = pulse_window
        if pulse_repetition_rate_Hz <= 0:
            raise ValueError("pulse_repetition_rate_Hz <= 0")
        self.pulse_repetition_rate = pulse_repetition_rate_Hz
        if frame_number_waveforms_in_frame < 1:
            raise ValueError("frame_number_waveforms_in_frame < 1")
        self.frame_number_waveforms_in_frame = frame_number_waveforms_in_frame
        if frame_time_s < 0:
            raise ValueError("frame_time_s < 0")
        self.frame_frame_time = frame_time_s
        if frames_requested < 1:
            raise ValueError("frames_requested < 1")
        self.frame_frames_requested = frames_requested
        #
        # derived quantities
        #
        self.band_width = self.pulse_fmax - self.pulse_fmin
        pulse_duration = 1.0 / self.band_width  # approximation
        self.range_resolution_mps = 0.5 * c0 * pulse_duration
        self.max_range_m = 0.5 * c0 / self.pulse_repetition_rate
        fcenter = 0.5 * (self.pulse_fmax + self.pulse_fmin)
        lambda_c = c0 / fcenter
        self.max_velocity = lambda_c / 4 * self.pulse_repetition_rate  # TODO check
        self.velocity_resolution = (
            lambda_c
            / (2 * self.frame_number_waveforms_in_frame)
            * self.pulse_repetition_rate
        )  # TODO check

    def get_solver_fmin_Hz(self) -> float:
        return self.pulse_fmin

    def get_solver_fmax_Hz(self) -> float:
        return self.pulse_fmax

    def get_solver_max_range_m(self) -> float:
        return self.max_range_m

    def get_radar_max_range_m(self) -> float:
        return self.max_range_m

    def get_radar_range_resolution_m(self) -> float:
        return self.range_resolution_mps

    def get_radar_max_velocity_mps(self) -> float:
        return self.max_velocity

    def get_radar_velocity_resolution_mps(self) -> float:
        return self.velocity_resolution

    def get_simulation_time_parameters(self) -> npt.NDArray[np.float64]:
        raise NotImplementedError("Not Implemented")

    def get_parametersweep_cpi_indices(self) -> typing.List[typing.List[int]]:
        raise NotImplementedError("Not Implemented")

    def get_MIMO(self) -> MIMOAntennaArray:
        raise NotImplementedError("Not Implemented")

    @classmethod
    def from_pickled(cls, file_name: typing.Union[str, Path]):
        """accesses the currently open *.cst project"""
        file_name = Path(file_name)
        if not file_name.exists():
            raise FileExistsError("file `{}` does not exists".format(file_name))
        try:
            with open(file_name, "rb") as f:
                obj = pickle.load(f)
            if not isinstance(obj, cls):
                raise TypeError(
                    f"Expected instance of {cls.__name__}, got {type(obj).__name__}"
                )
            return obj
        except (pickle.PickleError, IOError, EOFError) as e:
            raise ValueError("error reading file: {}", e)

    def save_pickled(self, file_name: typing.Union[str, Path]):
        with open(file_name, "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def from_RADAR_specs(
        cls,
        f_center_Hz: float,
        range_max_m: float,
        range_resolution_m: float,
        velocity_max_mps: float,
        velocity_resolution_mps: float,
        frames_requested: npt.ArrayLike,
    ):
        """
        Choose a setup that is fulfilling the requested performance
        characteristics of the RADAR
        """
        bandwidth = c0 / range_resolution_m
        pulse_fmin_Hz = f_center_Hz - bandwidth / 2
        pulse_fmax_Hz = f_center_Hz + bandwidth / 2
        pulse_window = wd.boxcar
        lambda_c = c0 / f_center_Hz
        pulse_repetition_rate_Hz = 2 * range_max_m / c0
        pulse_repetition_rate_Hz = max(
            pulse_repetition_rate_Hz, 4 * velocity_max_mps / lambda_c
        )  # TODO check
        frame_number_waveforms_in_frame = math.ceil(
            lambda_c / (2 * velocity_resolution_mps) * pulse_repetition_rate_Hz
        )
        frame_time_s = frame_number_waveforms_in_frame / pulse_repetition_rate_Hz
        return cls(
            pulse_fmin_Hz,
            pulse_fmax_Hz,
            pulse_window,
            pulse_repetition_rate_Hz,
            frame_number_waveforms_in_frame,
            frame_time_s,
            frames_requested,
        )


##############################################################################


def analytic_linear_chirp(t, fc, B, Tc):
    r"""linear chirp that is for fc >> B approximately an analytic signal
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
    wndw = np.heaviside(1 - 2 * np.abs(t) / Tc, 1.0)
    freq = fc + 0.5 * B / Tc * t  # instant freq
    return wndw * np.exp(1j * 2.0 * np.pi * freq * t)


def time_delay_from_beat_frequency(fbeat, Tc, B):
    """
    valid for linear chirp
    """
    return fbeat * Tc / B


def distance_from_beat_frequency(fbeat, Tc, B):
    """
    distance of scatterer from radar (neglecting Tx-Rx distance)
    """
    return time_delay_from_beat_frequency(fbeat, Tc, B) * c0 / 2


def velocity_from_frame_frequency(fframe, fc):
    return fframe / fc * c0 / 2


class FMCWMimoRadar(Radar):

    def __init__(
        self,
        mimo: typing.Union[MIMOAntennaArray, None],
        chirp_fstart_Hz: float,
        chirp_fstop_Hz: float,
        chirp_Tc_s: float,
        chirp_Tr_s: float,
        adc_nbins: int,
        adc_tstart_s: float,
        adc_tstop_s: float,
        use_complex_mixer: bool,
        frame_number_waveforms: int,
        frame_time_s: float,
        frames_requested: npt.ArrayLike,
    ):
        # setup mimo data
        self.mimo = mimo
        # chirp
        self.chirp_fstart = chirp_fstart_Hz
        self.chirp_fstop = chirp_fstop_Hz
        self.chirp_Tc = chirp_Tc_s
        self.chirp_Tr = chirp_Tr_s
        self.chirp_S = (chirp_fstop_Hz - chirp_fstart_Hz) / chirp_Tc_s
        self.chirp_fmin = min(chirp_fstart_Hz, chirp_fstop_Hz)
        self.chirp_fmax = max(chirp_fstart_Hz, chirp_fstop_Hz)
        self.chirp_B = self.chirp_fmax - self.chirp_fmin
        self.chirp_signal = analytic_linear_chirp
        # adc
        self.adc_nbins = adc_nbins
        self.adc_dt = chirp_Tc_s / (
            adc_nbins - 1
        )  # ensure integer number of samples per chirp
        self.adc_tstart = adc_tstart_s
        self.adc_tstop = adc_tstop_s
        # lowpass
        self.lowpass_fcutoff = 0.99 / (2 * self.adc_dt)  # 0.99 Nyquist sampling limit
        # mixer
        self.complex_mixer = use_complex_mixer
        #
        self.frame_number_waveforms = frame_number_waveforms
        self.frame_time = frame_time_s
        # derived quantities
        self.solver_fmin = self.chirp_fmin
        self.solver_fmax = self.chirp_fmax
        self.band_width = self.chirp_fmax - self.chirp_fmin
        S = self.band_width / self.chirp_Tc
        Fs = 1.0 / self.adc_dt
        self.max_range_m = Fs * c0 / (2 * S)
        self.range_resolution_mps = c0 / (2 * self.band_width)
        f_center = 0.5 * (self.chirp_fmax + self.chirp_fmin)
        lambda_center = c0 / f_center
        self.max_velocity = lambda_center / (4 * self.chirp_Tc)
        self.velocity_resolution = lambda_center / self.frame_time
        self.frame_time_chirps = chirp_Tc_s * frame_number_waveforms
        # setup frame data
        self.frames_requested = np.array(frames_requested)
        self.frames_requested = self.__validate_convert_frames_requested(
            self.frames_requested, self.frame_time
        )
        self.solver_time_instances, self.parametersweep_cpi_indices = (
            self.__calculate_solver_time_instances(
                self.frames_requested,
                self.frame_time,
                self.frame_number_waveforms,
                self.chirp_Tc,
                self.chirp_Tr,
            )
        )

    def __calculate_solver_time_instances(
        self,
        requested_frames: npt.ArrayLike,
        frame_time: float,
        number_waveforms_per_frame: int,
        Tc: float,
        Tr: float,
    ):
        parametersweep_cpi_indices = []
        ts = []
        isweep = 1
        for iframe in requested_frames:
            cpi_indices = []
            for iwaveform in range(0, number_waveforms_per_frame):
                t = frame_time * iframe + Tc / 2 + iwaveform * Tr
                ts.append(t)
                cpi_indices.append(isweep)
                isweep += 1
            parametersweep_cpi_indices.append(cpi_indices)
        return np.array(ts, dtype=np.float64), parametersweep_cpi_indices

    def __validate_convert_frames_requested(
        self, requested_frames: npt.ArrayLike, frame_time: float
    ):
        if np.issubdtype(requested_frames.dtype, np.floating):
            if np.any(requested_frames < 0):
                raise ValueError("negative frame value encountered")
            return int(requested_frames / frame_time)
        if np.issubdtype(requested_frames.dtype, np.integer):
            if np.any(requested_frames < 0):
                raise ValueError("negative frame value encountered")
            return requested_frames
        raise ValueError("requested frames must be integer or float values")

    @classmethod
    def from_pickled(cls, file_name: typing.Union[str, Path]):
        """accesses the currently open *.cst project"""
        file_name = Path(file_name)
        if not file_name.exists():
            raise FileExistsError("file `{}` does not exists".format(file_name))
        try:
            with open(file_name, "rb") as f:
                obj = pickle.load(f)
            if not isinstance(obj, cls):
                raise TypeError(
                    f"Expected instance of {cls.__name__}, got {type(obj).__name__}"
                )
            return obj
        except (pickle.PickleError, IOError, EOFError) as e:
            raise ValueError("error reading file: {}", e)

    def save_pickled(self, file_name: typing.Union[str, Path]):
        with open(file_name, "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)

    #
    # Chirp
    #
    def get_chirp_fstart(self) -> float:
        return self.chirp_fstart

    def get_chirp_fstop(self) -> float:
        return self.chirp_fstop

    def get_chirp_Tc(self) -> float:
        return self.chirp_Tc

    #
    # ADC
    #
    def get_adc_tstart(self) -> float:
        return self.adc_tstart

    def get_adc_tstop(self) -> float:
        return self.adc_tstop

    def get_adc_dt(self) -> float:
        return self.adc_dt

    def get_adc_nbins(self) -> float:
        return self.adc_nbins

    #
    # Low Pass Filter
    #
    def get_lowpass_cutoff(self) -> float:
        return self.lowpass_fcutoff

    #
    # Mixer
    #
    def get_complex_mixer(self) -> bool:
        return self.complex_mixer

    #
    # Solver Related
    #
    def get_solver_fmin_Hz(self) -> float:
        return self.solver_fmin

    def get_solver_fmax_Hz(self) -> float:
        return self.solver_fmax

    def get_solver_max_range_m(self) -> float:
        return self.max_range_m

    def get_radar_max_range_m(self) -> float:
        return self.max_range_m

    def get_radar_range_resolution_m(self) -> float:
        return self.range_resolution_mps

    def get_radar_max_velocity_mps(self) -> float:
        return self.max_velocity

    def get_radar_velocity_resolution_mps(self) -> float:
        return self.velocity_resolution

    def get_simulation_time_parameters(self) -> npt.NDArray[np.float64]:
        return self.solver_time_instances

    def get_parametersweep_cpi_indices(self) -> typing.List[typing.List[int]]:
        return self.parametersweep_cpi_indices

    def get_frame_time_chirps(self) -> float:
        return self.frame_time_chirps

    def get_chirp_repetition_time(self) -> float:
        return self.chirp_Tr

    def get_MIMO(self) -> MIMOAntennaArray:
        return self.mimo

    def ifsignal_to_range(
        self, freqs_Hz: npt.NDArray[np.float64]
    ) -> npt.NDArray[np.float64]:
        """convert IF signal beat frequency to range"""
        return freqs_Hz * self.chirp_Tc / self.chirp_B * c0 / 2

    def slowtimeifsignal_to_velocity(
        self, freqs_Hz: npt.NDArray[np.float64]
    ) -> npt.NDArray[np.float64]:
        """convert IF slow time frequency to velocity"""
        fc = 0.5 * (self.chirp_fmax + self.chirp_fmin)
        lambda0 = c0 / fc
        vradial = freqs_Hz * lambda0 / 2
        return vradial

    @classmethod
    def from_chirpcpi_specs(
        cls,
        mimo: typing.Union[MIMOAntennaArray, None],
        chirp_fstart_Hz: float,
        chirp_fstop_Hz: float,
        chirp_Tc_s: float,
        chirp_Tr_s: float,
        adc_nbins: int,
        adc_tstart_s: float,
        adc_tstop_s: float,
        use_complex_mixer: bool,
        frame_number_waveforms: int,
        frame_time_s: float,
        frames_requested: npt.ArrayLike,
    ):
        return cls(
            mimo,
            chirp_fstart_Hz,
            chirp_fstop_Hz,
            chirp_Tc_s,
            chirp_Tr_s,
            adc_nbins,
            adc_tstart_s,
            adc_tstop_s,
            use_complex_mixer,
            frame_number_waveforms,
            frame_time_s,
            frames_requested,
        )

    @classmethod
    def from_range_velocity_specs(
        cls,
        mimo: typing.Union[MIMOAntennaArray, None],
        f_center_Hz: float,
        range_max_m: float,
        range_resolution_m: float,
        velocity_max_mps: float,
        velocity_resolution_mps: float,
        frames_requested: npt.ArrayLike,
    ):
        """
        Choose a setup that is fulfilling the requested performance
        characteristics of the RADAR
        """
        lambda_c = c0 / f_center_Hz
        chirp_band_width = c0 / (2 * range_resolution_m)
        chirp_fstart_Hz = f_center_Hz - 0.5 * chirp_band_width
        chirp_fstop_Hz = f_center_Hz + 0.5 * chirp_band_width
        chirp_Tc_s = 2 * range_max_m / c0
        chirp_Tr_s = lambda_c / (4 * velocity_max_mps)
        chirp_Tr_s = max(chirp_Tr_s, chirp_Tc_s)
        chirp_Tc_s = max(chirp_Tr_s / 3, chirp_Tc_s)
        frame_time_s = lambda_c / (2 * velocity_resolution_mps)
        chirp_S = chirp_band_width / chirp_Tc_s
        adc_Ts_s = c0 / (2 * chirp_S * range_max_m)
        adc_nbins = 1 + math.ceil(chirp_Tc_s / adc_Ts_s)
        adc_tstart_s = -0.5 * chirp_Tc_s
        adc_tstop_s = +0.5 * chirp_Tc_s
        frame_number_waveforms_in_frame = int(
            math.ceil(lambda_c / (2 * velocity_resolution_mps * chirp_Tr_s))
        )
        frame_time_s = frame_number_waveforms_in_frame * chirp_Tr_s
        use_complex_mixer = bool
        return cls(
            mimo,
            chirp_fstart_Hz,
            chirp_fstop_Hz,
            chirp_Tc_s,
            chirp_Tr_s,
            adc_nbins,
            adc_tstart_s,
            adc_tstop_s,
            use_complex_mixer,
            frame_number_waveforms_in_frame,
            frame_time_s,
            frames_requested,
        )


######################################################################


def setup_single_FarField_source(
    prj: "cst.interface.Project", antenna_entry: AntennaEntry, m2proj_unit: float = 1
):
    name = antenna_entry.get_source_name()
    id = antenna_entry.get_id()
    file_name = antenna_entry.get_ffs_file_name()
    position = m2proj_unit * np.array(antenna_entry.get_position())
    U = antenna_entry.get_orientation_U()  # unit vectors are dimensionless
    W = antenna_entry.get_orientation_W()  # unit vectors are dimensionless
    ffs_vba = f"""
    FARFIELDSOURCE.Reset
    FARFIELDSOURCE.Name "{name}"
    FARFIELDSOURCE.Id "{id}"
    FARFIELDSOURCE.UseCopyOnly "true"
    FARFIELDSOURCE.Setposition "{position[0]}",  "{position[1]}",  "{position[2]}"
    FARFIELDSOURCE.SetTheta0XYZ "{W[0]}",  "{W[1]}",  "{W[2]}"
    FARFIELDSOURCE.SetPhi0XYZ "{U[0]}",  "{U[1]}",  "{U[2]}"
    FARFIELDSOURCE.Import "{file_name}"
    FARFIELDSOURCE.UseMultipoleFFS "false"
    FARFIELDSOURCE.Store
    """
    headline_vba = f"""setup ffs {name}"""
    prj.model3d.add_to_history(headline_vba, ffs_vba)


def setup_farfield_sources(prj: "cst.interface.Project", radar: Radar):
    m2proj_unit = 1
    if prj.model3d is not None:
        try:
            m2proj_unit = prj.model3d.Units.GetGeometryUnitToSI()
        except RuntimeError:
            pass

    mimo = radar.get_MIMO()
    for tx in mimo.get_txs():
        setup_single_FarField_source(prj, tx, m2proj_unit)

    for rx in mimo.get_rxs():
        setup_single_FarField_source(prj, rx, m2proj_unit)


def setup_asymptotic_solver(
    prj: "cst.interface.Project",
    radar: Radar,
    number_intersections: int,
    number_frequency_points: int,
):
    """
    Set up A-solver with good values
    """
    assert number_intersections > 0

    #
    Hz2proj_unit = prj.model3d.Units.GetFrequencySIToUnit()
    fmin = Hz2proj_unit * radar.get_solver_fmin_Hz()
    fmax = Hz2proj_unit * radar.get_solver_fmax_Hz()
    max_range = radar.get_solver_max_range_m()  # currently always in m
    df = (fmax - fmin) / number_frequency_points  # default broad band setting
    # transmitter
    vba_tx_list = []
    for tx in radar.get_MIMO().get_txs():
        tx_name = tx.get_source_name()
        vba_tx_template = f"""
            AsymptoticSolver.SetFieldSourcePhasor "{tx_name}", "1.0", "0.0"
            AsymptoticSolver.SetFieldSourceGroupname "{tx_name}", ""
            AsymptoticSolver.SetFieldSourceRays "{tx_name}", "False"
            AsymptoticSolver.SetFieldSourceActive "{tx_name}", "True"
            """
        vba_tx_list.append(vba_tx_template)
    vba_tx = "".join(vba_tx_list)
    # receivers
    vba_rx_list = []
    for rx in radar.get_MIMO().get_rxs():
        rx_name = rx.get_source_name()
        vba_rx_template = f"""
            AsymptoticSolver.SetFieldSourcePhasor "{rx_name}", "1.0", "0.0"
            AsymptoticSolver.SetFieldSourceGroupname "{rx_name}", ""
            AsymptoticSolver.SetFieldSourceRays "{rx_name}", "False"
            AsymptoticSolver.SetFieldSourceActive "{rx_name}", "False"
            """
        vba_rx_list.append(vba_rx_template)
    vba_rx = "".join(vba_rx_list)
    # solver vba
    solver_vba = f"""
    {vba_rx}
    AsymptoticSolver.SimultaneousFieldSourceExcitation "False"
    AsymptoticSolver.ResetPolarizations
    AsymptoticSolver.ResetFrequencyList
    AsymptoticSolver.ResetExcitationAngleList
    AsymptoticSolver.ResetObservationAngleList
    Units.Frequency "GHz"
    Solver.FrequencyRange "{fmin}", "{fmax}"
    ChangeSolverType "HF Asymptotic"
    AsymptoticSolver.Set "CalculateSParameters",  "True"
    AsymptoticSolver.Set "CalculateIncidentFarfield",  "False"
    AsymptoticSolver.SetSolverType "SBR_RAYTUBES"
    AsymptoticSolver.Set "RecordingMethod", "False"
    AsymptoticSolver.Set "BroadBandSweepActive", 1
    AsymptoticSolver.Set "BroadBandSweepRange", {max_range}
    AsymptoticSolver.AddFrequencySweep "{fmin}", "{fmax}", "{df}"
    AsymptoticSolver.SetSolverMode "FIELD_SOURCES"
    AsymptoticSolver.SetSolverType "SBR_RAYTUBES"
    AsymptoticSolver.SetSolverMaximumNumberOfReflections "{number_intersections}"
    AsymptoticSolver.SetMeshNormalTolerance "5"
    AsymptoticSolver.SetMeshSurfaceTolerance "0"
    AsymptoticSolver.SetMeshMaxEdgeLengthPerLambda "2"
    AsymptoticSolver.SetMeshMaxEdgeLengthPerDiagonal "0.1"
    AsymptoticSolver.SetSolverRaySpacingRT "1"
    AsymptoticSolver.SetSolverAdaptiveRaySubdivisionRT "True"
    AsymptoticSolver.SetSolverMaximumRayDistanceRT "2"
    AsymptoticSolver.SetSolverMinimumRayDistanceRT "0.03"
    AsymptoticSolver.SetSolverIncludeMetallicEdgeDiffraction "False"
    AsymptoticSolver.Set "MeshMaxWedgeLengthPerLambda", "0.25"
    AsymptoticSolver.Set "EnableDiffractedRaypathTracing", "0"
    AsymptoticSolver.Set "EnableWedgeDetectionRoutineForPTD", "False"
    AsymptoticSolver.ResetFieldSources
    {vba_tx}
    AsymptoticSolver.Set "DisableObservationSweepFarfieldComputation",  "False"
    """
    prj.model3d.add_to_history("RADAR - setup solver", solver_vba)


def stringify_1darray(x):
    delim = ";"
    xstr = delim.join(map(str, x))
    return xstr


def setup_parameter_sweep(prj: "cst.interface.Project", radar: Radar):
    # create parameter t
    t = radar.get_simulation_time_parameters()
    # time_si2unit = prj.model3d.Units.GetTimeSIToUnit()
    # t = time_si2unit*t
    tstr = stringify_1darray(t)
    if prj.model3d is not None:
        try:
            prj.model3d.ParameterSweep.AddSequence("Sweep")
            prj.model3d.ParameterSweep.AddParameter_ArbitraryPoints("Sweep", "t", tstr)
        except RuntimeError:
            pass


class AsymptoticSolverSimulation:
    def __init__(self, prj, radar: Radar):
        self.prj = prj
        self.radar = radar
        self.results = None

    @classmethod
    def from_file(cls, file_name: str, radar: Radar):
        """opens a *.cst file for working with it"""
        de = DesignEnvironment.new()
        cst_file = str(Path(cst_file).absolute())
        if not Path(cst_file).exists():
            raise FileExistsError("file `{}` not found".format(cst_file))
        prj = de.open_project(cst_file)
        return cls(prj, radar)

    @classmethod
    def from_current_project(cls, radar: Radar):
        """accesses the currently open *.cst project"""
        return cls(get_current_project(), radar)

    @classmethod
    def from_pickled(cls, file_name: typing.Union[str, Path]):
        """accesses the currently open *.cst project"""
        file_name = Path(file_name)
        if not file_name.exists():
            raise FileExistsError("file `{}` does not exists".format(file_name))
        try:
            with open(file_name, "rb") as f:
                obj = pickle.load(f)
            if not isinstance(obj, cls):
                raise TypeError(
                    f"Expected instance of {cls.__name__}, got {type(obj).__name__}"
                )
            return obj
        except (pickle.PickleError, IOError, EOFError) as e:
            raise ValueError("error reading file: {}", e)

    def save_pickled(self, file_name: typing.Union[str, Path]):
        with open(file_name, "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)

    def setup(self, number_intersections: int, number_frequency_points: int = 11):
        """setup the asymptotic solver with good parameters for the specified RADAR"""
        setup_farfield_sources(self.prj, self.radar)
        setup_asymptotic_solver(
            self.prj, self.radar, number_intersections, number_frequency_points
        )
        setup_parameter_sweep(self.prj, self.radar)

    def start(self):
        """start the asymptotic solver"""
        assert self.prj is not None
        assert self.prj.model3d is not None
        try:
            self.prj.model3d.ParameterSweep.Start()
        except RuntimeError as error:
            raise RuntimeError("Start parameter sweep failed") from error

    def get_results(
        self,
    ) -> typing.List[typing.Tuple[npt.NDArray[np.float64], ChannelTensor]]:
        if self.results:
            return self.results
        time_si2unit = self.prj.model3d.Units.GetTimeSIToUnit()
        mimo = self.radar.get_MIMO()
        rxs = []
        for rx in mimo.get_rxs():
            rxs.append(rx.get_source_name())
        txs = []
        for tx in mimo.get_txs():
            txs.append(tx.get_source_name())
        channel_tensors = []
        cst_file_path = Path(self.prj.folder()) / Path(self.prj.filename())
        include_run_ids_for_cpis = self.radar.get_parametersweep_cpi_indices()
        for include_run_ids in include_run_ids_for_cpis:
            ct = ChannelTensor.from_cst_file(
                cst_file_path,
                txs,
                rxs,
                skip_nonparametric=True,
                broad_band_result=True,
                include_run_ids=include_run_ids,
            )
            para_t = np.array(ct.get_time_data("t"))
            para_t_si = para_t / time_si2unit
            channel_tensors.append((para_t_si, ct))
        self.prj = None
        self.results = channel_tensors
        return channel_tensors


class IFSignalCalculation:
    """
    The IFSignalCalculation class provides functionallity to calculate
    the intermediate frequency (IF) signal of FMCW or Pulse based RADARs.
    After setting up the RADAR type
    """

    def __init__(
        self, radar: typing.Union[FMCWMimoRadar, PulsedMimoRadar], gpu: bool = False
    ):
        assert isinstance(radar, FMCWMimoRadar) or isinstance(radar, PulsedMimoRadar)
        self.radar = radar
        self.gpu = gpu

    @classmethod
    def from_FMCWMimoRadar(cls, radar: FMCWMimoRadar, gpu: bool = False):
        return cls(radar, gpu)

    @classmethod
    def from_PulsedMimoRadar(cls, radar: PulsedMimoRadar, gpu: bool = False):
        return cls(radar, gpu)

    # @classmethod
    # def from_fmcw_chirp(cls,
    #                     fstart_Hz: float,
    #                     fend_Hz: float,
    #                     Tc_s: float):
    #     pass

    # @classmethod
    # def from_fmcw_general_signal(cls,
    #                              fstart_Hz: float,
    #                              fend_Hz: float,
    #                              Tc_s: float):
    #     pass

    def compute(
        self, channel_tensors: typing.Union[ChannelTensor, typing.List[ChannelTensor]]
    ) -> typing.Tuple[npt.NDArray[np.float64], npt.NDArray[np.complex128]]:
        if isinstance(self.radar, FMCWMimoRadar):
            if isinstance(channel_tensors, ChannelTensor):
                return self.fmcw_single_cpi(channel_tensors)
            else:
                # Subject to later optimization, knowing the chirp is constant
                # the compuation can be optimize by precalculating quantities
                ts = []
                Hs = []
                for channel_tensor in channel_tensors:
                    t, H = self.fmcw_single_cpi(channel_tensor)
                    ts.append(t)
                    Hs.append(H)
                return ts, Hs
        elif isinstance(self.radar, PulsedMimoRadar):
            raise NotImplementedError("not implemented")

    def fmcw_single_cpi(
        self, channel_tensor: ChannelTensor
    ) -> typing.Tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
        # Subject to later optimization
        adc_nbins = self.radar.get_adc_nbins()
        frequencies = channel_tensor.get_frequencies()
        H = channel_tensor.get_tensor()
        if self.gpu:
            Hd = cp.asarray(H)
            fd = cp.asarray(frequencies)
            Hdif = cp.zeros((H.shape[0], H.shape[1], adc_nbins), dtype=np.complex128)
        else:
            Hd = H
            fd = frequencies
            Hdif = np.zeros((H.shape[0], H.shape[1], adc_nbins), dtype=np.complex128)
        #
        td = None
        for isweep in range(0, H.shape[0]):
            for ichannel in range(0, H.shape[1]):
                td, Hdif[isweep, ichannel, :] = IFSignalCalculation.fmcw(
                    frequencies=fd,
                    H=Hd[isweep, ichannel, :],
                    f0c=self.radar.get_chirp_fstart(),
                    f1c=self.radar.get_chirp_fstop(),
                    Tc=self.radar.get_chirp_Tc(),
                    adc_dt=self.radar.get_adc_dt(),
                    adc_t0=self.radar.get_adc_tstart(),
                    adc_nbins=adc_nbins,
                    f_IF_cutoff=self.radar.get_lowpass_cutoff(),
                    complex_mixer=self.radar.get_complex_mixer(),
                    gpu=self.gpu,
                )
        if self.gpu:
            Hdif = cp.asnumpy(Hdif)
            td = cp.asnumpy(td)
        return td, Hdif

    @staticmethod
    def fmcw(
        frequencies: npt.NDArray[np.float64],
        H: npt.NDArray[np.complex128],
        f0c: float,
        f1c: float,
        Tc: float,
        adc_dt: float,
        adc_t0: typing.Union[float, None] = None,
        adc_nbins: typing.Union[float, None] = None,
        f_IF_cutoff: typing.Union[float, None] = None,
        complex_mixer: bool = True,
        gpu: bool = True,
    ):
        """Calculates the ADC sampled IF signal
        Parameters
        ----------
        frequencies: array(float)
        transfer function frequencies > 0, sorted in ascending order
        H: array(complex)
        transfer function
        f0c: float
        chirp start frequency
        f1c: float
        chirp end frequency
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
        if gpu:
            xp = cp
            spx_local = spx
        else:
            xp = np
            spx_local = sc
        #
        Ha = 2 * H  # analytic signal
        f_base = frequencies[0]  # lowest frequency solver
        B_solver = frequencies[-1] - frequencies[1]  # solver bandwidth
        # demodulate spectrum by f_base
        # all calculations are performend in baseband of transferfunction H
        frequencies = frequencies - f_base
        dfH = frequencies[1] - frequencies[0]  # frequency spacing discrete H
        HTmax = 1.0 / dfH  # transfer function periode
        # internal sampling frequency of TD signal based on Chirp bandwidth
        # we allow the bandwidth to be negative when the chirp is a down chirp
        B_chirp = f1c - f0c
        # internal sampling rate based on Chirp and Solver bandwidth
        dt_internal = min(1.0 / (5 * xp.abs(B_chirp)), 1.0 / (5 * B_solver))
        # sampling chirp
        DT = (
            0.05 * Tc
        )  # extension beyond Chirp support to suppress artefacts in convolution
        t_chirp = xp.arange(-Tc / 2 - DT, Tc / 2 + DT, dt_internal)
        fchirp_shift = (f0c + f1c) / 2 - f_base  # bring chirp to baseband of H

        #
        def uchirp_complex_centered(t, fc, B, Tc):
            wndw = xp.heaviside(1 - 2 * np.abs(t) / Tc, 1.0)
            freq = fc + 0.5 * B / Tc * t  # instant freq
            return wndw * xp.exp(1j * 2.0 * np.pi * freq * t)

        chirpta = uchirp_complex_centered(t_chirp, fchirp_shift, B_chirp, Tc)

        #
        def ift_by_chirpz(H, df, t0, dt, t1=None, axis=0):
            Tp = 1.0 / df  # valid range of result
            w = xp.exp(1j * 2 * np.pi * df * dt)
            a = xp.exp(-1j * 2 * np.pi * df * t0)
            m = 1 + int(Tp / dt)  # non periodic length
            if t1:
                m = int((t1 - t0) / dt)
            h = spx_local.signal.czt(H, m, w, a, axis=axis)
            h = h / H.shape[axis]
            len_h = h.shape[axis]
            t = xp.linspace(t0, t0 + (len_h - 1) * dt, len_h)
            return (h, t)

        # sampling causal transfer function
        # no scaling required as 1/N in ift takes care
        hta, t_h = ift_by_chirpz(Ha, dfH, 0, dt_internal, t1=HTmax, axis=-1)
        hta = B_solver * hta  # B/N = df for the integral approximation
        yta = dt_internal * spx_local.signal.convolve(hta, chirpta, mode="full")
        t_Rx = t_chirp[0] + dt_internal * xp.linspace(0, len(yta), len(yta))

        def zero_pad_right(y, ntotal):
            if ntotal <= 0:
                return y
            return xp.pad(
                y, (0, ntotal - len(y)), mode="constant", constant_values=(0, 0)
            )

        chirpta = zero_pad_right(chirpta, yta.shape[-1])
        # formulation for IF data for mixer
        # spectrum > 2*f_asolver_mid already removed by analytical means
        # zero pad chirp to match dimension with yt
        if complex_mixer:
            # complex quadrature mixer + high freq rejection
            yif = 0.5 * np.conjugate(yta) * chirpta
        else:
            # real quadrature mixer + high freq rejection
            yif = 0.5 * np.real(np.conjugate(yta) * chirpta)
        #
        # idealized low pass filtering of yif
        #
        Yif = xp.fft.fft(yif, axis=-1)
        fif = xp.fft.fftfreq(Yif.shape[-1], t_Rx[1] - t_Rx[0])
        if f_IF_cutoff:
            idx = xp.argwhere(np.abs(fif) >= f_IF_cutoff).flatten()
            Yif[idx] = 0
        #
        # model ADC by evaluating the signal at the adc time samples via
        # linear interpolation
        #
        filtered_yif = xp.fft.ifft(Yif)
        if adc_t0:
            t = adc_t0 + adc_dt * xp.linspace(0, adc_nbins - 1, adc_nbins)
        else:
            t = t_chirp[0] + adc_dt * xp.linspace(0, adc_nbins - 1, adc_nbins)
        ip_filtered_yif = spx_local.interpolate.RegularGridInterpolator(
            [t_Rx], filtered_yif, method="linear"
        )
        yif = ip_filtered_yif(t)
        return t, yif


class RangeCalculation:
    def __init__(
        self,
        radar: typing.Union[FMCWMimoRadar, PulsedMimoRadar],
        if_signal_window: typing.Union[
            typing.Callable[[int], npt.NDArray], None
        ] = None,
        gpu: bool = False,
    ):
        assert isinstance(radar, FMCWMimoRadar) or isinstance(radar, PulsedMimoRadar)
        self.radar = radar
        self.gpu = gpu
        self.ifsignal_window = if_signal_window

    def compute(
        self, channel_tensors: typing.Union[ChannelTensor, typing.List[ChannelTensor]]
    ) -> typing.Tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
        self.ifsignal = IFSignalCalculation(radar=self.radar, gpu=self.gpu)
        ts, hifs = self.ifsignal.compute(channel_tensors=channel_tensors)
        if isinstance(hifs, np.ndarray) and isinstance(ts, np.ndarray):
            if isinstance(self.radar, FMCWMimoRadar):
                return self.fmcw_range(ts, hifs)
            else:
                return self.pulsed_range(ts, hifs)
        elif isinstance(hifs, list) and isinstance(ts, list):
            if isinstance(self.radar, FMCWMimoRadar):
                radial_ranges_m = []
                Y_s = []
                for icpi, hif in enumerate(hifs):
                    t = ts[icpi]
                    r, Y = self.fmcw_range(t, hif)
                    radial_ranges_m.append(r)
                    Y_s.append(Y)
                return radial_ranges_m, Y_s
            else:
                radial_ranges_m = []
                Y_s = []
                for icpi, hif in enumerate(hifs):
                    t = ts[icpi]
                    r, Y = self.pulsed_range(t, hif)
                    radial_ranges_m.append(r)
                    Y_s.append(Y)
                return radial_ranges_m, Y_s
        else:
            raise NotImplementedError("not implemented")

    def fmcw_range(
        self,
        ts: npt.NDArray[np.float64],
        hif: npt.NDArray[np.float64],
        window: typing.Union[typing.Callable[[int], npt.NDArray], None] = None,
        axis: int = -1,
    ) -> typing.Tuple[npt.NDArray, npt.NDArray]:
        if window:
            wnd = window(hif.shape[axis])
            shape = [1] * hif.ndim
            shape[axis] = wnd.shape[0]
            hif = hif * wnd.reshape(shape)
        Y = np.fft.fft(hif, axis=axis)
        n = hif.shape[axis]
        f = (
            1.0 / (n * (ts[1] - ts[0])) * np.arange(0, n, 1)
        )  # only positive frequency content
        radial_range_m = self.radar.ifsignal_to_range(freqs_Hz=f)
        return radial_range_m, Y

    def pulsed_range(
        self,
        ts: npt.NDArray[np.float64],
        hif: npt.NDArray[np.float64],
        window: typing.Union[typing.Callable[[int], npt.NDArray], None] = None,
        axis=-1,
    ) -> typing.Tuple[npt.NDArray, npt.NDArray]:
        raise NotImplementedError("pulsed radar is not implemented")


class RangeDopplerCalculation:
    def __init__(
        self,
        radar: typing.Union[FMCWMimoRadar, PulsedMimoRadar],
        if_signal_window: typing.Union[
            typing.Callable[[int], npt.NDArray], None
        ] = None,
        slow_time_signal_window: typing.Union[
            typing.Callable[[int], npt.NDArray], None
        ] = None,
        gpu: bool = False,
    ):
        assert isinstance(radar, FMCWMimoRadar) or isinstance(radar, PulsedMimoRadar)
        self.radar = radar
        self.gpu = gpu
        self.ifsignal_window = if_signal_window
        self.slow_time_signal_window = slow_time_signal_window

    def compute(
        self, channel_tensors: typing.Union[ChannelTensor, typing.List[ChannelTensor]]
    ) -> typing.Tuple[
        npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.complex128]
    ]:
        """
        Computes the Range Doppler Tensor or Tensors

        Parameters
        ----------
        channel_tensor : ChannelTensor or List[ChannelTensor]
            channel tensor of a calculation or a list of channel tensors

        Returns
        -------
        range_m : np.array
            radial range in meter
        velocity_mps : np.array
            radial velocity in meter per second
        range_doppler_tensor : np.array
            tensor rank 3 of complex values
        """
        self.ifsignal = IFSignalCalculation(radar=self.radar, gpu=self.gpu)
        ts, hifs = self.ifsignal.compute(channel_tensors=channel_tensors)
        if isinstance(hifs, np.ndarray) and isinstance(ts, np.ndarray):
            if isinstance(self.radar, FMCWMimoRadar):
                return self.fmcw_range_doppler(
                    ts,
                    hifs,
                    range_window=self.ifsignal_window,
                    doppler_window=self.slow_time_signal_window,
                )
            else:
                return self.pulsed_range_doppler(
                    ts,
                    hifs,
                    range_window=self.ifsignal_window,
                    doppler_window=self.slow_time_signal_window,
                )
        elif isinstance(hifs, list) and isinstance(ts, list):
            if isinstance(self.radar, FMCWMimoRadar):
                radial_ranges_m = []
                radial_velocities_mps = []
                Y_s = []
                for icpi, hif in enumerate(hifs):
                    t = ts[icpi]
                    r, vr, Y = self.fmcw_range_doppler(t, hif)
                    radial_ranges_m.append(r)
                    radial_velocities_mps.append(vr)
                    Y_s.append(Y)
                return radial_ranges_m, radial_velocities_mps, Y_s
            else:
                radial_ranges_m = []
                radial_velocities_mps = []
                Y_s = []
                for icpi, hif in enumerate(hifs):
                    t = ts[icpi]
                    r, vr, Y = self.pulsed_range_doppler(t, hif)
                    radial_velocities_mps.append(vr)
                    radial_ranges_m.append(r)
                    Y_s.append(Y)
                return radial_ranges_m, radial_velocities_mps, Y_s
        else:
            raise NotImplementedError("not implemented")

    def fmcw_range_doppler(
        self,
        ts: npt.NDArray[np.float64],
        hif: npt.NDArray[np.float64],
        range_window: typing.Union[typing.Callable[[int], npt.NDArray], None] = None,
        doppler_window: typing.Union[typing.Callable[[int], npt.NDArray], None] = None,
        axis: int = -1,
    ) -> typing.Tuple[
        npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.complex128]
    ]:
        if range_window:
            wnd = range_window(hif.shape[axis])
            shape = [1] * hif.ndim
            shape[axis] = -1
            hif = hif * wnd.reshape(shape)
        if doppler_window:
            wnd = doppler_window(hif.shape[0])
            shape = [1] * hif.ndim
            shape[0] = -1
            hif = hif * wnd.reshape(shape)

        Y = np.fft.fft(hif, axis=axis)
        Y = np.fft.fft(
            np.conjugate(Y), axis=0
        )  # conjugate for correct velocity and angle calc
        n = hif.shape[axis]
        f = (
            1.0 / (n * (ts[1] - ts[0])) * np.arange(0, n, 1)
        )  # only positive frequency content
        radial_range_m = self.radar.ifsignal_to_range(freqs_Hz=f)
        vtensor = np.fft.fftshift(np.fft.fft(Y, axis=0), axes=0)
        # vtensor = np.fft.fft(Y, axis=0)
        slow_time_freqs_Hz = np.fft.fftshift(
            np.fft.fftfreq(vtensor.shape[0], self.radar.get_chirp_repetition_time())
        )
        radial_velocity_mps = self.radar.slowtimeifsignal_to_velocity(
            freqs_Hz=slow_time_freqs_Hz
        )
        return radial_range_m, radial_velocity_mps, Y

    def pulsed_range_doppler(
        self,
        ts: npt.NDArray[np.float64],
        hif: npt.NDArray[np.float64],
        range_window: typing.Union[typing.Callable[[int], npt.NDArray], None] = None,
        doppler_window: typing.Union[typing.Callable[[int], npt.NDArray], None] = None,
        axis: int = -1,
    ) -> typing.Tuple[
        npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.complex128]
    ]:
        raise NotImplementedError("pulsed radar is not implemented")


class AngleCalculation:
    def __init__(self, mimo, algorithm, single_snapshot: bool):
        self.mimo = mimo
        self.algorithm = algorithm
        self.single_snapshot = single_snapshot

    @classmethod
    def from_compressed_sensing(
        cls,
        mimo: MIMOAntennaArray,
        kind: str = "theta",
        second_angle_rad: float = 0,
        fov_min_rad: float = np.deg2rad(-90),
        fov_max_rad: float = np.deg2rad(+90),
        nsamples: int = 181,
    ):
        if fov_max_rad < fov_min_rad:
            raise ValueError("fov_max_deg < fov_min_deg")
        if kind != "theta" and kind != "phi":
            raise ValueError("kind has to be 'phi' or 'theta'")
        if nsamples < 1:
            raise ValueError("nsample must be greater than one")
        compressed_sensing = CSSingleSnapshot(
            kind=kind,
            vmin=fov_min_rad,
            vmax=fov_max_rad,
            nsamples=nsamples,
            virtual_array_positions=mimo.get_virtual_antenna_matrix(),
            k0=mimo.get_k0design(),
            second_dim_angle=second_angle_rad,
            coordinate_system=mimo.get_coordinate_system(),
        )
        return cls(mimo, compressed_sensing, True)

    @classmethod
    def from_frourier_transform(
        cls, mimo: MIMOAntennaArray, kind: str = "theta", window_function=None
    ):
        fourier = FourierSingleSnapshot(
            kind=kind,
            vmin=None,
            vmax=None,
            nsamples=None,
            virtual_array_positions=mimo.get_virtual_antenna_matrix(),
            k0=mimo.get_k0design(),
            second_dim_angle=None,
        )
        return cls(mimo, fourier, True)

    def compute(
        self,
        tensors: typing.Union[
            npt.NDArray[np.complex128], typing.List[npt.NDArray[np.complex128]]
        ],
    ):
        #
        if self.single_snapshot:
            calculator = AngleCalculation.__calculate_from_single_snapshot
        else:
            calculator = AngleCalculation.__calculate_from_covariance_matrix
        #
        if isinstance(tensors, list):
            angles_list = []
            spectra_list = []
            for tensor in tensors:
                angles, spectrum = calculator(self.algorithm, tensor)
                angles_list.append(angles)
                spectra_list.append(spectrum)
            return angles_list, spectra_list
        elif isinstance(tensors, np.ndarray):
            return calculator(self.algorithm, tensors)
        else:
            raise ValueError("unknown tensor class")

    @classmethod
    def from_mvdr(
        cls,
        mimo: MIMOAntennaArray,
        kind: str = "theta",
        second_angle_deg: float = 0,
        fov_min_deg: float = -90,
        fov_max_deg: float = +90,
        nsamples: int = 181,
    ):
        if fov_max_deg < fov_min_deg:
            raise ValueError("fov_max_deg < fov_min_deg")
        if kind != "theta" and kind != "phi":
            raise ValueError("kind has to be 'phi' or 'theta'")
        if nsamples < 1:
            raise ValueError("nsample must be greater than one")
        compressed_sensing = MVDRAlgorithm(
            kind=kind,
            vmin=fov_min_deg,
            vmax=fov_max_deg,
            nsamples=nsamples,
            virtual_array_positions=mimo.get_virtual_antenna_matrix(),
            k0=mimo.get_k0design(),
            second_dim_angle=second_angle_deg,
            coordinate_system=mimo.get_coordinate_system(),
        )
        return cls(mimo, compressed_sensing, False)

    @staticmethod
    def __calculate_from_single_snapshot(algorithm, tensor):
        Nc = tensor.shape[0]  # number chirps
        Nr = tensor.shape[2]  # number range bins
        Nvelocity = Nc
        Ntheta = algorithm.get_number_of_angles()
        Zz = np.zeros((Nvelocity, Ntheta, Nr), dtype=np.complex128)
        for ir in range(0, Nr):
            for ic in range(0, Nc):
                A = tensor[ic, :, ir]
                Zz[ic, :, ir] = algorithm.execute(A)
        return algorithm.get_scan_vars_degree(), Zz

    @staticmethod
    def __calculate_from_covariance_matrix(algorithm, tensor):
        Nc = tensor.shape[0]  # number chirps
        Nchannel = tensor.shape[1]  # number channels
        Nr = tensor.shape[2]  # number range bins
        Ntheta = algorithm.get_number_of_angles()
        Zz = np.zeros((Ntheta, Nr), dtype=np.complex128)
        for ir in range(0, Nr):
            # estimate covariance matrix from samples
            Rhat = np.zeros((Nchannel, Nchannel), dtype=np.complex128)
            # np.fill_diagonal(Rhat, self.diagonal_loading)
            for ic in range(0, Nc):
                A = tensor[ic, :, ir]
                Rhat += np.outer(A, A.T.conjugate())
            Rhat = Rhat / Nc  # normalization
            Zz[ic, :] = algorithm.execute(A)
        return algorithm.get_scan_vars_degree(), Zz
