# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

from setuptools.build_meta import *

from pathlib import Path

def _throw_error_non_editable_install():
    raise RuntimeError('This package can be installed in *editable* mode only. Please add "--editable" (or "-e") to your pip install command')

def prepare_metadata_for_build_wheel():
    _throw_error_non_editable_install()

def get_requires_for_build_wheel(config_settings=None):
    _throw_error_non_editable_install()

def get_requires_for_build_sdist(config_settings=None):
    _throw_error_non_editable_install()

def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    _throw_error_non_editable_install()

def get_requires_for_build_editable(config_settings=None):
    return []

def __getattr__(name: str):
    if name == "__version__":
        for parent in Path(__file__).parents:
            image_version = parent / "Image_Version"
            if not image_version.exists():
                continue

            contents = image_version.read_text()
            lines = contents.splitlines()
            if len(lines) > 3:
                version = f"{lines[3]}.{lines[2]}"
                return version
        return "0.0.0+unknown"

