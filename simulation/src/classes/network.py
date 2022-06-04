
import random
import string
import copy
import matplotlib.pyplot as plt
import seaborn as sns

from .nodes import AutonomousSystem, SourceAS, VictimAS, AllyAS
from .router_table import RoutingTable

class Internet(object):

	"""
	This class will represent a network of autonomous systems, i.e., the Internet. 

	It will initialize all necessary ASes, handle the communications between them,
	and collect and plot simulation data points.

	:param env: the simpy environment the simulation is running in
	:param init_graph: the initial graph, dictacting the topology of this Internet instance
	:param nr_ASes: the numbe of included autononmous systems
	:param propagation_delay: the time it takes for a message to be transmitted (we 
		ignore transmissions delay, etc...)
	:param logger: used to log events related to this instance
	:param log_subpath: path to store logs
	:param figure_subpath: path to store figures
	:param ASes: a list of all initiated autonomous systems
	:param source: the source autonomous system
	:param victim: the victim autonomous system
	:param allies: the ally autonomous systems

	:type env: simpy.Environment
	:type init_graph: nx.classes.graph.Graph
	:type nr_ASes: int
	:type propagation_delay: float
	:type logger: logging.RootLogger
	:type log_subpath: str
	:type figure_subpath: str
	:type ASes: list[AutonomousSystem]
	:type source: AutonomousSystem
	:type victim: AutonomousSystem
	:type allies: AutonomousSystem
	"""

	__special_AS_classes__ = {
		"standard": AutonomousSystem,
		"source": SourceAS,
		"victim": VictimAS,
		"ally": AllyAS
	}

	def __init__(self, env, graph, victim_indx, source_indx, ally_indc, attack_freq, prop_delay, 
		network_logger, create_logger_func, log_subpath, figure_subpath ):

		# set attributes
		self.env = env
		self.init_graph = graph
		self.nr_ASes = len(graph.nodes)
		self.propagation_delay = prop_delay
		self.logger = network_logger
		self.log_subpath = log_subpath
		self.figure_subpath = figure_subpath

		self.ASes = []
		self.allies = []

		# translate the networkx nodes to AutonomousSystem classes
		for node_indx in graph.nodes:

			# determine which nodes point towards this node, and which ones itself point to
			incoming = [u for u,v in graph.in_edges(node_indx)]
			outgoing = [v for u,v in graph.out_edges(node_indx)]
			neighbors = incoming + outgoing

			# create all the necessary routing table entries
			init_routing_table = [{
				"identifier": Internet.generate_random_identifier(), 
				"next_hop": out_node,
				"destination": victim_indx,
				"priority": 1,
				"split_percentage": None,
				"scrubbing_capabilities": None,
				"as_path": [],
				"origin": "original",
				"recvd_from": node_indx, # we just assume it comes from itself
				"time_added": 0
			} for out_node in outgoing]

			# select one best path by increasing the priority to 2
			if len(init_routing_table) > 0:
				selected_route = random.randint(0, len(init_routing_table)-1)
				init_routing_table[selected_route]["priority"] = 2

			# determine the role of this node, and initiaize it accordinly
			role = graph.nodes[node_indx]["role"]

			# for distributing additional information
			additional_attr = {}

			# TODO for now, special roles get the AS_path, the other dont, but want to do this, but hard
			if role in ["source", "victim", "ally"]:
				for entry_indx in range(len(init_routing_table)):
					init_routing_table[entry_indx]["as_path"] = graph.nodes[node_indx]["as_path_to_victim"]
				additional_attr["as_path_to_victim"] = graph.nodes[node_indx]["as_path_to_victim"]

			# depending on the role, further attributes are supplied
			if role == "source":
				additional_attr["attack_vol_limits"] = graph.nodes[node_indx]["attack_vol_limits"]
				additional_attr["attack_freq"] = attack_freq
			elif role == "victim":
				additional_attr["scrubbing_capability"] = None # TODO do we need this?
			elif role == "ally":
				additional_attr["scrubbing_capability"] = graph.nodes[node_indx]["scrubbing_cap"]

			# create an individual logger for this AS
			as_logger = create_logger_func(f"AS{node_indx}-LOGGER", f"{log_subpath}/log_node_{node_indx}.txt")

			# initialize the AS
			self.ASes.append(self.__special_AS_classes__[role](
					env, 
					self, 
					as_logger, 
					node_indx, 
					RoutingTable(self.env, init_routing_table, node_indx, as_logger), 
					neighbors, 
					additional_attr
					))

		# specifically save the special ASes
		self.source = self.ASes[source_indx]
		self.victim = self.ASes[victim_indx]
		self.allies = [self.ASes[ally_indx] for ally_indx in ally_indc]



	@staticmethod
	def generate_random_identifier(length=4):
		"""
		Generates a random string, used as an identifier.

		:param length: number of characters in the random string

		:type length: int
		"""
		return ''.join(random.choices(string.ascii_letters + string.digits, k = length))



	def relay_std_packet(self, pkt, next_hops_w_perc):
		"""
		This function is responsible to relay packets of type standard ("STD") between autonomous systems.

		:param pkt: the to be transmitted packet
		:param next_hops_w_perc: contains tuples, where each tuple consists of one of the next hops, and the percentage of
			traffic going to this hop, i.e., a multipath implementation.

		:type pkt: dict
		:type next_hops_w_perc: list[tuples[int, float]]
		"""

		# increase hop counter
		pkt["content"]["hc"] += 1

		# wait for the propagation delay
		yield self.env.timeout(self.propagation_delay + random.uniform(-0.01, 0.01)) # NOTE: random delay due to concurrency issues
		self.logger.debug(f"[{self.env.now}] Sending attack message to {[t[0] for t in next_hops_w_perc]} with percentages {[t[1] for t in next_hops_w_perc]} from {pkt['last_hop']}.")

		attack_vol = pkt["content"]["attack_volume"] # NOTE: this is implemented a bit more tidious, due to concurrency issues this bc concurrency issues
													# TODO may be replaceable by introducing small delay in for loop. do same for method below
		# split the attack traffic, according to proportions of the given routing table
		for next_hop, percentage in next_hops_w_perc:
			tmp_pkt = copy.deepcopy(pkt)
			modified_content = {k:v for k, v in pkt["content"].items()}
			modified_content["attack_volume"] = attack_vol * percentage
			tmp_pkt["content"] = modified_content
			tmp_pkt["next_hop"] = next_hop
			self.ASes[next_hop].process_pkt(tmp_pkt)




	def relay_rat(self, pkt, next_hops):
		"""
		This function is responsible to relay packets of type route advertisement ("RAT") between autonomous systems.

		:param pkt: the to be transmitted packet
		:param next_hops_w_perc: the list of next hops to send the package to

		:type pkt: dict
		:type next_hops_w_perc: list[int]
		"""
		
		# increase hop counter
		pkt["content"]["hc"] += 1

		# wait for the propagation delay
		yield self.env.timeout(self.propagation_delay + random.uniform(-0.01, 0.01))
		self.logger.debug(f"[{self.env.now}] RAT {pkt['identifier']}  delayed to {next_hops} from {pkt['last_hop']}.")

		# send it to all specified next hops
		for next_hop in next_hops:
			tmp_pkt = copy.deepcopy(pkt)
			tmp_pkt["next_hop"] = next_hop
			self.ASes[next_hop].process_pkt(tmp_pkt)


	def plot(self):
		"""
		This method will aggregated the collected data points to create figures about the recorded attack
		traffic at the victim and the allies over time.

		Generated figures as saved in the supplied path for figures during initialization of the Internet
		instance.

		# TODOs:
			* mark important events with vertical lines, like
				* help call out
				* attack path call out [maybe]
				* support call from each ally [maybe]
				* retreat call
		"""
		
		plt.figure("Arrived DDoS Traffic", figsize=(16, 10))
		plt.title("Recorded Attack Traffic from all Sinks")
		plt.grid()
		plt.ylim(0, 2000)

		# plot attack traffic
		plt.scatter(*list(zip(*self.source.attack_traffic_recording)), s= 2, c = "black")
		plt.plot(*list(zip(*self.source.attack_traffic_recording)), label = str(self.source), c = "black", lw= 0.5)

		# plot all sinks (victim + allies)
		for sink in self.allies + [self.victim]:
			plt.scatter(*list(zip(*sink.received_attacks)), s= 1, c = "black")
			plt.plot(*list(zip(*sink.received_attacks)), label = str(sink), lw= 0.3)

		plt.legend(loc = "upper right")
		plt.tight_layout()
		plt.savefig(f"{self.figure_subpath}/recorded_attack_traffic.png", dpi = 400)
		plt.savefig(f"{self.figure_subpath}/recorded_attack_traffic.svg", dpi = 400)
		