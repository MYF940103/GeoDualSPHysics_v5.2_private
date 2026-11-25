"""Compare pressure and plastic strain in Lian's dilative column with retained C08 particle states."""
import argparse
import csv
import gzip
import json
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors
import numpy as np
from scipy.ndimage import binary_erosion
from scipy.spatial import cKDTree

from c08_lian_partial_r1 import CACHE, CASE, FIG16_TICKS, PDF, axes_style, panel16
from c08_psi25_tpi_shape import baseline, pilot, write_rows
from digitize_lian_collapse_fronts import PANELS, connected_body, load_pages
from postprocess_lian_release import SOIL_IDS


DEST = CASE / "tests/figures/c08_psi25_tpi_fields"
STRAIN_AXES = {  # Original 180 dpi physical x=0/8 m and z=0/2 m ticks, Fig. 15 left.
    .3: (166, 657.5, 326, 203), .6: (164, 655, 539, 416), 1.2: (163, 652, 770, 648)}
STRAIN_MAX = {.3: .3, .6: 1., 1.2: 2.}
FIG15_TIMES = tuple(STRAIN_AXES)
FIG16_TIMES = tuple(FIG16_TICKS)


def fig15_image(page, ticks, strain=False):
    x0, x8, bed, z2 = ticks
    left, right, top = int(x0)-2, int(np.ceil(x8))+2, z2-2
    crop = page[top:bed+2, left:right+1]
    # The published left panels contain yellow annotations and a magnified inset.
    if strain:
        image = crop
    else:
        image = np.dstack((crop, 255*connected_body(crop, 15, 55).astype(np.uint8)))
    sx, sz = 8/(x8-x0), 2/(bed-z2)
    return image, ((left-x0-.5)*sx, (right-x0+.5)*sx, -1.5*sz, (bed-top+.5)*sz)


def paper_panels(page, key, tau):
    if key == "p":
        return [(label,*panel16(page, ticks)) for label, ticks in zip(
            ("Lian (a)  stabilized", "Lian (b)  non-stabilized"), FIG16_TICKS[tau])]
    if key == "kappa":
        return [("Lian  Fig. 15", *fig15_image(page, STRAIN_AXES[tau], strain=True))]
    _, x0, x8, z2, bed, _ = next(row for row in PANELS[15] if row[0] == tau)
    return [("Lian  Fig. 15", *fig15_image(page, (x0, x8, bed, z2)))]


def palette_limits(page, key, tau):
    if key == "kappa":
        row, left, right = {.3:(195,473,633), .6:(406,456,621), 1.2:(638,472,636)}[tau]
        return page[row,left:right], 0., STRAIN_MAX[tau]
    if key == "excess":
        return page[214, 1003:1169], -10., 10.
    return page[937, 446:612], -10., 20.


def print_colors_at_particles(image, extent, palette, vmin, vmax, xz):
    """Sample the nearest original raster pixel once. Keep only credible interior color samples."""
    h, w = image.shape[:2]
    xmin, xmax, zmin, zmax = extent
    ix = np.floor((xz[:,0]-xmin)*w/(xmax-xmin)).astype(int)
    iz = np.floor((zmax-xz[:,1])*h/(zmax-zmin)).astype(int)
    valid = (ix>=0) & (ix<w) & (iz>=0) & (iz<h)
    ix, iz = ix.clip(0,w-1), iz.clip(0,h-1)
    interior = binary_erosion(image[:,:,3] != 0, structure=np.ones((3,3), bool))
    distance, idx = cKDTree(palette.astype(float)).query(image[iz,ix,:3].astype(float))
    # 18 RGB units (Euclidean, out of 255 per channel) rejects ink and strongly mixed colors.
    valid &= interior[iz,ix] & (distance<=18)
    value = np.full(len(ix), np.nan)
    value[valid] = vmin + idx[valid]*(vmax-vmin)/(len(palette)-1)
    return value


def summary(values, lower, upper):
    if not len(values):
        return dict(n=0, minimum="",p05="", median="", p95="",maximum="",mean="",
                    below_scale="",above_scale="",negative="")
    q = np.percentile(values, [0,5,50,95,100])
    return dict(n=len(values), minimum=q[0],p05=q[1],median=q[2],p95=q[3],maximum=q[4],
                mean=values.mean(),below_scale=np.count_nonzero(values<lower),
                above_scale=np.count_nonzero(values>upper),negative=np.count_nonzero(values<0))


def compute_regions(frame, key, lower, upper, printed):
    x = frame["xz"][:,0]
    regions = {"all_soil":np.ones(len(x), bool), "x_below_2m":x<2,
               "x_2m_to_4m":(x>=2)&(x<4), "x_at_least_4m":x>=4,
               "kappa_above_0p1":frame["kappa"]>.1}
    if key=="excess":
        reference = printed[0][1]
        regions["in_printed_excess_below_minus2p5_kPa"] = reference < -2.5
    return [(name,summary(frame[key][mask], lower, upper)) for name, mask in regions.items()]


def draw(out, key, runs, page, records, pairs, samples):
    specs = {"kappa": ("15", "Accumulated equivalent plastic strain", "1", FIG15_TIMES),
             "excess": ("15", "Excess pore-water pressure", "kPa", FIG15_TIMES),
             "p": ("16", "Total pore-water pressure", "kPa", FIG16_TIMES)}
    figure, name, unit, times = specs[key]
    nref = 2 if key == "p" else 1
    n = nref + len(runs)
    # The morphology workflow already produces the Fig. 16 total-pressure comparison.
    plot = key != "p"
    if plot:
        fig = plt.figure(figsize=(3.6*n+.9,5.65), layout="constrained")
        grid = fig.add_gridspec(len(times),n+1,width_ratios=[1]*n+[.041])
        fig.suptitle(f"{name}\nLian et al. Fig. {figure}   ·   ψ = +2.5°",fontsize=13)
    for i,tau in enumerate(times):
        raw_palette, lo, hi = palette_limits(page,key,tau)
        cmap = colors.ListedColormap(raw_palette/255.)
        norm = colors.Normalize(lo,hi,clip=True)
        panels=paper_panels(page,key,tau)
        heads=[]
        for j,(label,im,extent) in enumerate(panels):
            if plot:
                ax = fig.add_subplot(grid[i,j])
                ax.imshow(im,extent=extent,origin="upper",interpolation="nearest")
                heads.append((ax,label))
        for j,(label,sequence) in enumerate(runs.items(),nref):
            if plot:
                ax=fig.add_subplot(grid[i,j])
                heads.append((ax,label))
            if tau not in sequence:
                if plot:
                    ax.text(.5,.5,"No saved frame",transform=ax.transAxes,ha="center",fontsize=8)
                continue
            part,step,t,actual,frame = sequence[tau]
            xz, values = frame["xz"], frame[key]
            clock = dict(run=label,figure=figure,field=key,unit=unit,nominal_tau_s=tau,
                         actual_tau_s=actual,time_s=t,part=part,completed_step=step)
            if plot:
                ax.scatter(xz[:,0],xz[:,1],c=values,cmap=cmap,norm=norm,s=1.9,linewidths=0,rasterized=True)
            printed=[]
            if key!="kappa":
                for ref,im,extent in panels:
                    value = print_colors_at_particles(im,extent,raw_palette,lo,hi,xz)
                    printed.append((ref,value))
                    good = np.isfinite(value)
                    delta = values[good].clip(lo,hi) - value[good]
                    pairs.append(dict(**clock,reference_panel=ref,paper_color_samples=len(delta),
                                      n_native=len(values),lower_color_limit=lo,upper_color_limit=hi,
                                      clipped_mean_difference_kPa=delta.mean() if len(delta) else "",
                                      clipped_mean_absolute_difference_kPa=np.abs(delta).mean() if len(delta) else ""))
            for region,stats in compute_regions(frame,key,lo,hi,printed):
                records.append(dict(**clock,region=region,display_min=lo,display_max=hi,**stats))
            for idx,particle in enumerate(SOIL_IDS):
                samples.writerow((label,key,tau,actual,int(particle),xz[idx,0],xz[idx,1],values[idx],
                                  *(f"{v[idx]:.5g}" if np.isfinite(v[idx]) else "" for _,v in printed),
                                  *([""]*(2-len(printed)))))
        if plot:
            for j,(ax,label) in enumerate(heads):
                axes_style(ax, f"{tau:g} s\nz (m)" if j==0 else "", i==len(times)-1)
                if i==0:
                    ax.set_title(label,fontsize=10)
            bar=fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),cax=fig.add_subplot(grid[i,-1]),
                             ticks=[lo, (lo+hi)/2, hi] if key=="kappa" else np.arange(lo,hi+1,10))
            bar.ax.tick_params(labelsize=8)
            if key!="kappa": bar.set_label(unit,fontsize=8)
    if plot:
        fig.savefig(out/f"fig{figure}_{key}.png",dpi=180)
        plt.close(fig)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag",required=True)
    ap.add_argument("--run",nargs=2,metavar=("LABEL","NATIVE_DIRECTORY"),action="append",default=[])
    args=ap.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+",args.tag): ap.error("Use a single tag directory")
    out=DEST/args.tag
    if out.exists(): ap.error(f"Output already exists: {out}")
    runs={"Explicit u-pl":baseline()}
    for label,path in args.run:
        if label in runs: ap.error("Duplicate run label")
        folder=Path(path).resolve()
        receipt=CASE/"tests/logs"/(folder.name+".native_review.json")
        if not json.loads(receipt.read_text(encoding="utf8")).get("passed"): ap.error(f"Unreviewed run: {folder}")
        runs[label]=pilot(folder)
    page,_=load_pages(CACHE,PDF)
    if page.shape!=(1857,1361,3): raise ValueError("Reference page calibration differs")
    out.mkdir(parents=True)
    region_rows,pairs=[],[]
    with gzip.open(out/"matched_particle_fields.csv.gz","wt",encoding="utf8",newline="") as stream:
        samples=csv.writer(stream)
        samples.writerow(("run","field","nominal_tau_s","actual_tau_s","id","x_m","z_m","native_value",
                          "paper_range_equivalent_kPa_fig15_or_fig16a","paper_range_equivalent_kPa_fig16b"))
        for key in ("kappa","excess","p"):
            draw(out,key,runs,page,region_rows,pairs,samples)
    write_rows(out/"regional_fields.csv",region_rows)
    write_rows(out/"printed_pressure_comparison.csv",pairs)
    (out/"methods.txt").write_text(
        "Lian et al. (2023), doi:10.1016/j.cma.2023.115967, Fig. 15 and 16, printed page 21.\n"
        "Native values are raw particle values at their actual release-relative clocks. No spatial/time smoothing or fit.\n"
        "Fig. 15: left is the accumulated equivalent plastic strain (0–0.3, 0–1, 0–2 by row). The published "
        "inset and arrows remain visible; no reference strain values are inferred from them. Right: excess pressure "
        "(−10 to +10 kPa), compared with PorePress minus each particle's fixed PorePress0. The authors describe "
        "dilation-induced excess pressure; the exact choice of their reference pressure has not been recovered.\n"
        "Fig. 16: total PorePress (−10 to +20 kPa); the two printed columns are stabilized and non-stabilized.\n"
        "Raster-based pressure comparisons sample the nearest original 180 dpi pixel at each native center inside "
        "the printed body with a one-pixel eroded mask. The RGB Euclidean distance to the original colorbar must be ≤18 "
        "(8-bit RGB). Fig. 15 masks warm ink/annotations together with any indistinguishable warm pixels. Display-range "
        "absolute and signed differences compare clipped native pressure with nearest-palette kPa on this common subset; "
        "they are descriptive, omit unmatched soil, and do not represent pointwise errors against author-supplied data. "
        "Native regional statistics include unmodified out-of-range values. Region x limits use current coordinates; "
        "kappa>0.1 defines an active/deformed material subset rather than the exact shear-band boundary. The Fig. 15 "
        "negative reference band uses only matched printed cool pixels whose nearest color is below −2.5 kPa.\n",
        encoding="utf8")
    print(out)


if __name__=="__main__":
    main()
