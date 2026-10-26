"""Native release figures/CSVs. Paper-reference acceptance is a separate review."""
import argparse
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE/'tests/scripts'))
from lian_release_r1 import native, bound, write_json, utc
from lian_mirror_review_r1 import sample


def weights(initial, x, z):
    """Bilinear interpolation in the initial material grid, not current bins."""
    axes = []
    for col, target in [('x',x), ('z',z)]:
        values = np.unique(initial[col])
        exact = values[np.isclose(values,target,atol=1e-9,rtol=0)]
        if len(exact):
            axes.append([(exact[0],1.)])
        else:
            lo, hi = values[values<target][-1], values[values>target][0]
            axes.append([(lo,(hi-target)/(hi-lo)),(hi,(target-lo)/(hi-lo))])
    result = []
    for xv, wx in axes[0]:
        for zv, wz in axes[1]:
            indices = np.flatnonzero(initial.x.eq(xv)&initial.z.eq(zv))
            assert len(indices) == 1
            result.append((int(indices[0]),float(wx*wz)))
    assert abs(sum(w for _,w in result)-1) < 1e-12
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, required=True)
    parser.add_argument('--tag', default='lian_release100_r1')
    args = parser.parse_args()
    folder = args.folder.resolve()
    out = CASE/'figures'
    out.mkdir(exist_ok=True)
    receipt = out/(args.tag+'.check.json')
    assert not receipt.exists(), 'Retained analysis is never overwritten'
    parts = sorted((folder/'data').glob('Part_*.bi4'))
    assert len(parts) == 2001, len(parts)
    initial = native(folder,0)
    probes = {'A':weights(initial,0.,10.),'B':weights(initial,1.25,8.75)}
    probe_info = {k:[dict(native_id=int(initial.id.iloc[i]),x0_m=float(initial.x.iloc[i]),
        z0_m=float(initial.z.iloc[i]),weight=w) for i,w in v] for k,v in probes.items()}
    rows, snapshots, outputs = [], {}, []
    sources = [bound(p) for p in [__file__, CASE/'tests/scripts/lian_release_r1.py',
        CASE/'tests/scripts/lian_mirror_review_r1.py', folder/'Run.out']]
    for i in range(2001):
        a = native(folder,i)
        row = sample(a,initial,1e-5,True)
        # Diagnostic nearest-node A/B values from sample() are replaced here by
        # paper Fig9 targets: A(0,10), B(1.25,8.75), tracked by initial native IDs.
        for key, stencil in probes.items():
            row[key+'_pressure_pa'] = sum(w*float(a.pressure.iloc[k]) for k,w in stencil)
            row[key+'_settlement_mm'] = 1000*sum(w*float(initial.z.iloc[k]-a.z.iloc[k]) for k,w in stencil)
            row[key+'_ux_mm'] = 1000*sum(w*float(a.x.iloc[k]-initial.x.iloc[k]) for k,w in stencil)
            row.pop(key+'_id')
        row.update(part=i,step=int(a.saved_step.iloc[0]))
        rows.append(row)
        if i in [10,20,60,300,1000,2000]:
            snapshots[i] = a
        if i%100 == 0:
            print('Formal native analysis',i,'/',2000,flush=True)
    assert abs(rows[-1]['time_s']-100) < 2e-5

    def csv(name, frame):
        path = out/(args.tag+'_'+name+'.csv')
        assert not path.exists()
        frame.to_csv(path,index=False,float_format='%.17g')
        outputs.append(bound(path))

    def png(name, fig):
        path = out/(args.tag+'_'+name+'.png')
        assert not path.exists()
        fig.savefig(path,dpi=180)
        plt.close(fig)
        outputs.append(bound(path))

    history = pd.DataFrame(rows)
    csv('history',history)
    fig, axes = plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for point,color,line in [('A','#215a8a','-'),('B','#b56b28','--')]:
        for ax,col,label,scale in [(axes[0,0],'pressure_pa','Pore pressure (kPa)',.001),
            (axes[0,1],'settlement_mm','Material settlement (mm)',1)]:
            nonzero=history.time_s.gt(0)
            ax.semilogx(history.time_s[nonzero],history.loc[nonzero,point+'_'+col]*scale,
                line,color=color,label=point)
            ax.set(xlabel='Actual saved time (s)',ylabel=label,xlim=(.05,100),xticks=[.05,.1,1,10,100])
            ax.grid(alpha=.2);ax.legend()
    axes[1,0].plot(history.time_s,history.force_N_m/1000,color='#215a8a')
    axes[1,0].set(xlabel='Actual saved time (s)',ylabel='Actual applied force (kN/m)',xlim=(0,100))
    axes[1,1].plot(history.time_s,history.pressure_mean_pa/1000,color='#215a8a')
    axes[1,1].set(xlabel='Actual saved time (s)',ylabel='Soil mean pressure (kPa)',xlim=(0,100))
    for ax in axes[1]:
        ax.set_xticks([0,25,50,75,100]);ax.grid(alpha=.2)
    fig.suptitle('Lian actual formal 100-s run: paper-position material probes\nNative histories only; SPH/FEM reference comparison remains independently reviewed')
    png('history',fig)
    fig,axes=plt.subplots(2,3,figsize=(14,8),layout='constrained')
    maximum=max(float(a.pressure.max()) for a in snapshots.values())/1000
    for ax,(i,a) in zip(axes.flat,snapshots.items()):
        contour=ax.tricontourf(initial.x,initial.z,a.pressure/1000,
            levels=np.linspace(0,max(maximum,1e-9),25),cmap='viridis',extend='both')
        ax.set(title=f'Actual t={a.time_s.iloc[0]:.6f} s',xlabel='Initial material x (m)',
            ylabel='Initial material z (m)',aspect='equal')
        csv(f'field_{i:04d}',pd.DataFrame(dict(id=initial.id,x0_m=initial.x,z0_m=initial.z,
            pressure_pa=a.pressure,sigma_zz_pa=a.sigma_zz,settlement_mm=1000*(initial.z-a.z),
            ux_mm=1000*(a.x-initial.x))))
    fig.colorbar(contour,ax=axes.ravel().tolist(),label='Pore pressure (kPa)',shrink=.8)
    fig.suptitle('Native pore-pressure development/decay; common color scale')
    png('profiles',fig)
    final=snapshots[2000]
    profile=[]
    for z in np.unique(initial.z):
        stencil=weights(initial,1.25,z)
        profile.append(dict(z0_m=float(z),ux_mm=1000*sum(w*float(final.x.iloc[k]-initial.x.iloc[k]) for k,w in stencil)))
    profile=pd.DataFrame(profile)
    csv('horizontal_profile',profile)
    fig,ax=plt.subplots(figsize=(5,6),layout='constrained')
    ax.plot(profile.ux_mm,profile.z0_m,color='#215a8a')
    ax.set(xlabel='Horizontal material displacement (mm)',ylabel='Initial elevation (m)',
        title='Section x0=1.25 m at actual final time')
    ax.grid(alpha=.2);png('horizontal_profile',fig)
    write_json(receipt,dict(passed=True,physical_reference_accepted=False,visual_review_passed=False,
        utc=utc(),actual_final_time_s=rows[-1]['time_s'],saved_frames=len(parts),paper_probes=probe_info,
        sources=sources,artifacts=outputs,limits=[
            'No digitized SPH/FEM reference is silently substituted by an analytical solution.',
            'Original 13-node load/1.3-m quadrature remains +4% versus the ideal 1.25-m strip.',
            'Only 15-s independent half-step evidence exists, not a full-cycle half test.',
            'Stress double, pore pressure/rate float; SPR/HG/stress-gradient correction off.']))


if __name__=='__main__':
    main()
