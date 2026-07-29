# Copyright (c) 2026, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0

"""The declarative knowledge about pypowsybl: every table the options can select from.

Purely declarative — no logic beyond the port-column view translation. :mod:`.resolve` turns
a combination of options into a spec by selecting and projecting these entries; adding
support for a new pypowsybl table or extension means adding an entry here.
"""

from __future__ import annotations

from dataclasses import dataclass

_TOPOLOGY_VIEWS = ("bus_branch", "bus_breaker")
_FEATURE_GROUPS = ("ac_pf_input", "dc_pf_input", "ac_pf_output", "dc_pf_output")


def _port_for_view(column: str, topology_view: str) -> str:
    """Translate a bus port column to the requested topology view.

    Every element table carries its connection points in all views at once (``bus_id``,
    ``bus1_id``, ``regulated_bus_id`` for the bus view; the same names with ``bus`` replaced
    by ``bus_breaker_bus`` for the bus/breaker view). Ports are declared once in the registry,
    in bus-view vocabulary, and translated here.
    """
    if topology_view == "bus_branch":
        return column
    return column.replace("bus", "bus_breaker_bus", 1)


@dataclass(frozen=True)
class _Table:
    """Registry entry for one base hyper-edge class: everything the options can project.

    The four feature-group fields form the solver × role grid of the ``features`` option
    (their names are its values, projected with ``getattr``).

    :param getter: pypowsybl getter of the table (``bus_breaker_getter`` overrides it in the
        bus/breaker view, for the tables that differ per view — the buses).
    :param ports: View-independent port columns (element ids, converter station ids, ...).
    :param bus_ports: Bus port columns, in bus-view vocabulary (see :func:`_port_for_view`).
    :param regulation_ports: Bus ports toward remotely regulated buses, added by ``regulation``.
    :param ac_pf_input: Problem-data columns of an AC power flow (impedances, limits,
        setpoints, ...).
    :param dc_pf_input: Their active-only subset — the data of the DC problem (reactive- and
        voltage-related columns dropped).
    :param ac_pf_output: State columns solved by an AC power flow.
    :param dc_pf_output: Their active-only subset, solved by a DC power flow.
    :param views: Topology views in which the class exists (switches: bus/breaker only).
    :param query: Optional row filter, forwarded to :class:`TableSpec`.
    """

    getter: str
    ports: tuple[str, ...] = ()
    bus_ports: tuple[str, ...] = ()
    regulation_ports: tuple[str, ...] = ()
    ac_pf_input: tuple[str, ...] = ()
    dc_pf_input: tuple[str, ...] = ()
    ac_pf_output: tuple[str, ...] = ()
    dc_pf_output: tuple[str, ...] = ()
    bus_breaker_getter: str | None = None
    views: tuple[str, ...] = _TOPOLOGY_VIEWS
    query: str | None = None


# Phase angles are excluded from the AC outputs: they are not permutation equivariant.
_TABLES = {
    "buses": _Table(
        "get_buses",
        bus_breaker_getter="get_bus_breaker_view_buses",
        ports=("id",),
        ac_pf_output=("v_mag",),
    ),
    "two_windings_transformers": _Table(
        "get_2_windings_transformers",
        bus_ports=("bus1_id", "bus2_id"),
        ac_pf_input=("r", "x", "g", "b", "rated_u1", "rated_u2", "rated_s", "rho", "alpha", "connected1", "connected2"),
        dc_pf_input=("x", "rho", "alpha", "connected1", "connected2"),
        ac_pf_output=("p1", "q1", "i1", "p2", "q2", "i2"),
        dc_pf_output=("p1", "p2"),
    ),
    "batteries": _Table(
        "get_batteries",
        bus_ports=("bus_id",),
        ac_pf_input=("max_p", "min_p", "min_q", "max_q", "target_p", "target_q", "connected"),
        dc_pf_input=("max_p", "min_p", "target_p", "connected"),
        ac_pf_output=("p", "q", "i"),
        dc_pf_output=("p",),
    ),
    "dangling_lines": _Table(
        "get_dangling_lines",
        bus_ports=("bus_id",),
        ac_pf_input=("r", "x", "g", "b", "p0", "q0"),
        dc_pf_input=("x", "p0"),
        ac_pf_output=("p", "q", "i"),
        dc_pf_output=("p",),
    ),
    "generators": _Table(
        "get_generators",
        bus_ports=("bus_id",),
        regulation_ports=("regulated_bus_id",),
        ac_pf_input=(
            "target_p",
            "min_p",
            "max_p",
            "min_q",
            "max_q",
            "rated_s",
            "target_v",
            "target_q",
            "voltage_regulator_on",
            "connected",
        ),
        dc_pf_input=("target_p", "min_p", "max_p", "connected"),
        ac_pf_output=("p", "q", "i"),
        dc_pf_output=("p",),
    ),
    "hvdc_lines": _Table(
        "get_hvdc_lines",
        ports=("converter_station1_id", "converter_station2_id"),
        ac_pf_input=("converters_mode", "target_p", "max_p", "nominal_v", "r", "connected1", "connected2"),
        dc_pf_input=("converters_mode", "target_p", "max_p", "r", "connected1", "connected2"),
    ),
    "lcc_converter_stations": _Table(
        "get_lcc_converter_stations",
        ports=("id",),
        bus_ports=("bus_id",),
        ac_pf_input=("power_factor", "loss_factor", "connected"),
        dc_pf_input=("loss_factor", "connected"),
        ac_pf_output=("p", "q", "i"),
    ),
    "lines": _Table(
        "get_lines",
        bus_ports=("bus1_id", "bus2_id"),
        ac_pf_input=("r", "x", "g1", "b1", "g2", "b2", "connected1", "connected2"),
        dc_pf_input=("x", "connected1", "connected2"),
        ac_pf_output=("p1", "q1", "i1", "p2", "q2", "i2"),
        dc_pf_output=("p1", "p2"),
    ),
    "loads": _Table(
        "get_loads",
        bus_ports=("bus_id",),
        ac_pf_input=("p0", "q0", "connected"),
        dc_pf_input=("p0", "connected"),
        ac_pf_output=("p", "q", "i"),
        dc_pf_output=("p",),
    ),
    # Shunts and SVCs are reactive-only devices: they carry nothing in the DC problem — with
    # ports=False they are dropped from pure-DC graphs entirely.
    "shunts": _Table(
        "get_shunt_compensators",
        bus_ports=("bus_id",),
        ac_pf_input=(
            "g",
            "b",
            "max_section_count",
            "section_count",
            "voltage_regulation_on",
            "target_v",
            "target_deadband",
            "connected",
        ),
        ac_pf_output=("p", "q", "i"),
    ),
    "static_var_compensators": _Table(
        "get_static_var_compensators",
        bus_ports=("bus_id",),
        regulation_ports=("regulated_bus_id",),
        ac_pf_input=("b_min", "b_max", "target_v", "target_q", "regulation_mode", "regulating", "connected"),
        ac_pf_output=("p", "q", "i"),
    ),
    "vsc_converter_stations": _Table(
        "get_vsc_converter_stations",
        ports=("id",),
        bus_ports=("bus_id",),
        regulation_ports=("regulated_bus_id",),
        ac_pf_input=(
            "loss_factor",
            "min_q",
            "max_q",
            "min_q_at_target_p",
            "max_q_at_target_p",
            "min_q_at_p",
            "max_q_at_p",
            "target_v",
            "target_q",
            "voltage_regulator_on",
            "connected",
        ),
        dc_pf_input=("loss_factor", "connected"),
        ac_pf_output=("p", "q", "i"),
    ),
    # get_switches returns every switch of the network, but only the retained ones belong to
    # the bus/breaker view: the others are internal to a bus/breaker bus and their
    # bus_breaker_bus1_id/bus_breaker_bus2_id are empty. Switches of bus/breaker-modelled
    # voltage levels are always reported as retained.
    "switches": _Table(
        "get_switches",
        ports=("bus_breaker_bus1_id", "bus_breaker_bus2_id"),
        ac_pf_input=("kind", "open"),
        dc_pf_input=("kind", "open"),
        views=("bus_breaker",),
        query="retained",
    ),
}


@dataclass(frozen=True)
class _Satellite:
    """Registry entry for a satellite table: how to fetch it and how it attaches to its parent.

    ``parent`` is only set for satellites with at most one row per parent element — the ones
    that can be merged. ``regulation_port`` is only used in the ``"connect"`` representation
    (merged port columns would leave NaN holes on parents without a satellite row), and only
    in the bus/branch view: tap changer tables expose the regulated bus in the bus view only.
    """

    getter: str
    features: tuple[str, ...]
    parent: str | None = None
    prefix: str = ""
    parent_port: str = "id"
    regulation_port: str | None = None


_SATELLITES = {
    "ratio_tap_changers": _Satellite(
        getter="get_ratio_tap_changers",
        features=("tap", "low_tap", "high_tap", "step_count", "oltc", "regulating", "target_v", "target_deadband"),
        parent="two_windings_transformers",
        prefix="rtc_",
        regulation_port="regulating_bus_id",
    ),
    "phase_tap_changers": _Satellite(
        getter="get_phase_tap_changers",
        features=(
            "tap",
            "low_tap",
            "high_tap",
            "step_count",
            "oltc",
            "regulating",
            "regulation_mode",
            "regulation_value",
            "target_deadband",
        ),
        parent="two_windings_transformers",
        prefix="ptc_",
        regulation_port="regulating_bus_id",
    ),
    "ratio_tap_changer_steps": _Satellite(
        getter="get_ratio_tap_changer_steps", features=("position", "rho", "r", "x", "g", "b")
    ),
    "phase_tap_changer_steps": _Satellite(
        getter="get_phase_tap_changer_steps", features=("position", "rho", "alpha", "r", "x", "g", "b")
    ),
    "operational_limits": _Satellite(
        getter="get_operational_limits",
        features=("side", "type", "acceptable_duration", "value"),
        parent_port="element_id",
    ),
    "reactive_capability_curve_points": _Satellite(
        getter="get_reactive_capability_curve_points", features=("num", "p", "min_q", "max_q")
    ),
    "linear_shunt_compensator_sections": _Satellite(
        getter="get_linear_shunt_compensator_sections",
        features=("g_per_section", "b_per_section", "max_section_count"),
        parent="shunts",
        prefix="sections_",
    ),
    "non_linear_shunt_compensator_sections": _Satellite(
        getter="get_non_linear_shunt_compensator_sections", features=("section", "g", "b")
    ),
    "dangling_lines_generation": _Satellite(
        getter="get_dangling_lines_generation",
        features=("min_p", "max_p", "target_p", "target_q", "target_v", "voltage_regulator_on"),
        parent="dangling_lines",
        prefix="generation_",
    ),
}


_INFRASTRUCTURE_FEATURES = {
    "voltage_levels": ("nominal_v", "high_voltage_limit", "low_voltage_limit"),
    "substations": ("TSO", "country"),
    "areas": ("area_type", "interchange_target"),
}


@dataclass(frozen=True)
class _ExtensionTable:
    """Registry entry for one table of a pypowsybl extension (``network.get_extensions``).

    Extension tables are satellites with a different fetch: indexed by the id of the carrying
    element (recovered as the ``parent_port`` column, always a port in ``"connect"`` mode),
    at most one row per element. The column split ports/features is declared here because id
    columns must never become features. ``parents`` lists the hyper-edge classes the features
    can be merged into — empty means the extension is representable in ``"connect"`` mode
    only (e.g. it only carries addresses, or it is relational like secondaryVoltageControl).

    ``bus_ports`` are only included in the ``bus_ports_view`` topology view: extension tables
    expose a single id namespace (``slackTerminal.bus_id`` is a bus-view id, the pilot-point
    ``bus_ids`` of secondaryVoltageControl a bus/breaker one), and an address from the wrong
    view would silently hang from a phantom node.
    """

    class_name: str
    table: str = ""
    features: tuple[str, ...] = ()
    ports: tuple[str, ...] = ()
    bus_ports: tuple[str, ...] = ()
    bus_ports_view: str = "bus_branch"
    parent_port: str = "id"
    parents: tuple[str, ...] = ()
    prefix: str = ""


_EXTENSIONS = {
    "activePowerControl": (
        _ExtensionTable(
            class_name="active_power_controls",
            features=("droop", "participate", "participation_factor", "max_target_p", "min_target_p"),
            parents=("generators", "batteries"),
            prefix="apc_",
        ),
    ),
    "hvdcAngleDroopActivePowerControl": (
        _ExtensionTable(
            class_name="hvdc_angle_droop_active_power_controls",
            features=("droop", "p0", "enabled"),
            parents=("hvdc_lines",),
            prefix="angle_droop_",
        ),
    ),
    "referencePriorities": (
        _ExtensionTable(
            class_name="reference_priorities",
            features=("priority",),
            parents=("generators",),
            prefix="reference_",
        ),
    ),
    # Voltage regulation of batteries; regulated_element_id is an element id (not a bus),
    # hence a port — connect mode only recovers it, merge keeps the two feature columns.
    "voltageRegulation": (
        _ExtensionTable(
            class_name="voltage_regulations",
            features=("voltage_regulator_on", "target_v"),
            ports=("regulated_element_id",),
            parents=("batteries",),
            prefix="regulation_",
        ),
    ),
    "standbyAutomaton": (
        _ExtensionTable(
            class_name="standby_automatons",
            features=(
                "standby",
                "b0",
                "low_voltage_threshold",
                "low_voltage_setpoint",
                "high_voltage_threshold",
                "high_voltage_setpoint",
            ),
            parents=("static_var_compensators",),
            prefix="standby_automaton_",
        ),
    ),
    "coordinatedReactiveControl": (
        _ExtensionTable(
            class_name="coordinated_reactive_controls",
            features=("q_percent",),
            parent_port="generator_id",
            parents=("generators",),
            prefix="coordinated_",
        ),
    ),
    # The slack bus an AC power flow leaned on (filled by run_ac with write_slack_bus=True):
    # one row per voltage level, all columns are addresses — connect only.
    "slackTerminal": (
        _ExtensionTable(
            class_name="slack_terminals",
            ports=("element_id",),
            bus_ports=("bus_id",),
            parent_port="voltage_level_id",
        ),
    ),
    # Relational extension, two tables: zones (pilot point bus and its target_v) and units
    # (generator → zone membership). zone_name/name is the address linking the two classes,
    # like areas/areas_voltage_levels. Pilot buses are bus/breaker ids; multi-bus pilot
    # points (comma-separated bus_ids) are not split yet.
    "secondaryVoltageControl": (
        _ExtensionTable(
            class_name="secondary_voltage_control_zones",
            table="zones",
            features=("target_v",),
            bus_ports=("bus_ids",),
            bus_ports_view="bus_breaker",
            parent_port="name",
        ),
        _ExtensionTable(
            class_name="secondary_voltage_control_units",
            table="units",
            features=("participate",),
            ports=("zone_name",),
            parent_port="unit_id",
        ),
    ),
}
