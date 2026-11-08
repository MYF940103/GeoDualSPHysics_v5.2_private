"""Compare two closed C08 dense traces; no solver, native decode or repeated algebra review."""
import argparse,json,math,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import upl_c08_stage_trace_window_review_r1 as trace

T=Path(__file__).resolve().parents[1];TAG='upl_c08_as05_trace_compare_r1';PREFIX=T/'figures'/TAG
BASE_CHECK=T/'logs/upl_c08_stage_trace_window_GPU_r1.trace.check.json'
JOBS=('upl_c08_stage_trace_window_GPU_r1','upl_c08_as05_window_GPU_r2');EPSILONS=(.2,.5)
COLS=['step_start_s','nstep','interstep','event','native_id','FSType','p_before_Pa','p_after_Pa','rate_before_Pa_s','rate_after_Pa_s','stored_dt_s','operator_dt_s','value_double','ponding_changed','J','n','theta','pos0','pos2','LP','lap','chain','ki']
PRESSURES=('p_n_Pa','p_half_Pa','p_full_prepond_Pa','p_full_postpond_Pa')
WINDOWS=((.619,.621),(.625,.627),(.635,.637))
need,stat=trace.need,trace.stat

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def bind(e):need(stat(e['path'])==e,'Closed input stat changed: '+e['path']);return e
def same64(a,b):return np.array_equal(np.asarray(a,dtype='<f8').view('<u8'),np.asarray(b,dtype='<f8').view('<u8'))
def physics(node):
    need(node is not None,'Missing actual execution XML block');attrs={k:v for k,v in node.attrib.items() if k!='comment' and not k.endswith('_comment')}
    if node.tag=='parameter' and node.get('key')=='ArtificialStressCoef':attrs['value']='CONTROLLED_EPSILON'
    return node.tag,tuple(sorted(attrs.items())),(node.text or '').strip(),tuple(physics(x) for x in node)
def export(path,rows):
    pd.DataFrame(rows).to_csv(path,index=False,mode='x',float_format='%.17g')

def rhs_windows(data,job,anchor):
    rows=[];rhs=data[data.event==1].copy();rhs['tau_s']=rhs.step_start_s-anchor
    for identity in trace.IDS:
        for stage in (2,3):
            own=rhs[(rhs.native_id==identity)&(rhs.interstep==stage)]
            selections=(('startup_le_0p25',own.tau_s<=.25),('stagnation_0p25_to_0p35',(own.tau_s>.25)&(own.tau_s<=.35)),('late_0p60_to_0p66',(own.tau_s>=.60)&(own.tau_s<=.66)))
            for label,mask in selections:
                d=own[mask];need(len(d)>0,'Empty declared RHS window');B=1e9/d.n.to_numpy();factor=B*d.ki.to_numpy()/(1000*9.80665)
                terms=dict(compression=-B*d.theta.to_numpy(),LP=factor*d.LP.to_numpy(),remaining_lap_defect_and_Ace=factor*(d.lap.to_numpy()-d.LP.to_numpy()),k_chain=B*d.chain.to_numpy()/(1000*9.80665))
                for term,v in terms.items():
                    need(np.isfinite(v).all(),'Nonfinite derived RHS contribution');rows.append(dict(group=job,native_id=identity,interstep=stage,window=label,term=term,samples=len(d),first_actual_tau_s=float(d.tau_s.iloc[0]),last_actual_tau_s=float(d.tau_s.iloc[-1]),FS23_samples=int(d.FSType.isin((2,3)).sum()),mean_Pa_s=float(v.mean()),RMS_Pa_s=float(np.sqrt(np.mean(v*v))),maxabs_Pa_s=float(np.abs(v).max()),min_Pa_s=float(v.min()),max_Pa_s=float(v.max())))
    return rows

def load(job,epsilon,check):
    rp=T/'logs'/(job+'.run.json');r,q=read(rp),read(check)
    need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==trace.END and r['saved_frames']==66 and r['consumed_stats_unchanged'],'Closed normal66-frame run required: '+job)
    need(q['stage']=='upl_c08_stage_trace_window_review_r1' and q['passed'] and q['CSV_consistency_checked'] and q['profile']=='window' and q['extra_true_events_preserved'],'Passed original window algebra check required')
    obs=q['observations'];need(obs['rows']==450003 and len(obs['sampled_steps'])==30000,'Original complete450003-row/30000-step trace required')
    entry=bind(q['trace']);need(entry==r['trace_file'],'Algebra check must bind this actual job trace');path=Path(entry['path'])
    need(path.name=='C08StageTrace.csv' and T/'outputs' in path.parents,'Actual test trace path required')
    xml=ET.parse(bind(r['input_xml'])['path']).getroot();coef=[x for x in xml.findall('execution/parameters/parameter') if x.get('key')=='ArtificialStressCoef']
    need(len(coef)==1 and np.float32(coef[0].get('value'))==np.float32(epsilon),'Actual XML epsilon differs')
    before=[stat(rp),stat(check),entry,r['input_xml']];anchor=float(r['actual_source_time_from_loader'])
    # One full CSV pass; original checker already validates all57 columns and every algebra/cast gate.
    data=pd.read_csv(path,usecols=COLS,float_precision='round_trip');need(len(data)==obs['rows'],'Closed raw row count differs')
    steps=[];extras=[];initial=data[data.nstep==trace.START].copy();initial.insert(0,'epsilon',epsilon);initial.insert(0,'group',job)
    for identity in trace.IDS:
        own=data[data.native_id==identity];parts=[own[(own.event==event)&(own.interstep==stage)].set_index('nstep',drop=False) for event,stage in ((1,2),(2,2),(1,3),(2,3))];pr,pu,cr,cu=parts
        for p in parts:need(p.nstep.tolist()==obs['sampled_steps'] and same64(p.step_start_s,pr.step_start_s),'Genuine same-stage sampled clocks/steps differ')
        pond=own[own.event==3];tail=pond.groupby('nstep',sort=False).tail(1);last=tail.set_index('nstep',drop=False)
        need(last.nstep.tolist()==obs['sampled_steps'] and same64(last.step_start_s,pr.step_start_s),'Every sampled step requires actual trailing ponding')
        extra=pond[~pond.index.isin(tail.index)];extra=extra.copy();extra.insert(0,'epsilon',epsilon);extra.insert(0,'group',job);extras.append(extra)
        dt=cu.operator_dt_s.to_numpy();pn=pu.p_before_Pa.to_numpy();half=pu.p_after_Pa.to_numpy();pre=cu.p_after_Pa.to_numpy();post=last.p_after_Pa.to_numpy()
        row=pd.DataFrame(dict(group=job,epsilon=epsilon,nstep=pr.nstep.to_numpy(),step_start_s=pr.step_start_s.to_numpy(),tau_s=pr.step_start_s.to_numpy()-anchor,native_id=identity,predictor_FSType=pr.FSType.to_numpy(),corrector_FSType=cr.FSType.to_numpy(),ponding_FSType=last.FSType.to_numpy(),p_n_Pa=pn,p_half_Pa=half,p_full_prepond_Pa=pre,p_full_postpond_Pa=post,ponding_increment_Pa=post-pre,corrector_rate_cast_increment_Pa=dt*(cu.rate_before_Pa_s.to_numpy()-cr.value_double.to_numpy()),corrector_update_rounding_increment_Pa=(pre-pn)-dt*cu.rate_before_Pa_s.to_numpy(),ponding_changed=last.ponding_changed.to_numpy()))
        need(np.isfinite(row[list(PRESSURES)]).all().all(),'Nonfinite stage pressure');steps.append(row)
    need(sum(len(x) for x in extras)==3*(obs['extra_leading_ponding_events']+obs['extra_trailing_ponding_events']),'An extra genuine ponding record was dropped')
    return dict(job=job,epsilon=epsilon,run=r,check=q,anchor=anchor,before=before,steps=pd.concat(steps,ignore_index=True).sort_values(['nstep','native_id']),extras=pd.concat(extras,ignore_index=True),initial=initial,RHS_windows=rhs_windows(data,job,anchor),physics=tuple(physics(xml.find('execution/'+k)) for k in ('special','parameters')))

def frequencies(own,identity,group):
    rows=[]
    for lo,hi in WINDOWS:
        d=own[(own.tau_s>=lo)&(own.tau_s<hi)];time=d.tau_s.to_numpy();p=d.p_full_prepond_Pa.to_numpy()
        need(len(p)>2 and np.all(np.diff(d.nstep)==1) and np.all(np.diff(time)>0),'Frequency window must contain original consecutive dense steps')
        dt=float(np.diff(time).mean());centered=p-p.mean();rms=float(np.sqrt(np.mean(centered**2)));freq=np.fft.rfftfreq(len(p),dt);spec=np.abs(np.fft.rfft(centered*np.hanning(len(p))))
        peak=1+int(np.argmax(spec[1:])) if rms>0 else None
        rows.append(dict(group=group,native_id=identity,requested_start_s=lo,requested_end_s=hi,first_actual_tau_s=float(time[0]),last_actual_tau_s=float(time[-1]),actual_center_tau_s=float(time.mean()),samples=len(p),actual_mean_dt_s=dt,p_prepond_mean_Pa=float(p.mean()),demeaned_RMS_Pa=rms,Hann_peak_Hz=None if peak is None else float(freq[peak]),FFT_bin_width_Hz=float(freq[1])))
    a,b=rows[0],rows[-1];gap=b['actual_center_tau_s']-a['actual_center_tau_s'];ratio=b['demeaned_RMS_Pa']/a['demeaned_RMS_Pa'] if a['demeaned_RMS_Pa']>0 else None
    growth=dict(group=group,native_id=identity,early_RMS_Pa=a['demeaned_RMS_Pa'],late_RMS_Pa=b['demeaned_RMS_Pa'],center_gap_s=gap,RMS_ratio=ratio,descriptive_RMS_log_growth_per_s=math.log(ratio)/gap if ratio is not None and ratio>0 else None)
    return rows,growth

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--candidate-check',type=Path,required=True);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root review before one offline comparison required')
    candidate=args.candidate_check.resolve();need(candidate.parent==T/'logs' and not list(PREFIX.parent.glob(TAG+'*')),'Actual candidate check/fresh outputs required');dest=Path(str(PREFIX)+'.check.json');files=[];before=[];result=dict(stage=TAG,passed=False,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0)
    try:
        groups=[load(job,e,check) for job,e,check in zip(JOBS,EPSILONS,(BASE_CHECK,candidate))];a,b=groups
        need(a['run']['program']==b['run']['program'] and a['run']['source_pre_file']==b['run']['source_pre_file'] and a['run']['source_build']==b['run']['source_build'] and a['anchor']==b['anchor'] and a['physics']==b['physics'],'Same program/PRE/source clock and physics except epsilon required')
        before=[stat(__file__),stat(T/'notes'/(TAG+'.md')),stat(trace.__file__)]+[x for g in groups for x in g['before']]
        da,db=a['steps'],b['steps'];need(np.array_equal(da[['nstep','native_id']],db[['nstep','native_id']]) and same64(da.step_start_s,db.step_start_s) and same64(da.tau_s,db.tau_s),'Only exact same sampled step/actual-time comparisons admitted')
        extrema=[];freq=[];growth=[];switches=[];rounding=[]
        for g in groups:
            for identity in trace.IDS:
                own=g['steps'][g['steps'].native_id==identity]
                for scope,d in (('all_recorded_starts',own),('dense_all_steps',own[own.nstep>=trace.DENSE])):
                    for channel in PRESSURES:
                        values=d[channel].to_numpy();i,j=int(np.argmin(values)),int(np.argmax(values));extrema.append(dict(group=g['job'],epsilon=g['epsilon'],native_id=identity,scope=scope,channel=channel,samples=len(d),min_Pa=float(values[i]),max_Pa=float(values[j]),recorded_sample_RMS_Pa=float(np.sqrt(np.mean(values**2))),min_nstep=int(d.iloc[i].nstep),max_nstep=int(d.iloc[j].nstep),min_actual_tau_s=float(d.iloc[i].tau_s),max_actual_tau_s=float(d.iloc[j].tau_s)))
                f,w=frequencies(own,identity,g['job']);freq.extend(f);growth.append(w)
                for phase in ('predictor','corrector','ponding'):
                    values=own[phase+'_FSType'].to_numpy();idx=np.flatnonzero(values[1:]!=values[:-1])+1
                    for i in idx:
                        prev,now=own.iloc[i-1],own.iloc[i];switches.append(dict(group=g['job'],native_id=identity,phase=phase,previous_sampled_step=int(prev.nstep),nstep=int(now.nstep),previous_actual_tau_s=float(prev.tau_s),actual_tau_s=float(now.tau_s),FS_before=int(values[i-1]),FS_after=int(values[i]),between_samples_consecutive_steps=bool(now.nstep-prev.nstep==1)))
                rounding.append(dict(group=g['job'],native_id=identity,rate_cast_increment_max_abs_Pa=float(own.corrector_rate_cast_increment_Pa.abs().max()),update_rounding_increment_max_abs_Pa=float(own.corrector_update_rounding_increment_Pa.abs().max()),positive_half_FS23_count=int(((own.corrector_FSType.isin((2,3)))&(own.p_half_Pa>0)).sum()),positive_full_prepond_FS23_count=int(((own.ponding_FSType.isin((2,3)))&(own.p_full_prepond_Pa>0)).sum()),ponding_changed_count=int(own.ponding_changed.sum())))
        tables=dict(steps=pd.concat([g['steps'] for g in groups],ignore_index=True),extra_ponding=pd.concat([g['extras'] for g in groups],ignore_index=True),initial_events=pd.concat([g['initial'] for g in groups],ignore_index=True),extrema=extrema,frequency_windows=freq,growth=growth,FS_transitions=switches,cast_rounding=rounding,RHS_windows=[row for g in groups for row in g['RHS_windows']])
        for leaf,rows in tables.items():path=Path(str(PREFIX)+'_'+leaf+'.csv');export(path,rows);files.append(path)
        plt.rcParams.update({'font.size':8,'figure.dpi':160});fig,axes=plt.subplots(3,2,figsize=(15,10),layout='constrained')
        for row,identity in enumerate(trace.IDS):
            for col,dense in enumerate((False,True)):
                ax=axes[row,col]
                for g,color in zip(groups,('C0','C1')):
                    d=g['steps'][g['steps'].native_id==identity];d=d[d.nstep>=trace.DENSE] if dense else d
                    channels=(('p_full_prepond_Pa','-'),('p_full_postpond_Pa','--'))+((('p_half_Pa',':'),) if dense else ())
                    for name,style in channels:
                        ax.plot(d.tau_s,d[name]/1000,style,c=color,lw=.7,label='epsilon '+str(g['epsilon'])+' '+name)
                ax.set(title=str(identity)+(' dense every step' if dense else ' actual early40-step/dense sampling'),xlabel='Actual recorded step-start tau [s]',ylabel='Raw total p [kPa]');ax.grid(alpha=.25);ax.legend(fontsize=5)
        fig.suptitle('Stage pressures: same program/PRE, epsilon .2 vs .5; no re-timing/interpolation/clipping; early unsampled peaks unknown');path=Path(str(PREFIX)+'_pressure.png');fig.savefig(path);plt.close(fig);files.append(path)
        need(all(stat(e['path'])==e for e in before),'Closed input/helper changed during comparison')
        initial_equal={str(identity):bool(same64(da[(da.native_id==identity)&(da.nstep==trace.START)].p_n_Pa,db[(db.native_id==identity)&(db.nstep==trace.START)].p_n_Pa)) for identity in trace.IDS}
        result.update(passed=True,analysis_completed=True,groups=list(JOBS),source_actual_time_s=a['anchor'],each_trace_rows=450003,sampled_steps_per_ID_per_group=30000,initial_three_ID_pn_bits_equal=initial_equal,original_algebra_checks={g['job']:g['check']['observations']['roundoff_checks'] for g in groups},original_cast_and_sequence_checks_reused_not_rerun=True,all_extra_ponding_records_exported=True,normal_final_ponding_retained_in_steps=True,stage_times_are_recorded_context_not_shifted_half_times=True,FFT_field='full pressure before ponding',FFT_method='demean then Hann, largest nonzero rFFT bin; no zero padding',RMS_growth_not_fitted_eigenvalue=True,no_cross_epsilon_accuracy_gate=True,visual_QA_pending=True)
    except Exception as error:result['first_failure']=str(error)
    result.update(consumed=before,files=[stat(p) for p in files if p.exists()])
    with dest.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],check=str(dest),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
