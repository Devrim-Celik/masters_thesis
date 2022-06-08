"""
Contains the Internet class..

Author:
	Devrim Celik 08.06.2022
"""

import random
import string
import copy
import matplotlib.pyplot as plt
import networkx as nx
from pyvis.network import Network

from .autonomous_system import AutonomousSystem
from .sourceAS import SourceAS
from .victimAS import VictimAS
from .allyAS import AllyAS
from .router_table import RoutingTable


class Internet(object):
	"""
	This class will represent a network of autonomous systems, i.e., the Internet.

	It will initialize all necessary ASes, handle the communications between them,
	and collect and plot simulation data points.

	:param env: the simpy environment the simulation is running in
	:param init_graph: the initial graph, dictacting the topology of this
		Internet instance
	:param nr_ASes: the numbe of included autononmous systems
	:param propagation_delay: the time it takes for a message to be
		transmitted (we ignore transmissions delay, etc...)
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


	def __init__(self, env, graph, victim_indx, source_indx, ally_indc,
				 attack_freq, prop_delay, network_logger, create_logger_func,
				 log_subpath, figure_subpath):

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

		self.plot_values = {
			"victim_scrubbing_capabilitiy": None,
			"victim_help_calls": [],
			"victim_help_retractment_calls": []
		}

		# save a plot of the initial graph
		Internet.save_graph(graph, f"{self.figure_subpath}/init_graph.html")

		# translate the networkx nodes to AutonomousSystem classes
		for node_indx in graph.nodes:

			# determine which nodes point towards this node, and which ones
			# itself point to
			incoming = [u for u, v in graph.in_edges(node_indx)]
			outgoing = [v for u, v in graph.out_edges(node_indx)]
			neighbors = incoming + outgoing

			# create all the necessary routing table entries
			init_routing_table = [{
				"identifier": Internet.generate_random_identifier(),
				"next_hop": out_node,
				"destination": victim_indx,
				"priority": 1,
				"split_percentage": 0,
				"scrubbing_capabilities": 0,
				"as_path": [],
				"origin": "original",
				"recvd_from": node_indx,
				"time_added": 0
			} for out_node in outgoing]

			# select one best path by increasing the priority to 2
			if len(init_routing_table) > 0:
				selected_route = random.randint(
					0, len(init_routing_table) - 1
				)
				init_routing_table[selected_route]["priority"] = 2

			# determine the role of this node, and initiaize it accordinly
			role = graph.nodes[node_indx]["role"]

			# for distributing additional information
			additional_attr = {}

			if role in ["source", "victim", "ally"]:
				for entry_indx in range(len(init_routing_table)):
					init_routing_table[entry_indx]["as_path"] = graph.nodes[node_indx]["as_path_to_victim"]
				additional_attr["as_path_to_victim"] = graph.nodes[node_indx]["as_path_to_victim"]

			# depending on the role, further attributes are supplied
			if role == "source":
				additional_attr["full_attack_vol"] = graph.nodes[node_indx]["full_attack_vol"]
				additional_attr["attack_freq"] = attack_freq
			elif role == "victim":
				additional_attr["scrubbing_capability"] = graph.nodes[node_indx]["scrubbing_cap"]
				self.plot_values["victim_scrubbing_capabilitiy"] = graph.nodes[node_indx]["scrubbing_cap"]
			elif role == "ally":
				additional_attr["scrubbing_capability"] = graph.nodes[node_indx]["scrubbing_cap"]

			# create an individual logger for this AS
			as_logger = create_logger_func(
				f"AS{node_indx}-LOGGER",
				f"{log_subpath}/log_node_{node_indx}.txt"
			)

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


	def relay_std_packet(self, pkt, next_hops_w_perc):
		"""
		This function is responsible to relay packets of type standard ("STD")
		between autonomous systems.

		:param pkt: the to be transmitted packet
		:param next_hops_w_perc: contains tuples, where each tuple consists of
			one of the next hops, and the percentage of traffic going to this
			hop, i.e., a multipath implementation.

		:type pkt: dict
		:type next_hops_w_perc: list[tuples[int, float]]
		"""

		# increase hop counter
		pkt["content"]["hc"] += 1

		# wait for the propagation delay NOTE random delay because
		# of concurrency issues
		yield self.env.timeout(
			self.propagation_delay + random.uniform(-0.01, 0.01)
		)
		self.logger.debug(f"[{self.env.now}] Sending attack message to {[t[0] for t in next_hops_w_perc]} with percentages {[t[1] for t in next_hops_w_perc]} from {pkt['last_hop']}.")

		# split the attack traffic, according to proportions of the
		# given routing table
		for next_hop, percentage in next_hops_w_perc:
			if percentage > 0:
				# NOTE needed because of concurrence issues
				tmp_pkt = copy.deepcopy(pkt)
				modified_content = {k: v for k, v in pkt["content"].items()}
				modified_content["attack_volume"] = pkt["content"]["attack_volume"] * percentage
				tmp_pkt["content"] = modified_content
				tmp_pkt["next_hop"] = next_hop
				self.ASes[next_hop].process_pkt(tmp_pkt)


	def relay_rat(self, pkt, next_hops):
		"""
		This function is responsible to relay packets of type route
		advertisement ("RAT") between autonomous systems.

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
		This method will aggregated the collected data points to create
		figures about the recorded attack traffic at the victim and the
		allies over time.

		Generated figures as saved in the supplied path for figures during
		initialization of the Internet instance.
		"""

		plt.figure("DDoS Traffic Recordings", figsize=(16, 10))
		plt.title("DDoS Traffic Recordings")
		plt.grid()
		plt.ylim(0, 2000)

		# plot attack traffic
		plt.plot(
			*list(zip(*self.source.attack_traffic_recording)),
			label=f"Sent by {str(self.source)}",
			color="black",
			lw=1.5,
			ls="dotted"
		)

		# plot all sinks (victim + allies)
		for sink in self.allies + [self.victim]:
			plt.scatter(
				*list(zip(*sink.received_attacks)),
				s=1,
				label=f"Received by {str(sink)}",
				marker="X"
			)

		plt.hlines(
			y=self.plot_values["victim_scrubbing_capabilitiy"],
			xmin=0,
			xmax=self.victim.received_attacks[-1][0],
			color="black",
			label="victim_scrubbing_capability"
		)

		for tp, val in self.plot_values["victim_help_calls"]:
			plt.annotate(
				f"[AS{self.victim.asn}]\nHelp Signal Issued",
				(tp, val + 15),
				xytext=(
					tp,
					max(val, self.plot_values["victim_scrubbing_capabilitiy"]) + 450
				),
				horizontalalignment="center",
				arrowprops=dict(arrowstyle='-|>', lw=2)
			)
		for tp, val in self.plot_values["victim_help_retractment_calls"]:
			plt.annotate(
				f"[AS{self.victim.asn}]\nHelp Signal Retracted",
				(tp, val + 15),
				xytext=(
					tp,
					max(val, self.plot_values["victim_scrubbing_capabilitiy"]) + 300
				),
				horizontalalignment="center",
				arrowprops=dict(arrowstyle='-|>', lw=2)
			)

		plt.legend(loc="upper right")
		plt.tight_layout()
		plt.savefig(f"{self.figure_subpath}/recorded_attack_traffic.png", dpi=400)
		plt.savefig(f"{self.figure_subpath}/recorded_attack_traffic.svg", dpi=400)


	def generate_networkx_graph(self, changed_edge_color="purple"):
		"""
		This method will use the initial networkx graph, and the ASes that run
		through a simulation, to generate the changed network topology as a
		networkx and save it as a PyVis html figure in the supplied figure
		path.

		:param changed_edge_color: the color assigned to indicated changed
			edges

		:type changed_edge_color: str
		"""

		# initialize a directed graph
		graph = nx.DiGraph()

		# add the nodes
		graph.add_nodes_from(range(self.nr_ASes))

		# add the edges, node by node
		for node_indx in range(self.nr_ASes):
			graph.nodes[node_indx]["role"] = "standard"
			graph.nodes[node_indx]["color"] = "lightgrey"
			next_hops_w_perc = self.ASes[node_indx].router_table.determine_next_hops(
				self.victim.asn
			)
			for next_hop, percentage in next_hops_w_perc:
				if percentage > 0:
					graph.add_edge(node_indx, next_hop)
					graph[node_indx][next_hop]["split_percentage"] = percentage
					graph[node_indx][next_hop]["title"] = percentage


		# denote the special nodes
		graph.nodes[self.source.asn]["role"] = "source"
		graph.nodes[self.source.asn]["color"] = "red"
		graph.nodes[self.victim.asn]["role"] = "victim"
		graph.nodes[self.victim.asn]["color"] = "green"
		for ally_AS in self.allies:
			graph.nodes[ally_AS.asn]["role"] = "ally"
			graph.nodes[ally_AS.asn]["color"] = "blue"


		# denote changed and removed edges:
		for u, v in self.init_graph.edges:
			# is in
			if (u, v) in graph.edges:
				pass
			# was changed
			elif (v, u) in graph.edges:
				graph[v][u]["color"] = changed_edge_color
			# not in there anymore
			else:
				pass

		# NOTE this is just hacky for now, to avoid the bidirectional arrows
		# induced by the router tables of allies and victim
		# only makes sense if the status of the graph at this point is that
		# it is defending, i.e., allies supporting
		tmp = []
		for u, v in graph.edges:
			if (v, u) in list(graph.edges) and not (v, u) in tmp:
				tmp.append((u, v))
		for u, v in tmp:
			if graph.nodes[u]["role"] != "standard":
				graph.remove_edge(u, v)
				graph[v][u]["color"] = changed_edge_color
			else:
				graph.remove_edge(v, u)
				graph[u][v]["color"] = changed_edge_color

		# save figure
		Internet.save_graph(graph, f"{self.figure_subpath}/generated_graph.html")


	@staticmethod
	def save_graph(graph, path):
		net = Network(
			notebook=True,
			directed=True,
			height="1000px",
			width="100%"
		)
		net.inherit_edge_colors(False)
		net.from_nx(graph)
		net.save_graph(path)


	@staticmethod
	def generate_random_identifier(length=4):
		"""
		Generates a random string, used as an identifier.

		:param length: number of characters in the random string

		:type length: int
		"""
		return ''.join(random.choices(
			string.ascii_letters + string.digits, k=length
		))
