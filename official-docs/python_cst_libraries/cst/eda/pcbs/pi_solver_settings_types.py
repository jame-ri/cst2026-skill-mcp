# Copyright 1998-2023 Dassault Systemes Deutschland GmbH.

from typing import Any, List

def convert_to_json_like_object(value: Any):
    def isiterable(x):
        try:
            iter(x)
            return True
        except TypeError:
            return False

    if value is None:
        return value

    if type(value) in (bool, int, float, str):
        return value

    if hasattr(value, 'to_json'):
        return value.to_json()

    if isinstance(value, list):
        res = []
        for item in value:
            res.append(convert_to_json_like_object(item))
        return res

    if isinstance(value, dict):
        res = {}
        for key, val in value.items():
            res[key] = convert_to_json_like_object(val)
        return res

    if hasattr(value, '__dict__'):
        res = {}
        for key, value in value.__dict__.items():
            res[key] = convert_to_json_like_object(value)
        return res

    if isiterable(value):
        res = []
        for item in value:
            res.append(convert_to_json_like_object(item))
        return res

    raise ValueError(f"Cannot convert {value} of type {type(value)} to json-like structure")


class Length():
    def __init__(self, value: float, units: str):
        self.value = value
        self.units = units

    def __repr__(self):
        return f"<Length {self.value}{self.units}>"

    def __str__(self):
        return f"{self.value}{self.units}"


class Choice(list):
    def __init__(self, choice: str, choices: list):
        self._choice = choice
        self._choices = choices

    def __eq__(self, other):
        if isinstance(other, str):
            return self._choice == other
        raise ValueError(f"Cannot compare to type {type(other)}")

    def assign_from(self, value):
        if not isinstance(value, str):
            raise ValueError("Can only assign from string.")
        self.choice = value

    def to_json(self):
        return self._choice

    def from_json(self, value):
        if isinstance(value, list):
            if len(value) == 1:
                self.choice = value[0]
                return
        raise ValueError(f"Unable to assign Choice from {value}")

    @property
    def choice(self) -> str:
        return self._choice

    @choice.setter
    def choice(self, choice: str):
        if choice not in self._choices:
            raise ValueError(f"{choice} is not a valid choice. It must be one of {self._choices}")
        self._choice = choice

    @property
    def choices(self) -> List[str]:
        return self._choices.copy()


class PIPort():
    def __init__(self, comp: str, pin1: str, pin2: str=None):
        self.comp = comp
        self.pin1  = pin1 
        self.pin2  = pin2 

    def __repr__(self):
        return f"<PIPort {self.comp}({self.pin1}-|>-{self.pin2})>"


class PIPortList(list):
    def append(self, __object: PIPort) -> None:
        if isinstance(__object, PIPort):
            return super().append(__object)
        if isinstance(__object, tuple) or isinstance(__object, list):
            try:
                return super().append(PIPort(*__object))
            except TypeError:
                raise ValueError(f"Could not convert to PIPort")
        raise ValueError(f"Expecting PIPort-type or constructing tuple/list for PIPort")

    def from_json(self, value):
        if not isinstance(value, list):
            raise ValueError(f"Expecting a list")
        self.clear()
        for val in value:
            if isinstance(val, dict):
                if 'name' in val:
                    val.pop('name')
                self.append(PIPort(**val))
            else:
                self.append(val)


class SIDouble():
    _mags = 'fpnum1kMGTP'

    def __init__(self, value: float, ext:str='1'):
        self.value  = value
        if ext not in self._mags:
            raise ValueError(f"The magnitude extension must be one of '{self._mags}'")
        self.ext = ext

    def assign_from(self, value: Any):
        if isinstance(value, float):
            self.value = value
            self.ext = ''
            
        elif isinstance(value, str):
            import re
            parts = re.split('([fpnumkMGTP])', value)
            parts = [p for p in parts if p]

            if not parts:
                raise ValueError(f"Failed to convert {value} to {self.__class__.__name__}.")
            
            self.value = float(parts[0])
            self.ext = ''
            if len(parts) > 1:
                self.ext = parts[1]


    def __float__(self):
        assert self.ext in self._mags
        iext = self._mags.find(self.ext)
        return self.value * 10.0 ** (-15 + 3 * iext)

    def __repr__(self):
        return f"<SIDouble {self.value}{self.ext}>"