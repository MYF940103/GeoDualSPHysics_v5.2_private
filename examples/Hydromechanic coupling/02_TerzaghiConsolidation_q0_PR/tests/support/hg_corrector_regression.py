"""Replay the archived HG-on column regressions after moving the corrector commit."""
import argparse
import csv
import json
from pathlib import Path
import subprocess

from tpi_variable_k import TESTS, check, history_exact, read_with_history
from public_tpi_regression import compare_one


def hg_summary(folder):
    return [line.strip() for line in (folder / "Run.out").read_text(errors="replace").splitlines()
            if line.lstrip().startswith("SoilHourglass:")]


def replay(backend, model, tag):
    stage = TESTS.parents[1] / "validation/force_stages_r1"
    if model == 0:
        control = stage / "runs" / f"column0_{backend}_validated"
        seed = stage / "seeds/column0"
        steps, expected_frames = 8, 8
        original = json.loads((control / "call.json").read_text())
        args = original["command"].copy()
    else:
        archive = TESTS / "outputs" / f"tpi_variable_k_r1_{backend}_column_archive"
        control, seed = archive / "result", archive / "seed"
        steps, expected_frames = 25, 3
        original = json.loads((archive / "call.json").read_text())
        args = original["args"].copy()
    check(original["exit"] == 0 and args[-1] == f"-nsteps:{steps}", "Archived command or exit")
    xml, = seed.glob("*.xml")
    output = TESTS / "outputs" / tag / f"{backend}_model{model}"
    output.mkdir(parents=True, exist_ok=False)
    exe = TESTS.parents[3] / "bin/windows" / (
        "DualSPHysics5.2CPU_win64.exe" if backend == "cpu" else "DualSPHysics5.2_GEO_win64.exe")
    args[0] = str(exe)
    dataopt = args.index("-dirdataout")
    check(Path(args[dataopt-2]).name == xml.stem, "Wrong archived seed")
    args[dataopt-2:dataopt] = [str(xml.with_suffix("")), str(output)]
    with (output / "console.log").open("xb") as log:
        code = subprocess.run(args, cwd=exe.parent, stdout=log, stderr=subprocess.STDOUT).returncode
    (output / "call.json").write_text(json.dumps(dict(args=args, exit=code)), encoding="utf8")
    check(code == 0, str(output / "console.log"))
    with (output / "Run.csv").open(encoding="utf-8-sig", newline="") as f:
        summary, = csv.DictReader(f, delimiter=";")
    check(int(summary["Steps"]) == steps and int(summary["PartsOut"]) == 0, "Step or exclusion count")
    baseline = sorted((control / "data").glob("Part_????.bi4"))
    actual = sorted((output / "data").glob("Part_????.bi4"))
    check(len(actual) == expected_frames and [p.name for p in baseline] == [p.name for p in actual], "Saved frames")
    rows = []
    for part, previous in zip(actual, baseline):
        diff = compare_one(part, previous, model)
        check(diff["marker_ok"] and not diff["different"] and all(diff["clock_exact"].values()), "Native state " + part.name)
        root, meta, arrays, history = read_with_history(part)
        check(meta["Nout"] == 0 and meta["Npok"] == root["CaseNp"] == 1040, "Soil/boundary IDs")
        check(bool(history) == bool(model == 2 and meta["Cpart"]), "TPI history presence")
        check(history_exact(history, read_with_history(previous)[3]), "TPI history " + part.name)
        rows.append(dict(part=part.name, time_s=float(meta["TimeStep"]), signed_dt_s=float(meta["dterror"]),
                         arrays=len(arrays), history=bool(history), exact_file=(part.read_bytes() == previous.read_bytes())))
    hg = hg_summary(output)
    check(hg == hg_summary(control) and len(hg) >= 3 and f"correctorupdates={steps} " in hg[0], "HG summary")
    return dict(model=model, reference=str(control), steps=steps, ids=1040, frames=rows, hourglass=hg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", choices=("cpu", "gpu"))
    parser.add_argument("tag")
    opt = parser.parse_args()
    check(opt.tag.isidentifier(), "Use a simple output tag")
    rows = [replay(opt.backend, m, opt.tag) for m in (0, 2)]
    with (TESTS / "logs" / f"{opt.tag}_{opt.backend}.json").open("x", encoding="utf8") as f:
        json.dump(dict(backend=opt.backend, passed=True, models=rows), f, indent=2)
