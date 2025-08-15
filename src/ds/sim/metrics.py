from __future__ import annotations
import numpy as np
from ..physics.constants import SOLAR_CONSTANT_1AU_W_M2


def compute_power_capture_GW(area_m2: float, a_AU: float, eff_1au: float) -> float:
	irr = SOLAR_CONSTANT_1AU_W_M2 / (a_AU ** 2)
	return (area_m2 * irr * eff_1au) * 1e-9
