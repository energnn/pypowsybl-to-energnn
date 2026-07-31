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


class TwoWindingsTransformers(PypowsyblElements):
    """Two-windings transformers (``get_2_windings_transformers``), connected to their two buses.

    The default features are the transformer data of the AC problem: impedance, magnetizing
    admittance, ratings, and the current transformation ratio and phase shift (``rho``,
    ``alpha`` — the effect of the tap changers on the pi-model). The tap changer devices
    themselves (positions, regulation settings) live in the satellite tables
    ``get_ratio_tap_changers``/``get_phase_tap_changers``: like every joined table, each has
    its own feature list parameter, naming the columns to bring in (``None`` = not joined).
    Joined columns land prefixed (``ratio_tap_changer_tap``, ...) so that they cannot collide
    with the transformer's own columns (both tables have a ``rho``), and are NaN (0
    downstream) for transformers without the device.

    :param ports: Address columns, the two extremity buses by default.
    :param features: Feature columns of the transformer table, the AC problem data by default.
    :param ratio_tap_changer_features: Columns of ``get_ratio_tap_changers`` to join,
        prefixed by ``ratio_tap_changer_`` in the graph — ``RATIO_TAP_CHANGER_FEATURES`` is
        a sensible full bundle. ``None`` (default) leaves the table out.
    :param phase_tap_changer_features: Columns of ``get_phase_tap_changers`` to join,
        prefixed by ``phase_tap_changer_`` in the graph — ``PHASE_TAP_CHANGER_FEATURES`` is
        a sensible full bundle. ``None`` (default) leaves the table out.
    :param operational_limit_features: Selected permanent current limit columns to join,
        among ``("current_limit1", "current_limit2")`` — see
        :func:`selected_permanent_current_limits`. ``None`` (default) leaves them out.
    """

    RATIO_TAP_CHANGER_FEATURES = ("tap", "low_tap", "high_tap", "regulating", "target_v", "target_deadband")
    PHASE_TAP_CHANGER_FEATURES = (
        "tap",
        "low_tap",
        "high_tap",
        "regulating",
        "regulation_mode",
        "regulation_value",
        "target_deadband",
    )

    def __init__(
        self,
        ports: Sequence[str] = ("bus1_id", "bus2_id"),
        features: Sequence[str] = (
            "r",
            "x",
            "g",
            "b",
            "rated_u1",
            "rated_u2",
            "rated_s",
            "rho",
            "alpha",
            "connected1",
            "connected2",
        ),
        *,
        ratio_tap_changer_features: Sequence[str] | None = None,
        phase_tap_changer_features: Sequence[str] | None = None,
        operational_limit_features: Sequence[str] | None = None,
    ):
        features = list(features)
        if ratio_tap_changer_features is not None:
            features += [f"ratio_tap_changer_{f}" for f in ratio_tap_changer_features]
        if phase_tap_changer_features is not None:
            features += [f"phase_tap_changer_{f}" for f in phase_tap_changer_features]
        if operational_limit_features is not None:
            features += list(operational_limit_features)
        super().__init__(ports=ports, features=features)
        self.ratio_tap_changer_features = ratio_tap_changer_features
        self.phase_tap_changer_features = phase_tap_changer_features
        self.operational_limit_features = operational_limit_features

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        df = network.get_2_windings_transformers(all_attributes=True).reset_index()
        if self.ratio_tap_changer_features is not None:
            tap_changers = network.get_ratio_tap_changers(all_attributes=True).add_prefix("ratio_tap_changer_")
            df = df.merge(tap_changers, how="left", left_on="id", right_index=True)
        if self.phase_tap_changer_features is not None:
            tap_changers = network.get_phase_tap_changers(all_attributes=True).add_prefix("phase_tap_changer_")
            df = df.merge(tap_changers, how="left", left_on="id", right_index=True)
        if self.operational_limit_features is not None:
            limits = selected_permanent_current_limits(network).reindex(columns=list(self.operational_limit_features))
            df = df.merge(limits, how="left", left_on="id", right_index=True)
        return df
