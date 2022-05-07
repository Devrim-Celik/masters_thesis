


import networkx as nx
import numpy as np



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



def add_shortest_distances(
	initial_Graph:nx.classes.graph.Graph,
	attack_flow_nodes:list,
	allies:list
	):
	"""
	This function will calculate the shortest distance to all ally nodes from all
	nodes that are on the attack flow and add this information as a node attribute
	to them. Note, that this information is available to all of these nodes in the
	AS network through the length of the AS_PATH path attribute. This information
	is a simulation of this information.

	:param initial_Graph: graph
	:param attack_flow_nodes: a list of all nodes that are on the attack path
	:param allies: list of all allies

	:type initial_Graph: nx.classes.graph.Graph
	:type attack_flow_nodes: list
	:type allies: list

	:return: the graph with added shortest distance information on attack path nodes
	:rtype: nx.classes.graph.Graph
	"""

	graph = initial_Graph.copy()
	undirected_graph = initial_Graph.to_undirected()

	for attack_flow_node in attack_flow_nodes:
		# create a dictionary for saving the shortest distances to all allies
		distances = {}

		for ally in allies:
			# calculate the shortest distance and note it down
			distances[ally] = len(list(nx.all_shortest_paths(undirected_graph.to_undirected(), attack_flow_node, ally))[0]) - 1 

		# save this ditionary as a node attribute
		graph.nodes[attack_flow_node]["ally_distances"] = distances

	return graph


def assignment_problem(
	initial_Graph:nx.classes.graph.Graph,
	allies:list,
	nr_attack_flows:int,
	):

	graph = initial_Graph.copy()

	# this will represent the centralized knowledge of all attack flow nodes
	distance_matrix  = np.zeros((len(allies), len(attack_flows)))

	# a list to keep track of all the covered attack flows and used allies
	used_allies = [False for _ in range(len(allies))]
	covered_attack_flows = [False for _ in range(len(allies))]