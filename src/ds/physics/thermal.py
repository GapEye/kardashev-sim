from __future__ import annotations
from typing import Tuple
from .constants import SIGMA_SB


def equilibrium_temperature_K(alpha: float, epsilon: float, irradiance_w_m2: float, view_factor: float = 1.0) -> float:
	q_abs = alpha * irradiance_w_m2 * view_factor
	if epsilon <= 0:
		raise ValueError("Emissivity must be > 0")
	T4 = q_abs / (epsilon * SIGMA_SB)
	return T4 ** 0.25


def pv_efficiency_derated(eff_1au: float, temp_coeff_per_K: float, T_cell_K: float, T_ref_K: float = 298.15) -> float:
	return max(0.0, eff_1au * (1.0 + temp_coeff_per_K * (T_cell_K - T_ref_K)))
