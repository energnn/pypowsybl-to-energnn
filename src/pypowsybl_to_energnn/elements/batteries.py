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

    The default features are the battery data of the AC problem: setpoints and active and
    reactive limits. The solved state (``p``/``q``/``i``) is requested explicitly in the
    output configurations.

    :param ports: Address columns, the connection bus by default.
    :param features: Feature columns, the AC problem data by default.
    """

    def __init__(
        self,
        ports: Sequence[str] = ("bus_id",),
        features: Sequence[str] = ("max_p", "min_p", "min_q", "max_q", "target_p", "target_q", "connected"),
    ):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_batteries(all_attributes=True).reset_index()
