"""
The main script for running a simulation.

Author:
	Devrim Celik 08.06.2022
"""

import simpy
import random
import numpy as np
from pathlib import Path
from datetime import datetime

from src.classes.network import Internet
from src.graph_generation import generate_directed_AS_graph
from src.aux import create_logger

SEED = random.randint(0, 2**32 - 1)

random.seed(SEED)
np.random.seed(SEED)



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



def run_simulation(env, net, max_sim_length, simulation_logger):
	"""
	Function to actually run the environment. Will start all processes involved,
	and the run the simulation.

	:param env: the logger responsible for environment events
	:param net: the network
	:param max_sim_length: maximum step number of the simulation
	:param simulation_logger: the logger responsible for environment events

	:type env: simpy.Environment
	:type net: Internet
	:type max_sim_length: int
	:type simulation_logger: logging.RootLogger
	"""

	# start the attacking cycles of the source node
	env.process(net.source.attack_cycle())

	# run the simulation
	simulation_logger.info("[*] Simulation is started.")
	env.run(until = max_sim_length)
	simulation_logger.info("[*] Simulation has ended.")



def main(nr_ASes = 200, nr_allies = 2, max_sim_length = 650, propagation_delay = 3, attack_freq = 1): # TODO cant change freq? causes bug??
	"""
	The main function that is responsible for initializing, running and finally plotting
	the results of the simulation.

	:param nr_ASes: the total number of autonomous sytems generated in the simulation
	:param nr_allies: the number of allies to the victim
	:param max_sim_length: the maximum step number for a simulation
	:param propagation_delay: the number of steps in the simulation it takes for a packet to be transmitted
	:param attack_freq: the nubmer of steps between attack packets

	:type nr_ASes: int
	:type nr_allies: int
	:type max_sim_length: int
	:type propagation_delay: float
	:type attack_freq: float
	"""

	# current date and time, used to name this simulation
	time_date_str = datetime.now().strftime("%d:%m:%Y_%H:%M:%S")

	# use this time date string, and the random seed, to name the simulation folder name
	simulation_folder_name = f"simulation_{time_date_str}_{SEED}"

	# directories for logs and figures
	log_path = f"./logs/{simulation_folder_name}"
	figure_path = f"./figures/{simulation_folder_name}"
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
	graph, victim, adversary, allies = generate_directed_AS_graph(nr_ASes, nr_allies, figure_path)	

	# initialize the Internet network
	net = Internet(env, graph, victim, adversary, allies, attack_freq, propagation_delay, network_logger, create_logger, log_path, figure_path)
	
	# run the simulation
	run_simulation(env, net, max_sim_length, simulation_logger)

	# create plots about this simulation
	net.plot()

	# also create a plot of the current topology
	net.generate_networkx_graph()



if __name__=="__main__":
	
	main()
