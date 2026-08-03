# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

import pypowsybl.network as pn
from energnn.converter import Converter, ElementsConverter
from energnn.graph import Graph
from energnn.graph.backend import Backend


class PypowsyblConverter(Converter):
    """Converter assembled from an explicit mapping of elements converters.

    Ready-made mappings live in :mod:`pypowsybl_to_energnn.ready_to_use`; to amend one at the
    margin, copy the dict and replace or add entries:

    .. code-block:: python

        converters = dict(ready_to_use.AC_LOAD_FLOW_INPUT)
        converters["generators"] = Generators(ports=("bus_id",), features=("target_p",))
        graph = PypowsyblConverter(converters)(network=network)

    :param elements_converter_dict: Mapping from hyper-edge class name to the
        :class:`ElementsConverter` producing its table.
    :param per_unit: Set ``network.per_unit`` before extraction, so that graphs cannot
        silently mix per-united and physical values. Mind the side effect: the *caller's*
        network object switches to that mode, and its tables read per-united afterwards.
    :param backend: Optional target backend for the produced graphs.
    """

    def __init__(
        self,
        elements_converter_dict: dict[str, ElementsConverter],
        *,
        per_unit: bool = True,
        backend: Backend | None = None,
    ):
        self.elements_converter_dict = dict(elements_converter_dict)
        self.per_unit = per_unit
        self.backend = backend

    def __call__(self, *, network: pn.Network, **kwargs) -> Graph:
        network.per_unit = self.per_unit
        return super().__call__(network=network, **kwargs)
