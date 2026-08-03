# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

from abc import abstractmethod
from typing import Sequence

import pandas as pd
import pypowsybl.network as pn
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


class PypowsyblElements(ElementsConverter):
    """Base class of all the pypowsybl elements converters, one subclass per class of objects.

    Each subclass (:class:`Lines`, :class:`Generators`, ...) declares its default ports and
    features (the data of the AC power flow problem), and implements :meth:`build_table` in
    plain pandas — that method is the whole story of how one class of objects becomes a
    table, and the place to look at (or copy and adapt) when a conversion must change.

    On top of the ports/features split inherited from :class:`ElementsConverter`, this base
    class validates that every requested column exists in the built table (with an explicit
    error message instead of a downstream pandas ``KeyError``) and isolates the dangling ports
    (see :func:`isolate_dangling_ports`).

    Every subclass keeps the object's own id in the built table as a regular ``id`` column
    (the pypowsybl index, recovered by ``reset_index``). Adding ``"id"`` to ``ports`` thus
    works for any class, not just :class:`Buses`: it publishes the object's id as an address,
    letting other classes connect to the element itself — e.g.
    ``Generators(ports=("id", "bus_id", "regulated_bus_id"))`` gives
    :class:`SecondaryVoltageControlUnits` a generator address to tie its ``unit_id`` port to.

    :param ports: Names of the columns of the built table holding addresses (bus ids, parent
        element ids, ...), or ``None``.
    :param features: Names of the columns holding features, or ``None``.
    """

    def __init__(self, ports: Sequence[str] | None, features: Sequence[str] | None):
        # energnn indexes the table with these lists; a tuple would be read as a single
        # MultiIndex key, hence the conversions.
        super().__init__(
            port_list=list(ports) if ports is not None else None,
            feature_list=list(features) if features is not None else None,
        )

    @abstractmethod
    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        """Return the table of this class of objects, one row per hyper-edge.

        The table must contain at least the requested port and feature columns. Subclasses
        receive all the keyword arguments of the conversion call verbatim (``network=...``
        among them).
        """
        raise NotImplementedError

    @property
    def _table_name(self) -> str:
        """Name used to designate the table in error messages."""
        return type(self).__name__

    def _get_table(self, **kwargs) -> pd.DataFrame:
        df = self.build_table(**kwargs)

        missing = [c for c in self.attributes if c not in df.columns]
        if missing:
            raise ValueError(f"Columns {missing} not found in '{self._table_name}'; available: {sorted(df.columns)}.")

        if self.port_list is not None:
            df = isolate_dangling_ports(df, self.port_list)
        return df
