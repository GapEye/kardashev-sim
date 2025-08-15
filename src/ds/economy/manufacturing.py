from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
from .reliability import Reliability


@dataclass
class Line:
	name: str
	kW: float
	throughput_per_day: float
	unit: str
	reliability: Reliability | None = None

	def effective_throughput(self, uptime_fraction: float, learning_factor: float) -> float:
		avail = self.reliability.availability() if self.reliability else 1.0
		return self.throughput_per_day * uptime_fraction * learning_factor * avail


def build_lines_from_config(nodes: Dict[str, Any]) -> Dict[str, Line]:
	lines: Dict[str, Line] = {}
	for name, cfg in nodes.items():
		kW = float(cfg.get("kW", 0))
		if "throughput_t_per_day" in cfg:
			throughput = float(cfg["throughput_t_per_day"]) * 1000.0
			unit = "kg"
		elif "throughput_m2_per_day" in cfg:
			throughput = float(cfg["throughput_m2_per_day"]) 
			unit = "m2"
		elif "throughput_kg_per_day" in cfg:
			throughput = float(cfg["throughput_kg_per_day"]) 
			unit = "kg"
		else:
			throughput = 0.0
			unit = "unit"
		rel = None
		if "mtbf_h" in cfg and "mttr_h" in cfg:
			rel = Reliability(mtbf_h=float(cfg["mtbf_h"]), mttr_h=float(cfg["mttr_h"]))
		lines[name] = Line(name=name, kW=kW, throughput_per_day=throughput, unit=unit, reliability=rel)
	return lines
