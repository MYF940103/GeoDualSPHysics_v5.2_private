"""Offline supported-option review; never launches or changes a solver."""
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
import fitz
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import numpy as np
import pandas as pd
from lian_release_r1 import CASE, TESTS, REPO, READER, native, bound, utc, write_json
from lian_mirror_review_r1 import sample
from lian_fig10_first3_r1 import COLORS, CROPS, TIMES, PDF
sys.path.insert(0, str(CASE/'support'))
from postprocess_lian_release import weights

TAG='lian_opt3_review_r1'
RUNS={'base':'lian_mirror15_r1_c', **{v:'lian_opt3_r1_'+v+'_3s' for v in ['grad','d0','d02','d08']}}
LABELS={'base':'Baseline, eta=.04', 'grad':'Stress-rate grad ON', 'd0':'Damping OFF',
        'd02':'Damping eta=.02', 'd08':'Damping eta=.08'}
STYLE={'base':('#252525','-'), 'grad':('#245f92','--'), 'd0':('#bc752c',':'),
       'd02':('#9a4f79','-.'), 'd08':('#637a35',(0,(5,1,1,1)))}


def verify_bindings(items):
    for e in items:
        now=bound(e['path'])
        assert now['sha256'].lower()==e['sha256'].lower(),e['path']
        assert now['bytes']==e['bytes'],e['path']


def metrics(a, initial, part):
    row=sample(a, initial, 1e-5, True)
    row.update(part=part, pressure_max_pa=float(a.pressure.max()),
        total_sigma_zz_rms_pa=float(np.sqrt(np.mean((a.sigma_zz-a.pressure)**2))))
    for label, point in [('A',(0.,10.)),('B',(1.25,8.75))]:
        stencil=weights(initial,*point)
        row['paper_'+label+'_pressure_pa']=sum(w*float(a.pressure.iloc[k]) for k,w in stencil)
        row['paper_'+label+'_settlement_mm']=1000*sum(w*float(initial.z.iloc[k]-a.z.iloc[k]) for k,w in stencil)
    for label, mask, col in [('left_normal',np.isclose(initial.x,0,rtol=0,atol=1e-9),'x'),
        ('right_normal',np.isclose(initial.x,20,rtol=0,atol=1e-9),'x'),
        ('bottom_normal',np.isclose(initial.z,0,rtol=0,atol=1e-9),'z'),
        ('bottom_tangent',np.isclose(initial.z,0,rtol=0,atol=1e-9),'x')]:
        assert mask.any()
        row[label+'_max_mm']=1000*float(abs(a.loc[mask,col]-initial.loc[mask,col]).max())
    return row


def main():
    receipt=TESTS/'logs'/(TAG+'.check.json')
    assert not receipt.exists(),'Retained analysis is never overwritten'
    state_path=TESTS/'logs/lian_opt3_r1.status.json'
    state=json.loads(state_path.read_text())
    assert state['status']=='matrix_completed_pending_review' and len(state['runs'])==9
    assert all(r['passed'] and r['exit_code']==0 and r['owned_exited'] for r in state['runs'])
    verify_bindings(state['inputs'])
    sources=[bound(p) for p in [__file__,state_path,PDF,READER,
        TESTS/'scripts/lian_fig10_first3_r1.py',TESTS/'scripts/lian_mirror_review_r1.py',
        TESTS/'scripts/lian_release_r1.py', CASE/'support/postprocess_lian_release.py']]
    for r in state['runs']:
        verify_bindings(r['outputs']+r.get('artifacts',[])+[r['log']])
        p=TESTS/'logs'/(r['name']+'.run.json')
        assert json.loads(p.read_text())==r
        sources.append(bound(p))
        text=(TESTS/'outputs'/r['name']/'Run.out').read_text(errors='replace')
        assert 'Finished execution (code=0)' in text
        assert re.search(r'mkbound:\s*0\s*->\s*Free slip',text)
        assert re.search(r'mkbound:\s*1\s*->\s*No-slip',text)
        xml=ET.parse(TESTS/'configs'/(r['name']+'_Def.xml'))
        assert {int(e.attrib['mkbound']):int(e.attrib['slipmode']) for e in xml.findall('.//mdbcslip/bound')}=={0:3,1:2}
        if r['stage']=='3s':
            pfx=pd.read_csv(TESTS/'figures'/(r['name']+'_prefix.csv'))
            assert pfx.all_fields0ulp.sum()>=3
    baseline_path=TESTS/'logs/lian_mirror15_r1_c.run.json'
    baseline=json.loads(baseline_path.read_text())
    assert baseline['exit_code']==0 and baseline['owned_exited']
    verify_bindings(baseline['outputs'])
    sources.append(bound(baseline_path))
    histories=[]; comparisons=[]; snapshots={}; initial=None
    for key,name in RUNS.items():
        folder=TESTS/'outputs'/name
        start=native(folder,0)
        if initial is None: initial=start
        assert np.array_equal(initial.to_numpy(),start.to_numpy())
        top=initial.z.gt(9.99).to_numpy()
        saved=pd.read_csv(TESTS/'figures'/(name+'_history.csv'),float_precision='round_trip') if key!='base' else None
        for i in range(61):
            a=native(folder,i)
            row=metrics(a,initial,i)
            if saved is not None:
                for c in saved.columns:
                    if c in row:
                        x,y=row[c],saved[c].iloc[i]
                        assert (x is None and pd.isna(y)) or x==y,(key,i,c,x,y)
            row['run']=key
            histories.append(row)
            if key=='base':
                snapshots['base',i]=a
            else:
                b=snapshots['base',i]
                assert np.array_equal(a.id,b.id)
                assert float(a.time_s.iloc[0])==float(b.time_s.iloc[0]) and int(a.saved_step.iloc[0])==int(b.saved_step.iloc[0])
                dp=a.pressure-b.pressure
                comparisons.append(dict(run=key,part=i,time_s=row['time_s'],
                    pressure_rms_change_pa=float(np.sqrt(np.mean(dp**2))),
                    pressure_max_abs_change_pa=float(abs(dp).max()),
                    top_material_max_change_mm=1000*float(abs(a.z.to_numpy()[top]-b.z.to_numpy()[top]).max()),
                    total_stress_rms_change_pa=float(np.sqrt(np.mean(((a.sigma_zz-a.pressure)-(b.sigma_zz-b.pressure))**2)))))
            if i in [10,20,60]: snapshots[key,i]=a
        print('All61 native frames independently checked:',name,flush=True)
    history=pd.DataFrame(histories); pairs=pd.DataFrame(comparisons)
    artifacts=[]
    def csv(label, frame):
        p=TESTS/'figures'/(TAG+'_'+label+'.csv'); assert not p.exists()
        frame.to_csv(p,index=False,float_format='%.17g'); artifacts.append(bound(p))
    def png(label, fig):
        p=TESTS/'figures'/(TAG+'_'+label+'.png'); assert not p.exists()
        fig.savefig(p,dpi=180); plt.close(fig); artifacts.append(bound(p))
    csv('history',history); csv('changes',pairs)
    selected=[]
    for key in RUNS:
        for target,part,maximum in TIMES:
            a=snapshots[key,part]
            selected.append(dict(run=key,target_time_s=target,actual_time_s=float(a.time_s.iloc[0]),
                pressure_max_kpa=float(a.pressure.max()/1000),pressure_min_kpa=float(a.pressure.min()/1000),
                above_colorbar_native_fraction_pct=100*float(a.pressure.gt(maximum*1000).mean()),
                paper_colorbar_max_kpa=maximum))
            csv(f'{key}_part{part:04d}',pd.DataFrame(dict(id=a.id,x_m=a.x,z_m=a.z,pressure_pa=a.pressure)))
    summary=pd.DataFrame(selected); csv('summary',summary)
    doc=fitz.open(PDF); pix=fitz.Pixmap(doc,63)
    image=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,pix.n)
    old_image=TESTS/'outputs/lian_fig10_ref_r1/figure10.png'
    assert np.array_equal(image,np.asarray(Image.open(old_image).convert('RGB')))
    sources.append(bound(old_image))
    cmap=ListedColormap(COLORS); cmap.set_over(COLORS[-1]); cmap.set_under('#b850b8')
    plt.rcParams.update({'font.size':10,'axes.titlesize':11})
    for label,columns in [('paper',['SPH','FEM','base','grad']),('damping',['base','d0','d02','d08'])]:
        fig=plt.figure(figsize=(18,10),layout='constrained')
        grid=fig.add_gridspec(3,5,width_ratios=[1,1,1,1,.045])
        for r,(target,part,maximum) in enumerate(TIMES):
            levels=np.linspace(0,maximum,13)
            for col,key in enumerate(columns):
                ax=fig.add_subplot(grid[r,col])
                if key in CROPS:
                    x0,y0,x1,y1=CROPS[key][r]
                    ax.imshow(image[y0:y1,x0:x1],extent=[0,20,0,10],origin='upper')
                    title=f'Paper {key} | t={target:g} s'
                else:
                    a=snapshots[key,part]
                    artist=ax.tricontourf(a.x,a.z,a.pressure/1000,levels=levels,norm=BoundaryNorm(levels,cmap.N),cmap=cmap,extend='both')
                    z=summary[summary.run.eq(key)&summary.target_time_s.eq(target)].iloc[0]
                    title=f'{LABELS[key]} | {z.actual_time_s:.6f} s\nmax {z.pressure_max_kpa:.4f} kPa; >bar {z.above_colorbar_native_fraction_pct:.2f}% nodes'
                ax.set(title=title,xlim=(0,20),ylim=(0,10),aspect='equal',xticks=[0,5,10,15,20],yticks=[0,5,10],xlabel='x (m)',ylabel='z (m)' if col==0 else '')
            cb=fig.colorbar(artist,cax=fig.add_subplot(grid[r,4]),ticks=[0,1,2,3,4,5] if maximum==5 else [0,.5,1,1.5,1.75])
            cb.set_label('Excess pore pressure (kPa)')
        fig.suptitle('Lian 3-s supported-option comparison: '+('paper / stress-rate gradient' if label=='paper' else 'damping sensitivity')+'\n'
            'Side FreeSlip / bottom NoSlip unchanged; SPR and HG OFF. Original row scales 0-5 / 0-5 / 0-1.75 kPa.\n'
            'No smoothing, zero-clipping or rescaling. Over-range raw values are retained; reference raster is not an exact field solution.',fontsize=13)
        png(label,fig)
    panels=[('paper_A_pressure_pa','A (0,10) pressure (kPa)',.001),('paper_B_pressure_pa','B (1.25,8.75) pressure (kPa)',.001),
        ('pressure_max_pa','Native maximum pressure (kPa)',.001),('paper_A_settlement_mm','A material settlement (mm)',1),
        ('paper_B_settlement_mm','B material settlement (mm)',1),('total_sigma_zz_rms_pa','Total vertical stress RMS (kPa)',.001)]
    fig,axes=plt.subplots(2,3,figsize=(15,8),layout='constrained')
    for key,(color,line) in STYLE.items():
        d=history[history.run.eq(key)]
        for ax,(field,title,scale) in zip(axes.flat,panels):
            ax.plot(d.time_s,d[field]*scale,color=color,ls=line,label=LABELS[key],lw=1.5)
            ax.set(xlabel='Actual time (s)',ylabel=title,xlim=(0,3)); ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=9)
    fig.suptitle('Lian 3-s native material histories | same load, material and mixed-slip boundaries\n'
        'B uses initial-coordinate bilinear material weights; parameter changes are not half-step or theory errors.')
    png('history',fig)
    fig,axes=plt.subplots(2,3,figsize=(15,8),layout='constrained')
    panels=[(k+'_max_mm',label,1) for k,label in [('left_normal','Left-wall normal displacement (mm)'),
        ('right_normal','Right-wall normal displacement (mm)'),('bottom_normal','Bottom normal displacement (mm)'),
        ('bottom_tangent','Bottom tangential displacement (mm)')]]+[
        ('vmax_m_s','Native maximum speed (m/s)',1),('force_N_m','Actual strip resultant (kN/m)',.001)]
    for key,(color,line) in STYLE.items():
        d=history[history.run.eq(key)]
        for ax,(field,title,scale) in zip(axes.flat,panels):
            ax.plot(d.time_s,d[field]*scale,color=color,ls=line,label=LABELS[key],lw=1.5)
            ax.set(xlabel='Actual time (s)',ylabel=title,xlim=(0,3));ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=9)
    fig.suptitle('Mixed-slip response on the initially adjacent SOIL material layers\n'
        'These are soil displacements, not prescribed wall motion; mDBC boundary particles remain fixed.')
    png('boundary',fig)
    extremes=[]
    for key in RUNS:
        h=history[history.run.eq(key)]; end=h.iloc[-1]
        result=dict(run=key,final_time_s=float(end.time_s),final_pressure_max_pa=float(end.pressure_max_pa),
            final_A_settlement_mm=float(end.paper_A_settlement_mm),final_B_settlement_mm=float(end.paper_B_settlement_mm),
            min_pressure_pa=float(h.pressure_min_pa.min()),max_speed_m_s=float(h.vmax_m_s.max()),
            max_force_error_N_m=float(abs(h.force_N_m-h.expected13_node_force_N_m).max()),
            final_total_stress_rms_pa=float(end.total_sigma_zz_rms_pa))
        for k in ['left_normal','right_normal','bottom_normal','bottom_tangent']:
            result['max_'+k+'_mm']=float(h[k+'_max_mm'].max())
        if key!='base':
            p=pairs[pairs.run.eq(key)]
            result.update(max_pressure_rms_change_pa=float(p.pressure_rms_change_pa.max()),
                max_top_material_change_mm=float(p.top_material_max_change_mm.max()))
        extremes.append(result)
    csv('extremes',pd.DataFrame(extremes))
    write_json(receipt,dict(passed=True,visual_review_passed=False,utc=utc(),sources=sources,artifacts=artifacts,
        verified_runs=9,native_samples_per_comparison=61,extremes=extremes,selected=selected,
        half_step_accepted=False,physical_full_accepted=False,SPR_tested=False,HG_tested=False,
        limitations=['Original13-node resultant13000N/m is +4% strip quadrature, unchanged.',
        'Paper SPH/FEM are raster numerical references: no exact FEM pressure-field error is available.',
        'Over-range fraction is native-node fraction, not continuum area. Pressure is never clipped in data.',
        'Each option is isolated relative to baseline; no option has a new independent half-step test here.',
        'Mixed-slip SPR and nonperiodic HG have NOT been tested; no new long run is admitted.']))
    print(pd.DataFrame(extremes).to_string(index=False),flush=True)


if __name__=='__main__':
    main()
