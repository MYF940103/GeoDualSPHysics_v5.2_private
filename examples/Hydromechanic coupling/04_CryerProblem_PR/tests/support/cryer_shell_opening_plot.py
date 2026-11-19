"""All 160 early output-clock positions from matrix propagation, plus separate actual native points."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from cryer_shell_opening_channels import T,Q,DT,TR,N0,Phase

TAG="cryer_shell_opening_dense_r1"


def main():
    fig=T/"figures"/(TAG+".png");out=fig.with_suffix(".csv")
    if fig.exists() or out.exists():raise FileExistsError(fig)
    cdata=np.load(T/"figures/cryer_shell_closed_rows_r1.npz")
    obs=pd.read_csv(T/"figures/cryer_shell_ramp_open_r2_native.csv")
    contrib=pd.read_csv(T/"figures/cryer_shell_opening_channels_r1.csv")
    f,axs=plt.subplots(2,2,figsize=(11.8,7.5),layout="constrained")
    rows=[]
    for label,filename,color in [("original","cryer_coupled_shell_modes_r1_blocks","#a55316"),
                                 ("paired","cryer_shell_tet_pair_r1_sph","#12678e")]:
        b=np.load(T/"figures"/(filename+".npz"))
        c=Phase(b,cdata,label,N0/2e8,True);o=Phase(b,cdata,label,N0/2e8,False)
        y=np.zeros(len(c.f))
        for n in range(4096):y=c.advance(y,min(1.,n*DT/TR))
        y=y[:-1].copy();g=[]
        for i in range(161):
            if i:y=o.advance(y,1.)
            p=Q*o.pressure(y,1.)
            r=dict(operator=label,open_step=i,tau_us=1.e6*i*DT,
                center_Pa=p[0],shell17_Pa=p[16],shell18_Pa=p[17])
            rows.append(r);g.append(r)
        df=pd.DataFrame(g)
        for ax,col in zip(axs.flat,["center_Pa","shell17_Pa","shell18_Pa"]):
            ax.plot(df.tau_us,df[col]/1000,color=color,label=("Original SPH" if label=="original" else "Paired mechanics"))
    for ax,k,t in zip(axs.flat,["p1_Pa","p17_Pa","p18_Pa"],["Center region, r/a=0.05","Shell 17, r/a=0.85","Shell 18, r/a=0.90"]):
        for name,mark,color,legend in [("explicit_A","x","#14814c","Saved explicit"),("server_P3_B","o","black","Saved P3"),
                                       ("local_first_open_P3_B","o","black",None)]:
            d=obs[(obs.observation==name)&(obs.step_in_B_clock>=4096)&(obs.step_in_B_clock<=4256)]
            ax.scatter((d.step_in_B_clock-4096)*DT*1e6,d[k]/1000,marker=mark,color=color,s=25,label=legend,zorder=5)
        ax.set(xlabel="Time after drainage opens (µs)",ylabel="Pressure (kPa)",title=t);ax.grid(alpha=.2)
    axs[0,0].legend(fontsize=8)
    x=np.arange(4)
    ax=axs[1,1]
    for i,(name,color) in enumerate([("original","#a55316"),("paired","#12678e")]):
        sel=contrib[(contrib.operator==name)&(contrib.acceleration_space=="all_material_vectors")&
            (contrib.shell==1)&(contrib.step_after_open==64)].iloc[0]
        vals=[sel.inherited_closed_derivative_Pa,sel.removed_boundary_pressure_force_Pa,
              sel.removed_boundary_Darcy_pressure_Pa,sel.removed_boundary_Darcy_acceleration_Pa]
        ax.bar(x+(i-.5)*.36,np.array(vals)/1000,.36,color=color)
    ax.set_xticks(x,["Closed-state\nremainder","Mechanical\npressure force","Darcy\npressure","Darcy\nacceleration"])
    ax.set(ylabel="Center pressure increment (kPa)",title="Opening contributions at 122.07 µs")
    ax.axhline(0,color="black",lw=.7);ax.grid(axis="y",alpha=.2)
    pd.DataFrame(rows).to_csv(out,index=False);f.savefig(fig,dpi=160);plt.close(f)


if __name__=="__main__":main()
