"""One-shot production-merge sequence. Authoring this file launches nothing.

Explicit --launch needs root-selected passed short-window check filenames.
15 s -> 15 s dt/2 -> offline gate -> 2Tv. No retry, restart or notifier.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
import numpy as np
import pandas as pd
import psutil
import traction_gate as gate
from hourglass_window import read_new

TESTS = gate.TESTS
RECORD = TESTS/"logs/hg_merge_sequence.status.json"
RUNNER = TESTS/"support/hg_merge_run.py"
CHECKER = TESTS/"support/hg_merge_check.py"
STAGES = (("hg_merge_15_x01", "15", "0.00001"),
          ("hg_merge_15_half", "15", "0.000005"),
          ("hg_merge_2tv", "72.8842857142858", "0.00001"))
LIMITS = {"geometry_mm_exclusive": .5, "post_0_1s_layer_stress_and_top_pair_pa": 100,
          "dt_over_tau": .2, "integrated_spin_rad_exclusive": .01,
          "sampled_load_resultant_error_N_m_exclusive": .001}


def save(report):
    report["updated_utc"] = datetime.now(timezone.utc).isoformat()
    temporary = RECORD.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    os.replace(temporary, RECORD)


def prerequisite(files, binary):
    exe = TESTS/f"outputs/mech_bin_{binary}/mechanics.exe"
    roles, receipts = set(), []
    for name in files:
        gate.require(Path(name).name == name and name.endswith(".check.json"), "Pass shallow logs/*.check.json filenames")
        path = TESTS/"logs"/name; review = gate.load(path)
        gate.require(review["status"] == "merge_checks_passed_not_full_cycle_acceptance"
                     and review["merge_and_requested_checks_passed"] and abs(review["seconds"]-.1) < 1e-12,
                     name+": initial 0.1-s merge prerequisite did not pass")
        for source, digest in review["scripts"].items():
            gate.require(gate.sha(source) == digest.lower(), "Changed short-review script: "+source)
        candidate = review["labels"][0]; result = review["results"][candidate]
        gate.require(result["native_run"] and result["evidence"]["exe_sha256"].lower() == gate.sha(exe),
                     name+": different production executable")
        for label in review["labels"]:
            runpath = TESTS/f"logs/{label}.run.json"
            gate.require(gate.sha(runpath) == review["results"][label]["evidence"]["run_manifest_sha256"], "Changed short-run manifest")
            gate.evidence(label, gate.load(runpath))
        xi = result["completion_check"]["xi"]
        if xi == .1: gate.require("half_dt" in review, "Active short prerequisite must include new half-dt result")
        roles.add(xi);receipts.append({"path": str(path), "sha256": gate.sha(path)})
    gate.require({0., .1} <= roles, "Need root-selected off and xi=0.1 short/half regression reports")
    return exe, receipts


class Samples:
    def __init__(self, label, dt, steps, stride, report):
        self.out, self.dt, self.steps, self.stride = TESTS/f"outputs/{label}", dt, steps, stride
        self.report, self.tails = report, ({}, {})
        self.pending, self.initial = pd.DataFrame(), None
        self.laststep, self.nextstep, self.last_hg_step = -1, 0, -1
        self.mass = None

    def frame(self, rows, seconds):
        m = gate.geometry(rows, self.initial, seconds)
        self.report["last_frame"] = m
        for field in ("max_dx_mm", "max_layer_z_span_mm", "max_layer_total_stress_error_pa", "top_pair_gap_pa"):
            if "stress" not in field and "gap" not in field or seconds >= .1-1e-7:
                self.report["sampled_max_"+field] = max(self.report.get("sampled_max_"+field, 0.), m[field])
        gate.require(max(m["max_dx_mm"], m["max_layer_z_span_mm"]) < .5, f"Geometry reached 0.5 mm at {seconds:.17g}s")
        if seconds >= .1-1e-7:
            gate.require(max(m["max_layer_total_stress_error_pa"], m["top_pair_gap_pa"]) <= 100,
                         f"Layer total-stress/top-pair error exceeds 100 Pa at {seconds:.17g}s")
        if seconds >= .1-1e-7 and "load_az" in rows:
            # Case-02's force fields belong to the last corrector; by 0.1 s
            # its ramp is over. This is a sampled guard, not an all-stage one.
            if self.mass is None:
                path = self.out.with_name(self.out.name+"_input")/("CaseTCq0_"+self.out.name+".xml")
                xml = ET.parse(path)
                self.mass = float(np.float32(xml.find("./execution/constants/massfluid").get("value")))
                hydro = xml.find("./execution/special/hydromechanics")
                gate.require(float(hydro.find("HydroMechTopLoadQ0").get("value")) == 10000
                             and float(hydro.find("HydroMechTopLoadRampTime").get("value")) == .01,
                             "Case-02 sampled load check requires the retained q0/ramp")
            ids = rows.id.to_numpy() if "id" in rows else rows.index.to_numpy()
            top = (ids-40)%100 == 99
            topids = set(range(139, 1040, 100))
            gate.require(set(ids[rows.fstype.isin([2, 3])]) == topids
                         and set(ids[rows.drained.eq(1)]) == topids
                         and rows.loc[top, "pressure"].eq(0).all(),
                         f"Sampled free-surface/drainage identity or pressure changed at {seconds:.17g}s")
            force = self.mass*float(rows.load_az.sum())
            error = abs(force+10000*.1)  # Retained case-02 periodic width = 0.1 m.
            gate.require(error < .001, f"Sampled top load resultant changed at {seconds:.17g}s")
            self.report["sampled_max_load_resultant_error_N_m"] = max(
                self.report.get("sampled_max_load_resultant_error_N_m", 0.), error)
            self.report["last_boundary_sample"] = dict(time_s=seconds, load_resultant_N_m=force,
                loaded_count=int(rows.load_az.ne(0).sum()), drained_ids=sorted(topids),
                top_normal_z_min=float(rows.loc[top, "normal_z"].min()),
                top_normal_z_max=float(rows.loc[top, "normal_z"].max()),
                phase="last_corrector_load_and_last_corrector_or_SaveData_classification")

    def poll(self):
        rows = read_new(self.out/"state.csv", self.tails[0])
        if not rows.empty:
            gate.finite(rows, "New full-step state")
            gate.require(rows.stage.eq("full_step").all() and rows.step.gt(self.laststep).all()
                         and rows.rho.gt(0).all() and rows.kplastic.eq(0).all(), "State stage/repeated row/density/plasticity failure")
            if self.initial is None: self.initial = gate.state(self.out/"initial_state.csv")
            self.pending = pd.concat([self.pending, rows], ignore_index=True)
            for step, frame in self.pending.groupby("step", sort=True):
                if len(frame) < 1000:
                    gate.require(step == self.pending.step.max(), "Incomplete non-trailing native frame");break
                gate.require(len(frame) == 1000 and frame.time_s.nunique() == 1 and step == self.nextstep,
                             "Overfull/mixed-time/skipped native frame")
                seconds = float(frame.time_s.iloc[0])
                gate.require(abs(seconds-step*self.dt) < 1e-6, "Incorrect actual full-step time")
                self.frame(frame, seconds);self.laststep = int(step)
                self.nextstep = min(self.laststep+self.stride, self.steps) if step < self.steps else self.steps+1
                self.report["checked_full_step_frames"] = self.report.get("checked_full_step_frames", 0)+1
            self.pending = self.pending[self.pending.step.gt(self.laststep)].copy()
        hg = read_new(self.out/"hourglass.csv", self.tails[1])
        if not hg.empty:
            gate.finite(hg, "New corrected-endpoint HG rows")
            gate.require(hg.stage.eq("corrected_endpoint").all() and hg.dt_s.eq(self.dt).all()
                         and hg.min_natural_dt_limit_s.ge(self.dt).all() and hg.dt_over_tau.le(.2).all()
                         and hg.integrated_max_skew_rad.ge(0).all() and hg.integrated_max_skew_rad.lt(.01).all()
                         and hg.step.gt(self.last_hg_step).all() and hg.step.diff().dropna().gt(0).all(), "HG dt/tau/spin/stage gate failed")
            self.last_hg_step = int(hg.step.iloc[-1])
            self.report["last_hg_sample"] = hg.iloc[-1].to_dict()

    def finish(self):
        gate.require(self.pending.empty and not any(t.get("partial") for t in self.tails)
                     and self.laststep == self.last_hg_step == self.steps, "Incomplete terminal CSV/frame coverage")
        self.frame(gate.state(self.out/"final_state.csv"), gate.load(self.out/"complete.json")["final_time"])


def stop_owned(wrapper, label, exe):
    """Only the known mechanics child of this Popen wrapper may be terminated."""
    if wrapper.poll() is not None: return {"already_exited": True}
    parent = psutil.Process(wrapper.pid); out = (TESTS/f"outputs/{label}").resolve()
    matches = [p for p in parent.children() if Path(p.exe()).resolve() == exe.resolve()
               and str(out).lower() in [a.lower() for a in p.cmdline()]]
    gate.require(len(matches) <= 1, "Refusing ambiguous child termination")
    if not matches:
        wrapper.wait(timeout=30);return {"solver_already_exited": True}
    child = matches[0]; start = gate.load(TESTS/f"logs/{label}.start.json")
    gate.require(child.ppid() == wrapper.pid and start["pid"] == child.pid
                 and Path(start["output"]).resolve() == out and Path(start["executable"]).resolve() == exe.resolve()
                 and child.create_time() >= parent.create_time(), "Refusing child identity mismatch")
    child.terminate();wrapper.wait(timeout=30)
    return {"solver_pid": child.pid, "wrapper_pid": wrapper.pid, "identity_verified": True, "terminated": True}


def run_stage(spec, binary, exe, report):
    label, duration, dt_text = spec;dt = float(dt_text)
    steps = 7288429 if label == "hg_merge_2tv" else round(float(duration)/dt)
    current = dict(label=label, target_seconds=float(duration), dt=dt, steps=steps, stride=round(.1/dt))
    report.update(stage=label, current=current);save(report)
    command = [sys.executable, "-B", str(RUNNER), "--name", label, "--duration", duration,
        "--dt", dt_text, "--output-interval", "0.1", "--xi", "0.1", "--top-mode", "5",
        "--engine", "wrapper", "--binary-label", binary, "--threads", "1", "--save", "1", "--run"]
    wrapper = subprocess.Popen(command, cwd=TESTS.parent, stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    current["wrapper_pid"] = wrapper.pid;samples = Samples(label, dt, steps, current["stride"], current)
    try:
        while True:
            samples.poll();save(report)
            if wrapper.poll() is not None: break
            try: wrapper.wait(timeout=20)
            except subprocess.TimeoutExpired: pass
        samples.poll()
        run = gate.load(TESTS/f"logs/{label}.run.json")
        gate.require(wrapper.returncode == 0 and run["status"] == "completed_pending_physical_acceptance"
                     and run["exit_code"] == 0 and run["completion_valid"], label+": solver/wrapper failed")
        samples.finish();current["evidence"] = gate.evidence(label, run)
        c, h = run["completion"], run["hourglass"]
        gate.require(c["mode"] == "production_symplectic" and c["native_step_calls"] == steps
                     and c["steps"] == h["steps"] == steps and abs(c["final_time"]-steps*dt) < 1e-6
                     and c["dt"] == dt and c["xi"] == h["xi"] == .1 and c["top_load_mode"] == 5
                     and c["max_fixed_dt_minus_mechanical_limit_s"] <= 0 and c["pore_dt_limit_s"] >= dt
                     and h["hg_force_calls"] == h["hg_updates"] == h["hg_rate_calls"] == 2*steps
                     and h["predictor_updates"] == h["corrector_updates"] == steps
                     and 0 <= h["integrated_max_skew_rad"] < .01 and h["max_dt_over_hg_tau"] <= .2,
                     label+": endpoint/dt/history/scope mismatch")
        current.update(status="completed_pending_physical_acceptance", final_time_s=c["final_time"])
        report.setdefault("runs", {})[label] = current;save(report)
    except Exception:
        current["status"] = "rejected"
        try: current["stop"] = stop_owned(wrapper, label, exe)
        except Exception as error: current["stop_error"] = str(error)
        raise


def worker(args):
    exe, receipts = prerequisite(args.prerequisite, args.binary_label)
    report = dict(status="running_not_accepted", stage="starting", worker_pid=os.getpid(), prerequisites=receipts,
        scripts={str(p): gate.sha(p) for p in (Path(__file__), RUNNER, CHECKER)}, thresholds=LIMITS,
        executable=str(exe), executable_sha256=gate.sha(exe), physical_accuracy_accepted=False,
        observations_are_sampled_not_all_step_bounds=True, sampled_boundary_guard=True,
        all_stage_boundary_guard=False, automatic_notifications_created=False)
    with RECORD.open("x", encoding="utf-8") as stream: json.dump(report, stream)
    try:
        for spec in STAGES[:2]: run_stage(spec, args.binary_label, exe, report)
        report["stage"] = "checking_15s_half_dt";save(report)
        command = [sys.executable, "-B", str(CHECKER), "--candidate", STAGES[0][0], "--reference", "hg_window_x01",
                   "--half", STAGES[1][0], "--seconds", "15", "--tag", "hg_merge_gate"]
        done = subprocess.run(command, cwd=TESTS.parent, stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        path = TESTS/"logs/hg_merge_gate.check.json";review = gate.load(path)
        report["gate"] = {"path": str(path), "sha256": gate.sha(path), "status": review["status"]}
        gate.require(done.returncode == 0 and review["full_15s_half_dt_gate_passed"], "15-s merge/half-dt gate rejected; no 2Tv launch")
        run_stage(STAGES[2], args.binary_label, exe, report)
        report.update(status="completed_2tv_pending_full_physical_review", stage="awaiting_independent_comparison_and_plots")
    except Exception as error:
        report.update(status="sequence_rejected", stop_reason=str(error))
    save(report);print(json.dumps({"status": report["status"], "stage": report["stage"], "record": str(RECORD)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--launch", action="store_true");mode.add_argument("--worker", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    parser.add_argument("--prerequisite", nargs="+", default=["hg_merge_off_r1.check.json", "hg_merge_short_half_r1.check.json"])
    parser.add_argument("--binary-label", default="hg_m1rel")
    args = parser.parse_args()
    if args.self_test:
        for label, expected in (("hg_soft_x01", True), ("hg_short_x1", False)):
            s = Samples(label, 1e-5, 10000, 1000, {});s.initial = gate.state(s.out/"initial_state.csv")
            try: s.frame(gate.state(s.out/"final_state.csv"), .1);passed = True
            except ValueError: passed = False
            gate.require(passed == expected, "Unexpected offline frame self-test: "+label)
            print(json.dumps({"label": label, "passed": passed, "expected": expected}))
        return
    if args.worker: worker(args);return
    prerequisite(args.prerequisite, args.binary_label)
    blocked = [RECORD, TESTS/"logs/hg_merge_sequence.worker.log", TESTS/"logs/hg_merge_gate.check.json"]
    for label, _, _ in STAGES:
        blocked += [TESTS/f"outputs/{label}", TESTS/f"logs/{label}.run.json", TESTS/f"logs/{label}.start.json"]
    gate.require(not any(p.exists() for p in blocked), "Refusing duplicate launch/overwrite; no automatic resumption")
    with blocked[1].open("x", encoding="utf-8") as stream:
        proc = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "--worker", "--binary-label", args.binary_label,
            "--prerequisite", *args.prerequisite], cwd=TESTS.parent, stdin=subprocess.DEVNULL,
            stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    print(json.dumps({"status": "worker_started_not_accepted", "pid": proc.pid, "record": str(RECORD)}))


if __name__ == "__main__":
    main()
