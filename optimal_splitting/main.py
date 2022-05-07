"""
This file is used to execute the functions and algorithms defined in `/src`. Explicitly, 
it will generate a random AS graph and try to diverge an DDoS adversaries traffic towards
some victim over multiple allies such that graph in question is modified as little as possible. 

Author:
    Devrim Celik - 01.05.2022
"""


import random
from pathlib import Path
from datetime import datetime

from src.generate_AS_network import generate_directed_AS_graph, graph_pruning_via_BFS
from src.auxiliary_functions import save_pyvis_network, save_as_pickle, color_graph, set_splits
from src.central_controller_functions import central_controller_complete, central_controller_greedy



def run_experiment(
	mode:str,
	nr_ASes:int = 200,
	nr_allies:int = 3,
	attack_volume:int = 100,
	ally_scrubbing_capabilities:list = [20, 5, 18],
	save_data:bool = True,
	save_html:bool = True, 
	experiment_path:str = "./experiments_central",
	seed:int = None
	):
	"""
	This function generates a random graph with a victim, and adversary and multipler allies for the
	victim, representing an autonomous system network. It then tries to modify the graph as little
	as possible, in order to divert some of the attack traffic to all the allies.
	The way in which the problem is solved can be selected.

	:param mode: defines the way in which the problem is solved; options are
		* `central_controller_complete`
		* `central_controller_greedy`
		* `decentral
		* `bgp`
	:param nr_ASes: the number of ASes int he graph
	:param nr_allies: the number of allies
	:param attack_volume: the attack volume of the DDoS adversary
	:param ally_scrubbing_capabilities: a list of scrubbing capabilities
	:param save_data: whether to save the generated data 
	:param save_html: whether to save html figures of the generated graphs
	:param experiment_path: where to save data and figures
	:param seed: a random seed

	:param mode: str
	:param nr_ASes: int
	:param nr_allies: int
	:param attack_volume: int 
	:param ally_scrubbing_capabilities: list
	:param save_data: str
	:param save_html: str
	:param experiment_path: str
	:param seed: int


	:return: all the data generated in this function
	:type path_to_pickle: dict
	"""

	if not mode in ["central_controller_complete", "central_controller_greedy"]:
		raise ValueError(f"You entered mode {mode}; this mode is not available.")

	if not attack_volume > sum(ally_scrubbing_capabilities):
		raise ValueError(f"The attack volume must be greater than the sum of the ally capabilities.")


	# get the timedate and a seed
	current_timedate_str = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
	if not seed:
		seed = random.randint(0, 10000000000000)
	random.seed(seed)


	#######################################################
	############## GRAPH GENERATION
	#######################################################
	# generate a directed graph represnting the AS network
	G_init, victim, adversary, allies = generate_directed_AS_graph(nr_ASes, nr_allies)

	# prune some edges of it
	G_pruned = graph_pruning_via_BFS(G_init, victim)

	
	#######################################################
	############## SPLITTING TRAFFIC CALCULATIONS
	#######################################################
	if mode == "central_controller_complete":
		G_modified, cost = central_controller_complete(G_pruned, victim, adversary, allies)
	elif mode == "central_controller_greedy":
		G_modified, cost = central_controller_greedy(G_pruned, victim, adversary, allies)
	elif mode == "decentral":
		pass
	elif mode == "bgp":
		pass

	# determine the split values and write them into the node/edge attributes
	G_with_splits = set_splits(G_modified, victim, adversary, allies, attack_volume, ally_scrubbing_capabilities, seed)

	# color the graph
	G_with_splits_colored = color_graph(G_with_splits, adversary, victim, allies)


	#######################################################
	############## SAVING RESULTS
	#######################################################
	# create a dictionary to save all the information
	data_dict = {
		"random_seed":seed,
		"mode":mode,
		"cost":cost,
		"experiment_timedate":current_timedate_str,
		"nr_ASes": nr_ASes,
		"nr_allies": nr_allies,
		"attack_volume": attack_volume,
		"ally_scrubbing_capabilities": ally_scrubbing_capabilities,
		"victim": victim,
		"adversary": adversary,
		"allies": allies,
		"G_init": G_init,
		"G_pruned": G_pruned, 
		"G_modified": G_modified,
		"G_with_splits": G_with_splits,
		"G_with_splits_colored": G_with_splits_colored
	}

	if save_data or save_html:
		# create a directory for this run
		experiment_folder = experiment_path + "/" + current_timedate_str + "_" + str(seed)
		print(seed)
		Path(experiment_folder).mkdir(parents=True)

	if save_data:
		save_as_pickle(data_dict, experiment_folder + "/experiment_data.pkl")
	
	if save_html:
		save_pyvis_network(G_init, experiment_folder + "/01_initial_Graph.html")
		save_pyvis_network(G_pruned, experiment_folder + "/02_pruned_Graph.html")
		save_pyvis_network(G_modified, experiment_folder + "/03_modified_Graph.html")
		save_pyvis_network(G_with_splits, experiment_folder + "/04_modified_Graph_with_splits.html")
		save_pyvis_network(G_with_splits_colored, experiment_folder + "/05_modified_Graph_with_splits_colored.html")

	return data_dict

if __name__=="__main__":
	run_experiment("central_controller_greedy")