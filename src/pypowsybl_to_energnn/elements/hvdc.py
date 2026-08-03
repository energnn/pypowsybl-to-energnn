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

    The HVDC line table carries no load flow output column (the solved state lives on the
    stations): no ``*_OUTPUT_FEATURES`` constants, and the defaults are the problem data
    alone.

    Two extensions refine the line's active power behaviour, each a satellite table indexed
    by line id with its own feature list parameter (``None`` = not joined), the joined
    columns landing prefixed and NaN (0 downstream) for lines without the extension:
    ``hvdcAngleDroopActivePowerControl`` (AC emulation: ``droop``, ``p0``, ``enabled``) and
    ``hvdcOperatorActivePowerRange`` (the operator bounds per direction).

    :param ports: Address columns, the two converter stations by default.
    :param features: Feature columns, ``AC_LOAD_FLOW_INPUT_FEATURES`` by default.
    :param hvdc_angle_droop_active_power_control_features: Columns of
        ``get_extensions("hvdcAngleDroopActivePowerControl")`` to join, prefixed by
        ``hvdc_angle_droop_active_power_control_`` in the graph —
        ``HVDC_ANGLE_DROOP_ACTIVE_POWER_CONTROL_FEATURES`` is the full bundle. ``None``
        (default) leaves the table out.
    :param hvdc_operator_active_power_range_features: Columns of
        ``get_extensions("hvdcOperatorActivePowerRange")`` to join, prefixed by
        ``hvdc_operator_active_power_range_`` in the graph —
        ``HVDC_OPERATOR_ACTIVE_POWER_RANGE_FEATURES`` is the full bundle. ``None``
        (default) leaves the table out.
    """

    AC_LOAD_FLOW_INPUT_FEATURES = ("converters_mode", "target_p", "max_p", "nominal_v", "r", "connected1", "connected2")
    DC_LOAD_FLOW_INPUT_FEATURES = ("converters_mode", "target_p", "max_p", "r", "connected1", "connected2")

    HVDC_ANGLE_DROOP_ACTIVE_POWER_CONTROL_FEATURES = ("droop", "p0", "enabled")
    HVDC_OPERATOR_ACTIVE_POWER_RANGE_FEATURES = ("opr_from_cs1_to_cs2", "opr_from_cs2_to_cs1")

    def __init__(
        self,
        ports: Sequence[str] = ("converter_station1_id", "converter_station2_id"),
        features: Sequence[str] = AC_LOAD_FLOW_INPUT_FEATURES,
        *,
        hvdc_angle_droop_active_power_control_features: Sequence[str] | None = None,
        hvdc_operator_active_power_range_features: Sequence[str] | None = None,
    ):
        features = list(features)
        if hvdc_angle_droop_active_power_control_features is not None:
            features += [f"hvdc_angle_droop_active_power_control_{f}" for f in hvdc_angle_droop_active_power_control_features]
        if hvdc_operator_active_power_range_features is not None:
            features += [f"hvdc_operator_active_power_range_{f}" for f in hvdc_operator_active_power_range_features]
        super().__init__(ports=ports, features=features)
        self.hvdc_angle_droop_active_power_control_features = hvdc_angle_droop_active_power_control_features
        self.hvdc_operator_active_power_range_features = hvdc_operator_active_power_range_features

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        df = network.get_hvdc_lines(all_attributes=True).reset_index()
        if self.hvdc_angle_droop_active_power_control_features is not None:
            extension = network.get_extensions("hvdcAngleDroopActivePowerControl")
            extension = extension.add_prefix("hvdc_angle_droop_active_power_control_")
            df = df.merge(extension, how="left", left_on="id", right_index=True)
        if self.hvdc_operator_active_power_range_features is not None:
            extension = network.get_extensions("hvdcOperatorActivePowerRange")
            extension = extension.add_prefix("hvdc_operator_active_power_range_")
            df = df.merge(extension, how="left", left_on="id", right_index=True)
        return df


class LccConverterStations(PypowsyblElements):
    """LCC converter stations (``get_lcc_converter_stations``), the line-commutated AC/DC
    interfaces of HVDC lines.

    The station bridges two address spaces: its ``id`` is the port the HVDC line attaches
    to, and its ``bus_id`` the AC bus it feeds. The default features concatenate the AC
    problem data and the state solved by a first AC load flow (``p``/``q``/``i``).

    :param ports: Address columns, the station id and its AC bus by default.
    :param features: Feature columns, ``AC_LOAD_FLOW_INPUT_FEATURES`` +
        ``AC_LOAD_FLOW_OUTPUT_FEATURES`` by default.
    """

    AC_LOAD_FLOW_INPUT_FEATURES = ("power_factor", "loss_factor", "connected")
    AC_LOAD_FLOW_OUTPUT_FEATURES = ("p", "q", "i")
    DC_LOAD_FLOW_INPUT_FEATURES = ("loss_factor", "connected")

    def __init__(
        self,
        ports: Sequence[str] = ("id", "bus_id"),
        features: Sequence[str] = AC_LOAD_FLOW_INPUT_FEATURES + AC_LOAD_FLOW_OUTPUT_FEATURES,
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
    The default features concatenate the AC problem data and the state solved by a first AC
    load flow (``p``/``q``/``i``).

    :param ports: Address columns, the station id, its AC bus and the regulated bus by
        default.
    :param features: Feature columns, ``AC_LOAD_FLOW_INPUT_FEATURES`` +
        ``AC_LOAD_FLOW_OUTPUT_FEATURES`` by default.
    """

    AC_LOAD_FLOW_INPUT_FEATURES = (
        "loss_factor",
        "min_q",
        "max_q",
        "min_q_at_target_p",
        "max_q_at_target_p",
        "target_v",
        "target_q",
        "voltage_regulator_on",
        "connected",
    )
    # min/max_q_at_p evaluate the capability curve at the solved p: an output like p itself.
    AC_LOAD_FLOW_OUTPUT_FEATURES = ("p", "q", "i", "min_q_at_p", "max_q_at_p")
    DC_LOAD_FLOW_INPUT_FEATURES = ("loss_factor", "connected")

    def __init__(
        self,
        ports: Sequence[str] = ("id", "bus_id", "regulated_bus_id"),
        features: Sequence[str] = AC_LOAD_FLOW_INPUT_FEATURES + AC_LOAD_FLOW_OUTPUT_FEATURES,
    ):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_vsc_converter_stations(all_attributes=True).reset_index()
