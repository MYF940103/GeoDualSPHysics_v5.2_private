"""Record the real release before installation and verify it from its protected Windows entries."""
import argparse
import collections
import json
import os
import sys
from pathlib import Path

import hydro_frozen_entry_apply_r1 as installer
import hydro_frozen_entry_review_r1 as review
from upl_xml_gencase_r1 import parse


V = Path(__file__).resolve().parent
SUITE = V.parent
REPO = SUITE.parents[1]
CASES = {p.name[:2]: p for p in sorted(SUITE.glob("0[1-8]_*"))}
WORK = CASES["04"] / "tests/outputs/hfe1/actual_install_r2"
PREVIOUS = WORK.parent / "original_before_install"
RELEASE = json.loads((V / "hydro_frozen_entry_release_r2.json").read_bytes())
TARGETS = {r["path"]: r for r in RELEASE["entries"]}
OLD = set("""HydroMechDynamicSeepage HydroMechTopLoadMode HydroMechTopLoadQ0 HydroMechTopLoadRampTime
HydroMechDrainage HydroMechDrainageStartTime HydroMechDrainageFixedGrid HydroMechFreeSeepage""".split())
SAMPLES = {"01": "xCaseSelfWeightConsolidation_Scenario2_FreshPR_win64_GPU.bat",
           "04": "xCaseCryer_TPI_P3_nu030_peak_r1_win64_GPU.bat",
           "05": "xCaseLianFlexibleStrip2D_PR_release_win64_GPU.bat",
           "08": "xCaseLianSaturatedColumnCollapse_psi0_shared_r6_win64_GPU.bat"}


def rel(p):
    return p.relative_to(SUITE).as_posix()


def stamp(p):
    x = p.stat()
    return [x.st_size, x.st_mtime_ns, x.st_ino]


def write_new(path, obj):
    with path.open("x", encoding="utf8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def root_inputs():
    return {rel(p): stamp(p) for case in CASES.values()
            for pat in ("*_Def.xml", "*.bat") for p in sorted(case.glob(pat))}


def retained():
    evidence = collections.defaultdict(set)
    inputs = json.loads((V / "hydro_frozen_clean_inputs_r2.json").read_bytes())
    for paths in inputs["external_runtime_paths"].values():
        evidence["runtime_attachments"].update(REPO / p for p in paths)
    for case in CASES.values():
        for pat in ("*.zip", "*.zip.sha256", "support/*.zip", "support/*.zip.sha256"):
            evidence["immutable_archives_and_sidecars"].update(case.glob(pat))
        for pat in ("*.png", "*.csv"):
            evidence["formal_figures_and_data"].update((case / "figures").rglob(pat))
        for d in case.glob("*_out"):
            if d.is_dir():
                evidence["formal_output_directories"].add(d)
                evidence["run_summaries"].update(p for p in (d / "Run.csv", d / "Run.out") if p.is_file())
                parts = sorted((d / "data").glob("Part_[0-9]*.bi4"))
                if parts:
                    evidence["first_last_native_parts"].update((parts[0], parts[-1]))
    check = CASES["08"] / review.PRE / "data/Part_1000.bi4"
    review.check(check in evidence["runtime_attachments"] and check in evidence["first_last_native_parts"],
                 "Original C08 GPU preloading data is missing")
    return {group: {rel(p): stamp(p) for p in sorted(items)} for group, items in evidence.items()}


def before():
    old = {r: installer.signature(SUITE / r) for r in TARGETS}
    review.check(all(old[r] == row["previous"] for r, row in TARGETS.items()), "First-install state differs")
    review.check(not PREVIOUS.exists(), "Original backup already exists")
    protected = retained()
    inputs = root_inputs()
    review.check(len(inputs) == 129 and len(TARGETS) == 59 and sum(bool(i) for i in old.values()) == 35,
                 "Unexpected release size")
    WORK.mkdir()
    write_new(WORK / "before.json", {"root_inputs": inputs, "protected": protected, "old": old})
    print("Recorded 129 root files and", {k: len(v) for k,v in protected.items()}, flush=True)


def verify_deployment():
    prior = json.loads((WORK / "before.json").read_bytes())
    inputs = root_inputs()
    review.check(inputs.keys() == prior["root_inputs"].keys(), "Root input set changed")
    review.check(all(inputs[r] == v for r,v in prior["root_inputs"].items() if r not in TARGETS),
                 "Unrelated root XML/BAT changed")
    review.check(all(installer.signature(SUITE / r) == row["proposed"] for r,row in TARGETS.items()),
                 "Formal deployment content differs from the reviewed files")
    backups = {rel: sig for rel,sig in prior["old"].items() if sig}
    actual = {p.relative_to(PREVIOUS).as_posix(): installer.signature(p) for p in PREVIOUS.rglob("*") if p.is_file()}
    review.check(actual == backups, "Original backups differ from the pre-install bytes")
    saved = retained()
    review.check(prior["protected"] == saved, "Retained outputs, attachments or archives changed")
    counts = {}
    for cid,case in CASES.items():
        xmls, bats = sorted(case.glob("*_Def.xml")),sorted(case.glob("*.bat"))
        for xml in xmls:
            tags = {el.tag for el in parse(xml.read_bytes()).iter()}
            review.check(not (tags & OLD), "Old XML control in " + str(xml))
        counts[cid] = {"xml": len(xmls), "bat": len(bats)}
    rows = RELEASE["staged_normal_entry"]["rows"]
    review.check(len(rows) == len({(r["case"],r["launcher"]) for r in rows}) == 28 and
                 all((CASES[r["case"]]/r["launcher"]).is_file() for r in rows), "Incomplete historical coverage")
    return {"root_case_counts": counts, "root_xml": sum(c["xml"] for c in counts.values()),
            "root_bat": sum(c["bat"] for c in counts.values()), "historical_entries": len(rows),
            "historical_isolated_preparations": sum(r["exit"] == 0 for r in rows),
            "retained_historical_preparation_guards": sum(r["exit"] != 0 for r in rows),
            "installed_files": len(TARGETS), "byte_identical_original_backups": len(backups),
            "new_files": len(TARGETS)-len(backups), "unchanged_protected_stats": {k:len(v) for k,v in saved.items()},
            "protected_stat_fields": ["size", "mtime_ns", "file_id"],
            "original_backup": rel(PREVIOUS), "preinstall_stat_snapshot": rel(WORK / "before.json")}


def sample(cid):
    case, bat = CASES[cid], SAMPLES[cid]
    row, = (r for r in RELEASE["staged_normal_entry"]["rows"] if r["launcher"] == bat)
    stem, route = review.parts_for(case, row["definition"], bat, case)
    workdir = case / stem.relative_to(case).parts[0]
    review.check(not workdir.exists(), f"Preserve pre-existing preparation at {workdir}")
    log = WORK / (bat + ".log")
    output = review.call(bat, case, log, 0)
    xml, bi4 = stem.with_suffix(".xml"), stem.with_suffix(".bi4")
    actual = review.particles_from_bi4(bi4)
    refpath = review.WORK / (cid + "_" + Path(row["definition"]).stem) / "restored/Case.bi4"
    ref = review.particles_from_bi4(refpath)
    review.check(actual.keys() == ref.keys() and all(actual[k].dtype == ref[k].dtype and
                 actual[k].shape == ref[k].shape and actual[k].tobytes() == ref[k].tobytes() for k in ref),
                 "Seed particles changed in " + bat)
    if route == "p3":
        review.check("passed preflight" in output, "Original P3 preflight missing")
    if route == "receiver":
        from xml.etree.ElementTree import tostring
        review.check(str(case / review.PRE / "data/Part_1000.bi4") in tostring(parse(xml.read_bytes()), encoding="unicode")
                     and "PASS scheduling only" in output, "Original C08 PRE binding missing")
    archived = WORK / "prepared" / cid
    archived.parent.mkdir(exist_ok=True)
    review.check(workdir.resolve().parent == case and archived.resolve().parent == WORK.resolve() / "prepared"
                 and not archived.exists(), "Unsafe temporary workspace relocation")
    os.rename(workdir, archived)
    return {"case":cid, "root_bat":bat, "argument":"--prepare-only", "exit":0, "route":route,
            "particles":len(actual["Idp"]), "exact_seed_fields":list(actual),
            "preserved_generated_xml":rel(archived / xml.relative_to(workdir)), "console_log":rel(log)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["before","bindings","sample","finish"])
    parser.add_argument("--case", choices=sorted(SAMPLES))
    args = parser.parse_args()
    if args.phase == "before":
        before()
    elif args.phase == "bindings":
        print(json.dumps(verify_deployment(), indent=2))
    elif args.phase == "sample":
        if args.case is None:
            parser.error("--case is required")
        result = sample(args.case)
        write_new(WORK / ("sample" + args.case + ".json"), result)
        print(json.dumps(result), flush=True)
    else:
        result = verify_deployment()
        result["real_root_preparations"] = [json.loads((WORK / ("sample"+c+".json")).read_bytes()) for c in SAMPLES]
        result["solver_launches"] = 0
        write_new(V / "hydro_frozen_install_r2.json", result)
        print("Actual release verified.", flush=True)
