"""Straight-sided original-material map diagnostics; not an SPH volume or mesh gate."""
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import TwoSlopeNorm
import c08_h18_compare_r2 as core
from c08_h18_centroid_partial_review_r1 import mapped

T = core.T
TAG = 'c08_h18_material_map_r1'
CASES = [('AS05_n255','c08_h18_as05_n255_r1','native_r1',91),
         ('AS05_n3825','c08_h18_wend_psi0_a05_w09_r1','native_r1',91),
         ('AS07_n255_FAILED','c08_h18_a07_n255_r1','native_partial_r1',33)]


def cross(a,b):return a[...,0]*b[...,1]-a[...,1]*b[...,0]


def measures(x, cells, area0):
    p=x[cells]
    e=np.roll(p,-1,axis=1)-p
    turn=cross(e,np.roll(e,-1,axis=1))
    local=p-p[:,:1]
    area=.5*np.sum(cross(local,np.roll(local,-1,axis=1)),axis=1)
    tri1=.5*cross(p[:,1]-p[:,0],p[:,2]-p[:,0])
    tri2=.5*cross(p[:,2]-p[:,0],p[:,3]-p[:,0])
    def intersects(a,b,c,d):
        return (cross(b-a,c-a)*cross(b-a,d-a)<0)&(cross(d-c,a-c)*cross(d-c,b-c)<0)
    bow=intersects(p[:,0],p[:,1],p[:,2],p[:,3])|intersects(p[:,1],p[:,2],p[:,3],p[:,0])
    return area/area0,(tri1<=0)|(tri2<=0),(turn.min(axis=1)<0)&(turn.max(axis=1)>0),bow,p


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true')
    assert p.parse_args().execution_authorized
    check=T/'logs'/(TAG+'.check.json');prefix=T/'figures'/TAG
    assert not check.exists() and not list(prefix.parent.glob(TAG+'*'))
    source=T/'outputs/c08_h18_wend_psi0_pre_r2/native_r1'
    roots=[T/'outputs'/tag/native for _,tag,native,_ in CASES]
    files=[Path(__file__),source/'completion.json',source/'typed22.bin']
    files += [r/q for r in roots for q in ('completion.json','typed22.bin','clocks.csv')]
    before=[core.stat(q) for q in files]
    pre=mapped(source,7060,1001)
    initial=np.array(pre[0]['Posd'][2060:][:,(0,2)])
    assert np.array_equal(pre[0]['Idp'][:,0],np.arange(7060))
    xs,zs=np.unique(initial[:,0]),np.unique(initial[:,1])
    assert len(xs)==100 and len(zs)==50
    ix,iz=np.searchsorted(xs,initial[:,0]),np.searchsorted(zs,initial[:,1])
    grid=np.full((50,100),-1,dtype=int)
    for node,(x,z) in enumerate(zip(ix,iz)):
        assert grid[z,x]==-1;grid[z,x]=node
    assert (grid>=0).all()
    cells=np.stack((grid[:-1,:-1],grid[:-1,1:],grid[1:,1:],grid[1:,:-1]),axis=-1).reshape(-1,4)
    p0=initial[cells];local0=p0-p0[:,:1]
    area0=.5*np.sum(cross(local0,np.roll(local0,-1,axis=1)),axis=1)
    assert len(cells)==4851 and (area0>0).all() and np.allclose(area0,.04**2,rtol=0,atol=1e-15)
    reference_time=float(pre[-1]['time']);rows=[];critical=[];snapshots={}
    expected=np.r_[np.arange(1805),np.arange(2060,7060)]
    for (label,tag,_,count),root in zip(CASES,roots):
        done=core.read(root/'completion.json')
        assert done['samples']==count and (done.get('saved_prefix_native_passed',False) if count==33 else done['passed'])
        frames=mapped(root,6805,count);clock=core.table(root/'clocks.csv');assert len(clock)==count
        for part,f in enumerate(frames):
            assert np.array_equal(f['Idp'][:,0],expected) and float(f['time'])==float(clock[part]['time_s'])
            x=f['Posd'][1805:][:,(0,2)];j=f['PoroVolumeRatio'][1805:,0]
            ratio,tri,mixed,bow,poly=measures(x,cells,area0);meanj=np.mean(j[cells],axis=1)
            at=int(ratio.argmin())
            row=dict(case=label,part=part,time_s=float(f['time']),tau_s=float(f['time'])-reference_time,
                min_area_ratio=float(ratio.min()),max_area_ratio=float(ratio.max()),nonpositive_area_cells=int((ratio<=0).sum()),
                chosen_diagonal_triangle_reversal=int(tri.sum()),mixed_turn_cells=int(mixed.sum()),self_cross_cells=int(bow.sum()),
                area_minus_meanJ_RMS=float(np.sqrt(np.mean((ratio-meanj)**2))),min_native_J=float(j.min()),max_native_J=float(j.max()),
                total_signed_area_ratio=float(np.sum(ratio*area0)/np.sum(area0)))
            rows.append(row)
            critical.append(dict(case=label,part=part,tau_s=row['tau_s'],cell=at,
                ID_LL=int(cells[at,0]+2060),ID_LR=int(cells[at,1]+2060),ID_UR=int(cells[at,2]+2060),ID_UL=int(cells[at,3]+2060),
                signed_area_ratio=float(ratio[at]),native_corner_mean_J=float(meanj[at])))
            if part in (30,60,90) and count==91:snapshots[(label,part)]=(poly.copy(),ratio.copy(),meanj.copy())
    outputs=[]
    for suffix,table in (('_history.csv',rows),('_min_cells.csv',critical)):
        q=Path(str(prefix)+suffix);core.write_csv(q,table);outputs.append(q)
    values=[q[1] for q in snapshots.values()]
    norm=TwoSlopeNorm(vmin=min(v.min() for v in values),vcenter=1,vmax=max(v.max() for v in values))
    fig,axes=plt.subplots(2,3,figsize=(16,8),layout='constrained')
    for i,label in enumerate(('AS05_n255','AS05_n3825')):
        for a,part in zip(axes[i],(30,60,90)):
            poly,ratio,_=snapshots[(label,part)]
            pc=PolyCollection(poly,array=ratio,cmap='coolwarm',norm=norm,edgecolors='.3',linewidth=.12)
            a.add_collection(pc);a.autoscale();a.set_aspect('equal');a.set(xlabel='x [m]',ylabel='z [m]',title=f'{label}; part{part}; A<=0: {(ratio<=0).sum()}')
    fig.colorbar(pc,ax=list(axes.flat),label='Signed straight-sided area / initial area',shrink=.7)
    fig.suptitle('Original-material quadrilaterals: deformation-resolution diagnostic\n'
                 'Straight chords are not exact curved material boundaries; this is not an SPH volume gate')
    q=Path(str(prefix)+'_cells.png');fig.savefig(q,dpi=170);plt.close(fig);outputs.append(q)
    assert all(core.stat(q['path'])==q for q in before)
    check.write_text(core.json.dumps(dict(stage=TAG,analysis_complete=True,consumed=before,consumed_stats_unchanged=True,
        original_soil_IDs=5000,verified_grid=[100,50],verified_material_quads=4851,original_cell_connectivity_written=False,
        outputs=[core.stat(q) for q in outputs],physical_acceptance=False,negative_area_is_exact_material_volume=False,
        zero_energy_cause_proven=False,solver_invocations=0,native_decodes=0,SHA_scans=0),indent=2)+'\n')


if __name__=='__main__':main()
