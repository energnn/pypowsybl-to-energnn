# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

from typing import Sequence

import pandas as pd
import pypowsybl.network as pn

from .base import PypowsyblElements


class Generators(PypowsyblElements):
    """Generators (``get_generators``), connected to their bus and to the bus they regulate.

    The ``regulated_bus_id`` port points to the remotely regulated bus — an edge toward a
    possibly distant node, essential to voltage control (drop it for active-only problems).
    The feature bundles of the power flow grid (solver × role) are exposed as class
    constants, additive at will. The default features concatenate the AC problem data
    (setpoints, active and reactive limits, regulation status) and the state solved by a
    first AC load flow (``p``/``q``/``i``).

    The ``activePowerControl`` extension (droop, participation in the frequency regulation)
    is a satellite table indexed by generator id: like every joined table, it has its own
    feature list parameter, naming the columns to bring in (``None`` = not joined). Joined
    columns land prefixed (``active_power_control_droop``, ...) and are NaN (0 downstream)
    for generators without the extension.

    :param ports: Address columns, the connection bus and the regulated bus by default.
    :param features: Feature columns of the generator table,
        ``AC_LOAD_FLOW_INPUT_FEATURES`` + ``AC_LOAD_FLOW_OUTPUT_FEATURES`` by default.
    :param active_power_control_features: Columns of ``get_extensions("activePowerControl")``
        to join, prefixed by ``active_power_control_`` in the graph —
        ``ACTIVE_POWER_CONTROL_FEATURES`` is the full bundle. ``None`` (default) leaves the
        table out.
    """

    AC_LOAD_FLOW_INPUT_FEATURES = (
        "target_p",
        "min_p",
        "max_p",
        "min_q",
        "max_q",
        "min_q_at_target_p",
        "max_q_at_target_p",
        "min_q_at_p",
        "max_q_at_p",
        "rated_s",
        "target_v",
        "target_q",
        "voltage_regulator_on",
        "connected",
    )
    AC_LOAD_FLOW_OUTPUT_FEATURES = ("p", "q", "i")
    DC_LOAD_FLOW_INPUT_FEATURES = ("target_p", "min_p", "max_p", "connected")
    DC_LOAD_FLOW_OUTPUT_FEATURES = ("p",)

    ACTIVE_POWER_CONTROL_FEATURES = ("droop", "participate", "participation_factor", "max_target_p", "min_target_p")

    def __init__(
        self,
        ports: Sequence[str] = ("bus_id", "regulated_bus_id"),
        features: Sequence[str] = AC_LOAD_FLOW_INPUT_FEATURES + AC_LOAD_FLOW_OUTPUT_FEATURES,
        *,
        active_power_control_features: Sequence[str] | None = None,
    ):
        features = list(features)
        if active_power_control_features is not None:
            features += [f"active_power_control_{f}" for f in active_power_control_features]
        super().__init__(ports=ports, features=features)
        self.active_power_control_features = active_power_control_features

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        df = network.get_generators(all_attributes=True).reset_index()
        if self.active_power_control_features is not None:
            extension = network.get_extensions("activePowerControl").add_prefix("active_power_control_")
            df = df.merge(extension, how="left", left_on="id", right_index=True)
        return df
