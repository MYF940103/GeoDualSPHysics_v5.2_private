"""Separate normal-representation and SPR effects using completed native fields."""
from concurrent.futures import ThreadPoolExecutor
import json
import re
import xml.etree.ElementTree as ET
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import numpy as np
import pandas as pd
from lian_release_r1 import TESTS, READER, native, bound, utc, write_json
from lian_opt3_review_r1 import metrics, verify_bindings
from lian_fig10_first3_r1 import COLORS, CROPS, TIMES

TAG='lian_spr_mix_review_r1'
RUNS={'old':'lian_opt3_r1_grad_3s','off':'lian_spr_mix_r1_off_3s','on':'lian_spr_mix_r1_on_3s'}
LABEL={'old':'Original normals, SPR OFF','off':'Planar normals, SPR OFF','on':'Planar normals, SPR ON'}
STYLE={'old':('#353535',':'),'off':('#28618e','-'),'on':('#ae692c','--')}


def main():
    receipt=TESTS/'logs'/(TAG+'.check.json');assert not receipt.exists()
    status=TESTS/'logs/lian_spr_mix_r1.status.json';s=json.loads(status.read_text())
    assert s['status']=='pair_completed_pending_review' and len(s['runs'])==6
    assert all(r['passed'] and r['exit_code']==0 and r['owned_exited'] for r in s['runs'])
    verify_bindings(s['inputs'])
    sources=[bound(p) for p in [__file__,status,READER,TESTS/'scripts/lian_opt3_review_r1.py',
        TESTS/'scripts/lian_fig10_first3_r1.py',TESTS/'scripts/lian_mirror_review_r1.py']]
    for r in s['runs']:
        verify_bindings(r['outputs']+r['artifacts'])
        manifest=TESTS/'logs'/(r['name']+'.run.json')
        assert json.loads(manifest.read_text())==r
        sources.append(bound(manifest))
        text=(TESTS/'outputs'/r['name']/'Run.out').read_text(errors='replace')
        assert 'Finished execution (code=0)' in text
        for mk,mode in [(0,'Free slip'),(1,'No-slip'),(2,'Free slip')]:
            assert re.search(r'mkbound:\s*'+str(mk)+r'\s*->\s*'+mode,text)
        if r['option']=='on':assert 'SPR stationary wall planes (one per mk): 3' in text
        xml=ET.parse(TESTS/'configs'/(r['name']+'_Def.xml'))
        assert {int(e.attrib['mkbound']):int(e.attrib['slipmode']) for e in xml.findall('.//mdbcslip/bound')}=={0:3,1:2,2:3}
        if r['stage']=='3s':
            prefix=pd.read_csv(TESTS/'figures'/(r['name']+'_prefix.csv'))
            assert prefix.all_native_fields0ulp.all() and len(prefix)==4
    old_manifest=TESTS/'logs/lian_opt3_r1_grad_3s.run.json'
    old=json.loads(old_manifest.read_text());assert old['passed'] and old['exit_code']==0
    verify_bindings(old['outputs']);sources.append(bound(old_manifest))
    saved={k:pd.read_csv(TESTS/'figures'/(v+'_history.csv'),float_precision='round_trip') for k,v in RUNS.items()}
    history=[];changes=[];snapshots={};origin=None
    with ThreadPoolExecutor(max_workers=2) as pool:
        for i in range(61):
            arrays=dict(zip(RUNS,pool.map(lambda n:native(TESTS/'outputs'/n,i),RUNS.values())))
            if origin is None:origin=arrays['old']
            for key,a in arrays.items():
                assert np.array_equal(a.id,origin.id)
                row=metrics(a,origin,i)
                assert a.time_s.iloc[0]==arrays['old'].time_s.iloc[0] and a.saved_step.iloc[0]==arrays['old'].saved_step.iloc[0]
                for c in saved[key].columns:
                    if c in row:
                        x,y=row[c],saved[key][c].iloc[i]
                        assert (x is None and pd.isna(y)) or x==y,(key,i,c,x,y)
                row['run']=key;history.append(row)
                if i in [10,20,60]:snapshots[key,i]=a
            top=origin.z.gt(9.99).to_numpy()
            for label,lhs,rhs in [('normal_representation','off','old'),('SPR','on','off')]:
                a,b=arrays[lhs],arrays[rhs];p=a.pressure-b.pressure
                changes.append(dict(comparison=label,part=i,time_s=float(a.time_s.iloc[0]),
                    pressure_rms_pa=float(np.sqrt(np.mean(p**2))),pressure_max_abs_pa=float(abs(p).max()),
                    top_material_max_mm=1000*float(abs(a.z.to_numpy()[top]-b.z.to_numpy()[top]).max()),
                    total_stress_rms_pa=float(np.sqrt(np.mean(((a.sigma_zz-a.pressure)-(b.sigma_zz-b.pressure))**2)))))
            if i%10==0:print('Three-way matched native frame',i,flush=True)
    history=pd.DataFrame(history);changes=pd.DataFrame(changes);artifacts=[]
    def csv(label,frame):
        p=TESTS/'figures'/(TAG+'_'+label+'.csv');assert not p.exists()
        frame.to_csv(p,index=False,float_format='%.17g');artifacts.append(bound(p))
    def png(label,fig):
        p=TESTS/'figures'/(TAG+'_'+label+'.png');assert not p.exists()
        fig.savefig(p,dpi=180);plt.close(fig);artifacts.append(bound(p))
    csv('history',history);csv('changes',changes)
    selected=[]
    for key in RUNS:
        for target,part,maximum in TIMES:
            a=snapshots[key,part]
            selected.append(dict(run=key,target_time_s=target,actual_time_s=float(a.time_s.iloc[0]),
                pressure_max_kpa=float(a.pressure.max()/1000),above_bar_native_pct=100*float(a.pressure.gt(maximum*1000).mean())))
            csv(f'{key}_part{part:04d}',pd.DataFrame(dict(id=a.id,x_m=a.x,z_m=a.z,pressure_pa=a.pressure)))
    selected=pd.DataFrame(selected);csv('selected',selected)
    image_path=TESTS/'outputs/lian_fig10_ref_r1/figure10.png';sources.append(bound(image_path))
    image=np.asarray(Image.open(image_path).convert('RGB'))
    cmap=ListedColormap(COLORS);cmap.set_over(COLORS[-1]);cmap.set_under('#b850b8')
    plt.rcParams.update({'font.size':10,'axes.titlesize':11})
    fig=plt.figure(figsize=(22,10),layout='constrained');grid=fig.add_gridspec(3,6,width_ratios=[1,1,1,1,1,.045])
    for row,(target,part,maximum) in enumerate(TIMES):
        levels=np.linspace(0,maximum,13)
        for col,key in enumerate(['SPH','FEM','old','off','on']):
            ax=fig.add_subplot(grid[row,col])
            if key in CROPS:
                x0,y0,x1,y1=CROPS[key][row];ax.imshow(image[y0:y1,x0:x1],extent=[0,20,0,10],origin='upper')
                title=f'Paper {key} | {target:g} s'
            else:
                a=snapshots[key,part];m=selected[selected.run.eq(key)&selected.target_time_s.eq(target)].iloc[0]
                artist=ax.tricontourf(a.x,a.z,a.pressure/1000,levels=levels,norm=BoundaryNorm(levels,cmap.N),cmap=cmap,extend='both')
                title=LABEL[key]+f'\n{m.actual_time_s:.6f} s | max {m.pressure_max_kpa:.4f} kPa\n>bar {m.above_bar_native_pct:.2f}% native nodes'
            ax.set(title=title,xlim=(0,20),ylim=(0,10),aspect='equal',xticks=[0,5,10,15,20],yticks=[0,5,10],xlabel='x (m)',ylabel='z (m)' if col==0 else '')
        fig.colorbar(artist,cax=fig.add_subplot(grid[row,5]),label='Excess pressure (kPa)',ticks=[0,1,2,3,4,5] if maximum==5 else [0,.5,1,1.5,1.75])
    fig.suptitle('Lian: separate planar-normal representation from SPR | eta=.04, stress-rate gradient ON, HG OFF\n'
        'Side FreeSlip / bottom NoSlip preserved. Row limits 0-5 / 0-5 / 0-1.75 kPa; no field clipping, smoothing or rescaling.\n'
        'Paper raster is a numerical reference, not an exact field solution; over-range fractions are native-node fractions.',fontsize=13)
    png('fields',fig)
    for label,panels in [('history',[('paper_A_pressure_pa','A material pressure (kPa)',.001),('paper_B_pressure_pa','B material pressure (kPa)',.001),
        ('pressure_max_pa','Native maximum pressure (kPa)',.001),('paper_A_settlement_mm','A material settlement (mm)',1),
        ('paper_B_settlement_mm','B material settlement (mm)',1),('total_sigma_zz_rms_pa','Total vertical stress RMS (kPa)',.001)]),
        ('boundary',[(k+'_max_mm',name,1) for k,name in [('left_normal','Left normal displacement (mm)'),('right_normal','Right normal displacement (mm)'),
        ('bottom_normal','Bottom normal displacement (mm)'),('bottom_tangent','Bottom tangential displacement (mm)')]]+
        [('vmax_m_s','Maximum speed (m/s)',1),('force_N_m','Applied resultant (kN/m)',.001)])]:
        fig,axes=plt.subplots(2,3,figsize=(15,8),layout='constrained')
        for key,(color,line) in STYLE.items():
            h=history[history.run.eq(key)]
            for ax,(field,name,scale) in zip(axes.flat,panels):
                ax.plot(h.time_s,h[field]*scale,color=color,ls=line,lw=1.5,label=LABEL[key]);ax.grid(alpha=.2)
                ax.set(xlim=(0,3),xlabel='Actual time (s)',ylabel=name)
        axes[0,0].legend(fontsize=9)
        fig.suptitle('Lian native '+label+' | fixed walls, same physical/material/load configuration\n'
            'Displacements belong to initially adjacent SOIL layers. A/B use initial material coordinates; cross-option differences are not half-step errors.')
        png(label,fig)
    end=history[history.part.eq(60)];extremes=[]
    for key in RUNS:
        h=history[history.run.eq(key)];e=end[end.run.eq(key)].iloc[0]
        d=dict(run=key,pressure_max_pa=float(e.pressure_max_pa),A_settlement_mm=float(e.paper_A_settlement_mm),
            B_settlement_mm=float(e.paper_B_settlement_mm),min_pressure_pa=float(h.pressure_min_pa.min()),
            vmax_m_s=float(h.vmax_m_s.max()),force_error_N_m=float(abs(h.force_N_m-h.expected13_node_force_N_m).max()))
        for k in ['left_normal','right_normal','bottom_normal','bottom_tangent']:d['max_'+k+'_mm']=float(h[k+'_max_mm'].max())
        extremes.append(d)
    maxima=changes.groupby('comparison')[['pressure_rms_pa','pressure_max_abs_pa','top_material_max_mm','total_stress_rms_pa']].max().reset_index()
    csv('extremes',pd.DataFrame(extremes));csv('max_changes',maxima)
    write_json(receipt,dict(passed=True,visual_review_passed=False,utc=utc(),sources=sources,artifacts=artifacts,
        verified_runs=6,matched_samples=61,extremes=extremes,max_changes=maxima.to_dict('records'),
        half_step_accepted=False,physical_full_accepted=False,HG_tested=False,
        limitations=['SPH/FEM reference is raster only, not exact raw truth; no whole-field theory error is claimed.',
            'Normal representation and SPR effects are separately compared; uniform original strip quadrature remains +4%.',
            'Cross-option differences are not half-step errors; independent 5Pa/.005mm half validation remains pending.',
            'Old worker completion notification failed because a full status dict was interpolated as text (159564chars); no solver failure or old worker restart.']))
    print(pd.DataFrame(extremes).to_string(index=False),flush=True);print(maxima.to_string(index=False),flush=True)


if __name__=='__main__':main()
