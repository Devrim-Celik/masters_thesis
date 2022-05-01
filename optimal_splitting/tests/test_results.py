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

@pytest.mark.repeat(0)
def test_connectivity(generate_random_setup):
	# generate a random setup
	nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites = generate_random_setup

	# run a test, using a random setup and without saving the data
	data_dict = generate_supported_graph(nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites, False, False)

	# test if each node (that is not a sink itself) has either the victim or the allies in their descendants
	sinks = [data_dict["victim"]] + data_dict["allies"]
	G = data_dict["G_with_splits_colored"]
	for node in list(G.nodes):
		if (not node in sinks) and (not set(list(nx.descendants(G, node))) & set(sinks)):
			assert False
	assert True

@pytest.mark.repeat(0)
def test_reachability_sinks_from_adv(generate_random_setup):
	# generate a random setup
	nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites = generate_random_setup

	# run a test, using a random setup and without saving the data
	data_dict = generate_supported_graph(nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites, False, False)

	# test if all sinks (allies and victim) can be reached from the victim
	sinks = [data_dict["victim"]] + data_dict["allies"]
	G = data_dict["G_with_splits_colored"]
	adv_desc = list(nx.descendants(G, data_dict["adversary"]))

	assert len(set(adv_desc) & set(sinks)) == len(sinks)


@pytest.mark.repeat(0)
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

	assert same_number_of_edges & only_original_or_reversed


@pytest.mark.repeat(300)
def test_distribution_of_attack_flow(generate_random_setup):
	# generate a random setup
	nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites = generate_random_setup

	# run a test, using a random setup and without saving the data
	data_dict = generate_supported_graph(nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites, False, False)

	### for each node, note the amount of attack traffic it is supposed to receive
	### this is our "goal"
	expected_attack_traffic = [0 for _ in range(nr_ASes)]
	expected_attack_traffic[data_dict["victim"]] = attack_volume - sum(ally_scrubbing_capabilites)
	for ally, ally_capabilities in zip(data_dict["allies"], ally_scrubbing_capabilites):
		expected_attack_traffic[ally] = ally_capabilities

	### calculate how much each node actually received
	G = data_dict["G_with_splits_colored"]
	received_attack_traffic = [0 for _ in range(nr_ASes)]
	received_attack_traffic[data_dict["adversary"]] = attack_volume
	
	S = [data_dict["adversary"]]
	
	while S:
		# get the current node
		current_node = S.pop(-1)
		# check that has it outwards pointing edges
		outward_edges = list(G.out_edges(current_node))
		# if there exist outward pointing edges...
		if outward_edges:
			# get a list of all the outward pointing edges with the corresponding split percentages
			outward_edges_w_perc = [(u, v, G[u][v]["split_perc"]) for u, v in outward_edges]
			# check that "incoming traffic vol = outgoing traffic vol" by testing that the outgoing
			# split percentages sum up to one
			if round(sum([x[2] for x in outward_edges_w_perc])) != 1:
				print(data_dict["random_seed"], outward_edges_w_perc)
				assert False # TODO gets triggered????
			# now start transfering the traffic from the current node to its neighbors
			incoming_vol = received_attack_traffic[current_node]
			received_attack_traffic[current_node] = 0
			for u, v, percentage in outward_edges_w_perc:
				received_attack_traffic[v] += incoming_vol * percentage
				# also add the neighbors to the stack, if they received any traffic
				if percentage > 0:
					S.append(v)

	assert all([expected == round(received) for (expected, received) in zip(expected_attack_traffic, received_attack_traffic)])