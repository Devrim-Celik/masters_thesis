from pathlib import Path
from datetime import datetime

from src.generate_AS_network import generate_directed_AS_graph, graph_pruning_via_BFS
from src.auxiliary_functions import save_pyvis_network, save_as_pickle, color_graph
from src.split_merge import build_cost_and_split_matrices, ally_assignment_problem, apply_changes, set_splits

EXPERIMENT_FOLDER = "./experiments"
CURRENT_TIMEDATE_STR = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")


def generate_supported_graph(
	nr_ASes:int = 200,
	nr_allies:int = 3,
	attack_volume:int = 100,
	ally_scrubbing_capabilities:list = [20, 5, 18], 
	):

	# create a directory for this run
	experiment_folder = EXPERIMENT_FOLDER + "/" + CURRENT_TIMEDATE_STR
	Path(experiment_folder).mkdir(parents=True)

	#######################################################
	############## GRAPH GENERATION
	#######################################################
	# generate a directed graph represnting the AS network
	G_init, victim, adversary, allies = generate_directed_AS_graph(nr_ASes, nr_allies)
	save_pyvis_network(G_init, experiment_folder + "/00_initial_Graph.html")

	# prune some edges of it
	G_pruned = graph_pruning_via_BFS(G_init, victim)
	save_pyvis_network(G_pruned, experiment_folder + "/01_pruned_Graph.html")
		
	
	#######################################################
	############## SPLITTING TRAFFIC CALCULATIONS
	#######################################################
	# calculate the costs for merging attack flow with the different allies
	cost_matrix, split_node_matrix, changes_list, used_edges_list = build_cost_and_split_matrices(G_pruned, victim, adversary, allies)

	# solve the assignment problem
	final_changes, used_splits = ally_assignment_problem(cost_matrix, split_node_matrix, changes_list, nr_allies)

	# apply the changes
	G_modified = apply_changes(G_pruned, final_changes, used_edges_list, used_splits)
	save_pyvis_network(G_modified, experiment_folder + "/02_modified_Graph.html")

	# determine the split values and write them into the node/edge attributes
	G_with_splits = set_splits(G_modified, victim, adversary, allies, used_edges_list, attack_volume, ally_scrubbing_capabilities)
	save_pyvis_network(G_with_splits, experiment_folder + "/03_modified_Graph_with_splits.html")

	# color the graph
	G_with_splits_colored = color_graph(G_with_splits, adversary, victim, allies)
	save_pyvis_network(G_with_splits_colored, experiment_folder + "/04_modified_Graph_with_splits_colored.html")



	# create a dictionary to save all the information
	save_dict = {
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
		"G_with_splits_colored": G_with_splits_colored,
		"cost_matrix": cost_matrix,
		"changes_list": changes_list,
		"used_edges_list": used_edges_list,
		"final_changes": final_changes
	}

	save_as_pickle(save_dict, experiment_folder + "/experiment_data.pkl")
	
	return save_dict


if __name__=="__main__":
	generate_supported_graph()