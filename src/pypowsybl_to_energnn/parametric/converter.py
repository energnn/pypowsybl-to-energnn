# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

"""Spec → graph: execute a resolved spec against a pypowsybl network.

The only stage that touches pandas and the network: :class:`SpecElementsConverter` reads and
validates one table per :class:`TableSpec`, and :class:`PypowsyblConverter` assembles them —
from options (resolved through :mod:`.resolve`) or directly from a spec (:meth:`from_spec`).
"""

from __future__ import annotations

import pandas as pd
import pypowsybl.network as pn
from energnn.converter import Converter, ElementsConverter

from .resolve import resolve_spec
from .spec import MergedTable, TableSpec


class SpecElementsConverter(ElementsConverter):
    """Elements converter driven by a :class:`TableSpec`.

    Reads the spec's pypowsybl table (index levels recovered as columns with ``reset_index``),
    joins the merged auxiliary tables, and validates that every requested column exists — with
    an explicit error message instead of a downstream pandas ``KeyError``.
    """

    def __init__(self, spec: TableSpec):
        feature_list = list(spec.features) if spec.features is not None else []
        for m in spec.merged:
            feature_list.extend(m.prefix + f for f in m.features)
        super().__init__(
            port_list=list(spec.ports) if spec.ports is not None else None,
            feature_list=feature_list if feature_list else None,
        )
        self.spec = spec

    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        df = _fetch_table(network, self.spec.getter, self.spec.getter_args)
        for m in self.spec.merged:
            df = df.join(self._merged_features(network, m, df))
        df = df.reset_index()
        missing = [c for c in self.attributes if c not in df.columns]
        if missing:
            raise ValueError(f"Columns {missing} not found in '{self.spec.getter}'; available: {sorted(df.columns)}.")
        if self.spec.query is not None:
            df = df.query(self.spec.query)
        if self.port_list is not None:
            df = _isolate_dangling_ports(df, self.port_list)
        return df

    def _merged_features(self, network: pn.Network, m: MergedTable, df: pd.DataFrame) -> pd.DataFrame:
        """Return the features of merged table ``m``, one row per row of ``df`` (see :class:`MergedTable`)."""
        table = _fetch_table(network, m.getter, m.getter_args)
        missing = [c for c in m.features if c not in table.columns]
        if missing:
            raise ValueError(f"Columns {missing} not found in '{m.getter}'; available: {sorted(table.columns)}.")
        if m.on is None:
            return table[list(m.features)].add_prefix(m.prefix)
        if m.on not in df.columns:
            raise ValueError(f"Join column '{m.on}' not found in '{self.spec.getter}'; available: {sorted(df.columns)}.")
        key = df[m.on]
        for hop_getter, hop_column in m.via:
            hop = getattr(network, hop_getter)(all_attributes=True)
            if hop_column not in hop.columns:
                raise ValueError(f"Join column '{hop_column}' not found in '{hop_getter}'; available: {sorted(hop.columns)}.")
            key = key.map(hop[hop_column])
        features = table.reindex(key)[list(m.features)]
        features.index = df.index
        return features.add_prefix(m.prefix)


def _fetch_table(network: pn.Network, getter: str, getter_args: tuple[str, ...]) -> pd.DataFrame:
    """Fetch a pypowsybl table, extension tables included.

    ``get_extensions`` takes the extension (and table) name as positional arguments and no
    ``all_attributes`` flag — regular getters take the opposite.
    """
    method = getattr(network, getter)
    if getter_args:
        return method(*getter_args)
    return method(all_attributes=True)


def _isolate_dangling_ports(df: pd.DataFrame, port_columns: list[str]) -> pd.DataFrame:
    """Replace empty-string port values by per-element sentinel addresses.

    pypowsybl uses ``''`` when a connection point does not exist: ``bus_id`` of an element
    disconnected in the bus view, ``substation_id`` of a voltage level without substation, ...
    Left as-is, ``''`` would become one ordinary shared address, spuriously connecting every
    such object through a single phantom node. Each empty port is instead rerouted to its own
    fresh address — deterministic (derived from the element id and the column name), so the
    graph does not depend on row order and is reproducible across runs.
    """
    empty_masks = {col: df[col] == "" for col in port_columns}
    if not any(mask.any() for mask in empty_masks.values()):
        return df

    df = df.copy()
    ids = df["id"] if "id" in df.columns else df.index.to_series()
    for col, mask in empty_masks.items():
        df.loc[mask, col] = ids[mask].map(lambda element_id: f"__dangling__{element_id}__{col}")
    return df


class PypowsyblConverter(Converter):
    """Converter configured by options rather than by subclassing (ROADMAP §1).

    The options resolve into an explicit spec (``self.spec``), the pivot format: dump it with
    :meth:`to_dict`, store it next to your datasets, and reload it with :meth:`from_spec`.

    Structure options — which hyper-edge classes exist and how they connect:

    :param topology_view: ``"bus_branch"`` (bus view, the one power flows operate on) or
        ``"bus_breaker"`` (finer view: bus/breaker buses and switches).
    :param regulation: Include ports toward the remotely regulated buses
        (``regulated_bus_id`` of generators, SVCs and VSC stations — a voltage regulation —
        and ``regulating_bus_id`` of tap changers in ``"connect"`` mode, which for phase tap
        changers regulates a flow or a current). Frequency regulation (droop) carries no port
        and will arrive as features through ``extensions``.
    :param satellites: Mapping from satellite table name (see keys of
        ``registry._SATELLITES``) to its representation: ``"merge"`` joins its columns into
        the features of its parent class (one-row-per-parent satellites only), ``"connect"``
        makes it a hyper-edge class of its own with a port to the parent element. Satellites
        absent from the mapping are not extracted.
    :param infrastructure: Mapping from infrastructure level (``"voltage_levels"``,
        ``"substations"``, ``"areas"``) to its representation, with the same vocabulary:
        ``"merge"`` copies the level's features down onto the buses (nominal_v and voltage
        limits through ``voltage_level_id``, country and TSO through the bus → voltage level
        → substation chain), ``"connect"`` represents the level as a hyper-edge class —
        substations and areas then attach through the voltage levels, which must be connected
        as well. Levels absent from the mapping are not extracted.
    :param extensions: Mapping from pypowsybl extension name (see keys of
        ``registry._EXTENSIONS``) to its representation, with the same vocabulary:
        ``"merge"`` joins the extension's feature columns into every carrying class
        (activePowerControl spans generators *and* batteries; elements without the extension
        get NaN → 0), ``"connect"`` makes each extension table a hyper-edge class of its own,
        the carrier id recovered from the index as a port. Address-only or relational
        extensions (slackTerminal, secondaryVoltageControl) are ``"connect"``-only.
        Extensions absent from the mapping are not extracted.
    :param ports: ``False`` strips all addresses from the graph (classes left with neither
        ports nor features are then dropped). Orthogonal to the feature groups — e.g. a
        training target keeps its ports by default; drop them only when the addresses are
        redundant, such as rows aligned with an input graph extracted from the same network.

    Feature option — which columns each class carries:

    :param features: The feature groups to project on each class, cumulative, on a
        solver × role grid: ``"ac_pf_input"`` — the data of the AC power flow problem
        (impedances, limits, setpoints, ...) — and ``"ac_pf_output"`` — the state it solves
        (``p``/``q``/``i``, ``v_mag`` on the buses of the topology view) — plus their
        active-only DC counterparts ``"dc_pf_input"``/``"dc_pf_output"``. AC and DC groups
        cannot be mixed: a graph describes the problem of one solver. The typical GNN input
        carries ``("ac_pf_input", "ac_pf_output")`` — the problem warm-started by a first
        power flow — and a training target only ``("ac_pf_output",)``. Output columns are
        NaN until a power flow has run on the network: run one first.

    Other options:

    :param per_unit: Set ``network.per_unit`` before extraction, so that graphs cannot
        silently mix per-united and physical values.
    :param main_component_only: Not implemented yet.
    :param backend: Optional target backend for the produced graphs.
    """

    def __init__(
        self,
        *,
        topology_view: str = "bus_branch",
        per_unit: bool = True,
        features: tuple[str, ...] = ("ac_pf_input",),
        regulation: bool = True,
        satellites: dict[str, str] | None = None,
        infrastructure: dict[str, str] | None = None,
        extensions: dict[str, str] | None = None,
        ports: bool = True,
        main_component_only: bool = False,
        backend=None,
    ):
        if main_component_only:
            raise NotImplementedError("main_component_only is not implemented yet.")
        spec = resolve_spec(
            topology_view=topology_view,
            features=features,
            regulation=regulation,
            satellites=satellites,
            infrastructure=infrastructure,
            extensions=extensions,
            ports=ports,
        )
        self._init_from_spec(spec, per_unit=per_unit, backend=backend)

    def _init_from_spec(self, spec: dict[str, TableSpec], *, per_unit: bool, backend) -> None:
        self.spec = spec
        self.per_unit = per_unit
        self.backend = backend
        self.elements_converter_dict = {k: SpecElementsConverter(s) for k, s in spec.items()}

    @classmethod
    def from_spec(cls, spec: dict[str, TableSpec | dict], *, per_unit: bool = True, backend=None) -> "PypowsyblConverter":
        """Build a converter directly from a spec, bypassing the options.

        This is both the deserialization path (``spec`` as returned by :meth:`to_dict`) and the
        amendment path: resolve options first, tweak the resulting spec, then rebuild.
        """
        converter = cls.__new__(cls)
        table_specs = {k: s if isinstance(s, TableSpec) else TableSpec.from_dict(s) for k, s in spec.items()}
        converter._init_from_spec(table_specs, per_unit=per_unit, backend=backend)
        return converter

    def to_dict(self) -> dict:
        """Return the resolved spec as a JSON/YAML-ready dict of plain strings."""
        return {k: s.to_dict() for k, s in self.spec.items()}

    def __call__(self, *, network: pn.Network, **kwargs):
        network.per_unit = self.per_unit
        return super().__call__(network=network, **kwargs)
