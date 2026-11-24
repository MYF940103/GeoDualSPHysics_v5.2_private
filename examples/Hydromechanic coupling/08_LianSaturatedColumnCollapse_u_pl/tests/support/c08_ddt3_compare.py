"""Isolated +2.5-degree DDT3 two-stage test. See --help. Default runs no solver."""
import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

CASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CASE / "support"))
from run_lian_release import BIN, contract, validate_solver, write_record

GROUP = "psi2p5"
TESTS = CASE / "tests"
CONTROL = CASE / "figures/validation_explicit/psi2p5"
TAG = "c08_ddt3_psi2p5"
STEMS = {"preload": TAG + "_pre_r1", "collapse": TAG + "_r1"}
OUT = {stage: TESTS / "outputs" / name for stage, name in STEMS.items()}
FIG = TESTS / "figures" / TAG
METRICS = ("front_x_m", "runout_m", "top_settlement_mm", "bottom_settlement_mm", "mean_settlement_mm",
           "p_min_kPa", "p_max_kPa", "p_mean_kPa", "excess_min_kPa", "excess_max_kPa",
           "excess_mean_kPa", "nearest_min_dp", "nearest_p05_dp", "nearest_below_half_dp",
           "total_zz_min_kPa", "total_zz_max_kPa", "kappa_max", "J_min", "J_max", "speed_max_m_s")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def identity(path):
    stat = path.stat()
    return {"path": str(path.resolve()), "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def definition(stage):
    return TESTS / "configs" / (STEMS[stage] + "_Def.xml")


def check_definitions():
    for stage, suffix in (("preload", "_pre"), ("collapse", "")):
        base = ET.parse(CASE / ("CaseLianCollapse_psi2p5" + suffix + "_Def.xml")).getroot()
        candidate = ET.parse(definition(stage)).getroot()
        setting = candidate.find(".//parameter[@key='DensityDT']")
        require(setting.get("value") == "3" and base.find(".//parameter[@key='DensityDT']").get("value") == "0",
                "Expected the DDT 0/3 pair")
        setting.set("value", "0")
        if stage == "collapse":
            handoff = candidate.find(".//gravitypreload")
            native = OUT["preload"] / "data/Part_1000.bi4"
            require((OUT[stage] / handoff.get("statefile")).resolve() == native.resolve(), "Wrong test source path")
            handoff.set("statefile", base.find(".//gravitypreload").get("statefile"))
        require(ET.tostring(base) == ET.tostring(candidate), f"Additional change in {definition(stage)}")


def invoke(name, args, directory, receipt):
    log = directory / (name + "_console.log")
    with log.open("xb") as stream:
        env = os.environ.copy()
        env["PATH"] = str(BIN) + os.pathsep + env["PATH"]
        child = subprocess.Popen(list(map(str, args)), cwd=CASE, env=env, stdout=stream, stderr=subprocess.STDOUT)
        call = {"argv": list(map(str, args)), "pid": child.pid, "started_utc": now(), "program": identity(Path(args[0])),
                "log": str(log)}
        receipt["calls"].append(call)
        write_record(directory / "provenance.json", receipt)
        rc = child.wait()
    call.update(exitcode=rc, ended_utc=now())
    write_record(directory / "provenance.json", receipt)
    if rc:
        lines = log.read_text(encoding="utf8", errors="replace").splitlines()
        call.update(first_error=next((line for line in lines if line.startswith(("*** Exception", "Error:", "Text:"))), None),
                    last_saved_line=next((line for line in reversed(lines) if re.match(r"^Part_\d+\s", line)), None),
                    last_console_lines=lines[-9:])
        raise RuntimeError(f"{name} exited with code {rc}. See {log}")


def source_qualified():
    receipt = json.loads((OUT["preload"] / "checked.json").read_text())
    source = OUT["preload"] / "data/Part_1000.bi4"
    require(receipt["frames"] == 1001 and receipt["source"] == identity(source), "Certified PRE file has changed")
    return source


def check_runtime(dest, stage):
    validate_solver(dest, stage)
    log = (dest / "Run.out").read_text(errors="replace")
    require('DensityDiffusion="Fourtakas et al 2019 (full)"' in log
            and re.search(r'^\s*DensityDiffusionValue=0\.1(?:0*)\s*$', log, re.M),
            "No runtime evidence of the requested DDT3 coefficient")


def run_stage(stage, solver, gencase):
    dest = OUT[stage]
    prereq = source_qualified() if stage == "collapse" else None
    if stage == "collapse":
        pre = json.loads((OUT["preload"] / "provenance.json").read_text())
        require(pre["solver"] == identity(solver), "Use the same solver for both DDT3 stages")
    if dest.exists():
        old = json.loads((dest / "provenance.json").read_text())
        require(old["state"] == "completed" and old["solver"] == identity(solver)
                and old["definition"] == identity(definition(stage)), f"Existing output requires offline review: {dest}")
        check_runtime(dest, stage)
        return
    solver_id, gen_id = identity(solver), identity(gencase)
    dest.mkdir()  # Exclusive stage claim. A failed or interrupted stage is never launched again here.
    rec = dict(state="started", method="fresh", group=GROUP, stage=stage, started_utc=now(), solver=solver_id,
               gencase=gen_id, definition=identity(definition(stage)), calls=[])
    if prereq:
        rec["preload"] = identity(prereq)
    write_record(dest / "provenance.json", rec)
    try:
        prefix = dest / STEMS[stage]
        invoke("gencase", [gencase, definition(stage).with_suffix(""), prefix, "-save:all"], dest, rec)
        generated = ET.parse(prefix.with_suffix(".xml"))
        require(generated.find(".//parameter[@key='DensityDT']").get("value") == "3", "Generated input lost DensityDT=3")
        if prereq:
            raw = generated.find(".//gravitypreload").get("statefile")
            require((dest / raw).resolve() == prereq.resolve(), "Generated input points to the wrong PRE")
        boundary = "-mdbc_freeslip" if stage == "preload" else "-mdbc_freeslip:1"
        invoke("solver", [solver, "-gpu:0", "-stable", boundary, prefix, dest, "-dirdataout", "data",
                          "-svres", f"-nsteps:{contract(stage)[0]}"], dest, rec)
        rec.update(state="solver_completed", solver_ended_utc=now())
        write_record(dest / "provenance.json", rec)
        check_runtime(dest, stage)
        rec.update(state="completed", completed_utc=now())
    except Exception as exc:
        rec["error"] = str(exc)
        if rec["state"] != "solver_completed":
            rec["state"] = "failed"
        raise
    finally:
        write_record(dest / "provenance.json", rec)


def write_rows(path, rows):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf8", newline="") as stream:
        writer = csv.DictWriter(stream, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def qualify(stage):
    import numpy as np
    import postprocess_lian_release as post
    dest = OUT[stage]
    pre = stage == "preload"
    receipt = json.loads((dest / "provenance.json").read_text())
    require(receipt["state"] in ("solver_completed", "completed") and receipt["calls"][-1]["exitcode"] == 0,
            f"Review solver receipt before using {dest}")
    check_runtime(dest, stage)
    files, runtime = post.inventory(dest, pre)
    refpath = files[0] if pre else source_qualified()
    reference_meta, ref = post.native(refpath)
    figdir = FIG / stage
    figdir.mkdir(parents=True, exist_ok=True)
    signature = {"source": identity(files[-1] if pre else refpath), "frames": len(files),
                 "saved_file_stats": [post.stat_id(p) for p in files], "run": identity(dest / "Run.csv")}
    marker = dest / "checked.json"
    if marker.exists():
        prior = json.loads(marker.read_text())
        require(all(prior[k] == v for k,v in signature.items()) and (figdir / "history.csv").is_file(),
                "Prior native review belongs to different inputs or has missing products")
        return
    start = float(reference_meta["TimeStep"])
    initial = ref if pre else post.native(OUT["preload"] / "data/Part_0000.bi4")[1]
    z = initial["Posd"][post.SOIL_IDS, 2]
    top, bottom = abs(z - z.max()) < post.DP / 4, abs(z - z.min()) < post.DP / 4
    prev = ref["Kplastic"][-5000:].copy()
    clocks = np.cumsum(np.r_[start, np.full(2_000_000 if pre else 600_000, post.DT)])
    rows = []
    for i, file in enumerate(files):
        m, a = post.native(file)
        prev = post.check_frame(m, a, i, pre, ref, prev, start, GROUP)
        if pre and i == len(files)-1:
            require(" stressdiffusion 3 0.10000000149011612 material " in m["GravityPreloadHandoffContract"],
                    "Same-material handoff lacks the active DDT3 coefficient")
        if not pre:
            require((dest / m["GravityPreloadStateFile"]).resolve() == refpath.resolve(),
                    f"Receiver source identity differs in PART {i}")
        step = int(m["Step"])
        complete = 0 if pre and i == 0 else step+1
        fi = complete - (0 if pre else 2_000_000)
        t = float(m["TimeStep"])
        require(0 <= fi < len(clocks) and t == clocks[fi] and (not rows or complete > rows[-1]["completed_step"]),
                f"Scalar clock or save order differs in {file}")
        measurements = post.measures(a, ref, top, bottom, i, t, t - start)[0]
        measurements.update(completed_step=complete, signed_dterror_s=float(m["dterror"]))
        rows.append(measurements)
    require(rows[-1]["completed_step"] == contract(stage)[0], "Wrong completed step")
    write_rows(figdir / "history.csv", rows)
    post.history_plot(figdir, GROUP, pre, rows)
    write_record(marker, dict(**signature, stage=stage, group=GROUP, actual_end_s=rows[-1]["time_s"],
                              solver_loop_s=float(runtime["TSimul"]), physical_acceptance=False))


def compare():
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ref = np.genfromtxt(CONTROL / "history.csv", delimiter=",", names=True)
    trial = np.genfromtxt(FIG / "collapse/history.csv", delimiter=",", names=True)
    require(len(trial) == len(ref) == 301 and np.array_equal(trial["completed_step"], ref["completed_step"])
            and np.array_equal(trial["time_s"],ref["time_s"]), "Actual saved clocks do not match across trials")
    with (CASE / "support/lian_collapse_fronts.csv").open(encoding="utf8", newline="") as f:
        paper = {float(r["tau_s"]):r for r in csv.DictReader(f) if r["group"] == GROUP}
    require(all(r["kind"] == "visible" for r in paper.values()) and set(paper) == {.3,.6,1.2}, "Paper references differ")
    samples = []
    for t in (.3, .6, 1.2, 3.):
        ix = int(np.argmin(abs(ref["tau_s"] - t)))
        require(abs(ref["tau_s"][ix] - t) < 5.01e-6, f"Missing sample at {t}")
        row = dict(part=int(ref["part"][ix]), nominal_tau_s=t, actual_tau_s=ref["tau_s"][ix], time_s=ref["time_s"][ix],
                   completed_step=int(ref["completed_step"][ix]))
        for k in METRICS:
            a, b = float(ref[k][ix]), float(trial[k][ix])
            row.update({f"off_{k}":a,f"ddt3_{k}":b,f"change_{k}":b-a})
        paper_x = float(paper[t]["front_x_m"]) if t in paper else None
        row.update(paper_front_m=paper_x, paper_digitization_m=paper[t]["digitization_m"] if t in paper else None,
                   off_minus_paper_m=None if paper_x is None else row["off_front_x_m"]-paper_x,
                   ddt3_minus_paper_m=None if paper_x is None else row["ddt3_front_x_m"]-paper_x)
        samples.append(row)
    write_rows(FIG / "comparison.csv", samples)
    fig, ax = plt.subplots(3,2, figsize=(11,9), sharex=True, layout="constrained")
    for data, label in ((ref,"DDT off"),(trial,"DDT3")):
        for panel, key, ylabel in zip(ax.ravel(),
            ("front_x_m","top_settlement_mm","excess_min_kPa","excess_max_kPa","nearest_below_half_dp","nearest_p05_dp"),
            ("Front x [m]","Material top settlement [mm]","Minimum excess pressure [kPa]",
             "Maximum excess pressure [kPa]","Particles with NN < 0.5 dp","5th percentile NN / dp")):
            panel.plot(data["tau_s"],data[key],label=label,ls="-" if label=="DDT3" else "--")
            panel.set_ylabel(ylabel)
            panel.grid(alpha=.2)
    ax[0,0].errorbar(list(paper),[float(r["front_x_m"]) for r in paper.values()],
                     yerr=[float(r["digitization_m"]) for r in paper.values()],fmt="ks",ms=4,label="Lian Fig. 15")
    ax[0,0].legend(fontsize=8)
    for panel in ax[-1]:
        panel.set_xlabel("Time since wall release [s]")
    fig.savefig(FIG / "comparison.png", dpi=180)
    plt.close(fig)


def compare_material_fields():
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize, SymLogNorm
    from postprocess_lian_release import native, DP, RELEASE_IDS
    from scipy.spatial import cKDTree
    paths = (CASE / "CaseLianCollapse_psi2p5_GPU_out", OUT["collapse"])
    with (FIG / "comparison.csv").open(encoding="utf-8", newline="") as handle:
        samples = list(csv.DictReader(handle))
    fields = []
    for row in samples:
        nominal = float(row["nominal_tau_s"])
        idx = int(row["part"])
        for setting, directory in zip((0, 3), paths):
            meta, values = native(directory / "data" / f"Part_{idx:04d}.bi4")
            require(np.array_equal(values["Idp"], RELEASE_IDS) and int(meta["Step"]) + 1 == int(row["completed_step"])
                    and meta["TimeStep"] == float(row["time_s"]), "Material plot does not match history")
            xz = values["Posd"][-5000:, [0, 2]]
            nearest = cKDTree(xz).query(xz, k=2)[0][:, 1] / DP
            p, p0 = (values[key][-5000:].astype("f8") / 1000 for key in ("PorePress", "PorePress0"))
            excess = values["ExcessPorePress"][-5000:].astype("f8") / 1000
            fields.append(np.column_stack((np.full(5000, nominal), np.full(5000,float(row["actual_tau_s"])),
                          np.full(5000, setting), values["Idp"][-5000:], xz, p, p0, excess, nearest)))
    combined = np.concatenate(fields)
    np.savetxt(FIG / "comparison_material.csv", combined, delimiter=",", fmt="%.12g", comments="",
               header="nominal_tau_s,actual_tau_s,DensityDT,id,x_m,z_m,p_kPa,p0_kPa,excess_kPa,nearest_over_dp")
    limit = max(1., np.max(np.abs(combined[:,8])))
    styles = ((8, "Excess pressure [kPa]", "RdBu_r", SymLogNorm(linthresh=1, vmin=-limit, vmax=limit)),
              (9, "Nearest distance / dp", "viridis", Normalize(vmin=0, vmax=combined[:,9].max())))
    for col, name, cmap, norm in styles:
        fig, axes = plt.subplots(4, 2, figsize=(12,7.6), sharex=True, sharey=True, layout="constrained")
        for i, (panel, arr) in enumerate(zip(axes.ravel(), fields)):
            plot = panel.scatter(arr[:,4],arr[:,5],c=arr[:,col],s=1,cmap=cmap,norm=norm,linewidths=0)
            panel.set_aspect("equal")
            if i < 2:
                panel.set_title(("DDT off","DDT3")[i])
            if i % 2 == 0:
                panel.set_ylabel(f"{arr[0,0]:g} s\nz [m]")
            if i >= 6:
                panel.set_xlabel("x [m]")
        fig.colorbar(plot, ax=axes, label=name, shrink=.85)
        fig.savefig(FIG / ("comparison_pressure.png" if col==8 else "comparison_spacing.png"), dpi=180)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("initial","preload","collapse","qualify-preload","review","all"), default="initial")
    parser.add_argument("--solver", type=Path, help="candidate GPU exe; required only for solver stages")
    parser.add_argument("--gencase", type=Path, default=BIN / "GenCase_win64.exe")
    args = parser.parse_args()
    check_definitions()
    if args.stage == "initial":
        print("Matched explicit no-HG +2.5 degree XML pair, DDT3; receiver resolves to", OUT["preload"] / "data/Part_1000.bi4")
        return
    if args.stage in ("preload","collapse","all") and (args.solver is None or not args.solver.is_file()):
        parser.error("supply an existing --solver candidate")
    if args.stage in ("preload","all"):
        run_stage("preload",args.solver.resolve(),args.gencase.resolve())
    if args.stage in ("preload","qualify-preload","collapse","all","review"):
        qualify("preload")
    if args.stage in ("collapse","all"):
        run_stage("collapse",args.solver.resolve(),args.gencase.resolve())
    if args.stage in ("collapse","review","all"):
        qualify("collapse")
        compare()
        compare_material_fields()


if __name__ == "__main__":
    main()
