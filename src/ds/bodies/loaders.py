from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any
from .bodies_schema import BodiesFile


def load_json(path: str | Path) -> Dict[str, Any]:
	p = Path(path)
	with p.open("r", encoding="utf-8") as f:
		return json.load(f)


def load_bodies(path: str | Path) -> BodiesFile:
	data = load_json(path)
	return BodiesFile(**data)
