"""Three-ID ReleasedSubstages trace versus cached completed-only n3 summaries."""
import argparse,json,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import upl_c08_as05_trace_compare_r1 as old
T=old.T;TAG='upl_c08_stage_ponding_trace_compare_r1';PREFIX=T/'figures'/TAG
BASE='upl_c08_asn3_window_GPU_r1';NEW='upl_c08_stage_ponding_window_GPU_r2';CHANNELS=('p_n_Pa','p_half_raw_Pa','p_half_after_Pa','p_full_prepond_Pa','p_full_postpond_Pa')
need,stat,bind=old.need,old.stat,old.bind

def load_new():
    rp=T/'logs'/(NEW+'.run.json');qp=T/'logs/upl_c08_stage_trace_ponding_window_r1.check.json';npth=T/'logs'/(NEW+'.native_r1.json');r,q,n=old.read(rp),old.read(qp),old.read(npth)
    need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==4264000 and r['saved_frames']==66 and r['consumed_stats_unchanged'],'Completed actual new66-frame run required')
    need(q['passed'] and q['stage']=='upl_c08_stage_ponding_review_r1' and q['profile']=='window' and q['CSV_consistency_checked'] and q['released_half_projection_checked'] and q['half_projection_preserves_saved_old_step_base'] and q['extra_true_events_preserved'],'Passed new half-aware original algebra review required')
    need(n['passed'] and n['original_native_guards_passed'] and n['consumed_stats_unchanged'] and bind(n['source_run'])==stat(rp),'Actual new policy native guards required');m=old.read(bind(n['metadata'])['path']);need(m['passed'] and m['samples']==66 and m['FreeSeepagePondingPolicy']=='ReleasedSubstages' and m['FreeSeepagePondingActive'] and m['AS_exponent_float_reference']==3. and m['AS_coefficient_float_reference']==float(np.float32(.2)),'Typed actual new policy/AS metadata differs')
    obs=q['observations'];need(obs['rows']==540003 and len(obs['sampled_steps'])==obs['half_ponding_events']==30000,'Complete540003-row new trace and30000 actual half events required');entry=bind(q['trace']);need(entry==r['trace_file'],'Actual checked CSV differs from run');anchor=float(r['actual_source_time_from_loader'])
    before=[stat(rp),stat(qp),stat(npth),entry,r['input_xml'],n['metadata']]
    # The sole raw CSV read; its57-column arithmetic has already passed, and is not rerun here.
    data=pd.read_csv(entry['path'],usecols=old.COLS,float_precision='round_trip');need(len(data)==540003,'Actual closed trace row count differs');data['_row']=np.arange(len(data));steps=[];extras=[]
    for identity in old.trace.IDS:
        own=data[data.native_id==identity];parts=[own[(own.event==event)&(own.interstep==stage)].set_index('nstep',drop=False) for event,stage in ((1,2),(2,2),(1,3),(2,3))];pr,pu,cr,cu=parts
        for p in parts:need(p.nstep.tolist()==obs['sampled_steps'] and old.same64(p.step_start_s,pr.step_start_s),'Actual original core step/clock sequence differs')
        pond=own[own.event==3];half=pond[(pond.interstep==2)&(pond._row>pond.nstep.map(pu._row))&(pond._row<pond.nstep.map(cr._row))];hp=half.set_index('nstep',drop=False)
        # Row position is essential: an initial leading event can also carry interstep2.
        need(hp.nstep.tolist()==obs['sampled_steps'] and old.same64(hp.step_start_s,pr.step_start_s),'Exactly one genuine between-update-and-RHS half projection per sampled step required')
        tail=pond[pond._row>pond.nstep.map(cu._row)].groupby('nstep',sort=False).tail(1);last=tail.set_index('nstep',drop=False);need(last.nstep.tolist()==obs['sampled_steps'] and old.same64(last.step_start_s,pr.step_start_s),'Actual final ponding missing')
        extra=pond[~pond._row.isin(pd.concat((half._row,tail._row)))].copy();extra.insert(0,'group',NEW);extras.append(extra.drop(columns='_row'))
        row=pd.DataFrame(dict(group=NEW,epsilon=.2,nstep=pr.nstep.to_numpy(),step_start_s=pr.step_start_s.to_numpy(),tau_s=pr.step_start_s.to_numpy()-anchor,native_id=identity,p_n_Pa=pu.p_before_Pa.to_numpy(),p_half_raw_Pa=pu.p_after_Pa.to_numpy(),p_half_after_Pa=hp.p_after_Pa.to_numpy(),p_full_prepond_Pa=cu.p_after_Pa.to_numpy(),p_full_postpond_Pa=last.p_after_Pa.to_numpy(),half_projection_increment_Pa=hp.p_after_Pa.to_numpy()-hp.p_before_Pa.to_numpy(),half_FSType=hp.FSType.to_numpy(),half_projection_changed=hp.ponding_changed.to_numpy()))
        need(np.isfinite(row[list(CHANNELS)]).all().all(),'Nonfinite extracted stage pressure');steps.append(row)
    need(sum(len(d) for d in extras)==3*(obs['extra_leading_ponding_events']+obs['extra_trailing_ponding_events']),'A true extra ponding event was lost')
    initial=data[data.nstep==old.trace.START].drop(columns='_row').copy();initial.insert(0,'group',NEW)
    return dict(run=r,anchor=anchor,before=before,steps=pd.concat(steps,ignore_index=True),extras=pd.concat(extras,ignore_index=True),initial=initial,RHS=old.rhs_windows(data,NEW,anchor))

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full-read before one offline three-ID analysis');need(not list(PREFIX.parent.glob(TAG+'*')),'Fresh output prefix required');dest=Path(str(PREFIX)+'.check.json');before=[];files=[];result=dict(stage=TAG,passed=False,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,queue_invocations=0,SHA_scans=0)
    try:
        cache=T/'figures/upl_c08_asn3_trace_compare_r1.check.json';c=old.read(cache);need(c['passed'] and c['analysis_completed'] and c['original_algebra_checks_reused_not_rerun'],'Passed existing n3 summary analysis required');entries={Path(e['path']).name:e for e in c['files']};tables={}
        for leaf in ('extrema','frequency_windows','growth','RHS_windows'):
            entry=bind(entries['upl_c08_asn3_trace_compare_r1_'+leaf+'.csv']);d=pd.read_csv(entry['path'],float_precision='round_trip');tables[leaf]=d[d.group==BASE].copy();before.append(entry)
        basepath=T/'logs'/(BASE+'.run.json');br=old.read(basepath);need(stat(basepath) in c['consumed'] and br['passed'] and br['actual_exit']==br['actual_Win32_exit']==0,'Cached n3 must bind its actual completed run');g=load_new();r=g['run'];need(r['source_pre_file']==br['source_pre_file'] and g['anchor']==c['source_actual_time_s']==float(br['actual_source_time_from_loader']),'Same original PRE and actual source clock required')
        physics=[]
        for run in (br,r):
            xml=ET.parse(bind(run['input_xml'])['path']).getroot();p={x.get('key'):x.get('value') for x in xml.findall('execution/parameters/parameter')};need(float(p['ArtificialStressCoef'])==.2 and float(p['ArtificialStressExp'])==3.,'Same epsilon.2/exponent3 actual XML required');physics.append(tuple(old.physics(xml.find('execution/'+section)) for section in ('special','parameters')))
        need(physics[0]==physics[1],'Actual physical XML differs beyond the explicitly changed program policy');before += [stat(__file__),stat(T/'notes'/(TAG+'.md')),stat(old.__file__),stat(cache),stat(basepath),br['input_xml']]+g['before']
        rows=[];freq=[];growth=[]
        for identity in old.trace.IDS:
            own=g['steps'][g['steps'].native_id==identity]
            for scope,d in (('all_recorded_starts',own),('startup_recorded_before_dense',own[own.nstep<old.trace.DENSE]),('dense_all_steps',own[own.nstep>=old.trace.DENSE])):
                for name in CHANNELS:
                    v=d[name].to_numpy();i,j=int(np.argmin(v)),int(np.argmax(v));rows.append(dict(group=NEW,epsilon=.2,native_id=identity,scope=scope,channel=name,samples=len(d),min_Pa=float(v[i]),max_Pa=float(v[j]),recorded_sample_RMS_Pa=float(np.sqrt(np.mean(v*v))),min_nstep=int(d.iloc[i].nstep),max_nstep=int(d.iloc[j].nstep),min_actual_tau_s=float(d.iloc[i].tau_s),max_actual_tau_s=float(d.iloc[j].tau_s)))
            f,w=old.frequencies(own,identity,NEW);freq.extend(f);growth.append(w)
        baseex=tables['extrema'].copy();baseex.loc[baseex.channel=='p_half_Pa','channel']='p_half_raw_Pa';basehalf=baseex[baseex.channel=='p_half_raw_Pa'].copy();basehalf['channel']='p_half_after_Pa';baseex=pd.concat((baseex,basehalf),ignore_index=True)
        pairs=[];newfreq=pd.DataFrame(freq)
        for identity in old.trace.IDS:
            x=tables['frequency_windows'][tables['frequency_windows'].native_id==identity];y=newfreq[newfreq.native_id==identity]
            for key in ('requested_start_s','requested_end_s','first_actual_tau_s','last_actual_tau_s','actual_center_tau_s','actual_mean_dt_s'):need(old.same64(x[key],y[key]),'Narrow-window actual clock pairing differs: '+key)
            need(np.array_equal(x.samples,y.samples),'Actual narrow-window counts differ')
            for (_,u),(_,v) in zip(x.iterrows(),y.iterrows()):pairs.append(dict(native_id=identity,requested_start_s=u.requested_start_s,requested_end_s=u.requested_end_s,first_actual_tau_s=u.first_actual_tau_s,last_actual_tau_s=u.last_actual_tau_s,samples=int(u.samples),baseline_demeaned_RMS_Pa=u.demeaned_RMS_Pa,new_demeaned_RMS_Pa=v.demeaned_RMS_Pa,RMS_new_over_baseline=v.demeaned_RMS_Pa/u.demeaned_RMS_Pa if u.demeaned_RMS_Pa>0 else None,baseline_Hann_peak_Hz=u.Hann_peak_Hz,new_Hann_peak_Hz=v.Hann_peak_Hz,FFT_bin_width_Hz=u.FFT_bin_width_Hz))
        outputs=dict(extrema=pd.concat((baseex,pd.DataFrame(rows)),ignore_index=True),frequency_windows=pd.concat((tables['frequency_windows'],newfreq),ignore_index=True),frequency_pairs=pairs,growth=pd.concat((tables['growth'],pd.DataFrame(growth)),ignore_index=True),RHS_windows=pd.concat((tables['RHS_windows'],pd.DataFrame(g['RHS'])),ignore_index=True),new_initial_events=g['initial'],new_extra_ponding=g['extras'])
        for leaf,table in outputs.items():p=Path(str(PREFIX)+'_'+leaf+'.csv');old.export(p,table);files.append(p)
        plt.rcParams.update({'font.size':8,'figure.dpi':160});fig,axes=plt.subplots(3,2,figsize=(15,10),layout='constrained')
        for row,identity in enumerate(old.trace.IDS):
            for col,dense in enumerate((False,True)):
                d=g['steps'][g['steps'].native_id==identity];d=d[d.nstep>=old.trace.DENSE] if dense else d;ax=axes[row,col]
                for name,style in zip(CHANNELS,('-','--',':','-','--')):ax.plot(d.tau_s,d[name]/1000,style,lw=.7,label=name)
                ax.set(title=str(identity)+(' every-step dense window' if dense else ' actual early40-step/dense samples'),xlabel='Actual step-start tau [s]',ylabel='Raw p [kPa]');ax.grid(alpha=.25);ax.legend(fontsize=6)
        fig.suptitle('ReleasedSubstages only: raw half update and force-consumed projected half shown separately; no filtering/re-timing/clipping');p=Path(str(PREFIX)+'_pressure.png');fig.savefig(p);plt.close(fig);files.append(p)
        need(all(stat(e['path'])==e for e in before),'Consumed closed input/helper changed');result.update(passed=True,analysis_completed=True,groups=[BASE,NEW],source_actual_time_s=g['anchor'],new_raw_CSV_passes=1,baseline_raw_CSV_passes=0,original540003_row_algebra_reused_not_rerun=True,three_fixed_native_IDs=list(old.trace.IDS),sampled_steps_per_ID=30000,dense_steps_per_ID=24000,new_half_after_is_actual_between_UPDATE2_and_RHS3=True,baseline_half_after_uses_checked_unprojected_half_identity=True,new_extra_ponding_rows=len(g['extras']),narrow_windows_actual_clocks_paired=True,baseline_step_series_not_reread=True,programs_are_different=(r['program']!=br['program']),FFT_field='full pressure before final ponding',FFT_method='same actual narrow windows; demean then Hann largest nonzero rFFT bin, no padding',RMS_growth_not_fitted_eigenvalue=True,startup_RMS_is_sample_RMS_not_time_weighted=True,no_cross_policy_accuracy_gate=True,visual_QA_pending=True)
    except Exception as error:result['first_failure']=str(error)
    result.update(consumed=before,files=[stat(p) for p in files if p.exists()])
    with dest.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],check=str(dest),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
