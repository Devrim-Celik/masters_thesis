
from pathlib import Path
from datetime import datetime
import pandas as pd
from tqdm import tqdm

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
	nr_ASes:int = 500,
	nr_allies_list:int = list(range(1,11)),
	nr_executions:int = 5,
	experiment_path:str = "./experiments",
	step_cost:int = 1,
	entry_change_cost:int = 3,
	):
	"""
	This function generates a random graph with a victim, and adversary and multipler allies for the
	victim, representing an autonomous system network. It then tries to modify the graph as little
	as possible, in order to divert some of the attack traffic to all the allies.
	The way in which the problem is solved can be selected.

	:param mode: defines the way in which the problem is solved; options are
		* `central_controller_complete`
		* `central_controller_greedy`
		* `decentralized`
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
				cost = cost_function(G_pruned, G_modified, victim, adversary, allies, step_cost, entry_change_cost)

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
	run_comparison()