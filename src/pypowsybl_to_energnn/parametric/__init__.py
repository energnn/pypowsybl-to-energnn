# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

"""Parameterizable pypowsybl-to-energnn converter (ROADMAP §1).

A :class:`PypowsyblConverter` is configured by a few orthogonal options instead of
hand-written element specs. The options fall into two groups:

- **structure** — which hyper-edge classes exist and how they connect: ``topology_view``,
  ``regulation``, ``satellites``, ``infrastructure``, ``ports``;
- **features** — which column groups each class carries, cumulative, on a solver × role
  grid: ``"ac_pf_input"``/``"ac_pf_output"`` (the data of the AC power flow problem, and
  the state it solves — ``p``, ``q``, ``i``, ``v_mag``) and their active-only DC
  counterparts ``"dc_pf_input"``/``"dc_pf_output"``. A typical GNN input carries input and
  output of one solver, a training target only the output.

The package follows the data flow, one module per stage:

- :mod:`.spec` — the pivot format (:class:`TableSpec`, :class:`MergedTable`): explicit,
  serializable with :meth:`PypowsyblConverter.to_dict`, amendable, and reloadable with
  :meth:`PypowsyblConverter.from_spec`;
- :mod:`.registry` — the declarative knowledge about pypowsybl (tables, satellites,
  infrastructure levels);
- :mod:`.resolve` — options → spec (:func:`resolve_spec`);
- :mod:`.converter` — spec → graph (:class:`PypowsyblConverter`).
"""

from .converter import PypowsyblConverter, SpecElementsConverter
from .resolve import resolve_spec
from .spec import MergedTable, TableSpec

__all__ = [
    "MergedTable",
    "PypowsyblConverter",
    "SpecElementsConverter",
    "TableSpec",
    "resolve_spec",
]
