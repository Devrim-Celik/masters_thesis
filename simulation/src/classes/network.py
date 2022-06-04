
import logging
import random
import string

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
		prop_delay = 3,
		attack_vol = 100,
		attack_freq = 30
		):

		# set attributes
		self.env = env
		self.propagation_delay = prop_delay
		self.nr_ASes = len(graph.nodes)
		self.ASes = []
		self.allies = []

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
				"as_path": None,
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
			elif role == "ally":
				additional_attr["scrubbing_capability"] = ALLY_SCRUB

			self.ASes.append(self.__special_AS_classes__[role](env, self, node_indx, RoutingTable(init_routing_table), neighbors, additional_attr))
			self.ASes[-1].router_table.set_AS(self.ASes[-1])

		self.source = self.ASes[source_indx]
		self.victim = self.ASes[victim_indx]
		self.allies = [self.ASes[ally_indx] for ally_indx in ally_indc]



	@staticmethod
	def generate_random_identifier(length=16):
		return ''.join(random.choices(string.ascii_letters + string.digits, k = length))

	def relay_std_packet(
		self,
		identifier,
		pkt_type,
		src,
		dst,
		last_hop,
		next_hops_w_perc: list,
		content
		):

		# increase hop counter
		content["hc"] += 1
		# wait for the propagation delay
		yield self.env.timeout(self.propagation_delay)

		# TODO change thsi bck to debug
		logging.info(f"[{self.env.now}] Sending attack message to {[t[0] for t in next_hops_w_perc]} with percentages {[t[1] for t in next_hops_w_perc]}.")

		# split the attack traffic, according to proportions of the given routing table
		for next_hop, percentage in next_hops_w_perc:
			modified_content = {k:v for k, v in content.items()}
			modified_content["attack_volume"] *= percentage
			self.ASes[next_hop].process_pkt(identifier, pkt_type, src, dst, last_hop, next_hop, modified_content)

	def relay_rat(
		self,
		identifier,
		pkt_type,
		src,
		dst,
		last_hop,
		next_hops: list,
		content
		):

		# increase hop counter
		content["hc"] += 1
		# wait for the propagation delay
		yield self.env.timeout(self.propagation_delay)

		logging.debug(f"[{self.env.now}] RAT {identifier} relayed to {next_hops} from {last_hop}.")
		for next_hop in next_hops:
			self.ASes[next_hop].process_pkt(identifier, pkt_type, src, dst, last_hop, next_hop, content)