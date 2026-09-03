# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

from typing import Callable, Sequence, Union

import pandas as pd
import pypowsybl.network as pn

from .base import PypowsyblElements


class TableConverter(PypowsyblElements):
    """Generic elements converter driven by an arbitrary table — the escape hatch.

    The dedicated classes (:class:`Lines`, :class:`Generators`, ...) cover the pypowsybl
    tables with their options; this class covers everything else without writing a subclass.
    The table is either:

    - the name of a ``pypowsybl.network.Network`` method (e.g. ``"get_switches"``), called
      with ``all_attributes=True``, the index recovered as a regular ``id`` column;
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
        ports: Sequence[str] | None = None,
        features: Sequence[str] | None = None,
    ):
        super().__init__(ports=ports, features=features)
        self.table = table

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        if isinstance(self.table, str):
            return getattr(network, self.table)(all_attributes=True).reset_index()
        return self.table(network=network, **kwargs)

    @property
    def _table_name(self) -> str:
        if isinstance(self.table, str):
            return self.table
        return getattr(self.table, "__name__", repr(self.table))
