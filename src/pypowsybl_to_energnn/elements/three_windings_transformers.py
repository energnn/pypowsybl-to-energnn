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


class ThreeWindingsTransformers(PypowsyblElements):
    """Three-windings transformers (``get_3_windings_transformers``), one port per winding.

    The star model: three legs around the ``rated_u0`` star bus, each carrying its own
    pi-model (``r1``/``x1``/... with the ``rho``/``alpha`` effect of its tap changers) and
    its own solved state — the feature bundles mirror :class:`TwoWindingsTransformers` leg
    by leg. Unlike the two-windings class, the tap changer devices are not merge options
    here: a transformer can carry one device per leg (rows of the tap changer tables
    distinguished by their ``side``), which a one-row-per-id join cannot represent — use
    the :class:`RatioTapChangers`/:class:`PhaseTapChangers` classes instead.

    :param ports: Address columns, the three winding buses by default.
    :param features: Feature columns, ``AC_LOAD_FLOW_INPUT_FEATURES`` +
        ``AC_LOAD_FLOW_OUTPUT_FEATURES`` by default.
    :param operational_limit_features: Selected permanent current limit columns to join,
        among ``("current_limit1", "current_limit2", "current_limit3", "has_current_limit1",
        "has_current_limit2", "has_current_limit3")`` — the ``has_*`` indicators telling a
        missing limit apart from a zero one; see
        :func:`selected_permanent_current_limits`. ``None`` (default) leaves them out.
    """

    AC_LOAD_FLOW_INPUT_FEATURES = (
        "rated_u0",
        "r1", "x1", "g1", "b1", "rated_u1", "rated_s1", "rho1", "alpha1", "connected1",
        "r2", "x2", "g2", "b2", "rated_u2", "rated_s2", "rho2", "alpha2", "connected2",
        "r3", "x3", "g3", "b3", "rated_u3", "rated_s3", "rho3", "alpha3", "connected3",
    )  # fmt: skip
    AC_LOAD_FLOW_OUTPUT_FEATURES = ("p1", "q1", "i1", "p2", "q2", "i2", "p3", "q3", "i3")
    DC_LOAD_FLOW_INPUT_FEATURES = (
        "x1", "rho1", "alpha1", "connected1",
        "x2", "rho2", "alpha2", "connected2",
        "x3", "rho3", "alpha3", "connected3",
    )  # fmt: skip
    DC_LOAD_FLOW_OUTPUT_FEATURES = ("p1", "p2", "p3")

    def __init__(
        self,
        ports: Sequence[str] = ("bus1_id", "bus2_id", "bus3_id"),
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
        df = network.get_3_windings_transformers(all_attributes=True).reset_index()
        if self.operational_limit_features is not None:
            limits = selected_permanent_current_limits(network).reindex(columns=list(self.operational_limit_features))
            df = df.merge(limits, how="left", left_on="id", right_index=True)
        return df
