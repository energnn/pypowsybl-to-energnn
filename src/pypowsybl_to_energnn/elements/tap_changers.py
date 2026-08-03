# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

"""The tap changer devices, as hyper-edge classes of their own.

The connect form of the tap changers, dual of the
``ratio_tap_changer_features``/``phase_tap_changer_features`` merge options of
:class:`TwoWindingsTransformers`: one hyper-edge per device, tied to its transformer
through the ``id`` port (the transformers must then expose their id as a port too) and to
the bus it regulates through ``regulating_bus_id`` — a remote-regulation edge like the
``regulated_bus_id`` of the generators, which the merged form cannot represent. Merge when
only the device data matters, connect when the regulation structure does.

The step tables follow, in the same mould as :class:`ReactiveCapabilityCurvePoints`:
:class:`RatioTapChangerSteps`/:class:`PhaseTapChangerSteps` carry one hyper-edge per
(device, position) pair — the number of steps per device is not bounded, so the discrete
range of the changer fits the graph structure rather than a fixed-width feature vector.
"""

from typing import Sequence

import pandas as pd
import pypowsybl.network as pn

from .base import PypowsyblElements
from .two_windings_transformers import TwoWindingsTransformers


class RatioTapChangers(PypowsyblElements):
    """Ratio tap changers (``get_ratio_tap_changers``), one hyper-edge per device.

    The ``id`` port is the transformer carrying the device; ``regulating_bus_id`` points to
    the bus whose voltage the changer regulates (a bus view id, on the same addresses as
    :class:`Buses`), possibly far from the transformer. The default features are
    ``TwoWindingsTransformers.RATIO_TAP_CHANGER_FEATURES``, the bundle of the merged form.

    :param ports: Address columns, the carrying transformer and the regulated bus by
        default.
    :param features: Feature columns, the tap position bounds and regulation settings by
        default.
    """

    def __init__(
        self,
        ports: Sequence[str] = ("id", "regulating_bus_id"),
        features: Sequence[str] = TwoWindingsTransformers.RATIO_TAP_CHANGER_FEATURES,
    ):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_ratio_tap_changers(all_attributes=True).reset_index()


class PhaseTapChangers(PypowsyblElements):
    """Phase tap changers (``get_phase_tap_changers``), one hyper-edge per device.

    The ``id`` port is the transformer carrying the device; ``regulating_bus_id`` points to
    the regulated bus (a bus view id, on the same addresses as :class:`Buses`). The default
    features are ``TwoWindingsTransformers.PHASE_TAP_CHANGER_FEATURES``, the bundle of the
    merged form — ``regulation_mode`` among them is categorical (hashed to an arbitrary
    deterministic float; go through :class:`TableConverter` for a proper encoding).

    :param ports: Address columns, the carrying transformer and the regulated bus by
        default.
    :param features: Feature columns, the tap position bounds and regulation settings by
        default.
    """

    def __init__(
        self,
        ports: Sequence[str] = ("id", "regulating_bus_id"),
        features: Sequence[str] = TwoWindingsTransformers.PHASE_TAP_CHANGER_FEATURES,
    ):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_phase_tap_changers(all_attributes=True).reset_index()


class RatioTapChangerSteps(PypowsyblElements):
    """Ratio tap changer steps (``get_ratio_tap_changer_steps``), one hyper-edge per step.

    The discrete range of the changers: one hyper-edge per (device, position) pair, holding
    the ratio and pi-model corrections of the step — the current position is the ``tap`` of
    :class:`RatioTapChangers`. The ``id`` port is the carrying transformer, which must
    expose its id as a port too.

    :param ports: Address columns, the carrying transformer by default.
    :param features: Feature columns, the position and its ratio and pi-model corrections by
        default.
    """

    def __init__(
        self,
        ports: Sequence[str] = ("id",),
        features: Sequence[str] = ("position", "rho", "r", "x", "g", "b"),
    ):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_ratio_tap_changer_steps(all_attributes=True).reset_index()


class PhaseTapChangerSteps(PypowsyblElements):
    """Phase tap changer steps (``get_phase_tap_changer_steps``), one hyper-edge per step.

    Like :class:`RatioTapChangerSteps`, with the phase shift ``alpha`` of each step on top —
    the current position is the ``tap`` of :class:`PhaseTapChangers`. The ``id`` port is the
    carrying transformer, which must expose its id as a port too.

    :param ports: Address columns, the carrying transformer by default.
    :param features: Feature columns, the position and its ratio, phase shift and pi-model
        corrections by default.
    """

    def __init__(
        self,
        ports: Sequence[str] = ("id",),
        features: Sequence[str] = ("position", "rho", "alpha", "r", "x", "g", "b"),
    ):
        super().__init__(ports=ports, features=features)

    def build_table(self, network: pn.Network, **kwargs) -> pd.DataFrame:
        return network.get_phase_tap_changer_steps(all_attributes=True).reset_index()
