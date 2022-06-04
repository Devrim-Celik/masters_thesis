
import logging
import random
import string
import matplotlib.pyplot as plt
import seaborn as sns
import copy

from .nodes import AutonomousSystem, SourceAS, VictimAS, AllyAS
from .router_table import RoutingTable

# unusued prioty = 1
# used = 2
# ally = 3

class Internet(object):

	__special_AS_classes__ = {
		"standard": AutonomousSystem,
		"source": SourceAS,
		"victim": VictimAS,
		"ally": AllyAS
	}

	def __init__(
		self,
		env,
		graph,
		victim_indx, 
		source_indx,
		ally_indc,
		main_logger,
		network_logger,
		create_logger_func,
		logger_subpath,
		prop_delay = 3,
		attack_vol = 100,
		attack_freq = 1
		):

		# set attributes
		self.env = env
		self.propagation_delay = prop_delay
		self.nr_ASes = len(graph.nodes)
		self.ASes = []
		self.allies = []
		self.logger = network_logger
		# TODO add these as properties to the networkx graph nodes
		VICTIM_SCRUB = 50
		ALLY_SCRUB = 10	


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

			if role in ["source", "victim", "ally"]:
				for entry_indx in range(len(init_routing_table)): # todo this is still a problem, if we have multiple next hops with different as paths
					init_routing_table[entry_indx]["as_path"] = graph.nodes[node_indx]["as_path_to_victim"]
				additional_attr["as_path_to_victim"] = graph.nodes[node_indx]["as_path_to_victim"]



			if role == "source":
				additional_attr["attack_vol"] = attack_vol
				additional_attr["attack_freq"] = attack_freq
			elif role == "victim":
				additional_attr["scrubbing_capability"] = VICTIM_SCRUB
				print(init_routing_table)
			elif role == "ally":
				additional_attr["scrubbing_capability"] = ALLY_SCRUB + random.randint(-5, 15)

			# create a logger for the AS
			as_logger = create_logger_func(f"AS{node_indx}-LOGGER", f"{logger_subpath}/log_node_{node_indx}.txt")

			self.ASes.append(self.__special_AS_classes__[role](env, self, main_logger, as_logger, node_indx, RoutingTable(self.env, init_routing_table, node_indx, as_logger), neighbors, additional_attr))

		self.source = self.ASes[source_indx]
		self.victim = self.ASes[victim_indx]
		self.allies = [self.ASes[ally_indx] for ally_indx in ally_indc]



	@staticmethod
	def generate_random_identifier(length=4):
		return ''.join(random.choices(string.ascii_letters + string.digits, k = length))

	def relay_std_packet(
		self,
		pkt,
		next_hops_w_perc: list
		):

		# increase hop counter
		pkt["content"]["hc"] += 1
		# wait for the propagation delay
		yield self.env.timeout(self.propagation_delay + random.uniform(-0.01, 0.01))

		# TODO change thsi bck to debug
		self.logger.info(f"[{self.env.now}] Sending attack message to {[t[0] for t in next_hops_w_perc]} with percentages {[t[1] for t in next_hops_w_perc]} from {pkt['last_hop']}.")


		attack_vol = pkt["content"]["attack_volume"] # NOTE: need this bc concurrency issues

		# split the attack traffic, according to proportions of the given routing table
		for next_hop, percentage in next_hops_w_perc:
			tmp_pkt = copy.deepcopy(pkt)
			modified_content = {k:v for k, v in pkt["content"].items()}
			modified_content["attack_volume"] = attack_vol * percentage
			tmp_pkt["content"] = modified_content
			tmp_pkt["next_hop"] = next_hop
			self.ASes[next_hop].process_pkt(tmp_pkt)

	def relay_rat(
		self,
		pkt,
		next_hops
		):

		# increase hop counter
		pkt["content"]["hc"] += 1
		# wait for the propagation delay
		yield self.env.timeout(self.propagation_delay + random.uniform(-0.01, 0.01))
		self.logger.debug(f"[{self.env.now}] RAT {pkt['identifier']}  delayed to {next_hops} from {pkt['last_hop']}.")
		for next_hop in next_hops:
			pkt["next_hop"] = next_hop
			self.ASes[next_hop].process_pkt(pkt)


	def plot_arrived_attacks(self):
		plt.figure("ATTACK")
		for ally in self.allies:
			#plt.title(title = f"ally-{ally.asn}")
			#print(ally.received_attacks)
			#data = Internet.transform()
			c = "#"+''.join([random.choice('0123456789ABCDEF') for j in range(6)])
			plt.scatter(*list(zip(*ally.received_attacks)), label = f"Ally:{ally.asn} [{ally.scrubbing_cap}]", s= 1, color = c)
			#plt.plot(*list(zip(*ally.received_attacks)), label = f"Ally:{ally.asn} [{ally.scrubbing_cap}]", color = c)
		#plt.figure(str(self.victim.asn))
		#plt.title(title = f"victim")
		#print(self.victim.received_attacks)

		c = "#"+''.join([random.choice('0123456789ABCDEF') for j in range(6)])
		plt.scatter(*list(zip(*self.victim.received_attacks)), label = "Victim:" + str(self.victim.asn), s = 1,color = c)
		#plt.plot(*list(zip(*self.victim.received_attacks)), label = "Victim:" + str(self.victim.asn), color  = c)
		plt.legend()
		plt.show()
		
	@staticmethod
	def transform(received_attacks):
		data = []
		available_ts = {t[0]: indx for indx, t in enumerate(received_attacks)}
		for ts in range(received_attacks[-1][0]):
			if ts in available_ts.keys():
				data.append((ts, received_attacks[available_ts[ts]][1]))
			else:
				data.append([ts, 0])
		return data