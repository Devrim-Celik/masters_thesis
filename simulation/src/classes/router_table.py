"""
Contains the RoutingTable class.

Author:
	Devrim Celik 08.06.2022
"""

import numpy as np
import pandas as pd


# TODO needs to handle empty
class RoutingTable():
	"""
	This class represents a routing table of a BGP router.

	Just as with a normal routing table, one can append and remove entries from it and ask for the current next
	hop of a destination. It furthermore allows uneuqal cost multipathing, which is calculted and implemented for the
	"priority" attribute of a route: the router multipaths between all entries with the highest priority.

	Generally, within the table, we differentiate between "original" entries (entries added before help call was issued)
	and newly added ones by "allies".


	:param env: simpy environment on which simulation is running
	:param table: contains the routes
	:param asn: the autonomous system number of the AS that this router serves in
	:param logger: a logger
	:param attack_vol_on_victim: the current believe on the attack volume of the DDoS attack on the victim

	:type env: simpy.Environment
	:type table: pd.DataFrame
	:type asn: int
	:type logger: logging.RootLogger
	:type attack_vol_on_victim: float
	"""

	__available_origins__ = [
		"original",
		"ally"
	]

	__available_keys__ = [
		"identifier",
		"next_hop",
		"destination",
		"priority",
		"split_percentage",
		"scrubbing_capabilities",
		"as_path",
		"origin",
		"recvd_from",
		"time_added",
	]

	__priority_table__ = {
		"unused_original": 1,
		"initial_used_original": 2,
		"split_used_original": 3,
		"splitting_ally": 3,
		"not_splitting_ally": 1
	}


	def __init__(self, env, initial_entries, asn, logger):

		# set attributes
		self.env = env
		self.table = pd.DataFrame(initial_entries) if len(initial_entries) != 0 else pd.DataFrame(
			columns=self.__available_keys__
		)
		self.asn = asn
		self.logger = logger
		self.attack_vol_on_victim = None
		# for printing
		self.new_line = "\n"
		self.tab = "\t"
		self.string_first_last_line = "+--+----------+----+--------+-----+---+-----+-------------+-------------+"
		self.string_middle_line = "+" + "-" * (len(self.string_first_last_line) - 2) + "+"

		if len(self.table) != 0:
			self.update()


	def update(self):
		"""
		The key method of the "RoutingTable" class. Using the route entries in
		its "table" attribute, this method determines the used path(s) toward
		the victim, with adequate split percentages when multipathing is
		necessary.
		"""

		if len(self.table):
			# start by resetting split percentages
			self.table["split_percentage"] = 0

			# case 1: we do not have any allies (that have a high priority)
			# in which case the original with the highest priority get
			# 100 percent
			if not self.table[self.table["priority"] == self.table["priority"].max()]["origin"].str.contains("ally").any():
				self.table.loc[self.table["priority"] == self.table["priority"].max(), "split_percentage"] = 1.0
			# case 2: we have allies, and they are the only ones with the
			# highest priority, in which case we split proportionally
			elif self.table[self.table["priority"] == self.table["priority"].max()]["origin"].str.contains("ally").all():
				self.table["split_percentage"] = self.table.apply(
					lambda row: row["scrubbing_capabilities"] / self.table["scrubbing_capabilities"].sum(),
					axis=1
				)
			# case 3: we have allies and an original entry that both
			# should be used; in this case, distribute to the allies
			# proportionally to the attack volume, and the rest goes to
			# the victim
			else:
				# variables used
				traffic_amount_already_split_away = self.table[(self.table["origin"].str.contains("ally").any()) & (self.table["priority"] != 3)]["scrubbing_capabilities"].sum()
				traffic_amount_split_away_here = self.table[(self.table["origin"].str.contains("ally").any()) & (self.table["priority"] == 3)]["scrubbing_capabilities"].sum()

				# calculate the amount of arriving traffic, by subracting
				# ally scrubbing capabilities that receive before on the
				# attack path
				incoming_taffic_magnitude = self.attack_vol_on_victim - traffic_amount_already_split_away

				# if the scrubbing capabilities of the allies at this node
				# exceed this, we split the traffic between those allies
				# proportionally, by setting incoming_taffic_magnitude to the
				# sum of all those allies scrubbing capabilities
				if traffic_amount_split_away_here > incoming_taffic_magnitude:
					incoming_taffic_magnitude = traffic_amount_split_away_here

				# set the allies
				self.table["split_percentage"] = self.table.apply(
					lambda row: row["scrubbing_capabilities"] / incoming_taffic_magnitude if row["priority"] == 3 else 0,
					axis=1
				)
				# then the highest original entry
				self.table.loc[(self.table["origin"] == "original") & (self.table["priority"] == self.table["priority"].max()), "split_percentage"] = 1.0 - self.table["split_percentage"].sum()
			self.logger.debug(f"[{self.env.now}] Routing Table:\n{self}")

		# check to see that percentage is 1.0
		if len(self.table) > 0 and round(self.table["split_percentage"].sum(), 1) != 1.0:
			yield Exception(f"[{self.asn}] Router Entry Percentages do not add up to 1.0")


	def determine_next_hops(self, dst):
		"""
		Returns a list of next hops towards the victim, with probabilities.

		:returns: the list of next hop with percentages
		:rytpe: list[tuple[int, float]]
		"""
		return list(
			self.table[["next_hop", "split_percentage"]].groupby(["next_hop"]).sum().itertuples(
				index=True,
				name=None
			)
		)


	def determine_highest_original(self):
		"""
		Returns the a list containing next hop of the route, that is original
		and has the highest priority of the originals.

		:returns: a list with the "original" next hop with the highest
			probability
		:rtype: list[int]

		"""
		if len(self.table):
			return [self.table[self.table["origin"] == "original"].loc[self.table[self.table["origin"] == "original"]["priority"].idxmax()]["next_hop"]]
		else:
			return []


	def add_entry(self, entry: dict):
		"""
		Add an entry to the table, and afterwards update the routing table
		percentages.

		:param entry: the new entry, need value for keys described
			in "__available_keys__"
		:type entry: dict
		"""
		self.table = pd.DataFrame(self.table.to_dict('records') + [entry])
		self.update()


	def remove_all_allies(self):
		"""
		Removes all entries from the table, that originated from an ally, and
		update the routing table percentages afterwards.
		"""
		self.table = self.table[~("ally" in self.table["origin"])]
		self.update()


	def update_attack_volume(self, attack_volume):
		"""
		Update the current estimation of the attack volume.

		:param attack_volume: the new value for the attack volumeapproximation
		:type attack_volume: float
		"""
		self.attack_vol_on_victim = attack_volume
		self.update()


	def reduce_allies_based_on_asn(self, asn):
		"""
		Given a asn, this function will decrease the priority of all the
		ally entries who were received by this node to
		__priority_table__["not_splitting_ally"].

		:param entry: a asn
		:type entry: int
		"""
		self.table.loc[("ally" in self.table["origin"]) | (self.table["recvd_from"] == asn), "priority"] = self.__priority_table__["not_splitting_ally"]
		self.update()


	def increase_original_priority(self):
		"""
		Increases the priority of the original entry with the priority
		self.__priority_table__["initial_used_original"] to
		__priority_table__["split_used_original"].
		Update the split percentages afterwards
		"""
		self.table.loc[(self.table["origin"] == "original") & (self.table["priority"] == self.__priority_table__["initial_used_original"]), "priority"] = self.__priority_table__["split_used_original"]
		self.update()


	def decrease_original_priority(self):
		"""
		Increases the priority of the original entry with priority
		__priority_table__["split_used_original"] to
		self.__priority_table__["initial_used_original"].
		Update the split percentages afterwards.
		"""
		self.table.loc[(self.table["origin"] == "original") & (self.table["priority"] == self.__priority_table__["split_used_original"]), "priority"] = self.__priority_table__["initial_used_original"]
		self.update()


	def reset(self):
		"""
		Reset the routing table by removing all ally entries and decreasing
		the original priority to __priority_table__["initial_used_original"].
		Update the split percentages afterwards.
		"""
		self.table = self.table[self.table["origin"] == "original"]
		self.decrease_original_priority()
		self.update()


	def __str__(self):
		return self.table.to_markdown()
