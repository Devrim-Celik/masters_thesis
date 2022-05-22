"""
Contains functions that implemented the algorithm to generate minimal changes
on an input graph such that attack traffic can be diverted to allies of the victim,
using a decentralized setting.

Author:
    Devrim Celik - 05.05.2022
"""


import networkx as nx
import numpy as np

def reachable_by_source(
    G:nx.classes.graph.Graph,
    victim:int,
    source:int,
    allies:list
    ):
    """
    This function will determine the set of all nodes that are reachable by the source
    of the DDoS traffic through graph traversion.
    
    
    :param initial_Graph: graph
    :param victim: the victim node
    :param source: the source node
    :param allies: the list of allies

    :type initial_Graph: nx.classes.graph.Graph
    :type victim: int
    :type source: int
    :type allies: list

    :return: all nodes reachable from the source, except for the victim and allies
    :rtype: list
    """
    
    # for recording nodes
    attack_flow_nodes = []
    
    # start a queue
    Q = [source]

    while Q:
        # get the next node
        current_node = Q.pop(0)
        attack_flow_nodes.append(current_node)

        # consider all its outward pointing edges
        for u, v in G.out_edges(current_node):

            # add the node to the queue, if it is node the victim node
            if not (v in allies + [victim] or v in attack_flow_nodes):
                Q.append(v)

    return attack_flow_nodes


def add_shortest_distances(
	initial_Graph:nx.classes.graph.Graph,
    victim:int,
	allies:list
	):
	"""
	This function will calculate the shortest distance to all ally nodes from all
	nodes that are not allies or victims. Note, that this information is available 
    to all of these nodes in the AS network through the length of the AS_PATH path attribute. 
    This information is a simulation of this information.

	:param initial_Graph: graph
    :param victim: the victim node
	:param allies: list of all allies

	:type initial_Graph: nx.classes.graph.Graph
	:type victim: int
	:type allies: list

	:return: the graph with added shortest distance information on attack path nodes
	:rtype: nx.classes.graph.Graph
	"""

	graph = initial_Graph.copy()
	undirected_graph = initial_Graph.to_undirected()

	for node in list(set(graph.nodes) - set(allies + [victim])):
		# create a dictionary for saving the shortest distances to all allies
		distances = {}

		for ally in allies:
			# calculate the shortest distance and note it down
			distances[ally] = len(list(nx.all_shortest_paths(undirected_graph.to_undirected(), node, ally))[0]) - 1 

		# save this ditionary as a node attribute
		graph.nodes[node]["distances_allies"] = distances

	return graph



def propagate_attack_magnitude(
    graph,
    start_node,
    attack_vol_to_carry,
    source,
    destination
    ):
    """
    TODO 
    """

    Q = [start_node] 

    while Q:
        # select the current node
        current_node = Q.pop(-1)

        # calculate how much attack traffic flows out of it
        # NOTE the if else, is if the victim node is the starting node, since it has no outflowing edges
        out_attack_vol = sum([graph[u][v][f"attack_vol_to_dst_{destination}"] for u, v in graph.out_edges(current_node)]) if not current_node == start_node else attack_vol_to_carry

        # then get a list of all edges that point towards the curret node, and
        # whose origin has the adversary as a anscestor and doesnt create a loop
        path_leads_to_source = lambda u, v: source in list(nx.ancestors(graph, u)) or u == source # to check whether this path leads to the source
        loop_prevention = lambda u, v: not current_node in list(nx.ancestors(graph, u)) # to prevent loops
        in_edges_source_anc = [(u, v) for u, v in graph.in_edges(current_node) if path_leads_to_source(u, v) and loop_prevention(u, v)]

        # we will equally split the attack traffic among these edges
        for u, v in in_edges_source_anc :
            graph[u][v][f"attack_vol_to_dst_{destination}"] = out_attack_vol/len(in_edges_source_anc)
            Q.append(u)

    return graph


def decentralized(
    initial_Graph:nx.classes.graph.Graph,
    victim:int,
    source:int,
    allies:list,
    ally_scrubbing_capabilities:list,
    attack_volume:int
    ):
    """
    This function implements a decentralized algorithm (in nature) to solve the 
    diverting problem.

    :param initial_Graph: the initial AS network graph
    :param victim: the victim node
    :param reachable_by_sourcerce: the node that is the source of the DDoS attack traffic
    :param allies: the list of ally nodes
    :param ally_scrubbing_capabilities: the list of the scrubbing capabilities of the allies
    :param attack_volume: the attack volume

    :type initial_Graph: nx.classes.graph.Graph
    :type victim: int
    :type source: int
    :type allies: list
    :type ally_scrubbing_capabilities: list
    :type attack_volume: int

    :return: the modified graph that is now diverting DDoS traffic to allies
    :rtype: nx.classes.graph.Graph
    """


    graph = initial_Graph.copy()
    undirected_graph = initial_Graph.to_undirected()

    # start by adding all shortest paths to the inform
    graph_w_dist = add_shortest_distances(graph, victim, allies)
    
    # this list will keep track of all nodes that are currently receiving attack traffic
    receiving_nodes = [node for node in graph_w_dist.nodes if graph_w_dist.nodes[node]["on_attack_path"]]

    used_allies = []

    while set(used_allies) != set(allies):
        # to avoid duplications
        receiving_nodes = list(set(receiving_nodes))

        # then find the node with the shortest distance to one of the allies
        min_node = None
        min_dist = float("inf")
        to_ally = None

        # check all nodes are currently receiving attack traffic, how far they are from the allies
        # NOTE: excluding allies and victim for now, may be changed
        for node in list(set(receiving_nodes) - set(allies + [victim])):
            distance_dict = graph_w_dist.nodes[node]["distances_allies"]
            for key, value in distance_dict.items():
                # if we find a shorter distance to an ally we are not yet connected
                # to, save the information
                if value < min_dist and not key in used_allies:
                    min_dist = value
                    min_node = node
                    to_ally = key

        # get the path in question
        path = list(nx.all_shortest_paths(undirected_graph.to_undirected(), min_node, to_ally))[0]
        
        # for deciding the correct splits later, we will set an attribute for
        # each edge that will represent how much traffic it must carry
        for u, v in graph.edges:    
            graph[u][v][f"attack_vol_to_dst_{to_ally}"] = 0


        # note that this node has to split a certain amount to the first edge in question
        # get the amount of traffic
        attack_traffic_to_ally = ally_scrubbing_capabilities[allies.index(to_ally)] 

        # now go through the path and change the path accordingly; also note the splits if necessary
        for u, v in zip(path[:-1], path[1:]):
            # if the edge need to be changed, do so
            if (v, u) in graph.edges:
                graph.remove_edge(v, u)
                graph.add_edge(u, v)
                graph[u][v][f"attack_vol_to_dst_{to_ally}"] = 0

            # in any case, denote that the edges and nodes are now receiving attack traffic
            graph[u][v]["on_attack_path"] = True
            graph.nodes[v]["on_attack_path"] = True
            receiving_nodes.append(node)

            # note how much attack traffic this edge has to carry
            graph[u][v][f"attack_vol_to_dst_{to_ally}"] += attack_traffic_to_ally

        # now, from the select node, go the path back up to the adversary and propagate 
        # the amount of traffic each edge must carry
        graph = propagate_attack_magnitude(
                    graph,
                    min_node,
                    attack_traffic_to_ally,
                    source,
                    to_ally
                    )


        # note that this ally is now reachable
        used_allies.append(to_ally)

    # also note the attack traffic for the victim
    for u, v in graph.edges:    
        graph[u][v][f"attack_vol_to_dst_{victim}"] = 0    
    graph = propagate_attack_magnitude(
                    graph,
                    victim,
                    attack_volume - sum(ally_scrubbing_capabilities),
                    source,
                    victim
                    )

    # for each edge, accumulate all the traffic to the different allies it needs to carry
    for u, v in graph.edges:
        graph[u][v]["attack_vol"] = sum([graph[u][v][key] for key in graph[u][v].keys() if "attack_vol_to_dst_" in key])


    # now go through each node, and calculate the split percentage if it has any edges that carry attacks in or out
    for node in graph.nodes:
        # collect or in and out going edges that carry attack volume
        in_nodes_w_attack = [(u, v) for u, v in graph.in_edges(node) if graph[u][v]["attack_vol"] != 0]
        out_nodes_w_attack = [(u, v) for u, v in graph.out_edges(node) if graph[u][v]["attack_vol"] != 0]

        # make sure that 
        if len(out_nodes_w_attack) != 0:
            # calculate how much is flowing in, or set it if the node is the source itself
            incoming_attack_vol = sum([graph[u][v]["attack_vol"] for u, v in in_nodes_w_attack]) if node != source else attack_volume
           
            # distribute it to all outflow  ing nodes
            for u, v in out_nodes_w_attack:
                graph[u][v]["split_perc"] = graph[u][v]["attack_vol"]/incoming_attack_vol

    return graph