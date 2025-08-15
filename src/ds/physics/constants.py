from __future__ import annotations
from dataclasses import dataclass

AU_M = 1.495978707e11
SIGMA_SB = 5.670374419e-8  # W m^-2 K^-4
SOLAR_LUMINOSITY_W = 3.828e26
SOLAR_CONSTANT_1AU_W_M2 = 1361.0
GM_SUN = 1.32712440018e20  # m^3/s^2
GM_EARTH = 3.986004418e14
GM_MERCURY = 2.203186855e13
RADIUS_SUN_M = 6.9634e8

@dataclass(frozen=True)
class BodyOrbit:
	semi_major_axis_m: float
	eccentricity: float = 0.0


def irradiance_w_m2(distance_au: float) -> float:
	return SOLAR_CONSTANT_1AU_W_M2 / (distance_au ** 2)
