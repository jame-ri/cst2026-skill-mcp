# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

"""
The cst package provides a Python interface to the CST Studio Suite.
"""
from pathlib import Path

def _get_install_path() -> Path:
    # this file should lie in <CST_INSTALL_DIR>/<Bin64>/python_cst_libraries/cst
    return Path(__file__).parent.parent.parent.parent


def _get_install_bin64():
    import os
    # this file should lie in <CST_INSTALL_DIR>/<Bin64>/python_cst_libraries/cst
    this_dir = os.path.dirname(os.path.abspath(__file__))
    if not this_dir.endswith(os.path.normcase("python_cst_libraries/cst")):
        return

    bin64 = os.path.normpath(os.path.join(this_dir, '../../'))
    return bin64


def _check_supported_python_version():
    from sys import version_info, platform
    import os
    import re

    bin64 = _get_install_bin64()
    if not bin64:
        return

    if platform == 'win32':
        cp = 'cp'
    else:
        cp = 'cpython-'

    cst_interface_re = re.compile(f"_cst_interface.{cp}3([0-9]+).*")
    cst_interface_files = [f for f in os.listdir(bin64) if cst_interface_re.match(f)]
    supported_versions = [f'3.{cst_interface_re.match(f).group(1)}' for f in cst_interface_files]

    if f'{version_info.major}.{version_info.minor}' not in supported_versions:
        raise ImportError(f"The cst package supports only Python {'/'.join(supported_versions)}")


def _get_version_from_image_version(install_path):
    import os
    image_version = os.path.join(install_path, 'Image_Version')
    if os.path.exists(image_version):
        with open(image_version) as fimage_version:
            contents = fimage_version.read()

        try:
            lines = contents.split()
            studio_version_major, studio_version_minor = lines[3].split(".")
            return (studio_version_major, studio_version_minor)
        except Exception as e:
            raise ImportError("Failed to read CST Studio Version from Image_Version file with contents:\n{0}\n{1}".format(contents, str(e)))
    else:
        raise ImportError("Unable to find Image_Version file {0}. Did you move this python file outside the CST Installation?".format(image_version))



def _add_install_bin64_to_sys_path():
    import sys
    import os

    bin64 = _get_install_bin64()
    if not bin64:
        return

    install_path = os.path.normpath(os.path.join(bin64, '../'))
    studio_version_major, _ = _get_version_from_image_version(install_path)
    os.environ["CST_INSTALLPATH_{0}".format(studio_version_major)] = install_path

    if bin64 in sys.path:
        return
    sys.path.insert(0, bin64)

_check_supported_python_version()
_add_install_bin64_to_sys_path()


def __getattr__(name: str):
    if name == "__studio_version_major__":
        return _get_version_from_image_version(_get_install_path())[0]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
