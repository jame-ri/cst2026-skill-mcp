# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

from cst.interface import get_calling_app as _get_calling_app, get_current_project as _get_current_project

import warnings


warnings.warn(
    "The module 'cst.interface.current_module' is deprecated and will be removed in future versions. Please use 'cst.interface.get_calling_app()' or 'cst.interface.get_current_project()' instead.",
    DeprecationWarning,
    stacklevel=2
)

try:
    _prj = _get_current_project()
except Exception as e:
    raise RuntimeError(f"Error in setting current_project: Could not connect to open project: " + str(e))

if _prj is None:
    raise RuntimeError("Error in setting current_project: Could not connect to open project.")

model3d = _prj.model3d
schematic = _prj.schematic
filename = _prj.filename
folder = _prj.folder

try:
    caller_app = _get_calling_app()
    assert caller_app
except Exception as e:
    raise RuntimeError("Error in setting current_project: Could not set caller app. " + str(e))

__all__ = ["model3d", "schematic", "caller_app"]
