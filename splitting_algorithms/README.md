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

#### DESIRED OUTCOME
A new graph `G' = (V, E')` where all edges `E'` are either in `E` or where their reversed directions are in `E'`, such that
	- one is able to reach all allies and the victim, when starting from `adv` by reversing some of the edges and deciding on the propotion of splits for nodes that have multiple outward pointing edges
	- the difference between `E` and `E'` is minimized
	- the paths towards the allies is as short as possible

## Structure of Directory
- `main.py`: randomly generate an input setup and applies one of the algorithms
- `algorithms_comparisons`: runs all algorithms on the same graph, for different setups, to compare the costs of the 
	proposed modificiations
- `src/`: contains the source code
	- `auxiliary_functions.py`: contains helper functions for saving/loading data, coloring the network, generating figures, etc... and the cost function
	- `central_controller_function.py`: contains functions related to the central controller algorithm
	- `decentralized_function.py`: contains functions related to the decentralized algorithm
	- `generate_AS_network.py`: contains the code for generating an input graph 
	
- `tests/`: contains files with test files using the `pytest` package
	- `test_algorithms.py`: contains test suites for validating the correctness of the proposed modifications of the algorithms
	- `test_graph._generation.py`: contains test suites for validating the correctness of the initial graph generation function in `generate_AS_network.py`


## Testing
After having installed the `pytest` package through
```
$ pip3 install pytest
```
simply change directory to `tests` and execute
```
$ pytest --mode [ALGORITHM_TYPE]
```
to run all tests on the supplied algorithm type, where `ALGORITHM_TYPE` is either
	- `central_controller_complete`,
	- `central_controller_greedy`, or
	- `decentralized`.
If no `mode` is supplied, the default mode is `central_controller_complete`.