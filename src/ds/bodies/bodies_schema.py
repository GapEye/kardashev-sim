from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class Body(BaseModel):
	name: str
	type: str
	GM_km3_s2: Optional[float] = None
	radius_m: Optional[float] = None
	albedo: Optional[float] = None
	mean_density_kg_m3: Optional[float] = None
	rot_period_hours: Optional[float] = None
	axial_tilt_deg: Optional[float] = None
	orbital_a_AU: Optional[float] = None
	orbital_e: Optional[float] = None
	surface_temp_K_range: Optional[List[float]] = None
	composition_mass_frac: Optional[Dict[str, float]] = None
	resource_availability: Optional[Dict[str, float | Dict[str, float]]] = None
	mining_notes: Optional[str] = None


class BodiesFile(BaseModel):
	bodies: List[Body]
