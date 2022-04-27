import sys
import networkx as nx
import pytest
import random

sys.path.insert(0, '../src') # TODO is this smart ??? is there a better way

from .generate_AS_network import generate_directed_AS_graph, graph_pruning_via_BFS	
# generate a directed graph represnting the AS network

@pytest.fixture
def generate_random_setup_for_init():
	"""
	Generates a set of parameters used for generating a initial graph.

	Returns:
		nr_ASes (int)						number of ASes vertices
		nr_allies (int)						number of allies
	"""
	nr_ASes = random.randint(100, 500)
	nr_allies = random.randint(1, 8)

	return (nr_ASes, nr_allies)

#@pytest.mark.parametrize('execution_number', range(10))
def test_sink_behavoir(generate_random_setup):

	nr_ASes, nr_allies = generate_random_setup
	# generate a initial graph 
	G_init, victim, adversary, allies = generate_directed_AS_graph(nr_ASes, nr_allies)
	# and prune it
	G_pruned = graph_pruning_via_BFS(G_init, victim)

	# test if each node (that is not the victim itself) has the victim as one of their descendants
	has_connectivity = nr_ASes
	for node in range(nr_ASes):
		if (not victim in set(list(nx.descendants(G, node)))) and (node != sinks) :
			has_connectivity -= 1
	assert has_connectivity == nr_ASes