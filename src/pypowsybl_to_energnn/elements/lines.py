# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

from typing import Sequence

import pandas as pd
import pypowsybl.network as pn

from .base import PypowsyblElements
from .operational_limits import selected_permanent_current_limits


class Lines(PypowsyblElements):
    """AC lines (``get_lines``), one hyper-edge per line, connected to its two buses.

    The feature bundles of the power flow grid (solver × role) are exposed as class
    constants, additive at will. The default features concatenate the AC problem data
    (pi-model impedance and shunt admittances, connection statuses) and the state solved by a
    first AC load flow — in practice the GNN input starts from a solved state, so run a power
    flow before converting (unsolved columns are NaN, 0 downstream). Restrict to
    ``AC_LOAD_FLOW_INPUT_FEATURES`` for the pure problem data.

    :param ports: Address columns, the two extremity buses by default.
    :param features: Feature columns of the line table, ``AC_LOAD_FLOW_INPUT_FEATURES`` +
        ``AC_LOAD_FLOW_OUTPUT_FEATURES`` by default.
    :param operational_limit_features: Selected permanent current limit columns to join,
        among ``("current_limit1", "current_limit2")`` — NaN (0 downstream) for lines
        without one, see :func:`selected_permanent_current_limits`. ``None`` (default)
        leaves them out.
    """

    AC_LOAD_FLOW_INPUT_FEATURES = ("r", "x", "g1", "b1", "g2", "b2", "connected1", "connected2")
    AC_LOAD_FLOW_OUTPUT_FEATURES = ("p1", "q1", "i1", "p2", "q2", "i2")
    DC_LOAD_FLOW_INPUT_FEATURES = ("x", "connected1", "connected2")
    DC_LOAD_FLOW_OUTPUT_FEATURES = ("p1", "p2")

    def __init__(
        self,
        ports: Sequence[str] = ("bus1_id", "bus2_id"),
        features: Sequence[str] = AC_LOAD_FLOW_INPUT_FEATURES + AC_LOAD_FLOW_OUTPUT_FEATURES,
        *,
        operational_limit_features: Sequence[str] | None = None,
    ):
        features = list(features)
        if operational_limit_features is not None:
            features += list(operational_limit_features)
        super().__init__(ports=ports, features=features)
        self.operational_limit_features = operational_limit_features

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        df = network.get_lines(all_attributes=True).reset_index()
        if self.operational_limit_features is not None:
            limits = selected_permanent_current_limits(network).reindex(columns=list(self.operational_limit_features))
            df = df.merge(limits, how="left", left_on="id", right_index=True)
        return df
