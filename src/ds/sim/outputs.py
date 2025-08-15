from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import json
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
plt.style.use("seaborn-v0_8-darkgrid")


def write_outputs(results: Dict[str, Any], out_dir: Path) -> None:
	out_dir.mkdir(parents=True, exist_ok=True)
	fig_dir = out_dir / "figs"
	fig_dir.mkdir(parents=True, exist_ok=True)
	# Write timeseries
	ts: pd.DataFrame = results["timeseries"]
	ts.to_csv(out_dir / "timeseries.csv", index=False)
	# Optional parquet outputs if pyarrow/fastparquet available
	try:
		ts.to_parquet(out_dir / "timeseries.parquet", index=False)
	except Exception:
		pass
	# Events
	events_df = pd.DataFrame(results["events"]) if results.get("events") else pd.DataFrame(columns=["type"]) 
	events_df.to_csv(out_dir / "events.csv", index=False)
	try:
		events_df.to_parquet(out_dir / "events.parquet", index=False)
	except Exception:
		pass
	with (out_dir / "summary.json").open("w", encoding="utf-8") as f:
		json.dump(results["summary"], f, indent=2)
	# Write parameter docs/values for interpretability if present
	if "parameters" in results:
		with (out_dir / "parameters.json").open("w", encoding="utf-8") as f:
			json.dump(results["parameters"], f, indent=2)
	# Per-band CSV summary if available
	if "bands" in results.get("summary", {}):
		bands = results["summary"]["bands"] or []
		if bands:
			pd.DataFrame(bands).to_csv(out_dir / "band_summary.csv", index=False)
	# Plots
	plt.figure(figsize=(9,4.8))
	plt.plot(ts["day"] / 365.0, ts["cum_area_m2"] / 1e6)
	plt.xlabel("Years")
	plt.ylabel("Cumulative area (km^2)")
	plt.grid(True)
	plt.tight_layout()
	plt.savefig(fig_dir / "area_vs_time.png", dpi=150)
	plt.close()

	plt.figure(figsize=(9,4.8))
	plt.plot(ts["day"] / 365.0, ts["power_GW_1AU_equiv"])
	plt.xlabel("Years")
	plt.ylabel("Power (GW @1AU)")
	plt.grid(True)
	plt.tight_layout()
	plt.savefig(fig_dir / "power_vs_time.png", dpi=150)
	plt.close()

	# Optional: per-band area if present
	band_cols = [c for c in ts.columns if c.startswith("band_") and c.endswith("_area_m2")]
	if band_cols:
		plt.figure(figsize=(9,4.8))
		for c in sorted(band_cols):
			plt.plot(ts["day"] / 365.0, ts[c] / 1e6, label=c)
		plt.xlabel("Years")
		plt.ylabel("Band cumulative area (km^2)")
		plt.legend(loc="best", fontsize=8)
		plt.grid(True)
		plt.tight_layout()
		plt.savefig(fig_dir / "band_areas_vs_time.png", dpi=150)
		plt.close()

	# Additional plot: launched area per day (cadence proxy)
	plt.figure(figsize=(9,4.8))
	launch_km2_per_day = ts["launched_m2"] / 1e6
	plt.plot(ts["day"] / 365.0, launch_km2_per_day)
	ax = plt.gca()
	ax.ticklabel_format(style="plain", axis="y", useOffset=False, scilimits=(0,0))
	plt.xlabel("Years")
	plt.ylabel("Launched area per day (km^2/day)")
	plt.grid(True)
	plt.tight_layout()
	plt.savefig(fig_dir / "launch_cadence_vs_time.png", dpi=150)
	plt.close()

	# Additional plot: mass drivers online over time
	if "mass_drivers_online" in ts.columns:
		plt.figure(figsize=(9,4.8))
		x_years = ts["day"] / 365.0
		y_md = ts["mass_drivers_online"].astype(float)
		scale = 1.0
		y_label = "Mass drivers online"
		if y_md.max() >= 1e6:
			scale = 1e6
			y_label += " (millions)"
		plt.step(x_years, y_md / scale, where="post")
		ax = plt.gca()
		ax.ticklabel_format(style="plain", axis="y", useOffset=False, scilimits=(0,0))
		if scale == 1.0:
			ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
		plt.xlabel("Years")
		plt.ylabel(y_label)
		plt.grid(True)
		plt.tight_layout()
		plt.savefig(fig_dir / "mass_drivers_vs_time.png", dpi=150)
		plt.close()


def plot_run(out_dir: Path) -> None:
	ts = pd.read_csv(out_dir / "timeseries.csv")
	plt.figure(figsize=(8,4))
	plt.plot(ts["day"] / 365.0, ts["cum_area_m2"] / 1e9)
	plt.xlabel("Years")
	plt.ylabel("Cumulative area (km^2)")
	plt.grid(True)
	plt.tight_layout()
	plt.show()
