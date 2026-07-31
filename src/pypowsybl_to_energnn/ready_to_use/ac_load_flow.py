# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

"""Explicit configurations for the AC power flow, in the bus/branch (bus view) topology.

``AC_LOAD_FLOW_INPUT`` carries the data of the AC problem: it is simply every element class
with its defaults, since the class defaults *are* the AC problem data — open a class
(:class:`Lines`, :class:`Generators`, ...) to read its column lists and options.
``AC_LOAD_FLOW_OUTPUT`` carries the state the problem solves (``p``/``q``/``i`` per element,
``v_mag`` on the buses) — output columns are NaN until a power flow has run on the network,
so run one first. The typical GNN input concatenates both: the problem warm-started by a
first power flow.

These dicts are plain data meant to be copied and amended entry by entry
(see :class:`PypowsyblConverter`). Output notes: the ports let predictions be matched back
to the network (drop them when redundant with an input graph extracted from the same
network); phase angles are excluded from the bus outputs (not permutation equivariant); HVDC
lines carry no output column and are omitted entirely.
"""

from pypowsybl_to_energnn.elements import (
    Batteries,
    Buses,
    DanglingLines,
    Generators,
    HvdcLines,
    LccConverterStations,
    Lines,
    Loads,
    ShuntCompensators,
    StaticVarCompensators,
    TwoWindingsTransformers,
    VscConverterStations,
)

AC_LOAD_FLOW_INPUT = {
    "buses": Buses(),
    "lines": Lines(),
    "two_windings_transformers": TwoWindingsTransformers(),
    "generators": Generators(),
    "loads": Loads(),
    "shunts": ShuntCompensators(),
    "static_var_compensators": StaticVarCompensators(),
    "batteries": Batteries(),
    "dangling_lines": DanglingLines(),
    "hvdc_lines": HvdcLines(),
    "lcc_converter_stations": LccConverterStations(),
    "vsc_converter_stations": VscConverterStations(),
}

AC_LOAD_FLOW_OUTPUT = {
    "buses": Buses(features=("v_mag",)),
    "lines": Lines(features=("p1", "q1", "i1", "p2", "q2", "i2")),
    "two_windings_transformers": TwoWindingsTransformers(features=("p1", "q1", "i1", "p2", "q2", "i2")),
    "generators": Generators(ports=("bus_id",), features=("p", "q", "i")),
    "loads": Loads(features=("p", "q", "i")),
    "shunts": ShuntCompensators(features=("p", "q", "i")),
    "static_var_compensators": StaticVarCompensators(ports=("bus_id",), features=("p", "q", "i")),
    "batteries": Batteries(features=("p", "q", "i")),
    "dangling_lines": DanglingLines(features=("p", "q", "i")),
    "lcc_converter_stations": LccConverterStations(ports=("bus_id",), features=("p", "q", "i")),
    "vsc_converter_stations": VscConverterStations(ports=("bus_id",), features=("p", "q", "i")),
}
