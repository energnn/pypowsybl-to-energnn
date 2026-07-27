# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

import numpy as np
import pypowsybl.network as pn
import pytest
from energnn.converter import Converter
from energnn.graph import Graph, GraphStructure

from pypowsybl_to_energnn import elements


class SmallConverter(Converter):
    elements_converter_dict = {
        "buses": elements.BusesConverter(["id"], None),
        "lines": elements.LinesConverter(["bus1_id", "bus2_id"], ["r", "x"]),
        "loads": elements.LoadsConverter(["bus_id"], ["p0", "q0"]),
    }


@pytest.fixture(scope="module")
def network():
    return pn.create_ieee14()


@pytest.fixture(scope="module")
def graph(network):
    return SmallConverter()(network=network)


def test_returns_graph(graph):
    assert isinstance(graph, Graph)
    assert set(graph.hyper_edge_sets.keys()) == set(SmallConverter.elements_converter_dict.keys())


def test_addresses_are_consecutive_integers(network, graph):
    n_addresses = len(graph.non_fictitious_addresses)
    assert n_addresses == len(network.get_buses())

    for hyper_edge_set in graph.hyper_edge_sets.values():
        if hyper_edge_set.port_dict is not None:
            for port_array in hyper_edge_set.port_dict.values():
                port_array = np.asarray(port_array)
                # energnn stores ports as float arrays, but their values must be integers.
                assert np.array_equal(port_array, np.round(port_array))
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
    other_graph = SmallConverter()(network=network)
    for k, hyper_edge_set in graph.hyper_edge_sets.items():
        other_hyper_edge_set = other_graph.hyper_edge_sets[k]
        if hyper_edge_set.port_dict is not None:
            for port_name, port_array in hyper_edge_set.port_dict.items():
                assert np.array_equal(np.asarray(port_array), np.asarray(other_hyper_edge_set.port_dict[port_name]))
        if hyper_edge_set.feature_array is not None:
            assert np.array_equal(np.asarray(hyper_edge_set.feature_array), np.asarray(other_hyper_edge_set.feature_array))


def test_get_structure():
    structure = SmallConverter().get_structure()
    assert isinstance(structure, GraphStructure)
