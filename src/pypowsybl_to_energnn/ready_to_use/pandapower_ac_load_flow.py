# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

from pypowsybl_to_energnn.converter import Converter
from pypowsybl_to_energnn.elements import (
    BusesConverter,
    LinesConverter,
    LoadsConverter,
    ExtGridConverter,
)


class PandapowerACLoadFlowInputConverter(Converter):

    elements_converter_dict = {
        "buses": BusesConverter(["energnn_adress"], None),
        "lines": LinesConverter(["from_bus", "to_bus"], ["r_ohm", "x_ohm", "c_nf", "max_i_ka"]),
        "loads": LoadsConverter(["bus"], ["p_mw", "q_mvar", "in_service"]),
        "ext_grids": ExtGridConverter(["bus"], ["vm_pu", "va_degree"])
    }


class PandapowerACLoadFlowOutputConverter(Converter):

    elements_converter_dict = {
        "buses": BusesConverter(None, ["vm_pu"]),  # Phase angle is not permutation equivariant
        "lines": LinesConverter(None, ["p_from_mw", "q_from_mvar", "i_from_ka", "p_to_mw", "q_to_mvar", "i_to_ka"]),
        "loads": LoadsConverter(None, ["p_mw", "q_mvar"]),
    }
