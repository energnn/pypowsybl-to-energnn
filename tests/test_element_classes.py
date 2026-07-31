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
    Batteries,
    Buses,
    DanglingLines,
    Generators,
    HvdcLines,
    LccConverterStations,
    Lines,
    Loads,
    PypowsyblConverter,
    SecondaryVoltageControlUnits,
    SecondaryVoltageControlZones,
    ShuntCompensators,
    StaticVarCompensators,
    TwoWindingsTransformers,
    VscConverterStations,
)

CLASSES_AND_GETTERS = [
    (Batteries, "get_batteries"),
    (Buses, "get_buses"),
    (DanglingLines, "get_dangling_lines"),
    (Generators, "get_generators"),
    (HvdcLines, "get_hvdc_lines"),
    (LccConverterStations, "get_lcc_converter_stations"),
    (Lines, "get_lines"),
    (Loads, "get_loads"),
    (ShuntCompensators, "get_shunt_compensators"),
    (StaticVarCompensators, "get_static_var_compensators"),
    (TwoWindingsTransformers, "get_2_windings_transformers"),
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


def test_lines_operational_limits(eurostag):
    converter = Lines(operational_limit_features=("current_limit1", "current_limit2"))
    _, df_feature = converter(network=eurostag)

    line_ids = list(eurostag.get_lines().index)
    row = df_feature.iloc[line_ids.index("NHV1_NHV2_1")]
    # Values checked against get_operational_limits: the selected permanent CURRENT limits.
    assert row["current_limit1"] == 500.0
    assert row["current_limit2"] == 1100.0


def test_transformers_operational_limits_missing_are_nan(eurostag):
    # The eurostag transformers carry no operational limit: the columns must still exist.
    converter = TwoWindingsTransformers(operational_limit_features=("current_limit1", "current_limit2"))
    _, df_feature = converter(network=eurostag)
    assert df_feature["current_limit1"].isna().all()
    assert df_feature["current_limit2"].isna().all()


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

    _, df_feature = DanglingLines(operational_limit_features=("current_limit",))(network=network)
    assert df_feature["current_limit"].tolist() == [250.0]


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

    # One hyper-edge per (zone, pilot bus), sharing the zone address and repeating target_v;
    # the pilot bus/breaker ids (NLOAD, NHV2) are translated into their bus view bus.
    assert df_port["name"].tolist() == ["z1", "z1"]
    assert df_port["pilot_bus_id"].tolist() == ["VLLOAD_0", "VLHV2_0"]
    assert df_feature["target_v"].tolist() == [400.0, 400.0]


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
