"""Prepare three fresh CPU negative-entry clones only; never invoke a program."""
import argparse
import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
ROOT = T.parents[3]
STAGE = "upl_hg_column_reject_prepare_r1"
MANIFEST = ("upl_hg_column_r1.inputs.json", 628141,
            "c1d9ec4018fff42dd444caf4bca757e5e3d27ad546ca49a68596225abf68e187")
RUNTIME_SHA = "fe5388994c5a1055fb63d4643614f4c572d681e64e0cb049e30ed507a5a38584"
BI4_SHA = "f2836ffeb049fc777de7687608dd5dfbece81f78440bdc01f21890ee3e3fedac"
NORMAL_SHA = "0509139e4fee0c57d3b480f213c4b9062cf467ce6a24c0a1d13d87148a885f97"
SHARED_ERROR = ("Experimental dynamic HG is CPU-only in the constant-k X-periodic loaded column, "
                "without time-dependent viscosity; actual FreeSlip bottom geometry is checked after loading particles.")
WALL_ERROR = "Dynamic wall fixture requires finite stationary FreeSlip wall normals."
H = "./execution/special/hydromechanics/"
P = "./execution/parameters/parameter[@key='{key}']"
VISCO_NAME = "upl_hg_column_reject_visco_r1.dat"
VISCO_BYTES = b"0 0\n0.0000019073486328125 0.1\n"


def need(ok, why):
    if not ok:
        raise ValueError(why)


def entry(path):
    p = Path(path).resolve(strict=True)
    raw = p.read_bytes()
    return dict(path=str(p), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def verify(e):
    actual = entry(e["path"])
    need(actual["bytes"] == e["bytes"] and actual["sha256"] == e["sha256"].lower(),
         "Changed bound input: " + e["path"])
    return Path(actual["path"])


def one(root, xpath):
    nodes = root.findall(xpath)
    need(len(nodes) == 1, "Expected one XML node: " + xpath)
    return nodes[0]


def dom(raw):
    root = ET.fromstring(raw, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
    for node in root.iter():
        if node.text is not None and not node.text.strip():
            node.text = None
        if node.tail is not None and not node.tail.strip():
            node.tail = None
    return root


def unique_replace(raw, before, after):
    need(before and raw.count(before) == 1, "Runtime byte edit is not unique")
    return raw.replace(before, after, 1), (before, after)


def set_value(raw, xpath, name, value, parameter=False):
    """Edit only one existing value attribute; preserve every other input byte."""
    root = dom(raw)
    old = one(root, xpath).get("value")
    pattern = rb"<parameter\b[^>]*>" if parameter else rb"<" + name.encode("ascii") + rb"\b[^>]*>"
    tags = list(re.finditer(pattern, raw))
    if parameter:
        tags = [m for m in tags if re.search(rb"\bkey\s*=\s*(['\"])" + name.encode("ascii") + rb"\1", m.group())]
    need(len(tags) == 1, "Expected one editable start tag: " + name)
    before = tags[0].group()
    attrs = list(re.finditer(rb"\bvalue\s*=\s*(['\"])([^'\"]*)\1", before))
    need(len(attrs) == 1 and attrs[0].group(2).decode("ascii") == old, "Expected one bound value: " + name)
    a = attrs[0]
    after = before[:a.start(2)] + value.encode("ascii") + before[a.end(2):]
    changed, undo = unique_replace(raw, before, after)
    return changed, undo, dict(xpath=xpath, attribute="value", old=old, new=value)


def add_visco_time(raw):
    root = dom(raw)
    need(not root.findall(P.format(key="ViscoTime")), "Baseline already has ViscoTime")
    lines = []
    for m in re.finditer(rb"(?m)^([ \t]*)<parameter\b[^\r\n]*\r?\n", raw):
        if re.search(rb"\bkey\s*=\s*(['\"])Visco\1", m.group()):
            lines.append(m)
    need(len(lines) == 1, "Expected one complete Visco parameter line")
    line = lines[0]
    newline = b"\r\n" if line.group().endswith(b"\r\n") else b"\n"
    addition = (line.group(1) + b'<parameter key="ViscoTime" value="' + VISCO_NAME.encode("ascii")
                + b'" comment="Negative CPU entry probe: valid zero-initial viscosity schedule; HG scope must reject before stepping" />' + newline)
    changed, undo = unique_replace(raw, line.group(), line.group() + addition)
    return changed, undo


def make_variant(raw, case):
    edits, changes = [], []
    changed = raw
    if case == "variable_k":
        for name, value in (("HydroMechConductivityModel", "1"), ("HydroMechConductivityCk", "0.1")):
            changed, undo, change = set_value(changed, H + name, name, value)
            edits.append(undo)
            changes.append(change)
    elif case == "visco_time":
        changed, undo = add_visco_time(changed)
        edits.append(undo)
    else:
        need(case == "no_slip", "Undeclared negative case")
        changed, undo, change = set_value(changed, P.format(key="SlipMode"), "SlipMode", "2", True)
        edits.append(undo)
        changes.append(change)
    inverse_bytes = changed
    for before, after in reversed(edits):
        need(inverse_bytes.count(after) == 1, "Inverse byte edit is not unique")
        inverse_bytes = inverse_bytes.replace(after, before, 1)
    need(inverse_bytes == raw, "Undeclared runtime byte change")
    inverse = dom(changed)
    for change in changes:
        node = one(inverse, change["xpath"])
        need(node.get(change["attribute"]) == change["new"], "Changed XML attribute differs")
        node.set(change["attribute"], change["old"])
    if case == "visco_time":
        node = one(inverse, P.format(key="ViscoTime"))
        need(node.get("value") == VISCO_NAME, "ViscoTime is not the declared relative file")
        one(inverse, "./execution/parameters").remove(node)
    need(ET.tostring(inverse) == ET.tostring(dom(raw)), "Inverse DOM differs outside declared attributes/new parameter")
    return changed, changes


def write_fresh(path, raw):
    with path.open("xb") as handle:
        handle.write(raw)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prepare", action="store_true", required=True)
    ap.parse_args()
    started = datetime.now(timezone.utc).isoformat()
    name, size, sha = MANIFEST
    source_manifest = entry(T / "logs" / name)
    need(source_manifest["bytes"] == size and source_manifest["sha256"] == sha,
         "Reviewed HG preparation manifest changed")
    manifest = json.loads(verify(source_manifest).read_text(encoding="utf-8-sig"))
    need(manifest["stage"] == "upl_hg_column_prepare_r1" and manifest["passed"] and manifest["prepared"],
         "Prepared HG source manifest rejected")
    rows = [row for row in manifest["variants"] if row["window"] == "smoke"]
    need(len(rows) == 1, "Prepared smoke variant ambiguous")
    source = {key: copy.copy(rows[0][key]) for key in ("configuration", "runtime", "initial_BI4", "normals")}
    bindings = [source_manifest, entry(__file__), entry(T / "notes" / "upl_hg_column_reject_prepare_r1.json")]
    for key, e in source.items():
        verify(e)
        wanted = BI4_SHA if key == "initial_BI4" else NORMAL_SHA if key == "normals" else RUNTIME_SHA
        need(e["sha256"] == wanted, "Reviewed smoke source differs: " + key)
        bindings.append(e)
    raw = verify(source["runtime"]).read_bytes()
    need(verify(source["configuration"]).read_bytes() == raw, "Smoke runtime/configuration bytes differ")
    baseline = dom(raw)
    for key, wanted in (("SoilHourglassXi", .1), ("SoilDamping", 1.), ("SoilDampingCoef", .02),
                        ("Visco", 0.), ("ViscoTreatment", 1.), ("SlipMode", 3.), ("Boundary", 2.),
                        ("SoilBoundaryDerivativeSPR", 0.), ("DtFixed", 2. ** -19), ("TimeMax", 2. ** -18)):
        need(float(one(baseline, P.format(key=key)).get("value")) == wanted, "Baseline parameter differs: " + key)
    for key, wanted in (("HydroMech", 1.), ("HydroMechDynamicSeepage", 1.),
                        ("HydroMechConductivityModel", 0.), ("HydroMechConductivityCk", 0.)):
        need(float(one(baseline, H + key).get("value")) == wanted, "Baseline hydro value differs: " + key)
    need(not baseline.findall(P.format(key="ViscoTime")), "Baseline viscosity schedule must be absent")
    source_files = [ROOT / "src" / "source" / (name + ".cpp")
                    for name in ("JSph", "JSphCpu", "JSphCfgRun", "JDsViscoInput")]
    source_bindings = [entry(path) for path in source_files]
    need(SHARED_ERROR in source_files[0].read_text(encoding="utf-8"), "Reviewed shared HG guard text changed")
    need(WALL_ERROR in source_files[1].read_text(encoding="utf-8"), "Reviewed actual wall guard text changed")
    need('txword=="MDBC_NOSLIP"' in source_files[2].read_text(encoding="utf-8"), "NoSlip CLI parser missing")
    bindings.extend(source_bindings)
    seed = T / "outputs" / "upl_hg_column_reject_seed_r1"
    record = T / "logs" / "upl_hg_column_reject_r1.inputs.json"
    need(all((T / name).is_dir() for name in ("configs", "outputs", "logs")), "Existing test directories required")
    need(not seed.exists() and not record.exists(), "Retained seed/manifest protected")
    plans = []
    for case in ("variable_k", "visco_time", "no_slip"):
        stem = "upl_hg_column_reject_" + case + "_r1"
        prefix = seed / stem
        config = T / "configs" / (stem + ".xml")
        output = T / "outputs" / ("upl_hg_column_reject_DebugCPU_" + case + "_r1")
        future_logs = {key: str(T / "logs" / ("upl_hg_column_reject_DebugCPU_" + case + "_r1." + suffix))
                       for key, suffix in (("call", "call.json"), ("run", "run.json"), ("console", "console.log"))}
        for path in [config, output] + [Path(v) for v in future_logs.values()]:
            need(not path.exists(), "Retained future label protected: " + str(path))
        changed, changes = make_variant(raw, case)
        boundary = "-mdbc_noslip" if case == "no_slip" else "-mdbc_freeslip"
        arguments = ["-cpu", "-ompthreads:1", "-stable", boundary, str(prefix), str(output),
                     "-dirdataout", "data", "-svres", "-nsteps:2"]
        job = dict(case=case, input_prefix=str(prefix), expected_error_substring=WALL_ERROR if case == "no_slip" else SHARED_ERROR,
                   expected_guard="InitDynamicPoreWallCpu actual native wall FreeSlip guard" if case == "no_slip" else "JSph shared public dynamic-HG scope guard",
                   changed_attributes=changes, added_parameter="ViscoTime" if case == "visco_time" else None,
                   inverse_runtime_bytes_exact=True, inverse_DOM_exact=True, all_other_runtime_bytes_unchanged=True,
                   original_HG_ON_comment_preserved=True, source_configuration=source["configuration"], source_runtime=source["runtime"],
                   source_initial_BI4=source["initial_BI4"], source_normals=source["normals"],
                   expected_no_Part1=True, forbidden_stepped_output=str(output / "data" / "Part_0001.bi4"),
                   expected_rejection_before_stepping=True, negative_result_observed=False,
                   solver_arguments=arguments, proposed_working_directory=str(ROOT / "src"),
                   proposed_output=str(output), proposed_logs=future_logs, physical_acceptance=False)
        plans.append((job, config, prefix, changed))
    seed.mkdir()
    jobs = []
    for job, config, prefix, changed in plans:
        runtime = prefix.with_suffix(".xml")
        bi4 = prefix.with_suffix(".bi4")
        normals = prefix.parent / (prefix.name + "_Normals.nbi4")
        write_fresh(config, changed)
        write_fresh(runtime, changed)
        write_fresh(bi4, verify(source["initial_BI4"]).read_bytes())
        write_fresh(normals, verify(source["normals"]).read_bytes())
        job.update(configuration=entry(config), runtime=entry(runtime), initial_BI4=entry(bi4), normals=entry(normals))
        need(job["configuration"]["sha256"] == job["runtime"]["sha256"], "Prepared config/runtime copy differs")
        need(job["initial_BI4"]["sha256"] == BI4_SHA and job["normals"]["sha256"] == NORMAL_SHA,
             "Prepared seed/native normals changed")
        if job["case"] == "visco_time":
            schedule = seed / VISCO_NAME
            write_fresh(schedule, VISCO_BYTES)
            need(schedule.read_bytes() == VISCO_BYTES, "Viscosity schedule copy differs")
            job.update(viscosity_schedule=entry(schedule), viscosity_schedule_relative_value=VISCO_NAME,
                       viscosity_schedule_rows=[[0., 0.], [2. ** -19, .1]],
                       initial_scalar_Visco_unchanged_zero=True, viscosity_parser_executed=False)
        jobs.append(job)
    for e in bindings:
        verify(e)
    result = dict(stage=STAGE, status="prepared_not_run", prepared=True, preparation_complete=True,
                  started_utc=started, ended_utc=datetime.now(timezone.utc).isoformat(),
                  source_manifest=source_manifest, source_smoke=source, jobs=jobs, inputs=bindings,
                  source_inputs_unchanged=True, seed_directory=str(seed),
                  negative_tests_executed=False, all_rejections_verified=False, noPart1_observed=False,
                  runtime_or_solver_program_invoked=False, GenCase_invoked=False, GPU_program_invoked=False,
                  production_or_formal_input_changed=False, physical_acceptance=False)
    write_fresh(record, (json.dumps(result, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print("Prepared three CPU rejection probes only; no rejection result observed: " + str(record))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
