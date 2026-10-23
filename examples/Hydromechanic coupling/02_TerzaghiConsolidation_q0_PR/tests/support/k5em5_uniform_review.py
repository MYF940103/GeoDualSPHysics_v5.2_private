"""Native same-grid causal review and static figures; no solver or release edits."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from formal_release_sequence import CASE, TESTS, REPO, save, utc
from mdbc_gpu_vector_run import read, bound
import k5_guard_probe as probe
sys.path.insert(0, str(CASE/"support"))
import release_case as reference
from compare_precision_q0 import pressure_theory

COLORS = ["#2168a6", "#d87832"]


def layer(a):
    b = a.copy()
    b["layer"] = (b.id-40)%100
    b["z0"] = (b.layer+.5)*.01
    b["total_error"] = b.sigma_zz-b.pressure+10000
    b["rho_stress_invariant"] = np.log(b.rho/2100)+(b.sigma_xx+b.sigma_yy+b.sigma_zz)/(3*(2e6/(3*(1-2*.3))))
    return b.groupby("layer").mean(numeric_only=True)


def finish(fig, path, foot):
    fig.text(.09, .025, foot, fontsize=9)
    fig.tight_layout(rect=(0, .06, 1, .95))
    with path.open("xb") as stream:
        fig.savefig(stream, dpi=180)
    plt.close(fig)


def operators():
    tag = "k5em5_uniform_operator_r1"
    check = TESTS/"logs"/(tag+".check.json")
    assert not check.exists()
    sources = [("k=1e-4", CASE/"CaseTerzaghiConsolidation_q0_PR_full_k1em4_release_GPU_out", 10),
               ("k=5e-5", TESTS/"outputs/k5em5_gpu_r2_c", 100)]
    fig, axes = plt.subplots(2, 2, figsize=(11, 9))
    records, evidence, measurements = [], [Path(__file__)], []
    for color, (name, folder, part) in zip(COLORS, sources):
        a = probe.native(folder, part)
        b = layer(a)
        generated = next(p for p in folder.glob("*.xml") if reference.ET.parse(p).find("./execution/particles") is not None)
        model = reference.model(generated)
        tv = model["cv"]*(float(a.time_s.iloc[0])-.01)
        p = pressure_theory(b.z0.to_numpy(), tv, model)
        axes[0,0].plot(b.pressure/10000, b.z0, color=color, label=name)
        axes[0,0].plot(p/10000, b.z0, color=color, ls="--", lw=1)
        axes[0,1].plot(b.total_error, b.z0, color=color, label=name)
        axes[1,0].plot(1000*b.rho_stress_invariant, b.z0, color=color, label=name)
        b["series"] = name
        records.append(b)
        evidence += [folder/"data"/f"Part_{part:04d}.bi4", generated]
        measurements.append(dict(series=name, time_s=float(a.time_s.iloc[0]), top_gap_pa=float(abs(b.total_error.iloc[-1]-b.total_error.iloc[-2])),
                                 top_rho_stress_invariant=float(b.rho_stress_invariant.iloc[-1])))
    x,z = np.meshgrid((np.arange(10)+.5)*.01, (np.arange(100)+.5)*.01)
    x,z = x.ravel(),z.ravel()
    rows=[]
    for level in range(90,100):
        i=level*10+5
        dr=np.stack(((x[i]-x+.05)%.1-.05,z[i]-z),axis=1)
        rr=(dr*dr).sum(1)
        use=(rr>1e-20)&(rr<=(2*.018)**2)
        g=dr*(-2.7852/.018**4*np.maximum(0,1-np.sqrt(rr)/(2*.018))**3*use)[:,None]
        moment=-np.einsum("ai,aj->ij",dr,g)*.01**2
        corr=g@np.linalg.inv(moment).T
        pressure=10000*(.995-z)
        lap=2*np.sum(.01**2*(pressure[i]-pressure)*(dr*corr).sum(1)/(rr+(.1*.018)**2))
        rows.append(dict(layer=level,z0_m=z[i],raw_linear_compression_response=moment[1,1],corrected_response=1.,linear_pressure_laplacian_pa_m2=lap,
                         drained_node_not_evolved=level==99))
    operator=pd.DataFrame(rows)
    v=operator[~operator.drained_node_not_evolved]
    axes[1,1].plot(v.linear_pressure_laplacian_pa_m2/1000,v.z0_m,color=COLORS[0],marker="o",ms=3)
    axes[1,1].axvline(0,color=".2",ls="--",lw=1,label="Exact linear Laplacian = 0")
    for ax in axes.flat:
        ax.set_ylim(.90,1)
        ax.set_ylabel("Initial material z0 (m)")
        ax.grid(alpha=.2)
    axes[0,0].set(title="Pressure at actual t=0.1 s; solid numeric / dashed ideal",xlabel="Pore pressure / q0",xlim=(0,1))
    axes[0,0].legend(fontsize=9)
    axes[0,1].axvline(0,color=".2",ls="--",lw=1)
    axes[0,1].set(title="Cauchy total-stress residual; not HG-augmented stress",xlabel="sigma_zz - p + q0 (Pa)",xlim=(-110,110))
    axes[1,0].axvline(0,color=".2",ls="--",lw=1)
    axes[1,0].set(title="Elastic stress / density integration consistency",xlabel="1000 * [ln(rho/rho0) + tr(sigma)/(3K)]")
    axes[1,1].set(title="Manufactured linear-pressure stencil (not a solution)",xlabel="Computed Laplacian (kPa/m2)")
    axes[1,1].legend(fontsize=8)
    fig.suptitle("Same dp=0.01 m: near-drainage evidence and independent stencil checks",fontsize=13)
    png=TESTS/"figures"/(tag+".png")
    finish(fig,png,"Ideal pressure omits the ramp. Stencil reconstruction uses double arithmetic, not a bitwise solver replay. Neither defect alone proves causation.")
    profile=TESTS/"figures"/(tag+"_profiles.csv")
    stencil=TESTS/"figures"/(tag+"_stencil.csv")
    pd.concat(records).to_csv(profile,index=False,mode="x")
    operator.to_csv(stencil,index=False,mode="x")
    save(check,dict(analysis_complete=True,utc=utc(),physical_acceptance=False,measurements=measurements,
                    manufactured_top_raw_compression_response=rows[-1]["raw_linear_compression_response"],
                    manufactured_last_evolved_layer_linear_laplacian=rows[-2]["linear_pressure_laplacian_pa_m2"],
                    limits=["Nodal pressure boundary lies at the top particle, z=.995, whereas theory uses H=1.",
                            "The invariant also includes density writeback/time-integration error; its nonzero value does not isolate spatial error."],
                    evidence=[bound(p) for p in evidence+[png,profile,stencil,REPO/"src/source/JSphCpu.cpp",REPO/"src/source/FunSphKernel.h"]]))
    print(png)


def pairs():
    tag="k5em5_uniform_pairs_r1"
    check=TESTS/"logs"/(tag+".check.json")
    assert not check.exists()
    gpu=read(TESTS/"logs/k5em5_uniform_dt_r1.status.json")
    cpu=read(TESTS/"logs/k5em5_rhocorr_r1.status.json")
    assert gpu["status"]=="completed_diagnostic_not_full_admission" and cpu["status"]=="completed_pending_causal_review"
    def compare(i):
        a,b,c,d=[probe.native(TESTS/"outputs"/name,i) for name in ("k5em5_uniform_dt_r1_c","k5em5_uniform_dt_r1_h","k5em5_rhocorr_r1_off","k5em5_rhocorr_r1_on")]
        assert np.array_equal(a.id,b.id) and np.array_equal(a.id,c.id) and np.array_equal(a.id,d.id)
        top=a.id.mod(100).eq(39)
        return dict(time_s=float(a.time_s.iloc[0]), half_pressure_rms_pa=float(np.sqrt(np.mean((a.pressure-b.pressure)**2))),
                    half_top_difference_mm=abs(float((a.z[top]-b.z[top]).mean())*1000),
                    cpu_gpu_pressure_rms_pa=float(np.sqrt(np.mean((a.pressure-c.pressure)**2))),
                    on_off_pressure_rms_pa=float(np.sqrt(np.mean((c.pressure-d.pressure)**2))))
    with ThreadPoolExecutor(max_workers=4) as pool:
        data=pd.DataFrame(pool.map(compare,range(301)))
    csvpath=TESTS/"figures"/(tag+".csv")
    data.to_csv(csvpath,index=False,mode="x")
    fig,axes=plt.subplots(2,2,figsize=(11,9))
    rows=[]
    for suffix,color,name in (("off",COLORS[0],"Original continuity"),("on",COLORS[1],"Matched spatial divergence")):
        label="k5em5_rhocorr_r1_"+suffix
        history=pd.read_csv(TESTS/"figures"/(label+"_runtime.csv"))
        h=history[history.time_s>=.1-1e-7]
        axes[0,0].plot(h.time_s,h.top_gap_pa,color=color,label=name)
        a=probe.native(TESTS/"outputs"/label,100)
        b=layer(a)
        axes[0,1].plot(b.total_error,b.z0,color=color,label=name)
        axes[1,0].plot(1000*b.rho_stress_invariant,b.z0,color=color)
        axes[1,1].plot(b.pressure/10000,b.z0,color=color)
        rows.append(dict(variant=suffix,post_point1_max_layer_error_pa=float(h.max_layer_total_error_pa.max()),
                         post_point1_max_top_gap_pa=float(h.top_gap_pa.max()),top_invariant_at_point1=float(b.rho_stress_invariant.iloc[-1]),
                         final_top_settlement_mm=float(history.top_settlement_mm.iloc[-1])))
    axes[0,0].axhline(100,color=".2",ls="--",lw=1)
    axes[0,0].set(title="Original safety window, t >= 0.1 s",xlabel="Actual time (s)",ylabel="Top adjacent-layer gap (Pa)")
    axes[0,0].legend(fontsize=9)
    for ax in list(axes.flat)[1:]:
        ax.set_ylim(.90,1)
        ax.set_ylabel("Initial material z0 (m)")
    axes[0,1].axvline(0,color=".2",ls="--",lw=1)
    axes[0,1].set(title="Total-stress residual at t=0.1 s",xlabel="sigma_zz - p + q0 (Pa)")
    axes[1,0].axvline(0,color=".2",ls="--",lw=1)
    axes[1,0].set(title="Stress/density invariant at t=0.1 s",xlabel="1000 * [ln(rho/rho0) + tr(sigma)/(3K)]")
    axes[1,1].set(title="Numerical pore pressure at t=0.1 s",xlabel="Pore pressure / q0")
    for ax in axes.flat:
        ax.grid(alpha=.2)
    fig.suptitle("Isolated CPU spatial-divergence test: dp=0.01 m, k=5e-5, same loading/HG/dt",fontsize=13)
    png=TESTS/"figures"/(tag+".png")
    finish(fig,png,"Only continuity changed in an isolated object. No pressure/density double patch, Darcy change, physical acceptance or full-cycle admission.")
    r=dict(analysis_complete=True,utc=utc(),physical_acceptance=False,full_admitted=False,variants=rows,
           all_301_sample_half_max_pressure_rms_pa=float(data.half_pressure_rms_pa.max()),
           all_301_sample_half_max_top_difference_mm=float(data.half_top_difference_mm.max()),
           cpu_gpu_control_pressure_rms_max_pa=float(data.cpu_gpu_pressure_rms_pa.max()),
           on_off_is_not_half_step=True,evidence=[bound(p) for p in (Path(__file__),csvpath,png)])
    save(check,r)
    print(json.dumps({k:v for k,v in r.items() if k!="evidence"},indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pairs",action="store_true")
    args=p.parse_args()
    pairs() if args.pairs else operators()
