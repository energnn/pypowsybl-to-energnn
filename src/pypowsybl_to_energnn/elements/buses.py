# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

from typing import Sequence

import pandas as pd
import pypowsybl.network as pn

from .base import PypowsyblElements


class Buses(PypowsyblElements):
    """Buses of the bus view (``get_buses``), the nodes every other element attaches to.

    Their ``id`` is the address the ``bus_id``/``bus1_id``/... ports of the other classes
    point to. The buses carry no problem data (``AC_LOAD_FLOW_INPUT_FEATURES`` is empty):
    their default feature is the voltage magnitude solved by a first AC load flow. Phase
    angles (``v_angle``) are deliberately never suggested: they are not permutation
    equivariant.

    :param ports: Address columns, ``("id",)`` by default.
    :param features: Feature columns, ``AC_LOAD_FLOW_OUTPUT_FEATURES`` by default (pass
        ``None`` for structural buses without features).
    """

    AC_LOAD_FLOW_INPUT_FEATURES: tuple[str, ...] = ()
    AC_LOAD_FLOW_OUTPUT_FEATURES = ("v_mag",)

    def __init__(
        self,
        ports: Sequence[str] = ("id",),
        features: Sequence[str] | None = AC_LOAD_FLOW_INPUT_FEATURES + AC_LOAD_FLOW_OUTPUT_FEATURES,
    ):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_buses(all_attributes=True).reset_index()
