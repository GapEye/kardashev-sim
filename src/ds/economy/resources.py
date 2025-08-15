from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Inventory:
	mass_kg: Dict[str, float] = field(default_factory=dict)

	def add(self, name: str, kg: float) -> None:
		self.mass_kg[name] = self.mass_kg.get(name, 0.0) + kg

	def remove(self, name: str, kg: float) -> None:
		avail = self.mass_kg.get(name, 0.0)
		if kg > avail + 1e-9:
			raise ValueError(f"Insufficient {name}: have {avail}, need {kg}")
		self.mass_kg[name] = avail - kg

	def total_mass(self) -> float:
		return sum(self.mass_kg.values())
