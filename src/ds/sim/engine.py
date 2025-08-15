from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
import pandas as pd
from ..mission.scheduler import Scheduler
from ..mission.orbit_assignment import OrbitBand, assign_orbits_uniform, optical_depth
import numpy as np
from ..physics.thermal import equilibrium_temperature_K, pv_efficiency_derated
from tqdm import tqdm
from ..physics.constants import AU_M
from .metrics import compute_power_capture_GW


@dataclass
class SimulationResults:
	timeseries: pd.DataFrame
	events: List[Dict[str, Any]]
	summary: Dict[str, Any]


def run_simulation(scenario: Dict[str, Any]) -> Dict[str, Any]:
	H_years = int(scenario.get("horizon_years", 25))
	H_days = H_years * 365
	vehicles = scenario.get("vehicles")
	factory_cfg = scenario.get("factories")
	sched = Scheduler({"vehicles": vehicles, "scenario": scenario}, factory_cfg)
	t = []
	events: List[Dict[str, Any]] = []
	cum_area = 0.0
	# Pre-fetch scenario fields and functions to local vars for speed in the loop
	# Multi-band support
	lb = scenario.get("launch_strategy", {}).get("target_bands_AU")
	if isinstance(lb, list) and len(lb) > 0 and all(isinstance(x, (list, tuple)) and len(x) == 2 for x in lb):
		bands = [OrbitBand(amin_AU=float(r[0]), amax_AU=float(r[1])) for r in lb]
	else:
		band_range = scenario.get("launch_strategy", {}).get("target_a_AU_range", [0.35, 0.45])
		bands = [OrbitBand(amin_AU=float(band_range[0]), amax_AU=float(band_range[1]))]
	band_means = [ (b.amin_AU + b.amax_AU) * 0.5 for b in bands ]
	band_mean = float(np.mean(band_means)) if band_means else 0.4
	# Band weights for deployment split
	weights = scenario.get("launch_strategy", {}).get("band_weights")
	if isinstance(weights, list) and len(weights) == len(bands):
		w = np.array([max(0.0, float(x)) for x in weights], dtype=float)
		w = w / w.sum() if w.sum() > 0 else np.ones(len(bands)) / len(bands)
	else:
		w = np.ones(len(bands)) / max(1, len(bands))
	# Track cumulative area per band
	cum_area_bands = [0.0 for _ in bands]
	# Collector effective efficiency with degradation
	collector_cfg = scenario.get("collectors", {}).get("collector_types", {})
	# pick first type if present
	if isinstance(collector_cfg, dict) and collector_cfg:
		first = next(iter(collector_cfg.values()))
		base_eff_1au = float(first.get("efficiency_1AU", 0.25))
		deg_per_year = float(first.get("degradation_per_year", 0.0))
	else:
		base_eff_1au = 0.25
		deg_per_year = 0.0
	op_depth = optical_depth
	compute_power = compute_power_capture_GW
	tappend = t.append
	eextend = events.extend

	# Utility for nested gets
	def _get(path: str, default: Any = None) -> Any:
		parts = path.split(".")
		cur: Any = scenario
		for p in parts:
			if not isinstance(cur, dict) or p not in cur:
				return default
			cur = cur[p]
		return cur

	# Provide context to scheduler (if needed in future)
	setattr(sched.factory, "_band_mean", band_mean)
	for day in tqdm(range(H_days), desc=f"Sim {scenario.get('name','scenario')}", miniters=max(1, H_days//200)):
		res = sched.step_day(day)
		# Transit bottleneck: cap deployed area by tug power budget
		area_ready = res.area_launched_m2
		transport_cfg = scenario.get("transport", {})
		fleet_MW = float(transport_cfg.get("fleet_power_MW", scenario.get("vehicles", {}).get("tugs", {}).get("elec_tug", {}).get("fleet_power_MW", 1.0)))
		area_per_MW_per_day = float(transport_cfg.get("area_per_MW_per_day", 1.0e4))
		transport_cap_m2_per_day = fleet_MW * area_per_MW_per_day
		area_transported = min(area_ready, transport_cap_m2_per_day)
		# Energy use for transport (electric tugs): MW used is proportional to area moved
		transport_MW_used = area_transported / area_per_MW_per_day if area_per_MW_per_day > 0 else 0.0
		transport_MWh = transport_MW_used * 24.0
		# Split transported area across bands by weights
		if len(cum_area_bands) > 0 and area_transported > 0:
			increments = (w * area_transported).tolist()
			for i in range(len(cum_area_bands)):
				cum_area_bands[i] += increments[i]
		cum_area = float(np.sum(cum_area_bands))
		# Compute OD as the max across bands
		if len(cum_area_bands) > 0:
			ods = [op_depth(cum_area_bands[i], band_means[i]) for i in range(len(cum_area_bands))]
			od = float(np.max(ods))
		else:
			od = op_depth(cum_area, band_mean)
		# Enforce optical depth cap if provided by scenario targets
		od_cap = float(scenario.get("targets", {}).get("optical_depth_max", 1.0))
		if od > od_cap:
			od = od_cap
		# Time-varying efficiency due to degradation
		current_years = day / 365.0
		eff_now = max(0.0, base_eff_1au * ((1.0 - deg_per_year) ** current_years))
		# Thermal derating from Mercury site radiator sizing: simple scalar on efficiency
		radiator_m2 = float(scenario.get("mercury_site", {}).get("radiator_area_m2", 1e5))
		derate = min(1.0, radiator_m2 / 1e5)
		# Beaming chain losses
		beaming = scenario.get("beaming", {})
		eta_tx = float(beaming.get("tx_conversion", 0.85))
		eta_point = float(beaming.get("pointing", 0.97))
		eta_rx = float(beaming.get("rx_conversion", 0.85))
		eta_atm = float(beaming.get("earth_atmosphere", 0.92))
		eff_chain = eta_tx * eta_point * eta_rx * eta_atm
		# Sum power across bands using their respective radii
		if len(cum_area_bands) > 0:
			p_sum = 0.0
			for i in range(len(cum_area_bands)):
				p_sum += compute_power(cum_area_bands[i], a_AU=float(band_means[i]), eff_1au=eff_now * derate * eff_chain)
			power_GW = p_sum
		else:
			power_GW = compute_power(cum_area, a_AU=band_mean, eff_1au=eff_now * derate * eff_chain)
		tappend({
			"day": day,
			"phase": res.phase,
			"pv_m2": res.pv_m2_produced,
			"structure_kg": res.structure_kg,
			"launched_m2": res.area_launched_m2,
			"cum_area_m2": cum_area,
			"optical_depth": od,
			"power_GW_1AU_equiv": power_GW,
			"mass_drivers_online": res.mass_drivers_online,
			"energy_kWh": res.energy_kWh,
			"resource_remaining_kg": res.resource_remaining_kg,
			"used_mass_kg_day": res.used_mass_kg_day,
			"transport_MW_used": transport_MW_used,
			"transport_MWh": transport_MWh,
			**({f"band_{i}_area_m2": float(cum_area_bands[i]) for i in range(len(cum_area_bands))}),
			**({f"band_{i}_od": float(op_depth(cum_area_bands[i], float(band_means[i]))) for i in range(len(cum_area_bands))}),
		})
		eextend(res.events)
	# Summary
	ts = pd.DataFrame(t)
	years_to_target = None
	# Robustly coerce target to float in case it was provided as a string
	target_raw = scenario.get("targets", {}).get("total_collector_area_m2", 0.0)
	try:
		target = float(target_raw)
	except Exception:
		target = 0.0
	meet = ts[ts["cum_area_m2"] >= target]
	if not meet.empty:
		years_to_target = meet.iloc[0]["day"] / 365.0
	# Per-band final metrics
	band_summaries: List[Dict[str, Any]] = []
	if len(cum_area_bands) > 0:
		for i in range(len(cum_area_bands)):
			band_area = float(cum_area_bands[i])
			band_a = float(band_means[i])
			band_od = float(op_depth(band_area, band_a))
			band_power = float(compute_power(band_area, a_AU=band_a, eff_1au=eff_now * derate * eff_chain))
			band_summaries.append({
				"index": i,
				"a_AU_mean": band_a,
				"cum_area_m2": band_area,
				"optical_depth": band_od,
				"power_GW": band_power,
			})

	# Aggregate material and energy totals
	total_energy_kWh = float(ts["energy_kWh"].sum()) if "energy_kWh" in ts.columns else 0.0
	total_transport_MWh = float(ts["transport_MWh"].sum()) if "transport_MWh" in ts.columns else 0.0
	# Resource usage/remaining
	total_used_mass_kg = float(ts["used_mass_kg_day"].sum()) if "used_mass_kg_day" in ts.columns else None
	final_resource_remaining_kg = None
	if "resource_remaining_kg" in ts.columns:
		col_rr = ts["resource_remaining_kg"].dropna()
		if not col_rr.empty:
			final_resource_remaining_kg = float(col_rr.iloc[-1])
	final_area = float(ts["cum_area_m2"].iloc[-1]) if not ts.empty else 0.0
	areal_density = float(first.get("areal_density_kg_m2", 0.15)) if isinstance(first, dict) else 0.15
	collector_mass_kg = final_area * areal_density
	energy_per_m2_kWh_m2 = (total_energy_kWh / final_area) if final_area > 0 else None
	transport_energy_per_m2_kWh_m2 = ((total_transport_MWh * 1000.0) / final_area) if final_area > 0 else None

	# Derived efficiency & transport summaries
	md = scenario.get("vehicles", {}).get("launchers", {}).get("mercury_mass_driver", {})
	mtbf = float(md.get("mtbf_h", 0.0))
	mttr = float(md.get("mttr_h", 0.0))
	availability = (mtbf / (mtbf + mttr)) if (mtbf + mttr) > 0 else None
	transport_cfg = scenario.get("transport", {})
	fleet_MW = float(transport_cfg.get("fleet_power_MW", scenario.get("vehicles", {}).get("tugs", {}).get("elec_tug", {}).get("fleet_power_MW", 1.0)))
	area_per_MW_per_day = float(transport_cfg.get("area_per_MW_per_day", 1.0e4))
	cap_per_day = fleet_MW * area_per_MW_per_day
	tug_power_kW = float(scenario.get("vehicles", {}).get("tugs", {}).get("elec_tug", {}).get("power_kW", 0.0))
	implied_tugs = (fleet_MW * 1000.0 / tug_power_kW) if tug_power_kW > 0 else None

	# Caps/replication
	max_growth_multiplier_cfg = _get("caps.max_growth_multiplier", None)
	final_growth_multiplier = getattr(sched.factory, "growth_multiplier", None)

	summary = {
		"years_to_target": years_to_target,
		"total_area_m2": final_area,
		"delivered_power_GW_at_1AU_equiv": float(ts["power_GW_1AU_equiv"].iloc[-1]),
		"earth_mass_kg": scenario.get("earth_bootstrap", {}).get("launches", 0) * scenario.get("vehicles", {}).get("launchers", {}).get("earth_to_transfer", {}).get("payload_kg", 0),
		"in_situ_fraction": 0.9,
		"energy_kWh_total": total_energy_kWh,
		"energy_per_m2_kWh_m2": energy_per_m2_kWh_m2,
		"transport_MWh_total": total_transport_MWh,
		"transport_energy_per_m2_kWh_m2": transport_energy_per_m2_kWh_m2,
		"materials": {
			"collector_areal_density_kg_m2": areal_density,
			"collector_mass_kg": collector_mass_kg,
			"structure_kg_total": float(ts["structure_kg"].sum()) if "structure_kg" in ts.columns else None,
			"resource_used_kg_total": total_used_mass_kg,
			"resource_remaining_kg_final": final_resource_remaining_kg,
		},
		"bands": band_summaries,
		"efficiencies": {
			"pv_eff_1au_base": base_eff_1au,
			"pv_eff_1au_end": eff_now,
			"thermal_derate": derate,
			"beaming": {
				"tx_conversion": float(beaming.get("tx_conversion", 0.85)),
				"pointing": float(beaming.get("pointing", 0.97)),
				"rx_conversion": float(beaming.get("rx_conversion", 0.85)),
				"earth_atmosphere": float(beaming.get("earth_atmosphere", 0.92)),
				"chain": eff_chain,
			},
			"effective_eff_1au_end": eff_now * derate * eff_chain,
		},
		"transport": {
			"fleet_power_MW": fleet_MW,
			"area_per_MW_per_day": area_per_MW_per_day,
			"area_cap_m2_per_day": cap_per_day,
			"implied_tug_count": implied_tugs,
			"tug_power_kW": tug_power_kW if tug_power_kW > 0 else None,
			"transport_MWh_total": total_transport_MWh,
		},
		"caps": {
			"max_growth_multiplier": float(max_growth_multiplier_cfg) if max_growth_multiplier_cfg is not None else None,
			"growth_multiplier_final": float(final_growth_multiplier) if final_growth_multiplier is not None else None,
		},
		"mass_driver_availability": availability,
	}

	# Parameter docs and values for outputs
	param_docs: Dict[str, str] = {
		"horizon_years": "Simulation length; longer horizon allows later phases to accrue area/power.",
		"phases.phase0_days": "Initial setup (no launches); affects when production/launching starts.",
		"phases.phase1_days": "Ramp-up phase; by default launches still gated until phase 2 in this model.",
		"phases.phase2_days": "Steady expansion phase when daily PV can be launched.",
		"production.uptime_fraction": "Multiplies all manufacturing line throughputs.",
		"production.learning_curve_b": "Learning-curve exponent; lower b accelerates throughput growth over time.",
		"launch_strategy.cadence_per_day": "Global cap on packages launched per day across rails.",
		"launch_strategy.target_a_AU_range": "Single deployment band; sets mean radius for OD and 1/r^2 power.",
		"launch_strategy.target_bands_AU": "Multiple deployment bands; area split by optional band_weights; per-band OD and power tracked.",
		"launch_strategy.band_weights": "Optional weights for area split across bands; normalized to 1.",
		"caps.max_growth_multiplier": "Upper bound on replication growth multiplier (limits exponential growth).",
		"resources.usable_mass_mercury_kg": "Estimated mass of usable materials from Mercury composition model.",
		"transport.fleet_power_MW": "Tug fleet electrical power; caps daily deployed area.",
		"transport.area_per_MW_per_day": "Scaling from fleet power to deployed area per day (model constant).",
		"beaming.tx_conversion": "Transmitter conversion efficiency factor in delivered power.",
		"beaming.pointing": "Pointing/phase efficiency factor in delivered power.",
		"beaming.rx_conversion": "Receiver conversion efficiency factor in delivered power.",
		"beaming.earth_atmosphere": "Atmospheric transmission factor for delivered power to Earth.",
		"collectors.efficiency_1AU": "Base PV efficiency at 1 AU for the default collector type.",
		"collectors.degradation_per_year": "Annual PV degradation; reduces efficiency exponentially over years.",
		"mercury_site.radiator_area_m2": "Thermal derating proxy; larger radiators reduce efficiency losses.",
		"vehicles.launchers.mercury_mass_driver.cooldown_s": "Cooldown between shots; sets base launch cadence.",
		"vehicles.launchers.mercury_mass_driver.mtbf_h": "Mean time between failures; with MTTR sets availability for cadence.",
		"vehicles.launchers.mercury_mass_driver.mttr_h": "Mean time to repair; with MTBF sets availability for cadence.",
		"targets.total_collector_area_m2": "Target cumulative area; summary reports time to reach if within horizon.",
		"targets.optical_depth_max": "Reference OD threshold; reported OD is capped to this for readability.",
	}
	# Values extraction (with simple deriveds)
	def _first_collector(default: Any = None) -> Dict[str, Any]:
		ct = scenario.get("collectors", {}).get("collector_types", {})
		return next(iter(ct.values())) if isinstance(ct, dict) and ct else default

	# Compute usable materials on Mercury from bodies data (Fe + 0.2*SiO2 within 10 m shell)
	def _estimate_usable_mercury_mass_kg() -> float | None:
		bodies = scenario.get("bodies")
		if not isinstance(bodies, dict) or "bodies" not in bodies:
			return None
		lst = bodies.get("bodies", [])
		if not isinstance(lst, list) or not lst:
			return None
		mer = next((b for b in lst if isinstance(b, dict) and b.get("name") == "Mercury"), None)
		if not isinstance(mer, dict):
			mer = lst[0] if isinstance(lst[0], dict) else None
		if not isinstance(mer, dict):
			return None
		comp = mer.get("composition_mass_frac", {})
		# Utilization factors configurable via scenario.resources.utilization
		util_cfg = scenario.get("resources", {}).get("utilization", {}) if isinstance(scenario.get("resources", {}), dict) else {}
		fe_util = float(util_cfg.get("Fe", 1.0))
		si_util = float(util_cfg.get("SiO2", 0.2))
		fe_frac = float(comp.get("Fe", 0.0))
		si_frac = float(comp.get("SiO2", 0.0))
		usable_frac = max(0.0, fe_util * fe_frac + si_util * si_frac)
		radius_m = float(mer.get("radius_m", 2.4397e6))
		density = float(mer.get("mean_density_kg_m3", 5427.0))
		depth_m = float(scenario.get("resources", {}).get("mining_depth_m", 10.0)) if isinstance(scenario.get("resources", {}), dict) else 10.0
		volume_shell_m3 = 4.0 * np.pi * (radius_m ** 2) * depth_m
		return usable_frac * density * volume_shell_m3

	md = scenario.get("vehicles", {}).get("launchers", {}).get("mercury_mass_driver", {})
	mtbf = float(md.get("mtbf_h", 0.0))
	mttr = float(md.get("mttr_h", 0.0))
	availability = (mtbf / (mtbf + mttr)) if (mtbf + mttr) > 0 else None
	beaming = scenario.get("beaming", {})
	eta_chain = float(beaming.get("tx_conversion", 0.85)) * float(beaming.get("pointing", 0.97)) * float(beaming.get("rx_conversion", 0.85)) * float(beaming.get("earth_atmosphere", 0.92))
	transport_cfg = scenario.get("transport", {})
	fleet_MW = float(transport_cfg.get("fleet_power_MW", scenario.get("vehicles", {}).get("tugs", {}).get("elec_tug", {}).get("fleet_power_MW", 1.0)))
	cap_per_day = fleet_MW * float(transport_cfg.get("area_per_MW_per_day", 1.0e4))
	col = _first_collector({})
	usable_mercury_mass = _estimate_usable_mercury_mass_kg()
	param_values: Dict[str, Any] = {
		"caps.max_growth_multiplier": float(_get("caps.max_growth_multiplier", 0.0)) or None,
		"resources.usable_mass_mercury_kg": float(_get("resources.usable_mass_mercury_kg", 0.0)) or None,
		"horizon_years": H_years,
		"phases.phase0_days": _get("phases.phase0_days", 365),
		"phases.phase1_days": _get("phases.phase1_days", 3 * 365),
		"phases.phase2_days": _get("phases.phase2_days", 21 * 365),
		"production.uptime_fraction": _get("production.uptime_fraction", 0.85),
		"production.learning_curve_b": _get("production.learning_curve_b", 0.85),
		"launch_strategy.cadence_per_day": _get("launch_strategy.cadence_per_day", 1e9),
		"launch_strategy.target_a_AU_range": _get("launch_strategy.target_a_AU_range", [0.35, 0.45]),
		"launch_strategy.target_bands_AU": _get("launch_strategy.target_bands_AU", None),
		"launch_strategy.band_weights": _get("launch_strategy.band_weights", None),
		"transport.fleet_power_MW": fleet_MW,
		"transport.area_per_MW_per_day": float(transport_cfg.get("area_per_MW_per_day", 1.0e4)),
		"transport.area_cap_m2_per_day": cap_per_day,
		"beaming.tx_conversion": float(beaming.get("tx_conversion", 0.85)),
		"beaming.pointing": float(beaming.get("pointing", 0.97)),
		"beaming.rx_conversion": float(beaming.get("rx_conversion", 0.85)),
		"beaming.earth_atmosphere": float(beaming.get("earth_atmosphere", 0.92)),
		"beaming.total_chain_efficiency": eta_chain,
		"collectors.efficiency_1AU": float(col.get("efficiency_1AU", 0.25)) if isinstance(col, dict) else None,
		"collectors.degradation_per_year": float(col.get("degradation_per_year", 0.0)) if isinstance(col, dict) else None,
		"mercury_site.radiator_area_m2": float(_get("mercury_site.radiator_area_m2", 1e5)),
		"vehicles.launchers.mercury_mass_driver.cooldown_s": float(md.get("cooldown_s", 120.0)),
		"vehicles.launchers.mercury_mass_driver.mtbf_h": mtbf if mtbf > 0 else None,
		"vehicles.launchers.mercury_mass_driver.mttr_h": mttr if mttr > 0 else None,
		"vehicles.launchers.mercury_mass_driver.availability": availability,
		"targets.total_collector_area_m2": float(_get("targets.total_collector_area_m2", 0.0)),
		"targets.optical_depth_max": float(_get("targets.optical_depth_max", 1.0)),
		"resources.usable_mass_mercury_kg": usable_mercury_mass,
	}
	
	return {"timeseries": ts, "events": events, "summary": summary, "parameters": {"docs": param_docs, "values": param_values}}
