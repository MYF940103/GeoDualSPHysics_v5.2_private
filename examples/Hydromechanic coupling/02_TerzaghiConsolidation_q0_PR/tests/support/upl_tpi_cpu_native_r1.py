"""Root-admitted P1 native build, unique read, or offline review; never a solver.

Each action is separate, requires its own frozen root admission, and has no
automatic follow-up. The retained neutral loader and old readers are read-only.
"""
from __future__ import annotations
import argparse
import csv
import math
import os
from pathlib import Path
import re
import shutil
import struct
import upl_tpi_cpu_build_r2 as b

T, L, S = b.T, b.L, b.S
TAG = "upl_tpi_cpu_native_r1"
CPP = T / "support" / (TAG + ".cpp")
NOTE = T / "notes" / (TAG + ".md")
SCRIPT = Path(__file__).resolve()
BASE = L / "upl_bigstep_native_r1.build.json"
COMPILE = L / "upl_bigstep_native_r1_Compile.call.json"
LINK = L / "upl_bigstep_native_r1_Link.call.json"
BUILDROOT = T / "outputs" / (TAG + "_build")
BUILD = L / (TAG + ".build.json")
PROGRAM = BUILDROOT / (TAG + ".exe")
NEUTRAL = T / "support/upl_cpu_public_native_r1.cpp"
RETAINED = T / "outputs/upl_bigstep_2tv_CPU1_r1_native_r1"
DT = 6.250143051147461e-6
WINDOWS = {
    "debug2ms": dict(steps=320, frames=18, end=.002000045776367195,
                     post=0, common_A=17),
    "startup015": dict(steps=24000, frames=344, end=.1500034332275618,
                       post=226, common_A=343),
}
SIDECAR_COLUMNS = "part,native_id,source_step_zero_based,completed_step,source_time_s,actual_save_time_s,dt_s,pn_Pa,previous_Pa,prediction_double_Pa,half_actual_float_Pa,endpoint_q_actual_float_Pa,S_1_per_m_s,Rgamma_Pa_per_m_s,raw_final_float_Pa,final_float_Pa,theta_half_for_J_1_per_s,theta_endpoint_1_per_s,Jn,Jhalf,Jfull,source_drained,endpoint_drained,commit_drained,commits,endpoint_calls,core_field_bit_checks,hg_snapshot_checks".split(",")


def bits(value, kind="d"):
    return struct.pack("<" + kind, value)


def finite(value):
    x = float(value)
    b.need(math.isfinite(x), "Nonfinite native/pressure-sidecar field")
    return x


def f32(value):
    return struct.unpack("<f", bits(value, "f"))[0]


class Admission:
    def __init__(self, action, path):
        self.entry = b.stat(path)
        self.data = b.read(path)
        b.need(self.data.get("stage") == TAG + "." + action + "_admission"
               and self.data.get("passed") is True and self.data.get("action_only") is True,
               "Independently reviewed exact-action root admission required")
        self.frozen = {str(Path(x["path"]).resolve()): x for x in self.data["inputs"]}
        for p in (SCRIPT, NOTE, CPP, Path(b.__file__)):
            self.pin(p)
        self.finish()

    def pin(self, path):
        key = str(Path(path).resolve())
        b.need(key in self.frozen, "Consumed input absent from root admission: " + key)
        return b.same(self.frozen[key])

    def finish(self):
        for x in self.frozen.values():
            b.same(x)
        b.same(self.entry)


def no_active_reader(program, data=None):
    import psutil
    target = Path(program).resolve()
    for p in psutil.process_iter(["pid", "name", "exe", "cmdline", "create_time"]):
        info = p.info
        name = (info.get("name") or "").lower()
        exe = info.get("exe")
        if name == target.name.lower():
            b.need(exe is not None, "A same-name reader has inaccessible identity")
            b.need(Path(exe).resolve() != target, "Original reader is already active; do not decode twice")
        if data and info.get("cmdline"):
            args = [str(x).lower() for x in info["cmdline"]]
            b.need(not ("--read" in args and str(Path(data).resolve()).lower() in args),
                   "A native reader already owns this data directory")


def environment(tag, root, calls):
    # Store the literal batch text rather than nesting call's quotes in the
    # Popen command-line list; old failed environment attempts stay protected.
    batch = root / "load_environment.cmd"
    with batch.open("xb") as f:
        f.write(("@echo off\r\ncall \"" + str(b.VCVARS) +
                 "\" x64 -vcvars_ver=14.36 >nul\r\n"
                 "if errorlevel 1 exit /b %errorlevel%\r\nset\r\n").encode("mbcs"))
    call, raw = b.invoke(tag + ".environment", [os.environ.get("COMSPEC", "C:/Windows/System32/cmd.exe"),
                         "/d", "/s", "/c", batch.name], root, os.environ.copy(), True)
    calls.append(call)
    env = {k.upper(): v for k, v in os.environ.items()}
    env.update((k.upper(), v) for k, v in (line.split("=", 1) for line in raw.decode("mbcs").splitlines()
               if "=" in line and not line.startswith("=")))
    env.pop("CL", None)
    env.pop("_CL_", None)
    b.need(env.get("VCTOOLSVERSION") == "14.36.32532", "Original reader compiler ABI changed")
    return env, b.stat(batch)


def build(ad):
    b.need(not BUILDROOT.exists() and not BUILD.exists(), "Existing reader build/failure is protected")
    for p in (BASE, COMPILE, LINK, NEUTRAL, b.VCVARS):
        ad.pin(p)
    base, compile_call, link_call = b.read(BASE), b.read(COMPILE), b.read(LINK)
    b.need(base.get("passed") is True and base.get("private_offline_reader") is True,
           "Retained successful pure-reader recipe required")
    old_object = Path(base["object"]["path"]).resolve()
    old_source = Path(base["source"]["path"]).resolve()
    old_args = compile_call["arguments"]
    link_args = link_call["arguments"]
    dependencies = [b.stat(x["path"]) for x in base["actual_archived_headers"] + base["runtime"]]
    dependencies += [b.stat(x) for x in link_args if not str(x).startswith("/")
                     and str(x).lower().endswith((".obj", ".lib"))
                     and Path(x).resolve() != old_object]
    for x in dependencies:
        ad.pin(x["path"])
    ad.pin(compile_call["program"]["path"])
    ad.pin(link_call["program"]["path"])
    BUILDROOT.mkdir()
    result = dict(stage=TAG + ".build", passed=False, root_admission=ad.entry,
                  actual_CPU_build_helper=ad.pin(Path(b.__file__)),
                  calls=[], solver_invocations=0, reader_invocations=0,
                  old_reader_or_loader_changed=False, physical_acceptance=False)
    try:
        env, batch = environment(TAG, BUILDROOT, result["calls"])
        obj = BUILDROOT / "reader.obj"
        dep = BUILDROOT / "dependencies.json"
        args, skip = [], False
        for x in old_args:
            if skip:
                skip = False
                continue
            if x.lower() == "/sourcedependencies":
                skip = True
            elif x.lower().startswith(("/fo", "/fd")) or (not x.startswith("/") and Path(x).resolve() == old_source):
                continue
            else:
                args.append(x)
        args += ["/Fo" + str(obj), "/Fd" + str(BUILDROOT / "reader.pdb"),
                 "/sourceDependencies", str(dep), str(CPP)]
        call, _ = b.invoke(TAG + ".compile", [compile_call["program"]["path"], *args], S / "VS", env)
        result["calls"].append(call)
        included = {Path(x).resolve() for x in b.read(dep)["Data"]["Includes"]}
        b.need(NEUTRAL.resolve() in included and all(not p.is_relative_to((S / "source").resolve()) for p in included),
               "Reader missed its retained neutral loader or consumed live source headers")
        args = []
        for x in link_args:
            if x.lower().endswith(".obj") and not x.startswith("/") and Path(x).resolve() == old_object:
                args.append(str(obj))
            elif x.lower().startswith("/out:"):
                args.append("/OUT:" + str(PROGRAM))
            elif x.lower().startswith(("/pdb:", "/implib:", "/ltcgout:", "/ilk:", "/pgd:")):
                prefix = x.split(":", 1)[0]
                ext = {"/pdb": ".pdb", "/implib": ".lib", "/ltcgout": ".iobj", "/ilk": ".ilk", "/pgd": ".pgd"}[prefix.lower()]
                args.append(prefix + ":" + str(BUILDROOT / ("reader" + ext)))
            else:
                args.append(x)
        args.append("/ILK:" + str(BUILDROOT / "reader.ilk"))
        call, _ = b.invoke(TAG + ".link", [link_call["program"]["path"], *args], S / "VS", env)
        result["calls"].append(call)
        copies = []
        for entry in base["runtime"]:
            target = BUILDROOT / Path(entry["path"]).name
            shutil.copy2(entry["path"], target)
            copies.append(dict(source=b.stat(entry["path"]), destination=b.stat(target)))
        for entry in dependencies:
            b.same(entry)
        ad.finish()
        result.update(passed=True, program=b.stat(PROGRAM), object=b.stat(obj),
                      compiler_dependencies=b.stat(dep), environment_batch=batch,
                      runtime=copies, original_dependencies=dependencies,
                      original_dependencies_stats_unchanged=True, SHA_scans=0)
    except Exception as exc:
        result["failure"] = str(exc)
        raise
    finally:
        b.write_new(BUILD, result)


def get_job(ad):
    job = ad.data["job"]
    b.need(job["window"] in WINDOWS and job["scheme"] in ("A", "B", "C")
           and job["configuration"] in ("DebugCPU", "ReleaseCPU")
           and re.fullmatch(r"[A-Za-z0-9_]+", job["tag"]), "Explicit bounded P1 job profile required")
    tag = job["tag"]
    job["native_output"] = str(T / "outputs" / (tag + "_native_r1"))
    for key in ("run_receipt", "call", "program", "plan", "run_out"):
        ad.pin(job[key]["path"])
    run, call = b.read(job["run_receipt"]["path"]), b.read(job["call"]["path"])
    b.need(run.get("passed") is True and run.get("scheme") == job["scheme"]
           and run.get("window") == job["window"] and run.get("configuration") == job["configuration"],
           "Original sealed successful scheme/configuration/window run required")
    b.need(Path(run["program"]["path"]).resolve() == Path(job["program"]["path"]).resolve()
           and Path(call["program"]["path"]).resolve() == Path(job["program"]["path"]).resolve()
           and Path(call["child"]["exe"]).resolve() == Path(job["program"]["path"]).resolve()
           and call.get("actual_Popen_wait_exit") == call.get("actual_Win32_exit") == 0,
           "Owned actual solver program/creation record and genuine exits differ")
    actual_env = run["actual_environment"].get("UPL_TPI_CPU_R1")
    b.need(actual_env in (None, "", "A") if job["scheme"] == "A" else actual_env == job["scheme"],
           "Actual owned pressure-scheme environment differs")
    output = Path(job["output_directory"]).resolve()
    data = Path(job["data"]).resolve()
    b.need(output == Path(run["output_directory"]).resolve() and data == output / "data"
           and output.is_relative_to((T / "outputs").resolve()), "Original job output/data ownership differs")
    for p in data.glob("Part_*.bi4"):
        ad.pin(p)
    return job


def read_native(ad):
    job = get_job(ad)
    check = L / (job["tag"] + ".native_r1.json")
    target = Path(job["native_output"])
    b.need(not check.exists() and not target.exists(), "Any existing native attempt/output is protected")
    ad.pin(BUILD)
    built = b.read(BUILD)
    b.need(built.get("passed") is True, "Reviewed completed private reader build required")
    ad.pin(PROGRAM)
    no_active_reader(PROGRAM, job["data"])
    result = dict(stage=TAG + ".read", passed=False, job=job, root_admission=ad.entry,
                  actual_CPU_build_helper=ad.pin(Path(b.__file__)),
                  reader_program=b.stat(PROGRAM), physical_acceptance=False,
                  solver_invocations=0, read_attempts=1)
    try:
        call, _ = b.invoke(job["tag"] + ".native_r1", [str(PROGRAM), "--read", "CPU", job["data"],
                           job["plan"]["path"], job["window"], str(target)], S / "VS", os.environ.copy())
        result["call"] = call
        done = b.read(target / "completion.json")
        w = WINDOWS[job["window"]]
        b.need(done.get("passed") is True and done["samples"] == w["frames"]
               and done["actual_end_s"] == w["end"] and done["post_open_frames"] == w["post"]
               and done["post_open_drained_particle_checks"] == 10 * w["post"],
               "Independent bounded native completion differs")
        ad.finish()
        result.update(passed=True, completion=b.stat(target / "completion.json"),
                      files=[b.stat(p) for p in target.iterdir() if p.is_file()],
                      pressure_scheme_not_proven_by_legacy_BI4_metadata=True)
    except Exception as exc:
        result["failure"] = str(exc)
        raise
    finally:
        b.write_new(check, result)


def hg_run(job):
    text = Path(job["run_out"]["path"]).read_text(encoding="utf-8-sig", errors="strict")
    steps = WINDOWS[job["window"]]["steps"]
    first = re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", text)
    second = re.search(r"SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)", text)
    guard = re.search(r"SoilHourglass: max\|sum\(M0\*Href\)\|=([^ ]+) max\|sum\(mi\*deltaAce\)\|=([^ ]+) max\(dt/tau\)=([^ ]+) spinbound=([^\r\n]+)", text)
    b.need(first and second and guard and tuple(map(int, first.groups())) == (2 * steps, steps, steps, 2 * steps)
           and tuple(map(int, second.groups())) == (steps + 1, steps - 1), "Original logical/actual HG phase/cache counters differ")
    net, actual, tau, spin = map(finite, guard.groups())
    b.need(min(net, actual, tau, spin) >= 0 and tau <= .2 and spin < .01,
           "Original HG stiffness/small-spin safety failed")
    return dict(forcecalls=2 * steps, predictorupdates=steps, correctorupdates=steps,
                ratecalls=2 * steps, ratecalculations=steps + 1, cachehits=steps - 1,
                max_reference_net=net, max_actual_float_net=actual, max_dt_tau=tau, spinbound=spin)


def load_plan(path, window):
    rows = list(csv.DictReader(Path(path).open(encoding="utf-8-sig", newline="")))
    w = WINDOWS[window]
    b.need(len(rows) == w["frames"] and int(rows[-1]["completed_steps"]) == w["steps"], "Exact bounded plan differs")
    clock = [0.]
    for _ in range(w["steps"]):
        clock.append(clock[-1] + DT)
    for part, row in enumerate(rows):
        n = int(row["completed_steps"])
        b.need(int(row["part"]) == part and bits(float(row["time_s"])) == bits(clock[n])
               and float(row["dt_s"]) == DT and int(row["saved_step"]) == (n - 1 if n else 0),
               "CSV exact scalar clock/zero-based step differs")
    return rows, clock


def prefix_A(ad, job):
    count = WINDOWS[job["window"]]["common_A"]
    current = Path(job["native_output"])
    done = RETAINED / "completion.json"
    ad.pin(done)
    b.need(b.read(done).get("passed") is True, "Retained full-A native receipt missing")
    declarations = {
        "original15.bin": ((1040, 15), 166408),
        "physical.bin": ((1000, 26), 208008),
        "common_j_theta.bin": ((1040, 2), 16648),
        "soil_n.bin": ((1000, 1), 8008),
        "clock.bin": (None, 28),
    }
    result = []
    for name, (shape, stride) in declarations.items():
        old, new = RETAINED / name, current / name
        ad.pin(old)
        ad.pin(new)
        hsize = 8 if shape is None else 12
        with old.open("rb") as a, new.open("rb") as z:
            ah, zh = a.read(hsize), z.read(hsize)
            av = struct.unpack("<" + "I" * (hsize // 4), ah)
            zv = struct.unpack("<" + "I" * (hsize // 4), zh)
            b.need((av == (1682, 28) and zv == (WINDOWS[job["window"]]["frames"], 28)) if shape is None
                   else av == (*shape, 1682) and zv == (*shape, WINDOWS[job["window"]]["frames"]),
                   "Original distinct binary declaration headers differ")
            for i in range(count):
                x, y = a.read(stride), z.read(stride)
                b.need(len(x) == len(y) == stride and x == y,
                       "Default-A exact retained payload differs: " + name + " part=" + str(i))
        result.append(dict(file=name, original_header=av, new_header=zv, shared_records=count,
                           header_rewritten=False, all_shared_record_bytes_equal=True))
    return result


def sidecar(ad, job, plan, clock):
    output = Path(job["output_directory"])
    paths = [output / ("UplTpiCpuR1" + suffix) for suffix in (".policy.json", ".csv", ".summary.json")]
    if job["scheme"] == "A":
        b.need(not any(p.exists() for p in paths), "Untaken default-A branch must not create TPI sidecars")
        return dict(expected_absent=True, native_scheme_evidence="Actual owned environment plus default-A branch")
    for p in paths:
        ad.pin(p)
    policy, summary = b.read(paths[0]), b.read(paths[2])
    scheme = "B_TPI_alpha_0p5_beta0" if job["scheme"] == "B" else "C_PPE_t_alpha0_beta0"
    alpha = .5 if job["scheme"] == "B" else 0.
    b.need(policy.get("stage") == "upl_tpi_cpu_r1" and policy.get("scheme") == scheme
           and policy.get("alpha") == alpha and policy.get("beta") == 0 and policy.get("M0") is True
           and policy.get("native_count") == 1040 and policy.get("soil_count") == 1000
           and policy.get("history_ID_owned") is True and policy.get("history_cold_start") is True
           and policy.get("half_equals_endpoint_history_guess") is True
           and policy.get("endpoint_source_clock_is_original_n") is True,
           "Actual private M0 scheme/history policy differs")
    for document in (policy, summary):
        b.need(document.get("full_restart_supported") is False and document.get("paper_literal_LF") is False
               and document.get("second_order_claimed") is False and document.get("true_implicit_solution") is False
               and document.get("physical_acceptance") is False, "Prototype limits must remain explicit")
    w = WINDOWS[job["window"]]
    b.need(summary.get("completed") is True and summary.get("scheme") == scheme and summary.get("alpha") == alpha
           and summary.get("beta") == 0 and summary.get("commits") == summary.get("endpoint_calls") == w["steps"]
           and summary.get("core_field_bit_checks") == 7000 * w["steps"]
           and summary.get("HG_readonly_snapshot_checks") == 2000 * w["steps"]
           and bits(float(summary["actual_end"])) == bits(w["end"]), "Actual completed lifecycle summary differs")
    rowcount, max_rounding = 0, 0.
    import numpy as np
    physical = Path(job["native_output"]) / "physical.bin"
    with paths[1].open(encoding="utf-8-sig", newline="") as f, physical.open("rb") as native:
        reader = csv.DictReader(f)
        b.need(reader.fieldnames == SIDECAR_COLUMNS, "Exact 28-column sidecar schema differs")
        b.need(struct.unpack("<III", native.read(12)) == (1000, 26, w["frames"]), "Case02 physical export header differs")
        for part, planned in enumerate(plan):
            n = int(planned["completed_steps"])
            actual_time = struct.unpack("<d", native.read(8))[0]
            state = np.frombuffer(native.read(1000 * 26 * 8), dtype="<f8").reshape(1000, 26)
            b.need(bits(actual_time) == bits(clock[n]), "Sidecar/native actual saved time differs")
            seen, source_count, endpoint_count, commit_count = set(), 0, 0, 0
            for _ in range(1000):
                row = next(reader, None)
                b.need(row is not None and list(row) == SIDECAR_COLUMNS, "Missing/extra sidecar columns or rows")
                values = {k: finite(v) for k, v in row.items()}
                k = int(values["native_id"])
                b.need(values["native_id"] == k and 40 <= k < 1040 and k not in seen and values["part"] == part,
                       "Sidecar native ownership/part duplicated or changed")
                seen.add(k)
                b.need(values["completed_step"] == values["commits"] == values["endpoint_calls"] == n
                       and values["source_step_zero_based"] == (n - 1 if n else 0)
                       and values["core_field_bit_checks"] == 7000 * n and values["hg_snapshot_checks"] == 2000 * n
                       and bits(values["source_time_s"]) == bits(clock[n - 1 if n else 0])
                       and bits(values["actual_save_time_s"]) == bits(clock[n]) and values["dt_s"] == DT,
                       "Saved actual source/commit/history counters or scalar clock differ")
                final, J = state[k - 40, 6], state[k - 40, 8]
                b.need(bits(values["final_float_Pa"], "f") == bits(final, "f")
                       and bits(values["Jfull"]) == bits(J), "Saved sidecar pressure/J differs from native state")
                flags = [values[x] for x in ("source_drained", "endpoint_drained", "commit_drained")]
                b.need(all(x in (0., 1.) for x in flags), "Dirichlet flags are not exact booleans")
                source_count += int(flags[0]); endpoint_count += int(flags[1]); commit_count += int(flags[2])
                if not n:
                    b.need(all(values[x] == 0. for x in ("pn_Pa", "previous_Pa", "prediction_double_Pa", "half_actual_float_Pa", "endpoint_q_actual_float_Pa", "S_1_per_m_s", "Rgamma_Pa_per_m_s", "raw_final_float_Pa", "final_float_Pa"))
                           and values["Jn"] == values["Jhalf"] == values["Jfull"] == 1., "Cold initial sidecar state differs")
                    rowcount += 1
                    continue
                prediction = values["pn_Pa"] if alpha == 0 else values["pn_Pa"] + alpha * (values["pn_Pa"] - values["previous_Pa"])
                b.need(bits(values["prediction_double_Pa"]) == bits(prediction), "Actual history pressure prediction differs")
                half = 0. if flags[0] else f32(prediction)
                b.need(bits(values["half_actual_float_Pa"], "f") == bits(half, "f"), "Mechanical half pressure history/Dirichlet differs")
                diagonal, residual, q = (values[x] for x in ("S_1_per_m_s", "Rgamma_Pa_per_m_s", "endpoint_q_actual_float_Pa"))
                if flags[1]:
                    b.need(diagonal == residual == 0., "A constrained endpoint row must not claim an elliptic residual")
                    raw = 0.
                else:
                    b.need(diagonal > 0., "Nonpositive/nonfinite elliptic diagonal is not masked or regularized")
                    exact = q + residual / diagonal
                    raw = f32(exact)
                    max_rounding = max(max_rounding, abs(raw - exact))
                b.need(bits(values["raw_final_float_Pa"], "f") == bits(raw, "f")
                       and bits(values["final_float_Pa"], "f") == bits(0. if flags[2] else raw, "f"),
                       "Actual beta0 float writeback or original final Dirichlet policy differs")
                Jexpected = values["Jn"] + DT * values["Jhalf"] * values["theta_half_for_J_1_per_s"]
                b.need(bits(values["Jfull"]) == bits(Jexpected), "Original single J corrector was advanced or reinterpreted")
                rowcount += 1
            expected_drain = 10 if n > 1600 else 0
            b.need(len(seen) == 1000 and source_count == endpoint_count == commit_count == expected_drain,
                   "All actual source/endpoint/commit Dirichlet owner counts differ")
        b.need(next(reader, None) is None and native.read(1) == b"", "Trailing sidecar or native records differ")
    return dict(rows=rowcount, expected_rows=1000 * w["frames"], actual_ID_owned_history=True,
                actual_M0_alpha=alpha, beta=0, max_actual_pressure_float_writeback_rounding_Pa=max_rounding,
                per_saved_row_formula_and_J_corrector_checked=True,
                unsaved_history_values_independently_observed=False,
                PorePressRate_is_legacy_scaled_endpoint_residual_not_actual_dpdt=True,
                no_finite_Kw_or_half_equivalence_claim=True)


def review(ad):
    job = get_job(ad)
    path = L / (job["tag"] + ".native_review_r1.json")
    b.need(not path.exists(), "Existing native review, including failure, is protected")
    native = L / (job["tag"] + ".native_r1.json")
    ad.pin(native)
    result = dict(stage=TAG + ".review", passed=False, root_admission=ad.entry, job=job,
                  actual_CPU_build_helper=ad.pin(Path(b.__file__)),
                  physical_acceptance=False, cross_model_5Pa_or_half_equivalence_gate=False,
                  solver_reader_or_build_invocations=0)
    try:
        b.need(b.read(native).get("passed") is True, "Independent native gate must pass before offline science review")
        for p in Path(job["native_output"]).iterdir():
            if p.is_file():
                ad.pin(p)
        plan, clock = load_plan(job["plan"]["path"], job["window"])
        result["HG_original_guards"] = hg_run(job)
        result["sidecar"] = sidecar(ad, job, plan, clock)
        if job["scheme"] == "A" and job["configuration"] == "ReleaseCPU":
            result["retained_A_exact_shared_records"] = prefix_A(ad, job)
            result["forced_final_is_not_shared_with_retained_A"] = True
        else:
            result["Debug_is_not_Release_bit_truth"] = job["configuration"] == "DebugCPU"
            result["cross_model_bit_equivalence_claimed"] = False
        ad.finish()
        result.update(passed=True, original_native_guards_not_relaxed=True,
                      no_interpolation_or_header_clock_rewrite=True,
                      full_cycle_theory_restart_or_physical_acceptance=False,
                      later_pressure_settlement_stress_comparison_required=True)
    except Exception as exc:
        result["failure"] = str(exc)
        raise
    finally:
        b.write_new(path, result)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["build", "read", "review"])
    p.add_argument("--execution-authorized", action="store_true")
    p.add_argument("--admission", required=True, type=Path)
    a = p.parse_args()
    b.need(a.execution_authorized, "One independently reviewed root action required")
    ad = Admission(a.action, a.admission)
    {"build": build, "read": read_native, "review": review}[a.action](ad)


if __name__ == "__main__":
    main()
