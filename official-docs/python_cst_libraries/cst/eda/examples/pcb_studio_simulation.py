# Copyright 1998-2023 Dassault Systemes Deutschland GmbH.

"""
**End-to-End example - Simulate a PCB with PCB Studio**
    - script access to PCB Studio (:mod:`cst.interface`)
    - importing a PCB design (using :mod:`cst.eda.pcb_api`)
    - setting up the part library (:mod:`cst.eda.part_library`):
        - R,L,C: standard + SPICE + Touchstone
    - automatic report generation (:mod:`cst.results`)

Note: Not included yet: manipulate PCB Studio solver settings and run solver
"""

import os
from os.path import join, dirname, abspath, exists

datadir = join( dirname(abspath(__file__)), 'data' )


def import_design(outdir, name):
    from cst.eda.pcb_api import PCB

    assert exists(outdir)

    # import design:
    design = join( datadir, name)
    ldb_file = join(outdir, 'ldb.ldb')
    pcb = PCB.convert_from(design, cad_type='simlab', ldb_file=ldb_file)

    return pcb


def create_part_library():
    from cst.eda.part_library import PartLibrary, to_number
    plb = PartLibrary()

    mu = b'\xc2\xb5'.decode('utf-8') # using greek mu works as well

    # add standard Cs
    for name, val in [
        ( "CAP",            "1u"    ),
        ( "PCAP,100UF",     "100U"  ),
        ( "PCAP,3.3UF",     "3.3U"  ),
        ( "CAP,.1UF",       ".1"+mu ),
        ]:
        val = to_number(val)
        plb.add_RLC(name, type='C', C=val, R=0, L=0)

    # add standard Rs
    for name, val in [
        ( "RES_9",          9       ),
        ( "RES_100K",       100e3   ),
        ( "RES_0.294",      0.294   ),
        ( "RES_20K",        '20k'   ),
        ( "RES_28K",        '28k'   ),
        ( "RES_100K",       '100k'  ),
        ( "RES_150",        150     ),
        ( "RES_20K",        20e3    ),
    ]:
        val = to_number(val)
        plb.add_RLC(name, type='R', R=val, C=0, L=0)

    # add standard Ls
    # ...

    # SPICE
    plb.add_RLC_SPICE( 'SPICE_Cap', 'C', join(datadir, 'spice_cap.cir'))

    # Touchstone
    plb.add_RLC_Touchstone( 'Touchstone_Cap', 'C', join(datadir, 'cap-ds.s2p'))

    return plb


def get_bom():
    bom = [
        ("C1", "CAP"),
        ("C2", "PCAP,100UF"),
        ("C3", "PCAP,3.3UF"),
        ("C4", "CAP,.1UF"),
        ("R1", "RES_9"),
        ("R2", "RES_100K"),
        ("R3", "RES_0.294"),
        ("R4", "RES_20K"),
        ("R5", "RES_28K"),
        ("R6", "RES_100K"),
        ("R7", "RES_150"),
        ("R8", "RES_20K"),
    ]
    return dict(bom)


def post_process(cstfile):
    assert exists(cstfile)

    from cst.results import ProjectFile
    pp = ProjectFile(cstfile, allow_interactive=True)
    sch = pp.get_schematic()
    results = {}

    for item in sch.get_tree_items():
        if item.startswith('Blocks\\PCBSSCHEM1\\Impedances'):
            i = sch.get_result_item(item)
            results[item] = i

    return results


def main(outdir):

    if not exists(outdir):
        os.makedirs(outdir)

    pcb = import_design(outdir, 'workflow.dar')

    plb = create_part_library()

    # normally BOM comes with layout, but here we specify explicitly
    bom = get_bom()

    # if simulation does not exist, create and run it:
    cstfile = join( outdir, 'sim.cst')
    if not exists(cstfile):

        # define solver settings
        from cst.eda.pcbs.pi_solver_settings import PISolverSettings, PIPort, Length
        ss = PISolverSettings()
        ss.ports.append(PIPort(comp='C3', pin1='2', pin2='1'))
        ss.ports.append(PIPort('U3', pin1='7')) # auto-find pin2='14' in PCBS!
        ss.voltage_reference_layers = ['LYR_2']
        ss.generate_plots = True
        ss.maximum_mesh_step = Length(1, 'mm')

        # CST simulation part:
        from cst.interface import DesignEnvironment
        de = DesignEnvironment()
        prj = de.new_pcbs()
        pcbs = prj.pcbs

        pcbs.set_pcb(pcb)
        pcbs.set_part_library(plb)
        pcbs.set_bom(bom)

        prj.save(cstfile)

        # transfer solver settings and run solver
        pcbs.set_pi_solver_settings(ss)
        pcbs.run_solver('pi')

        prj.save(cstfile)

        de.close()


    results = post_process(cstfile)

    print('-'*80)
    print(f"Stored PCBS simulation in outdir={outdir}")
    if results:
        print("Results:")
        for item in results:
            print(f"\t{item}")
    else:
        print("No results computed: Manual step still needed at point (*) in script.")
    print('-'*80)

    return cstfile, results


if __name__=='__main__':
    import tempfile
    outdir = tempfile.mkdtemp(prefix='output_CST_')
    cstfile, results = main(outdir=outdir)
