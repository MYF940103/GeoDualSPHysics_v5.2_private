"""Exercise the real root BAT preprocessing paths on independent directories without starting a solver."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import hydro_frozen_entry_stage_r1 as stage
from hydro_frozen_xml_review_r1 import WORK, check, particles_from_bi4
from upl_xml_gencase_r1 import parse


PRE = "CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out"


def link_original(original, copy):
    copy.parent.mkdir(parents=True, exist_ok=True)
    os.link(original, copy)


def populate(case, root, overlay_path):
    overlay = overlay_path / case.name
    shutil.copytree(overlay, root)
    cid = case.name[:2]
    if cid == "04":
        mapping = json.loads((root / "support" / stage.ARCHIVES).read_text())
        for package in {spec["archive"] for spec in mapping.values()}:
            link_original(stage.package_path(case, package), root / package)
    elif cid == "08":
        for f in (case / "support").iterdir():
            if f.is_file() and f.suffix in (".py", ".ps1") and not (root / "support" / f.name).exists():
                link_original(f, root / "support" / f.name)
        for version in range(3, 7):
            for program in (case / "support" / f"runtime_r{version}").iterdir():
                if program.is_file():
                    link_original(program, root / "support" / f"runtime_r{version}" / program.name)
        for script in case.glob("xCase*.bat"):
            link_original(script, root / script.name)
        for rel in ("Run.csv", "data/Part_1000.bi4"):
            link_original(case / PRE / rel, root / PRE / rel)
    else:
        for prog in ("GenCase_win64.exe", "DualSPHysics5.2_GEO_win64.exe"):
            link_original(case / "support/bin" / prog, root / "support/bin" / prog)


def parts_for(source, name, entry, root):
    cid = source.name[:2]
    stem = name.removesuffix("_Def.xml")
    if cid == "04":
        m = json.loads((root / "support" / stage.ARCHIVES).read_text())[name]
        w = root / m["workspace"]
        if m["mode"] == "p3":
            return w / "support/upl_seed_nu030_r1/CaseCryerProblem_u_pl_nu030_r1", m["mode"]
        return w / "prepare" / stem / "Case", m["mode"]
    if cid == "08":
        backend = "GPU" if "_GPU." in entry else "CPU"
        return root / (f"{stem}_{backend}_prepare") / stem, "receiver" if "_shared_preload_" not in name else "preload"
    return root / (stem + "_prepare") / stem, "gen"


def call(bat, root, log, rc, args=("--prepare-only",)):
    cmd = [os.environ["COMSPEC"], "/d", "/c", bat, *args]
    windows=Path(os.environ["SystemRoot"])
    # The original C08 post-tool explicitly uses its own interpreter if installed.
    # No Python executable on PATH or in the user setting is available to migrated C04/C05/C01 preparation.
    env = dict(os.environ, PYTHON=str(root / "absent_python.exe"),
               PATH=os.pathsep.join(str(x) for x in (windows/"System32",windows/"System32/WindowsPowerShell/v1.0",windows)))
    for envkey in ("PYTHONHOME","PYTHONPATH","CONDA_PREFIX"):
        env.pop(envkey,None)
    check(shutil.which("python",path=env["PATH"]) is None and not Path(env["PYTHON"]).exists(), "Restricted preparation unexpectedly has Python")
    with log.open("xb") as out:
        run = subprocess.run(cmd, cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT, timeout=150)
    check(run.returncode == rc, f"Expected {rc} but received {run.returncode} at {bat}. See {log}")
    return log.read_bytes().decode("utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", default="bat1")
    ap.add_argument("--overlay", type=Path, default=stage.OVERLAY)
    args = ap.parse_args()
    check(args.tag.isalnum(), "Use a fresh simple run label")
    trial = stage.STAGE / args.tag
    trial.mkdir()
    logs = trial / "logs"
    logs.mkdir()
    entries = json.loads((args.overlay.parent / (args.overlay.name + "_entries.json")).read_text())
    by_case = {row["case"] for row in entries}
    for cid in sorted(by_case):
        source, = stage.SUITE.glob(cid + "_*")
        populate(source, trial / cid, args.overlay)
    results = []
    for row in sorted(entries, key=lambda r: (r["case"], r["definition"])):
        cid, name = row["case"], row["definition"]
        source, = stage.SUITE.glob(cid + "_*")
        root = trial / cid
        for wrapper in sorted(row["launchers"]):
            locked = cid == "08" and "_shared_r5_" in wrapper and "_psi0_" not in wrapper
            needs_cpu = cid == "08" and "_CPU." in wrapper and "_shared_preload_" not in wrapper
            reason = "historic psi gate" if locked else "missing actual archived CPU PRE" if needs_cpu else None
            log = logs / (wrapper + ".log")
            output = call(wrapper, root, log, int(reason is not None))
            item = dict(definition=name, launcher=wrapper, case=cid, exit=int(reason is not None), log=str(log.relative_to(trial)))
            if reason:
                msg = "NOT admitted" if locked else "scheduling check"
                check(msg in output, f"Incorrect rejection at {wrapper}")
                output_stem, _ = parts_for(source, name, wrapper, root)
                check(not output_stem.parent.exists(), "Unexpected partial/solver on held receiver")
                item["preserved_guard"] = reason
            else:
                actual, route = parts_for(source, name, wrapper, root)
                xml = parse(actual.with_suffix(".xml").read_bytes())
                particles = particles_from_bi4(actual.with_suffix(".bi4"))
                original = WORK / (cid + "_" + Path(name).stem) / "restored/Case.bi4"
                reference = particles_from_bi4(original)
                check(particles.keys() == reference.keys(), "Different seed field names")
                for key in particles:
                    check(particles[key].dtype == reference[key].dtype and particles[key].shape == reference[key].shape
                          and particles[key].tobytes() == reference[key].tobytes(), "Changed seed " + key + " " + name)
                item.update(route=route, particles=len(particles["Idp"]), seed_fields=list(particles),
                            effective_xml=str(actual.with_suffix(".xml").relative_to(root)))
                if route == "receiver":
                    pre = root / PRE / "data/Part_1000.bi4"
                    check(os.path.samefile(pre,source / PRE / "data/Part_1000.bi4"), "Different archived PRE")
                    check(str(pre) in ET.tostring(xml, encoding="unicode") and "__GRAVITY_PRELOAD_STATE__" not in ET.tostring(xml, encoding="unicode"), "Invalid effective handoff path")
                    check("PASS scheduling only" in output, "Original PRE schedule has not passed")
                    item["historical_pre_material_state_file"] = str(pre)
                if route == "p3":
                    check("passed preflight" in output, "Original sealed P3 BAT did not complete")
                    item["p3_scope"] = "real archived BAT check-only + checked seed; full retains independent accepted peak requirement"
            results.append(item)
            print(cid, wrapper, item.get("route", reason), flush=True)
    # The mutable wrappers must still refuse an existing result, without changing it.
    for cid in ("01", "05", "08"):
        row = next(r for r in results if r["case"] == cid and r["exit"] == 0)
        root = trial / cid
        seed = root / row["effective_xml"]
        retained = seed.read_bytes()
        msg = call(row["launcher"], root, logs / (cid + "_existing.log"), 1)
        check("Output already exists" in msg and retained == seed.read_bytes(), "Existing-output protection failed")
    check(not list(trial.glob("*/**/Run.out")), "Unexpected solver Run.out")
    # The single copied GPU PRE Run.csv is the only historical solver CSV on the staged copy.
    check(set(trial.glob("*/**/Run.csv")) == {trial / "08" / PRE / "Run.csv"}, "Unexpected solver output")
    receipt = dict(staging=str(trial), planned_inputs=len(entries), launches=len(results), rows=results,
                   real_preparation_entries=sum(not x["exit"] for x in results),
                   kept_locked_or_missing=sum(bool(x["exit"]) for x in results), existing_output_refusals=3,
                   solver_launches=0, pre_files_were_inputs_only=True)
    (trial / "entry_review.json").write_text(json.dumps(receipt, indent=2), encoding="utf8")
    print(trial / "entry_review.json")


if __name__ == "__main__":
    main()

