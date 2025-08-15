from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
from .manufacturing import Line, build_lines_from_config


@dataclass
class ReplicationCfg:
	factory_kit_mass_kg: float
	replication_factor: float
	replication_cycle_days: float



class Factory:
	def __init__(self, nodes_cfg: Dict[str, Any], replication_cfg: Dict[str, Any], *, max_growth_multiplier: float | None = None, resource_limit_kg: float | None = None, collector_areal_density_kg_m2: float = 0.15):
		self.lines: Dict[str, Line] = build_lines_from_config(nodes_cfg)
		self.rep_cfg = ReplicationCfg(
			factory_kit_mass_kg=float(replication_cfg["factory_kit_mass_kg"]),
			replication_factor=float(replication_cfg["replication_factor"]),
			replication_cycle_days=float(replication_cfg["replication_cycle_days"]),
		)
		self.elapsed_days: float = 0.0
		self.growth_multiplier: float = 1.0
		self.max_growth_multiplier: float = float(max_growth_multiplier) if (max_growth_multiplier is not None and max_growth_multiplier > 0) else float("inf")
		# Resource constraint (usable in-situ mass)
		self.resource_limit_kg: float | None = float(resource_limit_kg) if (resource_limit_kg is not None and resource_limit_kg >= 0) else None
		self.resource_used_kg: float = 0.0
		self.collector_areal_density_kg_m2: float = float(collector_areal_density_kg_m2)
		# Launch infrastructure build-out
		md_cfg = nodes_cfg.get("mass_driver_build", {})
		self.md_duration_days: float = float(md_cfg.get("duration_days", 120.0))
		self.md_progress_days: float = 0.0
		self.num_mass_drivers: int = 0

	def tick_day(self, uptime_fraction: float, learning_b: float) -> Dict[str, float]:
		self.elapsed_days += 1.0
		learning_factor = (self.elapsed_days ** (1.0 - learning_b)) if learning_b > 0 else 1.0
		outputs: Dict[str, float] = {"ore_kg": 0.0, "refined_kg": 0.0, "pv_m2": 0.0, "structure_kg": 0.0}
		energy_kWh_total = 0.0
		for name, line in self.lines.items():
			th = line.effective_throughput(uptime_fraction, learning_factor) * self.growth_multiplier
			# Approximate energy consumption scaled by same factors as throughput
			avail = line.reliability.availability() if line.reliability else 1.0
			energy_kWh_total += line.kW * 24.0 * uptime_fraction * learning_factor * avail * self.growth_multiplier
			if name == "regolith_mining":
				outputs["ore_kg"] += th
			elif name == "beneficiation":
				outputs["refined_kg"] += min(th, outputs["ore_kg"]) * 0.75
			elif name == "smelter":
				outputs["refined_kg"] += min(th, outputs["refined_kg"]) * 0.2
			elif name == "pv_line":
				outputs["pv_m2"] += th
			elif name == "reflector_line":
				outputs["pv_m2"] += th * 0.5
			elif name == "structure_line":
				outputs["structure_kg"] += th
		# Apply resource cap on outputs (based on usable mass remaining)
		pv_mass_kg = outputs["pv_m2"] * self.collector_areal_density_kg_m2
		total_mass_needed_kg = pv_mass_kg + outputs["structure_kg"]
		remaining = None if self.resource_limit_kg is None else max(0.0, self.resource_limit_kg - self.resource_used_kg)
		if remaining is not None and total_mass_needed_kg > remaining + 1e-9:
			scale = remaining / total_mass_needed_kg if total_mass_needed_kg > 0 else 0.0
			outputs["pv_m2"] *= scale
			outputs["structure_kg"] *= scale
			pv_mass_kg = outputs["pv_m2"] * self.collector_areal_density_kg_m2
			total_mass_needed_kg = pv_mass_kg + outputs["structure_kg"]
		# Account resource use
		self.resource_used_kg += total_mass_needed_kg
		outputs["resource_remaining_kg"] = (None if self.resource_limit_kg is None else max(0.0, self.resource_limit_kg - self.resource_used_kg))
		outputs["used_mass_kg_day"] = total_mass_needed_kg
		# Replication with cap
		if self.elapsed_days % self.rep_cfg.replication_cycle_days == 0:
			self.growth_multiplier = min(self.growth_multiplier * self.rep_cfg.replication_factor, self.max_growth_multiplier)
		# Mass driver build progress scales with available manufacturing capacity (approx by growth multiplier)
		self.md_progress_days += self.growth_multiplier
		if self.md_progress_days >= self.md_duration_days:
			completed = int(self.md_progress_days // self.md_duration_days)
			self.num_mass_drivers += completed
			self.md_progress_days -= completed * self.md_duration_days
		outputs["energy_kWh"] = energy_kWh_total
		return outputs
