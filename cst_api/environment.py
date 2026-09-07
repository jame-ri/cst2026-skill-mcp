"""Resolve machine bindings at runtime; no machine-specific paths are stored."""
import os
from pathlib import Path
import sys


def configure():
    explicit = os.environ.get("CST_PYTHON_LIB_DIR")
    roots = [Path(value) for name in ("CST_INSTALL_DIR", "CST_HOME", "CST_ROOT")
             if (value := os.environ.get(name))]
    for name in ("ProgramFiles", "ProgramFiles(x86)"):
        if os.environ.get(name):
            roots.append(Path(os.environ[name]) / "CST Studio Suite 2026")
    candidates = ([Path(explicit)] if explicit else []) + [
        root / subdirectory for root in roots
        for subdirectory in ("AMD64/python_cst_libraries", "python_cst_libraries")]
    for candidate in candidates:
        if (candidate / "cst").is_dir():
            sys.path.insert(0, str(candidate.resolve()))
            return
    # A compatible interpreter may already have the vendor bindings installed.
