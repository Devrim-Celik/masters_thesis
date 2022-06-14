"""
The main script for running a simulation.

Author:
	Devrim Celik 08.06.2022
"""

import random
from pathlib import Path
from datetime import datetime
import argparse
import simpy
import numpy as np


from src.classes.network import Internet
from src.graph_generation import generate_directed_AS_graph
from src.auxiliary_functions import create_logger




def setup_env(simulation_logger):
	"""
	Initializes the simpy.Environment.

	:param simulation_logger: the logger responsible for environment events

	:type simulation_logger: logging.RootLogger

	:returns: the simpy environment
	:rytpe: simpy.Environment
	"""

	env = simpy.Environment()
	simulation_logger.info("[*] Simulation is setup.")

	return env


def run_simulation(env, net, simulation_length, simulation_logger):
	"""
	Function to actually run the environment. Will start all processes involved,
	and the run the simulation.

	:param env: the logger responsible for environment events
	:param net: the network
	:param simulation_length: maximum step number of the simulation
	:param simulation_logger: the logger responsible for environment events

	:type env: simpy.Environment
	:type net: Internet
	:type simulation_length: int
	:type simulation_logger: logging.RootLogger
	"""

	# start the attacking cycles of the source node
	env.process(net.source.attack_cycle())

	# run the simulation
	simulation_logger.info("[*] Simulation is started.")
	env.run(until=simulation_length)
	simulation_logger.info("[*] Simulation has ended.")


def main():
	"""
	The main function that is responsible for initializing, running and
	finally plottingthe results of the simulation.
	"""

	# current date and time, used to name this simulation
	time_date_str = datetime.now().strftime("%d:%m:%Y_%H:%M:%S")

	# argument parser
	parser = argparse.ArgumentParser()
	parser.add_argument("--seed", type=int, default=random.randint(0, 2**32 - 1), help="random seed; in [0, 2**32-1]")
	parser.add_argument("--nr_ASes", type=int, default=200, help="number of ASes in simulations")
	parser.add_argument("--nr_allies", type=int, default=2, help="number of allies")
	parser.add_argument("--simulation_length", type=int, default=650, help="number of steps the simulation runs")
	parser.add_argument("--propagation_delay", type=float, default=3, help="number of steps in the simulation it takes for a packet to be transmitted")
	parser.add_argument("--full_attack_volume", type=float, default=1000, help="the attack volume Mbps")
	parser.add_argument("--attack_frequency", type=float, default=1, help="number of steps in the simulation between attack packets sent")
	parser.add_argument("--log_path", type=str, default="./logs", help="path to save logs")
	parser.add_argument("--figure_path", type=str, default="./figures", help="path to save figures")
	args = parser.parse_args()

	# set the seed
	args.seed = 1 # TODO remove
	args.simulation_length = 300
	random.seed(args.seed)
	np.random.seed(args.seed)

	# use this time date string, and the random seed, to name the
	# simulation folder name
	simulation_folder_name = f"simulation_{time_date_str}_{args.seed}"

	# directories for logs and figures
	log_path = f"{args.log_path}/{simulation_folder_name}"
	figure_path = f"{args.figure_path}/{simulation_folder_name}"
	Path(log_path).mkdir(parents=True, exist_ok=True)
	Path(figure_path).mkdir(parents=True, exist_ok=True)
	print(f"[*] Logs will be saved in: {log_path}/")
	print(f"[*] Figures will be saved in: {figure_path}/")


	# create separate loggers
	network_logger = create_logger("[NETWORK]", f"{log_path}/network_logs.txt")
	simulation_logger = create_logger("[SIM]", f"{log_path}/simulation_logs.txt")

	# setup the simpy environment
	env = setup_env(simulation_logger)

	# create an initial AS graph
	graph, victim, adversary, allies = generate_directed_AS_graph(
		args.nr_ASes,
		args.nr_allies,
		args.full_attack_volume
	)

	# initialize the Internet network
	net = Internet(env, graph, victim, adversary, allies,
				   args.attack_frequency, args.propagation_delay,
				   network_logger, create_logger, log_path,
				   figure_path)

	# run the simulation
	run_simulation(env, net, args.simulation_length, simulation_logger)

	# create plots about this simulation
	net.plot()

	# also create a plot of the current topology
	net.generate_networkx_graph()


if __name__ == "__main__":
	main()
