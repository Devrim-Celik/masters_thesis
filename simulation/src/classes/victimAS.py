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

	:param scrubbing_capability: scrubbing capability of this node
	:param as_path_to_victim:
	:param help_signal_issued: used to recognize, whether a help signal
		has already been issued
	:param attack_volume_approx: used to keep track of the attack traffic
		approximation
	:param ally_help: for collecting the allies that are helping this vctim

	:type scrubbing_capability: int
	:type as_path_to_victim: list[int]
	:type help_signal_issued: bool
	:type ally_help: dict
	"""

	__doc__ += AutonomousSystem.__doc__


	def __init__(self, *args, **kwargs):
		super().__init__(*args)

		# remember scrubbing capabilitiy
		self.scrubbing_capability = args[-1]["scrubbing_capability"]
		self.as_path_to_victim = []
		self.help_signal_issued = False
		self.attack_volume_approx = None
		self.attack_volume_approximations = []
		self.expected_attack_volume = self.scrubbing_capability
		self.alpha_ewa = 0.6
		self.ally_percentage = 1.0
		self.ally_help = {}
		self.help_msg_delay = 11
		self.help_msg_ctr = 0
		self.attack_src = None
		# TODO
		self.last_retractment = -10000000
		self.last_help = -10000000
		self.new_signal_threshold = 25

	def attack_vol_approximation(self):
		"""
		Method to approximate the attack volume by the victim.

		:return: the approximated attack volume
		:rtype: float
		"""

		# TODO this needs a part, where it compares against expected and uses this to update
		# ONE QUICK IDEA: if ally perc == 1, use this, since i
		# MAYBE THIS IDEA DOESNT BELONG HERE, BUT WITH ALLY SPLIT PERC
		# what i mean: if we receive more than we expect -> the attack volume changes, AND, the split percentage???

		recent = self.received_attacks[-1][1] + sum(self.ally_help.values()) * self.ally_percentage
		if self.attack_volume_approximations:
			self.attack_volume_approx = self.alpha_ewa * recent + (1- self.alpha_ewa) * self.attack_volume_approximations[-1]
		else:
			self.attack_volume_approx = recent

		self.attack_volume_approximations.append(self.attack_volume_approx)


		self.network.plot_values["victim_attack_approximations"].append(
			(self.env.now, self.attack_volume_approx)
		)

		return self.attack_volume_approx


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
			if (self.attack_vol_approximation()> self.scrubbing_capability):
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
			if (self.attack_vol_approximation() < self.scrubbing_capability):
				atk_pkts += 1

		return (atk_pkts >= min_atk_pkts) and (self.env.now - self.last_help) > self.new_signal_threshold


	def help_cycle(self):
		while True:
			help_pkt = {
				"identifier": f"help_{self.help_msg_ctr}_{self.asn}",
				"type": "RAT",
				"src": self.asn,
				"dst": None,
				"last_hop": self.asn,
				"content": {
					"attack_volume": self.attack_vol_approximation(), # TODO 
					"attacker_asn": self.attack_src,
					"scrubbing_capability": self.scrubbing_capability,
					"relay_type": "broadcast" if self.help_msg_ctr == 0 else "broadcast", # TODO sencdond broadcast to attck path
					"protocol": "help",
					"ally_percentage": self.ally_percentage,
					"initial_call": self.help_msg_ctr == 0,
					"hc": 0
				}
			}
			self.logger.info(f"Help Packet \"{help_pkt['identifier']}\" sent.")
			self.help_msg_ctr += 1
			self.send_packet(help_pkt, self.ebgp_AS_peers)
			yield self.env.timeout(self.help_msg_delay)

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

		# save the attack packets
		self.received_attacks.append(
			(self.env.now, pkt["content"]["attack_volume"])
		)
		self.network.plot_values["victim_help_calls"].append(
			(self.env.now, pkt["content"]["attack_volume"])
		)


		# Case: The attack is larger than our scrubbing capabilities / then we expect
		if self.expected_attack_volume < int(pkt["content"]["attack_volume"]):
			
			# if this is the first attack packet we see
			if not self.help_signal_issued:
				self.logger.info(f"[{self.env.now}] Initiating Help Cycle.")
				# we set the attack volume approximation
				self.attack_volume_approx = pkt["content"]["attack_volume"]
				self.attack_src = pkt["src"]
				self.env.process(self.help_cycle())

				self.help_signal_issued = True



		# Case: We do not need help anymore
		elif self.help_signal_issued and self.retractment_condition():
			print("IMPLEMENT ME!, STOP THE HELP!!")
			self.logger.info(f"[{self.env.now}] Issueing Help Retractment.")
			self.help_signal_issued = False
			self.last_retractment = self.env.now
			# TODO right now we broadcast this pkt, but, we could also say: do
			# only broadcast it to ebgp peers from which you received a
			# support or attack_path protocol RAT
			help_pkt = {
				"identifier": f"help_retractment_{float(self.env.now):6.2}",
				"type": "RAT",
				"src": self.asn,
				"dst": None,
				"last_hop": self.asn,
				"content": {
					"attacker_asn": pkt["src"],
					"relay_type": "broadcast",
					"protocol": "help_retractment",
					"hc": 0
				}
			}
			self.rat_reaction_help_retractment(help_pkt)

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
			self.ally_percentage = min((self.attack_volume_approx - self.scrubbing_capability) / sum(self.ally_help.values()), 1)


	def __str__(self):
		return f"AS-{self.asn} (Victim) [{self.scrubbing_capability }]"
