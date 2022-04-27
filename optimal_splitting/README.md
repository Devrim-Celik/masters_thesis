# Optimal Splitting Algorithm

This directory contains:  	
	1. functions to generate directed, acyclic graphs that resemble the autononmous system network.
	2. an algorithm for defining optimal split.

Regarding the seconds point, the here implemented algorithm tries to solve the folowwing optimization problems:

#### INPUT
We are given 
	- a directed, acyclic graph `G = (V, E)` with (`vic`, `adv`, `ally_1`, ..., `ally_N`) in `V`, where
		- `vic` represents an autonomous system that contains an IP block, that is under attack of a volumetric DDoS attack. Furthermore, this node is the sink of the graph, i.e., starting to traverse the graph from any starting node always ends up at the victim.
		- `adv` represents an autonomous system that contains the source of the DDoS attack traffic.
		- `ally_n` represents a node that declared its willingness to help in the defense against the DDoS attack by offering some of its scrubbing capabilities.
	- the attack volume `attack_vol`
	- the offered scrubbing capabilities for each ally (`capab_ally_1`, `capab_ally_2`, ..., `capab_ally_N`)

#### Desired Outcome
A new graph `G' = (V, E')` where all edges `E'` are either in `E` or where their reversed directions are in `E'`, such that
	- one is able to reach all allies and the victim, when starting from `adv` by reversing some of the edges and deciding on the propotion of splits for nodes that have multiple outward pointing edges
	- the difference between `E` and `E'` is minimized
	- splits for the attack traffic happen as early as possible

## Structure of Directory
- `main.py`: randomly generate an input setup and apply the algorithm
- `src/`: contains the source code
	- `auxiliary_functions.py`: contains helper functions for saving/loading data, coloring the network, generating figures, etc...
	- `generate_AS_network.py`: contains the code for generating an input graph 
	- `split_merge.py`: contains the source code for the optimization algorithm
- `tests/`: contains files with test files using the `pytest` package
	- `test_initial_graph.py`: contains test suites for validating the correctness of the initial graph generation function in `generate_AS_network.py`
	- `test_results.py`: contains test suites for validating the correctness of the result of the optimization algorithm described in `split_merge.py`

## Running Test Suites
After having installed the `pytest` package through
```
$ pip3 install pytest
```
simply change directory to `tests` and execute
```
$ pytest
```