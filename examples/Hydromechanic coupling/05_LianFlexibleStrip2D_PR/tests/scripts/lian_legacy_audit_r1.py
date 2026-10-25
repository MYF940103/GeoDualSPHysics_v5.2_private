"""Selected retained native frames only; no solver or historical file changes."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lian_release_r1 import CASE, TESTS, REPO, READER, native, bound, write_json

TAG='lian_legacy_audit_r1'


def main():
    receipt=TESTS/'logs'/(TAG+'.json');assert not receipt.exists()
    folder=CASE/'CaseLianFlexibleStrip2D_PR_out'
    initial=native(folder,0)
    indices={name:int(np.argmin((initial.x-x)**2+(initial.z-z)**2))
             for name,(x,z) in {'A':(.1,10),'B':(1.25,8.75)}.items()}
    evidence=[bound(__file__),bound(READER),bound(folder/'Run.out'),bound(folder/'data/Part_0000.bi4'),
              bound(REPO/'src/papers/u-pw/Lian 2023 u-pl.md')]
    rows=[]
    for part in [20,60,100,200,282,400,492,600,602,773,800,999]:
        a=native(folder,part)
        assert np.array_equal(a.id,initial.id) and np.isfinite(a.to_numpy()).all() and a.kplastic.eq(0).all()
        strip=a.x.between(0,1.25)&a.z.between(9.95,10.05)
        watch=a[a.id.eq(1744)].iloc[0]
        row=dict(part=part,time_s=float(a.time_s.iloc[0]),pressure_min_pa=a.pressure.min(),
                 pressure_max_pa=a.pressure.max(),pressure_mean_pa=a.pressure.mean(),
                 pressure_rms_pa=np.sqrt(np.mean(a.pressure**2)),vmax_m_s=np.linalg.norm(a[['vx','vy','vz']],axis=1).max(),
                 geometric_strip_count=int(strip.sum()),total_load_N_m=float(-(a.mass*a.load_az).sum()),
                 id1744_x_m=float(watch.x),id1744_z_m=float(watch.z),id1744_p_pa=float(watch.pressure),
                 stress_double=bool(a.stress_double.iloc[0]),position_double=bool(a.position_double.iloc[0]))
        for name,k in indices.items():
            row[name+'_native_id']=int(a.id.iloc[k]);row[name+'_pressure_pa']=float(a.pressure.iloc[k])
            row[name+'_settlement_mm']=1000*float(initial.z.iloc[k]-a.z.iloc[k])
        rows.append(row);evidence.append(bound(folder/'data'/f'Part_{part:04d}.bi4'))
    data=pd.DataFrame(rows)
    csv=TESTS/'figures'/(TAG+'.csv');data.to_csv(csv,index=False,float_format='%.17g')
    fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    for field,style in [('A_pressure_pa','-o'),('B_pressure_pa','--s')]:
        axes[0,0].plot(data.time_s,data[field]/1000,style,label=field.split('_')[0],ms=3)
    axes[0,0].set(ylabel='Native-point pore pressure (kPa)');axes[0,0].legend()
    axes[0,1].plot(data.time_s,data.pressure_mean_pa/1000,'o-',color='#215a8a');axes[0,1].set(ylabel='All-soil mean pore pressure (kPa)')
    axes[1,0].plot(data.time_s,data.id1744_x_m*1e6,'o-',color='#b56b28');axes[1,0].axhline(0,color='.4',lw=.8);axes[1,0].set(ylabel='Id 1744 x (micrometres)')
    axes[1,1].plot(data.time_s,data.geometric_strip_count,'o-',color='#215a8a');axes[1,1].set(ylabel='Current-coordinate strip nodes')
    for ax in axes.flat:ax.set(xlabel='Actual retained time (s)');ax.grid(alpha=.2)
    fig.suptitle('Retained float-stress Lian baseline - selected native frames, no new solve')
    png=TESTS/'figures'/(TAG+'.png');fig.savefig(png,dpi=160);plt.close(fig)
    result=dict(scope='Retained evidence audit only',native_soil_count=len(initial),probes={k:int(initial.id.iloc[v]) for k,v in indices.items()},
                all_selected_elastic=True,rows=rows,sources=evidence,artifacts=[bound(csv),bound(png)],
                limits=['Selected snapshots are not a dense history or new accuracy acceptance.',
                        'Old positions are float exports; sub-ULP material displacements cannot be recovered.',
                        'Paper section 4.3 reports complete dissipation at 100 s; retained output ends at 49.95001 s.',
                        'Native point B is the nearest available node, not an exact FEM point or interpolated paper curve.'])
    write_json(receipt,result);print(data.to_string(index=False))


if __name__=='__main__':main()
