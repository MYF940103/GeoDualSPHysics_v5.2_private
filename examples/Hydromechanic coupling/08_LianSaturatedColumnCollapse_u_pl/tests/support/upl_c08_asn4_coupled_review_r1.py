"""Closed CPU coupled completed rows, including genuine failure prefixes; no solver/reader actions."""
import argparse,csv,json,math,struct
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
T=Path(__file__).resolve().parents[1];TAG='upl_c08_asn4_coupled_review_r1';PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json')
SOURCE=T/'logs/upl_c08_asn4_coupled_cpu_r1.check.json';NATIVE=T/'outputs/upl_c08_asn4_window_GPU_r1/native_partial_r1';FOCUS=(7013,7015,6963,7014);DT=.0000025
FIELDS=('p_Pa','last_cor_rate_Pa_s','last_cor_theta_s','J','n','rho','k','kappa','speed_m_s','effective_trace_Pa','total_trace_Pa','x_m','z_m')
STATES=('completed_step','time_s','tau_s','updates','dt_s','signed_dterror_new_window_s','FS23_count','max_ledger_relative_error','p_RMS_Pa','velocity_RMS_m_s')+tuple(f+s for f in FIELDS for s in ('_min','_min_ID','_max','_max_ID'))
POINTS=('completed_step','time_s','tau_s','updates','native_id','p_Pa','last_cor_rate_Pa_s','last_cor_theta_s','J','n','rho','k','kappa','effective_trace_Pa','total_trace_Pa','x','y','z','vx','vy','vz','completed_FS','P0_Pa')

def need(x,s):
 if not x:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def bind(e):need(stat(e['path'])==e,'Sealed file changed: '+e['path']);return e
def entry(entries,path):return bind(next(e for e in entries if Path(e['path']).resolve()==Path(path).resolve()))
def bits(x):return struct.pack('<d',float(x))
def fbits(x):return struct.pack('<f',float(x))
def table(path):
 with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def csvfile(leaf,rows):
 need(rows,'No completed records to export');keys=list(dict.fromkeys(k for row in rows for k in row));p=Path(str(PREFIX)+'_'+leaf+'.csv')
 with p.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
 return p
def save(p,obj):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(obj,f,indent=2,allow_nan=False);f.write('\n')

def endpoint(points,last,source,consumed,before):
 result=dict(performed=False,reason='CPU did not normally complete4000 updates at the actual GPU part65 clock',comparison_is_descriptive=True,GPU_exact_restart_or_replay=False)
 if not source['passed'] or int(last['updates'])!=4000 or int(last['completed_step'])!=4264000:return result
 clocks=table(NATIVE/'clocks.csv')
 if bits(last['time_s'])!=bits(clocks[65]['time_s']) or int(clocks[65]['completed_step'])!=4264000:return result
 # Only this one original sealed native record is accessed, after the exact endpoint condition.
 from upl_c08_fsmask_r1 import SCHEMA,TYPES
 before.append(stat(T/'support/upl_c08_fsmask_r1.py'));before.extend(entry(consumed,NATIVE/q) for q in ('typed22.bin','typed22_layout.csv'))
 layout=table(NATIVE/'typed22_layout.csv');need(len(layout)==22,'Original22 endpoint schema differs');fields=[('time','<f8')]
 for q,(name,kind,width) in zip(layout,SCHEMA):need((q['array'],q['type'],int(q['components']),int(q['bytes_per_particle']))==(name,kind,width,TYPES[kind].itemsize*width),'Original22 endpoint layout differs');fields.append((name,TYPES[kind],(6805,width)))
 dtype=np.dtype(fields);need(dtype.itemsize==8+6805*212,'Original endpoint record stride differs')
 with (NATIVE/'typed22.bin').open('rb') as f:need(struct.unpack('<III',f.read(12))==(6805,22,66),'Original66/6805/22 endpoint header differs');f.seek(12+65*dtype.itemsize);raw=f.read(dtype.itemsize)
 need(len(raw)==dtype.itemsize and (NATIVE/'typed22.bin').stat().st_size==12+66*dtype.itemsize,'Original endpoint payload incomplete');frame=np.frombuffer(raw,dtype=dtype,count=1)[0];need(bits(frame['time'])==bits(last['time_s']),'Actual native endpoint time differs');ids=frame['Idp'][:,0];comparisons=[]
 for identity in FOCUS:
  at=np.flatnonzero(ids==identity);need(len(at)==1,'Original endpoint focus missing');q=int(at[0]);cpu=next(r for r in points if int(r['completed_step'])==4264000 and int(r['native_id'])==identity);v=frame['Vel'][q].astype(float);p=float(frame['PorePress'][q,0]);trace=float(frame['SigmaState_kk'][q,0]+frame['SigmaState_kk'][q,1]+frame['SigmaState_kk'][q,2]);gpu=dict(p_Pa=p,J=float(frame['PoroVolumeRatio'][q,0]),kappa=float(frame['Kplastic'][q,0]),vx_m_s=float(v[0]),vy_m_s=float(v[1]),vz_m_s=float(v[2]),speed_m_s=float(np.linalg.norm(v)),effective_trace_Pa=trace,total_trace_Pa=trace-3*p);cv=dict(p_Pa=float(cpu['p_Pa']),J=float(cpu['J']),kappa=float(cpu['kappa']),vx_m_s=float(cpu['vx']),vy_m_s=float(cpu['vy']),vz_m_s=float(cpu['vz']),speed_m_s=float(cpu['speed_m_s']),effective_trace_Pa=float(cpu['effective_trace_Pa']),total_trace_Pa=float(cpu['total_trace_Pa']))
  comparisons.append(dict(native_ID=identity,CPU=cv,GPU=gpu,CPU_minus_GPU={k:cv[k]-gpu[k] for k in gpu},CPU_FS=int(cpu['completed_FS']),GPU_FS=int(frame['FSType'][q,0])))
 result.update(performed=True,reason='Actual completed step/time match only; no interpolation',original_GPU_part=65,completed_step=4264000,time_s=float(last['time_s']),stress_comparison='effective/total traces only; CPU focus CSV has no six stress components',points=comparisons);return result

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read before one offline review');need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial review protected')
 source=read(SOURCE);need(source['stage']=='upl_c08_asn4_coupled_cpu_r1' and source['physical_trajectories']==1 and source['source_part']==64 and source['source_completed_step']==4260000 and source['planned_max_integrated_updates']==4000 and not source['physical_acceptance'],'Actual bounded trajectory terminal check required');before=[stat(__file__),stat(T/'notes'/(TAG+'.md')),stat(SOURCE),bind(source['actual_call'])];call=read(source['actual_call']['path']);rc=source['actual_exit'];need(isinstance(rc,int) and rc==source['actual_Win32_exit']==call['actual_Popen_wait_exit']==call['actual_Win32_exit'] and rc!=259 and call['ownership_failure'] is None and call['typed_returncode_captured_before_postchecks'] and call.get('ended_utc'),'Actual owned target termination/exits do not match')
 paths={q:bind(next(e for e in source['files'] if Path(e['path']).name==q)) for q in ('states.csv','focus.csv')};before.extend(paths.values());states=table(paths['states.csv']['path']);points=table(paths['focus.csv']['path']);need(1<=len(states)<=4000 and len(points)==4*len(states) and list(states[0])==list(STATES) and list(points[0])==list(POINTS),'Exact62-state/23-focus schemas and complete row counts required')
 with Path(paths['states.csv']['path']).open(encoding='utf-8',newline='') as f:rawlines=f.readlines()
 with Path(paths['focus.csv']['path']).open(encoding='utf-8',newline='') as f:focuslines=f.readlines()
 need(len(rawlines)==len(states)+1 and len(focuslines)==len(points)+1 and rawlines[-1].endswith('\n') and focuslines[-1].endswith('\n'),'Unflushed/truncated final row; do not silently drop it')
 native_consumed=source['consumed'];before.extend(entry(native_consumed,NATIVE/q) for q in ('completion.json','clocks.csv'));nd=read(NATIVE/'completion.json');clocks=table(NATIVE/'clocks.csv');need(nd['passed'] and nd['stage']=='upl_c08_asn4_partial_r1' and nd['samples']==66 and nd['typed_arrays']==22 and nd['actual_native_IDs_per_frame']==6805 and len(clocks)==66 and int(clocks[64]['completed_step'])==4260000,'Original selected snapshot clock/binding differs');start=float(clocks[64]['time_s']);pre=float(nd['source_actual_time_s']);scalar=start;by_step={};p0={};lastk={};history=[];focus_rows=[]
 for q in points:need(None not in q and all(v is not None and math.isfinite(float(v)) for v in q.values()),'Malformed/nonfinite focus row');by_step.setdefault(int(q['completed_step']),[]).append(q)
 for update,q in enumerate(states,1):
  need(None not in q and all(v is not None and math.isfinite(float(v)) for v in q.values()),'Malformed/nonfinite state row');scalar+=DT;step=4260000+update;need(int(q['completed_step'])==step and int(q['updates'])==update and bits(q['time_s'])==bits(scalar) and bits(q['tau_s'])==bits(scalar-pre) and bits(q['dt_s'])==bits(DT),'Actual completed scalar+=dt clock/step differs');signed=float(q['signed_dterror_new_window_s']);need(signed!=-np.finfo(float).max and signed<=1e-14 and float(q['max_ledger_relative_error'])<=5e-13 and 0<=int(q['FS23_count'])<=5000,'Original signed interval/ledger/FS count guard differs')
  for field in FIELDS:need(2060<=int(q[field+'_min_ID'])<7060 and 2060<=int(q[field+'_max_ID'])<7060 and float(q[field+'_min'])<=float(q[field+'_max']),'Global soil extrema ownership/range differs')
  history.append(dict(**q,elapsed_from_part64_ms=1000*(scalar-start)));rr=by_step.get(step,[]);need(len(rr)==4 and {int(r['native_id']) for r in rr}==set(FOCUS),'Four focus IDs/last flush structure differ')
  for r in rr:
   identity=int(r['native_id']);need(int(r['updates'])==update and bits(r['time_s'])==bits(scalar) and bits(r['tau_s'])==bits(scalar-pre) and int(r['completed_FS']) in (0,1,2,3),'Focus actual time/step/FS differs');p0.setdefault(identity,fbits(r['P0_Pa']));need(p0[identity]==fbits(r['P0_Pa']) and float(r['kappa'])>=lastk.get(identity,0.),'Original material P0 bits/monotone kappa differs');lastk[identity]=float(r['kappa']);speed=math.sqrt(sum(float(r[k])**2 for k in ('vx','vy','vz')));focus_rows.append(dict(**r,elapsed_from_part64_ms=1000*(scalar-start),speed_m_s=speed,trace_identity_roundoff_Pa=float(r['total_trace_Pa'])-(float(r['effective_trace_Pa'])-3*float(r['p_Pa']))))
 last=states[-1];terminal={}
 if source['passed']:
  need(rc==0 and source['consumed_stats_unchanged'] and len(states)==4000,'Normal terminal coverage/exits differ');e=bind(source['component_completion']);before.append(e);done=read(e['path']);need(done['passed'] and done['physical_updates']==4000 and done['completed_step']==4264000 and done['states_rows']==4000 and done['focus_rows']==16000 and bits(done['source_saved_time_s'])==bits(start) and bits(done['elastic_PRE_actual_time_s'])==bits(pre) and bits(done['actual_end_s'])==bits(scalar) and done['all_completed_original_guards_passed'] and done['last_cor_rate_is_not_completed_state_RHS'] and not done['Ace_Rsigma_after_cleanup_read'],'Normal completed metadata differs');terminal=dict(source_passed=True,actual_exit=rc,completed_rows=4000,reason='normal4000-update completion')
 else:
  need(rc!=0 and source.get('component_failure'),'Only a sealed genuine target failure prefix is supported');e=bind(source['component_failure']);before.append(e);failure=read(e['path']);need(not failure['passed'] and failure['has_completed_row'] and failure['completed_rows']==len(states) and failure['last_output_completed_step']==int(last['completed_step']) and bits(failure['last_output_time_s'])==bits(scalar) and not failure['unsaved_failure_state_read'] and not failure['unsaved_failure_time_inferred'] and source['actual_completed_rows']==len(states) and source['last_original_states_csv_line']==rawlines[-1],'Failure metadata/last actual flushed row differs');terminal=dict(source_passed=False,actual_exit=rc,completed_rows=len(states),failed_phase=failure['failed_phase'],first_component_exception=failure['first_exception'],wrapper_first_failure=source.get('first_failure'),last_original_states_csv_line=rawlines[-1],unsaved_failure_state_read=False,unsaved_failure_time_inferred=False)
 records=[]
 for label,field,op,threshold in (('first_sample_pmin_lt_minus100kPa','p_Pa_min','<',-100000.),('first_sample_pmin_lt_minus300kPa','p_Pa_min','<',-300000.),('first_sample_speed_gt2m_s','speed_m_s_max','>',2.),('first_sample_speed_gt10m_s','speed_m_s_max','>',10.)):
  found=next((q for q in states if (float(q[field])<threshold if op=='<' else float(q[field])>threshold)),None);records.append(dict(kind='descriptive_first_sample',name=label,field=field,condition=op+str(threshold),found=found is not None,completed_step=int(found['completed_step']) if found else None,time_s=float(found['time_s']) if found else None,tau_s=float(found['tau_s']) if found else None,updates=int(found['updates']) if found else None,native_ID=int(found[field+'_ID']) if found else None,value=float(found[field]) if found else None,not_an_acceptance_limit=True))
 for field in FIELDS:
  for direction,choose in (('min',min),('max',max)):
   key=field+'_'+direction;q=choose(states,key=lambda r:float(r[key]));records.append(dict(kind='global_sampled_extremum',name=field+'_'+direction,field=key,condition=direction,found=True,completed_step=int(q['completed_step']),time_s=float(q['time_s']),tau_s=float(q['tau_s']),updates=int(q['updates']),native_ID=int(q[key+'_ID']),value=float(q[key]),not_an_acceptance_limit=True))
 gpu=endpoint(focus_rows,last,source,native_consumed,before);files=[csvfile('history',history),csvfile('focus',focus_rows),csvfile('events_extrema',records)];x=np.asarray([q['elapsed_from_part64_ms'] for q in history]);num=lambda key:np.asarray([float(q[key]) for q in states])
 fig,axes=plt.subplots(3,2,figsize=(13,10),constrained_layout=True)
 for key,label in (('p_Pa_min','p min'),('p_Pa_max','p max'),('p_RMS_Pa','p RMS')):axes[0,0].plot(x,num(key)/1000,lw=.8,label=label)
 for key,label in (('speed_m_s_max','speed max'),('velocity_RMS_m_s','speed RMS')):axes[0,1].plot(x,num(key),lw=.8,label=label)
 for key in ('min','max'):axes[1,0].plot(x,num('J_'+key),lw=.8,label='J '+key);axes[1,1].plot(x,num('kappa_'+key),lw=.8,label='kappa '+key)
 for prefix,label in (('effective_trace_Pa','effective'),('total_trace_Pa','total')):
  for suffix in ('min','max'):axes[2,0].plot(x,num(prefix+'_'+suffix)/1000,lw=.8,label=label+' trace '+suffix)
 ax=axes[2,1];right=ax.twinx()
 for suffix in ('min','max'):ax.plot(x,num('last_cor_rate_Pa_s_'+suffix),lw=.7,label='retained Cor rate '+suffix);right.plot(x,num('last_cor_theta_s_'+suffix),lw=.7,ls='--',color='C'+str(2+(suffix=='max')),label='retained Cor theta '+suffix)
 right.set_ylabel('Retained Cor theta [1/s]');lines=ax.get_lines()+right.get_lines();ax.legend(lines,[q.get_label() for q in lines],fontsize=6)
 for ax,title,ylabel in zip(axes.ravel(),('Completed pressure','Completed speed','Current volume ratio','Plastic history','Stress traces','Stored last-Cor observations'),('Pressure [kPa]','Speed [m/s]','J','kappa','Trace [kPa]','Retained Cor rate [Pa/s]')):ax.set(title=title,xlabel='Actual elapsed from input part64 [ms]',ylabel=ylabel);ax.ticklabel_format(axis='x',style='plain',useOffset=False);ax.grid(alpha=.25)
 for ax in axes.ravel()[:-1]:ax.legend(fontsize=7)
 fig.suptitle('CPU coupled completed rows; '+('normal completion' if source['passed'] else 'FAILED target, retained complete prefix')+'\nCor rate/theta are retained observations, not instantaneous RHS at the completed state.');path=Path(str(PREFIX)+'_global.png');fig.savefig(path,dpi=165);plt.close(fig);files.append(path)
 fig,axes=plt.subplots(3,2,figsize=(13,10),constrained_layout=True)
 for color,identity in enumerate(FOCUS):
  rr=[q for q in focus_rows if int(q['native_id'])==identity];xx=[q['elapsed_from_part64_ms'] for q in rr]
  for ax,key,scale in ((axes[0,0],'p_Pa',.001),(axes[0,1],'J',1),(axes[1,0],'speed_m_s',1),(axes[1,1],'kappa',1),(axes[2,1],'last_cor_theta_s',1)):ax.plot(xx,[float(q[key])*scale for q in rr],lw=.7,color='C'+str(color),label=str(identity))
  axes[2,0].step(xx,[int(q['completed_FS']) for q in rr],where='post',lw=.7,color='C'+str(color),label=str(identity))
 for ax,title,ylabel in zip(axes.ravel(),('Completed p','Completed J','Stored-velocity speed','Completed kappa','Completed FS classification','Retained last-Cor theta'),('Pressure [kPa]','J','Speed [m/s]','kappa','FSType','Retained Cor theta [1/s]')):ax.set(title=title,xlabel='Actual elapsed from input part64 [ms]',ylabel=ylabel);ax.ticklabel_format(axis='x',style='plain',useOffset=False);ax.legend(fontsize=7);ax.grid(alpha=.25)
 axes[2,0].set_yticks((0,1,2,3));fig.suptitle('Four fixed material IDs; all actual completed samples, no smoothing or inferred failed state.');path=Path(str(PREFIX)+'_focus.png');fig.savefig(path,dpi=165);plt.close(fig);files.append(path)
 need(all(stat(e['path'])==e for e in before),'Closed consumed data changed');save(CHECK,dict(stage=TAG,passed=True,analysis_completed=True,source_terminal_check=stat(SOURCE),source_target_passed=source['passed'],terminal=terminal,actual_completed_rows=len(states),focus_rows=len(points),first_completed_step=int(states[0]['completed_step']),last_completed_step=int(last['completed_step']),source_part64_time_s=start,elastic_PRE_actual_time_s=pre,last_completed_time_s=scalar,scalar_plus_equal_dt_verified=True,signed_dterror_min_s=float(num('signed_dterror_new_window_s').min()),signed_dterror_max_s=float(num('signed_dterror_new_window_s').max()),original_source_consumed_stats_unchanged=source.get('consumed_stats_unchanged'),events_are_descriptive_not_acceptance_thresholds=True,events_extrema=records,GPU_endpoint_comparison=gpu,stress_endpoint_comparison_limited_to_trace=True,last_Cor_rate_theta_not_completed_state_RHS=True,no_material_plane_order_or_net_force_causation_claim=True,first_threshold_sample_is_not_proven_onset=True,first_plot_state_is_first_completed_update_not_input_snapshot=True,source_failure_not_relabelled_success=True,analysis_passed_does_not_imply_trajectory_passed=True,GPU_exact_restart_or_replay=False,physical_acceptance=False,visual_QA_pending=True,consumed=before,consumed_stats_unchanged=True,files=[stat(p) for p in files],solver_invocations=0,decoder_invocations=0,VTK_invocations=0,build_invocations=0,SHA_scans=0));print('COUPLED_COMPLETED_REVIEW_READY',CHECK,flush=True)

if __name__=='__main__':main()
