"""Replay the closed-wall native PRE once with archived physical CPU objects."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np

TAG = "c08_pre_m0_r1"
T = Path(__file__).resolve().parents[1]
BUILD = T/"outputs"/(TAG+"_build")
OUT = T/"outputs"/TAG
PRE = T/"outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4"
SRC = T/"support"/(TAG+".cpp")


def build():
    import c08_h18_wend_matrix_r1 as m
    old = m.read(m.L/"c08_tpi_state_r1.build.json")
    assert old["passed"] and not OUT.exists() and not BUILD.exists()
    for item in old["retained_physical_objects"]+old["runtime"]+old["generated_includes"]:
        m.bind(item)
    objlist = m.read(m.bind(old["original_object_list"])["path"])
    libfile = Path(m.bind(objlist["resolved_library_tlog"])["path"])
    libs = [Path(q.strip('"')).parent for q in libfile.read_text(encoding="utf-16").splitlines()
            if not q.startswith("^") and q.lower().endswith(".lib")]
    setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                           stdout=subprocess.PIPE, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    env = {k.upper():v for k,v in os.environ.items()}
    env.update((k.upper(),v) for k,v in (q.split("=",1) for q in setup.stdout.decode("mbcs").splitlines()
                                          if "=" in q and not q.startswith("=")))
    assert env["VCTOOLSVERSION"] == "14.36.32532" and libs
    env["LIB"] = ";".join(dict.fromkeys(map(str,libs)))
    env["OMP_NUM_THREADS"] = "1"
    env.pop("CL", None)
    env.pop("_CL_", None)
    oldexe = Path(m.bind(old["program"])["path"])
    exe = BUILD/"ClosedPreProbe.exe"
    BUILD.mkdir()
    calls = []
    for suffix, binding in zip(("compile","link"), old["calls"]):
        rec = m.read(m.bind(binding)["path"])
        args = [str(SRC) if a==old["source"]["path"] else a.replace(str(oldexe),str(exe)).replace(str(oldexe.parent),str(BUILD))
                for a in rec["arguments"]]
        calls.append(m.invoke(TAG+"."+suffix,[rec["program"],*args],T.parents[3]/"src/VS",env))
    for dep in old["runtime"]:
        shutil.copy2(dep["path"],BUILD/Path(dep["path"]).name)
    source = PRE.parents[1]
    calls.append(m.invoke(TAG+".component",[str(exe),"-cpu","-ompthreads:1","-stable","-mdbc_freeslip",
                                           str(source/source.name),str(OUT)],T.parent,env))
    return calls


def describe(rows):
    def span(q):
        return [float(np.min(q)),float(np.max(q))]
    def rms(q):
        return float(np.sqrt(np.mean(q*q)))
    def group(mask):
        r = rows[mask]
        R = r["Rgamma"]
        dp = R/r["S_LP"]
        return dict(count=len(r),R_RMS_Pa_m_s=rms(R),R_abs_max_Pa_m_s=float(np.max(abs(R))),
                    abs_dp_p50_p95_p99_max_Pa=np.quantile(abs(dp),[.5,.95,.99,1]).tolist(),
                    R_over_arithmetic_bound_gt1_count=int(sum(abs(R)>r["roundoff_bound"])),
                    compression_RMS=rms(r["compression"]),Darcy_RMS=rms(r["Darcy"]),gradk_RMS=rms(r["gradk"]),
                    signed_volume_Rgamma_over_gamma_m2_s=float(np.sum(r["V_m2"]*R)/9806.65))
    assert len(rows)==5000 and np.array_equal(np.sort(rows["id"]),np.arange(2060,7060))
    assert np.isfinite(np.column_stack([rows[n] for n in rows.dtype.names])).all()
    assert np.all(rows["S_LP"]>0)
    fs = np.isin(rows["FS_fresh"],[2,3])
    assert np.array_equal(fs,np.isin(rows["FS_saved"],[2,3])) and np.all(rows["p_Pa"][fs]<=0)
    groups = {"all":np.ones(len(rows),bool),"non_FS":~fs,"interior_no_wall_donor":~fs&(rows["wall_neighbors"]==0),
              "non_FS_wall_donor":~fs&(rows["wall_neighbors"]>0),"FS":fs}
    return dict(groups={n:group(mask) for n,mask in groups.items()},FS_fresh_changes=int(sum(rows["FS_saved"]!=rows["FS_fresh"])),
                FS_zero=int(sum(fs&(rows["p_Pa"]==0))),FS_negative=int(sum(fs&(rows["p_Pa"]<0))),
                all_negative_pressure=int(sum(rows["p_Pa"]<0)),FS_zero_R_positive=int(sum(fs&(rows["p_Pa"]==0)&(rows["Rgamma"]>0))),
                range={n:span(rows[n]) for n in ("p_Pa","p0_Pa","J","kappa","sxx_Pa","syy_Pa","szz_Pa","sxz_Pa","n","k_m_s","actual_finite_kw_rate_Pa_s")},
                nonzero_kappa=int(sum(rows["kappa"]!=0)),max_speed_m_s=float(np.max(np.hypot(rows["vx_m_s"],rows["vz_m_s"]))),
                excess_p_range_Pa=span(rows["p_Pa"]-rows["p0_Pa"]),theta_saved_minus_fresh_RMS=rms(rows["theta_saved_s_1"]-rows["theta_fresh_s_1"]))


if __name__=="__main__":
    if sys.argv[1:]==["--review"]:
        sys.path.insert(0,str(T.parents[1]/"02_TerzaghiConsolidation_q0_PR/tests/support"))
        from upl_tpi_partial_bi4_r1 import read
        receipt=json.loads((T/"logs"/(TAG+".check.json")).read_text(encoding="utf-8"))
        rows=np.genfromtxt(OUT/"rows.csv",delimiter=",",names=True)
        with PRE.open("rb") as fh:
            assert hashlib.file_digest(fh,"sha256").hexdigest()==receipt["source_sha256"]
        frame=read(PRE)
        a,meta=frame["arrays"],frame["part"]["values"]
        assert len(a)==22 and meta["Npok"]==7060
        assert meta["GravityPreloadPhase"]==0 and meta["Step"]+1==2000000 and meta["Nout"]==0
        byid=np.argsort(a["Idp"])
        assert np.array_equal(a["Idp"][byid],np.arange(7060))
        idx=byid[rows["id"].astype(int)]
        native_fields={"PorePress":"p_Pa","PorePress0":"p0_Pa","Kplastic":"kappa","PoroVolumeRatio":"J",
                       "FSType":"FS_saved","PoroThetaLastStage":"theta_saved_s_1"}
        for key,column in native_fields.items():
            assert np.array_equal(a[key][idx],rows[column]),key
        for key,columns in (("SigmaState_kk",("sxx_Pa","syy_Pa","szz_Pa")),("SigmaState_ij",(None,None,"sxz_Pa")),
                            ("Posd",("x_m",None,"z_m")),("Vel",("vx_m_s",None,"vz_m_s"))):
            for axis,column in enumerate(columns):
                if column:
                    assert np.array_equal(a[key][idx,axis],rows[column]),column
        assert all(receipt[k]==v for k,v in describe(rows).items())
        assert np.array_equal(rows["Rgamma"],rows["compression"]+rows["Darcy"]+rows["gradk"])
        storage=9806.65*rows["n"]/1e9
        mismatch=np.abs(rows["Rgamma"]-storage*rows["actual_finite_kw_rate_Pa_s"])
        assert np.all(mismatch<=rows["roundoff_bound"]+np.finfo(np.float32).eps*np.abs(rows["Rgamma"]))
        surface=np.isin(rows["FS_fresh"],[2,3])
        candidate=(rows["p_Pa"]+rows["Rgamma"]/rows["S_LP"]).astype(np.float32)
        changed=(candidate!=rows["p_Pa"]) & ~surface
        print(json.dumps(dict(native_soil_rows_verified=len(rows),non_FS_float32_pressure_changes=int(changed.sum()),
              non_FS_particles=int((~surface).sum()),projected_FS_positive=int((surface & (candidate>0)).sum()),
              max_storage_times_rate_difference=float(mismatch.max())),indent=2))
        sys.exit(0)
    assert len(sys.argv)==1
    import c08_h18_wend_matrix_r1 as m
    calls=build()
    rows=OUT/"rows.csv"
    result=describe(np.genfromtxt(rows,delimiter=",",names=True))
    with PRE.open("rb") as f:
        digest=hashlib.file_digest(f,"sha256").hexdigest()
    m.save(m.L/(TAG+".check.json"),dict(passed=True,calls=calls,actual_force_evaluations=1,physical_steps=0,wall_retirements=0,
          source_compute_backend="retained GPU finite Kw",spatial_operator_backend="archived DebugCPU",
          source=m.stat(PRE),source_sha256=digest,source_run=m.stat(m.L/"c08_h18_wend_psi0_pre_r2.run.json"),
          retained_build=m.stat(m.L/"c08_tpi_state_r1.build.json"),component_source=m.stat(SRC),rows=m.stat(rows),**result))
    print(json.dumps(result,indent=2))
