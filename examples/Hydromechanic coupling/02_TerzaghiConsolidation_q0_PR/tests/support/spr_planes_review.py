"""Review and plot the bounded CPU plane/corner and NoPen evidence only."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

TESTS=Path(__file__).resolve().parents[1]
PREFIX=TESTS/'figures/spr_planes_review_r2'


def bound(path):
    path=Path(path)
    with path.open('rb') as stream:return dict(path=str(path),sha256=hashlib.file_digest(stream,'sha256').hexdigest().upper())


def load(name):return json.loads((TESTS/'logs'/(name+'.json')).read_text(encoding='utf-8-sig'))


def main():
    receipt=TESTS/'logs/spr_planes_review_r2.check.json';assert not receipt.exists()
    records=[];evidence=[]
    for tag,geometries in [('spr_planes_r3_rel',('corner2','edge3')),('spr_planes_r2_dbg',('corner2','edge3')),('spr_planes_r4_rel',('wedge2',)),('spr_planes_r4_dbg',('wedge2',))]:
        source=load(tag+'.check');evidence.append(bound(TESTS/'logs'/(tag+'.check.json')))
        for row in source['runs']:
            if row['geometry'] not in geometries:continue
            assert row['passed'] and row['active_wall_count']==row['wall_count']
            for item in row['outputs']:assert bound(item['path'])['sha256']==item['sha256']
            folder=TESTS/'outputs'/row['name'];wall=pd.read_csv(folder/'wall.csv',float_precision='round_trip');soil=pd.read_csv(folder/'soil.csv',float_precision='round_trip')
            assert wall.actual.notna().all() and (wall.error<=wall.tolerance).all() and (soil.difference<=soil.tolerance).all()
            assert wall.id.nunique()==row['wall_count'] and len(wall)==6*row['wall_count']
            record=dict(name=row['name'],geometry=row['geometry'],build='Debug' if 'dbg' in tag else 'Release',slip_mode=row['slip_mode'],
                wall_count=row['wall_count'],constant_max_error_m_s=float(wall[wall.trial.eq(0)].error.max()),affine_max_error_m_s=float(wall[wall.trial.eq(1)].error.max()),
                max_velocity_tolerance_ratio=float((wall.error/wall.tolerance).max()),consumer_tolerance_ratio=float((soil.difference/soil.tolerance).max()),
                stress_rate_max_diff_pa_s=row['consumer_max'][0],pressure_rate_max_diff_pa_s=row['consumer_max'][1],density_rate_max_diff_kg_m3_s=row['consumer_max'][2])
            records.append(record)
    frame=pd.DataFrame(records);assert len(frame)==18
    pulse=[]
    for tag,nopen in [('spr_pulse_r1',False),('spr_pulse_nopen_r1',True)]:
        proof=load(tag+'.check');assert proof['passed'];evidence.append(bound(TESTS/'logs'/(tag+'.check.json')))
        for row in proof['half']:pulse.append(dict(nopen=nopen,**row))
    half=pd.DataFrame(pulse)
    reference=load('spr_nopen_reference_r1.check');assert reference['completed']
    nopen=pd.DataFrame([{k:row[k] for k in ('geometry','slip_mode','max_pure_tangent_normal_shift_m_s','max_inward_normal_shift_m_s','tangent_invariance_passed')} for row in reference['runs']])
    on=load('spr_nopen_on_r1.check');assert on['completed']
    assert all(x.get('original_nopen_shift_0ulp',False) if x['geometry']=='2d_h' else x['expected_inclined_rejection'] for x in on['runs'])
    old=load('spr_planes_regression_r1.check');assert old['passed'] and len(old['planes'])==18 and len(old['native_pairs'])==2
    assert all(x['all_native_fields_0ulp'] for x in old['native_pairs'])
    outputs=[]
    for suffix,data in [('_operators.csv',frame),('_half.csv',half),('_nopen.csv',nopen)]:
        path=Path(str(PREFIX)+suffix);data.to_csv(path,index=False,mode='x');outputs.append(path)
    fig,axes=plt.subplots(1,3,figsize=(16,4.8))
    labels=[x.geometry.replace('corner2','C2').replace('wedge2','W2').replace('edge3','E3')+' S'+str(x.slip_mode)+' '+x.build[0] for x in frame.itertuples()]
    axes[0].scatter(np.arange(18),frame.max_velocity_tolerance_ratio,color='#24649b',marker='o',label='Velocity / limit')
    axes[0].scatter(np.arange(18),frame.consumer_tolerance_ratio,color='#9b7440',marker='x',label='S/P/R operator / limit')
    axes[0].axhline(1,color='.3',ls='--');axes[0].set(yscale='log',ylim=(1e-5,2),title='Manufactured-field tolerance ratios',ylabel='Maximum error / declared limit')
    axes[0].set_xticks(np.arange(18),labels,rotation=65,ha='right',fontsize=8);axes[0].legend(fontsize=8)
    for i,row in enumerate(half.itertuples()):
        axes[1].bar(i,row.pressure_rms_max_pa,color='#24649b' if not row.nopen else '#8b803e',hatch='//' if row.nopen else None)
    axes[1].set_xticks(range(len(half)),[x.geometry.replace('corner2','C2').replace('wedge2','W2')+' S'+str(x.slip_mode)+(' NP' if x.nopen else '') for x in half.itertuples()],rotation=50,ha='right')
    axes[1].set(ylim=(0,.01),ylabel='Maximum pressure RMS difference (Pa)',title='2-ms coarse/half pulses; limit = 0.5 Pa')
    for i,row in enumerate(nopen.itertuples()):axes[2].bar(i,row.max_pure_tangent_normal_shift_m_s,color='#24649b' if row.geometry=='2d_h' else '#b47c37',hatch='//' if row.geometry=='2d_t' else None)
    axes[2].set_xticks(range(4),['0 deg S2','0 deg S3','30 deg S2','30 deg S3'],rotation=35,ha='right')
    axes[2].set(ylim=(0,.008),ylabel='Spurious normal velocity correction (m/s)',title='Existing NoPen, SPR OFF; tangent input 0.01 m/s')
    for ax in axes:ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.suptitle('CPU fixed-plane/corner extension: bounded checks, not long-cycle 2-D acceptance')
    fig.tight_layout(rect=(0,.05,1,.94));fig.text(.5,.015,'C2: right-angle corner; W2: oblique wall pair; E3: 3-D edge. Inclined NoPen remains rejected. Raw R kernel bias is not claimed removed.',ha='center',fontsize=9)
    path=Path(str(PREFIX)+'_checks.png');assert not path.exists();fig.savefig(path,dpi=170);plt.close(fig);outputs.append(path)
    before=pd.read_csv(TESTS/'outputs/spr_planes_r1_corner2_s2/wall.csv',float_precision='round_trip')
    after=pd.read_csv(TESTS/'outputs/spr_planes_r3_rel_corner2_s2/wall.csv',float_precision='round_trip')
    a=before[before.trial.eq(1)].groupby('id').agg(x=('x','first'),z=('z','first'),error=('error','max'))
    b=after[after.trial.eq(1)].groupby('id').agg(x=('x','first'),z=('z','first'),error=('error','max'))
    assert np.array_equal(a[['x','z']],b[['x','z']])
    compare=a.rename(columns={'error':'before_error_m_s'}).join(b.error.rename('after_error_m_s'))
    path=Path(str(PREFIX)+'_corner_data.csv');compare.to_csv(path,mode='x');outputs.append(path)
    fig,axes=plt.subplots(1,3,figsize=(15,4.8))
    nodes=after[after.trial.eq(1)].groupby('id').first();nodes=nodes[(abs(nodes.fx-nodes.gx)+abs(nodes.fz-nodes.gz))>1e-12]
    axes[0].scatter(nodes.gx,nodes.gz,marker='x',color='#9b7440',label='Original ghost target')
    axes[0].scatter(nodes.fx,nodes.fz,facecolors='none',edgecolors='#24649b',s=60,label='Interior fit centre')
    for row in nodes.itertuples():axes[0].annotate('',(row.fx,row.fz),(row.gx,row.gz),arrowprops=dict(arrowstyle='->',color='.6',lw=.7))
    axes[0].set(title='Fit centre moves; target stays unchanged',xlim=(-.03,.04),ylim=(-.005,.035));axes[0].legend(fontsize=8,loc='upper left')
    for ax,data,title in [(axes[1],a,'Before: per-mk admission only'),(axes[2],b,'After: interior fit / original target')]:
        sc=ax.scatter(data.x,data.z,c=np.maximum(data.error,1e-12),cmap='cividis',norm=LogNorm(vmin=1e-12,vmax=.02),s=35)
        ax.set(title=title,xlim=(-.03,.10),ylim=(-.03,.10))
    for ax in axes:ax.axvline(0,color='.3',lw=.8);ax.axhline(0,color='.3',lw=.8);ax.set(xlabel='x (m)',ylabel='z (m)',aspect='equal');ax.grid(alpha=.15)
    fig.suptitle('Identical 2-D corner geometry, NoSlip affine mapping test (not a compatible flow solution)')
    fig.subplots_adjust(left=.055,right=.88,bottom=.15,top=.82,wspace=.3)
    coloraxis=fig.add_axes([.915,.18,.014,.59])
    fig.colorbar(sc,cax=coloraxis,label='Maximum component error (m/s); display floor 1e-12')
    path=Path(str(PREFIX)+'_corner.png');assert not path.exists();fig.savefig(path,dpi=170);plt.close(fig);outputs.append(path)
    result=dict(passed=True,manufactured_cases=18,legacy_plane_cases=18,one_dimensional_0ulp_pairs=2,short_half_pairs=len(half),
        max_affine_aux_error_m_s=float(frame.affine_max_error_m_s.max()),max_half_pressure_rms_pa=float(half.pressure_rms_max_pa.max()),
        max_half_material_displacement_mm=float(half.material_displacement_max_mm.max()),inclined_nopen_not_promoted=True,
        time_window_s=.002,visual_inspected=False,evidence=evidence,outputs=[bound(p) for p in outputs])
    with receipt.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)
    print({k:v for k,v in result.items() if k not in ('outputs','evidence')})


if __name__=='__main__':main()
