# Design Notes

- Hybrid DES/time-step: SimPy environment with daily tick for production/launch cadence; discrete events for failures and maintenance.
- Physics: Analytic irradiance and radiative equilibrium; simplified two-impulse Hohmann for Earth↔Mercury; launch Δv budget from Mercury mass-driver augmented by optional sails/tugs.
- Manufacturing: Process lines with throughput, energy, MTBF/MTTR. Learning curve factor `b` applies to cycle times/throughputs. Replication modeled as periodic creation of new lines based on replication parameters.
- Reliability: Exponential time-to-failure with MTBF, repair with MTTR; availability tracked per line.
- Orbit assignment: Uniformly distributes collectors within semimajor-axis bands; avoids self-shading via simple optical-depth cap.
- Optimization: Simple LP for line counts allocation stubbed via heuristic; sweep support for parameter study.

## Limitations

- No full n-body or high-fidelity SRP perturbations; station-keeping approximated by a fixed propellant fraction.
- Power-beaming modeled only as optional multiplier for available factory power; not a full RF/laser link budget.
- Many constants configurable in `data/*.json` and scenario YAML; defaults are illustrative.
