import argparse
import os
from pathlib import Path
from .config import load_yaml_config, set_seed
from .sim.scenarios import build_scenario
from .sim.engine import run_simulation
from .sim.outputs import write_outputs, plot_run
import json
from tqdm import tqdm


def main() -> None:
	parser = argparse.ArgumentParser(prog="ds.cli", description="Dyson Swarm Simulation CLI")
	sub = parser.add_subparsers(dest="cmd", required=True)

	p_run = sub.add_parser("run", help="Run a scenario")
	p_run.add_argument("--scenario", required=True, type=str)
	p_run.add_argument("--out", required=True, type=str)
	p_run.add_argument("--mc", type=int, default=1)

	p_plot = sub.add_parser("plot", help="Plot a prior run")
	p_plot.add_argument("--run", required=True, type=str)

	p_sweep = sub.add_parser("sweep", help="Parameter sweep")
	p_sweep.add_argument("--scenario", required=True, type=str)
	p_sweep.add_argument("--out", required=True, type=str)
	p_sweep.add_argument("--param", required=True, type=str, help="key=min:max:step e.g. production.uptime_fraction=0.7:0.95:0.05")

	args = parser.parse_args()

	if args.cmd == "run":
		cfg = load_yaml_config(args.scenario)
		if args.mc <= 1:
			set_seed(cfg.get("seed", 0))
			scenario = build_scenario(cfg)
			results = run_simulation(scenario)
			write_outputs(results, Path(args.out))
			print(json.dumps(results["summary"], indent=2))
		else:
			base = Path(args.out)
			base.mkdir(parents=True, exist_ok=True)
			summaries = []
			for i in tqdm(range(args.mc), desc="MC runs"):
				cfg_i = dict(cfg)
				cfg_i["seed"] = int(cfg.get("seed", 0)) + i
				set_seed(cfg_i["seed"])
				scenario = build_scenario(cfg_i)
				out_i = base / f"replicate_{i:03d}"
				results = run_simulation(scenario)
				write_outputs(results, out_i)
				summaries.append(results["summary"]) 
			print(json.dumps({"mc": args.mc, "summaries": summaries}, indent=2))
	elif args.cmd == "plot":
		plot_run(Path(args.run))
	elif args.cmd == "sweep":
		cfg = load_yaml_config(args.scenario)
		key, rng = args.param.split("=")
		min_v, max_v, step_v = map(float, rng.split(":"))
		vals = []
		v = min_v
		while v <= max_v + 1e-12:
			vals.append(v)
			v += step_v
		base_out = Path(args.out)
		base_out.mkdir(parents=True, exist_ok=True)
		summaries = []
		for val in vals:
			d = cfg
			# nested set by dotted key
			keys = key.split(".")
			target = d
			for k in keys[:-1]:
				target = target.setdefault(k, {})
			target[keys[-1]] = val
			set_seed(d.get("seed", 0))
			scenario = build_scenario(d)
			out_dir = base_out / f"{key.replace('.', '_')}_{val:.3f}"
			results = run_simulation(scenario)
			write_outputs(results, out_dir)
			summaries.append(results["summary"]) 
		print(json.dumps({"sweep_param": key, "values": vals, "summaries": summaries}, indent=2))

if __name__ == "__main__":
	main()
