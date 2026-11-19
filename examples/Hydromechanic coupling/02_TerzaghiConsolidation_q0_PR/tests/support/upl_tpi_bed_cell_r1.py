"""Independent material half-cell geometry and sampled-clock integral; retain point/mean distinction."""
import json
import struct
from pathlib import Path

import numpy as np
import pandas as pd

T = Path(__file__).resolve().parents[1]
TAG = "upl_tpi_bed_cell_r1"
M = 1666666.75 + 4*769230.8125/3


def main():
    source=T/"outputs/upl_tpi_p3_B10us_full2tv_GPU_r1_native_full10us_r1"
    outputs=[T/"figures"/(TAG+".csv"),T/"figures"/(TAG+"_quadrature.csv"),T/"logs"/(TAG+".check.json")]
    if any(p.exists() for p in outputs):raise RuntimeError("Use sealed review")
    path=source/"physical.bin"
    with path.open("rb") as f:
        if struct.unpack("<3I",f.read(12))!=(1000,26,1653):raise ValueError("Native header")
    dtype=np.dtype([("t","<f8"),("q","<f8",(1000,26))])
    if path.stat().st_size != 12+1653*dtype.itemsize:raise ValueError("Native extent")
    ids=pd.read_csv(source/"native_ids.csv",float_precision="round_trip")
    plan=pd.read_csv(T.parent/"figures/upl_tpi_p3_full_diagnostic_r1/history.csv",float_precision="round_trip")
    if not np.array_equal(ids.id,np.arange(40,1040)):
        raise ValueError("Native IDs/clock")
    layer=np.rint(ids.z0/.01-.5).astype(int)
    # Read the sealed 344-MB file once in storage order even on a contended disk.
    q=np.empty((1653,2,26))
    t=np.empty(1653)
    with path.open("rb") as f:
        f.seek(12)
        for start in range(0,1653,32):
            count=min(32,1653-start)
            records=np.frombuffer(f.read(count*dtype.itemsize),dtype=dtype,count=count)
            t[start:start+count]=records["t"]
            for k in (0,1):
                q[start:start+count,k]=records["q"][:,np.asarray(layer)==k,:].mean(axis=1)
    if not np.array_equal(t,plan.time_s):raise ValueError("Actual times changed")
    def val(k,col):
        return q[:,k,col]
    tab=pd.DataFrame(dict(part=plan.part,time_s=t,completed_step=plan.completed_step))
    z,vel,J,theta,p,stress=[val(0,c) for c in (2,5,8,9,6,15)]
    z1,vel1=val(1,2),val(1,5)
    # Lower material face is the fixed z=0 plane. Upper face is the midpoint of
    # the first and second layer centers, advected at their mean velocity.
    dz_lower=z
    dz_upper=.5*(z1-z)
    lower_rate = vel/dz_lower
    upper_rate = .5*(vel1-vel)/dz_upper
    cell_rate = .5*(vel1+vel)/(dz_lower+dz_upper)
    Jgeo=(dz_lower+dz_upper)/(dz_lower[0]+dz_upper[0])
    ef_geom=M*np.log(Jgeo)
    ef_state=M*np.log(J)
    pr=plan.ref_bottom_pressure_Pa
    tab["bottom_z_m"]=z;tab["upper_face_z_m"]=dz_lower+dz_upper
    tab["lower_half_J"]=dz_lower/dz_lower[0];tab["upper_half_J"]=dz_upper/dz_upper[0]
    tab["cell_J"]=Jgeo;tab["native_point_J"]=J
    tab["lower_half_velocity_rate_s1"]=lower_rate;tab["upper_half_velocity_rate_s1"]=upper_rate
    tab["upper_face_velocity_m_s"]=.5*(vel1+vel);tab["cell_divergence_s1"]=cell_rate
    tab["saved_last_force_theta_s1"]=theta
    tab["material_stress_minus_M_log_native_J_Pa"]=stress-ef_state
    tab["M_log_native_J_minus_cell_Pa"]=ef_state-ef_geom
    tab["M_log_cell_minus_target_effective_Pa"]=ef_geom+10000.-pr
    tab["reference_minus_native_pressure_Pa"]=pr-p
    tab["original_total_error_Pa"]=stress-p+10000.
    pieces=tab.iloc[:,-5:-1].sum(axis=1,skipna=False)
    if (pieces-tab.original_total_error_Pa).abs().max()>1e-8:raise ValueError("Decomposition")
    windows=[(0,1652),(0,1428),(1428,1652),(1262,1652)]
    quadrature=[]
    for a,b in windows:
        for stride in (1,2,4):
            ix=np.unique(np.r_[np.arange(a,b+1,stride),b])
            dt=np.diff(t[ix])
            def integ(y):return np.dot(dt,.5*(y[ix][:-1]+y[ix][1:]))
            quadrature.append(dict(first_part=a,last_part=b,first_time=float(t[a]),last_time=float(t[b]),
                stride_saved_only=stride,samples=len(ix),largest_save_gap_s=float(dt.max()),
                actual_updates=int(plan.completed_step[b]-plan.completed_step[a]),
                native_lnJ_change=float(np.log(J[b]/J[a])),sample_integral_saved_theta=float(integ(theta)),
                actual_cell_lnJ_change=float(np.log(Jgeo[b]/Jgeo[a])),sample_integral_cell_rate=float(integ(cell_rate)),
                native_closure_equivalent_Pa=float(M*(integ(theta)-np.log(J[b]/J[a]))),
                cell_closure_equivalent_Pa=float(M*(integ(cell_rate)-np.log(Jgeo[b]/Jgeo[a])))))
    tab.to_csv(outputs[0],index=False)
    pd.DataFrame(quadrature).to_csv(outputs[1],index=False)
    outputs[2].write_text(json.dumps(dict(frames=len(tab),final=tab.iloc[-1].to_dict(),
        quadrature=quadrature,saved_stages_sufficient_to_reconstruct_method=False,physical_acceptance=False),
        indent=2,allow_nan=False)+"\n",encoding="utf-8")


if __name__ == "__main__":main()
