# Copyright 1998-2023 Dassault Systemes Deutschland GmbH.

"""
**EDA Import to 3D**
using the :mod:`.pcb_api` module for manipulation/selection of components:
 - 'mounted' state
"""

import os
from os.path import join, dirname, abspath, exists

datadir = join( dirname(abspath(__file__)), 'data' )


def create_simulation(outdir, names_of_mounted_components):
    from cst.eda.pcb_api import PCB

    assert exists(outdir)

    # import design:
    design = join( datadir, 'workflow.dar')
    ldb_file = join(outdir, 'ldb.ldb')
    pcb = PCB.convert_from(design, cad_type='simlab', ldb_file=ldb_file)

    # some checks:
    assert pcb.length_unit.name == 'mil'
    mm_to_mil = 1 / 0.0254

    # select subset of comps:
    bbox = None
    for c in pcb.components:
        c.is_mounted = c.name in names_of_mounted_components
        if c.is_mounted:
            for p,p2 in c.outline:
                if bbox is None:
                    from cst.eda.pcb_api import BoundingBox
                    bbox = BoundingBox(p)
                else:
                    bbox.extend(p)

    # sim. settings:
    ss = pcb.simulation_settings  # abbr.
    ss.select_rectangular_area(bbox.xmin-10, bbox.xmax+10, bbox.ymin, bbox.ymax)

    # create 3D Microwave Studio project
    from cst.interface import DesignEnvironment
    de = DesignEnvironment()
    prj = de.new_mws()

    # import the PCB
    from cst.eda.pcb_api import import_pcb
    import_pcb(pcb, prj, ldb_name='pcb.ldb')

    return pcb, prj, de


def main(outdir):
    """
    Create 3D model of the demo PCB, with focus on components.
    :param outdir: output directory, must exist and be empty
    """

    assert not os.listdir(outdir)

    names_of_mounted_components = 'R1', 'R2', 'R4'

    # create 3D simulation
    cstfile = join( outdir, 'sim.cst')
    pcb, prj, de = create_simulation(outdir, names_of_mounted_components)
    prj.save(cstfile)

    # close this CST Studio Suite instance
    de.close()

    print('-'*60)
    print(f"Created 3D Model containing components {names_of_mounted_components}: {cstfile}")
    print('-'*60)


if __name__=='__main__':
    import tempfile
    outdir = tempfile.mkdtemp(prefix='output_CST_')
    main(outdir=outdir)
    pass
