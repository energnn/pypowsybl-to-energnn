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


class DanglingLines(PypowsyblElements):
    """Dangling lines (``get_dangling_lines``), connected to their single bus.

    A dangling line models a line whose remote end lies outside the network, with a boundary
    injection: its problem data combines line data (``r``/``x``/``g``/``b``) and load-like
    data (``p0``/``q0``). The default features concatenate it with the state solved by a
    first AC load flow (``p``/``q``/``i``).

    :param ports: Address columns, the connection bus by default.
    :param features: Feature columns of the dangling line table,
        ``AC_LOAD_FLOW_INPUT_FEATURES`` + ``AC_LOAD_FLOW_OUTPUT_FEATURES`` by default.
    :param operational_limit_features: Selected permanent current limit columns to join —
        ``("current_limit",)``, single-sided element — see
        :func:`selected_permanent_current_limits`. ``None`` (default) leaves them out.
    """

    AC_LOAD_FLOW_INPUT_FEATURES = ("r", "x", "g", "b", "p0", "q0")
    AC_LOAD_FLOW_OUTPUT_FEATURES = ("p", "q", "i")
    DC_LOAD_FLOW_INPUT_FEATURES = ("x", "p0")
    DC_LOAD_FLOW_OUTPUT_FEATURES = ("p",)

    def __init__(
        self,
        ports: Sequence[str] = ("bus_id",),
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
        df = network.get_dangling_lines(all_attributes=True).reset_index()
        if self.operational_limit_features is not None:
            limits = selected_permanent_current_limits(network).reindex(columns=list(self.operational_limit_features))
            df = df.merge(limits, how="left", left_on="id", right_index=True)
        return df
