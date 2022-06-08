"""
Contains the SourceAS class.

Author:
	Devrim Celik 08.06.2022
"""

import random
import math

from .autonomous_system import AutonomousSystem


class SourceAS(AutonomousSystem):
	"""
	This class represents an autonomous systems, that is the source of attack
	traffic; it inherits from "AutonomousSystem".

	:param full_attack_vol: the amount of traffic that the DDoS attack emits
	:param attack_freq: delay, in steps, between sending attacks
	:param as_path_to_victim: the path to the victim, by nodes
	:param atk_path_signal: whether the atk_path_singal was send out and
		is currently in affect
	:param attack_traffic_recording: records the send out attack packets
		for later plotting

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
		self.full_attack_vol = args[-1]["full_attack_vol"]
		self.standard_load = 50
		self.attack_start = random.randint(0, 40)
		self.attack_slowdown = 200
		self.attack_stop = 300
		self.attack_freq = args[-1]["attack_freq"]
		self.as_path_to_victim = args[-1]["as_path_to_victim"]
		self.atk_path_signal = False
		self.attack_traffic_recording = []



	def attack_cycle(self):
		"""
		This method, once called, will initiate an attack cycle.
		"""

		self.logger.info(f"[{self.env.now}] Starting attack on {self.as_path_to_victim[-1]} with full strength {self.full_attack_vol} and frequency {self.attack_freq}.")

		atk_indx = 0
		while True:
			yield self.env.timeout(self.attack_freq)

			if self.env.now < self.attack_start:
				attack_volume = random.randint(
					self.standard_load - 10,
					self.standard_load + 10
				)
			elif self.attack_start <= self.env.now < self.attack_slowdown:
				attack_volume = self.full_attack_vol - random.randint(
					0,
					int(self.full_attack_vol / 15)
				)
			elif self.attack_slowdown <= self.env.now < self.attack_stop:
				attack_volume = max(
					self.full_attack_vol * (0.95)**(self.env.now - self.attack_slowdown),
					self.standard_load
				)
			elif self.attack_stop <= self.env.now < self.attack_stop + 150:
				attack_volume = random.randint(
					self.standard_load - 10,
					self.standard_load + 10
				)
			elif self.attack_stop + 150 <= self.env.now < self.attack_start + self.attack_stop + 150:
				attack_volume = random.randint(
					self.standard_load - 10,
					self.standard_load + 10
				)
			elif self.attack_start + self.attack_stop + 150 <= self.env.now < self.attack_slowdown + self.attack_stop + 150:
				attack_volume = self.full_attack_vol - random.randint(
					0,
					int(self.full_attack_vol / 15)
				)
			elif self.attack_slowdown + self.attack_stop + 150 <= self.env.now < self.attack_stop + self.attack_stop + 150:
				attack_volume = max(
					self.full_attack_vol * (0.95)**(self.env.now - (self.attack_slowdown + self.attack_stop + 150)),
					self.standard_load)
			else:
				attack_volume = random.randint(
					self.standard_load - 10,
					self.standard_load + 10
				)

			self.attack_traffic_recording.append((self.env.now, attack_volume))
			pkt = {
				"identifier": f"Attack_Packet_{self.asn}_{atk_indx}",
				"type": "STD",
				"src": self.asn,
				"dst": self.as_path_to_victim[-1],
				"last_hop": self.asn,
				"content": {
					"attack_volume": attack_volume,
					"relay_type": "next_hop",
					"hc": 0
				}
			}

			self.send_packet(
				pkt,
				self.router_table.determine_next_hops(self.as_path_to_victim[-1])
			)
			atk_indx += 1



	def rat_reaction_help(self, pkt):
		"""
		This method represents the reaction of a DDoS source AS to receiving
		a help protocol RAT message. The main reaction revolves around
		issuing a RAT that will determine the attack path.

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
				"type": "RAT",
				"src": self.asn,
				"dst": None,
				"last_hop": self.asn,
				"content": {
					"relay_type": "original_next_hop",
					"protocol": "attack_path",
					"as_path_to_victim": self.as_path_to_victim,
					"handled_AS": [],
					"hc": 0
				}
			}
			self.send_packet(pkt, self.router_table.determine_highest_original())
			self.seen_rats.append(pkt["identifier"])

			# own reaction
			self.router_table.increase_original_priority()



	def __str__(self):
		return f"AS-{self.asn} (Source) [{self.full_attack_vol}]"
