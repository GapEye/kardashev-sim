from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Reliability:
	mtbf_h: float
	mttr_h: float

	def availability(self) -> float:
		if self.mtbf_h <= 0:
			return 0.0
		return self.mtbf_h / (self.mtbf_h + self.mttr_h)
