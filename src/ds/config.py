from __future__ import annotations
import yaml
import random
import numpy as np
from pathlib import Path
from typing import Any, Dict


def load_yaml_config(path: str | Path) -> Dict[str, Any]:
	p = Path(path)
	with p.open("r", encoding="utf-8") as f:
		cfg = yaml.safe_load(f)
	return cfg


def set_seed(seed: int) -> None:
	random.seed(seed)
	np.random.seed(seed)
