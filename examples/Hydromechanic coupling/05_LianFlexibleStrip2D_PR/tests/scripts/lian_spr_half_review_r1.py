"""Offline native audit of the completed mixed-slip SPR 3-s half pair."""
from concurrent.futures import ThreadPoolExecutor
import json
import re
import sys
import xml.etree.ElementTree as ET
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lian_release_r1 import CASE, TESTS, READER, native, bound, utc, write_json
from lian_mirror_review_r1 import sample
from lian_opt3_review_r1 import verify_bindings
sys.path.insert(0, str(CASE/'support'))
from postprocess_lian_release import weights

TAG='lian_spr_half_review_r1'
RUNS={'coarse':('lian_spr_mix_r1_on_3s',1e-5),'half':('lian_spr_half_r1',5e-6)}
STYLE={'coarse':('#28618e','-'),'half':('#ae692c','--')}


def metrics(a, initial, part, dt):
    row=sample(a,initial,dt,True)
    row.update(part=part,pressure_max_pa=float(a.pressure.max()),
        total_sigma_zz_rms_pa=float(np.sqrt(np.mean((a.sigma_zz-a.pressure)**2))))
    for label,point in [('A',(0.,10.)),('B',(1.25,8.75))]:
        stencil=weights(initial,*point)
        row['paper_'+label+'_pressure_pa']=sum(w*float(a.pressure.iloc[k]) for k,w in stencil)
        row['paper_'+label+'_settlement_mm']=1000*sum(w*float(initial.z.iloc[k]-a.z.iloc[k]) for k,w in stencil)
    for label,mask,col in [('left_normal',np.isclose(initial.x,0,rtol=0,atol=1e-9),'x'),
        ('right_normal',np.isclose(initial.x,20,rtol=0,atol=1e-9),'x'),
        ('bottom_normal',np.isclose(initial.z,0,rtol=0,atol=1e-9),'z'),
        ('bottom_tangent',np.isclose(initial.z,0,rtol=0,atol=1e-9),'x')]:
        assert mask.any()
        row[label+'_max_mm']=1000*float(abs(a.loc[mask,col]-initial.loc[mask,col]).max())
    return row


def main():
    receipt=TESTS/'logs'/(TAG+'.check.json');assert not receipt.exists()
    status=TESTS/'logs/lian_spr_half_r1.status.json';s=json.loads(status.read_text())
    assert s['status']=='half_passed_pending_review' and s['half_accepted']
    assert s['owned_exited'] and s['exit_code']==0 and s['checked_frames']==61
    verify_bindings(s['inputs']+s['outputs']+s['artifacts'])
    sources=[bound(p) for p in [__file__,status,READER,TESTS/'notes/lian_spr_half_r1.json',
        TESTS/'scripts/lian_release_r1.py',TESTS/'scripts/lian_mirror_review_r1.py',
        TESTS/'scripts/lian_opt3_review_r1.py',CASE/'support/postprocess_lian_release.py']]
    manifest=TESTS/'logs/lian_spr_mix_r1_on_3s.run.json';c=json.loads(manifest.read_text())
    assert c['passed'] and c['owned_exited'] and c['exit_code']==0
    verify_bindings(c['outputs']+c['artifacts']);sources.append(bound(manifest))
    for name,dt in RUNS.values():
        text=(TESTS/'outputs'/name/'Run.out').read_text(errors='replace')
        assert 'Finished execution (code=0)' in text and 'RTX 3050' in text
        assert 'SPR stationary wall planes (one per mk): 3' in text
        for mk,mode in [(0,'Free slip'),(1,'No-slip'),(2,'Free slip')]:
            assert re.search(r'mkbound:\s*'+str(mk)+r'\s*->\s*'+mode,text)
        xml=ET.parse(TESTS/'configs'/(name+'_Def.xml'))
        parameters={e.attrib['key']:e.attrib['value'] for e in xml.findall('.//execution/parameters/parameter')}
        assert float(parameters['DtFixed'])==dt and parameters['SoilBoundaryDerivativeSPR']=='1'
        assert parameters['SoilStressRateGradCorr']=='1' and float(parameters.get('SoilHourglassXi','0'))==0
        assert {int(e.attrib['mkbound']):int(e.attrib['slipmode']) for e in xml.findall('.//mdbcslip/bound')}=={0:3,1:2,2:3}
    saved_h=pd.read_csv(TESTS/'figures/lian_spr_half_r1_history.csv',float_precision='round_trip')
    saved_p=pd.read_csv(TESTS/'figures/lian_spr_half_r1_half.csv',float_precision='round_trip')
    history=[];pairs=[];snapshots={};initial=None
    with ThreadPoolExecutor(max_workers=2) as pool:
        for i in range(61):
            arrays=dict(zip(RUNS,pool.map(lambda n:native(TESTS/'outputs'/n,i),[v[0] for v in RUNS.values()])))
            if initial is None:
                initial=arrays['coarse'];assert initial.id.nunique()==20301
                assert np.array_equal(initial[['id','x','y','z']],arrays['half'][['id','x','y','z']])
            for key,a in arrays.items():
                row=metrics(a,initial,i,RUNS[key][1]);row['run']=key;history.append(row)
                if key=='half':
                    for col in saved_h.columns:
                        x,y=row[col],saved_h[col].iloc[i]
                        assert (x is None and pd.isna(y)) or x==y,(i,col,x,y)
                if i in [10,20,60]:snapshots[key,i]=a
            a,b=arrays['half'],arrays['coarse'];top=initial.z.gt(9.99).to_numpy()
            assert np.array_equal(a.id,b.id) and abs(a.time_s.iloc[0]-b.time_s.iloc[0])<=1.01e-5
            row=dict(part=i,half_time_s=float(a.time_s.iloc[0]),coarse_time_s=float(b.time_s.iloc[0]),
                pressure_rms_pa=float(np.sqrt(np.mean((a.pressure-b.pressure)**2))),
                top_material_max_mm=1000*float(abs(a.z.to_numpy()[top]-b.z.to_numpy()[top]).max()),
                pressure_max_abs_pa=float(abs(a.pressure-b.pressure).max()),
                total_stress_rms_pa=float(np.sqrt(np.mean(((a.sigma_zz-a.pressure)-(b.sigma_zz-b.pressure))**2))))
            assert row['pressure_rms_pa']<=5 and row['top_material_max_mm']<=.005
            for col in saved_p.columns:assert row[col]==saved_p[col].iloc[i],(i,col)
            pairs.append(row)
            if i%10==0:print('Independent native half pair',i,flush=True)
    history=pd.DataFrame(history);pairs=pd.DataFrame(pairs);artifacts=[]
    def csv(label,frame):
        p=TESTS/'figures'/(TAG+'_'+label+'.csv');assert not p.exists()
        frame.to_csv(p,index=False,float_format='%.17g');artifacts.append(bound(p))
    def png(label,fig):
        p=TESTS/'figures'/(TAG+'_'+label+'.png');assert not p.exists()
        fig.savefig(p,dpi=170);plt.close(fig);artifacts.append(bound(p))
    csv('history',history);csv('pairs',pairs)
    for label,panels in [('history',[('paper_A_pressure_pa','A material pressure (kPa)',.001),
        ('paper_B_pressure_pa','B material pressure (kPa)',.001),('pressure_max_pa','Maximum pressure (kPa)',.001),
        ('paper_A_settlement_mm','A material settlement (mm)',1),('paper_B_settlement_mm','B material settlement (mm)',1),
        ('total_sigma_zz_rms_pa','Total vertical stress RMS (kPa)',.001)]),
        ('boundary',[(k+'_max_mm',name,1) for k,name in [('left_normal','Left normal displacement (mm)'),
        ('right_normal','Right normal displacement (mm)'),('bottom_normal','Bottom normal displacement (mm)'),
        ('bottom_tangent','Bottom tangential displacement (mm)')]]+
        [('vmax_m_s','Maximum speed (m/s)',1),('force_N_m','Applied resultant (kN/m)',.001)])]:
        fig,axes=plt.subplots(2,3,figsize=(15,8),layout='constrained')
        for key,(color,line) in STYLE.items():
            h=history[history.run.eq(key)]
            for ax,(field,name,scale) in zip(axes.flat,panels):
                ax.plot(h.time_s,h[field]*scale,color=color,ls=line,label=f'SPR ON, dt={RUNS[key][1]*1e6:g} us')
                ax.set(xlim=(0,3),xlabel='Actual saved time (s)',ylabel=name);ax.grid(alpha=.2)
        axes[0,0].legend()
        fig.suptitle('Lian mixed-slip SPR: independent 3-s half pair | grad ON, eta=.04, HG OFF\n'
            'Initial material A/B and adjacent SOIL layers; not wall motion or full-cycle/theory acceptance.')
        png(label,fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    for ax,col,limit,unit in zip(axes,['pressure_rms_pa','top_material_max_mm'],[5,.005],['Pressure RMS difference (Pa)','Top material vertical difference (mm)']):
        ax.plot(pairs.half_time_s,pairs[col],color='#28618e',label='Saved native half pair')
        ax.axhline(limit,color='#353535',ls='--',label=f'Original limit: {limit:g}')
        ax.set(xlim=(0,3),ylim=(0,limit*1.1),xlabel='Actual half saved time (s)',ylabel=unit);ax.grid(alpha=.2);ax.legend()
    fig.suptitle('All 61 original half-step gates | no threshold relaxation; time matching tolerance 10.1 us')
    png('half',fig)
    fig,axes=plt.subplots(1,3,figsize=(16,5),layout='constrained')
    for ax,key in zip(axes[:2],RUNS):
        a=snapshots[key,60]
        artist=ax.tricontourf(a.x,a.z,a.pressure/1000,levels=np.linspace(0,1.75,13),cmap='viridis',extend='both')
        ax.set(title=f'{key}: {a.time_s.iloc[0]:.6f} s\nmax {a.pressure.max()/1000:.6f} kPa',xlabel='x (m)',ylabel='z (m)',aspect='equal')
        fig.colorbar(artist,ax=ax,label='Pressure (kPa)',shrink=.7)
    a,b=snapshots['half',60],snapshots['coarse',60]
    fields=pd.DataFrame(dict(id=initial.id,x0_m=initial.x,z0_m=initial.z,coarse_pressure_pa=b.pressure,
        half_pressure_pa=a.pressure,pressure_difference_pa=a.pressure-b.pressure,
        settlement_difference_mm=1000*(b.z-a.z)))
    csv('fields',fields);maximum=float(abs(fields.pressure_difference_pa).max())
    artist=axes[2].tricontourf(initial.x,initial.z,fields.pressure_difference_pa,
        levels=np.linspace(-maximum,maximum,21),cmap='RdBu_r',extend='both')
    axes[2].set(title='Half minus coarse\nActual matched saves, not theory error',xlabel='Initial x (m)',ylabel='Initial z (m)',aspect='equal')
    fig.colorbar(artist,ax=axes[2],label='Pressure difference (Pa)',shrink=.7)
    fig.suptitle('Native 3-s pressure | identical 0-1.75 kPa limits, unmodified over-range data; no smoothing')
    png('fields',fig)
    summary=[]
    for key in RUNS:
        h=history[history.run.eq(key)];e=h.iloc[-1]
        summary.append(dict(run=key,actual_end_s=float(e.time_s),pressure_max_pa=float(e.pressure_max_pa),
            A_settlement_mm=float(e.paper_A_settlement_mm),B_settlement_mm=float(e.paper_B_settlement_mm),
            maximum_speed_m_s=float(h.vmax_m_s.max()),force_error_N_m=float(abs(h.force_N_m-h.expected13_node_force_N_m).max())))
    csv('summary',pd.DataFrame(summary))
    write_json(receipt,dict(passed=True,visual_review_passed=False,utc=utc(),sources=sources,artifacts=artifacts,
        owned_exit_verified=True,native_ids=20301,matched_samples=61,summary=summary,
        max_pressure_rms_pa=float(pairs.pressure_rms_pa.max()),max_top_material_mm=float(pairs.top_material_max_mm.max()),
        max_point_pressure_difference_pa=float(pairs.pressure_max_abs_pa.max()),
        max_total_stress_rms_difference_pa=float(pairs.total_stress_rms_pa.max()),
        half_step_accepted=True,physical_full_accepted=False,HG_tested=False,
        limitations=['Only 61 saved samples, not every integration substep; saves can differ by one step.',
            'Independent time-step agreement is not theory/FEM/100-s or general-boundary acceptance.',
            'Original 13-node strip quadrature is +4%; near-wall plots describe SOIL, not wall displacement.',
            'SPR has not been established as a global improvement; nonperiodic HG remains untested.']))
    print(pd.DataFrame(summary).to_string(index=False),flush=True)
    print(pairs[['pressure_rms_pa','top_material_max_mm','pressure_max_abs_pa','total_stress_rms_pa']].max(),flush=True)


if __name__=='__main__':main()
