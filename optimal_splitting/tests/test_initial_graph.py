import sys
import networkx as nx
import pytest
import random

sys.path.insert(0, '..') # TODO is this smart ??? is there a better way

from main import generate_supported_graph

@pytest.fixture
def generate_random_setup():
	"""
	Generates a set of parameters used for an experiment.

	Returns:
		nr_ASes (int)						number of ASes vertices
		nr_allies (int)						number of allies
		attack_volume (int)					attack volume	
		ally_scrubbing_capabilites (list): 	scrubbing capabilities of the allies
	"""
	nr_ASes = random.randint(100, 500)
	nr_allies = random.randint(1, 8)
	attack_volume = random.randint(50, 500)
	ally_scrubbing_capabilites = [random.randint(1, int(attack_volume/nr_allies)) for _ in range(nr_allies)]
	return (nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites)

#@pytest.mark.parametrize('execution_number', range(10))
def test_connectivity(generate_random_setup):
	# run a test, using a random setup and without saving the data
	data_dict = generate_supported_graph(*generate_random_setup, False, False)

	# test if each node (that is not a sink itself) has either the victim or the allies in their descendants
	sinks = [data_dict["victim"]] + data_dict["allies"]
	G = data_dict["G_with_splits_colored"]
	for node in list(G.nodes):
		if (not node in sinks) and (not set(list(nx.descendants(G, node))) & set(sinks)):
			assert False
	assert True

#@pytest.mark.parametrize('execution_number', range(10))
def test_connectivity(generate_random_setup):
	# run a test, using a random setup and without saving the data
	data_dict = generate_supported_graph(*generate_random_setup, False, False)

	# test if each node (that is not a sink itself) has either the victim or the allies in their descendants
	sinks = [data_dict["victim"]] + data_dict["allies"]
	G = data_dict["G_with_splits_colored"]
	reachable_nodes = len(list(G.nodes))
	for node in list(G.nodes):
		if (not node in sinks) and (not set(list(nx.descendants(G, node))) & set(sinks)):
			reachable_nodes -= 1
	assert reachable_nodes == len(list(G.nodes))

# TODO test to check that no attack path existis that is not covered by considering splits

# TODO test to check that the splits are correct
# * flow in = flow out
# * nodes get the right amount of flow

	