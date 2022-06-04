import pickle
from pyvis.network import Network
import networkx as nx
import logging

def save_as_pickle(
    object_to_pickle:object, 
    path_to_pickle:str,
    verbose:bool = False
    ):
    """
    Saves Python object as pickle.

    :param object_to_pickle: the Python to be pickles
    :param path_to_pickle: path specifying where to save the pickle file
    :param verbose: verbose option

    :type object_to_pickle: object
    :type path_to_pickle: str
    :type verbose: bool
    """

    with open(path_to_pickle, 'wb') as handle:
        pickle.dump(object_to_pickle, handle, protocol=pickle.HIGHEST_PROTOCOL)

    if verbose:
        print(f"[+] Saved to \"{path_to_pickle}\".")


def load_pickle(
    path_to_pickle:str,
    verbose:bool = False
    ):
    """
    Reads Python pickle from file.

    :param path_to_pickle: path specifying where pickle file is saved
    :param verbose: verbose option

    :type path_to_pickle: str
    :type verbose: bool

    :return: the unpickled Python object
    :rtype: object
    """

    with open(path_to_pickle, 'rb') as handle:
        unpickled_object = pickle.load(handle)

    if verbose:
        print(f"[+] Loaded \"{path_to_pickle}\".")

    return unpickled_object


def gen_pyvis_network(
    Graph:nx.classes.graph.Graph
    ):
    """
    Using the PyVis module, the function generates a PyVis Network object
    from a networkx Graph that can be used to interactively display a Graph.

    :param Graph: the networkx Graph

    :type Graph: nx.classes.graph.Graph

    :return: the PyVis Network
    :rtype: pyvis.network.Network
    """

    net = Network(
        notebook = True, 
        directed = True, 
        height = '1000px', 
        width = "100%"
    )
    net.inherit_edge_colors(False)
    net.from_nx(Graph)
    return net


def save_pyvis_network(
    Graph:nx.classes.graph.Graph, 
    html_path:str,
    verbose:bool = False
    ):
    """
    Saves an interactive figure of a PyVis Network as html.

    :param Graph: the networkx Graph
    :param html_path: path specifying where to save the html figure
    :param verbose: verbose option

    :type Graph: nx.classes.graph.Graph
    :type html_path: str
    :type verbose: bool
    """

    net = gen_pyvis_network(Graph)
    net.save_graph(html_path)

    if verbose:
        print(f"[+] Saved Graph to \"{html_path}\".")


def assign_attributes(
    Graph:nx.classes.graph.Graph, 
    victim:int, 
    adversary:int,
    allies:list = [],
    type_to_value:dict = {"T":30, "M": 20, "C":10, "CP":10}
    ):
    """
    Given a graph, the victim and adversary node (and optionally a set of helpers), 
    this function will assign an array of attributes to these nodes.
    
    :param Graph: the graph for whose nodes and edges attributes will be assigned
    :param victim: the victim node in the graph
    :param adversary: the adversary node in the graph
    :param allies: the ally nodes to the victm in the graph
    :param type_to_value: a dictionary, cotaining value attributes according to the type of node

    :type Graph: nx.classes.graph.Graph
    :type victim: int
    :type adversary: int
    :type allies: int
    :type type_to_value: dict

    :return: the graph with the set attributes
    :rytpe: nx.classes.graph.Graph
    """

    for node_indx in range(len(Graph.nodes)):
        # colors according to attack/defense role
        if node_indx == victim:
            Graph.nodes[node_indx]["role"] = "victim"
            Graph.nodes[node_indx]["color"] = "green"

        elif node_indx == adversary:
            Graph.nodes[node_indx]["role"] = "source"
            Graph.nodes[node_indx]["color"] = "red"

        elif node_indx in allies:
            Graph.nodes[node_indx]["role"] = "ally"
            Graph.nodes[node_indx]["color"] = "blue"

        else:
            Graph.nodes[node_indx]["role"] = "standard"
            Graph.nodes[node_indx]["color"] = "lightgrey"
        
    return Graph


def create_logger(name, log_file_location, level = logging.DEBUG, log_format_str = '%(name)s ==> %(levelname)s: %(message)s'):
    formatter = logging.Formatter(log_format_str)

    handler = logging.FileHandler(log_file_location)        
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger
