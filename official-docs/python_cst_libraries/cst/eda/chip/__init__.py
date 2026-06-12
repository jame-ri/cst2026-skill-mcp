# Copyright 1998-2023 Dassault Systemes Deutschland GmbH.

import platform

if platform.system() == "Windows":
    import os

    from cst.interface import install_paths
    oa_path = os.path.join(install_paths.root(), "OpenAccess", "bin", "x64", "opt")

    try:
        with os.add_dll_directory(oa_path):
            from _cst_chip_interface import *

    except (AttributeError, ImportError):
        path = os.environ.get('PATH', None)
        if path:
            os.environ['PATH'] = oa_path + os.pathsep + path
        else:
            os.environ['PATH'] = oa_path

        from _cst_chip_interface import *

        if path:
            os.environ['PATH'] = path
        else:
            os.environ.pop('PATH')

