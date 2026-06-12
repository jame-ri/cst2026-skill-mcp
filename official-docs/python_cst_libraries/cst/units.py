# Copyright 1998-2023 Dassault Systemes Deutschland GmbH.

"""
The cst.units library provides an interface to work with SI and imperial units.
"""
from _cst_interface.units import Unit
from _cst_interface.units import *


def scaling_factor_to_SI(unit: "Unit"):
    """
    Compute scaling factor into equivalent SI unit.

    :param unit: Simple or compound unit.
    :return: numerical scaling factor for converting into SI units.
    """
    return (1 * unit).convert_to(unit.inSI()).value


def __getattr__(name):
    if name == "__all__":
        import sys

        return [attr for attr in dir(sys.modules[__name__]) if attr[0] != "_"]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
