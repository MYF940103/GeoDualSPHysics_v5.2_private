"""Measure suction on the original C08 saved material points and their geometric support."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial import cKDTree

from c08_psi25_tpi_native import CASE, TESTS, PRE, RELEASE_IDS, SOIL_IDS, read_frame, native, require

RUNS = {
    "beta0": "c08_psi25_tpi_paper_b0_r1",
    "positive_only": "c08_psi25_tpi_paper_b004_r1",
    "all_zero": "c08_psi25_tpi_surface_zero_r1",
}
OUT = TESTS / "figures/c08_psi25_local_suction"
DP = .04
H = float(np.float32(.072))
FIXED = len(RELEASE_IDS) - len(SOIL_IDS)


def save(name, records):
    with (OUT / name).open("x", newline="", encoding="utf8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0])
        writer.writeheader()
        writer.writerows(records)


def neighborhood(a, i, tree, fs_tree):
    points = tree.data
    offsets = np.asarray(tree.query_ball_point(points[i], 2*H), dtype=int)
    offsets = offsets[offsets != i]
    delta = points[offsets] - points[i]
    r = np.linalg.norm(delta, axis=1)
    bed = offsets < FIXED  # includes any fixed donor, not a reconstructed ghost at a force stage
    p = a["PorePress"][offsets].astype(float)/1000
    soil = ~bed
    fs = np.isin(a["FSType"][offsets], [2, 3]) & soil
    # A direction matrix of material neighbors only; kernel-derivative weights for Wendland C2.
    # This is not the solver correction matrix or a hydromechanical force evaluation.
    weights = a["PoroCurrentVolume"][offsets[soil]] * np.maximum(0., 1-r[soil]/(2*H))**3
    moment = (delta[soil].T * weights) @ delta[soil]
    eig = np.linalg.eigvalsh(moment)
    return dict(other_soil_2H=int(soil.sum()), fixed_2H=int(bed.sum()), fs_soil_2H=int(fs.sum()),
                nearest_soil_dp=r[soil].min()/DP, nearest_fs_dp=fs_tree.query(points[i])[0]/DP,
                other_soil_h12=int((soil & (r<2*1.2*DP)).sum()),
                fixed_h12=int((bed & (r<2*1.2*DP)).sum()),
                soil_direction_ratio=eig[0]/eig[-1], soil_min_kPa=p[soil].min(),
                soil_median_kPa=np.median(p[soil]), soil_max_kPa=p[soil].max(),
                fixed_min_kPa=p[bed].min() if bed.any() else "",
                fixed_max_kPa=p[bed].max() if bed.any() else "")


def measure():
    _, initial = native(PRE.with_name("Part_0000.bi4"))
    soil0 = initial["Posd"][-len(SOIL_IDS):]
    require(np.array_equal(initial["Idp"][-len(SOIL_IDS):], SOIL_IDS), "Unexpected initial IDs")
    right = np.isclose(soil0[:,0], soil0[:,0].max(), rtol=0, atol=1e-8)
    frames, tracks, events = [], [], []
    clock = {}
    for label, tag in RUNS.items():
        receipt = json.loads((TESTS/"logs"/(tag+".native_review.json")).read_text())
        require(receipt["tag"] == tag and receipt["passed"] and receipt["frames"] == 132, "Unreviewed output")
        sealed = {name:(size, modified) for name,size,modified in receipt["files"]}
        for part in range(5, 133):
            path = TESTS/"outputs"/tag/"data"/f"Part_{part:04}.bi4"
            stat = path.stat()
            require(sealed[str(path.relative_to(CASE))] == (stat.st_size,stat.st_mtime_ns), "Changed saved frame")
            meta, a, history, prev = read_frame(path)
            tau = meta["TimeStep"]-receipt["release_time_s"]
            step = meta["Step"]+1
            key = (meta["TimeStep"], tau, step, history["PreviousTime"])
            require(clock.setdefault(part,key)==key and history["SavedTime"]==meta["TimeStep"]
                    and np.array_equal(a["Idp"],RELEASE_IDS), "Unmatched time or IDs")
            p = a["PorePress"][FIXED:].astype(float)/1000
            fs = np.isin(a["FSType"][FIXED:], [2,3])
            xz = a["Posd"][:,[0,2]]
            tree = cKDTree(xz)
            fs_tree = cKDTree(xz[FIXED:][fs])
            worst = int(np.argmin(p))
            severe = np.flatnonzero(p < -50)
            info = dict(run=label, part=part, step=step, time_s=meta["TimeStep"], tau_s=tau)
            frames.append(dict(info, min_id=int(SOIL_IDS[worst]), min_kPa=p[worst], p01_kPa=np.percentile(p,1),
                               p05_kPa=np.percentile(p,5), median_kPa=np.median(p), below50=len(severe),
                               below100=int((p < -100).sum()), below50_fs=int(fs[severe].sum()),
                               below50_initial_right=int(right[severe].sum())))
            targets = np.unique(np.r_[np.searchsorted(SOIL_IDS,[7010,7018]),worst,severe])
            for s in targets:
                i = FIXED + s
                row = dict(info, id=int(SOIL_IDS[s]), x0_m=soil0[s,0], z0_m=soil0[s,2],
                           x_m=xz[i,0], z_m=xz[i,1], fs_type=int(a["FSType"][i]),
                           p_kPa=p[s], p_prev_kPa=float(prev[s])/1000,
                           p0_kPa=float(a["PorePress0"][i])/1000,
                           J=a["PoroVolumeRatio"][i], theta_last_s_inv=a["PoroThetaLastStage"][i],
                           k_m_s=a["PoroHydraulicConductivity"][i], kappa=float(a["Kplastic"][i]),
                           eff_mean_compression_kPa=-np.mean(a["SigmaState_kk"][i])/1000,
                           vx_m_s=float(a["Vel"][i,0]), vz_m_s=float(a["Vel"][i,2]),
                           **neighborhood(a,i,tree,fs_tree))
                if row["id"] in (7010,7018):
                    tracks.append(row)
                if p[s] < -50:
                    events.append(row)
    return frames, tracks, events


def figure(frames, tracks):
    fig, ax = plt.subplots(3,2,figsize=(11,8.5),sharex=True,layout="constrained")
    names = {"beta0":"Positive cap, β = 0", "positive_only":"Positive cap, β = 0.04",
             "all_zero":"Zero surface, β = 0.04"}
    colors = {"beta0":"#777777","positive_only":"#2166ac","all_zero":"#b33c28"}
    for label in RUNS:
        rows = [r for r in tracks if r["run"]==label and r["id"]==7010]
        group = [r for r in frames if r["run"]==label]
        t = [r["tau_s"] for r in rows]
        for axis,field,source in ((ax[0,0],"p_kPa",rows),(ax[0,1],"p05_kPa",group),
                                  (ax[1,0],"J",rows),(ax[1,1],"kappa",rows),
                                  (ax[2,0],"other_soil_2H",rows),(ax[2,1],"below50",group)):
            axis.plot(t,[r[field] for r in source],color=colors[label],label=names[label],lw=1.55)
        if label=="all_zero":
            mask = np.array([r["fs_type"] in (2,3) for r in rows])
            ax[0,0].scatter(np.array(t)[mask],np.array([r["p_kPa"] for r in rows])[mask],
                            color=colors[label],s=9,zorder=3,label="ID 7010 on zero surface")
    titles = ["ID 7010 · gauge pore pressure","All soil · 5th percentile of gauge pressure",
              "ID 7010 · volume ratio","ID 7010 · accumulated plastic strain",
              "ID 7010 · other soil centers within 2h","All soil · gauge pressure below −50 kPa"]
    for a,title,unit in zip(ax.flat,titles,["kPa","kPa","J","κ","Soil neighbors","Particles out of 5,000"]):
        a.set_title(title,fontsize=11,loc="left")
        a.set_ylabel(unit)
        a.grid(alpha=.22)
    ax[0,0].legend(fontsize=8)
    for a in ax[-1]: a.set_xlabel("Time after wall removal (s)")
    fig.savefig(OUT/"suction.png",dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    frames, tracks, events = measure()
    OUT.mkdir(exist_ok=False)
    save("all_soil.csv",frames)
    save("material_points.csv",tracks)
    save("below_minus50kPa.csv",events)
    figure(frames,tracks)
