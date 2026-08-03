# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

from typing import Sequence

import pandas as pd
import pypowsybl.network as pn

from .base import PypowsyblElements


def _merge_infrastructure(
    df: pd.DataFrame,
    network: pn.Network,
    voltage_level_features: Sequence[str] | None,
    substation_features: Sequence[str] | None,
) -> pd.DataFrame:
    """Join the ``voltage_levels`` and ``substations`` infrastructure tables onto the buses.

    Both joins chain through the ``voltage_level_id`` column of the bus table; the joined
    columns land prefixed (``voltage_level_nominal_v``, ``substation_country``, ...). The
    substation join also lands the plain ``substation_id`` column, usable as a port.
    """
    if voltage_level_features is None and substation_features is None:
        return df

    voltage_levels = network.get_voltage_levels(all_attributes=True)
    if voltage_level_features is not None:
        df = df.merge(voltage_levels.add_prefix("voltage_level_"), how="left", left_on="voltage_level_id", right_index=True)
    if substation_features is not None:
        df = df.assign(substation_id=df["voltage_level_id"].map(voltage_levels["substation_id"]))
        substations = network.get_substations(all_attributes=True).add_prefix("substation_")
        df = df.merge(substations, how="left", left_on="substation_id", right_index=True)
    return df


def _with_infrastructure_features(
    features: Sequence[str] | None,
    voltage_level_features: Sequence[str] | None,
    substation_features: Sequence[str] | None,
) -> Sequence[str] | None:
    merged = []
    if voltage_level_features is not None:
        merged += [f"voltage_level_{f}" for f in voltage_level_features]
    if substation_features is not None:
        merged += [f"substation_{f}" for f in substation_features]
    if not merged:
        return features
    return (list(features) if features is not None else []) + merged


class Buses(PypowsyblElements):
    """Buses of the bus view (``get_buses``), the nodes every other element attaches to.

    Their ``id`` is the address the ``bus_id``/``bus1_id``/... ports of the other classes
    point to. The buses carry no problem data (``AC_LOAD_FLOW_INPUT_FEATURES`` is empty):
    their default feature is the voltage magnitude solved by a first AC load flow. Phase
    angles (``v_angle``) are deliberately never suggested: they are not permutation
    equivariant.

    The ``voltage_levels`` and ``substations`` infrastructure tables are satellites chained
    through the ``voltage_level_id`` column: like every joined table, each has its own
    feature list parameter naming the columns to bring in (``None`` = not joined). Joined
    columns land prefixed (``voltage_level_nominal_v``, ...); the substation join also lands
    the plain ``substation_id`` column, usable as a port. Mind that substations mostly carry
    categorical columns (``TSO``, ``country``): encode them through :class:`TableConverter`
    instead of listing them as raw features. This is the flat form of the infrastructure;
    :class:`VoltageLevels` and :class:`Substations` are the chain form, with each tier as
    its own hyper-edge class.

    :param ports: Address columns, ``("id",)`` by default.
    :param features: Feature columns, ``AC_LOAD_FLOW_OUTPUT_FEATURES`` by default (pass
        ``None`` for structural buses without features).
    :param voltage_level_features: Columns of ``get_voltage_levels`` to join, prefixed by
        ``voltage_level_`` in the graph — ``VOLTAGE_LEVEL_FEATURES`` is the numeric bundle.
        ``None`` (default) leaves the table out.
    :param substation_features: Columns of ``get_substations`` to join, prefixed by
        ``substation_`` in the graph. ``None`` (default) leaves the table out.
    """

    AC_LOAD_FLOW_INPUT_FEATURES: tuple[str, ...] = ()
    AC_LOAD_FLOW_OUTPUT_FEATURES = ("v_mag",)

    VOLTAGE_LEVEL_FEATURES = ("nominal_v", "high_voltage_limit", "low_voltage_limit")

    def __init__(
        self,
        ports: Sequence[str] = ("id",),
        features: Sequence[str] | None = AC_LOAD_FLOW_INPUT_FEATURES + AC_LOAD_FLOW_OUTPUT_FEATURES,
        *,
        voltage_level_features: Sequence[str] | None = None,
        substation_features: Sequence[str] | None = None,
    ):
        features = _with_infrastructure_features(features, voltage_level_features, substation_features)
        super().__init__(ports=ports, features=features)
        self.voltage_level_features = voltage_level_features
        self.substation_features = substation_features

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        df = network.get_buses(all_attributes=True).reset_index()
        return _merge_infrastructure(df, network, self.voltage_level_features, self.substation_features)


class BusBreakerViewBuses(PypowsyblElements):
    """Buses of the bus/breaker view (``get_bus_breaker_view_buses``), the finer topology nodes.

    The ``bus_breaker_bus_id``/... ports of the other classes (and :class:`Switches`, on
    both sides) point to their ``id``. The ``bus_id`` column holds the bus view bus each of
    them merges into — adding it to ``ports`` bridges the two views in one graph. Like
    :class:`Buses` (see its docstring for the infrastructure joins, shared by this class),
    they carry no problem data, and their default feature is the voltage magnitude solved by
    a first AC load flow.

    :param ports: Address columns, ``("id",)`` by default.
    :param features: Feature columns, ``AC_LOAD_FLOW_OUTPUT_FEATURES`` by default (pass
        ``None`` for structural buses without features).
    :param voltage_level_features: Columns of ``get_voltage_levels`` to join, prefixed by
        ``voltage_level_`` in the graph — ``VOLTAGE_LEVEL_FEATURES`` is the numeric bundle.
        ``None`` (default) leaves the table out.
    :param substation_features: Columns of ``get_substations`` to join, prefixed by
        ``substation_`` in the graph. ``None`` (default) leaves the table out.
    """

    AC_LOAD_FLOW_INPUT_FEATURES: tuple[str, ...] = ()
    AC_LOAD_FLOW_OUTPUT_FEATURES = ("v_mag",)

    VOLTAGE_LEVEL_FEATURES = Buses.VOLTAGE_LEVEL_FEATURES

    def __init__(
        self,
        ports: Sequence[str] = ("id",),
        features: Sequence[str] | None = AC_LOAD_FLOW_INPUT_FEATURES + AC_LOAD_FLOW_OUTPUT_FEATURES,
        *,
        voltage_level_features: Sequence[str] | None = None,
        substation_features: Sequence[str] | None = None,
    ):
        features = _with_infrastructure_features(features, voltage_level_features, substation_features)
        super().__init__(ports=ports, features=features)
        self.voltage_level_features = voltage_level_features
        self.substation_features = substation_features

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        df = network.get_bus_breaker_view_buses(all_attributes=True).reset_index()
        return _merge_infrastructure(df, network, self.voltage_level_features, self.substation_features)
