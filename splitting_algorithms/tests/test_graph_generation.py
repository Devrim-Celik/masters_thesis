"""
A PyTest file that contains test for validating functions from "generate_AS_network.py"

Author:
    Devrim Celik - 01.05.2022
"""


import sys
import networkx as nx
import pytest
import random
from typing import Callable

sys.path.insert(0, '..') # TODO is this smart ??? is there a better way

from main import generate_directed_AS_graph, graph_pruning_via_BFS	

NR_EXECUTIONS_PER_TEST = 2

@pytest.fixture
def generate_random_setup():
	"""
	Generates a set of parameters used for generating a initial graph.

	:return: a tuple containing two ints, the number of ASes and the number of allies.
	:rtype: tuple
	"""
	nr_ASes = random.randint(100, 500)
	nr_allies = random.randint(1, 8)

	return (nr_ASes, nr_allies)

@pytest.mark.repeat(NR_EXECUTIONS_PER_TEST)
def test_sink_behavoir(
	generate_random_setup:Callable
	):
	"""
	This function tests whether all nodes are able to reach the victim node in the graph.

	:param generate_random_setup: a pytest fixture that returns a tuple with two ints
	
	:type generate_random_setup: Callable

	:raises AssertionError: raises an exception if not all nodes can reach the victim node
	"""
	nr_ASes, nr_allies = generate_random_setup
	# generate a initial graph 
	G_init, victim, adversary, allies = generate_directed_AS_graph(nr_ASes, nr_allies)
	# and prune it
	G_pruned = graph_pruning_via_BFS(G_init, victim)

	# test if each node (that is not the victim itself) has the victim as one of their descendants
	has_connectivity = nr_ASes
	for node in range(nr_ASes):
		if (not victim in set(list(nx.descendants(G_init, node)))) and (node != victim) :
			has_connectivity -= 1
	assert has_connectivity == nr_ASes