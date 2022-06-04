"""


"""

# TODO source is also on attack path
# TODO maybe packet to dict

import simpy
import logging
import numpy as np

class AutonomousSystem(object):
	"""
	This class is the representing a standard autonomous system in our simulations.

	:param env: the simpy environment this AS will be running in
	:param network: the network this AS is integrated in
	:param asn: a value representing its autonomous systen number, basically an identifer
	:param router_table: an object, which will be used to simulate a routing table
	:param ebgp_AS_peers: a list of all the ASes it is connected through EBGP sessions
	:param seen_rats: a list of all seen route advertisements, in order to recognize novel ones
	:param advertised: the list of ASNs (in real life it would IP blocks) this AS is advertising routes for
						and ready to receive packets for
	:param received_attacks: to collected data on received attacks
	:param on_attack_path: to denote, whether this AS lies on an attack path
	:param attack_path_last_hop: if it is on attack path, this value will denote the ASN of the predecessor


	:type env: simpy.Environment
	:type network: network.Internet
	:type asn: int
	:type router_table: router_table.RouterTable
	:type ebgp_AS_peers: list[int]
	:type seen_rats: list[str]
	:type advertised: list[int]
	:type received_attacks: list[tuple]
	:type on_attack_path: bool
	:type attack_path_last_hop: int
	"""

	def __init__(self, env, network, asn, router_table, ebgp_AS_peers, additional_attr):

		# TODO checks
		
		# set attributes
		self.env = env
		self.network = network
		self.asn = asn
		self.router_table = router_table
		self.ebgp_AS_peers = ebgp_AS_peers
		self.seen_rats = []
		self.advertised = [self.asn]
		self.received_attacks = []
		self.on_attack_path = False
		self.attack_path_last_hop = None

	def send_packet(self, identifier, pkt_type, src, dst, last_hop, next_hops, content):
		"""
		This method is reponsible for sending a packet. It calls corresponding functions, depending
		on the type of the received packet. Either a normal packet with attack load ("STD") or a route 
		advertisement ("RAT").
		"""
		if pkt_type == "STD":
			self.env.process(self.network.relay_std_packet(identifier, pkt_type, src, dst, last_hop, next_hops, content))
		elif pkt_type == "RAT":
			self.env.process(self.network.relay_rat(identifier, pkt_type, src, dst, last_hop, next_hops, content))

	def process_pkt(
		self,
		identifier,
		pkt_type,
		src,
		dst,
		last_hop,
		next_hop,
		content
		): # TODO do we need all these arguments? like last hop and next hop might be redundant
		if pkt_type == "STD":
			self.process_std_pkt(identifier, pkt_type, src, dst, last_hop, next_hop, content)

		elif pkt_type == "RAT":
			# send as necessary
			if content["relay_type"] == "next_hop": # TODO when do we use this??? check this pls
				self.send_packet(identifier, pkt_type, src, dst, self.asn, self.router_table.determine_next_hops(dst), content)
			elif content["relay_type"] == "original_next_hop":
				self.send_packet(identifier, pkt_type, src, dst, self.asn, self.router_table.determine_highest_original(), content)
			elif content["relay_type"] == "broadcast":
				self.send_packet(identifier, pkt_type, src, dst, self.asn, list(set(self.ebgp_AS_peers) - {last_hop}), content)

			# react to it if it didnt see it yet
			if not identifier in self.seen_rats:
				self.seen_rats.append(identifier)

				if content["protocol"] == "help":
					self.rat_reaction_help(identifier, pkt_type, src, dst, last_hop, next_hop, content)
				elif content["protocol"] == "support":
					self.rat_reaction_support(identifier, pkt_type, src, dst, last_hop, next_hop, content)
				elif content["protocol"] == "attack_path":
					self.rat_reaction_attack_path(identifier, pkt_type, src, dst, last_hop, next_hop, content)



	def process_std_pkt(
		self,
		identifier,
		pkt_type,
		src,
		dst,
		last_hop,
		next_hop,
		content
		):

		# if the destination of this packet is an address this AS advertise, this node is getting attacked
		if dst in self.advertised:
			self.attack_reaction(identifier, pkt_type, src, dst, last_hop, next_hop, content)
		# else, relay it
		else:
			self.send_packet(identifier, pkt_type, src, dst, self.asn, self.router_table.determine_next_hops(dst), content)

	def attack_reaction(
		self,
		identifier,
		pkt_type,
		src,
		dst,
		last_hop,
		next_hop,
		content
		):

		logging.info(f"[{self.env.now}][{self.asn}] Attack Packet with ID {identifier} arrived with magnitutde {content['attack_volume']} Gbps.") # pkt.content['attack_volume']
		self.received_attacks.append((self.env.now, content['attack_volume']))

	def rat_reaction_help(self, identifier, pkt_type, src, dst, last_hop, next_hop, content):
		self.router_table.update_attack_volume(content["attack_volume"])

	# TODO include allies capapbilities not responsible for
	def rat_reaction_support(self, identifier, pkt_type, src, dst, last_hop, next_hop, content): 

		# we add a router, only if we dont know if we are on the attack path yet, or, if the router comes not from the attack path
		if (not self.on_attack_path) or (last_hop != self.attack_path_last_hop):
			# add the advertised route the routing table
			entry = {
				"identifier": "TODO", 
				"next_hop": content["as_path_to_victim"][content["hc"]-2],
				"destination": dst,
				"priority": 3,
				"split_percentage": None,
				"scrubbing_capabilities": content["scrubbing_capability"],
				"as_path": content["as_path_to_victim"][:content["hc"]][::-1], # TODO -1 or not???, want to include this node as start
				"origin": f"ally_{src}",
				"recvd_from": last_hop,
				"time_added": self.env.now
			}
			self.router_table.add_entry(entry) # TODO need to trigger some change?
			logging.info(f"[{self.env.now}][{self.asn}] Added entry from RAT {identifier}.")

	def rat_reaction_attack_path(self, identifier, pkt_type, src, dst, last_hop, next_hop, content):
		# increase the priority of the original next hop to be on par with the ally routes
		logging.info(f"[{self.env.now}][{self.asn}] Attack Path {identifier} arrived. Increasing original priority.") # pkt.content['attack_volume']
		self.on_attack_path = True
		self.attack_path_last_hop = last_hop
		self.router_table.increase_original_priority()
		self.router_table.reduce_allies_based_on_last_hop(last_hop)


class SourceAS(AutonomousSystem):
	# TODO can only handle if *args is used, not **kwargs (or we can make it vice verca) --> general soluation
	def __init__(self, *args, **kwargs):
		super().__init__(*args)

		# used to determine size and frequency of attack packets
		self.attack_volume = args[-1]["attack_vol"]
		self.attack_freq = args[-1]["attack_freq"]

		# TODO
		self.as_path_to_victim = args[-1]["as_path_to_victim"]


		# used to recognize, whether an attack path signal has already been issued
		self.atk_path_signal = False	


	def attack_cycle(self):

		logging.info(f"[{self.env.now}][{self.asn}] Starting attack on {self.as_path_to_victim[-1]} of magnitude {self.attack_volume} and frequency {self.attack_freq}.")
		
		atk_indx = 0
		while True:
			yield self.env.timeout(self.attack_freq)
			self.send_packet(f"Attack_Packet_{self.asn}_{atk_indx}", "STD", self.asn, self.as_path_to_victim[-1], self.asn, self.router_table.determine_next_hops(self.as_path_to_victim[-1]), {"attack_volume" : self.attack_volume, "relay_type": "next_hop", "hc": 0})
			atk_indx += 1


	def rat_reaction_help(self, identifier, pkt_type, src, dst, last_hop, next_hop, content):
		self.router_table.update_attack_volume(content["attack_volume"])

		if (content["attacker_asn"] == self.asn) and (not self.atk_path_signal):
			# attack path signal
			self.atk_path_signal = True
			self.on_attack_path = True
			logging.info(f"[{self.env.now}][{self.asn}] Help registered. Determining Attack Path.")
			self.send_packet(f"atk_path_signal_form_{self.asn}", "RAT", self.asn, None, self.asn, self.router_table.determine_highest_original(), {"relay_type": "original_next_hop", "protocol": "attack_path", "as_path_to_victim": self.as_path_to_victim, "handled_AS": [], "hc": 0})
			self.seen_rats.append(f"atk_path_signal_form_{self.asn}")

			# own reaction: 
			self.router_table.increase_original_priority()

class VictimAS(AutonomousSystem):
	# TODO can only handle if *args is used, not **kwargs (or we can make it vice verca) --> general soluation
	def __init__(self, *args, **kwargs):
		super().__init__(*args)

		# remember scrubbing capabilitiy
		self.scrubbing_cap = args[-1]["scrubbing_capability"]

		# TODO
		self.as_path_to_victim = args[-1]["as_path_to_victim"]

		# used to recognize, whether a help signal has already been issued
		self.help_signal_issued = False	

	def attack_reaction(
		self,
		identifier,
		pkt_type,
		src,
		dst,
		last_hop,
		next_hop,
		content
		):
	
		logging.info(f"[{self.env.now}][{self.asn}] Attack Packet with ID {identifier} arrived with magnitutde {content['attack_volume']} Gbps.") # pkt.content['attack_volume']
		self.received_attacks.append((self.env.now, content['attack_volume']))

		if not self.help_signal_issued:
			logging.info(f"[{self.env.now}][{self.asn}] Attack registered. Calling for help.")
			self.help_signal_issued = True
			self.send_packet(
				"help",
				"RAT",
				self.asn,
				None,
				self.asn,
				self.ebgp_AS_peers,
				{"attack_volume": content["attack_volume"], "attacker_asn": src, "relay_type": "broadcast", "protocol": "help", "hc": 0}
			)

class AllyAS(AutonomousSystem):
	# TODO can only handle if *args is used, not **kwargs (or we can make it vice verca) --> general soluation
	def __init__(self, *args, **kwargs):
		super().__init__(*args)

		# remember scrubbing capabilitiy
		self.scrubbing_cap = args[-1]["scrubbing_capability"]
		
		# TODO
		self.as_path_to_victim = args[-1]["as_path_to_victim"]
		
		# used to recognize, whether a help signal has already been issued
		self.help_signal_issued = False	



	def rat_reaction_help(self, identifier, pkt_type, src, dst, last_hop, next_hop, content):
		self.router_table.update_attack_volume(content["attack_volume"])
		logging.info(f"[{self.env.now}][{self.asn}] Help registered. Sending Support.")
		self.advertised.append(self.as_path_to_victim[-1])
		self.send_packet(f"support_from_{self.asn}", "RAT", self.asn, None, self.asn, self.router_table.determine_highest_original(), {"relay_type": "original_next_hop", "scrubbing_capability": self.scrubbing_cap, "protocol": "support", "ally": self.asn, "as_path_to_victim": self.as_path_to_victim, "hc": 0})
		#TODO do we need this? if yes, how to implement
		#self.next_hops = [[n, 0, origin, amount] for n, p, origin, amount in self.next_hops]