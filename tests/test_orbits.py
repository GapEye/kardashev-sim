from ds.physics.orbits import hohmann_delta_v_between_circular


def test_hohmann_earth_to_mercury_bounds():
	dv1, dv2, total = hohmann_delta_v_between_circular(1.0, 0.387)
	# Known order of magnitude ~ 9-12 km/s
	assert 6000.0 < total < 18000.0
	assert dv1 > 0 and dv2 > 0

