"""


"""

# TODO source is also on attack path
# TODO maybe packet to dict
# TODO pkt_type to type
import simpy
import logging
import numpy as np
import random
import copy

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

	def __init__(self, env, network, main_logger, logger, asn, router_table, ebgp_AS_peers, additional_attr):

		# TODO checks
		
		# set attributes
		self.env = env
		self.network = network
		self.main_logger = main_logger
		self.logger = logger
		self.asn = asn
		self.router_table = router_table
		self.ebgp_AS_peers = ebgp_AS_peers
		self.seen_rats = []
		self.advertised = [self.asn]
		self.received_attacks = []
		self.on_attack_path = False
		self.attack_path_last_hop = None
		self.new_line = "\n"
		self.tab = "\t"

	def send_packet(self, pkt, next_hops):
		"""
		This method is reponsible for sending a packet. It calls corresponding functions, depending
		on the type of the received packet. Either a normal packet with attack load ("STD") or a route 
		advertisement ("RAT").
		"""
		if next_hops == []:
			return

		self.logger.debug(f"""[{self.env.now}] Sending Packet with Next Hops {next_hops}:
			=====================================================================
			Identifier: 	{pkt['identifier']}
			Type: 			{pkt['pkt_type']}
			Source: 		{pkt['src']}
			Destination:	{pkt['dst']}
			Content:		{"".join([f'{self.new_line}{self.tab*4}{key} = {value}' for key, value in pkt['content'].items()])}
			=====================================================================
		""")

		if pkt["pkt_type"] == "STD":
			self.env.process(self.network.relay_std_packet(pkt, next_hops))
		elif pkt["pkt_type"] == "RAT":
			self.env.process(self.network.relay_rat(pkt, next_hops))

	def process_pkt(self, pkt): # TODO do we need all these arguments? like last hop and next hop might be redundant

		self.logger.debug(f"""[{self.env.now}] Received Packet from {pkt['last_hop']}:
			=====================================================================
			Identifier: 	{pkt['identifier']}
			Type: 			{pkt['pkt_type']}
			Source: 		{pkt['src']}
			Destination:	{pkt['dst']}
			Content:		{"".join([f'{self.new_line}{self.tab*4}{key} = {value}' for key, value in pkt['content'].items()])}
			=====================================================================
		""")

		if pkt["pkt_type"] == "STD":
			self.process_std_pkt(pkt)

		elif pkt["pkt_type"] == "RAT":
			# send as necessary
			pkt_tmp = copy.deepcopy(pkt) # can we Delete this TODO? --> pretty sure not
			pkt_tmp["last_hop"] = self.asn
			if pkt["content"]["relay_type"] == "next_hop": # TODO when do we use this??? check this pls
				next_hops = self.router_table.determine_next_hops(dst)
			elif pkt["content"]["relay_type"] == "original_next_hop":
				next_hops = self.router_table.determine_highest_original()
			elif pkt["content"]["relay_type"] == "broadcast":
				next_hops = list(set(self.ebgp_AS_peers) - {pkt["last_hop"]})
			self.send_packet(pkt_tmp, next_hops) 

			# react to it if it didnt see it yet
			if not pkt["identifier"] in self.seen_rats:
				self.seen_rats.append(pkt["identifier"])

				if pkt["content"]["protocol"] == "help":
					self.rat_reaction_help(pkt)
				elif pkt["content"]["protocol"] == "support":
					self.rat_reaction_support(pkt)
				elif pkt["content"]["protocol"] == "attack_path":
					self.rat_reaction_attack_path(pkt)



	def process_std_pkt(self, pkt):

		# if the destination of this packet is an address this AS advertise, this node is getting attacked
		if pkt["dst"] in self.advertised:
			self.attack_reaction(pkt)
		# else, relay it
		else:
			pkt["last_hop"] = self.asn
			self.send_packet(pkt, self.router_table.determine_next_hops(pkt["dst"]))

	def attack_reaction(self, pkt):
		self.logger.info(f"[{self.env.now}] Attack Packet with ID {pkt['identifier']} arrived with magnitutde {pkt['content']['attack_volume']} Gbps.")
		self.main_logger.info(f"[{self.env.now}][{self.asn}] Attack Packet with ID {pkt['identifier']} arrived with magnitutde {pkt['content']['attack_volume']} Gbps.")
				
		self.received_attacks.append((self.env.now, pkt["content"]["attack_volume"]))

	def rat_reaction_help(self, pkt):
		self.router_table.update_attack_volume(pkt["content"]["attack_volume"])

	# TODO include allies capapbilities not responsible for
	def rat_reaction_support(self, pkt): 
		self.logger.info(f"Reacting to Support RAT")
		# we add a router, only if we dont know if we are on the attack path yet, or, if the router comes not from the attack path
		if (not self.on_attack_path) or (pkt["last_hop"] != self.attack_path_last_hop): # TODO put this in priority if else, 1 and 3
			# add the advertised route the routing table
			entry = {
				"identifier": "TODO", 
				"next_hop": pkt["content"]["as_path_to_victim"][pkt["content"]["hc"]-1],
				"destination": pkt["content"]["as_path_to_victim"][-1], # the router thiinks, the destination is the vicitm, although ally
				"priority": 3,
				"split_percentage": None,
				"scrubbing_capabilities": pkt["content"]["scrubbing_capability"],
				"as_path": pkt["content"]["as_path_to_victim"][pkt["content"]["hc"]:], # TODO -1 or not???, want to include this node as start
				"origin": f"ally_{pkt['src']}",
				"recvd_from": pkt["last_hop"],
				"time_added": self.env.now
			}
			self.router_table.add_entry(entry) # TODO need to trigger some change?
			self.main_logger.info(f"[{self.env.now}][{self.asn}] Added entry from RAT {pkt['identifier']}.")

	def rat_reaction_attack_path(self, pkt):
		self.logger.info(f"Reacting to Attack Path RAT")
		# increase the priority of the original next hop to be on par with the ally routes
		self.on_attack_path = True
		self.attack_path_last_hop = pkt["last_hop"]
		self.router_table.increase_original_priority()
		self.router_table.reduce_allies_based_on_last_hop(pkt["last_hop"])


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

		self.logger.info(f"[{self.env.now}] Starting attack on {self.as_path_to_victim[-1]} of magnitude {self.attack_volume} and frequency {self.attack_freq}.")
		self.main_logger.info(f"[{self.env.now}][{self.asn}] Starting attack on {self.as_path_to_victim[-1]} of magnitude {self.attack_volume} and frequency {self.attack_freq}.")
		
		atk_indx = 0
		while True:
			yield self.env.timeout(self.attack_freq)
			pkt = {
				"identifier": f"Attack_Packet_{self.asn}_{atk_indx}",
				"pkt_type": "STD",
				"src": self.asn,
				"dst": self.as_path_to_victim[-1],
				"last_hop": self.asn,
				"content": {"attack_volume" : self.attack_volume + random.randint(-10, 10), "relay_type": "next_hop", "hc": 0}
			}
			self.send_packet(pkt, self.router_table.determine_next_hops(self.as_path_to_victim[-1]))
			atk_indx += 1


	def rat_reaction_help(self, pkt):
		self.router_table.update_attack_volume(pkt["content"]["attack_volume"])

		if (pkt["content"]["attacker_asn"] == self.asn) and (not self.atk_path_signal):
			# attack path signal
			self.atk_path_signal = True
			self.on_attack_path = True
			self.logger.info(f"[{self.env.now}] Help registered. Determining Attack Path.")
			self.main_logger.info(f"[{self.env.now}][{self.asn}] Help registered. Determining Attack Path.")
			pkt = {
				"identifier": f"atk_path_signal_form_{self.asn}",
				"pkt_type": "RAT",
				"src": self.asn,
				"dst": None,
				"last_hop": self.asn,
				"content": {"relay_type": "original_next_hop", "protocol": "attack_path", "as_path_to_victim": self.as_path_to_victim, "handled_AS": [], "hc": 0}
			}
			self.send_packet(pkt, self.router_table.determine_highest_original())
			self.seen_rats.append(pkt["identifier"])

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

	def attack_reaction(self, pkt):
		
		self.logger.info(f"[{self.env.now}] Attack Packet with ID {pkt['identifier']} arrived with magnitutde {pkt['content']['attack_volume']} Gbps.")
		self.main_logger.info(f"[{self.env.now}][{self.asn}] Attack Packet with ID {pkt['identifier']} arrived with magnitutde {pkt['content']['attack_volume']} Gbps.")
		self.received_attacks.append((self.env.now, pkt["content"]["attack_volume"]))

		if not self.help_signal_issued:
			self.logger.info(f"[{self.env.now}] Attack registered. Calling for help.")
			self.main_logger.info(f"[{self.env.now}][{self.asn}] Attack registered. Calling for help.")
			self.help_signal_issued = True
			pkt = {
				"identifier": "help",
				"pkt_type": "RAT",
				"src": self.asn,
				"dst": None,
				"last_hop": self.asn,
				"content": {"attack_volume": pkt["content"]["attack_volume"], "attacker_asn": pkt["src"], "relay_type": "broadcast", "protocol": "help", "hc": 0}
			}
			self.send_packet(pkt, self.ebgp_AS_peers)

	def rat_reaction_support(self, pkt):
		pass # ally doesnt change and doesnt add rules to router entry: --> TODO add it (for completeness) but dont follow? might be hard

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



	def rat_reaction_help(self, pkt):
		self.router_table.update_attack_volume(pkt["content"]["attack_volume"])
		self.logger.info(f"[{self.env.now}] Help registered. Sending Support.")
		self.main_logger.info(f"[{self.env.now}][{self.asn}] Help registered. Sending Support.")
		self.advertised.append(self.as_path_to_victim[-1])
		pkt = {
			"identifier": f"support_from_{self.asn}",
			"pkt_type": "RAT",
			"src": self.asn,
			"dst": None,
			"last_hop": self.asn,
			"content": {"relay_type": "original_next_hop", "scrubbing_capability": self.scrubbing_cap, "protocol": "support", "ally": self.asn, "as_path_to_victim": self.as_path_to_victim, "hc": 0}
		}
		self.send_packet(pkt, self.router_table.determine_highest_original())
