# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

import json

import numpy as np
import pandas as pd
import pypowsybl.loadflow as lf
import pypowsybl.network as pn
import pytest
from energnn.graph import Graph, GraphStructure

from pypowsybl_to_energnn import PypowsyblConverter, TableSpec, resolve_spec


@pytest.fixture(scope="module", params=["ieee14", "eurostag_tutorial_example1", "four_substations_node_breaker"])
def network(request):
    network = getattr(pn, f"create_{request.param}_network", None)
    network = network() if network is not None else getattr(pn, f"create_{request.param}")()
    lf.run_ac(network)
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


def test_default_input(network):
    converter = PypowsyblConverter()
    _check_graph(converter, converter(network=network))


def test_features_target_ac(network):
    # A training target: only the solved AC state. By default it keeps its addresses —
    # ports is an orthogonal option, not part of the target recipe.
    converter = PypowsyblConverter(features=("ac_pf_output",))
    graph = converter(network=network)
    _check_graph(converter, graph)
    v_mag = np.asarray(graph.hyper_edge_sets["buses"].feature_array)
    assert np.any(v_mag != 0)
    assert "id" in graph.hyper_edge_sets["buses"].port_dict
    # Classes without output columns (e.g. HVDC lines) survive as ports-only classes.
    assert converter.spec["hvdc_lines"].features is None
    assert converter.spec["hvdc_lines"].ports is not None


def test_ports_false_strips_addresses(network):
    # ports=False for when the addresses are redundant, e.g. rows aligned with an input
    # graph extracted from the same network; ports-only classes are then dropped.
    converter = PypowsyblConverter(features=("ac_pf_output",), ports=False)
    graph = converter(network=network)
    _check_graph(converter, graph)
    assert graph.hyper_edge_sets["buses"].port_dict is None
    assert "hvdc_lines" not in converter.spec


def test_features_target_dc(network):
    lf.run_dc(network)
    converter = PypowsyblConverter(features=("dc_pf_output",), ports=False)
    graph = converter(network=network)
    _check_graph(converter, graph)
    # Reactive-only devices and buses carry no DC output: they must be dropped entirely.
    for k in ("buses", "shunts", "static_var_compensators"):
        assert k not in converter.spec
    lf.run_ac(network)  # restore the AC solution for the other module-scoped tests


def test_feature_groups_are_cumulative(network):
    # The typical GNN input: the problem data plus the state solved by a first power flow.
    converter = PypowsyblConverter(features=("ac_pf_input", "ac_pf_output"))
    graph = converter(network=network)
    _check_graph(converter, graph)
    feature_names = graph.hyper_edge_sets["lines"].feature_names
    assert "r" in feature_names and "p1" in feature_names


def test_features_combine_with_structure_options(network):
    # Feature groups are orthogonal to satellites and infrastructure: e.g. N-1 screening
    # wants flows and operational limits in the same graph.
    converter = PypowsyblConverter(
        features=("ac_pf_input", "ac_pf_output"),
        satellites={"operational_limits": "connect"},
        infrastructure={"voltage_levels": "connect"},
    )
    graph = converter(network=network)
    _check_graph(converter, graph)
    assert "operational_limits" in graph.hyper_edge_sets
    assert "voltage_levels" in graph.hyper_edge_sets


def test_dc_pf_input_is_the_active_subset(network):
    # The DC problem data drops the reactive- and voltage-related columns.
    converter = PypowsyblConverter(features=("dc_pf_input",))
    graph = converter(network=network)
    _check_graph(converter, graph)
    loads = graph.hyper_edge_sets["loads"].feature_names
    assert "p0" in loads and "q0" not in loads
    lines = graph.hyper_edge_sets["lines"].feature_names
    assert "x" in lines and "r" not in lines


def test_ac_groups_cover_dc_groups():
    # Registry invariant: the dc_pf_* groups are subsets of their ac_pf_* counterparts —
    # requesting AC always covers what DC would give, which is why mixing them is rejected.
    from pypowsybl_to_energnn.parametric.registry import _TABLES

    for name, table in _TABLES.items():
        assert set(table.dc_pf_input) <= set(table.ac_pf_input), name
        assert set(table.dc_pf_output) <= set(table.ac_pf_output), name


def test_per_unit_is_enforced(network):
    network.per_unit = False
    PypowsyblConverter()(network=network)
    assert network.per_unit is True
    PypowsyblConverter(per_unit=False)(network=network)
    assert network.per_unit is False
    network.per_unit = True


def test_bus_breaker_topology_view():
    network = pn.create_four_substations_node_breaker_network()
    bus_branch = PypowsyblConverter()(network=network)
    bus_breaker_converter = PypowsyblConverter(topology_view="bus_breaker")
    bus_breaker = bus_breaker_converter(network=network)
    _check_graph(bus_breaker_converter, bus_breaker)

    assert "switches" in bus_breaker.hyper_edge_sets
    n_buses = lambda g: np.asarray(g.hyper_edge_sets["buses"].port_dict["id"]).shape[0]  # noqa: E731
    assert n_buses(bus_breaker) > n_buses(bus_branch)


def test_bus_breaker_switches_retained_only():
    network = pn.create_four_substations_node_breaker_network()
    switches = network.get_switches()
    n_retained = int(switches.retained.sum())
    assert n_retained < len(switches)  # the fixture network does have non-retained switches

    graph = PypowsyblConverter(topology_view="bus_breaker")(network=network)
    ports = graph.hyper_edge_sets["switches"].port_dict
    assert np.asarray(ports["bus_breaker_bus1_id"]).shape[0] == n_retained

    # Retained switch ports must be actual bus/breaker buses — non-retained switches have empty
    # bus_breaker_bus*_id and would inject a spurious '' address into the graph.
    bus_ids = set(np.asarray(graph.hyper_edge_sets["buses"].port_dict["id"]).tolist())
    for k in ("bus_breaker_bus1_id", "bus_breaker_bus2_id"):
        assert set(np.asarray(ports[k]).tolist()) <= bus_ids


def test_bus_breaker_switches_of_bus_breaker_voltage_level():
    # Switches of bus/breaker-modelled voltage levels are reported as retained by pypowsybl:
    # the "retained" filter must keep them.
    network = pn.create_empty()
    network.create_substations(id="S")
    network.create_voltage_levels(id="VL", substation_id="S", topology_kind="BUS_BREAKER", nominal_v=400.0)
    network.create_buses(id=["B1", "B2"], voltage_level_id=["VL", "VL"])
    network.create_switches(id="COUPLER", voltage_level_id="VL", kind="BREAKER", bus1_id="B1", bus2_id="B2", open=False)

    graph = PypowsyblConverter(topology_view="bus_breaker")(network=network)
    assert np.asarray(graph.hyper_edge_sets["switches"].port_dict["bus_breaker_bus1_id"]).shape[0] == 1


@pytest.mark.parametrize("topology_view", ["bus_branch", "bus_breaker"])
def test_element_bus_ports_live_in_the_bus_table(topology_view):
    # Each topology view reads bus ids from a different column (bus_id vs bus_breaker_bus_id):
    # check that the ids picked from element tables are consistent with the id space of the bus
    # table of the same view — a column mix-up would silently disconnect elements from buses.
    network = pn.create_four_substations_node_breaker_network()
    graph = PypowsyblConverter(topology_view=topology_view)(network=network)
    bus_ids = set(np.asarray(graph.hyper_edge_sets["buses"].port_dict["id"]).tolist())
    for k in ("loads", "generators", "lines", "two_windings_transformers", "shunts"):
        for port, array in graph.hyper_edge_sets[k].port_dict.items():
            if "bus" in port:
                assert set(np.asarray(array).tolist()) <= bus_ids, (k, port)


def test_dangling_ports_are_isolated():
    # Disconnected elements have bus_id == '' in the bus view. A shared '' address would
    # spuriously connect them all through a single phantom node: each one must instead hang
    # from its own isolated address.
    network = pn.create_four_substations_node_breaker_network()
    network.update_loads(id=["LD1", "LD6"], connected=[False, False])
    graph = PypowsyblConverter()(network=network)

    load_ids = list(network.get_loads().index)
    ports = np.asarray(graph.hyper_edge_sets["loads"].port_dict["bus_id"])
    ld1, ld6 = ports[load_ids.index("LD1")], ports[load_ids.index("LD6")]
    bus_ids = set(np.asarray(graph.hyper_edge_sets["buses"].port_dict["id"]).tolist())
    assert ld1 != ld6
    assert ld1 not in bus_ids and ld6 not in bus_ids

    # Deterministic: converting again yields the same addresses.
    graph2 = PypowsyblConverter()(network=network)
    np.testing.assert_array_equal(ports, np.asarray(graph2.hyper_edge_sets["loads"].port_dict["bus_id"]))


def test_dangling_substation_ports_are_isolated():
    # Voltage levels without a substation have substation_id == '': same phantom-node hazard.
    network = pn.create_empty()
    network.create_voltage_levels(id=["VL1", "VL2"], topology_kind=["BUS_BREAKER", "BUS_BREAKER"], nominal_v=[400.0, 400.0])
    network.create_buses(id=["B1", "B2"], voltage_level_id=["VL1", "VL2"])
    converter = PypowsyblConverter(infrastructure={"voltage_levels": "connect", "substations": "connect"})
    graph = converter(network=network)
    substation_ports = np.asarray(graph.hyper_edge_sets["voltage_levels"].port_dict["substation_id"])
    assert substation_ports[0] != substation_ports[1]


def test_regulation_ports():
    with_regulation = PypowsyblConverter()
    without_regulation = PypowsyblConverter(regulation=False)
    assert "regulated_bus_id" in with_regulation.spec["generators"].ports
    assert "regulated_bus_id" not in without_regulation.spec["generators"].ports


def test_satellites_connect():
    network = pn.create_eurostag_tutorial_example1_network()
    converter = PypowsyblConverter(satellites={"operational_limits": "connect", "ratio_tap_changer_steps": "connect"})
    graph = converter(network=network)
    _check_graph(converter, graph)
    assert np.asarray(graph.hyper_edge_sets["operational_limits"].port_dict["element_id"]).shape[0] > 0
    assert np.asarray(graph.hyper_edge_sets["ratio_tap_changer_steps"].port_dict["id"]).shape[0] > 0


def test_satellites_merge():
    network = pn.create_eurostag_tutorial_example1_network()
    converter = PypowsyblConverter(satellites={"ratio_tap_changers": "merge"})
    graph = converter(network=network)
    _check_graph(converter, graph)

    feature_names = graph.hyper_edge_sets["two_windings_transformers"].feature_names
    assert "rtc_tap" in feature_names
    # NGEN_NHV1 has no ratio tap changer: its merged features must fall back to 0, not NaN.
    features = np.asarray(graph.hyper_edge_sets["two_windings_transformers"].feature_array)
    assert np.all(np.isfinite(features))


def test_satellites_merge_variable_cardinality_is_rejected():
    with pytest.raises(ValueError, match="cannot be merged"):
        PypowsyblConverter(satellites={"operational_limits": "merge"})


def test_satellites_unknown_name_is_rejected():
    with pytest.raises(ValueError, match="Unknown satellites"):
        PypowsyblConverter(satellites={"foo": "merge"})
    with pytest.raises(ValueError, match="Invalid mode"):
        PypowsyblConverter(satellites={"operational_limits": "bar"})


def test_infrastructure_connect(network):
    converter = PypowsyblConverter(infrastructure={"voltage_levels": "connect", "substations": "connect", "areas": "connect"})
    graph = converter(network=network)
    _check_graph(converter, graph)
    for k in ("voltage_levels", "substations", "areas", "areas_voltage_levels"):
        assert k in graph.hyper_edge_sets
    assert "voltage_level_id" in converter.spec["buses"].ports
    assert "substation_id" in converter.spec["voltage_levels"].ports


def test_infrastructure_connect_is_level_by_level(network):
    converter = PypowsyblConverter(infrastructure={"voltage_levels": "connect"})
    graph = converter(network=network)
    _check_graph(converter, graph)
    assert "voltage_levels" in graph.hyper_edge_sets
    for k in ("substations", "areas", "areas_voltage_levels"):
        assert k not in graph.hyper_edge_sets
    # Without the substations level, voltage levels must not carry a dangling substation port.
    assert converter.spec["voltage_levels"].ports == ("id",)


def test_infrastructure_merge(network):
    # Merged levels add no hyper-edge class: their features are copied down onto the buses.
    converter = PypowsyblConverter(infrastructure={"voltage_levels": "merge", "substations": "merge"})
    graph = converter(network=network)
    _check_graph(converter, graph)
    for k in ("voltage_levels", "substations"):
        assert k not in graph.hyper_edge_sets
    feature_names = graph.hyper_edge_sets["buses"].feature_names
    assert "voltage_level_nominal_v" in feature_names
    assert "substation_country" in feature_names  # bus → voltage level → substation chain join

    nominal_v = np.asarray(graph.hyper_edge_sets["buses"].feature_array)[
        ..., list(feature_names).index("voltage_level_nominal_v")
    ]
    assert np.any(nominal_v != 0)


def test_infrastructure_merge_onto_connected_voltage_levels(network):
    # Substation features land on the voltage-level class when it exists as such.
    converter = PypowsyblConverter(infrastructure={"voltage_levels": "connect", "substations": "merge"})
    graph = converter(network=network)
    _check_graph(converter, graph)
    assert "substations" not in graph.hyper_edge_sets
    assert "substation_country" in graph.hyper_edge_sets["voltage_levels"].feature_names


def test_infrastructure_works_in_bus_breaker_view():
    # Both bus tables carry voltage_level_id: the attachment is identical in both views.
    network = pn.create_four_substations_node_breaker_network()
    converter = PypowsyblConverter(topology_view="bus_breaker", infrastructure={"voltage_levels": "merge"})
    graph = converter(network=network)
    _check_graph(converter, graph)
    assert "voltage_level_nominal_v" in graph.hyper_edge_sets["buses"].feature_names


def test_infrastructure_invalid_options():
    with pytest.raises(ValueError, match="Unknown infrastructure"):
        PypowsyblConverter(infrastructure={"foo": "merge"})
    with pytest.raises(ValueError, match="must be a dict"):
        PypowsyblConverter(infrastructure=("voltage_levels",))
    with pytest.raises(ValueError, match="cannot be merged"):
        PypowsyblConverter(infrastructure={"areas": "merge"})
    with pytest.raises(ValueError, match="voltage_levels"):
        PypowsyblConverter(infrastructure={"substations": "connect"})


def test_extensions_merge():
    network = pn.create_eurostag_tutorial_example1_network()
    network.create_extensions("activePowerControl", id="GEN", droop=4.0, participate=True)
    network.create_extensions("referencePriorities", id="GEN", priority=1)
    converter = PypowsyblConverter(extensions={"activePowerControl": "merge", "referencePriorities": "merge"})
    graph = converter(network=network)
    _check_graph(converter, graph)

    feature_names = graph.hyper_edge_sets["generators"].feature_names
    assert "apc_droop" in feature_names and "reference_priority" in feature_names
    droop = np.asarray(graph.hyper_edge_sets["generators"].feature_array)[..., list(feature_names).index("apc_droop")]
    assert np.any(droop != 0)
    # activePowerControl spans several carrier classes: batteries get the columns too.
    assert "apc_droop" in graph.hyper_edge_sets["batteries"].feature_names


def test_extensions_connect():
    network = pn.create_eurostag_tutorial_example1_network()
    network.create_extensions("activePowerControl", id="GEN", droop=4.0, participate=True)
    converter = PypowsyblConverter(extensions={"activePowerControl": "connect"})
    graph = converter(network=network)
    _check_graph(converter, graph)
    # The carrier id is recovered from the extension table index as a port.
    assert np.asarray(graph.hyper_edge_sets["active_power_controls"].port_dict["id"]).shape[0] == 1


def test_extensions_slack_terminal():
    network = pn.create_eurostag_tutorial_example1_network()
    lf.run_ac(network, parameters=lf.Parameters(write_slack_bus=True))
    converter = PypowsyblConverter(extensions={"slackTerminal": "connect"})
    graph = converter(network=network)
    _check_graph(converter, graph)
    ports = graph.hyper_edge_sets["slack_terminals"].port_dict
    # The slack bus is a bus-view address: it must live in the bus table of the same view.
    bus_ids = set(np.asarray(graph.hyper_edge_sets["buses"].port_dict["id"]).tolist())
    assert set(np.asarray(ports["bus_id"]).tolist()) <= bus_ids


def test_extensions_secondary_voltage_control():
    network = pn.create_eurostag_tutorial_example1_network()
    zones = pd.DataFrame({"name": ["z1"], "target_v": [400.0], "bus_ids": ["NHV1"]}).set_index("name")
    units = pd.DataFrame({"unit_id": ["GEN"], "participate": [True], "zone_name": ["z1"]}).set_index("unit_id")
    network.create_extensions("secondaryVoltageControl", [zones, units])

    converter = PypowsyblConverter(topology_view="bus_breaker", extensions={"secondaryVoltageControl": "connect"})
    graph = converter(network=network)
    _check_graph(converter, graph)
    zones_ports = graph.hyper_edge_sets["secondary_voltage_control_zones"].port_dict
    units_ports = graph.hyper_edge_sets["secondary_voltage_control_units"].port_dict
    # The zone name is the address linking units to their zone (areas_voltage_levels pattern):
    # both classes must resolve 'z1' to the same integer address.
    assert np.asarray(zones_ports["name"]).tolist() == np.asarray(units_ports["zone_name"]).tolist()
    # The pilot-point bus is a bus/breaker-view address: it must live in that view's bus table.
    bus_ids = set(np.asarray(graph.hyper_edge_sets["buses"].port_dict["id"]).tolist())
    assert set(np.asarray(zones_ports["bus_ids"]).tolist()) <= bus_ids


def test_extensions_bus_ports_live_in_a_single_view():
    # Extension tables expose one bus-id namespace only: the port is dropped in the other
    # view rather than silently hanging from phantom addresses.
    zones = PypowsyblConverter(extensions={"secondaryVoltageControl": "connect"})
    assert "bus_ids" not in zones.spec["secondary_voltage_control_zones"].ports
    slack = PypowsyblConverter(topology_view="bus_breaker", extensions={"slackTerminal": "connect"})
    assert "bus_id" not in slack.spec["slack_terminals"].ports


def test_extensions_invalid_options():
    with pytest.raises(ValueError, match="cannot be merged"):
        PypowsyblConverter(extensions={"slackTerminal": "merge"})
    with pytest.raises(ValueError, match="cannot be merged"):
        PypowsyblConverter(extensions={"secondaryVoltageControl": "merge"})
    with pytest.raises(ValueError, match="Unknown extensions"):
        PypowsyblConverter(extensions={"foo": "merge"})
    with pytest.raises(ValueError, match="must be a dict"):
        PypowsyblConverter(extensions=("activePowerControl",))


def test_spec_round_trip(network):
    converter = PypowsyblConverter(
        topology_view="bus_breaker",
        satellites={"ratio_tap_changers": "merge"},
        infrastructure={"substations": "merge"},  # exercises the on/via serialization
        extensions={"activePowerControl": "merge", "slackTerminal": "connect"},  # and getter_args
    )
    spec_dict = json.loads(json.dumps(converter.to_dict()))
    reloaded = PypowsyblConverter.from_spec(spec_dict)

    assert reloaded.spec == converter.spec
    graph, reloaded_graph = converter(network=network), reloaded(network=network)
    for k in converter.spec:
        original = graph.hyper_edge_sets[k].feature_array
        recovered = reloaded_graph.hyper_edge_sets[k].feature_array
        assert (original is None) == (recovered is None)
        if original is not None:
            np.testing.assert_array_equal(np.asarray(original), np.asarray(recovered))


def test_spec_is_amendable(network):
    spec = resolve_spec()
    spec["loads"] = TableSpec("get_loads", ports=("bus_id",), features=("p0", "q0"))
    del spec["batteries"]
    converter = PypowsyblConverter.from_spec(spec)
    graph = converter(network=network)
    assert "batteries" not in graph.hyper_edge_sets
    assert set(graph.hyper_edge_sets["loads"].feature_names.keys()) == {"p0", "q0"}


def test_unknown_column_message():
    network = pn.create_ieee14()
    converter = PypowsyblConverter.from_spec({"loads": TableSpec("get_loads", ports=("bus_id",), features=("foo",))})
    with pytest.raises(ValueError, match="'foo'.*get_loads|get_loads.*'foo'"):
        converter(network=network)


def test_invalid_options():
    with pytest.raises(ValueError, match="Invalid topology_view"):
        PypowsyblConverter(topology_view="foo")
    with pytest.raises(ValueError, match="Invalid topology_view"):
        PypowsyblConverter(topology_view="node_breaker")  # dropped from the supported views
    with pytest.raises(ValueError, match="Unknown feature groups"):
        PypowsyblConverter(features=("foo",))
    with pytest.raises(ValueError, match="iterable of feature groups"):
        PypowsyblConverter(features="ac_pf_input")  # a bare string would be iterated character by character
    with pytest.raises(ValueError, match="mix AC and DC"):
        PypowsyblConverter(features=("ac_pf_input", "dc_pf_output"))
    with pytest.raises(NotImplementedError):
        PypowsyblConverter(main_component_only=True)


def test_get_structure():
    assert isinstance(PypowsyblConverter().get_structure(), GraphStructure)
    target = PypowsyblConverter(features=("ac_pf_output",), ports=False)
    assert isinstance(target.get_structure(), GraphStructure)
