# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

import numpy as np
import pandas as pd
import pypowsybl.network as pn
import pytest

from pypowsybl_to_energnn import (
    Areas,
    AreasVoltageLevels,
    Batteries,
    BusBreakerViewBuses,
    Buses,
    DanglingLines,
    Generators,
    HvdcLines,
    LccConverterStations,
    Lines,
    Loads,
    OperationalLimits,
    PhaseTapChangers,
    PhaseTapChangerSteps,
    PypowsyblConverter,
    RatioTapChangers,
    RatioTapChangerSteps,
    ReactiveCapabilityCurvePoints,
    SecondaryVoltageControlUnits,
    SecondaryVoltageControlZones,
    ShuntCompensators,
    StaticVarCompensators,
    Substations,
    Switches,
    ThreeWindingsTransformers,
    TwoWindingsTransformers,
    VoltageLevels,
    VscConverterStations,
)

CLASSES_AND_GETTERS = [
    (Areas, "get_areas"),
    (AreasVoltageLevels, "get_areas_voltage_levels"),
    (Batteries, "get_batteries"),
    (BusBreakerViewBuses, "get_bus_breaker_view_buses"),
    (Buses, "get_buses"),
    (DanglingLines, "get_dangling_lines"),
    (Generators, "get_generators"),
    (HvdcLines, "get_hvdc_lines"),
    (LccConverterStations, "get_lcc_converter_stations"),
    (Lines, "get_lines"),
    (Loads, "get_loads"),
    (PhaseTapChangers, "get_phase_tap_changers"),
    (PhaseTapChangerSteps, "get_phase_tap_changer_steps"),
    (RatioTapChangers, "get_ratio_tap_changers"),
    (RatioTapChangerSteps, "get_ratio_tap_changer_steps"),
    (ReactiveCapabilityCurvePoints, "get_reactive_capability_curve_points"),
    (ShuntCompensators, "get_shunt_compensators"),
    (StaticVarCompensators, "get_static_var_compensators"),
    (Substations, "get_substations"),
    (ThreeWindingsTransformers, "get_3_windings_transformers"),
    (TwoWindingsTransformers, "get_2_windings_transformers"),
    (VoltageLevels, "get_voltage_levels"),
    (VscConverterStations, "get_vsc_converter_stations"),
]


@pytest.fixture(scope="module")
def ieee14():
    return pn.create_ieee14()


@pytest.fixture(scope="module")
def eurostag():
    return pn.create_eurostag_tutorial_example1_network()


@pytest.mark.parametrize("cls, getter", CLASSES_AND_GETTERS, ids=lambda p: getattr(p, "__name__", p))
def test_defaults_extract(ieee14, cls, getter):
    # Every class converts with its defaults on any network — including one where its table
    # is empty (no battery, no HVDC line, ... in the IEEE 14 test case).
    converter = cls()
    df_port, df_feature = converter(network=ieee14)

    assert list(df_port.columns) == converter.port_list
    assert len(df_port) == len(getattr(ieee14, getter)())
    if converter.feature_list is None:
        assert df_feature is None
    else:
        assert list(df_feature.columns) == converter.feature_list
        assert len(df_feature) == len(df_port)


def test_unknown_column_message_names_the_class(ieee14):
    converter = Lines(features=("foo",))
    with pytest.raises(ValueError, match=r"\['foo'\] not found in 'Lines'"):
        converter(network=ieee14)


def test_ratio_tap_changers_merge(eurostag):
    converter = TwoWindingsTransformers(ratio_tap_changer_features=TwoWindingsTransformers.RATIO_TAP_CHANGER_FEATURES)
    prefixed = [f"ratio_tap_changer_{f}" for f in TwoWindingsTransformers.RATIO_TAP_CHANGER_FEATURES]
    assert [f for f in converter.feature_list if f.startswith("ratio_tap_changer_")] == prefixed

    _, df_feature = converter(network=eurostag)
    transformer_ids = list(eurostag.get_2_windings_transformers().index)
    tap = df_feature["ratio_tap_changer_tap"]
    # NHV2_NLOAD has a ratio tap changer, NGEN_NHV1 does not (NaN, turned into 0 downstream).
    assert tap.notna()[transformer_ids.index("NHV2_NLOAD")]
    assert tap.isna()[transformer_ids.index("NGEN_NHV1")]


def test_phase_tap_changers_merge():
    # Column-by-column selection: joined features are requested like any other feature.
    network = pn.create_four_substations_node_breaker_network()
    converter = TwoWindingsTransformers(phase_tap_changer_features=("tap",))
    _, df_feature = converter(network=network)

    transformer_ids = list(network.get_2_windings_transformers().index)
    expected_tap = network.get_phase_tap_changers().loc["TWT", "tap"]
    assert df_feature["phase_tap_changer_tap"][transformer_ids.index("TWT")] == expected_tap


def test_three_windings_transformers():
    # One port per winding, and the aggregated limits gain a third side — previously the
    # THREE rows were silently dropped by the pivot.
    network = pn.create_micro_grid_be_network()
    converter = ThreeWindingsTransformers(
        operational_limit_features=("current_limit1", "current_limit2", "current_limit3", "has_current_limit3")
    )
    df_port, df_feature = converter(network=network)

    assert len(df_port) == 1
    buses = set(network.get_buses().index)
    for port in ("bus1_id", "bus2_id", "bus3_id"):
        assert set(df_port[port]) <= buses
    row = df_feature.iloc[0]
    assert row["current_limit1"] == 938.2
    assert row["current_limit2"] == 1705.8
    assert row["current_limit3"] == 17870.4
    assert row["has_current_limit3"] == True  # noqa: E712


def test_tap_changers_as_their_own_classes(eurostag):
    # The connect form: one hyper-edge per device, tied to its transformer and to the bus it
    # regulates — the remote-regulation edge the merged form cannot represent.
    df_port, df_feature = RatioTapChangers()(network=eurostag)
    assert df_port["id"].tolist() == ["NHV2_NLOAD"]
    assert df_port["regulating_bus_id"].tolist() == ["VLLOAD_0"]
    assert df_feature["target_v"].tolist() == [158.0]

    network = pn.create_four_substations_node_breaker_network()
    df_port, df_feature = PhaseTapChangers()(network=network)
    assert df_port["id"].tolist() == ["TWT"]
    assert df_port["regulating_bus_id"].tolist() == ["S1VL1_0"]
    assert df_feature["tap"].tolist() == [15.0]


def test_tap_changer_steps(eurostag):
    # One hyper-edge per (device, position): the discrete range of the changer, unbounded
    # per device, carried by the graph structure.
    df_port, df_feature = RatioTapChangerSteps()(network=eurostag)
    assert df_port["id"].tolist() == ["NHV2_NLOAD"] * 3
    assert df_feature["position"].tolist() == [0.0, 1.0, 2.0]
    assert df_feature["rho"].tolist() == pytest.approx([0.850567, 1.000667, 1.150767])

    network = pn.create_four_substations_node_breaker_network()
    df_port, df_feature = PhaseTapChangerSteps()(network=network)
    assert len(df_port) == len(network.get_phase_tap_changer_steps()) == 33
    assert set(df_port["id"]) == {"TWT"}
    assert df_feature["alpha"].iloc[0] == pytest.approx(-42.8)


def test_buses_merge_the_infrastructure_tables(eurostag):
    # voltage_levels and substations chain through voltage_level_id; joined columns land
    # prefixed, and the substation join also lands the plain substation_id, usable as a port.
    converter = Buses(
        ports=("id", "substation_id"),
        voltage_level_features=Buses.VOLTAGE_LEVEL_FEATURES,
        substation_features=("fictitious",),
    )
    df_port, df_feature = converter(network=eurostag)

    prefixed = [f"voltage_level_{f}" for f in Buses.VOLTAGE_LEVEL_FEATURES] + ["substation_fictitious"]
    assert converter.feature_list == ["v_mag"] + prefixed
    assert set(df_port["substation_id"]) <= set(eurostag.get_substations().index)
    nominal_v = dict(zip(df_port["id"], df_feature["voltage_level_nominal_v"]))
    assert nominal_v == {"VLGEN_0": 24.0, "VLHV1_0": 380.0, "VLHV2_0": 380.0, "VLLOAD_0": 150.0}


def test_infrastructure_chain():
    # The chain form: buses hang from their voltage level, voltage levels from their
    # substation, each tier a class of its own. Fresh network: PypowsyblConverter switches
    # it to per-unit, which would corrupt the shared fixture for raw-value assertions.
    network = pn.create_eurostag_tutorial_example1_network()
    config = {
        "buses": Buses(ports=("id", "voltage_level_id")),
        "voltage_levels": VoltageLevels(),
        "substations": Substations(),
    }
    graph = PypowsyblConverter(config)(network=network)

    bus_ports = graph.hyper_edge_sets["buses"].port_dict
    voltage_level_ports = graph.hyper_edge_sets["voltage_levels"].port_dict
    voltage_level_addresses = set(np.asarray(voltage_level_ports["id"]).tolist())
    assert set(np.asarray(bus_ports["voltage_level_id"]).tolist()) <= voltage_level_addresses
    substation_addresses = set(np.asarray(graph.hyper_edge_sets["substations"].port_dict["id"]).tolist())
    assert set(np.asarray(voltage_level_ports["substation_id"]).tolist()) <= substation_addresses


def test_areas_tie_to_their_voltage_levels():
    # The transversal tier: a voltage level can be enrolled in several areas, one relational
    # hyper-edge per (area, voltage level) pair.
    network = pn.create_eurostag_tutorial_example1_network()
    network.create_areas(id="control", area_type="ControlArea", interchange_target=100.0)
    network.create_areas(id="bidding", area_type="BiddingZone", interchange_target=50.0)
    network.create_areas_voltage_levels(id=["control", "control", "bidding"], voltage_level_id=["VLHV1", "VLHV2", "VLHV1"])

    df_port, df_feature = Areas()(network=network)
    assert df_port["id"].tolist() == ["control", "bidding"]
    assert df_feature["interchange_target"].tolist() == [100.0, 50.0]

    df_port, df_feature = AreasVoltageLevels()(network=network)
    assert df_feature is None
    memberships = set(zip(df_port["id"], df_port["voltage_level_id"]))
    assert memberships == {("control", "VLHV1"), ("control", "VLHV2"), ("bidding", "VLHV1")}
    assert set(df_port["voltage_level_id"]) <= set(network.get_voltage_levels().index)


def test_reactive_capability_curve_points():
    # One hyper-edge per curve point: the number of points per machine is not bounded, so
    # the curve is carried by the graph structure. Machines with min/max limits are absent.
    network = pn.create_four_substations_node_breaker_network()
    df_port, df_feature = ReactiveCapabilityCurvePoints()(network=network)

    raw = network.get_reactive_capability_curve_points()
    assert len(df_port) == len(raw) > 0
    machines = (
        set(network.get_generators().index)
        | set(network.get_batteries().index)
        | set(network.get_vsc_converter_stations().index)
    )
    assert set(df_port["id"]) <= machines
    # The first point of GH1, checked against the raw table.
    assert df_feature.iloc[0][["p", "min_q", "max_q"]].tolist() == [0.0, -769.3, 860.0]


def test_bus_breaker_view_buses(eurostag):
    # The finer topology nodes; their bus_id column bridges toward the bus view, and the
    # infrastructure joins are shared with Buses.
    converter = BusBreakerViewBuses(ports=("id", "bus_id"), voltage_level_features=("nominal_v",))
    df_port, df_feature = converter(network=eurostag)

    assert set(df_port["id"]) == set(eurostag.get_bus_breaker_view_buses().index)
    assert set(df_port["bus_id"]) <= set(eurostag.get_buses().index)
    assert converter.feature_list == ["v_mag", "voltage_level_nominal_v"]


def test_switches_keep_the_retained_ones():
    # Only the retained switches belong to the bus/breaker view: the others are internal to
    # a bus/breaker bus (empty bus columns) and are dropped.
    network = pn.create_four_substations_node_breaker_network()
    df_port, df_feature = Switches()(network=network)

    switches = network.get_switches(all_attributes=True)
    assert len(df_port) == switches["retained"].sum() > 0
    bus_breaker_buses = set(network.get_bus_breaker_view_buses().index)
    assert set(df_port["bus_breaker_bus1_id"]) <= bus_breaker_buses
    assert set(df_port["bus_breaker_bus2_id"]) <= bus_breaker_buses


def test_lines_operational_limits(eurostag):
    converter = Lines(
        operational_limit_features=("current_limit1", "current_limit2", "has_current_limit1", "has_current_limit2")
    )
    _, df_feature = converter(network=eurostag)

    line_ids = list(eurostag.get_lines().index)
    row = df_feature.iloc[line_ids.index("NHV1_NHV2_1")]
    # Values checked against get_operational_limits: the selected permanent CURRENT limits.
    assert row["current_limit1"] == 500.0
    assert row["current_limit2"] == 1100.0
    assert row["has_current_limit1"] == True  # noqa: E712
    assert row["has_current_limit2"] == True  # noqa: E712


def test_has_current_limit_tells_a_missing_limit_apart_from_a_zero_one():
    # A zero limit and no limit both become 0 downstream: the indicator disambiguates.
    network = pn.create_eurostag_tutorial_example1_network()
    network.create_operational_limits(
        element_id="NHV1_NHV2_2", side="ONE", name="permanent_limit", type="CURRENT", value=0.0, acceptable_duration=-1
    )
    converter = Lines(operational_limit_features=("current_limit1", "has_current_limit1"))
    _, df_feature = converter(network=network)

    line_ids = list(network.get_lines().index)
    row = df_feature.iloc[line_ids.index("NHV1_NHV2_2")]
    assert row["current_limit1"] == 0.0
    assert row["has_current_limit1"] == True  # noqa: E712


def test_transformers_operational_limits_missing_are_nan(eurostag):
    # The eurostag transformers carry no operational limit: the columns must still exist.
    converter = TwoWindingsTransformers(
        operational_limit_features=("current_limit1", "current_limit2", "has_current_limit1", "has_current_limit2")
    )
    _, df_feature = converter(network=eurostag)
    assert df_feature["current_limit1"].isna().all()
    assert df_feature["current_limit2"].isna().all()
    # Elements absent from the limits table: the indicator is NaN there, i.e. 0 downstream.
    assert df_feature["has_current_limit1"].isna().all()


def test_operational_limits_class_keeps_every_selected_thermal_limit(eurostag):
    # One hyper-edge per limit: the variable number of temporary limits per (element, side)
    # is carried by the graph structure instead of a fixed-width feature vector.
    df_port, df_feature = OperationalLimits()(network=eurostag)

    limits = eurostag.get_operational_limits(all_attributes=True).reset_index()
    expected = limits[limits["selected"] & (limits["type"] == "CURRENT")]
    assert len(df_port) == len(expected) == 9
    assert set(df_port["element_id"]) == {"NHV1_NHV2_1", "NHV1_NHV2_2"}
    assert df_feature["permanent"].sum() == 4

    mask = (df_port["element_id"] == "NHV1_NHV2_1") & df_feature["permanent"] & df_feature["side_one"]
    assert df_feature.loc[mask, "value"].tolist() == [500.0]


def test_operational_limits_class_empty_without_limits(ieee14):
    df_port, df_feature = OperationalLimits()(network=ieee14)
    assert len(df_port) == 0
    assert len(df_feature) == 0


def test_operational_limits_graph_ties_limits_to_their_element():
    # The carrying elements expose their id as a port, and the limits hang from it. Fresh
    # network: PypowsyblConverter switches it to per-unit, which would corrupt the shared
    # fixture for raw-value assertions.
    network = pn.create_eurostag_tutorial_example1_network()
    config = {
        "buses": Buses(),
        "lines": Lines(ports=("id", "bus1_id", "bus2_id")),
        "operational_limits": OperationalLimits(),
    }
    graph = PypowsyblConverter(config)(network=network)

    limit_ports = graph.hyper_edge_sets["operational_limits"].port_dict
    line_addresses = set(np.asarray(graph.hyper_edge_sets["lines"].port_dict["id"]).tolist())
    assert set(np.asarray(limit_ports["element_id"]).tolist()) <= line_addresses


def test_dangling_lines_operational_limits():
    # Dangling lines are single-sided: their permanent limit has side NONE and lands in a
    # single current_limit column.
    network = pn.create_eurostag_tutorial_example1_network()
    network.create_dangling_lines(
        id="DL", voltage_level_id="VLLOAD", bus_id="NLOAD", p0=10.0, q0=3.0, r=1.0, x=10.0, g=0.0, b=0.0
    )
    network.create_operational_limits(
        element_id="DL", side="NONE", name="permanent_limit", type="CURRENT", value=250.0, acceptable_duration=-1
    )

    _, df_feature = DanglingLines(operational_limit_features=("current_limit", "has_current_limit"))(network=network)
    assert df_feature["current_limit"].tolist() == [250.0]
    assert df_feature["has_current_limit"].tolist() == [True]


def test_active_power_control_merge():
    network = pn.create_ieee14()
    network.create_extensions("activePowerControl", id="B1-G", droop=4.0, participate=True)

    converter = Generators(active_power_control_features=("droop", "participate"))
    _, df_feature = converter(network=network)

    generator_ids = list(network.get_generators().index)
    droop = df_feature["active_power_control_droop"]
    assert droop[generator_ids.index("B1-G")] == 4.0
    # Generators without the extension get NaN (0 downstream).
    assert droop.isna().sum() == len(generator_ids) - 1


def test_hvdc_lines_extensions_merge():
    network = pn.create_four_substations_node_breaker_network()
    network.create_extensions("hvdcAngleDroopActivePowerControl", id="HVDC1", droop=0.1, p0=100.0, enabled=True)
    network.create_extensions("hvdcOperatorActivePowerRange", id="HVDC1", opr_from_cs1_to_cs2=500.0, opr_from_cs2_to_cs1=400.0)

    converter = HvdcLines(
        hvdc_angle_droop_active_power_control_features=HvdcLines.HVDC_ANGLE_DROOP_ACTIVE_POWER_CONTROL_FEATURES,
        hvdc_operator_active_power_range_features=("opr_from_cs1_to_cs2",),
    )
    _, df_feature = converter(network=network)

    hvdc_ids = list(network.get_hvdc_lines().index)
    droop = df_feature["hvdc_angle_droop_active_power_control_droop"]
    assert droop[hvdc_ids.index("HVDC1")] == pytest.approx(0.1)
    assert df_feature["hvdc_operator_active_power_range_opr_from_cs1_to_cs2"][hvdc_ids.index("HVDC1")] == 500.0
    # HVDC2 carries neither extension: NaN, 0 downstream.
    assert droop.isna()[hvdc_ids.index("HVDC2")]


def test_standby_automaton_merge():
    network = pn.create_four_substations_node_breaker_network()
    network.create_extensions(
        "standbyAutomaton",
        id="SVC",
        standby=True,
        b0=0.0001,
        low_voltage_threshold=390.0,
        low_voltage_setpoint=395.0,
        high_voltage_threshold=410.0,
        high_voltage_setpoint=405.0,
    )

    converter = StaticVarCompensators(standby_automaton_features=("b0",))
    _, df_feature = converter(network=network)

    compensator_ids = list(network.get_static_var_compensators().index)
    assert df_feature["standby_automaton_b0"][compensator_ids.index("SVC")] == pytest.approx(0.0001)


@pytest.fixture()
def eurostag_with_secondary_voltage_control():
    network = pn.create_eurostag_tutorial_example1_network()
    zones = pd.DataFrame.from_records(index="name", data=[{"name": "z1", "target_v": 400.0, "bus_ids": "NLOAD,NHV2"}])
    units = pd.DataFrame.from_records(index="unit_id", data=[{"unit_id": "GEN", "participate": True, "zone_name": "z1"}])
    network.create_extensions("secondaryVoltageControl", [zones, units])
    return network


def test_secondary_voltage_control_zones(eurostag_with_secondary_voltage_control):
    df_port, df_feature = SecondaryVoltageControlZones()(network=eurostag_with_secondary_voltage_control)

    # One hyper-edge per zone: the first resolvable candidate of "NLOAD,NHV2" wins,
    # translated into its bus view bus.
    assert df_port["name"].tolist() == ["z1"]
    assert df_port["pilot_bus_id"].tolist() == ["VLLOAD_0"]
    assert df_feature["target_v"].tolist() == [400.0]


def test_secondary_voltage_control_pilot_bus_resolution():
    # findPilotBus semantics: candidates tried in order, unresolvable ids skipped, a zone
    # with no resolvable candidate left dangling — in both views.
    network = pn.create_eurostag_tutorial_example1_network()
    zones = pd.DataFrame.from_records(
        index="name",
        data=[
            {"name": "z1", "target_v": 380.0, "bus_ids": "UNKNOWN,NHV2"},
            {"name": "z2", "target_v": 225.0, "bus_ids": "UNKNOWN"},
        ],
    )
    units = pd.DataFrame.from_records(
        index="unit_id",
        data=[
            {"unit_id": "GEN", "participate": True, "zone_name": "z1"},
            {"unit_id": "GEN2", "participate": True, "zone_name": "z2"},
        ],
    )
    network.create_extensions("secondaryVoltageControl", [zones, units])

    converter = SecondaryVoltageControlZones(ports=("name", "pilot_bus_id", "pilot_bus_breaker_bus_id"))
    df_port, _ = converter(network=network)
    assert df_port["pilot_bus_id"].tolist() == ["VLHV2_0", "__dangling__z2__pilot_bus_id"]
    assert df_port["pilot_bus_breaker_bus_id"].tolist() == ["NHV2", "__dangling__z2__pilot_bus_breaker_bus_id"]


def test_secondary_voltage_control_busbar_section_pilot():
    # In a node/breaker network the pilot point is located by a busbar section id, resolved
    # into the section's bus in each view.
    network = pn.create_four_substations_node_breaker_network()
    zones = pd.DataFrame.from_records(index="name", data=[{"name": "za", "target_v": 400.0, "bus_ids": "S1VL2_BBS1"}])
    units = pd.DataFrame.from_records(index="unit_id", data=[{"unit_id": "GH1", "participate": True, "zone_name": "za"}])
    network.create_extensions("secondaryVoltageControl", [zones, units])

    converter = SecondaryVoltageControlZones(ports=("name", "pilot_bus_id", "pilot_bus_breaker_bus_id"))
    df_port, _ = converter(network=network)
    assert df_port["pilot_bus_id"].tolist() == ["S1VL2_0"]
    assert df_port["pilot_bus_breaker_bus_id"].tolist() == ["S1VL2_0"]


def test_secondary_voltage_control_units(eurostag_with_secondary_voltage_control):
    df_port, df_feature = SecondaryVoltageControlUnits()(network=eurostag_with_secondary_voltage_control)

    assert df_port["zone_name"].tolist() == ["z1"]
    assert df_port["unit_id"].tolist() == ["GEN"]
    assert df_feature["participate"].tolist() == [1.0]


def test_secondary_voltage_control_without_extension(ieee14):
    # pypowsybl raises on networks without the extension; the classes yield empty tables
    # instead, so they can sit in a configuration applied to mixed datasets.
    for converter in (SecondaryVoltageControlZones(), SecondaryVoltageControlUnits()):
        df_port, df_feature = converter(network=ieee14)
        assert len(df_port) == 0
        assert len(df_feature) == 0


def test_secondary_voltage_control_graph(eurostag_with_secondary_voltage_control):
    # End to end: zones tie to buses through their pilots, units tie to generators through
    # the generator id — which the generators must therefore expose as a port.
    config = {
        "buses": Buses(),
        "generators": Generators(ports=("id", "bus_id", "regulated_bus_id")),
        "secondary_voltage_control_zones": SecondaryVoltageControlZones(),
        "secondary_voltage_control_units": SecondaryVoltageControlUnits(),
    }
    graph = PypowsyblConverter(config)(network=eurostag_with_secondary_voltage_control)

    zone_ports = graph.hyper_edge_sets["secondary_voltage_control_zones"].port_dict
    bus_addresses = set(np.asarray(graph.hyper_edge_sets["buses"].port_dict["id"]).tolist())
    assert set(np.asarray(zone_ports["pilot_bus_id"]).tolist()) <= bus_addresses

    unit_ports = graph.hyper_edge_sets["secondary_voltage_control_units"].port_dict
    generator_addresses = set(np.asarray(graph.hyper_edge_sets["generators"].port_dict["id"]).tolist())
    assert set(np.asarray(unit_ports["unit_id"]).tolist()) <= generator_addresses
    # The two secondary voltage control classes share the zone address.
    assert set(np.asarray(unit_ports["zone_name"]).tolist()) <= set(np.asarray(zone_ports["name"]).tolist())


def test_join_options_compose_the_structure():
    converter = TwoWindingsTransformers(
        ratio_tap_changer_features=("tap",),
        phase_tap_changer_features=("tap",),
        operational_limit_features=("current_limit1", "current_limit2"),
    )
    structure = converter.get_structure()
    assert "ratio_tap_changer_tap" in structure.feature_list
    assert "phase_tap_changer_tap" in structure.feature_list
    assert "current_limit1" in structure.feature_list
