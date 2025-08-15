from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
from ..physics.orbits import mass_driver_delta_v_from_length
from ..economy.reliability import Reliability


@dataclass
class LaunchSystem:
	name: str
	max_g: float
	cooldown_s: float
	muzzle_delta_v_m_s: float
	reliability: Reliability | None = None

	def cadence_per_day(self) -> float:
		base = max(1.0, 86400.0 / self.cooldown_s)
		avail = self.reliability.availability() if self.reliability else 1.0
		return base * avail


def mercury_mass_driver(cfg: Dict[str, Any]) -> LaunchSystem:
	md = cfg["launchers"]["mercury_mass_driver"]
	rel = None
	if "mtbf_h" in md and "mttr_h" in md:
		rel = Reliability(mtbf_h=float(md.get("mtbf_h", 0)), mttr_h=float(md.get("mttr_h", 0)))
	return LaunchSystem(
		name="mercury_mass_driver",
		max_g=float(md.get("max_g", 30)),
		cooldown_s=float(md.get("cooldown_s", 120)),
		muzzle_delta_v_m_s=float(md.get("muzzle_delta_v_m_s", 4500)),
		reliability=rel,
	)


def solar_thermal_steam_launcher() -> LaunchSystem:
	return LaunchSystem(name="solar_thermal_steam", max_g=10.0, cooldown_s=300.0, muzzle_delta_v_m_s=2500.0)


def electromagnetic_sling() -> LaunchSystem:
	return LaunchSystem(name="em_sling", max_g=20.0, cooldown_s=180.0, muzzle_delta_v_m_s=3200.0)
