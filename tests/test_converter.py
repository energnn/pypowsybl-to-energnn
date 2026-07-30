# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

import numpy as np
import pypowsybl.network as pn
import pytest
from energnn.graph import Graph, GraphStructure

from pypowsybl_to_energnn import PypowsyblConverter, TableConverter

SMALL_CONFIG = {
    "buses": TableConverter("get_buses", ports=["id"]),
    "lines": TableConverter("get_lines", ports=["bus1_id", "bus2_id"], features=["r", "x"]),
    "loads": TableConverter("get_loads", ports=["bus_id"], features=["p0", "q0"]),
}


@pytest.fixture(scope="module")
def network():
    return pn.create_ieee14()


@pytest.fixture(scope="module")
def graph(network):
    return PypowsyblConverter(SMALL_CONFIG)(network=network)


def test_returns_graph(graph):
    assert isinstance(graph, Graph)
    assert set(graph.hyper_edge_sets.keys()) == set(SMALL_CONFIG.keys())


def test_addresses_are_consecutive_integers(network, graph):
    n_addresses = len(graph.non_fictitious_addresses)
    assert n_addresses == len(network.get_buses())

    for hyper_edge_set in graph.hyper_edge_sets.values():
        if hyper_edge_set.port_dict is not None:
            for port_array in hyper_edge_set.port_dict.values():
                port_array = np.asarray(port_array)
                assert np.issubdtype(port_array.dtype, np.integer)
                assert np.all(port_array >= 0)
                assert np.all(port_array < n_addresses)


def test_features_are_finite_floats(graph):
    for hyper_edge_set in graph.hyper_edge_sets.values():
        if hyper_edge_set.feature_array is not None:
            feature_array = np.asarray(hyper_edge_set.feature_array)
            assert np.issubdtype(feature_array.dtype, np.floating)
            assert np.all(np.isfinite(feature_array))


def test_feature_names_match_feature_list(graph):
    feature_names = graph.hyper_edge_sets["lines"].feature_names
    assert set(feature_names.keys()) == {"r", "x"}


def test_conversion_is_deterministic(network, graph):
    other_graph = PypowsyblConverter(SMALL_CONFIG)(network=network)
    for k, hyper_edge_set in graph.hyper_edge_sets.items():
        other_hyper_edge_set = other_graph.hyper_edge_sets[k]
        if hyper_edge_set.port_dict is not None:
            for port_name, port_array in hyper_edge_set.port_dict.items():
                assert np.array_equal(np.asarray(port_array), np.asarray(other_hyper_edge_set.port_dict[port_name]))
        if hyper_edge_set.feature_array is not None:
            assert np.array_equal(np.asarray(hyper_edge_set.feature_array), np.asarray(other_hyper_edge_set.feature_array))


def test_the_config_is_amendable(network):
    # The whole override story: copy the dict, replace or add entries.
    config = dict(SMALL_CONFIG)
    config["loads"] = TableConverter("get_loads", ports=["bus_id"], features=["p0"])
    del config["lines"]
    graph = PypowsyblConverter(config)(network=network)

    assert "lines" not in graph.hyper_edge_sets
    assert set(graph.hyper_edge_sets["loads"].feature_names.keys()) == {"p0"}
    # The original config is left untouched.
    assert set(SMALL_CONFIG) == {"buses", "lines", "loads"}


def test_per_unit_is_enforced(network):
    network.per_unit = False
    PypowsyblConverter(SMALL_CONFIG)(network=network)
    assert network.per_unit is True
    PypowsyblConverter(SMALL_CONFIG, per_unit=False)(network=network)
    assert network.per_unit is False
    network.per_unit = True


def test_get_structure():
    assert isinstance(PypowsyblConverter(SMALL_CONFIG).get_structure(), GraphStructure)


def test_bus_breaker_config():
    # The bus/breaker view is a config like any other: the finer bus table, and the switches
    # that connect its buses. get_switches returns every switch of the network, but only the
    # retained ones belong to the view (the others are internal to a bus/breaker bus and have
    # empty bus_breaker_bus*_id); switches of bus/breaker-modelled voltage levels are always
    # reported as retained.
    def retained_switches(network, **_):
        return network.get_switches(all_attributes=True).reset_index().query("retained")

    config = {
        "buses": TableConverter("get_bus_breaker_view_buses", ports=["id"]),
        "switches": TableConverter(retained_switches, ports=["bus_breaker_bus1_id", "bus_breaker_bus2_id"]),
        "loads": TableConverter("get_loads", ports=["bus_breaker_bus_id"], features=["p0", "q0"]),
    }

    network = pn.create_four_substations_node_breaker_network()
    graph = PypowsyblConverter(config)(network=network)

    n_retained = int(network.get_switches().retained.sum())
    assert n_retained < len(network.get_switches())  # the fixture network does have non-retained switches
    ports = graph.hyper_edge_sets["switches"].port_dict
    assert np.asarray(ports["bus_breaker_bus1_id"]).shape[0] == n_retained

    # Every switch and load port must resolve to an actual bus/breaker bus: a mix-up between
    # views (bus_id vs bus_breaker_bus_id) would silently hang elements from phantom nodes.
    bus_ids = set(np.asarray(graph.hyper_edge_sets["buses"].port_dict["id"]).tolist())
    for k in ("bus_breaker_bus1_id", "bus_breaker_bus2_id"):
        assert set(np.asarray(ports[k]).tolist()) <= bus_ids
    assert set(np.asarray(graph.hyper_edge_sets["loads"].port_dict["bus_breaker_bus_id"]).tolist()) <= bus_ids
