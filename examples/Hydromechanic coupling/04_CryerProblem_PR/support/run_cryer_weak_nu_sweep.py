"""Prepare, run and review the three additional fixed-reference Cryer profiles."""
import argparse
import csv
from datetime import datetime, timezone
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
from time import monotonic
import xml.etree.ElementTree as ET

from scipy.optimize import minimize_scalar

from plot_cryer_formal_four_nu_r1 import Reference
from run_cryer_weak_full import CASE, PACKAGE, MANIFEST_SHA, preflight, read_json, sha


ANGLES = {"045": .45, "010": .10, "020": .20}
DT = 2.**-19
DRAIN = 4096
DENSE_STRIDE = 32
DENSE_END_TV = Fraction(3, 25)
RUNTIME = CASE / "support/weak_nu_sweep_r1"
PROGRAM = RUNTIME / "weak_nu_full.exe"
TESTS = CASE / "tests"
RUNS = TESTS / "outputs/cryer_weak_nu_sweep_r1"
TAG = TESTS / "logs/cryer_weak_nu_sweep_r1"
BASE_XML = CASE / "CaseCryerWeakFull_nu030_1Tv_Def.xml"


def need(ok, message):
    if not ok:
        raise ValueError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, data, mode="x"):
    with path.open(mode, encoding="utf8") as stream:
        json.dump(data, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write("\n")


def fingerprint(path):
    stat = path.stat()
    return dict(bytes=stat.st_size, mtime_ns=stat.st_mtime_ns)


def define(group):
    nu = ANGLES[group]
    stem = f"CaseCryerWeakFull_nu{group}_1Tv"
    f = Fraction(str(nu))
    longitudinal = 2_000_000 * (1-f) / ((1+f)*(1-2*f))
    cv = longitudinal * Fraction(1, 100000) / 9810
    one_tv = Fraction(1, 400) / cv
    step_at = lambda tv: DRAIN + math.ceil(tv * one_tv * (2**19))
    scheduled = [*range(0,DRAIN+1,64), *(step_at(Fraction(i,200)) for i in range(1,201))]
    end_dense = step_at(DENSE_END_TV)
    dense = sorted(set(range(DRAIN,end_dense+1,DENSE_STRIDE)) | {DRAIN+1,end_dense})
    ref = Reference(nu, finite=False)
    peak = minimize_scalar(lambda t: -float(ref.pressure([t])[0]), method="bounded",
                           bounds=(float(one_tv)/200,float(one_tv)*float(DENSE_END_TV)),
                           options={"xatol": 1e-13})
    need(peak.success and 0.01*peak.x >= DENSE_STRIDE*DT, f"Inadequate peak sample cadence for nu={nu}")
    peak_native = DRAIN + round(peak.x/DT)
    saved = sorted(set(scheduled) | {DRAIN+1,DRAIN+64,DRAIN+128,peak_native})
    need(len(scheduled)==265 and len(saved)==269 and saved[-1]==scheduled[-1], "Unexpected state plan")
    return dict(group=group, nu=nu, stem=stem, dt_s=DT, drain_step=DRAIN, drainage_time_s=DRAIN*DT,
                tv_interval_s=float(one_tv/200), legacy_cv_m2_s=float(cv), end_s=saved[-1]*DT,
                end_step=saved[-1], saved_steps=saved, dense_steps=dense, dense_end_step=end_dense,
                theory_peak_tau_s=float(peak.x), theory_peak_pressure_pa=float(-peak.fun))


def definition(plan):
    tree = ET.parse(BASE_XML)
    case = tree.getroot()
    case.set("app", "Cryer weak-nu sweep r1")
    case.find("execution/special/soils/PRvs").set("value", str(plan["nu"]))
    weak = case.find("execution/special/weakfull")
    weak.set("checkpoint_states", "4")
    weak.set("dense_stride_steps", str(DENSE_STRIDE))
    weak.set("peak_end_Tv", str(float(DENSE_END_TV)))
    weak.set("comment", "Fixed reference weak GPU with four additional early or peak states. Dense peak fields are scalar reductions.")
    for key, value in (("TimeMax",plan["end_s"]),("TimeOut",plan["tv_interval_s"])):
        node = case.find(f'execution/parameters/parameter[@key="{key}"]')
        node.set("value", repr(value))
        if key == "TimeMax":
            node.set("comment", f'Step {plan["end_step"]}, first attaining drainage-relative Tv=1')
    case.findall("execution/special/timeout/tout")[-1].set("timeout",repr(plan["tv_interval_s"]))
    return tree


def physical_xml(element):
    detail = {k:v for k,v in element.attrib.items() if k not in ("comment","units_comment","_rem","app","date")}
    return element.tag, detail, [physical_xml(c) for c in element]


def prepare(plan, make_xml=False):
    xml = CASE / f'{plan["stem"]}_Def.xml'
    expected = definition(plan)
    if make_xml and not xml.exists():
        ET.indent(expected, space="    ")
        with xml.open("xb") as stream:
            expected.write(stream,encoding="utf-8",xml_declaration=True)
    need(xml.is_file() and physical_xml(ET.parse(xml).getroot()) == physical_xml(expected.getroot()),
         f"XML differs from the predefined weak sweep profile: {xml}")
    result = dict(plan, xml=str(xml), xml_sha256=sha(xml), frozen_package_sha256=MANIFEST_SHA)
    folder = RUNS / plan["group"]
    folder.mkdir(parents=True,exist_ok=True)
    receipt, steps = folder/"profile.json", folder/"steps.txt"
    listing = "".join(f"{step}\n" for step in plan["saved_steps"])
    if receipt.is_file():
        need(read_json(receipt)==result and steps.read_text(encoding="ascii")==listing,
             f"Previous profile or steps changed: {folder}")
    else:
        with steps.open("x",encoding="ascii") as stream:
            stream.write(listing)
        save(receipt,result)
    return result, steps


def check_program():
    built = read_json(RUNTIME/"build.json")
    need(built["returncode"]==0 and sha(PROGRAM)==built["program_sha256"], "Wrong weak sweep host program")
    manifest = read_json(PACKAGE/"manifest.json")
    files = {r["name"]:r for r in manifest["files"]}
    for path in RUNTIME.glob("*.dll"):
        need(path.name in files and sha(path)==files[path.name]["sha256"], f"Wrong runtime DLL: {path}")
    need((RUNTIME/"cryer_weak_window.dll").is_file(), "Frozen weak DLL is missing next to the host")
    return built


def output_path(plan):
    return CASE / f'{plan["stem"]}_GPU_out'


def solve(plan, steps, built, hardware):
    output = output_path(plan)
    need(not output.exists(), f"Preserve existing output: {output}")
    prefix = TAG.with_name(f'cryer_weak_nu{plan["group"]}_full_r1')
    argv = [str(PROGRAM), str(plan["nu"]), str(steps), str(plan["dense_end_step"]), str(output)]
    context = dict(argv=argv, cwd=str(PACKAGE), owner_pid=os.getpid(), utc=now(),
                   program_sha256=built["program_sha256"], profile_sha256=sha(steps.with_name("profile.json")),
                   gpu_inventory=hardware, output=str(output))
    save(prefix.with_suffix(".owner.json"), context)
    timer = monotonic()
    with prefix.with_suffix(".console.log").open("xb") as console:
        with subprocess.Popen(argv, cwd=PACKAGE, stdout=console, stderr=subprocess.STDOUT) as proc:
            start = dict(context, child_pid=proc.pid)
            save(prefix.with_suffix(".start.json"),start)
            print(f'nu={plan["nu"]}: GPU solver PID {proc.pid}',flush=True)
            code = proc.wait()
    save(prefix.with_suffix(".call.json"),dict(start,returncode=code,ended_utc=now()))
    need(code==0, f"Solver returned {code}; preserve partial output and {prefix.name}.console.log")
    need((output/"complete.txt").read_text().strip()=="full", "Missing native completion seal")
    with (output/"actual_clock.csv").open(encoding="utf8",newline="") as stream:
        actual = list(csv.DictReader(stream))
    need([int(r["step"]) for r in actual]==plan["saved_steps"] and
         all(float(r["time_s"])==int(r["step"])*DT for r in actual), "Owned saved clock differs from the plan")
    with (output/"material.csv").open(encoding="utf8",newline="") as stream:
        material, = csv.DictReader(stream)
    nu = struct.unpack("<f",struct.pack("<f",plan["nu"]))[0]
    mu, lam = 2e6/(2*(1+nu)), 2e6*nu/((1+nu)*(1-2*nu))
    sound = math.sqrt((lam+2*mu)/2100)
    need(float(material["nu_nominal"])==plan["nu"] and float(material["nu_effective"])==nu and
         float(material["dt_s"])==DT and math.isclose(float(material["mu_Pa"]),mu,rel_tol=2e-15) and
         math.isclose(float(material["lambda_Pa"]),lam,rel_tol=2e-15) and
         math.isclose(float(material["sound_m_s"]),sound,rel_tol=2e-15) and
         math.isclose(float(material["av_scale"]),sound/float(material["base_sound_m_s"]),rel_tol=2e-15),
         "Actual elastic and artificial-viscosity settings differ from the requested material")
    with (output/"closed_gate.csv").open(encoding="utf8",newline="") as stream:
        closed = list(csv.DictReader(stream))
    need([(int(r["step"]),int(r["passed"])) for r in closed]==[(s,1) for s in (3904,3968,4032,4096)],
         "Actual host did not pass the four original closed-state gates")
    names = {"complete.txt","actual_clock.csv","peak_history.csv","material.csv","closed_gate.csv",
             *(f"state_{s}.bin" for s in plan["saved_steps"])}
    need({p.name for p in output.iterdir()}==names, "Incomplete native state inventory")
    save(output/"server_run.json",dict(mode="full",returncode=code,nu=plan["nu"],
         package=MANIFEST_SHA, profile=plan, program_sha256=built["program_sha256"], gpu_inventory=hardware,
         material=material,elapsed_seconds=monotonic()-timer,utc_finished=now(),
         files=[dict(name=n, **fingerprint(output/n)) for n in sorted(names)]))


def completed_output(plan):
    output = output_path(plan)
    seal = read_json(output/"server_run.json")
    need(seal["profile"]==plan and seal["package"]==MANIFEST_SHA and seal["returncode"]==0,
         "The new material and schedule are not bound to a completed solve")
    return output


def postprocess(plan):
    from review_cryer_weak_nu import review

    output = completed_output(plan)
    review(PACKAGE,output,plan["nu"],plan["saved_steps"],plan["dense_steps"])


def execute(plans, args, built, hardware):
    errors = []
    for plan, steps in plans:
        stage = "solver"
        try:
            if not args.postprocess:
                out = output_path(plan)
                if out.exists():
                    completed_output(plan)
                else:
                    solve(plan,steps,built,hardware)
            if not args.solver_only:
                stage = "review"
                postprocess(plan)
        except Exception as exc:
            errors.append(dict(group=plan["group"],stage=stage,error=str(exc)))
            print(f'nu={plan["nu"]}, {stage}: {exc}',file=sys.stderr,flush=True)
    if not errors and not args.solver_only and len(plans)==len(ANGLES):
        try:
            subprocess.run([sys.executable,"-B","-X","utf8",str(CASE/"support/plot_cryer_weak_nu_sweep.py")],
                           cwd=CASE,check=True)
        except subprocess.CalledProcessError as exc:
            errors.append(dict(stage="compare",error=str(exc)))
    return errors


def owned(args, plans, built, hardware):
    thread = os.environ.get("CODEX_THREAD_ID")
    need(thread and args.owner_cli.is_file(), "Direct ownership requires the active thread and its CLI")
    save(TAG.with_suffix(".owner.json"),dict(pid=os.getpid(),utc=now(),groups=[p[0]["group"] for p in plans]))
    errors = execute(plans,args,built,hardware)
    terminal = TAG.with_suffix(".terminal.json")
    save(terminal,dict(errors=errors,utc=now(),results=[str(output_path(p)) for p,_ in plans]))
    message = (f"已授权 Cryer 多泊松比 weak-full 同线程终态：{terminal}。核实各组真实退出、原生与图表，"
               "保存失败和原始输出；仅离线补派生，禁止重复求解、重发或重新布防。评估达到精度标准后才考虑公共 XML 开关。")
    save(TAG.with_suffix(".queue_attempt.json"),dict(utc=now(),terminal=str(terminal)))
    try:
        result = dict(returncode=subprocess.run([str(args.owner_cli),"queue","--thread",thread,"--message",message],
                      cwd=CASE,capture_output=True,timeout=45).returncode)
    except (OSError,subprocess.TimeoutExpired) as exc:
        result = dict(delivery="unknown",error=str(exc))
    save(TAG.with_suffix(".queue_result.json"),result)
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", choices=("all",*ANGLES), default="all")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--prepare",action="store_true",help="Write and validate new XML and deterministic save plans")
    modes.add_argument("--check-only",action="store_true",help="Verify the frozen DLL/operator pack and save plans")
    modes.add_argument("--postprocess",action="store_true",help="Only review successful native outputs")
    modes.add_argument("--solver-only",action="store_true")
    parser.add_argument("--owner-cli",type=Path)
    args = parser.parse_args()
    need(not args.owner_cli or not (args.prepare or args.check_only or args.postprocess), "Invalid owned solve mode")
    preflight(verify_payload=not args.postprocess and not args.prepare)
    plans = [prepare(define(group),args.prepare) for group in (ANGLES if args.group=="all" else (args.group,))]
    if args.prepare or args.check_only:
        if args.check_only:
            check_program()
        for p,_ in plans:
            print(f'nu={p["nu"]}: {p["end_step"]} steps, {len(p["saved_steps"])} full states, '
                  f'{len(p["dense_steps"])} dense samples, endpoint={p["end_s"]:.12g} s',flush=True)
        return 0
    built = None if args.postprocess else check_program()
    hardware = None if args.postprocess else subprocess.check_output(
        ["nvidia-smi","--query-gpu=name,driver_version,memory.total","--format=csv"],text=True).splitlines()
    return int(bool(owned(args,plans,built,hardware) if args.owner_cli else execute(plans,args,built,hardware)))


if __name__ == "__main__":
    raise SystemExit(main())
