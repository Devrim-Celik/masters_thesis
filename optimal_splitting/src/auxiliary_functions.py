import pickle
from pyvis.network import Network
import networkx as nx

def save_as_pickle(object_to_pickle, path):
    with open(path, 'wb') as handle:
        pickle.dump(object_to_pickle, handle, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"[+] Saved to \"{path}\".")

def load_pickle(path_to_pickle):
    with open(path_to_pickle, 'rb') as handle:
        unpickled_object = pickle.load(handle)
    print(f"[+] Loaded \"{path_to_pickle}\".")
    return unpickled_object

def gen_pyvis_network(G):
    """
    For Plotting. TODO
    """
    net = Network(
        notebook=True, 
        directed=True, 
        height='1000px', 
        width="100%"
    )
    net.inherit_edge_colors(False)
    net.from_nx(G)
    return net

def save_pyvis_network(G, html_path):
    net = gen_pyvis_network(G)
    net.save_graph(html_path)
    print(f"[+] Saved Graph to \"{html_path}\".")

def assign_attributes(
    Graph:nx.classes.graph.Graph, 
    victim_node:int, 
    adversary_node:int,
    helper_nodes:list = [],
    type_to_value:dict = {"T":30, "M": 20, "C":10, "CP":10}
):
    """
    Given a graph, the victim and adversary node (and optionally a set of helpers), this function will assign
    an array of attributes to these nodes.
    
    Args:
        Graph: the networkx graph object
        victim_node: the number of the node representing the destination of the DDoS attack traffic
        adversary_node: the number of the node representing the source of the DDoS attack traffic
        helper_nodes: a list of integers, representing the set of all helpers
    
    """
    for node_indx in range(len(Graph.nodes)):
        # colors according to attack/defense role
        if node_indx == victim_node:
            Graph.nodes[node_indx]["color"] = "green"
            Graph.nodes[node_indx]["victim"] = True
        elif node_indx == adversary_node:
            Graph.nodes[node_indx]["color"] = "red"
            Graph.nodes[node_indx]["adversary"] = True
        elif node_indx in helper_nodes:
            Graph.nodes[node_indx]["color"] = "blue"
            Graph.nodes[node_indx]["helper"] = True
        else:
            Graph.nodes[node_indx]["color"] = "darkgrey"
            
        # size according to type
        Graph.nodes[node_indx]["value"] = type_to_value[Graph.nodes[node_indx]["type"]]
            
    return Graph


def indicate_attack_paths(
    G_init:nx.classes.graph.Graph,
    adversary:int,
    victim:int,
    indication_color:str = "deeppink"
):
    G = G_init.copy()
    # use inbuild function to see all the paths that lead from adversary to victim
    all_attack_paths = list(nx.all_simple_paths(G, adversary, victim))

    # go through each of them, and color any non-colored nodes and edges
    for attack_path in all_attack_paths:
        for u, v in zip(attack_path[:-1], attack_path[1:]):
            if G.nodes[u]["color"] == "darkgrey":
                #G.nodes[u]["color"] = indication_color
                G.nodes[u]["opacity"] = 0.75 #doesnt work
            if not "color" in G[u][v]:
                G[u][v]["color"] = indication_color
                
    return G


def color_graph(G_init, adversary, victim, allies, color = "orange", non_splitting_node_color = "black"):
    
    G = G_init.copy()
    
    # define a list for all special nodes
    special_nodes = [adversary, victim, *allies]
    
    # set the default attack volume for all nodes and edges
    for node in G.nodes:
        if G.nodes[node]["attack_vol"] != 0 and not node in special_nodes:
            # decide if the node on the path is actually splitting:
            if len(list(G.out_edges(node))) > 1:
                G.nodes[node]["color"] = color
            else:
                G.nodes[node]["color"] = non_splitting_node_color
    for u, v in G.edges:
        if G[u][v]["split_perc"] != 0:
            G[u][v]["color"] = color

    return G