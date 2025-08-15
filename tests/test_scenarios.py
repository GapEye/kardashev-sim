from pathlib import Path
from ds.sim.scenarios import build_scenario
from ds.sim.engine import run_simulation


def test_reproducibility_seed():
	cfg = {"name": "seeded", "seed": 123, "horizon_years": 1, "production": {"uptime_fraction": 0.85, "learning_curve_b": 0.85}}
	s1 = build_scenario(cfg)
	s2 = build_scenario(cfg)
	r1 = run_simulation(s1)
	r2 = run_simulation(s2)
	assert r1["summary"]["total_area_m2"] == r2["summary"]["total_area_m2"]
