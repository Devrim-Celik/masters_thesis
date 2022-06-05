import simpy
import logging
import random
from pathlib import Path
from datetime import datetime
import networkx as nx

from src.classes.network import Internet
from src.graph_generation import generate_directed_AS_graph
from src.aux import create_logger

SEED = random.randint(0, 1000000000000)
random.seed(SEED)

def setup_env(simulation_logger):
    # create and simpy environment instance
    env = simpy.Environment()
    simulation_logger.info("[*] Simulation is setup.")
    return env

def run_simulation(
	env,
	net,
	max_sim_length,
	simulation_logger):

	# start the attacking cycles of the source node
	env.process(net.source.attack_cycle())

	# run the simulation
	simulation_logger.info("[*] Simulation is started.")
	env.run(until = max_sim_length)
	simulation_logger.info("[*] Simulation has ended.")




def main(nr_ASes = 300, nr_allies = 4, max_sim_length = 100, propagation_delay = 3, attack_freq = 1):
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
	#net.generate_networkx_graph() # TODO uncomment

if __name__=="__main__":
	main()
