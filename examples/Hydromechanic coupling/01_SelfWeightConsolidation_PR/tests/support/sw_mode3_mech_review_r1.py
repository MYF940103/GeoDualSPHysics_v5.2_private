"""Offline matched k0/k1e-3 startup review from sealed CSVs; no native reader or solver."""
import argparse
import ast
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import sw_mode3_mech_r1 as worker

TAG='sw_mode3_mech_review_r1'
TESTS=worker.TESTS
NOTE=TESTS/'notes'/(TAG+'.json')


def covariance(x,y,scale):
    x,y=np.asarray(x,dtype=float).ravel(),np.asarray(y,dtype=float).ravel(); assert x.shape==y.shape and scale>0 and np.isfinite(x).all() and np.isfinite(y).all()
    a,b=x-x.mean(),y-y.mean(); xx,yy=np.mean(a*a),np.mean(b*b); cov=float(np.mean(a*b))
    return dict(samples=len(x),covariance_pa2=cov,normalized_covariance=cov/(scale*scale),normalization_pressure_pa=scale,
        correlation=cov/np.sqrt(xx*yy) if xx>0 and yy>0 else None,root_mean_square_ratio=float(np.sqrt(np.mean(x*x)/np.mean(y*y))) if np.mean(y*y)>0 else None)


def enrich(a,h,p,label):
    a=a.sort_values(['part','layer']).copy(); assert len(a)==25700 and not a.duplicated(['part','layer']).any()
    assert np.array_equal(a.layer.to_numpy(),np.tile(np.arange(100),257))
    assert np.array_equal(a.part.to_numpy(),np.repeat(np.arange(257),100))
    a['q_fixed_double_pa']=a.pressure_pa-a.porepress0_pa; top=a[a.layer==99].set_index('part').z_m
    a['hydro_current_pa']=p['rho_w']*p['g']*np.maximum(0.,a.part.map(top)-a.z_m)
    a['q_current_pa']=a.pressure_pa-a.hydro_current_pa; a['hydro_current_minus_fixed_p0_pa']=a.hydro_current_pa-a.porepress0_pa
    for key in ['pressure_pa','q_current_pa','sigma_zz','total_sigma_zz_pa']:
        initial=a[a.part==0].set_index('layer')[key]; a[key+'_change']=a[key]-a.layer.map(initial)
    initial_trace=a[a.part==0].set_index('layer')[['sigma_xx','sigma_yy','sigma_zz']].sum(axis=1)
    a['volumetric_strain_increment_from_stress']=(a[['sigma_xx','sigma_yy','sigma_zz']].sum(axis=1)-a.layer.map(initial_trace))/(3*p['K'])
    a['variant']=label; h=h.copy(); h['variant']=label
    for part,row in h.iterrows():
        b=a[a.part==part]; assert len(b)==100 and b.time_s.eq(row.time_s).all() and b.natural_step.eq(row.natural_step).all()
        for name,boundary in [('bottom',b.iloc[0]),('top',b.iloc[-1])]:
            for key in ['pressure_pa','porepress0_pa','excess_native_pa','q_fixed_double_pa','q_current_pa','hydro_current_minus_fixed_p0_pa','sigma_zz','total_sigma_zz_pa','settlement_mm','vz']:
                h.loc[part,name+'_'+key]=boundary[key]
        for key in ['pressure_pa_change','q_current_pa_change','sigma_zz_change','total_sigma_zz_pa_change']:
            h.loc[part,key+'_layer_rms']=np.sqrt(np.mean(b[key].to_numpy()**2))
    return a,h


def summary(h):
    keys=['bottom_pressure_pa','bottom_q_fixed_double_pa','bottom_q_current_pa','bottom_hydro_current_minus_fixed_p0_pa','top_settlement_mm','bottom_settlement_mm','top_vz','bottom_vz','speed_max_m_s','r_excluding_top_rms_pa','pressure_pa_change_layer_rms']
    late=h[h.time_s>=.75*h.time_s.iloc[-1]]; early=h[h.time_s<=.002]
    return dict(final={k:float(h[k].iloc[-1]) for k in keys},early_actual_end_s=float(early.time_s.iloc[-1]),
        early_max_abs={k:float(abs(early[k]).max()) for k in keys},all_max_abs={k:float(abs(h[k]).max()) for k in keys},
        last_quarter=dict(start_s=float(late.time_s.iloc[0]),samples=len(late),range={k:float(late[k].max()-late[k].min()) for k in keys},endpoint_delta={k:float(late[k].iloc[-1]-late[k].iloc[0]) for k in keys}))


def figures(profiles,histories,path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(13,8),constrained_layout=True); raxis=axes[1,2].twinx()
    for a,h,color,name in zip(profiles,histories,['tab:blue','tab:orange'],['k=0','k=1e-3']):
        b=a[a.part==256]; z=b.z0_m; t=h.time_s
        for key,style,label in [('pressure_pa','-','p'),('q_fixed_double_pa',':','q fixed'),('q_current_pa','--','q current')]:axes[0,0].plot(b[key]/1000,z,style,color=color,label=name+' '+label)
        axes[0,1].plot(b.sigma_zz/1000,z,color=color,label=name+' effective'); axes[0,1].plot(b.total_sigma_zz_pa/1000,z,'--',color=color,label=name+' total')
        axes[0,2].plot(b.settlement_mm,z,color=color,label=name)
        axes[1,0].plot(t,h.bottom_pressure_pa-h.bottom_pressure_pa.iloc[0],color=color,label=name)
        for key,style in [('top','-'),('bottom','--')]:
            axes[1,1].plot(t,h[key+'_settlement_mm'],style,color=color,label=name+' '+key)
            axes[1,2].plot(t,h[key+'_vz'],style,color=color,label=name+' '+key+' vz')
        raxis.plot(t,h.r_excluding_top_rms_pa,':',color=color,alpha=.65,label=name+' R990')
    titles=['Final p / two excess definitions [kPa]','Final effective / total sigma zz [kPa]','Final material settlement increment [mm]',
            'Bottom p change from own initial [Pa]','Material settlement increment [mm]','Signed material vz [m/s]; dotted R990']
    for i,(ax,title) in enumerate(zip(axes.flat,titles)):
        ax.set(title=title,xlabel='Actual saved time [s]' if i>=3 else '',ylabel='Initial material z [m]' if i<3 else ''); ax.grid(alpha=.25); ax.legend(fontsize=7)
    raxis.set(yscale='symlog',ylabel='Non-top native R RMS [Pa]'); raxis.legend(fontsize=6,loc='lower right')
    fig.suptitle('Same-initial-state mechanical isolation; all saved observations, no filtering; not physical acceptance')
    fig.savefig(path,dpi=180); plt.close(fig)


def review():
    paths={k:TESTS/d/(TAG+s) for k,d,s in [('check','logs','.check.json'),('png','figures','.png'),('profiles','figures','_profiles.csv'),('history','figures','_history.csv')]}
    assert not any(p.exists() for p in paths.values()),'Fresh offline artifacts only'
    check=worker.read(worker.CHECK); assert check['passed'] and len(check['jobs'])==1
    worker.verify([check['run']]+check['jobs']); run=worker.read(check['run']['path']); worker.verify([run['prepared']]); prepared=worker.read(run['prepared']['path']); worker.verify(prepared['inputs'])
    assert check['source_program_attribution']==prepared['source_program_attribution'] and not prepared['source_program_attribution']['exact_HG_source_at_build_time_proven']
    records=[worker.bound(p) for p in [__file__,NOTE,worker.__file__,worker.CHECK]]+[check['run'],run['prepared']]+prepared['inputs']
    jobs=[(worker.LABEL,prepared['job'],check['jobs'][0]),(worker.REFERENCE,prepared['reference']['job'],prepared['reference']['receipt'])]; profiles=[]; histories=[]; results={}; trees=[]
    for label,job,rr in jobs:
        worker.verify([rr]); receipt=worker.read(rr['path']); worker.verify([receipt['sealed_completion']]); done=worker.read(receipt['sealed_completion']['path'])
        assert receipt['passed'] and receipt['hg']['passed'] and receipt['initial_reference']['passed'] and len(receipt['rows'])==len(receipt['reader_exits'])==257
        assert all(x['exit_code']==0 for x in receipt['reader_exits']) and done['solver_finished'] and done['owned_exited'] and done['exit_code']==0 and not done['surviving_owned']
        assert done['program']==job['program'] and done['runtime']==job['runtime'] and done['config']==job['config'] and done['bat']==job['bat']
        records += [rr,receipt['sealed_completion'],job['config'],job['bat'],job['program']]+job['runtime']+done['outputs']+receipt['artifacts']; worker.verify(records)
        src=lambda suffix:next(x for x in receipt['artifacts'] if Path(x['path']).name==job['name']+suffix)
        h=pd.read_csv(src('_history_r.csv')['path'],float_precision='round_trip'); pd.testing.assert_frame_equal(h,pd.DataFrame(receipt['rows']),check_dtype=False,check_exact=True)
        clock,steps=worker.window.plan(job); assert np.array_equal(h.natural_step,steps) and np.array_equal(h.time_s,clock[steps]) and h.true_drained_count.eq(10).all() and h.dterror_s.le(1e-14).all()
        tree=ET.parse(job['config']['path']); trees.append(tree); p=worker.old.parameters(Path(job['config']['path']).read_text(encoding='utf8')); assert p==job['parameters'] and p['k']==(0 if label==worker.LABEL else float(np.float32(.001)))
        if label==worker.LABEL:assert receipt['initial38_bitexact'] and receipt['pore_diffusion_bound_applicable'] is False and receipt['pore_limit_passed'] is None
        text=next(Path(x['path']).read_text(errors='replace') for x in done['outputs'] if Path(x['path']).name=='Run.out'); assert worker.hg.parse_hg(text,job)==receipt['hg']
        a,h=enrich(pd.read_csv(src('_numeric_profiles.csv')['path'],float_precision='round_trip'),h,p,label); profiles.append(a); histories.append(h); results[label]=summary(h)
    assert jobs[0][1]['program']==jobs[1][1]['program'] and jobs[0][1]['runtime']==jobs[1][1]['runtime']
    signature=lambda t:[(e.tag,sorted(e.attrib.items())) for e in t.getroot().iter() if e.tag!='HydraulicConductivity']; assert signature(trees[0])==signature(trees[1])
    a,b=profiles; assert np.array_equal(histories[0].time_s,histories[1].time_s) and np.array_equal(histories[0].saved_step,histories[1].saved_step)
    assert np.array_equal(a.loc[a.part==0].drop(columns='variant').to_numpy(),b.loc[b.part==0].drop(columns='variant').to_numpy())
    receipt=worker.read(check['jobs'][0]['path']); pair_record=next(x for x in receipt['artifacts'] if Path(x['path']).name.endswith('_k0_k1em3_pairs.csv')); pairs=pd.read_csv(pair_record['path'],float_precision='round_trip')
    assert len(pairs)==257 and pairs.time_eligible.all() and pairs.same_saved_step.all() and not pairs.gate_applied.any() and pairs.initial38_bitexact.iloc[0]
    assert np.array_equal(pairs.time_s,histories[0].time_s) and np.array_equal(pairs.saved_step,histories[0].saved_step)
    qscale=float(abs(a.loc[a.part==0,'excess_native_pa']).max()); correlations={}
    for name,mask in [('all',np.ones(len(a),dtype=bool)),('early',a.time_s.to_numpy()<=.002),('last_quarter',a.time_s.to_numpy()>=.75*a.time_s.max())]:
        correlations[name]=covariance(a.loc[mask,'pressure_pa_change'],b.loc[mask,'pressure_pa_change'],qscale)
    worker.verify(records); pd.concat([x[x.part==256] for x in profiles],ignore_index=True).to_csv(paths['profiles'],index=False,float_format='%.17g')
    pd.concat(histories,ignore_index=True).to_csv(paths['history'],index=False,float_format='%.17g'); figures(profiles,histories,paths['png']); worker.verify(records)
    worker.seal(paths['check'],dict(analysis_checks_passed=True,inputs=worker.unique(records),jobs=results,actual_matched_samples=257,derived_profile_rows=200,derived_history_rows=514,
        pressure_change_descriptive_covariance=correlations,source_program_attribution=prepared['source_program_attribution'],native_reader_started=False,solver_started=False,
        interpretation='Both pressure changes use their own initial field. Covariance/correlation may describe shared transients,not a unique cause or causal percentage. No diffusion/quasi-static k0 theory was applied. R990 is undrained integration diagnostic for k0 only; all-layer R and dynamic stresses retained in profiles.',
        physical_acceptance=False,theory_acceptance=False,full_acceptance=False,restart_admitted=False,new_thresholds_applied=False,figures_require_visual_review=True,artifacts=[worker.bound(v) for k,v in paths.items() if k!='check']))
    print(paths['check'])


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8')); c=covariance([0,1,2],[0,2,4],2); assert c['correlation']==1 and abs(c['root_mean_square_ratio']-.5)<1e-14
    assert covariance([0,0],[1,2],1)['correlation'] is None
    print(json.dumps(dict(passed=True,files_written=False,native_reader_started=False,solver_started=False)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); modes=parser.add_mutually_exclusive_group(); modes.add_argument('--selftest',action='store_true'); modes.add_argument('--review',action='store_true'); args=parser.parse_args()
    if args.selftest:selftest()
    elif args.review:review()
    else:parser.print_help()
