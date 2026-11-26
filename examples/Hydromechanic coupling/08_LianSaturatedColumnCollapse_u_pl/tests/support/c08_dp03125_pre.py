"""Prepare and check the independently initialized C08 dp=0.03125 m preload."""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np

from c08_psi25_tpi_run import CASE, TESTS, identity, now, record
from c08_psi25_tpi_native import PRE, require, verify_source_material
from lian_collapse_geometry_review_r1 import vtk
from upl_tpi_partial_bi4_r1 import read

TAG = "c08_dp03125_pre"
DP, DT = .03125, 5e-6
MATERIAL_COUNT = 8192
DEFINITION = TESTS/"configs"/f"{TAG}_r2_Def.xml"
PREVIOUS_DEF = TESTS/"configs/c08_h18_wend_branches_psi2p5_pre_r1_Def.xml"
SAVED_CLOCKS = TESTS/"configs/c08_h18_wend_branches_psi2p5_pre_r1.steps.csv"
BUILD = TESTS/"outputs/c08_preload_schema2_Release_r1"
PROGRAM = BUILD/"DualSPHysics5.2_GEO_win64.exe"
GENCASE = BUILD/"GenCase_win64.exe"
REFERENCE = PRE.with_name("Part_0000.bi4")
GEN = TESTS/"outputs"/(TAG+"_seed_r4")
SEED = GEN/TAG
LOG = TESTS/"logs"
STEPS = {"smoke": 4000, "preload": 2_000_000}
PRELOAD_TAG = TAG+"_preload_r1"


def load(path):
    return json.loads(path.read_text(encoding="utf8"))


def call(label, argv, output):
    label = LOG/label
    ready = dict(command=[str(x) for x in argv], program=identity(argv[0]), owner_pid=os.getpid(),
                 output=str(output), start_utc=now())
    require(not label.with_suffix(".start.json").exists() and not label.with_suffix(".call.json").exists(),
            f"Retained call for {label}")
    with label.with_suffix(".console.log").open("xb") as handle:
        with subprocess.Popen(ready["command"], cwd=CASE, stdout=handle, stderr=subprocess.STDOUT) as child:
            ready["child_pid"] = child.pid
            record(label.with_suffix(".start.json"), ready)
            rc = child.wait()
    record(label.with_suffix(".call.json"), dict(ready, returncode=rc, end_utc=now()))
    require(rc==0, f"{argv[0].name} exit {rc}, see {label.with_suffix('.console.log')}")


def prepare():
    coarse = ET.parse(PREVIOUS_DEF)
    refined = ET.parse(DEFINITION)
    cell = coarse.find(".//newvarcte[@Dp]")
    target = refined.find(".//newvarcte[@Dp]")
    require(float(cell.attrib["Dp"])==.04 and float(target.attrib["Dp"])==DP, "Wrong spacing")
    cell.attrib.update(target.attrib)
    for coarse_box, refined_box in zip(coarse.findall(".//mainlist/drawbox")[:3],
                                       refined.findall(".//mainlist/drawbox")[:3], strict=True):
        for element in ("point", "size"):
            coarse_box.find(element).attrib.update(refined_box.find(element).attrib)
    for doc in (coarse,refined):
        for element in doc.iter():
            if element.text is not None and not element.text.strip():
                element.text = None
            if element.tail is not None and not element.tail.strip():
                element.tail = None
    require(ET.tostring(coarse.getroot())==ET.tostring(refined.getroot()),
            "Preload inputs differ outside the particle spacing and boundary lattice")
    original_run = load(LOG/"c08_h18_wend_branches_psi2p5_pre_r1.call.json")
    require(original_run["actual_solver_Win32_exit"]==0 and
            Path(original_run["actual_solver"]["exe"])==PROGRAM, "Original preload executable mismatch")
    original_owner = load(LOG/"c08_h18_wend_branches_psi2p5_pre_r1.owner_admission.json")
    original_program = original_owner["program"]
    observed = identity(PROGRAM)
    require(all(observed[key]==original_program[key] for key in ("path", "bytes", "mtime_ns")),
            "The historical preload program revision changed")
    GEN.mkdir()
    call(TAG+"_gencase_r4", [GENCASE, DEFINITION.with_suffix(""), SEED, "-save:all"], GEN)
    generated = ET.parse(SEED.with_suffix(".xml"))
    parts = generated.find("execution/particles")
    reg = [(int(e.attrib["mkbound"]),int(e.attrib["begin"]),int(e.attrib["count"]))
           for e in parts.findall("fixed")]
    fluid, = parts.findall("fluid")
    nfix = int(fluid.attrib["begin"])
    expected = [(0,0,325),(1,325,1970),(2,2295,325)]
    require(reg==expected and nfix==2620 and int(fluid.attrib["count"])==MATERIAL_COUNT,
            "Unexpected fixed MK partition or material population")
    points, fields = vtk(GEN/(TAG+"_All.vtk"))
    require(not np.any(points[:,1]), "2-D seed coordinates expected")
    # In lattice coordinates the centres are half a step from each physical plane.
    grids = ((range(-5,0),range(65)), (range(-5,389),range(-5,0)),
             (range(128,133),range(65)), (range(128),range(64)))
    for (_, begin, count), (xs,zs) in zip([*reg,(3,nfix,MATERIAL_COUNT)],grids,strict=True):
        mask = (fields["Idp"]>=begin)&(fields["Idp"]<begin+count)
        samples = points[mask][:,[0,2]] / DP - .5
        require(sorted(map(tuple,samples))==[(i,j) for i in xs for j in zs],
                f"Off-lattice or duplicate point in generated particle range {begin}:{begin+count}")
    static = (SEED.with_suffix(".xml"), SEED.with_suffix(".bi4"), GEN/(TAG+"_Normals.nbi4"))
    record(GEN/"seed.json",dict(spacing=DP, fixed=nfix, material=MATERIAL_COUNT, fixed_parts=reg,
                              files=[identity(x) for x in (*static,DEFINITION,PROGRAM)]))
    print("Generated material/fixed counts", MATERIAL_COUNT, nfix, "fixed MK parts", reg, flush=True)


def review(output, step_limit, seed):
    with (output/"Run.csv").open(encoding="utf-8-sig",newline="") as f:
        log, = csv.DictReader(f, delimiter=";")
    frames = step_limit//2000+1
    require((int(log["Steps"]),int(log["PartFiles"]),int(log["PartsOut"]))==(step_limit,frames,0),
            "Wrong run limit, output count or exclusions")
    require("Finished execution (code=0)." in (output/"Run.out").read_text(encoding="utf8",errors="replace"),
            "Missing solver completion")
    paths = sorted((output/"data").glob("Part_????.bi4"))
    require([p.name for p in paths]==[f"Part_{i:04d}.bi4" for i in range(frames)],"Missing native frame")
    nfix = seed["fixed"]
    size = nfix+MATERIAL_COUNT
    soil = slice(nfix,None)
    expected_ids = np.arange(size, dtype=np.uint32)
    original = read(REFERENCE)
    expected_types = {k:t["type_id"] for k,t in original["types"].items()}
    with SAVED_CLOCKS.open(encoding="utf8", newline="") as stream:
        schedule = list(csv.DictReader(stream))[:frames]
    require(len(schedule)==frames and int(schedule[-1]["completed_step"])==step_limit,
            "The original preload save schedule differs")
    clock, completed, max_speed, max_dterror = 0., 0, 0., -float("inf")
    for part,path in enumerate(paths):
        state = read(path)
        header = state["root"]["values"]
        meta = state["part"]["values"]
        require({k:t["type_id"] for k,t in state["types"].items()}==expected_types,
                f"Native 22-array layout changed at {path.name}")
        require(header["Data2d"] and not header["PeriMode"] and header["Npiece"]==1 and
                header["CaseNfixed"]==nfix and header["CaseNp"]==size and header["CaseNfluid"]==MATERIAL_COUNT and
                header["Dp"]==DP and np.isclose(header["H"],DP*1.8,rtol=2e-7,atol=0) and
                header["MassFluid"]==np.float32(header["Rhop0"]*DP**2),
                "Geometry, spacing or particle mass mismatch")
        require(meta["Npok"]==size and meta["Nout"]==0 and meta["Cpart"]==part and
                meta["MaterialLawVersion"]==2 and meta["GravityPreloadPhase"]==0 and
                meta["SoilDampingActive"] and meta["PoreShepardActive"], "Unexpected closed-wall preload metadata")
        if part:
            planned = schedule[part]
            require(int(planned["part"])==part and int(planned["completed_step"])>completed,
                    "The reference save schedule is out of order")
            next_step = int(planned["completed_step"])
            for _ in range(completed,next_step):
                clock += DT
            completed = next_step
            require(meta["Step"]+1==completed and meta["TimeStep"]==float(planned["time_s"])==clock and
                    meta["dtmin"]==meta["dtmax"]==DT and np.isfinite(meta["dterror"]) and meta["dterror"]<=1e-14,
                    f"Fixed clock or recorded step limit differs at {path.name}")
            max_dterror = max(max_dterror, float(meta["dterror"]))
        else:
            require(meta["TimeStep"]==0. and meta["Step"]==0, "Unexpected initial time")
        order = np.argsort(state["arrays"]["Idp"])
        a = {k:v[order] for k,v in state["arrays"].items()}
        require(np.array_equal(a["Idp"],expected_ids) and all(np.isfinite(v).all() for v in a.values()),
                "Missing material or nonfinite state")
        if not part:
            fixed = a["Posd"][:nfix]
            p0 = a["PorePress0"].tobytes()
            prior_kappa = np.zeros(size)
            x,z = (a["Posd"][soil,j] for j in [0,2])
            ix,iz = np.rint(x/DP-.5).astype(int),np.rint(z/DP-.5).astype(int)
            require(np.array_equal(np.sort(ix*64+iz),np.arange(MATERIAL_COUNT))
                    and np.array_equal(x,(ix+.5)*DP) and np.array_equal(z,(iz+.5)*DP)
                    and np.all((ix>=0)&(ix<128)&(iz>=0)&(iz<64)), "Unexpected initial soil lattice")
            require(not np.any(a["Kplastic"]), "Nonzero initial hardening")
        J = a["PoroVolumeRatio"][soil]
        solid = 1.-float(np.float32(.35))
        n = 1.-solid/J
        rho = 1000.+1072.5/J
        close = lambda x,y: np.allclose(x,y,atol=0,rtol=2e-14)
        require(np.array_equal(a["Posd"][:nfix],fixed) and not np.any(a["Vel"][:nfix]) and
                a["PorePress0"].tobytes()==p0 and not np.any(a["Posd"][:,1]) and
                np.array_equal(a["ExcessPorePress"],a["PorePress"]-a["PorePress0"]), "Fixed markers or pressure baseline changed")
        require(np.all((n>0)&(n<1)) and close(n,a["PoroPorosity"][soil]) and
                close(rho,a["PoroMixtureDensity"][soil]) and np.array_equal(rho.astype("f4"),a["Rhop"][soil]) and
                close(J*DP**2,a["PoroCurrentVolume"][soil]) and
                close(float(np.float32(.0002))*np.exp((J-1)/(2*solid)), a["PoroHydraulicConductivity"][soil]),
                "Porosity, conductivity or volume ledger mismatch")
        require(np.all(a["Kplastic"]>=prior_kappa) and not np.any(a["Kplastic"][:nfix]) and
                np.all(a["FSType"]<=4) and not np.any(a["HydroMechLoadAce"]), "Plastic history, out-of-range tag or unexpected external load")
        prior_kappa = a["Kplastic"]
        max_speed = max(max_speed,float(np.max(np.linalg.norm(a["Vel"][soil],axis=1))))
    if step_limit==STEPS["preload"]:
        verify_source_material(meta,"psi2p5")
    return dict(passed=True, steps=step_limit, frames=frames, spacing_m=DP, geometry=seed["fixed_parts"],
                material_count=MATERIAL_COUNT, time_s=clock, max_signed_dterror_s=max_dterror,
                solver_wall_s=float(log["TTotal"]), max_saved_speed_m_s=max_speed,
                final_max_speed_m_s=float(np.max(np.linalg.norm(a["Vel"][soil],axis=1))),
                final_max_kappa=float(a["Kplastic"][soil].max()), final_min_p_Pa=float(a["PorePress"][soil].min()),
                final_max_p_Pa=float(a["PorePress"][soil].max()),
                source_schema2=step_limit==STEPS["preload"], final_native=identity(paths[-1]))


def verified_seed():
    seed = load(GEN/"seed.json")
    require(all(identity(Path(x["path"]))==x for x in seed["files"]), "Preload seed or program was changed")
    return seed


def review_run(mode):
    tag = TAG+"_smoke_r2" if mode=="smoke" else PRELOAD_TAG
    destination = TESTS/"outputs"/tag
    seal = load(LOG/(tag+".call.json"))
    start = load(LOG/(tag+".start.json"))
    require(all(start[k]==seal[k] for k in start) and seal["returncode"]==0 and
            seal["program"]==identity(PROGRAM) and seal["output"]==str(destination),
            "Expected a completed, bound preload")
    check = LOG/(tag+".check.json")
    require(not check.exists(), "Retained offline review already exists")
    result = review(destination,STEPS[mode],verified_seed())
    record(check,result)
    print(json.dumps(result, indent=2),flush=True)


def run(mode):
    verified_seed()
    if mode=="preload":
        require(load(LOG/(TAG+"_smoke_r2.check.json"))["passed"], "Review the smoke first")
    tag = TAG+"_smoke_r2" if mode=="smoke" else PRELOAD_TAG
    destination = TESTS/"outputs"/tag
    destination.mkdir()
    cap = STEPS[mode]
    call(tag, [PROGRAM, "-gpu:0", "-stable", "-mdbc_freeslip", SEED, destination, "-dirdataout", "data",
               "-svres", f"-nsteps:{cap}"], destination)
    review_run(mode)


def own_preload(cli, thread):
    require(cli.is_file() and thread and thread==os.environ.get("CODEX_THREAD_ID"),
            "The terminal notice must target the authorizing thread")
    prefix = LOG/PRELOAD_TAG
    record(prefix.with_suffix(".owner.json"),dict(owner_pid=os.getpid(), start_utc=now(),
           seed=identity(GEN/"seed.json"), thread=thread))
    try:
        run("preload")
        phase, error = "preload_native_passed_pending_equilibrium_and_handoff", None
    except Exception as exc:
        phase, error = "preload_interrupted_preserved", str(exc)
    terminal = prefix.with_suffix(".terminal.json")
    record(terminal,dict(phase=phase, error=error, end_utc=now()))
    message = (f"已授权 C08 正压截断、细粒距 0.03125 m 独立预载已终态。先查 {terminal}，"
               f"同前缀 .start/.call/.check、实际输出、同材料合同、已存时钟与压力/应力/速度。"
               "求解通过仅供离线预载平衡评审。另核已构建细网格私有三轮接收器、短窗后再决定长程。"
               "保持正压截断及负压演化。保留全部失败与已存状态，勿重跑预载、重发或重新布防。")
    record(prefix.with_suffix(".queue_attempt.json"),dict(terminal=str(terminal), utc=now()))
    try:
        process = subprocess.run([str(cli),"queue","--thread",thread,"--message",message],
                                 cwd=CASE,capture_output=True,timeout=45)
        notice = dict(returncode=process.returncode)
    except (OSError,subprocess.TimeoutExpired) as exc:
        notice = dict(delivery="unknown",error=str(exc))
    record(prefix.with_suffix(".queue_result.json"),notice)
    return int(error is not None)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare","smoke","review-smoke","own-preload"))
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--thread")
    args = parser.parse_args()
    if args.mode=="prepare":
        prepare()
    elif args.mode=="own-preload" and args.cli:
        sys.exit(own_preload(args.cli,args.thread))
    elif args.mode=="smoke":
        run("smoke")
    elif args.mode=="review-smoke":
        review_run("smoke")
    else:
        parser.error("own-preload requires --cli and --thread")
