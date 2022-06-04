import logging
import random

from .nodes import AS, Victim, Source, Ally

class Internet(object):


	def __init__(
		self,
		env,
		graph,
		victim, 
		source, 
		allies,
		attack_volume = 100,
		attack_freq = 30,
		):

		self.env = env
		self.nr_ASes = len(graph.nodes)
		self.propagation_delay = 3
		self.ASes = []
		self.allies = []

		# todo somehow get scurbbing capabilities, generating during grpah generaiton
		VICTIM_SCRUB = 50
		ALLY_SCRUB = 10	

		for node_indx in graph.nodes:

			in_nodes = [u for u,v in graph.in_edges(node_indx)]
			out_nodes = [v for u,v in graph.out_edges(node_indx)]

			neighbors = in_nodes + out_nodes

			if len(out_nodes) > 0:
				next_hops = [[node, 0, "unused_original", None] for node in out_nodes]
				selected_next_hop = random.choice(range(len(out_nodes)))
				next_hops[selected_next_hop][1] = 1
				next_hops[selected_next_hop][2] = "original"
			else:
				next_hops = None

			if graph.nodes[node_indx]["role"] == "victim":
				As = Victim(env, self, node_indx, "victim", neighbors, next_hops, VICTIM_SCRUB)
				self.victim = As

			elif graph.nodes[node_indx]["role"] == "source":
				As = Source(env, self, node_indx, "source", neighbors, next_hops, graph.nodes[node_indx]["as_path_to_victim"], attack_volume, attack_freq)
				self.source = As

			elif graph.nodes[node_indx]["role"] == "ally":
				As = Ally(env, self, node_indx, "ally", neighbors, next_hops, graph.nodes[node_indx]["as_path_to_victim"], ALLY_SCRUB)
				self.allies.append(As)

			else:
				As = AS(env, self, node_indx, "standard", neighbors, next_hops, graph.nodes[node_indx]["as_path_to_victim"])

			self.ASes.append(As)

	def relay_packet(
		self,
		identifier,
		pkt_type,
		src,
		dst,
		last_hop,
		next_hop,
		content
		):

		logging.debug(f"[{self.env.now}] -->[{identifier} | {pkt_type}]<--\n \t [src: {src}, dst: {dst}, last_hop: {last_hop}, next_hop: {next_hop}]\n \t Content: {content}")
		content["hc"] += 1	
		yield self.env.timeout(self.propagation_delay)
		self.ASes[next_hop].process_packet(identifier, pkt_type, src, dst, last_hop, next_hop, content)