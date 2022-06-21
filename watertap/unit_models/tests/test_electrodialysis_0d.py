###############################################################################
# WaterTAP Copyright (c) 2021, The Regents of the University of California,
# through Lawrence Berkeley National Laboratory, Oak Ridge National
# Laboratory, National Renewable Energy Laboratory, and National Energy
# Technology Laboratory (subject to receipt of any required approvals from
# the U.S. Dept. of Energy). All rights reserved.
#
# Please see the files COPYRIGHT.md and LICENSE.md for full copyright and license
# information, respectively. These files are also available online at the URL
# "https://github.com/watertap-org/watertap/"
#
###############################################################################
import pytest
from watertap.property_models.ion_DSPMDE_prop_pack import DSPMDEParameterBlock
from watertap.unit_models.electrodialysis_0d import Electrodialysis0D
from pyomo.environ import (
    ConcreteModel,
    assert_optimal_termination,
    value,
    Set,
    Param,
    Var,
    units as pyunits,
    Suffix,
    Constraint,
    SolverFactory,
    SolverStatus,
    TerminationCondition,
)
from idaes.core import (
    FlowsheetBlock,
    MaterialFlowBasis,
    MaterialBalanceType,
    MomentumBalanceType,
    EnergyBalanceType,
)
from idaes.core.util.exceptions import ConfigurationError
from idaes.core.util.model_statistics import degrees_of_freedom
from pyomo.util.check_units import assert_units_consistent
import idaes.core.util.scaling as iscale
from idaes.core.util.testing import initialization_tester
from idaes.core.solvers import get_solver
import re

__author__ = "Xiangyu Bi"

solver = get_solver()

# -----------------------------------------------------------------------------
# Start test class
class TestElectrodialysisVoltageConst:
    @pytest.fixture(scope="class")
    def electrodialysis_cell1(self):
        m = ConcreteModel()
        m.fs = FlowsheetBlock(default={"dynamic": False})
        ion_dict = {
            "solute_list": ["Na_+", "Cl_-"],
            "mw_data": {"H2O": 18e-3, "Na_+": 23e-3, "Cl_-": 35.5e-3},
            "electrical_mobility_data": {"Na_+": 5.19e-8, "Cl_-": 7.92e-8},
            "charge": {"Na_+": 1, "Cl_-": -1},
        }
        m.fs.properties = DSPMDEParameterBlock(default=ion_dict)
        m.fs.unit = Electrodialysis0D(default={"property_package": m.fs.properties})
        m.fs.unit.config.operation_mode = "Constant_Voltage"
        return m

    @pytest.mark.unit
    def test_build_model(self, electrodialysis_cell1):
        m = electrodialysis_cell1
        # test configrations
        assert len(m.fs.unit.config) == 7
        assert not m.fs.unit.config.dynamic
        assert not m.fs.unit.config.has_holdup
        assert m.fs.unit.config.operation_mode == "Constant_Voltage"
        assert m.fs.unit.config.material_balance_type == MaterialBalanceType.useDefault
        assert (
            m.fs.unit.config.momentum_balance_type == MomentumBalanceType.pressureTotal
        )
        assert m.fs.unit.config.property_package is m.fs.properties
        assert "H2O" in m.fs.properties.component_list

        # test all essential params and vars are built
        assert isinstance(m.fs.unit.membrane_set, Set)
        assert isinstance(m.fs.unit.water_density, Param)
        assert isinstance(m.fs.unit.cell_pair_num, Var)
        assert isinstance(m.fs.unit.cell_width, Var)
        assert isinstance(m.fs.unit.cell_length, Var)
        assert isinstance(m.fs.unit.spacer_thickness, Var)
        assert isinstance(m.fs.unit.membrane_thickness, Var)
        assert isinstance(m.fs.unit.solute_diffusivity_membrane, Var)
        assert isinstance(m.fs.unit.ion_trans_number_membrane, Var)
        assert isinstance(m.fs.unit.water_trans_number_membrane, Var)
        assert isinstance(m.fs.unit.water_permeability_membrane, Var)
        assert isinstance(m.fs.unit.membrane_surface_resistance, Var)
        assert isinstance(m.fs.unit.current, Var)
        assert isinstance(m.fs.unit.voltage, Var)
        assert isinstance(m.fs.unit.current_utilization, Var)
        assert isinstance(m.fs.unit.power_electrical, Var)
        assert isinstance(m.fs.unit.specific_power_electrical, Var)
        assert isinstance(m.fs.unit.current_efficiency, Var)
        assert isinstance(m.fs.unit.elec_migration_flux_in, Var)
        assert isinstance(m.fs.unit.elec_migration_flux_out, Var)
        assert isinstance(m.fs.unit.nonelec_flux_in, Var)
        assert isinstance(m.fs.unit.nonelec_flux_out, Var)
        assert isinstance(m.fs.unit.eq_current_voltage_relation, Constraint)
        assert isinstance(m.fs.unit.eq_elec_migration_flux_in, Constraint)
        assert isinstance(m.fs.unit.eq_elec_migration_flux_out, Constraint)
        assert isinstance(m.fs.unit.eq_nonelec_flux_in, Constraint)
        assert isinstance(m.fs.unit.eq_nonelec_flux_out, Constraint)
        assert isinstance(m.fs.unit.eq_mass_transfer_term_diluate, Constraint)
        assert isinstance(m.fs.unit.eq_mass_transfer_term_concentrate, Constraint)
        assert isinstance(m.fs.unit.eq_power_electrical, Constraint)
        assert isinstance(m.fs.unit.eq_specific_power_electrical, Constraint)
        assert isinstance(m.fs.unit.eq_current_efficiency, Constraint)
        assert isinstance(m.fs.unit.eq_isothermal_diluate, Constraint)
        assert isinstance(m.fs.unit.eq_isothermal_concentrate, Constraint)

    @pytest.mark.unit
    def test_stats_constant_vol(self, electrodialysis_cell1):
        m = electrodialysis_cell1
        assert_units_consistent(m)
        assert degrees_of_freedom(m) == 33
        # Specify a system
        # Note: Testing scenarios in this file are primarily in accord with an experimental
        # setup reported by Campione et al. in Desalination 465 (2019): 79-93.
        # set the operational parameters
        m.fs.unit.water_trans_number_membrane["cem"].fix(5.8)
        m.fs.unit.water_trans_number_membrane["aem"].fix(4.3)
        m.fs.unit.water_permeability_membrane["cem"].fix(2.16e-14)
        m.fs.unit.water_permeability_membrane["aem"].fix(1.75e-14)
        m.fs.unit.voltage.fix(0.5)
        m.fs.unit.electrodes_resistance.fix(0)
        m.fs.unit.cell_pair_num.fix(10)
        m.fs.unit.current_utilization.fix(1)
        m.fs.unit.spacer_thickness.fix(2.7e-4)
        m.fs.unit.membrane_surface_resistance["cem"].fix(1.89e-4)
        m.fs.unit.membrane_surface_resistance["aem"].fix(1.77e-4)
        m.fs.unit.cell_width.fix(0.1)
        m.fs.unit.cell_length.fix(0.79)
        m.fs.unit.membrane_thickness["aem"].fix(1.3e-4)
        m.fs.unit.membrane_thickness["cem"].fix(1.3e-4)
        m.fs.unit.solute_diffusivity_membrane["cem", "Na_+"].fix(1.8e-10)
        m.fs.unit.solute_diffusivity_membrane["aem", "Na_+"].fix(1.25e-10)
        m.fs.unit.solute_diffusivity_membrane["cem", "Cl_-"].fix(1.8e-10)
        m.fs.unit.solute_diffusivity_membrane["aem", "Cl_-"].fix(1.25e-10)
        m.fs.unit.ion_trans_number_membrane["cem", "Na_+"].fix(1)
        m.fs.unit.ion_trans_number_membrane["aem", "Na_+"].fix(0)
        m.fs.unit.ion_trans_number_membrane["cem", "Cl_-"].fix(0)
        m.fs.unit.ion_trans_number_membrane["aem", "Cl_-"].fix(1)

        # check ion transfer number requirements
        assert (
            sum(
                value(m.fs.unit.ion_trans_number_membrane["cem", j])
                for j in m.fs.properties.ion_set
            )
            == 1
        )
        assert (
            sum(
                value(m.fs.unit.ion_trans_number_membrane["aem", j])
                for j in m.fs.properties.ion_set
            )
            == 1
        )
        assert sum(
            value(m.fs.unit.ion_trans_number_membrane["cem", j])
            for j in m.fs.properties.cation_set
        ) == sum(
            value(m.fs.unit.ion_trans_number_membrane["aem", j])
            for j in m.fs.properties.anion_set
        )

        # set the inlet stream
        m.fs.unit.inlet_diluate.pressure.fix(101325)
        m.fs.unit.inlet_diluate.temperature.fix(298.15)
        m.fs.unit.inlet_diluate.flow_mol_phase_comp[0, "Liq", "H2O"].fix(2.40e-2)
        m.fs.unit.inlet_diluate.flow_mol_phase_comp[0, "Liq", "Na_+"].fix(7.38e-5)
        m.fs.unit.inlet_diluate.flow_mol_phase_comp[0, "Liq", "Cl_-"].fix(7.38e-5)
        m.fs.unit.inlet_concentrate.pressure.fix(101325)
        m.fs.unit.inlet_concentrate.temperature.fix(298.15)
        m.fs.unit.inlet_concentrate.flow_mol_phase_comp[0, "Liq", "H2O"].fix(2.40e-2)
        m.fs.unit.inlet_concentrate.flow_mol_phase_comp[0, "Liq", "Na_+"].fix(7.38e-5)
        m.fs.unit.inlet_concentrate.flow_mol_phase_comp[0, "Liq", "Cl_-"].fix(7.38e-5)

        assert degrees_of_freedom(m) == 0

    @pytest.mark.component
    def test_initialization_scaling(self, electrodialysis_cell1):
        m = electrodialysis_cell1
        # set default scaling for state vars
        m.fs.properties.set_default_scaling(
            "flow_mol_phase_comp", 1e2, index=("Liq", "H2O")
        )
        m.fs.properties.set_default_scaling(
            "flow_mol_phase_comp", 1e4, index=("Liq", "Na_+")
        )
        m.fs.properties.set_default_scaling(
            "flow_mol_phase_comp", 1e4, index=("Liq", "Cl_-")
        )
        iscale.calculate_scaling_factors(m.fs)
        initialization_tester(m)
        badly_scaled_var_values = {
            var.name: val for (var, val) in iscale.badly_scaled_var_generator(m)
        }
        assert not badly_scaled_var_values
        # check to make sure DOF does not change
        assert degrees_of_freedom(m) == 0

    @pytest.mark.component
    def test_solve(self, electrodialysis_cell1):
        m = electrodialysis_cell1
        # run solver and check for optimal solution
        results = solver.solve(m)
        assert_optimal_termination(results)
        badly_scaled_var_values = {
            var.name: val for (var, val) in iscale.badly_scaled_var_generator(m)
        }
        assert not badly_scaled_var_values

    @pytest.mark.component
    def test_solution(self, electrodialysis_cell1):
        m = electrodialysis_cell1

        assert value(
            m.fs.unit.outlet_diluate.flow_mol_phase_comp[0, "Liq", "H2O"]
        ) == pytest.approx(2.29e-2, rel=5e-2)
        assert value(
            m.fs.unit.outlet_diluate.flow_mol_phase_comp[0, "Liq", "Na_+"]
        ) == pytest.approx(5.9e-06, rel=5e-1)
        assert value(
            m.fs.unit.outlet_diluate.flow_mol_phase_comp[0, "Liq", "Cl_-"]
        ) == pytest.approx(5.9e-06, rel=5e-1)
        assert value(
            m.fs.unit.outlet_concentrate.flow_mol_phase_comp[0, "Liq", "H2O"]
        ) == pytest.approx(2.51e-2, rel=5e-2)
        assert value(
            m.fs.unit.outlet_concentrate.flow_mol_phase_comp[0, "Liq", "Na_+"]
        ) == pytest.approx(1.417e-4, rel=5e-3)
        assert value(
            m.fs.unit.outlet_concentrate.flow_mol_phase_comp[0, "Liq", "Cl_-"]
        ) == pytest.approx(1.417e-4, rel=5e-3)

    @pytest.mark.component
    def test_performance_contents(self, electrodialysis_cell1):
        m = electrodialysis_cell1
        perform_dict = m.fs.unit._get_performance_contents()
        assert "vars" in perform_dict
        assert value(
            perform_dict["vars"]["Electrical power consumption(Watt)"]
        ) == pytest.approx(4.6, rel=5e-1)
        assert value(
            perform_dict["vars"]["Specific electrical power consumption (kWh/m**3)"]
        ) == pytest.approx(3.09, rel=5e-2)
        assert value(
            perform_dict["vars"]["Current efficiency for deionzation"]
        ) == pytest.approx(0.71, rel=5e-2)


class TestElectrodialysisCurrentConst:
    @pytest.fixture(scope="class")
    def electrodialysis_cell2(self):
        m = ConcreteModel()
        m.fs = FlowsheetBlock(default={"dynamic": False})
        ion_dict = {
            "solute_list": ["Na_+", "Cl_-"],
            "mw_data": {"H2O": 18e-3, "Na_+": 23e-3, "Cl_-": 35.5e-3},
            "electrical_mobility_data": {"Na_+": 5.19e-8, "Cl_-": 7.92e-8},
            "charge": {"Na_+": 1, "Cl_-": -1},
        }
        m.fs.properties = DSPMDEParameterBlock(default=ion_dict)
        m.fs.unit = Electrodialysis0D(default={"property_package": m.fs.properties})
        m.fs.unit.config.operation_mode = "Constant_Current"
        return m

    @pytest.mark.unit
    def test_build_model(self, electrodialysis_cell2):
        m = electrodialysis_cell2

        # test configrations
        assert len(m.fs.unit.config) == 7
        assert not m.fs.unit.config.dynamic
        assert not m.fs.unit.config.has_holdup
        assert m.fs.unit.config.operation_mode == "Constant_Current"
        assert m.fs.unit.config.material_balance_type == MaterialBalanceType.useDefault
        assert (
            m.fs.unit.config.momentum_balance_type == MomentumBalanceType.pressureTotal
        )
        assert m.fs.unit.config.property_package is m.fs.properties
        assert "H2O" in m.fs.properties.component_list

        # test all essential params and vars are built
        assert isinstance(m.fs.unit.membrane_set, Set)
        assert isinstance(m.fs.unit.water_density, Param)
        assert isinstance(m.fs.unit.cell_pair_num, Var)
        assert isinstance(m.fs.unit.cell_width, Var)
        assert isinstance(m.fs.unit.cell_length, Var)
        assert isinstance(m.fs.unit.spacer_thickness, Var)
        assert isinstance(m.fs.unit.membrane_thickness, Var)
        assert isinstance(m.fs.unit.solute_diffusivity_membrane, Var)
        assert isinstance(m.fs.unit.ion_trans_number_membrane, Var)
        assert isinstance(m.fs.unit.water_trans_number_membrane, Var)
        assert isinstance(m.fs.unit.water_permeability_membrane, Var)
        assert isinstance(m.fs.unit.membrane_surface_resistance, Var)
        assert isinstance(m.fs.unit.current, Var)
        assert isinstance(m.fs.unit.voltage, Var)
        assert isinstance(m.fs.unit.current_utilization, Var)
        assert isinstance(m.fs.unit.power_electrical, Var)
        assert isinstance(m.fs.unit.specific_power_electrical, Var)
        assert isinstance(m.fs.unit.current_efficiency, Var)
        assert isinstance(m.fs.unit.elec_migration_flux_in, Var)
        assert isinstance(m.fs.unit.elec_migration_flux_out, Var)
        assert isinstance(m.fs.unit.nonelec_flux_in, Var)
        assert isinstance(m.fs.unit.nonelec_flux_out, Var)
        assert isinstance(m.fs.unit.eq_current_voltage_relation, Constraint)
        assert isinstance(m.fs.unit.eq_elec_migration_flux_in, Constraint)
        assert isinstance(m.fs.unit.eq_elec_migration_flux_out, Constraint)
        assert isinstance(m.fs.unit.eq_nonelec_flux_in, Constraint)
        assert isinstance(m.fs.unit.eq_nonelec_flux_out, Constraint)
        assert isinstance(m.fs.unit.eq_mass_transfer_term_diluate, Constraint)
        assert isinstance(m.fs.unit.eq_mass_transfer_term_concentrate, Constraint)
        assert isinstance(m.fs.unit.eq_power_electrical, Constraint)
        assert isinstance(m.fs.unit.eq_specific_power_electrical, Constraint)
        assert isinstance(m.fs.unit.eq_current_efficiency, Constraint)
        assert isinstance(m.fs.unit.eq_isothermal_diluate, Constraint)
        assert isinstance(m.fs.unit.eq_isothermal_concentrate, Constraint)

    @pytest.mark.unit
    def test_stats_constant_vol(self, electrodialysis_cell2):
        m = electrodialysis_cell2
        assert_units_consistent(m)
        assert degrees_of_freedom(m) == 33
        # Specify a system
        # set the operational parameters
        m.fs.unit.water_trans_number_membrane["cem"].fix(5.8)
        m.fs.unit.water_trans_number_membrane["aem"].fix(4.3)
        m.fs.unit.water_permeability_membrane["cem"].fix(2.16e-14)
        m.fs.unit.water_permeability_membrane["aem"].fix(1.75e-14)
        m.fs.unit.current.fix(8)
        m.fs.unit.electrodes_resistance.fix(0)
        m.fs.unit.cell_pair_num.fix(10)
        m.fs.unit.current_utilization.fix(1)
        m.fs.unit.spacer_thickness.fix(2.7e-4)
        m.fs.unit.membrane_surface_resistance["cem"].fix(1.89e-4)
        m.fs.unit.membrane_surface_resistance["aem"].fix(1.77e-4)
        m.fs.unit.cell_width.fix(0.1)
        m.fs.unit.cell_length.fix(0.79)
        m.fs.unit.membrane_thickness["aem"].fix(1.3e-4)
        m.fs.unit.membrane_thickness["cem"].fix(1.3e-4)
        m.fs.unit.solute_diffusivity_membrane["cem", "Na_+"].fix(1.8e-10)
        m.fs.unit.solute_diffusivity_membrane["aem", "Na_+"].fix(1.25e-10)
        m.fs.unit.solute_diffusivity_membrane["cem", "Cl_-"].fix(1.8e-10)
        m.fs.unit.solute_diffusivity_membrane["aem", "Cl_-"].fix(1.25e-10)
        m.fs.unit.ion_trans_number_membrane["cem", "Na_+"].fix(1)
        m.fs.unit.ion_trans_number_membrane["aem", "Na_+"].fix(0)
        m.fs.unit.ion_trans_number_membrane["cem", "Cl_-"].fix(0)
        m.fs.unit.ion_trans_number_membrane["aem", "Cl_-"].fix(1)

        # check ion transfer number requirements
        assert (
            sum(
                value(m.fs.unit.ion_trans_number_membrane["cem", j])
                for j in m.fs.properties.ion_set
            )
            == 1
        )
        assert (
            sum(
                value(m.fs.unit.ion_trans_number_membrane["aem", j])
                for j in m.fs.properties.ion_set
            )
            == 1
        )
        assert sum(
            value(m.fs.unit.ion_trans_number_membrane["cem", j])
            for j in m.fs.properties.cation_set
        ) == sum(
            value(m.fs.unit.ion_trans_number_membrane["aem", j])
            for j in m.fs.properties.anion_set
        )

        # set the inlet stream
        m.fs.unit.inlet_diluate.pressure.fix(101325)
        m.fs.unit.inlet_diluate.temperature.fix(298.15)
        m.fs.unit.inlet_diluate.flow_mol_phase_comp[0, "Liq", "H2O"].fix(2.40e-2)
        m.fs.unit.inlet_diluate.flow_mol_phase_comp[0, "Liq", "Na_+"].fix(7.38e-5)
        m.fs.unit.inlet_diluate.flow_mol_phase_comp[0, "Liq", "Cl_-"].fix(7.38e-5)
        m.fs.unit.inlet_concentrate.pressure.fix(101325)
        m.fs.unit.inlet_concentrate.temperature.fix(298.15)
        m.fs.unit.inlet_concentrate.flow_mol_phase_comp[0, "Liq", "H2O"].fix(2.40e-2)
        m.fs.unit.inlet_concentrate.flow_mol_phase_comp[0, "Liq", "Na_+"].fix(7.38e-5)
        m.fs.unit.inlet_concentrate.flow_mol_phase_comp[0, "Liq", "Cl_-"].fix(7.38e-5)
        assert degrees_of_freedom(m) == 0

    @pytest.mark.component
    def test_initialization_scaling(self, electrodialysis_cell2):
        m = electrodialysis_cell2
        # set default scaling for state vars
        m.fs.properties.set_default_scaling(
            "flow_mol_phase_comp", 1e2, index=("Liq", "H2O")
        )
        m.fs.properties.set_default_scaling(
            "flow_mol_phase_comp", 1e4, index=("Liq", "Na_+")
        )
        m.fs.properties.set_default_scaling(
            "flow_mol_phase_comp", 1e4, index=("Liq", "Cl_-")
        )
        iscale.calculate_scaling_factors(m.fs)
        initialization_tester(m)
        badly_scaled_var_values = {
            var.name: val for (var, val) in iscale.badly_scaled_var_generator(m)
        }
        assert not badly_scaled_var_values
        # check to make sure DOF does not change
        assert degrees_of_freedom(m) == 0

    @pytest.mark.component
    def test_solve(self, electrodialysis_cell2):
        m = electrodialysis_cell2
        # run solver and check for optimal solution
        results = solver.solve(m)
        assert_optimal_termination(results)
        badly_scaled_var_values = {
            var.name: val for (var, val) in iscale.badly_scaled_var_generator(m)
        }
        assert not badly_scaled_var_values

    @pytest.mark.component
    def test_solution(self, electrodialysis_cell2):
        m = electrodialysis_cell2

        assert value(
            m.fs.unit.outlet_diluate.flow_mol_phase_comp[0, "Liq", "H2O"]
        ) == pytest.approx(2.31e-2, rel=5e-2)
        assert value(
            m.fs.unit.outlet_diluate.flow_mol_phase_comp[0, "Liq", "Na_+"]
        ) == pytest.approx(1.46e-05, rel=5e-2)
        assert value(
            m.fs.unit.outlet_diluate.flow_mol_phase_comp[0, "Liq", "Cl_-"]
        ) == pytest.approx(1.46e-05, rel=5e-2)
        assert value(
            m.fs.unit.outlet_concentrate.flow_mol_phase_comp[0, "Liq", "H2O"]
        ) == pytest.approx(2.49e-2, rel=5e-2)
        assert value(
            m.fs.unit.outlet_concentrate.flow_mol_phase_comp[0, "Liq", "Na_+"]
        ) == pytest.approx(1.330e-4, rel=5e-3)
        assert value(
            m.fs.unit.outlet_concentrate.flow_mol_phase_comp[0, "Liq", "Cl_-"]
        ) == pytest.approx(1.330e-4, rel=5e-3)

    @pytest.mark.component
    def test_performance_contents(self, electrodialysis_cell2):
        m = electrodialysis_cell2
        perform_dict = m.fs.unit._get_performance_contents()
        assert "vars" in perform_dict
        assert value(
            perform_dict["vars"]["Electrical power consumption(Watt)"]
        ) == pytest.approx(3.5, rel=5e-1)
        assert value(
            perform_dict["vars"]["Specific electrical power consumption (kWh/m**3)"]
        ) == pytest.approx(2.33, rel=5e-2)
        assert value(
            perform_dict["vars"]["Current efficiency for deionzation"]
        ) == pytest.approx(0.71, rel=5e-2)


class TestElectrodialysis_withNeutralSPecies:
    @pytest.fixture(scope="class")
    def electrodialysis_cell3(self):
        m = ConcreteModel()
        m.fs = FlowsheetBlock(default={"dynamic": False})
        ion_dict = {
            "solute_list": ["Na_+", "Cl_-", "N"],
            "mw_data": {"H2O": 18e-3, "Na_+": 23e-3, "Cl_-": 35.5e-3, "N": 61.8e-3},
            "electrical_mobility_data": {"Na_+": 5.19e-8, "Cl_-": 7.92e-8},
            "charge": {"Na_+": 1, "Cl_-": -1},
        }
        m.fs.properties = DSPMDEParameterBlock(default=ion_dict)
        m.fs.unit = Electrodialysis0D(default={"property_package": m.fs.properties})
        m.fs.unit.config.operation_mode = "Constant_Current"
        return m

    @pytest.mark.unit
    def test_build_model(self, electrodialysis_cell3):
        m = electrodialysis_cell3

        # test configrations
        assert len(m.fs.unit.config) == 7
        assert not m.fs.unit.config.dynamic
        assert not m.fs.unit.config.has_holdup
        assert m.fs.unit.config.operation_mode == "Constant_Current"
        assert m.fs.unit.config.material_balance_type == MaterialBalanceType.useDefault
        assert (
            m.fs.unit.config.momentum_balance_type == MomentumBalanceType.pressureTotal
        )
        assert m.fs.unit.config.property_package is m.fs.properties
        assert "H2O" in m.fs.properties.component_list

        # test all essential params and vars are built
        assert isinstance(m.fs.unit.membrane_set, Set)
        assert isinstance(m.fs.unit.water_density, Param)
        assert isinstance(m.fs.unit.cell_pair_num, Var)
        assert isinstance(m.fs.unit.cell_width, Var)
        assert isinstance(m.fs.unit.cell_length, Var)
        assert isinstance(m.fs.unit.spacer_thickness, Var)
        assert isinstance(m.fs.unit.membrane_thickness, Var)
        assert isinstance(m.fs.unit.solute_diffusivity_membrane, Var)
        assert isinstance(m.fs.unit.ion_trans_number_membrane, Var)
        assert isinstance(m.fs.unit.water_trans_number_membrane, Var)
        assert isinstance(m.fs.unit.water_permeability_membrane, Var)
        assert isinstance(m.fs.unit.membrane_surface_resistance, Var)
        assert isinstance(m.fs.unit.current, Var)
        assert isinstance(m.fs.unit.voltage, Var)
        assert isinstance(m.fs.unit.current_utilization, Var)
        assert isinstance(m.fs.unit.power_electrical, Var)
        assert isinstance(m.fs.unit.specific_power_electrical, Var)
        assert isinstance(m.fs.unit.current_efficiency, Var)
        assert isinstance(m.fs.unit.elec_migration_flux_in, Var)
        assert isinstance(m.fs.unit.elec_migration_flux_out, Var)
        assert isinstance(m.fs.unit.nonelec_flux_in, Var)
        assert isinstance(m.fs.unit.nonelec_flux_out, Var)
        assert isinstance(m.fs.unit.eq_current_voltage_relation, Constraint)
        assert isinstance(m.fs.unit.eq_elec_migration_flux_in, Constraint)
        assert isinstance(m.fs.unit.eq_elec_migration_flux_out, Constraint)
        assert isinstance(m.fs.unit.eq_nonelec_flux_in, Constraint)
        assert isinstance(m.fs.unit.eq_nonelec_flux_out, Constraint)
        assert isinstance(m.fs.unit.eq_mass_transfer_term_diluate, Constraint)
        assert isinstance(m.fs.unit.eq_mass_transfer_term_concentrate, Constraint)
        assert isinstance(m.fs.unit.eq_power_electrical, Constraint)
        assert isinstance(m.fs.unit.eq_specific_power_electrical, Constraint)
        assert isinstance(m.fs.unit.eq_current_efficiency, Constraint)
        assert isinstance(m.fs.unit.eq_isothermal_diluate, Constraint)
        assert isinstance(m.fs.unit.eq_isothermal_concentrate, Constraint)

    @pytest.mark.unit
    def test_stats_constant_vol(self, electrodialysis_cell3):
        m = electrodialysis_cell3
        assert_units_consistent(m)
        assert degrees_of_freedom(m) == 37
        # Specify a system
        # set the operational parameters
        m.fs.unit.water_trans_number_membrane["cem"].fix(5.8)
        m.fs.unit.water_trans_number_membrane["aem"].fix(4.3)
        m.fs.unit.water_permeability_membrane["cem"].fix(2.16e-14)
        m.fs.unit.water_permeability_membrane["aem"].fix(1.75e-14)
        m.fs.unit.current.fix(8)
        m.fs.unit.electrodes_resistance.fix(0)
        m.fs.unit.cell_pair_num.fix(10)
        m.fs.unit.current_utilization.fix(1)
        m.fs.unit.spacer_thickness.fix(2.7e-4)
        m.fs.unit.membrane_surface_resistance["cem"].fix(1.89e-4)
        m.fs.unit.membrane_surface_resistance["aem"].fix(1.77e-4)
        m.fs.unit.cell_width.fix(0.1)
        m.fs.unit.cell_length.fix(0.79)
        m.fs.unit.membrane_thickness["aem"].fix(1.3e-4)
        m.fs.unit.membrane_thickness["cem"].fix(1.3e-4)
        m.fs.unit.solute_diffusivity_membrane["cem", "Na_+"].fix(1.8e-10)
        m.fs.unit.solute_diffusivity_membrane["aem", "Na_+"].fix(1.25e-10)
        m.fs.unit.solute_diffusivity_membrane["cem", "Cl_-"].fix(1.8e-10)
        m.fs.unit.solute_diffusivity_membrane["aem", "Cl_-"].fix(1.25e-10)
        m.fs.unit.solute_diffusivity_membrane["cem", "N"].fix(1.8e-10)
        m.fs.unit.solute_diffusivity_membrane["aem", "N"].fix(1.25e-10)
        m.fs.unit.ion_trans_number_membrane["cem", "Na_+"].fix(1)
        m.fs.unit.ion_trans_number_membrane["aem", "Na_+"].fix(0)
        m.fs.unit.ion_trans_number_membrane["cem", "Cl_-"].fix(0)
        m.fs.unit.ion_trans_number_membrane["aem", "Cl_-"].fix(1)

        # check ion transfer number requirements
        assert (
            sum(
                value(m.fs.unit.ion_trans_number_membrane["cem", j])
                for j in m.fs.properties.ion_set
            )
            == 1
        )
        assert (
            sum(
                value(m.fs.unit.ion_trans_number_membrane["aem", j])
                for j in m.fs.properties.ion_set
            )
            == 1
        )
        assert sum(
            value(m.fs.unit.ion_trans_number_membrane["cem", j])
            for j in m.fs.properties.cation_set
        ) == sum(
            value(m.fs.unit.ion_trans_number_membrane["aem", j])
            for j in m.fs.properties.anion_set
        )

        # set the inlet stream
        m.fs.unit.inlet_diluate.pressure.fix(101325)
        m.fs.unit.inlet_diluate.temperature.fix(298.15)
        m.fs.unit.inlet_diluate.flow_mol_phase_comp[0, "Liq", "H2O"].fix(2.40e-2)
        m.fs.unit.inlet_diluate.flow_mol_phase_comp[0, "Liq", "Na_+"].fix(7.38e-5)
        m.fs.unit.inlet_diluate.flow_mol_phase_comp[0, "Liq", "Cl_-"].fix(7.38e-5)
        m.fs.unit.inlet_diluate.flow_mol_phase_comp[0, "Liq", "N"].fix(7.38e-6)
        m.fs.unit.inlet_concentrate.pressure.fix(101325)
        m.fs.unit.inlet_concentrate.temperature.fix(298.15)
        m.fs.unit.inlet_concentrate.flow_mol_phase_comp[0, "Liq", "H2O"].fix(2.40e-2)
        m.fs.unit.inlet_concentrate.flow_mol_phase_comp[0, "Liq", "Na_+"].fix(7.38e-5)
        m.fs.unit.inlet_concentrate.flow_mol_phase_comp[0, "Liq", "Cl_-"].fix(7.38e-5)
        m.fs.unit.inlet_concentrate.flow_mol_phase_comp[0, "Liq", "N"].fix(7.38e-6)
        assert degrees_of_freedom(m) == 0

    @pytest.mark.component
    def test_initialization_scaling(self, electrodialysis_cell3):
        m = electrodialysis_cell3
        # set default scaling for state vars
        m.fs.properties.set_default_scaling(
            "flow_mol_phase_comp", 1e2, index=("Liq", "H2O")
        )
        m.fs.properties.set_default_scaling(
            "flow_mol_phase_comp", 1e4, index=("Liq", "Na_+")
        )
        m.fs.properties.set_default_scaling(
            "flow_mol_phase_comp", 1e4, index=("Liq", "Cl_-")
        )
        m.fs.properties.set_default_scaling(
            "flow_mol_phase_comp", 1e5, index=("Liq", "N")
        )
        iscale.calculate_scaling_factors(m.fs)
        initialization_tester(m)
        badly_scaled_var_values = {
            var.name: val for (var, val) in iscale.badly_scaled_var_generator(m)
        }
        assert not badly_scaled_var_values
        # check to make sure DOF does not change
        assert degrees_of_freedom(m) == 0

    @pytest.mark.component
    def test_solve(self, electrodialysis_cell3):
        m = electrodialysis_cell3
        # run solver and check for optimal solution
        results = solver.solve(m)
        assert_optimal_termination(results)
        badly_scaled_var_values = {
            var.name: val for (var, val) in iscale.badly_scaled_var_generator(m)
        }
        assert not badly_scaled_var_values

    @pytest.mark.component
    def test_solution(self, electrodialysis_cell3):
        m = electrodialysis_cell3

        assert value(
            m.fs.unit.outlet_diluate.flow_mol_phase_comp[0, "Liq", "H2O"]
        ) == pytest.approx(2.31e-2, rel=5e-2)
        assert value(
            m.fs.unit.outlet_diluate.flow_mol_phase_comp[0, "Liq", "Na_+"]
        ) == pytest.approx(1.50e-05, rel=5e-2)
        assert value(
            m.fs.unit.outlet_diluate.flow_mol_phase_comp[0, "Liq", "Cl_-"]
        ) == pytest.approx(1.46e-05, rel=5e-2)
        assert value(
            m.fs.unit.outlet_diluate.flow_mol_phase_comp[0, "Liq", "N"]
        ) == pytest.approx(7.67e-06, rel=5e-2)
        assert value(
            m.fs.unit.outlet_concentrate.flow_mol_phase_comp[0, "Liq", "H2O"]
        ) == pytest.approx(2.49e-2, rel=5e-2)
        assert value(
            m.fs.unit.outlet_concentrate.flow_mol_phase_comp[0, "Liq", "Na_+"]
        ) == pytest.approx(1.330e-4, rel=5e-3)
        assert value(
            m.fs.unit.outlet_concentrate.flow_mol_phase_comp[0, "Liq", "Cl_-"]
        ) == pytest.approx(1.330e-4, rel=5e-3)
        assert value(
            m.fs.unit.outlet_concentrate.flow_mol_phase_comp[0, "Liq", "N"]
        ) == pytest.approx(7.09e-06, rel=5e-2)

    @pytest.mark.component
    def test_performance_contents(self, electrodialysis_cell3):
        m = electrodialysis_cell3
        perform_dict = m.fs.unit._get_performance_contents()
        assert "vars" in perform_dict
        assert value(
            perform_dict["vars"]["Electrical power consumption(Watt)"]
        ) == pytest.approx(3.5, rel=5e-1)
        assert value(
            perform_dict["vars"]["Specific electrical power consumption (kWh/m**3)"]
        ) == pytest.approx(2.31, rel=5e-2)
        assert value(
            perform_dict["vars"]["Current efficiency for deionzation"]
        ) == pytest.approx(0.71, rel=5e-2)