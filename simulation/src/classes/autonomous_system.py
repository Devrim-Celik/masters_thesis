"""
Contains the AutonomousSystem class.

Author:
	Devrim Celik 08.06.2022
"""


import copy


class AutonomousSystem(object):
	"""
	This class is the representing a standard autonomous system in our
	simulations.

	:param env: the simpy environment this AS will be running in
	:param network: the network this AS is integrated in
	:param asn: a value representing its autonomous systen number, basically
		an identifer
	:param router_table: an object, which will be used to simulate
		a routing table
	:param ebgp_AS_peers: a list of all the ASes it is connected
		through EBGP sessions
	:param seen_rats: a list of all seen route advertisements, in order to
		recognize novel ones
	:param advertised: the list of ASNs (in real life it would IP blocks) this
		 AS is advertising routes for and ready to receive packets for
	:param received_attacks: to collected data on received attacks
	:param on_attack_path: to denote, whether this AS lies on an attack path
	:param attack_path_predecessor: if it is on attack path, this value will
		denote the ASN of the predecessor
	:param helping_node: collects all nodes that this list is helping

	:type env: simpy.Environment
	:type network: network.Internet
	:type asn: int
	:type router_table: router_table.RouterTable
	:type ebgp_AS_peers: list[int]
	:type seen_rats: list[str]
	:type advertised: list[int]
	:type received_attacks: list[tuple]
	:type on_attack_path: bool
	:type attack_path_predecessor: int
	:type helping_node: list
	"""


	def __init__(self, env, network, logger, asn, router_table, ebgp_AS_peers,
				 additional_attr):
		# set attributes
		self.env = env
		self.network = network
		self.logger = logger
		self.asn = asn
		self.router_table = router_table
		self.ebgp_AS_peers = ebgp_AS_peers
		self.seen_rats = []
		self.advertised = [self.asn]
		self.received_attacks = []
		self.on_attack_path = False
		self.attack_path_predecessors = []
		self.helping_node = []
		# for printing
		self.new_line = "\n"
		self.tab = "\t"
		

	def send_packet(self, pkt, next_hops):
		"""
		This method is reponsible for sending a packet. It calls corresponding
		functions, depending on the type of the received packet. Either a
		normal packet with attack load ("STD") or a route
		advertisement ("RAT").

		:param pkt: the, to be sent, packet
		:param next_hops: a list of destinations this packet is going to be
			transmitted to (RAT)/a list of destination with probabilites this
			 packet is going to be distributed to (STD)

		:type pkt: dict
		:type next_hops: list[int] for RAT packets
			/ list[tuple[int, float]] for standard packets
		"""
		if next_hops == []:
			return

		self.logger.debug(f"""[{self.env.now}] Sending Packet with Next Hops {next_hops}:
			=====================================================================
			Identifier: 	{pkt['identifier']}
			Type: 			{pkt['type']}
			Source: 		{pkt['src']}
			Destination:	{pkt['dst']}
			Content:		{"".join([f'{self.new_line}{self.tab*4}{key} = {value}' for key, value in pkt['content'].items()])}
			=====================================================================
		""")

		# call the corresponding send function
		if pkt["type"] == "STD":
			# check that all targets are connected to this AS
			if set([t[0] for t in next_hops]).issubset(set(self.ebgp_AS_peers)):
				self.env.process(self.network.relay_std_packet(pkt, next_hops))
			else:
				raise Exception("Trying to send to an AS, that is not a peer!")
		elif pkt["type"] == "RAT":
			# check that all targets are connected to this AS
			if set(next_hops).issubset(set(self.ebgp_AS_peers)):
				self.env.process(self.network.relay_rat(pkt, next_hops))
			else:
				raise Exception("Trying to send to an AS, that is not a peer!")


	def process_pkt(self, pkt): 
		"""
		This method is responsible for handling incoming packets. Generally, we
		can differentiate between the following types of packets:
			* STD: a standard packet, carrying some load
			* RAT: a route advertisement, which can contain one of the following
				   protocol calls
				* help: issued from an attacked victim
				* support: issued from an ally of the attacked victim
				* as_path: issued from the AS where the attack traffic
					originates from

		Since the reaction to different protocol calls is quite different
		between different types of autonomous systems, this method calls
		specific "reaction" methods, depending on the type of RAT.

		:param pkt: the incoming packets

		:type pkt: dict
		"""
		self.logger.debug(f"""[{self.env.now}] Received Packet from {pkt['last_hop']}:
			=====================================================================
			Identifier: 	{pkt['identifier']}
			Type: 			{pkt['type']}
			Source: 		{pkt['src']}
			Destination:	{pkt['dst']}
			Content:		{"".join([f'{self.new_line}{self.tab*4}{key} = {value}' for key, value in pkt['content'].items()])}
			=====================================================================
		""")

		# for standard packets
		if pkt["type"] == "STD":
			self.process_std_pkt(pkt)
		# for RAT packets
		elif pkt["type"] == "RAT":

			# distributed as specified by the protocol
			pkt_tmp = copy.deepcopy(pkt)
			pkt_tmp["last_hop"] = self.asn

			if pkt["content"]["relay_type"] == "original_next_hop":
				next_hops = self.router_table.determine_highest_original()
				self.send_packet(pkt_tmp, next_hops) 
			elif pkt["content"]["relay_type"] == "broadcast":
				next_hops = list(set(self.ebgp_AS_peers) - {pkt["last_hop"]})
				self.send_packet(pkt_tmp, next_hops) 
			elif pkt["content"]["relay_type"] == "no_relay":
				pass

			# react to it, if this packet has not already been seen
			if not pkt["identifier"] in self.seen_rats:
				self.seen_rats.append(pkt["identifier"])
				# call the corresponding reaction
				if pkt["content"]["protocol"] == "help":
					self.rat_reaction_help(pkt)
				elif pkt["content"]["protocol"] == "help_retractment":
					self.rat_reaction_help_retractment(pkt)
				elif pkt["content"]["protocol"] == "support":
					self.rat_reaction_support(pkt)


	def process_std_pkt(self, pkt):
		"""
		This method is responsible for processing an incoming, standard
		packet. The basic idea is, that if we are the destination of the
		packet, we will receive it, and otherwise it will be relayed to the
		next hop.

		:param pkt: the incoming packets

		:type pkt: dict
		"""

		# if the destination of this packet is an address this AS advertise,
		# this node is getting attacked
		if pkt["dst"] in self.advertised:
			self.attack_reaction(pkt)
		# else, relay it
		else:
			pkt["last_hop"] = self.asn
			self.send_packet(
				pkt, 
				self.router_table.determine_next_hops(pkt["dst"])
			)


	def attack_reaction(self, pkt):
		"""
		This method implements the response to receiving an attack packet.

		:param pkt: the incoming packets

		:type pkt: dict
		"""
		self.logger.info(f"[{self.env.now}] Attack Packet with ID {pkt['identifier']} arrived with magnitutde {pkt['content']['attack_volume']} Gbps.")
		self.received_attacks.append(
			(self.env.now, pkt["content"]["attack_volume"])
		)


	def rat_reaction_help_retractment(self, pkt):
		"""
		This method implements the response to receiving a RAT packet, with
		the help retractment protocol. Variables will be reset and routing
		table will be resetted to the original status.

		:param pkt: the incoming packets

		:type pkt: dict
		"""
		self.logger.info(f"Reacting to Help Retractment RAT")
		self.router_table.reset()
		self.helping_node = []

		# reset any attribute that might have been set
		if hasattr(self, "on_attack_path"):
			self.on_attack_path = False
		if hasattr(self, "attack_path_predecessor"):
			self.attack_path_predecessors = None
		if hasattr(self, "atk_path_signal"):
			self.atk_path_signal = False
		if hasattr(self, "attack_volume_approx"):
			self.attack_volume_approx = None
		if hasattr(self, "ally_help"):
			self.ally_help = {}
		if hasattr(self, "supporting_allies"):
			self.supporting_allies = []


	def rat_reaction_help(self, pkt):
		"""
		This method implements the response to receiving a RAT packet, with
		the help protocol. A default AS will simply broadcast it to its peers.

		:param pkt: the incoming packets

		:type pkt: dict
		"""
		self.logger.info(f"Reacting to Help RAT")
		self.helping_node.append(pkt["src"])
		self.router_table.update_victim_info(pkt["content"]["scrubbing_capability"], pkt["content"]["attack_volume"], pkt["content"]["ally_percentage"])

		attack_path_predecessors = self.network.get_atk_path_predecessors(self.asn)
		self.on_attack_path = bool(attack_path_predecessors)
		self.attack_path_predecessors = attack_path_predecessors

		if self.on_attack_path and pkt["content"]["initial_call"]:
			# increase the priority of the original next hop entry
			self.router_table.increase_original_priority()
			# decrease the priority of all ally paths that come from the attack path
			for asn in self.attack_path_predecessors:
				self.router_table.reduce_allies_based_on_asn(asn)

		else:
			pass # happens when we are not on attack path anymore


	def rat_reaction_support(self, pkt):
		"""
		This method implements the response to receiving a RAT packet, with
		the support protocol. This node might update its routing table, if
			a) it does not believe itself to be on the attack path, or
			b) if it is on the attack path, the last hop of the package does
				not come along the attack path.

		:param pkt: the incoming packets

		:type pkt: dict
		"""
		if pkt["content"]["as_path_to_victim"][-1] in self.helping_node:
			self.logger.info(f"Reacting to Support RAT")

			# add the advertised route the routing table
			entry = {
				"identifier": f"support_RAT_reaction_{int(self.env.now)}",
				"next_hop": pkt["content"]["as_path_to_victim"][pkt["content"]["hc"] - 1],
				"destination": pkt["content"]["as_path_to_victim"][-1],
				"priority": 3 if (not pkt["last_hop"] in self.attack_path_predecessors) else 1,
				"split_percentage": 0,
				"scrubbing_capabilities": pkt["content"]["scrubbing_capability"],
				"as_path": pkt["content"]["as_path_to_victim"][pkt["content"]["hc"]:],
				"origin": f"ally_{pkt['src']}",
				"recvd_from": pkt["last_hop"],
				"time_added": self.env.now
			}
			self.router_table.add_entry(entry)


	def __str__(self):
		return f"AS-{self.asn}"
