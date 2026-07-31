# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

"""The HVDC subsystem: HVDC lines and their LCC/VSC converter stations.

An HVDC line does not touch any AC bus directly: it runs between two converter stations,
which are the elements connected to the AC grid. The line therefore uses its station ids as
ports, and each station exposes its own ``id`` as a port so that the line finds it — dropping
the stations from a configuration disconnects the HVDC lines from the graph.
"""

from typing import Sequence

import pandas as pd
import pypowsybl.network as pn

from .base import PypowsyblElements


class HvdcLines(PypowsyblElements):
    """HVDC lines (``get_hvdc_lines``), connected to their two converter stations.

    :param ports: Address columns, the two converter stations by default.
    :param features: Feature columns, the AC problem data by default.
    """

    def __init__(
        self,
        ports: Sequence[str] = ("converter_station1_id", "converter_station2_id"),
        features: Sequence[str] = ("converters_mode", "target_p", "max_p", "nominal_v", "r", "connected1", "connected2"),
    ):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_hvdc_lines(all_attributes=True).reset_index()


class LccConverterStations(PypowsyblElements):
    """LCC converter stations (``get_lcc_converter_stations``), the line-commutated AC/DC
    interfaces of HVDC lines.

    The station bridges two address spaces: its ``id`` is the port the HVDC line attaches
    to, and its ``bus_id`` the AC bus it feeds.

    :param ports: Address columns, the station id and its AC bus by default.
    :param features: Feature columns, the AC problem data by default.
    """

    def __init__(
        self,
        ports: Sequence[str] = ("id", "bus_id"),
        features: Sequence[str] = ("power_factor", "loss_factor", "connected"),
    ):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_lcc_converter_stations(all_attributes=True).reset_index()


class VscConverterStations(PypowsyblElements):
    """VSC converter stations (``get_vsc_converter_stations``), the voltage-source AC/DC
    interfaces of HVDC lines.

    Like generators, a VSC station can regulate the voltage of a (possibly remote) bus: the
    ``regulated_bus_id`` port points to it. The station bridges two address spaces: its
    ``id`` is the port the HVDC line attaches to, and its ``bus_id`` the AC bus it feeds.

    :param ports: Address columns, the station id, its AC bus and the regulated bus by
        default.
    :param features: Feature columns, the AC problem data by default.
    """

    def __init__(
        self,
        ports: Sequence[str] = ("id", "bus_id", "regulated_bus_id"),
        features: Sequence[str] = (
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
        ),
    ):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_vsc_converter_stations(all_attributes=True).reset_index()
