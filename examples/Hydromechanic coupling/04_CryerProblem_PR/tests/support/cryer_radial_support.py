"""Frozen-geometry sensitivity of the corrected velocity gradient to its kernel radius."""
import json
from cryer_shell_equilibrium import NATIVE, TESTS, TOTAL, SOIL, Reference, Q, R, need, write
from cryer_shell_gradient import DP
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


def main():
    tag="cryer_radial_support_r1"
    target=TESTS/"figures"/(tag+".csv")
    summary=TESTS/"logs"/(tag+".check.json")
    need(not target.exists() and not summary.exists(),"Existing sensitivity data")
    ids=pd.read_csv(NATIVE/"native_ids.csv",float_precision="round_trip").iloc[SOIL]
    x=ids[["x0","y0","z0"]].to_numpy()
    volumes=ids.initial_native_volume_m3.to_numpy()
    native=np.memmap(NATIVE/"common26.bin",offset=12,dtype="<f8",mode="r",shape=(577,1+TOTAL*26))
    peak=native[417,1:].reshape(TOTAL,26)[SOIL]
    need(np.array_equal(x,native[0,1:].reshape(TOTAL,26)[SOIL,:3]),"Owner order")
    radii=np.linalg.norm(x,axis=1)
    shell=np.rint(radii/DP).astype(int)
    # Prescribed analytical M0 field at the actual returned sample time, independent of simulated motion.
    tau=(416-64)*2.**-13
    ref=Reference(.3,finite=False)
    rates=ref.xi**2*(ref.H*ref.kappa)/R**2
    coef=Q*ref.amplitude*np.exp(-rates*tau)
    use=np.abs(coef)>1.e-12
    need(np.sum(np.abs(coef[~use]))<1.e-9,"Analytical series truncation in Pa")
    z=np.outer(radii/R,ref.xi[use])
    sphere=(np.sin(z)-z*np.cos(z))/z**3
    c=ref.beta*np.dot(ref.mean,coef)-ref.H/ref.K*Q
    ur_over_r=((sphere-ref.sx[use]/3)@coef[use]+c/3)/ref.H
    div_ref=((np.sinc(z/np.pi)-ref.sx[use])@coef[use]+c)/ref.H
    amp=1.e-4
    wave=np.pi/DP
    fields=np.stack((amp*x,amp*x*np.cos(wave*radii[:,None]),x*ur_over_r[:,None],peak[:,:3]-x),axis=1)
    truth=np.stack((np.full(len(x),3*amp),amp*(3*np.cos(wave*radii)-wave*radii*np.sin(wave*radii)),div_ref),axis=1)
    tree=cKDTree(x)
    rows=[]
    reports=[]
    for ratio in (1.8,1.5,1.2):
        h=ratio*DP
        measured=np.empty((len(x),4));jac=np.empty(len(x))
        condition=np.empty(len(x));counts=np.empty(len(x),dtype=int)
        for i,pos in enumerate(x):
            other=np.array(sorted(tree.query_ball_point(pos,2*h)))
            other=other[other!=i]
            dx=x[other]-pos
            weight=np.maximum(1-np.linalg.norm(dx,axis=1)/(2*h),0)**3*volumes[other]
            counts[i]=np.count_nonzero(weight)
            weighted=weight[:,None]*dx
            moment=dx.T@weighted
            condition[i]=np.linalg.cond(moment)
            basis=np.linalg.solve(moment,weighted.T)
            grad=np.einsum("njk,ln->jkl",fields[other]-fields[i],basis)
            measured[i]=np.trace(grad,axis1=1,axis2=2)
            jac[i]=np.linalg.det(np.eye(3)+grad[3])-1
        need(max(condition)<100 and np.max(np.abs(measured[:,0]-truth[:,0]))<1e-15,"Moment or affine reproduction")
        groups=[("inner_10",shell<=10),("outer_11_19",(shell>10)&(shell<20)),("surface",shell==20)]
        groups.extend((str(j),shell==j) for j in range(1,21))
        for name,subset in groups:
            row=dict(h_over_dp=ratio,region=name,count=int(sum(subset)),neighbors_min=int(min(counts[subset])),
                     neighbors_max=int(max(counts[subset])),max_condition=float(max(condition[subset])),
                     measured_A_detF_minus_1=float(jac[subset].mean()),
                     saved_A_J_minus_1=float(peak[subset,8].mean()-1))
            for k,label in enumerate(("affine","alternating","M0_smooth")):
                calc=measured[subset,k];value=truth[subset,k]
                row[label+"_projection"]=float(calc@value/(value@value))
                row[label+"_rms_error"]=float(np.sqrt(np.mean((calc-value)**2)))
            rows.append(row)
            if name in ("inner_10","surface","1"):reports.append(row)
    baseline=next(row for row in rows if row["region"]=="inner_10" and row["h_over_dp"]==1.8)
    prior=json.loads((TESTS/"logs/cryer_shell_gradient_r1.check.json").read_text())["summaries"][0]
    need(abs(baseline["alternating_projection"]-prior["alternating_response_projection"])<2e-12,
         "Baseline native stencil differs")
    write(target,rows)
    with summary.open("x",encoding="utf8") as f:
        json.dump(dict(passed=True,soil_count=len(x),actual_finite_Kw_control_part=417,
                       analytical_M0_tau_s=tau,radial_material_layout_unchanged=True,solver_steps=0,
                       geometry="Original 20 shells, dp=.0025 m. Change only the velocity-gradient stencil.",
                       groups=reports),f,indent=2,allow_nan=False)


if __name__=="__main__":main()
