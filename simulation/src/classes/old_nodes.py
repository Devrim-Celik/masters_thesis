import simpy
import logging
import numpy as np

# TODO 
# maybe have a standard process packet
# which calls function: special reactions
# different for each class -> maybe only if it has protocol send? is that good neoug?

# next_hops -> router table

class AS(object):
	"""
	This class represents a generic autonmous system, as used in our simulation.
	Generally, they are connected to a set of other ASes, have a ASN, can receive and
	send messages.
	"""

	__available_AS_roles__ = [
		"standard",
		"source",
		"victim",
		"ally"
	]

	def __init__(
		self,
		env: simpy.Environment,
		net,
		asn:int,
		role: str,
		ebgp_AS_peers: list,
		next_hops: int,
		as_path_to_victim:list,
		):
		"""
		:param env: the simpy environment
		:param net: the internet object
		:param asn: autonomous system number
		:param role: the role of this AS
		:param ebgp_AS_peers: all ASes that are connected to this AS
		:param next_hop: the AS, that is the next hop towards the target IP address, according to BGP
		:param victim_asn: the ASN of the victim node

		:type env: simpy.Environment
		:type net: Internet
		:type asn: int
		:type role: str
		:type ebgp_AS_peers: list
		:type next_hop: int
		:type victim_asn: int

		"""

		# check that this AS is actually connected to its next hop
		assert next_hops == None or set([t[0] for t in next_hops]).issubset(set(ebgp_AS_peers))
		# check that the role is valid
		assert role in self.__available_AS_roles__

		# assign attributes
		self.env = env
		self.net = net
		self.asn = asn
		self.role = role
		self.next_hops = next_hops
		self.ebgp_AS_peers = ebgp_AS_peers
		self.as_path_to_victim = as_path_to_victim


		# for saving received advertisements, in order to diferentiate between new and old
		self.received_router_advs = []
		self.received_ally_changes = []

		# which packet this one would accept
		self.advertised = [self.asn]

		# variable denoting whether this node is on the attack path and aware of it
		self.on_attack_path = False
		self.attack_volume_on_victim = None
		self.is_entry_for_allies = []

		# since these are only initialized in the specific cases
		if role == "victim":
			self.help_called = False
			self.scrubbing_cap = None
		elif role == "ally":
			self.scrubbing_cap = None

	def choose_next_hop(self):
		# TODO instead of binary probable choice, split
		return int(np.random.choice([t[0] for t in self.next_hops], 1, p=[t[1] for t in self.next_hops]))

	def choose_original(self):
		return [t[0] for t in self.next_hops if t[2] == "original"][0]

	def split_next_hops(self):
		if self.next_hops:# avoid victim
			to_allies = 0
			new_next_hops = []
			for entry in self.next_hops:
				print(entry)
				if entry[2] == "ally": #TOOD make entries to dictionaries...
					print("SOP")
					new_next_hops.append(entry[0], entry[3]/self.attack_volume_on_victim, entry[1], entry[3])
					to_allies += entry[3]
				elif entry[2] == "original":
					print("YOP")
					original_entry = entry
				elif entry[2] == "unused_original":
					print("NOP")
					new_next_hops.append(entry)
			print(to_allies)
			print(self.attack_volume_on_victim)
			new_next_hops.append([original_entry[0], 1 - to_allies/self.attack_volume_on_victim, original_entry[2], original_entry[3]])
			print(new_next_hops)
			self.next_hops = new_next_hops

	def send_packet(
		self,
		identifier,
		pkt_type,
		src,
		dst,
		last_hop,
		next_hop,
		content
		):
		"""
		This method is used in order to send packets, by making use of the hierachical upper Internet
		object.

		:param pkt: The packet to send

		:type pkt: Packet
		"""
		content["hc"] += 1	
		self.env.process(self.net.relay_packet(identifier, pkt_type, src, dst, last_hop, next_hop, content))

	def process_packet(
		self,
		identifier,
		pkt_type,
		src,
		dst,
		last_hop,
		next_hop,
		content
		):
		"""
		This method's purpose is to handle an incoming packet.

		:param packet: The received packet

		:type packet: Packet
		""" 
		logging.debug(f"[{self.env.now}|{self.asn}] Received a Packet")
		if pkt_type == "attack":
			self.handle_traffic_pkt(identifier, pkt_type, src, dst, last_hop, next_hop, content)

		elif pkt_type == "route_adv":
			self.handle_route_adv_pkt(identifier, pkt_type, src, dst, last_hop, next_hop, content)

	def handle_traffic_pkt(self, identifier, pkt_type, src, dst, last_hop, next_hop, content):
		logging.debug(f"\t[{self.env.now}|{self.asn}] Received a Traffic Packet")
		# if the packet represents attack traffic, decide whether this AS is the target,
		# or whether it has to keep passing its on to its target
		if dst in self.advertised:
			logging.info(f"[{self.env.now} | Node-{self.asn}] Attack Packet with ID {identifier} arrived with magnitutde {content['attack_volume']} Gbps.") # pkt.content['attack_volume']

		else:
			# if this AS is just an intermediary node, change the header of the packet and send it forward
			self.send_packet(identifier, pkt_type, src, dst, self.asn, self.choose_next_hop(), content)


	def handle_route_adv_pkt(self, identifier, pkt_type, src, dst, last_hop, next_hop, content):
		logging.debug(f"\t[{self.env.now}|{self.asn}] Received a Route Adv Packet")
		# route advertisement: check if already receive, if not, broadcast according to specifications
		if not identifier in self.received_router_advs:

			# remeber that we saw this packet
			self.received_router_advs.append(identifier)

			if content["relay_to"] == "next_hop" and self.next_hops: # 2nd condition for victim
				self.send_packet(identifier, pkt_type, src, dst, self.asn, self.choose_next_hop(), content)

			elif content["relay_to"] == "original_next_hop" and self.next_hops: # 2nd condition for victim
				self.send_packet(identifier, pkt_type, src, dst, self.asn, self.choose_original(), content)


			elif content["relay_to"] == "broadcast":
				for AS_neigh in set(self.ebgp_AS_peers) - {last_hop}:
					self.send_packet(identifier, pkt_type, src, dst, self.asn, AS_neigh, content)
			

			if content["protocol"] == "help":
				for indx, value in enumerate(self.next_hops):
					if value[2] == "original":
						self.next_hops[indx][3] = content["attack_volume"]
						self.attack_volume_on_victim = content["attack_volume"]

			elif content["protocol"] == "support" and self.asn != content["as_path_to_victim"][-1]: # to exclude victim # TODO have a variable self.is_victim for these test
				
				self.next_hops = [[node, 0, origin, amount] for node, prob, origin, amount in self.next_hops]
				self.next_hops.append([content["as_path_to_victim"][content["hc"]-2], 1, f"ally_{content['ally']}", content["scrubbing_cap"]])
				# -2 because previous send packet increased
				logging.info(f"I {self.asn}, changed to {content['as_path_to_victim'][content['hc']-2]}." + str(self.next_hops) + "----" + str(content['as_path_to_victim']) + " & " + str(content["hc"])) 
				
			elif content["protocol"] == "attack_path":
				self.on_attack_path = True
				self.split_next_hops()
class Source(AS):
	"""
	A special AS, representing a source of DDoS attack traffic. It inherits
	from the general AS class.
	"""

	def __init__(
		self,
		env: simpy.Environment,
		net,
		asn:int,
		role: str,
		ebgp_AS_peers: list,
		next_hops: list,
		as_path_to_victim: list,
		attack_volume: int,
		attack_freq: int
		):
		"""
		:param env: the simpy environment
		:param net: the internet object
		:param asn: autonomous system number
		:param role: the role of this AS
		:param ebgp_AS_peers: all ASes that are connected to this AS
		:param next_hop: the AS, that is the next hop towards the target IP address, according to BGP
		:param victim_asn: the asn number of the victim, i.e., the destination of the DDoS attack traffic
		:param attack_volume: the magnitude of the attack volume in Gbps
		:param attack_freq: the number of steps between attacks

		:type env: simpy.Environment
		:type net: Internet
		:type asn: int
		:type role: str
		:type ebgp_AS_peers: list
		:type next_hop: int
		:type victim_asn: int
		:type attack_volume: int
		:type attack_freq: int

		"""

		# pass corresponding attributes to AS object to initiate
		super().__init__(
			env,
			net,
			asn,
			role,
			ebgp_AS_peers,
			next_hops,
			as_path_to_victim
			)

		# save the remaining attributes
		self.attack_volume = attack_volume
		self.attack_freq = attack_freq
		self.issued_attack_path = False

	def attack_cycle(self):
		"""
		This function will periodically send out attack toward the victim.
		"""
		logging.info(f"[{self.env.now} | Node-{self.asn}] Starting attack cycle with destination Node-{self.as_path_to_victim[-1]}.")
		
		atk_indx = 0
		while True:
			yield self.env.timeout(self.attack_freq)
			self.send_packet(f"Attack_Packet_{self.asn}_{atk_indx}", "attack", self.asn, self.as_path_to_victim[-1], self.asn, self.choose_next_hop(), {"attack_volume" : self.attack_volume, "hc": 0})
			atk_indx += 1
				
	def handle_route_adv_pkt(self, identifier, pkt_type, src, dst, last_hop, next_hop, content):
			# route advertisement: check if already receive, if not, broadcast according to specifications
			print("YESS")
			if not identifier in self.received_router_advs:
				print("YES?")
				# remeber that we saw this packet
				self.received_router_advs.append(identifier)

				# relay the advertisement as usual
				if content["relay_to"] == "next_hop":
					# TODO, the source of this packet == next hop, dont send since redundant
					self.send_packet(identifier, pkt_type, src, dst, self.asn, self.choose_next_hop(), content)

				elif content["relay_to"] == "broadcast":
					# send it to all neighbors, except the neighbor we received it from
					for asn in set(self.ebgp_AS_peers) - {last_hop}:	
						self.send_packet(identifier, pkt_type, src, dst, self.asn, asn, content)

				if content["protocol"] == "support":
					# do the changes as usual
					self.next_hops = [[node, 0, origin, amount] for node, prob, origin, amount in self.next_hops]
					self.next_hops.append([content["as_path_to_victim"][content["hc"]-2], 1, f"ally_{content['ally']}"])
					# -2 because previous send packet increased
					logging.info(f"I {self.asn}, changed to {content['as_path_to_victim'][content['hc']-2]}." + str(self.next_hops) + "----" + str(content['as_path_to_victim']) + " & " + str(content["hc"])) 
				elif content["protocol"] == "help":
					if not self.issued_attack_path:
						self.send_packet(f"attack_path_from{self.asn}", "route_adv", self.asn, None, self.asn, self.choose_original(), {"relay_to": "original_next_hop", "protocol": "attack_path", "as_path_to_victim": self.as_path_to_victim, "hc": 0})
						self.issued_attack_path = True

class Victim(AS):
	"""
	A special AS, representing a destination and victim of DDoS attack traffic. It inherits
	from the general AS class.
	"""

	def __init__(
		self,
		env: simpy.Environment,
		net,
		asn:int,
		role: str,
		ebgp_AS_peers: list,
		next_hops: list,
		scrubbing_cap: int
		):
		"""
		:param env: the simpy environment
		:param net: the internet object
		:param asn: autonomous system number
		:param role: the role of this AS
		:param ebgp_AS_peers: all ASes that are connected to this AS
		:param next_hop: the AS, that is the next hop towards the target IP address, according to BGP

		:type env: simpy.Environment
		:type net: Internet
		:type asn: int
		:type role: str
		:type ebgp_AS_peers: list
		:type next_hop: int
		"""

		# check that the role is set correctly
		assert role == "victim"

		# pass corresponding attributes to AS object to initiate
		super().__init__(
			env,
			net,
			asn,
			role,
			ebgp_AS_peers,
			next_hops,
			None
			)

		# save the remaining attributes
		self.scrubbing_cap = scrubbing_cap


	def handle_traffic_pkt(self, identifier, pkt_type, src, dst, last_hop, next_hop, content):
		# if the packet represents attack traffic, decide whether this AS is the target,
		# or whether it has to keep passing its on to its target
		if dst in self.advertised:
			logging.info(f"[{self.env.now} | Node-{self.asn}] Attack Packet with ID {identifier} arrived with magnitutde {content['attack_volume']} Gbps.") # pkt.content['attack_volume']
			if not self.help_called:	
				logging.info(f"[{self.env.now} | Node-{self.asn}] Calling for help.")
			
				self.help_called = True

				for AS_neigh in self.ebgp_AS_peers:
					self.send_packet(
						"help",
						"route_adv",
						self.asn,
						None,
						self.asn,
						AS_neigh,
						{"attack_volume": content["attack_volume"], "relay_to": "broadcast", "protocol": "help", "hc": 0}
						)
		else:
			self.send_packet(identifier, pkt_type, src, dst, self.asn, self.choose_next_hop(), content)

class Ally(AS):
	"""
	A special AS, representing an ally to the victim of the DDoS attack traffic. It inherits
	from the general AS class.
	"""

	def __init__(
		self,
		env: simpy.Environment,
		net,
		asn:int,
		role: str,
		ebgp_AS_peers: list,
		next_hop: list,
		as_path_to_victim,
		scrubbing_cap: int
		):
		"""
		:param env: the simpy environment
		:param net: the internet object
		:param asn: autonomous system number
		:param role: the role of this AS
		:param ebgp_AS_peers: all ASes that are connected to this AS
		:param next_hop: the AS, that is the next hop towards the target IP address, according to BGP

		:type env: simpy.Environment
		:type net: Internet
		:type asn: int
		:type role: str
		:type ebgp_AS_peers: list
		:type next_hop: int
		"""

		# check that the role is set correctly
		assert role == "ally"

		# pass corresponding attributes to AS object to initiate
		super().__init__(
			env,
			net,
			asn,
			role,
			ebgp_AS_peers,
			next_hop,
			as_path_to_victim
			)

		# save the remaining attributes
		self.scrubbing_cap = scrubbing_cap

	def handle_route_adv_pkt(self, identifier, pkt_type, src, dst, last_hop, next_hop, content):
		logging.debug(f"\t[{self.env.now}|{self.asn}] Received a ALLLYLALNSDÖLKSAND Route Adv Packet")
		
		# route advertisement: check if already receive, if not, broadcast according to specifications
		if not identifier in self.received_router_advs:

			# remeber that we saw this packet
			self.received_router_advs.append(identifier)

			# relay the advertisement as usual
			if content["relay_to"] == "next_hop":
				self.send_packet(identifier, pkt_type, src, dst, self.asn, self.choose_next_hop(), content)

			elif content["relay_to"] == "original_next_hop":
				self.send_packet(identifier, pkt_type, src, dst, self.asn, self.choose_original(), content)

			elif content["relay_to"] == "broadcast":
				# send it to all neighbors, except the neighbor we received it from
				for asn in set(self.ebgp_AS_peers) - {last_hop}:	
					self.send_packet(identifier, pkt_type, src, dst, self.asn, asn, content)

			# check if it is a call for help, if yes, initiate help process
			if content["protocol"] == "help":
				self.advertised.append(self.as_path_to_victim[-1])
				self.send_packet(f"support_from_{self.asn}", "route_adv", self.asn, None, self.asn, self.choose_next_hop(), {"relay_to": "next_hop", "scrubbing_cap": self.scrubbing_cap, "protocol": "support", "ally": self.asn, "as_path_to_victim": self.as_path_to_victim, "hc": 0})
				self.next_hops = [[n, 0, origin, amount] for n, p, origin, amount in self.next_hops]
