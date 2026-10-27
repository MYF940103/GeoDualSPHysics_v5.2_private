"""Independent actual-program short-window HG review, never launches a solver."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lian_release_r1 import TESTS, READER, native, bound, utc, write_json
from lian_opt3_review_r1 import verify_bindings
from lian_spr_half_review_r1 import metrics
from lian_hg_short_r1 import hg_stats

TAG='lian_hg_short_review_r1'


def main():
    receipt=TESTS/'logs'/(TAG+'.check.json');assert not receipt.exists()
    state_path=TESTS/'logs/lian_hg_short_r1.status.json';s=json.loads(state_path.read_text())
    assert s['status']=='short_passed_pending_review' and len(s['runs'])==6
    assert s['half_pairs']==31 and all(r['passed'] and r['exit_code']==0 and r['owned_exited'] for r in s['runs'])
    verify_bindings(s['inputs']);histories=[];sources=[bound(p) for p in [__file__,state_path,READER,
        TESTS/'scripts/lian_hg_short_r1.py',TESTS/'scripts/lian_spr_half_review_r1.py']]
    snapshots={};origin=None
    for job,r in zip(s['jobs'],s['runs']):
        assert job['name']==r['name'];verify_bindings(r['outputs']+r['artifacts'])
        manifest=TESTS/'logs'/(r['name']+'.run.json');assert json.loads(manifest.read_text())==r;sources.append(bound(manifest))
        folder=TESTS/'outputs'/r['name'];text=(folder/'Run.out').read_text(errors='replace')
        assert 'Finished execution (code=0)' in text
        if job['xi']:assert hg_stats(text)==r['hg_stats']
        if job['backend']=='gpu_debug':assert 'ERROR SUMMARY: 0 errors' in (TESTS/'logs'/(r['name']+'.log')).read_text(errors='replace')
        saved=pd.read_csv(TESTS/'figures'/(r['name']+'_history.csv'),float_precision='round_trip')
        for i in range(len(saved)):
            a=native(folder,i)
            if origin is None:origin=a
            assert np.array_equal(a.id,origin.id)
            row=metrics(a,origin,i,job['dt']);row['run']=r['name']
            for col in saved.columns:
                x,y=row[col],saved[col].iloc[i]
                assert (x is None and pd.isna(y)) or x==y,(r['name'],i,col)
            histories.append(row)
            if job['reference']:
                m=json.loads((TESTS/'logs'/(job['reference']+'.run.json')).read_text())
                b=native(TESTS/'outputs'/job['reference'],i)
                source=TESTS/'outputs'/job['reference']/'data'/f'Part_{i:04d}.bi4'
                old=next(e for e in m['outputs'] if e['path'].lower()==str(source.resolve()).lower())
                assert bound(source)['sha256']==old['sha256']
                assert list(a.columns)==list(b.columns) and a.to_numpy(dtype='<f8').tobytes()==b.to_numpy(dtype='<f8').tobytes()
            if job['backend']=='gpu':snapshots[r['name'],i]=a
        print('Independent short native review:',r['name'],len(saved),flush=True)
    history=pd.DataFrame(histories);pairs=[];changes=[];top=origin.z.gt(9.99).to_numpy()
    for i in range(31):
        c=snapshots['lian_hg_short_r1_on_c',i];h=snapshots['lian_hg_short_r1_on_h',i];o=snapshots['lian_hg_short_r1_off_gpu',i]
        assert c.time_s.iloc[0]==o.time_s.iloc[0] and abs(c.time_s.iloc[0]-h.time_s.iloc[0])<=1.01e-5
        p=float(np.sqrt(np.mean((h.pressure-c.pressure)**2)));d=1000*float(abs(h.z.to_numpy()[top]-c.z.to_numpy()[top]).max())
        assert p<=5 and d<=.005
        pairs.append(dict(part=i,coarse_time_s=float(c.time_s.iloc[0]),half_time_s=float(h.time_s.iloc[0]),pressure_rms_pa=p,top_material_max_mm=d))
        changes.append(dict(part=i,time_s=float(c.time_s.iloc[0]),pressure_rms_pa=float(np.sqrt(np.mean((c.pressure-o.pressure)**2))),
            point_pressure_max_pa=float(abs(c.pressure-o.pressure).max()),top_material_max_mm=1000*float(abs(c.z.to_numpy()[top]-o.z.to_numpy()[top]).max()),
            total_stress_rms_pa=float(np.sqrt(np.mean(((c.sigma_zz-c.pressure)-(o.sigma_zz-o.pressure))**2)))))
    pairs=pd.DataFrame(pairs);changes=pd.DataFrame(changes)
    assert float(pairs.pressure_rms_pa.max())==s['max_pressure_rms_pa'] and float(pairs.top_material_max_mm.max())==s['max_top_material_mm']
    artifacts=[]
    def csv(label,frame):
        path=TESTS/'figures'/(TAG+'_'+label+'.csv');assert not path.exists()
        frame.to_csv(path,index=False,float_format='%.17g');artifacts.append(bound(path))
    def png(label,fig):
        path=TESTS/'figures'/(TAG+'_'+label+'.png');assert not path.exists()
        fig.savefig(path,dpi=170);plt.close(fig);artifacts.append(bound(path))
    csv('history',history);csv('pairs',pairs);csv('changes',changes)
    fig,axes=plt.subplots(2,3,figsize=(15,8),layout='constrained')
    panels=[('paper_A_pressure_pa','A material pressure (kPa)',.001),('paper_B_pressure_pa','B material pressure (kPa)',.001),
        ('total_sigma_zz_rms_pa','Total vertical stress RMS (kPa)',.001),('paper_A_settlement_mm','A material settlement (mm)',1),
        ('bottom_tangent_max_mm','Bottom soil tangential displacement (mm)',1),('force_N_m','Applied resultant (kN/m)',.001)]
    for run,color,line,label in [('off_gpu','#353535',':','HG OFF, 10 us'),('on_c','#28618e','-','HG .1, 10 us'),('on_h','#ae692c','--','HG .1, 5 us')]:
        h=history[history.run.eq('lian_hg_short_r1_'+run)]
        for ax,(field,title,scale) in zip(axes.flat,panels):
            ax.plot(h.time_s,h[field]*scale,color=color,ls=line,label=label)
            ax.set(xlim=(0,.15),xlabel='Actual saved time (s)',ylabel=title);ax.grid(alpha=.2)
    axes[0,0].legend()
    fig.suptitle('Real Lian nonperiodic HG startup | SPR ON, grad ON, eta=.04, original mixed slip/load\n'
        'HG ON/OFF effects are not half-step errors; .15 s does not test drainage after1s or full-cycle accuracy.')
    png('history',fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    for ax,column,limit,label in zip(axes,['pressure_rms_pa','top_material_max_mm'],[5,.005],['Pressure RMS (Pa)','Top material vertical difference (mm)']):
        ax.plot(pairs.half_time_s,pairs[column],color='#28618e');ax.axhline(limit,color='#353535',ls='--',label='Original threshold')
        ax.set(xlim=(0,.15),ylim=(0,limit*1.1),xlabel='Actual half time (s)',ylabel=label);ax.grid(alpha=.2);ax.legend()
    fig.suptitle('HG ON independent half pair | all31 saved native samples; no relaxed limits')
    png('half',fig)
    summary=[]
    for name in ['off_gpu','on_c','on_h']:
        h=history[history.run.eq('lian_hg_short_r1_'+name)];e=h.iloc[-1]
        summary.append(dict(run=name,actual_end_s=float(e.time_s),peak_pressure_pa=float(e.pressure_max_pa),
            A_settlement_mm=float(e.paper_A_settlement_mm),B_settlement_mm=float(e.paper_B_settlement_mm),
            total_stress_rms_pa=float(e.total_sigma_zz_rms_pa),max_speed_m_s=float(h.vmax_m_s.max()),
            max_force_error_N_m=float(abs(h.force_N_m-h.expected13_node_force_N_m).max())))
    csv('summary',pd.DataFrame(summary))
    write_json(receipt,dict(passed=True,visual_review_passed=False,utc=utc(),sources=sources,artifacts=artifacts,
        verified_runs=6,native_ids=20301,hg_off_CPU3frames_GPU31frames0ulp=True,gpu_debug_actual_program_memcheck_errors=0,
        half_pairs=31,max_pressure_rms_pa=float(pairs.pressure_rms_pa.max()),max_top_material_mm=float(pairs.top_material_max_mm.max()),
        HG_on_minus_off_maxima=changes.drop(columns=['part','time_s']).max().to_dict(),summary=summary,
        physical_full_accepted=False,long_run_admitted=False,
        limitations=['Only startup through.15s, no activated drainage after1s or theory/full-cycle acceptance.',
            'Independent half errors and same-dt HG ON/OFF effects are distinct.',
            'Fixed mixed-slip planar walls, original+4% nodal load quadrature, elastic/small rotation/fresh HG only.']))
    print(pd.DataFrame(summary).to_string(index=False),flush=True);print('Half:',s['max_pressure_rms_pa'],s['max_top_material_mm'],flush=True)


if __name__=='__main__':main()
