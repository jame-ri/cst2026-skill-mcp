#!/usr/bin/env bash

cstinst=$(readlink -f "$0")
curdir=$(dirname "$cstinst")
cstinst=$(dirname "$curdir")
cstinst=$(dirname "$cstinst")
cstinst=$(dirname "$cstinst")
cstinst=$(dirname "$cstinst")
cstinst=$(dirname "$cstinst")

export LD_LIBRARY_PATH=$cstinst/LinuxAMD64
export PYTHONPATH=$cstinst/LinuxAMD64/python_cst_libraries
$cstinst/LinuxAMD64/python/python $curdir/example_starter.py
