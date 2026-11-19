"""Independent Cryer BI4 audit. No solver, GenCase or native-file writes."""
from pathlib import Path
import argparse
import csv
import json
import sys
from itertools import islice

import numpy as np

TESTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TESTS.parents[1] / "02_TerzaghiConsolidation_q0_PR/tests/support"))
from upl_tpi_partial_bi4_r1 import read

CENTER = [17338,17343,17769,17770,17771,17772,18412,18443,18592,18755,18756,
          18757,18758,19403,19460,19553,19554,19979]
TYPES = {"DatUint": "Idp FSType", "DatFloat3": "Vel Sigma_kk Sigma_ij FSNormal HydroMechLoadAce",
         "DatDouble3": "Posd SigmaState_kk SigmaState_ij",
         "DatFloat": "Rhop Kplastic PosDiv PorePress PorePress0 ExcessPorePress",
         "DatDouble": "PoroVolumeRatio PoroPorosity PoroThetaLastStage PoroCurrentVolume PoroMixtureDensity PoroHydraulicConductivity"}
EXPECTED_TYPES = {name: typ for typ,names in TYPES.items() for name in names.split()}
T_D = 2**-7
SOIL = slice(8,None)
N0 = float(np.float32(.3))
K0 = float(np.float32(1e-5))
MASS = float(np.float32(.0000328125))
RHO0 = 2100.
TOTAL = 37181


def need(ok, message):
    if not ok:
        raise ValueError(message)


def snapshot(path, part, step, dt):
    b = read(path)
    root,meta = b["root"]["values"], b["part"]["values"]
    root_expected = dict(CaseNp=TOTAL, CaseNfixed=8, CaseNfluid=37173, Data2d=0,
                         Npiece=1, Piece=0, ReuseIds=0, NpDynamic=0, PeriMode=0,
                         CaseNmoving=0, CaseNfloat=0, Symmetry=0, Dp=.0025,
                         H=float(np.float32(.0045)), Rhop0=RHO0, MassFluid=MASS, MassBound=MASS)
    need(all(root[k]==v for k,v in root_expected.items()), "native sphere/header differs")
    expected = dict(Cpart=part, Npok=TOTAL, Nout=0, Step=max(step-1,0),
                    TimeStep=float(step*dt), SymplecticDtPre=dt,
                    HydroMechDynamicSeepage=1, DynamicSeepageSchema=1,
                    HydroMechConductivityModel=0, HydroMechConductivityCk=0.)
    need(all(meta[k]==v for k,v in expected.items()), "native event/step/metadata differs")
    required_types = {"HydroMechDynamicSeepage":2,"DynamicSeepageSchema":8,
                      "HydroMechConductivityModel":8,"HydroMechConductivityCk":12,
                      "SymplecticDtPre":12,"dterror":12}
    need(all(b["part"]["types"][k]==v for k,v in required_types.items()), "metadata type differs")
    err=meta["dterror"]
    need(np.isfinite(err) and err<=1e-14 and (part==0 or err != -sys.float_info.max), "signed dt error")
    need({k:v["type_name"] for k,v in b["types"].items()}==EXPECTED_TYPES,"22 native types differ")
    source=b["arrays"]
    order=np.argsort(source["Idp"])
    need(np.array_equal(source["Idp"][order],np.arange(TOTAL)), "native ID coverage differs")
    arrays={k:v[order] for k,v in source.items()}
    need(all(np.isfinite(v).all() for v in arrays.values()), "nonfinite native record")
    return arrays, float(err)


def physical(a, initial, post):
    pos=a["Posd"]
    p=a["PorePress"]
    for k in ("PorePress0","Kplastic"):
        need(not np.any(a[k]),"nonzero "+k)
    need(np.array_equal(a["ExcessPorePress"],p-a["PorePress0"]), "float excess differs")
    need(np.all((a["Rhop"]>=700)&(a["Rhop"]<=3000)) and np.max(a["FSType"])<=4,"density/FS guard")
    for k in ("kk","ij"):
        need(np.array_equal(a["Sigma_"+k],a["SigmaState_"+k].astype(np.float32)), "stress display differs")
    need(np.array_equal(pos[:8].view("u8"),initial[:8].view("u8")) and not np.any(a["Vel"][:8]),"fixed geometry")
    for k in ("PoroThetaLastStage","PoroPorosity","PoroCurrentVolume","PoroMixtureDensity","PoroHydraulicConductivity"):
        need(not np.any(a[k][:8]), "fixed marker "+k)
    j=a["PoroVolumeRatio"][SOIL]
    need(np.all(a["PoroVolumeRatio"][:8]==1) and np.all(j>1-N0), "invalid J")
    radius=np.linalg.norm(pos[SOIL],axis=1)
    need(np.min(radius)>0 and np.max(radius)<=.0525, "sphere radius")
    n=a["PoroPorosity"][SOIL]
    need(np.all((n>0)&(n<1)) and np.max(np.abs((1.-n)*j-(1.-N0)))<=5e-13, "solid-volume ledger")
    for k,ref in (("PoroPorosity",1-(1-N0)/j),("PoroCurrentVolume",(MASS/RHO0)*j),
                  ("PoroMixtureDensity",1000+(RHO0-1000)/j),("PoroHydraulicConductivity",K0)):
        need(np.allclose(a[k][SOIL],ref,rtol=5e-13,atol=0), "saved J ledger "+k)
    fs=np.isin(a["FSType"][SOIL],[2,3])
    if post:
        need(fs.any() and not p[SOIL][fs].any(), "active FS2/3 pressure")
    move=pos[SOIL]-initial[SOIL]
    r0=np.linalg.norm(initial[SOIL],axis=1)
    effective=-np.mean(a["SigmaState_kk"][SOIL],axis=1)
    saved_mass=a["PoroMixtureDensity"][SOIL]*a["PoroCurrentVolume"][SOIL]
    saved_load=a["HydroMechLoadAce"][SOIL].astype(float)*saved_mass[:,None]
    radial=np.einsum("ij,ij->i",saved_load,pos[SOIL])/radius
    return dict(center18_Pa=float(np.mean(p[CENTER],dtype=np.float64)),
                center18_std_Pa=float(np.std(p[CENTER],dtype=np.float64)),
                pressure_min_Pa=float(np.min(p[SOIL])),pressure_max_Pa=float(np.max(p[SOIL])),
                mean_pressure_Pa=float(np.mean(p[SOIL],dtype=np.float64)),
                mean_total_compression_Pa=float(np.mean(effective+p[SOIL])),
                saved_J_inward_load_proxy_N=float(-radial.sum()),
                saved_J_net_load_proxy_N=float(np.linalg.norm(saved_load.sum(axis=0))),
                rms_total_error_to_closed_load_Pa=float(np.sqrt(np.mean((effective+p[SOIL]-10000)**2))),
                mean_inward_mm=float(1000*np.mean(r0-radius)),
                shell_inward_mm=float(1000*np.mean((r0-radius)[r0>=.05-2*float(np.float32(.0045))])),
                max_displacement_mm=float(1000*np.max(np.linalg.norm(move,axis=1))),
                max_speed_m_s=float(np.max(np.linalg.norm(a["Vel"][SOIL].astype(float),axis=1))),
                J_min=float(j.min()),J_max=float(j.max()),surface_count=int(fs.sum()),
                surface_p_absmax_Pa=float(np.max(np.abs(p[SOIL][fs]),initial=0)),
                active_drain_count=int(fs.sum()) if post else 0)


def saved_observations(folder, steps):
    """Read only the actual saved final-round rows and the corresponding phase intervals."""
    ids=np.arange(8,TOTAL) if steps[-1]<=64 else np.asarray(CENTER)
    with (folder/"UplTpiP3GpuR1.round3.csv").open(newline="") as pressure, (folder/"UplTpiP3DtR1.csv").open(newline="") as clock:
        rows=csv.DictReader(pressure)
        ticks=csv.DictReader(clock)
        for i,step in enumerate(steps):
            segment=list(islice(rows,len(ids)))
            tick=next(ticks)
            need(len(segment)==len(ids) and all(int(r["part"])==i and int(r["round"])==3 and int(r["completed_step"])==step for r in segment),"round3 save identity")
            need([int(r["native_id"]) for r in segment]==ids.tolist(),"round3 saved material IDs")
            need(int(tick["part"])==i and int(tick["completed_updates"])==step,"phase save identity")
            yield ids,np.array([float(r["final_field_float_Pa"]) for r in segment],dtype=np.float32),np.array([float(r["Jfull"]) for r in segment]),tick
        need(next(rows,None) is None and next(ticks,None) is None,"trailing sidecar rows")


def audit(data, steps, dt, reference=None, exact=False, p3_sidecars=False, radial=None):
    files=sorted(data.glob("Part_*.bi4"))
    need(len(files)==len(steps),"native file count differs from plan")
    if reference:
        need(len(list(reference.glob("Part_*.bi4")))==len(steps),"reference schedule differs")
    history=[]
    observed=saved_observations(data.parent,steps) if p3_sidecars else None
    for i,(file,step) in enumerate(zip(files,steps)):
        need(file.name==f"Part_{i:04d}.bi4","non-contiguous PART")
        a,err=snapshot(file,i,step,dt)
        if observed is not None:
            cohort,pressure,J,tick=next(observed)
            need(a["PorePress"][cohort].tobytes()==pressure.tobytes() and a["PoroVolumeRatio"][cohort].tobytes()==J.tobytes(),"native pressure/J differs from committed endpoint")
            need(float(tick["actual_save_time_s"])==step*dt and int(tick["saved_step"])==max(step-1,0),"sidecar/native clock")
            interval=float(tick["max_dt_minus_bound_s"])
            if i:
                need(np.float64(interval).tobytes()==np.float64(err).tobytes(), "noninitial signed interval differs")
            else:
                need(interval==-sys.float_info.max and err in (0.,-sys.float_info.max),"unexpected initial interval convention")
        if not i:
            initial=a["Posd"].copy()
            ids=np.flatnonzero(np.linalg.norm(initial,axis=1)<=.0025+1e-12)
            need(ids.tolist()==CENTER and np.max(np.abs(np.linalg.norm(initial[CENTER],axis=1)-.0025))<1e-15,"fixed r0/a=.05 cohort")
            need(all(not np.any(a[k]) for k in ("Vel","PorePress","PoroThetaLastStage","SigmaState_kk","SigmaState_ij","HydroMechLoadAce")) and np.all(a["PoroVolumeRatio"]==1), "initial rest")
        # All admitted dt are powers of two, and step fits exactly in binary64.
        time=step*dt
        row=dict(part=i,completed_step=step,time_s=time,tau_s=time-T_D,signed_dterror_s=err)
        row.update(physical(a,initial,time>T_D))
        if radial is not None:
            if not i:
                radial.set_materials(np.linalg.norm(initial[SOIL],axis=1),a["PoroCurrentVolume"][SOIL])
                # CENTER was established from sorted initial native IDs above.
                # Freeze its material connectivity once, before the sphere deforms.
                from cryer_material_shell_volume import faces, volume
                center_faces=faces(initial[CENTER])
                center_volume=volume(initial[CENTER],center_faces)
            center_effective=np.mean(a["SigmaState_kk"][CENTER],dtype=np.float64)
            row.update(center18_effective_mean_tensile_Pa=float(center_effective),
                       center18_total_compression_Pa=row["center18_Pa"]-float(center_effective),
                       center18_J_minus_1=float(a["PoroVolumeRatio"][CENTER].mean()-1),
                       center18_enclosed_volume_change=float(volume(a["Posd"][CENTER],center_faces)/center_volume-1))
            radial.observe(row,a["PorePress"][SOIL],a["FSType"][SOIL])
        if reference:
            other,other_err=snapshot(reference/file.name,i,step,dt)
            if exact:
                for k in EXPECTED_TYPES:
                    need(a[k].tobytes()==other[k].tobytes(),f"default path changed {k} in {file.name}")
                need(np.float64(err).tobytes()==np.float64(other_err).tobytes(),"signed dt bytes differ")
            diff=a["PorePress"][SOIL].astype(float)-other["PorePress"][SOIL]
            disp=1000*np.linalg.norm(a["Posd"][SOIL]-other["Posd"][SOIL],axis=1)
            row.update(compare_pressure_rms_Pa=float(np.sqrt(np.mean(diff**2))),
                       compare_displacement_max_mm=float(np.max(disp)))
            need(row["compare_pressure_rms_Pa"]<=5 and np.max(disp)<=.005, "backend comparison exceeded")
        history.append(row)
    if observed is not None:
        need(next(observed,None) is None,"extra save information")
    return history


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("data",type=Path)
    parser.add_argument("history",type=Path)
    parser.add_argument("steps",type=int,choices=[2,64,128,4097,36864])
    parser.add_argument("--reference",type=Path)
    parser.add_argument("--exact",action="store_true")
    parser.add_argument("--p3-sidecars",action="store_true")
    args=parser.parse_args()
    need(not args.history.exists() and (not args.exact or args.reference),"fresh output and valid reference required")
    dt=2**(-20 if args.steps==128 else -19)
    steps=list(range(0,args.steps+1,round(2**-13/dt)))
    if steps[-1]!=args.steps:
        steps.append(args.steps)
    history=audit(args.data,steps,dt,args.reference,args.exact,args.p3_sidecars)
    with args.history.open("x",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(history[0]))
        w.writeheader()
        w.writerows(history)
    print(json.dumps({"frames":len(history),"end":history[-1],"drained_receivers":sum(r["active_drain_count"] for r in history)},indent=2))
