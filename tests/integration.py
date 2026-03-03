import pypowsybl.loadflow as lf
import pypowsybl.network as pn

from pypowsybl_to_energnn.ready_to_use import ACLoadFlowInputConverter, ACLoadFlowOutputConverter


def test_ac_loadflow_ieee14():
    input_converter = ACLoadFlowInputConverter()
    output_converter = ACLoadFlowOutputConverter()

    network = pn.create_ieee14()
    lf.run_ac(network)
    network.per_unit = True

    input_graph = input_converter(network)
    output_graph = output_converter(network)
    print(input_graph)
    print(output_graph)


def test_ac_loadflow_ieee300():
    input_converter = ACLoadFlowInputConverter()
    output_converter = ACLoadFlowOutputConverter()

    network = pn.create_ieee300()
    lf.run_ac(network)
    network.per_unit = True

    input_graph = input_converter(network)
    output_graph = output_converter(network)
    print(input_graph)
    print(output_graph)
