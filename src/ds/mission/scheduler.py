from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
import numpy as np
from ..physics.constants import AU_M
from ..economy.factories import Factory
from .phases import Phases
from .launch_strategy import mercury_mass_driver, solar_thermal_steam_launcher, electromagnetic_sling


@dataclass
class DayResult:
	day: int
	phase: int
	pv_m2_produced: float
	structure_kg: float
	area_launched_m2: float
	mass_drivers_online: int
	events: List[Dict[str, Any]]
	energy_kWh: float
	resource_remaining_kg: float | None = None
	used_mass_kg_day: float | None = None


class Scheduler:
	def __init__(self, config: Dict[str, Any], factory_cfg: Dict[str, Any]):
		# Scenario-configurable phase durations with sensible defaults
		phases_cfg = config.get("scenario", {}).get("phases", {})
		phase0_days = int(phases_cfg.get("phase0_days", 365))
		phase1_days = int(phases_cfg.get("phase1_days", 3 * 365))
		phase2_days = int(phases_cfg.get("phase2_days", 21 * 365))
		self.phases = Phases(phase0_days=phase0_days, phase1_days=phase1_days, phase2_days=phase2_days)
		# Resource and growth caps from scenario
		scenario = config.get("scenario", {})
		caps = scenario.get("caps", {})
		max_growth = float(caps.get("max_growth_multiplier", float("inf")))
		# Usable materials from Mercury composition
		mercury = scenario.get("bodies", {}).get("bodies", [])[0] if isinstance(scenario.get("bodies", {}), dict) else None
		usable_mass_kg = None
		if isinstance(mercury, dict):
			comp = mercury.get("composition_mass_frac", {})
			# Assume usable: Fe + 0.2*SiO2 (rough proxy for PV structure/silicon fraction)
			fe_frac = float(comp.get("Fe", 0.0))
			si_frac = float(comp.get("SiO2", 0.0))
			usable_frac = fe_frac + 0.2 * si_frac
			# Mining depth slice proxy: 10 m average over planet surface at density
			radius_m = float(mercury.get("radius_m", 2.4397e6))
			density = float(mercury.get("mean_density_kg_m3", 5427.0))
			volume_shell_m3 = 4.0 * 3.141592653589793 * (radius_m ** 2) * 10.0
			usable_mass_kg = usable_frac * density * volume_shell_m3
		# Collector areal density from scenario collectors file (first type)
		collectors = scenario.get("collectors", {})
		col_default = None
		if isinstance(collectors, dict) and "collector_types" in collectors and collectors["collector_types"]:
			col_default = next(iter(collectors["collector_types"].values()))
		areal_density = float(col_default.get("areal_density_kg_m2", 0.15)) if col_default else 0.15
		self.factory = Factory(factory_cfg["nodes"], factory_cfg["replication"], max_growth_multiplier=max_growth, resource_limit_kg=usable_mass_kg, collector_areal_density_kg_m2=areal_density)
		self.launch_primary = mercury_mass_driver(config["vehicles"])
		self.launch_alt1 = solar_thermal_steam_launcher()
		self.launch_alt2 = electromagnetic_sling()
		self.uptime = float(config["scenario"]["production"]["uptime_fraction"]) if "scenario" in config else 0.85
		self.learning_b = float(config.get("scenario", {}).get("production", {}).get("learning_curve_b", 0.85))
		self.target_band = config.get("scenario", {}).get("launch_strategy", {}).get("target_a_AU_range", [0.35, 0.45])
		# Package sizing from collectors data if available; fallback to 5000 m2
		collectors = config.get("scenario", {}).get("collectors", {})
		default_type = None
		if isinstance(collectors, dict) and "collector_types" in collectors:
			# pick the first defined type
			default_type = next(iter(collectors["collector_types"].values()))
		self.package_area_m2 = float(default_type.get("area_m2", 5000.0)) if default_type else 5000.0
		# Scenario global cadence cap (total per day across all rails)
		self.scenario_cadence_cap = float(config.get("scenario", {}).get("launch_strategy", {}).get("cadence_per_day", 1e9))

	def step_day(self, day: int) -> DayResult:
		phase = self.phases.which(day)
		outputs = self.factory.tick_day(self.uptime, self.learning_b)
		pv_m2 = outputs["pv_m2"]
		struct_kg = outputs["structure_kg"]
		energy_kWh = outputs.get("energy_kWh", 0.0)
		resource_remaining_kg = outputs.get("resource_remaining_kg")
		used_mass_kg_day = outputs.get("used_mass_kg_day")
		energy_kWh = outputs.get("energy_kWh", 0.0)
		# Launch allocation heuristic: enabled only when at least one mass driver is built
		cadence_single = self.launch_primary.cadence_per_day()
		num_md = getattr(self.factory, "num_mass_drivers", 0)
		cadence_total = cadence_single * max(0, num_md)
		# Apply global cadence cap from scenario
		cadence_total = min(cadence_total, self.scenario_cadence_cap)
		area_to_launch = pv_m2 * (1.0 if phase >= 2 else 0.0)
		max_launched = cadence_total * self.package_area_m2
		launched = min(area_to_launch, max_launched)
		events: List[Dict[str, Any]] = []
		if launched > 0:
			events.append({"type": "launch", "area_m2": launched, "system": self.launch_primary.name})
		# Build completion events (log weekly to reduce event volume)
		if num_md > 0 and day % 7 == 0:
			events.append({"type": "infrastructure", "mass_drivers_online": num_md})
		return DayResult(day=day, phase=phase, pv_m2_produced=pv_m2, structure_kg=struct_kg, area_launched_m2=launched, mass_drivers_online=num_md, events=events, energy_kWh=energy_kWh, resource_remaining_kg=resource_remaining_kg, used_mass_kg_day=used_mass_kg_day)
