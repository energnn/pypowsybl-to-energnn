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

from pypowsybl_to_energnn import PypowsyblConverter, ready_to_use

CONFIGS = {
    "ac_input": ready_to_use.AC_LOAD_FLOW_INPUT,
    "ac_output": ready_to_use.AC_LOAD_FLOW_OUTPUT,
    "dc_input": ready_to_use.DC_LOAD_FLOW_INPUT,
    "dc_output": ready_to_use.DC_LOAD_FLOW_OUTPUT,
}


@pytest.fixture(scope="module", params=["ieee14", "ieee300", "eurostag_tutorial_example1_network"])
def network(request):
    network = getattr(pn, f"create_{request.param}")()
    lf.run_ac(network)
    return network


def _check_graph(config, graph):
    assert isinstance(graph, Graph)
    assert set(graph.hyper_edge_sets.keys()) == set(config.keys())

    for k, hyper_edge_set in graph.hyper_edge_sets.items():
        elements_converter = config[k]

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


@pytest.mark.parametrize("config_name", CONFIGS)
def test_configs_convert(network, config_name):
    if config_name.startswith("dc"):
        lf.run_dc(network)
    config = CONFIGS[config_name]
    _check_graph(config, PypowsyblConverter(config)(network=network))
    if config_name.startswith("dc"):
        lf.run_ac(network)  # restore the AC solution for the other module-scoped tests


def test_ac_output_carries_the_solved_state(network):
    # Output columns are NaN (0 downstream) until a power flow has run: the fixture ran one.
    graph = PypowsyblConverter(ready_to_use.AC_LOAD_FLOW_OUTPUT)(network=network)
    v_mag = np.asarray(graph.hyper_edge_sets["buses"].feature_array)
    assert np.any(v_mag != 0)


def test_dc_configs_are_the_active_subsets_of_the_ac_ones():
    # The DC problem is the active-only restriction of the AC one: every DC class and every
    # DC column must exist in the AC counterpart — requesting AC always covers DC, and the
    # configs cannot drift apart silently.
    for dc, ac in (
        (ready_to_use.DC_LOAD_FLOW_INPUT, ready_to_use.AC_LOAD_FLOW_INPUT),
        (ready_to_use.DC_LOAD_FLOW_OUTPUT, ready_to_use.AC_LOAD_FLOW_OUTPUT),
    ):
        assert set(dc) <= set(ac)
        for k, dc_converter in dc.items():
            assert set(dc_converter.port_list) <= set(ac[k].port_list), k
            assert set(dc_converter.feature_list or []) <= set(ac[k].feature_list or []), k


def test_get_structure():
    for config in CONFIGS.values():
        assert isinstance(PypowsyblConverter(config).get_structure(), GraphStructure)
