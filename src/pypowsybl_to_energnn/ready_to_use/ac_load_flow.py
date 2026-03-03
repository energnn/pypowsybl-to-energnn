# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

from pypowsybl_to_energnn.converter import Converter
from pypowsybl_to_energnn.elements import (
    BatteriesConverter,
    BusesConverter,
    DanglingLinesConverter,
    GeneratorsConverter,
    HVDCLinesConverter,
    LCCConverterStationsConverter,
    LinesConverter,
    LoadsConverter,
    ShuntCompensatorsConverter,
    StaticVarCompensatorsConverter,
    VSCConverterStationsConverter,
)


class ACLoadFlowInputConverter(Converter):

    elements_converter_dict = {
        "batteries": BatteriesConverter(
            ["bus_id"],
            ["max_p", "min_p", "min_q", "max_q", "target_p", "target_q", "connected"],
        ),
        "buses": BusesConverter(["id"], None),
        "dangling_lines": DanglingLinesConverter(["bus_id"], ["r", "x", "g", "b", "p0", "q0"]),
        "generators": GeneratorsConverter(
            ["bus_id", "regulated_bus_id"],
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
            ],
        ),
        "hvdc_lines": HVDCLinesConverter(
            ["converter_station1_id", "converter_station2_id"],
            ["converters_mode", "target_p", "max_p", "nominal_v", "r", "connected1", "connected2"],
        ),
        "lcc_converter_stations": LCCConverterStationsConverter(
            ["id", "bus_id"], ["power_factor", "loss_factor", "connected"]
        ),
        "lines": LinesConverter(["bus1_id", "bus2_id"], ["r", "x", "g1", "b1", "g2", "b2", "connected1", "connected2"]),
        "loads": LoadsConverter(["bus_id"], ["p0", "q0", "connected"]),
        "shunts": ShuntCompensatorsConverter(
            ["bus_id"],
            [
                "g",
                "b",
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
        "vsc_converter_stations": VSCConverterStationsConverter(
            ["id", "bus_id", "regulated_bus_id"],
            [
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
    }


class ACLoadFlowOutputConverter(Converter):

    elements_converter_dict = {
        "batteries": BatteriesConverter(None, ["p", "q", "i"]),
        "buses": BusesConverter(None, ["v_mag"]),  # Phase angle is not permutation equivariant
        "dangling_lines": DanglingLinesConverter(None, ["p", "q", "i"]),
        "generators": GeneratorsConverter(None, ["p", "q", "i"]),
        # Nothing for HVDC lines.
        "lcc_converter_stations": LCCConverterStationsConverter(None, ["p", "q", "i"]),
        "lines": LinesConverter(None, ["p1", "q1", "i1", "p2", "q2", "i2"]),
        "loads": LoadsConverter(None, ["p", "q", "i"]),
        "shunts": ShuntCompensatorsConverter(None, ["p", "q", "i"]),
        "static_var_compensators": StaticVarCompensatorsConverter(None, ["p", "q", "i"]),
        "vsc_converter_stations": VSCConverterStationsConverter(None, ["p", "q", "i"]),
    }
