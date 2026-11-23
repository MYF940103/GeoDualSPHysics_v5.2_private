"""Use native soil positions and total pressures for the C08 release-field comparison."""
import csv
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm, Normalize

from c08_m0_release_short_review_r1 import read
from c08_m0_release_mature_review_r1 import gpu, TAG, OPEN, soils
from c08_m0_beta_compare import equal


def main():
    subjects=[TAG+"_w03_"+s for s in ("b0","b004")]
    for s in subjects:
        assert (gpu.T/"logs"/(s+".review.json")).is_file()
    times=[(OPEN+8,0.04),(OPEN+200,1),(OPEN+1000,5),(OPEN+6000,30)]
    samples=[]
    for subject in subjects:
        table=gpu.T/"figures"/(subject+".csv")
        with table.open(newline="") as f:
            index={int(r["step"]):i for i,r in enumerate(csv.DictReader(f),1)}
        fields=[]
        for step,_ in times:
            _,p=read(gpu.T/"outputs"/subject/"data",index[step])
            fields.append(soils(p["arrays"]))
        samples.append(fields)
    extrema=[[v["PorePress"].astype(float)*.001 for v in row] for row in samples]
    low=min(x.min() for row in extrema for x in row);high=max(x.max() for row in extrema for x in row)
    norm=TwoSlopeNorm(vmin=low,vcenter=0.,vmax=high)
    difference=[on-off for off,on in zip(*extrema)]
    dmax=max(np.abs(v).max() for v in difference)
    dnorm=Normalize(-dmax,dmax)
    fig,axes=plt.subplots(3,4,figsize=(14,6.5),sharex=True,sharey=True,layout="constrained")
    sid=samples[0][0]["Idp"]
    measurements=[]
    for col,(step,ms) in enumerate(times):
        axes[0,col].set_title("τ = {:g} ms".format(ms))
        for row in (0,1,2):
            a=samples[min(1,row)][col]
            assert equal(a["Idp"],sid)
            pos=a["Posd"][:,[0,2]]
            field=extrema[row][col] if row<2 else difference[col]
            ax=axes[row,col]
            handle=ax.scatter(pos[:,0],pos[:,1],c=field,s=3,marker="s",linewidths=0,cmap="RdBu_r",norm=norm if row<2 else dnorm)
            if row==1:handle_pressure=handle
            ax.set_aspect("equal",adjustable="box")
            ax.set(xlim=(-.03,4.06),ylim=(-.03,2.04))
            if row==2:ax.set_xlabel("x (m)")
            if col==0:ax.set_ylabel(["β = 0\nz (m)","β = 0.04\nz (m)","β0.04 − β0\nz (m)"][row])
            if row<2:
                j=int(np.argmin(field))
                neg=field<0
                near=pos[:,0]>4.-.144
                fs=np.isin(a["FSType"],(2,3))
                measurements.append(dict(step=step,release_ms=ms,beta=(0.04 if row else 0),soil_count=len(field),
                    min_pressure_kPa=field[j],min_original_id=int(sid[j]),x_min_m=pos[j,0],z_min_m=pos[j,1],
                    neg_all=int(neg.sum()),neg_fs=int((neg&fs).sum()),neg_within_2H_of_original_right_wall=int((neg&near).sum()),
                    mean_negative_part_all_soil_kPa=np.minimum(field,0).mean(),max_pressure_kPa=field.max(),
                    max_abs_difference_kPa=np.abs(difference[col]).max()))
    fig.colorbar(handle_pressure,ax=axes[:2,:],label="Total pore pressure (kPa)",shrink=.92)
    fig.colorbar(handle,ax=axes[2,:],label="Difference (kPa)",shrink=.92)
    fig.suptitle("C08 ψ = 0° · original material particles after release · AS and NoPen off")
    stem=TAG+"_w03_fields"
    plot=gpu.T/"figures"/(stem+".png");table=gpu.T/"figures"/(stem+".csv")
    assert not table.exists() and not plot.exists()
    with table.open("x",newline="") as f:
        w=csv.DictWriter(f,fieldnames=measurements[0]);w.writeheader();w.writerows(measurements)
    fig.savefig(plot,dpi=175)
    plt.close(fig)
    print(plot)


if __name__=="__main__":main()
