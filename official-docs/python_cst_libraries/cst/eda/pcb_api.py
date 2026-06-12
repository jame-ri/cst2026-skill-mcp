# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

import _cst_eda_interface.pcb_api

# import all classes and functions into namespace "cst.eda.pcb_api"
from _cst_eda_interface.pcb_api import *
from _cst_eda_interface.pcb_api import _ThermalModelSimplificationTopology

# aliases for compatibility
PECSheetPort = DiscretePort

SimulationSettings.thermal_model_simplification_algorithm = property(
    SimulationSettings.thermal_model_layer_simplification.fget,
    SimulationSettings.thermal_model_layer_simplification.fset,
    SimulationSettings.thermal_model_layer_simplification.fdel,
    """.. deprecated:: 2025.0 Use :py:attr:`.thermal_model_layer_simplification` instead."""
)

class Thermal_Model_Simplification_Algorithm:
    """.. deprecated:: 2025.0 Use :py:class:`.ThermalModelLayerSimplification` instead."""
    detail = ThermalModelLayerSimplification.OFF
    compact = ThermalModelLayerSimplification.LAYERWISE
    simple = ThermalModelLayerSimplification.ALL

from _cst_eda_interface.geometry2d import R2 as XYPosition
from .geometry2d import BoundingBox


def import_pcb(pcb, cst_project, ldb_name='pcb.ldb', show_dialog=False, part_library=None):
    """
    Import the PCB into the given 3D project.

    :param pcb: The PCB
    :param cst_project: The CST 3D Project
    :param ldb_name: Short name of the .ldb file to be stored in the cst project
    :param show_dialog: if True, open EDA Import Dialog in interactive mode
    :param part_library: If specified as `PartLibrary` object, part models will be added from here.
    :return: None
    """
    _import_impl(pcb, cst_project, ldb_name=ldb_name, update_existing=False,
                 show_dialog=show_dialog,
                 part_library=part_library
                 )

# shortcut
PCB.import_to = import_pcb


def update_pcb(pcb, cst_project, ldb_name='pcb.ldb', show_dialog=False, part_library=None):
    """
    Update existing PCB import (including PCB simulation settings) in given 3D project.

    :param pcb: The PCB
    :param cst_project: The CST 3D Project
    :param ldb_name: Short name of the .ldb file, already present in the cst project
    :param show_dialog: if True, open EDA Import Dialog in interactive mode
    :param part_library: If specified as `PartLibrary` object, part models will be added from here
    :return: None
    """
    _import_impl(pcb, cst_project, ldb_name=ldb_name, update_existing=True,
                 show_dialog=show_dialog,
                 part_library=part_library
                 )

# shortcut
PCB.update_in = update_pcb


def _import_impl(pcb, cst_project, ldb_name='pcb.ldb', update_existing=False,
                 show_dialog=False,
                 part_library=None
                 ):
    import os

    assert ldb_name.endswith('.ldb')
    ldb_name = os.path.basename(ldb_name)

    from cst.interface import ProjectType
    pt = cst_project.project_type()
    if pt == ProjectType.EMS:
        problem_type = "LF"
    elif pt == ProjectType.MPS:
        problem_type = 'Thermal'
    elif pt == ProjectType.MWS:
        problem_type = 'HF'
    else:
        raise ValueError("Unsupported project type:", pt)

    m3d = os.path.join(cst_project.folder(), 'Model', '3D')

    ldbname_fullpath = os.path.join(m3d, ldb_name)
    if update_existing:
        assert os.path.exists(ldbname_fullpath)

    if not __save_and_generate3D(pcb, ldbname_fullpath, problem_type=problem_type,
                                 show_dialog=show_dialog,
                                 part_library=part_library
                                 ):
        # TODO get report items (errors...) from importdialog and return them and/or store them in the pcb
        raise RuntimeError("Creating the 3D model failed")

    if update_existing:
        cst_project.model3d.full_history_rebuild()
    else:
        cst_project.model3d.add_to_history(
            f"pcb import of {ldbname_fullpath}",
            f"""
            With LayoutDB
                 .Reset
                 .SourceFileName "{ldbname_fullpath}"
                 .LdbFileName "*{ldb_name}"
                 .PcbType "ldb"
                 .KeepSynchronized "True"
                 .LoadDB
            End With 
            """
        )


def __save_and_generate3D(pcb: PCB, targetfile: str, problem_type="High Frequency",
                          show_dialog=False,
                          part_library=None
                          ):
    """
    [do not use directly]
    """

    import os
    import sys
    import subprocess

    from cst.interface import install_paths as ins

    if part_library:
        part_library._add_parts(pcb)

    pcb.save(targetfile)
    pcb.simulation_settings.save(targetfile+'ss')

    if os.path.exists(targetfile + '3d'):
        os.remove(targetfile + '3d')

    env = os.environ.copy()

    lib_env_var = 'PATH'
    if sys.platform.lower().startswith('linux'):
        lib_env_var = 'LD_LIBRARY_PATH'
    cur_lib_env = env.get(lib_env_var)
    if not cur_lib_env:
        env[lib_env_var] = ins.acis_bin64()
    else:
        env[lib_env_var] = ins.acis_bin64() + os.pathsep + cur_lib_env

    edaexe = os.path.join(ins.bin64(), 'pcbimport_AMD64')
    cmd = [edaexe ]
    if not show_dialog:
        cmd.append( '-hide' )
    cmd.extend(['-parent', str(os.getpid())])

    problem_type = problem_type.lower()
    if problem_type in ('hf', 'high frequency'):
        pass
    elif problem_type in ('lf', 'low frequency'):
        cmd.append('-is_ems')
    elif problem_type in ('th', 'thermal'):
        cmd.append('-is_mps')
    else:
        print("WARNING: unknown problem_type '%s', assuming 'High Frequency' instead" % problem_type)

    cmd.extend(['-i', targetfile])

    res = subprocess.run(cmd, env=env)
    return res.returncode == 0


PCB.save_and_generate3D = __save_and_generate3D
