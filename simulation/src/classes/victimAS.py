"""
Contains the VictimAS class.

Author:
	Devrim Celik 08.06.2022
"""

import simpy 
import numpy as np

from .autonomous_system import AutonomousSystem

class VictimAS(AutonomousSystem):

	"""
	This class represents an autonomous systems, that is the victim of DDoS
	attack traffic; it inherits from "AutonomousSystem".

	:param scrubbing_capability: scrubbing capability of this node
	:param as_path_to_victim:
	:param help_signal_issued: used to recognize, whether a help signal
		has already been issued
	:param ally_help: for collecting the allies that are helping this vctim

	:type scrubbing_capability: int
	:type as_path_to_victim: list[int]
	:type help_signal_issued: bool
	:type ally_help: dict
	"""

	__doc__ += AutonomousSystem.__doc__


	def __init__(self, *args, **kwargs):
		super().__init__(*args)

		##### set attributes
		# standard
		self.scrubbing_capability = args[-1]["scrubbing_capability"]
		self.as_path_to_victim = []
		self.attack_src = None
		# for attack volume approximation
		self.attack_volume_approximations = []
		self.expected_attack_volume = self.scrubbing_capability
		self.alpha_ewa = 0.3
		self.accelerator = 0.0
		self.momentum_starting_value = 0.001
		self.accelerator_factor = 0.25
		self.momentum_limit_value = 0.75

		# for help packet config
		self.help_msg_delay = 11
		self.help_msg_ctr = 0
		# for help signal and retractment
		self.last_retractment = -10000000
		self.last_help = -10000000
		self.help_signal_issued = False
		self.new_signal_threshold = 25
		self.help_process = None
		# for ally activation
		self.ally_activation_recordings = []
		self.ally_activation = 1.0
		self.ally_help_info = {}

		self.t2test = []
		self.t3test = []


	def attack_vol_approximation(self):
		"""
		Method to approximate the attack volume by the victim.

		:return: the approximated attack volume
		:rtype: float
		"""
		# HUGE TODO HUGE TODO: Just compare it to the victim scrubbing capability. If everything works as planned, we would expect 
		# the incoming traffic to be exactly that. 


		if not self.attack_volume_approximations:
			recent = self.received_attacks[-1][1]
		elif True:
			to_allies = sum([d["scrubbing_capability"] * d["activation"] for d in self.ally_help_info.values()])
			recent = to_allies + self.received_attacks[-1][1] # naive
			if sum([d["scrubbing_capability"] for d in self.ally_help_info.values()]) > self.attack_volume_approximations[-1]: # nuances if possible # TODO if condition is not really perfect...
				ratio = self.received_attacks[-1][1] / self.scrubbing_capability
				if np.sign(ratio - 1) == np.sign(self.accelerator):
					self.accelerator *= (1 + self.accelerator_factor)
				else:
					self.accelerator = np.sign(ratio - 1) * self.momentum_starting_value
				
				# apply limits to the momementun
				self.accelerator = min(max(self.accelerator, -self.momentum_limit_value), self.momentum_limit_value)


				recent *= 1 + self.accelerator

		"""
		elif True:
			recent = self.received_attacks[-1][1] + sum([d["scrubbing_capability"] * d["activation"] for d in self.ally_help_info.values()])
		else:
			recent = self.attack_volume_approximations[-1] * max(min(ratio, 1.05), 0.95) # TODO old one was without min max 
		"""
		"""
		if self.ally_help_info and t3 != 1:
			recent = self.attack_volume_approximations[-1] + self.attack_volume_approximations[-1]* (1 - self.received_attacks[-1][1]/(t2 * (1 - t3))) * 0.1
		"""

		self.logger.info(f"{self.env.now}: recent: {self.received_attacks[-1][1]} + {self.ally_help_info}")


		# smoothing using previous attack volume approximation
		if self.attack_volume_approximations:
			new_approx = self.alpha_ewa * recent + (1 - self.alpha_ewa) * self.attack_volume_approximations[-1]
			self.logger.info(f"{self.env.now}: recent: {recent}, old: {self.attack_volume_approximations[-1]} and alpha {self.alpha_ewa}.")
		else:
			new_approx = recent


		self.attack_volume_approximations.append(new_approx)

		self.network.plot_values["victim_attack_approximations"].append(
			(self.env.now, new_approx)
		)

		return new_approx



	def calculate_new_ally_activation(self):
		if self.ally_help_info:
			ally_activation = min(max((self.attack_volume_approximations[-1] - self.scrubbing_capability) / sum([d["scrubbing_capability"] for d in self.ally_help_info.values()]), 0), 1)
		else:
			ally_activation = 1.0
		return ally_activation


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
			if (self.attack_volume_approximations[-1] > self.scrubbing_capability):
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
			if (self.attack_volume_approximations[-1] < self.scrubbing_capability):
				atk_pkts += 1

		return (atk_pkts >= min_atk_pkts) and (self.env.now - self.last_help) > self.new_signal_threshold

	def set_ally_activation_w_delay(self, delay, new_activation, ally):
		try:
			yield self.env.timeout(delay)
			# TODO self.ally_activation_recordings.append([self.env.now, new_activation])
			self.logger.info(f"{self.env.now} | Setting Ally {ally} percentage to {new_activation}.")
			self.ally_help_info[ally]["activation"] = new_activation
		except simpy.Interrupt:
			pass

	def help_cycle(self):

		try:
			processes = []
			while True:
				new_ally_activation = self.calculate_new_ally_activation()
				for ally, dic in self.ally_help_info.items():
					processes.append([self.env.process(self.set_ally_activation_w_delay(dic["splitting_node_delay"]*2, new_ally_activation, ally)), self.env.now + dic["splitting_node_delay"]*2])
				help_pkt = {
					"identifier": f"help_{self.help_msg_ctr}_{self.asn}",
					"type": "RAT",
					"src": self.asn,
					"dst": None,
					"last_hop": self.asn,
					"content": {
						"attack_volume": self.attack_volume_approximations[-1], # TODO 
						"attacker_asn": self.attack_src,
						"scrubbing_capability": self.scrubbing_capability,
						"relay_type": "broadcast" if self.help_msg_ctr == 0 else "broadcast", # TODO sencdond broadcast to attck path
						"protocol": "help",
						"ally_percentage": new_ally_activation,
						"initial_call": self.help_msg_ctr == 0,
						"hc": 0
					}
				}
				self.logger.info(f"Help Packet \"{help_pkt['identifier']}\" sent.")
				self.help_msg_ctr += 1
				self.send_packet(help_pkt, self.ebgp_AS_peers)
				yield self.env.timeout(self.help_msg_delay)

		except simpy.Interrupt:
			for p, t in processes:
				if t > self.env.now:
					p.interrupt()

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

		self.attack_vol_approximation()

		# Case: The attack is larger than our scrubbing capabilities / then we expect
		if self.expected_attack_volume < int(pkt["content"]["attack_volume"]):
			# if this is the first attack packet we see
			if not self.help_signal_issued:
				self.logger.info(f"[{self.env.now}] Initiating Help Cycle.")
				# we set the attack volume approximation
				self.attack_volume_approximations.append(pkt["content"]["attack_volume"])
				self.attack_src = pkt["src"]
				self.help_process = self.env.process(self.help_cycle())

				self.help_signal_issued = True



		# Case: We do not need help anymore
		elif self.help_signal_issued and self.retractment_condition():
			if self.help_process != None:
				self.help_process.interrupt()
				self.help_process
			self.logger.info(f"[{self.env.now}] Issueing Help Retractment.")
			self.ally_activation = 1.0
			self.ally_help_info = {}
			self.help_signal_issued = False
			self.accelerator = 0.0
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
			try:
				self.ally_help_info[f"ally{pkt['src']}"] = {"scrubbing_capability": pkt["content"]["scrubbing_capability"], "splitting_node_delay": self.env.now - pkt["content"]["splitting_node_time"], "activation": 1.0}
			except:
				print("\n"*5)
				print(pkt)
				print("\n"*5)
	def __str__(self):
		return f"AS-{self.asn} (Victim) [{self.scrubbing_capability }]"
