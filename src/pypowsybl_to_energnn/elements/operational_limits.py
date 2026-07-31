# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

import pandas as pd
import pypowsybl.network as pn

# ``side`` values of get_operational_limits, mapped to the column each limit lands in.
_COLUMN_BY_SIDE = {"ONE": "current_limit1", "TWO": "current_limit2", "NONE": "current_limit", "": "current_limit"}


def selected_permanent_current_limits(network: pn.Network) -> pd.DataFrame:
    """Aggregate ``get_operational_limits`` into one permanent current limit per element side.

    ``get_operational_limits`` holds one row per (element, side, limit type, acceptable
    duration, limit group): this function keeps the rows of the *selected* limit groups, of
    type ``CURRENT``, with ``acceptable_duration == -1`` (the permanent limit — temporary
    limits like ``10'`` or ``1'`` are dropped), and pivots them into one row per element with
    one column per side: ``current_limit1``/``current_limit2`` for branches, ``current_limit``
    for single-sided elements (dangling lines).

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
    limits = limits.assign(column=limits["side"].map(_COLUMN_BY_SIDE))
    # aggfunc="min": the most conservative limit, in the untypical case where several selected
    # rows survive for the same (element, side).
    pivot = limits.pivot_table(index="element_id", columns="column", values="value", aggfunc="min")
    for column in list(pivot.columns):
        pivot[f"has_{column}"] = pivot[column].notna()
    return pivot
