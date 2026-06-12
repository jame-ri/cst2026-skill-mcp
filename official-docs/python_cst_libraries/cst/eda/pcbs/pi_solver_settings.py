# Copyright 1998-2025 Dassault Systemes Deutschland GmbH.

# <pi_solver_settings>
from cst.eda.pcbs.pi_solver_settings_types import convert_to_json_like_object, PIPort, PIPortList, SIDouble, Length, Choice

class PISolverSettings:
    """
    This class provides access to all the settings of the PI Solver.
    """
    def __init__(self):
        self._ports = PIPortList()
        self._adaptive_sweep = bool(True)
        self._adaptive_sweep_fmin_reset_factor = SIDouble(value=3.0, ext='')
        self._adaptive_sweep_max_error = SIDouble(value=0.003, ext='')
        self._adaptive_sweep_n_confirmations = int(3)
        self._adaptive_sweep_n_equidistant_samples_before = int(3)
        self._add_DC_point = bool(False)
        self._area_restriction_from_power_nets = bool(False)
        self._contrast_Zs_percent = SIDouble(value=5.0, ext='')
        self._detect_RLC_models = bool(True)
        self._disable_models_where_ports = bool(True)
        self._export_touchstone = bool(False)
        self._filter_PCB = bool(True)
        self._fmax = SIDouble(value=2.0, ext='G')
        self._fmin = SIDouble(value=100.0, ext='k')
        self._generate_voltage_plots_for_all = bool(False)
        self._heal_geometry_problems = bool(False)
        self._hmax = Length(value=0.0, units='mm')
        self._logarithmic_sweep = bool(True)
        self._mesh_refinement = bool(False)
        self._mesh_refinement_3D = bool(False)
        self._n_samples = int(100)
        self._n_via_segments = int(0)
        self._only_refine_around_the_top_percent = SIDouble(value=100.0, ext='')
        self._only_refine_if_current_larger_than = SIDouble(value=0.01, ext='')
        self._optimize_decaps = bool(False)
        self._port_impedance = SIDouble(value=50.0, ext='')
        self._replace_ports_by_IO_excitations = bool(False)
        self._restrict_to_extrema = bool(True)
        self._restrict_to_selected_nets = bool(True)
        self._show_eda_import_dialog = bool(False)
        self._solver_choice = Choice(choice='3D Frequency Domain', choices=['3D Frequency Domain', '3D Frequency Domain Fast Resonant'])
        self._suppress_solder_mask = bool(True)
        self._suppress_unconnected_pads = bool(False)
        self._tolerance_fs_percent = SIDouble(value=5.0, ext='')
        self._use_zero_layer_thickness = bool(True)
        self._voltage_reference_layers = list()
        self._voltage_reference_net_restriction_mode = Choice(choice='only GND nets', choices=['all nets', 'only GND nets', 'only Power/GND nets'])
        
        # Deprecated settings
        self._directly_run_MWS_simulation = False

    @property
    def ports(self):
        """The list of excitations for the PI-Solver"""
        return self._ports

    @ports.setter
    def ports(self, value):
        if not isinstance(value, PIPortList):
            raise ValueError(f"Cannot assign {value} to logarithmic_sweep, expecting PIPortList")
        for i, port in enumerate(value):
            if not isinstance(port, PIPort):
                raise ValueError(f"{i}-th item is of type {type(port)}. Expecting all items in the list to be of type PIPort")
        self._ports = value

    
    @property
    def adaptive_mesh_refinement(self):
        """Adaptive mesh refinement"""
        return self._mesh_refinement_3D
    
    @adaptive_mesh_refinement.setter
    def adaptive_mesh_refinement(self, value: bool):
        if isinstance(value, bool):
            self._mesh_refinement_3D = value
            return
    
        if hasattr(self._mesh_refinement_3D, 'assign_from'):
            self._mesh_refinement_3D.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to adaptive_mesh_refinement, expecting a bool-type")
    
    
    @property
    def adaptive_sweep(self):
        """Adaptive sweep"""
        return self._adaptive_sweep
    
    @adaptive_sweep.setter
    def adaptive_sweep(self, value: bool):
        if isinstance(value, bool):
            self._adaptive_sweep = value
            return
    
        if hasattr(self._adaptive_sweep, 'assign_from'):
            self._adaptive_sweep.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to adaptive_sweep, expecting a bool-type")
    
    
    @property
    def adaptive_sweep_fmin_reset_factor(self):
        """If a sample at frequency 'f' failed, reset fmin to f times"""
        return self._adaptive_sweep_fmin_reset_factor
    
    @adaptive_sweep_fmin_reset_factor.setter
    def adaptive_sweep_fmin_reset_factor(self, value: SIDouble):
        if isinstance(value, SIDouble):
            self._adaptive_sweep_fmin_reset_factor = value
            return
    
        if hasattr(self._adaptive_sweep_fmin_reset_factor, 'assign_from'):
            self._adaptive_sweep_fmin_reset_factor.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to adaptive_sweep_fmin_reset_factor, expecting a SIDouble-type")
    
    
    @property
    def adaptive_sweep_max_error(self):
        """Maximum error"""
        return self._adaptive_sweep_max_error
    
    @adaptive_sweep_max_error.setter
    def adaptive_sweep_max_error(self, value: SIDouble):
        if isinstance(value, SIDouble):
            self._adaptive_sweep_max_error = value
            return
    
        if hasattr(self._adaptive_sweep_max_error, 'assign_from'):
            self._adaptive_sweep_max_error.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to adaptive_sweep_max_error, expecting a SIDouble-type")
    
    
    @property
    def adaptive_sweep_n_confirmations(self):
        """Number of confirmations"""
        return self._adaptive_sweep_n_confirmations
    
    @adaptive_sweep_n_confirmations.setter
    def adaptive_sweep_n_confirmations(self, value: int):
        if isinstance(value, int):
            self._adaptive_sweep_n_confirmations = value
            return
    
        if hasattr(self._adaptive_sweep_n_confirmations, 'assign_from'):
            self._adaptive_sweep_n_confirmations.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to adaptive_sweep_n_confirmations, expecting a int-type")
    
    
    @property
    def adaptive_sweep_n_equidistant_samples_before(self):
        """Number of equidistant samples before adaptive sweep"""
        return self._adaptive_sweep_n_equidistant_samples_before
    
    @adaptive_sweep_n_equidistant_samples_before.setter
    def adaptive_sweep_n_equidistant_samples_before(self, value: int):
        if isinstance(value, int):
            self._adaptive_sweep_n_equidistant_samples_before = value
            return
    
        if hasattr(self._adaptive_sweep_n_equidistant_samples_before, 'assign_from'):
            self._adaptive_sweep_n_equidistant_samples_before.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to adaptive_sweep_n_equidistant_samples_before, expecting a int-type")
    
    
    @property
    def add_DC_point(self):
        """compute behavior at f=0"""
        return self._add_DC_point
    
    @add_DC_point.setter
    def add_DC_point(self, value: bool):
        if isinstance(value, bool):
            self._add_DC_point = value
            return
    
        if hasattr(self._add_DC_point, 'assign_from'):
            self._add_DC_point.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to add_DC_point, expecting a bool-type")
    
    
    @property
    def area_restriction_from_power_nets(self):
        """Restrict simulation area based on power nets"""
        return self._area_restriction_from_power_nets
    
    @area_restriction_from_power_nets.setter
    def area_restriction_from_power_nets(self, value: bool):
        if isinstance(value, bool):
            self._area_restriction_from_power_nets = value
            return
    
        if hasattr(self._area_restriction_from_power_nets, 'assign_from'):
            self._area_restriction_from_power_nets.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to area_restriction_from_power_nets, expecting a bool-type")
    
    
    @property
    def consider_components(self):
        """Consider components"""
        return self._detect_RLC_models
    
    @consider_components.setter
    def consider_components(self, value: bool):
        if isinstance(value, bool):
            self._detect_RLC_models = value
            return
    
        if hasattr(self._detect_RLC_models, 'assign_from'):
            self._detect_RLC_models.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to consider_components, expecting a bool-type")
    
    
    @property
    def directly_run_simulation(self):
        """This property has been deprecated and has no effect."""
        return self._directly_run_MWS_simulation
    
    @directly_run_simulation.setter
    def directly_run_simulation(self, value):
        self._directly_run_MWS_simulation = value
    
    
    @property
    def disable_models_where_ports(self):
        """Disable models where ports defined"""
        return self._disable_models_where_ports
    
    @disable_models_where_ports.setter
    def disable_models_where_ports(self, value: bool):
        if isinstance(value, bool):
            self._disable_models_where_ports = value
            return
    
        if hasattr(self._disable_models_where_ports, 'assign_from'):
            self._disable_models_where_ports.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to disable_models_where_ports, expecting a bool-type")
    
    
    @property
    def exclude_solder_mask(self):
        """Exclude solder mask"""
        return self._suppress_solder_mask
    
    @exclude_solder_mask.setter
    def exclude_solder_mask(self, value: bool):
        if isinstance(value, bool):
            self._suppress_solder_mask = value
            return
    
        if hasattr(self._suppress_solder_mask, 'assign_from'):
            self._suppress_solder_mask.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to exclude_solder_mask, expecting a bool-type")
    
    
    @property
    def export_touchstone(self):
        """Export S-parameters as Touchstone"""
        return self._export_touchstone
    
    @export_touchstone.setter
    def export_touchstone(self, value: bool):
        if isinstance(value, bool):
            self._export_touchstone = value
            return
    
        if hasattr(self._export_touchstone, 'assign_from'):
            self._export_touchstone.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to export_touchstone, expecting a bool-type")
    
    
    @property
    def extrema_contrast(self):
        """Extrema contrast"""
        return self._contrast_Zs_percent
    
    @extrema_contrast.setter
    def extrema_contrast(self, value: SIDouble):
        if isinstance(value, SIDouble):
            self._contrast_Zs_percent = value
            return
    
        if hasattr(self._contrast_Zs_percent, 'assign_from'):
            self._contrast_Zs_percent.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to extrema_contrast, expecting a SIDouble-type")
    
    
    @property
    def fmax(self):
        """Maximum frequency"""
        return self._fmax
    
    @fmax.setter
    def fmax(self, value: SIDouble):
        if isinstance(value, SIDouble):
            self._fmax = value
            return
    
        if hasattr(self._fmax, 'assign_from'):
            self._fmax.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to fmax, expecting a SIDouble-type")
    
    
    @property
    def fmin(self):
        """Minimum frequency"""
        return self._fmin
    
    @fmin.setter
    def fmin(self, value: SIDouble):
        if isinstance(value, SIDouble):
            self._fmin = value
            return
    
        if hasattr(self._fmin, 'assign_from'):
            self._fmin.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to fmin, expecting a SIDouble-type")
    
    
    @property
    def frequency_tolerance(self):
        """Frequency tolerance"""
        return self._tolerance_fs_percent
    
    @frequency_tolerance.setter
    def frequency_tolerance(self, value: SIDouble):
        if isinstance(value, SIDouble):
            self._tolerance_fs_percent = value
            return
    
        if hasattr(self._tolerance_fs_percent, 'assign_from'):
            self._tolerance_fs_percent.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to frequency_tolerance, expecting a SIDouble-type")
    
    
    @property
    def generate_plots(self):
        """Generate plots"""
        return self._generate_voltage_plots_for_all
    
    @generate_plots.setter
    def generate_plots(self, value: bool):
        if isinstance(value, bool):
            self._generate_voltage_plots_for_all = value
            return
    
        if hasattr(self._generate_voltage_plots_for_all, 'assign_from'):
            self._generate_voltage_plots_for_all.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to generate_plots, expecting a bool-type")
    
    
    @property
    def heal_geometry_problems(self):
        """Heal geometry problems"""
        return self._heal_geometry_problems
    
    @heal_geometry_problems.setter
    def heal_geometry_problems(self, value: bool):
        if isinstance(value, bool):
            self._heal_geometry_problems = value
            return
    
        if hasattr(self._heal_geometry_problems, 'assign_from'):
            self._heal_geometry_problems.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to heal_geometry_problems, expecting a bool-type")
    
    
    @property
    def logarithmic_sweep(self):
        """Logarithmic sweep"""
        return self._logarithmic_sweep
    
    @logarithmic_sweep.setter
    def logarithmic_sweep(self, value: bool):
        if isinstance(value, bool):
            self._logarithmic_sweep = value
            return
    
        if hasattr(self._logarithmic_sweep, 'assign_from'):
            self._logarithmic_sweep.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to logarithmic_sweep, expecting a bool-type")
    
    
    @property
    def maximum_mesh_step(self):
        """Max. mesh step [0=automatic]"""
        return self._hmax
    
    @maximum_mesh_step.setter
    def maximum_mesh_step(self, value: Length):
        if isinstance(value, Length):
            self._hmax = value
            return
    
        if hasattr(self._hmax, 'assign_from'):
            self._hmax.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to maximum_mesh_step, expecting a Length-type")
    
    
    @property
    def mesh_refinement(self):
        """Mesh refinement around vias"""
        return self._mesh_refinement
    
    @mesh_refinement.setter
    def mesh_refinement(self, value: bool):
        if isinstance(value, bool):
            self._mesh_refinement = value
            return
    
        if hasattr(self._mesh_refinement, 'assign_from'):
            self._mesh_refinement.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to mesh_refinement, expecting a bool-type")
    
    
    @property
    def model_etch_layers_as_2D_sheets(self):
        """Model etch layers as 2D sheets"""
        return self._use_zero_layer_thickness
    
    @model_etch_layers_as_2D_sheets.setter
    def model_etch_layers_as_2D_sheets(self, value: bool):
        if isinstance(value, bool):
            self._use_zero_layer_thickness = value
            return
    
        if hasattr(self._use_zero_layer_thickness, 'assign_from'):
            self._use_zero_layer_thickness.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to model_etch_layers_as_2D_sheets, expecting a bool-type")
    
    
    @property
    def n_drill_segments(self):
        """Number of segments for drill representation (round=0)"""
        return self._n_via_segments
    
    @n_drill_segments.setter
    def n_drill_segments(self, value: int):
        if isinstance(value, int):
            self._n_via_segments = value
            return
    
        if hasattr(self._n_via_segments, 'assign_from'):
            self._n_via_segments.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to n_drill_segments, expecting a int-type")
    
    
    @property
    def n_samples(self):
        """Number of samples"""
        return self._n_samples
    
    @n_samples.setter
    def n_samples(self, value: int):
        if isinstance(value, int):
            self._n_samples = value
            return
    
        if hasattr(self._n_samples, 'assign_from'):
            self._n_samples.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to n_samples, expecting a int-type")
    
    
    @property
    def only_plot_at_extrema(self):
        """Only plot at impedance extrema"""
        return self._restrict_to_extrema
    
    @only_plot_at_extrema.setter
    def only_plot_at_extrema(self, value: bool):
        if isinstance(value, bool):
            self._restrict_to_extrema = value
            return
    
        if hasattr(self._restrict_to_extrema, 'assign_from'):
            self._restrict_to_extrema.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to only_plot_at_extrema, expecting a bool-type")
    
    
    @property
    def only_refine_if_current_larger_than(self):
        """Restrict to vias carrying at least this current"""
        return self._only_refine_if_current_larger_than
    
    @only_refine_if_current_larger_than.setter
    def only_refine_if_current_larger_than(self, value: SIDouble):
        if isinstance(value, SIDouble):
            self._only_refine_if_current_larger_than = value
            return
    
        if hasattr(self._only_refine_if_current_larger_than, 'assign_from'):
            self._only_refine_if_current_larger_than.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to only_refine_if_current_larger_than, expecting a SIDouble-type")
    
    
    @property
    def optimize_decaps(self):
        """Run Decap Analysis"""
        return self._optimize_decaps
    
    @optimize_decaps.setter
    def optimize_decaps(self, value: bool):
        if isinstance(value, bool):
            self._optimize_decaps = value
            return
    
        if hasattr(self._optimize_decaps, 'assign_from'):
            self._optimize_decaps.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to optimize_decaps, expecting a bool-type")
    
    
    @property
    def port_impedance(self):
        """Port impedance"""
        return self._port_impedance
    
    @port_impedance.setter
    def port_impedance(self, value: SIDouble):
        if isinstance(value, SIDouble):
            self._port_impedance = value
            return
    
        if hasattr(self._port_impedance, 'assign_from'):
            self._port_impedance.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to port_impedance, expecting a SIDouble-type")
    
    
    @property
    def replace_ports_by_IO_excitations(self):
        """Replace all ports at components with excitations at internal IO devices"""
        return self._replace_ports_by_IO_excitations
    
    @replace_ports_by_IO_excitations.setter
    def replace_ports_by_IO_excitations(self, value: bool):
        if isinstance(value, bool):
            self._replace_ports_by_IO_excitations = value
            return
    
        if hasattr(self._replace_ports_by_IO_excitations, 'assign_from'):
            self._replace_ports_by_IO_excitations.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to replace_ports_by_IO_excitations, expecting a bool-type")
    
    
    @property
    def restrict_to_excited_nets(self):
        """Restrict to excited nets"""
        return self._filter_PCB
    
    @restrict_to_excited_nets.setter
    def restrict_to_excited_nets(self, value: bool):
        if isinstance(value, bool):
            self._filter_PCB = value
            return
    
        if hasattr(self._filter_PCB, 'assign_from'):
            self._filter_PCB.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to restrict_to_excited_nets, expecting a bool-type")
    
    
    @property
    def restrict_to_excited_nets_3D(self):
        """Restrict to excited nets"""
        return self._restrict_to_selected_nets
    
    @restrict_to_excited_nets_3D.setter
    def restrict_to_excited_nets_3D(self, value: bool):
        if isinstance(value, bool):
            self._restrict_to_selected_nets = value
            return
    
        if hasattr(self._restrict_to_selected_nets, 'assign_from'):
            self._restrict_to_selected_nets.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to restrict_to_excited_nets_3D, expecting a bool-type")
    
    
    @property
    def restrict_to_fraction_of_high_current_vias(self):
        """Restrict to the fraction of high-current vias"""
        return self._only_refine_around_the_top_percent
    
    @restrict_to_fraction_of_high_current_vias.setter
    def restrict_to_fraction_of_high_current_vias(self, value: SIDouble):
        if isinstance(value, SIDouble):
            self._only_refine_around_the_top_percent = value
            return
    
        if hasattr(self._only_refine_around_the_top_percent, 'assign_from'):
            self._only_refine_around_the_top_percent.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to restrict_to_fraction_of_high_current_vias, expecting a SIDouble-type")
    
    
    @property
    def show_eda_import_dialog(self):
        """Show eda import dialog"""
        return self._show_eda_import_dialog
    
    @show_eda_import_dialog.setter
    def show_eda_import_dialog(self, value: bool):
        if isinstance(value, bool):
            self._show_eda_import_dialog = value
            return
    
        if hasattr(self._show_eda_import_dialog, 'assign_from'):
            self._show_eda_import_dialog.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to show_eda_import_dialog, expecting a bool-type")
    
    
    @property
    def solver_choice(self):
        """Solver"""
        return self._solver_choice
    
    @solver_choice.setter
    def solver_choice(self, value: Choice):
        if isinstance(value, Choice):
            self._solver_choice = value
            return
    
        if hasattr(self._solver_choice, 'assign_from'):
            self._solver_choice.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to solver_choice, expecting a Choice-type")
    
    
    @property
    def suppress_unconnected_pads(self):
        """Suppress unconnected mid-layer pads"""
        return self._suppress_unconnected_pads
    
    @suppress_unconnected_pads.setter
    def suppress_unconnected_pads(self, value: bool):
        if isinstance(value, bool):
            self._suppress_unconnected_pads = value
            return
    
        if hasattr(self._suppress_unconnected_pads, 'assign_from'):
            self._suppress_unconnected_pads.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to suppress_unconnected_pads, expecting a bool-type")
    
    
    @property
    def voltage_reference_conductors(self):
        """Reference conductors"""
        return self._voltage_reference_net_restriction_mode
    
    @voltage_reference_conductors.setter
    def voltage_reference_conductors(self, value: Choice):
        if isinstance(value, Choice):
            self._voltage_reference_net_restriction_mode = value
            return
    
        if hasattr(self._voltage_reference_net_restriction_mode, 'assign_from'):
            self._voltage_reference_net_restriction_mode.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to voltage_reference_conductors, expecting a Choice-type")
    
    
    @property
    def voltage_reference_layers(self):
        """Reference layers"""
        return self._voltage_reference_layers
    
    @voltage_reference_layers.setter
    def voltage_reference_layers(self, value: list):
        if isinstance(value, list):
            self._voltage_reference_layers = value
            return
    
        if hasattr(self._voltage_reference_layers, 'assign_from'):
            self._voltage_reference_layers.assign_from(value)
            return
    
        raise ValueError(f"Cannot assign {value} to voltage_reference_layers, expecting a list-type")
    

    def to_json(self):
        res = {}
        for name, value in self.__dict__.items():
            res[name.lstrip('_')] = convert_to_json_like_object(value)
        return res
    
    def from_json(self, data: dict):
        for name, value in data.items():
            try:
                attr = getattr(self, '_'+name)
            except AttributeError:
                setattr(self, name, value)
                continue

            aclass = attr.__class__
            if hasattr(aclass, 'from_json'):
                attr.from_json(value)
            elif isinstance(value, dict):
                setattr(self, '_'+name, aclass(**value))
            else:
                setattr(self, '_'+name, aclass(value))


# </pi_solver_settings>