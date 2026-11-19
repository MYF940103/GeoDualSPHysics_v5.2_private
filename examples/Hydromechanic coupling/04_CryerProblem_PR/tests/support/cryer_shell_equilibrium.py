"""Radial small-strain equilibrium on retained native Cryer states; no solver calls."""
from pathlib import Path
import csv
import json
import os
import struct
import sys

for thread_variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[thread_variable] = "1"

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from cryer_p3_verify_r1 import snapshot, need, T_D, TOTAL, SOIL

TESTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TESTS.parent / "support"))
from plot_cryer_formal_four_nu_r1 import Reference, Q, R
TAG = "cryer_shell_equilibrium_r1"
NATIVE = TESTS / "outputs/upl_cryer_freebody_peak_GPU_r1_native"
DRAIN = TESTS / "outputs/cryer_p3_gpu_drain4097_r1/data"


def sphere_weights(radii):
    """Exact r? integration of the piecewise-linear shell means, constant inside first radius."""
    weights = np.zeros_like(radii)
    weights[0] = (radii[0] / R)**3
    for i, (lo, hi) in enumerate(zip(radii[:-1], radii[1:])):
        vol = (hi**3 - lo**3)/R**3
        moment = 0.75 * (hi**4 - lo**4)/R**3
        right = (moment - lo*vol)/(hi - lo)
        weights[i] += vol-right
        weights[i+1] += right
    need(abs(sum(weights)-1)<1e-12 and np.min(weights)>0, "radial quadrature")
    return weights


def reduced(values, bins, volumes, shell_volumes):
    return np.bincount(bins, weights=values*volumes, minlength=len(shell_volumes))/shell_volumes


def reference_fields(ref, tau, radii):
    if tau==0:
        p = np.full(len(radii), Q*ref.B)
        average = Q*ref.B
    else:
        decay = Q * ref.amplitude * np.exp(-ref.decay*tau)
        p = (np.sinc(np.outer(radii/R, ref.xi)/np.pi)-ref.sx) @ decay
        average = ref.mean @ decay
    c = ref.beta*average-ref.H/ref.K*Q
    return p, average, c


def observe(method, part, t, p, kk, fs, bins, V0, sv, counts, r, geometric_w, ref):
    need(np.all(np.isfinite(kk)) and np.all(np.isfinite(p)), "nonfinite native stress or p")
    dtau = t-T_D
    theory_p, theory_mean, theory_C = reference_fields(ref, dtau, r)
    p_shell = reduced(p,bins,V0,sv)
    eff = reduced(kk.mean(axis=1),bins,V0,sv)  # tension-positive diagonal of effective stress
    c = ref.H/ref.K*eff-p_shell
    dp = p_shell-theory_p
    dc = c-theory_C
    strain_term = ref.H/ref.K*eff-(theory_p+theory_C)
    need(np.max(abs(dp-strain_term+dc))<1e-9, "stress/pressure decomposition")
    need(np.array_equal(np.isin(fs,(2,3)),bins==len(r)-1),"FS membership differs from outer reference shell")
    if dtau>0:
        need(np.all(p[np.isin(fs,(2,3))]==0), "open boundary pressure")
    pbar = geometric_w @ p_shell
    # Remove the known quadrature error of these same theory samples before comparing.
    # The corrected pressure difference is a discrete, geometry-weighted diagnostic.
    dmean = geometric_w @ dp
    qerr = ref.K/ref.H*(ref.beta*dmean-dc[0])
    data = dict(method=method,part=part,time_s=t,tau_s=dtau,tv=dtau*ref.legacy_cv/R**2,
                center_p_Pa=p_shell[0],center_dp_Pa=dp[0],center_dC_Pa=dc[0],
                center_dvolumetric_stress_term_Pa=strain_term[0],C_reference_Pa=theory_C,
                center_total_compression_Pa=p_shell[0]-eff[0],center_total_error_Pa=dp[0]-strain_term[0]*ref.K/ref.H,
                center_effective_mean_tensile_Pa=eff[0],surface_effective_mean_tensile_Pa=eff[-1],
                native_volume_mean_dp_Pa=np.average(dp,weights=sv),geometry_mean_dp_Pa=dmean,
                true_reference_mean_p_Pa=theory_mean,geometry_mean_p_Pa=pbar,
                theory_geometry_quadrature_error_Pa=geometric_w@theory_p-theory_mean,
                geometry_q_equivalent_minus_q_Pa=qerr,
                shell_C_span_Pa=np.ptp(c),inner_to_surface_C_difference_Pa=c[-1]-c[0])
    shells=[dict(method=method,part=part,tau_s=dtau,r0_over_a=x/R,count=int(counts[i]),
                 p_Pa=p_shell[i],p_reference_Pa=theory_p[i],C_Pa=c[i],C_reference_Pa=theory_C,
                 dp_Pa=dp[i],dC_Pa=dc[i],dH_eps_v_Pa=strain_term[i]) for i,x in enumerate(r)]
    return data,shells


def write(path,rows):
    with path.open("x",newline="",encoding="utf8") as out:
        writer=csv.DictWriter(out,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)


def plot(A, profiles, path):
    fig,axes=plt.subplots(1,2,figsize=(11,4.4),layout="constrained")
    series=(("center_dp_Pa","dp_Pa","Pressure error"),
            ("center_dvolumetric_stress_term_Pa","dH_eps_v_Pa","Volumetric stress term"),
            ("center_dC_Pa","dC_Pa","Equilibrium constant error"))
    shell=pd.DataFrame(profiles).query("method=='A_finiteKw' and part==417")
    for col,radial,label in series:
        axes[0].plot(A.tau_s*1000,A[col],label=label)
        axes[1].plot(shell.r0_over_a,shell[radial],".-",label=label)
    axes[0].set(xlabel="Time after drainage opening (ms)",ylabel="Difference from finite-Kw reference (Pa)",title="Fixed 18 center particles, Mandel window")
    axes[1].set(xlabel="Initial material radius / sphere radius",ylabel="Difference from finite-Kw reference (Pa)",title="20 material shells at sampled center peak")
    for ax in axes:
        ax.axhline(0,color="0.5",lw=.8);ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.savefig(path,dpi=180);plt.close(fig)


def main():
    figdir = TESTS/"figures"
    outputs = [figdir/(TAG+suffix) for suffix in ("_history.csv","_profiles.csv",".png")]
    receipt = TESTS/"logs"/(TAG+".check.json")
    need(not any(x.exists() for x in outputs+[receipt]), "preserve previous review")
    meta = json.loads((NATIVE/"completion.json").read_text())
    need(meta["passed"] and meta["samples"]==577 and meta["total_native_ids"]==TOTAL,"sealed native baseline")
    ids = pd.read_csv(NATIVE/"native_ids.csv",float_precision="round_trip")
    need(np.array_equal(ids.id,np.arange(TOTAL)),"unmatched native ids")
    ids=ids.iloc[SOIL]
    V0=ids.initial_native_volume_m3.to_numpy()
    r=np.arange(1,21)*.0025
    bins=np.rint(ids.r0_m.to_numpy()/.0025).astype(int)-1
    need(np.max(abs(r[bins]-ids.r0_m))<1e-12 and np.array_equal(bins==0,ids.center18==1),"shells and center18")
    counts=np.bincount(bins,minlength=20)
    sv=np.bincount(bins,weights=V0,minlength=20)
    weights=sphere_weights(r)
    cols=pd.read_csv(NATIVE/"columns.csv")
    lookup=dict(zip(cols.name,cols.column))
    fn=NATIVE/"common26.bin"
    with fn.open("rb") as f: need(struct.unpack("<III",f.read(12))==(TOTAL,26,577),"record shape")
    need(fn.stat().st_size==12+577*(8+TOTAL*26*8),"record size")
    native=np.memmap(fn,mode="r",offset=12,dtype="<f8",shape=(577,1+TOTAL*26))
    ticks=pd.read_csv(NATIVE/"summary.csv",float_precision="round_trip")
    need(np.array_equal(native[:,0],ticks.time_s) and ticks.part.to_list()==list(range(577)),"actual native clocks")
    a=Reference(.3)
    records=[]; profiles=[]
    for part in range(64,577):
        payload=native[part,1:].reshape(TOTAL,26)[SOIL]
        row,ps=observe("A_finiteKw",part,ticks.time_s[part],payload[:,lookup["PorePress"]],
                      payload[:,[lookup[k] for k in ("sigma_xx","sigma_yy","sigma_zz")]],
                      payload[:,lookup["FSType"]],bins,V0,sv,counts,r,weights,a)
        need(abs(row["center_p_Pa"]-ticks.center_pressure_Pa[part])<1e-8,"center reduction")
        if part in (64,65,408,417,576):profiles.extend(ps)
        records.append(row)
    b=Reference(.3,finite=False)
    b.cv=b.H*b.kappa;b.decay=b.xi**2*b.cv/R**2
    for part,step in ((64,4096),(65,4097)):
        state,_ = snapshot(DRAIN/f"Part_{part:04d}.bi4",part,step,2**-19)
        row,ps=observe("P3_M0",part,step*2**-19,state["PorePress"][SOIL],state["SigmaState_kk"][SOIL],
                      state["FSType"][SOIL],bins,V0,sv,counts,r,weights,b)
        records.append(row);profiles.extend(ps)
    df=pd.DataFrame(records); A=df[(df.method=="A_finiteKw") & (df.tv>=.005)]
    peak=A.loc[A.center_p_Pa.idxmax()]
    need(peak.part==417,"changed peak selection")
    write(outputs[0],records);write(outputs[1],profiles)
    plot(A,profiles,outputs[2])
    result=dict(source="upl_cryer_freebody_peak_GPU_r1_native",p3_local="cryer_p3_gpu_drain4097_r1",native_shell_counts=counts.tolist(),
                source_window_A=[64,576],source_frames_P3=[64,65],peak=peak.to_dict(),preopen=records[0],P3=records[-2:],
                benchmark_decision="No physical gate changed; returned P3 peak/full trajectories required for TPI accuracy.")
    with receipt.open("x",encoding="utf8") as f: json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(result["peak"],indent=2))


if __name__=="__main__":
    main()
