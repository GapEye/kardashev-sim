import math
from ds.physics.constants import SOLAR_CONSTANT_1AU_W_M2
from ds.physics.thermal import equilibrium_temperature_K


def test_solar_constant_positive():
	assert SOLAR_CONSTANT_1AU_W_M2 > 1000


def test_equilibrium_temperature_scaling():
	T1 = equilibrium_temperature_K(alpha=1.0, epsilon=1.0, irradiance_w_m2=1000.0)
	T2 = equilibrium_temperature_K(alpha=1.0, epsilon=1.0, irradiance_w_m2=2000.0)
	assert T2 > T1
	assert math.isclose(T2 / T1, (2.0) ** 0.25, rel_tol=1e-6)
