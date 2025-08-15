from __future__ import annotations
from typing import Dict, Any


class MaterialsRegistry:
	def __init__(self, data: Dict[str, Any]) -> None:
		self._data = data

	def get(self, name: str) -> Dict[str, Any]:
		return self._data["materials"][name]
