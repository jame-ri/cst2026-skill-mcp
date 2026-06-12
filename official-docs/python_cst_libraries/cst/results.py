# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

"""
This module allows reading one-dimensional result curves, data points and two-dimensional colormap results of CST project files.

No running instance of CST Studio Suite is required for data access.

Supported are unpacked and unprotected project files generated with CST Studio Suite 2025 or CST Studio Suite 2026. 

To understand how this module can be used, see the `Examples`_ section of the documentation.
"""
from _cst_results import *
from _cst_interface.units import *


def get_version_info():
    """
    Get a dictionary containing version information of the files used by this module
    """
    info = dict()
    info[__name__] = {'Version': str(__version__), 'File': __file__}
    import _cst_results
    info[ResultItem.__module__] = {'Version': _cst_results.__version_info__(),
                                   'File': _cst_results.__file__}
    return info


def print_version_info():
    """Print version information of this module"""
    info = get_version_info()
    print("Versions:")
    for name, v in info.items():
        print(" " + name + " : " + v['Version'])
    print("Files:")
    for name, v in info.items():
        print(" " + name + " : " + v['File'])


__version__ = "2025-07-14"
__all__ = ["ResultItem", "ProjectFile", "ResultModule", "get_version_info", "print_version_info"]
