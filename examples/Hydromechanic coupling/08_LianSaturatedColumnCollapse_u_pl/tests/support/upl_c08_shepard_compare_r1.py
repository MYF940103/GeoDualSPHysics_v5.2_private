"""Failed72-save Shepard prefix versus retained total-n3 prefix; actual7246-call meter, no physical pass."""
import argparse,csv,json,struct
from pathlib import Path
import upl_c08_clustering_r1 as cluster
import upl_c08_as_effective_partial_review_r1 as native
from matplotlib.colors import SymLogNorm
from matplotlib.collections import LineCollection
np,c,plt=cluster.np,cluster.c,cluster.plt
T=c.T;TAG='upl_c08_shepard_compare_r1';PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json');JOB='upl_c08_shepard_window_GPU_r1';DT=.0000025;SAMPLES=72;SPACING=tuple(range(9,70,10))+(71,)
METER='call,Nstep,completed_step,step_start_time_s,operator_dt_s,soil_IDs,interval,storage_before_m3,storage_after_m3,delta_storage_m3,sum_abs_weighted_delta_m3,max_abs_delta_p_Pa,changed_pressure_bits,p_before_min_Pa,p_before_max_Pa,p_after_min_Pa,p_after_max_Pa,primary_bitcheck_performed,primary_bitcheck_passed'.split(',')

def write(leaf,rows):
 p=Path(str(PREFIX)+'_'+leaf+'.csv')
 with p.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 return p

def load_new(old,before):
 rp=T/'logs/upl_c08_shepard_partial_r1.check.json';r=c.read(rp);c.need(r['passed'] and r['partial'] and not r['runtime_success_claimed'],'Explicit failed72 saved-native receipt required');readerpath=T/'logs/upl_c08_shepard_partial_r1.build.json';before.extend((c.stat(rp),c.bind(r['source_failed_run']),c.bind(r['actual_call']),c.bind(r['completion']),c.bind(r['metadata']),c.stat(readerpath)));before.extend(c.bind(e) for e in r['consumed']);run=c.read(r['source_failed_run']['path']);done=c.read(r['completion']['path']);m=c.read(r['metadata']['path']);call=c.read(r['actual_call']['path']);reader=c.read(readerpath);directory=Path(r['completion']['path']).parent
 c.need(not run['passed'] and not run['solver_completed'] and run['actual_exit']==run['actual_Win32_exit']==1 and run['failed_stage']=='solver' and run['ownership_errors']==[] and run['consumed_stats_unchanged'] and not run['unsaved_failure_time_known'],'Sealed failed Release solver1 prefix required');c.need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None and reader['passed'] and Path(call['program']).resolve()==Path(reader['program']['path']).resolve(),'Actual native call/build differs')
 counts=dict(samples=72,completed_steps=4288000,typed_arrays=22,typed_bytes_per_particle=212,actual_native_IDs_per_frame=6805,soil_IDs=5000,actual_fixed_IDs=1805,ledger_checks=360000,fixed_marker_checks=129960,P0_bits_checks=489960,rho_cache_bits_checks=360000,kappa_nondecreasing_from_PRE_checks=360000,nonempty_signed_intervals=72,plane_gap_checks=720000)
 c.need(done['passed'] and done['stage']=='upl_c08_shepard_partial_r1' and all(done[k]==v for k,v in counts.items()) and done['max_scalar_clock_error_s']<=1e-14 and done['max_signed_dterror_s']<=1e-14 and done['max_ledger_relative_error']<=5e-13 and done['FS23_pressure_checks']>0 and not done['completed_runtime_Run_csv_checked'] and done['partial'] and not done['runtime_success_claimed'] and done['original_planned_samples']==90 and done['original_planned_end']==4360000 and done['used_launch_plan_prefix_samples']==72 and done['last_saved_step']==4287999 and not done['failure_unsaved_state_reconstructed'] and done['saved_steps_checked_against_launch_plan'] and done['source_PREs_read']==1 and done['source_material_law_version']==1 and done['target_material_law_version']==2,'Original22/ID/P0/ledger/kappa/FS/clock/native guards differ')
 c.need(done['kept_bed_IDs']==[1800,1852,1904,1956,2008] and done['actual_retired_count']==255 and done['NoPenOn_argument'] and done['DynamicNoPenetrationPolicy']=='FixedPlaneStageProjectionReleaseOnly' and done['DynamicNoPenetrationActive'] and not done['DynamicNoPenetrationReactionClosed'] and not done['reaction_J_Darcy_closed'],'Original keep5/plane split scope differs')
 c.need(m['passed'] and m['stage']=='upl_c08_shepard_partial_r1.metadata' and m['profile']=='failed_window_partial' and m['partial'] and not m['runtime_success_claimed'] and m['used_launch_plan_prefix_samples']==72 and m['planned_cadence_steps']==4000 and m['samples']==m['metadata_header_scans']==m['keep_policy_headers']==m['AS_active_true_headers']==m['pore_shepard_active_true_headers']==m['soil_damping_inactive_headers']==72 and m['expected_PoreShepardActive'] and not m['expected_SoilDampingActive'] and m['AS_policy']=='ReleaseOnly' and m['AS_coefficient_float_reference']==float(np.float32(.2)) and m['AS_exponent_float_reference']==3. and m['expected_ponding_policy']=='CompletedOnly' and m['ponding_policy_keys_absent_headers']==72,'Actual Shepard/filter/AS/CompletedOnly metadata differs')
 before.extend(c.bind(run[k]) for k in ('program','source_build','source_capture','source_archive','source_pre_file','input_xml','planned_steps','partial_filter_metering'));build=c.read(run['source_build']['path']);c.need(build['passed'] and build['program']==run['program'] and build['source_capture']==run['source_capture'] and build['source_archive']==run['source_archive'] and build['AS_stress_space']=='original_total' and build['release_Shepard_policy']=='RetainLoadedFlag' and build['meter_scope']=='existing_filter_wrapper_plus_FS_projection' and build['consumed_stats_unchanged'],'Private total-AS/Shepard source binding differs')
 for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv','history.csv'):before.append(native.entry(r['outputs'],directory/leaf))
 c.need(c.table(directory/'typed22_layout.csv')==c.table(old['native']/'typed22_layout.csv'),'Same literal22 layout required');clocks=c.table(directory/'clocks.csv');history=c.table(directory/'history.csv');c.need(len(clocks)==len(history)==72 and (directory/'typed22.bin').stat().st_size==12+72*old['frames'].dtype.itemsize,'Actual72 file extent differs')
 return dict(label='release_shepard40',epsilon=.2,exponent=3.,run=run,done=done,native=directory,clocks=clocks,history=history,dtype=old['frames'].dtype,count=72)

def meter(run,source,clocks):
 rows=c.table(c.bind(run['partial_filter_metering'])['path']);c.need(len(rows)==7246 and list(rows[0])==METER,'Original19-column7246-call meter required');scalar=source;net=absnet=weighted=0.;S0=float(rows[0]['storage_before_m3']);derived=[]
 for index,q in enumerate(rows,1):
  c.need(None not in q and all(np.isfinite(float(q[k])) for k in METER[:-1]) and int(q['call'])==index and int(q['completed_step'])==4000000+40*index and int(q['Nstep'])==4000000+40*index-1 and int(q['soil_IDs'])==5000 and int(q['interval'])==40 and native.bits(q['operator_dt_s'])==native.bits(DT) and int(q['primary_bitcheck_performed'])==int(index==1) and q['primary_bitcheck_passed']==('true' if index==1 else ''),'Actual meter call/step/dt/first-only bitcheck differs')
  for _ in range(39):scalar+=DT
  c.need(native.bits(scalar)==native.bits(q['step_start_time_s']),'Actual filter start scalar clock differs');scalar+=DT
  if index%100==0:c.need(native.bits(scalar)==native.bits(clocks[index//100-1]['time_s']),'Actual completed filter/native save clocks differ')
  r=dict(q);net+=float(q['delta_storage_m3']);absnet+=abs(float(q['delta_storage_m3']));weighted+=float(q['sum_abs_weighted_delta_m3']);r.update(filter_completed_clock_s=scalar,tau_s=scalar-source,after_last_native_save=int(q['completed_step'])>4288000,first_actual_filter_before_S=S0,cumulative_net_delta_S=net,cumulative_abs_net_delta_S=absnet,cumulative_abs_weighted_delta_S=weighted,relative_cumulative_net_over_S0=net/S0 if S0 else None,relative_cumulative_abs_net_over_absS0=absnet/abs(S0) if S0 else None,relative_cumulative_abs_weighted_over_absS0=weighted/abs(S0) if S0 else None);derived.append(r)
 windows=[]
 for lo,hi in ((0.,.3),(.3,.5),(.5,.6),(.6,.7),(.7,.72),(.72,np.inf)):
  q=[r for r in derived if lo<=r['tau_s']<hi];c.need(q,'Empty declared actual-time meter band');d=np.asarray([float(r['delta_storage_m3']) for r in q]);w=np.asarray([float(r['sum_abs_weighted_delta_m3']) for r in q]);r=dict(nominal_lo_s=lo,nominal_hi_s=hi if np.isfinite(hi) else None,actual_tau_first_s=q[0]['tau_s'],actual_tau_last_s=q[-1]['tau_s'],calls=len(q),calls_after_last_native_save=sum(r['after_last_native_save'] for r in q),sum_net_delta_S=float(d.sum()),sum_abs_net_delta_S=float(np.abs(d).sum()),sum_abs_weighted_delta_S=float(w.sum()),positive_delta_S_calls=int(np.count_nonzero(d>0)),negative_delta_S_calls=int(np.count_nonzero(d<0)),max_abs_delta_p_Pa=max(float(r['max_abs_delta_p_Pa']) for r in q))
  for key in ('p_before_min_Pa','p_before_max_Pa','p_after_min_Pa','p_after_max_Pa'):r[key+'_min']=min(float(a[key]) for a in q);r[key+'_max']=max(float(a[key]) for a in q)
  windows.append(r)
 c.need(sum(q['calls'] for q in windows)==7246,'Actual meter bands must partition all calls');return derived,windows,dict(actual_calls=7246,calls_after_last_native_save=sum(r['after_last_native_save'] for r in derived),last_filter_completed_step=int(rows[-1]['completed_step']),last_filter_step_start_time_s=float(rows[-1]['step_start_time_s']),last_filter_completed_clock_derived_s=derived[-1]['filter_completed_clock_s'],last_filter_tau_derived_s=derived[-1]['tau_s'],filter_observations_are_not_unsaved_field_reconstruction=True,first_actual_filter_before_S=S0,sum_net_delta_S=net,sum_abs_net_delta_S=absnet,sum_abs_weighted_delta_S=weighted,relative_net_over_S0=net/S0 if S0 else None,relative_abs_net_over_absS0=absnet/abs(S0) if S0 else None,relative_abs_weighted_over_absS0=weighted/abs(S0) if S0 else None,endpoint_S_after_minus_first_before=float(rows[-1]['storage_after_m3'])-S0,storage_units='2D unit-thickness model volume; not true fluid mass',same_wrapper_includes_FS_positive_projection=True,primary_bitcheck_is_first_call_only=True)

def extrema_update(results,a,g,part,tau,step):
 soil=a['Idp'][:,0]>=2060;ids=a['Idp'][soil,0];pos=a['Posd'][soil];p=a['PorePress'][soil,0].astype(float);kk=a['SigmaState_kk'][soil];ij=a['SigmaState_ij'][soil];values=[('p',p,'Pa'),('speed',np.linalg.norm(a['Vel'][soil].astype(float),axis=1),'m/s')]+[(key,a[field][soil,0].astype(float),unit) for key,field,unit in (('excess_fixed_P0','ExcessPorePress','Pa'),('kappa','Kplastic','1'),('J','PoroVolumeRatio','1'),('n','PoroPorosity','1'),('rho','PoroMixtureDensity','kg/m3'),('k','PoroHydraulicConductivity','m/s'))]
 for j,name in enumerate(('xx','yy','zz','xy','yz','xz')):
  v=kk[:,j] if j<3 else ij[:,j-3];values.extend((('effective_'+name,v,'Pa'),('total_'+name,v-p if j<3 else v,'Pa')))
 for field,v,unit in values:
  for kind,i in (('min',int(np.argmin(v))),('max',int(np.argmax(v)))):
   key=(g['label'],field,kind);value=float(v[i]);old=results.get(key)
   if old is None or (value<old['value'] if kind=='min' else value>old['value']):results[key]=dict(group=g['label'],field=field,extreme=kind,value=value,unit=unit,part=part,time_s=float(a['time']),tau_s=tau,completed_step=step,native_id=int(ids[i]),x_m=float(pos[i,0]),z_m=float(pos[i,2]),p_Pa=float(p[i]),J=float(a['PoroVolumeRatio'][soil,0][i]),kappa=float(a['Kplastic'][soil,0][i]),FSType=int(a['FSType'][soil,0][i]))

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();c.need(args.execution_authorized,'Root full-read after explicit failed72 native completion');c.need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial comparison protected');before=[c.stat(p) for p in (Path(__file__),T/'notes'/(TAG+'.md'),Path(cluster.__file__),Path(c.__file__),Path(native.__file__),T/'support/upl_c08_fsmask_r1.py')]
 old=native.load(native.SPECS[0],before);old.update(epsilon=.2,exponent=3.,dtype=old['frames'].dtype,history=c.table(old['native']/'history.csv'));oldreceipt=c.read(T/'logs'/native.SPECS[0][1]);before.append(native.entry(oldreceipt['outputs'],old['native']/'history.csv'));new=load_new(old,before);groups=(old,new);c.need(old['run']['source_pre_file']==new['run']['source_pre_file'] and native.bits(old['done']['source_actual_time_s'])==native.bits(new['done']['source_actual_time_s']),'Same certified PRE/actual scalar source required')
 prefix=T/'logs/upl_c08_causal_prefix90_r1.check.json';p=c.read(prefix);c.need(p['passed'] and p['actual_common_saved_frames']==90 and p['all22_and_actual_time_payload_byte_exact'] and p['typed_layout_byte_exact'] and p['signed_clock_header_and_common_rows_byte_exact'] and p['consumed_stats_unchanged'],'Retained total-n3 actual full-r6 prefix proof required');before.append(c.stat(prefix))
 for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv','completion.json'):before.append(native.entry(p['consumed'],old['native']/leaf))
 roots=[c.ET.parse(g['run']['input_xml']['path']).getroot() for g in groups];c.need(all(tuple(c.physics(r.find('execution/'+k)) for k in ('special','parameters'))==tuple(c.physics(roots[0].find('execution/'+k)) for k in ('special','parameters')) for r in roots),'Same XML physics required; program release dispatch intentionally differs')
 body=[];cohorts=[];focus=[];differences=[];extrema={};last={};scalar=float(old['done']['source_actual_time_s']);P0=None;files=[]
 with (old['native']/'typed22.bin').open('rb') as fa,(new['native']/'typed22.bin').open('rb') as fb:
  c.need(fa.read(12)==struct.pack('<III',6805,22,90) and fb.read(12)==struct.pack('<III',6805,22,72),'Preserve actual baseline90/candidate72 headers')
  for part in range(72):
   for _ in range(4000):scalar+=DT
   pair=[]
   for g,f in zip(groups,(fa,fb)):
    raw=f.read(g['dtype'].itemsize);c.need(len(raw)==g['dtype'].itemsize,'Short original record');a=np.frombuffer(raw,dtype=g['dtype'],count=1)[0];time,tau,step=c.inspect(a,g,part);c.need(native.bits(time)==native.bits(scalar),'Actual paired scalar clocks differ');p0=a['PorePress0'].view('<u4');P0=p0.copy() if P0 is None else P0;c.need(np.array_equal(p0,P0),'Fixed-material P0 bits differ');m=cluster.measures(a) if part in SPACING else None;row=c.quantities(a,g,part,tau,step);row.update(effective_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(a['SigmaState_kk'][a['Idp'][:,0]>=2060]**2,axis=1)+2*np.sum(a['SigmaState_ij'][a['Idp'][:,0]>=2060]**2,axis=1)))),mean_kappa=float(np.mean(a['Kplastic'][a['Idp'][:,0]>=2060,0])),NN_min_over_dp=float(m['nn'].min()) if m else None,NN_median_over_dp=float(np.median(m['nn'])) if m else None,near_pairs_lt0p7dp=len(m['pairs']) if m else None);body.append(row);extrema_update(extrema,a,g,part,tau,step);soil=a['Idp'][:,0]>=2060;slots=np.flatnonzero(soil)
    if m:cohorts.extend(cluster.summarize(m,dict(group=g['label'],part=part,time_s=time,tau_s=tau,completed_step=step)))
    for identity in native.FOCUS:
     i=identity-2060;s=slots[i];c.need(int(a['Idp'][s,0])==identity,'Original native focus identity differs');focus.append(dict(group=g['label'],part=part,time_s=time,tau_s=tau,completed_step=step,native_id=identity,x_m=float(a['Posd'][s,0]),z_m=float(a['Posd'][s,2]),p_Pa=float(a['PorePress'][s,0]),excess_fixed_P0_Pa=float(a['ExcessPorePress'][s,0]),FSType=int(a['FSType'][s,0]),J=float(a['PoroVolumeRatio'][s,0]),kappa=float(a['Kplastic'][s,0]),speed_m_s=float(np.linalg.norm(a['Vel'][s].astype(float))),effective_trace_Pa=float(a['SigmaState_kk'][s].sum())))
    pair.append(a)
    if part==71:last[g['label']]=dict(x=m['x'].copy(),fixed=m['fixed'].copy(),ids=m['ids'].copy(),FS=a['FSType'][soil,0].copy(),p=m['p'].copy(),kappa=m['kappa'].copy(),nn=m['nn'].copy(),pairs=m['pairs'].copy(),time=time,tau=tau)
   a,b=pair;soil=a['Idp'][:,0]>=2060;d=dict(part=part,time_s=scalar,tau_s=scalar-float(old['done']['source_actual_time_s']),completed_step=4000000+4000*(part+1))
   for key in ('p_mean_Pa','p_min_Pa','p_max_Pa','p_RMS_Pa','negative_p_soil_count','mean_settlement_from_PRE_mm','front_particle_center_x_m','max_particle_center_z_m','velocity_RMS_m_s','max_speed_m_s','effective_stress_Frobenius_RMS_Pa','total_stress_Frobenius_RMS_Pa','max_kappa','min_J','max_J'):d[key+'_Shepard_minus_off']=body[-1][key]-body[-2][key]
   for key in ('NN_min_over_dp','near_pairs_lt0p7dp'):d[key+'_Shepard_minus_off']=body[-1][key]-body[-2][key] if part in SPACING else None
   for field,unit in (('PorePress','Pa'),('Kplastic','1'),('PoroVolumeRatio','1'),('Vel','m_s'),('Posd','m')):v=b[field][soil].astype(float)-a[field][soil].astype(float);norm=np.linalg.norm(v,axis=1);d[field+'_same_ID_RMS_difference_'+unit]=float(np.sqrt(np.mean(norm*norm)));d[field+'_same_ID_max_difference_'+unit]=float(norm.max())
   sk=b['SigmaState_kk'][soil]-a['SigmaState_kk'][soil];ij=b['SigmaState_ij'][soil]-a['SigmaState_ij'][soil];d['effective_stress_same_ID_Frobenius_RMS_difference_Pa']=float(np.sqrt(np.mean(np.sum(sk*sk,axis=1)+2*np.sum(ij*ij,axis=1))));d['different_saved_FS_IDs']=int(np.count_nonzero(a['FSType'][soil]!=b['FSType'][soil]));differences.append(d)
   if (part+1)%15==0:print('SAVED72_PAIR',part+1,flush=True)
  c.need(fb.read(1)==b'' and fa.tell()==12+72*old['dtype'].itemsize,'Saved72 prefix/actual candidate72 extent differs; baseline keeps18 unconsumed records')
 mr,mw,ms=meter(new['run'],float(new['done']['source_actual_time_s']),new['clocks']);c.need(len(body)==144 and len(cohorts)==96 and len(focus)==1152,'Full72/all5000/focus/eight-time cohort accounting differs')
 for leaf,rows in (('history',body),('differences',differences),('focus',focus),('cohorts',cohorts),('extrema',list(extrema.values())),('meter',mr),('meter_windows',mw)):files.append(write(leaf,rows))
 def finish(fig,leaf):
  p=Path(str(PREFIX)+'_'+leaf+'.png');fig.savefig(p,dpi=160);plt.close(fig);files.append(p)
 colors={old['label']:'C0',new['label']:'C1'};fig,axes=plt.subplots(3,3,figsize=(16,11),layout='constrained')
 for g in groups:
  rr=[r for r in body if r['group']==g['label']];t=[r['tau_s'] for r in rr];color=colors[g['label']]
  for key,style in (('p_min_Pa','--'),('p_max_Pa',':'),('p_RMS_Pa','-')):axes[0,0].plot(t,[r[key]*.001 for r in rr],style,c=color,label=g['label']+' '+key)
  for index,keys,scale in ((1,('velocity_RMS_m_s','max_speed_m_s'),1.),(2,('mean_settlement_from_PRE_mm',),1.),(3,('front_particle_center_x_m','max_particle_center_z_m'),1.),(4,('effective_stress_Frobenius_RMS_Pa','total_stress_Frobenius_RMS_Pa'),.001),(5,('max_kappa','mean_kappa'),1.),(6,('min_J','max_J'),1.),(7,('NN_min_over_dp','NN_median_over_dp'),1.)):
   for key,style in zip(keys,('-','--')):
    use=[r for r in rr if r[key] is not None];axes.ravel()[index].plot([r['tau_s'] for r in use],[r[key]*scale for r in use],style,c=color,marker='o' if index==7 else None,ms=3,label=g['label']+' '+key)
 for i,identity in enumerate((7017,5944,6814)):
  for g in groups:
   rr=[r for r in focus if r['group']==g['label'] and r['native_id']==identity];axes[2,2].plot([r['tau_s'] for r in rr],[r['p_Pa']*.001 for r in rr],'-' if g is new else '--',c='C'+str(i),label=str(identity)+' '+g['label'])
 for ax,title in zip(axes.ravel(),('Saved pressure [kPa]','Speed [m/s]','PRE mean settlement [mm]','Particle-center front / height [m]','Stress Frobenius RMS [kPa]','Plastic history','J range','Soil NN / dp: eight selected saves','Native fixed-ID pressure [kPa]')):ax.set(title=title,xlabel='Actual tau since certified PRE [s]');ax.grid(alpha=.2);ax.legend(fontsize=5)
 axes[0,0].set_yscale('symlog',linthresh=1.);axes[2,2].set_yscale('symlog',linthresh=1.);fig.suptitle('Failed Shepard40 prefix: same total-AS .2/n3; saved72 states only, descriptive');finish(fig,'history')
 fig,axes=plt.subplots(2,3,figsize=(16,9),layout='constrained');t=np.asarray([r['tau_s'] for r in mr])
 for key,style in (('p_before_min_Pa','--'),('p_after_min_Pa','-'),('p_before_max_Pa',':'),('p_after_max_Pa','-.')):axes[0,0].plot(t,[float(r[key])*.001 for r in mr],style,lw=.7,label=key)
 for key in ('cumulative_net_delta_S','cumulative_abs_net_delta_S','cumulative_abs_weighted_delta_S'):axes[0,1].plot(t,[r[key] for r in mr],lw=.8,label=key)
 axes[0,2].plot(t,[float(r['max_abs_delta_p_Pa'])*.001 for r in mr],lw=.7,label='max particle |delta p|');axes[1,0].plot(t,[float(r['changed_pressure_bits']) for r in mr],lw=.6,label='changed pressure bit-patterns')
 for ax,lo,hi in ((axes[1,1],.52,.54),(axes[1,2],.722,.7247)):
  rr=[r for r in mr if lo<=r['tau_s']<hi]
  for key,style in (('p_before_min_Pa','--'),('p_after_min_Pa','-'),('p_before_max_Pa',':'),('p_after_max_Pa','-.')):ax.plot([r['tau_s'] for r in rr],[float(r[key])*.001 for r in rr],style,lw=.8,label=key)
  ax.set_title('Actual meter tau [%g,%g) [kPa]'%(lo,hi));ax.set_yscale('symlog',linthresh=1.)
 for ax,title in zip(axes.ravel()[:4],('All-soil filter envelopes [kPa]','Cumulative model S changes; not fluid mass','Per-call pressure correction [kPa]','Actual changed float pressure patterns')):ax.set_title(title)
 for ax in axes.ravel():ax.set_xlabel('Actual completed-filter scalar tau [s]');ax.grid(alpha=.2);ax.legend(fontsize=6)
 axes[0,0].set_yscale('symlog',linthresh=1.);fig.suptitle('7246 actual wrapper calls; final46 beyond last native save, no unsaved field reconstruction');finish(fig,'meter')
 fig,axes=plt.subplots(3,2,figsize=(12,12),layout='constrained')
 for row,(field,title) in enumerate((('p','Raw p [Pa]'),('kappa','kappa'),('nn','Nonself NN / dp'))):
  lo=min(q[field].min() for q in last.values());hi=max(q[field].max() for q in last.values());norm=SymLogNorm(1000.,vmin=lo,vmax=hi) if field=='p' else plt.Normalize(lo,hi if hi>lo else lo+1.)
  for col,g in enumerate(groups):
   q=last[g['label']];ax=axes[row,col];x=q['x'];sc=ax.scatter(x[:,0],x[:,1],c=q[field],norm=norm,s=5,cmap='coolwarm' if field=='p' else 'viridis');ax.scatter(q['fixed'][:,0],q['fixed'][:,1],s=2,c='.65');
   if field=='nn' and len(q['pairs']):ax.add_collection(LineCollection(x[q['pairs']],colors='red',linewidths=.5))
   ax.set(title=g['label']+' tau %.9f: '%q['tau']+title,xlabel='x [m]',ylabel='z [m]',aspect='equal');fig.colorbar(sc,ax=ax,label=title)
 fig.suptitle('Last shared actual .72s save; common full raw ranges, red pairs r<.7dp');finish(fig,'final')
 c.need(all(c.stat(e['path'])==e for e in before),'Closed input/helper changed');result=dict(stage=TAG,passed=True,analysis_completed=True,actual_matched_samples=72,original_headers={old['label']:[6805,22,90],new['label']:[6805,22,72]},candidate_runtime_success=False,original_plan_samples=90,original_planned_end=4360000,last_saved_completed_step=4288000,last_saved_actual_time_s=scalar,unsaved_failure_time_known=False,soil_IDs_per_sample=5000,spacing_parts=list(SPACING),spacing_frames_per_group=8,typed_sequential_passes_per_group=1,all22_finite_and_ID_checks=True,clock_steps_and_P0_bits_match=True,source_programs_intentionally_differ=True,numerical_smoothing_not_theory_error=True,cross_option_5Pa_or_half_gates=False,native_pressure_peaks_are_saved_10ms_samples=True,meter_global_envelopes_not_fixed_ID_extrema=True,meter=ms,meter_windows=mw,native_focus_IDs=list(native.FOCUS),saved_extrema=list(extrema.values()),final_history=[q for q in body if q['part']==71],physical_acceptance=False,repair_claimed=False,other_psi_admitted=False,dense_causal_trace_read=False,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,build_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed=before,consumed_stats_unchanged=True,files=[c.stat(p) for p in files])
 with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
 print('SHEPARD_COMPARE_READY',CHECK,flush=True)

if __name__=='__main__':main()
