# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

"""Explicit configurations for the DC power flow: the active-only subsets of the AC ones.

Column by column, the ``DC_*`` feature bundles are the ``AC_*`` ones with the reactive- and
voltage-related columns dropped (an invariant checked by the test suite, on the class
constants). Reactive-only devices (shunts, static VAR compensators) carry nothing in the DC
problem and are omitted entirely, as are the voltage-regulation ports (``regulated_bus_id``).
The buses carry no DC feature either: ``v_mag`` is an AC quantity and phase angles are not
permutation equivariant.
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
    ThreeWindingsTransformers,
    TwoWindingsTransformers,
    VscConverterStations,
)

DC_LOAD_FLOW_INPUT = {
    "buses": Buses(features=None),
    "lines": Lines(features=Lines.DC_LOAD_FLOW_INPUT_FEATURES),
    "two_windings_transformers": TwoWindingsTransformers(features=TwoWindingsTransformers.DC_LOAD_FLOW_INPUT_FEATURES),
    "three_windings_transformers": ThreeWindingsTransformers(features=ThreeWindingsTransformers.DC_LOAD_FLOW_INPUT_FEATURES),
    "generators": Generators(ports=("bus_id",), features=Generators.DC_LOAD_FLOW_INPUT_FEATURES),
    "loads": Loads(features=Loads.DC_LOAD_FLOW_INPUT_FEATURES),
    "batteries": Batteries(features=Batteries.DC_LOAD_FLOW_INPUT_FEATURES),
    "dangling_lines": DanglingLines(features=DanglingLines.DC_LOAD_FLOW_INPUT_FEATURES),
    "hvdc_lines": HvdcLines(features=HvdcLines.DC_LOAD_FLOW_INPUT_FEATURES),
    "lcc_converter_stations": LccConverterStations(features=LccConverterStations.DC_LOAD_FLOW_INPUT_FEATURES),
    "vsc_converter_stations": VscConverterStations(
        ports=("id", "bus_id"), features=VscConverterStations.DC_LOAD_FLOW_INPUT_FEATURES
    ),
}

DC_LOAD_FLOW_OUTPUT = {
    "lines": Lines(features=Lines.DC_LOAD_FLOW_OUTPUT_FEATURES),
    "two_windings_transformers": TwoWindingsTransformers(features=TwoWindingsTransformers.DC_LOAD_FLOW_OUTPUT_FEATURES),
    "three_windings_transformers": ThreeWindingsTransformers(features=ThreeWindingsTransformers.DC_LOAD_FLOW_OUTPUT_FEATURES),
    "generators": Generators(ports=("bus_id",), features=Generators.DC_LOAD_FLOW_OUTPUT_FEATURES),
    "loads": Loads(features=Loads.DC_LOAD_FLOW_OUTPUT_FEATURES),
    "batteries": Batteries(features=Batteries.DC_LOAD_FLOW_OUTPUT_FEATURES),
    "dangling_lines": DanglingLines(features=DanglingLines.DC_LOAD_FLOW_OUTPUT_FEATURES),
}
