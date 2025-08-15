from ds.sim.scenarios import build_scenario
from ds.sim.engine import run_simulation


def test_monotonic_area(tmp_path):
	cfg = {
		"name": "test",
		"horizon_years": 2,
		"production": {"uptime_fraction": 0.85, "learning_curve_b": 0.9},
	}
	scenario = build_scenario(cfg)
	res = run_simulation(scenario)
	ts = res["timeseries"]
	assert (ts["cum_area_m2"].diff().fillna(0) >= -1e-6).all()
	assert (ts["launched_m2"] >= -1e-6).all()
