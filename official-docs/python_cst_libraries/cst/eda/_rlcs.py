# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

from dataclasses import dataclass
from enum import Enum


class PartType(Enum):
    R_HF = "R"  # don't change!
    L_HF = "L"
    C_HF = "C"

    @classmethod
    def from_string(cls, s):
        if not s:
            return None
        s = s.lower().strip()
        if s in ("r", "res", "resistor"):
            return cls.R_HF
        if s in ("l", "ind", "inductor"):
            return cls.L_HF
        if s in ("c", "cap", "capacitor"):
            return cls.C_HF
        return None



def _parse_RLC_value(s: str, typ: str):
    from .part_library import _magtrans
    from pyparsing import pyparsing_common
    from pyparsing import CaselessLiteral as CLiteral
    from pyparsing import Empty, Optional, Word, rest_of_line

    allowed_units = Empty()
    if typ=='R':
        allowed_units = CLiteral("Ohms") | CLiteral("Ohm") | CLiteral("R")
    elif typ=='L':
        allowed_units = CLiteral("Henries") | CLiteral("Henry") | CLiteral("H")
    elif typ=='C':
        allowed_units = CLiteral("Farads") | CLiteral("Farad") | CLiteral("F")
    else:
        raise UserWarning(f"Non existing type given: {typ=}")

    num = pyparsing_common.number().set_results_name("value")
    magn = Optional(
        Word("".join(_magtrans.keys()), exact=1).set_parse_action(
            lambda t: _magtrans.get(t[0])
        )
    ).set_results_name("magn")
    unit = Optional(allowed_units).set_results_name("unit")

    parser = num + magn + unit + rest_of_line.set_results_name("remainder")
    pres = parser.parse_string(s)

    value = pres["value"] * pres.get("magn", 1)
    fully_parsed = len(pres.get("remainder", "")) == 0

    return value, fully_parsed


@dataclass
class RLCItem:
    partname: str
    type: PartType
    R: float = 0
    L: float = 0
    C: float = 0

    def check(self):
        if not self.partname:
            raise UserWarning("Part has no partname")
        if self.type not in PartType:
            raise UserWarning(f"Part {self.type} not in expected types")
        if self.type == PartType.C_HF and self.C == 0:
            raise UserWarning(
                f"Capacity is zero for part {self.partname} which is unphysical and not allowed"
            )
        if self.R < 0 or self.L < 0 or self.C < 0:
            raise UserWarning(
                f"One or more values are negative in {self} which is not allowed"
            )

    def add_to_plb(self, plb):
        self.check()
        existing_part = plb._part(self.partname)
        if existing_part:
            raise UserWarning(
                f"Part not added, because a part with name '{self.partname}' already exists"
            )
        plb.add_RLC(self.partname, self.type.value, self.R, self.L, self.C)
