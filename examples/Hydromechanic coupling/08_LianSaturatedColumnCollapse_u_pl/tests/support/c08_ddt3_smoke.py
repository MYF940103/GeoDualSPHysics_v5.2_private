"""Run and review the 40-step +2.5-degree DDT3 implementation comparison on one backend."""
import argparse
import csv
import json
from pathlib import Path
import re
import shutil
import sys
import xml.etree.ElementTree as ET

from c08_ddt3_compare import BIN, CASE, TESTS, check_definitions, identity, invoke, now, require, write_record

GROUP = "psi2p5"
STEPS = 40
SHARED = TESTS / "outputs/c08_ddt3_smoke_inputs_r1"
PREFLIGHT = TESTS / "outputs/c08_ddt3_psi2p5_preflight_r1"
OLD_PRE = CASE / "CaseLianCollapse_psi2p5_pre_GPU_out/data/Part_1000.bi4"
STEM = "CaseLianCollapse_psi2p5_pre"
NEW_BUILD = CASE.parents[2] / "src/VS/x64/c08_ddt3_r1"
SCHEMA_ERROR = "Missing/incompatible same-material plastic handoff schema/contract."


def seed(kind):
    if kind == "on":
        return PREFLIGHT / "pre/c08_ddt3_psi2p5_pre_r1"
    if kind == "negative":
        return SHARED / "negative/c08_ddt3_psi2p5_r1"
    return SHARED / "off" / STEM


def setup(gencase):
    check_definitions()
    mark = SHARED / "prepared.json"
    if not mark.exists():
        SHARED.mkdir()
        dest = seed("off").parent
        dest.mkdir()
        receipt = {"calls":[]}
        invoke("gencase", [gencase, CASE / (STEM+"_Def"), seed("off"), "-save:all"], dest, receipt)
        negative = seed("negative")
        negative.parent.mkdir()
        receiver = PREFLIGHT / "collapse/c08_ddt3_psi2p5_r1"
        for suffix in (".bi4","_Normals.nbi4"):
            shutil.copy2(str(receiver) + suffix, str(negative) + suffix)
        original = receiver.with_suffix(".xml").read_bytes()
        statefile = ET.fromstring(original).find(".//gravitypreload").get("statefile")
        require(original.count(statefile.encode("ascii")) == 1 and OLD_PRE.is_file(), "Unexpected negative fixture")
        negative.with_suffix(".xml").write_bytes(original.replace(statefile.encode("ascii"), str(OLD_PRE).encode("utf8")))
        files = [identity(s) for kind in ("off", "on", "negative") for s in
                 [Path(str(seed(kind)) + ext) for ext in (".xml", ".bi4", "_Normals.nbi4")]]
        write_record(mark, {"seed_files":files, "negative_source":identity(OLD_PRE), "prepared_utc":now()})
    info = json.loads(mark.read_text())
    require(all(identity(Path(s["path"])) == s for s in info["seed_files"])
            and identity(OLD_PRE) == info["negative_source"], "Frozen smoke seed differs")
    for kind in ("off","on","negative"):
        xml = ET.parse(seed(kind).with_suffix(".xml"))
        require(xml.find(".//parameter[@key='DensityDT']").get("value") == ("0" if kind=="off" else "3"),
                "Unexpected generated DDT mode")
    print("Validated old/new input seeds and the deliberately incompatible OFF source", flush=True)


def job(backend, key, program, input_type, loc):
    path = loc / key
    receipt_path = path / "provenance.json"
    negative = input_type == "negative"
    if path.exists():
        previous = json.loads(receipt_path.read_text())
        require(previous["passed_runtime"] and previous["program"] == identity(program)
                and previous["input"] == identity(seed(input_type).with_suffix(".xml")),
                f"Existing partial or mismatched smoke; preserve {path}")
        return
    path.mkdir()
    rec = {"program":identity(program), "input":identity(seed(input_type).with_suffix(".xml")),
           "key":key,"started_utc":now(),"calls":[],"passed_runtime":False}
    write_record(receipt_path, rec)
    device = ["-cpu","-ompthreads:1"] if backend=="CPU" else ["-gpu:0"]
    argv = [program,*device,"-stable","-mdbc_freeslip:1" if negative else "-mdbc_freeslip",
            seed(input_type),path,"-dirdataout","data","-svres","-tout:0.00005","-nsteps:40"]
    try:
        try:
            invoke("solver", argv, path, rec)
        except RuntimeError:
            if not negative:
                raise
        call = rec["calls"][-1]
        console = (path / "solver_console.log").read_text(errors="replace")
        if negative:
            require(call.get("exitcode") == 1 and SCHEMA_ERROR in console and not any((path / "data").glob("Part_*.bi4")),
                    "Expected a rejected schema2 handoff before the first state")
        else:
            require(call.get("exitcode") == 0 and "Finished execution (code=0)" in console, "No successful solver footer")
            state = "Fourtakas et al 2019 (full)" if key == "new_on" else "None"
            log = (path / "Run.out").read_text(errors="replace")
            require(f'DensityDiffusion="{state}"' in log, "Wrong DDT selected at runtime")
            if input_type == "on":
                require(re.search(r'^\s*DensityDiffusionValue=0\.1(?:0*)\s*$',log,re.M), "Wrong DDT coefficient")
            with (path / "Run.csv").open(encoding="utf-8-sig",newline="") as stream:
                summary, = csv.DictReader(stream, delimiter=";")
            require(int(summary["Steps"]) == STEPS and int(summary["PartsOut"]) == 0, "Unexpected solver summary")
        rec.update(passed_runtime=True)
    except Exception as exc:
        rec["error"] = str(exc)
        raise
    finally:
        rec["ended_utc"] = now()
        write_record(receipt_path, rec)


def review(backend, loc):
    import numpy as np
    import postprocess_lian_release as post
    from c08_ddt3_compare import write_rows
    frames = {}
    paths = []
    for key in ("old_off","new_off","new_on"):
        jobdir = loc / key
        provenance = json.loads((jobdir / "provenance.json").read_text())
        require(provenance["passed_runtime"] and provenance["calls"][-1]["exitcode"] == 0, f"{key} incomplete")
        files = sorted((jobdir / "data").glob("Part_*.bi4"))
        require(len(files) >= 3 and [p.name for p in files]==[f"Part_{i:04d}.bi4" for i in range(len(files))],
                f"Missing saved steps in {key}")
        states = []
        clocks = np.cumsum(np.r_[0.,np.full(STEPS,post.DT)])
        for i, f in enumerate(files):
            m,a = post.native(f)
            if i == 0:
                ref,prev = a,a["Kplastic"][-5000:].copy()
            prev = post.check_frame(m,a,i,True,ref,prev,0.,GROUP)
            complete = 0 if i==0 else int(m["Step"])+1
            t = float(m["TimeStep"])
            require(0 <= complete <= STEPS and t == clocks[complete] and (i==0 or complete>states[-1][0]),
                    f"Bad actual saved step in {f}")
            states.append((complete,m,a))
        require(states[-1][0]==STEPS, f"Missing final short frame in {key}")
        frames[key]=states
        paths.append(str(jobdir / "provenance.json"))
    require(len({len(v) for v in frames.values()})==1,"Smoke save counts differ")
    rows=[]
    signal = False
    for i,(old,off,on) in enumerate(zip(frames["old_off"],frames["new_off"],frames["new_on"])):
        step = off[0]
        require(step==old[0]==on[0] and all(off[1][k]==on[1][k] for k in ("Step","TimeStep","Cpart")),
                "The three smoke clocks differ")
        for k in ("Step","TimeStep","dterror","Cpart"):
            require(np.asarray(old[1][k]).tobytes()==np.asarray(off[1][k]).tobytes(),f"OFF clock differs: {i} {k}")
        for k,v in old[2].items():
            w=off[2][k]
            require(v.dtype==w.dtype and v.shape==w.shape and v.tobytes()==w.tobytes(),f"OFF regression: {i} {k}")
            if i==0:
                require(w.dtype==on[2][k].dtype and w.tobytes()==on[2][k].tobytes(),f"Initial state differs: {k}")
        fx,fy=(state[2] for state in (off,on))
        row=dict(part=i,completed_step=step,time_s=float(off[1]["TimeStep"]),
                 signed_dterror_off_s=float(off[1]["dterror"]),signed_dterror_on_s=float(on[1]["dterror"]))
        for key, names in (("SigmaState_kk",("xx","yy","zz")),("SigmaState_ij",("xy","yz","xz"))):
            dif = fy[key][-5000:]-fx[key][-5000:]
            for j,name in enumerate(names):
                row["max_abs_delta_sigma_"+name+"_Pa"]=float(np.max(abs(dif[:,j])))
                row["rms_delta_sigma_"+name+"_Pa"]=float(np.sqrt(np.mean(dif[:,j]**2)))
            signal = signal or bool(np.any(dif != 0))
        for key in ("PoroVolumeRatio","PoroPorosity","Rhop","PorePress","Kplastic"):
            row["max_abs_delta_"+key] = float(np.max(np.abs(fy[key][-5000:].astype("f8")-fx[key][-5000:])))
        rows.append(row)
    require(signal,"DDT3 did not change any native soil stress within 40 steps")
    negative_verified=False
    if backend=="CPU":
        q=json.loads((loc/"negative/provenance.json").read_text())
        negative_verified=q["passed_runtime"] and q["calls"][-1]["exitcode"]==1
        require(negative_verified,"ON/OFF source compatibility check incomplete")
    write_rows(TESTS/"figures"/f"c08_ddt3_smoke_{backend}_r1.csv",rows)
    marker = TESTS/"logs"/f"c08_ddt3_smoke_{backend}_r1.check.json"
    write_record(marker,dict(passed=True,backend=backend,steps=STEPS,native_fields=22,frames=len(rows),off_exact=True,
                             on_changed=True,negative_off_pre_rejected=negative_verified,final_deltas=rows[-1],
                             runtime_receipts=paths,physical_acceptance=False))
    print(marker, flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend",type=str.upper,choices=("CPU","GPU"),required=True)
    parser.add_argument("--stage",choices=("prepare","run","review"),default="prepare")
    parser.add_argument("--old",type=Path)
    parser.add_argument("--new",type=Path)
    parser.add_argument("--gencase",type=Path,default=BIN/"GenCase_win64.exe")
    args=parser.parse_args()
    cpu=args.backend=="CPU"
    name="DualSPHysics5.2CPU_win64_debug.exe" if cpu else "DualSPHysics5.2_GEO_win64.exe"
    old=(args.old or BIN/name).resolve()
    new=(args.new or NEW_BUILD/("DebugCPU" if cpu else "Release")/name).resolve()
    setup(args.gencase.resolve())
    loc=TESTS/"outputs"/f"c08_ddt3_smoke_{args.backend}_r1"
    if args.stage=="run":
        require(old.is_file() and new.is_file() and not old.samefile(new),"Two independent solver binaries are required")
        loc.mkdir(exist_ok=True)
        for key, program, variant in (("old_off",old,"off"),("new_off",new,"off"),("new_on",new,"on")):
            job(args.backend,key,program,variant,loc)
        if cpu:
            job(args.backend,"negative",new,"negative",loc)
    if args.stage in ("review","run"):
        review(args.backend,loc)


if __name__=="__main__":
    main()
