# PyPowSyBl to EnerGNN
*Converts **PyPowSyBl** networks into **EnerGNN** graphs.*

This helper package is part of the [EnerGNN](https://github.com/energnn/energnn) project.
The `Converter` and `ElementsConverter` abstract base classes live in `energnn.converter`;
this package only provides their **PyPowSyBl** implementations:

- One elements converter class per class of PyPowSyBl objects (`Lines`, `Generators`,
  `TwoWindingsTransformers`, ...), each in its own module under
  `pypowsybl_to_energnn.elements`, carrying its default ports and features (the data of the
  AC power flow problem) and its options to join satellite tables (tap changers,
  operational limits, extensions) — the conversion itself is plain pandas in the class's
  `build_table` method.
- `TableConverter`, the generic escape hatch for any other table — a PyPowSyBl getter or
  any callable returning a DataFrame.
- Ready-to-use configurations for common use cases — explicit, copyable dicts mapping each
  hyper-edge class to its elements converter — in `pypowsybl_to_energnn.ready_to_use`.
---

## Supported Formats

Thanks to [PyPowSyBl](https://powsybl.readthedocs.io/projects/pypowsybl/en/stable/),
the following formats are supported
([source](https://powsybl.readthedocs.io/projects/powsybl-core/en/stable/grid_exchange_formats/index.html)).

- CIM-CGMES
- UCTE-DEF
- IIDM (XIIDM, JIIDM, BIIDM)
- IEEE-CDF
- PSS®E
- PowerFactory
- MatPower
---

## Installation

```shell
pip install pypowsybl-to-energnn
```
---

## Basic Usage

A converter extracts [Pandas](https://pandas.pydata.org/) dataframes from a **PyPowSyBl**
network and assembles them into an `energnn.graph.Graph`, which is a Hyper Heterogeneous
Multi Graph. Each entry of its `elements_converter_dict` produces one class of hyper-edges,
defined by a list of *ports* (columns holding addresses, e.g. bus ids) and a list of
*features* (columns holding numerical values).

Ready-to-use configurations are available in `pypowsybl_to_energnn.ready_to_use`.
```python
import pypowsybl.loadflow as lf
import pypowsybl.network as pn
import pypowsybl_to_energnn as pe
from energnn.graph import Graph

input_converter = pe.PypowsyblConverter(pe.AC_LOAD_FLOW_INPUT)
output_converter = pe.PypowsyblConverter(pe.AC_LOAD_FLOW_OUTPUT)

network = pn.create_ieee14()  # Or any other PyPowSyBl network
lf.run_ac(network)  # The output columns are NaN until a power flow has run

input_graph: Graph = input_converter(network=network)
output_graph: Graph = output_converter(network=network)
```

Graphs are built on a numpy backend by default. To get graphs on another backend
(e.g. jax), pass the `backend` argument:

```python
from energnn.graph import JaxBackend

input_converter = pe.PypowsyblConverter(pe.AC_LOAD_FLOW_INPUT, backend=JaxBackend())
```

Converters can also return the structure of the graphs they output,
which is useful for creating an **EnerGNN** model without converting an actual network first.

```python
from energnn.model.ready_to_use import TinyRecurrentEquivariantGNN

model = TinyRecurrentEquivariantGNN(
    in_structure=input_converter.get_structure(),
    out_structure=output_converter.get_structure(),
)
```
---

## Custom Configurations

A configuration is a plain dict mapping each hyper-edge class to an elements converter.
Each converter class defaults to the ports and features of the AC power flow problem —
open the class (one module per class in `pypowsybl_to_energnn/elements/`) to read its
column lists — and every column choice can be overridden at construction. To adjust a
ready-to-use configuration at the margin, copy the dict and replace or add entries; to
start from scratch, write your own:

```python
import pypowsybl_to_energnn as pe

config = dict(pe.AC_LOAD_FLOW_INPUT)
config["generators"] = pe.Generators(ports=("bus_id",), features=("target_p", "energy_source"))
del config["batteries"]

converter = pe.PypowsyblConverter(config)
```

Note that the `"id"` column (the index of PyPowSyBl tables, recovered as a regular column)
can be used as a port like any other column. Every class validates the requested columns
(with an explicit error listing the available ones) and isolates the dangling ports: an
empty connection point (e.g. `bus_id` of a disconnected element) is rerouted to its own
sentinel address instead of spuriously connecting every such element through a shared
phantom node.
---

## Joined Tables

Some element classes have satellite tables: the tap changers and operational limits of the
branches, the `activePowerControl`/`standbyAutomaton` extensions, ... Each satellite table
of a class has its own feature list parameter, symmetric with `features`: pass the columns
to bring in (`None`, the default, leaves the table out). Joined columns land in the graph
prefixed by their table name (`ratio_tap_changer_tap`, `active_power_control_droop`, ...),
and are NaN (0 downstream) for elements without the satellite:

```python
import pypowsybl_to_energnn as pe

config = dict(pe.AC_LOAD_FLOW_INPUT)
config["lines"] = pe.Lines(operational_limit_features=("current_limit1", "current_limit2"))
config["two_windings_transformers"] = pe.TwoWindingsTransformers(
    ratio_tap_changer_features=pe.TwoWindingsTransformers.RATIO_TAP_CHANGER_FEATURES,
)
config["generators"] = pe.Generators(active_power_control_features=("droop", "participate"))
```

The secondary voltage control extension is not a satellite of an existing element but a
structure of its own — control zones piloting buses, units enrolling generators — and comes
as two dedicated hyper-edge classes, `SecondaryVoltageControlZones` and
`SecondaryVoltageControlUnits` (see their docstrings for the address wiring).
---

## Custom Tables

When no dedicated class fits, `TableConverter` converts any table: a PyPowSyBl getter name,
or any callable returning a DataFrame with one row per hyper-edge. The callable receives
all the arguments of the conversion call verbatim (`network=...` among them), so derived
features, filtered rows or ad-hoc joins are just pandas:

```python
import pypowsybl_to_energnn as pe

def loads_with_squared_demand(network, **_):
    df = network.get_loads(all_attributes=True).reset_index()
    df["p0_squared"] = df["p0"] ** 2
    return df

config = dict(pe.AC_LOAD_FLOW_INPUT)
config["loads"] = pe.TableConverter(
    loads_with_squared_demand, ports=["bus_id"], features=["p0", "p0_squared"]
)
```
---

## Combining **PyPowSyBl** networks with other data sources

Since the conversion arguments are forwarded to every table callable, a table does not have
to come from PyPowSyBl at all — any DataFrame passed to the conversion call can become a
class of hyper-edges, and its PyPowSyBl ids (bus ids, element ids) connect it to the rest
of the graph:

```python
import pandas as pd
import pypowsybl.network as pn
import pypowsybl_to_energnn as pe

config = dict(pe.AC_LOAD_FLOW_INPUT)
config["generator_costs"] = pe.TableConverter(
    lambda gen_costs, **_: gen_costs, ports=["generator_id"], features=["marginal_cost"]
)

converter = pe.PypowsyblConverter(config)
network = pn.create_ieee14()
gen_costs = pd.read_csv("generator_costs.csv")
graph = converter(network=network, gen_costs=gen_costs)
```
---

## Development

This project uses [uv](https://docs.astral.sh/uv/). To set up a development environment
and run the test suite:

```shell
uv sync --group dev
uv run pytest
```

Formatting and linting:

```shell
uv run black src tests
uv run flake8 src tests
```