# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

import logging

import cst.units
from cst.eda.pcb_api import PCB, SimulationSettings

logger = logging.getLogger(__name__)
known_units = {
    cst.units.one: None,
}
for u in ["nm", "um", "mm", "cm", "m", "mil", "inch", "Ohm", "deg", "A", "V", "W"]:
    known_units[getattr(cst.units, u)] = u


class ToCommandsHelper:
    def __init__(self, inst, instname):
        self.inst = inst
        self.instname = instname

        self.skip_these = []
        self.explicit_order = []
        self.callbacks = {}
        self.replace_module_names = {}
        self.default = None

        self.coverage_test = False
        self.include_undocumented_and_private = False

        self._reset()

    def _reset(self):
        from collections import defaultdict

        self.privates_skipped = []
        self.undoc_skipped = []
        self.deprecated_skipped = []
        self.explicitly_skipped = []
        self.callables_skipped = []
        self.other_skipped = []
        self.import_statements = defaultdict(set)
        self.commands = []

    def _merge_converter(self, src):
        self.privates_skipped += src.privates_skipped
        self.undoc_skipped += src.undoc_skipped
        self.deprecated_skipped += src.deprecated_skipped
        self.explicitly_skipped += src.explicitly_skipped
        self.callables_skipped += src.callables_skipped
        self.other_skipped += src.other_skipped
        for k, v in src.import_statements.items():
            self.import_statements[k].update(v)
        self.commands += src.commands

    def _copy_config(self, src):
        self.skip_these = src.skip_these
        self.explicit_order = src.explicit_order
        self.callbacks = src.callbacks
        self.replace_module_names = src.replace_module_names
        self.coverage_test = src.coverage_test
        self.include_undocumented_and_private = src.include_undocumented_and_private

    def python_code(self):
        stmt = ""
        for module, what in sorted(self.import_statements.items()):
            module = self.replace_module_names.get(module, module)
            stmt += f"from {module} import {', '.join(sorted(what))}\n"

        if stmt:
            stmt += "\n"
        stmt += "\n".join(self.commands)
        return stmt

    def convert_unit(self, unit):
        assert unit in known_units
        unit = known_units[unit]
        if unit:
            self.import_statements["cst.units"].add(unit)
        return unit

    def convert(self):
        self._reset()
        template = "{full_attr_name} = {value}"

        inst_class = self.inst.__class__

        full_prefix = inst_class.__qualname__ + "."
        attr_names = sorted(dir(self.inst))
        for explicit in self.explicit_order:
            if explicit.startswith(full_prefix):
                explicit = explicit[len(full_prefix):]
                i = attr_names.index(explicit)
                if i >= 0:
                    del attr_names[i]
                    attr_names.append(explicit)

        for attr_name in attr_names:
            full_attr_id = full_prefix + attr_name

            if full_attr_id in self.skip_these:
                self.explicitly_skipped.append(full_attr_id)
                continue

            if attr_name.startswith('_') and not self.include_undocumented_and_private:
                self.privates_skipped.append(full_attr_id)
                continue

            attr = getattr(self.inst, attr_name)

            if callable(attr):
                self.callables_skipped.append(full_attr_id)
                continue

            attr_class = getattr(inst_class, attr_name, None)
            doc = getattr(attr_class, '__doc__')

            # skip attributes that are not documented
            if not doc and not self.include_undocumented_and_private:
                self.undoc_skipped.append(full_attr_id)
                continue

            if doc and doc.find("deprecated") >= 0:
                self.deprecated_skipped.append(full_attr_id)
                continue

            # check whether the property has a unit
            unit = getattr(self.inst, "_unit_" + attr_name, None)

            # if a default is given, only create code for stuff that is not default
            def_attr = None
            if self.default:
                if unit is None:
                    def_attr = getattr(self.default, attr_name)
                else:
                    def_attr = getattr(self.default, "_quantity_" + attr_name).convert_to(unit).value
                if isinstance(attr, float) or isinstance(def_attr, float):
                    is_non_default = abs(attr - def_attr) > 1e-4 * (abs(attr) + abs(def_attr))
                else:
                    is_non_default = attr != def_attr

                if self.coverage_test:
                    assert is_non_default, f"Expecting a value for attr with name {full_attr_id} not {attr}"
                if not is_non_default:
                    continue


            # check for special handlers
            cb = self.callbacks.get(full_attr_id)
            if cb:
                cb(self, full_attr_id, attr)
                continue

            def is_pybind_enum(v):
                return all([hasattr(v, x) for x in ('name', 'value', '__entries')])

            def has_simple_type(v):
                if isinstance(v, list):
                    return all(has_simple_type(m) for m in v)
                else:
                    return v.__class__ in [int, bool, float, str] or is_pybind_enum(v)

            if has_simple_type(attr):
                full_attr_name = f"{self.instname}.{attr_name}"
                try:
                    setattr(self.inst, attr_name, attr)
                    logger.info(f'Creating to generate command for {full_attr_id}, {type(attr)}')

                    if hasattr(attr, "__module__"):
                        self.import_statements[attr.__module__].add(attr.__class__.__qualname__)

                    
                    # special case for pybind11 enum types
                    if is_pybind_enum(attr):
                        attr_val = str(attr)
                    else:
                        if isinstance(attr, float):
                            attr_val = "{:.7g}".format(attr)
                        else:
                            attr_val = repr(attr)
                        if unit is not None:
                            unit_val = self.convert_unit(unit)
                            if unit_val is not None:
                                attr_val += " * " + unit_val

                    self.commands.append(template.format(full_attr_name=full_attr_name, value=attr_val))

                except AttributeError as e:
                    self.other_skipped.append(full_attr_id)
                    self.commands.append("#  " + template.format(full_attr_name=full_attr_name, value=repr(attr)))
                    logger.warning(f'Failed to generate command for {full_attr_id} {type(attr)}')
                    pass
                except RuntimeError as e:
                    self.other_skipped.append(full_attr_id)
                    self.commands.append("#  " + template.format(full_attr_name=full_attr_name, value=repr(attr)))
                    logger.warning(f'Failed to generate command for {full_attr_id} {type(attr)}')
                    pass
            else:
                subhelper = ToCommandsHelper(attr, f"{self.instname}.{attr_name}")
                subhelper._copy_config(self)
                if self.default:
                    subhelper.default = getattr(self.default, attr_name)
                subhelper.convert()
                self._merge_converter(subhelper)


def simulation_settings_converter(sim_settings: SimulationSettings, only_changes=True) -> ToCommandsHelper:
    custom_commands = {}

    def net_settings_cb(converter: ToCommandsHelper, full_attr_id, net_settings):
        converter.commands += [
            f'# {full_attr_id}',
        ]
        for name, settings in net_settings.items():
            converter.commands += [
                f'net_settings = {converter.instname}.net_settings(pcb.net("{name}"))',
            ]

            subhelper = ToCommandsHelper(settings, 'net_settings')
            subhelper._copy_config(converter)
            if converter.default:
                subhelper.default = converter.default._net_settings(name)
            subhelper.convert()
            converter._merge_converter(subhelper)

        converter.commands.append(f'#')

    def dominant_nets_cb(converter: ToCommandsHelper, full_attr_id, dom_nets):
        converter.commands.append(f'{converter.instname}.set_dominant_nets({repr(dom_nets)})')

    def selection_areas_cb(converter: ToCommandsHelper, full_attr_id, sel_areas):
        converter.commands += [
            f'# {full_attr_id}',
            f'{converter.instname}.delete_all_selection_areas(disable_area_restrictions=False)',
        ]
        indent = '    '
        unit_val = converter.convert_unit(converter.inst.length_unit.unit)
        for sa in sel_areas:
            outline = sa.get_outline().shell.approximate_polyline(1e-3, include_end=False)
            if len(outline) < 3:
                continue
            outline = f',\n{indent}'.join(str(p) for p in outline)
            converter.commands += [
                f'sel_area = {converter.instname}.select_polygonal_area([\n{indent}{outline},\n], enable_area_restrictions=False, unit={unit_val})',
            ]

            subhelper = ToCommandsHelper(sa, 'sel_area')
            subhelper._copy_config(converter)
            if converter.default:
                subhelper.default = converter.default.select_rectangular_area(0, 1, 0, 1, enable_area_restrictions=False)
            subhelper.convert()
            converter._merge_converter(subhelper)
        converter.commands.append(f'#')

    def make_port_cb(constructor_name, instance_name=None, pin_location = True, use_pec_sheet = False):
        if not instance_name:
            instance_name = constructor_name
        def port_cb(converter: ToCommandsHelper, full_attr_id, ports):
            converter.commands.append(f'# {full_attr_id}')
            for p in ports:
                if pin_location:
                    converter.commands += [
                        f'pin = pcb.component("{p.location[0]}").pin("{p.location[1]}")',
                        f'{instance_name} = pcb.simulation_settings.{constructor_name}(pin)',
                    ]
                else:
                    converter.commands += [
                        f'component = pcb.component("{p.location}")',
                        f'{instance_name} = pcb.simulation_settings.{constructor_name}(component)',
                    ]
                if use_pec_sheet:
                    # always assign this attribute. it is lazy-evaluated, so comparing with default does not work.
                    converter.commands += [
                        f'{instance_name}.use_pec_sheet = {p.use_pec_sheet}',
                    ]

                subhelper = ToCommandsHelper(p, instance_name)
                subhelper._copy_config(converter)
                if converter.default:
                    subhelper.default = getattr(converter.default, f"_{constructor_name}")(p.location)
                subhelper.convert()
                converter._merge_converter(subhelper)
            converter.commands.append(f'#')
        return port_cb

    def net_based_area_selection_cb(converter: ToCommandsHelper, full_attr_id, nbas):
        subhelper = ToCommandsHelper(nbas, 'nbas')
        subhelper._copy_config(converter)
        if converter.default:
            subhelper.default = converter.default.net_based_area_selection
        subhelper.convert()

        if subhelper.commands:
            converter.commands += [
                f'# {full_attr_id}',
                f'nbas = {converter.instname}.net_based_area_selection',
            ]

        converter._merge_converter(subhelper)

        # If any nets are set, we need to trigger a computation.
        if nbas.nets:
            converter.commands.append(f"nbas.update(enable_area_restrictions=False)")

        converter.commands.append(f'#')

    def grid_size_cb(converter: ToCommandsHelper, full_attr_id, grid_size):
        # 'grid_size' has a DB-specific default value, so we cannot detect non-default values.
        # Include 'grid_size' always, if snapping enabled.
        if converter.inst.snap_to_grid:
            attr_val = repr(grid_size)
            unit_val = converter.convert_unit(converter.inst._unit_grid_size)
            converter.commands.append(f"{converter.instname}.grid_size = {attr_val} * {unit_val}")
        else:
            converter.explicitly_skipped.append(full_attr_id)

    replace_module_names = {}
    replace_module_names['_cst_eda_interface.pcb_api'] = 'cst.eda.pcb_api'
    custom_commands['SimulationSettings.nets_with_settings'] = net_settings_cb
    custom_commands['SimulationSettings.dominant_nets'] = dominant_nets_cb
    custom_commands['SimulationSettings.rlc_nodes'] = make_port_cb("rlc_node")
    custom_commands['SimulationSettings.current_ports'] = make_port_cb("current_port")
    custom_commands['SimulationSettings.potentials'] = make_port_cb("potential")
    custom_commands['SimulationSettings.discrete_ports'] = make_port_cb("discrete_port", use_pec_sheet=True)
    custom_commands['SimulationSettings.heat_sources'] = make_port_cb("heat_source", pin_location=False)
    custom_commands['SimulationSettings.selection_areas'] = selection_areas_cb
    custom_commands['SimulationSettings.net_based_area_selection'] = net_based_area_selection_cb
    custom_commands["NetBasedAreaSelection.grid_size"] = grid_size_cb

    if only_changes:
        def_ss = SimulationSettings()
    else:
        def_ss = None

    converter = ToCommandsHelper(sim_settings, 'pcb.simulation_settings')
    converter.callbacks = custom_commands
    converter.replace_module_names = replace_module_names
    converter.default = def_ss
    converter.skip_these += [
        'SimulationSettings.length_unit',
        'SimulationSettings.first_auto_port_number',  # set by Modeler on first import
        'SimulationSettings.lateral_reference_length',  # set by PCB-converter
        'SimulationSettings.report_items',
        'SimulationSettings.thermal_model_simplification_algorithm',  # deprecated/renamed
        'NetSimulationSettings.net',
        'RLCNode.location',
        'CurrentPort.location',
        'CurrentPort.name',
        'Potential.location',
        'Potential.name',
        'DiscretePort.location',
        'DiscretePort.use_pec_sheet',
        'HeatSource.location',
    ]
    converter.explicit_order += [
        # There is some cross-talk potential between these settings.
        # Ensure they are set in a specific order, so the scripts are easier to read.
        'SimulationSettings.selection_areas',
        'SimulationSettings.net_based_area_selection',
        'SimulationSettings.restrict_to_selected_area',
    ]

    return converter


def create_user_script_for_pcb(pcb, user_script_file: str, only_changes=True):
    converter = simulation_settings_converter(pcb.simulation_settings, only_changes=only_changes)
    converter.convert()
    code = converter.python_code()

    code_lines = code.split('\n')    

    def_user_script = "def user_script(pcb, **kwargs):\n"

    with open(user_script_file, 'w') as fuser:
        fuser.write(def_user_script)
        for code_line in code_lines:
            fuser.write(f'    {code_line}\n')    

