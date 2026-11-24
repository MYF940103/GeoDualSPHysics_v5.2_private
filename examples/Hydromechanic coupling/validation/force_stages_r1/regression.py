"""Same-backend Release regression for force-stage and translation-unit refactoring."""
import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import numpy as np

BASE = Path(__file__).resolve().parent
HYDRO = BASE.parents[1]
REPO = HYDRO.parents[1]
BIN = REPO / "bin/windows"
COL = HYDRO / "02_TerzaghiConsolidation_q0_PR/tests"
SPHERE = HYDRO / "04_CryerProblem_PR/tests"
C08 = HYDRO / "08_LianSaturatedColumnCollapse_u_pl/tests"
sys.path.insert(0, str(COL / "support"))
from upl_tpi_partial_bi4_r1 import _Cursor, _numeric, _values

EXECUTABLE = {"cpu": "DualSPHysics5.2CPU_win64.exe", "gpu": "DualSPHysics5.2_GEO_win64.exe"}
LANES = ("dry_verlet", "dry_cdbc", "column0", "column1", "column2", "sphere2")
STEPS = dict(dry_verlet=16, dry_cdbc=6, column0=8, column1=8, column2=8, sphere2=4)


def require(test, why):
    if not test:
        raise ValueError(why)


def parameter(tree, key, value):
    node = tree.find(f"execution/parameters/parameter[@key='{key}']")
    require(node is not None, "Missing input "+key)
    node.set("value", str(value))


def prepare(lane, benchmark=False):
    """These are numerical regression windows, not physical validation or new formal inputs."""
    if lane in ("dry_verlet","dry_cdbc"):
        source = HYDRO.parent / "Elastoplastic_basic/12_GranularColumnCollapse/tests/outputs/basic_a05_dp002_r2_seed"
    elif lane.startswith("column"):
        i = 0 if lane == "column0" else 3
        source = COL / f"outputs/tpi_r_public_compat_gpu_r1/{i}_default/seed"
    else:
        source = SPHERE / "outputs/public_tpi_sphere4hist_cpu_hist1/seed"
    available=list(source.glob("*.xml"))
    if available:
        xml,=available
        inputs={p.name:p.read_bytes() for p in (xml,xml.with_suffix(".bi4"),source/(xml.stem+"_Normals.nbi4")) if p.is_file()}
    else:
        group={"dry_verlet":"dry","dry_cdbc":"dry","column0":"col0","column1":"col2","column2":"col2","sphere2":"sphere"}[lane]
        with ZipFile(BASE/"regression_inputs.zip") as archive:
            inputs={Path(n).name:archive.read(n) for n in archive.namelist() if n.startswith(group+"/")}
        xml,=(Path(n) for n in inputs if n.endswith(".xml"))
    tree=ET.ElementTree(ET.fromstring(inputs[xml.name]))
    special = tree.find("execution/special")
    if lane == "dry_verlet":
        parameter(tree, "StepAlgorithm", 1)
        parameter(tree, "Shifting", 3)
        parameter(tree, "TimeOut", 1.e-8)
    if lane == "dry_cdbc":
        parameter(tree, "Boundary", 1)
        parameter(tree, "TimeOut", 1.e-8)
    if lane.startswith("column") or lane == "sphere2":
        if lane=="column1":
            parameter(tree, "DtFixed", 1.e-6)
            parameter(tree, "DtIni", 1.e-6)
        dt = float(tree.find("execution/parameters/parameter[@key='DtFixed']").get("value"))
        t = special.find("timeout")
        if t is not None:
            special.remove(t)
        if lane != "sphere2" and not benchmark:
            special.find("hydromechanics/HydroMechModel").set("value", lane[-1])
            special.find("drainage").set("start", repr(3*dt))
            special.find("externalload").set("ramptime", repr(2*dt))
        parameter(tree, "TimeOut", 0.001 if benchmark else repr(dt))
    label=lane+"_1us" if lane=="column1" else lane
    dest = BASE / "seeds" / (label+"_bench" if benchmark else label)
    dest.mkdir(parents=True, exist_ok=True)
    seed = dest / xml.stem
    raw = ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True)
    target = seed.with_suffix(".xml")
    if target.exists():
        require(target.read_bytes() == raw, "Prepared input differs "+lane)
    else:
        files=[xml.stem+".bi4"]
        normals=xml.stem+"_Normals.nbi4"
        if normals in inputs:
            files.append(normals)
        for ext in files:
            (dest/ext).write_bytes(inputs[ext])
        target.write_bytes(raw)
    return seed


def execute(version, backend, lane, repetition=None, trial="", benchmark_steps=384):
    exe = BASE / version / EXECUTABLE[backend]
    require(exe.is_file(), str(exe))
    seed = prepare(lane, benchmark=repetition is not None)
    name = f"{lane}_{backend}_{version}" + (f"_bench{repetition}" if repetition is not None else "") + trial
    dest = BASE / "runs" / name
    dest.mkdir(parents=True)
    flags = ["-"+backend, "-stable"]
    if backend == "cpu":
        flags.append("-ompthreads:1")
    if lane.startswith("column"):
        flags.append("-mdbc_freeslip")
    n = STEPS[lane] if repetition is None else benchmark_steps
    if repetition is not None:
        flags.append("-tout:0.001")
    cmd = [str(exe), *flags, str(seed), str(dest), "-dirdataout", "data", "-svres", f"-nsteps:{n}"]
    env = os.environ.copy()
    env["PATH"] = str(BIN) + os.pathsep + env["PATH"]
    utc=datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()
    print(name, flush=True)
    with (dest / "console.log").open("xb") as output:
        run = subprocess.run(cmd, cwd=BIN, env=env, stdout=output, stderr=subprocess.STDOUT,
                             timeout=300, creationflags=subprocess.CREATE_NO_WINDOW)
    elapsed = time.perf_counter()-start
    rec = dict(command=cmd, exit=run.returncode, wall_s=elapsed, start_utc=utc,
               end_utc=datetime.now(timezone.utc).isoformat(), executable_bytes=exe.stat().st_size,
               executable_mtime_ns=exe.stat().st_mtime_ns)
    if run.returncode == 0:
        with (dest/"Run.csv").open(encoding="utf8", errors="replace") as f:
            row, = csv.DictReader(f, delimiter=";")
        rec.update(loop_s=float(row["TSimul"]), steps=int(row["Steps"]), parts=int(row["PartFiles"]),
                   parts_out=int(row["PartsOut"]), hardware=row["Hardware"], configuration=row["Configuration"])
    (dest/"call.json").write_text(json.dumps(rec, indent=2),encoding="utf8")
    if run.returncode or rec["steps"] != n or rec["parts_out"]:
        raise RuntimeError(f"{name}: {rec}. See console.log")
    return rec


def unpack(path):
    data = path.read_bytes()
    require(data[:58].rstrip(b" ") == b"#FileJBD JPartDataBi4", str(path))
    c = _Cursor(data,64)
    def item(depth):
        d = c.block(c.uint())
        require(d.string()=="\nITEM\n" and depth < 4, "JBD item")
        name = d.string()
        attributes = [d.boolean(),d.boolean(),d.string(),d.string()]
        count, nested, size = d.uint(),d.uint(),d.uint()
        d.finish(name)
        values,types = _values(c.block(size))
        arrays = {}
        for _ in range(count):
            head = c.block(c.uint())
            require(head.string()=="\nARRAY","JBD array")
            key = head.string()
            require(key not in arrays, "Duplicate array "+key)
            hidden,t,n,sz = head.boolean(),head.integer(),head.uint(),head.uint()
            head.finish(key)
            a,spec = _numeric(c,t,n)
            require(np.isfinite(a).all() and sz==spec["data_bytes"], key)
            arrays[key] = ((hidden,t,n,sz), a)
        children = [item(depth+1) for _ in range(nested)]
        return name,attributes,values,types,arrays,children
    root = item(0)
    c.finish("BI4")
    return root


def early_step_rejection(version):
    # Preserve the original unsuccessful model-1 baseline and replay the identical input once.
    base=BASE/"runs/column1_cpu_old"
    old=json.loads((base/"call.json").read_text())
    require(old["exit"]==1, "Unexpected original fixture outcome")
    output_arg=old["command"].index(str(base))
    spec=ET.parse(Path(old["command"][output_arg-1]).with_suffix(".xml"))
    require(float(spec.find("execution/parameters/parameter[@key='DtFixed']").get("value"))>1.e-5,
            "The old rejected input must remain intact")
    dest=BASE/"runs"/f"column1_cpu_{version}_rejected"
    dest.mkdir()
    cmd=old["command"].copy()
    cmd[0]=str(BASE/version/EXECUTABLE["cpu"])
    cmd[output_arg]=str(dest)
    env=os.environ.copy()
    env["PATH"]=str(BIN)+os.pathsep+env["PATH"]
    with (dest/"console.log").open("xb") as log:
        rc=subprocess.run(cmd,cwd=BIN,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=45,
                          creationflags=subprocess.CREATE_NO_WINDOW).returncode
    def cause(path):
        text=(path/"console.log").read_text(errors="replace")
        return next(l for l in text.splitlines() if "current step or DtMin exceeds" in l)
    require(rc==1 and cause(base)==cause(dest),"Different rejection or guard data")
    parts=lambda path:sorted(p.name for p in (path/"data").glob("Part_????.bi4"))
    require(parts(base)==parts(dest)==["Part_0000.bi4"],"Unexpected rejected PART set")
    require((base/"data/Part_0000.bi4").read_bytes()==(dest/"data/Part_0000.bi4").read_bytes(),
            "Initial rejected native frame changed")
    return dict(command=cmd,exit=rc,original_cause=cause(base),new_cause=cause(dest),initial_frame_exact=True)


def compare(lane, backend, old_version, new_version, trial=""):
    def folder(version):
        return BASE/"runs"/(f"{lane}_{backend}_{version}"+trial)
    def files(version):
        return sorted((folder(version)/"data").glob("Part_????.bi4"))
    left,right = files(old_version),files(new_version)
    require(left and [x.name for x in left]==[x.name for x in right], "Frame count")
    result = dict(lane=lane,backend=backend,frames=len(left),array_comparisons=0,history_frames=0,
                  scalar_comparisons=0,saved_steps=[],saved_times_s=[],exact_part_bytes=0)
    def fields(x,y,depth,ids,part):
        n,h,v,t,a,k=x
        m,g,w,u,b,j=y
        require((n,h,t)==(m,g,u) and list(a)==list(b) and len(k)==len(j), "Schema "+n)
        for key in v:
            if key=="RunCode":
                require((v[key],w[key])==ids, "Inconsistent run identity")
            first, second = v[key],w[key]
            ok = (first==second) if isinstance(first,str) else (np.asarray(first).tobytes()==np.asarray(second).tobytes())
            require(ok,f"{part}/{key} differs: {first} vs {second}")
            result["scalar_comparisons"]+=1
        for key in a:
            require(a[key][0]==b[key][0] and a[key][1].tobytes()==b[key][1].tobytes(), f"{part}/{key} changed")
            result["array_comparisons"]+=1
        if depth==1:
            require(v["Nout"]==0 and len(a["Idp"][1])==len(np.unique(a["Idp"][1]))==v["Npok"],"Active ID set")
            result["saved_steps"].append(int(v["Step"]))
            result["saved_times_s"].append(float(v["TimeStep"]))
            result["native_arrays"]=list(a)
            result["active_ids"]=int(v["Npok"])
        if n=="TpiPressureHistory":
            result["history_frames"]+=1
        for s,r in zip(k,j):
            fields(s,r,depth+1,ids,part)
    for l,r in zip(left,right):
        x,y=unpack(l),unpack(r)
        fields(x,y,0,(x[2]["RunCode"],y[2]["RunCode"]),l.name)
        require(l.read_bytes()==r.read_bytes(),f"{l.name} native byte stream differs")
        result["exact_part_bytes"]+=l.stat().st_size
    old_log=(folder(old_version)/"Run.out").read_text(errors="replace")
    new_log=(folder(new_version)/"Run.out").read_text(errors="replace")
    def hg(log):
        return [line.strip() for line in log.splitlines() if line.lstrip().startswith("SoilHourglass:")]
    require(hg(old_log)==hg(new_log), "Hourglass phase counts, history update or final reductions differ")
    result["hourglass_final_summary"]=hg(new_log)
    if lane.startswith("column"):
        require(len(result["hourglass_final_summary"])>=3 and "forcecalls=16" in result["hourglass_final_summary"][0],
                "Column hourglass history did not advance")
        initial=unpack(right[0])[-1][0][4]
        pos=initial["Posd" if "Posd" in initial else "Pos"][1]
        owner=initial["Idp"][1]
        topids=owner[(owner>=40) & (pos[:,2]==pos[owner>=40,2].max())]
        require(len(topids)==10,"Top material set")
        levels={}
        for file in right[1:]:
            n=unpack(file)[-1][0]
            p=n[4]["PorePress"][1][np.isin(n[4]["Idp"][1],topids)]
            step=int(n[2]["Step"])+1
            if step==3:require(np.all(p>0),"Drain event frame must still be closed")
            if step>=4:require(np.all(p==0),"Drained top material pressure")
            levels[step]=[float(p.min()),float(p.max())]
        require(3 in levels and 4 in levels,"Missing event frames")
        result["top_pressure_range_Pa_by_completed_step"]=levels
    for log in (old_log,new_log):
        require("Finished execution (code=0)." in log,"Missing successful exit")
        if lane=="dry_verlet":
            require('StepAlgorithm="Verlet"' in log and "Shifting algorithm (Lind" in log,"Verlet and shifting must execute")
        if lane=="dry_cdbc":
            require('Boundary="DBC"' in log and 'StepAlgorithm="Symplectic"' in log,"Conventional cDBC must execute")
        if lane.startswith("column") or lane=="sphere2":
            require(f"HydroMechModel={lane[-1]} (" in log,"Unexpected hydromechanical model")
            wall='DBC' if lane=="sphere2" else 'mDBC'
            require(f'Boundary="{wall}"' in log,"Unexpected hydraulic boundary")
    require(lane not in ("column2","sphere2") or result["history_frames"]==len(left)-1,"Missing TPI pressure history")
    return result


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("action",choices=("run","compare","bench","reject"))
    ap.add_argument("--version",required=True)
    ap.add_argument("--old",default="old")
    ap.add_argument("--backend",nargs="+",choices=EXECUTABLE,default=list(EXECUTABLE))
    ap.add_argument("--lane",nargs="+",choices=LANES,default=LANES)
    ap.add_argument("--trial",default="")
    args=ap.parse_args()
    output=[]
    for backend in args.backend:
        if args.action=="reject":
            require(backend=="cpu", "The retained rejected fixture exists only on CPU")
            output.append(early_step_rejection(args.version))
        elif args.action=="bench":
            import psutil
            process=psutil.Process()
            original_affinity=process.cpu_affinity()
            if backend=="cpu":
                # The two builds run on the same logical CPU on this hybrid processor.
                chosen=2 if 2 in original_affinity else min(original_affinity)
                process.cpu_affinity([chosen])
            pairs=[]
            for i in range(4):
                versions=(args.old,args.version) if i%2==0 else (args.version,args.old)
                pair={v:execute(v,backend,"column2",i,args.trial) for v in versions}
                parts=[sorted(Path(pair[v]["command"][-5],"data").glob("Part_????.bi4")) for v in versions]
                require(parts[0] and [p.name for p in parts[0]]==[p.name for p in parts[1]],"Timing output schedule")
                require(all(a.read_bytes()==b.read_bytes() for a,b in zip(*parts)),"Timing window native mismatch")
                pairs.append(pair)
            ratios=[r[args.version]["loop_s"]/r[args.old]["loop_s"] for r in pairs]
            output.append(dict(backend=backend,pairs=pairs,median_ratio=statistics.median(ratios),
                               solver_inherited_affinity=process.cpu_affinity(),
                               median_wall_ratio=statistics.median(r[args.version]["wall_s"]/r[args.old]["wall_s"] for r in pairs)))
            process.cpu_affinity(original_affinity)
        else:
            for lane in args.lane:
                if args.action=="compare":
                    output.append(compare(lane,backend,args.old,args.version,args.trial))
                else:
                    execute(args.version,backend,lane,trial=args.trial)
    if output:
        name=f"{args.action}_{args.version}_{'_'.join(args.backend)}{args.trial}.json"
        with (BASE/name).open("x",encoding="utf8") as out:json.dump(output,out,indent=2)
