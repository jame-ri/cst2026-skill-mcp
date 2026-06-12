# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

from __future__ import annotations

import pathlib
import functools
from types import ModuleType, NoneType
from dataclasses import dataclass
from typing import Callable, Any, Generator, Type, get_type_hints

from ..data_types import TemplateSettings, DefineParameters, EvaluateParameters
import os
import warnings
import inspect


class TemplateLayoutError(Exception):
    pass


class TypeHintWarning(UserWarning):
    pass


class UnsupportedSettingsContent(Exception):
    pass


@dataclass
class TBPPFunctions:
    define: Callable[..., TemplateSettings | None]
    evaluate: Callable[..., ...] | None
    evaluate_multiple: Callable[..., ...] | None


def load_module(file_name: pathlib.Path, module_name: str) -> ModuleType:
    import importlib.machinery
    import importlib.util
    import sys

    importlib.machinery.SOURCE_SUFFIXES.append('.rtpy')
    spec = importlib.util.spec_from_file_location(module_name, file_name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    spec.loader.exec_module(module)
    return module


def _analyze_module_old_style(module: ModuleType) -> TBPPFunctions:
    # check for old layout first
    if not hasattr(module, 'define'):
        raise TemplateLayoutError("No 'define' function defined")
    if not inspect.isfunction(module.define):
        raise TemplateLayoutError(
            f"'define' module attribute is of wrong type. Found {type(module.define)} expected function")
    if not (nparams := len(inspect.signature(module.define).parameters)) == 2:
        raise TemplateLayoutError(
            f"If the template does not comply with the new style, 'define' needs to have exactly 2 parameters, {nparams} found.")
    define: Callable[[DefineParameters, dict], TemplateSettings] = lambda def_params, settings: module.define(
        def_params, settings)
    ret = TBPPFunctions(define=define, evaluate=None, evaluate_multiple=None)
    if not hasattr(module, 'evaluate') and not hasattr(module.evaluate, 'evaluate_multiple'):
        raise TemplateLayoutError("No 'evaluate' or 'evaluate_multiple' function defined")
    if hasattr(module, 'evaluate'):
        if not inspect.isfunction(module.evaluate):
            raise TemplateLayoutError(
                f"'evaluate' module attribute is of wrong type. Found {type(module.evaluate)} expected function")
        if not (nparams := len(inspect.signature(module.evaluate).parameters)) == 2:
            raise TemplateLayoutError(
                f"If the template does not comply with the new style, 'evaluate' needs to have exactly 2 parameters, {nparams} found.")
        ret.evaluate = lambda eval_params, settings: module.evaluate(eval_params, settings)
    if hasattr(module, 'evaluate_multiple'):
        if not inspect.isgeneratorfunction(module.evaluate_multiple):
            raise TemplateLayoutError(
                f"'evaluate_multiple module attribute is of wrong type. Found {type(module.evaluate_multiple)} expected generator function")
        ret.evaluate_multiple = lambda eval_params, settings: module.evaluate_multiple(eval_params, settings)
    return ret


def _check_function(module: ModuleType, name: str, additional_params: dict[str, Type]) -> Callable:
    if not hasattr(module, name):
        raise TemplateLayoutError(f"No '{name}' function defined")
    func = getattr(module, name)
    if not inspect.isfunction(func):
        raise TemplateLayoutError(
            f"'{name}' module attribute is of wrong type. Found {type(module.define)}, expected function")
    allowed_params: dict[str, Type] = {"calling_app": None, "prj": None, "settings": dict[str, ...]} | additional_params
    non_recognized_params = set(inspect.signature(func).parameters) - allowed_params.keys()
    if non_recognized_params:
        raise TemplateLayoutError(f"'{name}' function has non-recognized parameters: {non_recognized_params}.")

    for pname, param in inspect.signature(func).parameters.items():
        if (expected_type := allowed_params.get(
                pname)) and param.annotation is not inspect.Parameter.empty and param.annotation != expected_type:
            warnings.warn(
                f"The type hint for parameter '{pname}' of function '{name}' is unexpected. Found: {param.annotation}, expected: {expected_type}.",
                TypeHintWarning)

        if param.default is not inspect.Parameter.empty:
            raise TemplateLayoutError(
                f"The default value {param.default} was provided to parameter {pname} of function {name}. This is not supported, please remove the default.")

    return func


def _decorator_single_result(func: Callable[..., Generator]) -> Callable:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        gen = func(*args, **kwargs)
        try:
            val = next(gen)
            warnings.warn(
                "The evaluate function should return in case of a single result (non-multiple). A yield was detected instead.",
                UserWarning)
        except StopIteration as e:
            val = e.value
        return val

    return wrapper


def _analyze_module_new_style(module: ModuleType) -> TBPPFunctions:
    define = _check_function(module, 'define', {"def_params": DefineParameters})
    evaluate = _check_function(module, 'evaluate', {"eval_params": EvaluateParameters})

    if inspect.isgeneratorfunction(evaluate):
        evaluate_multiple = evaluate
        evaluate = _decorator_single_result(evaluate)
    else:
        evaluate_multiple = None

    ret = TBPPFunctions(define=define, evaluate=evaluate, evaluate_multiple=evaluate_multiple)

    if hasattr(module, 'evaluate_multiple'):
        raise TemplateLayoutError(
            "An 'evaluate_multiple' function was found in the module. This is no longer required in the new layout and should be renamed/removed.")

    define_hints = get_type_hints(define)
    allowed_define_ret_hints = [TemplateSettings, TemplateSettings | None]
    if "return" in define_hints and (define_ret_hint := define_hints.get("return")) not in allowed_define_ret_hints:
        warnings.warn(
            f"The 'define' function provides an unexpected type hint. Expected {TemplateSettings}, found {define_ret_hint}.",
            TypeHintWarning)
    return ret


def analyze_module(module: ModuleType) -> TBPPFunctions:
    """Checks the template layout and returns the resulting module functions to be used for the evaluation"""
    if os.getenv("CST_PYTHON_TBPP_NEW_STYLE") != "0":
        try:
            return _analyze_module_new_style(module)
        except TemplateLayoutError as e:
            new_style_exception = e

        try:
            ret_old_style = _analyze_module_old_style(module)
            warnings.warn(
                f"The python template is not compliant with the required template layout: {new_style_exception}\n"
                "{SEE_PYTHON_TBPP_LAYOUT_OH}\n"
                "Attempting to interpret the template in the previous technical demonstrator layout which is deprecated.", DeprecationWarning)
            return ret_old_style
        except TemplateLayoutError:
            raise TemplateLayoutError(
                f"The python template is not compliant with the required template layout: {new_style_exception}\n"
                "{SEE_PYTHON_TBPP_LAYOUT_OH}")

    return _analyze_module_old_style(module)


def fill_all_params_from_dict(func: Callable[..., ...], param_dict: dict) -> Callable[[], ...]:
    return functools.partial(func, **{k: param_dict[k] for k in inspect.signature(func).parameters})


def check_returned_tuple(tup: tuple):
    if not isinstance(tup, tuple):
        raise TemplateLayoutError(
            f"The result of a multiple-template evaluation is not a tuple. Returned result: {tup}")
    if not len(tup) == 2:
        raise TemplateLayoutError(
            f"The result of a multiple-template evaluation has the wrong tuple size (expected 2, got {len(tup)}). Returned result: {tup}")
    if not type(tup[0]) is str:
        raise TemplateLayoutError(
            f"The first tuple entry of the multiple-template evaluation result has the wrong type (expected {str}, got {type(tup[0])}. Result was: {tup}")


def check_settings(settings: dict[str, ...]) -> None:
    if not isinstance(settings, dict):
        raise UnsupportedSettingsContent(
            f"The type of settings is not a dictionary. This is not supported. type(settings) = {type(settings)}")

    def check_for_allowed_types(obj: Any) -> None:
        allowed_types = dict[str, ...], list, str, int, float, bool, NoneType
        if isinstance(obj, dict):
            for k, v in obj.items():
                if not isinstance(k, str):
                    raise UnsupportedSettingsContent(
                        f"The dict which is part of settings contains unsupported keys. Expected {str} but got {type(k)}.")
                check_for_allowed_types(v)
        elif isinstance(obj, list):
            list(map(check_for_allowed_types, obj))
        else:
            if type(obj) not in allowed_types:
                raise UnsupportedSettingsContent(
                    f"The type of a setting in settings is not a {allowed_types}, instead it was {type(obj)} which is not supported.")

    check_for_allowed_types(settings)
