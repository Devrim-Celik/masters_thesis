"""
Contains the AllyAS class.

Author:
	Devrim Celik 08.06.2022
"""


from .autonomous_system import AutonomousSystem


class AllyAS(AutonomousSystem):
	"""
	This class represents an autonomous systems, that is the victim of DDoS
	attack traffic; it inherits from "AutonomousSystem".

	:param scrubbing_capability: the scrubbing capability of this ally
	:param as_path_to_victim: the as path from this victim to the ally

	:type scrubbing_capability: float
	:type as_path_to_victim: list[int]
	"""

	__doc__ += AutonomousSystem.__doc__

	def __init__(self, *args, **kwargs):
		super().__init__(*args)

		# remember scrubbing capabilitiy
		self.scrubbing_capability = args[-1]["scrubbing_capability"]

		# the path to the victim
		self.as_path_to_victim = args[-1]["as_path_to_victim"]

		# helping
		self.helping_nodes = []

	def send_support(self, victim):

		self.logger.info(f"[{self.env.now}] Sending Support.")

		# add the address of the victim node to the set of addresses this AS is ready to
		# accept packets for
		self.advertised.append(victim)
		self.helping_node.append(victim)

		# send out the support message
		pkt = {"identifier": f"support_from_{self.asn}_{float(self.env.now):6.2}",
			   "type": "RAT",
			   "src": self.asn,
			   "dst": None,
			   "last_hop": self.asn,
			   "content": {"relay_type": "original_next_hop", 
						   "scrubbing_capability": self.scrubbing_capability, 
						   "protocol": "support", 
						   "ally": self.asn, 
						   "victim": victim, 
						   "as_path_to_victim": self.as_path_to_victim, 
						   "hc": 0
				}
		}
		self.send_packet(pkt, self.router_table.determine_highest_original())


	def rat_reaction_help(self, pkt):
		"""
		This method represents the reaction of a ally node to receiving an help RAT message.
		It will broadcast a support message, letting other nodes know that they may reroute DDoS
		traffic to this ally and how much this ally can scrub.

		:param pkt: the incoming packets

		:type pkt: dict
		"""

		if not pkt["src"] in self.helping_nodes:
			self.helping_nodes.append(pkt["src"])

			# firstly denote the current amount of attack volume on the victim
			self.router_table.update_victim_info(pkt["content"]["scrubbing_capability"], pkt["content"]["attack_volume"], pkt["content"]["ally_percentage"])
			self.logger.info(f"[{self.env.now}] Help registered.")
			self.attack_vol_on_victim = pkt["content"]["attack_volume"]
			self.send_support(pkt["src"])

	def __str__(self):
		return f"AS-{self.asn} (Ally) [{self.scrubbing_capability}]"
		