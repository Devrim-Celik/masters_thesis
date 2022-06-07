import numpy as np
import pandas as pd

# TODO needs to handle empty 

class RoutingTable():

	__available_origins__ = [
		"original",
		"ally"
	]

	__available_keys__ = [ # TODO way to differentiate
		"identifier", # TODO what to choose here?
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

	def __init__(
		self,
		env,
		initial_entries: list,
		asn: int,
		logger
		):

		# set table
		self.env = env
		self.table = pd.DataFrame(initial_entries) if len(initial_entries) != 0 else pd.DataFrame(columns = self.__available_keys__)
		self.asn = asn
		self.logger = logger
		self.new_line = "\n"
		self.tab = "\t"
		self.string_first_last_line = "+--+----------+----+--------+-----+---+-----+-------------+-------------+"
		self.string_middle_line = "+" + "-"*(len(self.string_first_last_line)-2) + "+"

		if len(self.table) != 0:
			pass

			# check for valid key values
			#assert all([set(entry.keys()).issubset(self.__available_keys__) for entry in initial_entries])

			# check values of origin during initialization
			#assert all([entry["origin"] == "original" for entry in initial_entries])

			# check there is exactly one with highest priority during initialization
			#assert len([entry for entry in self.table if (entry["priority"] == self.highest_priority)]) == 1

		# to save the attack volume once it is known
		self.attack_vol_on_victim = None
		
		if len(self.table) != 0:
			self.update()

	def __str__(self):
		return self.table.to_markdown()

	def update(self):

		if len(self.table): 

			# start by resetting split percentages
			self.table["split_percentage"] = 0

			# case 1: we do not have any allies (that have a high priority), in which case the original with the highest priority get 100 percent
			if not self.table[self.table["priority"] == self.table["priority"].max()]["origin"].str.contains("ally").any():
				self.table.loc[self.table["priority"] == self.table["priority"].max(), "split_percentage"] = 1.0
			# case 2: we have allies, and they are the only ones with the highest priority, in which case we split proportionally
			elif self.table[self.table["priority"] == self.table["priority"].max()]["origin"].str.contains("ally").all():
				self.table["split_percentage"] = self.table.apply(lambda row: row["scrubbing_capabilities"]/self.table["scrubbing_capabilities"].sum(), axis = 1)
			# case 3: we have allies and an original entry that both should be used; in this case, distribute to the allies
			#			proportionally to the attack volume, and the rest goes to the victim
			else:
				# variables used 
				traffic_amount_already_split_away = self.table[(self.table["origin"].str.contains("ally").any()) & (self.table["priority"] != 3)]["scrubbing_capabilities"].sum()
				traffic_amount_split_away_here = self.table[(self.table["origin"].str.contains("ally").any()) & (self.table["priority"] == 3)]["scrubbing_capabilities"].sum()

				# calculate the amount of arriving traffic, by subracting ally scrubbing capabilities that receive before on the attack path
				incoming_taffic_magnitude = self.attack_vol_on_victim - traffic_amount_already_split_away

				# if the scrubbing capabilities of the allies at this node exceed this, we split the traffic between those allies proportionally, by setting 
				# incoming_taffic_magnitude to the sum of all those allies scrubbing capabilities
				if traffic_amount_split_away_here > incoming_taffic_magnitude:
					incoming_taffic_magnitude = traffic_amount_split_away_here

				# set the allies
				self.table["split_percentage"] = self.table.apply(lambda row: row["scrubbing_capabilities"]/incoming_taffic_magnitude if row["priority"] == 3 else 0, axis = 1)
				# then the highest original entry
				self.table.loc[(self.table["origin"] == "original") & (self.table["priority"] == self.table["priority"].max()), "split_percentage"] = 1.0 - self.table["split_percentage"].sum()
			self.logger.debug(f"[{self.env.now}] Routing Table:\n{self}")	

		# check to see that percentage == 1
		if len(self.table) > 0 and round(self.table["split_percentage"].sum(), 1) != 1.0:
			print(self.env.now, self.asn ,"DOESNT SUM UP TO 1")


	def determine_next_hops(self, dst):
		# returns a list of next hops with splits
		#return list(self.table[["next_hop", "split_percentage"]].itertuples(index = False, name = None))
		# NOTE: in the case, that next_hops is [(21, 0.5), (21, 0.5)], it will split the attack packet into smaller ones, what we do not want
		# instead, we will combine them into [(21, 0.5), (21, 0.5)] with the below:
		return list(self.table[["next_hop", "split_percentage"]].groupby(["next_hop"]).sum().itertuples(index = True, name = None))

	def determine_highest_original(self): 
		if len(self.table):
			return [self.table[self.table["origin"] == "original"].loc[self.table[self.table["origin"] == "original"]["priority"].idxmax()]["next_hop"]]
		else:
			return []

	def add_entry(self, entry: dict):
		self.table = pd.DataFrame(self.table.to_dict('records') + [entry])
		self.update()

	def remove_all_allies(self):
		self.table = self.table[~("ally" in self.table["origin"])]
		self.update()

	def update_attack_volume(self, attack_volume):
		self.attack_vol_on_victim = attack_volume
		self.update()

	def reduce_allies_based_on_last_hop(self, last_hop):
		self.table.loc[("ally" in self.table["origin"]) | (self.table["recvd_from"] == last_hop), "priority"] = self.__priority_table__["not_splitting_ally"]
		self.update()

	def increase_original_priority(self):
		self.table.loc[(self.table["origin"] == "original") & (self.table["priority"] == self.__priority_table__["initial_used_original"]), "priority"] = self.__priority_table__["split_used_original"]
		self.update()

	def decrease_original_priority(self):
		self.table.loc[(self.table["origin"] == "original") & (self.table["priority"] == self.__priority_table__["split_used_original"]), "priority"] = self.__priority_table__["initial_used_original"]
		self.update()

	def reset(self):
		self.table = self.table[self.table["origin"] == "original"]
		# decrease the original priority (and also update included)
		self.decrease_original_priority()
		self.update()