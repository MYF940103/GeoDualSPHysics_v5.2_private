"""Area-weighted gauge pressure for the whole published and simulated bodies, independently."""
import csv
import json
import argparse

import numpy as np
from scipy.ndimage import binary_erosion
from scipy.spatial import cKDTree

from c08_positive_suction_sites import OUT, RUNS, checked
from c08_psi25_tpi_fields import CACHE, FIG16_TIMES, PDF, load_pages, palette_limits, paper_panels
from c08_psi25_tpi_native import SOIL_IDS, TESTS, require
from c08_psi25_suction_stencil import V0


def quantile(values, weights, q):
    order = np.argsort(values, kind="stable")
    centers = np.cumsum(weights[order])
    return values[order[np.searchsorted(centers,q*centers[-1])]]


def measure(p, area, lower_edge, next_bin):
    negative = p<0
    total = area.sum()
    def pct(mask):
        return 100*area[mask].sum()/total
    return dict(n=len(p),analyzed_area_m2=total,min_kPa=p.min(),
        p01_kPa=quantile(p,area,.01),p05_kPa=quantile(p,area,.05),
        p50_kPa=quantile(p,area,.5),negative_area_pct=pct(negative),
        negative_only_p05_kPa=quantile(p[negative],area[negative],.05) if negative.any() else "",
        negative_only_p50_kPa=quantile(p[negative],area[negative],.50) if negative.any() else "",
        below_minus5_area_pct=pct(p < -5),floor_color_or_raw_at_or_below_pct=pct(p<=lower_edge),
        lowest_two_colors_or_equivalent_pct=pct(p<=next_bin))


def main():
    tag=RUNS["beta004"]
    receipt=json.loads((TESTS/"logs"/(tag+".native_review.json")).read_text(encoding="utf8"))
    require(receipt["passed"] and receipt["tag"]==tag and receipt["frames"]==132,"Native source")
    page,_=load_pages(CACHE,PDF)
    rows=[]
    for t in FIG16_TIMES:
        palette,lo,hi=palette_limits(page,"p",t)
        require((lo,hi)==(-10,20) and len(palette)==166,"Original gauge-pressure scale")
        increment=(hi-lo)/(len(palette)-1)
        label,rgba,extent=paper_panels(page,"p",t)[0]
        require("(a)" in label,"Stabilized panel")
        mask=rgba[:,:,3]>0
        h,w=mask.shape
        xmin,xmax,zmin,zmax=extent
        pixel_area=(xmax-xmin)*(zmax-zmin)/(w*h)
        distance,idx=cKDTree(palette.astype(float)).query(rgba[:,:,:3].astype(float).reshape(-1,3))
        dist,index=distance.reshape(h,w),idx.reshape(h,w)
        interior=binary_erosion(mask,structure=np.ones((3,3),bool))
        valid=interior & (dist<=18)
        values=lo+index[valid]*increment
        two=binary_erosion(interior,structure=np.ones((3,3),bool)) & (dist<=18)
        rows.append(dict(source="Lian Fig16a printed",nominal_tau_s=t,actual_tau_s="",
            body_pixels=int(mask.sum()),interior_pixels=int(interior.sum()),
            interior_rgb_coverage_pct=100*valid.sum()/interior.sum(),
            fraction_body_retained_pct=100*valid.sum()/mask.sum(),
            erode_2px_negative_pct=100*np.mean((lo+index[two]*increment)<0),
            **measure(values,np.full(len(values),pixel_area),lo,lo+increment)))
        part=round(100*t)+12
        m,a,_=checked(TESTS/"outputs"/tag/"data"/f"Part_{part:04d}.bi4",receipt)
        tau=m["TimeStep"]-receipt["release_time_s"]
        soil=np.isin(a["Idp"],SOIL_IDS)
        require(np.array_equal(a["Idp"][soil],SOIL_IDS) and abs(tau-t)<1e-9,"Actual solid IDs and time")
        area=V0*a["PoroVolumeRatio"][soil]
        require(np.allclose(area,a["PoroCurrentVolume"][soil],rtol=1e-8,atol=0),"Unit thickness areas")
        p=a["PorePress"][soil].astype(float)/1000
        rows.append(dict(source="C08 TPI beta=.04",nominal_tau_s=t,actual_tau_s=tau,
            body_pixels="",interior_pixels="",interior_rgb_coverage_pct="",fraction_body_retained_pct="",
            erode_2px_negative_pct="",**measure(p,area,lo,lo+increment)))
    with (OUT/"fig16_pressure_area.csv").open("x",encoding="utf8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


def plot_area():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with (OUT/"fig16_pressure_area.csv").open(encoding="utf8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    path = OUT/"fig16_pressure_area.png"
    require(not path.exists(), "Retained pressure comparison figure exists")
    times = (.01, .5, 1.2)
    series = (("Lian Fig16a printed", "Lian 2023, Fig. 16(a)", "#aa582d"),
              ("C08 TPI beta=.04", "C08, β = 0.04", "#246482"))
    fig, axes = plt.subplots(1, 2, figsize=(10.3, 4.25))
    fig.subplots_adjust(left=.088, right=.98, bottom=.19, top=.75, wspace=.30)
    for ax, key, title, unit, ylim in zip(
            axes, ("below_minus5_area_pct", "p05_kPa"),
            ("Soil area with pressure below −5 kPa", "Area-weighted 5th percentile"),
            ("Soil area (%)", "Gauge pore pressure (kPa)"), ((0,28),(-18,3.3))):
        for i,(source, label, color) in enumerate(series):
            values = [r for r in rows if r["source"]==source]
            require(tuple(float(r["nominal_tau_s"]) for r in values)==times, "Pressure plot clocks")
            y = [float(r[key]) for r in values]
            bars = ax.bar(np.arange(3)+(i-.5)*.34, y, width=.31, color=color, label=label)
            ax.bar_label(bars, labels=[f"{v:.2f}" if v else "0" for v in y], padding=3, fontsize=9)
        ax.axhline(0, linewidth=.7, color="#505050")
        ax.set_axisbelow(True)
        ax.grid(axis="y", color="#dedede", linewidth=.6)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set(title=title, ylabel=unit, ylim=ylim, xlabel="Time after wall removal (s)")
        ax.set_xticks(np.arange(3), ["0.01", "0.50", "1.20"])
    fig.suptitle("Positive-dilatancy column collapse (+2.5°)", fontsize=16, y=.98)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center",
               bbox_to_anchor=(.5,.90), ncol=2, frameon=False)
    fig.savefig(path, dpi=190)
    plt.close(fig)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figure-from-csv", action="store_true")
    if parser.parse_args().figure_from_csv:
        plot_area()
    else:
        main()
        plot_area()
