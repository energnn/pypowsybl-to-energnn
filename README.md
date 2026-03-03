# PyPowSyBl to EnerGNN
*Converts **PyPowSyBl** networks into **EnerGNN** graphs.*

This helper package is part of the [EnerGNN](https://github.com/EnerGNN/EnerGNN) project, and provides:

- A modular and extensible framework for converting PyPowSyBl networks into EnerGNN graphs.
- A set of predefined converters for common use cases.
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

This package relies on so-called `Converters`, which extract [Pandas](https://pandas.pydata.org/)
dataframes from **PyPowSyBl** networks to populate `energnn.JaxGraph` objects,
which are Hyper Heterogeneous Multi Graphs.

Multiple ready-to-use implementations are available in `pypowsybl_to_energnn.ready_to_use`.
```python
import pypowsybl.network as pn
import pypowsybl_to_energnn as pe
from energnn.graph import JaxGraph

input_converter = pe.ready_to_use.ACLoadFlowInputConverter()
output_converter = pe.ready_to_use.ACLoadFlowOutnputConverter()

network = pn.create_ieee14()  # Or any other PyPowSyBl network

input_graph: JaxGraph = input_converter(network)
output_graph: JaxGraph = output_converter(network)
```

Converters can also return the structure of the graphs they output,
which is useful for creating an **EnerGNN** model.

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
then you can implement your own converter and specify which addresses and which features you want to extract,
as long as they are supported by **PyPowSyBl**.

```python
class MyConverter(pe.Converter):
    elements_converter_dict = {
        "buses": pe.elements.BusesConverter(["id"], None),
        "generators": pe.elements.GeneratorsConverter(["bus_id"], ["energy_source"]),
        ...
    }
```
---

## Custom Features
If you want to extract features that are combinations of **PyPowSyBl** features,
then you can implement your own element converter.

```python
class MyBusesConverter(pe.elements.ElementConverter):
    """This converter extracts the squared voltage magnitudes of the buses, and indices."""
    def _get_table(self, *, network: pn.Network, **kwargs) -> pd.DataFrame:
        bus_df = network.get_batteries(all_attributes=True).reset_index()
        bus_df["squared_voltage"] = bus_df["v_mag"] ** 2
        return bus_df

class MyConverter(pe.Converter):
    """This converter uses the MyBusesConverter to extract the squared voltage magnitudes of the buses."""
    elements_converter_dict = {
        "buses": MyBusesConverter(["id"], ["squared_voltage"]),
    }
```
---

## Combining **PyPowSyBl** networks with other data sources

If you wish to combine **PyPowSyBl** networks with other data sources,
then you can implement your own converter that combines the data sources.
```python

class MyBusesConverter(pe.elements.ElementsConverter):
    def _get_table(self, *, network: pn.Network, other_table: pd.DataFrame):
        df = ...  # Combine the data sources
        return df
    
class MyConverter(pe.Converter):
    elements_converter_dict = {
        "buses": MyBusesConverter(["id"], None),
        ...
    }
    
converter = MyConverter()
network = pn.Network.create_ieee14()
other_table = pd.read_csv("other_table.csv")
graph = converter(network, other_table)
```

Notice that the example above considers a dataframe, but any other data type can be used.