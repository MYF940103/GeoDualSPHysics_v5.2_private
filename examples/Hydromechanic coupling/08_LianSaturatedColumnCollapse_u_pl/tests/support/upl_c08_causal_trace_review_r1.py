"""One-pass97/56-column causal telemetry review; no solver, reader or physical acceptance."""
import argparse,csv,json,math,struct,sys
from pathlib import Path
import mdbc_partition_components_r3 as e
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_causal_trace_review_r1';IDS=(7017,5944,6814);START=4000000;DT=.0000025;EPS=sys.float_info.epsilon
BASE=('step_start_s,nstep,interstep,event,stored_dt_s,operator_dt_s,native_id,hits,FSType,p_before_Pa,p_after_Pa,rate_before_Pa_s,rate_after_Pa_s,J,n,theta,ki,LP,divAce,lap,chain,value_double'.split(',')+[x+str(c) for x in ('pos','FSNormal') for c in range(3)]+['C'+str(c) for c in range(9)]+[x+str(c) for x in ('finishedAce','Lx','Gp','GpCorr','GJ') for c in range(3)]+['raw_FS_branch','drainfs','closedfs','freeseepage','ponding_changed'])
MAT='material_status,material_commit,base_I_Pa,trial_I_Pa,returned_I_Pa,kappa_old,kappa_candidate,kappa_saved,trace_drop_roundoff_budget_Pa,actual_bulk_modulus_Pa,trial_update_identity_Pa,trial_update_roundoff_budget_Pa'.split(',')
SIGMA=['sigma_rate_'+q for q in ('xx','yy','zz','xy','yz','xz')]+['sigma_rate_trace'];JSTATE='Jbase,Jhalf,Jnew,stage_theta,pressure_base_Pa'.split(',');MOVE=[x+str(c) for x in ('move_before','move_after','velocity_before','velocity_after') for c in range(3)];HIT='plane_hit_x,plane_hit_z,plane_velocity_clamp_x,plane_velocity_clamp_z'.split(',');HEADER=BASE+MAT+SIGMA+JSTATE+MOVE+HIT
RHS=BASE[13:56];FLAGS=('raw_FS_branch','drainfs','closedfs','freeseepage');INTS=('nstep','interstep','event','native_id','hits','FSType','material_status','material_commit',*HIT)
TOTAL_BASE='completed_step,native_id,last_step_start_s,last_operator_dt_s,sum_cor_dt_s,material_pre_count,material_cor_count,plane_pre_count,plane_cor_count,errors'.split(',');STATUS=['status_'+s+str(k) for s in ('pre','cor') for k in range(8)];COUNTACT=[x+'_'+s+'_'+a for x in ('plane_hit','velocity_clamp') for s in ('pre','cor') for a in ('x','z')]
SUMS='sum_cor_dt_rsigma_trace_Pa,sum_cor_trial_minus_returned_I_Pa,sum_cor_abs_trace_drop_Pa,sum_cor_local_trace_budget_Pa,trace_drop_sum_roundoff_budget_Pa,sum_cor_log_Jnew_over_Jbase,sum_cor_dt_theta,initial_I_Pa,last_returned_I_Pa,actual_bulk_modulus_Pa,base_trace_changes,sum_cor_trial_update_identity_Pa,sum_cor_local_trial_update_budget_Pa,sum_cor_abs_dt_rsigma_trace_Pa,endpoint_trace_closure_Pa,endpoint_trace_roundoff_budget_Pa'.split(',');TOTAL_HEADER=TOTAL_BASE+STATUS+COUNTACT+SUMS+['sum_delta_v_'+s+str(k) for s in ('pre','cor') for k in range(3)]
TOTAL_INTS={'completed_step','native_id','material_pre_count','material_cor_count','plane_pre_count','plane_cor_count','errors','base_trace_changes',*STATUS,*COUNTACT}
need,stat,bind=e.need,e.stat,e.bind
def bits(x):return struct.pack('<f',x)
def f32(x):return struct.unpack('<f',bits(x))[0]
def bits64(x):return struct.pack('<d',x)
def selected(step):return step%40==0 or 4316000<=step<4324000 or 4332000<=step<4340000

def parse(raw,line):
 need(len(raw)==97,'CSV width differs at line '+str(line));r=dict(zip(HEADER,raw))
 for k in HEADER:
  if r[k]=='':continue
  if k in INTS:need(r[k].isdigit(),'Unsigned integer '+k+' at line '+str(line));r[k]=int(r[k])
  else:r[k]=float(r[k]);need(math.isfinite(r[k]),'Nonfinite '+k+' at line '+str(line))
 need(r['event'] in (1,2,3,4,5) and r['hits']==1 and r['native_id'] in IDS and 0<=r['FSType']<=4 and r['stored_dt_s']==DT,'Event/ID/hit/FS/stored dt differs')
 allowed=set(BASE[:13]);event=r['event']
 if event==1:allowed.update(RHS);allowed.update(SIGMA);allowed.add('actual_bulk_modulus_Pa')
 elif event==3:allowed.add('ponding_changed')
 elif event==4:allowed.update(MAT+SIGMA+[k for k in JSTATE if k!='Jnew'])
 elif event==5:allowed.update(JSTATE+MOVE+HIT);allowed.discard('Jnew') if r['interstep']!=3 else None
 need(all((r[k]!='')==(k in allowed) for k in HEADER),'Actual per-event field applicability differs at line '+str(line))
 for k in ('p_before_Pa','p_after_Pa','rate_before_Pa_s','rate_after_Pa_s','kappa_old','kappa_candidate','kappa_saved','pressure_base_Pa','actual_bulk_modulus_Pa',*SIGMA[:6],*[x+str(c) for x in ('velocity_before','velocity_after') for c in range(3)]):
  if r[k]!='':need(r[k]==f32(r[k]),'Recorded float field not exact float32: '+k)
 if event==1:need(all(r[k] in (0.,1.) for k in FLAGS),'RHS flags differ')
 return r

def review_trace(path,end,anchor):
 expected=[i for i in range(START,end) if selected(i)];state=dict(rows=0,events=0,RHS_records=0,UPDATE_records=0,PONDING_records=0,MATERIAL_records=0,PLANE_records=0,extra_leading_ponding_events=0,extra_trailing_ponding_events=0,update_bits_checks=0,ponding_bits_checks=0,RHS_rate_bits_checks=0,stage_pressure_bits_checks=0,max_clock_replay_error_s=0.,max_C_XZ_condition_inf=0.,nonfinite_C_condition_records=0,roundoff_checks={},sampled_steps=[],material_pre_history_restored_checks=0,material_cor_history_committed_checks=0,trial_update_budget_checks=0,max_trial_update_budget_fraction=0.,sampled_adjacent_base_trace_changes=0,plane_records_checked=0,actual_bulk_modulus_Pa=None,max_abs_rsigma_trace_minus_3Ktheta_Pa_s=0.)
 def close(label,got,want,scale):
  budget=128*EPS*max(1.,abs(got),abs(want),scale);error=abs(got-want);v=state['roundoff_checks'].setdefault(label,dict(count=0,max_abs_error=0.,max_budget_fraction=0.));v['count']+=1;v['max_abs_error']=max(v['max_abs_error'],error);v['max_budget_fraction']=max(v['max_budget_fraction'],error/budget);need(error<=budget,label+' exceeds the declared binary64 roundoff budget: '+repr((got,want,error,budget)))
 def same32(a,b,label):need(bits(a)==bits(b),label+' float32 bits differ');state['stage_pressure_bits_checks']+=1
 def pressure_checks(r):
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
 def same64(a,b,label):need(bits64(a)==bits64(b),label+' binary64 bits differ')
 def row_checks(r):
  event=r['event']
  if event<=3:pressure_checks(r)
  else:
   state['MATERIAL_records' if event==4 else 'PLANE_records']+=1;need(r['interstep'] in (2,3) and r['operator_dt_s']==(DT*.5 if r['interstep']==2 else DT),'Material/plane actual half/full dt differs');same32(r['p_before_Pa'],r['p_after_Pa'],'Material/plane pressure unchanged');same32(r['rate_before_Pa_s'],r['rate_after_Pa_s'],'Material/plane rate unchanged')
  if event in (1,4):
   K=r['actual_bulk_modulus_Pa'];need(K>0,'Actual positive float bulk modulus required')
   if state['actual_bulk_modulus_Pa'] is None:state['actual_bulk_modulus_Pa']=K
   else:same64(K,state['actual_bulk_modulus_Pa'],'Actual constant K')
   same64(r['sigma_rate_trace'],(r['sigma_rate_xx']+r['sigma_rate_yy'])+r['sigma_rate_zz'],'Actual named/packed Rsigma trace')
   if event==1:state['max_abs_rsigma_trace_minus_3Ktheta_Pa_s']=max(state['max_abs_rsigma_trace_minus_3Ktheta_Pa_s'],abs(r['sigma_rate_trace']-3*K*r['theta']))
  if event==4:
   need(r['material_status'] in (1,2,3,4) and r['material_commit']==1,'Actual original CommitAllowed material status required');need(0<=r['kappa_old']<=r['kappa_candidate'],'Original nonnegative monotonic candidate history differs')
   same32(r['kappa_saved'],r['kappa_old'] if r['interstep']==2 else r['kappa_candidate'],'Actual Pre-restored/Cor-committed kappa');state['material_pre_history_restored_checks' if r['interstep']==2 else 'material_cor_history_committed_checks']+=1
   budget=r['trial_update_roundoff_budget_Pa'];need(budget>=0 and r['trace_drop_roundoff_budget_Pa']>=0,'Nonnegative declared local budgets required');residual=(r['trial_I_Pa']-r['base_I_Pa'])-r['operator_dt_s']*r['sigma_rate_trace'];close('trial_update_record',r['trial_update_identity_Pa'],residual,abs(r['trial_I_Pa'])+abs(r['base_I_Pa'])+abs(r['operator_dt_s']*r['sigma_rate_trace']))
   need(abs(r['trial_update_identity_Pa'])<=budget,'Actual before-return trial update exceeds declared gamma16 forward budget');state['trial_update_budget_checks']+=1;state['max_trial_update_budget_fraction']=max(state['max_trial_update_budget_fraction'],abs(r['trial_update_identity_Pa'])/budget if budget else 0.)
  if event in (4,5):need(r['Jbase']>1.-f32(.35) and r['Jhalf']>1.-f32(.35),'Original saturated material/plane J domain differs')
  if event==5:
   state['plane_records_checked']+=1
   for axis,key in ((0,'x'),(2,'z')):
    hit=r['plane_hit_'+key];clamp=r['plane_velocity_clamp_'+key];before=r['velocity_before'+str(axis)];need(hit in (0,1) and clamp==int(hit and before<0.),'Actual negative normal velocity clamp flag differs');same32(r['velocity_after'+str(axis)],0. if clamp else before,'Actual plane velocity projection')
    if not hit:same64(r['move_before'+str(axis)],r['move_after'+str(axis)],'Unhit plane move unchanged')
   same32(r['velocity_before1'],r['velocity_after1'],'Plane tangent velocity unchanged');same64(r['move_before1'],r['move_after1'],'Plane tangent move unchanged')
 previous_return={};events=[];previous=None;clock=anchor;advanced=START
 def step_checks(events):
  step=events[0][0]['nstep'];time=events[0][0]['step_start_s'];state['sampled_steps'].append(step);need(START<=step<end and selected(step),'Unknown sampled global step');required=((1,2),(2,2),(4,2),(5,2),(1,3),(4,3),(5,3),(2,3));core=[];leading=[];trailing=[]
  for batch in events:
   r=batch[0];need(r['nstep']==step and r['step_start_s']==time,'One sampled step has differing actual stage clocks')
   if r['event']==3:need(len(core) in (0,8),'CompletedOnly cannot pond between substage core events');(leading if not core else trailing).append(batch)
   else:need(len(core)<8 and (r['event'],r['interstep'])==required[len(core)],'Genuine pressure/material/plane stage order differs');core.append(batch)
  need(len(core)==8 and trailing,'Missing core or completed-geometry ponding');state['extra_leading_ponding_events']+=len(leading);state['extra_trailing_ponding_events']+=len(trailing)-1
  for i,identity in enumerate(IDS):
   pr,pu,mp,pp,cr,mc,pc,cu=(batch[i] for batch in core);same32(pr['rate_after_Pa_s'],pu['rate_before_Pa_s'],'Predictor RHS->update rate');same32(cr['rate_after_Pa_s'],cu['rate_before_Pa_s'],'Corrector RHS->update rate');same32(pr['p_after_Pa'],pu['p_before_Pa'],'Original predictor old pressure');same32(pu['p_after_Pa'],cr['p_before_Pa'],'CompletedOnly force reads raw half pressure');same32(pu['p_before_Pa'],cu['p_before_Pa'],'Corrector pressure update retains saved p_n base')
   for material,plane,rhs,pressure in ((mp,pp,pr,pu['p_after_Pa']),(mc,pc,cr,cr['p_after_Pa'])):
    for record in (material,plane):same32(record['p_before_Pa'],pressure,'Actual material/plane current half pressure');same32(record['pressure_base_Pa'],pu['p_before_Pa'],'Actual pressure_base is saved p_n');same32(record['rate_before_Pa_s'],rhs['rate_after_Pa_s'],'Actual material/plane RHS rate');same64(record['stage_theta'],rhs['theta'],'Actual same-stage theta')
    for key in SIGMA+['actual_bulk_modulus_Pa']:same64(material[key],rhs[key],'RHS->material '+key)
    for key in ('Jbase','Jhalf','stage_theta'):same64(material[key],plane[key],'Actual material->plane pending '+key)
   same32(mp['kappa_old'],mc['kappa_old'],'Corrector original kappa base');same32(mp['kappa_saved'],mc['kappa_old'],'Predictor restored kappa feeds Cor');same64(mp['base_I_Pa'],mc['base_I_Pa'],'Actual unchanged within-step stress trace base');same64(mp['Jbase'],pr['J'],'Predictor actual J_n');same64(mc['Jbase'],mp['Jbase'],'Corrector actual J_n base');same64(mc['Jhalf'],cr['J'],'Corrector force actual J_half');same64(mp['Jhalf'],mc['Jhalf'],'Retained actual predictor J_half')
   close('actual_predictor_J',mp['Jhalf'],mp['Jbase']+DT*.5*mp['Jbase']*mp['stage_theta'],abs(mp['Jbase'])+abs(DT*.5*mp['Jbase']*mp['stage_theta']));close('actual_corrector_J',pc['Jnew'],mc['Jbase']+DT*mc['Jhalf']*mc['stage_theta'],abs(mc['Jbase'])+abs(DT*mc['Jhalf']*mc['stage_theta']));need(pc['Jnew']>1.-f32(.35),'Actual Cor Jnew saturated domain differs')
   if identity in previous_return and previous_return[identity][0]+1==step:state['sampled_adjacent_base_trace_changes']+=int(bits64(mp['base_I_Pa'])!=bits64(previous_return[identity][1]))
   previous_return[identity]=(step,mc['returned_I_Pa']);p=cu['p_after_Pa']
   for batch in trailing:same32(p,batch[i]['p_before_Pa'],'Full pressure update->actual final ponding');p=batch[i]['p_after_Pa']
   for a,b in zip(leading,leading[1:]):same32(a[i]['p_after_Pa'],b[i]['p_before_Pa'],'Actual repeated leading ponding')
  return step,time
 def check_clock(current):
  nonlocal advanced,clock
  need(current is not None,'Empty actual trace')
  while advanced<current[0]:clock+=DT;advanced+=1
  error=abs(current[1]-clock);state['max_clock_replay_error_s']=max(state['max_clock_replay_error_s'],error);need(error<=1e-14,'Recorded stage clock differs from scalar +=dt replay')
 with path.open(encoding='utf-8-sig',newline='') as f:
  reader=csv.reader(f);need(next(reader,None)==HEADER and len(HEADER)==97,'Exact97-column causal header required');line=1
  while True:
   batch=[]
   for i in range(3):
    raw=next(reader,None)
    if raw is None:need(i==0,'Incomplete three-ID event at EOF');break
    line+=1;batch.append(parse(raw,line))
   if not batch:break
   need(tuple(r['native_id'] for r in batch)==IDS,'Actual event native-ID order differs')
   for r in batch:need(all(r[k]==batch[0][k] for k in ('step_start_s','nstep','interstep','event','stored_dt_s','operator_dt_s')),'Actual three-ID event context differs');row_checks(r)
   if events and events[0][0]['nstep']!=batch[0]['nstep']:
    current=step_checks(events);need(previous is None or current[0]>previous[0],'Actual sampled steps not strictly increasing');check_clock(current);previous=current;events=[]
   events.append(batch);state['rows']+=3;state['events']+=1
  current=step_checks(events) if events else None;need(previous is None or current[0]>previous[0],'Final sampled step order differs');check_clock(current)
 need(state['sampled_steps']==expected,'Missing/extra actual sampled steps');return state

def review_totals(path,end,cadence,anchor,K):
 expected=list(range(START+cadence,end+1,cadence));state=dict(rows=0,snapshots=0,final_by_ID={},max_clock_replay_error_s=0.,max_cor_dt_replay_error_s=0.,max_formula_roundoff_budget_fraction=0.,endpoint_declared_budget_checks=0,endpoint_not_gated_due_to_base_changes=[]);count_done=0;clock=anchor;sumdt=0.;laststart=anchor;u=EPS*.5
 def close(got,want,scale,label):
  budget=128*EPS*max(1.,abs(got),abs(want),scale);error=abs(got-want);state['max_formula_roundoff_budget_fraction']=max(state['max_formula_roundoff_budget_fraction'],error/budget);need(error<=budget,label+' differs beyond original128eps algebra budget')
 with path.open(encoding='utf-8-sig',newline='') as f:
  reader=csv.reader(f);need(next(reader,None)==TOTAL_HEADER and len(TOTAL_HEADER)==56,'Exact56-column cumulative header required')
  for completed in expected:
   count=completed-START;batch=[]
   while count_done<count:laststart=clock;clock+=DT;sumdt+=DT;count_done+=1
   for identity in IDS:
    raw=next(reader,None);need(raw is not None and len(raw)==56,'Missing/incomplete cumulative ID row');r={}
    for key,value in zip(TOTAL_HEADER,raw):
     if key in TOTAL_INTS:need(value.isdigit(),'Cumulative unsigned field differs: '+key);r[key]=int(value)
     else:r[key]=float(value);need(math.isfinite(r[key]),'Nonfinite cumulative '+key)
    need(r['native_id']==identity and r['completed_step']==completed and r['errors']==0 and all(r[key]==count for key in ('material_pre_count','material_cor_count','plane_pre_count','plane_cor_count')),'Actual cumulative step/ID/Pre/Cor/plane count/error differs')
    for stage in ('pre','cor'):need(sum(r['status_'+stage+str(k)] for k in range(8))==count and all(r['status_'+stage+str(k)]==0 for k in (0,5,6,7)),'Actual successful material status totals differ')
    for stage in ('pre','cor'):
     for axis in ('x','z'):need(0<=r['velocity_clamp_'+stage+'_'+axis]<=r['plane_hit_'+stage+'_'+axis]<=count,'Actual cumulative contact count differs')
    need(r['last_operator_dt_s']==DT and bits64(r['actual_bulk_modulus_Pa'])==bits64(K) and r['base_trace_changes']<count,'Actual cumulative dt/K/base-trace-change domain differs');ce=abs(r['last_step_start_s']-laststart);de=abs(r['sum_cor_dt_s']-sumdt);state['max_clock_replay_error_s']=max(state['max_clock_replay_error_s'],ce);state['max_cor_dt_replay_error_s']=max(state['max_cor_dt_replay_error_s'],de);need(ce<=1e-14 and de<=1e-14,'Actual Cor-only dt/physical clock differs from scalar +=dt replay')
    for key in ('sum_cor_abs_trace_drop_Pa','sum_cor_local_trace_budget_Pa','trace_drop_sum_roundoff_budget_Pa','sum_cor_local_trial_update_budget_Pa','sum_cor_abs_dt_rsigma_trace_Pa','endpoint_trace_roundoff_budget_Pa'):need(r[key]>=0,'Negative cumulative absolute/budget field: '+key)
    gamma=count*u/(1.-count*u);gamma4=4*u/(1.-4*u);local=r['sum_cor_local_trace_budget_Pa'];want=local+gamma*(r['sum_cor_abs_trace_drop_Pa']+local);close(r['trace_drop_sum_roundoff_budget_Pa'],want,want,'Trace-drop accumulation budget')
    endpoint=(r['sum_cor_dt_rsigma_trace_Pa']-r['sum_cor_trial_minus_returned_I_Pa'])-(r['last_returned_I_Pa']-r['initial_I_Pa']);scale=sum(abs(r[k]) for k in ('sum_cor_dt_rsigma_trace_Pa','sum_cor_trial_minus_returned_I_Pa','last_returned_I_Pa','initial_I_Pa'));close(r['endpoint_trace_closure_Pa'],endpoint,scale,'Actual Cor endpoint identity')
    local+=r['sum_cor_local_trial_update_budget_Pa'];budget=local+gamma*(r['sum_cor_abs_dt_rsigma_trace_Pa']+r['sum_cor_abs_trace_drop_Pa']+local)+gamma4*scale;close(r['endpoint_trace_roundoff_budget_Pa'],budget,budget,'Declared endpoint forward budget')
    if not r['base_trace_changes']:need(abs(r['endpoint_trace_closure_Pa'])<=r['endpoint_trace_roundoff_budget_Pa'],'Actual no-base-jump Cor endpoint exceeds declared forward budget');state['endpoint_declared_budget_checks']+=1
    else:state['endpoint_not_gated_due_to_base_changes'].append(dict(completed_step=completed,native_id=identity,base_trace_changes=r['base_trace_changes'],endpoint_trace_closure_Pa=r['endpoint_trace_closure_Pa']))
    state['final_by_ID'][str(identity)]=r;state['rows']+=1;batch.append(r)
   state['snapshots']+=1
  need(next(reader,None) is None,'Unknown extra cumulative row; never drop it silently')
 need(count_done==end-START,'Final cumulative count incomplete');return state

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=('smoke','window'));ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full-read before one independent CSV review');job='upl_c08_causal_'+a.action+'_GPU_r1';end=4000010 if a.action=='smoke' else 4360000;cadence=10 if a.action=='smoke' else 4000;check=L/(job+'.trace_review_r1.json');need(not check.exists(),'Existing completed/failed review protected');before=[];result=dict(stage=TAG,passed=False,action=a.action,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,queue_invocations=0,SHA_scans=0,raw_CSV_rewritten=False)
 try:
  rp=L/(job+'.run.json');np=L/(job+'.native_r1.json');r,n=e.read(rp),e.read(np);need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['consumed_stats_unchanged'] and r['actual_steps']==end and r['saved_frames']==((end-START)//cadence),'Actual sealed successful causal run required');need(n['passed'] and n['original_native_guards_passed'] and n['consumed_stats_unchanged'] and bind(n['source_run'])==stat(rp),'Actual original native guard closure required')
  sbpath=Path(bind(r['source_build'])['path']);sb=e.read(sbpath);need(sb['passed'] and sb['actual_typed_exit_code']==sb['actual_Win32_exit']==0 and sb['source_stats_unchanged'] and sb['trace_macro_enabled'] and sb['causal_macro_enabled'] and sb['source_capture']==r['source_capture'] and sb['source_archive']==r['source_archive'],'Exact normal dual-macro source build required for writer-gate evidence')
  trace=bind(r['trace_file']);totals=bind(r['totals_file']);need(Path(trace['path']).name=='C08CausalTrace.csv' and Path(totals['path']).name=='C08CausalTotals.csv' and Path(trace['path']).parent==T/'outputs'/job==Path(totals['path']).parent,'Actual job CSV paths differ');before=[stat(__file__),stat(T/'notes'/(TAG+'.md')),stat(rp),stat(np),stat(sbpath),bind(r['program']),bind(sb['source_capture']),bind(sb['source_archive']),bind(n['completion']),bind(n['metadata']),trace,totals]
  anchor=float(r['actual_source_time_from_loader']);observations=review_trace(Path(trace['path']),end,anchor);cumulative=review_totals(Path(totals['path']),end,cadence,anchor,observations['actual_bulk_modulus_Pa']);need(all(stat(q['path'])==q for q in before),'Sealed CSV/source/native bindings changed during read');result.update(passed=True,trace=trace,totals=totals,source_run=stat(rp),native_receipt=stat(np),source_build=stat(sbpath),program=r['program'],original_native_guards_passed=True,consumed_stats_unchanged=True,observations=observations,cumulative=cumulative,CSV_consistency_checked=True,original_RHS128eps_and_float_bits_preserved=True,CompletedOnly_negative_pressure_preserved=True,saved_pressure_p_n_base_checked=True,predictor_history_restored_corrector_committed=True,pending_zero_evidence='bound normal writer host gate; pending_valid is NOT a CSV column',pending_zero_independently_exported=False,trace_drop_budget_not_whole_return_error=True,local_trial_budget_operand_components_not_independently_exported=True,actual_plane_locations_not_exported_hit_geometry_not_independently_reconstructed=True,Cor_logJ_not_assumed_equal_dtTheta=True,extra_true_events_preserved=True)
 except Exception as error:result['first_failure']=str(error)
 result['consumed']=before;e.save(check,result);print(json.dumps(dict(passed=result['passed'],check=str(check),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
