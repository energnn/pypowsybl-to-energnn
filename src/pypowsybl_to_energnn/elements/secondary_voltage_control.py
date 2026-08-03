# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

"""The secondary voltage control extension, as hyper-edge classes of its own.

Unlike ``activePowerControl`` or ``standbyAutomaton``, which add columns to an existing
element and are merged into it, the secondary voltage control describes objects that exist
on their own: control *zones*, each regulating the voltage of its pilot point to a
``target_v``, through the *units* (generators) enrolled in the zone. The extension exposes
them as two tables (``get_extensions("secondaryVoltageControl", table_name="zones"/"units")``),
converted here as two hyper-edge classes.

The zone name is the address that ties the two classes together: a zone hyper-edge and its
unit hyper-edges all carry it as a port. Zone names live in the same global address space as
every other id — pypowsybl guarantees no uniqueness across those spaces, so avoid naming a
zone like a bus.

On networks without the extension, pypowsybl raises instead of returning an empty table (the
single-table extension getters return empty tables); both classes translate that into empty
tables, so they can sit in a configuration applied to mixed datasets.
"""

from typing import Sequence

import pandas as pd
import pypowsybl.network as pn
from pypowsybl import PyPowsyblError

from .base import PypowsyblElements


def _secondary_voltage_control_table(network: pn.Network, table_name: str, columns: list[str]) -> pd.DataFrame:
    try:
        return network.get_extensions("secondaryVoltageControl", table_name=table_name).reset_index()
    except PyPowsyblError:
        return pd.DataFrame(columns=columns)


class SecondaryVoltageControlZones(PypowsyblElements):
    """Secondary voltage control zones, one hyper-edge per zone, connected to its pilot bus.

    A zone regulates a single pilot point, located by a list of candidate identifiers
    (``bus_ids``, comma-separated): busbar section or bus/breaker view bus ids, alternatives
    covering topology changes — not several simultaneous pilots. Mirroring the load flow's
    resolution, the candidates are tried in order and the first one landing on a bus wins —
    in the bus view (``pilot_bus_id``, the default port, on the same addresses as
    :class:`Buses`) and in the bus/breaker view (``pilot_bus_breaker_bus_id``, for
    bus/breaker configurations) alike. A zone with no resolvable candidate is left with a
    dangling pilot port.

    :param ports: Address columns, the zone name and the bus view pilot bus by default.
    :param features: Feature columns, the pilot voltage target by default.
    """

    def __init__(self, ports: Sequence[str] = ("name", "pilot_bus_id"), features: Sequence[str] = ("target_v",)):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        zones = _secondary_voltage_control_table(network, "zones", columns=["name", "target_v", "bus_ids"])
        candidates = zones.assign(candidate_id=zones["bus_ids"].str.split(",")).explode("candidate_id")
        candidates = candidates.reset_index(drop=True)

        # Resolve each candidate — a busbar section id or a bus/breaker view bus id — in both views.
        busbar_sections = network.get_busbar_sections(all_attributes=True)
        bus_breaker_buses = network.get_bus_breaker_view_buses()
        is_busbar_section = candidates["candidate_id"].isin(busbar_sections.index)
        bus_breaker_bus = candidates["candidate_id"].map(busbar_sections["bus_breaker_bus_id"])
        bus_breaker_bus = bus_breaker_bus.where(
            is_busbar_section, candidates["candidate_id"].where(candidates["candidate_id"].isin(bus_breaker_buses.index))
        )
        bus_view_bus = candidates["candidate_id"].map(busbar_sections["bus_id"])
        bus_view_bus = bus_view_bus.where(is_busbar_section, candidates["candidate_id"].map(bus_breaker_buses["bus_id"]))

        candidates["pilot_bus_id"] = bus_view_bus.replace("", float("nan"))
        candidates["pilot_bus_breaker_bus_id"] = bus_breaker_bus.replace("", float("nan"))
        # One row per zone: per view, the first candidate that resolves wins (groupby.first
        # skips NaN); a zone with no resolvable candidate keeps NaN, isolated downstream.
        return candidates.groupby("name", sort=False, as_index=False).first()


class SecondaryVoltageControlUnits(PypowsyblElements):
    """Secondary voltage control units: the enrolment of a generator in a control zone.

    One hyper-edge per enrolled generator, tying the zone ``name`` address (shared with
    :class:`SecondaryVoltageControlZones`) to the generator's own id. For the ``unit_id``
    port to actually land on the generator, the generator must expose its id as a port too:
    use ``Generators(ports=("id", "bus_id", "regulated_bus_id"))`` in such a configuration.

    :param ports: Address columns, the zone name and the enrolled generator by default.
    :param features: Feature columns, the participation status by default.
    """

    def __init__(self, ports: Sequence[str] = ("zone_name", "unit_id"), features: Sequence[str] = ("participate",)):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        return _secondary_voltage_control_table(network, "units", columns=["unit_id", "participate", "zone_name"])
