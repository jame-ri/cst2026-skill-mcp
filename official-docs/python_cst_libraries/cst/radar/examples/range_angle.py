# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

"""A simple example showing how to calculate the range and angle of two corner reflectors from an
asymptotic solver simulation.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from cst.radar.channel_tensor import get_antenna_positions_from_model, ChannelTensor
from cst.radar.coordinate_systems import SphericalCoordinateSystem, SensorCoordinateSystem1
from cst.radar.spectral_algorithms import BartlettAlgorithm, MVDRAlgorithm, MUSICAlgorithm, create_virtual_antenna_matrix
from cst.radar.range_angle import angle_range_map, angle_range_map_limited_range
from cst.radar.range import range_map_from_channeltensor_pulsed_radar
from cst.radar.physical_constants import c0, freqHz_to_k0
import cst.radar.plot as tls


def generate_target_list_from_exact_positions(sensor_coordinate_system):
    """ Calcualte the desired target positions from the center of mass
        of the analyically known corner reflector position in the sensor
        coordinate system
    """
    corner_reflector_1 = np.array([-1, 0, 5])
    corner_reflector_2 = np.array([3, 0, 3])
    corner_list = [corner_reflector_1, corner_reflector_2]
    target_list_range = []
    target_list_angle = []
    for corner_pos in corner_list:
        theta, _, r = sensor_coordinate_system.get_theta_phi_r(corner_pos)
        r_meter = r
        theta_deg = np.rad2deg(theta)
        target_list_range.append(r_meter)
        target_list_angle.append(theta_deg)
    return (target_list_range, target_list_angle)


def calculate_range_angle_map():
    use_pickled_data = True
    if use_pickled_data:
        # load precalculated data from pickled data
        model_dir = Path(__file__).parent
        data_file = model_dir / Path('data') / Path('corner_reflectors_range_angle.pkl')
        channel_tensor = ChannelTensor.from_pickle_file(data_file)
        # specify transmitter names and positions manually
        tx_dict = {'Tx1': np.array([0., 0., 0.]),
                   'Tx2': np.array([0.00197368, 0., 0.])}
        # specify receiver names and positions
        rx_dict = {'Rx1': np.array([0.00592105, 0., 0.]),
                   'Rx2': np.array([0.00986842, 0., 0.]),
                   'Rx3': np.array([0.01381579, 0., 0.])}
    else:
        #  load the parametric F-parameters of the simulation and organize them in the `ChannelTensor`
        model_dir = Path(r'./')
        cst_file_name = model_dir / r'corner_reflectors_range_angle.cst'
        txs = ['Tx1', 'Tx2']  # specify the name of the transmitter FFS
        rxs = ['Rx1', 'Rx2', 'Rx3']  # specify the name of the receiver FFS
        channel_tensor = ChannelTensor.from_cst_file(cst_file_name, txs, rxs)
        # load the antenna positions from Parameter file
        # specify those manually when you have not parametrized the source position
        tx_dict, rx_dict = get_antenna_positions_from_model(cst_file_name, rxs, txs)

    # calculate the range_tensor from this data assuming a pulsed RADAR signal
    range_axis_vals, range_tensor = range_map_from_channeltensor_pulsed_radar(channel_tensor,
                                                                            max_range=10,
                                                                            Nbins=1024,
                                                                            window_order=8,
                                                                            window_amplitude_correction=True
                                                                            )
    # for the first parameter sweep and channel number 0 plot the range map
    plt.plot(range_axis_vals, np.abs(range_tensor[0, 0, :]))
    plt.yscale('log')
    plt.xlim(0, 10)
    plt.title('Pulsed RADAR - Estimated Ranges Sweep 0 Channel 0')
    plt.xlabel('distance / m')
    plt.ylabel('signal strenght / a.u.')
    plt.show()
    # organize the virtual array positions and order them according to the channel dictionary
    channel_dict = channel_tensor.get_channel_dict()
    virtual_array_positions = create_virtual_antenna_matrix(tx_dict, rx_dict, channel_dict, scale=1)
    #
    f0design = 76e+9  # reference frequency for angle of arrival algorithm
    k0 = freqHz_to_k0*f0design
    FoV = np.deg2rad(np.array([-85, 85]))  # field of view settings
    # specify sensor scan coordiante system
    Uhat = np.array([1, 0, 0])
    Vhat = np.array([0, 1, 0])
    What = np.array([0, 0, 1])
    origin = np.array([0.00592105, 0, 0])
    sensor_coordinate_system = SensorCoordinateSystem1(Uhat, Vhat, What, origin)
    # setup the angle of arrival detection algorithm
    mvdr_algorithm = MVDRAlgorithm(kind="theta",
                                vmin=FoV[0],
                                vmax=FoV[1],
                                nsamples=720,
                                virtual_array_positions=virtual_array_positions,
                                k0=k0,
                                second_dim_angle=0,
                                coordinate_system=sensor_coordinate_system)
    mvdr_algorithm.set_sigma_regularization_factor(1e-15)  # loading factor for the covariance matrix
    # run the mvdr_algorithm over each range bin
    new_range, Zz = angle_range_map_limited_range(mvdr_algorithm, range_tensor, range_axis_vals, max_range=10)
    angle = mvdr_algorithm.get_scan_vars_degree()
    # visualize the resulting range-angle map
    X, Y = np.meshgrid(new_range, angle)
    Z = np.log(np.abs(Zz))
    tls.visualize_map3d(X, Y, Z, xlabel='range/m', ylabel='angle/deg')
    plt.pcolormesh(X, Y, Z)
    plt.xlabel(r'range / m')
    plt.ylabel(r'theta / deg')
    plt.title('Pulsed RADAR - MVDR')
    plt.colorbar()
    target_list_range, target_list_angle = generate_target_list_from_exact_positions(sensor_coordinate_system)
    plt.scatter(target_list_range, target_list_angle, color='r', alpha=0.5, edgecolors='none', marker='o')
    plt.show()
    tls.visualize_map_polar(np.array(new_range), angle, np.log(np.abs(Zz)), angle_in_deg=True)


def main():
    calculate_range_angle_map()


if __name__ == '__main__':
    main()
