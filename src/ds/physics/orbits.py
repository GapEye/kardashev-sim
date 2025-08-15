from __future__ import annotations
import math
from typing import Tuple
from .constants import GM_SUN, AU_M


def hohmann_delta_v_between_circular(a1_AU: float, a2_AU: float) -> Tuple[float, float, float]:
	"""Return (dv1, dv2, total) for Hohmann transfer around the Sun.
	Units: AU for inputs; outputs m/s.
	"""
	a1 = a1_AU * AU_M
	a2 = a2_AU * AU_M
	r1 = a1
	r2 = a2
	mu = GM_SUN
	v1 = math.sqrt(mu / r1)
	v2 = math.sqrt(mu / r2)
	a_t = 0.5 * (r1 + r2)
	v_peri = math.sqrt(mu * (2.0 / r1 - 1.0 / a_t))
	v_apo = math.sqrt(mu * (2.0 / r2 - 1.0 / a_t))
	dv1 = abs(v_peri - v1)
	dv2 = abs(v2 - v_apo)
	return dv1, dv2, dv1 + dv2


def mass_driver_delta_v_from_length(max_g: float, rail_length_m: float) -> float:
	"""Δv = sqrt(2 a L), with a = max_g * 9.80665"""
	g0 = 9.80665
	a = max_g * g0
	return math.sqrt(2.0 * a * rail_length_m)
