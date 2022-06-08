"""
Contains the VictimAS class.

Author:
	Devrim Celik 08.06.2022
"""

from .autonomous_system import AutonomousSystem


class VictimAS(AutonomousSystem):

	"""
	This class represents an autonomous systems, that is the victim of DDoS
	attack traffic; it inherits from "AutonomousSystem".

	:param scrubbing_cap: scrubbing capability of this node
	:param as_path_to_victim:
	:param help_signal_issued: used to recognize, whether a help signal
		has already been issued
	:param nr_help_updates: used to keep track of the number of help updates
		issued
	:param attack_volume_approx: used to keep track of the attack traffic
		approximation
	:param ally_help: for collecting the allies that are helping this vctim

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
		self.as_path_to_victim = []
		self.help_signal_issued = False
		self.nr_help_updates = 0
		self.attack_volume_approx = None

		self.ally_help = {}

		# TODO
		self.last_retractment = -10000000
		self.last_help = -10000000
		self.new_signal_threshold = 25
		self.help_update_pkt_threshold = 10
		self.help_update_pkt_ctr = self.help_update_pkt_threshold


	def attack_vol_approximation(self):
		"""
		Method to approximate the attack volume by the victim.

		:return: the approximated attack volume
		:rtype: float
		"""
		return self.received_attacks[-1][1]


	def help_condition(self, nr_last_rcv=5, min_atk_pkts=5):
		"""
		This method is the trigger to whether a help call should be
		issued by the victim.

		:param nr_last_rcv: TODO probably gonna be overhauled
		:param min_atk_pkts: TODO probably gonna be overhauled

		:type nr_last_rcv: TODO probably gonna be overhauled
		:type min_atk_pkts: TODO probably gonna be overhauled

		:returns: whether a help call should be issued or not
		:rtype: bool
		"""
		atk_pkts = 0

		for atk_time, atk_vol in self.received_attacks[:-nr_last_rcv]:
			if (self.attack_vol_approximation() + sum(self.ally_help.values()) > self.scrubbing_cap):
				atk_pkts += 1

		return (atk_pkts >= min_atk_pkts) and (self.env.now - self.last_retractment) > self.new_signal_threshold


	def retractment_condition(self, nr_last_rcv=5, min_atk_pkts=5):
		"""
		This method is the trigger to whether a help call should be retracted
		by the victim.

		:param nr_last_rcv: TODO probably gonna be overhauled
		:param min_atk_pkts: TODO probably gonna be overhauled

		:type nr_last_rcv: TODO probably gonna be overhauled
		:type min_atk_pkts: TODO probably gonna be overhauled

		:returns: whether a retractment call should be issued or not
		:rtype: bool
		"""

		atk_pkts = 0

		for atk_time, atk_vol in self.received_attacks[:-nr_last_rcv]:
			if (self.attack_vol_approximation() + sum(self.ally_help.values()) < self.scrubbing_cap):
				atk_pkts += 1

		return (atk_pkts >= min_atk_pkts) and (self.env.now - self.last_help) > self.new_signal_threshold


	def attack_reaction(self, pkt):
		"""
		This method represents the reaction of a victim node to receiving an
		DDoS attack packet. The first it gets attack, it will issue a help
		statement to alert allies and the source AS. Subsequent attack packets
		are used to estimate
		the current attack volume (which might change over time) and then are
		broadcasted, in order to correctly adapt splitting rates.

		:param pkt: the incoming packets

		:type pkt: dict
		"""

		self.logger.info(f"[{self.env.now}] Attack Packet with ID {pkt['identifier']} arrived with magnitutde {pkt['content']['attack_volume']} Gbps.")
		self.received_attacks.append(
			(self.env.now, pkt["content"]["attack_volume"])
		)


		help_pkt = {
			"identifier": None,
			"type": "RAT",
			"src": self.asn,
			"dst": None,
			"last_hop": self.asn,
			"content": None
		}

		# Case: We need Help
		if not self.help_signal_issued and self.help_condition():
			self.logger.info(f"[{self.env.now}] Attack registered. Calling for help.")
			self.network.plot_values["victim_help_calls"].append(
				(self.env.now, self.received_attacks[-1][1])
			)
			self.help_signal_issued = True
			self.last_help = self.env.now
			help_pkt["identifier"] = f"help_{float(self.env.now):6.2}"
			help_pkt["content"] = {
				"attack_volume": self.attack_vol_approximation() + sum(self.ally_help.values()),
				"attacker_asn": pkt["src"],
				"relay_type": "broadcast",
				"protocol": "help",
				"hc": 0
			}

		# Case: We do not need help anymore
		elif self.help_signal_issued and self.retractment_condition():
			self.logger.info(f"[{self.env.now}] Issueing Help Retractment.")
			self.network.plot_values["victim_help_retractment_calls"].append(
				(self.env.now, self.received_attacks[-1][1])
			)
			self.help_signal_issued = False
			help_pkt["identifier"] = f"help_retractment_{float(self.env.now):6.2}"
			self.last_retractment = self.env.now
			# TODO right now we broadcast this pkt, but, we could also say: do
			# only broadcast it to ebgp peers from which you received a
			# support or attack_path protocol RAT
			help_pkt["content"] = {
				"attacker_asn": pkt["src"],
				"relay_type": "broadcast",
				"protocol": "help_retractment",
				"hc": 0
			}
			self.rat_reaction_help_retractment(help_pkt)

		# Case: We already asked for help, but want to update attack volume
		elif self.help_signal_issued:
			self.help_update_pkt_ctr += 1
			if self.help_update_pkt_ctr >= self.help_update_pkt_threshold:
				self.help_update_pkt_ctr = 0

				self.logger.info(f"[{self.env.now}] Attack registered. Sending out update message.")
				help_pkt["identifier"] = f"help_update{self.nr_help_updates}_{float(self.env.now):6.2}"
				help_pkt["content"] = {
					"attack_volume": self.attack_vol_approximation() + sum(self.ally_help.values()),
					"attacker_asn": pkt["src"],
					"relay_type": "broadcast",
					"protocol": "help_update",
					"hc": 0
				}
				self.nr_help_updates += 1

		self.send_packet(help_pkt, self.ebgp_AS_peers)


	def rat_reaction_support(self, pkt):
		"""
		This method represents the reaction of a victim node to receiving an
		support RAT message. It will denote the available scrubbing
		capabilities of the ally, in order to, later, more accurately
		approximate the original attack volume.

		:param pkt: the incoming packets

		:type pkt: dict
		"""
		if self.help_signal_issued:
			self.ally_help[f"ally{pkt['src']}"] = pkt["content"]["scrubbing_capability"]


	def __str__(self):
		return f"AS-{self.asn} (Victim) [{self.scrubbing_cap}]"
