"""Derived genuine-stage C08 terms, only after the closed window CSV checker passes."""
import argparse,csv,json,math
from array import array
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import upl_c08_stage_trace_window_review_r1 as trace

T=Path(__file__).resolve().parents[1];TAG='upl_c08_stage_trace_terms_r1'
PROFILES={'window':('upl_c08_stage_trace_window_GPU_r1',4264000,66),'short':('upl_c08_stage_trace_smoke_Release_r1',4012000,3)}
IDS=trace.IDS;KW=1e9;RW=1000.;GAMMA=RW*9.80665
TERMS=('compression','LP','interior_defect','FS_Ace_L','divAce','k_chain')
BASE=trace.HEADER[:13]
EVENT_FIELDS=BASE+['tau_s','observed_p_increment_Pa','J','n','theta','divAce','raw_FS_branch']+[x+'_Pa_s' for x in TERMS]+['sum_terms_Pa_s','value_double','sum_minus_value_Pa_s','ponding_changed']
STEP_FIELDS=['nstep','step_start_s','tau_s','native_id','predictor_FSType','corrector_FSType','ponding_FSType','p_n_Pa','p_half_Pa','p_full_prepond_Pa','p_full_postpond_Pa','actual_prepond_increment_Pa','actual_ponding_increment_Pa','actual_full_increment_Pa']
STEP_FIELDS += [s+'_'+k for s in ('predictor','corrector') for k in ('J','n','theta','divAce')]
STEP_FIELDS += [s+'_'+k+'_Pa_s' for s in ('predictor','corrector') for k in TERMS]
STEP_FIELDS += [s+'_'+k for s in ('predictor','corrector') for k in ('value_double_Pa_s','rate_float_Pa_s')]+['corrector_delta_'+k+'_Pa' for k in TERMS]+['rate_cast_increment_Pa','update_rounding_increment_Pa','RHS_recomposition_increment_Pa','leading_ponding_events','trailing_ponding_events']
need=trace.need

def stat(path):
 p=Path(path).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)

def terms(r):
 f=lambda k:float(r[k]);pref=KW/f('n');ki=f('ki');A=[f('finishedAce'+str(i)) for i in range(3)];L=[f('Lx'+str(i)) for i in range(3)];G=[f('GpCorr'+str(i)) for i in range(3)];free=bool(f('raw_FS_branch'))
 return dict(zip(TERMS,(-pref*f('theta'),pref*ki/GAMMA*f('LP'),0. if free else -pref*ki/GAMMA*sum(a*b for a,b in zip(G,L)),pref*ki/GAMMA*RW*sum(a*b for a,b in zip(A,L)) if free else 0.,pref*ki/GAMMA*RW*f('divAce'),pref/GAMMA*f('chain'))))

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--profile',choices=tuple(PROFILES),default='window');ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full-read before the one offline terms analysis')
 job,end,frames=PROFILES[a.profile];SOURCE=T/'outputs'/job/'C08StageTrace.csv';REVIEW=T/'logs'/(job+'.trace.check.json');RUN=T/'logs'/(job+'.run.json');PREFIX=T/'figures'/(TAG+('_window' if a.profile=='window' else '_short_verify'))
 check=Path(str(PREFIX)+'.check.json');need(not list(PREFIX.parent.glob(PREFIX.name+'*')),'Existing complete/partial derived outputs protected')
 q=json.loads(REVIEW.read_text(encoding='utf-8'));run=json.loads(RUN.read_text(encoding='utf-8'));before=[stat(SOURCE),stat(REVIEW),stat(RUN),stat(__file__),stat(T/'notes'/(TAG+'.md')),stat(Path(trace.__file__))]
 need(q['passed'] and q['profile']==a.profile and q['CSV_consistency_checked'] and q['extra_true_events_preserved'] and q['trace']==before[0],'Passed matching closed trace review required')
 need(run['passed'] and run['actual_exit']==run['actual_Win32_exit']==0 and run['actual_steps']==end and run['saved_frames']==frames and run['consumed_stats_unchanged'] and run['trace_file']==before[0],'Passed matching owned run and CSV binding required')
 anchor=float(run['actual_source_time_from_loader']);need(math.isfinite(anchor),'Actual loader source clock required')
 buffers={i:array('d') for i in IDS};stats={};files=[];counts=dict(rows=0,sampled_steps=0,step_ID_rows=0,leading_ponding_events=0,trailing_ponding_events=0)
 result=dict(stage=TAG,profile=a.profile,passed=False,short_verification_does_not_include_point6_pressure_pulse=a.profile=='short',physical_acceptance=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,raw_CSV_rewritten=False,consumed=before)
 def extreme(identity,phase,name,value,tau,unit):
  key=(identity,phase,name,unit);s=stats.setdefault(key,dict(count=0,positive=0,negative=0,zero=0,min=value,max=value,min_tau_s=tau,max_tau_s=tau));s['count']+=1;s['positive']+=value>0;s['negative']+=value<0;s['zero']+=value==0
  if value<s['min']:s['min']=value;s['min_tau_s']=tau
  if value>s['max']:s['max']=value;s['max_tau_s']=tau
 try:
  ep=Path(str(PREFIX)+'_events.csv');sp=Path(str(PREFIX)+'_steps.csv');files.extend((ep,sp))
  with ep.open('x',encoding='utf-8',newline='') as ef,sp.open('x',encoding='utf-8',newline='') as sf,SOURCE.open(encoding='utf-8-sig',newline='') as src:
   ew=csv.DictWriter(ef,fieldnames=EVENT_FIELDS);ew.writeheader();sw=csv.DictWriter(sf,fieldnames=STEP_FIELDS);sw.writeheader();reader=csv.DictReader(src);need(reader.fieldnames==trace.HEADER,'Original 57-column header differs')
   def finish(group):
    if not group:return
    step=int(group[0]['nstep']);time=float(group[0]['step_start_s'])
    if counts['sampled_steps']==0:need(step==trace.START and time==anchor,'First source-step trace differs from the actual loader clock')
    tau=time-anchor;counts['sampled_steps']+=1
    for identity in IDS:
     rows=[r for r in group if int(r['native_id'])==identity];core={(int(r['event']),int(r['interstep'])):r for r in rows if int(r['event'])!=3};pr,pu,cr,cu=(core[k] for k in ((1,2),(2,2),(1,3),(2,3)));lead=[];trail=[];seen=False;rt={}
     for r in rows:
      event=int(r['event']);phase=int(r['interstep']);counts['rows']+=1
      if event==3:(trail if seen else lead).append(r)
      else:seen=True
      out={k:r[k] for k in BASE};out.update(tau_s=tau,observed_p_increment_Pa=float(r['p_after_Pa'])-float(r['p_before_Pa']),ponding_changed=r['ponding_changed'])
      if event==1:
       t=terms(r);rt[phase]=t;out.update({k:r[k] for k in ('J','n','theta','divAce','raw_FS_branch')});out.update({k+'_Pa_s':v for k,v in t.items()});out.update(sum_terms_Pa_s=sum(t.values()),value_double=r['value_double'],sum_minus_value_Pa_s=sum(t.values())-float(r['value_double']))
       for k,v in t.items():extreme(identity,phase,k,v,tau,'Pa/s')
       extreme(identity,phase,'recorded_value_double',float(r['value_double']),tau,'Pa/s')
      ew.writerow(out)
     need(trail,'Closed review must include actual trailing ponding');final=trail[-1];pn=float(pu['p_before_Pa']);p_half=float(pu['p_after_Pa']);p_pre=float(cu['p_after_Pa']);p_post=float(final['p_after_Pa']);dt=float(cu['operator_dt_s']);rate=float(cu['rate_before_Pa_s']);value=float(cr['value_double'])
     row=dict(nstep=step,step_start_s=time,tau_s=tau,native_id=identity,predictor_FSType=int(pr['FSType']),corrector_FSType=int(cr['FSType']),ponding_FSType=int(final['FSType']),p_n_Pa=pn,p_half_Pa=p_half,p_full_prepond_Pa=p_pre,p_full_postpond_Pa=p_post,actual_prepond_increment_Pa=p_pre-pn,actual_ponding_increment_Pa=p_post-p_pre,actual_full_increment_Pa=p_post-pn,predictor_value_double_Pa_s=float(pr['value_double']),predictor_rate_float_Pa_s=float(pu['rate_before_Pa_s']),corrector_value_double_Pa_s=value,corrector_rate_float_Pa_s=rate,rate_cast_increment_Pa=dt*(rate-value),update_rounding_increment_Pa=(p_pre-pn)-dt*rate,RHS_recomposition_increment_Pa=dt*(value-sum(rt[3].values())),leading_ponding_events=len(lead),trailing_ponding_events=len(trail))
     for phase,label,r in ((2,'predictor',pr),(3,'corrector',cr)):
      row.update({label+'_'+k:float(r[k]) for k in ('J','n','theta','divAce')});row.update({label+'_'+k+'_Pa_s':v for k,v in rt[phase].items()})
     for k,v in rt[3].items():row['corrector_delta_'+k+'_Pa']=dt*v;extreme(identity,3,'corrector_delta_'+k,dt*v,tau,'Pa')
     for k in ('actual_prepond_increment_Pa','actual_ponding_increment_Pa','actual_full_increment_Pa'):extreme(identity,3,k,row[k],tau,'Pa')
     sw.writerow(row);buffers[identity].extend(float(row[k]) for k in STEP_FIELDS);counts['step_ID_rows']+=1
     if identity==IDS[0]:counts['leading_ponding_events']+=len(lead);counts['trailing_ponding_events']+=len(trail)
   group=[]
   for r in reader:
    if group and r['nstep']!=group[0]['nstep']:finish(group);group=[]
    group.append(r)
   finish(group)
  need(counts['rows']==q['observations']['rows'] and counts['sampled_steps']==len(q['observations']['sampled_steps']),'Derived stream omitted/added original rows/steps')
  summary=Path(str(PREFIX)+'_extrema.csv');files.append(summary)
  with summary.open('x',encoding='utf-8',newline='') as f:
   w=csv.DictWriter(f,fieldnames=['native_id','interstep','term','units','count','positive','negative','zero','min','max','min_tau_s','max_tau_s']);w.writeheader()
   for (identity,phase,name,unit),s in sorted(stats.items()):w.writerow(dict(native_id=identity,interstep=phase,term=name,units=unit,**s))
  data={i:np.asarray(buffers[i]).reshape(-1,len(STEP_FIELDS)) for i in IDS};col={k:j for j,k in enumerate(STEP_FIELDS)}
  plt.rcParams.update({'font.size':8,'figure.dpi':170})
  def plots(dense):
   suffix='dense' if dense else 'full';fig,axes=plt.subplots(3,3,figsize=(16,11),layout='constrained')
   for ii,identity in enumerate(IDS):
    d=data[identity];d=d[d[:,col['nstep']]>=trace.DENSE] if dense else d;x=d[:,col['tau_s']]
    ax=axes[ii,0]
    for k,label in (('p_n_Pa','old p_n'),('p_half_Pa','half update'),('p_full_prepond_Pa','full before ponding'),('p_full_postpond_Pa','full after ponding')):ax.plot(x,d[:,col[k]]*.001,lw=.7,label=label)
    ax.set(title=str(identity)+' actual stage pressures',ylabel='Raw total p [kPa]',yscale='symlog');ax.set_yscale('symlog',linthresh=.1);ax.legend(fontsize=6)
    for jj,(label,phase) in enumerate((('predictor',2),('corrector',3)),1):
     ax=axes[ii,jj]
     for k in TERMS:ax.plot(x,d[:,col[label+'_'+k+'_Pa_s']],lw=.7,label=k)
     ax.plot(x,d[:,col[label+'_value_double_Pa_s']],c='black',lw=.8,ls=':',label='recorded value')
     ax.set(title=str(identity)+' '+label+' RHS',ylabel='RHS terms [Pa/s]');ax.set_yscale('symlog',linthresh=1);ax.legend(fontsize=6)
   for ax in axes.flat:ax.set_xlabel('Recorded step-start tau [s]');ax.grid(alpha=.25)
   fig.suptitle(('SHORT VERIFICATION, no .6 s pressure pulse; ' if a.profile=='short' else '')+'Genuine stage terms; total p; symlog display only; no re-timing/interpolation')
   path=Path(str(PREFIX)+'_rhs_'+suffix+'.png');fig.savefig(path);plt.close(fig);files.append(path)
   fig,axes=plt.subplots(3,3,figsize=(16,11),layout='constrained')
   for ii,identity in enumerate(IDS):
    d=data[identity];d=d[d[:,col['nstep']]>=trace.DENSE] if dense else d;x=d[:,col['tau_s']];a,b,c=axes[ii];an=a.twinx();bt=b.twinx();ct=c.twinx()
    for label,ls in (('predictor','--'),('corrector','-')):
     a.plot(x,d[:,col[label+'_J']],color='C0',ls=ls,lw=.7,label=label+' J');an.plot(x,d[:,col[label+'_n']],color='C1',ls=ls,lw=.7,label=label+' n');b.plot(x,d[:,col[label+'_theta']],color='C2',ls=ls,lw=.7,label=label+' theta');bt.plot(x,d[:,col[label+'_divAce']],color='C3',ls=ls,lw=.7,label=label+' divAce');c.scatter(x,d[:,col[label+'_FSType']],s=1,c='C0' if label=='predictor' else 'C1',label=label+' FS')
    ct.plot(x,d[:,col['actual_ponding_increment_Pa']]*.001,c='C4',lw=.7,label='ponding delta p');a.set(title=str(identity)+' J / n',ylabel='J');an.set_ylabel('n');b.set(title=str(identity)+' theta / divAce',ylabel='theta [1/s]');bt.set_ylabel('divAce [1/s^2]');b.set_yscale('symlog',linthresh=1);bt.set_yscale('symlog',linthresh=1);c.set(title=str(identity)+' actual FS / ponding',ylabel='FSType',yticks=range(5));ct.set_ylabel('Actual ponding delta p [kPa]');ct.set_yscale('symlog',linthresh=.1)
    for left,right in ((a,an),(b,bt),(c,ct)):
     h,l=left.get_legend_handles_labels();h2,l2=right.get_legend_handles_labels();left.legend(h+h2,l+l2,fontsize=5)
   for ax in axes.flat:ax.set_xlabel('Recorded step-start tau [s]');ax.grid(alpha=.25)
   fig.suptitle(('SHORT VERIFICATION, no .6 s pressure pulse; ' if a.profile=='short' else '')+'Actual predictor/corrector state; all ponding events retained in events.csv; no smoothing')
   path=Path(str(PREFIX)+'_state_'+suffix+'.png');fig.savefig(path);plt.close(fig);files.append(path)
  plots(False)
  if a.profile=='window':plots(True)
  need(all(stat(p['path'])==p for p in before),'Closed input/check or frozen author files changed')
  result.update(passed=True,analysis_completed=True,counts=counts,actual_source_time_from_loader_s=anchor,source_clock_not_fitted_or_nominal_10=True,sampling_gap_not_filled=True,dense_selection_by_global_step=True,stage_time_axis_is_actual_context_step_start_not_shifted_half_time=True,all_original_events_retained=True,terms_follow_recorded_current_branch=True,per_corrector_contributions_are_frozen_unrounded_terms_times_actual_operator_dt=True,pressure_increment_rounding_separately_reported=True,no_added_physical_threshold=True,three_IDs_not_full_field_causation_or_accuracy=True,AS_AV_effective_stress_not_separately_observed=True,visual_QA_pending=True)
 except Exception as error:result['first_failure']=str(error)
 result['files']=[stat(p) for p in files if p.exists()]
 with check.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)
 print(json.dumps(dict(passed=result['passed'],check=str(check),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
