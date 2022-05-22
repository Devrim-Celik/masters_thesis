"""
Contains auxiliary functions used to
    * save to / read from pickle files
    * vizualize graphs and save those vizualisations as html files
    * colors graphs
    * assess the cost of a proposed modification of an algorithm

Author:
    Devrim Celik - 01.05.2022
"""


import pickle
from pyvis.network import Network
import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

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


def comparison_plot(
    comparison_results_df:pd.DataFrame,
    figure_path:str,
    nr_ASes:int,
    nr_executions:int,
    figure_size:tuple = (16, 10),
    alpha:float = 0.8,
    verbose:bool = False
    ):
    """
    Used by `run_comparison`, this function uses the recorded cost data of different
    algorithms to generate a line plot to compare their performances.

    :param comparison_results_df: the recorded cost data
    :param figure_path: where to save the lineplot
    :param nr_ASes: number of ASes in the used graphs
    :param nr_executions: number of executions per comparison setting
    :param figure_size: size of the generated figure
    :param alpha: the opacity of the displayed lines
    :param verbose: verbose option

    :type comparison_results_df: pd.DataFrame
    :type figure_path: str
    :type nr_ASes: int
    :type nr_executions: int
    :type figure_size: tuple
    :type alpha: float
    :type verbose: bool
    """

    plt.figure(figsize = figure_size)
    sns.lineplot(
        data = comparison_results_df, 
        x = "nr_allies", 
        y = "cost", 
        hue = "mode", 
        alpha = alpha)
    plt.title(f"Comparison of Algorithms of Increasing Number of Allies.\nNumber of ASes: {nr_ASes}   |    Number of Executions: {nr_executions}")
    plt.legend(loc = 'upper left')

    plt.savefig(figure_path)
    
    if verbose:
        print(f"[+] Saved to \"{figure_path}\".")


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
    for u, v in Graph.edges:
        if "split_perc" in Graph[u][v].keys() and Graph[u][v]["split_perc"] != 0:
            Graph[u][v]["color"] = splitting_color

            if not u in special_nodes:
                if round(Graph[u][v]["split_perc"]) == 1:
                    Graph.nodes[u]["color"] = non_splitting_node_color
                else:
                    Graph.nodes[u]["color"] = splitting_color
    return Graph


def cost_function(
    G_original:nx.classes.graph.Graph,
    G_modified:nx.classes.graph.Graph,
    victim:int,
    source:int,
    allies:list,
    step_cost:float,
    router_entry_change_cost:float
    ):
    """
    This function implements a cost function, that compares the cost for the modifictions
    of the original graph.
    
    :param G_original: the original AS network topology
    :param G_modified: the modified AS network topology
    :param victim: the victim node in the graph
    :param source: the source of the DDoS attack traffic
    :param allies: ally nodes to the victim
    :param step_cost: the cost for each hop the attack traffic flows after
        having split from the original attack path
    :param router_entry_change_cost: cost for "manually" changing a single
        entry in a routers BGP routing table

    :type G_original: nx.classes.graph.Graph
    :type G_modified: nx.classes.graph.Graph
    :type victim: int
    :type source: int
    :type allies: list
    :type step_cost: float
    :type router_entry_change_cost: float

    :return: the cost of the modifications
    :rytpe: int
    """

    ###########################################################################
    # part 1 of cost function: count the number of router table entry changes #
    ###########################################################################
    # each reversion of an edge implies changing the routing table of twe BGP routers
    edge_reversions = 0
    for edge in G_original.edges:
        if not edge in G_modified.edges:
            edge_reversions += 1
    cost_change = 2 * edge_reversions * router_entry_change_cost


    ################################################################################
    # part 2 of cost function: count the number of edges added to the attack flows #
    ################################################################################
    attack_path_edges_original = []
    attack_path_edges_modified = []

    # calculate the edges that are on the attack path in the original graph
    attack_flows_original = list(nx.all_simple_paths(G_original, source, victim))
    for attack_flow in attack_flows_original:
        for edge in zip(attack_flow[:-1], attack_flow[1:]):
            attack_path_edges_original.append(edge)
    nr_edges_attack_flow_original = len(set(attack_path_edges_original))


    # calculate the edges that are on the attack path in the modified graph
    attack_flows_modified = list(nx.all_simple_paths(G_modified, source, victim))
    for ally in allies:
        attack_flows_modified += list(nx.all_simple_paths(G_modified, source, ally))
    for attack_flow in attack_flows_modified:
        for edge in zip(attack_flow[:-1], attack_flow[1:]):
            attack_path_edges_modified.append(edge)
    nr_edges_attack_flow_modified = len(set(attack_path_edges_modified))

    # calculate the number of added edges on the attack flow and multipy by step_cost
    cost_path_length = step_cost * (nr_edges_attack_flow_modified - nr_edges_attack_flow_original)

    return cost_change + cost_path_length