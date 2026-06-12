# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

import os
from typing import List, Optional

def get_post_converter_script_paths(src: Optional[str]=None):
    from _cst_eda_interface.pcb_api import (
        _get_post_converter_script_paths,
        _eval_post_converter_script_paths,
    )

    if src:
        return _eval_post_converter_script_paths(src)
    return _get_post_converter_script_paths()

def write_post_converter_script_paths(paths: List[os.PathLike]):
    from _cst_eda_interface.pcb_api import _write_post_converter_script_paths

    _write_post_converter_script_paths([str(p) for p in paths])
    
def read_create_vias():
    from _cst_eda_interface.pcb_api import _read_create_vias
    return _read_create_vias()

def write_create_vias(b):
    from _cst_eda_interface.pcb_api import _write_create_vias
    _write_create_vias(b)