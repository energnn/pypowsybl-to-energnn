import pypowsybl.loadflow as lf
import pypowsybl.network as pn
import pandapower as pp
import pandapower.networks as ppn

from pypowsybl_to_energnn.ready_to_use import ACLoadFlowInputConverter, ACLoadFlowOutputConverter, PandapowerACLoadFlowInputConverter,\
    PandapowerACLoadFlowOutputConverter


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

def test_pandapower_ac_loadflow_simple():
    input_converter = PandapowerACLoadFlowInputConverter()
    output_converter = PandapowerACLoadFlowOutputConverter()

    net = pp.create_empty_network()
    pp.create_buses(net, nr_buses=2, vn_kv=110.0)
    pp.create_line(net, from_bus=0, to_bus=1, length_km=5, std_type="N2XS(FL)2Y 1x185 RM/35 64/110 kV")
    pp.create_ext_grid(net, bus=0)
    pp.create_load(net, bus=1, p_mw=50)
    pp.runpp(net)

    input_graph = input_converter(net)
    output_graph = output_converter(net)
    print(input_graph)
    print(output_graph)

def test_pandapower_ac_loadflow_ieee14(): #TODO: extend to IEEE 14, this function is not ready yet
    input_converter = PandapowerACLoadFlowInputConverter()
    output_converter = PandapowerACLoadFlowOutputConverter()

    net = ppn.case14()
    pp.runpp(net)

    input_graph = input_converter(net)
    output_graph = output_converter(net)
    print(input_graph)
    print(output_graph)

if __name__ == "__main__":
    test_pandapower_ac_loadflow_simple()
