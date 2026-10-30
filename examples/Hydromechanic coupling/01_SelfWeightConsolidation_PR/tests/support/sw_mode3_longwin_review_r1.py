"""Offline 1025-save mode3 review; adopt sealed native guards, no new solver or full admission."""
import argparse
import ast
import json
from pathlib import Path
import numpy as np
import pandas as pd
import sw_mode3_longwin_r1 as worker
import sw_mode3_window_review_r1 as prior

TESTS, TAG = worker.TESTS, 'sw_mode3_longwin_review_r1'
NOTE = TESTS/'notes'/(TAG+'.json')
PARTS, BIN = [0,256,512,768,1024], prior.ENVELOPE_BIN_S


def series(z,t,p,height,finite=True):
    """Batched1024-term quasi-static series: precompute spatial matrices, not1025 tiny matvec calls."""
    z,t=np.asarray(z),np.asarray(t); B=p['Mf']/(p['M']+p['Mf']); cv=p['k']*p['M']/(p['rho_w']*p['g']); d=(B if finite else 1)*cv
    lam=(2*np.arange(1024)+1)*np.pi/(2*height); C=np.cos(z[:,None]*lam); S=np.sin(z[:,None]*lam)
    gamma=(p['rho']-p['rho_w'])*p['g']; coefficients=2*B*gamma/(height*lam**2); decay=coefficients[:,None]*np.exp(-d*lam[:,None]**2*t)
    q=(C@decay).T; integral=((S/lam)@decay).T; rate=(S@(d*lam[:,None]*decay)).T/p['M']*1000
    q[t==0]=B*gamma*(height-z); settlement=(B*gamma*(height*z-z*z/2)-integral)/p['M']*1000; settlement[t==0]=0.; rate[t==0]=np.nan
    depth=np.maximum(height-z,0.); return dict(p_pa=q+p['rho_w']*p['g']*depth,q_pa=q,settlement_increment_mm=settlement,
        sigma_zz_pa=q-gamma*depth,total_sigma_zz_pa=np.broadcast_to(-p['rho']*p['g']*depth,q.shape),vertical_velocity_m_s=-rate/1000,
        legacy_Tv=cv*t/height**2,finite_Kw_Tv=B*cv*t/height**2)


def dense_history(a,rows,p,label,refs):
    a=a.sort_values(['part','layer']); v=lambda k:a[k].to_numpy().reshape(1025,100); h=pd.DataFrame(rows); extra=dict(job=label)
    z=v('z_m'); hydro=p['rho_w']*p['g']*np.maximum(z[:,-1,None]-z,0.); observed={k:v(k) for k in ['pressure_pa','porepress0_pa','excess_native_pa','settlement_mm','sigma_zz','total_sigma_zz_pa','vz']}
    observed.update(q_fixed_double_pa=v('pressure_pa')-v('porepress0_pa'),q_current_pa=v('pressure_pa')-hydro,reference_shift_pa=hydro-v('porepress0_pa'))
    assert abs(observed['q_fixed_double_pa']-observed['q_current_pa']-observed['reference_shift_pa']).max()<1e-9
    for key,x in observed.items():extra['bottom_'+key]=x[:,0]; extra['top_'+key]=x[:,-1]
    extra['top_minus_bottom_settlement_mm']=v('settlement_mm')[:,-1]-v('settlement_mm')[:,0]
    for prefix,r in refs.items():
        for k in ['legacy_Tv','finite_Kw_Tv']:extra[prefix+k]=r[k]
        for k in ['p_pa','q_pa','settlement_increment_mm','sigma_zz_pa','total_sigma_zz_pa','vertical_velocity_m_s']:
            extra[prefix+'bottom_'+k]=r[k][:,0]; extra[prefix+'top_'+k]=r[k][:,-1]
        for actual,want,name in [('pressure_pa','p_pa','pressure_rms_pa'),('settlement_mm','settlement_increment_mm','settlement_rms_mm'),('sigma_zz','sigma_zz_pa','effective_sigma_zz_rms_pa'),
                ('total_sigma_zz_pa','total_sigma_zz_pa','total_sigma_zz_rms_pa'),('q_fixed_double_pa','q_pa','q_fixed_rms_pa'),('q_current_pa','q_pa','q_current_rms_pa'),('vz','vertical_velocity_m_s','layer_mean_vz_residual_rms_m_s')]:
            delta=observed[actual]-r[want]; extra[prefix+name]=np.sqrt(np.mean(delta*delta,axis=1)); extra[prefix+'non_top_'+name]=np.sqrt(np.mean(delta[:,:99]**2,axis=1))
    extra.update(bottom_pressure_H1_residual_pa=v('pressure_pa')[:,0]-refs['H1_finite_']['p_pa'][:,0],top_settlement_H1_residual_mm=v('settlement_mm')[:,-1]-refs['H1_finite_']['settlement_increment_mm'][:,-1],
        reference_velocity_defined=h.time_s.to_numpy()>0,H1_reference_absmax_vz_m_s=np.max(abs(refs['H1_finite_']['vertical_velocity_m_s']),axis=1))
    return pd.concat([h,pd.DataFrame(extra)],axis=1)


def sampled_statistics(h):
    keys=['bottom_pressure_pa','bottom_q_fixed_double_pa','bottom_q_current_pa','top_settlement_mm','bottom_settlement_mm','top_minus_bottom_settlement_mm','bottom_sigma_zz','top_sigma_zz',
        'speed_max_m_s','r_excluding_top_rms_pa','H1_finite_pressure_rms_pa','HD_finite_pressure_rms_pa','H1_finite_settlement_rms_mm','bottom_pressure_H1_residual_pa','top_settlement_H1_residual_mm','H1_finite_layer_mean_vz_residual_rms_m_s']
    windows=[('full',0.,.09375),('startup',0.,.0234375),('extension',.0234375,.09375),('last_quarter',.0703125,.09375),('early5ms',0.,.005),('early10ms',0.,.01),('early20ms',0.,.02)]
    def summarize(a,meta):
        row=dict(job=h.job.iloc[0],actual_start_s=float(a.time_s.iloc[0]),actual_end_s=float(a.time_s.iloc[-1]),samples=len(a),**meta)
        for key in keys:
            x=a[key].to_numpy(); x=x[np.isfinite(x)]; assert len(x)
            row.update({key+'_defined_samples':len(x),key+'_mean':float(x.mean()),key+'_rms':float(np.sqrt(np.mean(x*x))),key+'_min':float(x.min()),key+'_max':float(x.max()),key+'_range':float(np.ptp(x)),key+'_endpoint_change':float(x[-1]-x[0])})
        return row
    w=[summarize(h[(h.time_s>=lo if lo==0 else h.time_s>lo)&(h.time_s<=hi)],dict(window=name,requested_start_s=lo,requested_end_s=hi)) for name,lo,hi in windows]
    groups=np.floor(h.time_s.to_numpy()/BIN).astype(int); e=[summarize(h[groups==i],dict(bin=i,nominal_start_s=i*BIN,nominal_end_s=(i+1)*BIN)) for i in sorted(set(groups))]
    return pd.DataFrame(w),pd.DataFrame(e)


def figures(selected,histories,envelopes,paths):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator, ScalarFormatter
    plt.rcParams.update({'font.size':9,'axes.grid':True,'grid.alpha':.25}); colors=['tab:blue','tab:orange']
    fig,axes=plt.subplots(2,3,figsize=(14,9),constrained_layout=True)
    for label,color in zip(['coarse','half'],colors):
        b=selected[label].query('part==1024').sort_values('layer')
        for ax,key,scale in zip(axes.flat,['pressure_pa','q_current_pa','settlement_mm','sigma_zz','total_sigma_zz_pa','r_native_pa'],[1000,1000,1,1000,1000,1]):ax.plot(b[key]/scale,b.z0_m,color=color,label=label)
        axes[0,1].plot(b.excess_native_pa/1000,b.z0_m,'--',color=color,label=label+' fixed p0 native q')
    for prefix,style in [('H1_finite_','k--'),('HD_finite_','k:'),('H1_legacy_','k-.')]:
        for i,k,s in [(0,'p_pa',1000),(1,'q_pa',1000),(2,'settlement_increment_mm',1),(3,'sigma_zz_pa',1000),(4,'total_sigma_zz_pa',1000)]:axes.flat[i].plot(b[prefix+k]/s,b.z0_m,style,label=prefix.rstrip('_'))
    for ax,title in zip(axes.flat,['Final total p [kPa]','Current hydro / fixed p0 q [kPa]','Settlement increment [mm]','Effective sigma zz [kPa]','Total sigma zz [kPa]','All-layer R [Pa], k>0']):ax.set(title=title,ylabel='Initial material z [m]')
    fig.suptitle('Actual final .09375-s profiles; H1 primary / HD different-domain quasi-static diagnostics')
    def save(fig,axes,path,time_axis=False):
        for ax in axes.flat:
            ax.xaxis.set_major_locator(MaxNLocator(6)); f=ScalarFormatter(useOffset=False); f.set_scientific(False); ax.xaxis.set_major_formatter(f); ax.legend(fontsize=6)
            if time_axis:ax.set_xlabel('Actual saved time [ms]')
        with path.open('xb') as stream:fig.savefig(stream,format='png',dpi=180)
        plt.close(fig)
    save(fig,axes,paths['profiles_png']); fig,axes=plt.subplots(3,3,figsize=(16,12),constrained_layout=True)
    for label,color in zip(['coarse','half'],colors):
        h=histories[label]; t=h.time_s*1000; e=envelopes[label]
        for i,k,s,style in [(0,'bottom_pressure_pa',1000,'-'),(0,'top_pressure_pa',1000,':'),(1,'top_settlement_mm',1,'-'),(1,'bottom_settlement_mm',1,'--'),(2,'bottom_sigma_zz',1000,'-'),(2,'top_sigma_zz',1000,':'),
                (3,'bottom_q_fixed_double_pa',1000,'-'),(3,'bottom_q_current_pa',1000,'--'),(4,'speed_max_m_s',1,'-'),(4,'H1_finite_layer_mean_vz_residual_rms_m_s',1,'--'),(5,'H1_finite_pressure_rms_pa',1,'-'),(5,'HD_finite_pressure_rms_pa',1,'--')]:axes.flat[i].plot(t,h[k]/s,style,color=color,label=label+' '+k.replace('_pa',''))
        for i,k in [(6,'bottom_pressure_H1_residual_pa'),(7,'top_settlement_H1_residual_mm'),(8,'H1_finite_layer_mean_vz_residual_rms_m_s')]:
            axes.flat[i].plot(t,h[k],color=color,linewidth=.6,label=label+' saved observations'); axes.flat[i].bar((e.actual_start_s+e.actual_end_s)*500,e[k+'_max']-e[k+'_min'],bottom=e[k+'_min'],width=(e.actual_end_s-e.actual_start_s)*1000,color=color,alpha=.2,label=label+' fixed1ms bin min/max')
    for i,k,s in [(0,'H1_finite_bottom_p_pa',1000),(1,'H1_finite_top_settlement_increment_mm',1),(2,'H1_finite_bottom_sigma_zz_pa',1000),(4,'H1_reference_absmax_vz_m_s',1)]:axes.flat[i].plot(t,h[k]/s,'k:',label='H1 quasi-static')
    for ax,title in zip(axes.flat,['Bottom/top p [kPa]','Top/bottom increment [mm]','Bottom/top effective sigma zz [kPa]','Bottom two q definitions [kPa]','Raw speed / layer-mean vz residual [m/s]','H1 / HD p RMS [Pa]',
            'Bottom p - H1 envelope [Pa]','Top increment - H1 envelope [mm]','Layer-mean signed-vz residual RMS envelope [m/s]']):ax.set_title(title)
    fig.suptitle('All1025 actual saves; sampled envelopes, not guaranteed wave peaks; t0 reference velocity undefined')
    save(fig,axes,paths['history_png'],True)


def review(tag):
    paths={k:TESTS/folder/(tag+s) for k,folder,s in [('check','logs','.check.json'),('profiles_png','figures','_profiles.png'),('history_png','figures','_history.png')]+[(k,'figures','_'+k+'.csv') for k in ['selected_profiles','history','windows','envelope']]}; assert not any(p.exists() for p in paths.values())
    check=worker.read(worker.CHECK); assert check['passed'] and len(check['jobs'])==2 and not check['held_jobs'] and check['prefix_all38_including_dterror'] and not check['excluded_fields']
    records=[worker.bound(worker.CHECK),check['run']]+check['jobs']; worker.verify(records); run=worker.read(check['run']['path']); worker.verify([run['prepared']]); prepared=worker.read(run['prepared']['path'])
    assert run['status']=='mode3_long_window_prefix_and_half_passed_pending_physical_review' and run['jobs']==check['jobs'] and run['finished_utc'] and len(prepared['jobs'])==2
    capture=prepared['new_build_source_capture']; assert capture==check['new_build_source_capture'] and capture['sources_captured_before_build'] and not capture['compiled_from_snapshot']
    assert not prepared['prior_window_source_attribution']['exact_HG_source_at_build_time_proven']
    records += [run['prepared']]+prepared['inputs']+[worker.bound(p) for p in [__file__,NOTE,worker.__file__,prior.__file__,prior.theory.__file__,prior.base.__file__]]; worker.verify(records)
    histories={}; selected={}; envelopes={}; windows=[]; results={}; refs=None; common=None
    for i,(job,rr) in enumerate(zip(prepared['jobs'],check['jobs'])):
        assert job['suffix']==['coarse','half'][i] and job['frames']==1025; r=worker.read(rr['path']); done=worker.read(r['sealed_completion']['path'])
        assert r['passed'] and not r['errors'] and r['initial_reference']['passed'] and r['hg']['passed'] and r['prefix_all38_including_dterror'] and not r['excluded_fields']
        assert done['solver_finished'] and done['exit_code']==0 and done['owned_exited'] and not done['surviving_owned'] and all(done[k]==job[k] for k in ['program','runtime','config','bat'])
        records += [r['sealed_completion'],job['config'],job['bat'],job['program']]+job['runtime']+done['outputs']+r['artifacts']; worker.verify(records)
        assert len(r['rows'])==len(r['reader_exits'])==1025 and all(x['part']==j and x['exit_code']==0 for j,x in enumerate(r['reader_exits']))
        clock,steps=worker.plan(job); assert all(x['part']==j and x['natural_step']==steps[j] and x['saved_step']==(steps[j]-1 if j else 0) and x['time_s']==clock[steps[j]] and x['pore_limit_passed'] and x['true_drained_count']==10 and x['dterror_s']<=1e-14 for j,x in enumerate(r['rows']))
        assert len(r['prefixes'])==257 and all(x['passed'] and x['different_values']==0 and x['compared_fields']==38 and x['compared_particles']==1040 and x['compared_values']==39520 and x['dterror_included'] and x['excluded_fields']=='' and x['time_s']==x['reference_time_s'] and x['saved_step']==x['reference_saved_step'] for x in r['prefixes'])
        source=lambda suffix:next(x for x in r['artifacts'] if Path(x['path']).name==job['name']+'_'+suffix+'.csv'); load=lambda suffix:pd.read_csv(source(suffix)['path'],float_precision='round_trip')
        prior.same_columns(pd.DataFrame(r['rows']),load('history_r')); prior.same_columns(pd.DataFrame(r['prefixes']).select_dtypes(exclude=['object']),load('prefix_pairs'))
        fields=load('prefix_fields'); assert len(fields)==9766 and not fields.duplicated(['part','field']).any() and fields.groupby('part').field.nunique().eq(38).all() and set(fields.part)==set(range(257)) and 'dterror_s' in set(fields.field) and fields.different_values.eq(0).all() and fields.max_abs_difference.eq(0).all()
        assert len(r['pairs'])==(1025 if i else 0) and all(x['passed'] and x['time_eligible'] and abs(x['actual_time_difference_s'])<=1e-14 and x['pressure_rms_pa']<=5 and x['material_displacement_max_difference_mm']<=.005 for x in r['pairs'])
        if i:prior.same_columns(pd.DataFrame(r['pairs']).select_dtypes(exclude=['object']),load('half_pairs'))
        p=worker.old.parameters(Path(job['config']['path']).read_text(encoding='utf8')); assert p==job['parameters'] and worker.hg.parse_hg((worker.OUTPUTS/job['name']/'Run.out').read_text(errors='replace'),job)==r['hg']
        raw=load('numeric_profiles').sort_values(['part','layer']); assert len(raw)==102500 and not raw.duplicated(['part','layer']).any() and np.isfinite(raw.to_numpy(dtype='<f8')).all()
        for j,b in raw.groupby('part'):assert np.array_equal(b.layer,np.arange(100)) and b.time_s.eq(r['rows'][j]['time_s']).all() and b.natural_step.eq(r['rows'][j]['natural_step']).all() and np.array_equal(b.z0_m,raw.iloc[:100].z0_m) and np.array_equal(b.porepress0_pa,raw.iloc[:100].porepress0_pa)
        z=raw.iloc[:100].z0_m.to_numpy(); hd=float(z[-1]); assert abs(hd-(p['H']-p['dp']/2))<=1e-12
        if refs is None:refs={name:series(z,np.array([x['time_s'] for x in r['rows']]),p,height,finite) for name,height,finite in [('H1_finite_',p['H'],True),('H1_legacy_',p['H'],False),('HD_finite_',hd,True)]}; common=p
        else:assert p==common and np.array_equal(histories['coarse'].time_s,[x['time_s'] for x in r['rows']]) and job['program']==prepared['jobs'][0]['program'] and job['runtime']==prepared['jobs'][0]['runtime']
        a,_=prior.enrich(raw[raw.part.isin(PARTS)], [r['rows'][j] for j in PARTS],p,job['name']); h=dense_history(raw,r['rows'],p,job['name'],refs); w,e=sampled_statistics(h)
        selected[job['suffix']],histories[job['suffix']],envelopes[job['suffix']]=a,h,e; windows.append(w); results[job['suffix']]=dict(final=h.iloc[-1].to_dict(),hg=r['hg'],initial_reference=r['initial_reference'],original_profiles=source('numeric_profiles'),original_history=source('history_r'),adopted_native_checks=1025,exact_all38_prefix_states=257)
    data=dict(selected_profiles=pd.concat(selected.values(),ignore_index=True),history=pd.concat(histories.values(),ignore_index=True),windows=pd.concat(windows,ignore_index=True),envelope=pd.concat(envelopes.values(),ignore_index=True)); assert len(data['selected_profiles'])==1000 and len(data['history'])==2050
    records=worker.unique([dict(x,sha256=x['sha256'].lower()) for x in records]); worker.verify(records)
    for k,a in data.items():
        with paths[k].open('x',encoding='utf8',newline='') as stream:a.to_csv(stream,index=False,float_format='%.17g')
    figures(selected,histories,envelopes,paths); worker.verify(records)
    worker.seal(paths['check'],dict(analysis_checks_passed=True,inputs=records,jobs=results,new_build_source_capture=capture,prior_window_source_attribution=prepared['prior_window_source_attribution'],
        native_frames_redecoded=0,adopted_sealed_native_frames=2050,independent_half_samples=1025,all38_exact_prefix_samples_each=257,selected_profile_parts=PARTS,envelope_bin_s=BIN,
        reference_scope='H1 finite-Kw B*Cv primary quasi-static diagnostic,legacy Cv separate; HD different-domain sensitivity,not fitted actual-initial-state truth. No dynamic/theory gate.',velocity_scope='Signed vz residual from100 layer means,not independent1000-particle native RMS; t0 derivative undefined/NaN,raw speed includes consolidation motion.',
        physical_acceptance=False,automatic_full_run_admitted=False,restart_admitted=False,formal_acceptance=False,solver_started=False,native_reader_started=False,figures_require_visual_review=True,artifacts=[worker.bound(p) for k,p in paths.items() if k!='check']))
    return dict(check=str(paths['check']),analysis_checks_passed=True,physical_acceptance=False)


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8')); assert worker.selftest()['passed']; p=worker.old.parameters(worker.expected(worker.JOBS[0],worker.CASE/'private/solver.exe')[0]); z=np.array([.005,.5,.995]); t=np.array([0.,.0234375,.09375])
    for finite in [True,False]:
        r=series(z,t,p,p['H'],finite)
        for j,time in enumerate(t):
            old=prior.theory.reference(z,time,p,finite)
            for k in ['p_pa','q_pa','settlement_increment_mm']:np.testing.assert_allclose(r[k][j],old[k],rtol=1e-12,atol=1e-9)
            np.testing.assert_allclose(r['vertical_velocity_m_s'][j],-prior.settlement_rate(z,time,p,finite)/1000,rtol=1e-12,atol=1e-12,equal_nan=True)
    return dict(passed=True,files_written=False,live_output_read=False,solver_started=False,native_reader_started=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); modes=parser.add_mutually_exclusive_group(); modes.add_argument('--selftest',action='store_true'); modes.add_argument('--review',action='store_true'); parser.add_argument('--tag',default=TAG)
    args=parser.parse_args(); assert args.tag and Path(args.tag).name==args.tag and args.tag.replace('_','').isalnum()
    if args.selftest:print(json.dumps(selftest()))
    elif args.review:print(json.dumps(review(args.tag)))
    else:parser.print_help()
