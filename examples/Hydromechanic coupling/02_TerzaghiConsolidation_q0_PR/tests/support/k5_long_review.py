"""Read-only 15-s review: full manifests/half CSV, explicit native sample audit."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import subprocess
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import k5_cell_sequence as cell
from formal_release_sequence import CASE, TESTS, utc
from mdbc_gpu_vector_run import read, bound, verify
sys.path.insert(0, str(CASE/"support"))
from release_case import model, settlement, pressure_theory

TAG = "k5_long5_r1"
CHECK = TESTS/"logs"/(TAG+".review.json")


def main():
    assert not CHECK.exists(), "Preserve the completed review"
    state_path = TESTS/"logs"/(TAG+".status.json")
    queue_path = TESTS/"logs"/(TAG+".queue_attempt.json")
    s, q = read(state_path), read(queue_path)
    assert s["status"] == q["terminal"]["status"] == "pair_passed_pending_review"
    assert s["runs"] == q["terminal"]["runs"] and s["half"] == q["terminal"]["half"]
    assert s["prefixes"] == q["terminal"]["prefixes"] and s["queue_status"] == "queued"
    admission = TESTS/"logs/k5_window_admission_r1.json"
    a = read(admission)
    assert a["family"] == "5" and a["admit_15s"] and not a["admit_2tv"]
    evidence = s["inputs"]+[bound(p) for p in (state_path, queue_path, admission, Path(__file__))]
    source_path = TESTS/"logs/k5_cell8_1s_r1.status.json"
    source = read(source_path)
    verify(source["inputs"])
    evidence += source["inputs"]+[bound(source_path)]
    for r in source["runs"]:
        if r["label"].endswith(("_1c", "_1h")): evidence += r["outputs"]
    for r in s["runs"]:
        assert r["completed"] and r["exit_code"] == 0 and r["owned_process_exited"]
        assert not r.get("stopped_by_monitor", False) and r["frames"] == 15001
        evidence += r["outputs"]
    evidence += [s["half"]["csv"]]
    unique = {p["path"]: p for p in evidence}
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda item: verify([item]), unique.values()))
    print("Verified hashes:", len(unique), flush=True)
    live = subprocess.check_output(["powershell", "-NoProfile", "-Command",
        "@(Get-Process -Name 'DualSPHysics*' -ErrorAction SilentlyContinue).Count"], text=True).strip()
    assert live == "0"
    half = pd.read_csv(s["half"]["csv"]["path"], float_precision="round_trip")
    assert len(half) == 15001 and np.isfinite(half.to_numpy()).all()
    assert abs(half.time_s.to_numpy()-np.arange(15001)*.001).max() < 1e-8
    assert (half.pressure_rms_pa >= 0).all() and (half.top_settlement_difference_mm >= 0).all()
    assert half.pressure_rms_pa.max() == s["half"]["max_pressure_rms_pa"] <= 5
    assert half.top_settlement_difference_mm.max() == s["half"]["max_top_settlement_difference_mm"] <= .005
    # Full worker safety and half trajectories are hash-bound. Independently
    # decode dense early states, all old 1-s prefix states, and 50-ms later states.
    # This is explicitly NOT a second complete 30002-frame native replay.
    peak_index = int(half.pressure_rms_pa.idxmax())
    indices = sorted(set(range(151)) | set(range(0,1001,5)) | set(range(0,15001,50)) |
        {peak_index, int(half.top_settlement_difference_mm.idxmax()), 15000})
    data, histories, summaries, initials = [], [], [], []
    for r, suffix in zip(s["runs"], ("c", "h")):
        folder = TESTS/"outputs"/r["label"]
        files = sorted((folder/"data").glob("Part_*.bi4"),key=lambda p:int(p.stem.split("_")[-1]))
        assert len(files) == 15001
        assert all(f.name == f"Part_{i:04d}.bi4" for i, f in enumerate(files))
        text = (folder/"Run.out").read_text(encoding="utf-8-sig", errors="replace")
        assert "Finished execution (code=0)." in text
        run = pd.read_csv(folder/"Run.csv", sep=";").iloc[0]
        n = round(15/r["dt_s"])
        assert run.Np == 2592 and run.Nfixed == 32 and run.PartsOut == 0
        assert run.Steps == n and run.PartFiles == 15001
        calls = re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", text)
        work = re.search(r"ratecalculations=(\d+) endpoint_rate_reuses=(\d+)", text)
        limits = re.search(r"max\(dt/tau\)=(\S+) spinbound=(\S+)", text)
        assert list(map(int,calls.groups())) == [2*n,n,n,2*n]
        assert list(map(int,work.groups())) == [n+1,n-1]
        assert float(limits[1]) <= .2 and float(limits[2]) < .01
        period = re.search(r"PeriodicXinc=\(([^,]+),", text)
        assert abs(float(period[1])+.025) < 1e-12
        assert "DTs adjusted to DtMin............: 0" in text
        xml = folder/(r["label"]+".xml")
        m = model(xml); evidence.append(bound(xml))
        assert m["k"] == 1e-5 and m["dt"] == r["dt_s"] and m["tmax"] == 15
        frames, rows = {}, []
        first = cell.probe.native(folder, 0); initials.append(first)
        z0 = first.z.to_numpy().reshape(8,320).mean(0)
        for j,i in enumerate(indices):
            b = cell.probe.native(folder, i); frames[i] = b
            row = cell.metrics(b,first)
            assert row["step"] == i*round(.001/r["dt_s"])
            assert abs(row["time_s"]-i*.001) < 1e-8
            t = row["time_s"]; tv = m["cv"]*max(t-m["tD"],0)/m["H"]**2
            row.update(tv=tv, classical_top_mm=settlement(z0[-1],t,m),
                classical_bottom_mm=settlement(z0[0],t,m))
            if t > m["tD"]:
                truth = pressure_theory(z0,tv,m)
                p = b.pressure.to_numpy().reshape(8,320).mean(0)
                row.update(classical_mean_pa=float(truth.mean()), profile_rmse_pa=float(np.sqrt(np.mean((p-truth)**2))))
            else: row.update(classical_mean_pa=np.nan, profile_rmse_pa=np.nan)
            rows.append(row)
            if j % 100 == 0: print("Native samples",suffix,j,"/",len(indices),flush=True)
        assert {k:rows[-1][k] for k in r["final"]} == r["final"]
        reference = TESTS/"outputs"/(s["config"]["reference"]+"_1"+suffix)
        for i in range(201):
            old, new = cell.probe.native(reference,i), frames[5*i]
            assert np.array_equal(old.id,new.id) and old.step.iloc[0] == new.step.iloc[0]
            assert abs(old.time_s.iloc[0]-new.time_s.iloc[0]) < 1e-8
            assert old[cell.FIELDS].to_numpy(dtype="<f8").tobytes() == new[cell.FIELDS].to_numpy(dtype="<f8").tobytes()
        h = pd.DataFrame(rows); csv=TESTS/"figures"/(r["label"]+"_review.csv")
        h.to_csv(csv,index=False,mode="x"); evidence.append(bound(csv))
        post = h[h.stress_guard_applicable]
        final = rows[-1]
        summaries.append(dict(label=r["label"],actual_time_s=final["time_s"],steps=n,frames=15001,
            independently_decoded_samples=len(indices),prefix_samples_native_0_ulp=201,
            loop_seconds=float(run.TSimul),estimated_2tv_days=float(run.TSimul)/15*728.75286/86400,
            final=final,top_theory_error_percent=100*(final["top_settlement_mm"]/final["classical_top_mm"]-1),
            bottom_theory_bias_mm=final["bottom_settlement_mm"]-final["classical_bottom_mm"],
            sampled_post_point1s_max_stress_pa=float(post.max_layer_total_error_pa.max()),
            sampled_post_point1s_max_top_gap_pa=float(post.top_gap_pa.max()),
            sampled_max_equivalent_force_error_N_m=float(abs(post.equivalent_full_width_resultant_N_m+1000).max()),
            hg_max_dt_tau=float(limits[1]),hg_spin_bound=float(limits[2]),hg_rate_calculations=n+1,hg_endpoint_reuses=n-1))
        data.append(frames); histories.append(h)
    for i in indices:
        b,c = data[0][i],data[1][i]; row=half.iloc[i]
        assert np.array_equal(b.id,c.id) and c.step.iloc[0] == 2*b.step.iloc[0]
        p=float(np.sqrt(np.mean((b.pressure-c.pressure)**2)))
        u=abs(float((b.z[initials[0].z>.996]-c.z[initials[1].z>.996]).mean()*1000))
        assert abs(p-row.pressure_rms_pa)<1e-11 and abs(u-row.top_settlement_difference_mm)<1e-12
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    colors=("#256da3","#c47725"); styles=("-","--"); labels=("Coarse: 5 us","Half: 2.5 us")
    fig,axes=plt.subplots(2,3,figsize=(14,8))
    keys=("mean_pressure_pa","top_settlement_mm","bottom_settlement_mm","max_layer_total_error_pa","top_gap_pa","Q_pa")
    ylabs=("Mean pore pressure (Pa)","Top material settlement (mm)","Bottom material settlement (mm)","Max layer total-stress error (Pa)","Top adjacent-layer stress gap (Pa)","Q: RMS second layer difference (Pa)")
    for h,color,style,label in zip(histories,colors,styles,labels):
        for j,(ax,key,ylab) in enumerate(zip(axes.flat,keys,ylabs)):
            sub=h[h.time_s>=.1-1e-7] if j>=3 else h
            ax.plot(sub.time_s,sub[key],color=color,ls=style,label=label)
            ax.set(xlabel="Actual time (s)",ylabel=ylab,xlim=(.1 if j>=3 else 0,15));ax.grid(alpha=.2)
    for ax,key in zip(axes[0],("classical_mean_pa","classical_top_mm","classical_bottom_mm")):
        h=histories[0]; ax.plot(h.time_s,h[key],":",color=".25",label="Classical material reference")
    for ax in axes[1,:2]: ax.axhline(100,color=".25",ls=":");ax.set_ylim(0,105)
    axes[0,0].legend(fontsize=8);axes[0,1].legend(fontsize=8)
    fig.suptitle("k=1e-5, 8 x 320 periodic cell: 15-s pressure / material displacement / stress")
    fig.text(.5,.008,"Curves: 1-ms samples to .15 s, 5-ms to 1 s, then 50-ms; all 15001 native states per run passed worker safety. Not 2Tv.",ha="center",fontsize=9)
    fig.tight_layout(rect=(0,.035,1,.95)); png=TESTS/"figures"/(TAG+"_history.png")
    with png.open("xb") as stream:fig.savefig(stream,dpi=160)
    plt.close(fig);evidence.append(bound(png))
    fig,axes=plt.subplots(2,3,figsize=(14,8))
    z0=initials[0].z.to_numpy().reshape(8,320).mean(0)
    for j,i in enumerate((1000,5000,15000)):
        for frames,color,style,label in zip(data,colors,styles,labels):
            b=frames[i];p=b.pressure.to_numpy().reshape(8,320).mean(0)
            total=(b.sigma_zz-b.pressure).to_numpy().reshape(8,320).mean(0)
            axes[0,j].plot(p/10000,z0,color=color,ls=style,label=label)
            axes[1,j].plot(total+10000,z0,color=color,ls=style)
        t=float(data[0][i].time_s.iloc[0]);tv=m["cv"]*(t-m["tD"])/m["H"]**2
        axes[0,j].plot(pressure_theory(z0,tv,m)/10000,z0,":",color=".25",label="Classical reference")
        axes[0,j].set(xlabel="Pore pressure / q0",ylabel="Initial material height z0/H",title=f"Actual t={t:.6g} s; Tv={tv:.5g}",xlim=(0,1.05),ylim=(0,1))
        axes[1,j].set(xlabel="Layer total stress + q0 (Pa)",ylabel="Initial material height z0/H",xlim=(-105,105),ylim=(0,1))
        for ax in axes[:,j]:ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=8);fig.suptitle("Native material-layer profiles; common axes, not a full-cycle validation")
    fig.text(.5,.008,"Classical ideal load / incompressible-water small-strain reference; numerical Kw=2e8 Pa, .01-s ramp and moving particles.",ha="center",fontsize=9)
    fig.tight_layout(rect=(0,.035,1,.95));png=TESTS/"figures"/(TAG+"_profiles.png")
    with png.open("xb") as stream:fig.savefig(stream,dpi=160)
    plt.close(fig);evidence.append(bound(png))
    fig,axes=plt.subplots(1,3,figsize=(14,4.5))
    axes[0].plot(half.time_s,half.pressure_rms_pa,color=colors[0]);axes[0].axhline(5,ls=":",color=".25")
    axes[0].set(xlabel="Actual time (s)",ylabel="Coarse/half pressure RMS difference (Pa)",ylim=(0,5.2))
    axes[1].plot(half.time_s,half.top_settlement_difference_mm,color=colors[0]);axes[1].axhline(.005,ls=":",color=".25")
    axes[1].set(xlabel="Actual time (s)",ylabel="Top material settlement difference (mm)",ylim=(0,.0052))
    axes[2].plot(half.time_s,half.pressure_rms_pa,color=colors[0],marker="o",ms=3);axes[2].axhline(5,ls=":",color=".25")
    axes[2].set(xlabel="Actual time (s); initial transient zoom",ylabel="Pressure RMS difference (Pa)",xlim=(0,.03),ylim=(0,5.2))
    for ax in axes:ax.grid(alpha=.2)
    fig.suptitle("Original dense half-step limits: all 15001 sample pairs")
    fig.tight_layout(rect=(0,0,1,.92));png=TESTS/"figures"/(TAG+"_half.png")
    with png.open("xb") as stream:fig.savefig(stream,dpi=160)
    plt.close(fig);evidence.append(bound(png))
    result=dict(audit_passed=True,reviewed_utc=utc(),verified_recorded_hashes=len(unique),no_solver_processes_observed=True,
        full_hash_bound_worker_safety_samples_per_run=15001,independent_native_indices=indices,
        independent_native_audit_scope="Explicit samples and both full 201-sample prefixes, NOT a second full native safety replay",
        half_samples=15001,max_pressure_rms_pa=float(half.pressure_rms_pa.max()),peak_pressure_time_s=float(half.iloc[peak_index].time_s),
        max_top_settlement_difference_mm=float(half.top_settlement_difference_mm.max()),runs=summaries,
        full_cycle_admitted=False,formal_inputs_changed=False,production_modified=False,
        limitations=["15 s reaches only Tv about .041; late Tv>1 dissipation remains untested for k1e-5.",
            "Uniform periodic cell excludes longer horizontal modes; no general sliding/complex-wall proof.",
            "Finite Kw/load ramp/moving particles differ from classical ideal theory; same-dt prefix is not exact HG restart.",
            "Whole-cycle half-step, plasticity and large rotation remain unvalidated."],evidence=evidence)
    with CHECK.open("x",encoding="utf8") as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps({k:v for k,v in result.items() if k not in ("evidence","independent_native_indices")},indent=2),flush=True)


if __name__ == "__main__": main()
