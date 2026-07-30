# PyPowSyBl to EnerGNN
*Converts **PyPowSyBl** networks into **EnerGNN** graphs.*

This helper package is part of the [EnerGNN](https://github.com/energnn/energnn) project.
The `Converter` and `ElementsConverter` abstract base classes live in `energnn.converter`;
this package only provides their **PyPowSyBl** implementations:

- `TableConverter`, an elements converter that extracts one class of hyper-edges from a
  table — a PyPowSyBl getter or any callable returning a DataFrame — and handles the
  generic plumbing (ports/features split, column validation, dangling-port isolation).
- Ready-to-use configurations for common use cases — explicit, copyable dicts mapping each
  hyper-edge class to its `TableConverter` — in `pypowsybl_to_energnn.ready_to_use`.
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

A configuration is a plain dict mapping each hyper-edge class to a `TableConverter` — the
PyPowSyBl getter (or callable, see below) it reads, its port columns (addresses: bus ids,
parent element ids, ...) and its feature columns. To adjust a ready-to-use configuration at
the margin, copy the dict and replace or add entries; to start from scratch, write your own:

```python
import pypowsybl_to_energnn as pe

config = dict(pe.AC_LOAD_FLOW_INPUT)
config["generators"] = pe.TableConverter("get_generators", ports=["bus_id"], features=["target_p", "energy_source"])
del config["batteries"]

converter = pe.PypowsyblConverter(config)
```

Note that the `"id"` column (the index of PyPowSyBl tables, recovered as a regular column)
can be used as a port like any other column. `TableConverter` validates the requested
columns (with an explicit error listing the available ones) and isolates the dangling ports:
an empty connection point (e.g. `bus_id` of a disconnected element) is rerouted to its own
sentinel address instead of spuriously connecting every such element through a shared
phantom node.
---

## Custom Tables

The table of a `TableConverter` can also be any callable returning a DataFrame with one row
per hyper-edge. It receives all the arguments of the conversion call verbatim
(`network=...` among them), so derived features, filtered rows or joined satellite tables
are just pandas:

```python
import pypowsybl_to_energnn as pe

def transformers_with_ratio_tap_changers(network, **_):
    df = network.get_2_windings_transformers(all_attributes=True)
    rtc = network.get_ratio_tap_changers(all_attributes=True).add_prefix("rtc_")
    return df.join(rtc).reset_index()

config = dict(pe.AC_LOAD_FLOW_INPUT)
config["two_windings_transformers"] = pe.TableConverter(
    transformers_with_ratio_tap_changers,
    ports=["bus1_id", "bus2_id"],
    features=["r", "x", "rho", "alpha", "rtc_tap", "rtc_target_v"],
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