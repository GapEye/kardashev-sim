from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import yaml
from ..bodies.loaders import load_json


def build_scenario(cfg: Dict[str, Any]) -> Dict[str, Any]:
	root = Path(__file__).resolve().parents[3] # git/


	data_dir = root / "data"
	bodies = load_json(data_dir / "bodies.json")
	materials = load_json(data_dir / "materials.json")
	factories = load_json(data_dir / "factories.json")
	vehicles = load_json(data_dir / "vehicles.json")
	collectors = load_json(data_dir / "collectors.json")
	scenario = dict(cfg)
	scenario.update({
		"bodies": bodies,
		"materials": materials,
		"factories": factories,
		"vehicles": vehicles,
		"collectors": collectors,
	})
	return scenario
