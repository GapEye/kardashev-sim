from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Phases:
	phase0_days: int
	phase1_days: int
	phase2_days: int

	def which(self, day: int) -> int:
		if day < self.phase0_days:
			return 0
		elif day < self.phase0_days + self.phase1_days:
			return 1
		else:
			return 2
