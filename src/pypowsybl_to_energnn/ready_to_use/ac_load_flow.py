# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

"""Explicit configurations for the AC power flow, in the bus/branch (bus view) topology.

Three assemblies of the per-class feature bundles (open a class — :class:`Lines`,
:class:`Generators`, ... — to read the column lists):

- ``AC_LOAD_FLOW_WARM_START_INPUT`` — every class with its defaults: the problem data
  *and* the state solved by a first AC load flow, which is the realistic GNN input (run a
  power flow before converting; unsolved columns are NaN, 0 downstream);
- ``AC_LOAD_FLOW_INPUT`` — the problem data alone (impedances, limits, setpoints), for the
  simulator-proxy setting;
- ``AC_LOAD_FLOW_OUTPUT`` — the solved state alone (``p``/``q``/``i`` per element,
  ``v_mag`` on the buses), the typical prediction target.

These dicts are plain data meant to be copied and amended entry by entry
(see :class:`PypowsyblConverter`). ``regulated_bus_id`` ports (generators, SVCs, VSC
stations) point to the remotely regulated bus — an edge toward a possibly distant node,
essential to voltage control. Output notes: the ports let predictions be matched back to
the network (drop them when redundant with an input graph extracted from the same network);
phase angles are excluded from the bus outputs (not permutation equivariant); HVDC lines
carry no output column and are omitted entirely.
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

AC_LOAD_FLOW_WARM_START_INPUT = {
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

AC_LOAD_FLOW_INPUT = {
    "buses": Buses(features=None),
    "lines": Lines(features=Lines.AC_LOAD_FLOW_INPUT_FEATURES),
    "two_windings_transformers": TwoWindingsTransformers(features=TwoWindingsTransformers.AC_LOAD_FLOW_INPUT_FEATURES),
    "generators": Generators(features=Generators.AC_LOAD_FLOW_INPUT_FEATURES),
    "loads": Loads(features=Loads.AC_LOAD_FLOW_INPUT_FEATURES),
    "shunts": ShuntCompensators(features=ShuntCompensators.AC_LOAD_FLOW_INPUT_FEATURES),
    "static_var_compensators": StaticVarCompensators(features=StaticVarCompensators.AC_LOAD_FLOW_INPUT_FEATURES),
    "batteries": Batteries(features=Batteries.AC_LOAD_FLOW_INPUT_FEATURES),
    "dangling_lines": DanglingLines(features=DanglingLines.AC_LOAD_FLOW_INPUT_FEATURES),
    "hvdc_lines": HvdcLines(features=HvdcLines.AC_LOAD_FLOW_INPUT_FEATURES),
    "lcc_converter_stations": LccConverterStations(features=LccConverterStations.AC_LOAD_FLOW_INPUT_FEATURES),
    "vsc_converter_stations": VscConverterStations(features=VscConverterStations.AC_LOAD_FLOW_INPUT_FEATURES),
}

AC_LOAD_FLOW_OUTPUT = {
    "buses": Buses(features=Buses.AC_LOAD_FLOW_OUTPUT_FEATURES),
    "lines": Lines(features=Lines.AC_LOAD_FLOW_OUTPUT_FEATURES),
    "two_windings_transformers": TwoWindingsTransformers(features=TwoWindingsTransformers.AC_LOAD_FLOW_OUTPUT_FEATURES),
    "generators": Generators(ports=("bus_id",), features=Generators.AC_LOAD_FLOW_OUTPUT_FEATURES),
    "loads": Loads(features=Loads.AC_LOAD_FLOW_OUTPUT_FEATURES),
    "shunts": ShuntCompensators(features=ShuntCompensators.AC_LOAD_FLOW_OUTPUT_FEATURES),
    "static_var_compensators": StaticVarCompensators(
        ports=("bus_id",), features=StaticVarCompensators.AC_LOAD_FLOW_OUTPUT_FEATURES
    ),
    "batteries": Batteries(features=Batteries.AC_LOAD_FLOW_OUTPUT_FEATURES),
    "dangling_lines": DanglingLines(features=DanglingLines.AC_LOAD_FLOW_OUTPUT_FEATURES),
    "lcc_converter_stations": LccConverterStations(
        ports=("bus_id",), features=LccConverterStations.AC_LOAD_FLOW_OUTPUT_FEATURES
    ),
    "vsc_converter_stations": VscConverterStations(
        ports=("bus_id",), features=VscConverterStations.AC_LOAD_FLOW_OUTPUT_FEATURES
    ),
}
