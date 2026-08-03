# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

"""Explicit configurations for the AC power flow, in the bus/breaker topology.

The bus/breaker counterparts of the :mod:`ac_load_flow` assemblies — same three roles,
same feature bundles — on the nodes and edges of the finer view: :class:`BusBreakerViewBuses`
as the address space, every ``bus*_id`` port swapped for its ``bus_breaker_bus*_id`` twin
(pypowsybl exposes both on every element table, including ``regulated_bus_breaker_bus_id``,
so the remote regulation edges survive the change of view), plus the retained
:class:`Switches` as an extra class — the edges the bus view collapses, input-only. On
networks without switches the dicts still convert (the switches table is simply empty), so
they can sit on mixed datasets. For the secondary voltage control, amend with
``SecondaryVoltageControlZones(ports=("name", "pilot_bus_breaker_bus_id"))``.
"""

from pypowsybl_to_energnn.elements import (
    Batteries,
    BusBreakerViewBuses,
    DanglingLines,
    Generators,
    HvdcLines,
    LccConverterStations,
    Lines,
    Loads,
    ShuntCompensators,
    StaticVarCompensators,
    Switches,
    TwoWindingsTransformers,
    VscConverterStations,
)

BUS_BREAKER_AC_LOAD_FLOW_WARM_START_INPUT = {
    "buses": BusBreakerViewBuses(),
    "switches": Switches(),
    "lines": Lines(ports=("bus_breaker_bus1_id", "bus_breaker_bus2_id")),
    "two_windings_transformers": TwoWindingsTransformers(ports=("bus_breaker_bus1_id", "bus_breaker_bus2_id")),
    "generators": Generators(ports=("bus_breaker_bus_id", "regulated_bus_breaker_bus_id")),
    "loads": Loads(ports=("bus_breaker_bus_id",)),
    "shunts": ShuntCompensators(ports=("bus_breaker_bus_id",)),
    "static_var_compensators": StaticVarCompensators(ports=("bus_breaker_bus_id", "regulated_bus_breaker_bus_id")),
    "batteries": Batteries(ports=("bus_breaker_bus_id",)),
    "dangling_lines": DanglingLines(ports=("bus_breaker_bus_id",)),
    "hvdc_lines": HvdcLines(),
    "lcc_converter_stations": LccConverterStations(ports=("id", "bus_breaker_bus_id")),
    "vsc_converter_stations": VscConverterStations(ports=("id", "bus_breaker_bus_id", "regulated_bus_breaker_bus_id")),
}

BUS_BREAKER_AC_LOAD_FLOW_INPUT = {
    "buses": BusBreakerViewBuses(features=None),
    "switches": Switches(features=Switches.AC_LOAD_FLOW_INPUT_FEATURES),
    "lines": Lines(ports=("bus_breaker_bus1_id", "bus_breaker_bus2_id"), features=Lines.AC_LOAD_FLOW_INPUT_FEATURES),
    "two_windings_transformers": TwoWindingsTransformers(
        ports=("bus_breaker_bus1_id", "bus_breaker_bus2_id"),
        features=TwoWindingsTransformers.AC_LOAD_FLOW_INPUT_FEATURES,
    ),
    "generators": Generators(
        ports=("bus_breaker_bus_id", "regulated_bus_breaker_bus_id"), features=Generators.AC_LOAD_FLOW_INPUT_FEATURES
    ),
    "loads": Loads(ports=("bus_breaker_bus_id",), features=Loads.AC_LOAD_FLOW_INPUT_FEATURES),
    "shunts": ShuntCompensators(ports=("bus_breaker_bus_id",), features=ShuntCompensators.AC_LOAD_FLOW_INPUT_FEATURES),
    "static_var_compensators": StaticVarCompensators(
        ports=("bus_breaker_bus_id", "regulated_bus_breaker_bus_id"),
        features=StaticVarCompensators.AC_LOAD_FLOW_INPUT_FEATURES,
    ),
    "batteries": Batteries(ports=("bus_breaker_bus_id",), features=Batteries.AC_LOAD_FLOW_INPUT_FEATURES),
    "dangling_lines": DanglingLines(ports=("bus_breaker_bus_id",), features=DanglingLines.AC_LOAD_FLOW_INPUT_FEATURES),
    "hvdc_lines": HvdcLines(features=HvdcLines.AC_LOAD_FLOW_INPUT_FEATURES),
    "lcc_converter_stations": LccConverterStations(
        ports=("id", "bus_breaker_bus_id"), features=LccConverterStations.AC_LOAD_FLOW_INPUT_FEATURES
    ),
    "vsc_converter_stations": VscConverterStations(
        ports=("id", "bus_breaker_bus_id", "regulated_bus_breaker_bus_id"),
        features=VscConverterStations.AC_LOAD_FLOW_INPUT_FEATURES,
    ),
}

BUS_BREAKER_AC_LOAD_FLOW_OUTPUT = {
    "buses": BusBreakerViewBuses(features=BusBreakerViewBuses.AC_LOAD_FLOW_OUTPUT_FEATURES),
    "lines": Lines(ports=("bus_breaker_bus1_id", "bus_breaker_bus2_id"), features=Lines.AC_LOAD_FLOW_OUTPUT_FEATURES),
    "two_windings_transformers": TwoWindingsTransformers(
        ports=("bus_breaker_bus1_id", "bus_breaker_bus2_id"),
        features=TwoWindingsTransformers.AC_LOAD_FLOW_OUTPUT_FEATURES,
    ),
    "generators": Generators(ports=("bus_breaker_bus_id",), features=Generators.AC_LOAD_FLOW_OUTPUT_FEATURES),
    "loads": Loads(ports=("bus_breaker_bus_id",), features=Loads.AC_LOAD_FLOW_OUTPUT_FEATURES),
    "shunts": ShuntCompensators(ports=("bus_breaker_bus_id",), features=ShuntCompensators.AC_LOAD_FLOW_OUTPUT_FEATURES),
    "static_var_compensators": StaticVarCompensators(
        ports=("bus_breaker_bus_id",), features=StaticVarCompensators.AC_LOAD_FLOW_OUTPUT_FEATURES
    ),
    "batteries": Batteries(ports=("bus_breaker_bus_id",), features=Batteries.AC_LOAD_FLOW_OUTPUT_FEATURES),
    "dangling_lines": DanglingLines(ports=("bus_breaker_bus_id",), features=DanglingLines.AC_LOAD_FLOW_OUTPUT_FEATURES),
    "lcc_converter_stations": LccConverterStations(
        ports=("bus_breaker_bus_id",), features=LccConverterStations.AC_LOAD_FLOW_OUTPUT_FEATURES
    ),
    "vsc_converter_stations": VscConverterStations(
        ports=("bus_breaker_bus_id",), features=VscConverterStations.AC_LOAD_FLOW_OUTPUT_FEATURES
    ),
}
