# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

from pathlib import Path
from cst.radar.channel_tensor import ChannelTensor
import numpy as np

import pathlib
import os


model_dir = Path(r'./')
cst_file_name = model_dir / r'modelMIMOConfig2d.cst'


txs = ['Tx1', 'Tx2', 'Tx3', 'Tx4']  # names transmitter FFS in model
rxs = ['Rx1', 'Rx2', 'Rx3']  # names receiver FFS in model
broad_band_result = True
skip_nonparametric = True

time_sweep_parameter_name = 't'
all_cpi_times = np.linspace(0,10,17)
chirp_duration = 49.155146e-6
coherent_proc_interval_duration = 0.971620e-3
coherent_proc_interval_chirp_count = 3
#chirp_duty_cycle = 15.177281 # Not needed when chirp count and duration are given

selected_cpi_times = [0, 1e-5, 0.125, 0.25, 0.5, 0.625, 0.750, 0.875, 1.]


## STEP 1: CREATE SWEEP DATA FROM CPI TIMES
chirp_midpoint_times = []
for cpi_time in all_cpi_times:
    # Identify frame index (starts from 1) at current time instance
    frame_idx = int(np.floor(1+cpi_time/coherent_proc_interval_duration))
    # Chirps are assumed to come sequentially (without gaps) at the beginning of a frame
    for chirp_idx_in_frame in range(1,coherent_proc_interval_chirp_count+1):
        chirp_midpoint_times.append( (frame_idx-1)*coherent_proc_interval_duration + (chirp_idx_in_frame-0.5)*chirp_duration )


## STEP 1.5: PERFORM CST SIMULATION


## STEP 2: LOAD DATA FROM CST SIMULATION
from cst.results import ProjectFile
# cst result importer prevent issues with relative paths
cst_file_name = os.path.abspath(cst_file_name)
if not pathlib.Path(cst_file_name).exists:
    print('Error. CST file cannot be found')
    #return False
Rx, Tx = (rxs[0], txs[0])    
project = ProjectFile(cst_file_name, allow_interactive=True)
fpara_name = '1D Results\\F-Parameters\\F{},{}'.format(Rx, Tx)
if broad_band_result:
    fpara_name = '1D Results\\F-Parameters Broad Band\\F{},{}'.format(Rx, Tx)
# Load all the Run IDs (starts from 1)
all_run_ids = project.get_3d().get_run_ids(fpara_name, skip_nonparametric)

runId_timeInstance_frameIdx_ntuple_list = []
for run_id in all_run_ids:
    # Get the parameter names and their values at the given Run ID
    run_id_parameter_combinations = project.get_3d().get_parameter_combination(run_id)
    time_at_run_id = float(run_id_parameter_combinations[time_sweep_parameter_name])  
    # Identify frame index (starts from 1) at current time instance
    frame_idx = int(np.floor(1+time_at_run_id/coherent_proc_interval_duration))
    # Fill a n-tuple list which holds: 1) the Run ID, 
    # 2) the time instance which corresponds to that Run ID in the simulation,
    # 3) the frame index for the overall transmitted FMCW signal
    runId_timeInstance_frameIdx_ntuple_list.append((run_id, time_at_run_id, frame_idx))
    

   

## STEP 3: GET RUN ID/TIME INSTANCE FROM SELECTED CPIs
selected_runId_timeInstance_frameIdx_ntuples = []
for cpi_time in selected_cpi_times:
    # Identify frame index (starts from 1) at selected time instance
    frame_idx = int(np.floor(1+cpi_time/coherent_proc_interval_duration))
    # Find the n-tuple which has the specified frame index,
    # then add it into the according list
    matches = [ntuple for ntuple in runId_timeInstance_frameIdx_ntuple_list if ntuple[2] == frame_idx ]
    if (len(matches) == 0):
        print("WARNING: No RunID/Time Instance match for selected CPI time ", cpi_time)
    else:
        for match in matches:
            # Check if the selected CPI times yield the same Run ID
            # Skip if an entry already exists in the list, no need to put same data repeatedly
            if match not in selected_runId_timeInstance_frameIdx_ntuples:
                selected_runId_timeInstance_frameIdx_ntuples.append(match)
            else:
                print("INFO: n-tuple with Run ID",match[0],"already exists in the list, skipping..")
# Extract the Run IDs from the n-tuple
run_ids_to_include = [run_ids[0] for run_ids in selected_runId_timeInstance_frameIdx_ntuples ]  



#channel_tensor = ChannelTensor.from_cst_file(cst_file_name, txs, rxs, skip_nonparametric=True, broad_band_result=True)
#print(channel_tensor.get_time_data(time_sweep_parameter_name))

channel_tensor = ChannelTensor.from_cst_file(cst_file_name, txs, rxs, skip_nonparametric=True, broad_band_result=True, include_run_ids=run_ids_to_include)
print(channel_tensor.get_time_data(time_sweep_parameter_name))

