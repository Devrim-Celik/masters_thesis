"""
Contains functions to generate graphs which will be used for simulations.

Author:
    Devrim Celik 08.06.2022
"""
import networkx as nx
import random

from .auxiliary_functions import assign_attributes


def to_directed_via_bfs(input_graph, victim):
    """
    Used to make an undirected Graph with a victim node into a directed graph, such that
    the resulting graph is a sensible assignment for a directed, acyclic graph with a sink,
    representing the victim node. It represents the traffic flow with a destination located in
    the victim AS.

    :param G_init: undirected networkx graph, reprsenting AS network
    :param victim: victim node identifier

    :type G_init: nx.classes.graph.Graph
    :type victim: int

    :return: directed graph
    :rytpe: nx.classes.graph.Graph
    """
    graph = input_graph.copy()

    # representing the queue through a list and the pop(0) and append() methods
    Q = [victim]
    # for indicating, whether nodes were already explored a not
    explored = [False]*len(graph.nodes)
    # for remembering which edges to remove and add
    edges_to_remove = []
    edges_to_add = []
    
    while Q:
        # assign the current node by dequeuing an element
        current = Q.pop(0)
        
        # consider all neighbors of the current node
        for neighbor in graph.neighbors(current):
            
            if not explored[neighbor]:
                Q.append(neighbor)
                edges_to_remove.append((current, neighbor))
                edges_to_add.append((neighbor, current))
        #mark this node as explored
        explored[current] = True        
    
    # make G into a directed graph
    graph = graph.to_directed()

    # remove and add the edges, after checking if this action is legal
    for u, v in edges_to_remove:
        if (u, v) in graph.edges:
            graph.remove_edge(u, v)
    for u, v, in edges_to_add:
        if not (u, v) in graph.edges:
            graph.add_edge(u, v)
        
    return graph




def add_AS_PATH_to_victim(graph_init, victim):
    """
    This function will take a graph, and add the "as_path_to_victim" attribute to all notes,
    containg the set of nodes that form the shortest path from every node to the victim node.
    """
    graph = graph_init.copy()

    for node_indx in graph.nodes:
        # calculate shortest path
        as_path = list(nx.shortest_path(graph, node_indx, victim))
        graph.nodes[node_indx]["as_path_to_victim"] = as_path

    return graph


def graph_pruning_via_BFS(
    Graph:nx.classes.graph.Graph,
    victim:int,
    max_out_edges:int = 1
):
    """
    Prunes a graph, by considering all outward pointing edges of every node,
    associating with each of them how far the victim node is if one were to 
    follow them, and then to delete all nodes that do not have the shortest distance. 

    :param Graph: undirected networkx graph, reprsenting AS network
    :param victim: victim node
    :param max_out_edges: max number of outward pointing edges a node may habe

    :type G_init: nx.classes.graph.Graph
    :type victim: int
    :type max_out_edges: int

    :return: pruned graph
    :rytpe: nx.classes.graph.Graph
    """

    # make a copy to not mingle with the original graph
    G_pruned = Graph.copy()
    
    # get a list of all nodes, minus the victim node (it has only incoming connections)
    all_nodes = list(G_pruned.nodes)
    all_nodes.remove(victim)
    
    nr_edges_pruned = 0
    
    # go through each node
    for node in all_nodes:
        # get a list of all outward pointing edges
        outward_edges = list(G_pruned.out_edges(node))

        # then for each, determine the length of the shortest path
        costs = []
        for _, next_node in outward_edges:
            costs.append(len(list(nx.shortest_simple_paths(G_pruned, next_node, victim))[0]))

        # then remove all the ones who dont belong to the set of shortest
        shortest_path_length = min(costs)
        delete = [indx for indx, cost in enumerate(costs) if cost != shortest_path_length]
        for delete_indx in delete:
            u, v = outward_edges[delete_indx]
            G_pruned.remove_edge(u, v)
            nr_edges_pruned += 1

        # then, if it is still move than max_out_edges, remove the appropriate amount of edges
        outward_edges = list(G_pruned.out_edges(node))
        if len(outward_edges) > max_out_edges:
            to_delete = random.sample(outward_edges, len(outward_edges) - max_out_edges)
            for u, v in to_delete:
                G_pruned.remove_edge(u, v)
                nr_edges_pruned += 1

    return G_pruned




def generate_directed_AS_graph(nr_ASes, nr_allies, full_attack_vol):
    """
    Creates a directed, acyclic network topology representing the AS network. Edges
    represent flows as directed by BGP for some IP range.
    Furthermore assigns a victim node, an adversary node and ally nodes. 

    Also, this function will assign the attack volume of the source and the 
    scrubbing capabilities of the victim and the allies.

    :param nr_ASes: number of AS to be in the graph
    :param nr_allies: number of allies willing to help scrubbing DDoS traffic      
    :param full_attack_vol: the attack volume of the DDoS attack in Mbps


    :type nr_ASes: int
    :type nr_allies: int
    :type full_attack_vol: float

    :return: a tuple containing
        * the generated graph
        * the victim node
        * the adversary node
        * the allies of the victim
    :rtype: tuple
    """

    # generate the an undirected graph, whose topology is close to the AS network
    G = nx.random_internet_as_graph(nr_ASes)

    # get the list of customers and content-providers
    customers_and_cps = [indx for indx in range(nr_ASes) if G.nodes[indx]["type"] in ["C", "CP"]]

    # from this list, randomly select the victim, adversary and allies
    selected = random.sample(customers_and_cps, nr_allies+2)
    victim = selected[0]
    adversary = selected[1]
    allies = selected[2:]

    # assign attributes (e.g. color)
    G = assign_attributes(G, victim, adversary, allies)
    
    # change it to a directed, acyclic graph, with the victim as a sink
    G = to_directed_via_bfs(G, victim)
    
    # prune
    G = graph_pruning_via_BFS(G, victim, 1)

    # add distances to all sinks
    G = add_AS_PATH_to_victim(G, victim)

    # add attack volume limits to adversary
    G.nodes[adversary]["full_attack_vol"] = full_attack_vol

    # add scrubbing capabilities to victim
    G.nodes[victim]["scrubbing_cap"] = random.randint(int(full_attack_vol/5), int(full_attack_vol/3)) 

    # add scrubbing capabilities to ally
    avg_scrub = (full_attack_vol - G.nodes[victim]["scrubbing_cap"]) / nr_allies
    fake_shit = {135: 600, 65: 400}
    for ally_indx in allies:
        #G.nodes[ally_indx]["scrubbing_cap"] = random.randint(100, int(avg_scrub)) * 1.5
        #G.nodes[ally_indx]["scrubbing_cap"] = random.randint(50, 100) * 6
        G.nodes[ally_indx]["scrubbing_cap"] = fake_shit[ally_indx]

    return G, victim, adversary, allies