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
    point to. By default they carry no feature: in the AC problem the bus state (``v_mag``)
    is an output, requested explicitly in the output configurations. Phase angles
    (``v_angle``) are deliberately never suggested: they are not permutation equivariant.

    :param ports: Address columns, ``("id",)`` by default.
    :param features: Feature columns, none by default.
    """

    def __init__(self, ports: Sequence[str] = ("id",), features: Sequence[str] | None = None):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_buses(all_attributes=True).reset_index()
