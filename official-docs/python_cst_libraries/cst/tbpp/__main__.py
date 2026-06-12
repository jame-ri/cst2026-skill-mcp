# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

from cst.interface import get_current_project, get_calling_app_name
import argparse
import pathlib
import types

from ._impl.debugging import wait_for_debugger_if_requested
from ._impl.module import load_module, analyze_module, TBPPFunctions, fill_all_params_from_dict, TemplateLayoutError, check_returned_tuple, check_settings
from .data_types import DefineParameters, EvaluateParameters
import warnings


def run_template():
    warnings.simplefilter("default", DeprecationWarning)

    if wait_for_debugger_if_requested():
        breakpoint()

    parser = argparse.ArgumentParser(description="Command module used internally by CST Studio Suite to perform template based post-processing")
    parser.add_argument("rtpy_module_path", type=pathlib.Path)
    args, _ = parser.parse_known_args()

    tbpp_module: types.ModuleType = load_module(args.rtpy_module_path, "tbpp_user_mod")
    tbpp_functions: TBPPFunctions = analyze_module(tbpp_module)

    prj = get_current_project()
    app = getattr(prj, get_calling_app_name())

    # noinspection PyProtectedMember
    argdict = app._get_tbpp_startup_info()

    if argdict["create"]:
        script_settings: dict = {}
    else:
        script_settings: dict = argdict["script_settings"]
    output_dict = {}
    param_dict = {"settings": script_settings, "prj": prj, "calling_app": app}

    if argdict["op"] == "define":
        def_pars = DefineParameters(name=argdict["name"], create=argdict["create"], name_changed=argdict["name_changed"])
        param_dict["def_params"] = def_pars
        define = fill_all_params_from_dict(tbpp_functions.define, param_dict)
        ret_define = define()
        output_dict["define_succeeded"]: bool = ret_define is not None
        output_dict["template_name"]: str = def_pars.name
        if ret_define:
            output_dict["result_type"]: str = ret_define.result_type
            output_dict["eval_type"]: str = ret_define.eval_type
    elif argdict["op"] == "evaluate_multiple":
        if not tbpp_functions.evaluate_multiple:
            raise TemplateLayoutError("The template result type is configured as 'multiple', but no suitable generator function was found")
        param_dict["eval_params"] = EvaluateParameters(name=argdict["name"], result_id=argdict["result_id"])
        evaluate_multiple = fill_all_params_from_dict(tbpp_functions.evaluate_multiple, param_dict)
        ret_gen = evaluate_multiple()
        num_results = 0
        try:
            while True:
                tup = next(ret_gen)
                check_returned_tuple(tup)
                num_results = num_results + 1
                app.ProcessResult(tup[1], tup[0], argdict["args"])
                if app.GetTemplateAborted():
                    app.ReportWarningToWindow("Template evaluation was aborted by user.")
                    break
        except StopIteration as e:
            if e.value:
                warnings.warn("The multiple template did return a non-trivial value, which is ignored. "
                              "Did you accidentally use 'return' instead of 'yield' to produce multiple results? "
                              f"Returned value: {e.value}", UserWarning)
        if num_results == 0:
            warnings.warn("The multiple template did not return any result.", UserWarning)
    elif argdict["op"] == "evaluate":
        if not tbpp_functions.evaluate:
            raise TemplateLayoutError(
                "The template result type is configured as 'single', but no evaluate function was found")
        param_dict["eval_params"] = EvaluateParameters(name=argdict["name"], result_id=argdict["result_id"])
        evaluate = fill_all_params_from_dict(tbpp_functions.evaluate, param_dict)
        ret_eval = evaluate()
        app.ProcessResult(ret_eval, argdict["name"], argdict["args"])

    check_settings(script_settings)
    output_dict["script_settings"] = script_settings

    # Note that this should be the last call in this module, since the calling process will stop listening for requests
    # when the result info was set
    # noinspection PyProtectedMember
    app._set_tbpp_result_info(output_dict)


if __name__ == "__main__":
    run_template()
    import gc
    gc.collect()
