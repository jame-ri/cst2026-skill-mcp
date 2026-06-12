# Copyright 1998-2023 Dassault Systemes Deutschland GmbH.

from cst.radar.channel_tensor import ChannelTensor
from cst.radar.physical_constants import c0, Z0
from cst.radar.rcs_estimation import rcs_vs_distance_calculation_from_radar_equation
from cst.radar.rcs_estimation import rcs_vs_distance_calculaton_from_antenna_pattern
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def power_to_dB(x):
    return 10*np.log10(np.abs(x) + 1E-30)


def plate_max_rcs(lambda0, w, h):
    """ Analytical RCS """
    rcs_max_analytic = 4*np.pi*w*w*h*h/(lambda0*lambda0)
    return rcs_max_analytic


def rcs_estimation_from_FParameter_demo_small_corner_reflector():
    #
    # load f-parameter from simulation
    #
    use_pickled_data = True
    if use_pickled_data:
        # load precalculated data from pickled data
        model_dir = Path(__file__).parent
        data_file = model_dir / Path('data') / Path('rcs_range_plate.pkl')
        channel_tensor = ChannelTensor.from_pickle_file(data_file)
    else:
        #  load the parametric F-parameters of the simulation and organize them in the `ChannelTensor`
        model_dir = Path(r'./')
        cst_file_name = model_dir / r'rcs_range_plate.cst'
        txs = ['Tx']  # names transmitter FFS in model
        rxs = ['Rx']  # names receiver FFS in model
        channel_tensor = ChannelTensor.from_cst_file(cst_file_name, txs, rxs)
        model_dir = Path(__file__).parent
        data_file = model_dir / Path('data') / Path('rcs_range_plate.pkl')
        channel_tensor.serialize_to_pickle_file(data_file)

    freq = channel_tensor.get_frequencies()
    fparas = channel_tensor.get_tensor()
    # take the first F-parameter from a parametric simulation
    F = fparas[0, 0, :]
    df = freq[1] - freq[0]
    fc = 0.5*(freq[1] + freq[0])
    lambda0 = c0/fc
    print("unambigious range interval {}/m".format(c0/(2*df)))
    max_rcs = plate_max_rcs(w=0.05, h=0.05, lambda0=lambda0)
    print("rcs {}/m2".format(max_rcs))
    print("rcs {}/dB".format(power_to_dB(max_rcs)))
    #
    # demonstrate calculation from RADAR equation
    #
    start_range = 0
    R = 5  # distance in m of object
    dist, rcs = rcs_vs_distance_calculation_from_radar_equation(F, freq, R, Gr = 1, Gt = 1, start_range = start_range)
    plt.plot(dist, rcs, label = "RADAR Eq. R={}/m".format(R), linewidth=3)
    #
    # demonstrate calculation from generalized equation
    #
    field = np.sqrt(0.5/(0.5/Z0*4*np.pi))  # field value isotropic source
    tx_field = field  # replace with FF E value pattern in direction of object for anisotropic pattern
    rx_field = field  # replace with FF E value pattern in direction of object for anisotropic pattern
    dist, rcs = rcs_vs_distance_calculaton_from_antenna_pattern(F, freq, tx_field, rx_field, start_range)
    R = 5
    plt.plot(dist, rcs,'--r' ,label = "Generalize Eq. R={}/m".format(R), linewidth=3)
    #
    # max analytical value
    #
    plt.stem([R],[max_rcs], linefmt='k', label='max analytical RCS', markerfmt='^')
    plt.xlim(0,10)
    plt.xlabel('range / m')
    plt.ylabel('RCS / m2')
    plt.title('Range-RCS Estimation')
    plt.legend()
    plt.show()


def main():
    rcs_estimation_from_FParameter_demo_small_corner_reflector()


if __name__ == '__main__':
    main()
