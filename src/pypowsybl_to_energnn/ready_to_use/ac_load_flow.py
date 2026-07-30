# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

"""Explicit configurations for the AC power flow, in the bus/branch (bus view) topology.

``AC_LOAD_FLOW_INPUT`` carries the data of the AC problem (impedances, limits, setpoints);
``AC_LOAD_FLOW_OUTPUT`` the state it solves (``p``/``q``/``i`` per element, ``v_mag`` on the
buses) — output columns are NaN until a power flow has run on the network, so run one first.
The typical GNN input concatenates both: the problem warm-started by a first power flow.

These dicts are plain data meant to be copied and amended entry by entry
(see :class:`PypowsyblConverter`). ``regulated_bus_id`` ports (generators, SVCs, VSC
stations) point to the remotely regulated bus — an edge toward a possibly distant node,
essential to voltage control.
"""

from pypowsybl_to_energnn.elements import TableConverter

AC_LOAD_FLOW_INPUT = {
    "buses": TableConverter("get_buses", ports=["id"]),
    "lines": TableConverter(
        "get_lines",
        ports=["bus1_id", "bus2_id"],
        features=["r", "x", "g1", "b1", "g2", "b2", "connected1", "connected2"],
    ),
    "two_windings_transformers": TableConverter(
        "get_2_windings_transformers",
        ports=["bus1_id", "bus2_id"],
        features=["r", "x", "g", "b", "rated_u1", "rated_u2", "rated_s", "rho", "alpha", "connected1", "connected2"],
    ),
    "generators": TableConverter(
        "get_generators",
        ports=["bus_id", "regulated_bus_id"],
        features=[
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
    "loads": TableConverter("get_loads", ports=["bus_id"], features=["p0", "q0", "connected"]),
    "shunts": TableConverter(
        "get_shunt_compensators",
        ports=["bus_id"],
        features=[
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
    "static_var_compensators": TableConverter(
        "get_static_var_compensators",
        ports=["bus_id", "regulated_bus_id"],
        features=["b_min", "b_max", "target_v", "target_q", "regulation_mode", "regulating", "connected"],
    ),
    "batteries": TableConverter(
        "get_batteries",
        ports=["bus_id"],
        features=["max_p", "min_p", "min_q", "max_q", "target_p", "target_q", "connected"],
    ),
    "dangling_lines": TableConverter("get_dangling_lines", ports=["bus_id"], features=["r", "x", "g", "b", "p0", "q0"]),
    # HVDC lines attach to the AC graph through their converter stations, whose "id" is a
    # port for that purpose.
    "hvdc_lines": TableConverter(
        "get_hvdc_lines",
        ports=["converter_station1_id", "converter_station2_id"],
        features=["converters_mode", "target_p", "max_p", "nominal_v", "r", "connected1", "connected2"],
    ),
    "lcc_converter_stations": TableConverter(
        "get_lcc_converter_stations",
        ports=["id", "bus_id"],
        features=["power_factor", "loss_factor", "connected"],
    ),
    "vsc_converter_stations": TableConverter(
        "get_vsc_converter_stations",
        ports=["id", "bus_id", "regulated_bus_id"],
        features=[
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

# The addresses let predictions be matched back to the network; drop the ports when they are
# redundant, e.g. rows aligned with an input graph extracted from the same network.
# Phase angles are excluded from the bus outputs: they are not permutation equivariant.
# HVDC lines carry no output column: they are omitted entirely.
AC_LOAD_FLOW_OUTPUT = {
    "buses": TableConverter("get_buses", ports=["id"], features=["v_mag"]),
    "lines": TableConverter("get_lines", ports=["bus1_id", "bus2_id"], features=["p1", "q1", "i1", "p2", "q2", "i2"]),
    "two_windings_transformers": TableConverter(
        "get_2_windings_transformers",
        ports=["bus1_id", "bus2_id"],
        features=["p1", "q1", "i1", "p2", "q2", "i2"],
    ),
    "generators": TableConverter("get_generators", ports=["bus_id"], features=["p", "q", "i"]),
    "loads": TableConverter("get_loads", ports=["bus_id"], features=["p", "q", "i"]),
    "shunts": TableConverter("get_shunt_compensators", ports=["bus_id"], features=["p", "q", "i"]),
    "static_var_compensators": TableConverter("get_static_var_compensators", ports=["bus_id"], features=["p", "q", "i"]),
    "batteries": TableConverter("get_batteries", ports=["bus_id"], features=["p", "q", "i"]),
    "dangling_lines": TableConverter("get_dangling_lines", ports=["bus_id"], features=["p", "q", "i"]),
    "lcc_converter_stations": TableConverter("get_lcc_converter_stations", ports=["bus_id"], features=["p", "q", "i"]),
    "vsc_converter_stations": TableConverter("get_vsc_converter_stations", ports=["bus_id"], features=["p", "q", "i"]),
}
