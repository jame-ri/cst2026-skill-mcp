# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

from typing import Dict, List, Tuple
from pathlib import Path

import _cst_eda_interface.part_library

# import public classes and functions into namespace "cst.eda.part_library"
from _cst_eda_interface.part_library import PartLibrary

from .report_items import ReportItem, Severity, removed_duplicates

_magtrans = {
    "f": 1e-15,
    "F": 1e-15,
    "p": 1e-12,
    "P": 1e-12,
    "n": 1e-9,
    "N": 1e-9,
    "u": 1e-6,
    "U": 1e-6,
    "\u00b5": 1e-6,  # greek mu
    "m": 1e-3,
    "k": 1e3,
    "K": 1e3,
    "M": 1e6,
    "G": 1e9,
}


def to_number(s):
    """
    Convert python value (int, float, str) to a number.
    Trailing unit prefixes (n,m,k,M,G etc.) are supported, e.g. to_number("1.2k")==1200.

    :param s: Type can be one of int, float, or str.
    :return: The number (float or int).
    """
    if type(s) in (float, int):
        return s
    assert isinstance(s, str)
    assert len(s) > 0
    if s[-1] in _magtrans:
        return float(s[:-1]) * _magtrans[s[-1]]
    else:
        return float(s)


def add_rlcs_from_csvfile(
    part_lib: PartLibrary,
    csv_file: Path,
    property_to_purpose_mapping: List[Tuple[str,str]],
) -> List[ReportItem]:
    """
    The function read a table from the csv-file and interprets the values in the rows
    to create lumped elements R/L/C with parasitics, which will be added to the given `plb`.
    It will return a list of errors that occurred in the conversion.
    In case of unreadable or broken csv file, it will raise an exception.

    :param part_lib: The part library to which the parts need to be added
    :param csv_file: The full path to the csv file which contains the values for importing the parts.
    :param property_to_purpose_mapping: The mapping that links the ECAD component properties to
        the standardized component properties. The data format is a list of tuples, where each tuple
        is of the form `(PROPERTY_NAME: str, PURPOSE: str)`,
        and `PURPOSE` is the standardized property purpose, i.e. one of

        * `REFDES`: component-instance name
        * `PARTNAME`: library-part's name
        * `TYPE`: part type (`R`, `L`, or `C`)
        * `NOMINAL`: nominal value, e.g. 10uF
        * `R`: resistance nominal value
        * `L`: inductance nominal value
        * `C`: capacitance nominal value
        * `Rp`: parasitic resistance value
        * `Lp`: parasitic inductance value
        * `Cp`: parasitic capacitance value

        Either `NOMINAL` or one of `R`, `L`, or `C` must be provided.

    :return: List of `ReportItem`, can be a mixture of errors, warnings, info.
    """
    from ._csv_import_impl import get_rlcs_and_bom_from_csvfile_impl

    tmp = get_rlcs_and_bom_from_csvfile_impl(csv_file, property_to_purpose_mapping)

    report_items = tmp._report_items

    for i in tmp._rlc_items:
        try:
            i.add_to_plb(part_lib)
            severity = Severity.INFO
            msg = "Created part"
        except Exception as e:
            severity = Severity.ERROR
            msg = f"Unable to create part: {str(e)}"

        report_items.append(
            ReportItem(
                type='PART',
                id=i.partname,
                severity=severity,
                message=msg
            )
        )

    return removed_duplicates(report_items)


def get_bom_from_csvfile(
    csv_file: Path,
    property_to_purpose_mapping: List[Tuple[str, str]],
) -> Dict[str,str]:
    """
    Read BOM (component-to-partname mapping) from csv-file.

    :param csv_file:
    :param property_to_purpose_mapping: component-property name mapping:
        should cover REFDES and PARTNAME at least
    :return: mapping of component name to partname
    """

    from ._csv_import_impl import _read_components_csv_file, map_comp_props
    data = _read_components_csv_file(csv_file)
    if not data:
        raise RuntimeError(
            f"No data could be extracted from {csv_file}, please verify that the file content is correct."
        )

    comp_props = map_comp_props(data, property_to_purpose_mapping)

    return { cp.REFDES: (cp.PARTNAME if cp.PARTNAME else None)
             for cp in comp_props if cp.REFDES }
