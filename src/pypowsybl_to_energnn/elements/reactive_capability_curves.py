# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

from typing import Sequence

import pandas as pd
import pypowsybl.network as pn

from .base import PypowsyblElements


class ReactiveCapabilityCurvePoints(PypowsyblElements):
    """Reactive capability curve points (``get_reactive_capability_curve_points``).

    The full reactive diagram of the machines that carry a curve (generators, batteries,
    VSC converter stations): one hyper-edge per curve point, holding its coordinates
    (``p``, ``min_q``, ``max_q``). The number of points per machine is not bounded, so the
    curve fits the graph structure rather than a fixed-width feature vector — the
    ``min_q_at_p``/``min_q_at_target_p``/... columns of the machine tables are the flat
    counterparts, the curve already evaluated at one operating point. For the ``id`` port
    to land on the machine, the machine classes must expose their id as a port too — e.g.
    ``Generators(ports=("id", "bus_id", "regulated_bus_id"))``. Machines with plain min/max
    limits carry no curve, hence no hyper-edge.

    :param ports: Address columns, the carrying machine by default.
    :param features: Feature columns, the point coordinates by default.
    """

    def __init__(self, ports: Sequence[str] = ("id",), features: Sequence[str] = ("p", "min_q", "max_q")):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_reactive_capability_curve_points().reset_index()
