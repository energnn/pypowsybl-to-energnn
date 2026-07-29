# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

import pandas as pd
import pypowsybl.network as pn
from energnn.converter import ElementsConverter


class NetworkElementsConverter(ElementsConverter):
    """Base class for elements converters that read a single pypowsybl network table.

    Subclasses only need to set ``_network_getter`` to the name of the ``pypowsybl.network.Network``
    method that returns their table (e.g. ``"get_lines"``).

    The ``"id"`` column is the index of pypowsybl tables, not an attribute: it is stripped from the
    ``attributes`` requested from pypowsybl, and recovered as a regular column with ``reset_index``.

    :cvar _network_getter: Name of the ``pypowsybl.network.Network`` method returning the table.
    """

    _network_getter: str

    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        attributes = [a for a in self.attributes if a != "id"]
        return getattr(network, self._network_getter)(attributes=attributes).reset_index()


class TwoWindingsTransformersConverter(NetworkElementsConverter):
    _network_getter = "get_2_windings_transformers"


class ThreeWindingsTransformersConverter(NetworkElementsConverter):
    _network_getter = "get_3_windings_transformers"


class BatteriesConverter(NetworkElementsConverter):
    _network_getter = "get_batteries"


class BranchesConverter(NetworkElementsConverter):
    _network_getter = "get_branches"


class BusBarSectionsConverter(NetworkElementsConverter):
    _network_getter = "get_busbar_sections"


class BusesConverter(NetworkElementsConverter):
    _network_getter = "get_buses"


class BusBreakerViewBusesConverter(NetworkElementsConverter):
    _network_getter = "get_bus_breaker_view_buses"


class DanglingLinesConverter(NetworkElementsConverter):
    _network_getter = "get_dangling_lines"


class DanglingLinesGenerationConverter(NetworkElementsConverter):
    _network_getter = "get_dangling_lines_generation"


class GeneratorsConverter(NetworkElementsConverter):
    _network_getter = "get_generators"


class HVDCLinesConverter(NetworkElementsConverter):
    _network_getter = "get_hvdc_lines"


class LCCConverterStationsConverter(NetworkElementsConverter):
    _network_getter = "get_lcc_converter_stations"


class LinesConverter(NetworkElementsConverter):
    _network_getter = "get_lines"


class LoadsConverter(NetworkElementsConverter):
    _network_getter = "get_loads"


class OperationalLimitsConverter(NetworkElementsConverter):
    _network_getter = "get_operational_limits"


class PhaseTapChangersConverter(NetworkElementsConverter):
    _network_getter = "get_phase_tap_changers"


class RatioTapChangersConverter(NetworkElementsConverter):
    _network_getter = "get_ratio_tap_changers"


class ShuntCompensatorsConverter(NetworkElementsConverter):
    _network_getter = "get_shunt_compensators"


class StaticVarCompensatorsConverter(NetworkElementsConverter):
    _network_getter = "get_static_var_compensators"


class SubstationsConverter(NetworkElementsConverter):
    _network_getter = "get_substations"


class SwitchesConverter(NetworkElementsConverter):
    _network_getter = "get_switches"


class VoltageLevelsConverter(NetworkElementsConverter):
    _network_getter = "get_voltage_levels"


class VSCConverterStationsConverter(NetworkElementsConverter):
    _network_getter = "get_vsc_converter_stations"


class TieLinesConverter(NetworkElementsConverter):
    _network_getter = "get_tie_lines"


class DCNodesConverter(NetworkElementsConverter):
    _network_getter = "get_dc_nodes"


class DCLinesConverter(NetworkElementsConverter):
    _network_getter = "get_dc_lines"


class VoltageSourceConvertersConverter(NetworkElementsConverter):
    _network_getter = "get_voltage_source_converters"


class DCGroundsConverter(NetworkElementsConverter):
    _network_getter = "get_dc_grounds"


class DCBusesConverter(NetworkElementsConverter):
    _network_getter = "get_dc_buses"
