# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

import pandas as pd
import pypowsybl.network as pn
import pytest
from energnn.graph import HyperEdgeSetStructure

from pypowsybl_to_energnn import elements


@pytest.fixture(scope="module")
def network():
    return pn.create_ieee14()


def test_ports_and_features(network):
    converter = elements.LinesConverter(["bus1_id", "bus2_id"], ["r", "x"])
    df_port, df_feature = converter(network=network)

    assert list(df_port.columns) == ["bus1_id", "bus2_id"]
    assert list(df_feature.columns) == ["r", "x"]
    assert len(df_port) == len(df_feature)
    assert len(df_port) == len(network.get_lines())


def test_ports_only(network):
    converter = elements.BusesConverter(["id"], None)
    df_port, df_feature = converter(network=network)

    assert df_feature is None
    assert list(df_port.columns) == ["id"]
    assert df_port["id"].is_unique
    assert len(df_port) == len(network.get_buses())


def test_features_only(network):
    converter = elements.LoadsConverter(None, ["p0", "q0"])
    df_port, df_feature = converter(network=network)

    assert df_port is None
    assert list(df_feature.columns) == ["p0", "q0"]
    assert len(df_feature) == len(network.get_loads())


def test_no_ports_nor_features_raises():
    with pytest.raises(ValueError):
        elements.LinesConverter(None, None)


def test_empty_table(network):
    # There is no battery in the IEEE 14 test case: the converter must still return
    # well-formed (empty) tables.
    converter = elements.BatteriesConverter(["bus_id"], ["max_p", "min_p"])
    df_port, df_feature = converter(network=network)

    assert len(df_port) == 0
    assert len(df_feature) == 0
    assert list(df_port.columns) == ["bus_id"]
    assert list(df_feature.columns) == ["max_p", "min_p"]


def test_get_structure():
    converter = elements.GeneratorsConverter(["bus_id"], ["target_p", "target_v"])
    structure = converter.get_structure()
    assert isinstance(structure, HyperEdgeSetStructure)


@pytest.mark.parametrize(
    "converter_class",
    [
        elements.TwoWindingsTransformersConverter,
        elements.BranchesConverter,
        elements.BusesConverter,
        elements.GeneratorsConverter,
        elements.LinesConverter,
        elements.LoadsConverter,
        elements.ShuntCompensatorsConverter,
        elements.SubstationsConverter,
        elements.SwitchesConverter,
        elements.VoltageLevelsConverter,
    ],
)
def test_id_port_smoke(network, converter_class):
    # The "id" column is the index of pypowsybl tables: every converter must be able to expose
    # it as a port.
    converter = converter_class(["id"], None)
    df_port, df_feature = converter(network=network)

    assert df_feature is None
    assert list(df_port.columns) == ["id"]


def test_custom_elements_converter(network):
    class SquaredVoltageBusesConverter(elements.NetworkElementsConverter):
        _network_getter = "get_buses"

        def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
            df = network.get_buses(attributes=["v_mag"]).reset_index()
            df["squared_v_mag"] = df["v_mag"] ** 2
            return df

    converter = SquaredVoltageBusesConverter(["id"], ["squared_v_mag"])
    df_port, df_feature = converter(network=network)

    assert list(df_feature.columns) == ["squared_v_mag"]
    assert len(df_port) == len(network.get_buses())
