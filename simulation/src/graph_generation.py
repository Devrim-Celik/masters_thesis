
import networkx as nx
import random


from .aux import save_pyvis_network, assign_attributes


def to_directed_via_BFS(input_Graph, victim):
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
    Graph = input_Graph.copy()

    # representing the queue through a list and the pop(0) and append() methods
    Q = [victim]
    # for indicating, whether nodes were already explored a not
    explored = [False]*len(Graph.nodes)
    # for remembering which edges to remove and add
    edges_to_remove = []
    edges_to_add = []
    
    while Q:
        # assign the current node by dequeuing an element
        current = Q.pop(0)
        
        # consider all neighbors of the current node
        for neighbor in Graph.neighbors(current):
            
            if not explored[neighbor]:
                Q.append(neighbor)
                edges_to_remove.append((current, neighbor))
                edges_to_add.append((neighbor, current))
        #mark this node as explored
        explored[current] = True        
    
    # make G into a directed graph
    Graph = Graph.to_directed()

    # remove and add the edges, after checking if this action is legal
    for u,v in edges_to_remove:
        if (u, v) in Graph.edges:
            Graph.remove_edge(u, v)
    for u,v, in edges_to_add:
        if not (u, v) in Graph.edges:
            Graph.add_edge(u, v)
        
    return Graph




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




def generate_directed_AS_graph(nr_ASes, nr_allies, figures_path, attack_vol_min = 450, attack_vol_max = 550, scrubbing_cap_min = 5):
    """
    Creates a directed, acyclic network topology representing the AS network. Edges
    represent flows as directed by BGP for some IP range.
    Furthermore assigns a victim node, an adversary node and ally nodes.

    :param nr_ASes: number of AS to be in the graph
    :param nr_allies: number of allies willing to help scrubbing DDoS traffic      
    :param :
    :param :
    :param :
    :param :
    :param :

    :type nr_ASes: int
    :type nr_allies: int

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
    G = to_directed_via_BFS(G, victim)
    
    # prune
    G = graph_pruning_via_BFS(G, victim, 1)

    # add distances to all sinks
    G = add_AS_PATH_to_victim(G, victim)

    # save figure
    save_pyvis_network(G, f"{figures_path}/init_graph.html")

    # add attack volume limits to adversary
    a = random.randint(attack_vol_min, attack_vol_max)
    b = random.randint(attack_vol_min, attack_vol_max)
    attack_vol_limits = tuple(sorted([a, b]))
    G.nodes[adversary]["attack_vol_limits"] = attack_vol_limits

    # add scrubbing capabilities to victim
    G.nodes[victim]["scrubbing_cap"] = random.randint(200, attack_vol_max - 50) 

    # add scrubbing capabilities to ally
    remaining = attack_vol_min - scrubbing_cap_min * len(allies)
    for ally_indx in allies:
        tmp = random.randint(70, max(int(remaining/2), 80))
        G.nodes[ally_indx]["scrubbing_cap"] = tmp + scrubbing_cap_min
        remaining -= tmp # todo uncomment

    return G, victim, adversary, allies