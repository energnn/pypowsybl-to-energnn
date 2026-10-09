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
    "ac_warm_start_input": ready_to_use.AC_LOAD_FLOW_WARM_START_INPUT,
    "ac_input": ready_to_use.AC_LOAD_FLOW_INPUT,
    "ac_output": ready_to_use.AC_LOAD_FLOW_OUTPUT,
    "dc_input": ready_to_use.DC_LOAD_FLOW_INPUT,
    "dc_output": ready_to_use.DC_LOAD_FLOW_OUTPUT,
    "bus_breaker_ac_warm_start_input": ready_to_use.BUS_BREAKER_AC_LOAD_FLOW_WARM_START_INPUT,
    "bus_breaker_ac_input": ready_to_use.BUS_BREAKER_AC_LOAD_FLOW_INPUT,
    "bus_breaker_ac_output": ready_to_use.BUS_BREAKER_AC_LOAD_FLOW_OUTPUT,
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


def test_dc_feature_bundles_are_subsets_of_the_ac_ones():
    # Same invariant at the source: the per-class DC constants restrict the AC ones.
    for config in (ready_to_use.AC_LOAD_FLOW_WARM_START_INPUT,):
        for k, converter in config.items():
            cls = type(converter)
            for role in ("INPUT", "OUTPUT"):
                dc_bundle = getattr(cls, f"DC_LOAD_FLOW_{role}_FEATURES", None)
                if dc_bundle is not None:
                    assert set(dc_bundle) <= set(getattr(cls, f"AC_LOAD_FLOW_{role}_FEATURES")), (k, role)


def test_warm_start_input_concatenates_problem_and_solved_state():
    # The realistic GNN input is the AC problem warm-started by a first load flow: the
    # defaults of every class, i.e. its AC input bundle followed by its AC output bundle.
    assert set(ready_to_use.AC_LOAD_FLOW_WARM_START_INPUT) == set(ready_to_use.AC_LOAD_FLOW_INPUT)
    for k, converter in ready_to_use.AC_LOAD_FLOW_WARM_START_INPUT.items():
        cls = type(converter)
        expected = list(cls.AC_LOAD_FLOW_INPUT_FEATURES) + list(getattr(cls, "AC_LOAD_FLOW_OUTPUT_FEATURES", ()))
        assert converter.feature_list == expected, k
        assert converter.port_list == ready_to_use.AC_LOAD_FLOW_INPUT[k].port_list, k


def _bus_breaker_twin(port):
    return port.replace("bus", "bus_breaker_bus", 1)


def test_bus_breaker_configs_mirror_the_bus_view_ones():
    # Same assemblies in the finer view: every bus view class is there with its ports
    # remapped to their bus_breaker twins and identical features; the retained switches are
    # the only addition (input-only, hence absent from the output config).
    for bus_breaker, bus_view, extra in (
        (ready_to_use.BUS_BREAKER_AC_LOAD_FLOW_WARM_START_INPUT, ready_to_use.AC_LOAD_FLOW_WARM_START_INPUT, {"switches"}),
        (ready_to_use.BUS_BREAKER_AC_LOAD_FLOW_INPUT, ready_to_use.AC_LOAD_FLOW_INPUT, {"switches"}),
        (ready_to_use.BUS_BREAKER_AC_LOAD_FLOW_OUTPUT, ready_to_use.AC_LOAD_FLOW_OUTPUT, set()),
    ):
        assert set(bus_breaker) == set(bus_view) | extra
        for k, bus_view_converter in bus_view.items():
            assert bus_breaker[k].port_list == [_bus_breaker_twin(p) for p in bus_view_converter.port_list], k
            assert bus_breaker[k].feature_list == bus_view_converter.feature_list, k


def test_bus_breaker_configs_convert_a_node_breaker_network():
    # On a node/breaker network the switches class carries the retained switches, tied to
    # the bus/breaker view buses on both sides.
    network = pn.create_four_substations_node_breaker_network()
    lf.run_ac(network)
    config = ready_to_use.BUS_BREAKER_AC_LOAD_FLOW_WARM_START_INPUT
    graph = PypowsyblConverter(config)(network=network)
    _check_graph(config, graph)

    switches = graph.hyper_edge_sets["switches"]
    assert np.asarray(switches.feature_array).shape[0] > 0
    bus_addresses = set(np.asarray(graph.hyper_edge_sets["buses"].port_dict["id"]).tolist())
    for port in ("bus_breaker_bus1_id", "bus_breaker_bus2_id"):
        assert set(np.asarray(switches.port_dict[port]).tolist()) <= bus_addresses


def test_get_structure():
    for config in CONFIGS.values():
        assert isinstance(PypowsyblConverter(config).get_structure(), GraphStructure)
