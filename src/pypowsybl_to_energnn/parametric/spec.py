# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

"""The pivot format: an explicit, serializable spec — one :class:`TableSpec` per hyper-edge class.

Plain data, no dependency on the rest of the package: options resolve into it
(:mod:`.resolve`), the converters execute it (:mod:`.converter`), and it round-trips through
``to_dict``/``from_dict`` so it can be versioned and stored next to the datasets it produced.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MergedTable:
    """An auxiliary table merged into the features of a hyper-edge class.

    Only tables with at most one row per element of the target class can be merged: rows are
    joined and each feature column is prefixed with ``prefix``. Elements without a matching
    row get NaN features (turned into 0 downstream by the base :class:`Converter`).

    The join key is the id of the target element itself (``on=None``, e.g. a tap changer
    into its transformer), or a foreign-key column of the target table (``on="..."``, e.g.
    voltage-level features onto buses through their ``voltage_level_id``). ``via`` lists
    intermediate hops ``(getter, column)`` resolving the key across tables (e.g. bus →
    voltage level → substation). ``getter_args`` are positional arguments of the getter —
    the extension (and table) name for ``get_extensions``.
    """

    getter: str
    features: tuple[str, ...]
    prefix: str
    on: str | None = None
    via: tuple[tuple[str, str], ...] = ()
    getter_args: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        d: dict = {"getter": self.getter, "features": list(self.features), "prefix": self.prefix}
        if self.on is not None:
            d["on"] = self.on
        if self.via:
            d["via"] = [list(hop) for hop in self.via]
        if self.getter_args:
            d["getter_args"] = list(self.getter_args)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "MergedTable":
        return cls(
            getter=d["getter"],
            features=tuple(d["features"]),
            prefix=d["prefix"],
            on=d.get("on"),
            via=tuple((hop[0], hop[1]) for hop in d.get("via", ())),
            getter_args=tuple(d.get("getter_args", ())),
        )


@dataclass(frozen=True)
class TableSpec:
    """Conversion spec for one hyper-edge class: a pypowsybl getter and its column split.

    :param getter: Name of the ``pypowsybl.network.Network`` method returning the table.
    :param ports: Columns holding addresses (bus ids, parent element ids, ...), or ``None``.
    :param features: Columns holding features, or ``None``.
    :param merged: Auxiliary tables merged into the features (see :class:`MergedTable`).
    :param query: Optional :meth:`pandas.DataFrame.query` expression filtering the rows (e.g.
        ``"retained"`` to keep only the switches that belong to the bus/breaker view).
    :param getter_args: Positional arguments of the getter — the extension (and table) name
        for ``get_extensions``.
    """

    getter: str
    ports: tuple[str, ...] | None = None
    features: tuple[str, ...] | None = None
    merged: tuple[MergedTable, ...] = ()
    query: str | None = None
    getter_args: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        d: dict = {
            "getter": self.getter,
            "ports": list(self.ports) if self.ports is not None else None,
            "features": list(self.features) if self.features is not None else None,
        }
        if self.merged:
            d["merged"] = [m.to_dict() for m in self.merged]
        if self.query is not None:
            d["query"] = self.query
        if self.getter_args:
            d["getter_args"] = list(self.getter_args)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "TableSpec":
        return cls(
            getter=d["getter"],
            ports=tuple(d["ports"]) if d.get("ports") is not None else None,
            features=tuple(d["features"]) if d.get("features") is not None else None,
            merged=tuple(MergedTable.from_dict(m) for m in d.get("merged", ())),
            query=d.get("query"),
            getter_args=tuple(d.get("getter_args", ())),
        )
