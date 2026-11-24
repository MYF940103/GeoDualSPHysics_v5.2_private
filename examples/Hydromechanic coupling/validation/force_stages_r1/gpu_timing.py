"""Warm GPU timing on one Windows performance core with 1 Hz NVIDIA telemetry."""
import argparse
import csv
import ctypes as ct
import json
from pathlib import Path
import shutil
import statistics
import subprocess

import psutil

from regression import BASE, execute, require


def performance_core(allowed):
    # SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX(RelationProcessorCore), 64-bit group 0.
    kernel = ct.WinDLL("kernel32", use_last_error=True)
    size = ct.c_ulong()
    kernel.GetLogicalProcessorInformationEx(0, None, ct.byref(size))
    data = ct.create_string_buffer(size.value)
    if not kernel.GetLogicalProcessorInformationEx(0, data, ct.byref(size)):
        raise ct.WinError(ct.get_last_error())
    buf = data.raw
    offset = 0
    cores = {}
    while offset < len(buf):
        record = buf[offset:]
        length = int.from_bytes(record[4:8], "little")
        require(length >= 48 and offset + length <= len(buf), "Invalid processor-core record")
        efficiency = record[9]
        group_count = int.from_bytes(record[30:32], "little")
        for i in range(group_count):
            affinity = record[32+16*i:48+16*i]
            if int.from_bytes(affinity[8:10], "little") == 0:
                mask = int.from_bytes(affinity[:8], "little")
                for cpu in allowed:
                    if mask & (1 << cpu):
                        cores[cpu] = efficiency
        offset += length
    fast = [cpu for cpu in allowed if cores.get(cpu) == max(cores.values())]
    return (2 if 2 in fast else min(fast)), cores


def trial(versions, index, steps, suffix):
    records = {}
    for version in versions:
        records[version] = execute(version, "gpu", "column2", index, suffix, steps)
    paths = [sorted((Path(record["command"][-5]) / "data").glob("Part_????.bi4"))
             for record in records.values()]
    require(paths[0] and [p.name for p in paths[0]] == [p.name for p in paths[1]], "Saved schedule")
    require(all(a.read_bytes() == b.read_bytes() for a, b in zip(*paths)), "Native PART differs")
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--old", default="old")
    parser.add_argument("--version", default="validated")
    args = parser.parse_args()
    versions = [args.old, args.version]
    output = BASE / f"bench_{args.version}_gpu_pinned192.json"
    telemetry = output.with_suffix(".csv")
    require(not output.exists() and not telemetry.exists(), "Fresh output required")
    process = psutil.Process()
    original = process.cpu_affinity()
    cpu, core_classes = performance_core(original)
    nvidia_smi = shutil.which("nvidia-smi")
    require(nvidia_smi, "NVIDIA telemetry utility unavailable")
    fields = "timestamp,pstate,clocks.current.graphics,clocks.current.memory,power.draw,utilization.gpu"
    cmd = [nvidia_smi, "-i", "0", "--query-gpu=" + fields, "--format=csv,noheader,nounits", "-l", "1"]
    with telemetry.open("xb", buffering=0) as stream:
        stream.write((fields + "\n").encode())
        sampler = subprocess.Popen(cmd, stdout=stream, stderr=subprocess.DEVNULL,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            other = [n for n in original if n != cpu]
            if other:
                psutil.Process(sampler.pid).cpu_affinity([other[-1]])
            process.cpu_affinity([cpu])
            warmup = trial(versions, 0, 48, "_pinnedWarm48")
            pairs = [trial(versions if i % 2 == 0 else list(reversed(versions)), i, 192, "_pinned192")
                     for i in range(4)]
        finally:
            process.cpu_affinity(original)
            sampler.terminate()
            sampler.wait(timeout=10)
    with telemetry.open(encoding="utf8") as stream:
        samples = list(csv.DictReader(stream, skipinitialspace=True))
    require(samples and all(s["pstate"].strip().startswith("P") for s in samples), "GPU telemetry")
    ratio = lambda r, key: r[args.version][key] / r[args.old][key]
    result = dict(backend="gpu", steps=192, warmup_steps=48, paired_parts_byte_exact=True,
                  logical_cpu=cpu, performance_core_classes=core_classes, warmup=warmup, pairs=pairs,
                  median_ratio=statistics.median(ratio(r, "loop_s") for r in pairs),
                  median_wall_ratio=statistics.median(ratio(r, "wall_s") for r in pairs),
                  telemetry_file=telemetry.name, telemetry_command=cmd, telemetry_rows=len(samples),
                  pstates=sorted(set(s["pstate"].strip() for s in samples)))
    with output.open("x", encoding="utf8") as out:
        json.dump(result, out, indent=2)
