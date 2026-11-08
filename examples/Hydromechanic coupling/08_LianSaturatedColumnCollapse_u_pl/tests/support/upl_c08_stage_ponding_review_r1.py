"""Check ReleasedSubstages C08 CSV: original strict numerical gates plus genuine half ponding."""
import argparse,csv,json,math,struct,sys
from pathlib import Path
T=Path(__file__).resolve().parents[1];TAG='upl_c08_stage_ponding_review_r1';IDS=(5809,4956,4959);DT=.0000025;START=4000000;DENSE=4240000;END=4264000;EPS=sys.float_info.epsilon
HEADER=('step_start_s,nstep,interstep,event,stored_dt_s,operator_dt_s,native_id,hits,FSType,p_before_Pa,p_after_Pa,rate_before_Pa_s,rate_after_Pa_s,J,n,theta,ki,LP,divAce,lap,chain,value_double'.split(',')+[x+str(c) for x in ('pos','FSNormal') for c in range(3)]+['C'+str(c) for c in range(9)]+[x+str(c) for x in ('finishedAce','Lx','Gp','GpCorr','GJ') for c in range(3)]+['raw_FS_branch','drainfs','closedfs','freeseepage','ponding_changed'])
RHS=HEADER[13:56];INTS=('nstep','interstep','event','native_id','hits','FSType');FLAGS=('raw_FS_branch','drainfs','closedfs','freeseepage')
def need(b,msg):
 if not b:raise RuntimeError(msg)
def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def bits(x):return struct.pack('<f',x)
def f32(x):return struct.unpack('<f',bits(x))[0]
def parse(raw,line):
 need(len(raw)==57,'CSV width differs at line '+str(line));r=dict(zip(HEADER,raw))
 for k in INTS:need(r[k] and r[k].isdigit(),'Unsigned integer '+k+' at line '+str(line));r[k]=int(r[k])
 for k in HEADER:
  if k in INTS or r[k]=='':continue
  r[k]=float(r[k]);need(math.isfinite(r[k]),'Nonfinite '+k+' at line '+str(line))
 need(r['event'] in (1,2,3) and r['hits']==1 and r['native_id'] in IDS and 0<=r['FSType']<=4,'Event/ID/hit/FS differs at line '+str(line));need(r['stored_dt_s']==DT,'Actual stored dt differs')
 for k in ('p_before_Pa','p_after_Pa','rate_before_Pa_s','rate_after_Pa_s'):need(isinstance(r[k],float) and r[k]==f32(r[k]),'Recorded float field is not a float32 value: '+k)
 if r['event']==1:
  need(all(isinstance(r[k],float) for k in RHS),'Missing RHS field');need(all(r[k] in (0.,1.) for k in FLAGS),'RHS bool differs');need(r['ponding_changed']=='','RHS unexpectedly has ponding result')
 else:
  need(all(r[k]=='' for k in RHS),'Non-RHS blank field changed')
  need(r['ponding_changed'] in (0.,1.) if r['event']==3 else r['ponding_changed']=='','Ponding result applicability differs')
 return r

def review(path,profile):
 end=START+800 if profile=='smoke2ms' else END
 expected_steps=list(range(START,end,40)) if profile=='smoke2ms' else list(range(START,DENSE,40))+list(range(DENSE,END));state=dict(rows=0,events=0,RHS_records=0,UPDATE_records=0,PONDING_records=0,extra_leading_ponding_events=0,extra_trailing_ponding_events=0,half_ponding_events=0,half_FS23_records=0,half_negative_pressure_records=0,half_projection_changed_records=0,update_bits_checks=0,ponding_bits_checks=0,RHS_rate_bits_checks=0,stage_pressure_bits_checks=0,max_clock_replay_error_s=0.,max_C_XZ_condition_inf=0.,nonfinite_C_condition_records=0,roundoff_checks={},sampled_steps=[])
 def close(label,got,want,scale):
  budget=128*EPS*max(1.,abs(got),abs(want),scale);error=abs(got-want);v=state['roundoff_checks'].setdefault(label,dict(count=0,max_abs_error=0.,max_budget_fraction=0.));v['count']+=1;v['max_abs_error']=max(v['max_abs_error'],error);v['max_budget_fraction']=max(v['max_budget_fraction'],error/budget);need(error<=budget,label+' exceeds the declared binary64 roundoff budget: '+repr((got,want,error,budget)))
 def same32(a,b,label):need(bits(a)==bits(b),label+' float32 bits differ');state['stage_pressure_bits_checks']+=1
 def row_checks(r):
  event=r['event'];state[('RHS_records' if event==1 else 'UPDATE_records' if event==2 else 'PONDING_records')]+=1
  if event==1:
   need(r['operator_dt_s']==0. and r['interstep'] in (2,3),'RHS stage/dt differs');need(r['drainfs']==0. and r['closedfs']==0. and r['freeseepage']==1.,'C08 original undrained/free-seepage switches differ')
   need(r['raw_FS_branch']==float(r['FSType'] in (2,3)),'Actual raw-FS branch differs from recorded classification');C=[r['C'+str(i)] for i in range(9)];need(all(C[i]==0. for i in (1,3,4,5,7)),'2D C y block must remain zero')
   det=C[0]*C[8]-C[2]*C[6];cond=(max(abs(C[0])+abs(C[2]),abs(C[6])+abs(C[8]))*max(abs(C[8])+abs(C[2]),abs(C[6])+abs(C[0]))/abs(det)) if det else math.inf
   if math.isfinite(cond):state['max_C_XZ_condition_inf']=max(state['max_C_XZ_condition_inf'],cond)
   else:state['nonfinite_C_condition_records']+=1
   J,n,theta,ki=r['J'],r['n'],r['theta'],r['ki'];solid=1.-f32(.35);need(J>solid and 0<n<1 and ki>0,'Recorded saturated J/n/k domain differs');close('n_from_J',n,1.-solid/J,1.)
   A=[r['finishedAce'+str(i)] for i in range(3)];L=[r['Lx'+str(i)] for i in range(3)];G=[r['GpCorr'+str(i)] for i in range(3)];need(all(struct.pack('<d',G[i])==struct.pack('<d',r['Gp'+str(i)]) for i in range(3)),'closedfs0 must retain the actual Gp as GpCorr');Gj=[r['GJ'+str(i)] for i in range(3)];lp,da=r['LP'],r['divAce']
   lap=lp+1000*(A[0]*L[0]+A[1]*L[1]+A[2]*L[2]+da) if r['raw_FS_branch'] else lp-G[0]*L[0]-G[1]*L[1]-G[2]*L[2]+1000*da
   lapscale=abs(lp)+sum(abs(G[i]*L[i]) for i in range(3))+1000*(sum(abs(A[i]*L[i]) for i in range(3))+abs(da));close('lap',r['lap'],lap,lapscale)
   scale=ki/(solid*2.);chain=scale*(Gj[0]*(G[0]+1000*A[0])+Gj[1]*(G[1]+1000*A[1])+Gj[2]*(G[2]+1000*A[2]));chainscale=abs(scale)*sum(abs(Gj[i])*(abs(G[i])+1000*abs(A[i])) for i in range(3));close('chain',r['chain'],chain,chainscale)
   gamma=1000*9.80665;value=1e9/n*(-theta+ki/gamma*r['lap']+r['chain']/gamma);valuescale=abs(1e9/n)*(abs(theta)+abs(ki/gamma*r['lap'])+abs(r['chain']/gamma));close('value',r['value_double'],value,valuescale)
   same32(r['rate_after_Pa_s'],f32(r['value_double']),'RHS overwrite');state['RHS_rate_bits_checks']+=1;same32(r['p_before_Pa'],r['p_after_Pa'],'RHS pressure read')
  elif event==2:
   need(r['interstep'] in (2,3) and r['operator_dt_s']==(DT*.5 if r['interstep']==2 else DT),'Actual pressure update half/full dt differs');predicted=f32(r['p_before_Pa']+r['operator_dt_s']*r['rate_before_Pa_s']);same32(predicted,r['p_after_Pa'],'Explicit pressure update');same32(r['rate_before_Pa_s'],r['rate_after_Pa_s'],'Update rate read');state['update_bits_checks']+=1
  else:
   need(r['operator_dt_s']==0. and r['interstep'] in (0,2,3),'Ponding stage/dt differs');expected=0. if r['FSType'] in (2,3) and r['p_before_Pa']>0 else r['p_before_Pa'];same32(expected,r['p_after_Pa'],'Positive-only ponding');same32(r['rate_before_Pa_s'],r['rate_after_Pa_s'],'Ponding rate remains unchanged');need(r['ponding_changed']==float(r['p_before_Pa']!=r['p_after_Pa']),'Ponding changed flag differs');state['ponding_bits_checks']+=1
 def step_checks(events):
  if not events:return
  step=events[0][0]['nstep'];clock=events[0][0]['step_start_s'];state['sampled_steps'].append(step);need(START<=step<end and (step>=DENSE or step%40==0),'Unexpected sampled global step')
  required=((1,2),(2,2),(1,3),(2,3));core=[];leading=[];half=[];trailing=[]
  for e in events:
   r=e[0];need(r['nstep']==step and r['step_start_s']==clock,'One step has differing actual clocks')
   if r['event']==3:
    if not core:leading.append(e)
    elif len(core)==2:
     need(not half and r['interstep']==2,'Exactly one predictor-stage half ponding is required');half.append(e)
    elif len(core)==4:trailing.append(e)
    else:need(False,'Ponding occurred inside a genuine RHS/update pair')
   else:
    need(len(core)<4 and (r['event'],r['interstep'])==required[len(core)],'Actual RHS/update stage order differs')
    if len(core)==2:need(len(half)==1,'Corrector RHS requires the prior genuine half ponding')
    core.append(e)
  need(len(core)==4 and len(half)==1 and trailing,'Missing genuine force/update/half/complete-boundary events');state['extra_leading_ponding_events']+=len(leading);state['extra_trailing_ponding_events']+=len(trailing)-1;state['half_ponding_events']+=1
  for i in range(3):
   pr,pu,cr,cu=(e[i] for e in core);hp=half[0][i]
   same32(pr['rate_after_Pa_s'],pu['rate_before_Pa_s'],'Predictor RHS->update rate');same32(cr['rate_after_Pa_s'],cu['rate_before_Pa_s'],'Corrector RHS->update rate');same32(pr['p_after_Pa'],pu['p_before_Pa'],'Predictor old-step pressure')
   same32(pu['p_after_Pa'],hp['p_before_Pa'],'Predictor half update->half ponding pressure');same32(pu['rate_after_Pa_s'],hp['rate_before_Pa_s'],'Predictor half update->half ponding rate')
   same32(hp['p_after_Pa'],cr['p_before_Pa'],'Corrector RHS must read the projected half pressure');same32(hp['rate_after_Pa_s'],cr['rate_before_Pa_s'],'Half ponding must retain the prior rate before corrector overwrite')
   need(hp['FSType']==cr['FSType'],'Half ponding and next same-geometry force RHS classifications differ')
   same32(pu['p_before_Pa'],cu['p_before_Pa'],'Corrector update must use original full-step old pressure')
   state['half_FS23_records']+=int(hp['FSType'] in (2,3));state['half_negative_pressure_records']+=int(hp['p_before_Pa']<0);state['half_projection_changed_records']+=int(hp['ponding_changed'])
   before=cu['p_after_Pa']
   for e in trailing:same32(before,e[i]['p_before_Pa'],'Complete-step update->ponding chain');before=e[i]['p_after_Pa']
   for a,b in zip(leading,leading[1:]):same32(a[i]['p_after_Pa'],b[i]['p_before_Pa'],'Leading repeated ponding chain')
  return step,clock
 previous=None;events=[]
 with path.open(encoding='utf-8-sig',newline='') as f:
  reader=csv.reader(f);need(next(reader,None)==HEADER and len(HEADER)==57,'Exact57-column trace schema required');line=1
  while True:
   batch=[]
   for i in range(3):
    raw=next(reader,None)
    if raw is None:need(i==0,'Incomplete three-ID event at EOF');break
    line+=1;batch.append(parse(raw,line))
   if not batch:break
   need(tuple(r['native_id'] for r in batch)==IDS,'Each actual event must retain the three original ID rows in order')
   for r in batch:need(all(r[k]==batch[0][k] for k in ('nstep','step_start_s','interstep','event','stored_dt_s','operator_dt_s')),'Three-ID event context differs');row_checks(r)
   state['rows']+=3;state['events']+=1
   if events and events[0][0]['nstep']!=batch[0]['nstep']:
    current=step_checks(events)
    if previous:
     need(current[0]>previous[0] and current[1]>previous[1],'Actual sampled steps/clocks are not increasing');replay=previous[1]
     for unused in range(current[0]-previous[0]):replay+=DT
     err=abs(current[1]-replay);state['max_clock_replay_error_s']=max(state['max_clock_replay_error_s'],err);need(err<=1e-14,'Observed clock differs from scalar +=dt across actual step gap')
    previous=current;events=[]
   events.append(batch)
  current=step_checks(events)
  if previous:
   replay=previous[1]
   for unused in range(current[0]-previous[0]):replay+=DT
   err=abs(current[1]-replay);state['max_clock_replay_error_s']=max(state['max_clock_replay_error_s'],err);need(current[0]>previous[0] and current[1]>previous[1] and err<=1e-14,'Final actual step/clock order/replay differs')
 need(state['sampled_steps']==expected_steps,'Missing/extra actual sampled steps');return state

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--profile',choices=('smoke2ms','window'),required=True);ap.add_argument('--csv',type=Path,required=True);ap.add_argument('--check',type=Path,required=True);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full-read before one offline CSV review required');source=a.csv.resolve();dest=a.check.resolve();need(source.name=='C08StageTrace.csv' and T/'outputs' in source.parents and dest.parent==T/'logs' and dest.name.startswith('upl_c08_stage_trace_') and not dest.exists(),'Fresh trace review check and actual test CSV required');before=stat(source);result=dict(stage=TAG,passed=False,profile=a.profile,trace=before,solver_invocations=0,decoder_invocations=0,builds=0,queue_attempts=0,physical_acceptance=False,runtime_binding_proven_by_this_check=False,owner_review_required=True,raw_CSV_rewritten=False,SHA_scans=0)
 try:result.update(observations=review(source,a.profile));need(stat(source)==before,'CSV changed during read; preserve and review the actual owner');result.update(passed=True,CSV_consistency_checked=True,extra_true_events_preserved=True,released_half_projection_checked=True,half_projection_preserves_saved_old_step_base=True)
 except Exception as error:result['first_failure']=str(error)
 result['consumed']=[before,stat(__file__),stat(T/'notes'/(TAG+'.md'))]
 with dest.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)
 print(json.dumps(dict(passed=result['passed'],check=str(dest),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
