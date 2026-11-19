"""Finite-Kw C08 exposure to the Eq. 47 trigger; reads retained trajectories only."""
import csv
import json
import struct
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from c08_h18_compare_r2 import SCHEMA, TYPES, read22

TESTS = Path(__file__).resolve().parents[1]
FIG = TESTS / "figures"
TAG = "c08_eq47_history_r1"
RECEIVER = "c08_h18_as03n255_full3_r1"
DP = 0.04


def require(test, message):
    if not test:
        raise ValueError(message)


def h18_trajectory():
    native = TESTS / "outputs" / RECEIVER / "native_r1"
    done = json.loads((native / "completion.json").read_text())
    require(done["passed"] and done["samples"] == 301 and done["new_updates"] == 600000
            and done["group"] == "psi0" and done["soil_IDs"] == 5000, "Unexpected receiver profile")
    expected = np.r_[np.arange(1805), np.arange(2060, 7060)]
    with (native / "typed22_layout.csv").open(newline="") as fh:
        layout = [(r["array"], r["type"], int(r["components"])) for r in csv.DictReader(fh)]
    require(tuple(layout) == SCHEMA, "Native schema mismatch")
    raw = native / "typed22.bin"
    with raw.open("rb") as fh:
        require(struct.unpack("<III", fh.read(12)) == (6805, 22, 301), "Unexpected header")
    dtype = np.dtype([("time", "<f8")] + [(k, TYPES[t], (6805, w)) for k, t, w in SCHEMA])
    require(raw.stat().st_size == 12 + 301 * dtype.itemsize, "Native extent")
    with (native / "clocks.csv").open(newline="") as fh:
        clocks = list(csv.DictReader(fh))
    bundle = dict(frames=np.memmap(raw, dtype=dtype, mode="r", offset=12, shape=(301,)),
                  clocks=clocks, expected=expected)
    previous = None
    history, risk = [], []
    counts = np.zeros(5000, dtype=int)
    run = np.zeros_like(counts)
    longest = np.zeros_like(counts)
    last_steps = 0
    for frame in range(301):
        state = read22(bundle, frame)
        time = float(clocks[frame]["tau_from_actual_release_s"])
        steps = int(clocks[frame]["completed_step"])
        if frame:
            require(steps - last_steps == (1999 if frame == 300 else 2000), "Changed saved cadence")
        mask = slice(1805, None)
        p = state["PorePress"][mask, 0]
        ex = state["ExcessPorePress"][mask, 0]
        neg = p < 0
        fs = np.isin(state["FSType"][mask, 0], (2, 3))
        pos = state["Posd"][mask][:, (0, 2)]
        kappa = state["Kplastic"][mask, 0]
        nn = cKDTree(pos).query(pos, k=2)[0][:, 1]
        close = nn < 0.7 * DP
        run = np.where(neg, run + 1, 0)
        longest = np.maximum(longest, run)
        counts += neg
        plastic = np.zeros(len(p), dtype=bool)
        if previous is not None:
            plastic = kappa > previous["kappa"]
            require(np.all(kappa >= previous["kappa"]), "Plastic history decreased")
            # Only nodes with no close neighbour at the previous save are at risk.
            # Stratification by plastic activity uses the interval ENDING at the previous save.
            if frame >= 2:
                for n in (False, True):
                    for a in (False, True):
                        eligible = ~previous["close"] & (previous["negative"] == n) & (previous["plastic"] == a)
                        risk.append(dict(part=frame, tau_s=time, prior_negative=n, prior_plastic=a,
                                         eligible=int(eligible.sum()), newly_close=int(np.sum(eligible & close))))
        history.append(dict(part=frame, tau_s=time, completed_step=steps, negative=int(neg.sum()),
                            false_activations_if_excess=int(np.sum((ex < 0) & ~neg)),
                            occupied_close=int(close.sum()), negative_and_close=int(np.sum(neg & close)),
                            surface_negative=int(np.sum(fs & neg)), kappa_increased=int(plastic.sum()),
                            pmin_Pa=float(p.min()), min_spacing_over_dp=float(nn.min()/DP),
                            front_x_m=float(pos[:, 0].max())))
        previous = dict(kappa=kappa, negative=neg, close=close, plastic=plastic)
        last_steps = steps
    return pd.DataFrame(history), pd.DataFrame(risk), pd.DataFrame(dict(
        native_id=np.arange(2060, 7060), negative_saves=counts, longest_consecutive_negative_saves=longest))


def h12_trace():
    name = "upl_c08_stage_trace_terms_r2_window"
    checked = json.loads((FIG / (name + ".check.json")).read_text())
    require(checked["passed"], "Underlying pressure trace review failed")
    use = ["nstep", "tau_s", "step_start_s", "native_id", "p_n_Pa", "p_full_postpond_Pa"]
    data = pd.read_csv(FIG / (name + "_steps.csv"), usecols=use, float_precision="round_trip")
    outcomes, dense = [], []
    for ident, grp in data.groupby("native_id"):
        grp = grp.sort_values("nstep")
        step = grp.nstep.to_numpy()
        require(np.all(np.diff(step) > 0), "Duplicate or unordered trace")
        pos = np.flatnonzero(np.diff(step) == 1) + 1
        require(len(pos) and np.all(np.diff(pos) == 1), "Expected one dense step interval")
        dt = 2.5e-6
        clk = grp.step_start_s.to_numpy()
        require(np.all(clk[pos] == clk[pos-1] + dt), "Nonadjacent scalar clock")
        pn, after = (grp[key].to_numpy() for key in ("p_n_Pa", "p_full_postpond_Pa"))
        require(np.array_equal(after[pos-1].astype(np.float32).view(np.uint32),
                               pn[pos].astype(np.float32).view(np.uint32)), "Discontinuous committed pressure")
        # The old sign selects Eq47's row. Do not use the sign of the extrapolation.
        pn_1, current, following = pn[pos-1], pn[pos], after[pos]
        extrap = current + 0.5 * (current - pn_1)
        negative = current < 0
        require(negative.any(), "No actual negative trace rows")
        selected = pd.DataFrame(dict(native_id=ident, step=step[pos], tau_s=grp.tau_s.to_numpy()[pos],
                                     pn_Pa=current, previous_Pa=pn_1, actual_next_Pa=following,
                                     p_alpha_Pa=extrap))
        dense.append(selected)
        for group, subset in (("all", np.ones(len(pos), bool)), ("negative", negative)):
            def rms(x):
                return float(np.sqrt(np.mean(x[subset]**2)))
            outcomes.append(dict(native_id=int(ident), rows=group, updates=int(subset.sum()),
                                 cold_error_rms_Pa=rms(following-current),
                                 extrapolation_error_rms_Pa=rms(following-extrap),
                                 history_increment_rms_Pa=rms(extrap-current),
                                 history_increment_abs_max_Pa=float(np.max(abs((extrap-current)[subset]))),
                                 changed_trigger_if_extrapolated=int(np.sum(((extrap<0)!=negative)&subset))))
    return pd.DataFrame(outcomes), pd.concat(dense,ignore_index=True)


def main():
    files = {suffix: FIG / (TAG + suffix) for suffix in
             ("_frames.csv", "_risk.csv", "_material.csv", "_trace.csv", "_trace_plot.csv", ".png")}
    check = TESTS / "logs" / (TAG + ".check.json")
    require(not any(p.exists() for p in (*files.values(),check)), "Prior output exists")
    hist,risk,material = h18_trajectory()
    trace,dense = h12_trace()
    for df,suffix in zip((hist,risk,material,trace),("_frames.csv","_risk.csv","_material.csv","_trace.csv")):
        df.to_csv(files[suffix], index=False)
    by_class = risk.groupby(["prior_negative","prior_plastic"])[["eligible","newly_close"]].sum().reset_index()
    by_class["fraction"] = by_class.newly_close / by_class.eligible
    fig, axes = plt.subplots(2,2,figsize=(11,7),constrained_layout=True)
    for field,label in (("negative","Negative pressure"),("occupied_close","Nearest neighbour < 0.7 dp")):
        axes[0,0].plot(hist.tau_s,100*hist[field]/5000,label=label)
    axes[0,0].set(xlabel="Time after release (s)",ylabel="Soil particles (%)", title="Wendland, h/dp = 1.8")
    axes[0,0].legend()
    for active,label,dx in ((False,"No increase in prior interval",-.18),(True,"Plastic history increased",.18)):
        s = by_class.loc[by_class.prior_plastic == active].sort_values("prior_negative")
        axes[0,1].bar(np.arange(2)+dx,100*s.fraction,.35,label=label)
    axes[0,1].set(xticks=[0,1],xticklabels=["Prior p ≥ 0","Prior p < 0"],
                  ylabel="Newly close at next save (%)", title="Previously separated particles")
    axes[0,1].legend(fontsize=8)
    sample = dense[(dense.tau_s>=.619) & (dense.tau_s<.621)]
    sample.to_csv(files["_trace_plot.csv"],index=False)
    for ident,s in sample.groupby("native_id"):
        axes[1,0].plot(s.tau_s*1000,s.pn_Pa/1000,label=f"ID {ident}")
    axes[1,0].set(xlabel="Time after release (ms)", ylabel="Committed pressure (kPa)",title="Cubic, h/dp = 1.2, consecutive steps")
    axes[1,0].legend(fontsize=8)
    s=trace[trace.rows=="negative"]
    for k,label,dx in (("cold_error_rms_Pa","Previous pressure",-.18),("extrapolation_error_rms_Pa","Linear history",.18)):
        axes[1,1].bar(np.arange(len(s))+dx,s[k],.35,label=label)
    axes[1,1].set(xticks=np.arange(len(s)),xticklabels=s.native_id.astype(str),xlabel="Soil particle ID",
                  ylabel="Next-pressure prediction RMS (Pa)",title="Negative-pressure steps, finite Kw trajectory")
    axes[1,1].legend(fontsize=8)
    fig.savefig(files[".png"],dpi=160)
    plt.close(fig)
    summary=dict(receiver=RECEIVER,frames=len(hist),soil_ids=len(material),
                 negative_soil_frame_observations=int(hist.negative.sum()),
                 ever_negative_ids=int((material.negative_saves>0).sum()),
                 longest_negative_run_in_saves=int(material.longest_consecutive_negative_saves.max()),
                 close_observations=int(hist.occupied_close.sum()),
                 close_negative_observations=int(hist.negative_and_close.sum()),
                 by_class=by_class.to_dict("records"),
                 trace_source="upl_c08_stage_trace_terms_r2_window_steps.csv", dense_start_tau_s=float(dense.tau_s.min()),
                 dense_end_tau_s=float(dense.tau_s.max()),trace=trace.to_dict("records"),
                 new_coupled_updates=0, beta_feedback_evaluated=False)
    check.write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))

if __name__ == "__main__":
    main()
