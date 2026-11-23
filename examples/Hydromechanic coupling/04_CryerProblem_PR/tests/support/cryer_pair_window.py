"""Drive an independent fixed-reference material-point Cryer ramp/hold/drain experiment."""
import argparse
import csv
import ctypes as ct
import json
import time
from pathlib import Path
import numpy as np
from scipy import sparse
from scipy.spatial import cKDTree
from cryer_coupled_shell_modes import T, DT, MU, LAM, DAMP
from c04_p3_pressure_component import CryerSPHPressure
from cryer_tet_mechanics import TetMechanics
from cryer_tet_av_reference import H, ALPHA, SOUND


def save_json(path, data):
    with path.open("x", encoding="utf8") as file:
        json.dump(data, file, indent=2, allow_nan=False)


class Driver:
    def __init__(self, dll):
        self.lib = ct.CDLL(str(dll.resolve()))
        self.lib.errorText.restype = ct.c_char_p
        pointer, integer, real = ct.c_void_p, ct.c_int, ct.c_double
        for name, args in {
            "init":[integer,real,real,real,real], "setCsr":[integer,integer,pointer,pointer,pointer],
            "setGeometry":[pointer]*6, "start":[], "advance":[integer], "readState":[pointer]*5,
            "forceFixture":[pointer,pointer,pointer,real,pointer,pointer,pointer],
            "pressureFixture":[pointer,pointer,pointer,integer,pointer], "release":[],
            "readPrevious":[pointer], "restore":[integer]+[pointer]*6
        }.items():
            getattr(self.lib,name).argtypes=args

    def call(self, name, *args):
        for a in args:
            if isinstance(a,np.ndarray) and not a.flags.c_contiguous:
                raise ValueError(f"Noncontiguous buffer for {name}")
        ptr=[ct.c_void_p(a.ctypes.data) if isinstance(a,np.ndarray) else a for a in args]
        if getattr(self.lib,name)(*ptr):
            raise RuntimeError(self.lib.errorText().decode())

    def upload(self,key,matrices):
        items=[m.sorted_indices() for m in matrices]
        a=items[0]
        for b in items[1:]:
            assert np.array_equal(a.indptr,b.indptr) and np.array_equal(a.indices,b.indices)
        values=a.data if len(items)==1 else np.column_stack([m.data for m in items])
        self.call("setCsr",key,a.nnz,a.indptr.astype(np.int32,copy=False),
                  a.indices.astype(np.int32,copy=False),np.ascontiguousarray(values,np.float64))


def viscosity_matrix(m):
    pairs=cKDTree(m.x).query_pairs(2*H,output_type="ndarray")
    i,j=pairs.T
    dx=m.x[i]-m.x[j]
    rr=np.einsum("ij,ij->i",dx,dx)
    assert np.ptp(m.native_volume)==0 and np.ptp(m.mass)==0
    values=ALPHA*SOUND*H*m.native_volume[0]*(-2.08891/H**5)*(1-np.sqrt(rr)/(2*H))**3/(rr+.01*H**2)
    matrix=sparse.coo_matrix((values,(i,j)),shape=(m.n,m.n)).tocsr()
    return (matrix+matrix.T).tocsr()


def validate(g,m,hydro):
    with np.load(T/"outputs/cryer_tet_step_reference_r1.npz") as f:
        assert np.array_equal(f["native_ids"],m.ids)
        v,s,p=[np.ascontiguousarray(f[key]) for key in ("v_m_s","stress_Pa","p_Pa")]
        av,pa,acc=[np.zeros_like(v) for _ in range(3)]
        g.call("forceFixture",v,s,p,float(f["q_Pa"]),av,pa,acc)
        err={"viscosity":float(abs(av-f["viscous_acceleration_m_s2"]).max()),
             "pressure":float(abs(pa-f["pressure_force_N"]/m.mass[:,None]).max()),
             "total_with_damping":float(abs(acc-(f["acceleration_m_s2"]-DAMP*v)).max())}
        if max(err.values())>1e-8:
            raise ArithmeticError(f"CPU-force mismatch {err}")
        theta=np.ascontiguousarray(f["divergence_v_per_s"])
        a=acc.astype(np.float32).astype(np.float64)
        div=m.divergence(a)
        out=np.zeros(m.n)
        for drain in (False,True):
            g.call("pressureFixture",p,acc,theta,int(drain),out)
            target=hydro.sweep(p,theta,a,div,drain)
            err[f"pressure_round_{'open' if drain else 'closed'}_Pa"]=float(abs(target-out).max())
            if not np.array_equal(target,out):
                raise ArithmeticError(f"Pressure comparison {err}")
    return err


def record(m,fs,step,arrays,rows,swriter,tri,normal,area):
    p,u,v,s,J=arrays
    surface=np.zeros(m.n,dtype=bool)
    surface[m.surface]=True
    assert np.array_equal(surface,fs) and all(np.isfinite(x).all() for x in arrays)
    radial=m.x/np.linalg.norm(m.x,axis=1)[:,None]
    inward=-1000*np.sum(u*radial,axis=1)
    speed=np.linalg.norm(v,axis=1)
    displacement=np.linalg.norm(u,axis=1)*1000
    sigma=p-s[:,:3].mean(axis=1)
    center=np.linalg.norm(m.x,axis=1)<.003
    assert center.sum()==18 and surface.sum()==5153
    rms=lambda x:float(np.sqrt(np.mean(x*x)))
    time_s=step*DT
    t=dict(step=step,time_s=time_s,tau_s=time_s-.0078125,center_Pa=p[center].mean(),
           mean_Pa=p.mean(),min_Pa=p.min(),max_Pa=p.max(),surface_absmax_Pa=abs(p[fs]).max(),
           rms_p_to_10000_Pa=rms(p-10000),rms_total_to_10000_Pa=rms(sigma-10000),
           max_speed_m_s=speed.max(),rms_speed_m_s=rms(speed),rms_displacement_mm=rms(displacement),
           rms_surface_displacement_mm=rms(inward[fs]),mean_inward_mm=inward.mean(),
           surface_inward_mm=1000*np.mean(np.linalg.norm(m.x[fs],axis=1)-np.linalg.norm(m.x[fs]+u[fs],axis=1)),
           min_J=J.min(),max_J=J.max(),
           max_radius_m=np.linalg.norm(m.x+u,axis=1).max(),kinetic_J=.5*np.sum(m.mass*speed**2))
    sface=s[tri].mean(axis=1)
    pressure_face=p[tri].mean(axis=1)
    q=1e4*min(max(step-1,0)/2048.,1.)
    traction=np.column_stack([np.sum(sface[:,k]*normal,axis=1)
                              for k in ([0,3,5],[3,1,4],[5,4,2])])
    residual=traction+(q-pressure_face)[:,None]*normal
    radial_residual=np.sum(residual*normal,axis=1)
    t["face_traction_rms_Pa"]=np.sqrt(np.average(np.sum(residual**2,axis=1),weights=area))
    t["face_tangent_rms_Pa"]=np.sqrt(np.average(np.sum((residual-radial_residual[:,None]*normal)**2,axis=1),weights=area))
    t["q_at_source_Pa"]=q
    assert np.all(J>1-float(np.float32(.3))) and t["max_radius_m"]<.0525
    if step>4096:
        assert np.all(p[fs]==0)
    rows.append(t)
    for shell in np.unique(m.shells):
        z=m.shells==shell
        swriter.writerow([step,time_s,shell,int(z.sum()),np.mean(p[z]),np.std(p[z]),
                          np.mean(sigma[z]),np.mean(inward[z]),np.max(speed[z]),np.mean(J[z])])
    return t


def execute(dll,out,target,resume=None,weak=None,*,prepare_viscosity=viscosity_matrix,check_forces=validate):
    out.mkdir(exist_ok=False)
    m=TetMechanics(T/"outputs/cryer_tet_reference_r1.npz")
    h=CryerSPHPressure.load()
    assert np.array_equal(m.ids,h.ids)
    with np.load(T/"outputs/cryer_tet_reference_r1.npz") as mesh:
        tri=mesh["faces"]
        area_vector=mesh["face_area_out"]
        area=np.linalg.norm(area_vector,axis=1)
        normal=area_vector/area[:,None]
    g=Driver(dll)
    g.call("init",m.n,DT,MU,LAM,DAMP)
    try:
        g.upload(0,m.D)
        g.upload(1,m.HT)
        for k in (2,3):
            g.upload(k,[h.E])
        g.upload(4,[prepare_viscosity(m)])
        geometry=[np.ascontiguousarray(buf) for buf in
                  (m.x,m.mass,m.unit_surface_force,1/h.S0,h.normal_lx,h.fs.astype(np.uint8))]
        g.call("setGeometry",*geometry)
        g.call("start")
        e=check_forces(g,m,h)
        if weak:
            e.update(weak(g,m,h))
        save_json(out/"fixture.json",e)
        print("Independent mechanics and pressure fixtures",e,flush=True)
        arrays=[np.empty(shape) for shape in (m.n,(m.n,3),(m.n,3),(m.n,6),m.n)]
        rows=[]
        current=0
        if resume:
            check=json.loads((resume.parent/"completed.json").read_text())
            if not (check["closed_pass"] and check["steps"]==4160 and target>4160):
                raise ValueError("Continuation requires accepted closed equilibrium and reviewed first opening")
            with np.load(resume) as z:
                if not np.array_equal(z["ids"],m.ids) or int(z["step"])!=4160 or z["program"].item()!=str(dll.resolve()):
                    raise ValueError("Incompatible material IDs, program or clock")
                g.call("restore",4160,*[np.ascontiguousarray(z[k]) for k in ("p","previous","u","v","stress","J")])
                g.call("readState",*arrays)
                previous=np.empty(m.n)
                g.call("readPrevious",previous)
                assert np.array_equal(previous,z["previous"])
                assert all(np.array_equal(a,z[k]) for a,k in zip(arrays,("p","u","v","stress","J")))
            current=4160
        steps=sorted({current,1,2,4,8,16,32,4097,target,*range(64,target+1,64)})
        steps=[i for i in steps if current<=i<=target]
        started=time.perf_counter()
        with (out/"shells.csv").open("x",newline="") as sf,(out/"history.csv").open("x",newline="") as hf:
            shells=csv.writer(sf)
            shells.writerow(["step","time_s","material_shell","count","p_mean_Pa","p_std_Pa","total_compression_Pa",
                             "inward_mm","speed_max_m_s","mean_J"])
            hist=None
            for step in steps:
                if step>current:
                    g.call("advanceWeak" if weak else "advance",step-current)
                current=step
                g.call("readState",*arrays)
                row=record(m,h.fs,step,arrays,rows,shells,tri,normal,area)
                if hist is None:
                    hist=csv.DictWriter(hf,fieldnames=row);hist.writeheader()
                hist.writerow(row);hf.flush();sf.flush()
                if step in (64,2048,3904,4096,4097,target) or step%512==0:
                    print(f'step {step}: center {row["center_Pa"]:.4f} Pa, max speed {row["max_speed_m_s"]:.6g} m/s, elapsed {time.perf_counter()-started:.1f} s',flush=True)
                if step in (4096,4097,target):
                    previous=np.empty(m.n)
                    g.call("readPrevious",previous)
                    np.savez(out/f"state_{step}.npz",ids=m.ids,p=arrays[0],previous=previous,
                             u=arrays[1],v=arrays[2],stress=arrays[3],J=arrays[4],step=step,program=str(dll.resolve()))
        closed=[r for r in rows if r["step"] in (3904,3968,4032,4096)]
        limits={"rms_p_to_10000_Pa":100,"rms_total_to_10000_Pa":100,"max_speed_m_s":1e-5,
                "rms_displacement_mm":1e-5,"rms_surface_displacement_mm":1e-5}
        save_json(out/"completed.json",dict(solver="fixed-reference research component",steps=current,
                    material_ids=m.n,wall_seconds=time.perf_counter()-started,fixture=e,closed_limits=limits,
                    closed_max={k:max(r[k] for r in closed) for k in limits} if closed else {},
                    closed_pass=len(closed)==4 and all(r[k]<=v for r in closed for k,v in limits.items())))
    except Exception as exc:
        save_json(out/"interrupted.json",dict(reason=str(exc),last_read_step=rows[-1]["step"] if locals().get("rows") else None))
        raise
    finally:
        g.call("releaseWeak" if weak else "release")


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dll",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--steps",type=int,choices=(4160,36864),default=4160)
    ap.add_argument("--resume",type=Path)
    a=ap.parse_args()
    if a.steps>4160 and not a.resume:
        ap.error("Opening review and exact checkpoint are required to extend this research window")
    execute(a.dll,a.out,a.steps,a.resume)
