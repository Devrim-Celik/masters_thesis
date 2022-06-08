"""
Contains old code snippets, that  might be reused at one point.

Author:
	Devrim Celik 08.06.2022
"""


################################################################################### 07.06
# allyAS: Where we used dynamic prograamming for ally exchange and have ally_exchange messages


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
			"type": "RAT",
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
				"type": "RAT",
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
		"""
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
				"type": "RAT",
				"src": self.asn,
				"dst": None,
				"last_hop": self.asn,
				"content": {"relay_type": "broadcast", "scrubbing_capability": self.scrubbing_cap, "protocol": "ally_exchange", "ally": self.asn, "victim": self.as_path_to_victim[-1], "as_path_to_victim": self.as_path_to_victim, "hc": 0}
			}
			self.send_packet(pkt, self.ebgp_AS_peers)
		
		else: 
			print("SHOULDNT HAPPEN, HELP SHOULD ARRIVE BEFORE ALLY EXCHANGE")
		"""
	def __str__(self):
		return f"AS-{self.asn} (Ally) [{self.scrubbing_cap}]"