"""Run and review the isolated −5° C08 TPI receiver at 2.5 microseconds."""
import argparse
import csv
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np

from c08_tpi_psim5_dt25_build import (
    BUILD, CAPS, CASE, DT, FILTER_STEPS, HOLD, OPEN, OUTPUTS, PROGRAM, RUNTIME_FILES,
    SAVE_STEPS, SOURCE, SOURCE_DT, identity, load, require, save,
)

sys.path.insert(0, str(CASE / "support"))
from c08_psi25_tpi_native import check_state, read_frame
from postprocess_lian_tpi import (
    identities, inspect_output, material_snapshots, plots, read_original_pre, verify_frame, write_csv,
)
from postprocess_lian_release import SOIL_IDS, field_plot, history_plot, measures
from run_lian_tpi import call, now, pre_frame


GROUP = "psim5"
TAG = "c08_tpi_psim5_dt25_r1"
STEM = "CaseLianCollapse_psim5_TPI"
INPUTS = OUTPUTS / (TAG + "_inputs")
ORIGINAL = OUTPUTS / "c08_tpi_formal_inputs_r1" / GROUP
DEFINITION = CASE / "tests/configs/c08_tpi_psim5_dt25_Def.xml"
OUT = {"short": OUTPUTS / (TAG + "_short"), "full": CASE / (STEM + "_dt25_GPU_out")}
FIGURES = CASE / "figures/validation_tpi/psim5_dt25"
RECEIPT = "postprocess_tpi.native.json"


def planned_steps(window):
    return [SOURCE+1, SOURCE+2, OPEN-1, OPEN, *range(OPEN+1, OPEN+9),
            *range(OPEN+SAVE_STEPS, CAPS[window]+1, SAVE_STEPS)]


def receiver_dt(tree):
    for key in ("DtIni", "DtFixed"):
        parameter = tree.find(f'execution/parameters/parameter[@key="{key}"]')
        require(float(parameter.get("value")) == SOURCE_DT, f"Original {key} differs")
        parameter.set("value", "0.0000025")


def prepare():
    retained = load(ORIGINAL / "inputs.json")
    require(retained["source"] == identity(pre_frame(GROUP))
            and retained["definition"] == identity(CASE / (STEM + "_Def.xml"))
            and all(identity(Path(row["path"])) == row for row in retained["files"]),
            "The original same-material source or seed no longer matches the sealed input")
    expected = ET.parse(CASE / (STEM + "_Def.xml"))
    receiver_dt(expected)
    declared = ET.parse(DEFINITION)
    require(ET.tostring(expected.getroot()) == ET.tostring(declared.getroot()),
            "Only the receiver's initial and fixed steps may differ from the formal definition")
    seed = INPUTS / STEM
    receipt = INPUTS / "inputs.json"
    if receipt.is_file():
        prior = load(receipt)
        require(prior["source"] == retained["source"] and prior["definition"] == identity(DEFINITION)
                and prior["original_input"] == identity(ORIGINAL / "inputs.json")
                and all(identity(Path(row["path"])) == row for row in prior["files"]),
                "The retained smaller-step seed changed")
        return seed
    seed_tree = ET.parse((ORIGINAL / STEM).with_suffix(".xml"))
    receiver_dt(seed_tree)
    require(Path(seed_tree.find("execution/special/gravitypreload").get("statefile")).resolve() == pre_frame(GROUP),
            "The prepared seed does not refer to the genuine 5 µs preload")
    INPUTS.mkdir()
    particles = [INPUTS / (STEM + suffix) for suffix in (".bi4", "_Normals.nbi4")]
    for path in particles:
        shutil.copy2(ORIGINAL / path.name, path)
    seed_tree.write(seed.with_suffix(".xml"), encoding="utf8", xml_declaration=True)
    save(receipt, dict(group=GROUP, source=retained["source"], definition=identity(DEFINITION),
                       original_input=identity(ORIGINAL / "inputs.json"),
                       files=[identity(f) for f in (*particles, seed.with_suffix(".xml"))]))
    return seed


def ready_program():
    manifest = load(BUILD / "build.json")
    require(manifest["executable"] == identity(PROGRAM) and manifest["changed_host_objects"] == 2
            and manifest["changed_cuda_objects"] == 0 and manifest["retained_objects"] == 111
            and manifest["abi"]["symbols_equal"] and manifest["abi"]["dependencies_equal"]
            and manifest["source_dt"] == SOURCE_DT and manifest["receiver_dt"] == DT
            and manifest["caps"] == CAPS and manifest["warm_steps"] == HOLD and manifest["beta"] == .04
            and all((BUILD / name).is_file() for name in RUNTIME_FILES),
            "Expected the reviewed isolated 2.5 µs build")
    return PROGRAM


def run(window):
    if window == "full":
        checked_short()
    seed = prepare()
    executable = ready_program()
    folder = OUT[window]
    # Leave all pre-existing partial or completed runs untouched.
    folder.mkdir()
    save(folder / "launch_inputs.json", dict(group=GROUP, window=window,
         build=identity(BUILD / "build.json"), source=identity(pre_frame(GROUP)),
         seed=identity(INPUTS / "inputs.json"), exe=identity(executable), beta=.04,
         source_dt=SOURCE_DT, receiver_dt=DT, cap=CAPS[window], planned_steps=planned_steps(window)))
    args = [executable, "-gpu:0", "-stable", "-mdbc_freeslip:1", seed, folder,
            "-dirdataout", "data", "-svres", f"-nsteps:{CAPS[window]}"]
    call("solver", args, folder, env=dict(os.environ, C08_PRIVATE_BETA="0.04"))


def verify_call(folder, window, steps):
    solver = load(folder / "solver.call.json")
    start = load(folder / "solver.start.json")
    launch = load(folder / "launch_inputs.json")
    seed_receipt = load(INPUTS / "inputs.json")
    require(seed_receipt["definition"] == identity(DEFINITION)
            and seed_receipt["source"] == identity(pre_frame(GROUP))
            and seed_receipt["original_input"] == identity(ORIGINAL / "inputs.json")
            and all(identity(Path(item["path"])) == item for item in seed_receipt["files"]),
            "The generated receiver seed changed during the job")
    expected = (GROUP, window, SOURCE_DT, DT, .04, CAPS[window], steps)
    require(tuple(launch[k] for k in ("group", "window", "source_dt", "receiver_dt", "beta", "cap",
                                      "planned_steps")) == expected
            and launch["build"] == identity(BUILD / "build.json") and launch["source"] == identity(pre_frame(GROUP))
            and launch["seed"] == identity(INPUTS / "inputs.json") and launch["exe"] == identity(ready_program()),
            "The run does not belong to the frozen smaller-step admission")
    require(solver["returncode"] == 0 and all(solver[k] == v for k, v in start.items())
            and solver["executable"] == launch["exe"]
            and solver["argv"] == [str(PROGRAM), "-gpu:0", "-stable", "-mdbc_freeslip:1", str(INPUTS / STEM),
                                  str(folder), "-dirdataout", "data", "-svres", f"-nsteps:{CAPS[window]}"],
            "Successful owned solver receipt required")


def inspect_telemetry(path, cap, pre_time, release_time):
    dt_rows = rounds = filters = release_rows = 0
    minimum = math.inf
    imported = finished = warm = False
    with path.open(encoding="utf8", errors="replace") as stream:
        for line in stream:
            if line.startswith("C08M0Dt "):
                step, phase, fixed, bound, *scales = map(float, line.split()[1:])
                require(step == SOURCE+1+dt_rows//5 and phase == (0,1,0,0,0)[dt_rows%5]
                        and bound >= fixed == DT and len(scales) == 4
                        and all(map(math.isfinite, (bound, *scales))), f"Invalid stage step at {step:g}")
                dt_rows += 1
                minimum = min(minimum, bound)
            elif line.startswith("C08GpuRound "):
                step, round_, filtered = map(int, line.split()[1:])
                require(step == SOURCE+1+rounds//3 and round_ == rounds%3+1
                        and filtered == int(round_==3 and step%FILTER_STEPS==0 and step<=OPEN),
                        f"Invalid pressure round at {step}")
                rounds += 1
                filters += filtered
            elif line.startswith("C08M0Release "):
                _, step, time, retired, soil, fixed, *_ = line.split()
                require((int(step), float(time), int(retired), int(soil), int(fixed))
                        == (OPEN, release_time, 255, 5000, 1805), "Wrong release event or registry")
                release_rows += 1
            elif line.startswith("C08Mature history="):
                cells = dict(column.split("=", 1) for column in line.split()[1:])
                require(not warm and (cells["history"], float(cells["source"]), int(cells["M0_wall_hold"]),
                        float(cells["release"]), float(cells["receiver_dt"]), int(cells["closed_filter_steps"]))
                        == ("cold_actual_p", pre_time, HOLD, release_time, DT, FILTER_STEPS),
                        "Wrong consumer clock or cold history")
                warm = True
            elif "C08Mature imported 7060 fixed 2060 material 5000" in line:
                imported = True
            elif "Finished execution (code=0)" in line:
                finished = True
    require(imported and warm and finished and release_rows == 1 and dt_rows == 5*(cap-SOURCE)
            and rounds == 3*(cap-SOURCE) and filters == 5, "Incomplete phase telemetry or solver completion")
    return dict(dt_checks=dt_rows, min_allowed_dt_s=minimum, pressure_rounds=rounds, pre_shepard_calls=filters)


def checked_short():
    output = OUT["short"]
    result = load(output / RECEIPT)
    steps = planned_steps("short")
    verify_call(output, "short", steps)
    require(result["passed"] is True and result["group"] == GROUP and result["window"] == "short"
            and result["dt_s"] == DT and result["cap"] == CAPS["short"] and result["frames"] == len(steps)
            and result["history"] == identity(output / "smallstep_history.csv")
            and result["inputs"] == identities([Path(item[0]) for item in result["inputs"]]),
            "Independent smaller-step short review is missing or changed")
    prefix = sorted((output / "data").glob("Part_????.bi4"))
    require(len(prefix) == len(steps) and all(str(p) in {row[0] for row in result["inputs"]} for p in prefix),
            "The native short-window file sequence changed")
    return prefix


def history_row(values, reference, top, bottom, part, time, release_time, step, error, fs):
    row, _, _, _, pressure, _ = measures(values, reference, top, bottom, part, time, time-release_time)
    area = values["PoroCurrentVolume"][-len(SOIL_IDS):]
    order = np.argsort(pressure, kind="stable")
    totals = np.cumsum(area[order])
    row.update(completed_step=step, saved_step=step-1, released=int(step>OPEN), signed_dterror_s=float(error),
               p_area_p05_kPa=pressure[order[np.searchsorted(totals, .05*totals[-1])]],
               p_negative_area_pct=100*area[pressure<0].sum()/totals[-1],
               p_below_minus5_area_pct=100*area[pressure<-5].sum()/totals[-1],
               free_surface_count=int(fs.sum()), free_surface_negative_count=int(np.sum(pressure[fs]<0)),
               free_surface_min_kPa=pressure[fs].min(), free_surface_max_kPa=pressure[fs].max())
    return row


def exact_prefix(old, frame):
    old_m, old_a, old_h, old_p = read_frame(old)
    m, a, hist, prev = frame
    keys = ("Step", "TimeStep", "dterror", "dtmin", "dtmax", "SymplecticDtPre")
    hkeys = ("PreviousTime", "SavedTime", "Dt", "CompletedUpdates", "Scheme")
    require(all(np.asarray(old_m[k]).tobytes() == np.asarray(m[k]).tobytes() for k in keys)
            and all(np.asarray(old_h[k]).tobytes() == np.asarray(hist[k]).tobytes() for k in hkeys)
            and all(value.tobytes() == old_a[k].tobytes() for k, value in a.items())
            and prev.tobytes() == old_p.tobytes(), f"Short/full native trajectory mismatch at {old.name}")


def review(window):
    output = OUT[window]
    receipt = output / RECEIPT
    history = output / "smallstep_history.csv"
    require(not receipt.exists() and not history.exists() and not history.with_suffix(".tmp").exists(),
            f"Existing review or partial history at {output}; preserve it")
    steps = planned_steps(window)
    verify_call(output, window, steps)
    prefix = checked_short() if window == "full" else []
    refpath, initial, prem, ref, top, bottom = read_original_pre(GROUP)
    cap = CAPS[window]
    clock = np.cumsum(np.r_[prem["TimeStep"], np.full(cap-SOURCE, DT)])
    release_time = float(clock[HOLD])
    files, saved_run = inspect_output(output, steps, cap, float(clock[-1]))
    sealed = [refpath, initial, output/"Run.csv", output/"Run.out", output/"data/Part_Head.ibi4",
              output/"solver.start.json", output/"solver.call.json", output/"launch_inputs.json", *files]
    bound = identities(sealed)
    stats = inspect_telemetry(output/"Run.out", cap, float(clock[0]), release_time)
    last, adjacent = SOURCE, 0
    prior_p, prior_k = ref["PorePress"][SOIL_IDS], ref["Kplastic"][SOIL_IDS]
    rows = []
    for part, (file, step) in enumerate(zip(files, steps, strict=True), 1):
        frame = read_frame(file)
        m, a, hist, prev = frame
        verify_frame(m, hist, GROUP, step, part, clock, refpath, dt=DT, open_step=OPEN)
        fs = check_state(m, a, ref, prior_k, step>OPEN)
        require(fs.any(), f"No free-surface material in {file.name}")
        if last+1 == step:
            require(prev.tobytes() == prior_p.tobytes(), f"Wrong adjacent pressure history at {file.name}")
            adjacent += 1
        if part <= len(prefix):
            exact_prefix(prefix[part-1], frame)
        rows.append(history_row(a, ref, top, bottom, part, float(m["TimeStep"]), release_time, step, m["dterror"], fs))
        prior_p, prior_k, last = a["PorePress"][-len(SOIL_IDS):], a["Kplastic"][-len(SOIL_IDS):], step
    verify_call(output, window, steps)
    require(adjacent == 11 and identities(sealed) == bound, "Incomplete pressure history or changed originals")
    write_csv(history, rows)
    save(receipt, dict(passed=True, group=GROUP, window=window, inputs=bound, preload=str(refpath), dt_s=DT,
                       source_dt_s=SOURCE_DT, cap=cap, frames=len(rows), source_time_s=float(clock[0]),
                       release_time_s=release_time, end_s=float(clock[-1]), adjacent_history=adjacent,
                       prefix_frames=len(prefix), beta=.04, pressure_surface_policy="PositiveOnlyCap",
                       history=identity(history),
                       physical_acceptance=False, hardware=saved_run["Hardware"], loop_wall_s=float(saved_run["TSimul"]),
                       **stats))
    print(receipt, flush=True)


def publish():
    from postprocess_lian_tpi import export_particles

    output = OUT["full"]
    receipt = load(output / RECEIPT)
    require(receipt["passed"] and receipt["dt_s"] == DT and receipt["cap"] == CAPS["full"]
            and receipt["history"] == identity(output / "smallstep_history.csv")
            and receipt["inputs"] == identities([Path(item[0]) for item in receipt["inputs"]]),
            "Native review missing or inputs changed")
    with (output / "smallstep_history.csv").open(encoding="utf8", newline="") as stream:
        rows = [{k: float(v) for k,v in row.items()} for row in csv.DictReader(stream)]
    for row in rows:
        row["part"] = int(row["part"])
    published = FIGURES / "postprocess.json"
    if published.exists():
        require(load(published) == receipt, "Published figures refer to a different native review")
        return
    FIGURES.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output / "smallstep_history.csv", FIGURES / "history.csv")
    history_plot(FIGURES, GROUP, False, rows)
    snapshots = material_snapshots(GROUP, output, rows, FIGURES)
    field_plot(FIGURES, snapshots, GROUP, False)
    plots(GROUP, rows, FIGURES)
    export_particles(GROUP, output, receipt, dt=DT, open_step=OPEN, planned_steps=planned_steps("full"))
    save(published, receipt)
    print(FIGURES, flush=True)


def own(cli, thread):
    require(cli.is_file() and thread and thread == os.environ.get("CODEX_THREAD_ID"),
            "Owned continuation requires the active Codex thread")
    prefix = CASE / "tests/logs" / TAG
    save(prefix.with_suffix(".owner.json"), dict(owner_pid=os.getpid(), started_utc=now(), thread=thread))
    stage = "solver"
    error = None
    try:
        run("full")
        stage = "native_review"
        review("full")
        stage = "plots"
        publish()
        stage = "completed_pending_physical_review"
    except Exception as exc:
        error = str(exc)
        print(error, file=sys.stderr, flush=True)
    terminal = prefix.with_suffix(".terminal.json")
    save(terminal, dict(stage=stage, error=error, output=str(OUT["full"]), ended_utc=now()))
    message = (f"C08 −5° 2.5 µs 一次正式续办终态：{terminal}。核实实际退出、native和图表。"
               "失败保留全部证据，仅派生失败离线诊断；不重跑、不重发该通知。")
    save(prefix.with_suffix(".queue_attempt.json"), dict(utc=now(), terminal=str(terminal)))
    try:
        rc = subprocess.run([str(cli),"queue","--thread",thread,"--message",message],
                            cwd=CASE, capture_output=True, timeout=45).returncode
        result = dict(returncode=rc)
    except (OSError, subprocess.TimeoutExpired) as exc:
        result = dict(delivery="unknown", error=str(exc))
    save(prefix.with_suffix(".queue_result.json"), result)
    return int(error is not None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run", "review", "publish", "owned-full"))
    parser.add_argument("--window", choices=CAPS, default="short")
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--thread")
    args = parser.parse_args()
    if args.action == "prepare":
        print(prepare())
    elif args.action == "run":
        run(args.window)
    elif args.action == "review":
        review(args.window)
    elif args.action == "publish":
        publish()
    else:
        if not args.cli:
            parser.error("owned-full requires --cli and --thread")
        sys.exit(own(args.cli, args.thread))
