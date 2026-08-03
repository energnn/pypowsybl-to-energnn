# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

"""One elements converter class per class of pypowsybl objects, one module per class.

Every class declares its default ports and features (e.g. the data of the AC power flow problem)
and its merge options (satellite tables, extensions), and implements the conversion in plain
pandas in its ``build_table`` method — start reading there. :class:`TableConverter` is the
generic escape hatch for any other table (derived features, exogenous sources, ...).
"""

from .base import PypowsyblElements, isolate_dangling_ports
from .batteries import Batteries
from .buses import Buses
from .dangling_lines import DanglingLines
from .generators import Generators
from .hvdc import HvdcLines, LccConverterStations, VscConverterStations
from .lines import Lines
from .loads import Loads
from .operational_limits import selected_permanent_current_limits
from .secondary_voltage_control import SecondaryVoltageControlUnits, SecondaryVoltageControlZones
from .shunt_compensators import ShuntCompensators
from .static_var_compensators import StaticVarCompensators
from .table import TableConverter
from .two_windings_transformers import TwoWindingsTransformers

__all__ = [
    "Batteries",
    "Buses",
    "DanglingLines",
    "Generators",
    "HvdcLines",
    "LccConverterStations",
    "Lines",
    "Loads",
    "PypowsyblElements",
    "SecondaryVoltageControlUnits",
    "SecondaryVoltageControlZones",
    "ShuntCompensators",
    "StaticVarCompensators",
    "TableConverter",
    "TwoWindingsTransformers",
    "VscConverterStations",
    "isolate_dangling_ports",
    "selected_permanent_current_limits",
]
