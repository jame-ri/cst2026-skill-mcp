# Copyright 1998-2023 Dassault Systemes Deutschland GmbH.

from typing import Union, List

class Parameter:
    """\
    Class that representing a parameter from CST Studio Suite. Requires explicit conversion to the desired type.
    e.g. val = float(params.my_parameter)
    """
    def __init__(self, name, expr, value, descr=None, **kwargs):
        self.name = name        
        self._expr = expr
        self._value = value
        self._descr = descr

        self._is_used = False

    def __bool__(self):
        self._is_used = True
        return bool(float(self._value))

    def __int__(self):
        self._is_used = True
        return int(self._value)

    def __float__(self):
        self._is_used = True
        return float(self._value)

    def __str__(self):
        self._is_used = True
        return str(self._value)

    def __repr__(self):
        star = '*' if self._is_used else ''
        return f"<Parameter{star} name={self.name} value={self._value}>"

class Parameters:
    """\
    Container class that holds the parameters stemming from CST Studio Suite. The parameters are automatically added as attributes.
    As result the following two statements are equivalent:

        - params.get('my_parameter')
        - params.my_parameter
    """
    def __init__(self, par_file=None):
        self._new_parameters = set()
        self._existing_parameters = set()

        if not par_file:
            return

        import json
        with open(par_file) as fpar:
            pars = json.load(fpar)

        parameters_data = pars.get("parameters", [])

        if isinstance(parameters_data, list):
            for parameter_data in parameters_data:
                name = parameter_data.get("name")
                assert name        
                setattr(self, name, Parameter(**parameter_data))
                self._existing_parameters.add(name)

        units = pars.get("units")
        class Units:
            pass

        self.units = Units()        
        for name, info in units.items():
            from cst.units import Unit
            encoded = info.get("encoded")
            if encoded is None:
                raise RuntimeError("Could not read unit information")
            u = Unit.decode(encoded)
            setattr(self.units, name, u)

    def __repr__(self):
        all_pars = [getattr(self, n) for n in self._existing_parameters]
        all_pars += [getattr(self, n) for n in self._new_parameters]
        all_pars.sort(key=lambda p: p.name)
        return f'<Parameters {all_pars}>'

    def get(self, name: str, initial_value: Union[int, float]=None, descr: str=None) -> 'Parameter':
        """
        Gets a parameter by name. 

        Args:
            name (str): The name of the parameter
            initial_value (Union[int, float], optional): If the parameter does not exist yet, this value must be given or it will raise an exception. Defaults to None.
            descr (str, optional): Allow to add a description to parameter. Defaults to None.

        Returns:
            Parameter: Instance of the requested parameter 
        """
        if not hasattr(self, name):
            if initial_value is None:
                raise UserWarning("Creating a parameter requires an initial value.")
            self._new_parameters.add(name)
            setattr(self, name, Parameter(name=name, expr=str(initial_value), value=str(initial_value), descr=descr))
        return getattr(self, name)

    def get_used_parameters(self) -> List['Parameter']:
        used_pars = []
        for par in self.__dict__.values():
            if not isinstance(par, Parameter):
                continue
            if par._is_used:
                used_pars.append(par)
        return used_pars

    def get_new_parameters(self) -> List['Parameter']:
        new_pars = []
        for par in self.__dict__.values():
            if not isinstance(par, Parameter):
                continue
            if par.name in self._new_parameters:
                new_pars.append(par)
        return new_pars


def store_dependent_parameters(parameters: Parameters, pars_dep_file: str):
    import os
    os.makedirs(os.path.dirname(pars_dep_file), exist_ok=True)

    used_par_names = [p.name for p in parameters.get_used_parameters()]
    new_parameters = [
        {"name": p.name
        , "expr": p._expr
        , "value": p._value
        , "descr": p._descr if p._descr else ''
        } 
        for p in parameters.get_new_parameters()]

    import json
    data = {"used_parameters": used_par_names}
    data["new_parameters"] = new_parameters

    with open(pars_dep_file, 'w') as fp:
        json.dump(data, fp, indent=4)
