"""Bind the reviewed local Cryer implementation evidence to one distributable Release."""
import csv
import json
from pathlib import Path

T=Path(__file__).resolve().parents[1]
L=T/"logs"
F=T/"figures"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stat(path):
    path=path.resolve()
    s=path.stat()
    return dict(path=str(path),bytes=s.st_size,mtime_ns=s.st_mtime_ns)


def qualify():
    evidence=[]
    def checked(path):
        value=json.loads(path.read_text(encoding="utf-8-sig"))
        require(value.get("passed") is True, str(path))
        evidence.append(stat(path))
        return value
    def table(name):
        path=F/(name+".csv")
        with path.open(newline="") as f: rows=list(csv.DictReader(f))
        evidence.append(stat(path))
        return rows
    release=checked(L/"cryer_p3_gpu_r2_Release.build.json")
    debug=checked(L/"cryer_p3_gpu_r2_Debug.build.json")
    program=release["program"]
    require(stat(Path(program["path"]))==program, "Release identity")
    dt=2**-19
    for tag,n in (("debug2",2),("default128",128),("b64",64),("drain4097",4097)):
        run=checked(L/f"cryer_p3_gpu_{tag}_r1.run.json")
        exe=(debug if tag=="debug2" else release)["program"]
        require(run["inputs"][0]==exe and run["n"]==n and run["win32_exit"]==run["popen_exit"]==0,"owned run "+tag)
        require(run["dt"]==(2**-20 if tag=="default128" else dt),"profile step")
        if tag!="default128":
            side=checked(L/f"cryer_p3_sides_{tag}_r1.check.json")
            require(side["steps"]==n and side["dt_phases"]==5 and side["pressure_rounds"]==3 and side["min_selected_bound_s"]>=dt,"P3 records "+tag)
        else:
            require(run["tpi_environment"]=={},"unexpected private default selector")
    mem=L/"cryer_p3_gpu_debug2_r1.memcheck.log"
    require("ERROR SUMMARY: 0 errors" in mem.read_text(),"memcheck")
    evidence.append(stat(mem))
    for suffix in ("run","pressure_review","native_pressure_binding"):
        checked(L/f"upl_tpi_cryer_p3_cpu_B64_r1.{suffix}.json")
    checked(L/"upl_tpi_cryer_pressure_row_r1.check.json")
    exact=table("cryer_p3_gpu_default128_r1")
    require(len(exact)==2 and all(float(row["compare_pressure_rms_Pa"])==float(row["compare_displacement_max_mm"])==0 for row in exact),"default A regression")
    cross=table("cryer_p3_cpu_gpu_b64_r1")
    pr=max(float(row["compare_pressure_rms_Pa"]) for row in cross)
    mm=max(float(row["compare_displacement_max_mm"]) for row in cross)
    require(len(cross)==2 and pr<=5 and mm<=.005,"cross-backend")
    history=table("cryer_p3_gpu_drain4097_r1")
    require([int(r["completed_step"]) for r in history]==[*range(0,4097,64),4097],"4097 native schedule")
    require(all(int(r["active_drain_count"])==0 for r in history[:-1]),"unexpected earlier drainage")
    closed,opened=history[-2:]
    require(float(closed["time_s"])==2**-7 and float(opened["time_s"])==4097*dt,"drain source clock")
    require(float(closed["surface_p_absmax_Pa"])>0 and float(opened["surface_p_absmax_Pa"])==0,"drain transition")
    require(int(opened["surface_count"])==int(opened["active_drain_count"])>0,"empty/open drain set")
    out=L/"cryer_tpi_p3_server_qualification_r1.json"
    with out.open("x",encoding="utf-8") as f:
        json.dump(dict(passed=True,scheme="B",rounds=3,nu=.3,dt_s=dt,program=program,evidence=evidence,
                       center18_preopen_Pa=float(closed["center18_Pa"]),
                       last_preopen_FS_absmax_Pa=float(closed["surface_p_absmax_Pa"]),
                       postopen_receivers=int(opened["active_drain_count"]),
                       CPU_GPU_startup_pressure_RMS_Pa=pr,CPU_GPU_startup_max_displacement_mm=mm,
                       default_A_native_22_exact_frames=2,
                       local_scope="3D startup implementation and first post-opening save",
                       server_peak_or_full_completed=False,physical_acceptance=False),f,indent=2,allow_nan=False)
    print(out)


if __name__=="__main__":
    qualify()
