"""Compare former and current formal drainage inputs and actual GenCase particle fields."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[3]
REPO = BASE.parents[1]
sys.path.insert(0, str(BASE / "validation"))
from upl_xml_gencase_r1 import PROGRAM, contents, parse, particles_from_bi4, require

REV = "7965df7d7cabb1d1ba42f131c4873ea01a242f46"
OLD = ("HydroMechDrainage", "HydroMechDrainageStartTime", "HydroMechDrainageFixedGrid", "HydroMechFreeSeepage")
UNUSED_C03 = ("HydroMechFreeSurfaceDrainage", "HydroMechFreeSurfaceDrainageStartTime")


def options(root):
    special = root.find("execution/special")
    water = special.find("hydromechanics")
    if water is None:
        water = special.find("soils")
    public = special.find("drainage")
    if public is not None:
        require(all(water.find(k) is None for k in OLD + UNUSED_C03), "Mixed drainage definitions")
        return [public.get("mode", "drained"), float(public.get("start", 0)), public.get("clock", "time")]
    def get(key, default):
        node = water.find(key)
        return node.get("value") if node is not None else default
    enabled = get(OLD[0], "1") in ("1", "true")
    free = get(OLD[3], "0") in ("1", "true")
    mode = "freeSeepage" if free else "drained" if enabled else "off"
    return [mode, float(get(OLD[1], 0)), "fixedStep" if get(OLD[2], "0") in ("1", "true") else "time"]


def without_drainage(root):
    special = root.find("execution/special")
    for parent in (special, special.find("hydromechanics"), special.find("soils")):
        if parent is not None:
            for child in list(parent):
                if child.tag in ("drainage",) + OLD + UNUSED_C03:
                    parent.remove(child)
    return contents(special)


def generate(raw, folder):
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "Case_Def.xml").write_bytes(raw)
    with (folder / "gencase.log").open("xb") as log:
        proc = subprocess.run([str(PROGRAM), "Case_Def", "Case", "-save:all"], cwd=folder,
                              stdout=log, stderr=subprocess.STDOUT)
    require(proc.returncode == 0, f"{folder} GenCase exit {proc.returncode}")
    return parse((folder / "Case.xml").read_bytes()), particles_from_bi4(folder / "Case.bi4")


def outside_cases():
    # Tracked public example definitions outside this suite. Exclude retained output, fixtures and snapshots.
    names = subprocess.check_output(["git", "ls-files", "-z", "--", "examples"], cwd=REPO).decode().split("\0")
    checked, coupled = 0, []
    for name in names:
        p = REPO / name
        if not name.endswith("_Def.xml") or BASE in p.parents or not p.is_file():
            continue
        if any(x.lower() in {"tests", "support", "figures", "outputs", "output"} or x.lower().endswith("_out")
               for x in p.relative_to(REPO).parts[:-1]):
            continue
        checked += 1
        raw = re.sub(rb"<!--.*?-->", b"", p.read_bytes(), flags=re.S)
        if re.search(rb"<hydromechanics\b|<HydroMech\b[^>]*\bvalue\s*=\s*['\"](?:1|true)['\"]", raw, re.I):
            coupled.append(name)
    return dict(checked_tracked_definitions=checked, coupled=coupled)


def main(tag):
    case4 = Path(__file__).resolve().parents[2]
    inventory = json.loads((case4 / "tests/logs/public_xml_roots_migration_r1.check.json").read_text())["definitions"]
    cases = {p.name[:2]:p for p in BASE.glob("0*") if p.is_dir()}
    actual = {(n,p.name) for n,c in cases.items() for p in c.glob("*_Def.xml")}
    require(actual == {(i["case"],i["definition"]) for i in inventory}, "Root inventory changed")
    rows = []
    workspace = case4 / "tests/outputs" / tag
    for item in inventory:
        num, name = item["case"], item["definition"]
        path = cases[num] / name
        original = subprocess.check_output(["git","show",REV+":"+path.relative_to(REPO).as_posix()], cwd=REPO)
        raw = path.read_bytes()
        old, new = parse(original), parse(raw)
        opt = options(old)
        require(options(new) == opt, f"{name} effective drainage changed")
        row = dict(case=num, definition=name, mode=opt[0], start_s=opt[1], clock=opt[2])
        if original.replace(b"\r\n", b"\n") == raw.replace(b"\r\n", b"\n"):
            row["disposition"] = ("C01 sealed FreshPR release" if "FreshPR" in name else
                "public implicit default" if num == "01" else item["status"])
        else:
            require(item["status"] in ("public and checked","no model or external load keys to migrate")
                    and "FreshPR" not in name, f"{name} frozen input changed")
            require(without_drainage(old) == without_drainage(new), f"{name} changed other input")
            a, pa = generate(original, workspace / num / path.stem / "previous")
            b, pb = generate(raw, workspace / num / path.stem / "current")
            require(options(a) == options(b) == opt, f"{name} GenCase drainage differs")
            require(without_drainage(a) == without_drainage(b), f"{name} generated special changed")
            for section in ("constants","parameters","particles"):
                require(contents(a.find("execution/"+section)) == contents(b.find("execution/"+section)),
                        f"{name} generated {section} differs")
            require(pa.keys() == pb.keys() and "Idp" in pa, f"{name} BI4 fields differ")
            for k in pa:
                require(pa[k].dtype == pb[k].dtype and pa[k].shape == pb[k].shape
                        and pa[k].tobytes() == pb[k].tobytes(), f"{name} initial BI4 {k} differs")
            row.update(disposition="migrated", gencase_exits=[0,0], same_start_particles=len(pa["Idp"]),
                       identical_typed_arrays=sorted(pa))
            if any(k.encode() in original for k in UNUSED_C03):
                row["previous_draining_keys"] = "Unconsumed C03 names; original defaults drained/0/time"
        print(num, name, row["disposition"], flush=True)
        rows.append(row)
    receipt = dict(reference=REV, definitions=rows, outside_suite=outside_cases(), solver_launches=0)
    with (case4 / "tests/logs" / (tag+".check.json")).open("x",encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--tag", required=True)
    tag = cli.parse_args().tag
    require(re.fullmatch(r"[A-Za-z0-9_]+", tag), "Invalid tag")
    main(tag)
