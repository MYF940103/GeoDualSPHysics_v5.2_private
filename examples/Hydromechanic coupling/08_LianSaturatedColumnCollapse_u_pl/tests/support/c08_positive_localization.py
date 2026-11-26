"""Read retained C08 frames and measure recent plastic strain across local shear-band normals."""
import argparse
import csv
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np

from c08_positive_suction_sites import DP, RUNS, checked
from c08_psi25_tpi_native import TESTS, require

OUT = TESTS/"figures/c08_positive_localization"
TIMES = (.30,.60,.88,1.20)
HEIGHTS = (.48,.80,1.12)
LOOKBACK = .04
HALF_TANGENT = .12
HALF_NORMAL = (.28,.40)
BIN = .04


def quantiles(x, weight, probabilities):
    keep = weight>0.
    require(keep.any(), "No positive weights in section")
    x,weight = x[keep],weight[keep]
    order = np.argsort(x,kind="stable")
    x,weight = x[order],weight[order]
    midpoint = np.cumsum(weight)-weight/2
    return np.interp(probabilities,midpoint/weight.sum(),x)


def centerline(pos, rate, volume, z0):
    """Choose the local recent-strain ridge without using pore pressure."""
    zs, xs = [], []
    for z in z0 + np.arange(-2,3)*.04:
        ids = np.flatnonzero((abs(pos[:,1]-z)<.025) & (pos[:,0]>2.50) & (rate>0))
        require(len(ids)>=3, f"No supported active profile at z={z:.3f} m")
        i = ids[np.argmax(rate[ids])]
        near = ids[(abs(pos[ids,0]-pos[i,0])<=.11)&(rate[ids]>=.80*rate[i])]
        weights = volume[near]*rate[near]
        zs.append(float(np.average(pos[near,1],weights=weights)))
        xs.append(float(np.average(pos[near,0],weights=weights)))
    slope, x0 = np.polyfit(np.array(zs)-z0,xs,1)
    misfit = np.sqrt(np.mean(np.square(np.array(xs)-x0-slope*(np.array(zs)-z0))))
    tangent = np.array([slope,1.])/np.hypot(slope,1.)
    normal = np.array([tangent[1],-tangent[0]])
    return np.array([x0,z0]), tangent, normal, misfit, zs, xs


def measure(pos, volume, rate, kappa, pressure, ptype, z0, tau, prev_tau):
    origin,tangent,normal,misfit,zs,xs = centerline(pos,rate,volume,z0)
    along = (pos-origin)@tangent
    offset = (pos-origin)@normal
    slot = abs(along)<=HALF_TANGENT
    sec = dict(tau_s=tau, previous_tau_s=prev_tau, z_m=z0, center_x_m=origin[0],
               normal_x=normal[0],normal_z=normal[1],ridge_fit_rms_m=misfit,
               ridge_fit_residual_dp=misfit/DP,tangent_span_m=2*HALF_TANGENT,
               ridge_centroid_x=";".join(f"{x:.8g}" for x in xs),
               ridge_centroid_z=";".join(f"{z:.8g}" for z in zs))
    for radius,tag in zip(HALF_NORMAL,("028","040")):
        selected=slot & (abs(offset)<=radius)
        d, v, r, k, p = (x[selected] for x in (offset,volume,rate,kappa,pressure))
        lo,hi = quantiles(d,v*r,[.10,.90])
        old_lo,old_hi = quantiles(d,v*k,[.10,.90])
        deficit = np.maximum(-5-p,0.)
        deep = p < -5
        p_lo,p_hi = quantiles(d,v*deficit,[.10,.90]) if deep.any() else (np.nan,np.nan)
        inside = (d>=lo)&(d<=hi)
        for name,value in {
            "count":len(p),"surface_known_count":int(np.isin(ptype[selected],[2,3]).sum()),
            "min_s_m":d.min(),"max_s_m":d.max(),
            "recent_q10_m":lo,"recent_q90_m":hi,"recent_w80_m":hi-lo,
            "recent_w80_dp":(hi-lo)/DP,
            "cumulative_w80_m":old_hi-old_lo,"suction_w80_m":p_hi-p_lo,
            "suction_median_s_m":quantiles(d,v*deficit,[.5])[0] if deep.any() else np.nan,
            "p_below_minus5_area_fraction":v[deep].sum()/v.sum(),
            "suction_weight_in_recent_w80":(v[inside]*deficit[inside]).sum()/(v*deficit).sum() if deep.any() else np.nan,
            "peak_recent_s_inv":r.max(),"average_recent_s_inv":np.average(r,weights=v),
            "min_p_kPa":p.min(),
            "area_weight_covered_m2":v.sum(),
        }.items():
            sec[f"{name}_{tag}"]=value
    radii=np.arange(-.40,.40+BIN/2,BIN)
    profiles=[]
    for left,right in zip(radii[:-1],radii[1:]):
        selected = slot & (offset>=left) & (offset<right)
        weights = volume[selected]
        def mean(x):
            return np.average(x[selected],weights=weights) if len(weights) else np.nan
        profiles.append(dict(tau_s=tau,z_m=z0,distance_left_m=left,distance_right_m=right,
            distance_m=(left+right)/2,particles=len(weights),area_m2=weights.sum(),
            mean_recent_kappa_rate_s_inv=mean(rate),mean_cumulative_kappa=mean(kappa),
            mean_p_kPa=mean(pressure)))
    return sec, profiles,origin,normal


def plot(frames,sections,profiles):
    fig,axes=plt.subplots(2,4,figsize=(14,7),layout="constrained",
                          gridspec_kw=dict(height_ratios=(1.45,1.)))
    section_colors=("#11704b","#242b2c","#8663a0")
    for i,(tau,prev_tau,pos,vol,rate,kap,pressure,ptype) in enumerate(frames):
        ax=axes[0,i]
        values = np.maximum(rate,.001)
        artist=ax.scatter(*pos.T,c=values,cmap="magma",norm=LogNorm(.001,2.5),s=4,linewidths=0)
        for color, (row,origin,normal) in zip(section_colors,sections[i]):
            ends=np.array([origin-HALF_NORMAL[-1]*normal,origin+HALF_NORMAL[-1]*normal])
            ax.plot(*ends.T,color="white",lw=2.5)
            ax.plot(*ends.T,color=color,lw=1.4)
            ax.scatter(*origin,color=color,edgecolors="white",s=18,zorder=5)
        ax.set(xlim=(2.5,4.45),ylim=(-.03,2.03),aspect="equal",title=f"{tau:.2f} s",
               xlabel="x (m)")
        if i==0:
            ax.set_ylabel("z (m)")
        ax=axes[1,i]
        right=ax.twinx()
        section=sections[i][1][0]
        table = [row for row in profiles[i] if row["z_m"]==HEIGHTS[1]]
        n=np.array([row["distance_m"] for row in table])
        activity=[row["mean_recent_kappa_rate_s_inv"] for row in table]
        p=[row["mean_p_kPa"] for row in table]
        ax.axvspan(section["recent_q10_m_040"],section["recent_q90_m_040"],color="#e3ad71",alpha=.25)
        ax.plot(n,activity,"o-",markersize=2.7,lw=1.3,color="#ad4c20")
        right.plot(n,p,"s-",markersize=2.4,lw=1,color="#1e5c8a")
        ax.axvline(0,color="0.55",lw=.7,ls=":")
        ax.set(xlim=(-.4,.4),xlabel="Distance along normal (m)",
               title=f"z = 0.80 m  |  width {section['recent_w80_m_040']:.2f} m",ylim=(0,1.50))
        right.set(ylim=(-29,12))
        if i==0:
            ax.set_ylabel("Mean recent Δκ/Δt (s⁻¹)",color="#ad4c20")
        if i==3:
            right.set_ylabel("Mean gauge pressure (kPa)",color="#1e5c8a")
        ax.tick_params(axis="y",labelcolor="#ad4c20")
        right.tick_params(axis="y",labelcolor="#1e5c8a")
        ax.grid(axis="y",alpha=.18)
    fig.colorbar(artist,ax=axes[0,:],shrink=.87,label="Recent Δκ/Δt (s⁻¹)",extend="both")
    fig.suptitle("C08 +2.5°  |  Plastic localization after wall removal",fontsize=15)
    path=OUT/"sections.png"
    require(not path.exists(),"Existing figure")
    fig.savefig(path,dpi=170)
    plt.close(fig)


def main():
    tag=RUNS["beta004"]
    receipt=json.loads((TESTS/"logs"/f"{tag}.native_review.json").read_text(encoding="utf8"))
    require(receipt["passed"] and receipt["tag"]==tag and receipt["frames"]==132,"Native source")
    def read(t):
        f=TESTS/"outputs"/tag/"data"/f"Part_{round(100*t)+12:04d}.bi4"
        meta,arrays,_=checked(f,receipt)
        tau=meta["TimeStep"]-receipt["release_time_s"]
        require(abs(tau-t)<1e-9,"Wrong actual clock")
        return tau, {key:v[-5000:] for key,v in arrays.items()}
    frames, per_frame, all_profiles, extent = [],[],[],[]
    for t in TIMES:
        tau, a = read(t)
        prev_tau,b = read(t-LOOKBACK)
        require(np.array_equal(a["Idp"],b["Idp"]),"Native material IDs differ")
        pos=a["Posd"][:,[0,2]]
        volume=a["PoroCurrentVolume"]
        kappa=a["Kplastic"].astype(float)
        delta=kappa-b["Kplastic"]
        pressure=a["PorePress"].astype(float)/1000
        ptype=a["FSType"]
        require((volume>0).all() and (delta>=0).all() and abs(tau-prev_tau-LOOKBACK)<1e-9,
                "Native volume, plastic history, or comparison times changed")
        rate=delta/(tau-prev_tau)
        frames.append((tau,prev_tau,pos,volume,rate,kappa,pressure,ptype))
        terms=(pos,volume,rate,kappa,pressure,ptype)
        cuts=[measure(*terms,z,tau,prev_tau) for z in HEIGHTS]
        per_frame.append([(row,origin,normal) for row,profile,origin,normal in cuts])
        all_profiles.append([p for row,profile,origin,normal in cuts for p in profile])
        strong=rate>=.20
        deep=pressure < -5
        mass=volume*rate
        order=np.argsort(-rate,kind="stable")
        threshold=np.searchsorted(np.cumsum(volume[order]),.1*volume.sum())+1
        most_active=order[:threshold]
        extent.append(dict(tau_s=tau,previous_tau_s=prev_tau,front_center_x_m=pos[:,0].max(),
            rate_max_s_inv=rate.max(),rate_p95_s_inv=quantiles(rate,volume,[.95])[0],
            area_rate_ge_point20_pct=100*volume[strong].sum()/volume.sum(),
            area_p_below_minus5_pct=100*volume[deep].sum()/volume.sum(),
            area_both_pct=100*volume[strong&deep].sum()/volume.sum(),
            recent_activity_in_p_below_minus5_pct=100*mass[deep].sum()/mass.sum(),
            recent_activity_in_top_area_decile_pct=100*mass[most_active].sum()/mass.sum(),
            observed_top_decile_area_pct=100*volume[most_active].sum()/volume.sum()))
    OUT.mkdir(exist_ok=True)
    for name,rows in (("sections.csv",[x[0] for frame in per_frame for x in frame]),
                      ("profiles.csv",[x for frame in all_profiles for x in frame]),("extent.csv",extent)):
        with (OUT/name).open("x",newline="",encoding="utf8") as stream:
            writer=csv.DictWriter(stream,fieldnames=rows[0])
            writer.writeheader()
            writer.writerows(rows)
    plot(frames,per_frame,all_profiles)


def fixture():
    """Gaussian band with a known normal and central 80 percent width."""
    z0=.80
    center=np.array([3.50,z0])
    t=np.array([-.5,1.])/np.hypot(.5,1.)
    n=np.array([t[1],-t[0]])
    s,d=np.meshgrid(np.arange(-.5,.501,.01),np.arange(-.5,.501,.01))
    pos=center+s.ravel()[:,None]*t+d.ravel()[:,None]*n
    rate=np.exp(-.5*(d.ravel()/.08)**2)
    vol=np.full(len(rate),.0001)
    pressure=-1-9*rate
    row,*_=measure(pos,vol,rate,rate,pressure,np.zeros(len(rate)),z0,1.,.96)
    recovered=np.array([row["normal_x"],row["normal_z"]])
    require(np.linalg.norm(recovered-n)<.02 and abs(row["center_x_m"]-center[0])<.005,
            "Incorrect known ridge orientation")
    require(abs(row["recent_w80_m_040"]-2*1.2815515655*.08)<.007,
            "Incorrect known Gaussian width")
    print("Manufactured rotated Gaussian band agrees with its analytic normal and 80% width.")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-only",action="store_true")
    args=parser.parse_args()
    fixture()
    if not args.fixture_only:
        main()
