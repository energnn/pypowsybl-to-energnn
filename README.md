# PyPowSyBl to EnerGNN
*Converts **PyPowSyBl** networks into **EnerGNN** graphs.*

This helper package is part of the [EnerGNN](https://github.com/energnn/energnn) project.
The `Converter` and `ElementsConverter` abstract base classes live in `energnn.converter`;
this package only provides their **PyPowSyBl** implementations:

- A set of elements converters, one per PyPowSyBl network table (buses, lines, generators, ...),
  that extract addresses and features from a `pypowsybl.network.Network`.
- Ready-to-use converters for common use cases, in `pypowsybl_to_energnn.ready_to_use`.
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

Multiple ready-to-use implementations are available in `pypowsybl_to_energnn.ready_to_use`.
```python
import pypowsybl.network as pn
import pypowsybl_to_energnn as pe
from energnn.graph import Graph

input_converter = pe.ACLoadFlowInputConverter()
output_converter = pe.ACLoadFlowOutputConverter()

network = pn.create_ieee14()  # Or any other PyPowSyBl network

input_graph: Graph = input_converter(network=network)
output_graph: Graph = output_converter(network=network)
```

Graphs are built on a numpy backend by default. To get graphs on another backend
(e.g. jax), set the `backend` attribute of the converter:

```python
from energnn.graph import JaxBackend

input_converter.backend = JaxBackend()
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

## Custom PyPowSyBl Converters

If your use case requires access to features that are not covered by the predefined converters,
then you can implement your own converter and specify which ports and which features you want to
extract, as long as they are supported by **PyPowSyBl**.

```python
import pypowsybl_to_energnn as pe

class MyConverter(pe.Converter):
    elements_converter_dict = {
        "buses": pe.elements.BusesConverter(["id"], None),
        "generators": pe.elements.GeneratorsConverter(["bus_id"], ["target_p", "energy_source"]),
    }
```

Note that the ``"id"`` column (the index of PyPowSyBl tables) can be used as a port like any
other column. One elements converter is available per PyPowSyBl network table:
`BusesConverter`, `LinesConverter`, `GeneratorsConverter`, `LoadsConverter`,
`TwoWindingsTransformersConverter`, `ShuntCompensatorsConverter`, ... (see
`pypowsybl_to_energnn.elements` for the full list).
---

## Custom Features

If you want to extract features that are combinations of **PyPowSyBl** features,
then you can implement your own elements converter. Subclasses of
`NetworkElementsConverter` read a single network table (set by `_network_getter`),
but `_get_table` can be overridden to build arbitrary columns.

```python
import pandas as pd
import pypowsybl.network as pn
import pypowsybl_to_energnn as pe

class SquaredVoltageBusesConverter(pe.elements.NetworkElementsConverter):
    """Extracts bus ids and squared voltage magnitudes."""
    _network_getter = "get_buses"

    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        df = network.get_buses(attributes=["v_mag"]).reset_index()
        df["squared_v_mag"] = df["v_mag"] ** 2
        return df

class MyConverter(pe.Converter):
    elements_converter_dict = {
        "buses": SquaredVoltageBusesConverter(["id"], ["squared_v_mag"]),
    }
```
---

## Combining **PyPowSyBl** networks with other data sources

All the arguments passed to a converter are forwarded verbatim to each of its elements
converters, so you can implement elements converters that combine the network with any
other data source.

```python
import pandas as pd
import pypowsybl.network as pn
import pypowsybl_to_energnn as pe
from energnn.converter import ElementsConverter

class MyBusesConverter(ElementsConverter):
    def _get_table(self, *, network: pn.Network, other_table: pd.DataFrame, **kwargs) -> pd.DataFrame:
        df = ...  # Combine the data sources
        return df

class MyConverter(pe.Converter):
    elements_converter_dict = {
        "buses": MyBusesConverter(["id"], None),
    }

converter = MyConverter()
network = pn.create_ieee14()
other_table = pd.read_csv("other_table.csv")
graph = converter(network=network, other_table=other_table)
```

Notice that the example above considers a dataframe, but any other data type can be used.
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