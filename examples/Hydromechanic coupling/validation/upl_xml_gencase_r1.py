"""Exercise production GenCase with legacy and unified hydromechanical definitions."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from xml.sax.saxutils import quoteattr

import numpy as np

BASE = Path(__file__).resolve().parents[1]
PROGRAM = BASE.parents[1] / "bin/windows/GenCase_win64.exe"
sys.path.insert(0, str(BASE / "02_TerzaghiConsolidation_q0_PR/tests/support"))
from upl_tpi_partial_bi4_r1 import _Cursor, _numeric, _values

CASES = {
    "01": "CaseSelfWeightConsolidation_Scenario2_FreshPR",
    "02": "CaseTerzaghiConsolidation_q0_PR_full_k1em4",
    "04": "CaseCryerProblem_u_pl_nu030_r1",
    "05": "CaseLianFlexibleStrip2D_PR_release",
    "06": "CaseYao2DConsolidation_PR_SPR",
}
LOAD = {"HydroMechTopLoadMode": "mode", "HydroMechTopLoadQ0": "q0", "HydroMechTopLoadRampTime": "ramptime"}
OLD_DYNAMIC = "HydroMechDynamicSeepage"
NEW_MODEL = "HydroMechModel"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def parse(raw):
    # TinyXML can write a literal '<' in a quoted annotation; escape only in the parser copy.
    return ET.fromstring(re.sub(rb"""(\s[\w:.-]+\s*=\s*)("[^"]*"|'[^']*')""",
        lambda m: m[1] + m[2].replace(b"<", b"&lt;"), raw))


def contents(element):
    return (element.tag, sorted(element.attrib.items()), (element.text or "").strip(),
            [contents(child) for child in element])


def legacy_options(hydro):
    values = {attr: hydro.find(key).attrib["value"] for key,attr in LOAD.items() if hydro.find(key) is not None}
    model = 1 if hydro.find(OLD_DYNAMIC) is not None and hydro.find(OLD_DYNAMIC).get("value") in ("1","true") else 0
    return model, values or {"mode":"0"}


def migrate(raw):
    original = parse(raw)
    model, load = legacy_options(original.find("execution/special/hydromechanics"))
    out = raw
    for key in (*LOAD, OLD_DYNAMIC):
        out = re.sub(rb"(?m)^[ \t]*<" + key.encode() + rb"\s[^\r\n]*?/>[ \t]*\r?\n", b"", out)
    def insert(match):
        indent, newline = match.groups()
        ext = " ".join(key + "=" + quoteattr(value) for key,value in load.items())
        return (indent + b"<externalload " + ext.encode() + b" />" + newline + match[0]
                + indent + b'    <HydroMechModel value="' + str(model).encode() + b'" />' + newline)
    out, count = re.subn(rb"(?m)^([ \t]*)<hydromechanics>[ \t]*(\r?\n)", insert, out)
    require(count == 1, "Unique hydromechanics section required")
    return out


def particles_from_bi4(path):
    raw = path.read_bytes()
    require(raw[:58].rstrip(b" ") == b"#FileJBD JPartDataBi4", "Unknown particle file")
    cursor = _Cursor(raw, 64)
    arrays = {}
    def item(expected):
        desc = cursor.block(cursor.uint())
        require((desc.string(),desc.string()) == ("\nITEM\n",expected), "Unexpected initial BI4 item")
        desc.boolean(); desc.boolean(); desc.string(); desc.string()
        n, children, size = desc.uint(), desc.uint(), desc.uint()
        desc.finish("item")
        values, _ = _values(cursor.block(size))
        for _ in range(n):
            field = cursor.block(cursor.uint())
            require(field.string() == "\nARRAY", "Invalid array")
            name = field.string()
            field.boolean()
            array_type,count,declared_bytes = field.integer(),field.uint(),field.uint()
            field.finish("array")
            array, meta = _numeric(cursor,array_type,count)
            require(name not in arrays and meta["data_bytes"] == declared_bytes, "Duplicate or truncated array")
            arrays[name] = array
        if expected == "JPartDataBi4":
            require(children == 1 and n == 0, "Expected one initial PART")
            item("PART_0000")
        else:
            require(children == 0 and values["TimeStep"] == 0 and values["Nout"] == 0, "Invalid initial PART")
    item("JPartDataBi4")
    cursor.finish("seed BI4")
    return arrays


def run_case(number, stem, tag, revision):
    case, = BASE.glob(number + "_*")
    source = case / (stem + "_Def.xml")
    # The maintained root definitions may already use the new schema.
    repo = BASE.parents[1]
    raw = subprocess.check_output(["git", "show", revision+":"+source.relative_to(repo).as_posix()], cwd=repo)
    work = case / "tests/outputs" / tag
    receipt = case / "tests/logs" / (tag + ".check.json")
    require(not work.exists() and not receipt.exists(), "Use a fresh tag for " + str(case))
    generated, arrays = [], []
    for label, definition in (("legacy",raw), ("unified",migrate(raw))):
        folder = work / label
        folder.mkdir(parents=True)
        (folder / "Case_Def.xml").write_bytes(definition)
        with (folder / "gencase.log").open("xb") as log:
            result = subprocess.run([str(PROGRAM), "Case_Def", "Case", "-save:all"], cwd=folder,
                                    stdout=log, stderr=subprocess.STDOUT)
        require(result.returncode == 0, f"{folder}: GenCase exit {result.returncode}")
        generated.append(parse((folder / "Case.xml").read_bytes()))
        arrays.append(particles_from_bi4(folder / "Case.bi4"))
    a, b = generated
    expected_model, expected_load = legacy_options(parse(raw).find("execution/special/hydromechanics"))
    oldspec, newspec = a.find("execution/special"), b.find("execution/special")
    oldhyd, newhyd = oldspec.find("hydromechanics"), newspec.find("hydromechanics")
    require(oldspec.find("externalload") is None and oldhyd.find(NEW_MODEL) is None, "Unexpected legacy options")
    require(legacy_options(oldhyd) == (expected_model, expected_load), "GenCase changed original values")
    ext, = newspec.findall("externalload")
    new, = newhyd.findall(NEW_MODEL)
    require(ext.attrib == expected_load and new.attrib == {"value":str(expected_model)}, "New XML transmission")
    require(not any(newhyd.findall(key) for key in (*LOAD, OLD_DYNAMIC)), "Leftover selector/load key")
    for child in list(oldhyd):
        if child.tag in LOAD or child.tag == OLD_DYNAMIC:
            oldhyd.remove(child)
    newhyd.remove(new)
    newspec.remove(ext)
    require(contents(oldspec) == contents(newspec), "Additional special/soil/water/BC differences")
    for path in ("execution/constants","execution/parameters","execution/particles"):
        require(contents(a.find(path)) == contents(b.find(path)), "Changed " + path)
    particles = b.find("execution/particles")
    npart = int(particles.get("np"))
    require(arrays[0].keys() == arrays[1].keys() and "Idp" in arrays[0], "Changed BI4 fields")
    for field, old in arrays[0].items():
        new = arrays[1][field]
        require(old.dtype == new.dtype and old.shape == new.shape and old.shape[0] == npart
                and old.tobytes() == new.tobytes(), "Initial BI4 array differs: " + field)
    require(np.array_equal(np.sort(arrays[1]["Idp"]), np.arange(npart)), "Initial ID coverage")
    blocks = [dict(type=e.tag, **e.attrib) for e in particles if e.tag in ("fixed","fluid","moving","floating")]
    report = dict(passed=True, source=source.name, reference_revision=revision, model=expected_model, externalload=expected_load, particles=npart,
                  mk_blocks=blocks, identical_initial_fields=sorted(arrays[1]), other_special_fields_identical=True,
                  constants_parameters_particle_metadata_identical=True, actual_gencase_exits=[0,0], solver_launches=0)
    with receipt.open("x",encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    print(number, npart, expected_model, expected_load, flush=True)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--tag", default="upl_xml_gencase_r1")
    cli.add_argument("--case", choices=CASES)
    cli.add_argument("--reference-revision", default="41d23c4818801a45ca6dfc00b27a9a5b2ff066f2")
    args = cli.parse_args()
    require(re.fullmatch(r"[A-Za-z0-9_]+",args.tag), "Invalid stage name")
    for number, stem in CASES.items():
        if args.case is None or number == args.case:
            run_case(number,stem,args.tag,args.reference_revision)
