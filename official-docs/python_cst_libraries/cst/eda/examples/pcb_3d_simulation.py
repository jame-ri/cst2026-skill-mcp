# Copyright 1998-2023 Dassault Systemes Deutschland GmbH.

"""
**End-to-End example - Simulate a PCB in 3D**
 - using the :mod:`cst.eda.pcb_api` module for
    - importing a PCB design into CST format
    - defining 3D simulation settings / ports
 - using the :mod:`cst.interface` module for
    - 3D simulation of the PCB in CST Microwave Studio
 - using the :mod:`cst.results` for
     - S/Y/Z-matrix result extraction
"""

import os
from os.path import join, dirname, abspath, exists

datadir = join( dirname(abspath(__file__)), 'data' )

def _boundary_distance( dists):
    assert len(dists)==6
    return """
        With Background 
             .ResetBackground 
             .XminSpace "%s" 
             .XmaxSpace "%s" 
             .YminSpace "%s" 
             .YmaxSpace "%s" 
             .ZminSpace "%s" 
             .ZmaxSpace "%s" 
             .ApplyInAllDirections "False" 
        End With 
    """ % tuple(dists)


def _boundary_condition( bcs ):
    assert len(bcs)==6
    return """
With Boundary
     .Xmin "%s"
     .Xmax "%s"
     .Ymin "%s"
     .Ymax "%s"
     .Zmin "%s"
     .Zmax "%s"
     .Xsymmetry "none"
     .Ysymmetry "none"
     .Zsymmetry "none"
     .ApplyInAllDirections "False"
End With
    """ % tuple([bc for bc in bcs ])


def create_simulation(outdir):
    from cst.eda.pcb_api import PCB

    assert exists(outdir)

    # import design:
    design = join( datadir, 'workflow.dar')
    ldb_file = join(outdir, 'ldb.ldb')
    pcb = PCB.convert_from(design, cad_type='simlab', ldb_file=ldb_file)

    # some checks:
    assert pcb.length_unit.name == 'mil'
    mm_to_mil = 1/0.0254

    # sim. settings:
    ss = pcb.simulation_settings  # abbr.
    signal_net = 'DATA[3]'

    ss.select_nets(['GND', signal_net], True)
    ss.restrict_to_selected_nets = True

    net = pcb.net(signal_net)
    for pin in net.pins:
        p = ss.discrete_port(pin)
        assert p.use_pec_sheet
        p.reference_nets = ['GND']

    nbas = ss.net_based_area_selection  # abbr.
    nbas.nets = [signal_net]
    nbas.distance = 300  # mil
    nbas.snap_to_grid = True
    nbas.grid_size = 0.6 * mm_to_mil  # because design is in mil

    # create 3D Microwave Studio project
    from cst.interface import DesignEnvironment
    de = DesignEnvironment()
    prj = de.new_mws()

    from cst.eda.pcb_api import import_pcb
    import_pcb(pcb, prj, ldb_name='pcb.ldb')

    # set up 3D simulation
    prj.model3d.add_to_history('bc', _boundary_condition(['magnetic']*6))
    prj.model3d.add_to_history('boundary', _boundary_distance([10]*6))
    prj.model3d.add_to_history('solver type', 'ChangeSolverType "HF Frequency Domain"')
    prj.model3d.add_to_history('freq range', 'Solver.FrequencyRange "0.01", "5"')
    prj.model3d.add_to_history('tet order', 'FDSolver.OrderTet "First"')
    prj.model3d.add_to_history('mesh adapt', 'FDSolver.MeshAdaptionTet "False"')
    prj.model3d.add_to_history('compute yz', 'PostProcess1D.ActivateOperation "yz-matrices", "TRUE"')

    return pcb, prj, de


def post_process(cstfile, result_name):
    if not exists(cstfile):
        return None
    from cst.results import ProjectFile
    pp = ProjectFile(cstfile, allow_interactive=True)
    pp3d = pp.get_3d()
    items = pp3d.get_tree_items()
    results = {}
    for i,j in [ (i,j) for i in (1,2) for j in (1,2) ]:
        item =  f'1D Results\\{result_name}{i},{j}'
        if item not in items:
            return None
        results[i,j] = pp3d.get_result_item(item).get_data()
    return results


def main(outdir):
    """
    Create and run a 3D HF simulation of a printed circuit board,
    post-process and save results.

    :param outdir: output directory, must exist and be empty
    """

    assert not os.listdir(outdir)

    # create 3D simulation
    cstfile = join( outdir, 'sim.cst')
    pcb, prj, de = create_simulation(outdir)
    prj.save(cstfile)

    # run 3D simulation
    prj.model3d.run_solver()

    # export in touchstone format:
    from cst.post_processing.s_parameters import export_touchstone
    export_touchstone(prj, join(outdir, 'touchstone'))

    # post-process S,Y,Z matrices: extract raw data into .pickle files:
    for result_name in (r'S-Parameters\S', r'Z Matrix\Z', r'Y Matrix\Y'):
        results = post_process(cstfile, result_name)
        assert results is not None
        import pickle
        with open(join(outdir, result_name[-1]+'.pickle'),'wb') as out:
            pickle.dump(results, out)

    # close this CST Studio Suite instance
    de.close()

    print('-'*60)
    print(f"Stored 3D simulation results in outdir={outdir}")
    print('-'*60)

    return cstfile, results, de


if __name__=='__main__':
    import tempfile
    outdir = tempfile.mkdtemp(prefix='output_CST_')
    main(outdir=outdir)
    pass
