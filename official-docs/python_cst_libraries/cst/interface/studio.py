# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

"""
Wrapper module around _cst_interface
"""

import csv
import os
from pathlib import Path
from typing import Union, List, Dict
from contextlib import contextmanager

from _cst_interface import DesignEnvironment as _DesignEnvironmentBase
from _cst_interface import (
    Project,
    ProjectType,
    running_design_environments,
    install_paths,
    Dim,
    Model3D,
)


class DesignEnvironmentStartupError(Exception):
    """Is raised when something goes wrong while launching the DesignEnvironment"""

    def __init__(self, message, returncode):
        super().__init__(message)
        self.returncode = returncode


class DesignEnvironment(_DesignEnvironmentBase):
    """
    This class provides an interface to the CST Studio Suite main frontend.
    It allows to connect to, and open new CST Studio Suite instances. Furthermore it allows to
    open or create .cst projects.
    """

    def __init__(
        self,
        mode=_DesignEnvironmentBase.StartMode.New,
        pid=None,
        options=None,
        gui_linux=None,
        process_info=None,
        env=None,
    ):
        super(DesignEnvironment, self).__init__(
            mode=mode,
            pid=pid,
            options=options,
            gui_linux=gui_linux,
            process_info=process_info,
            env=env,
        )
        self._post_init()

    @staticmethod
    def new(
        options: List[str] = None,
        gui_linux: bool = None,
        process_info: "ProcessInfo" = None,
        env: Dict = None,
    ) -> "DesignEnvironment":
        return DesignEnvironment(**locals())

    @staticmethod
    def connect(pid_or_address: Union[int, str]) -> "DesignEnvironment":
        return DesignEnvironment(pid=pid_or_address)

    @staticmethod
    def connect_to_any() -> "DesignEnvironment":
        return DesignEnvironment(_DesignEnvironmentBase.StartMode.Existing)

    @staticmethod
    def connect_to_any_or_new() -> "DesignEnvironment":
        return DesignEnvironment(_DesignEnvironmentBase.StartMode.ExistingOrNew)

    @contextmanager
    def quiet_mode_enabled(self):
        """Convenience method to turn on quiet mode with a 'with'-statement and automatically reset it to the previous state on exiting."""
        was_on_before = self.in_quiet_mode()
        if not was_on_before:
            self.set_quiet_mode(True)
        try:
            yield
        finally:
            if not was_on_before:
                self.set_quiet_mode(False)

    @contextmanager
    def quiet_mode_disabled(self):
        """Convenience method to turn off quiet mode with a 'with'-statement and automatically reset it to the previous state on exiting."""
        was_on_before = self.in_quiet_mode()
        if was_on_before:
            self.set_quiet_mode(False)
        try:
            yield
        finally:
            if was_on_before:
                self.set_quiet_mode(True)


DesignEnvironment.connect.__doc__ = _DesignEnvironmentBase.connect.__doc__
DesignEnvironment.connect_to_any.__doc__ = _DesignEnvironmentBase.connect_to_any.__doc__
DesignEnvironment.connect_to_any_or_new.__doc__ = (
    _DesignEnvironmentBase.connect_to_any_or_new.__doc__
)
DesignEnvironment.new.__doc__ = _DesignEnvironmentBase.new.__doc__


def get_calling_app_name():
    """
    Funcion that returns the calling app name (model3d/schemtic/pcbs/...)
    """
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--calling-app", type=str, default=None, help="Calling application"
    )

    args, _ = parser.parse_known_args()

    if args.calling_app is not None:
        return args.calling_app

    # may be unset
    return os.environ.get("CST_CALLING_APP")


def get_calling_app():
    """
    Funcion that returns the calling app, equal to (prj.model3d/prj.schematic/prj.pcbs/...) depending
    on the context in which this app was launched.
    """

    prj = get_current_project()
    name = get_calling_app_name()
    if not name:
        raise RuntimeError(f"Calling app name unknown: {name}")
    try:
        return getattr(prj, name)
    except AttributeError:
        raise RuntimeError(f"Project does not have a running app named: {name}")


def get_current_project():
    """
    Convenience function to get the currently active project. This is either given by command line parameters or auto-deduced.
    In case this function is being called from a python centric-workflow, it will try to determine the currently open project
    automatically.
    """

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cst-pid", "--cst_pid", type=int, default=None, help="CST Studio Suite process ID"
    )
    parser.add_argument("--prj", type=str, default=None, help="Name of active project")

    args, _ = parser.parse_known_args()

    if args.cst_pid is None:
        running_des = running_design_environments()
        if len(running_des) != 1:
            raise RuntimeError(
                f"Detected {len(running_des)} open CST Studio Suites. To auto-determine the current project there"
                " please make sure there is only one CST Studio Suite running. Note that it may take some time to"
                " close CST Studio Suite."
            )
        de = DesignEnvironment.connect(running_des[0])
    else:
        de = DesignEnvironment.connect(args.cst_pid)

    if args.prj is None:
        prj = de.active_project()
    else:
        prj = de.open_project(args.prj)

    return prj


def _connect_to_project_or_open(cstfile: os.PathLike, open_closed: bool):
    des_pids = running_design_environments()
    cstfile = Path(cstfile)
    if not cstfile.is_absolute():
        cstfile = cstfile.absolute()

    if not cstfile.exists():
        raise RuntimeError(f"The given cstfile '{cstfile}' does not exist.")

    if not cstfile.suffix == ".cst":
        raise RuntimeError(
            f"The given cstfile '{cstfile}' does appear to be a .cst file."
        )

    cstfile = cstfile.resolve()

    for de_pid in des_pids:
        de = DesignEnvironment.connect(de_pid)
        try:
            return next(
                de.get_open_project(p)
                for p in de.list_open_projects()
                if Path(p).resolve() == cstfile
            )
        except StopIteration:
            pass

    if open_closed:
        return Project.open(cstfile)
    else:
        raise RuntimeError(
            f"The CST-file '{cstfile}' does not appear to be open anywhere."
        )


