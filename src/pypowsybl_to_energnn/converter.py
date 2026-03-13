# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

import random

import jax.numpy as jnp
import numpy as np
import pandas as pd
import pypowsybl.network as pn
from energnn.graph import GraphStructure, JaxGraph, JaxGraphShape, JaxHyperEdgeSet

from pypowsybl_to_energnn.elements import ElementsConverter


class Converter:

    elements_converter_dict: dict[str, ElementsConverter]

    def get_structure(self) -> GraphStructure:
        return GraphStructure(hyper_edge_sets={k: c.get_structure() for k, c in self.elements_converter_dict.items()})

    def __call__(self, network: pn.Network, **kwargs) -> JaxGraph:
        # Build dict of tables
        tables = {}
        for k, component_converter in self.elements_converter_dict.items():
            tables[k] = component_converter(network=network, **kwargs)

        # First, convert str addresses into unique integers.
        address_tables = {k: tables[k][0] for k in tables.keys()}
        int_address_tables, n_addresses = _str_to_int(address_tables)

        # Then, convert features into floats.
        feature_tables = {k: tables[k][1] for k in tables.keys()}
        float_feature_tables = _any_to_float(feature_tables)

        # Convert tabls into JaxGraph.
        tables = {k: (int_address_tables[k], float_feature_tables[k]) for k in tables.keys()}
        graph = _tables_to_jaxgraph(tables, n_addresses)

        return graph


def _str_to_int(address_tables: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], int]:
    """Converts addresses into unique integers."""

    # 1. Gather the set of all addresses.
    all_addresses = set()
    for k, df in address_tables.items():
        if df is not None:
            all_addresses.update(df.values.squeeze().reshape(-1).tolist())

    # 2. Create a mapping from addresses to integers.
    str_to_int_dict = {k: i for i, k in enumerate(all_addresses)}

    # 3. Apply the mapping to each DataFrames.
    out_dict = {}
    for k, df in address_tables.items():
        if df is not None:
            out_dict[k] = df.map(lambda x: str_to_int_dict[x])
        else:
            out_dict[k] = None

    return out_dict, len(str_to_int_dict)


def _any_to_float(
    feature_tables: dict[str, pd.DataFrame], min_val: float = -1e6, max_val: float = 1e6
) -> dict[str, pd.DataFrame]:

    out_dict = {}
    for k, df in feature_tables.items():
        if df is not None:

            # Convert categorical features into floats.
            for col in df.columns:
                if df[col].dtype.kind in {"U", "S", "O"}:
                    df[col] = np.float64(list(map(lambda x: random.Random(x).random(), df[col])))

            out_dict[k] = df.astype(float)
            out_dict[k].replace(-np.inf, min_val, inplace=True)
            out_dict[k].replace(np.inf, max_val, inplace=True)
            out_dict[k].fillna(0, inplace=True)
            out_dict[k].clip(min_val, max_val, inplace=True)
        else:
            out_dict[k] = None
    return out_dict


def _tables_to_jaxgraph(tables: dict[str, tuple[pd.DataFrame, pd.DataFrame]], n_addresses: int) -> JaxGraph:

    # Créons des JaxGraph direct

    # 1. Créer le dictionnaire de JaxEdge
    hyper_edge_set_dict = {}
    hyper_edge_set_shapes = {}
    for k, (df_address, df_feature) in tables.items():

        # 1.1. Dictionary that maps address names to values.
        if df_address is not None:
            port_dict = {kk: jnp.array(df_address[kk], dtype=jnp.int32) for kk in df_address.columns}
        else:
            port_dict = None

        # 1.2. Array that contains all hyper-edge features.
        if df_feature is not None:
            feature_array = jnp.array(df_feature.values, dtype=jnp.float32)
        else:
            feature_array = None

        # 1.3. Dictionary that maps feature names to their position in feature_array.
        if df_feature is not None:
            feature_names = {kk: jnp.array(i, dtype=jnp.int32) for i, kk in enumerate(df_feature.columns)}
        else:
            feature_names = None

        # 1.4. Non fictitious mask.
        if df_address is None:
            n = df_feature.shape[0]
        else:
            n = df_address.shape[0]
        non_fictitious = jnp.ones(n, dtype=jnp.float32)
        hyper_edge_set_shapes = jnp.array([n], dtype=jnp.int32)

        # 1.5. Create the JaxEdge.
        hyper_edge_set_dict[k] = JaxHyperEdgeSet(
            port_dict=port_dict, feature_array=feature_array, feature_names=feature_names, non_fictitious=non_fictitious
        )

    # 2. Créer la true shape, qui est égale à la current shape.
    true_shape = JaxGraphShape(hyper_edge_sets=hyper_edge_set_shapes, addresses=jnp.array([n_addresses], dtype=jnp.int32))
    current_shape = JaxGraphShape(hyper_edge_sets=hyper_edge_set_shapes, addresses=jnp.array([n_addresses], dtype=jnp.int32))

    # 3. Créer le non_fictitious_addresses, qui doit être de la taille du nombre d'adresses uniques. Nombre qu'on avait direct.
    non_fictitious_addresses = jnp.ones(n_addresses, dtype=jnp.float32)

    return JaxGraph(
        hyper_edge_sets=hyper_edge_set_dict,
        true_shape=true_shape,
        current_shape=current_shape,
        non_fictitious_addresses=non_fictitious_addresses,
    )
