# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

from typing import Sequence

import pandas as pd
import pypowsybl.network as pn

from .base import PypowsyblElements


class Switches(PypowsyblElements):
    """Switches of the bus/breaker view (``get_switches``), the edges the bus view collapses.

    Only the *retained* switches belong to the bus/breaker view: the others are internal to
    a bus/breaker bus (their bus columns are empty) and are dropped by :meth:`build_table` —
    switches of bus/breaker-modelled voltage levels are always reported as retained. This
    class only makes sense in a bus/breaker configuration; in the bus view, switches are
    already collapsed inside the buses. The categorical ``kind`` column (breaker,
    disconnector, ...) is left out of the default features: encode it through
    :class:`TableConverter` if needed.

    :param ports: Address columns, the two bus/breaker view buses by default.
    :param features: Feature columns, the open status by default.
    """

    AC_LOAD_FLOW_INPUT_FEATURES = ("open",)
    AC_LOAD_FLOW_OUTPUT_FEATURES: tuple[str, ...] = ()
    DC_LOAD_FLOW_INPUT_FEATURES = ("open",)
    DC_LOAD_FLOW_OUTPUT_FEATURES: tuple[str, ...] = ()

    def __init__(
        self,
        ports: Sequence[str] = ("bus_breaker_bus1_id", "bus_breaker_bus2_id"),
        features: Sequence[str] = AC_LOAD_FLOW_INPUT_FEATURES + AC_LOAD_FLOW_OUTPUT_FEATURES,
    ):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        df = network.get_switches(all_attributes=True).reset_index()
        return df[df["retained"]]
