# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict


# nothing specific for components therein, can be replace / elevated:
def _read_components_csv_file(filename):
    with open(filename, encoding="utf-8") as fin:
        try:
            return _read_components_csv_file_impl(fin)
        except Exception as e:
            raise Exception(f"Unable to parse file {str(filename)}:\n{e}")


# nothing specific for components therein, can be replace / elevated:
def _read_components_csv_file_impl(fin):
    import csv

    header_line = fin.readline().strip()
    sep_list = [";", ",", ":", "\t"]
    n = []
    for sep in sep_list:
        n.append(header_line.count(sep))
    if max(n) == 0:
        raise Exception(
            f"Unable to determine separator, appears to be none of {sep_list}"
        )
    separator = sep_list[n.index(max(n))]

    columns = [s.strip() for s in header_line.split(separator)]
    reader = csv.reader(fin, delimiter=separator)
    errors = []
    nc = len(columns)
    col2vals = defaultdict(list)

    for i, row in enumerate(reader):
        if len(row) != nc:
            errors.append(
                f"Incorrect number of fields ({len(row)} != {nc}) in line {i+1} (skipped)."
            )
            continue
        for icol, val in enumerate(row):
            col2vals[icol].append(val)

    if errors:
        msg = "\n\t".join(errors)
        raise RuntimeError(
            f"Multiple errors occurred while trying to import from csv-file:\n{msg}"
        )

    data = {}
    for icol, column_name in enumerate(columns):
        if column_name in data:
            continue

        data[column_name] = col2vals[icol]

    if not data:
        return []

    # convert to row-wise repr.
    lengths = set( len(col) for col in data.values() )
    if len(lengths) > 1:
        raise UserWarning(
            "The given data contains lists of unequal lengths which is unexpected. Aborting import."
        )

    n_rows = lengths.pop()
    res = []
    for irow in range(n_rows):
        di = {}
        for col in columns:
            if s:=data[col][irow].strip():
                di[col] = s
        res.append(di)

    return res


def map_comp_props(
    data: List[Dict], mapping: List[Tuple[str,str]]
):
    # build col-2-purpose(s) map:
    col2ps = defaultdict(list)
    for csv_column, purpose in mapping:
        col2ps[csv_column.upper()].append(purpose)

    # map csv columns to standard Component properties:
    from ._component_properties import ComponentProperties
    comp_props = []
    for di in data:
        mdi = {}
        for k,v in di.items():
            if purposes := col2ps.get(k.upper()):
                for p in purposes:
                    if p not in mdi:  # the first assignment wins
                        mdi[p] = v
        comp_props.append( ComponentProperties(**mdi) )

    return comp_props


def get_rlcs_and_bom_from_comp_props(comp_props):
    from .report_items import ReportItem, Severity, removed_duplicates
    report_items = []

    # process component props:
    rlc_items = []
    ignored_part_def = []
    bom = []
    s2v = {}
    for cp in comp_props:
        if not cp.PARTNAME:
            report_items.append(
                ReportItem(id=cp.REFDES, severity=Severity.ERROR, message="No part name specified")
            )
            continue

        if not cp.TYPE and not cp.R and not cp.L and not cp.R:
            ignored_part_def.append(cp.PARTNAME)
        else:
            try:
                rlc_items.append(cp.to_RLCItem(s2v))
            except Exception as e:
                report_items.append(
                    ReportItem(id=cp.PARTNAME, severity=Severity.ERROR, message=str(e), type='PART')
                )

        try:
            bom.append(cp.to_BOMItem())
        except Exception as e:
            report_items.append(
                ReportItem(id=cp.REFDES, severity=Severity.ERROR, message=str(e), type='BOM')
            )

    # check uniqueness:
    partname2items = defaultdict(list)
    for rlc in rlc_items:
        partname2items[rlc.partname].append(rlc)

    # remove identical defs:
    for items in partname2items.values():
        i = items[0]
        while len(items)>1 and items[-1]==i:
            items.pop()

    # conflicting defs?
    inconsistent_parts = sorted( k for k,v in partname2items.items() if len(v)>1 )

    # mark the conflict in the comp. props as an error:
    for cp in comp_props:
        if cp.PARTNAME in inconsistent_parts:
            report_items.append(
                ReportItem(id=cp.PARTNAME,
                           type='PART',
                           severity=Severity.ERROR,
                           message="Inconsistent part definition in different places"
                           )
            )

    rlc_items = [ v[0] for v in partname2items.values() if len(v)==1 ]

    for i in rlc_items:
        report_items.append(
            ReportItem(id=i.partname, type='PART',
                       severity=Severity.INFO, message="Created part")
        )

    import textwrap

    def prep(ss):
        s = ' '.join(ss) if ss else '<None>'
        return textwrap.indent('\n'.join(textwrap.wrap(s, width=60)), prefix=' '*4)

    report_items.append(
        ReportItem(severity=Severity.SUMMARY,
                   message=f"Parts created: {prep(i.partname for i in rlc_items)}",
                   type='PART',
                   )
    )
    if inconsistent_parts:
        report_items.append(
            ReportItem(severity=Severity.SUMMARY,
                       message=f"Inconsistent parts: {prep(inconsistent_parts)}",
                       type='PART',
                       )
        )
    report_items.append(
        ReportItem(severity=Severity.SUMMARY,
                   message=f"Skipped parts: {prep(ignored_part_def)}",
                   type='PART',
                   )
    )

    from types import SimpleNamespace
    return SimpleNamespace(
                            comp_props=comp_props,
                            bom=bom,
                            _rlc_items=rlc_items,
                            _string_to_value_translations=s2v,
                            _report_items=removed_duplicates(report_items),
                           )


def get_rlcs_and_bom_from_csvfile_impl(
        csv_file: Path,
        property_to_purpose_mapping: List[Tuple[str,str]]
):
    data = _read_components_csv_file(csv_file)
    if not data:
        raise RuntimeError(
            f"No data could be extracted from {csv_file}, please verify that the file content is correct."
        )

    comp_props = map_comp_props(data, property_to_purpose_mapping)

    return get_rlcs_and_bom_from_comp_props(comp_props)
