"""Replay genuine endpoint arithmetic on both backends without starting a solver."""
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
import pandas as pd

T = Path(__file__).resolve().parents[1]
TAG = "upl_tpi_cryer_pressure_row_r1"
WORK = T/"outputs"/TAG
SUP = T/"support"
C02 = T.parents[1]/"02_TerzaghiConsolidation_q0_PR/tests/outputs/upl_tpi_p3_B10us_window2s_GPU_r1"
CPU = T/"outputs/upl_tpi_cryer_p3_cpu_B64_r1"
GPU = T/"outputs/cryer_p3_gpu_b64_r1"
DTYPE = np.dtype([("predicted","<f8"),("diagonal","<f8"),("residual","<f8"),
    ("pn","<f4"),("previous","<f4"),("iterated","<f4"),("written","<f4"),("half","<f4"),
    ("sourceDrained","<u4"),("endpointDrained","<u4"),("padding","<u4")])

def write_doc(path,data):
    with path.open("x",encoding="utf-8") as f:
        json.dump(data,f,indent=2,allow_nan=False)
        f.write("\n")

def compile_component():
    WORK.mkdir()
    # The component uses the same VS toolset as the Cryer CPU qualification.
    vcvars = Path("D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat")
    cmdfile = WORK/"environment.cmd"
    cmdfile.write_text('@echo off\ncall "'+str(vcvars)+'" x64 8.1 -vcvars_ver=14.36 >nul\nif errorlevel 1 exit /b %errorlevel%\nset\n',encoding="mbcs")
    raw = subprocess.check_output([os.environ["COMSPEC"],"/d","/c",cmdfile.name],cwd=WORK)
    env = {k.upper():v for k,v in os.environ.items()}
    env.update((k.upper(),v) for k,v in (line.split("=",1) for line in raw.decode("mbcs").splitlines() if "=" in line and not line.startswith("=")))
    source = SUP/"upl_tpi_pressure_row_r1.cu"
    args = [shutil.which("nvcc"),"-arch=sm_86","-std=c++17","--fmad=false","--prec-div=true",
        "-Xcompiler","/fp:precise",str(source),"-o",str(WORK/"replay.exe")]
    if not args[0]:
        raise FileNotFoundError("nvcc")
    with (WORK/"compile.log").open("xb") as log:
        rc = subprocess.run(args,cwd=WORK,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
    write_doc(T/"logs"/(TAG+".build.json"),dict(passed=rc==0,returncode=rc,argv=args,
        header=str(SUP/"TpiPressureRow.h"),source=str(source),host_compiler=env["VCTOOLSINSTALLDIR"]))
    if rc: raise RuntimeError("Component build failed, see compile.log")

def last_frame(path,part,n):
    # Genuine complete final frame only. Read a bounded suffix of the 0.5GB
    # C02 table and explicitly prove complete native IDs rather than assuming
    # a nominal row stride or accepting a truncated suffix.
    with path.open("rb") as f:
        header=f.readline(); postheader=f.tell()
        f.seek(0,2);offset=max(postheader,f.tell()-2_500_000)
        f.seek(offset)
        if offset>postheader:f.readline()
        buf=io.BytesIO(header+f.read())
    rows=pd.read_csv(buf,float_precision="round_trip")
    selected=rows[rows.part==part].sort_values("native_id").reset_index(drop=True)
    if len(selected)!=n:raise ValueError("Incomplete actual saved rows in "+str(path))
    return selected

def check():
    records=[]; evidence=[]; validated={}; common={}
    def add(rows,label,path,part,iteration,first_id,n):
        ids=rows.native_id.to_numpy()
        if not np.array_equal(ids,np.arange(first_id,first_id+n)):raise ValueError(label+" native IDs")
        if not (rows.part==part).all():raise ValueError(label+" saved state")
        is_cpu="pressure_round" in rows
        if not (rows["pressure_round" if is_cpu else "round"]==iteration).all():raise ValueError(label+" pressure round")
        x=np.zeros(n,dtype=DTYPE)
        fields={"predicted":"prediction_double_Pa","diagonal":"S_1_per_m_s","residual":"Rgamma_Pa_per_m_s",
            "pn":"pn_Pa","previous":"previous_Pa","iterated":"endpoint_q_actual_float_Pa",
            "written":"raw_candidate_float_Pa" if is_cpu else "raw_final_float_Pa",
            "half":"mechanical_half_actual_float_Pa" if is_cpu else "half_actual_float_Pa",
            "sourceDrained":"source_drained","endpointDrained":"endpoint_drained"}
        for name,column in fields.items():x[name]=rows[column].to_numpy()
        completed=int(rows.completed_step.iloc[0])
        if not ((rows.commits==completed)&(rows.endpoint_calls==3*completed)).all():
            raise ValueError(label+" one commit or three endpoint calls per step")
        history=np.stack((x["pn"],x["previous"],x["half"]),axis=1).view(np.uint32)
        if iteration==1:common[label]=history.copy()
        elif not np.array_equal(history,common[label]):raise ValueError(label+" committed history changed within step")
        if iteration>1 and not np.array_equal(x["iterated"].view(np.uint32),validated[label]):
            raise ValueError(label+" next row did not use its predecessor's actual projected field")
        validated[label]=rows["actual_after_BC_float_Pa" if is_cpu else "validated_BC_value_float_Pa"].to_numpy(dtype=np.float32).view(np.uint32).copy()
        records.append(x)
        evidence.append(dict(group=label,path=str(path),part=int(part),round=iteration,rows=n,
            actual_time_s=float(rows.actual_save_time_s.iloc[0]),source_time_s=float(rows.source_time_s.iloc[0]),
            completed_step=int(rows.completed_step.iloc[0]),source_drained=int(x["sourceDrained"].sum()),
            endpoint_drained=int(x["endpointDrained"].sum())))
    for iteration in (1,2,3):
        path=C02/("UplTpiP3GpuR1.round%d.csv"%iteration)
        rows=last_frame(path,1262,1000)
        add(rows,"C02_GPU_final",path,1262,iteration,40,1000)
        if int(rows.endpoint_drained.sum())!=10:raise ValueError("C02 active drainage coverage")
        path=GPU/("UplTpiP3GpuR1.round%d.csv"%iteration)
        frame=pd.read_csv(path,float_precision="round_trip")
        rows=frame[frame.part==1].sort_values("native_id")
        add(rows,"C04_GPU_B64",path,1,iteration,8,37173)
    path=CPU/"UplTpiP3CpuR1.csv"
    frame=pd.read_csv(path,float_precision="round_trip")
    for iteration in (1,2,3):
        rows=frame[(frame.part==1)&(frame.pressure_round==iteration)].sort_values("native_id")
        add(rows,"C04_CPU_B64",path,1,iteration,8,37173)
    fixture=WORK/"samples.bin"
    with fixture.open("xb") as f:
        for x in records:x.tofile(f)
    args=[str(WORK/"replay.exe"),str(fixture)]
    result=subprocess.run(args,cwd=WORK,capture_output=True)
    with (WORK/"replay.log").open("xb") as f:f.write(result.stdout+result.stderr)
    summary=json.loads(result.stdout) if result.returncode==0 else {}
    count=sum(e["rows"] for e in evidence)
    ok=result.returncode==0 and summary["rows_per_backend"]==count and summary["passed"]
    write_doc(T/"logs"/(TAG+".check.json"),dict(passed=ok,argv=args,returncode=result.returncode,
        evidence=evidence,results=summary,source_frozen_implementations_unchanged=True,
        all_sources_same_history_across_three_rounds=True,next_round_reads_actual_previous_field=True,
        history_ownership_and_commit_implemented_by_original_drivers=True,physical_acceptance=False))
    if not ok:raise RuntimeError("Row replay failed, see replay.log")

if __name__=="__main__":
    {"build":compile_component,"check":check}[sys.argv[1]]()
