import simpy
import logging
from pathlib import Path
from datetime import datetime
import networkx as nx

from src.classes.network import Internet
from src.graph_generation import generate_directed_AS_graph


time_date_str = datetime.now().strftime("%d:%m:%Y_%H:%M:%S")
"""
LOG_DIRECTORY = "./logs"
FIGURE_DIRECTORY = f"./figures/simulation_{time_date_str}"

Path(LOG_DIRECTORY).mkdir(parents=True, exist_ok=True)
Path(FIGURE_DIRECTORY).mkdir(parents=True, exist_ok=True)


logging.basicConfig(filename=f"./logs/log_{time_date_str}.txt",
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)

print(f"[*] Logs will be saved in: ./logs/log_{time_date_str}.txt")
print(f"[*] Figures will be saved in: {FIGURE_DIRECTORY}/")
"""

# TODO have a log file for each node, and one for important stuff

logging.basicConfig(filename=f"./log_{time_date_str}.txt",
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.INFO)
FIGURE_DIRECTORY = "./"

def setup_env():
    # create and simpy environment instance
    env = simpy.Environment()
    logging.info("[*] Simulation is setup.")
    return env

def run_simulation(
	env,
	net,
	max_sim_length:int = 300):
	env.process(net.source.attack_cycle())
	logging.info("[*] Simulation is started.")
	env.run(until = max_sim_length)
	logging.info("[*] Simulation has ended.")

def main(graph_pickle="./example_graph.pkl", nr_ASes = 100, nr_allies = 1):
	env = setup_env()
	graph, victim, adversary, allies = generate_directed_AS_graph(nr_ASes, nr_allies, FIGURE_DIRECTORY)
	net = Internet(env, graph, victim, adversary, allies)
	run_simulation(env, net)

if __name__=="__main__":
	main()
