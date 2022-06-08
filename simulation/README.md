# DDoS Defense Simulation [Proof of Concept]

This repository contains the code base for conducting simulations into the defense against distributed denials of service attacks by means of distributed defense through traffic redistributions; it serves as part of the final submission towards my Master's thesis.

---
## Files

* `run_simulation.py`: the main function, used to configure, execute and illustrate simulation runs.
* `src/`
	* `auxiliarly_functions.py`: contains various helper functions for data saving/loading and plotting.
	* `graph_generation.py`: responsible for setting up the initial graph on which the simulation will be based on.
	* `classes/`
		* `allyAS.py`: contains the `AllyAS` class, representing ally ASes to the victim.
		* `autonomous_system.py`: contains the `AutonomousSystem` class, representing a standard AS; all other
			special AS classes descend from it.
		* `network.py`: contains the `Internet` class, used to initialize the nodes, relay information between
			them, collect data and it implements the figure generation functions.
		* `sourceAS.py`: contains the `SourceAS` class, representing source ASes of the DDoS attack traffic.
		* `victimAS.py`: contains the `Victim` class, representing the victim AS of the DDoS attack.

---
## Usage
```
$ python3 main.py [--seed, default=random.randint(0, 2**32 - 1)] [--nr_ASes, default=200]  [--nr_allies, default=2] 
	[--simulation_length, default=650] [--propagation_delay, default=3] [--full_attack_volume, default=1000]
	[--attack_frequency, default=1] [--log_path, default="./logs"] [--log_path, default="./figures"]
```

---
## Dependencies
The required `Python3` dependencies can be downloaded through
```
pip3 install -r requirements.txt
```