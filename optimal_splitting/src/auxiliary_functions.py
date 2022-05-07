"""
Contains auxiliary functions used to
    * save to / read from pickle files
    * vizualize graphs and save those vizualisations as html files
    * colors graphs

Author:
    Devrim Celik - 01.05.2022
"""


import pickle
from pyvis.network import Network
import networkx as nx

def save_as_pickle(
    object_to_pickle:object, 
    path_to_pickle:str
    ):
    """
    Saves Python object as pickle.

    :param object_to_pickle: the Python to be pickles
    :param path_to_pickle: path specifying where to save the pickle file

    :type object_to_pickle: object
    :type path_to_pickle: str
    """

    with open(path_to_pickle, 'wb') as handle:
        pickle.dump(object_to_pickle, handle, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"[+] Saved to \"{path_to_pickle}\".")


def load_pickle(
    path_to_pickle:str
    ):
    """
    Reads Python pickle from file.

    :param path_to_pickle: path specifying where pickle file is saved

    :type path_to_pickle: str

    :return: the unpickled Python object
    :rtype: object
    """

    with open(path_to_pickle, 'rb') as handle:
        unpickled_object = pickle.load(handle)
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
    html_path:str
    ):
    """
    Saves an interactive figure of a PyVis Network as html.

    :param Graph: the networkx Graph
    :param html_path: path specifying where to save the html figure

    :type Graph: nx.classes.graph.Graph
    :type html_path: str
    """

    net = gen_pyvis_network(Graph)
    net.save_graph(html_path)
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
            Graph.nodes[node_indx]["color"] = "green"
            Graph.nodes[node_indx]["victim"] = True
        elif node_indx == adversary:
            Graph.nodes[node_indx]["color"] = "red"
            Graph.nodes[node_indx]["adversary"] = True
        elif node_indx in allies:
            Graph.nodes[node_indx]["color"] = "blue"
            Graph.nodes[node_indx]["ally"] = True
        else:
            Graph.nodes[node_indx]["color"] = "darkgrey"
            
        # size according to type
        Graph.nodes[node_indx]["value"] = type_to_value[Graph.nodes[node_indx]["type"]]
            
    return Graph


def indicate_attack_paths(
    input_Graph:nx.classes.graph.Graph,
    adversary:int,
    victim:int,
    indication_color:str = "deeppink"
    ):
    """
    Given a graph, this function will color all paths that lead from the adversary node
    to the victim node.
    
    :param input_Graph: graph for which the attack paths are to be colored
    :param adversary: the adversary node in the graph
    :param victim: the victim node in the graph
    :param indication_color: the color to use

    :type input_Graph: nx.classes.graph.Graph
    :type adversary: int
    :type victim: int
    :type indication_color: str

    :return: the graph with the set attributes
    :rytpe: nx.classes.graph.Graph
    """

    Graph = input_Graph.copy()
    # use inbuild function to see all the paths that lead from adversary to victim
    all_attack_paths = list(nx.all_simple_paths(Graph, adversary, victim))

    # go through each of them, and color any non-colored nodes and edges
    for attack_path in all_attack_paths:
        for u, v in zip(attack_path[:-1], attack_path[1:]):
            if Graph.nodes[u]["color"] == "darkgrey":
                #Graph.nodes[u]["color"] = indication_color # TODO
                Graph.nodes[u]["opacity"] = 0.75 #doesnt work
            if not "color" in G[u][v]:
                Graph[u][v]["color"] = indication_color
                
    return Graph


def color_graph(
    input_Graph:nx.classes.graph.Graph, 
    adversary:int, 
    victim:int, 
    allies:list, 
    splitting_color:str = "orange", 
    non_splitting_node_color:str = "black"
    ):
    """
    Given a graph, this function will color nodes and edges based on
    their attributes
    
    :param input_Graph: graph to color
    :param adversary: the adversary node in the graph
    :param victim: the victim node in the graph
    :param allies: ally nodes to the victim
    :param splitting_color: the color used to indicate splitting nodes and
        edges that result from these splits
    :param non_splitting_node_color: color used to indicate nodes that do
        not need to split, because they only have one outward pointing edge

    :type input_Graph: nx.classes.graph.Graph
    :type adversary: int
    :type victim: int
    :type allies: list
    :type splitting_color: str
    :type non_splitting_node_color: str

    :return: the graph with the set attributes
    :rytpe: nx.classes.graph.Graph
    """

    Graph = input_Graph.copy()
    
    # define a list for all special nodes
    special_nodes = [adversary, victim, *allies]
    
    # set the default attack volume for all nodes and edges
    for node in Graph.nodes:
        if Graph.nodes[node]["attack_vol"] != 0 and not node in special_nodes:
            # decide if the node on the path is actually splitting:
            if len(list(Graph.out_edges(node))) > 1:
                Graph.nodes[node]["color"] = splitting_color
            else:
                Graph.nodes[node]["color"] = non_splitting_node_color
    for u, v in Graph.edges:
        if Graph[u][v]["split_perc"] != 0:
            Graph[u][v]["color"] = splitting_color

    return Graph



def set_splits(
    G_init:nx.classes.graph.Graph, 
    victim:int, 
    adversary:int, 
    allies:list, 
    attack_volume:int, 
    ally_capabilites:list,
    seed:int
    ):
    """
    This function goes through a graph, which has been modified in order to divert attack traffic to 
    allies, and marks how much attack traffic each node will get, and how nodes should split traffic.
    
    :param G_init: the finished and modified graph
    :param victim: the victim node
    :param adversary: the adversary node
    :param allies: the ally nodes to the victim
    :param attack_volume: the attack volume of the adversary
    :param ally_capabilites: the allies' scrubbing capabilities
 
    :type G_init: nx.classes.graph.Graph
    :type victim: int
    :type adversary: int
    :type allies: list
    :type attack_volume: int
    :type ally_capabilites: list

    :return: the graph, where received attack volume and split percentages have been 
        added as node and edge attributes
    :rtype: nx.classes.graph.Graph           
    """    


    G = G_init.copy()
    
    # set the default attack volume for all nodes and edges
    for node in G.nodes:
        G.nodes[node]["attack_vol"] = 0
    for u, v in G.edges:
        G[u][v]["split_perc"] = 0
    
    # set the attack volume of the starting node
    G.nodes[adversary]["attack_vol"] = attack_volume
    
    # calculate the amount the victim has to cover
    victim_traffic = attack_volume - sum(ally_capabilites)

    # combine ally and victim information
    scrubbers = allies + [victim]
    scrubber_volume = ally_capabilites + [victim_traffic]

    scrubber_paths = []
    for scrubber in scrubbers:
        shortest_path_to_scrubber = list(nx.shortest_simple_paths(G, adversary, scrubber))[0]
        scrubber_paths.append([(u, v) for u, v in zip(shortest_path_to_scrubber[:-1], shortest_path_to_scrubber[1:])])

    # keeping track
    used_nodes = [adversary]
    used_edges_simple = []

    # go through each path, and add to each node on the path how much traffic it will relay
    for scrubber_indx, scrubber_path in enumerate(scrubber_paths):
        for u, v in scrubber_path:
            G.nodes[v]["attack_vol"] += scrubber_volume[scrubber_indx]
            used_nodes.append(v)
            used_edges_simple.append((u, v))
            
    # now, go through the used edges and calculate the split percentage
    # TODO more elegant filling of list
    for node in list(set(used_nodes)):
        # note the total attack volume it is relaying
        remaining = G.nodes[node]["attack_vol"]

        if remaining != 0: #TODO very rarely, this value is 0 and causes a division through 0 error,; dont understand how it happens
            # note all its outward pointing edges that are used for carrying attack traffic
            # and the corresponding nodes with their total incoming attack traffic
            outward_flows = [(G.nodes[v]["attack_vol"], (u, v)) for u, v in G.out_edges(node) if (u, v) in list(set(used_edges_simple))]
            # sort this from small to large by attack volumes
            outward_flows_sorted = sorted(outward_flows)
            # go through each next hop and calculate the percentage of traffic flowing their
            for next_hop_volume, (u, v) in outward_flows_sorted:
                G[u][v]["split_perc"] = min(next_hop_volume/G.nodes[node]["attack_vol"], remaining/G.nodes[node]["attack_vol"])
                remaining -= next_hop_volume
    return G