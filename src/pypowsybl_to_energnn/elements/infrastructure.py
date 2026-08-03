# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

"""The infrastructure tiers above the buses, as hyper-edge classes of their own.

The chain form of the infrastructure: buses point to their voltage level through their
native ``voltage_level_id`` column (in both topology views — add it to the ports of
:class:`Buses` or :class:`BusBreakerViewBuses`), each voltage level points to its
substation, and each tier is its own hyper-edge class carrying its own data::

    {
        "buses": Buses(ports=("id", "voltage_level_id")),
        "voltage_levels": VoltageLevels(),
        "substations": Substations(),
    }

The alternative flat form merges the same columns down onto the buses
(``voltage_level_features``/``substation_features`` on the bus classes) without adding
nodes to the graph. Chain when the grouping structure itself matters (elements of a
voltage level are second-order neighbours through it), flatten when only the data does.

Areas are the transversal tier: control areas, bidding zones, ... grouping voltage levels
freely (a voltage level can belong to several areas), hence a relational
:class:`AreasVoltageLevels` class tying :class:`Areas` to :class:`VoltageLevels` instead of
a parent column.
"""

from typing import Sequence

import pandas as pd
import pypowsybl.network as pn

from .base import PypowsyblElements


class VoltageLevels(PypowsyblElements):
    """Voltage levels (``get_voltage_levels``), the tier between buses and substations.

    Their ``id`` is the address the ``voltage_level_id`` column of the bus tables (and of
    every other element table) points to; their ``substation_id`` port hangs them from
    :class:`Substations`. A voltage level without substation (allowed by IIDM) keeps a
    dangling substation port. The default features are the numeric bundle also offered as
    ``Buses.VOLTAGE_LEVEL_FEATURES`` for the flat form.

    :param ports: Address columns, the voltage level id and its substation by default.
    :param features: Feature columns, the nominal voltage and the voltage limits by default.
    """

    def __init__(
        self,
        ports: Sequence[str] = ("id", "substation_id"),
        features: Sequence[str] | None = ("nominal_v", "high_voltage_limit", "low_voltage_limit"),
    ):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_voltage_levels(all_attributes=True).reset_index()


class Areas(PypowsyblElements):
    """Areas (``get_areas``): control areas, bidding zones, ... grouping voltage levels.

    An area is tied to its voltage levels by the relational :class:`AreasVoltageLevels`
    class — both carry the area ``id`` as a port. The default features are the interchange
    data: ``interchange_target`` as problem data, the solved ``interchange`` (and its
    ``ac_interchange``/``dc_interchange`` split) as state. ``area_type`` is categorical:
    encode it through :class:`TableConverter` if needed.

    :param ports: Address columns, ``("id",)`` by default.
    :param features: Feature columns, ``AC_LOAD_FLOW_INPUT_FEATURES`` +
        ``AC_LOAD_FLOW_OUTPUT_FEATURES`` by default.
    """

    AC_LOAD_FLOW_INPUT_FEATURES = ("interchange_target",)
    AC_LOAD_FLOW_OUTPUT_FEATURES = ("interchange", "ac_interchange", "dc_interchange")
    DC_LOAD_FLOW_INPUT_FEATURES = ("interchange_target",)
    DC_LOAD_FLOW_OUTPUT_FEATURES = ("interchange",)

    def __init__(
        self,
        ports: Sequence[str] = ("id",),
        features: Sequence[str] | None = AC_LOAD_FLOW_INPUT_FEATURES + AC_LOAD_FLOW_OUTPUT_FEATURES,
    ):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_areas(all_attributes=True).reset_index()


class AreasVoltageLevels(PypowsyblElements):
    """The area membership (``get_areas_voltage_levels``), one hyper-edge per enrolment.

    The relational table tying :class:`Areas` to :class:`VoltageLevels`: one hyper-edge per
    (area, voltage level) pair — a voltage level enrolled in several areas (a control area
    and a bidding zone, say) gets one hyper-edge each. Structural: no features by default.

    :param ports: Address columns, the area and the voltage level by default.
    :param features: Feature columns, ``None`` by default.
    """

    def __init__(self, ports: Sequence[str] = ("id", "voltage_level_id"), features: Sequence[str] | None = None):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_areas_voltage_levels(all_attributes=True).reset_index()


class Substations(PypowsyblElements):
    """Substations (``get_substations``), the top infrastructure tier.

    Their ``id`` is the address the ``substation_id`` port of :class:`VoltageLevels` points
    to. Substations only carry categorical columns (``TSO``, ``country``, ``geo_tags``), so
    the class is structural by default (no features): encode those columns through
    :class:`TableConverter` if needed.

    :param ports: Address columns, ``("id",)`` by default.
    :param features: Feature columns, ``None`` by default.
    """

    def __init__(self, ports: Sequence[str] = ("id",), features: Sequence[str] | None = None):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_substations(all_attributes=True).reset_index()
