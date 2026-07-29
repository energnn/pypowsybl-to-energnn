# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

"""Options → spec: select and project the registry into an explicit, serializable spec.

:func:`resolve_spec` validates a combination of options, walks the registry (:mod:`.registry`)
and produces the pivot format (:mod:`.spec`). No pypowsybl network is involved at this stage.
"""

from __future__ import annotations

import dataclasses

from .registry import (
    _EXTENSIONS,
    _FEATURE_GROUPS,
    _INFRASTRUCTURE_FEATURES,
    _SATELLITES,
    _TABLES,
    _TOPOLOGY_VIEWS,
    _port_for_view,
)
from .spec import MergedTable, TableSpec

_ATTACHMENT_MODES = ("merge", "connect")


def _validate_modes(option: str, requested: dict[str, str], known) -> None:
    """Shared validation for the dict-of-modes options (``satellites`` and ``infrastructure``)."""
    if not isinstance(requested, dict):
        raise ValueError(
            f"{option} must be a dict mapping table names to a mode among {_ATTACHMENT_MODES}, "
            f'e.g. {{"{next(iter(known))}": "connect"}}. Tables: {sorted(known)}.'
        )
    for name, mode in requested.items():
        if name not in known:
            raise ValueError(f"Unknown {option} table '{name}'. Available: {sorted(known)}.")
        if mode not in _ATTACHMENT_MODES:
            raise ValueError(f"Invalid mode '{mode}' for {option} table '{name}'. Expected one of {_ATTACHMENT_MODES}.")


def _validate_feature_groups(features) -> None:
    """Validate the ``features`` option: an iterable of feature-group names, not a bare string."""
    if isinstance(features, str):
        raise ValueError(
            f"features must be an iterable of feature groups among {_FEATURE_GROUPS}, "
            f'e.g. ("ac_pf_input", "ac_pf_output").'
        )
    unknown = [group for group in features if group not in _FEATURE_GROUPS]
    if unknown:
        raise ValueError(f"Unknown feature groups {unknown}. Available: {list(_FEATURE_GROUPS)}.")
    if any(g.startswith("ac_") for g in features) and any(g.startswith("dc_") for g in features):
        raise ValueError(
            f"Feature groups {sorted(features)} mix AC and DC: a graph describes the problem of one "
            f"solver, and the dc_* groups are the active-only subsets of their ac_* counterparts. "
            f"Combine input and output groups of the same solver instead."
        )


def _resolve_satellites(
    spec: dict[str, TableSpec], satellites: dict[str, str], *, topology_view: str, regulation: bool
) -> None:
    """Add the requested satellite tables to ``spec``, each in its requested mode.

    ``"merge"`` joins the satellite columns into the features of its parent class (one-row-
    per-parent satellites only); ``"connect"`` makes it a hyper-edge class of its own, with a
    port to the parent element. Satellites absent from the dict are simply not extracted.
    """
    _validate_modes("satellites", satellites, _SATELLITES)
    for name, mode in satellites.items():
        satellite = _SATELLITES[name]
        if mode == "connect":
            ports: tuple[str, ...] = (satellite.parent_port,)
            if regulation and satellite.regulation_port is not None and topology_view == "bus_branch":
                ports += (satellite.regulation_port,)
            spec[name] = TableSpec(satellite.getter, ports=ports, features=satellite.features)
        else:
            if satellite.parent is None:
                raise ValueError(
                    f"Satellite '{name}' has a variable number of rows per parent element "
                    f"and cannot be merged; use 'connect' instead."
                )
            parent_spec = spec[satellite.parent]
            merged = MergedTable(getter=satellite.getter, features=satellite.features, prefix=satellite.prefix)
            spec[satellite.parent] = dataclasses.replace(parent_spec, merged=parent_spec.merged + (merged,))


def _resolve_infrastructure(spec: dict[str, TableSpec], infrastructure: dict[str, str]) -> None:
    """Add the requested infrastructure levels to ``spec``, each in its requested mode.

    ``"merge"`` copies the level's features down onto the buses (voltage levels through
    ``voltage_level_id``, substations through the bus → voltage level → substation chain) —
    or onto the voltage-level class itself for substations when it exists. ``"connect"``
    represents the level as a hyper-edge class of its own; substations and areas then attach
    to the graph through the voltage levels, which must be connected as well. Levels absent
    from the dict are simply not extracted.
    """
    _validate_modes("infrastructure", infrastructure, _INFRASTRUCTURE_FEATURES)
    if infrastructure.get("areas") == "merge":
        raise ValueError("A voltage level can belong to several areas: 'areas' cannot be merged; use 'connect' instead.")
    voltage_levels_connected = infrastructure.get("voltage_levels") == "connect"
    for level in ("substations", "areas"):
        if infrastructure.get(level) == "connect" and not voltage_levels_connected:
            raise ValueError(
                f"'{level}': 'connect' attaches to the graph through the voltage levels; "
                f'add "voltage_levels": "connect" as well.'
            )

    if infrastructure.get("voltage_levels") == "merge":
        merged = MergedTable(
            getter="get_voltage_levels",
            features=_INFRASTRUCTURE_FEATURES["voltage_levels"],
            prefix="voltage_level_",
            on="voltage_level_id",
        )
        spec["buses"] = dataclasses.replace(spec["buses"], merged=spec["buses"].merged + (merged,))
    elif voltage_levels_connected:
        spec["buses"] = dataclasses.replace(spec["buses"], ports=(spec["buses"].ports or ()) + ("voltage_level_id",))
        spec["voltage_levels"] = TableSpec(
            "get_voltage_levels",
            ports=("id", "substation_id") if infrastructure.get("substations") == "connect" else ("id",),
            features=_INFRASTRUCTURE_FEATURES["voltage_levels"],
        )

    if infrastructure.get("substations") == "merge":
        if voltage_levels_connected:
            merged = MergedTable(
                getter="get_substations",
                features=_INFRASTRUCTURE_FEATURES["substations"],
                prefix="substation_",
                on="substation_id",
            )
            spec["voltage_levels"] = dataclasses.replace(
                spec["voltage_levels"], merged=spec["voltage_levels"].merged + (merged,)
            )
        else:
            merged = MergedTable(
                getter="get_substations",
                features=_INFRASTRUCTURE_FEATURES["substations"],
                prefix="substation_",
                on="voltage_level_id",
                via=(("get_voltage_levels", "substation_id"),),
            )
            spec["buses"] = dataclasses.replace(spec["buses"], merged=spec["buses"].merged + (merged,))
    elif infrastructure.get("substations") == "connect":
        spec["substations"] = TableSpec("get_substations", ports=("id",), features=_INFRASTRUCTURE_FEATURES["substations"])

    if infrastructure.get("areas") == "connect":
        spec["areas"] = TableSpec("get_areas", ports=("id",), features=_INFRASTRUCTURE_FEATURES["areas"])
        spec["areas_voltage_levels"] = TableSpec("get_areas_voltage_levels", ports=("id", "voltage_level_id"))


def _resolve_extensions(spec: dict[str, TableSpec], extensions: dict[str, str], *, topology_view: str) -> None:
    """Add the requested pypowsybl extensions to ``spec``, each in its requested mode.

    Extensions are satellites fetched through ``get_extensions``: ``"merge"`` joins their
    feature columns into every carrying class (an extension such as activePowerControl spans
    generators *and* batteries; elements without the extension get NaN → 0), dropping the id
    columns by construction; ``"connect"`` makes each extension table a hyper-edge class of
    its own, the carrier id recovered from the index as a port. Extensions absent from the
    dict are simply not extracted.
    """
    _validate_modes("extensions", extensions, _EXTENSIONS)
    for name, mode in extensions.items():
        tables = _EXTENSIONS[name]
        if mode == "merge":
            if any(not t.parents for t in tables):
                raise ValueError(
                    f"Extension '{name}' only carries addresses or is relational: "
                    f"it cannot be merged; use 'connect' instead."
                )
            for t in tables:
                getter_args = (name, t.table) if t.table else (name,)
                merged = MergedTable(getter="get_extensions", getter_args=getter_args, features=t.features, prefix=t.prefix)
                for parent in t.parents:
                    spec[parent] = dataclasses.replace(spec[parent], merged=spec[parent].merged + (merged,))
        else:
            for t in tables:
                port_columns = (t.parent_port,) + t.ports
                if topology_view == t.bus_ports_view:
                    port_columns += t.bus_ports  # bus addresses live in a single view (see registry)
                spec[t.class_name] = TableSpec(
                    "get_extensions",
                    getter_args=(name, t.table) if t.table else (name,),
                    ports=port_columns,
                    features=t.features or None,
                )


def resolve_spec(
    *,
    topology_view: str = "bus_branch",
    features: tuple[str, ...] = ("ac_pf_input",),
    regulation: bool = True,
    satellites: dict[str, str] | None = None,
    infrastructure: dict[str, str] | None = None,
    extensions: dict[str, str] | None = None,
    ports: bool = True,
) -> dict[str, TableSpec]:
    """Resolve a combination of options into an explicit spec, one :class:`TableSpec` per table.

    See :class:`PypowsyblConverter` for the meaning of each option. Classes that end up with
    neither ports nor features (e.g. reactive-only devices when only DC groups are
    requested without ports) are dropped from the spec.
    """
    if topology_view not in _TOPOLOGY_VIEWS:
        raise ValueError(f"Invalid topology_view '{topology_view}'. Expected one of {_TOPOLOGY_VIEWS}.")
    _validate_feature_groups(features)

    spec: dict[str, TableSpec] = {}
    for name, table in _TABLES.items():
        if topology_view not in table.views:
            continue
        getter = table.getter
        if topology_view == "bus_breaker" and table.bus_breaker_getter is not None:
            getter = table.bus_breaker_getter
        port_columns = table.ports + tuple(_port_for_view(c, topology_view) for c in table.bus_ports)
        if regulation:
            port_columns += tuple(_port_for_view(c, topology_view) for c in table.regulation_ports)
        # Iterate over _FEATURE_GROUPS, not the user tuple, so column order does not depend on it.
        columns: tuple[str, ...] = ()
        for group in _FEATURE_GROUPS:
            if group in features:
                columns += getattr(table, group)
        spec[name] = TableSpec(getter, ports=port_columns or None, features=columns or None, query=table.query)

    _resolve_satellites(spec, satellites or {}, topology_view=topology_view, regulation=regulation)
    _resolve_infrastructure(spec, infrastructure or {})
    _resolve_extensions(spec, extensions or {}, topology_view=topology_view)

    if not ports:
        spec = {k: dataclasses.replace(s, ports=None) for k, s in spec.items()}
    return {k: s for k, s in spec.items() if s.ports is not None or s.features is not None or s.merged}
