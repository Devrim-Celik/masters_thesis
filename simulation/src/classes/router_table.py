import numpy as np


# TODO needs to handle empty 
# TODO maybe with pandas??
class RoutingTable():

	__available_origins__ = [
		"original",
		"ally"
	]

	__available_keys__ = { # TODO way to differentiate
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
	}

	__priority_table__ = {
		"unused_original": 1,
		"initial_used_original": 2,
		"split_used_original": 3,
		"splitting_ally": 3,
		"not_splitting_ally": 1
	}

	def __init__(
		self,
		initial_entries: list
		):

		# set table
		self.table = initial_entries
		self.nr_entries = len(self.table)

		if self.nr_entries != 0:
			# set the highest priority
			self.set_highest_priority()

			# check for valid key values
			assert all([set(entry.keys()).issubset(self.__available_keys__) for entry in initial_entries])

			# check values of origin during initialization
			assert all([entry["origin"] == "original" for entry in initial_entries])

			# check there is exactly one with highest priority during initialization
			assert len([entry for entry in self.table if (entry["priority"] == self.highest_priority)]) == 1

		# to save the attack volume once it is known
		self.attack_vol_on_victim = None
		self.increased_origin_priority_status = False
		
		if self.nr_entries != 0:
			self.update()

	def set_AS(self, AS):
		# for logging
		self.AS = AS


	def update(self):
		if self.nr_entries: # TODO victim
			# updating the split percentages

			# if we didnt increase the origin priority yet:
			#	case 1) we dont have any ally entries, the original next hop will get 100%
			#	case 2) we have at least one ally, traffic is split evenly between only the ally paths (TODO, evenly? we could do proportional)
			if (not self.increased_origin_priority_status):
				nr_entries_highest_priority = len([True for entry in self.table if entry["priority"] == self.highest_priority])
				assigned_percentage = 1 / nr_entries_highest_priority
				for entry_indx in range(self.nr_entries):
					if self.table[entry_indx]["priority"] == self.highest_priority:
						self.table[entry_indx]["split_percentage"] = assigned_percentage
			# if we did increase the origin priority:
			#	case 1) there are no allies, again 100% to the victim
			#	case 2) there are allies, which get their share, and the rest goes to victim
			# NOTE: if we have allies, we assume that "self.attack_vol_on_victim" is already set
			else:
				distribute_percentages_to_allies = 0

				# we start off, by removing from the attack volume all allies that have been handled further up the attack path
				attack_vol_on_victim_tmp = self.attack_vol_on_victim
				"""
				for entry_indx in range(self.nr_entries):
					# this IF statement catches all allies that this node is not splitting for
					if (self.table[entry_indx]["priority"] != self.highest_priority) and ("ally" in self.table[entry_indx]["origin"]):
						attack_vol_on_victim_tmp -= self.table[entry_indx]["scrubbing_capabilities"]
				"""
				for entry_indx in range(self.nr_entries):
					# this IF statement catches all allies that this node is splitting for
					if (self.table[entry_indx]["priority"] == self.highest_priority) and ("ally" in self.table[entry_indx]["origin"]):
						self.table[entry_indx]["split_percentage"] = self.table[entry_indx]["scrubbing_capabilities"] / self.attack_vol_on_victim
						distribute_percentages_to_allies += self.table[entry_indx]["scrubbing_capabilities"] / self.attack_vol_on_victim
					# this IF statement catches the original next hop
					elif (self.table[entry_indx]["priority"] == self.highest_priority) and (self.table[entry_indx]["origin"] == "original"):
						# save its index, since its percentage is set at the end
						original_next_hop_entry_indx = entry_indx

				# at the end, after all allies got there share, distribute the remaining percentage to the original next hop
				self.table[original_next_hop_entry_indx]["split_percentage"] = 1 - distribute_percentages_to_allies

			# TODO a case where percentages are reset? maybe handled by first if?


	def set_highest_priority(self):
		if self.nr_entries: # TODO to avoid victim? maybe more elegant way
			self.highest_priority = max([entry["priority"] for entry in self.table])
			self.highest_original_priority = max([entry["priority"] for entry in self.table])


	def determine_next_hops(self, dst):
		# returns a list of next hops with splits
		return [(entry["next_hop"], entry["split_percentage"]) for entry in self.table if (entry["priority"] == self.highest_priority)]

	def determine_highest_original(self):
		return [entry["next_hop"] for entry in self.table if (entry["origin"] == "original") & (entry["priority"] == self.highest_original_priority)]

	def add_entry(self, entry: dict):
		# check correctness of keys
		assert set(entry.keys()).issubset(self.__available_keys__)
		self.table.append(entry)
		self.nr_entries = len(self.table)
		self.set_highest_priority()
		self.update()

	def remove_all_allies(self):
		self.table = [entry for entry in self.table if entry["origin"] != "ally"]
		self.nr_entries = len(self.table)
		self.set_highest_priority()
		self.update()

	def update_attack_volume(self, attack_volume):
		self.attack_vol_on_victim = attack_volume

	def reduce_allies_based_on_last_hop(self, last_hop):
		for entry_indx in range(self.nr_entries):
			if (self.table[entry_indx]["origin"] == "ally") or (self.table[entry_indx]["recvd_from"] == last_hop):
				self.table[entry_indx]["priority"] = self.__priority_table__["not_splitting_ally"]
		self.set_highest_priority()
		self.update()

	def increase_original_priority(self):
		for entry_indx in range(self.nr_entries):
			if self.table[entry_indx]["priority"] == self.__priority_table__["initial_used_original"]:
				self.table[entry_indx]["priority"] = self.__priority_table__["split_used_original"]
		self.increased_origin_priority_status = True
		self.set_highest_priority()
		self.update()
