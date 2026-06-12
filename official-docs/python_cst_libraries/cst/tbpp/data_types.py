# Copyright 1998-2023 Dassault Systemes Deutschland GmbH.

from dataclasses import dataclass
from enum import Enum

class ResultTypeEnum(Enum):
    ZERO_D = "0D"
    ONE_D = "1D"
    ONE_D_COMPLEX = "1DC"
    MULT_ZERO_D = "M0D"
    MULT_ONE_D = "M1D"
    MULT_ONE_D_COMPLEX = "M1DC"


class EvalTypeEnum(Enum):
    ALL_RUNS = "all_runs"
    SINGLE_RUN = "single_run"

@dataclass
class DefineParameters:
    name: str
    create: bool
    name_changed: bool


@dataclass
class EvaluateParameters:
    result_id: str
    name: str


@dataclass
class TemplateSettings:
    result_type: ResultTypeEnum
    eval_type: EvalTypeEnum