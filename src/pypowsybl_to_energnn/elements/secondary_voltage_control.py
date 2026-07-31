# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

"""The secondary voltage control extension, as hyper-edge classes of its own.

Unlike ``activePowerControl`` or ``standbyAutomaton``, which add columns to an existing
element and are merged into it, the secondary voltage control describes objects that exist
on their own: control *zones*, each regulating the voltage of one or more pilot buses to a
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
    """Secondary voltage control zones, connected to their pilot buses.

    A zone may pilot several buses (``bus_ids`` is a comma-separated list): the table holds
    one hyper-edge per (zone, pilot bus) pair, all sharing the zone ``name`` address —
    ``target_v`` is repeated on each. Beware: pypowsybl reports pilot buses as *bus/breaker*
    view ids; they are translated here into their bus view bus (the view the default
    configurations are built in), so that the ``pilot_bus_id`` port lands on the same
    addresses as :class:`Buses`. For a bus/breaker configuration, override
    :meth:`build_table` and keep the raw ids instead.

    :param ports: Address columns, the zone name and the pilot bus by default.
    :param features: Feature columns, the pilot voltage target by default.
    """

    def __init__(self, ports: Sequence[str] = ("name", "pilot_bus_id"), features: Sequence[str] = ("target_v",)):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        zones = _secondary_voltage_control_table(network, "zones", columns=["name", "target_v", "bus_ids"])
        # One row per (zone, pilot bus); the fresh index keeps the dangling-port sentinels
        # distinct across pilots of the same zone.
        zones = zones.assign(pilot_bus_id=zones["bus_ids"].str.split(",")).explode("pilot_bus_id").reset_index(drop=True)
        bus_view_bus = network.get_bus_breaker_view_buses()["bus_id"]
        zones["pilot_bus_id"] = zones["pilot_bus_id"].map(bus_view_bus)
        return zones


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
