# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

from typing import Sequence

import pandas as pd
import pypowsybl.network as pn

from .base import PypowsyblElements


class StaticVarCompensators(PypowsyblElements):
    """Static VAR compensators (``get_static_var_compensators``), connected to their bus and
    to the bus they regulate.

    Like generators, they may regulate the voltage of a remote bus: the ``regulated_bus_id``
    port points to it. Purely reactive devices, they are omitted from the DC configurations
    (no ``DC_*`` constants). The default features concatenate the AC problem data and the
    state solved by a first AC load flow (``p``/``q``/``i``).

    The ``standbyAutomaton`` extension (standby mode and its voltage thresholds/setpoints) is
    a satellite table indexed by compensator id: like every joined table, it has its own
    feature list parameter, naming the columns to bring in (``None`` = not joined). Joined
    columns land prefixed (``standby_automaton_b0``, ...) and are NaN (0 downstream) for
    compensators without the extension.

    :param ports: Address columns, the connection bus and the regulated bus by default.
    :param features: Feature columns of the compensator table,
        ``AC_LOAD_FLOW_INPUT_FEATURES`` + ``AC_LOAD_FLOW_OUTPUT_FEATURES`` by default.
    :param standby_automaton_features: Columns of ``get_extensions("standbyAutomaton")`` to
        join, prefixed by ``standby_automaton_`` in the graph — ``STANDBY_AUTOMATON_FEATURES``
        is the full bundle. ``None`` (default) leaves the table out.
    """

    AC_LOAD_FLOW_INPUT_FEATURES = ("b_min", "b_max", "target_v", "target_q", "regulation_mode", "regulating", "connected")
    AC_LOAD_FLOW_OUTPUT_FEATURES = ("p", "q", "i")

    STANDBY_AUTOMATON_FEATURES = (
        "standby",
        "b0",
        "low_voltage_threshold",
        "low_voltage_setpoint",
        "high_voltage_threshold",
        "high_voltage_setpoint",
    )

    def __init__(
        self,
        ports: Sequence[str] = ("bus_id", "regulated_bus_id"),
        features: Sequence[str] = AC_LOAD_FLOW_INPUT_FEATURES + AC_LOAD_FLOW_OUTPUT_FEATURES,
        *,
        standby_automaton_features: Sequence[str] | None = None,
    ):
        features = list(features)
        if standby_automaton_features is not None:
            features += [f"standby_automaton_{f}" for f in standby_automaton_features]
        super().__init__(ports=ports, features=features)
        self.standby_automaton_features = standby_automaton_features

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        df = network.get_static_var_compensators(all_attributes=True).reset_index()
        if self.standby_automaton_features is not None:
            extension = network.get_extensions("standbyAutomaton").add_prefix("standby_automaton_")
            df = df.merge(extension, how="left", left_on="id", right_index=True)
        return df
