"""
Contains the VictimAS class.

Author:
	Devrim Celik 08.06.2022
"""

from .autonomous_system import AutonomousSystem

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
		"""
		Method to approximate the attack volume by the victim.

		:return: the approximated attack volume
		:rtype: float
		"""
		return self.received_attacks[-1][1]


	def help_condition(self, nr_time_steps = 5, min_atk_pkts = 5): # TODO this as attributes
		"""
		This method is the trigger to whether a help call should be issued by the victim.

		:param nr_time_steps: TODO probably gonna be overhauled
		:param min_atk_pkts: TODO probably gonna be overhauled

		:type nr_time_steps: TODO probably gonna be overhauled
		:type min_atk_pkts: TODO probably gonna be overhauled

		:returns: whether a help call should be issued or not
		:rtype: bool
		"""
		atk_pkts = 0

		for atk_time, atk_vol in self.received_attacks:
			if (atk_time > self.env.now - nr_time_steps) and 	(self.attack_vol_approximation() + sum(self.ally_help.values()) > self.scrubbing_cap):
				atk_pkts += 1
		
		return (atk_pkts >= min_atk_pkts) and (self.env.now - self.last_retractment) > self.new_signal_threshold



	def retractment_condition(self, nr_time_steps = 5, min_atk_pkts = 5):
		"""
		This method is the trigger to whether a help call should be retracted by the victim.

		:param nr_time_steps: TODO probably gonna be overhauled
		:param min_atk_pkts: TODO probably gonna be overhauled

		:type nr_time_steps: TODO probably gonna be overhauled
		:type min_atk_pkts: TODO probably gonna be overhauled

		:returns: whether a retractment call should be issued or not
		:rtype: bool
		"""

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
			"type": "RAT",
			"src": self.asn,
			"dst": None,
			"last_hop": self.asn, 
			"content": None
		}

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

