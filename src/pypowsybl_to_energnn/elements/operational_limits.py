# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

from typing import Sequence

import pandas as pd
import pypowsybl.network as pn

from .base import PypowsyblElements

# ``side`` values of get_operational_limits, mapped to the column each limit lands in.
_COLUMN_BY_SIDE = {
    "ONE": "current_limit1",
    "TWO": "current_limit2",
    "THREE": "current_limit3",
    "NONE": "current_limit",
    "": "current_limit",
}


def _check_sides_are_known(limits: pd.DataFrame) -> None:
    """Raise on ``side`` values outside ``_COLUMN_BY_SIDE``, instead of silently dropping
    (or mislabelling) the corresponding rows downstream."""
    unknown = limits.loc[~limits["side"].isin(_COLUMN_BY_SIDE), "side"].unique()
    if len(unknown):
        raise ValueError(f"Unmapped operational limit side(s) {sorted(unknown)}; known sides: {sorted(_COLUMN_BY_SIDE)}.")


def selected_permanent_current_limits(network: pn.Network) -> pd.DataFrame:
    """Aggregate ``get_operational_limits`` into one permanent current limit per element side.

    ``get_operational_limits`` holds one row per (element, side, limit type, acceptable
    duration, limit group): this function keeps the rows of the *selected* limit groups, of
    type ``CURRENT``, with ``acceptable_duration == -1`` (the permanent limit — temporary
    limits like ``10'`` or ``1'`` are dropped), and pivots them into one row per element with
    one column per side: ``current_limit1``/``current_limit2`` for branches (plus
    ``current_limit3`` on three-windings transformers), ``current_limit`` for single-sided
    elements (dangling lines).

    Each ``current_limit*`` column comes with a ``has_current_limit*`` companion, ``True``
    where the element carries the limit. Downstream, NaN features become 0, which would make
    "no limit" indistinguishable from a zero limit: the indicator columns lift that
    ambiguity (0 on elements without the limit, through the same NaN mechanism). pypowsybl
    encodes "no limit" as 1.8e308 on some rows; those values are kept (indicator ``True``)
    and end up clipped by the downstream float conversion.

    Elements without any such limit are simply absent from the table: merge the result with
    ``how="left"`` and their values become NaN (0 downstream).

    :param network: Network to read the limits from.
    :return: Table indexed by element id, with the ``current_limit*`` and
        ``has_current_limit*`` columns present in the network (a requested side that no
        element has must be recovered with :meth:`pandas.DataFrame.reindex`).
    """
    limits = network.get_operational_limits(all_attributes=True).reset_index()
    limits = limits[limits["selected"] & (limits["type"] == "CURRENT") & (limits["acceptable_duration"] == -1)]
    _check_sides_are_known(limits)
    limits = limits.assign(column=limits["side"].map(_COLUMN_BY_SIDE))
    # aggfunc="min": the most conservative limit, in the untypical case where several selected
    # rows survive for the same (element, side).
    pivot = limits.pivot_table(index="element_id", columns="column", values="value", aggfunc="min")
    for column in list(pivot.columns):
        pivot[f"has_{column}"] = pivot[column].notna()
    return pivot


class OperationalLimits(PypowsyblElements):
    """Operational limits (``get_operational_limits``), one hyper-edge per limit.

    The limits table has no fixed cardinality: an element carries its permanent limit plus
    any number of temporary limits, with arbitrary acceptable durations that differ across
    elements and datasets — which rules out a fixed-width feature encoding (that is why
    :func:`selected_permanent_current_limits` reduces to the permanent limit). This class
    keeps every *selected* limit instead, each as its own hyper-edge tied to the carrying
    element: the variable cardinality becomes an aggregation problem for the GNN. For the
    ``element_id`` port to actually land on the element, the carrying classes must expose
    their id as a port too — e.g. ``Lines(ports=("id", "bus1_id", "bus2_id"))``.

    ``side`` is kept as a plain categorical feature (hashed to an arbitrary deterministic
    float by the converter, like every categorical column — go through
    :class:`TableConverter` for a proper encoding when the category structure matters);
    :meth:`build_table` only normalizes the empty value onto ``NONE``, the other encoding
    of "single-sided". ``acceptable_duration`` stays numeric — the durations are ordinal
    data, and the ``-1`` of the permanent limits cannot collide with a real duration.
    Sentinel "N/A" limits are kept as their 1.8e308 value (clipped by the downstream float
    conversion). Non-selected limit groups (alternate sets) are always dropped.

    :param ports: Address columns, the carrying element by default.
    :param features: Feature columns: the limit value, its acceptable duration and the
        ``side`` category by default.
    :param limit_types: ``type`` values to keep (``CURRENT``, ``ACTIVE_POWER``,
        ``APPARENT_POWER``) — thermal limits only by default; ``None`` keeps every type.
    """

    def __init__(
        self,
        ports: Sequence[str] = ("element_id",),
        features: Sequence[str] = ("value", "acceptable_duration", "side"),
        *,
        limit_types: Sequence[str] | None = ("CURRENT",),
    ):
        super().__init__(ports=ports, features=features)
        self.limit_types = limit_types

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        limits = network.get_operational_limits(all_attributes=True).reset_index()
        limits = limits[limits["selected"]]
        if self.limit_types is not None:
            limits = limits[limits["type"].isin(self.limit_types)]
        return limits.assign(side=limits["side"].replace("", "NONE"))
