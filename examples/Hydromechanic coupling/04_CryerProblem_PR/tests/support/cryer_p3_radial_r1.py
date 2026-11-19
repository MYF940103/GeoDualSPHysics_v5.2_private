"""Cryer material shells from the same checked native pass as the pressure history."""
import csv
from collections import defaultdict

import numpy as np

from cryer_p3_verify_r1 import need, T_D


class RadialPressure:
    """Assign material IDs to reference shells once; classify FS2/3 anew at each save."""
    radius = .05
    edges = np.linspace(0., 1., 11)

    def __init__(self, tv_rate):
        self.tv_rate = tv_rate
        self.frames = {}
        self.closed_pressure = None

    def set_materials(self, radius, volume):
        need(len(radius)==len(volume)==37173 and np.all(np.isfinite(radius))
             and np.all(radius>0) and np.all(volume>0) and np.all(np.isfinite(volume)), "radial material ledger")
        # Include roundoff-identical lattice radii on the upper edge of the inner bin.
        self.bins = np.searchsorted(self.edges[1:]+32*np.finfo(float).eps, radius/self.radius)
        need(self.bins.max()<len(self.edges)-1, "initial soil outside radial bins")
        self.volume = volume.copy()

    def observe(self,row,pressure,fs_type):
        if row["time_s"] < T_D:
            return
        p = np.asarray(pressure,dtype=float)
        if row["time_s"]==T_D:
            self.closed_pressure=p.copy()
        need(self.closed_pressure is not None,"missing closed tD material pressure")
        fs=np.isin(fs_type,(2,3))
        nb=len(self.edges)-1
        group=self.bins+nb*fs
        # Independent disjoint groups: free-surface labels can change after opening.
        def sums(values=None):
            return np.bincount(group,weights=values,minlength=2*nb).reshape(2,nb)
        counts=sums()
        volumes=sums(self.volume)
        numerators=sums(self.volume*p)
        delta=sums(self.volume*(p-self.closed_pressure))
        direct=float(np.average(p,weights=self.volume))
        reconstructed=float(numerators.sum()/volumes.sum())
        need(counts.sum()==37173 and counts[1].sum()==row["surface_count"] and
             row["active_drain_count"]==(counts[1].sum() if row["time_s"]>T_D else 0),
             "radial FS/soil population mismatch")
        need(abs(reconstructed-direct)<1e-7 and abs(np.mean(p)-row["mean_pressure_Pa"])<1e-7,
             "radial mean differs from original native pressure")
        shell_rows=[]
        for j,(lo,hi) in enumerate(zip(self.edges[:-1],self.edges[1:])):
            for name,groups in (("other_soil",[0]),("FS2or3",[1]),("all_soil",[0,1])):
                n=int(counts[groups,j].sum())
                v=float(volumes[groups,j].sum())
                shell_rows.append(dict(shell=j+1,r0_over_a_lower=lo,r0_over_a_upper=hi,
                    material_group=name,count=n,initial_volume_m3=v,
                    active_drained_count=int(counts[1,j]) if 1 in groups and row["time_s"]>T_D else 0,
                    pressure_V0mean_Pa=float(numerators[groups,j].sum()/v) if n else None,
                    pressure_minus_tD_same_ID_V0mean_Pa=float(delta[groups,j].sum()/v) if n else None))
        self.frames[row["part"]]=(row,shell_rows)

    def write(self,csv_path,plot_path):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        frames=[(part,row,row["tau_s"]*self.tv_rate) for part,(row,_) in self.frames.items()]
        need(len(frames)>=2 and frames[0][1]["time_s"]==T_D and
             all(a[1]["time_s"]<b[1]["time_s"] for a,b in zip(frames,frames[1:])),"radial frame order")
        labels=defaultdict(list)
        labels[frames[0][0]].append("closed_tD")
        labels[frames[1][0]].append("first_open_save")
        for target in (.01,.06,.2):
            if target<=frames[-1][2]:
                nearest=min(frames,key=lambda item:abs(item[2]-target))
                labels[nearest[0]].append("Fig7_Tv"+str(target))
        window=[f for f in frames if f[2]>=.005 and f[1]["tau_s"]<=.0625]
        if window:
            pos=max(range(len(window)),key=lambda i:window[i][1]["center18_Pa"])
            for index,name in ((pos-1,"before_sampled_peak"),(pos,"sampled_peak"),(pos+1,"after_sampled_peak")):
                if 0<=index<len(window):
                    labels[window[index][0]].append(name)
        records=[]
        fig,(profiles,opening)=plt.subplots(1,2,figsize=(11.6,4.8),layout="constrained")
        for part,row,tv in frames:
            if part not in labels:
                continue
            names="|".join(labels[part])
            shells=self.frames[part][1]
            records.extend(dict(part=part,completed_step=row["completed_step"],time_s=row["time_s"],
                                tau_s=row["tau_s"],legacy_Tv=tv,selection=names,**s) for s in shells)
            values=[s for s in shells if s["material_group"]=="all_soil"]
            x=[(s["r0_over_a_lower"]+s["r0_over_a_upper"])/2 for s in values]
            py=[s["pressure_V0mean_Pa"]/1000 if s["count"] else np.nan for s in values]
            # Adjacent peak saves accompany the sampled peak in the CSV. Showing all
            # three on top of each other hides the distinct drainage profiles.
            if any(label not in ("before_sampled_peak","after_sampled_peak") for label in labels[part]):
                if "closed_tD" in labels[part]:
                    label="Closed"
                elif "first_open_save" in labels[part]:
                    label="First open"
                elif "sampled_peak" in labels[part]:
                    label="Center peak"
                else:
                    label="Figure 7"
                profiles.plot(x,py,"o-",ms=3,lw=1.4,label=f"{label}, Tv={tv:.5g}")
            if "first_open_save" in labels[part]:
                for group,label,marker,color in (("other_soil","Other soil","o","#126f79"),
                        ("FS2or3","Drainage receivers (FS 2/3)","s","#ad502a")):
                    v=[s for s in shells if s["material_group"]==group and s["count"]]
                    opening.plot([(s["r0_over_a_lower"]+s["r0_over_a_upper"])/2 for s in v],
                                 [s["pressure_minus_tD_same_ID_V0mean_Pa"]/1000 for s in v],
                                 marker=marker,color=color,lw=1.4,ms=4,label=label)
                opening.set_title(f"First open save, τ = {row['tau_s']*1e6:.4g} µs")
        need(not csv_path.exists() and not plot_path.exists(),"preserve previous radial outputs")
        with csv_path.open("x",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=records[0])
            w.writeheader()
            w.writerows(records)
        profiles.set(title="All soil, volume-weighted shell pressure",ylabel="Pore pressure (kPa)")
        opening.set_ylabel("Change from closed tD, same material IDs (kPa)")
        opening.axhline(0,lw=.6,color=".45")
        for ax in (profiles,opening):
            ax.set(xlabel="Initial material radius r₀ / a",xlim=(0,1))
            ax.grid(alpha=.2)
            ax.legend(fontsize=8)
        fig.savefig(plot_path,dpi=190)
        plt.close(fig)
        return dict(selected_parts={str(k):v for k,v in sorted(labels.items())},
                    method="Ten initial r0/a shells (lo,hi], upper-edge tie within 32 binary64 eps; nominal a=.05 m; positive native initial material volume weight per ID. FS2or3 uses current saved FSType, active only at t>tD. Empty group has no mean.",
                    timing="legacy_Tv=(t-tD)*legacy_cv/a^2. Requested Figure 7 Tv uses the closest actual saved clock only when within covered Tv; no interpolation. Peak is the sampled maximum of the fixed 18 centers at Tv>=.005 and tau<=.0625 s; neighbors within that window in CSV.")
