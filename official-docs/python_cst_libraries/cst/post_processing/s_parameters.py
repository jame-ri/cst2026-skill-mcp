# Copyright 1998-2023 Dassault Systemes Deutschland GmbH.



def export_touchstone(prj,
                        filename,
                        impedance=50,
                        export_type='S',
                        format="RI",
                        frequency_range = "Full",
                        renormalize = True,
                        use_AR_results = False,
                        n_samples = 0,
                      ):
    """
    :param prj: CST project instance, of cst.interface.DesignEnvironment
    Also see CST VBA online help for the 3D TOUCHSTONE command.
    """

    s = f"""
        With TOUCHSTONE
        .Reset
        .FileName ("{filename}")
        .Impedance ("{impedance}")
        .ExportType ("{export_type}")
        .Format ("{format}")
        .FrequencyRange ("{frequency_range}")
        .Renormalize ("{renormalize}")
        .UseARResults ("{use_AR_results}")
        .SetNSamples ("{n_samples}")
        .Write
        End With
        """

    prj.model3d._execute_vba_code(f'sub main\n{s}\nend sub')
