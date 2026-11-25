"""Evaluate retained +2.5 degree soil columns on the original physical axes of Lian Figs. 15–16."""
import argparse
import csv
from pathlib import Path
import re
import struct

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors
import numpy as np
from scipy.spatial import cKDTree

from c08_lian_partial_r1 import CACHE, CASE, FIG16_TICKS, PDF, panel16
from digitize_lian_collapse_fronts import PANELS, connected_body, load_pages
from postprocess_lian_release import DP, RELEASE_IDS, SOIL_IDS, native, verify_source_material

ROOT = CASE / "tests/figures/c08_psi25_tpi"
FORMAL = CASE / "figures/validation_explicit/psi2p5"
TIMES = (.01, .3, .5, .6, 1.2)


def write_rows(path, rows):
    with path.open("w", encoding="utf8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def panel_samples():
    page, _ = load_pages(CACHE, PDF)
    panels = []
    for tau, x0, x8, z2, bed, _ in PANELS[15]:
        left, right, top = int(np.floor(x0))-3, int(np.ceil(x8))+3, z2-4
        crop = page[top:bed+2, left:right+1]
        mask = connected_body(crop, 15, 55)
        x = (left+np.arange(len(mask[0]))-x0)*8/(x8-x0)
        z = (bed-top-np.arange(len(mask)))*2/(bed-z2)
        panels.append((15, "published", tau, x, z, mask))
    for tau, pair in FIG16_TICKS.items():
        for label, ticks in zip(("stabilized", "non-stabilized"), pair):
            rgba, (xmin, xmax, zmin, zmax) = panel16(page, ticks)
            h, w = rgba.shape[:2]
            x = xmin+(np.arange(w)+.5)*(xmax-xmin)/w
            z = zmax-(np.arange(h)+.5)*(zmax-zmin)/h
            panels.append((16, label, tau, x, z, rgba[:, :, 3] != 0))
    return panels


def material(xz, p, excess, kappa):
    if not all(np.isfinite(a).all() for a in (xz, p, excess, kappa)) or len(xz) != len(SOIL_IDS):
        raise ValueError("Invalid material positions or pressure/plastic fields")
    return dict(xz=xz, p=p, excess=excess, kappa=kappa)


def baseline():
    with (FORMAL / "history.csv").open() as stream:
        history = {int(r["part"]): r for r in csv.DictReader(stream)}
    wanted = {round(100*t): t for t in TIMES}
    data = np.genfromtxt(FORMAL / "fields.csv", delimiter=",", names=True, encoding="utf8",
                         usecols=("part","id","x_m","z_m","p_kPa","excess_kPa","kappa"))
    result = {}
    for part, tau in wanted.items():
        group = data[data["part"] == part]
        row = history[part]
        if not np.array_equal(group["id"], SOIL_IDS) or abs(float(row["tau_s"])-tau) > 5.01e-6:
            raise ValueError(f"Wrong baseline IDs or clock at PART {part}")
        frame = material(np.column_stack((group["x_m"],group["z_m"])),group["p_kPa"],group["excess_kPa"],group["kappa"])
        result[tau] = (part, int(row["completed_step"]), float(row["time_s"]), float(row["tau_s"]), frame)
    return result


def header_value(prefix, key, type_number, fmt):
    name = key.encode("ascii")
    tag = struct.pack("<I",len(name))+name+struct.pack("<I",type_number)
    if prefix.count(tag) != 1:
        raise ValueError(f"Ambiguous or missing native header value {key}")
    return struct.unpack_from("<"+fmt,prefix,prefix.index(tag)+len(tag))[0]


def pilot(directory):
    from c08_psi25_tpi_native import read_frame
    selected = {}
    folder = directory.resolve()
    for file in sorted((folder / "data").glob("Part_????.bi4")):
        with file.open("rb") as stream:
            head = stream.read(8192)
        if not header_value(head,"GravityPreloadPhase",8,"I"):
            continue
        elapsed = header_value(head,"TimeStep",12,"d")-header_value(head,"GravityPreloadActualTime",12,"d")
        nearest = min(TIMES, key=lambda t: abs(elapsed-t))
        if abs(elapsed-nearest) <= 5.01e-6 and (nearest not in selected or abs(elapsed-nearest) < selected[nearest][0]):
            selected[nearest] = abs(elapsed-nearest), file
    if not selected:
        raise ValueError(f"No released frame at a paper time in {directory}")
    result = {}
    prestates = {}
    for tau, (_, file) in selected.items():
        meta, arr, _, _ = read_frame(file)
        if not (np.array_equal(arr["Idp"], RELEASE_IDS) and meta["HydroMechModel"] == 2
                and meta["GravityPreloadPhase"] and meta["Nout"] == 0):
            raise ValueError(f"Wrong TPI material set, phase or history: {file}")
        source_file = (folder / meta["GravityPreloadStateFile"]).resolve()
        if source_file not in prestates:
            source, state = native(source_file)
            verify_source_material(source, "psi2p5")
            prestates[source_file] = state["PorePress0"][SOIL_IDS]
        soil = arr["Idp"] >= SOIL_IDS[0]
        if not np.array_equal(arr["PorePress0"][soil], prestates[source_file]):
            raise ValueError(f"Inconsistent paired source P0 at {file}")
        p = arr["PorePress"][soil]
        excess = arr["ExcessPorePress"][soil]
        if not np.array_equal(excess, p - arr["PorePress0"][soil]):
            raise ValueError(f"Inconsistent total/material excess pressure at {file}")
        t, event = meta["TimeStep"], meta["GravityPreloadActualTime"]
        frame = material(arr["Posd"][soil][:, [0,2]], p.astype(float)*.001,
                         excess.astype(float)*.001,arr["Kplastic"][soil].astype(float))
        result[tau] = (meta["Cpart"], int(meta["Step"])+1, t, t-event, frame)
    return result


def panel_geometry(x, z, paper, frame):
    xx, zz = np.meshgrid(x,z)
    tree = cKDTree(frame["xz"])
    # dp/sqrt(2) is the center-to-corner distance of one original square particle cell.
    dist = tree.query(np.column_stack((xx.ravel(),zz.ravel())))[0].reshape(xx.shape)
    occupied = dist <= DP/np.sqrt(2)
    visible = (xx >= 0) & (xx <= 8) & (zz >= 0) & (zz <= 2)
    outside = (frame["xz"][:,0]<0)|(frame["xz"][:,0]>8)|(frame["xz"][:,1]<0)|(frame["xz"][:,1]>2)
    row = dict(front_reference_m=float(xx[paper].max()), front_centers_m=frame["xz"][:,0].max(),
               front_p99_centers_m=np.quantile(frame["xz"][:,0],.99), centers_outside_physical_frame=int(sum(outside)))
    row["front_difference_m"] = row["front_centers_m"]-row["front_reference_m"]
    for key, region in (("full",visible),("right",visible & (xx >= 2))):
        union = region & (paper | occupied)
        row[key+"_iou"] = np.count_nonzero(region & paper & occupied)/np.count_nonzero(union)
    # Physical columns: empty columns take zero height, so a short front is penalized.
    height_ref = np.where(paper & visible,zz,0).max(axis=0)
    height_sph = np.where(occupied & visible,zz,0).max(axis=0)
    use = (x>=2) & (np.maximum(height_ref,height_sph)>0)
    row["right_upper_envelope_rmse_m"] = np.sqrt(np.mean((height_ref[use]-height_sph[use])**2))
    return row, occupied, height_ref, height_sph


def fields(frame, tree):
    nn = tree.query(frame["xz"],k=2)[0][:,1]/DP
    p, excess, kappa = (frame[k] for k in ("p","excess","kappa"))
    return dict(p_min_kPa=p.min(),p_p05_kPa=np.quantile(p,.05),p_median_kPa=np.median(p),
                p_p95_kPa=np.quantile(p,.95),p_max_kPa=p.max(),p_negative_count=int(sum(p < 0)),
                p_below_minus10_count=int(sum(p < -10)),
                p_above20_count=int(sum(p > 20)), excess_min_kPa=excess.min(),excess_p05_kPa=np.quantile(excess,.05),
                excess_median_kPa=np.median(excess),excess_max_kPa=excess.max(),
                excess_below_minus10_count=int(sum(excess < -10)),excess_above10_count=int(sum(excess > 10)),
                nn_min_over_dp=nn.min(),nn_p05_over_dp=np.quantile(nn,.05),nn_below_half_count=int(sum(nn < .5)),
                kappa_mean=kappa.mean(),kappa_p99=np.quantile(kappa,.99),kappa_max=kappa.max(),
                kappa_positive_count=int(sum(kappa>0)))


def pressure_figure16(out, runs):
    page, _ = load_pages(CACHE, PDF)
    palette = colors.ListedColormap(page[937,446:612]/255.)
    scale = colors.Normalize(vmin=-10, vmax=20, clip=True)
    labels = ["Lian stabilized", "Lian non-stabilized", *runs]
    fig, axes = plt.subplots(3,len(labels),figsize=(3.55*len(labels),5.6),layout="constrained",
                             squeeze=False,sharex=True,sharey=True)
    for i,(tau,ticks) in enumerate(FIG16_TICKS.items()):
        for j,(ax,label) in enumerate(zip(axes[i],labels)):
            if j<2:
                pixels, extent = panel16(page,ticks[j])
                ax.imshow(pixels,extent=extent,interpolation="nearest")
            elif tau in runs[label]:
                frame = runs[label][tau][-1]
                ax.scatter(*frame["xz"].T,c=frame["p"],cmap=palette,norm=scale,s=2.7,linewidths=0,
                           rasterized=True)
            else:
                ax.text(.5,.5,"No saved frame",transform=ax.transAxes,ha="center",fontsize=8)
            ax.set(xlim=(0,8),ylim=(0,2.05),xticks=(0,2,4,6,8),yticks=(0,1,2),aspect="equal")
            if i==0: ax.set_title(label,fontsize=10)
            if j==0: ax.set_ylabel(f"{tau:g} s\nz (m)")
            if i==2: ax.set_xlabel("x (m)")
    bar = fig.colorbar(plt.cm.ScalarMappable(norm=scale,cmap=palette),ax=axes.ravel().tolist(),
                       location="bottom",ticks=(-10,0,10,20),shrink=.55,aspect=46,pad=.025)
    bar.set_label("Total pore-water pressure (kPa)")
    fig.suptitle("Lian et al. Fig. 16    |    Saturated column, ψ = +2.5°")
    fig.savefig(out/"figure16_pressure.png",dpi=165)
    plt.close(fig)


def evaluate(out, runs, panels):
    rows, envelopes, states = [], [], []
    for label, sequence in runs.items():
        for tau, (part, step, time, actual, frame) in sorted(sequence.items()):
            states.append(dict(run=label,nominal_tau_s=tau,part=part,completed_step=step,time_s=time,
                               actual_tau_s=actual,**fields(frame,cKDTree(frame["xz"]))))
    for figure in (15,16):
        selected = [q for q in panels if q[0]==figure and any(q[2] in s for s in runs.values())]
        fig, axes = plt.subplots(len(selected),len(runs),squeeze=False,
                                 figsize=(4.65*len(runs),1.8*len(selected)+.8),layout="constrained")
        for i, (_, paper_label, tau, x, z, paper) in enumerate(selected):
            for j,(label,sequence) in enumerate(runs.items()):
                ax = axes[i,j]
                ax.contour(x,z,paper.astype(float),levels=(.5,),colors="#c24a32",linewidths=1.25)
                if tau in sequence:
                    part, step, time, actual, frame = sequence[tau]
                    geom, occ, hp, hs = panel_geometry(x,z,paper,frame)
                    row = dict(run=label,figure=figure,paper_panel=paper_label,nominal_tau_s=tau,part=part,
                               completed_step=step,time_s=time,actual_tau_s=actual,**geom)
                    rows.append(row)
                    envelopes.extend(dict(run=label,figure=figure,paper_panel=paper_label,nominal_tau_s=tau,
                                          actual_tau_s=actual,x_m=xi,paper_top_m=rp,simulation_top_m=rs)
                                     for xi,rp,rs in zip(x,hp,hs) if 0<=xi<=8 and max(rp,rs)>0)
                    ax.contour(x,z,occ.astype(float),levels=(.5,),colors="#007598",linewidths=1)
                    ax.scatter(*frame["xz"].T,s=.45,color="#589bb0",alpha=.38,linewidths=0,rasterized=True)
                    ax.text(.98,.85,f"Right-half IoU {geom['right_iou']:.3f}",ha="right",
                            va="center",transform=ax.transAxes,fontsize=8)
                else:
                    ax.text(.98,.85,"No saved frame",ha="right",transform=ax.transAxes,fontsize=8)
                ax.set(xlim=(-.05,8),ylim=(-.05,2.13),xticks=(0,2,4,6,8),yticks=(0,1,2),aspect="equal")
                if not j: ax.set_ylabel(f"{tau:g} s\n{paper_label}\nz (m)")
                if not i: ax.set_title(label,fontsize=10)
                if i==len(selected)-1: ax.set_xlabel("x (m)")
        fig.suptitle(f"ψ = +2.5°    Lian et al. Fig. {figure} (red)\nC08 particle distribution and outline (blue)",
                     fontsize=12)
        fig.savefig(out/f"figure{figure}.png",dpi=165)
        plt.close(fig)
    write_rows(out/"shapes.csv",rows)
    write_rows(out/"upper_envelopes.csv",envelopes)
    write_rows(out/"native_fields.csv",states)
    pressure_figure16(out,runs)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag",required=True,help="New result subdirectory")
    ap.add_argument("--run",nargs=2,action="append",metavar=("LABEL","RUN_DIRECTORY"),default=[])
    args=ap.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9_-]+",args.tag):
        ap.error("Tag must be a single directory name")
    out=ROOT/args.tag
    if out.exists():
        ap.error(f"Output exists: {out}")
    runs={"Explicit u-pl":baseline()}
    for label, directory in args.run:
        if label in runs:
            ap.error("Run labels must be distinct")
        runs[label]=pilot(Path(directory))
    panels=panel_samples()
    with (CASE/"support/lian_collapse_fronts.csv").open() as f:
        refs={float(r["tau_s"]): float(r["front_x_m"]) for r in csv.DictReader(f) if r["group"]=="psi2p5"}
    for fig, _, tau, x, _, mask in panels:
        if fig==15:
            np.testing.assert_allclose(x[np.any(mask,axis=0)].max(),refs[tau],rtol=0,atol=1e-10)
    out.mkdir(parents=True,exist_ok=False)
    evaluate(out,runs,panels)


if __name__=="__main__":
    main()
