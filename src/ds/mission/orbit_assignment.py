from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
from ..physics.constants import AU_M


@dataclass
class OrbitBand:
	amin_AU: float
	amax_AU: float


def assign_orbits_uniform(num: int, band: OrbitBand) -> List[float]:
	if num <= 0:
		return []
	return list(np.linspace(band.amin_AU, band.amax_AU, num).tolist())


def optical_depth(area_total_m2: float, at_AU: float) -> float:
	sphere_area = 4.0 * np.pi * (at_AU ** 2) * (AU_M ** 2)
	return area_total_m2 / sphere_area
