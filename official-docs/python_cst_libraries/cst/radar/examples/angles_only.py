# Copyright 1998-2023 Dassault Systemes Deutschland GmbH.

from pathlib import Path
import pickle
import numpy as np
import matplotlib.pyplot as plt
from cst.radar.physical_constants import c0, freqHz_to_k0
from cst.radar.spectral_algorithms import MVDRAlgorithm, MUSICAlgorithm, BartlettAlgorithm
from cst.radar.spectral_algorithms import create_virtual_antenna_matrix, assemble_covariancematrix_single_frequency
from cst.radar.coordinate_systems import SensorCoordinateSystem1
from cst.radar.channel_tensor import ChannelTensor
from cst.radar.channel_tensor import get_antenna_positions_from_model


def annotate_corner_positions(ax, sensor_coordinate_system, ypos):
    """Mark the center of mass of the corner reflectors in the plot"""
    corner_pos1 = np.array([-1, 0, 5])
    theta1, phi1, _ = sensor_coordinate_system.get_theta_phi_r(corner_pos1)
    corner_pos2 = np.array([3, 0.00400, 3])

    theta2, phi2, _ = sensor_coordinate_system.get_theta_phi_r(corner_pos2)
    ax.annotate('object 1',
                xy=(np.rad2deg(theta1), ypos),
                xytext=(np.rad2deg(theta1), ypos),
                arrowprops=dict(facecolor='black', shrink=0.05))
    ax.annotate('object 2',
                xy=(np.rad2deg(theta2), ypos),
                xytext=(np.rad2deg(theta2), ypos),
                arrowprops=dict(facecolor='black', shrink=0.05))


def angles_from_single_frequency():
    """Demonstrate how to calculate the angles from a simulation with a single frequency
       or a small number of frequencies that are not sufficient to calculate a range as
       well. This approach give an idea about the optimal RADAR performance at a specific
       frequency.
    """
    #
    # Create a channel tensor from the simulation
    #
    use_pickled_data = True
    if use_pickled_data:
        # load precalculated data from pickled data
        model_dir = Path(__file__).parent
        data_file = model_dir / Path('data') / Path('rotating_corner_reflectors_angles_only.pkl')
        channel_tensor = ChannelTensor.from_pickle_file(data_file)
        # specify transmitter names and positions
        tx_dict = {'Tx1': np.array([0., 0., 0.]),
                   'Tx2': np.array([0.00197368, 0., 0.])}
        # specify receiver names and positions
        rx_dict = {'Rx1': np.array([0.00592105, 0., 0.]),
                   'Rx2': np.array([0.00986842, 0., 0.]),
                   'Rx3': np.array([0.01381579, 0., 0.]),
                   'Rx4': np.array([0.01776316, 0., 0.]),
                   'Rx5': np.array([0.02171053, 0., 0.]),
                   'Rx6': np.array([0.02565789, 0., 0.])}
    else:
        # load the data from a CST simulation
        model_dir = Path(r'.')
        cst_file_name = model_dir / r'rotating_corner_reflectors_angles_only.cst'
        txs = ['Tx1', 'Tx2']  # names transmitter FFS in model
        rxs = ['Rx1', 'Rx2', 'Rx3', 'Rx4', 'Rx5', 'Rx6']  # names receiver FFS in model
        channel_tensor = ChannelTensor.from_cst_file(cst_file_name, txs, rxs)
        # In the model the positions are defined as parameters and we can retrieve them
        # in this case automatically.
        tx_dict, rx_dict = get_antenna_positions_from_model(cst_file_name, rxs, txs)
    #
    # Calculate a covariance matrix from channel tensor from a single frequency
    # in order to judge the RADAR MIMO setup performance for angle detection
    #
    Rhat = assemble_covariancematrix_single_frequency(channel_tensor, ifreq=0)

    #
    # Use covariance matrix to determine angle
    #

    # first define the correct scan coordinate system for the MIMO array
    # in the model. In this specific case the FFS are located on the x-axis.
    Origin = np.array([0, 0, 0])
    Uhat = np.array([1, 0, 0])
    Vhat = np.array([0, 1, 0])
    What = np.array([0, 0, 1])
    sensor_coordinate_system = SensorCoordinateSystem1(Uhat, Vhat, What, Origin)
    # than setup the MVDR algorithm
    f0design = 77e+9  # array spacing in model is designed for this frequency
    lambda0 = c0/f0design
    channel_dict = channel_tensor.get_channel_dict()  # connection channel number with Tx/Rx pair
    virtual_array_positions = create_virtual_antenna_matrix(tx_dict, rx_dict, channel_dict, scale=1)
    print('virtual array positions in term of design wavelength \n {}'.format(np.real(virtual_array_positions)/lambda0))
    k0 = freqHz_to_k0*f0design
    FoV = np.deg2rad(np.array([-85, 85]))  # set field of view
    # Apply Bartlett algorithm
    algorithm = BartlettAlgorithm(kind="theta",
                                  vmin=FoV[0],
                                  vmax=FoV[1],
                                  nsamples=360,
                                  virtual_array_positions=virtual_array_positions,
                                  k0=k0,
                                  second_dim_angle=0,
                                  coordinate_system=sensor_coordinate_system)
    pseudo_spectrum = algorithm.execute(Rhat)
    angle = algorithm.get_scan_vars_degree()
    # Plot results
    fig, (ax1, ax2, ax3) = plt.subplots(3)
    ax1.plot(angle, np.abs(pseudo_spectrum))
    ax1.set_title('Bartlett', y=1, pad=-14)
    ax1.set(xlabel='angle / deg', ylabel='spectrum / a.u.', yscale='log')
    annotate_corner_positions(ax1, sensor_coordinate_system, ypos=np.amin(np.abs(pseudo_spectrum)))
    # Apply MVDR algorithm
    algorithm = MVDRAlgorithm(kind="theta",
                              vmin=FoV[0],
                              vmax=FoV[1],
                              nsamples=360,
                              virtual_array_positions=virtual_array_positions,
                              k0=k0,
                              second_dim_angle=0,
                              coordinate_system=sensor_coordinate_system)
    algorithm.set_sigma_regularization_factor(1e-20)  # good choice is crucial for accurate results
    pseudo_spectrum = algorithm.execute(Rhat)
    angle = algorithm.get_scan_vars_degree()
    # Plot results
    ax2.plot(angle, np.abs(pseudo_spectrum))
    ax2.set_title('MVDR', y=1, pad=-14)
    ax2.set(xlabel='angle / deg', ylabel='spectrum / a.u.', yscale='log')
    annotate_corner_positions(ax2, sensor_coordinate_system, ypos=np.amin(np.abs(pseudo_spectrum)))
    # Apply MUSIC algorithm
    # note that for MUSIC the number of objects have to be specified in advance
    algorithm = MUSICAlgorithm(kind="theta",
                               vmin=FoV[0],
                               vmax=FoV[1],
                               nsamples=360,
                               virtual_array_positions=virtual_array_positions,
                               k0=k0,
                               second_dim_angle=0,
                               coordinate_system=sensor_coordinate_system,
                               number_objects=2)
    pseudo_spectrum = algorithm.execute(Rhat)
    # Plot results
    angle = algorithm.get_scan_vars_degree()
    ax3.plot(angle, np.abs(pseudo_spectrum))
    ax3.set_title('MUSIC', y=1, pad=-14)
    ax3.set(xlabel='angle / deg', ylabel='spectrum / a.u.', yscale='log')
    # Mark exact object positions
    annotate_corner_positions(ax3, sensor_coordinate_system, ypos=np.amin(np.abs(pseudo_spectrum)))
    # Now plot everything
    plt.show()


def main():
    angles_from_single_frequency()


if __name__ == '__main__':
    main()
