# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

from pypowsybl_to_energnn.converter import Converter
from pypowsybl_to_energnn.elements import (
    BatteriesConverter,
    BusBarSectionsConverter,
    BusesConverter,
    ControllableLinesConverter,
    ControllableSecondaryVoltageControlZonesConverter,
    ControllableShuntsConverter,
    DanglingLinesConverter,
    GeneratorsConverter,
    HVDCLinesConverter,
    HVDCOperatorActivePowerRangeConverter,
    LCCConverterStationsConverter,
    LinesConverter,
    LoadsConverter,
    OperationalLimitsConverter,
    SecondaryVoltageControlUnitsConverter,
    SecondaryVoltageControlZonesConverter,
    ShuntCompensatorsConverter,
    StaticVarCompensatorsConverter,
    SubstationsConverter,
    TwoWindingsTransformersConverter,
    VSCConverterStationsConverter,
    VoltageLevelsConverter,
)


class TertiaryVoltageControlInputConverter(Converter):

    elements_converter_dict = {
        "two_windings_transformers": TwoWindingsTransformersConverter(
            ["id", "bus1_id", "bus2_id"],
            [
                "r",
                "x",
                "g",
                "b",
                "rated_u1",
                "rated_u2",
                "rated_s",
                "p1",
                "q1",
                "i1",
                "p2",
                "q2",
                "i2",
                "connected1",
                "connected2",
                "fictitious",
                "rho",
                "alpha",
                "r_at_current_tap",
                "x_at_current_tap",
                "g_at_current_tap",
                "b_at_current_tap",
            ],
        ),
        "batteries": BatteriesConverter(
            ["bus_id"],
            ["max_p", "min_p", "min_q", "max_q", "target_p", "target_q", "connected", "p", "q", "i"],
        ),
        "busbar_sections": BusBarSectionsConverter(["id", "bus_id"], ["v", "connected"]),
        "buses": BusesConverter(
            ["id", "voltage_level_id"], ["v_mag", "connected_component", "synchronous_component", "fictitious"]
        ),
        "dangling_lines": DanglingLinesConverter(["bus_id"], ["r", "x", "g", "b", "p0", "q0", "p", "q", "i"]),
        "generators": GeneratorsConverter(
            ["id", "bus_id", "regulated_bus_id"],
            [
                "target_p",
                "min_p",
                "max_p",
                "min_q",
                "max_q",
                "rated_s",
                "target_v",
                "target_q",
                "voltage_regulator_on",
                "connected",
                "p",
                "q",
                "i",
            ],
        ),
        "hvdc_lines": HVDCLinesConverter(
            ["id", "converter_station1_id", "converter_station2_id"],
            ["converters_mode", "target_p", "max_p", "nominal_v", "r", "connected1", "connected2"],
        ),
        "hvdc_operator_active_power_range": HVDCOperatorActivePowerRangeConverter(
            ["id"], ["opr_from_cs1_to_cs2", "opr_from_cs2_to_cs1"]
        ),
        "lcc_converter_stations": LCCConverterStationsConverter(
            ["id", "bus_id"], ["power_factor", "loss_factor", "connected", "p", "q", "i"]
        ),
        "lines": LinesConverter(
            ["id", "bus1_id", "bus2_id"],
            ["r", "x", "g1", "b1", "g2", "b2", "connected1", "connected2", "p1", "p2", "q1", "q2", "i1", "i2"],
        ),
        "loads": LoadsConverter(["bus_id"], ["p0", "q0", "connected", "p", "q", "i"]),
        "secondary_voltage_control_units": SecondaryVoltageControlUnitsConverter(["unit_id", "zone_name"], ["participate"]),
        "secondary_voltage_control_zones": SecondaryVoltageControlZonesConverter(["name", "bus_id"], ["target_v"]),
        "shunts": ShuntCompensatorsConverter(
            ["id", "bus_id"],
            [
                "p",
                "q",
                "i",
                "g",
                "b",
                "p",
                "max_section_count",
                "section_count",
                "voltage_regulation_on",
                "target_v",
                "target_deadband",
                "connected",
            ],
        ),
        "static_var_compensators": StaticVarCompensatorsConverter(
            ["bus_id", "regulated_bus_id"],
            ["b_min", "b_max", "target_v", "target_q", "regulation_mode", "regulating", "connected"],
        ),
        "substations": SubstationsConverter(["id"], ["country"]),
        "voltage_levels": VoltageLevelsConverter(
            ["substation_id", "id"], ["nominal_v", "high_voltage_limit", "low_voltage_limit"]
        ),
        "vsc_converter_stations": VSCConverterStationsConverter(
            ["id", "bus_id", "regulated_bus_id"],
            [
                "p",
                "q",
                "i",
                "loss_factor",
                "min_q",
                "max_q",
                "min_q_at_target_p",
                "max_q_at_target_p",
                "min_q_at_p",
                "max_q_at_p",
                "target_v",
                "target_q",
                "voltage_regulator_on",
                "connected",
            ],
        ),
        "operational_limits": OperationalLimitsConverter(
            ["element_id"], ["side", "acceptable_duration", "element_type", "name", "value"]
        ),
        "controllable_shunts": ControllableShuntsConverter(["shunt_id"], None),
        "controllable_lines": ControllableLinesConverter(["line_id"], None),
        "controllable_secondary_voltage_control_zones": ControllableSecondaryVoltageControlZonesConverter(["zone_id"], None),
    }
