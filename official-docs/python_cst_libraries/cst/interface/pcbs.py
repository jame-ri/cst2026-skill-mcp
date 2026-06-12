# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory, mkdtemp

from typing import Optional, List, Dict

import cst.eda.pcb_api as pcb_api
import cst.eda.part_library as part_lib
from cst.eda.pcbs.pi_solver_settings import PISolverSettings
from enum import Enum


class ItemType(Enum):
    """
    Class provides valid values for 'type' attribute of :py:class:`.SelectedItem`
    """

    MATERIAL = "material"
    """for materials"""
    LAYER = "layer"
    """for layers"""
    PAD_STACK = "pad_stack"
    """for padstacks"""
    FOOTPRINT = "footprint"
    """for footprints"""
    STIMULUS = "stimulus"
    """for stimuli"""
    EYE_MASK = "eye_mask"
    """for eye masks"""
    PART = "part"
    """for parts"""
    VCOMP = "vcomp"
    """for virtual components"""
    ANNO = "anno"
    """for annotations"""
    COMP = "comp"
    """for components"""
    PIN = "pin"
    """for component pins"""
    NET = "net"
    """for nets"""
    NETCLASS = "netclass"
    """for net classes"""
    SIGNAL_SPEC = "signal_spec"
    """for signal specifications"""
    TERMINAL = "terminal"
    """for terminals"""
    TRACE = "trace"
    """for traces"""
    AREA = "area"
    """for areas"""
    VIA = "via"
    """for vias"""
    DIECOMP = "diecomp"
    """for die components"""
    VDIECOMP = "vdiecomp"
    """for virtual die components"""
    UNDEFINED = "undefined"

    @classmethod
    def value_of(cls, value):
        for k, v in cls.__members__.items():
            if v.value == value:
                return v
        else:
            raise ValueError(f"'{cls.__name__}' enum not found for '{value}'")


@dataclass
class SelectedItem:
    """
    Class represents a selected item in PCBS project. Objects of this class are used as arguments
    in InterfacePCBS.get_selected_items(self) and
    in InterfacePCBS.set_selected_items(self, selected: List[SelectedItem]) methods

    An object of this class has two attributes:

    - 'id' - keeps ID of the selected object
    - 'type' - keeps type of the selected object
    - 'comp_id' - only needed for pins to capture the pin's component name

    For valid values for 'type' attribute see :py:class:`.ItemType`
    """

    id: str = ''
    type: ItemType = ItemType.UNDEFINED
    comp_id: str = ''

    def to_json(self):
        res = {}
        res["id"] = self.id
        res["type"] = self.type.value
        if self.comp_id:
            res['comp_id'] = self.comp_id
        return res

    def from_json(self, data: dict):
        self.id = data["id"]
        self.type = ItemType.value_of(data["type"])
        self.comp_id = data.get('comp_id', '')

    def __str__(self):
        return self.id + " " + self.type.value


class InterfacePCBS:
    """This class offers functionality to interoperate with CST PCB Studio (PCBS)"""

    def __init__(self, pcbs_api):
        self._pcbs_api = pcbs_api
        self.parent_project = pcbs_api.parent_project

    def _project_temp_dir(self):
        return Path(self.parent_project.folder(), "Temp")

    def new_command(self, *args):
        return self._pcbs_api.new_command(*args)

    def send_command(self, *args):
        return self._pcbs_api.send_command(*args)

    def set_pcb(self, pcb: pcb_api.PCB):
        """Loads the given PCB design into the currently active PCBS project."""
        tmp_dir = TemporaryDirectory(dir=self._project_temp_dir())
        tmp_dar = os.path.join(tmp_dir.name, "design.dar")
        pcb._convert_to_dar(tmp_dar)
        self._pcbs_api.send_command("_load_dar", {"file": tmp_dar})

    def get_pcb(self) -> pcb_api.PCB:
        """Returns a copy of the currently loaded PCB design in the PCBS project."""
        tmp_dir = TemporaryDirectory(dir=self._project_temp_dir())
        tmp_dar = os.path.join(tmp_dir.name, "design.dar")
        self._pcbs_api.send_command("_save_dar", {"file": tmp_dar})
        return pcb_api.PCB(tmp_dar)

    def set_part_library(self, part_lib: part_lib.PartLibrary):
        """Loads the given PartLibrary into the currently active PCBS project."""

        tmp_dir = TemporaryDirectory(dir=self._project_temp_dir())
        tmp_plb = os.path.join(tmp_dir.name, "design.plb_lib")
        part_lib.save(tmp_plb)
        self._pcbs_api.send_command("_load_parts", {"folder": tmp_dir.name})

    def get_part_library(self, workdir: os.PathLike=None) -> part_lib.PartLibrary:
        """Get a copy of the currently loaded PartLibrary in the active PCBS project.
        Files referenced in the part library will be copied into the specified `workdir`,
        or if the latter is unspecified, put into an auto-created directory.
        """
        if workdir:
            workdir = Path(workdir)
            workdir.mkdir(exist_ok=True, parents=True)
        else:
            tmpdir = mkdtemp(dir=self._project_temp_dir())  # not auto-deleted
            workdir = Path(tmpdir)

        self._pcbs_api.send_command("_save_parts", {"folder": str(workdir)})
        tmp_plb = workdir / "design.plb_lib"
        res = part_lib.PartLibrary(str(tmp_plb))
        return res

    def export_part_library(self, ppt_lib_file: os.PathLike):
        """
        Exports part library to the specified file
        ppt_lib_file - os.PathLike object as a path to the file
        """
        ppt_lib_file = str(ppt_lib_file)
        self._pcbs_api.send_command("export_part_library", ppt_lib_file)

    def import_part_library(
        self,
        file: os.PathLike,
        file_type: str = 'cst',
        action: str = 'add'
    ):
        """Imports parts

        :param file: String specifying the file to be imported
        :param file_type: Specifies the type of the file to be imported. Possible types see below
        :param action: Specifies the action to be performed on the imported parts. Possible types see below

        Possible file_types:

        - 'csv' - two-pin RLC from CSV-file (\\*.csv);
        - 'cst' - CST component part library file (\\*.ppt_lib);

        Possible actions:

        - 'add' - adds imported parts to the project;
        - 'assign' - assigns values to the available parts;

        """

        file = str(file)
        params = locals()
        params.pop("self")
        self._pcbs_api.send_command("import_part_library", params)

    def delete_all_parts(self):
        """Deletes all parts in the currently active PCBS project."""
        self._pcbs_api.send_command("_delete_all_parts")

    def delete_parts(self, partIDs: list):
        """Deletes parts by IDs in the currently active PCBS project."""
        self._pcbs_api.send_command("_delete_parts", {"ids": partIDs})

    def get_bom(self):
        """Returns a dict with the current Component-to-Partname mapping as a dict {<REFDES>: <PARTNAME|None>, ...}. A partname equal to None indicates that no part is currently assigned."""
        return self._pcbs_api.send_command("get_bom")

    def set_bom(self, bom: dict):
        """Modifies the Component-to-Partname mapping by means of a dict {<REFDES>: <PARTNAME|None>, ...}. A partname equal to None will remove any assigned part."""
        self._pcbs_api.send_command("set_bom", bom)

    def run_solver(self, solvername: str):
        """Starts the solver with the given name"""
        if solvername.lower() == "3dfefd":
            solvername = "fe"  # different naming inside PCBS!
        self._pcbs_api.send_command("run_solver", solvername)

    def get_pi_solver_settings(self):
        """Returns the PI-Solver Settings"""
        res = PISolverSettings()
        res.from_json(self._pcbs_api.send_command("get_pi_solver_settings", None))
        return res

    def set_pi_solver_settings(self, PIsolversettings: PISolverSettings):
        """Sets the PISolverSettings"""
        data = PIsolversettings.to_json()
        self._pcbs_api.send_command("set_pi_solver_settings", data)

    def import_layout(
        self,
        file: os.PathLike,
        cad_type: str,
        layout: bool = True,
        stackup: bool = True,
        comp_to_part_mapping: bool = True,
        comp_models: bool = True,
    ):
        """Imports a layout

        :param file: String specifying the file to be imported
        :param cad_type: Specifies the CAD type of the layout to be imported. Possible types see below
        :param layout: Optional parameter specifies whether the layout should be reimported, defaults to True
        :param stackup: Optional parameter specifies whether the stackup should be reimported, defaults to True
        :param comp_to_part_mapping: Optional parameter specifies whether the component-to-part mapping should be reimported, defaults to True
        :param comp_models: Optional parameter specifies whether the component models should be reimported, defaults to True

        Possible cad_types:

        - 'cadence_allegro' - Cadence (Allegro/APD/SiP);
        - 'mentor_graphics_hyperlynx' - Mentor Graphics HyperLynx;
        - 'odb++' - ODB++;
        - 'ipc_2581' - IPC-2581;
        - 'zuken_cr5000' - Zuken CR-5000/8000 ASCII;
        - 'simlab_pcbmod' - SimLab PCBMod;
        - 'cst_ldb' - CST Layout Database
        """

        file = str(file)
        params = locals()
        params.pop("self")
        self._pcbs_api.send_command("import_layout", params)

    def apply_ldf(self, ldf_file: os.PathLike):
        """
        Applies ldf-file to the project. Accepts a os.PathLike object as a path to the ldf-file
        ldf_file - String as a path to the ldf-file
        """
        self._pcbs_api.send_command("apply_ldf", str(ldf_file))

    def check_layer_stackup(self):
        """
        Checks the layer stackup.
        Returns an array of strings describing the problems. In case of no problems - the array is of zero length
        """
        return self._pcbs_api.send_command("check_layer_stackup")

    def fix_layer_stackup(self):
        """
        Command to auto-fix the layer stackup.
        Returns an array of strings describing the problems if auto-fix is impossible. In case of success the array is of zero length
        """
        return self._pcbs_api.send_command("fix_layer_stackup")

    def get_auto_tagging(self):
        """
        Returns a dict with the current auto-tagging settings
        """
        return self._pcbs_api.send_command("get_auto_tagging")

    def set_auto_tagging(self, auto_tagging_settings: dict):
        """
        Applies auto-tagging settings to the project.
        auto_tagging_settings - Auto-tagging settings as dict
        """
        self._pcbs_api.send_command("set_auto_tagging", auto_tagging_settings)

    def export_auto_tagging(self, settings_file: os.PathLike):
        """
        Writes auto-tagging settings to the specified file.
        settings_file - os.PathLike object as a path to the auto-tagging settings file
        """
        self._pcbs_api.send_command("export_auto_tagging", str(settings_file))

    def apply_auto_tagging(self, settings_file: os.PathLike):
        """
        Applies the specified auto-tagging settings file to the project.
        settings_file - os.PathLike object as a path to the auto-tagging settings file
        """
        self._pcbs_api.send_command("set_auto_tagging", str(settings_file))

    def run_auto_tagging(self, update_diff_pins=False):
        """
        Starts auto-tagging.
        update_diff_pins - Optional boolean parameter "Update differential pins". Default value is False
        """
        self._pcbs_api.send_command("run_auto_tagging", update_diff_pins)

    def export_bck_rules(self, setting_file: os.PathLike, rules=True, nets=True, comps=True):
        """
        Writes rule & net/component tagging settings to the specified file.
        settings_file - os.PathLike object as a path to the rule settings file
        rules - Optional boolean parameter specifying whether rule settings must be included into the file or not. default value is True
        nets - Optional boolean parameter specifying whether nets tagging settings must be included into the file or not. default value is True
        comps - Optional boolean parameter specifying whether components tagging settings must be included into the file or not. default value is True
        """
        setting_file = str(setting_file)
        params = locals()
        params.pop("self")
        self._pcbs_api.send_command("export_bck_rules", params)

    def apply_bck_rules(self, setting_file: os.PathLike):
        """
        Applies rule & tagging settings to the project.
        settings_file - os.PathLike object as a path to the rule settings file
        """
        self._pcbs_api.send_command("apply_bck_rules", str(setting_file))

    def get_bck_rule_settings(self):
        """
        Returns the current rule settings as dict, where key is a rule name and value is a rule dict object.
        Each rule dict contains name, id, included flag, tags dict and a dict of parameters,
        where key is a parameter name and value is a parameter dict.
        Each parameter dict contains name, type and value.

        Possible parameter types:

        - 'boolean' - the value of Boolean type (True|False);
        - 'integer' - the value of Long type;
        - 'float' - the value of Double type;
        - 'float_length' - the value of Double type representing length;
        - 'float_area' - the value of Double type representing area;
        - 'single_select_list' - the value of String type representing single selection;
        - 'multi_select_list' - the value is array of strings representing multi-selection;
        """
        return self._pcbs_api.send_command("get_bck_rule_settings")

    def set_bck_rule_settings(self, bck_rule_settings: dict):
        """
        Applies rule settings to the project.
        bck_rule_settings - Rule settings as dict, where key is a rule name and value is a rule dict object.
        Each rule dict contains name, included flag and a dict of parameters,
        where key is a parameter name and value is a parameter dict.
        Each parameter dict contains name, type and value.

        Possible parameter types:

        - 'boolean' - the value of Boolean type (True|False);
        - 'integer' - the value of Long type;
        - 'float' - the value of Double type;
        - 'float_length' - the value of Double type representing length;
        - 'float_area' - the value of Double type representing area;
        - 'single_select_list' - the value of String type representing single selection;
        - 'multi_select_list' - the value is an Array of Strings representing multi-selection;
        """
        self._pcbs_api.send_command("set_bck_rule_settings", bck_rule_settings)

    def get_nets_tagging(self):
        """
        Returns list of dicts with the current net-tagging settings
        """
        return self._pcbs_api.send_command("get_nets_tagging")

    def set_nets_tagging(self, net_tagging_settings: list):
        """
        Applies net-tagging settings to the project.
        net_tagging_settings - Net-tagging settings as list of dicts
        """
        self._pcbs_api.send_command("set_nets_tagging", net_tagging_settings)

    def get_comps_tagging(self):
        """
        Returns list of dicts with the current component-tagging settings
        """
        return self._pcbs_api.send_command("get_comps_tagging")

    def set_comps_tagging(self, comp_tagging_settings: list):
        """
        Applies component-tagging settings to the project.
        comp_tagging_settings - Component-tagging settings as list of dicts
        """
        self._pcbs_api.send_command("set_comps_tagging", comp_tagging_settings)

    def run_bck(self, rule_parameters=None):
        """
        Starts board checker.
        rule_parameters - Optional parameter with possible values: "custom" or "signal_spec".
        If "rule parameters" is not specified the project's value is used.
        Returns number of violations
        """
        return self._pcbs_api.send_command("run_bck", rule_parameters)

    def show_bck_results(self):
        """Shows violation view, if results are available"""
        self._pcbs_api.send_command("show_bck_results")

    def export_bck_results_as_xls(self, xls_file: os.PathLike):
        """
        Exports violations to the specified file
        xls_file - os.PathLike object as a path to the file
        """
        xls_file = str(xls_file)
        self._pcbs_api.send_command("export_bck_results_as_xls", xls_file)

    def add_bck_to_report(self):
        """
        Adds violation results to the current report
        """
        self._pcbs_api.send_command("add_bck_to_report")

    def show_decap_tool(self, show: bool = True):
        """Shows/closes EDA Decap Tool"""
        self._pcbs_api.send_command("show_decap_tool", show)

    def set_export_2d_settings(self, file_name: os.PathLike = "", simulator: str = "", model_name: str = ""):
        """Defines export 2D(TL) settings in the active PCBS project"""
        self._pcbs_api.send_command(
            "set_export_2d_settings",
            {"ExportFile": str(file_name), "ExportSimulator": simulator, "ExportModelName": model_name},
        )

    def export_2d(self, refresh_selection: bool = False, run_asynchronous: bool = False):
        """Exports 2D(TL) model of the active PCBS project"""
        self._pcbs_api.send_command("export_2d", {"Asynchronous": run_asynchronous, "RefreshSelection": refresh_selection})

    def get_selected_items(self) -> List[SelectedItem]:
        """Returns a list with the currently selected items in the Navigation Tree"""
        jsonList = self._pcbs_api.send_command("get_current_item_selection")
        itemList = []
        for obj in jsonList:
            item = SelectedItem()
            item.from_json(obj)
            itemList.append(item)

        return itemList

    def get_current_item_selection(self) -> List[Dict[str, str]]:
        """
        The method is deprecated. Use `get_selected_items(self) -> List[SelectedItem]` instead.

        Returns:
            list[Dict[str, str]]: A list with the currently selected items in the Navigation Tree.

        Example:
            [{'id': 'U23', 'type': 'comp'}, {'id': 'A6', 'type': 'net'}]

        Each dict contains:
            id (str): ID of the selected object.
            type (str): Type of the selected object. For valid values, see class :py:class:`.ItemType`.
        """
        return self._pcbs_api.send_command("get_current_item_selection")

    def set_selected_items(self, selected: List[SelectedItem]):
        """Changes current selection in the Navigation Tree to the specified items"""
        jsonList = []
        for item in selected:
            obj = item.to_json()
            jsonList.append(obj)

        self._pcbs_api.send_command("set_current_item_selection", jsonList)

    def set_current_item_selection(self, selected: List[Dict[str, str]]):
        """
        The method is deprecated. Use set_selected_items(self, selected: List[SelectedItem]) instead.

        Changes current selection in the Navigation Tree to the specified items.

        Args:
            selected (List[Dict[str, str]]): A list of dictionaries where each dictionary contains:
                - 'id' (str): The ID of the object to be selected.
                - 'type' (str): The type of the object to be selected. For valid values, see class :py:class:`.ItemType`.

        Examples:
            selected=[{'id': 'U22', 'type': 'comp'}, {'id': 'A2', 'type': 'net'}]
        """
        self._pcbs_api.send_command("set_current_item_selection", selected)

    def get_active_solver(self):
        """Returns the active solver"""
        return self._pcbs_api.send_command("get_active_solver")

    def set_active_solver(self, active_solver: str):
        """Changes active solver to the specified value"""
        self._pcbs_api.send_command("set_active_solver", active_solver)

    def get_mounted_components(self):
        """Returns a dict with the current Component-to-Mounted mapping as a dict {<REFDES>: <True|False>}."""
        return self._pcbs_api.send_command("get_mounted_components")

    def set_mounted_components(self, mounted: dict):
        """Modifies the Component-to-Mounted mapping by means of a dict {<REFDES>: <True|False>}."""
        self._pcbs_api.send_command("set_mounted_components", mounted)
