


import networkx as nx
import numpy as np

def reachable_by_source(
    G:nx.classes.graph.Graph,
    victim:int,
    source:int,
    allies:list
    ):
    """
    TODO.
    
    
    :param initial_Graph: graph
    :param victim: the victim node
    :param source: the source node
    :param allies: the list of allies

    :type initial_Graph: nx.classes.graph.Graph
    :type victim: int
    :type source: int
    :type allies: list

    :return: all nodes reachable from the source, except for the victim and allies
    :rtype: tuple
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


def decentralized(
    initial_Graph:nx.classes.graph.Graph,
    victim:int,
    source:int,
    allies:list,
    ally_scrubbing_capabilities:list,
    attack_volume:int
    ):

    graph = initial_Graph.copy()
    undirected_graph = initial_Graph.to_undirected()

    # NOTE: NOTE ALL EDGES USED ON ORIGINAL ATTACK PATH FOR LATER SPLITITNG TODO

    # start by adding all shortest paths to the inform
    graph_w_dist = add_shortest_distances(graph, victim, allies)

    used_allies = []

    while set(used_allies) != set(allies):
        # first get a list of nodes that are currently reachable by the source
        reachable_nodes = reachable_by_source(
            graph_w_dist,
            victim,
            source,
            allies
            )

        # then find the node with the shortest distance to one of the allies
        min_node = None
        min_dist = float("inf")
        to_ally = None

        for node in reachable_nodes:
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
        
        # note that this node has to split a certain amount to the first edge in question
        attack_traffic = ally_scrubbing_capabilities[allies.index(to_ally)] 

        # now go through the path and change the path accordingly; also note the splits if necessary
        for u, v in zip(path[:-1], path[1:]):
            #print(u, v)
            # if the edge need to be changed, do so
            if (v, u) in graph.edges:
                graph.remove_edge(v, u)
                graph.add_edge(u, v)

            # note that this edge has to carry the attack traffic
            graph[u][v]["split_abs"] = attack_traffic

            # set the split_abs value for all edges from the next step to 0
            for u_out, v_out in graph.out_edges(v):
                graph[u_out][v_out]["spit_abs"] = 0


        # note that this ally is now reachable
        used_allies.append(to_ally)

    # TODO: SPLITS

    return graph


















'''
def identify_attack_flows(
    initial_Graph:nx.classes.graph.Graph,
    victim:int,
    adversary:int
    ):
    """
    TODO.
    
    
    :param initial_Graph: graph
    :param victim: the victim node
    :param adversary: the adversary node
    
    :type initial_Graph: nx.classes.graph.Graph
    :type victim: int
    :type adversary: int
    
    :return: a tuple containing (in order):
        * the graph with the added flow information on nodes and edges
        * a list of all nodes in the attack path, ordered from closes to adversary to farthest
    :rtype: tuple
    """

    graph = initial_Graph.copy()
    
    attack_flow_nodes = []
    
    # set a attribute denoting the path taken
    for node_indx in graph.nodes:
        graph.nodes[node_indx]["AS_paths"] = []
    for u, v in graph.edges:
        graph[u][v]["AS_paths"] = []

    # start a queue
    Q = [adversary]
    graph.nodes[adversary]["AS_paths"] = [[adversary]]

    while Q:
        # get the next node
        current_node = Q.pop(0)
        attack_flow_nodes.append(current_node)
        
        # consider all its outward pointing edges
        for u, v in graph.out_edges(current_node):
            # note the flows that path through this note
            graph[u][v]["AS_paths"] = graph.nodes[current_node]["AS_paths"]

            # if the next node is not the victim node, then add it
            graph.nodes[v]["AS_paths"].extend([path + [v] for path in graph[u][v]["AS_paths"]])
            # make it unique
            graph.nodes[v]["AS_paths"] = [list(x) for x in set(tuple(x) for x in graph.nodes[v]["AS_paths"])]

            # add the node to the queue, if it is node the victim node
            if v != victim:
                Q.append(v)

    return graph, list(set(attack_flow_nodes))
'''