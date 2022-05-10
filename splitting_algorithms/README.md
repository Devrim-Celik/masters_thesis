# Splitting Algorithms

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

---

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

---

## Usage

##### `main.py`
Executing `main.py` will run one experiment in which  
1. a random AS network graph is generated,  
2. a victim, a DDoS source, and a set of allies is randomly selected, and  
3. the graph is modified such that all allies are reachable from the source, with the minimal amount of changes.  
To execute, simpy run
```
$ python3 main.py [--mode={"central_controller_complete", "central_controller_greedy", "decentralized", "bgp"}, default="central_controller_complete"] [--nr_ASes=NR_ASES, default=500] [--nr_allies=NR_ALLIES, default=4] [--attack_volume=ATTACK_VOLUME, default=1000] [--ally_scrubbing_capabilities=ALLY_SCRUBBING_CAPABILITIES, default=[150, 300, 40, 120]] [--verbose_enabled]
```
where  
- `mode` (str): determines the type of algorithm to execute
- `nr_ASes` (int): determines the number of ASes in the generated random graph
- `nr_allies` (int): determines the number of allies
- `attack_volume` (int): determine the attack volume of the DDoS attack in Gbps
- `ally_scrubbing_capabilities` (list): determines the scrubbing capabilities of the allies in Gbps
- `verbose_enabled`: whether to print information about saved and loaded files

** Example **
```
$ python3 main.py --mode central_controller_greedy --nr_ASes=780 --nr_allies 3 --attack_volume 500 --ally_scrubbing_capabilities 100 50 110 --verbose_enabled
```

##### `algorithms_comparison.py`
Executing `algorithms_comparison.py` will run one experiment in which  
1. multiple random graphs are generated with different amount of allies,  
2. each available algorithm is tested multiple times on these different setups, and  
3. the associated costs for the proposed modifications to the graph is saved, and displayed in a figure.  
To execute, simpy run
```
$ python3 algorithms_comparison.py [--nr_ASes=NR_ASES, default=500] [--max_allies=MAX_ALLIES, default=7] [--nr_executions=NR_EXECUTIONS, default=3] [--verbose_enabled]
```
where
- `nr_ASes` (int): determines the number of ASes in the generated random graphs
- `max_allies` (int): determines the number of the maximum amount of allies used in scenarios
- `nr_executions` (int): determine the number of times each scenario is tested on, in order to obtain a variance measure for the associated costs
- `verbose_enabled`: whether to print information about saved and loaded files

**Example**
```
$ python3 algorithms_comparison.py --nr_ASes=780 --max_allies 6 --nr_executions 4 --verbose_enabled
```

---

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