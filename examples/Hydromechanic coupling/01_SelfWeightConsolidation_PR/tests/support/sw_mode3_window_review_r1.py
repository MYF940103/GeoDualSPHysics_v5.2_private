"""Offline 257-save mode3 startup review; quasi-static references are diagnostics, not admission."""
import argparse
import ast
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import sw_mode3_window_r1 as worker
import sw_mode3_review_r1 as theory
import sw_stage1_equilibrium_review_r1 as base

TESTS, TAG = worker.TESTS, 'sw_mode3_window_review_r1'
NOTE = TESTS/'notes'/(TAG+'.json')
ENVELOPE_BIN_S = .001


def settlement_rate(z, t, p, finite=True):
    """Downward quasi-static increment rate [mm/s]; t=0 boundary incompatibility is not assigned zero."""
    z = np.asarray(z,dtype=float)
    if t == 0:return np.full_like(z,np.nan)
    B=p['Mf']/(p['M']+p['Mf']); diffusivity=(B if finite else 1)*p['k']*p['M']/(p['rho_w']*p['g'])
    lam=(2*np.arange(1024)+1)*np.pi/(2*p['H']); coefficients=2*B*(p['rho']-p['rho_w'])*p['g']/(p['H']*lam**2)
    return np.sin(z[:,None]*lam)@(coefficients*diffusivity*lam*np.exp(-diffusivity*lam**2*t))/p['M']*1000


def same_columns(actual, saved):
    """Exact numeric reproduction of serialized derived columns; no tolerances or time rewrite."""
    assert len(actual) == len(saved) and all(k in saved for k in actual)
    assert np.array_equal(actual.to_numpy(dtype='<f8'), saved[list(actual)].to_numpy(dtype='<f8'))


def enrich(raw, rows, p, label):
    a = raw.copy(); first = a[a.part == 0].sort_values('layer')
    assert len(a) == len(rows)*100 and len(first) == 100 and not a.duplicated(['part', 'layer']).any()
    assert np.isfinite(a.to_numpy(dtype='<f8')).all() and np.array_equal(first.layer, np.arange(100))
    hd = float(first.z0_m.iloc[-1]); assert abs(hd-(p['H']-p['dp']/2)) <= 1e-12
    a['job'] = label; a['saved_step'] = a.part.map({r['part']:r['saved_step'] for r in rows})
    a['q_fixed_double_pa'] = a.pressure_pa-a.porepress0_pa
    a['native_excess_roundoff_pa'] = a.excess_native_pa-a.q_fixed_double_pa
    a['drained_plane_now_m'] = a.part.map(a[a.layer == 99].set_index('part').z_m)
    a['hydro_now_pa'] = p['rho_w']*p['g']*np.maximum(a.drained_plane_now_m-a.z_m, 0.)
    a['q_current_pa'] = a.pressure_pa-a.hydro_now_pa
    a['reference_shift_pa'] = a.hydro_now_pa-a.porepress0_pa
    assert abs(a.q_fixed_double_pa-a.q_current_pa-a.reference_shift_pa).max() < 1e-9
    for row in rows:
        b = a[a.part == row['part']].sort_values('layer'); z = b.z0_m.to_numpy()
        assert len(b) == 100 and np.array_equal(b.layer, np.arange(100)) and np.array_equal(z, first.z0_m)
        assert np.array_equal(b.porepress0_pa, first.porepress0_pa) and b.time_s.eq(row['time_s']).all() and b.natural_step.eq(row['natural_step']).all()
        for domain, height in [('H1', p['H']), ('HD', hd)]:
            pp = dict(p, H=height); depth = np.maximum(height-z, 0.)
            for kind, finite in [('finite', True), ('legacy', False)]:
                ref = theory.reference(z, row['time_s'], pp, finite); prefix = domain+'_'+kind+'_'
                rate=settlement_rate(z,row['time_s'],pp,finite)
                values = dict(ref, sigma_zz_pa=ref['p_pa']-p['rho']*p['g']*depth, total_sigma_zz_pa=-p['rho']*p['g']*depth,
                    settlement_rate_mm_s=rate,vertical_velocity_m_s=-rate/1000)
                for key, value in values.items():a.loc[b.index, prefix+key] = value
    a['reference_velocity_defined']=a.time_s>0
    for prefix in ['H1_finite_','H1_legacy_','HD_finite_','HD_legacy_']:a[prefix+'vz_residual_m_s']=a.vz-a[prefix+'vertical_velocity_m_s']
    numeric=a.select_dtypes(include=[np.number]); derivative=[k for k in numeric if k.endswith(('settlement_rate_mm_s','vertical_velocity_m_s','vz_residual_m_s'))]
    assert np.isfinite(numeric.drop(columns=derivative).to_numpy()).all() and np.isfinite(numeric.loc[a.time_s>0,derivative].to_numpy()).all()
    assert numeric.loc[a.time_s==0,derivative].isna().all().all()
    return a, hd


def history(a, rows, label):
    h = base.history(a, rows, label); extras=[]
    for _, row in h.iterrows():
        b = a[a.part == row.part].sort_values('layer'); bottom, top = b.iloc[0], b.iloc[-1]
        extra=dict(bottom_q_fixed_double_pa=bottom.q_fixed_double_pa,top_p_pa=top.pressure_pa,top_q_fixed_double_pa=top.q_fixed_double_pa,
            top_q_current_pa=top.q_current_pa,top_sigma_zz_pa=top.sigma_zz,top_total_sigma_zz_pa=top.total_sigma_zz_pa)
        for domain in ['H1', 'HD']:
            for kind in ['finite', 'legacy']:
                prefix = domain+'_'+kind+'_'
                for field in ['p_pa', 'q_pa', 'settlement_increment_mm', 'sigma_zz_pa', 'total_sigma_zz_pa','settlement_rate_mm_s','vertical_velocity_m_s']:
                    extra[prefix+'bottom_'+field] = bottom[prefix+field]
                    extra[prefix+'top_'+field] = top[prefix+field]
                for field in ['legacy_Tv', 'finite_Kw_Tv']:extra[domain+'_'+field] = bottom[prefix+field]
                for actual, ref, name in [('pressure_pa','p_pa','pressure_rms_pa'), ('settlement_mm','settlement_increment_mm','settlement_increment_rms_mm'),
                        ('sigma_zz','sigma_zz_pa','effective_sigma_zz_rms_pa'), ('total_sigma_zz_pa','total_sigma_zz_pa','total_sigma_zz_rms_pa'),
                        ('q_fixed_double_pa','q_pa','q_fixed_rms_pa'), ('q_current_pa','q_pa','q_current_rms_pa'),('vz','vertical_velocity_m_s','layer_vz_residual_rms_m_s')]:
                    delta = b[actual].to_numpy()-b[prefix+ref].to_numpy()
                    extra[prefix+name] = float(np.sqrt(np.mean(delta*delta)))
                    extra[prefix+'non_top_'+name] = float(np.sqrt(np.mean(delta[:-1]*delta[:-1])))
        extras.append(extra)
    h=pd.concat([h,pd.DataFrame(extras)],axis=1)
    h['bottom_pressure_H1_residual_pa'] = h.bottom_p_pa-h.H1_finite_bottom_p_pa
    h['top_settlement_H1_residual_mm'] = h.top_settlement_mm-h.H1_finite_top_settlement_increment_mm
    h['bottom_settlement_H1_residual_mm'] = h.bottom_settlement_mm-h.H1_finite_bottom_settlement_increment_mm
    return h


def window_statistics(h):
    result = []; end = float(h.time_s.iloc[-1])
    windows = [('startup_0_to_5ms',0.,.005), ('startup_0_to_10ms',0.,.01), ('startup_0_to_20ms',0.,.02),
               ('5_to_10ms',.005,.01), ('10_to_20ms',.01,.02), ('final_20ms_to_end',.02,end)]
    keys = ['bottom_p_pa','bottom_q_native_pa','bottom_q_fixed_double_pa','bottom_q_current_pa','bottom_reference_shift_pa',
            'top_settlement_mm','bottom_settlement_mm','bottom_sigma_zz_pa','bottom_total_sigma_zz_pa','top_sigma_zz_pa',
            'top_minus_bottom_settlement_mm','speed_max_m_s','r_excluding_top_rms_pa','bottom_pressure_H1_residual_pa','top_settlement_H1_residual_mm','bottom_settlement_H1_residual_mm',
            'native_H1_vz_residual_rms_m_s','native_H1_vz_residual_absmax_m_s','native_H1_vz_residual_mean_m_s','native_H1_reference_absmax_vz_m_s']
    keys += [k for k in h if k.startswith(('H1_','HD_')) and ('rms_' in k or k.endswith('_Tv'))]
    for name, lo, hi in windows:
        a = h[(h.time_s>=lo if lo==0 else h.time_s>lo)&(h.time_s<=hi)]; assert len(a) >= 2
        row = dict(job=h.job.iloc[0],window=name,requested_start_s=lo,requested_end_s=hi,actual_start_s=float(a.time_s.iloc[0]),actual_end_s=float(a.time_s.iloc[-1]),samples=len(a))
        for key in keys:
            x = a[key].to_numpy(); x=x[np.isfinite(x)]; assert len(x)
            row.update({key+'_defined_samples':len(x),key+'_mean':float(x.mean()),key+'_rms':float(np.sqrt(np.mean(x*x))),key+'_min':float(x.min()),
                key+'_max':float(x.max()),key+'_absmax':float(abs(x).max()),key+'_range':float(np.ptp(x)),key+'_endpoint_change':float(x[-1]-x[0])})
        result.append(row)
    return pd.DataFrame(result)


def envelope(h):
    groups = np.floor(h.time_s.to_numpy()/ENVELOPE_BIN_S).astype(int); result = []
    for group in sorted(set(groups)):
        a = h[groups == group]; row = dict(job=h.job.iloc[0],bin=group,nominal_start_s=group*ENVELOPE_BIN_S,nominal_end_s=(group+1)*ENVELOPE_BIN_S,
            actual_start_s=float(a.time_s.iloc[0]),actual_end_s=float(a.time_s.iloc[-1]),samples=len(a))
        for key in ['bottom_pressure_H1_residual_pa','top_settlement_H1_residual_mm','bottom_settlement_H1_residual_mm','native_H1_vz_residual_rms_m_s']:
            x = a[key].to_numpy(); x=x[np.isfinite(x)]; assert len(x)
            row.update({key+'_defined_samples':len(x),key+'_min':float(x.min()),key+'_max':float(x.max()),key+'_range':float(np.ptp(x)),key+'_rms':float(np.sqrt(np.mean(x*x)))})
        result.append(row)
    return pd.DataFrame(result)


def native_audit(job, receipt, raw, short_initial, coarse):
    clock, steps = worker.plan(job); frames = {}; endpoints = []; rows = []; pairs = []; p = job['parameters']
    for part in range(257):
        a = worker.current.native(worker.OUTPUTS/job['name'], part); frames[part] = a
        row = dict(worker.stage.measure(a,frames[0],part,job,clock),**worker.short.r_summary(a,p),**worker.old.pore_limit(a,p,job['dt']))
        assert row['pore_limit_passed'] and row['natural_step'] == steps[part] and row['time_s'] == clock[steps[part]]
        assert all(receipt['rows'][part][key] == value for key,value in row.items())
        if part == 0:
            assert list(a) == list(short_initial) and np.array_equal(a.to_numpy(dtype='<f8').view('<u8'),short_initial.to_numpy(dtype='<f8').view('<u8'))
            initial,_ = worker.old.initial_reference(a,p); assert initial == receipt['initial_reference'] and initial['passed']
        direct = pd.DataFrame(worker.stage.profiles(a,frames[0],part))
        direct['r_native_pa'] = direct.excess_native_pa+p['Mf']*(direct.sigma_xx+direct.sigma_yy+direct.sigma_zz)/(3*p['K'])
        direct['included_in_r_summary'] = direct.layer != 99
        same_columns(direct, raw[raw.part == part].sort_values('layer'))
        z0,inverse=np.unique(frames[0].iloc[40:].z.to_numpy(),return_inverse=True)
        reference_vz=-settlement_rate(z0,row['time_s'],p)[inverse]/1000
        residual=a.iloc[40:].vz.to_numpy()-reference_vz
        row.update(reference_velocity_defined=part>0,native_H1_vz_residual_rms_m_s=float(np.sqrt(np.mean(residual*residual))) if part else None,
            native_H1_vz_residual_absmax_m_s=float(abs(residual).max()) if part else None,native_H1_vz_residual_mean_m_s=float(residual.mean()) if part else None,
            native_H1_reference_absmax_vz_m_s=float(abs(reference_vz).max()) if part else None); rows.append(row)
        soil = a.iloc[40:]; selected = soil[((soil.id.astype(int)-40)%100).isin([0,99])].copy()
        top = float(soil[((soil.id.astype(int)-40)%100) == 99].z.mean())
        selected['job'] = job['name']; selected['part'] = part; selected['material_layer'] = (selected.id.astype(int)-40)%100
        selected['settlement_increment_mm'] = (frames[0].set_index('id').loc[selected.id,'z'].to_numpy()-selected.z.to_numpy())*1000
        selected['q_fixed_double_pa'] = selected.pressure-selected.porepress0
        selected['q_current_pa'] = selected.pressure-p['rho_w']*p['g']*np.maximum(top-selected.z,0.)
        selected['H1_finite_vertical_velocity_m_s']=reference_vz[selected.index.to_numpy()-40]
        selected['H1_finite_vz_residual_m_s']=selected.vz-selected.H1_finite_vertical_velocity_m_s
        endpoints += selected.to_dict('records')
        if job['suffix'] == 'half':
            pair,_ = worker.short.pair(job['name']+'_vs_coarse','gpu_half',part,a,part,coarse[part],frames[0],coarse[0],p)
            assert pair['passed'] and pair == receipt['pairs'][part]; pairs.append(pair)
    return frames,rows,endpoints,pairs


def figures(profiles, histories, envelopes, paths):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator, ScalarFormatter
    plt.rcParams.update({'font.size':9,'axes.grid':True,'grid.alpha':.25})
    colors = {'coarse':'tab:blue','half':'tab:orange'}
    def finish(fig,axes,path,time_axis=False):
        for ax in axes.flat:
            ax.xaxis.set_major_locator(MaxNLocator(6)); fmt=ScalarFormatter(useOffset=False); fmt.set_scientific(False); ax.xaxis.set_major_formatter(fmt)
            ax.yaxis.set_major_locator(MaxNLocator(6)); ax.legend(fontsize=6)
            if time_axis:ax.set_xlabel('Actual saved time [ms]')
        with path.open('xb') as stream:fig.savefig(stream,format='png',dpi=180)
        plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(14,9),constrained_layout=True)
    for label,a in profiles.items():
        b=a[a.part==256].sort_values('layer'); color=colors[label]
        for index,key,scale in [(0,'pressure_pa',1000),(1,'excess_native_pa',1000),(2,'settlement_mm',1),(3,'sigma_zz',1000),(4,'total_sigma_zz_pa',1000),(5,'r_native_pa',1)]:
            axes.flat[index].plot(b[key]/scale,b.z0_m,color=color,label=label)
        axes[0,0].plot(b.porepress0_pa/1000,b.z0_m,':',color=color,label=label+' fixed p0')
        axes[0,1].plot(b.q_current_pa/1000,b.z0_m,'--',color=color,label=label+' current hydro q')
    for prefix,style,name in [('H1_finite_','k--','H1 finite Kw'),('HD_finite_','k:','HD different-domain diagnostic'),('H1_legacy_','k-.','H1 legacy Cv')]:
        for index,key,scale in [(0,'p_pa',1000),(1,'q_pa',1000),(2,'settlement_increment_mm',1),(3,'sigma_zz_pa',1000),(4,'total_sigma_zz_pa',1000)]:
            axes.flat[index].plot(b[prefix+key]/scale,b.z0_m,style,label=name)
    for ax,title in zip(axes.flat,['Final total p / fixed p0 [kPa]','Final native-fixed / current-hydro q [kPa]','Settlement increment [mm]',
                                  'Effective sigma zz [kPa]','Total sigma zz [kPa]','All-layer R [Pa], not an invariant for k>0']):
        ax.set(title=title,ylabel='Initial material z [m]')
    fig.suptitle('Mode3 startup: all 100 layers at actual final save; references quasi-static, not dynamic truth')
    finish(fig,axes,paths['profiles_png'])
    fig,axes=plt.subplots(3,3,figsize=(16,12),constrained_layout=True)
    for label,h in histories.items():
        t=h.time_s*1000; color=colors[label]
        for index,key,scale,style,name in [(0,'bottom_p_pa',1000,'-','bottom p'),(1,'bottom_q_native_pa',1000,'-','fixed p0 native q'),(1,'bottom_q_current_pa',1000,'--','current hydro q'),
                (2,'top_settlement_mm',1,'-','top'),(2,'bottom_settlement_mm',1,'--','bottom'),(3,'bottom_sigma_zz_pa',1000,'-','bottom'),(3,'top_sigma_zz_pa',1000,':','top'),
                (4,'bottom_total_sigma_zz_pa',1000,'-','bottom'),(5,'speed_max_m_s',1,'-','raw |v| max'),(5,'native_H1_vz_residual_rms_m_s',1,'--','H1 signed-vz residual RMS'),(6,'r_excluding_top_rms_pa',1,'-','990 non-top'),
                (7,'H1_finite_pressure_rms_pa',1,'-','H1 finite'),(7,'HD_finite_pressure_rms_pa',1,'--','HD finite'),(8,'H1_finite_settlement_increment_rms_mm',1,'-','H1 finite')]:
            axes.flat[index].plot(t,h[key]/scale,style,color=color,label=label+' '+name)
    for index,key,scale in [(0,'H1_finite_bottom_p_pa',1000),(2,'H1_finite_top_settlement_increment_mm',1),(3,'H1_finite_bottom_sigma_zz_pa',1000),(4,'H1_finite_bottom_total_sigma_zz_pa',1000),(5,'native_H1_reference_absmax_vz_m_s',1)]:
        axes.flat[index].plot(t,h[key]/scale,'k:',label='H1 quasi-static')
    for ax,title in zip(axes.flat,['Bottom p [kPa]','Bottom two q definitions [kPa]','Top/bottom settlement increment [mm]',
            'Effective sigma zz [kPa]','Bottom total sigma zz [kPa]','Raw speed / H1 velocity / residual [m/s]',
            'Direct 990-particle R RMS [Pa]','All-100-layer p reference RMS [Pa]','H1 increment settlement RMS [mm]']):ax.set_title(title)
    fig.suptitle('All 257 actual saves per dyadic step; no smoothing, interpolation or reference-error acceptance gate')
    finish(fig,axes,paths['history_png'],True)
    fig,axes=plt.subplots(2,2,figsize=(13,9),constrained_layout=True)
    for label,h in histories.items():
        e=envelopes[label]; color=colors[label]
        for ax,key,title in zip(axes.flat,['bottom_pressure_H1_residual_pa','top_settlement_H1_residual_mm','bottom_settlement_H1_residual_mm','native_H1_vz_residual_rms_m_s'],
                ['Bottom p minus H1 quasi-static [Pa]','Top increment minus H1 [mm]','Bottom increment minus H1 [mm]','Signed vz minus H1 vz: spatial RMS [m/s]']):
            ax.plot(h.time_s*1000,h[key],color=color,alpha=.6,linewidth=.8,label=label+' actual saves')
            lo,hi=e[key+'_min'],e[key+'_max']; width=(e.actual_end_s-e.actual_start_s)*1000
            ax.bar((e.actual_start_s+e.actual_end_s)*500,hi-lo,bottom=lo,width=width,color=color,alpha=.18,label=label+' fixed 1-ms-bin min/max')
            for boundary in [5,10,20]:ax.axvline(boundary,color='grey',linestyle=':',linewidth=.7)
            ax.set_title(title)
    fig.suptitle('Sampled residual envelopes, not guaranteed wave peaks; t=0 reference velocity undefined; no fitted decay gate')
    finish(fig,axes,paths['envelope_png'],True)


def review(tag):
    paths={key:TESTS/folder/(tag+suffix) for key,folder,suffix in [('check','logs','.check.json'),('profiles_png','figures','_profiles.png'),
        ('history_png','figures','_history.png'),('envelope_png','figures','_envelope.png')]+[(k,'figures','_'+k+'.csv') for k in ['profiles','final_profiles','history','windows','envelope','native_endpoints','half_pairs']]}
    assert not any(p.exists() for p in paths.values()),'Fresh offline tag required; never overwrite retained results'
    check=worker.read(worker.CHECK); assert check['passed'] and len(check['jobs'])==2 and not check['held_jobs']
    records=[worker.bound(worker.CHECK),check['run']]+check['jobs']; worker.verify(records); run=worker.read(check['run']['path'])
    assert run['status']=='mode3_dyadic_window_half_passed_pending_physical_review' and run['jobs']==check['jobs'] and run['finished_utc']
    worker.verify([run['prepared']]); prepared=worker.read(run['prepared']['path']); assert len(prepared['jobs'])==2
    assert prepared['source_program_attribution']==check['source_program_attribution'] and not prepared['source_program_attribution']['exact_HG_source_at_build_time_proven']
    assert prepared['no_same_dt_short_prefix'] and prepared['jobs'][0]['program']==prepared['jobs'][1]['program'] and prepared['jobs'][0]['runtime']==prepared['jobs'][1]['runtime']
    helpers=sorted({Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and str(m.__file__).endswith('.py') and Path(m.__file__).resolve().is_relative_to(worker.CASE.parent)})
    initial=prepared['initial_reference']; records += [run['prepared']]+prepared['inputs']+[worker.bound(p) for p in helpers+[NOTE,TESTS/'notes/sw_delivery_plan_r1.json',TESTS/'notes/sw_mode3_short_review_r1.json']]
    records += [initial['receipt'],initial['completion']]+initial['outputs']; worker.verify(records)
    short_initial=worker.current.native(Path(initial['folder']),0); profiles={}; histories={}; envelopes={}; summaries={}; coarse={}; endpoints=[]; pairs=[]; windows=[]
    for index,(job,rr) in enumerate(zip(prepared['jobs'],check['jobs'])):
        assert job['suffix']==['coarse','half'][index] and job['frames']==257
        receipt=worker.read(rr['path']); assert receipt['passed'] and not receipt['errors'] and len(receipt['rows'])==257 and receipt['initial38_only'] and receipt['no_same_dt_short_prefix']
        assert len(receipt['reader_exits'])==257 and all(r['part']==i and r['exit_code']==0 for i,r in enumerate(receipt['reader_exits']))
        worker.verify([receipt['sealed_completion']]); done=worker.read(receipt['sealed_completion']['path'])
        assert done['solver_finished'] and done['exit_code']==0 and done['owned_exited'] and not done['surviving_owned']
        assert all(done[k]==job[k] for k in ['program','runtime','config','bat'])
        source=next(r for r in receipt['artifacts'] if Path(r['path']).name==job['name']+'_numeric_profiles.csv')
        hist=next(r for r in receipt['artifacts'] if Path(r['path']).name==job['name']+'_history_r.csv')
        records += [rr,receipt['sealed_completion'],job['program'],job['config'],job['bat']]+job['runtime']+done['outputs']+receipt['artifacts']; worker.verify(records)
        assert sum(Path(r['path']).name.startswith('Part_') and Path(r['path']).suffix=='.bi4' for r in done['outputs'])==257
        p=worker.old.parameters(Path(job['config']['path']).read_text(encoding='utf8')); assert p==job['parameters']
        text=(worker.OUTPUTS/job['name']/'Run.out').read_text(errors='replace'); assert worker.hg.parse_hg(text,job)==receipt['hg'] and receipt['hg']['passed']
        raw=pd.read_csv(source['path'],float_precision='round_trip'); same_columns(pd.DataFrame(receipt['rows']),pd.read_csv(hist['path'],float_precision='round_trip'))
        frames,rows,native,pair=native_audit(job,receipt,raw,short_initial,coarse); endpoints+=native; pairs+=pair
        if index==0:coarse=frames
        a,hd=enrich(raw,rows,p,job['name']); h=history(a,rows,job['name']); e=envelope(h)
        profiles[job['suffix']],histories[job['suffix']],envelopes[job['suffix']]=a,h,e; windows.append(window_statistics(h))
        summaries[job['suffix']]=dict(final=h.iloc[-1].to_dict(),initial_reference=receipt['initial_reference'],hg=receipt['hg'],original_profiles=source,original_history=hist,
            H1_m=p['H'],HD_initial_drained_material_plane_m=hd,nominal_undrained_wave_speed_m_s=float(np.sqrt((p['M']+p['Mf'])/p['rho'])),
            nominal_H1_undrained_round_trip_s=float(2*p['H']/np.sqrt((p['M']+p['Mf'])/p['rho'])),wave_scale_is_not_an_exact_dynamic_solution=True)
    assert len(pairs)==257 and all(r['passed'] for r in pairs) and np.array_equal(histories['coarse'].time_s,histories['half'].time_s)
    assert not np.array_equal(histories['coarse'].saved_step.iloc[1:],histories['half'].saved_step.iloc[1:])
    pair_artifact=next(r for r in worker.read(check['jobs'][1]['path'])['artifacts'] if Path(r['path']).name.endswith('_half_pairs.csv'))
    same_columns(pd.DataFrame(pairs).select_dtypes(exclude=['object']),pd.read_csv(pair_artifact['path'],float_precision='round_trip'))
    data=dict(profiles=pd.concat(profiles.values(),ignore_index=True),final_profiles=pd.concat([a[a.part==256] for a in profiles.values()],ignore_index=True),
        history=pd.concat(histories.values(),ignore_index=True),windows=pd.concat(windows,ignore_index=True),envelope=pd.concat(envelopes.values(),ignore_index=True),native_endpoints=pd.DataFrame(endpoints),half_pairs=pd.DataFrame(pairs))
    assert len(data['profiles'])==51400 and len(data['final_profiles'])==200 and len(data['history'])==514 and len(data['native_endpoints'])==10280
    records=worker.unique([dict(r,sha256=r['sha256'].lower()) for r in records]); worker.verify(records)
    for key,a in data.items():
        with paths[key].open('x',encoding='utf8',newline='') as stream:a.to_csv(stream,index=False,float_format='%.17g')
    figures(profiles,histories,envelopes,paths); worker.verify(records)
    worker.seal(paths['check'],dict(analysis_checks_passed=True,inputs=records,jobs=summaries,independently_redecoded_native_frames=515,all_257_half_samples_rechecked=True,
        envelope_bin_s=ENVELOPE_BIN_S,window_policy='Cumulative startup windows overlap; later disjoint bins exclude their left endpoint. Actual saved samples only; no interpolation,curve fit,new threshold or automatic admission.',
        reference_scope='H1 finite-Kw B*Cv quasi-static actual-bulk-initialization diagnostic; legacy Cv reported separately. HD changes domain/initial field and is sensitivity only,not the actual H1 initial-state solution. Neither is exact dynamic startup truth.',
        pressure_scope='Native float32(p-p0),double fixed-p0 and instantaneous mean-drained-material-plane hydro excess are distinct; p0 and native metadata never rewritten.',
        displacement_scope='Material settlement increment since analytical stress initialization,not absolute selfweight displacement or paper zero-p loading.',
        velocity_scope='Signed reference vz=-d(incremental settlement)/dt; residual vz+ds_ref/dt/1000 removes expected quasi-static motion descriptively. t=0 derivative undefined/NaN and excluded,not assigned zero. Raw speed is not equated to wave amplitude; sampled saves need not capture all dynamic peaks.',
        source_program_attribution=prepared['source_program_attribution'],short_comparison='Initial38 only; changed dt means no same-dt short prefix.',
        no_theory_accuracy_gate_applied=True,physical_acceptance=False,automatic_full_run_admitted=False,restart_admitted=False,formal_acceptance=False,
        solver_started=False,new_half_run=False,figures_require_visual_review=True,artifacts=[worker.bound(p) for key,p in paths.items() if key!='check']))
    return dict(check=str(paths['check']),analysis_checks_passed=True,physical_acceptance=False)


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8')); assert worker.selftest()['passed']
    p=worker.old.parameters(worker.expected(worker.JOBS[0],worker.CASE/'private/solver.exe')[0]); z=np.array([0.,.005,.995,1.]); B=p['Mf']/(p['M']+p['Mf'])
    first=theory.reference(z,0.,p); assert np.array_equal(first['q_pa'],B*(p['rho']-p['rho_w'])*p['g']*(p['H']-z)) and np.all(first['settlement_increment_mm']==0)
    late=theory.reference(z,100.,p); assert abs(late['settlement_increment_mm'][-1]-B*(p['rho']-p['rho_w'])*p['g']*p['H']**2/(2*p['M'])*1000)<1e-10
    assert abs(late['finite_Kw_Tv']-B*late['legacy_Tv'])<1e-10 and abs(theory.reference(z,.01,p)['q_pa'][-1])<1e-9
    rate=settlement_rate(z,.01,p); difference=(theory.reference(z,.0100001,p)['settlement_increment_mm']-theory.reference(z,.0099999,p)['settlement_increment_mm'])/2e-7
    np.testing.assert_allclose(rate,difference,rtol=1e-7,atol=1e-7); assert np.isnan(settlement_rate(z,0.,p)).all() and rate[-1]>0
    synthetic=[]; rows=[]
    for part,t in enumerate([0.,.01]):
        rows.append(dict(part=part,time_s=t,natural_step=part,saved_step=0))
        for layer in range(100):
            synthetic.append(dict(part=part,time_s=t,natural_step=part,layer=layer,z0_m=(layer+.5)*.01,z_m=(layer+.5)*.01,
                pressure_pa=1.,porepress0_pa=0.,excess_native_pa=1.,settlement_mm=0.,sigma_xx=0.,sigma_yy=0.,sigma_zz=0.,
                total_sigma_zz_pa=-1.,r_native_pa=1.,vz=0.))
    enriched,_=enrich(pd.DataFrame(synthetic),rows,p,'synthetic'); hs=history(enriched,rows,'synthetic')
    assert hs.H1_finite_bottom_vertical_velocity_m_s.isna().iloc[0] and hs.H1_finite_top_vertical_velocity_m_s.iloc[-1]<0
    times=np.arange(257)*float(worker.JOBS[0]['interval']); h=pd.DataFrame(dict(job='synthetic',time_s=times))
    for key in ['bottom_pressure_H1_residual_pa','top_settlement_H1_residual_mm','bottom_settlement_H1_residual_mm','native_H1_vz_residual_rms_m_s']:h[key]=(-1.)**np.arange(257)
    h.loc[0,'native_H1_vz_residual_rms_m_s']=np.nan
    e=envelope(h); assert int(e.samples.sum())==257 and e.iloc[0].bottom_pressure_H1_residual_pa_min==-1 and e.iloc[0].bottom_pressure_H1_residual_pa_max==1
    a=pd.DataFrame(dict(x=[0.,1.])); same_columns(a,a.copy())
    return dict(passed=True,files_written=False,native_reader_started=False,solver_started=False,live_output_read=False,frames_per_job=257)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); modes=parser.add_mutually_exclusive_group(); modes.add_argument('--selftest',action='store_true'); modes.add_argument('--review',action='store_true')
    parser.add_argument('--tag',default=TAG); args=parser.parse_args(); assert args.tag and Path(args.tag).name==args.tag and args.tag.replace('_','').isalnum()
    if args.selftest:print(json.dumps(selftest()))
    elif args.review:print(json.dumps(review(args.tag)))
    else:parser.print_help()
