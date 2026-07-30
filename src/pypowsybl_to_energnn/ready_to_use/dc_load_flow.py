# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

"""Explicit configurations for the DC power flow: the active-only subsets of the AC ones.

Column by column, these are the AC configurations of :mod:`.ac_load_flow` with the
reactive- and voltage-related columns dropped (an invariant checked by the test suite).
Reactive-only devices (shunts, static VAR compensators) carry nothing in the DC problem and
are omitted entirely, as are the voltage-regulation ports (``regulated_bus_id``). The buses
carry no DC output either: ``v_mag`` is an AC quantity and phase angles are not permutation
equivariant.
"""

from pypowsybl_to_energnn.elements import TableConverter

DC_LOAD_FLOW_INPUT = {
    "buses": TableConverter("get_buses", ports=["id"]),
    "lines": TableConverter("get_lines", ports=["bus1_id", "bus2_id"], features=["x", "connected1", "connected2"]),
    "two_windings_transformers": TableConverter(
        "get_2_windings_transformers",
        ports=["bus1_id", "bus2_id"],
        features=["x", "rho", "alpha", "connected1", "connected2"],
    ),
    "generators": TableConverter(
        "get_generators",
        ports=["bus_id"],
        features=["target_p", "min_p", "max_p", "connected"],
    ),
    "loads": TableConverter("get_loads", ports=["bus_id"], features=["p0", "connected"]),
    "batteries": TableConverter("get_batteries", ports=["bus_id"], features=["max_p", "min_p", "target_p", "connected"]),
    "dangling_lines": TableConverter("get_dangling_lines", ports=["bus_id"], features=["x", "p0"]),
    "hvdc_lines": TableConverter(
        "get_hvdc_lines",
        ports=["converter_station1_id", "converter_station2_id"],
        features=["converters_mode", "target_p", "max_p", "r", "connected1", "connected2"],
    ),
    "lcc_converter_stations": TableConverter(
        "get_lcc_converter_stations", ports=["id", "bus_id"], features=["loss_factor", "connected"]
    ),
    "vsc_converter_stations": TableConverter(
        "get_vsc_converter_stations", ports=["id", "bus_id"], features=["loss_factor", "connected"]
    ),
}

DC_LOAD_FLOW_OUTPUT = {
    "lines": TableConverter("get_lines", ports=["bus1_id", "bus2_id"], features=["p1", "p2"]),
    "two_windings_transformers": TableConverter(
        "get_2_windings_transformers", ports=["bus1_id", "bus2_id"], features=["p1", "p2"]
    ),
    "generators": TableConverter("get_generators", ports=["bus_id"], features=["p"]),
    "loads": TableConverter("get_loads", ports=["bus_id"], features=["p"]),
    "batteries": TableConverter("get_batteries", ports=["bus_id"], features=["p"]),
    "dangling_lines": TableConverter("get_dangling_lines", ports=["bus_id"], features=["p"]),
}
