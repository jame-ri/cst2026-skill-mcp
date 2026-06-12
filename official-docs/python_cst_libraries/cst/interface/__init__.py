# Copyright 1998-2023 Dassault Systemes Deutschland GmbH.

"""
The cst.interface package provides a python interface that allows to control the CST Studio Suite.
It is possible to connect to a running DesignEnvironnent (main screen) or start a new one.
Once connected the package provides access to CST projects (.cst) which can be opened, closed and 
saved and provide access to the associated applications (prj.model3d).
"""

from .studio import *

__all__ = ["DesignEnvironment", "Project", "ProjectType"]
