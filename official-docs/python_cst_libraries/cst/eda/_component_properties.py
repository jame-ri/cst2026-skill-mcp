# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.


from dataclasses import dataclass
from types import SimpleNamespace

#
# NOTE: the field naming herein must match the fields coming from cstapps/import_customization
#
@dataclass
class ComponentProperties:
    """
    Supported component properties.
    """
    REFDES: str = ""
    PARTNAME: str = ""
    TYPE: str = ""
    NOMINAL: str = ""
    R: str = ""
    L: str = ""
    C: str = ""
    Rp: str = ""
    Lp: str = ""
    Cp: str = ""

    def to_BOMItem(self):
        if self.REFDES and self.PARTNAME:
            return SimpleNamespace(refdes=self.REFDES, partname=self.PARTNAME)
        else:
            raise RuntimeError("No component-to-part-mapping possible")


    def to_RLCItem(self, string_to_value_translations):

        import pyparsing
        from ._rlcs import _parse_RLC_value, RLCItem, PartType

        partname = self.PARTNAME
        if not partname:
            raise RuntimeError("No part name specified")

        # determine type:
        R, L, C = self.R, self.L, self.C

        type = PartType.from_string(self.TYPE)
        if type is None:
            # try to infer from R,L,C data
            if R and not L and not C:
                type = PartType.R_HF
            elif L and not C and not R:
                type = PartType.L_HF
            elif C and not R and not L:
                type = PartType.C_HF
            else:
                raise RuntimeError("Part type could not be determined")

        # determine values:
        values = {}

        def parse_value(sval, what):
            try:
                val, fully_parsed = _parse_RLC_value(sval, what)
            except pyparsing.exceptions.ParseException as perr:
                raise RuntimeError(f"Unable to get numerical value of '{sval}': {perr}")

            if fully_parsed:
                values[what] = val
                string_to_value_translations[sval] = val
            else:
                raise RuntimeError(f"Numerical value ({val}) was not fully parsed from '{sval}'")

        # first we try to read from NOMINAL if that was specified
        if s:=self.NOMINAL:
            parse_value(s, type.value)

        # now we try to read the RLC fields plus parasitics.
        for what in 'RLC':
            sval = getattr(self, what)
            sval_p = getattr(self, what+'p')
            if sval and sval_p and sval!=sval_p:
                raise RuntimeError(f"Both, nominal ({what}) and parasitic ({what}p) values given")
            if s:=(sval or sval_p):
                parse_value(s, what)

        if type.value not in values:
            raise RuntimeError(f"Nominal value {type.value} was not obtained")

        return RLCItem(
            type=type,
            partname=partname,
            **values
        )
