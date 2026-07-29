# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

import numpy as np
import pypowsybl.loadflow as lf
import pypowsybl.network as pn
import pytest
from energnn.graph import Graph, GraphStructure

from pypowsybl_to_energnn.ready_to_use import ACLoadFlowInputConverter, ACLoadFlowOutputConverter


@pytest.fixture(scope="module", params=["ieee14", "ieee300"])
def network(request):
    network = getattr(pn, f"create_{request.param}")()
    lf.run_ac(network)
    network.per_unit = True
    return network


def _check_graph(converter, graph):
    assert isinstance(graph, Graph)
    assert set(graph.hyper_edge_sets.keys()) == set(converter.elements_converter_dict.keys())

    for k, hyper_edge_set in graph.hyper_edge_sets.items():
        elements_converter = converter.elements_converter_dict[k]

        if elements_converter.feature_list is None:
            assert hyper_edge_set.feature_array is None
        else:
            assert set(hyper_edge_set.feature_names.keys()) == set(elements_converter.feature_list)
            feature_array = np.asarray(hyper_edge_set.feature_array)
            assert feature_array.shape[-1] == len(elements_converter.feature_list)
            assert np.all(np.isfinite(feature_array))

        if elements_converter.port_list is None:
            assert hyper_edge_set.port_dict is None
        else:
            assert set(hyper_edge_set.port_dict.keys()) == set(elements_converter.port_list)


def test_ac_load_flow_input(network):
    converter = ACLoadFlowInputConverter()
    _check_graph(converter, converter(network=network))


def test_ac_load_flow_output(network):
    converter = ACLoadFlowOutputConverter()
    _check_graph(converter, converter(network=network))


def test_get_structure():
    assert isinstance(ACLoadFlowInputConverter().get_structure(), GraphStructure)
    assert isinstance(ACLoadFlowOutputConverter().get_structure(), GraphStructure)
