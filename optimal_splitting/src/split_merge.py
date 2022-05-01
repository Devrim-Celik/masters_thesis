"""
Contains functions that implemented the algorithm to generate minimal changes
on an input graph such that attack traffic can be diverted to allies of the victim.

Author:
    Devrim Celik - 01.05.2022
"""


import random
import networkx as nx
import numpy as np

def calculate_merge_split_cost(
    G:nx.classes.graph.Graph,
    victim:int, 
    adversary:int,
    attack_path:list,
    ally:int,
    ally_path:list,
    step_cost:int = 2,
    split_step_cost:int = 1,
    change_cost:int = 5,
    unwanted_change_cost:int = 50,
    return_shortest_path_and_prime_graph:bool = False,
):
   """
    Creates a directed, acyclic network topology representing the AS network. Edges
    represent flows as directed by BGP for some IP range.
    Furthermore assigns a victim node, an adversary node and ally nodes.

    :param nr_ASes: number of AS to be in the graph
    :param nr_allies: number of allies willing to help scrubbing DDoS traffic      

    :type nr_ASes: int
    :type nr_allies: int

    :return: a tuple containing
        * the generated graph
        * the victim node
        * the adversary node
        * the allies of the victim
    :rtype: tuple
    """

    # start by initializing G prime as a copy of G
    G_prime = G.copy()
    
        
    # set the cost of travelling along the attack path to step cost
    for u, v in zip(attack_path[:-1], attack_path[1:]): # TODO IS THIS IRRELEVANT NOW
        G_prime[u][v]["weight"] = step_cost
        G_prime[u][v]["edge_origin"] = "original_attack_path"

    # then set the cost of all other edges to split_step_cost
    for u,v in G_prime.edges:
        if not "edge_origin" in G_prime[u][v]:
            G_prime[u][v]["weight"] = split_step_cost
            G_prime[u][v]["edge_origin"] = "split_original"
    
    # for each edge, add the opposite edge with cost change_cost
    edges = list(G_prime.edges) # since it is changing during the loop
    for u,v in edges:
        G_prime.add_edge(v, u)
        G_prime[v][u]["weight"] = change_cost + split_step_cost
        G_prime[v][u]["edge_origin"] = "changed"
    """
    # set the reverse of the ally path to split_step_cost
    for u, v in zip(ally_path[:-1], ally_path[1:]):
        G_prime[v][u]["weight"] = split_step_cost
        G_prime[v][u]["edge_origin"] = "ally_changed"
    """
    
    # set the unwanted changes, i.e., going through the victim
    for (u, v) in G_prime.in_edges(victim):
        G_prime[u][v]["weight"] = unwanted_change_cost
        G_prime[u][v]["edge_origin"] = "no_change_wanted"
    
    # caculate the shortest path from adversary to ally
    shortest_paths_generator = nx.shortest_simple_paths(G_prime, adversary, ally, weight="weight")
    shortest_path = next(shortest_paths_generator)

    # go through it, and calculate the associated cost and check whether a edge was changed
    total_cost = 0
    edge_changes = []
    used_edges = [] # also contains the edges that are used, but not changes, in 
                    # contrast to edge_changes, that only contains the changes
                    # edges on the path
    for u, v in zip(shortest_path[:-1], shortest_path[1:]):
        associated_edge_data = G_prime.get_edge_data(u, v)
        total_cost += associated_edge_data["weight"]
        used_edges.append((u, v))
        if "change" in associated_edge_data["edge_origin"]:
            edge_changes.append((u, v))
    
    return total_cost, edge_changes, used_edges
    
def build_cost_and_split_matrices(
    G:nx.classes.graph.Graph,
    victim:int, 
    adversary:int, 
    allies:list
):
    """
    Given that the "calculate_merge_split_cost" function is implemeted and implemented correctly, this 
    function will calculate the costs of trying to divert attack traffic to an ally. Explicitly, it will return
    a matrix with the cost of doing so for each (attack_path, ally) pair, together with the associated node 
    that is responsible for splitting the traffic, if there is such a node.
    
    :param G: nx.classes.graph.Graph
    :param victim: victim node
    :param adversary: adversary node
    :param allies: ally nodes to the victim

    :type G: nx.classes.graph.Graph
    :type victim: int
    :type adversary: int
    :type allies: int
    
    :return: a tuple with the following elements (in this order)
        * a matrix that contain the cost for merges, rows represent helpers, columns represent attack paths
        * a list of lists, containing the associated paths to change for the different diverting actions
        * a list of lists, containing all used edges (not only changed ones) associated to the diverting actions
            TODO the second argument can easily be extracted form the third
    :rtype: np.ndarray           
    """

    # determine all attack paths
    attack_paths = list(nx.all_simple_paths(G, adversary, victim))
    
    # determine all support paths
    allies_paths = [list(nx.all_simple_paths(G, ally, victim)) for ally in allies]

    # matrix for noting the merge cost and the splitting node if there is any
    # also a list for saving the done changes
    cost_matrix = np.zeros((len(allies), len(attack_paths))).astype("int")
    changes_list = [[None for _ in range(len(attack_paths))] for _ in range(len(allies))]
    used_edges_list = [[None for _ in range(len(attack_paths))] for _ in range(len(allies))]

    # pair each attack flow with each helper
    for attack_path_indx, attack_path in enumerate(attack_paths):
        for ally, ally_paths in enumerate(allies_paths):
            
            # since one ally may have multiple paths, and we are only interested in the one with the
            # lowest cost, we will collected them
            cost_collector = []
            change_collector = []
            used_edges_collector = []
            
            # go through all possible paths of the ally to the victim
            for ally_path in ally_paths:

                # and calculate the cost for merge/splitting and the splitting node if there is any
                cost, changes, used_edges = calculate_merge_split_cost(G, victim, adversary, attack_path, allies[ally], ally_path)
                # append the to the corresponding collectors
                cost_collector.append(cost)
                change_collector.append(changes)
                used_edges_collector.append(used_edges)
            # determine the best split, according to lowest cost, and write it together with the associated
            # splitting node into the previously calculated matrices
            cost_matrix[ally, attack_path_indx] = min(cost_collector)
            changes_list[ally][attack_path_indx] = change_collector[cost_collector.index(min(cost_collector))]
            used_edges_list[ally][attack_path_indx] = used_edges_collector[cost_collector.index(min(cost_collector))]
            
    return cost_matrix, changes_list, used_edges_list

def ally_assignment_problem(
    cost_matrix:np.ndarray, 
    changes_list:list,
    nr_allies:int,
):
    """
    This function solves the ally assignment problem. It considers a cost matrix, containing the cost for diverting
    a certain attack path towards a certain ally, and tries to assign the diverting of attack paths to the allies.
    
    :param cost_matrix: matrix containing the costs, rows represent allies and columns represent attack flows
    :param changes_list: a list of lists, containing the associated changes to those diverting actions
    :param nr_allies: number of allies TODO we can remove this, since this information is the nr of rows of the cost matrix

    :type cost_matrix: np.ndarray
    :type changes_list: list
    :type nr_allies: int

    :return: a list containing all changes of the selected diverting actions
    :rtype: list

    :TODO: check how to avoid that the different solutions contradict each other          
    """

    # for collecting all the final changes to be done
    changes_to_be_done = []
    used_allies = []
    associated_costs = []
    
    # for each attack flow, check the ally that has the lowest cost for helping
    for attack_flow_indx in range(cost_matrix.shape[1]):
        
        # get all costs of the helpers
        ally_costs = cost_matrix[:, attack_flow_indx]
        
        # NOTE: if there a multiple solution with the same cost, choose randomly one ally
        ally_min_value = np.min(ally_costs)
        lowest_allies = [ally_indx for ally_indx in range(len(ally_costs)) if ally_costs[ally_indx] == ally_min_value]
        chosen_ally = random.choice(lowest_allies)
        
        # note the parameteres
        used_allies.append(chosen_ally)
        associated_costs.append(ally_min_value)
        changes_to_be_done.append(changes_list[chosen_ally][attack_flow_indx])

    # determine all the unique allies used
    used_allies_unique = list(set(used_allies))

    if len(used_allies_unique) != nr_allies:
        # if not all allies were used, determine an attack flow were the addition of the not
        # ally causes the least increase in cost
        unused_allies = [ally_indx for ally_indx in range(nr_allies) if not ally_indx in used_allies_unique]

        for unused_ally in unused_allies:

            cost_difference = [cost_matrix[unused_ally][attack_flow_indx] - associated_costs[attack_flow_indx] for attack_flow_indx in range(cost_matrix.shape[1])]
            min_cost_difference = np.min(cost_difference)
            lowest_cost_differences_indices = [attack_flow_indx for attack_flow_indx in range(cost_matrix.shape[1]) if cost_difference[attack_flow_indx] == min_cost_difference]
            chosen_attack_flow = random.choice(lowest_cost_differences_indices)

            # mark it down, add the new change, dont delete the old one, because if there is only one attack flow, all should pariticpate
            used_allies.append(unused_ally)
            associated_costs.append(cost_matrix[unused_ally][chosen_attack_flow])
            changes_to_be_done.append(changes_list[unused_ally][chosen_attack_flow])

    # make a list of all the changes to be done
    final_changes = [item for sublist in changes_to_be_done for item in sublist]
    final_changes = list(set(final_changes))
  
    return final_changes    


def apply_changes(
    input_Graph:nx.classes.graph.Graph,
    list_of_edge_changes:list
    ):
    """
    Given a graph, and a list of edges, this function will change the topology of the
    graph by reversing the direction of edges, such that all the edges in the input list
    are contained in the new graph.
    
    :param input_Graph: the graph that whose topology will be changed
    :param list_of_edge_changes: list of edges that should be included by reversing original edges

    :type input_Graph: nx.classes.graph.Graph
    :type list_of_edge_changes: list

    :return: the changed graph
    :rtype: nx.classes.graph.Graph           
    """

    Graph = input_Graph.copy()

    # turn the indicated edges, and also change their color
    for u, v in list_of_edge_changes:
        Graph.remove_edge(v, u)
        Graph.add_edge(u, v)

    return Graph


def set_splits(
    G_init:nx.classes.graph.Graph, 
    victim:int, 
    adversary:int, 
    allies:list, 
    used_edges_list:list, 
    attack_volume:int, 
    ally_capabilites:list
    ):
    """
    This function goes through a graph, which has been modified in order to divert attack traffic to 
    allies, and marks how much attack traffic each node will get, and how nodes should split traffic.
    
    :param G_init: the finished and modified graph
    :param victim: the victim node
    :param adversary: the adversary node
    :param allies: the ally nodes to the victim
    :param used_edges_list: the used edges of the different diverting paths
    :param attack_volume: the attack volume of the adversary
    :param ally_capabilites: the allies' scrubbing capabilities
 
    :type G_init: nx.classes.graph.Graph
    :type victim: int
    :type adversary: int
    :type allies: list
    :type used_edges_list: list
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
    # calculate the shortest path to the victim from the adversary
    victim_path = list(nx.shortest_simple_paths(G, adversary, victim))[0]
    
    
    # combine ally and victim information
    scrubbers = allies + [victim]
    scrubber_volume = ally_capabilites + [victim_traffic]
    scrubber_paths = [edge_list[0] for edge_list in used_edges_list] + [[(u, v) for u, v in zip(victim_path[:-1], victim_path[1:])]]
    
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

