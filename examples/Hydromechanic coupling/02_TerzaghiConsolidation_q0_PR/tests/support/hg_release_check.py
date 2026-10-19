"""Offline same-physics CPU merge regression; never runs a solver.

One 1000-particle material frame is read at a time. --prefix permits a shorter
candidate against the beginning of a retained longer run, never a half-dt test.
Historical overwritten objects are explicitly unavailable, not reconstructed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
import numpy as np
import pandas as pd

TESTS = Path(__file__).resolve().parents[1]
PHYSICAL = ["x", "y", "z", "vx", "vy", "vz", "rho", "pressure",
            "sigma_xx", "sigma_yy", "sigma_zz", "sigma_xy", "sigma_yz", "sigma_xz", "kplastic"]
FLOAT32 = {"vx", "vy", "vz", "rho", "pressure", "pressure0", "kplastic", "load_az", "normal_z"}
DIAGNOSTIC = ["load_az", "fstype", "normal_z", "single_loaded"]
BINARY = np.dtype([("id", "<u4"), *[(c, "<f8") for c in ("x", "y", "z")],
                   *[(c, "<f4") for c in ("vx", "vy", "vz", "rho", "pressure", "pressure0")],
                   *[(c, "<f8") for c in PHYSICAL if c.startswith("sigma_")], ("kplastic", "<f4")])


def require(okay, message):
    if not okay:
        raise ValueError(message)


def label(value):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,72}", value):
        raise argparse.ArgumentTypeError("Use a shallow alphanumeric label")
    return value


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def entry(path):
    return dict(path=str(Path(path).resolve()), sha256=sha(path))


class Evidence:
    def __init__(self):
        self.freeze_path = TESTS / "logs/hg_release_base.json"
        self.freeze = load(self.freeze_path)
        require(self.freeze["source_and_copy_hashes_verified"], "Unverified release snapshot")
        self.archived = {str(Path(e["path"]).resolve()).lower(): e for e in self.freeze["entries"]}
        self.checked, self.mapped, self.missing_objects, self.missing_drivers = set(), [], [], []

    def verify(self, item, historical=False, build_driver=False):
        path, wanted = Path(item["path"]), item["sha256"].lower()
        identity = (str(path.resolve()).lower(), wanted)
        if identity in self.checked:
            return
        if path.is_file() and sha(path) == wanted:
            self.checked.add(identity)
            return
        saved = self.archived.get(identity[0])
        if historical and saved and saved["sha256"].lower() == wanted:
            copy = Path(self.freeze["snapshot"]) / saved["relative"]
            require(copy.is_file() and sha(copy) == wanted, f"Changed snapshot copy: {copy}")
            self.mapped.append(dict(original=str(path), copy=str(copy), sha256=wanted))
            self.checked.add(identity)
            return
        if historical and path.suffix.lower() == ".obj":
            self.missing_objects.append(dict(path=str(path), sha256=wanted,
                status="historical_object_unavailable_not_rebuilt", reason="Original object was not archived at this hash"))
            self.checked.add(identity)
            return
        if historical and build_driver and path.name == "mechanics_build.ps1":
            self.missing_drivers.append(dict(path=str(path), sha256=wanted,
                status="historical_build_driver_unavailable", reason="Retained driver copies do not have this historical hash"))
            self.checked.add(identity)
            return
        raise ValueError(f"Hash mismatch or missing evidence: {path}")


def configuration(run):
    choices = []
    for item in run["inputs"]:
        path = Path(item["path"])
        if path.suffix.lower() == ".xml":
            root = ET.parse(path).getroot()
            if root.find("execution/particles") is not None:
                choices.append((path, root))
    require(len(choices) == 1, "Expected one executed GenCase XML")
    path, root = choices[0]
    params = {n.get("key"): n.get("value") for n in root.findall("execution/parameters/parameter")}
    hyd = root.find("execution/special/hydromechanics")
    ignored = {"TimeMax", "TimeOut", "SoilBoundaryDerivativeSPR", "HydroMechDrainageFixedGrid", "timeout"}

    def canonical(node):
        if node is None or node.tag in ignored or node.get("key") in ignored:
            return None
        attrs = {}
        for key, val in node.attrib.items():
            if "comment" in key or key.startswith("_"):
                continue
            try:
                attrs[key] = float(val)
            except ValueError:
                attrs[key] = val
        return node.tag, attrs, [v for child in node if (v := canonical(child)) is not None]

    event_node = hyd.find("HydroMechDrainageFixedGrid")
    return dict(xml=entry(path), signature={s: canonical(root.find(s)) for s in
                ("casedef", "execution/constants", "execution/special", "execution/parameters", "execution/particles", "execution/motion")},
                spr=int(params.get("SoilBoundaryDerivativeSPR", "0")),
                event_grid=int(event_node.get("value")) if event_node is not None else 0,
                dt=float(params["DtFixed"]), event=float(hyd.find("HydroMechDrainageStartTime").get("value")))


def metadata(name, evidence, historical=False):
    path = TESTS / f"logs/{name}.run.json"
    run = load(path)
    require(run["completion_valid"] and run["exit_code"] == 0 and run["inputs_unchanged"], name+": incomplete run")
    for item in run["inputs"] + run["outputs"]:
        evidence.verify(item, historical)
    out = TESTS / "outputs" / name
    require(Path(run["output"]).resolve() == out.resolve(), name+": output identity")
    recorded = {str(Path(e["path"]).resolve()).lower() for e in run["outputs"]}
    hg_active = run["xi"] > 0
    required = ["initial_state.bin", "initial_state.csv", "initial_state.json", "final_state.bin",
                "final_state.csv", "final_state.json", "state.csv", "hourglass_complete.json", "complete.json"]
    if hg_active:
        required += ["hourglass.csv", "hourglass_final.csv"]
    if not historical:
        required.append("release_integration.json")
    require(all(str((out / f).resolve()).lower() in recorded for f in required), name+": required output not hash-bound")
    complete = load(out / "complete.json")
    require(complete == run["completion"] and complete["initial_time"] == 0 and complete["normal_soil"] == 1000,
            name+": raw completion differs")
    require(complete["steps"] == run["steps"] and complete["dt"] == run["dt"]
            and complete["stride"] == run["stride"]
            and abs(complete["final_time"] - run["steps"]*run["dt"]) <= 1e-7, name+": actual endpoint/step mismatch")
    require(load(out / "hourglass_complete.json") == run["hourglass"], name+": raw HG completion differs")
    hg = run["hourglass"]
    require(hg["xi"] == complete["xi"] == run["xi"] and hg["steps"] == run["steps"] and hg["dt"] == run["dt"],
            name+": HG scope differs")
    if not hg_active:
        require(run["xi"] == 0 and not run["hourglass_enabled"] and hg["xi_zero_bypasses_hg_allocation"]
                and all(hg[k] == 0 for k in ("hg_force_calls", "hg_updates", "predictor_updates", "corrector_updates",
                    "hg_rate_calls", "predictor_rate_calls", "endpoint_rate_calls", "first_pair_count", "min_pair_count",
                    "max_pair_count", "max_history_accel_m_s2", "max_net_hg_force_N_m", "max_net_hg_rate_N_m_s"))
                and not any((out / f).exists() for f in ("hourglass.csv", "hourglass_final.csv")),
                name+": disabled HG retained nonzero work/history")
    require(run["command"][0] == run["executable"] and run["command"][1:] == run["arguments"], name+": command differs")
    require(sha(run["executable"]) == run["executable_sha256"].lower(), name+": executable changed")
    builds = []
    for item in run["inputs"]:
        if item["path"].endswith(".build.json"):
            build = load(item["path"])
            if any(str(Path(e["path"]).resolve()).lower() == str(Path(run["executable"]).resolve()).lower()
                   for e in build.get("runtime", [])):
                builds.append((Path(item["path"]), build))
    require(len(builds) == 1, name+": actual executable build is ambiguous")
    build_path, build = builds[0]
    require(build["exe_sha256"].lower() == run["executable_sha256"].lower(), name+": executable/build hash differs")
    for key in ("inputs", "resolved_compile_link_inputs", "runtime"):
        for item in build[key]:
            evidence.verify(item, historical, build_driver=(key == "inputs"))
    evidence.verify(dict(path=str(build_path.with_suffix(".log")), sha256=build["build_log_sha256"]), historical)
    config = configuration(run)
    require(config["dt"] == run["dt"], name+": XML dt differs")
    mode = complete.get("boundary_derivative_mode", 0)
    event = bool(complete.get("event_policy", {}).get("enabled", False))
    if not historical:
        info = load(out / "release_integration.json")
        require(complete["mode"] == "production_symplectic" and complete["native_step_calls"] == run["steps"], name+": not production step")
        require(info["production_step_used"] and info["spr_enabled"] == bool(config["spr"])
                and info["fixed_grid_drainage"] == bool(config["event_grid"])
                and info["actual_final_time_s"] == complete["final_time"], name+": release runtime/XML mismatch")
        require(info["rate_logical_calls"] == info["rate_calculations"]+info["rate_cache_hits"], name+": cache count identity")
        if not hg_active:
            require(info["rate_logical_calls"] == info["rate_calculations"] == info["rate_cache_hits"] == 0,
                    name+": disabled HG cache is not zero")
        mode, event = 3*config["spr"], bool(config["event_grid"])
    return dict(name=name, run=run, out=out, complete=complete, config=config, mode=mode, event=event, hg_active=hg_active,
                receipt=dict(run=entry(path), build=entry(build_path), configuration=build["configuration"],
                             executable=entry(run["executable"]), actual_time=complete["final_time"],
                             steps=run["steps"], dt=run["dt"], inputs=len(run["inputs"]), outputs=len(run["outputs"])))


def bits(values, key):
    dtype = "<u4" if key in {"id", "fstype", "single_loaded", "drained"} else "<f4" if key in FLOAT32 else "<f8"
    return np.asarray(values, dtype=dtype).tobytes()


def native(meta, stem):
    out = meta["out"]
    array = np.fromfile(out / f"{stem}_state.bin", dtype=BINARY)
    require(BINARY.itemsize == 104 and len(array) == 1040 and np.array_equal(array["id"], np.arange(1040)),
            meta["name"]+": binary native IDs/layout")
    require(all(np.isfinite(array[k]).all() for k in BINARY.names), meta["name"]+": nonfinite native binary")
    frame = pd.read_csv(out / f"{stem}_state.csv", float_precision="round_trip")
    require(np.array_equal(frame.id.to_numpy(), np.arange(1040)) and np.isfinite(frame.to_numpy()).all(), meta["name"]+": native CSV")
    require(all(bits(array[k], k) == bits(frame[k], k) for k in PHYSICAL), meta["name"]+": CSV/binary mismatch")
    info = load(out / f"{stem}_state.json")
    require(info["completed_steps"] == (0 if stem == "initial" else meta["run"]["steps"])
            and info["time_s"] == (0 if stem == "initial" else meta["complete"]["final_time"]), meta["name"]+": native endpoint metadata")
    return array.tobytes()


def frames(meta):
    count = 0
    steps, stride, dt = (meta["run"][k] for k in ("steps", "stride", "dt"))
    for f in pd.read_csv(meta["out"] / "state.csv", chunksize=1000, float_precision="round_trip"):
        expected = min(count*stride, steps)
        require(len(f) == 1000 and np.array_equal(f.id.to_numpy(), np.arange(40, 1040)), meta["name"]+": sampled native IDs")
        require(f.step.nunique() == 1 and int(f.step.iloc[0]) == expected and f.time_s.nunique() == 1
                and abs(float(f.time_s.iloc[0])-expected*dt) <= 1e-7 and (f.stage == "full_step").all(), meta["name"]+": sampled time/stage")
        require(np.isfinite(f.drop(columns="stage").to_numpy()).all(), meta["name"]+": nonfinite sampled state")
        count += 1
        yield f.reset_index(drop=True)
    require(count == (steps+stride-1)//stride+1 == meta["complete"]["sampled_frames"], meta["name"]+": sampled frame count")


def compare(candidate, reference, prefix):
    require(candidate["run"]["dt"] == reference["run"]["dt"], "This is not a half-dt comparison")
    require(candidate["run"]["stride"] == reference["run"]["stride"], "Require matching sampling intervals")
    require(candidate["mode"] == reference["mode"] and candidate["event"] == reference["event"], "Different derivative/event models")
    require(candidate["hg_active"] == reference["hg_active"], "Different HG on/off paths")
    require(candidate["config"]["signature"] == reference["config"]["signature"], "XML physics differ beyond explicit implementation switches/output duration")
    steps, oldsteps = candidate["run"]["steps"], reference["run"]["steps"]
    require(steps <= oldsteps if prefix else steps == oldsteps, "Duration differs; use --prefix only for a shorter candidate")
    initial = native(candidate, "initial") == native(reference, "initial")
    final_c, final_r = native(candidate, "final"), native(reference, "final")
    final = final_c == final_r if steps == oldsteps else None
    equal = {k: True for k in PHYSICAL+DIAGNOSTIC+["drained"]}
    mismatches, permitted, count, unexpected = [], [], 0, False
    retained = iter(frames(reference))
    for c in frames(candidate):
        r = next(retained)
        require(bits(c.time_s, "time_s") == bits(r.time_s, "time_s") and bits(c.step, "step") == bits(r.step, "step"), "Matched actual times differ")
        for key in equal:
            if bits(c[key], key) == bits(r[key], key):
                continue
            equal[key] = False
            cb = np.frombuffer(bits(c[key], key), dtype=np.uint8).reshape(len(c), -1)
            rb = np.frombuffer(bits(r[key], key), dtype=np.uint8).reshape(len(r), -1)
            changed = np.flatnonzero(np.any(cb != rb, axis=1))
            allowed = (key == "drained" and candidate["mode"] == 3 and candidate["event"]
                       and candidate["run"]["dt"] == 1e-5 and candidate["config"]["event"] == .01
                       and int(c.step.iloc[0]) == 1000 and bool(reference["complete"].get("event_policy"))
                       and len(changed) > 0 and (c.loc[changed, key] == 1).all() and (r.loc[changed, key] == 0).all()
                       and ((c.loc[changed, "id"]-40) % 100 == 99).all() and (c.loc[changed, "fstype"] == 2).all())
            item = dict(field=key, step=int(c.step.iloc[0]), actual_time=float(c.time_s.iloc[0]), particles=int(len(changed)))
            if allowed:
                item["native_ids"] = c.loc[changed, "id"].astype(int).tolist()
                permitted.append(item)
            else:
                unexpected = True
                if len(mismatches) < 20:
                    mismatches.append(item)
        count += 1
    if steps == oldsteps:
        require(next(retained, None) is None, "Extra reference frames")
    hg_rows, hg_equal, history = 0, True, None
    if candidate["hg_active"]:
        with (candidate["out"] / "hourglass.csv").open("rb") as c, (reference["out"] / "hourglass.csv").open("rb") as r:
            for line in c:
                hg_equal &= line == r.readline()
                hg_rows += 1
            if steps == oldsteps:
                hg_equal &= r.read(1) == b""
        require(hg_rows == count, "HG sample rows/header do not match state frames")
        history = ((candidate["out"] / "hourglass_final.csv").read_bytes() ==
                   (reference["out"] / "hourglass_final.csv").read_bytes()) if steps == oldsteps else None
    return dict(passed=initial and final is not False and not unexpected and hg_equal and history is not False,
                compared_frames=count, native_ids_per_frame=1000, actual_times_bit_equal=True,
                initial_binary_equal=initial, final_binary_equal=final, fields_bit_equal=equal,
                hg_sample_csv_byte_equal=bool(hg_equal) if candidate["hg_active"] else None,
                hg_disabled_zero_state_verified=not candidate["hg_active"], final_hg_history_rate_csv_byte_equal=history,
                final_comparison_scope="full native binary/history" if steps == oldsteps else "sampled physical endpoint only; no retained intermediate binary/HG history",
                diagnostic_exceptions=permitted, unexpected_field_difference=unexpected, first_mismatches=mismatches,
                exception_reason="Only coarse .01-s drained display: new nominal-grid predicate vs old restored threshold; not a force-stage change")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=label, required=True)
    parser.add_argument("--reference", type=label, required=True)
    parser.add_argument("--tag", type=label, required=True)
    parser.add_argument("--prefix", action="store_true")
    args = parser.parse_args()
    target = TESTS / f"logs/{args.tag}.check.json"
    require(not target.exists(), "Refusing to overwrite review")
    result = dict(status="same_physics_merge_regression", passed=False, candidate=args.candidate,
                  reference=args.reference, prefix=args.prefix, reasons=[], physical_accuracy_accepted=False,
                  full_cycle_admitted=False, performance_measured=False, half_step_test=False, checker=entry(__file__))
    evidence = None
    try:
        evidence = Evidence()
        candidate = metadata(args.candidate, evidence)
        reference = metadata(args.reference, evidence, historical=True)
        result.update(candidate_evidence=candidate["receipt"], reference_evidence=reference["receipt"],
                      comparison=compare(candidate, reference, args.prefix))
        result["passed"] = result["comparison"]["passed"]
        if not result["passed"]:
            result["reasons"].append("Nonzero-bit implementation difference; no numerical tolerance substituted")
    except Exception as error:
        result["reasons"].append(f"{type(error).__name__}: {error}")
    if evidence:
        result["hash_evidence"] = dict(snapshot=entry(evidence.freeze_path), processed_entries=len(evidence.checked),
            verified_entries=len(evidence.checked)-len(evidence.missing_objects)-len(evidence.missing_drivers),
            mapped_snapshot_entries=evidence.mapped, historical_object_unavailable=evidence.missing_objects,
            historical_build_driver_unavailable=evidence.missing_drivers,
            limitation="Missing old objects/build driver prevent claiming fully reproducible relinking; retained executable, source/project and actual input/output hashes are checked. New build inputs/objects must all verify.")
    with target.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(dict(passed=result["passed"], path=str(target), reasons=result["reasons"])))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
