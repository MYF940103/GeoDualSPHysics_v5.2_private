"""Independent C02 full2Tv native build/read/review; each root-admitted, never a solver."""
from __future__ import annotations
import argparse
import csv
import math
from fractions import Fraction
import os
from pathlib import Path
import re
import shutil
import struct
import upl_tpi_cpu_build_r2 as b

T, L, S = b.T, b.L, b.S
TAG = "upl_tpi_gpu_full2tv_native_r1"
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
FULL_TAG = "upl_tpi_gpu_Release_B_full2tv_r1"
SOURCE_BUILD = L / "upl_tpi_gpu_full2tv_Release_r1.build.json"
SOURCE_PREP = L / "upl_tpi_gpu_full2tv_r1.prepare.json"
RETAINED = T / "outputs/upl_tpi_gpu_Release_B_startup015_r1_native_r4"
SHORT_REVIEW = L / "upl_tpi_gpu_Release_B_startup015_r1.native_review_r5.json"
DT = 6.250143051147461e-6
WINDOWS = {"full2tv": dict(steps=11661219,frames=1682,end=72.88428689946836,post=1564)}
PTX_TAG = "upl_tpi_gpu_Release_r3.raw_write_ptx_r1"
PTX_BINDING = L / (PTX_TAG + ".binding.json")
PTX_COMPILE = L / "upl_tpi_gpu_Release_r3.JSphGpu_ker.call.json"
SOURCE_FIXTURE_R2 = "UplTpiGpuSourceRoleFixtureR2: source_cases=8 owner_role_cases=8 device_cases_checked=16 device_kernel_completed=true private_error_bits=0"
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
                  actual_common_reader_build_helper=ad.pin(Path(b.__file__)),
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

def pressure_f32_ftz(value):
    """PTX cvt.rn.ftz.f32.f64: RN float32, then signed subnormal-result FTZ."""
    rounded = f32(value)
    return math.copysign(0., rounded) if 0. < abs(rounded) < 2.**-126 else rounded

def ptx_evidence(ad, job):
    # Read the one genuinely dumped new object; no cuobjdump/reader/program invocation.
    ad.pin(PTX_BINDING); binding = b.read(PTX_BINDING)
    b.need(binding.get("stage") == PTX_TAG + ".binding" and binding.get("passed") is True and
           binding.get("object_and_tool_stat_unchanged") is True and
           all(binding.get(k) == 0 for k in ("solver_invocations", "GPU_kernel_invocations", "reader_invocations", "build_invocations", "SHA_scans")),
           "Actual read-only PTX object/tool evidence is required")
    for key in ("input_object", "actual_tool", "call"):
        ad.pin(binding[key]["path"]); b.same(binding[key])
    call = b.read(binding["call"]["path"])
    b.need(call.get("passed") is True and call.get("actual_Popen_wait_exit") == call.get("actual_Win32_exit") == 0 and
           call["arguments"] == ["--dump-ptx", binding["input_object"]["path"]] and
           Path(call["program"]["path"]).resolve() == Path(binding["actual_tool"]["path"]).resolve() and
           Path(call["program"]["path"]).name.lower() == "cuobjdump.exe",
           "Actual cuobjdump command/exits differ")
    ad.pin(call["log"]["path"]); b.same(call["log"])
    run = b.read(job["run_receipt"]["path"]); ad.pin(run["source_build"]["path"])
    build = b.read(run["source_build"]["path"])
    obj = [e for e in build["objects"] if Path(e["path"]).resolve() == Path(binding["input_object"]["path"]).resolve()]
    b.need(len(obj) == 1 and {k: obj[0][k] for k in ("path", "bytes", "mtime_ns")} == binding["input_object"],
           "This actual solver build does not contain the dumped CUDA object")
    ad.pin(PTX_COMPILE); compiled = b.read(PTX_COMPILE)
    args = compiled["arguments"]
    b.need(compiled.get("passed") is True and compiled.get("actual_Popen_wait_exit") == compiled.get("actual_Win32_exit") == 0 and
           "-use_fast_math" in args and args[args.index("-o")+1] == binding["input_object"]["path"],
           "Actual CUDA compile flags/output do not match the PTX object")
    lines = Path(call["log"]["path"]).read_text(encoding="utf-8", errors="strict").splitlines()
    found = {}
    for name in ("BeginRowsKernel", "GuessKernel", "PrepareKernel"):
        starts = [i for i, line in enumerate(lines) if ".entry" in line and name in line]
        b.need(len(starts) == 1, "Actual private PTX entry is not unique: " + name)
        start = starts[0]
        end = next((i for i in range(start+1, len(lines)) if ".entry" in lines[i]), len(lines))
        body = lines[start:end]
        casts = [start+i+1 for i, line in enumerate(body) if "cvt.rn.ftz.f32.f64" in line]
        b.need(len(casts) == 1, "Actual pressure conversion is not one RN-f32 FTZ: " + name)
        input_casts = [start+i+1 for i, line in enumerate(body) if "cvt.ftz.f64.f32" in line]
        b.need(len(input_casts) == {"BeginRowsKernel": 2, "GuessKernel": 0, "PrepareKernel": 1}[name],
               "Actual float-input FTZ conversion count differs: " + name)
        found[name] = dict(entry_line=start+1, pressure_cast_line=casts[0], float_input_FTZ_lines=input_casts)
        if name == "PrepareKernel":
            b.need(sum("div.rn.f64" in x for x in body) == 1 and sum("add.rn.f64" in x for x in body) == 1 and
                   not any("div.approx" in x or "rcp." in x or "fma." in x for x in body),
                   "Actual raw correction must retain separate RN-double divide/add, not an inferred FMA/approx path")
            found[name].update(double_divide_line=start+next(i for i,x in enumerate(body) if "div.rn.f64" in x)+1,
                               double_add_line=start+next(i for i,x in enumerate(body) if "add.rn.f64" in x)+1)
    return dict(actual_binding=ad.pin(PTX_BINDING), actual_call=ad.pin(binding["call"]["path"]), actual_PTX=ad.pin(call["log"]["path"]),
                entry_instructions=found, model="RN_f32_then_sign_preserving_result_FTZ", pressure_added_ULP_tolerance=0,
                double_prediction_and_J_arithmetic_changed=False, solver_reader_or_tool_invocations=0)

def pin_reader(ad):
    """Bind the actual full reader program/runtime; never substitute an unbound executable."""
    ad.pin(BUILD); built = b.read(BUILD)
    b.need(built.get("stage") == TAG + ".build" and built.get("passed") is True and
           built.get("solver_invocations") == built.get("reader_invocations") == 0 and
           built.get("old_reader_or_loader_changed") is False and
           built.get("original_dependencies_stats_unchanged") is True,
           "Original completed full-reader implementation build is required")
    ad.pin(PROGRAM); b.same(built["program"])
    b.need(Path(built["program"]["path"]).resolve() == PROGRAM.resolve(),
           "Actual full-reader program path differs")
    for entry in built["runtime"]:
        ad.pin(entry["destination"]["path"]); b.same(entry["destination"])
    return built


def get_job(ad):
    job = dict(ad.data["job"])
    b.need((job.get("tag"),job.get("configuration"),job.get("scheme"),job.get("window")) ==
           (FULL_TAG,"Release","B","full2tv"), "Only the original single fresh-B full2Tv job is admitted")
    job["native_output"] = str(T / "outputs" / (FULL_TAG + "_native_full_r1"))
    for key in ("run_receipt","call","program","plan","run_out"):
        ad.pin(job[key]["path"]); b.same(job[key])
    start_path = L / (FULL_TAG + ".start.json"); ad.pin(start_path)
    run, call, start = b.read(job["run_receipt"]["path"]), b.read(job["call"]["path"]), b.read(start_path)
    b.need(run.get("passed") is True and run.get("stage") == "upl_tpi_gpu_full2tv_run_r1.run" and call.get("passed") is True and
           (run.get("tag"),run.get("configuration"),run.get("scheme"),run.get("window")) == (FULL_TAG,"Release","B","full2tv"),
           "A genuinely completed, sealed full-run owner result is required")
    program = Path(job["program"]["path"]).resolve()
    for e in (run["program"],call["target_program"],start["program"]): b.same(e)
    b.need(all(Path(e["path"]).resolve() == program for e in (run["program"],call["target_program"],start["program"])) and
           Path(call["target"]["exe"]).resolve() == program and call.get("tool_is_solver") is True and
           call.get("actual_Popen_wait_exit") == call.get("actual_Win32_exit") == call.get("target_actual_Win32_exit") == 0 and
           call.get("target_handle_acquired_before_wait") is True and call["target"] == start["target"] == run["target"] and
           call["target"]["argv"][1:] == call["target_arguments"] == run["arguments"] and
           abs((call["target_creation_FILETIME_ticks"]-116444736000000000)/1e7-call["target"]["created"]) <= 1e-6,
           "Original direct-GPU ownership, argv, creation time or native exits differ")
    b.need(run["actual_environment"] == call["actual_environment"] == {"UPL_TPI_GPU_R1":"B"}, "Actual full-run B selector differs")
    for key, required in (("source_build",SOURCE_BUILD),("prepared",SOURCE_PREP)):
        ad.pin(run[key]["path"]); b.same(run[key]); b.need(Path(run[key]["path"]).resolve() == required.resolve(), "Full source/build identity differs")
    built, prepared = b.read(SOURCE_BUILD), b.read(SOURCE_PREP)
    b.need(built.get("passed") is True and built.get("configuration") == "Release" and built.get("object_count") == 111 and
           built.get("replacement_object_count") == 1 and built.get("retained_effective_object_count") == 110 and
           Path(built["program"]["path"]).resolve() == program and prepared.get("passed") is True and
           prepared.get("other268_files_byte_identical") is True and prepared.get("helper_h_and_cuh_byte_identical") is True and
           Path(built["source_prepare"]["path"]).resolve() == SOURCE_PREP.resolve(), "Actual one-host source-window-only program required")
    b.same(built["program"]); b.same(built["source_prepare"])
    output, data = Path(job["output_directory"]).resolve(), Path(job["data"]).resolve()
    b.need(output == (T/"outputs"/FULL_TAG).resolve() == Path(run["output_directory"]).resolve() and data == output/"data" and
           Path(job["run_out"]["path"]).resolve() == output/"Run.out", "Original full output/data identity differs")
    text = Path(job["run_out"]["path"]).read_text(encoding="utf-8-sig"); ad.pin(call["log"]["path"])
    console = Path(call["log"]["path"]).read_text(encoding="utf-8-sig",errors="replace")
    b.need('RunMode="Stable - Pos-Cell - Single-GPU"' in text and console.count(SOURCE_FIXTURE_R2) == 1,
           "Actual GPU backend/once-only16-device-fixture proof differs")
    for p in data.glob("Part_*.bi4"): ad.pin(p)
    return job


def read_native(ad):
    job = get_job(ad)
    check = L / (job["tag"] + ".native_full_r1.json")
    target = Path(job["native_output"])
    b.need(not check.exists() and not target.exists(), "Any existing native attempt/output is protected")
    pin_reader(ad)
    no_active_reader(PROGRAM, job["data"])
    result = dict(stage=TAG + ".read", passed=False, job=job, root_admission=ad.entry,
                  actual_common_reader_build_helper=ad.pin(Path(b.__file__)),
                  reader_program=b.stat(PROGRAM), physical_acceptance=False,
                  solver_invocations=0, read_attempts=1)
    try:
        call, _ = b.invoke(job["tag"] + ".native_full_r1", [str(PROGRAM), "--read", "GPU", job["data"],
                           job["plan"]["path"], job["window"], str(target)], S / "VS", os.environ.copy())
        result["call"] = call
        done = b.read(target / "completion.json")
        w = WINDOWS[job["window"]]
        b.need(done.get("passed") is True and done["samples"] == w["frames"]
               and done.get("stage") == TAG and done.get("backend") == "GPU_full2Tv_private"
               and done.get("window") == job["window"] and done.get("native_total_arrays") == 22
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
    with Path(path).open(encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
    w=WINDOWS[window]
    b.need(len(rows)==w["frames"] and int(rows[-1]["completed_steps"])==w["steps"], "Full plan coverage differs")
    # Sparse exact scalar replay: keep only actual saved n and source n-1,
    # not an 11-million-element Python float list and never n*dt substitution.
    wanted=sorted({0,*[int(r["completed_steps"]) for r in rows],*[max(0,int(r["completed_steps"])-1) for r in rows]})
    clock={};actual=0.;previous=0
    for stop in wanted:
        for _ in range(previous,stop): actual+=DT
        clock[stop]=actual;previous=stop
    for part,row in enumerate(rows):
        n=int(row["completed_steps"])
        b.need(int(row["part"])==part and bits(float(row["time_s"]))==bits(clock[n]) and float(row["dt_s"])==DT and
               int(row["saved_step"])==(n-1 if n else 0), "Exact original scalar clock/zero-based saved Step differs")
    b.need(bits(clock[w["steps"]])==bits(w["end"]), "Full scalar endpoint differs")
    return rows,clock


def prefix_B_short(ad, job):
    """True same-backend records joined by actual time bits AND native Step.

    Five exports cover their declared fields only, never all22 raw-array proof.
    Original distinct headers remain intact; no assumed final-frame sharing.
    """
    current = Path(job["native_output"])
    for p in (SHORT_REVIEW, RETAINED / "completion.json"): ad.pin(p)
    oldreview, olddone = b.read(SHORT_REVIEW), b.read(RETAINED / "completion.json")
    b.need(oldreview.get("passed") is True and oldreview.get("stage") == "upl_tpi_gpu_native_r5.review" and
           oldreview["job"].get("scheme") == "B" and oldreview["job"].get("window") == "startup015" and
           olddone.get("passed") is True and olddone.get("samples") == 344 and olddone.get("backend") == "GPU_P1_private",
           "The retained same-dt B startup native review must already pass")
    def read_clock(path, expected):
        ad.pin(path)
        with path.open("rb") as f:
            b.need(struct.unpack("<II", f.read(8)) == (expected, 28), "Original clock declaration differs")
            rows = [f.read(28) for _ in range(expected)]
            b.need(all(len(x) == 28 for x in rows) and f.read(1) == b"", "Clock payload truncated/extra")
        keys = [(x[:8], struct.unpack_from("<I", x, 8)[0]) for x in rows]
        b.need(len(set(keys)) == len(keys), "Duplicate actual time/step native key")
        return rows, keys
    oldcount, newcount = int(olddone["samples"]), WINDOWS[job["window"]]["frames"]
    oldclock, oldkeys = read_clock(RETAINED / "clock.bin", oldcount)
    newclock, newkeys = read_clock(current / "clock.bin", newcount)
    lookup = {key: i for i, key in enumerate(newkeys)}
    shared = [(i, lookup[key]) for i, key in enumerate(oldkeys) if key in lookup]
    b.need(shared == [(i,i) for i in range(343)] and oldkeys[-1] not in lookup and
           oldkeys[-1][1] == 23999 and newkeys[343][1] == 24003,
           "Exactly343 true B prefix states required; short forced24000 is not full24004")
    results = []
    declarations = {"original15.bin": ((1040, 15), 166408), "physical.bin": ((1000, 26), 208008),
                    "common_j_theta.bin": ((1040, 2), 16648), "soil_n.bin": ((1000, 1), 8008),
                    "clock.bin": (None, 28)}
    for name, (shape, stride) in declarations.items():
        old, new = RETAINED / name, current / name
        ad.pin(old); ad.pin(new); hsize = 8 if shape is None else 12
        with old.open("rb") as a, new.open("rb") as z:
            ah = struct.unpack("<" + "I" * (hsize // 4), a.read(hsize))
            zh = struct.unpack("<" + "I" * (hsize // 4), z.read(hsize))
            b.need((ah == (oldcount, 28) and zh == (newcount, 28)) if shape is None else
                   ah == (*shape, oldcount) and zh == (*shape, newcount), "Original separate binary headers differ")
            for oi, ni in shared:
                a.seek(hsize + stride * oi); z.seek(hsize + stride * ni)
                x, y = a.read(stride), z.read(stride)
                b.need(len(x) == len(y) == stride and x == y,
                       "Same-B actual-time/step shared exported payload differs: " + name + " old/new=" + str((oi, ni)))
        results.append(dict(file=name, original_header=ah, new_header=zh, shared_records=len(shared),
                            all_shared_export_record_bytes_equal=True, header_rewritten=False))
    return dict(files=results, actual_shared_old_new_indices=shared,
                old_unshared_indices=[i for i, x in enumerate(oldkeys) if x not in lookup],
                record_join_uses_actual_time_bits_and_saved_Step=True,
                final_record_preclassified_as_shared=False, all22_raw_array_bit_proof=False)

def sidecar(ad, job, plan, clock):
    output = Path(job["output_directory"])
    paths = [output / ("UplTpiGpuR1" + suffix) for suffix in (".policy.json", ".csv", ".summary.json")]
    if job["scheme"] == "A":
        b.need(not any(p.exists() for p in paths), "Untaken default-A branch must not create TPI sidecars")
        return dict(expected_absent=True, native_scheme_evidence="Actual owned environment plus default-A branch")
    for p in paths:
        ad.pin(p)
    policy, summary = b.read(paths[0]), b.read(paths[2])
    scheme = "B_TPI_alpha_0p5_beta0" if job["scheme"] == "B" else "C_PPE_t_alpha0_beta0"
    alpha = .5 if job["scheme"] == "B" else 0.
    b.need(policy.get("stage") == "upl_tpi_gpu_r1" and policy.get("scheme") == scheme
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
           and summary.get("PorePressRate_is_legacy_scaled_residual_not_dpdt") is True
           and bits(float(summary["actual_end"])) == bits(w["end"]), "Actual completed lifecycle summary differs")
    rowcount, max_rounding = 0, 0.
    observed_input_subnormals = dict(pn=0, previous=0, endpoint_q=0)
    J_nonfused_matches = J_fused_matches = J_both_matches = 0
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
                # PTX cvt.ftz.f64.f32 preserves normal float inputs but flushes
                # a subnormal float to signed zero BEFORE ordinary RN-double math.
                for label, field in (("pn", "pn_Pa"), ("previous", "previous_Pa"), ("endpoint_q", "endpoint_q_actual_float_Pa")):
                    observed = f32(values[field])
                    observed_input_subnormals[label] += int(0. < abs(observed) < 2.**-126)
                pn_input, previous_input = pressure_f32_ftz(values["pn_Pa"]), pressure_f32_ftz(values["previous_Pa"])
                prediction = pn_input if alpha == 0 else pn_input + alpha * (pn_input - previous_input)
                b.need(bits(values["prediction_double_Pa"]) == bits(prediction), "Actual history pressure prediction differs")
                half = 0. if flags[0] else pressure_f32_ftz(prediction)
                b.need(bits(values["half_actual_float_Pa"], "f") == bits(half, "f"), "Mechanical half pressure history/Dirichlet differs")
                diagonal, residual, q = (values[x] for x in ("S_1_per_m_s", "Rgamma_Pa_per_m_s", "endpoint_q_actual_float_Pa"))
                b.need(bits(q, "f") == bits(0. if flags[1] else pressure_f32_ftz(prediction), "f"),
                       "Actual endpoint q is not the same history prediction under original endpoint BC")
                if flags[1]:
                    b.need(diagonal == residual == 0., "A constrained endpoint row must not claim an elliptic residual")
                    raw = 0.
                else:
                    b.need(diagonal > 0., "Nonpositive/nonfinite elliptic diagonal is not masked or regularized")
                    q_input = pressure_f32_ftz(q)  # Actual cvt.ftz.f64.f32 before div.rn/add.rn.
                    exact = q_input + residual / diagonal
                    raw = pressure_f32_ftz(exact)
                    max_rounding = max(max_rounding, abs(raw - exact))
                b.need(bits(values["raw_final_float_Pa"], "f") == bits(raw, "f")
                       and bits(values["final_float_Pa"], "f") == bits(0. if flags[2] else raw, "f"),
                       "Actual beta0 float writeback or original final Dirichlet policy differs")
                # Preserve original CUDA -use_fast_math/fmad. Original expression
                # is left-associated DT*Jhalf*theta followed by add to Jn.
                # First product is rounded binary64. Final multiply/add can be
                # separate or legally fused, both replayed exactly, no ULP slack.
                product = DT * values["Jhalf"]
                plain = values["Jn"] + product * values["theta_half_for_J_1_per_s"]
                fused = float(Fraction.from_float(values["Jn"]) + Fraction.from_float(product) *
                              Fraction.from_float(values["theta_half_for_J_1_per_s"]))
                nmatch = bits(values["Jfull"]) == bits(plain)
                fmatch = bits(values["Jfull"]) == bits(fused)
                b.need(nmatch or fmatch, "Original CUDA single J expression matches neither reviewed exact compiler path")
                J_nonfused_matches += int(nmatch); J_fused_matches += int(fmatch)
                J_both_matches += int(nmatch and fmatch)
                rowcount += 1
            expected_drain = 10 if n > 1600 else 0
            b.need(len(seen) == 1000 and source_count == endpoint_count == commit_count == expected_drain,
                   "All actual source/endpoint/commit Dirichlet owner counts differ")
        b.need(next(reader, None) is None and native.read(1) == b"", "Trailing sidecar or native records differ")
    return dict(rows=rowcount, expected_rows=1000 * w["frames"], actual_ID_owned_history=True,
                actual_M0_alpha=alpha, beta=0, max_actual_pressure_float_writeback_rounding_Pa=max_rounding,
                per_saved_row_formula_and_J_corrector_checked=True,
                J_noninitial_rows_checked=J_nonfused_matches + J_fused_matches - J_both_matches,
                J_nonfused_path_matches=J_nonfused_matches, J_fused_path_matches=J_fused_matches,
                J_both_paths_match=J_both_matches, J_added_ULP_tolerance=0,
                original_CUDA_fast_math_and_fmad_preserved=True,
                actual_pressure_cast_RN_f32_signed_FTZ=True, actual_float_input_to_double_signed_FTZ=True,
                observed_nonzero_subnormal_pressure_inputs=observed_input_subnormals,
                input_subnormal_count_is_descriptive_not_a_physical_limit=True, pressure_added_ULP_tolerance=0,
                unsaved_history_values_independently_observed=False,
                PorePressRate_is_legacy_scaled_endpoint_residual_not_actual_dpdt=True,
                no_finite_Kw_or_half_equivalence_claim=True)

def review(ad):
    job=get_job(ad);path=L/(FULL_TAG+".native_review_full_r1.json")
    b.need(not path.exists(),"Existing full review/partial is protected")
    native=L/(FULL_TAG+".native_full_r1.json");ad.pin(native)
    pin_reader(ad)
    result=dict(stage=TAG+".review",passed=False,root_admission=ad.entry,job=job,physical_acceptance=False,
                solver_reader_or_build_invocations=0,cross_model_5Pa_or_half_equivalence_gate=False)
    try:
        b.need(b.read(native).get("passed") is True,"Unique independently admitted full native must pass first")
        for p in Path(job["native_output"]).iterdir():
            if p.is_file():ad.pin(p)
        plan,clock=load_plan(job["plan"]["path"],job["window"])
        result["actual_pressure_cast_PTX"]=ptx_evidence(ad,job)
        result["HG_original_guards"]=hg_run(job)
        result["sidecar"]=sidecar(ad,job,plan,clock)
        result["same_B_short_actual_prefix"]=prefix_B_short(ad,job)
        ad.finish()
        result.update(passed=True,original_native_guards_not_relaxed=True,no_interpolation_or_header_clock_rewrite=True,
            full_pressure_settlement_stress_mode_and_theory_analysis_pending=True,all22_prefix_raw_array_bit_proof=False,
            full_cycle_theory_restart_or_physical_acceptance=False)
    except Exception as exc:result["failure"]=str(exc);raise
    finally:b.write_new(path,result)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("action",choices=["build","read","review"])
    p.add_argument("--execution-authorized",action="store_true");p.add_argument("--admission",required=True,type=Path)
    a=p.parse_args();b.need(a.execution_authorized,"Separate exact-action root admission required")
    ad=Admission(a.action,a.admission);{"build":build,"read":read_native,"review":review}[a.action](ad)


if __name__=="__main__":main()
