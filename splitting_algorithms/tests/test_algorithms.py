"""
A PyTest file that contains test for validating functions from "centralized_control_functions.py"

Author:
    Devrim Celik - 01.05.2022
"""


import sys
import networkx as nx
import pytest
import random
from typing import Callable

sys.path.insert(0, '..') # TODO is this smart ??? is there a better way

from main import run_experiment

NR_EXECUTIONS_PER_TEST = 100

@pytest.fixture
def generate_random_setup():
	"""
	Generates a set of parameters used for generating an experiment.

	:return: a tuple containing three ints and a list (in this order):
		* number of ASes
		* number of allies
		* attack volume
		* scrubbing capabilities of the allies
	:rtype: tuple
	"""

	nr_ASes = random.randint(100, 500)
	nr_allies = random.randint(1, 5)
	attack_volume = random.randint(50, 500)
	ally_scrubbing_capabilites = [random.randint(2, int(attack_volume/nr_allies)) - 1 for _ in range(nr_allies)]
	return (nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites)


@pytest.mark.repeat(NR_EXECUTIONS_PER_TEST)
def test_connectivity(
	mode:str,
	generate_random_setup:Callable
	):
	"""
	This function tests whether all nodes are able to reach the victim node or an ally.

	:param generate_random_setup: a pytest fixture that returns a tuple with a random setup
	
	:type generate_random_setup_for_init: Callable

	:raises AssertionError: raises an exception if not all nodes can reach the victim node or an ally node
	"""

	# generate a random setup
	nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites = generate_random_setup

	# run a test, using a random setup and without saving the data
	data_dict = run_experiment(mode, nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites, False, False)


	# test if each node (that is not a sink itself) has either the victim or the allies in their descendants
	sinks = [data_dict["victim"]] + data_dict["allies"]
	G = data_dict["G_modified_colored"]
	for node in list(G.nodes):
		if (not node in sinks) and (not set(list(nx.descendants(G, node))) & set(sinks)):
			assert False
	assert True


@pytest.mark.repeat(NR_EXECUTIONS_PER_TEST)
def test_reachability_sinks_from_adv(
	mode:str,
	generate_random_setup:Callable
	):
	"""
	This function tests whether the adversary can reach all sinks, i.e., the allies and the victim.

	:param generate_random_setup: a pytest fixture that returns a tuple with a random setup
	
	:type generate_random_setup_for_init: Callable

	:raises AssertionError: raises an exception if the adversary can not reach all sinks
	"""

	# generate a random setup
	nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites = generate_random_setup

	# run a test, using a random setup and without saving the data
	data_dict = run_experiment(mode, nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites, False, False)

	# test if all sinks (allies and victim) can be reached from the adversary
	sinks = [data_dict["victim"]] + data_dict["allies"]
	G = data_dict["G_modified_colored"]
	adv_desc = list(nx.descendants(G, data_dict["adversary"]))

	assert len(set(adv_desc) & set(sinks)) == len(sinks)


@pytest.mark.repeat(NR_EXECUTIONS_PER_TEST)
def test_correctness_of_changed_edges(
	mode:str,
	generate_random_setup:Callable
	):
	"""
	This function validates that the only changes done to the original graph are the reversion 
	of edge directions, i.e., no edges were deleted or added.

	:param generate_random_setup: a pytest fixture that returns a tuple with a random setup
	
	:type generate_random_setup_for_init: Callable

	:raises AssertionError: raises an exception if any other changes than edge reversions were done
	"""

	# generate a random setup
	nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites = generate_random_setup

	# run a test, using a random setup and without saving the data
	data_dict = run_experiment(mode, nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites, False, False)

	# for all edges in the resulting graph, check whether they (or their reversed form) are contained in the original 
	# graph and that no edges were added/deleted
	# 	first collect all original and changed edges
	edges_init = list(data_dict["G_pruned"].edges)
	edges_changed = list(data_dict["G_modified_colored"].edges)

	# for checking that no edges were delted/added
	same_number_of_edges = len(edges_init) == len(edges_changed)
	# for checking that the only changes are reversion
	only_original_or_reversed = all([((u, v) in edges_init) | ((v, u) in edges_init) for u, v in edges_changed])

	assert same_number_of_edges & only_original_or_reversed


@pytest.mark.repeat(NR_EXECUTIONS_PER_TEST)
def test_distribution_of_attack_flow(
	mode:str,
	generate_random_setup:Callable
	):
	"""
	This function starts at the adversary and follows traverses all possible paths from it 
	along the edge directions. During this traversal, it validates whether the amount of traffic
	that each node on the way receives and the splits along different edges (both saved as 
	attributes in the graph) are correct.

	:param generate_random_setup: a pytest fixture that returns a tuple with a random setup
	
	:type generate_random_setup_for_init: Callable

	:raises AssertionError: raises an exception if the split percentages / amount of traffic received
		by nodes is not correct.
	"""

	# generate a random setup
	nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites = generate_random_setup

	# run a test, using a random setup and without saving the data
	data_dict = run_experiment(mode, nr_ASes, nr_allies, attack_volume, ally_scrubbing_capabilites, False, False)
	### for each node, note the amount of attack traffic it is supposed to receive
	### this is our "goal"
	expected_attack_traffic = [0 for _ in range(nr_ASes)]
	expected_attack_traffic[data_dict["victim"]] = attack_volume - sum(ally_scrubbing_capabilites)
	for ally, ally_capabilities in zip(data_dict["allies"], ally_scrubbing_capabilites):
		expected_attack_traffic[ally] = ally_capabilities

	### calculate how much each node actually received
	G = data_dict["G_modified_colored"]
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

			# now start transfering the traffic from the current node to its neighbors
			incoming_vol = received_attack_traffic[current_node]
			outgoing_vol = 0
			
			# check that "incoming traffic vol = outgoing traffic vol" by testing that the outgoing
			# split percentages sum up to one
			# this only holds if the current node is not an ally or the victim
			assert (current_node in data_dict["allies"] + [data_dict["victim"]]) or round(sum([x[2] for x in outward_edges_w_perc])) == 1
			
			# 
			for u, v, percentage in outward_edges_w_perc:
				received_attack_traffic[v] += incoming_vol * percentage
				outgoing_vol += incoming_vol * percentage
				# also add the neighbors to the stack, if they have any outward going 
				# flow
				if percentage > 0 and any([G[u][v]["split_perc"] != 0 for u, v in G.out_edges(v)]):
					S.append(v)

			# the current nodes received attack traffic is the old one, minus the ones that flew out
			received_attack_traffic[current_node] -= outgoing_vol

	assert all([expected == round(received) for (expected, received) in zip(expected_attack_traffic, received_attack_traffic)])