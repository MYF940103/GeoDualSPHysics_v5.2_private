"""Remeasure three GPU releases on the same C02 seed, balancing all six launch orders."""
import argparse
import csv
import itertools
import json
import shutil
import statistics
import subprocess
from datetime import datetime
from pathlib import Path

import psutil

from gpu_timing import performance_core
from regression import BASE, execute, require


def run_block(order, index, steps, suffix):
    records = {}
    reference = None
    for version in order:
        record = execute(version, "gpu", "column2", index, suffix, steps)
        parts = sorted((Path(record["command"][-5]) / "data").glob("Part_????.bi4"))
        wanted_frames = {48: 2, 192: 3, 384: 5}[steps]
        require(len(parts) == record["parts"] == wanted_frames, "Unexpected BI4 frame count")
        contents = {p.name: p.read_bytes() for p in parts}
        if reference is None:
            reference = contents
        else:
            require(contents == reference, "Native PART bytes differ within the block")
        records[version] = record
    return records


def summarize(blocks, versions):
    results = {}
    for a, b in itertools.combinations(versions, 2):
        metrics = {}
        for field in ("loop_s", "wall_s"):
            ratios = [r[b][field] / r[a][field] for r in blocks]
            metrics[field] = {"paired_ratios": ratios, "median_ratio": statistics.median(ratios)}
        results[f"{b}/{a}"] = metrics
    return results


def sample_run_states(blocks, samples):
    for block in blocks:
        for record in block.values():
            start = datetime.fromisoformat(record["start_utc"])
            end = datetime.fromisoformat(record["end_utc"])
            inside = [s for t, s in samples if start <= t <= end]
            require(inside, "No device telemetry sample during program execution")
            clocks = [int(s["clocks.current.graphics"]) for s in inside]
            record["device_samples"] = {
                "count": len(inside),
                "clock_MHz_min_median_max": [min(clocks), statistics.median(clocks), max(clocks)],
                "pstates": sorted({s["pstate"] for s in inside}),
                "median_utilization_pct": statistics.median(int(s["utilization.gpu"]) for s in inside),
            }


def benchmark(mode, versions, tag):
    steps = 384 if mode == "default" else 192
    output = BASE / f"{tag}_gpu_{mode}.json"
    telemetry = output.with_suffix(".csv")
    require(not output.exists() and not telemetry.exists(), f"Use a fresh tag for {mode}")
    process = psutil.Process()
    original = process.cpu_affinity()
    core, classes = performance_core(original)
    fields = ["timestamp", "pstate", "clocks.current.graphics", "clocks.current.memory",
              "power.draw", "utilization.gpu"]
    smi = shutil.which("nvidia-smi")
    require(smi, "NVIDIA telemetry is required")
    command = [smi, "-i", "0", "--query-gpu=" + ",".join(fields), "--format=csv,noheader,nounits", "-l", "1"]
    warmup = None
    with telemetry.open("xb", buffering=0) as stream:
        stream.write((",".join(fields) + "\n").encode())
        sampler = subprocess.Popen(command, stdout=stream, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            # Leave the sampler away from the core reserved for the pinned host thread.
            alternatives = [n for n in original if n != core]
            if alternatives:
                psutil.Process(sampler.pid).cpu_affinity([alternatives[-1]])
            if mode == "pinned":
                process.cpu_affinity([core])
                warmup = run_block(versions, 0, 48, f"_{tag}_warm48")
            orders = list(itertools.permutations(versions))
            # Alternate cyclic and reverse-cyclic orders in time; each position and
            # ordered pair of consecutive programs occurs equally often within blocks.
            order_indexes = (0, 5, 3, 1, 4, 2)
            blocks = [run_block(orders[j], i, steps, f"_{tag}_{mode}") for i, j in enumerate(order_indexes)]
            affinity = process.cpu_affinity()
        finally:
            process.cpu_affinity(original)
            sampler.terminate()
            sampler.wait(timeout=10)
    with telemetry.open(encoding="utf-8") as stream:
        # nvidia-smi reports local wall time; run receipts record aware UTC timestamps.
        samples = [(datetime.strptime(row["timestamp"], "%Y/%m/%d %H:%M:%S.%f").astimezone(), row)
                   for row in csv.DictReader(stream, skipinitialspace=True)]
    require(samples, "No GPU telemetry")
    sample_run_states(blocks, samples)
    versions_median = {v: {key: statistics.median(block[v][key] for block in blocks)
                           for key in ("loop_s", "wall_s")} for v in versions}
    result = dict(mode=mode, steps=steps, host_affinity=affinity, cpu_efficiency_classes=classes,
                  versions=versions, warmup=warmup, blocks=blocks, version_medians=versions_median,
                  comparisons=summarize(blocks, versions), native_parts_byte_exact_within_each_block=True,
                  telemetry=telemetry.name, telemetry_cmd=command, telemetry_samples=len(samples))
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(output.name, versions_median, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Directory with the merged GPU Release program")
    parser.add_argument("--tag", required=True, help="Fresh run tag")
    parser.add_argument("--mode", choices=("default", "pinned", "both"), default="both")
    args = parser.parse_args()
    versions = ["old", "validated", args.version]
    require(len(set(versions)) == 3, "Three distinct program versions are required")
    for mode in (("default", "pinned") if args.mode == "both" else (args.mode,)):
        benchmark(mode, versions, args.tag)
