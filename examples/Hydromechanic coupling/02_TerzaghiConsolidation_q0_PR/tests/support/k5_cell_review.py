"""Offline native audit/figures for the periodic-cell short diagnostic."""
import json
from pathlib import Path
import re
import subprocess
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import k5_guard_probe as probe
import k5_cell_sequence as cell
from formal_release_sequence import TESTS, utc
from mdbc_gpu_vector_run import read, bound, verify


def difference(a, b, ai, bi, periodic):
    assert abs(a.time_s.iloc[0]-b.time_s.iloc[0]) < 1e-8
    if periodic:
        assert a.step.iloc[0] == b.step.iloc[0] and len(a) == 4*len(b)
        assert abs(ai.z.to_numpy()-np.tile(bi.z.to_numpy(), 4)).max() < 1e-14
        shifted = np.tile(bi.x.to_numpy(), 4)+np.repeat(np.arange(4)*cell.WIDTH, cell.NX*cell.NZ)
        assert abs(ai.x.to_numpy()-shifted).max() < 1e-14
        p = a.pressure.to_numpy()-np.tile(b.pressure.to_numpy(), 4)
        s = (a.sigma_zz-a.pressure).to_numpy()-np.tile((b.sigma_zz-b.pressure).to_numpy(), 4)
    else:
        assert np.array_equal(a.id, b.id) and b.step.iloc[0] == 2*a.step.iloc[0]
        p = (a.pressure-b.pressure).to_numpy()
        s = ((a.sigma_zz-a.pressure)-(b.sigma_zz-b.pressure)).to_numpy()
    u = abs(float((ai.z-a.z)[ai.z > .996].mean()-(bi.z-b.z)[bi.z > .996].mean())*1000)
    m = dict(time_s=float(a.time_s.iloc[0]), pressure_rms_pa=float(np.sqrt(np.mean(p*p))),
        top_settlement_difference_mm=u, max_total_stress_difference_pa=float(abs(s).max()))
    assert m["pressure_rms_pa"] <= 5 and u <= .005
    if periodic: assert m["max_total_stress_difference_pa"] <= 5
    return m


def main():
    check = TESTS/"logs/k5_cell_review_r1.check.json"
    assert not check.exists()
    status = TESTS/"logs"/(cell.TAG+".status.json")
    queue = TESTS/"logs"/(cell.TAG+".queue_attempt.json")
    state = read(status)
    assert state["status"] == read(queue)["terminal"]["status"] == "cell8_1s_pairs_passed_pending_review"
    assert state["queue_status"] == "queued" and len(state["runs"]) == 4
    old_path = TESTS/"logs/k5_grid320_review_r1.check.json"
    old = read(old_path); assert old["audit_passed"]
    evidence = state["inputs"]+old["evidence"]+[bound(p) for p in (Path(__file__), status, queue)]
    for item in state["runs"]:
        assert item["completed"] and item["owned_process_exited"] and item["exit_code"] == 0
        assert not item.get("stopped_by_monitor", False)
        evidence += item["outputs"]
    unique = {p["path"]: p for p in evidence}; verify(unique.values())
    print("Verified recorded hashes:", len(unique), flush=True)
    count = subprocess.check_output(["powershell", "-NoProfile", "-Command", "@(Get-Process -Name 'DualSPHysics*' -ErrorAction SilentlyContinue).Count"], text=True).strip()
    assert count == "0", "An unreviewed solver is still running"
    data, initial, histories, prefixes, summaries = {}, {}, {}, {}, []
    for item in state["runs"]:
        suffix = item["label"].removeprefix(cell.TAG+"_")
        folder = TESTS/"outputs"/item["label"]
        files = sorted((folder/"data").glob("Part_*.bi4"))
        assert len(files) == item["frames"]
        first = probe.native(folder, 0); initial[suffix] = first
        rows, frames, prefix = [], [], []
        for i in range(len(files)):
            a = probe.native(folder, i); m = cell.metrics(a, first)
            assert m["step"] == i*round(.005/item["dt_s"])
            rows.append(m); frames.append(a)
            if i <= 30: prefix.append(a[cell.FIELDS].to_numpy(dtype="<f8").tobytes())
        assert rows[-1] == item["final"]
        assert abs(rows[-1]["time_s"]-item["duration_s"]) < 1e-7
        n = round(item["duration_s"]/item["dt_s"])
        assert rows[-1]["step"] == n
        text = (folder/"Run.out").read_text(encoding="utf-8-sig", errors="replace")
        assert "Finished execution (code=0)." in text
        calls = re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)", text)
        limits = re.search(r"max\(dt/tau\)=(\S+) spinbound=(\S+)", text)
        assert list(map(int, calls.groups())) == [2*n, n, n, 2*n]
        assert float(limits[1]) <= .2 and float(limits[2]) < .01
        run = pd.read_csv(folder/"Run.csv", sep=";").iloc[0]
        assert run.Np == 2592 and run.Nfixed == 32 and run.PartsOut == 0 and run.Steps == n
        h = pd.DataFrame(rows); csv = TESTS/"figures"/(item["label"]+"_review.csv")
        h.to_csv(csv, index=False, mode="x"); evidence.append(bound(csv))
        post = h[h.stress_guard_applicable]
        summaries.append(dict(label=item["label"], final=rows[-1], samples=len(rows), loop_seconds=float(run.TSimul),
            post_point1s_max_stress_pa=float(post.max_layer_total_error_pa.max()), post_point1s_max_top_gap_pa=float(post.top_gap_pa.max()),
            max_equivalent_force_error_N_m=float(abs(post.equivalent_full_width_resultant_N_m+1000).max()),
            hg_max_dt_tau=float(limits[1]), hg_spin_bound=float(limits[2])))
        data[suffix], histories[suffix], prefixes[suffix] = frames, h, prefix
        print("Reviewed native", suffix, len(rows), flush=True)
    assert prefixes["015c"] == prefixes["1c"] and prefixes["015h"] == prefixes["1h"]
    comparisons, curves, full_profiles = [], {}, {}
    for suffix in ("1c", "1h"):
        folder = TESTS/"outputs"/(cell.FULL+"_"+suffix); fi = probe.native(folder, 0)
        rows = []; snapshots = {}
        for i, b in enumerate(data[suffix]):
            a = probe.native(folder, i)
            rows.append(difference(a, b, fi, initial[suffix], True))
            if i in (30, 200): snapshots[i] = (fi, a)
        curves[suffix] = pd.DataFrame(rows); full_profiles[suffix] = snapshots
    curves["half"] = pd.DataFrame([difference(a, b, initial["1c"], initial["1h"], False) for a,b in zip(data["1c"], data["1h"])])
    for kind, suffix, c in (("periodic", "1c", "1c"), ("periodic", "1h", "1h"), ("half", "1c", "half")):
        for length, samples in (("015", 31), ("1", 201)):
            h = curves[c].iloc[:samples]
            keys = ["pressure_rms_pa", "top_settlement_difference_mm", "max_total_stress_difference_pa"]
            peaks = {key: float(h[key].max()) for key in keys}
            left = (cell.FULL if kind == "periodic" else cell.TAG)+"_"+length+suffix[-1]
            receipt = next(r for r in state["comparisons"] if r["kind"] == kind and r["left"] == left)
            for key in keys: assert np.isclose(peaks[key], receipt[key], rtol=1e-12, atol=1e-12), key
            comparisons.append(dict(kind=kind, suffix=length+suffix[-1], samples=samples, **peaks))
        csv = TESTS/"figures"/("k5_cell_review_r1_"+c+".csv")
        curves[c].to_csv(csv, index=False, mode="x"); evidence.append(bound(csv))
    timing = []
    for suffix in ("1c", "1h"):
        full = next(r for r in old["runs"] if r["label"] == cell.FULL+"_"+suffix)["loop_seconds"]
        small = next(r for r in summaries if r["label"] == cell.TAG+"_"+suffix)["loop_seconds"]
        timing.append(dict(suffix=suffix, full_seconds=full, cell_seconds=small, observed_speedup=full/small,
            observed_reduction_percent=100*(1-small/full), estimated_cell_2tv_days=small*728.75286/86400))
    plt.rcParams.update({"font.size":10, "axes.spines.top":False, "axes.spines.right":False})
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for ax, key, title in zip(axes.flat, ("pressure_rms_pa", "top_settlement_difference_mm", "max_total_stress_difference_pa"),
        ("Periodic-field pressure RMS difference (Pa)", "Top material settlement difference (mm)", "Max pointwise total-stress difference (Pa)")):
        for suffix, color, style, label in (("1c", "#256da3", "-", "dt=5 microseconds"), ("1h", "#c47725", "--", "dt=2.5 microseconds")):
            ax.plot(curves[suffix].time_s, curves[suffix][key], color=color, ls=style, lw=1.5, label=label)
        ax.set(xlabel="Actual physical time (s)", ylabel=title, xlim=(0, 1)); ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=9)
    for suffix, color, style, label in (("1c", "#256da3", "-", "Cell coarse"), ("1h", "#c47725", "--", "Cell half")):
        h = histories[suffix]; p = h[h.stress_guard_applicable]
        axes[1, 0].plot(p.time_s, p.max_layer_total_error_pa, color=color, ls=style, label=label)
        axes[1, 1].plot(h.time_s, h.Q_pa, color=color, ls=style, label=label)
    axes[1, 0].axhline(100, color=".25", ls=":"); axes[1, 0].set(xlabel="Actual time (s); guard from 0.1 s", ylabel="Max layer total-stress error (Pa)", xlim=(.1, 1), ylim=(0,105))
    axes[1, 1].set(xlabel="Actual physical time (s)", ylabel="Q: RMS second layer difference (Pa)", xlim=(0,1)); axes[1, 1].legend(fontsize=9)
    x = np.arange(2)
    axes[1, 2].bar(x-.17, [r["full_seconds"]/60 for r in timing], .34, color="#555555", label="32-column full width")
    axes[1, 2].bar(x+.17, [r["cell_seconds"]/60 for r in timing], .34, color="#256da3", label="8-column cell")
    axes[1, 2].set(xticks=x, xticklabels=["Coarse", "Half"], ylabel="Observed 1-s GPU main-loop time (min)", ylim=(0,95)); axes[1, 2].legend(fontsize=8)
    for i,r in enumerate(timing): axes[1, 2].text(i, max(r["full_seconds"],r["cell_seconds"])/60+2, f'{r["observed_speedup"]:.3f}x', ha="center")
    for ax in axes[1, :2]: ax.grid(alpha=.2)
    fig.suptitle("k=1e-5, dp=1/320 m: 8-column periodic cell versus retained 32-column fields")
    fig.text(.5,.008,"Top-row difference scales are zoomed; maxima remain below 5 Pa / .005 mm / 5 Pa. Timing is not an interleaved repeated benchmark.",ha="center",fontsize=9)
    fig.tight_layout(rect=(0,.03,1,.95)); history_png = TESTS/"figures/k5_cell_review_r1_history.png"
    with history_png.open("xb") as stream: fig.savefig(stream,dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(2,2,figsize=(11,8))
    for row,index in enumerate((30,200)):
        fi,a = full_profiles["1c"][index]; b=data["1c"][index]
        for frame,zinitial,nx,color,style,label in ((a,fi,32,"#555555","-","32-column full width"),(b,initial["1c"],8,"#256da3","--","8-column cell")):
            z = zinitial.z.to_numpy().reshape(nx,320).mean(0)
            axes[row,0].plot(frame.pressure.to_numpy().reshape(nx,320).mean(0)/10000,z,color=color,ls=style,label=label)
            axes[row,1].plot((frame.sigma_zz-frame.pressure).to_numpy().reshape(nx,320).mean(0)+10000,z,color=color,ls=style)
        for col in range(2): axes[row,col].set(ylim=(.85,1),ylabel="Initial material height z0/H",title=f"Actual t={a.time_s.iloc[0]:.6g} s"); axes[row,col].grid(alpha=.2)
        axes[row,0].set_xlabel("Pore pressure / q0"); axes[row,1].set(xlabel="Layer total stress + q0 (Pa)",xlim=(-105,105))
    axes[0,0].legend(fontsize=9); fig.suptitle("Same-dt native near-surface profiles: full width / periodic cell")
    fig.text(.5,.008,"Upper 15% shown; unchanged q0 and particle spacing. Uniform 1D only, not sliding or complex-boundary validation.",ha="center",fontsize=9)
    fig.tight_layout(rect=(0,.03,1,.95)); profile_png=TESTS/"figures/k5_cell_review_r1_profiles.png"
    with profile_png.open("xb") as stream: fig.savefig(stream,dpi=160)
    plt.close(fig); evidence += [bound(history_png),bound(profile_png)]
    result=dict(reviewed_utc=utc(),audit_passed=True,verified_recorded_hashes=len(unique),no_solver_processes_observed=True,
        runs=summaries,comparisons=comparisons,timing=timing,native_prefix_0_ulp=True,full_cycle_admitted=False,
        limitations=["Only .15/1-s uniform periodic-cell equivalence and half-step evidence, not 15-s/2Tv or theory acceptance.",
            "Short separate runs measure observed timing, not controlled repeated whole-run acceleration.",
            "Reduced period excludes longer horizontal modes; no general sliding/plastic/complex-boundary or exact-HG-restart claim."],evidence=evidence)
    with check.open("x",encoding="utf8") as stream: json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps({k:v for k,v in result.items() if k not in ("evidence","runs")},indent=2),flush=True)


if __name__ == "__main__": main()
