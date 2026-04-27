# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

from abc import ABC, abstractmethod

import pandas as pd
import pypowsybl.network as pn
from energnn.graph import HyperEdgeSetStructure


class ElementsConverter(ABC):
    """Abstract base class for elements converters.

    :param address_list: List of address to extract from the network.
    :param feature_list: List of features to extract from the network.
    """

    def __init__(self, address_list: list[str] | None, feature_list: list[str] | None):
        self.address_list = address_list
        self.feature_list = feature_list

        self.attributes = []
        if self.address_list is not None:
            self.attributes.extend([s for s in self.address_list if s != "id"])
        if self.feature_list is not None:
            self.attributes.extend(self.feature_list)

    def __call__(self, *, network: pn.Network, **kwargs) -> tuple[pd.DataFrame, pd.DataFrame]:
        df = self._get_table(network=network, **kwargs)

        if self.address_list is not None:
            df_address = df[self.address_list]
        else:
            df_address = None

        if self.feature_list is not None:
            df_feature = df[self.feature_list]
        else:
            df_feature = None

        return df_address, df_feature

    @abstractmethod
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        """Should return a pandas DataFrame containing addresses and features."""
        raise NotImplementedError

    def get_structure(self) -> HyperEdgeSetStructure:
        """Get the edge structure of the element, useful for building an EnerGNN model."""
        return HyperEdgeSetStructure(port_list=self.address_list, feature_list=self.feature_list)


class TwoWindingsTransformersConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_2_windings_transformers(attributes=self.attributes).reset_index()


class ThreeWindingsTransformersConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_3_windings_transformers(attributes=self.attributes).reset_index()


class BatteriesConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_batteries(attributes=self.attributes).reset_index()


class BranchesConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_branches(attributes=self.attributes).reset_index()


class BusBarSectionsConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_busbar_sections(attributes=self.attributes).reset_index()


class BusesConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_buses(attributes=self.attributes).reset_index()


class BusBreakerViewBusesConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_bus_breaker_view_buses(attributes=self.attributes).reset_index()


class DanglingLinesConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_dangling_lines(attributes=self.attributes).reset_index()


class DanglingLinesGenerationConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_dangling_lines_generation(attributes=self.attributes).reset_index()


class GeneratorsConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_generators(attributes=self.attributes).reset_index()


class HVDCLinesConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_hvdc_lines(attributes=self.attributes).reset_index()


class HVDCOperatorActivePowerRangeConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_extensions("hvdcOperatorActivePowerRange")


class LCCConverterStationsConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_lcc_converter_stations(attributes=self.attributes).reset_index()


class LinesConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_lines(attributes=self.attributes).reset_index()


class LoadsConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_loads(attributes=self.attributes).reset_index()


class OperationalLimitsConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_operational_limits(attributes=self.attributes).reset_index()


# class PermanentLimitsConverter(ElementsConverter):
#     def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
#         limits = network.get_operational_limits(attributes=self.attributes).reset_index()
#         limits = limits[limits["name"] == "permanent_limit"]
#         return limits.reset_index()


class PhaseTapChangersConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_phase_tap_changers(attributes=self.attributes).reset_index()


class RatioTapChangersConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_ratio_tap_changers(attributes=self.attributes).reset_index()


class SecondaryVoltageControlUnitsConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_extensions("secondaryVoltageControl", "units")


class SecondaryVoltageControlZonesConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_extensions("secondaryVoltageControl", "zones")


class ShuntCompensatorsConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_shunt_compensators(attributes=self.attributes).reset_index()


class StaticVarCompensatorsConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_static_var_compensators(attributes=self.attributes).reset_index()


class StandByAutomatonConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_extensions("standbyAutomaton")


class SubstationsConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_substations(attributes=self.attributes).reset_index()


class SwitchesConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_switches(attributes=self.attributes).reset_index()


class VoltageLevelsConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_voltage_levels(attributes=self.attributes).reset_index()


class VSCConverterStationsConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_vsc_converter_stations(attributes=self.attributes).reset_index()


class TieLinesConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_tie_lines(attributes=self.attributes).reset_index()


class DCNodesConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_dc_nodes(attributes=self.attributes).reset_index()


class DCLinesConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_dc_lines(attributes=self.attributes).reset_index()


class VoltageSourceConvertersConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_voltage_source_converters(attributes=self.attributes).reset_index()


class DCGroundsConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_dc_grounds(attributes=self.attributes).reset_index()


class DCBusesConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_dc_buses(attributes=self.attributes).reset_index()


class ControllableLinesConverter(ElementsConverter):
    def _get_table(self, *, controllable_lines: list[str], **kwargs) -> pd.DataFrame:
        return pd.DataFrame(controllable_lines, columns=["line_id"])


class ControllableShuntsConverter(ElementsConverter):
    def _get_table(self, *, controllable_shunts: list[str], **kwargs) -> pd.DataFrame:
        return pd.DataFrame(controllable_shunts, columns=["shunt_id"])


class ControllableSecondaryVoltageControlZonesConverter(ElementsConverter):
    def _get_table(self, *, controllable_zones: list[str], **kwargs) -> pd.DataFrame:
        return pd.DataFrame(controllable_zones, columns=["zone_id"])
