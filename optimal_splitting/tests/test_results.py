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
	# generate a random setup
	nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites = generate_random_setup

	# run a test, using a random setup and without saving the data
	data_dict = generate_supported_graph(nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites, False, False)

	# test if each node (that is not a sink itself) has either the victim or the allies in their descendants
	sinks = [data_dict["victim"]] + data_dict["allies"]
	G = data_dict["G_with_splits_colored"]
	has_connectivity = nr_ASes
	for node in list(G.nodes):
		if (not node in sinks) and (not set(list(nx.descendants(G, node))) & set(sinks)):
			has_connectivity -= 1
	assert has_connectivity == nr_ASes

#@pytest.mark.parametrize('execution_number', range(10))
def test_reachability_sinks_from_adv(generate_random_setup):
	# generate a random setup
	nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites = generate_random_setup

	# run a test, using a random setup and without saving the data
	data_dict = generate_supported_graph(nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites, False, False)

	# test if all sinks (allies and victim) can be reached from the victim
	# TODO consider splits
	sinks = [data_dict["victim"]] + data_dict["allies"]
	G = data_dict["G_with_splits_colored"]
	adv_desc = list(nx.descendants(G, data_dict["adversary"]))
	assert len(set(adv_desc) & set(sinks)) == len(sinks)

#@pytest.mark.parametrize('execution_number', range(10))
def test_correctness_of_changed_edges(generate_random_setup):
	# generate a random setup
	nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites = generate_random_setup

	# run a test, using a random setup and without saving the data
	data_dict = generate_supported_graph(nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites, False, False)

	# for all edges in the resulting graph, check whether they (or their reversed form) are contained in the original 
	# graph and that no edges were added/deleted
	# 	first collect all original and changed edges
	edges_init = list(data_dict["G_pruned"].edges)
	edges_changed = list(data_dict["G_with_splits_colored"].edges)

	# for checking that no edges were delted/added
	same_number_of_edges = len(edges_init) == len(edges_changed)
	# for checking that the only changes are reversion
	only_original_or_reversed = all([((u, v) in edges_init) | ((v, u) in edges_init) for u, v in edges_changed])

	assert  same_number_of_edges & only_original_or_reversed 



#@pytest.mark.parametrize('execution_number', range(10))
def test_correctness_of_splits(generate_random_setup):
	# generate a random setup
	nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites = generate_random_setup

	# run a test, using a random setup and without saving the data
	data_dict = generate_supported_graph(nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites, False, False)

	# TODO
	assert True

#@pytest.mark.parametrize('execution_number', range(10))
def test_there_is_no_unprotected_attack_path(generate_random_setup):
	# generate a random setup
	nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites = generate_random_setup

	# run a test, using a random setup and without saving the data
	data_dict = generate_supported_graph(nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites, False, False)


	# TODO
	assert True
