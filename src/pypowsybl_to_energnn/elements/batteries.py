# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

from typing import Sequence

import pandas as pd
import pypowsybl.network as pn

from .base import PypowsyblElements


class Batteries(PypowsyblElements):
    """Batteries (``get_batteries``), connected to their bus.

    The feature bundles of the power flow grid (solver × role) are exposed as class
    constants, additive at will. The default features concatenate the AC problem data
    (setpoints, active and reactive limits) and the state solved by a first AC load flow
    (``p``/``q``/``i``).

    :param ports: Address columns, the connection bus by default.
    :param features: Feature columns of the battery table, ``AC_LOAD_FLOW_INPUT_FEATURES``
        + ``AC_LOAD_FLOW_OUTPUT_FEATURES`` by default.
    """

    AC_LOAD_FLOW_INPUT_FEATURES = (
        "max_p",
        "min_p",
        "min_q",
        "max_q",
        "min_q_at_target_p",
        "max_q_at_target_p",
        "min_q_at_p",
        "max_q_at_p",
        "target_p",
        "target_q",
        "connected",
    )
    AC_LOAD_FLOW_OUTPUT_FEATURES = ("p", "q", "i")
    DC_LOAD_FLOW_INPUT_FEATURES = ("max_p", "min_p", "target_p", "connected")
    DC_LOAD_FLOW_OUTPUT_FEATURES = ("p",)

    def __init__(
        self,
        ports: Sequence[str] = ("bus_id",),
        features: Sequence[str] = AC_LOAD_FLOW_INPUT_FEATURES + AC_LOAD_FLOW_OUTPUT_FEATURES,
    ):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_batteries(all_attributes=True).reset_index()
