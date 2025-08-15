# Dyson Swarm Construction & Launch Simulation

Plan, simulate, and tune an in-situ industrial build‑out for a Dyson Swarm. This model spans mining and manufacturing on Mercury, self‑replicating factories, mass‑driver launches, transport bottlenecks, multi‑band orbital deployment, beaming losses, thermal derating, reliability/maintenance, resource limits, and optical‑depth targets.

The CLI runs scenarios from YAML, sweeps parameters, and writes CSV/JSON plus plots for rapid iteration.

## Contents
- Overview of the simulation model
- Inputs and scenario schema (parameter reference)
- Outputs and files emitted
- Run and plotting instructions
- Tuning playbook (how to hit targets and diagnose bottlenecks)

---

## Overview

The simulator advances day‑by‑day across mission phases:
- Phase 0: bootstrap and setup (no launch).
- Phase 1: ramp‑up (manufacturing scaling, launch usually gated).
- Phase 2: steady expansion (daily production launched to deployment bands).

At each day the model:
1) Advances factory lines with uptime, learning curves, and availability (MTBF/MTTR).
2) Applies growth via replication (capped by `caps.max_growth_multiplier`).
3) Builds mass drivers as manufacturing capacity accrues.
4) Launches PV area packages subject to cadence limits and phase gate.
5) Constrains deployed area by tug fleet power (transport bottleneck).
6) Splits deployed area across orbital bands and accumulates per‑band OD.
7) Computes delivered power with PV degradation, thermal derating, and beaming chain losses.
8) Tracks resource consumption against usable Mercury materials.

Key abstractions live in:
- `ds/economy/*`: manufacturing lines, reliability, replication.
- `ds/mission/*`: phases, scheduler, launch systems.
- `ds/sim/*`: core loop, metrics, scenario assembly, outputs.
- `data/*`: bodies, factories, vehicles, collectors, scenario YAMLs.

All internal units are SI.

---

## Inputs and Scenario Schema

Scenarios are YAML files under `data/scenarios/`. They overlay the base JSON data in `data/` (bodies, collectors, factories, vehicles). Below is a parameter reference and its modeled effect.

### Mission horizon and phases
- `horizon_years` – total simulated years.
- `phases.phase0_days` – setup (no launch).
- `phases.phase1_days` – ramp‑up (manufacturing scales; default launch gate).
- `phases.phase2_days` – steady expansion (launch enabled).

### Targets and orbital constraints
- `targets.total_collector_area_m2` – area goal; summary reports time‑to‑target if met.
- `targets.optical_depth_max` – reference cap for reported OD.
- `launch_strategy.target_a_AU_range` – single deployment band [amin, amax] AU.
- `launch_strategy.target_bands_AU` – multiple bands, e.g. `[[0.38,0.42],[0.42,0.48],[0.48,0.52]]`.
- `launch_strategy.band_weights` – optional weights (normalized) for area split across bands.

### Production and replication
- `production.uptime_fraction` – multiplies line throughputs.
- `production.learning_curve_b` – learning exponent (lower → faster growth).
- `caps.max_growth_multiplier` – hard ceiling on replication growth.

### Launch systems and transport
- `launch_strategy.cadence_per_day` – global package limit/day.
- `vehicles.launchers.mercury_mass_driver.cooldown_s` – base cadence.
- `vehicles.launchers.mercury_mass_driver.mtbf_h` / `mttr_h` – availability (downtime) for cadence.
- `transport.fleet_power_MW` – tug electrical power budget.
- `transport.area_per_MW_per_day` – conversion from MW to m²/day transported.

### Beaming and thermal derating
- `beaming.tx_conversion`, `pointing`, `rx_conversion`, `earth_atmosphere` – factors multiplied into delivered power.
- `mercury_site.radiator_area_m2` – scalar derating of PV efficiency (proxy for thermal limits).

### Collectors and vehicles
- `collectors.collector_types.*`
  - `area_m2`, `areal_density_kg_m2`, `efficiency_1AU`, `degradation_per_year`, `temp_coeff_per_K`.
- `vehicles.tugs.elec_tug`
  - `power_kW` (per tug), optional `fleet_power_MW` shortcut.

### Resources (Mercury composition)
- `resources.mining_depth_m` – shell depth modeled as extractable.
- `resources.utilization.Fe` – usable fraction of Fe mass fraction.
- `resources.utilization.SiO2` – usable fraction of SiO₂ mass fraction (feeds silicon & structure proxy).

The simulator derives `resources.usable_mass_mercury_kg` from `data/bodies.json` (Mercury’s `composition_mass_frac`, `radius_m`, `mean_density_kg_m3`) and scenario utilization settings.

---

## Outputs

Writing to the chosen `--out` directory:

- `timeseries.csv` – daily table with e.g. `day`, `phase`, `pv_m2`, `structure_kg`, `launched_m2`, `cum_area_m2`, `energy_kWh`, `transport_MWh`, per‑band `band_i_area_m2` and `band_i_od`, etc.
- `events.csv` – sparse event log (launches, infrastructure updates).
- `summary.json` – end‑of‑run metrics, including:
  - Years to target, total area, delivered power at 1 AU equivalent
  - Materials: collector areal density, collector mass, structure mass total, resource mass used and remaining
  - Energy: manufacturing energy total and per‑m², transport energy total and per‑m²
  - Bands: area, OD, power per band
  - Efficiencies: PV base/end, thermal derate, beaming chain
  - Transport: fleet MW, area cap/day, implied tug count
  - Caps: configured replication cap and final growth multiplier (if present)
- `parameters.json` – two sections:
  - `docs`: descriptions of key parameters and effects
  - `values`: effective values used (including derived ones like `resources.usable_mass_mercury_kg`)
- `figs/` – plots: `area_vs_time.png`, `power_vs_time.png`, `launch_cadence_vs_time.png`, `mass_drivers_vs_time.png`, `band_areas_vs_time.png` (if bands enabled)

---

## Run Instructions

Prereqs: Python 3.11+

Install (editable):
```
pip install -e .
```

Run baseline:
```
# From repo root (no install required)
python run.py run --scenario data/scenarios/baseline.yaml --out results/baseline
python run.py plot --run results/baseline
```

Run the advanced K2 scenario:
```
python run.py run --scenario data/scenarios/advanced_k2.yaml --out results/advanced_k2
```

Parameter sweep (example):
```
python run.py sweep \
  --scenario data/scenarios/advanced_k2.yaml \
  --out results/sweep_k2 \
  --param production.uptime_fraction=0.80:0.95:0.03
```

---

## Tuning Playbook

Use these levers to reach targets or diagnose bottlenecks:

### Not reaching area/power target within horizon
- Increase `horizon_years` (if studying asymptotics) or accelerate growth via:
  - Higher `production.uptime_fraction`
  - Lower `production.learning_curve_b`
  - Increase `caps.max_growth_multiplier` (permits more replication growth)
- Ensure transport isn’t capping: raise `transport.fleet_power_MW` or `transport.area_per_MW_per_day`.
- Raise `launch_strategy.cadence_per_day` if cadence‑limited.

### Optical depth or band congestion
- Add bands via `launch_strategy.target_bands_AU` and adjust `band_weights`.
- Widen a band range or shift outward to lower OD (at the cost of 1/r² power).

### Transport bottleneck
- Increase tug fleet power or efficiency (`transport.*`).
- Lower package area per shot (collector `area_m2`) if cadence is strong but transport is not.

### Beaming/thermal losses too high
- Improve `beaming.*` factors.
- Increase `mercury_site.radiator_area_m2` to reduce thermal derating.

### Reliability throttling cadence
- Increase mass‑driver `mtbf_h` or reduce `mttr_h`.
- Increase number of rails indirectly by allowing more replication (higher cap), which speeds infrastructure buildout.

### Resource‑limited production
- Increase `resources.mining_depth_m` or utilization (`resources.utilization.Fe/SiO2`).
- Reduce areal density (`collectors.*.areal_density_kg_m2`) via thinner/lighter designs.
- Monitor `materials.resource_used_kg_total` and `materials.resource_remaining_kg_final` in `summary.json`.

### Reproducibility & performance
- `seed` sets RNG seed.
- Progress bars are fast; large sweeps can be parallelized externally (GNU parallel, job schedulers).

---

## Repository Layout
- `data/` – JSON + YAML inputs (bodies, collectors, factories, vehicles, scenarios)
- `src/ds/` – simulation engine and subsystems
- `tests/` – unit tests for physics and invariants

See `design_notes.md` for modeling notes and limitations.
