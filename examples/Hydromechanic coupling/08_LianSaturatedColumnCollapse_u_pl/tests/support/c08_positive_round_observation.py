"""Acquire and verify TPI stage observations with the original positive-only C08 boundary."""
import argparse
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

from c08_psi25_tpi_run import CASE, TESTS, PRE, SEED, CAP, expected_xml, now, record, identity
from c08_psi25_tpi_native import read_frame, expected_steps, require, inspect_log

LOG = TESTS/"logs"
TAG = "c08_positive_round_observation_r1"
BASE = "c08_psi25_tpi_paper_b004_r1"
BUILD = TESTS/"outputs/c08_psi25_round_probe_build_r1/build.json"
FOLDER = TESTS/"outputs"/TAG


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def solve():
    original = read(LOG/(BASE+".call.json"))
    control = read(LOG/(BASE+".native_review.json"))
    proof = read(BUILD)
    exe = Path(proof["program"])
    seed = read(SEED.parent/"inputs.json")
    require(original["returncode"]==0 and control["passed"] and control["frames"]==132
            and original["cap"]==CAP["paper"] and original["beta"]==.04
            and proof["unchanged_objects"]==112 and proof["changed_cuda_objects"]==0
            and identity(exe)==proof["executable"] and identity(PRE)==original["source"]==seed["source"]
            and all(identity(Path(i["path"]))==i for i in seed["inputs"])
            and SEED.with_suffix(".xml").read_bytes()==expected_xml(), "Build, PRE or seed mismatch")
    old=original["command"]
    require(old[1:5]==["-gpu","-stable","-mdbc_freeslip:1",str(SEED)] and
            old[6:]==["-dirdataout","data","-svres","-nsteps:"+str(CAP["paper"])], "Baseline call changed")
    cmd=[str(exe),*old[1:5],str(FOLDER),*old[6:]]
    logs=[LOG/(TAG+s) for s in (".start.json",".call.json",".console.log")]
    require(not FOLDER.exists() and not any(f.exists() for f in logs),"Prior/active observation needs review")
    FOLDER.mkdir()
    info=dict(tag=TAG,program=str(exe),exe=identity(exe),source=identity(PRE),PRE=str(PRE),
              seed=str(SEED),build=identity(BUILD),beta=.04,cap=CAP["paper"],command=cmd,
              original=BASE,boundary="positive_only",owner_pid=os.getpid(),start_utc=now())
    with logs[2].open("xb") as f:
        with subprocess.Popen(cmd,cwd=CASE,env=dict(os.environ,C08_PRIVATE_BETA="0.04"),
                              stdout=f,stderr=subprocess.STDOUT) as child:
            info["solver_pid"]=child.pid
            record(logs[0],info)
            rc=child.wait()
    record(logs[1],dict(**info,returncode=rc,end_utc=now()))
    require(rc==0, f"Solver exited {rc}; inspect original output")


def verify():
    call=read(LOG/(TAG+".call.json"))
    base=read(LOG/(BASE+".native_review.json"))
    cap=CAP["paper"]
    require(call["returncode"]==0 and call["cap"]==cap and call["source"]==identity(PRE)
            and call["build"]==identity(BUILD) and call["exe"]==identity(Path(call["program"]))
            and base["passed"] and base["frames"]==132,"Invalid call, control or identities")
    sealed={p:(size,mtime) for p,size,mtime in base["files"]}
    steps=expected_steps(cap)
    names=[f"Part_{part:04d}.bi4" for part in range(1,len(steps)+1)]
    require(sorted(p.name for p in (FOLDER/"data").glob("Part_????.bi4"))==names,"Incomplete native set")
    original=TESTS/"outputs"/BASE
    fields=None
    for name,step in zip(names,steps):
        old=original/"data"/name
        stat=old.stat()
        require(sealed[str(old.relative_to(CASE))]==(stat.st_size,stat.st_mtime_ns), "Control changed")
        m,a,h,p=read_frame(FOLDER/"data"/name)
        om,oa,oh,op=read_frame(old)
        require(m["Step"]+1==step==om["Step"]+1 and set(a)==set(oa)
                and all(a[k].dtype==oa[k].dtype and a[k].shape==oa[k].shape and
                        a[k].tobytes()==oa[k].tobytes() for k in a)
                and p.tobytes()==op.tobytes(), f"Observer changed native history or array at {name}")
        for k in ("TimeStep","dterror","dtmin","dtmax","SymplecticDtPre"):
            require(struct.pack("<d",m[k])==struct.pack("<d",om[k]),f"Different native {k} at {name}")
        release_key="GravityPreloadActualTime"
        require((release_key in m)==(release_key in om)==(step>2_000_200),
                f"Unexpected release timestamp presence at {name}")
        if release_key in m:
            require(struct.pack("<d",m[release_key])==struct.pack("<d",om[release_key]),
                    f"Different native release time at {name}")
        for k in ("Scheme","Valid","Schema","CompletedUpdates","PreviousTime","SavedTime","Dt"):
            require(h[k]==oh[k],f"Different pressure history {k} at {name}")
        for k in ("Nout","Npok","HydroMechModel","GravityPreloadPhase","PoreShepardActive",
                  "SoilDampingActive","HydroMechFreeSeepage","DynamicNoPenetrationReactionClosed"):
            require(m[k]==om[k],f"Different native policy {k} at {name}")
        fields=sorted(a)
    telemetry=inspect_log(FOLDER/"Run.out",cap)
    record(LOG/(TAG+".native_review.json"),dict(tag=TAG,original=BASE,passed=True,frames=len(names),
           arrays=fields,pressure_history_byte_equal=True,clocks_and_signed_intervals_equal=True,
           end_s=m["TimeStep"],release_time=m["GravityPreloadActualTime"],step=step,**telemetry))


def own(cli, thread):
    require(cli.is_file() and thread and thread==os.environ.get("CODEX_THREAD_ID"), "Incorrect thread or CLI")
    record(LOG/(TAG+".owner.json"),dict(pid=os.getpid(),thread=thread,start=now(),
           baseline=BASE,output_only=True,program_build=identity(BUILD)))
    stage="solve"
    try:
        solve()
        stage="native_comparison"
        verify()
        result=dict(stage="native_passed_pending_stage_budget_review",exit_code=0)
    except Exception as error:
        result=dict(stage=stage,exit_code=1,reason=str(error))
    terminal=LOG/(TAG+".terminal.json")
    record(terminal,dict(**result,end_utc=now()))
    message=(f"已授权 C08 +2.5° 正压截断三轮力阶段观测已终态：{terminal}。"
             "先核原start/call、构建与native同轨比较，检查真实9份压力行、逐轮CSV和子步/时钟，"
             "执行新的独立行分解与物理/论文评审。仅派生失败可离线修复。"
             "保留自由面负压演化，右列特殊泄压已取消。不得重复求解、重发或布防此通知。")
    record(LOG/(TAG+".queue_attempt.json"),dict(thread=thread,terminal=str(terminal),utc=now()))
    try:
        rc=subprocess.run([str(cli),"queue","--thread",thread,"--message",message],
                          cwd=CASE,capture_output=True,timeout=45).returncode
        outcome=dict(exit_code=rc)
    except (OSError,subprocess.TimeoutExpired) as error:
        outcome=dict(delivery="unknown",reason=str(error))
    record(LOG/(TAG+".queue_result.json"),outcome)
    return result["exit_code"]


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phase",choices=("solve","verify","own"))
    ap.add_argument("--cli",type=Path)
    ap.add_argument("--thread")
    args=ap.parse_args()
    if args.phase=="own": sys.exit(own(args.cli,args.thread))
    elif args.phase=="solve": solve()
    else: verify()
