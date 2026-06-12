# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

"""
This module provides a convenient way of representing F/S parameters from a simulation in a compact form.
The ChannelTensor object is created from simulation data and facilitates a convenient data representation.
Several methods to extract data from a CST Asymptotic solver simulation are provided.
"""

import json
import os
import pathlib
import pickle
import numpy as np
import re
from cst.results import ProjectFile

"""
Utility functions for extracting unit information from 1d results
"""


def get_frequency_unit_dict():
    return {'Hz': 1.0, 'kHz': 1e+3, 'MHz': 1e+6, 'GHz': 1e+9, 'THz': 1e+12, 'PHz': 1e+15}


def get_frequency_unit_from_xlabel(xlabel):
    match = re.search('Frequency / (.*)', xlabel)
    ending = match.group(1)
    return get_frequency_unit_dict()[ending]


def get_length_unit_dict():
    return {'km': 1e+3, 'm': 1.0, 'dm': 1e-1, 'cm': 1e-2, 'mm': 1e-3, 'um': 1e-6, 'nm': 1e-9, 'mil': 1609.344, 'ft': 0.3048, 'in': 0.0254}


def get_length_unit_from_xlabel(xlabel):
    match = re.search('Length / (.*)', xlabel)
    ending = match.group(1)
    return get_length_unit_dict()[ending]


class ChannelTensor:
    """F-parameter data tensor (snapshot,channel,frequency) and related quanties

    bare f-parameter data tensor: array(complex) tensor rank 3
        indicies are (snapshot,channel,frequency)
    run_id_dict: dict(int,int)
        maps snapshot number to run id
    channel_dict: dict(int,(str,str))
        maps channel number to Tx/Rx pairs
    frequencies: array(float)
        solver frequencies corresponding to frequency index
    """

    def __init__(self, channel_dict={},
                 run_id_dict={},
                 frequencies=[],
                 tensor=None,
                 number_of_channels=0,
                 number_of_frequencies=0,
                 number_of_snapshots=0,
                 all_run_id_parameter_combinations=[]):
        self.channel_dict = channel_dict
        self.run_id_dict = run_id_dict
        self.frequencies = frequencies
        self.tensor = tensor
        self.number_of_channels = number_of_channels
        self.number_of_frequencies = number_of_frequencies
        self.number_of_snapshots = number_of_snapshots
        self.all_run_id_parameter_combinations = all_run_id_parameter_combinations

    def get_tensor(self):
        """get bare f-parameter data tensor, indicies are (snapshot,channel,frequency)"""
        return self.tensor

    def get_indices_string(self):
        return "(snapshot,channel,frequency)"

    def get_frequencies(self):
        """frequencies in Hz"""
        return self.frequencies

    def get_number_of_channels(self):
        """number of channels = number Tx* number Rx antennas"""
        return self.number_of_channels

    def get_number_of_frequencies(self):
        """number of simulated frequencies"""
        return self.number_of_frequencies

    def get_number_of_snapshots(self):
        """number of snapshots from parameter sweep"""
        return self.number_of_snapshots

    def get_run_id_dict(self):
        """dictionary mapping the snapshot number to the solver run id"""
        return self.run_id_dict

    def get_channel_dict(self):
        """dictionary mapping the channel number to the Tx/Rx pair name"""
        return self.channel_dict
    
    def get_time_data(self, time_sweep_parameter_name):
        """list of time instances from specified parameter name"""
        time_instances_list = []
        for run_id_parameter_combinations in self.all_run_id_parameter_combinations:
            time_at_run_id = float(run_id_parameter_combinations[time_sweep_parameter_name])
            time_instances_list.append(time_at_run_id)
        return time_instances_list

    def __eq__(self, other):
        if not isinstance(other, ChannelTensor):
            return False
        return self.channel_dict == other.channel_dict and np.array_equal(self.tensor, other.tensor)

    def serialize_to_pickle_file(self, filename):
        """Serialize the channel tensor to file by Python pickle module."""
        with open(filename, 'wb') as f:
            pickle.dump(self, f)

    @classmethod
    def from_pickle_file(cls, filename):
        """Deserialize the channel tensor from file by Python pickle module."""
        with open(filename, 'rb') as f:
            new_tensor = pickle.load(f)
            return new_tensor
        raise FileNotFoundError('file {} not found!'.format(filename))

    @staticmethod
    def create_channel_dict(txs, rxs):
        channel_dict = {}
        ichannel = 0
        for arx in rxs:
            for atx in txs:
                channel_dict[ichannel] = (arx, atx)
                ichannel += 1
        return channel_dict

    @classmethod
    def from_cst_result3d(cls,
                          result3d,
                          txs,
                          rxs,
                          skip_nonparametric=True,
                          broad_band_result=False,
                          include_run_ids=[]):
        """
        create channel tensor from cst project

        Parameters
        ----------
        file_name: str
            name of cst file including file extension
        txs: list(str)
            list of active transmitter names in cst model
        rxs: list(str)
            list of relevant receiver names in cst model
        """

        # create channel dict
        channel_dict = ChannelTensor.create_channel_dict(txs, rxs)
        number_of_channels = len(channel_dict)

        # open project

        def generate_full_tree_name(Rx, Tx):
            if broad_band_result:
                return '1D Results\\F-Parameters Broad Band\\F{},{}'.format(Rx, Tx)
            else:
                return '1D Results\\F-Parameters\\F{},{}'.format(Rx, Tx)

        # create run_id dict
        Rx, Tx = channel_dict[0]
        fpara_name = generate_full_tree_name(Rx, Tx)
        all_run_ids = result3d.get_run_ids(fpara_name, skip_nonparametric)
        
        for run_id in include_run_ids:
            if (run_id not in all_run_ids):
                print('WARNING: Run id ',run_id,' cannot be included as it does not exist')
                               
        run_ids = []
        all_run_id_parameter_combinations = []
        for run_id in all_run_ids:
            if ( (run_id in include_run_ids) or len(include_run_ids) == 0):
                run_ids.append(run_id)
                all_run_id_parameter_combinations.append(result3d.get_parameter_combination(run_id))

        run_id_dict = {}
        irun = 0
        for id in run_ids:
            run_id_dict[irun] = id
            irun += 1
        number_of_snapshots = len(run_ids)
        # create tensor
        first_load = True
        for irun in run_id_dict:
            for ichannel in channel_dict:
                Rx, Tx = channel_dict[ichannel]
                fpara_name = generate_full_tree_name(Rx, Tx)
                Fparameter = result3d.get_result_item(
                    fpara_name, run_id=run_id_dict[irun])
                if first_load:
                    frequency_scale_to_Hz = get_frequency_unit_from_xlabel(
                        Fparameter.xlabel)
                    frequencies = frequency_scale_to_Hz * \
                        np.array(Fparameter.get_xdata())
                    number_of_frequencies = len(frequencies)
                    tensor = np.zeros((number_of_snapshots,
                                       number_of_channels,
                                       number_of_frequencies),
                                      dtype=np.complex128)
                first_load = False
                tensor[irun, ichannel, :] = np.array(Fparameter.get_ydata())
        return cls(channel_dict,
                   run_id_dict,
                   frequencies,
                   tensor,
                   number_of_channels,
                   number_of_frequencies,
                   number_of_snapshots,
                   all_run_id_parameter_combinations)

    @classmethod
    def from_cst_file(cls,
                      file_name,
                      txs,
                      rxs,
                      skip_nonparametric=True,
                      broad_band_result=False,
                      include_run_ids=[]):
        """
        create channel tensor from cst project from file `my_fancy_project.cst`

        Parameters
        ----------
        file_name: str
            name of cst file including file extension
        txs: list(str)
            list of active transmitter names in cst model
        rxs: list(str)
            list of relevant receiver names in cst model
        """
       
        # cst result importer prevent issues with relative paths
        file_name = os.path.abspath(file_name)
        if not pathlib.Path(file_name).exists:
            raise FileNotFoundError("file {} not found".format(file_name))
        project = ProjectFile(file_name, allow_interactive=True)
        return cls.from_cst_result3d(project.get_3d(),
                                    txs,
                                    rxs,
                                    skip_nonparametric,
                                    broad_band_result,
                                    include_run_ids)


def get_antenna_positions_from_model(model_file_name, rxs, txs):
    """retrieve antenna position from the 'Parameters.json' file of the model

    Parameters
    ----------
    model_file_name: str
        path to cst model file
    rxs: list(str)
        list of Rx antenna names
    txs: list(str)
        list of Tx antenna names

    Returns
    -------
    tuple(rx_dict, tx_dict)
        rx_dict : dict(str,array(3)) antenna name and position vector
        tx_dict : dict(str,array(3)) antenna name and position vector
    """
    if not pathlib.Path(model_file_name).exists:
        return False
    json_file = pathlib.Path.joinpath(pathlib.Path(
        model_file_name).parent, pathlib.Path(model_file_name).stem, 'Model')
    json_file = json_file / 'Parameters.json'
    if not pathlib.Path(json_file).exists:
        return False
    # frequency_scale_to_Hz = 1.0
    with json_file.open('r') as f:
        jdata = json.load(f)
        name_val_dict = {}
        for aentry in jdata["parameters"]:
            name_val_dict[aentry['name']] = aentry['value']
        rx_dict = {}
        for rx in rxs:
            name_x = "{}_x".format(rx)
            x = float(name_val_dict[name_x])
            name_y = "{}_y".format(rx)
            y = float(name_val_dict[name_y])
            name_z = "{}_z".format(rx)
            z = float(name_val_dict[name_z])
            rx_dict[rx] = np.array([x, y, z])
        tx_dict = {}
        for tx in txs:
            name_x = "{}_x".format(tx)
            x = float(name_val_dict[name_x])
            name_y = "{}_y".format(tx)
            y = float(name_val_dict[name_y])
            name_z = "{}_z".format(tx)
            z = float(name_val_dict[name_z])
            tx_dict[tx] = np.array([x, y, z])
        return (tx_dict, rx_dict)
