"""
This file is used compare the cost between all available algorithms, for different amount of allies.

Author:
    Devrim Celik - 07.05.2022
"""


from pathlib import Path
from datetime import datetime
import pandas as pd
from tqdm import tqdm
import argparse

from src.generate_AS_network import generate_directed_AS_graph, graph_pruning_via_BFS
from src.auxiliary_functions import comparison_plot, cost_function
from src.central_controller_functions import central_controller_complete, central_controller_greedy
from src.decentralized_functions import decentralized

ALGORITHMS = {
	"central_controller_complete":central_controller_complete,
	"central_controller_greedy":central_controller_greedy,
	"decentralized":decentralized
#	"bgp":None
}


def run_comparison(
	nr_ASes:int = 400,
	nr_allies_list:int = list(range(1,8)),
	nr_executions:int = 4,
	step_cost:int = 1,
	router_entry_change_cost:int = 3,
	experiment_path:str = "./experiments",
	verbose:bool = True
	):
	"""
	This function will generate AS network topologies, with variyng amounts of available allies,
	and run all available algorithms and note the costs to compare them in a graph.

	:param nr_ASes: the number of ASes int he graph
	:param nr_allies: the number of allies
	:param nr_executions: number of executions per setting; used to obtain cost variance
	:param step_cost: for the cost function 
	:param router_entry_change_cost: for the cost function
	:param experiment_path: where to save data and figure
	:param verbose: verbose option

	:type mode: str
	:type nr_ASes: int
	:type nr_executions: int
	:type step_cost: int
	:type router_entry_change_cost: int
	:type experiment_path: str 
	:type verbose: bool


	:return: the recorded costs
	:rtype: pd.DataFrame
	"""

	# set some arbitrary attack_volume
	attack_volume = 10000000

	# get the timedate and a seed
	current_timedate_str = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")

	# for saving the results of the comparison
	comparison_results = []

	# one ally number setting for each iteration
	for nr_allies in tqdm(nr_allies_list):

		# multiple executions allows to assess the error variance
		for execution_indx in range(nr_executions):

			# generate a directed graph represnting the AS network
			G_init, victim, adversary, allies = generate_directed_AS_graph(nr_ASes, nr_allies)

			# prune some edges of it
			G_pruned = graph_pruning_via_BFS(G_init, victim)

			# generate some placeholder scrubbing capabilities
			ally_scrubbing_capabilities = [5 for _ in range(nr_allies)]

			# one type of algorithm each iteration
			for mode in ALGORITHMS.keys():
				G_modified = ALGORITHMS[mode](G_pruned, victim, adversary, allies, ally_scrubbing_capabilities, attack_volume)
				cost = cost_function(G_pruned, G_modified, victim, adversary, allies, step_cost, router_entry_change_cost)

				# save the cost from the cost function
				comparison_results.append({
					"nr_allies":nr_allies,
					"mode":mode,
					"execution_indx":execution_indx,
					"cost":cost
					})
	

	# transform the dictionary to a pandas dataframe
	comparison_results_df = pd.DataFrame(comparison_results)

	# create a directory for this run
	experiment_folder = f"{experiment_path}/{current_timedate_str}_comparison"
	Path(experiment_folder).mkdir(parents=True)

	# save the data 
	comparison_results_df.to_pickle(f"{experiment_folder}/comparison_results_df.pkl")

	if verbose:
		print(f"[+] Saved to \"{experiment_folder}/comparison_results_df.pkl\".")

	# generate and save a plot
	comparison_plot(
		comparison_results_df,
		f"{experiment_folder}/comparison_plot.png",
		nr_ASes,
		nr_executions
		)

	return comparison_results_df

if __name__=="__main__":

	# argument parsing
	parser = argparse.ArgumentParser()
	parser.add_argument("--nr_ASes", type = int, default = 500, help = "number of ASes in simulations")
	parser.add_argument("--max_allies", type = int, default = 7, help = "max number of allies to iterate to")
	parser.add_argument("--nr_executions", type = int, default = 3, help = "number of executions per simulation")
	parser.add_argument("--verbose_enabled", action='store_true', help = "enabling verbose")
	args = parser.parse_args()

	run_comparison(
		nr_ASes = args.nr_ASes,
		nr_allies_list = list(range(1, args.max_allies + 1)),
		nr_executions = args.nr_executions,
		verbose = args.verbose_enabled
		)