"""


"""

# TODO source is also on attack path
# TODO maybe packet to dict
# TODO pkt_type to type

import random
import copy
import operator

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
	:param attack_path_predecessor: if it is on attack path, this value will denote the ASN of the predecessor


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
	"""

	def __init__(self, env, network, logger, asn, router_table, ebgp_AS_peers, additional_attr):

		# TODO checks
		
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
		self.attack_path_predecessor = None
		self.new_line = "\n"
		self.tab = "\t"
		# TODO include in docstinrg: a list nodes that are currently asking for help
		self.helping_node = []



	def send_packet(self, pkt, next_hops):
		"""
		This method is reponsible for sending a packet. It calls corresponding functions, depending
		on the type of the received packet. Either a normal packet with attack load ("STD") or a route 
		advertisement ("RAT").

		:param pkt: the, to be sent, packet
		:param next_hops: a list of destinations this packet is going to be transmitted to (RAT)/
							a list of destination with probabilites this packet is going to be distributed to (STD)

		:type pkt: dict
		:type next_hops: list/dict
		"""
		if next_hops == []: # TODO routing table
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

		# call the corresponding send function
		if pkt["pkt_type"] == "STD":
			# check that all targets are connected to this AS
			if set([t[0] for t in next_hops]).issubset(set(self.ebgp_AS_peers)):
				self.env.process(self.network.relay_std_packet(pkt, next_hops))
			else:
				raise Exception("Trying to send to an AS, that is not a peer!")
		elif pkt["pkt_type"] == "RAT":
			# check that all targets are connected to this AS
			
			if set(next_hops).issubset(set(self.ebgp_AS_peers)):
				self.env.process(self.network.relay_rat(pkt, next_hops))
			else:
				raise Exception("Trying to send to an AS, that is not a peer!")



	def process_pkt(self, pkt): 
		"""
		This method is responsible for handling incoming packets. Generally, we can 
		differentiate between the following types of packets:
			* STD: a standard packet, carrying some load 
			* RAT: a route advertisement, which can contain one of the following protocol calls
				* help: issued from an attacked victim
				* support: issued from an ally of the attacked victim
				* as_path: issued from the AS where the attack traffic originates from
		Since the reaction to different protocol calls is quite different between different types
		of autonomous systems, this method calls specific "reaction" methods, depending on the
		type of RAT.

		:param pkt: the incoming packets

		:type pkt: dict
		"""
		self.logger.debug(f"""[{self.env.now}] Received Packet from {pkt['last_hop']}:
			=====================================================================
			Identifier: 	{pkt['identifier']}
			Type: 			{pkt['pkt_type']}
			Source: 		{pkt['src']}
			Destination:	{pkt['dst']}
			Content:		{"".join([f'{self.new_line}{self.tab*4}{key} = {value}' for key, value in pkt['content'].items()])}
			=====================================================================
		""")

		# for standard packets
		if pkt["pkt_type"] == "STD":
			self.process_std_pkt(pkt)
		# for RAT packets
		elif pkt["pkt_type"] == "RAT":

			########## distributed as specified by the protocol
			pkt_tmp = copy.deepcopy(pkt) # can we Delete this TODO? --> pretty sure not
			pkt_tmp["last_hop"] = self.asn
			if pkt["content"]["relay_type"] == "next_hop": # TODO when do we use this??? check this pls
				next_hops = self.router_table.determine_next_hops(dst)
				self.send_packet(pkt_tmp, next_hops) 
			elif pkt["content"]["relay_type"] == "original_next_hop":
				next_hops = self.router_table.determine_highest_original()
				self.send_packet(pkt_tmp, next_hops) 
			elif pkt["content"]["relay_type"] == "broadcast":
				next_hops = list(set(self.ebgp_AS_peers) - {pkt["last_hop"]})
				self.send_packet(pkt_tmp, next_hops) 
			elif pkt["content"]["relay_type"] == "no_relay":
				pass

			############## react to it, if this packet has not already been seen
			if not pkt["identifier"] in self.seen_rats:
				self.seen_rats.append(pkt["identifier"])
				# call the corresponding reaction
				if pkt["content"]["protocol"] == "help":
					self.rat_reaction_help(pkt)
				elif pkt["content"]["protocol"] == "help_update":
					self.rat_reaction_help_update(pkt)
				elif pkt["content"]["protocol"] == "help_retractment":
					self.rat_reaction_help_retractment(pkt)
				elif pkt["content"]["protocol"] == "support":
					self.rat_reaction_support(pkt)
				elif pkt["content"]["protocol"] == "attack_path":
					self.rat_reaction_attack_path(pkt)
				elif pkt["content"]["protocol"] == "ally_exchange":
					self.rat_reaction_ally_exchange(pkt)

	def rat_reaction_ally_exchange(self, pkt):
		pass

	def process_std_pkt(self, pkt):
		"""
		This method is responsible for processing an incoming, standard packet. The basic idea is,
		that if we are the destination of the packet, we will receive it, and otherwise it will
		be relayed to the next hop.

		:param pkt: the incoming packets

		:type pkt: dict
		"""

		# if the destination of this packet is an address this AS advertise, this node is getting attacked
		if pkt["dst"] in self.advertised:
			self.attack_reaction(pkt)
		# else, relay it
		else:
			pkt["last_hop"] = self.asn
			self.send_packet(pkt, self.router_table.determine_next_hops(pkt["dst"]))



	def attack_reaction(self, pkt):
		"""
		This method implements the response to receiving an attack packet.

		:param pkt: the incoming packets

		:type pkt: dict
		"""
		self.logger.info(f"[{self.env.now}] Attack Packet with ID {pkt['identifier']} arrived with magnitutde {pkt['content']['attack_volume']} Gbps.")
		self.received_attacks.append((self.env.now, pkt["content"]["attack_volume"]))



	def rat_reaction_help_update(self, pkt):
		""" # TODO dont needs this, both help an dhelp update do the same
		This method implements the response to receiving a RAT packet, with the help update protocol. The router table will
		receive an update regarding the current estimate of the attack volume.

		:param pkt: the incoming packets

		:type pkt: dict
		"""
		self.logger.info(f"Reacting to Help Update RAT")
		self.router_table.update_attack_volume(pkt["content"]["attack_volume"])


	def rat_reaction_help_retractment(self, pkt):
		""" 

		:param pkt: the incoming packets

		:type pkt: dict
		"""
		self.logger.info(f"Reacting to Help Retractment RAT")
		self.router_table.reset()
		self.helping_node = []

		# reset any attribute that might have been set
		# TODO check if this really works
		if hasattr(self, "on_attack_path"):
			self.on_attack_path = False
		if hasattr(self, "attack_path_predecessor"):
			self.attack_path_predecessor = None
		if hasattr(self, "atk_path_signal"):
			self.atk_path_signal = False
		if hasattr(self, "nr_help_updates"):
			self.nr_help_updates = 0
		if hasattr(self, "attack_volume_approx"):
			self.attack_volume_approx = None
		if hasattr(self, "ally_help"):
			self.ally_help = {}
		if hasattr(self, "supporting_allies"):
			self.supporting_allies = []
			


	def rat_reaction_help(self, pkt):
		"""
		This method implements the response to receiving a RAT packet, with the help protocol. A default AS will simply
		broadcast it to its peers.

		:param pkt: the incoming packets

		:type pkt: dict
		"""
		self.logger.info(f"Reacting to Help RAT")
		self.helping_node.append(pkt["src"])
		self.router_table.update_attack_volume(pkt["content"]["attack_volume"])



	def rat_reaction_support(self, pkt): 
		"""
		This method implements the response to receiving a RAT packet, with the support protocol. This node
		might update its routing table, if 
			a) it does not believe itself to be on the attack path, or
			b) if it is on the attack path, the last hop of the package does not come along the attack path.

		:param pkt: the incoming packets

		:type pkt: dict
		"""
		if pkt["content"]["as_path_to_victim"][-1] in self.helping_node:
			self.logger.info(f"Reacting to Support RAT")

			# add the advertised route the routing table
			entry = {
				"identifier": "TODO", 
				"next_hop": pkt["content"]["as_path_to_victim"][pkt["content"]["hc"]-1],
				"destination": pkt["content"]["as_path_to_victim"][-1], # the router thiinks, the destination is the vicitm, although ally
				"priority": 3 if (pkt["last_hop"] != self.attack_path_predecessor) else 1, # depending on whether this node handles this split or not, set the priority
				"split_percentage": 0,
				"scrubbing_capabilities": pkt["content"]["scrubbing_capability"],
				"as_path": pkt["content"]["as_path_to_victim"][pkt["content"]["hc"]:], # TODO -1 or not???, want to include this node as start
				"origin": f"ally_{pkt['src']}",
				"recvd_from": pkt["last_hop"],
				"time_added": self.env.now
			}
			self.router_table.add_entry(entry) # TODO need to trigger some change?


	def rat_reaction_attack_path(self, pkt):
		"""
		This method implements the response to receiving a RAT packet, with the attack_path protocol. the response is
		to increase the priority of the original next hop, so that it is on an even level with used ally entries. At the same
		time, decrease all ally priorities that come from the attack path, since an AS further up the attack path is responsible
		for splitting towards it.

		:param pkt: the incoming packets

		:type pkt: dict
		"""
		self.logger.info(f"[{self.env.now}] Reacting to Attack Path RAT")

		# note that this AS is on the attack path, and not its predecessor
		self.on_attack_path = True
		self.attack_path_predecessor = pkt["last_hop"]

		# increase the priority of the original next hop entry
		self.router_table.increase_original_priority()
		# decrease the priority of all ally paths that come from the attack path
		self.router_table.reduce_allies_based_on_last_hop(pkt["last_hop"])



	def __str__(self):
		return f"AS-{self.asn}"






class SourceAS(AutonomousSystem):
	# TODO can only handle if *args is used, not **kwargs (or we can make it vice verca) --> general soluation

	"""
	This class represents an autonomous systems, that is the source of attack traffic; it inherits from "AutonomousSystem".

	:param attack_vol_limits:
	:param attack_freq:
	:param as_path_to_victim:
	:param atk_path_signal:
	:param attack_traffic_recording:

	:type attack_vol_limits: tuple[int, int]
	:type attack_freq: float
	:type as_path_to_victim: list[int]
	:type atk_path_signal: bool
	:type attack_traffic_recording:	list[float]	
	"""

	__doc__ += AutonomousSystem.__doc__



	def __init__(self, *args, **kwargs):
		
		super().__init__(*args)

		# used to determine size and frequency of attack packets
		self.attack_vol_limits = args[-1]["attack_vol_limits"]
		self.attack_freq = args[-1]["attack_freq"]

		# TODO
		self.as_path_to_victim = args[-1]["as_path_to_victim"]

		# used to recognize, whether an attack path signal has already been issued
		self.atk_path_signal = False	

		# used to record sent out attack traffic 
		self.attack_traffic_recording = []



	def attack_cycle(self):
		"""	
		This method, once called, will initiate an attack cycle.
		"""


		self.logger.info(f"[{self.env.now}] Starting attack on {self.as_path_to_victim[-1]} with limits {self.attack_vol_limits} and frequency {self.attack_freq}.")

		atk_indx = 0
		while True:
			yield self.env.timeout(self.attack_freq)

			# TODO just to simualte something
			if self.env.now <= 100:
				addition_factor = 400
			elif 100 < self.env.now <= 130:
				addition_factor = (self.env.now - 100) * 13.3
			elif 130 < self.env.now <= 230:
				addition_factor = - random.randint(*self.attack_vol_limits) 
			elif 230 < self.env.now <= 300:
				addition_factor = (self.env.now - 230) * 10
			elif 300 < self.env.now:
				addition_factor = 700

			attack_volume = random.randint(*self.attack_vol_limits) + addition_factor
			self.attack_traffic_recording.append((self.env.now, attack_volume))
			pkt = {
				"identifier": f"Attack_Packet_{self.asn}_{atk_indx}",
				"pkt_type": "STD",
				"src": self.asn,
				"dst": self.as_path_to_victim[-1],
				"last_hop": self.asn,
				"content": {"attack_volume" : attack_volume, "relay_type": "next_hop", "hc": 0}
			}
			self.send_packet(pkt, self.router_table.determine_next_hops(self.as_path_to_victim[-1]))
			atk_indx += 1



	def rat_reaction_help(self, pkt):
		"""
		This method represents the reaction of a DDoS source AS to receiving a help protocol RAT message.
		The main reaction revolves around issuing a RAT that will determine the attack path.

		:param pkt: the incoming packets

		:type pkt: dict
		"""
		self.router_table.update_attack_volume(pkt["content"]["attack_volume"])
		self.helping_node.append(pkt["src"])

		if (pkt["content"]["attacker_asn"] == self.asn) and (not self.atk_path_signal):
			# attack path signal
			self.atk_path_signal = True
			self.on_attack_path = True
			self.logger.info(f"[{self.env.now}] Help registered. Determining Attack Path.")
			pkt = {
				"identifier": f"atk_path_signal_from_{self.asn}_{float(self.env.now):6.2}",
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



	def __str__(self):
		return f"AS-{self.asn} (Source) [{self.attack_vol_limits}]"






class VictimAS(AutonomousSystem):

	"""
	This class represents an autonomous systems, that is the victim of DDoS attack traffic; it inherits 
	from "AutonomousSystem".

	:param scrubbing_cap:
	:param as_path_to_victim:
	:param help_signal_issued:
	:param nr_help_updates:
	:param ally_help:

	:type scrubbing_cap: int
	:type as_path_to_victim: list[int]
	:type help_signal_issued: bool
	:type nr_help_updates: int
	:type ally_help: dict	
	"""

	__doc__ += AutonomousSystem.__doc__

	# TODO can only handle if *args is used, not **kwargs (or we can make it vice verca) --> general soluation
	def __init__(self, *args, **kwargs):
		super().__init__(*args)

		# remember scrubbing capabilitiy
		self.scrubbing_cap = args[-1]["scrubbing_capability"]

		# TODO
		self.as_path_to_victim = args[-1]["as_path_to_victim"]

		# used to recognize, whether a help signal has already been issued
		self.help_signal_issued = False	

		# used to keep track of the number of help updates issued
		self.nr_help_updates = 0

		# used to keep track of the attack traffic
		self.attack_volume_approx = None

		# denote the allies that help
		self.ally_help = {}

		# to note when the last retractment was made, in order to not hastily issue a new help RAT
		self.last_retractment = -10000000
		self.last_help = -10000000

		# and a variable for a threshold
		self.new_signal_threshold = 25

		# help update threshold before new one
		self.help_update_pkt_threshold = 10
		self.help_update_pkt_ctr = self.help_update_pkt_threshold


	def attack_vol_approximation(self):
		# TODO maybe something fancier
		#	this is too flexible
		# 	but moving average to slow --> we dont want average, but current approximation
		#	also a threshold would be nice, so that it doesnt trigger every attack, but only when too much deviation
		return self.received_attacks[-1][1]


	def help_condition(self, nr_time_steps = 5, min_atk_pkts = 5): # TODO this as attributes

		atk_pkts = 0

		for atk_time, atk_vol in self.received_attacks:
			if (atk_time > self.env.now - nr_time_steps) and 	(self.attack_vol_approximation() + sum(self.ally_help.values()) > self.scrubbing_cap):
				atk_pkts += 1
		
		return (atk_pkts >= min_atk_pkts) and (self.env.now - self.last_retractment) > self.new_signal_threshold


	def retractment_condition(self, nr_time_steps = 5, min_atk_pkts = 5):


		atk_pkts = 0

		for atk_time, atk_vol in self.received_attacks:
			if (atk_time > self.env.now - nr_time_steps) and 	(self.attack_vol_approximation() + sum(self.ally_help.values()) < self.scrubbing_cap):
				atk_pkts += 1
		
		return (atk_pkts >= min_atk_pkts) and (self.env.now - self.last_help) > self.new_signal_threshold


	def attack_reaction(self, pkt):
		"""
		This method represents the reaction of a victim node to receiving an DDoS attack packet. The first it gets attack,
		it will issue a help statement to alert allies and the source AS. Subsequent attack packets are used to estimate
		the current attack volume (which might change over time) and then are broadcasted, in order to correctly adapt
		splitting rates.

		:param pkt: the incoming packets

		:type pkt: dict
		"""

		self.logger.info(f"[{self.env.now}] Attack Packet with ID {pkt['identifier']} arrived with magnitutde {pkt['content']['attack_volume']} Gbps.")
		self.received_attacks.append((self.env.now, pkt["content"]["attack_volume"]))


		help_pkt = {
			"identifier": None,
			"pkt_type": "RAT",
			"src": self.asn,
			"dst": None,
			"last_hop": self.asn, 
			"content": None
		}

		# TODO since sometimes the allies get less then they can (because of attack approximation being delayed in a sense),
		# we add this weird correcting scala
		TODO_CORRECTING_SCALA = 0.75

		if not self.help_signal_issued and self.help_condition(): # Case: We need Help
			self.logger.info(f"[{self.env.now}] Attack registered. Calling for help.")
			self.network.plot_values["victim_help_calls"].append((self.env.now, self.received_attacks[-1][1]))
			self.help_signal_issued = True
			self.last_help = self.env.now
			help_pkt["identifier"] = f"help_{float(self.env.now):6.2}"
			help_pkt["content"] = {"attack_volume": self.attack_vol_approximation() + sum(self.ally_help.values()), 
												"attacker_asn": pkt["src"], "relay_type": "broadcast", "protocol": "help", "hc": 0}
		elif self.help_signal_issued and self.retractment_condition():# Case: We do not need help anymore # TODO now is kinda bad condition (onyl one below capabilities package might be too hasty --> need like a counter since when it has been like this)
			self.logger.info(f"[{self.env.now}] Issueing Help Retractment.")
			self.network.plot_values["victim_help_retractment_calls"].append((self.env.now, self.received_attacks[-1][1]))
			self.help_signal_issued = False
			help_pkt["identifier"] = f"help_retractment_{float(self.env.now):6.2}"
			self.last_retractment = self.env.now
			# TODO right now we broadcast this pkt, but, we could also say: do only broadcast it to ebgp peers from which you received a support or attack_path protocol RAT
			help_pkt["content"] = {"attacker_asn": pkt["src"], "relay_type": "broadcast", "protocol": "help_retractment", "hc": 0}

		elif self.help_signal_issued: # we need a conditon there that decides when it changed enough instead o f this counter TODO
			# condition, so not to over send, causes problem since everything changes
			self.help_update_pkt_ctr += 1
			if self.help_update_pkt_ctr >= self.help_update_pkt_threshold:
				self.help_update_pkt_ctr = 0

				self.logger.info(f"[{self.env.now}] Attack registered. Sending out update message.")
				help_pkt["identifier"] = f"help_update{self.nr_help_updates}_{float(self.env.now):6.2}"
				help_pkt["content"] = {"attack_volume": self.attack_vol_approximation() + sum(self.ally_help.values()), 
										"attacker_asn": pkt["src"], "relay_type": "broadcast", "protocol": "help_update", "hc": 0}
				self.nr_help_updates += 1

		if help_pkt["identifier"] != None: # to chec that we even have a pkt set to send
			self.send_packet(help_pkt, self.ebgp_AS_peers)



	def rat_reaction_support(self, pkt):
		"""
		This method represents the reaction of a victim node to receiving an support RAT message. It will denote
		the available scrubbing capabilities of the ally, in order to, later, more accurately approximate the original
		attack volume.

		:param pkt: the incoming packets

		:type pkt: dict
		"""
		if self.help_signal_issued:
			self.ally_help[f"ally{pkt['src']}"] = pkt["content"]["scrubbing_capability"]



	def __str__(self):
		return f"AS-{self.asn} (Victim) [{self.scrubbing_cap}]"





class AllyAS(AutonomousSystem):
	# TODO can only handle if *args is used, not **kwargs (or we can make it vice verca) --> general soluation

	"""
	This class represents an autonomous systems, that is the victim of DDoS attack traffic; it inherits 
	from "AutonomousSystem".

	:param scrubbing_cap:
	:param as_path_to_victim:

	:type scrubbing_cap: int
	:type as_path_to_victim: list[int]
	"""

	__doc__ += AutonomousSystem.__doc__

	def __init__(self, *args, **kwargs):
		super().__init__(*args)

		# remember scrubbing capabilitiy
		self.scrubbing_cap = args[-1]["scrubbing_capability"]
		
		# the path to the victim
		self.as_path_to_victim = args[-1]["as_path_to_victim"]

		# a list of all supporting allies
		self.supporting_allies = []

		self.help_encountered = False

	def decide_to_help(self):
		# sort first by ally asn, in order to have it the same everywhere
		self.supporting_allies.sort(key=operator.itemgetter('ally_asn'))

		# TODO we do not consider ally scrubbing capabilities... simply subtract that from intiial attack vol 
		# NOTE we assume that attack vol is already set in table
		success, result = self.dynamic_programming(len(self.supporting_allies) - 1, self.attack_vol_on_victim)

		# if the method didnt succeed, this means that we dont have enough, i.e., this one should help
		# else, check that it is used
		return (not success) or any([self.supporting_allies[used]["ally_asn"] == self.asn for used in result["used_allies"]])

	def dynamic_programming(self, max_ally_indx, remaining_traffic):
		# base cases
		if remaining_traffic <= 0:
			return True, {"unique_edges": [], "used_allies": []}
		elif max_ally_indx < 0:
			return False, None

		# main case
		first_success, first_results = self.dynamic_programming(max_ally_indx - 1, remaining_traffic)
		second_success, second_results = self.dynamic_programming(max_ally_indx - 1, remaining_traffic - self.supporting_allies[max_ally_indx]["scrubbing_capability"])

		if second_success:
			second_results["used_allies"].append(max_ally_indx)
			second_results["unique_edges"].extend(self.supporting_allies[max_ally_indx]["as_path_edges"])
			second_results["unique_edges"] = list(set(second_results["unique_edges"]))

		if (not first_success and not second_success):
			return False, None
		elif (first_success and second_success):
			return True, first_results if (len(first_results["unique_edges"]) < len(second_results["unique_edges"])) else second_results
		else:
			return True, first_results if first_success else second_results



	def send_support(self, victim):

		self.logger.info(f"[{self.env.now}] Sending Support.")

		# add the address of the victim node to the set of addresses this AS is ready to accept packets for
		self.advertised.append(victim)
		self.helping_node.append(victim)

		# send out the support message
		pkt = {
			"identifier": f"support_from_{self.asn}_{float(self.env.now):6.2}",
			"pkt_type": "RAT",
			"src": self.asn,
			"dst": None,
			"last_hop": self.asn,
			"content": {"relay_type": "original_next_hop", "scrubbing_capability": self.scrubbing_cap, "protocol": "support", "ally": self.asn, "victim": victim, "as_path_to_victim": self.as_path_to_victim, "hc": 0}
		}
		self.send_packet(pkt, self.router_table.determine_highest_original())


	def rat_reaction_help(self, pkt):
		"""
		This method represents the reaction of a ally node to receiving an help RAT message. It will broadcast a 
		support message, letting other nodes know that they may reroute DDoS traffic to this ally and how much this
		ally can scrub.

		:param pkt: the incoming packets

		:type pkt: dict
		"""

		# firstly denote the current amount of attack volume on the victim
		self.router_table.update_attack_volume(pkt["content"]["attack_volume"])
		self.logger.info(f"[{self.env.now}] Help registered.")
		self.attack_vol_on_victim = pkt["content"]["attack_volume"]
		self.help_encountered = True

		self.supporting_allies.append({
			"ally_asn": self.asn, 
			"scrubbing_capability": self.scrubbing_cap, 
			"as_path_edges": [(u, v) for u, v in zip(self.as_path_to_victim[:-1], self.as_path_to_victim[1:])]
			})
		
		if self.decide_to_help():
			self.send_support(pkt["src"])
			# and send directly to all allies; note, that this is implemented as RAT pkg,
			# but isnt really one
			pkt = {
				"identifier": f"ally_exchange_from_{self.asn}_{float(self.env.now):6.2}",
				"pkt_type": "RAT",
				"src": self.asn,
				"dst": None,
				"last_hop": self.asn,
				"content": {"relay_type": "broadcast", "scrubbing_capability": self.scrubbing_cap, "protocol": "ally_exchange", "ally": self.asn, "victim": self.as_path_to_victim[-1], "as_path_to_victim": self.as_path_to_victim, "hc": 0}
			}
			self.send_packet(pkt, self.ebgp_AS_peers)

	def rat_reaction_ally_exchange(self, pkt):
		self.logger.info(f"[{self.env.now}] Ally Exchange registered.")
		self.supporting_allies.append({
			"ally_asn": pkt["src"], 
			"scrubbing_capability": pkt["content"]["scrubbing_capability"], 
			"as_path_edges": [(u, v) for u, v in zip(pkt["content"]["as_path_to_victim"][:-1], pkt["content"]["as_path_to_victim"][1:])]
			})
		if pkt["content"]["victim"] in self.helping_node: # if we are already helping
			if self.decide_to_help(): # and want to keep helping
				pass # nothing
			else:
				print("IMPLEMENT ME, I DONT WANT TO HELP ANYMORE")
		elif self.help_encountered: # we did not want to help, but saw the message
			if self.decide_to_help():
				self.send_support(pkt["src"])
				# and send directly to all allies; note, that this is implemented as RAT pkg,
				# but isnt really one
			pkt = {
				"identifier": f"ally_exchange_from_{self.asn}_{float(self.env.now):6.2}",
				"pkt_type": "RAT",
				"src": self.asn,
				"dst": None,
				"last_hop": self.asn,
				"content": {"relay_type": "broadcast", "scrubbing_capability": self.scrubbing_cap, "protocol": "ally_exchange", "ally": self.asn, "victim": self.as_path_to_victim[-1], "as_path_to_victim": self.as_path_to_victim, "hc": 0}
			}
			self.send_packet(pkt, self.ebgp_AS_peers)

		else: 
			print("SHOULDNT HAPPEN, HELP SHOULD ARRIVE BEFORE ALLY EXCHANGE")
	def __str__(self):
		return f"AS-{self.asn} (Ally) [{self.scrubbing_cap}]"