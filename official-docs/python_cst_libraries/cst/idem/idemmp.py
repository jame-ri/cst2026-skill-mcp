# Copyright 1998-2024 Dassault Systemes Deutschland GmbH.

import os
import re
import subprocess
import inspect
import cst.interface
from pathlib import Path

_DE_FOR_LICENSE = None


def _idemmp_exe_wrapper(exe_name, **kwargs):
    global _DE_FOR_LICENSE
    if not _DE_FOR_LICENSE:
        _DE_FOR_LICENSE = cst.interface.DesignEnvironment.new(options=["--hide"])

    env = os.environ.copy()
    env["IDEM_DE_FOR_LICENSE"] = _DE_FOR_LICENSE.pid()

    exe_path = Path(cst.interface.install_paths.bin64()) / exe_name
    cmd = [exe_path]
    for key, value in kwargs.items():
        if value is None:
            continue
        cmd.append(f"-{key}")
        cmd.append(f"{value}")

    pi = subprocess.run(cmd)
    if pi.returncode:
        raise RuntimeError(f"Process {exe_name} exited with exit code {pi.returncode}")


# wrapper for:
# idemmp_fitting -its <input filename> -o <output file> [-tol <tol>] [-orderMin <orderMin>] [-orderStep <orderStep>] [-orderMax <orderMax>] [-order <order>] [-bandwidth <bandwidth>] [-DC <DC>] [-sym <sym>] [-nThreads <nThreads>] [-xml <xml filename>] [-help]
def fitting(
    input_filename,
    output_filename,
    tol: float = None,
    orderMin: int = None,
    orderStep: int = None,
    orderMax: int = None,
    order: int = None,
    bandwidth: float = None,
    dc: bool = None,
    sym: bool = None,
    nThreads: int = None,
    xml: os.PathLike = None,
):
    func_args = locals().copy()
    func_args.pop("input_filename")
    func_args.pop("output_filename")

    ext = Path(input_filename).suffix
    if not ext:
        raise RuntimeError(f"Missing file extension in {input_filename}")

    input_filename_type = "ih5"
    if re.match("\.s[0-9]+p", ext):
        input_filename_type = "its"

    func_args[input_filename_type] = input_filename
    func_args["o"] = output_filename

    exe_name = inspect.currentframe().f_code.co_name
    _idemmp_exe_wrapper(exe_name, **func_args)




