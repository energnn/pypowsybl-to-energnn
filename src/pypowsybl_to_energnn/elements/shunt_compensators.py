# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

from typing import Sequence

import pandas as pd
import pypowsybl.network as pn

from .base import PypowsyblElements


class ShuntCompensators(PypowsyblElements):
    """Shunt compensators (``get_shunt_compensators``), connected to their bus.

    The default features are the shunt data of the AC problem: the admittance of the current
    section, the section counts, and the voltage regulation settings. Purely reactive
    devices, they carry nothing in the DC problem and are omitted from the DC configurations.

    :param ports: Address columns, the connection bus by default.
    :param features: Feature columns, the AC problem data by default.
    """

    def __init__(
        self,
        ports: Sequence[str] = ("bus_id",),
        features: Sequence[str] = (
            "g",
            "b",
            "max_section_count",
            "section_count",
            "voltage_regulation_on",
            "target_v",
            "target_deadband",
            "connected",
        ),
    ):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_shunt_compensators(all_attributes=True).reset_index()
