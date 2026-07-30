# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

from typing import Callable, Union

import pandas as pd
from energnn.converter import ElementsConverter


def isolate_dangling_ports(df: pd.DataFrame, ports: list[str]) -> pd.DataFrame:
    """Replace empty (``''`` or NaN) port values by per-element sentinel addresses.

    pypowsybl uses ``''`` when a connection point does not exist: ``bus_id`` of an element
    disconnected in the bus view, ``substation_id`` of a voltage level without substation, ...
    Left as-is, such values would become one ordinary shared address, spuriously connecting
    every such element through a single phantom node. Each empty port is instead rerouted to
    its own fresh address — deterministic (derived from the element id and the column name),
    so the graph does not depend on row order and is reproducible across runs.

    :param df: Table with one row per element, holding an ``id`` column (the row index is
        used as element id otherwise).
    :param ports: Names of the port columns to process.
    """
    masks = {column: df[column].isna() | (df[column] == "") for column in ports}
    if not any(mask.any() for mask in masks.values()):
        return df

    df = df.copy()
    ids = df["id"] if "id" in df.columns else df.index.to_series()
    for column, mask in masks.items():
        df.loc[mask, column] = ids[mask].map(lambda element_id: f"__dangling__{element_id}__{column}")
    return df


class TableConverter(ElementsConverter):
    """Elements converter for one class of hyper-edges, driven by a table.

    On top of the ports/features split inherited from :class:`ElementsConverter`, this class
    validates that every requested column exists (with an explicit error message instead of a
    downstream pandas ``KeyError``) and isolates the dangling ports
    (see :func:`isolate_dangling_ports`).

    The table is either:

    - the name of a ``pypowsybl.network.Network`` method (e.g. ``"get_lines"``), called with
      ``all_attributes=True``, the index recovered as a regular ``id`` column — the common
      case;
    - any callable returning a :class:`pandas.DataFrame` with one row per element. It
      receives all the keyword arguments of the conversion call verbatim (``network=...``
      among them), so it can filter or join pypowsybl tables, or read a table that comes from
      outside pypowsybl entirely — e.g. ``lambda gen_costs, **_: gen_costs`` picks a
      DataFrame passed as ``converter(network=network, gen_costs=...)``.

    :param table: pypowsybl getter name, or callable returning the table.
    :param ports: Names of the columns holding addresses (bus ids, parent element ids, ...),
        or ``None``.
    :param features: Names of the columns holding features, or ``None``.
    """

    def __init__(
        self,
        table: Union[str, Callable[..., pd.DataFrame]],
        ports: list[str] | None = None,
        features: list[str] | None = None,
    ):
        super().__init__(port_list=ports, feature_list=features)
        self.table = table

    def _get_table(self, **kwargs) -> pd.DataFrame:
        if isinstance(self.table, str):
            df = getattr(kwargs["network"], self.table)(all_attributes=True).reset_index()
        else:
            df = self.table(**kwargs)

        missing = [c for c in self.attributes if c not in df.columns]
        if missing:
            name = self.table if isinstance(self.table, str) else getattr(self.table, "__name__", repr(self.table))
            raise ValueError(f"Columns {missing} not found in '{name}'; available: {sorted(df.columns)}.")

        if self.port_list is not None:
            df = isolate_dangling_ports(df, self.port_list)
        return df
