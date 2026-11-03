"""Prepare one fresh CPU1 requested u-pl full2Tv input; no program invocation."""
import argparse
import csv
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sys
import xml.dom.minidom as DOM

T = Path(__file__).resolve().parents[1]
NAME, TAG = "upl_spr_av_full_prepare_r1", "upl_spr_av_2tv_CPU1_r1"
SOURCE_TAG = "upl_spr_av_new_requested_ON_r1"
DT, STEPS, N, EVENT = 2.0 ** -19, 38212357, 858, 5243
END_TEXT, INTERVAL = "72.8842868804931640625", "0.18218571428571428"
SEED = T / "outputs/upl_spr_av_2tv_seed_r1"
PREFIX = SEED / "upl_spr_av_2tv_r1"
OUT = T / "outputs" / TAG
CONFIG, BAT = (T / "configs" / (TAG + suffix) for suffix in (".xml", ".bat"))
CSV = T / "logs/upl_spr_av_full_r1.clock.csv"
RECORD = T / "logs/upl_spr_av_full_r1.inputs.json"
PINS = {
    "support/upl_spr_av_run_r1.py": (15888, "574c3a4da7ade2c1fda97d93a95c1544d6dc05e6896a5f08594053992d2fb757"),
    "notes/upl_spr_av_run_r1.json": (3340, "42ceee38a1ba1230cb2475eda1d827c30d3c05fe4c7842a0a60b058d7cbadd59"),
    "notes/upl_spr_av_full_plan_r1.json": (7887, "213782e1b3e962c3f3d26482e49a12b097ff02071e44fafc2a5a04f4a3a8943e"),
}
owner = None


def need(ok, why):
    if not bool(ok):
        raise ValueError(why)


def definitions():
    sys.dont_write_bytecode = True
    path = T / "support/upl_spr_av_run_r1.py"
    import hashlib
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    need((path.stat().st_size, digest) == PINS["support/upl_spr_av_run_r1.py"], "Frozen short definitions changed")
    spec = importlib.util.spec_from_file_location("spr_av_frozen_short_input_definitions", path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)  # Definitions/context only, never main/run/check_output.
    for name, (size, sha) in PINS.items():
        value.bind(dict(path=str(T / name), bytes=size, sha256=sha))
    return value


def element(doc, key):
    nodes = list(doc.getElementsByTagName("tout")) if key == "tout3" else [
        n for n in doc.getElementsByTagName("parameter") if n.getAttribute("key") == key]
    if key == "tout3":
        need(len(nodes) == 4, "Exactly four retained tout entries required")
        return nodes[3]
    need(len(nodes) == 1, "Unique parameter required: " + key)
    return nodes[0]


def edit(text, key, attribute, value):
    pattern = r"<tout\b[^>]*>" if key == "tout3" else r'<parameter\s+key="' + re.escape(key) + r'"[^>]*>'
    matches = list(re.finditer(pattern, text))
    need(len(matches) == (4 if key == "tout3" else 1), "Unique literal setting tag required")
    match = matches[3 if key == "tout3" else 0]
    tag = match.group()
    attrs = list(re.finditer(r'\b' + re.escape(attribute) + r'="([^"]*)"', tag))
    need(len(attrs) == 1, "Unique existing setting attribute required")
    a = attrs[0]
    newtag = tag[:a.start(1)] + value + tag[a.end(1):]
    return text[:match.start()] + newtag + text[match.end():], a.group(1)


def transform(source):
    text = source.decode("utf-8")
    original = DOM.parseString(text)
    for key, attribute, value in (("TimeMax", "value", "0.5"), ("TimeOut", "value", "0.0001220703125"),
                                  ("tout3", "time", "0.125"), ("tout3", "timeout", "0.001953125")):
        need(element(original, key).getAttribute(attribute) == value, "Actual retained short timing differs")
    changes = [
        ("TimeMax", "value", END_TEXT), ("TimeOut", "value", INTERVAL),
        ("tout3", "time", "0.0250244140625"), ("tout3", "timeout", INTERVAL),
        ("TimeMax", "comment", "Full 2Tv CPU1 requested u-pl candidate; root launch admission and actual validation required"),
        ("TimeOut", "comment", "Late nominal DeltaTv=.005; retained dense startup; references use actual saved times"),
    ]
    target, proof = text, []
    for key, attr, new in changes:
        target, old = edit(target, key, attr, new)
        proof.append(dict(setting=key, attribute=attr, old=old, new=new, numeric=attr != "comment"))
    inverse = target
    for row in reversed(proof):
        inverse, seen = edit(inverse, row["setting"], row["attribute"], row["old"])
        need(seen == row["new"], "Inverse literal value differs")
    after, back = DOM.parseString(target), DOM.parseString(target)
    for row in proof:
        element(back, row["setting"]).setAttribute(row["attribute"],
            element(original, row["setting"]).getAttribute(row["attribute"]))
    need(inverse.encode("utf-8") == source and back.toxml() == original.toxml() and
         sum(row["numeric"] for row in proof) == 4 and
         all(a.toxml() == b.toxml() for a, b in zip(
             original.getElementsByTagName("tout")[:3], after.getElementsByTagName("tout")[:3])),
         "Exact inverse UTF8/DOM/four numeric changes/retained startup proof failed")
    return target.encode("utf-8"), after, proof


def schedule(doc):
    segments = [(float(n.getAttribute("time")), float(n.getAttribute("timeout")))
                for n in doc.getElementsByTagName("tout")]
    need(segments == [(0., 64 * DT), (5120 * DT, DT), (5376 * DT, 64 * DT), (13120 * DT, float(INTERVAL))],
         "Exact four full output segments differ")
    rows = [dict(part=0, completed_steps=0, saved_step=0, time_s=0., dt_s=DT,
                 post_open_by_completed_step=False, target_time_s=0., final_partial=False)]
    base, time = 0, 0.
    while rows[-1]["completed_steps"] < STEPS:
        need(len(rows) <= N, "Output schedule exceeded declared858 frames")
        while base + 1 < len(segments) and time >= segments[base + 1][0]:
            base += 1
        tb, interval = segments[base]
        nt = int((time - tb) / interval)
        target = tb + interval * nt
        while target <= time:
            nt += 1
            target = tb + interval * nt
        if base + 1 < len(segments):
            target = min(target, segments[base + 1][0])
        completed = min(STEPS, math.ceil(target / DT))
        need(completed > rows[-1]["completed_steps"], "Output schedule failed to advance")
        time = completed * DT
        rows.append(dict(part=len(rows), completed_steps=completed, saved_step=completed - 1, time_s=time,
                         dt_s=DT, post_open_by_completed_step=completed > EVENT,
                         target_time_s=target, final_partial=target > float(END_TEXT)))
    need(len(rows) == N and rows[-1]["time_s"] == float(END_TEXT) and
         rows[458]["completed_steps"] == 108638 and rows[-2]["completed_steps"] == 38124716 and
         [r["completed_steps"] for r in rows[:458]] == owner.SAVE and
         sum(r["post_open_by_completed_step"] for r in rows) == 654 and rows[-1]["final_partial"],
         "Declared858 integer schedule/startup/final partial coverage differs")
    return rows


def portable_bat(program):
    cwd = owner.SRC
    rel = lambda p: os.path.relpath(p, cwd)
    return "\r\n".join([
        "@echo off", "setlocal EnableExtensions", 'pushd "%~dp0' + os.path.relpath(cwd, BAT.parent) + '"',
        'if errorlevel 1 exit /b 1',
        'set "program=' + rel(program["path"]) + '"', 'set "case=' + rel(PREFIX) + '"',
        'set "dirout=' + rel(OUT) + '"', 'if exist "%dirout%" goto protected',
        'if not exist "%program%" goto missing', 'if not exist "%case%.xml" goto missing',
        'if not exist "%case%.bi4" goto missing', 'if not exist "%case%_Normals.nbi4" goto missing',
        '"%program%" -cpu -ompthreads:1 -stable -mdbc_freeslip "%case%" "%dirout%" -dirdataout data -svres -nsteps:38212357',
        'set "result=%ERRORLEVEL%"', "popd", "exit /b %result%",
        ":protected", "echo Existing output preserved; no solver was launched.",
        "popd", "exit /b 1", ":missing", "echo Frozen program or prepared input missing; no solver was launched.",
        "popd", "exit /b 1", "",
    ]).encode("ascii")


def prepare(result):
    global owner
    owner = definitions()
    ctx = owner.context(SOURCE_TAG)  # Valid prepared short input/component, not proof of its requested run/native.
    job = ctx["job"]
    need((job["master"], job["SPR"], job["Visco"], job["eta"], job["HG"], job["SlipMode"]) == (1, 1, .1, .04, .1, 3),
         "Only the exact requested_ON short physical input is admitted for this preparation")
    for p in (__file__, T / "notes" / (NAME + ".json")):
        owner.adopt(p)
    manifest = owner.read(ctx["manifest"])
    for e in manifest["immutable_source_archives"]["new"]:
        owner.bind(e)
    owner.fresh(SEED, OUT, CONFIG, BAT, CSV)
    source = owner.bind(job["runtime"]).read_bytes()
    payload, doc, changes = transform(source)
    table, bat = schedule(doc), portable_bat(ctx["program"])
    SEED.mkdir()
    paths = [CONFIG, PREFIX.with_suffix(".xml"), PREFIX.with_suffix(".bi4"), Path(str(PREFIX) + "_Normals.nbi4"), BAT]
    contents = [payload, payload, owner.bind(job["initial_BI4"]).read_bytes(), owner.bind(job["normals"]).read_bytes(), bat]
    for path, content in zip(paths, contents):
        with path.open("xb") as stream:
            stream.write(content)
    with CSV.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    files = [owner.adopt(p) for p in paths + [CSV]]
    need(all(files[2][k] == job["initial_BI4"][k] and files[3][k] == job["normals"][k] for k in ("bytes", "sha256")),
         "Original BI4/Normals copies changed bytes")
    full = dict(job, tag=TAG, window="full2Tv", input_variant="requested_ON_full2Tv", input_prefix=str(PREFIX),
                output_directory=str(OUT), arguments=["-cpu", "-ompthreads:1", "-stable", "-mdbc_freeslip",
                    str(PREFIX), str(OUT), "-dirdataout", "data", "-svres", "-nsteps:38212357"],
                steps=STEPS, end_s=STEPS * DT, expected_samples=N, saved_clock_table=table,
                configuration_file=files[0], runtime=files[1], initial_BI4=files[2], normals=files[3],
                post_open_frames=654, post_open_drained_particle_checks_expected=6540,
                expected_HG_counters=dict(forcecalls=2*STEPS, ratecalls=2*STEPS, predictorupdates=STEPS,
                    correctorupdates=STEPS, ratecalculations=STEPS+1, ratecachehits=STEPS-1))
    result.update(prepared=True, source_input_manifest=ctx["manifest"], source_job=job, source_build=ctx["source_build"],
                  program=ctx["program"], component=ctx["component"], jobs=[full], files=files, portable_BAT=files[4],
                  planned_clock_CSV=files[5], declared_changes=changes, inverse_UTF8_bytes_and_DOM_exact=True,
                  unchanged_first_three_tout_entries=True, original_seed_and_normals_bytes_exact=True,
                  source_current_archives_only_not_mutable_live_source=True,
                  planned458_integer_prefix_matches=True, measured458_native_or_dterror_prefix_exact=False,
                  requested_short_run_or_r2_native_pass_claimed=False, separate_root_full_launch_admission_required=True,
                  mandatory_half_or_OFF_full=False, future_native_counts=dict(soil_ledger=858000, fixed_markers=34320,
                      all_ID_J_theta=892320, signed_noninitial_intervals=857, post_open_frames=654, actual_receivers=6540))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    if not args.execution_authorized:
        parser.error("Root full-read and explicit preparation-only authorization required")
    need(not RECORD.exists(), "Retained full preparation receipt protected")
    result = dict(stage=NAME, passed=False, prepared=False, failure=None, physical_acceptance=False,
                  full_run_admitted=False, source_formal_or_canonical_files_written=False,
                  solver_reader_build_Git_watcher_or_queue_invoked=False)
    try:
        prepare(result)
        result["passed"] = True
    except Exception as exc:
        result["failure"] = str(exc)
    try:
        need(owner is not None, "Definitions were not initialized")
        result["inputs"] = owner.final_bindings()
        result["bindings_unchanged"] = result["independent_final_rehash_performed"] = True
    except Exception as exc:
        result["inputs"] = list(owner.BOUND.values()) if owner else []
        result["bindings_unchanged"] = result["independent_final_rehash_performed"] = False
        result["failure"] = (result["failure"] + "; " if result["failure"] else "") + str(exc)
        result["passed"] = False
    with RECORD.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(dict(passed=result["passed"], receipt=str(RECORD), failure=result["failure"])))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
