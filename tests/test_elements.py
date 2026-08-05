# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

import numpy as np
import pandas as pd
import pypowsybl.network as pn
import pytest
from energnn.graph import HyperEdgeSetStructure

from pypowsybl_to_energnn import TableConverter, isolate_dangling_ports


@pytest.fixture(scope="module")
def network():
    return pn.create_ieee14()


def test_ports_and_features(network):
    converter = TableConverter("get_lines", ports=["bus1_id", "bus2_id"], features=["r", "x"])
    df_port, df_feature = converter(network=network)

    assert list(df_port.columns) == ["bus1_id", "bus2_id"]
    assert list(df_feature.columns) == ["r", "x"]
    assert len(df_port) == len(df_feature)
    assert len(df_port) == len(network.get_lines())


def test_ports_only(network):
    converter = TableConverter("get_buses", ports=["id"])
    df_port, df_feature = converter(network=network)

    assert df_feature is None
    assert list(df_port.columns) == ["id"]
    assert df_port["id"].is_unique
    assert len(df_port) == len(network.get_buses())


def test_features_only(network):
    converter = TableConverter("get_loads", features=["p0", "q0"])
    df_port, df_feature = converter(network=network)

    assert df_port is None
    assert list(df_feature.columns) == ["p0", "q0"]
    assert len(df_feature) == len(network.get_loads())


def test_no_ports_nor_features_raises():
    with pytest.raises(ValueError):
        TableConverter("get_lines")


def test_empty_table(network):
    # There is no battery in the IEEE 14 test case: the converter must still return
    # well-formed (empty) tables.
    converter = TableConverter("get_batteries", ports=["bus_id"], features=["max_p", "min_p"])
    df_port, df_feature = converter(network=network)

    assert len(df_port) == 0
    assert len(df_feature) == 0
    assert list(df_port.columns) == ["bus_id"]
    assert list(df_feature.columns) == ["max_p", "min_p"]


@pytest.mark.parametrize(
    "getter",
    [
        "get_2_windings_transformers",
        "get_branches",
        "get_buses",
        "get_generators",
        "get_lines",
        "get_loads",
        "get_shunt_compensators",
        "get_substations",
        "get_switches",
        "get_voltage_levels",
    ],
)
def test_id_port_smoke(network, getter):
    # The "id" column is the index of pypowsybl tables: every table must be able to expose
    # it as a port.
    df_port, df_feature = TableConverter(getter, ports=["id"])(network=network)

    assert df_feature is None
    assert list(df_port.columns) == ["id"]


def test_unknown_column_message(network):
    converter = TableConverter("get_loads", ports=["bus_id"], features=["foo"])
    with pytest.raises(ValueError, match=r"\['foo'\] not found in 'get_loads'"):
        converter(network=network)


def test_callable_table(network):
    # Derived features: any callable returning a DataFrame can be the table.
    def squared_voltage_buses(network, **_):
        df = network.get_buses().reset_index()
        df["squared_v_mag"] = df["v_mag"] ** 2
        return df

    converter = TableConverter(squared_voltage_buses, ports=["id"], features=["squared_v_mag"])
    df_port, df_feature = converter(network=network)

    assert list(df_feature.columns) == ["squared_v_mag"]
    assert len(df_port) == len(network.get_buses())


def test_callable_table_join():
    # Merging a satellite table into its parent is three lines of pandas in the table function.
    def transformers_with_ratio_tap_changers(network, **_):
        df = network.get_2_windings_transformers(all_attributes=True)
        rtc = network.get_ratio_tap_changers(all_attributes=True).add_prefix("rtc_")
        return df.join(rtc).reset_index()

    network = pn.create_eurostag_tutorial_example1_network()
    converter = TableConverter(
        transformers_with_ratio_tap_changers, ports=["bus1_id", "bus2_id"], features=["r", "x", "rtc_tap"]
    )
    df_port, df_feature = converter(network=network)

    assert len(df_port) == len(network.get_2_windings_transformers())
    # NHV2_NLOAD has a ratio tap changer, NGEN_NHV1 does not (NaN, turned into 0 downstream).
    assert df_feature["rtc_tap"].notna().any() and df_feature["rtc_tap"].isna().any()


def test_callable_table_external_source(network):
    # A table that does not come from pypowsybl at all, picked from the conversion kwargs.
    converter = TableConverter(lambda gen_costs, **_: gen_costs, ports=["generator_id"], features=["marginal_cost"])
    gen_costs = pd.DataFrame({"generator_id": ["B1-G", "B2-G"], "marginal_cost": [12.0, 7.5]})
    df_port, df_feature = converter(network=network, gen_costs=gen_costs)

    assert list(df_port["generator_id"]) == ["B1-G", "B2-G"]
    assert list(df_feature["marginal_cost"]) == [12.0, 7.5]


def test_unknown_column_message_names_the_callable(network):
    def my_table(network, **_):
        return network.get_loads().reset_index()

    converter = TableConverter(my_table, features=["foo"])
    with pytest.raises(ValueError, match="my_table"):
        converter(network=network)


def test_get_structure():
    converter = TableConverter("get_generators", ports=["bus_id"], features=["target_p", "target_v"])
    assert isinstance(converter.get_structure(), HyperEdgeSetStructure)


def test_isolate_dangling_ports():
    # '' and NaN port values must each be rerouted to their own sentinel address: shared
    # as-is, they would spuriously connect every such element through a single phantom node.
    df = pd.DataFrame({"id": ["a", "b", "c"], "bus_id": ["bus1", "", np.nan]})
    isolated = isolate_dangling_ports(df, ["bus_id"])

    assert isolated.loc[0, "bus_id"] == "bus1"
    assert isolated.loc[1, "bus_id"] != isolated.loc[2, "bus_id"]
    assert "" not in set(isolated["bus_id"])
    # Deterministic (derived from element id and column name), and the input is not mutated.
    assert isolated.loc[1, "bus_id"] == isolate_dangling_ports(df, ["bus_id"]).loc[1, "bus_id"]
    assert df.loc[1, "bus_id"] == ""


def test_isolate_dangling_ports_with_duplicated_ids():
    # Tables with one row per (element, ...) pair repeat the element id: two dangling ports
    # of the same id must still get distinct sentinels, or the rows would be spuriously
    # connected through a shared phantom node. Only the repeats gain a rank suffix.
    df = pd.DataFrame({"id": ["a", "a", "a"], "bus_id": ["bus1", "", ""]})
    isolated = isolate_dangling_ports(df, ["bus_id"])

    assert isolated.loc[0, "bus_id"] == "bus1"
    assert isolated.loc[1, "bus_id"] == "__dangling__a__bus_id"
    assert isolated.loc[2, "bus_id"] != isolated.loc[1, "bus_id"]


def test_isolate_dangling_ports_without_id_column():
    df = pd.DataFrame({"bus_id": ["", "bus1"]}, index=["a", "b"])
    isolated = isolate_dangling_ports(df, ["bus_id"])
    assert isolated.loc["a", "bus_id"] not in ("", "bus1")


def test_dangling_ports_are_isolated_end_to_end():
    # bus_id is '' for elements disconnected in the bus view: check the full path.
    network = pn.create_four_substations_node_breaker_network()
    network.update_loads(id=["LD1", "LD6"], connected=[False, False])
    converter = TableConverter("get_loads", ports=["bus_id"])
    df_port, _ = converter(network=network)

    load_ids = list(network.get_loads().index)
    ld1, ld6 = df_port.iloc[load_ids.index("LD1")]["bus_id"], df_port.iloc[load_ids.index("LD6")]["bus_id"]
    bus_ids = set(network.get_buses().index)
    assert ld1 != ld6
    assert ld1 not in bus_ids and ld6 not in bus_ids
