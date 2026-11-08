"""Compare51 sealed saved states: fresh effective-AS failure versus byte-certified total-AS n3 prefix."""
import argparse,csv,json,math,struct
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from upl_c08_fsmask_r1 import SCHEMA,TYPES
T=Path(__file__).resolve().parents[1];TAG='upl_c08_as_effective_partial_review_r1';PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json')
N=6805;DP=.04;HDP=1.2;DT=.0000025;EPS=.2;EXP=3.;FOCUS=(7013,7015,6963,7014,7017,5944,6814,5208)
SPECS=(('total_n3','upl_c08_causal_window_GPU_r1.native_r1.json',90,'source_run','original_native_guards_passed',0),('effective_n3','upl_c08_as_effective_partial_r1.check.json',51,'source_failed_run','original_saved_native_guards_passed',1))

def need(x,s):
 if not x:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def bind(e):need(stat(e['path'])==e,'Closed input changed: '+e['path']);return e
def entry(entries,path):return bind(next(e for e in entries if Path(e['path']).resolve()==Path(path).resolve()))
def bits(x):return struct.pack('<d',float(x))
def table(p):
 with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(leaf,rows,empty=()):
 p=Path(str(PREFIX)+'_'+leaf+'.csv');keys=list(rows[0]) if rows else list(empty)
 with p.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
 return p
def cubic(q):return 1.-1.5*q*q+.75*q*q*q if q<=1. else .25*(2.-q)**3 if q<2. else 0.
def tensor(frame,slots):
 d=frame['SigmaState_kk'][slots];s=frame['SigmaState_ij'][slots];a=np.zeros((len(slots),3,3));a[:,range(3),range(3)]=d;a[:,0,1]=a[:,1,0]=s[:,0];a[:,1,2]=a[:,2,1]=s[:,1];a[:,0,2]=a[:,2,0]=s[:,2];return a

def load(spec,before):
 label,leaf,count,runkey,guard,rc=spec;p=T/'logs'/leaf;r=read(p);need(r['passed'] and r[guard] and r['consumed_stats_unchanged'] and not r['physical_acceptance'],'Closed native guards required');before.extend((stat(p),bind(r['completion']),bind(r['metadata']),bind(r[runkey])));done=read(r['completion']['path']);native=Path(r['completion']['path']).parent;run=read(r[runkey]['path']);need(run['actual_exit']==run['actual_Win32_exit']==rc and run['consumed_stats_unchanged'] and bool(run['passed'])==(rc==0),'Actual source run status differs');before.extend(bind(run[k]) for k in ('program','source_build','source_capture','source_archive','source_pre_file'));metadata=read(r['metadata']['path'])
 need(done['passed'] and done['samples']==count and done['actual_native_IDs_per_frame']==N and done['typed_arrays']==22 and done['soil_IDs']==5000 and done['actual_fixed_IDs']==1805 and done['kept_bed_IDs']==[1800,1852,1904,1956,2008] and done['actual_retired_count']==255 and done['source_material_law_version']==1 and done['target_material_law_version']==2 and done['plane_x_m']==done['plane_z_m']==0 and not done['reaction_J_Darcy_closed'],'Original6805/22/keep5/plane scope differs')
 need(metadata['passed'] and metadata['samples']==count and metadata['expected_AS'] and metadata['AS_policy']=='ReleaseOnly' and metadata['AS_coefficient_float_reference']==float(np.float32(EPS)) and metadata['AS_exponent_float_reference']==EXP and metadata['expected_ponding_policy']=='CompletedOnly' and metadata['ponding_policy_keys_absent_headers']==count,'AS/ponding metadata differs')
 if rc:need(r['partial'] and not r['runtime_success_claimed'] and run['AS_stress_space']=='effective_test_only' and not done['failure_unsaved_state_reconstructed'],'Failed effective-AS prefix identity differs')
 else:need(done['completed_runtime_Run_csv_checked'],'Retained normal n3 window required')
 for q in ('typed22.bin','typed22_layout.csv','clocks.csv'):before.append(entry(r.get('files',r.get('outputs',[])),native/q))
 layout=table(native/'typed22_layout.csv');clocks=table(native/'clocks.csv');need(len(layout)==22 and len(clocks)==count,'Original full file extents differ');fields=[('time','<f8')]
 for row,(name,kind,width) in zip(layout,SCHEMA):need((row['array'],row['type'],int(row['components']),int(row['bytes_per_particle']))==(name,kind,width,TYPES[kind].itemsize*width),'Literal22 array schema differs');fields.append((name,TYPES[kind],(N,width)))
 dtype=np.dtype(fields);need(dtype.itemsize==8+N*212,'Literal native record stride differs')
 with (native/'typed22.bin').open('rb') as f:need(struct.unpack('<III',f.read(12))==(N,22,count) and (native/'typed22.bin').stat().st_size==12+count*dtype.itemsize,'Original51/90 header or byte extent differs; never rewrite')
 return dict(label=label,done=done,run=run,native=native,clocks=clocks,frames=np.memmap(native/'typed22.bin',mode='r',offset=12,dtype=dtype,shape=(count,)),count=count)

def inspect(ctx,part,scalar,expected):
 a=ctx['frames'][part];c=ctx['clocks'][part];need(np.array_equal(a['Idp'][:,0],expected) and bits(a['time'])==bits(scalar)==bits(c['time_s']) and int(c['completed_step'])==4000000+4000*(part+1) and int(c['saved_step'])==4000000+4000*(part+1)-1 and int(c['dterror_interval_empty'])==0 and -np.finfo(float).max<float(c['signed_dterror_s'])<=1e-14,'Real saved IDs/clock/signed interval differs')
 for name,kind,width in SCHEMA:need(np.isfinite(a[name]).all(),'Nonfinite saved array '+name)
 slots=np.flatnonzero(a['Idp'][:,0]>=2060);need(len(slots)==5000 and np.all(a['Posd'][slots,1]==0),'Exact5000 planar soil required');return a,slots

def measure(ctx,a,slots,part,time,tau,history,focus,extrema,pairrows):
 ids=a['Idp'][slots,0];x=a['Posd'][slots];v=a['Vel'][slots].astype(float);p=a['PorePress'][slots,0].astype(float);J=a['PoroVolumeRatio'][slots,0];kap=a['Kplastic'][slots,0].astype(float);fs=a['FSType'][slots,0];eff=tensor(a,slots);total=eff.copy();total[:,range(3),range(3)]-=p[:,None];speed=np.linalg.norm(v,axis=1);common=dict(group=ctx['label'],part=part,completed_step=4000000+4000*(part+1),time_s=time,tau_s=tau)
 values=dict(p_Pa=p,speed_m_s=speed,J=J,kappa=kap,effective_trace_Pa=np.trace(eff,axis1=1,axis2=2),total_trace_Pa=np.trace(total,axis1=1,axis2=2),x_m=x[:,0],z_m=x[:,2])
 for label,t in (('effective',eff),('total',total)):
  for name,i,j in (('xx',0,0),('yy',1,1),('zz',2,2),('xy',0,1),('yz',1,2),('xz',0,2)):values[label+'_'+name+'_Pa']=t[:,i,j]
 row=dict(common,p_mean_Pa=float(p.mean()),p_RMS_Pa=float(np.sqrt(np.mean(p*p))),velocity_RMS_m_s=float(np.sqrt(np.mean(speed*speed))),effective_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(eff*eff,axis=(1,2))))),total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(total*total,axis=(1,2))))),FS23_count=int(np.isin(fs,(2,3)).sum()))
 for name,u in values.items():
  for direction,index in (('min',int(np.argmin(u))),('max',int(np.argmax(u)))):
   row[name+'_'+direction]=float(u[index]);row[name+'_'+direction+'_ID']=int(ids[index]);extrema.append(dict(common,field=name,direction=direction,value=float(u[index]),native_ID=int(ids[index]),x_m=float(x[index,0]),z_m=float(x[index,2]),p_Pa=float(p[index]),J=float(J[index]),kappa=float(kap[index]),speed_m_s=float(speed[index]),FS=int(fs[index])))
 for identity in FOCUS:
  i=int(identity-2060);need(ids[i]==identity,'Fixed material focus differs');q=dict(common,native_ID=identity,x_m=float(x[i,0]),z_m=float(x[i,2]),FS=int(fs[i]));q.update({name:float(u[i]) for name,u in values.items() if name not in ('x_m','z_m')});focus.append(q)
 # A sufficient saved-state NEXT predictor exclusion, using original dx=(dt/2)*v_n.
 margins=x[:,(0,2)]-(DT*.5)*np.abs(v[:,(0,2)]);trial=x[:,(0,2)]+(DT*.5)*v[:,(0,2)];row.update(next_predictor_excluded_both=int(np.count_nonzero(np.all(margins>0,axis=1))),next_predictor_not_excluded_both=int(np.count_nonzero(~np.all(margins>0,axis=1))),next_predictor_trial_hit_x=int(np.count_nonzero(trial[:,0]<=0)),next_predictor_trial_hit_z=int(np.count_nonzero(trial[:,1]<=0)),next_predictor_margin_x_min_m=float(margins[:,0].min()),next_predictor_margin_z_min_m=float(margins[:,1].min()),next_predictor_margin_x_min_ID=int(ids[np.argmin(margins[:,0])]),next_predictor_margin_z_min_ID=int(ids[np.argmin(margins[:,1])]))
 tree=cKDTree(x[:,(0,2)]);_,at=tree.query(x[:,(0,2)],k=2);own=np.arange(5000);near=at[own,np.where(at[:,0]!=own,0,1)];nn=np.linalg.norm(x-x[near],axis=1)/DP;need(np.all(near!=own),'Nonself NN selection differs');close=tree.query_pairs(.7*DP,output_type='ndarray');dist=np.linalg.norm(x[close[:,0]]-x[close[:,1]],axis=1) if len(close) else np.empty(0);keep=dist<.7*DP;close,dist=close[keep],dist[keep];row.update(NN_min_over_dp=float(nn.min()),NN_p01_over_dp=float(np.quantile(nn,.01)),NN_median_over_dp=float(np.median(nn)),NN_below_0p5dp=int(np.count_nonzero(nn<.5)),NN_below_0p7dp=int(np.count_nonzero(nn<.7)),pairs_below_0p7dp=len(close),coincident_pairs=int(np.count_nonzero(dist==0)),closest_ID=int(ids[np.argmin(nn)]),closest_neighbor_ID=int(ids[near[np.argmin(nn)]]))
 # Conditional double-saved pair score; momentum uses total stress in BOTH programs.
 valid=dist>0;close,dist=close[valid],dist[valid];spectral_input=total if ctx['label']=='total_n3' else eff;eig,Q=np.linalg.eigh(spectral_input);positive=(Q*np.maximum(eig,0.)[:,None,:])@Q.transpose(0,2,1);scores=[];closing=attractive=repulsive=unresolved=0
 for ij,r in zip(close,dist):
  i,j=map(int,ij);direction=(x[i]-x[j])/r;s=float(r/DP);ratio=cubic(s/HDP)/cubic(1./HDP);F=EPS*ratio**EXP;raw=float(direction@(total[i]+total[j])@direction);art=-F*float(direction@(positive[i]+positive[j])@direction);net=raw+art;screen=32*np.finfo(np.float32).eps*(1.+F)*max(1.,float(np.abs(eig[i]).max()+np.abs(eig[j]).max()),float(np.abs(total[i]).max()+np.abs(total[j]).max()));sign='near_zero_unresolved' if abs(net)<=screen else 'attractive_shadow' if net>0 else 'repulsive_shadow';dr=float((v[i]-v[j])@direction);attractive+=sign=='attractive_shadow';repulsive+=sign=='repulsive_shadow';unresolved+=sign=='near_zero_unresolved';closing+=dr<0;scores.append(net);pairrows.append(dict(common,id_i=int(ids[i]),id_j=int(ids[j]),x_i_m=float(x[i,0]),z_i_m=float(x[i,2]),x_j_m=float(x[j,0]),z_j_m=float(x[j,2]),r_over_dp=s,separation_rate_m_s=dr,AS_spectral_input='total' if ctx['label']=='total_n3' else 'effective',AS_epsilon=EPS,AS_exponent=EXP,kernel_ratio=ratio,F_includes_epsilon=F,total_normal_Pa=raw,AS_normal_Pa=art,net_normal_Pa=net,float_screen_Pa=float(screen),net_sign=sign,p_i_Pa=float(p[i]),p_j_Pa=float(p[j]),J_i=float(J[i]),J_j=float(J[j]),kappa_i=float(kap[i]),kappa_j=float(kap[j]),FS_i=int(fs[i]),FS_j=int(fs[j])))
 row.update(pair_attractive_shadow=attractive,pair_repulsive_shadow=repulsive,pair_unresolved_shadow=unresolved,pair_closing=closing,pair_net_normal_max_Pa=max(scores) if scores else None,pair_net_normal_min_Pa=min(scores) if scores else None);history.append(row);return dict(ids=ids,x=x.copy(),p=p.copy(),J=J.copy(),kappa=kap.copy(),speed=speed.copy(),nn=nn.copy())

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read before one offline execution');need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial derived outputs protected');before=[stat(__file__),stat(T/'notes'/(TAG+'.md')),stat(T/'support/upl_c08_fsmask_r1.py')];prefix=T/'logs/upl_c08_causal_prefix90_r1.check.json';r=read(prefix);need(r['passed'] and r['actual_common_saved_frames']==90 and r['all22_and_actual_time_payload_byte_exact'] and r['typed_layout_byte_exact'] and r['signed_clock_header_and_common_rows_byte_exact'] and r['consumed_stats_unchanged'],'Retained n3 causal90 must have real full-r6 byte proof');before.append(stat(prefix));contexts=[load(spec,before) for spec in SPECS];need(contexts[0]['run']['source_pre_file']==contexts[1]['run']['source_pre_file'],'Same actual certified PRE required');need(bits(contexts[0]['done']['source_actual_time_s'])==bits(contexts[1]['done']['source_actual_time_s']),'Actual PRE clocks differ');oldentries=r['consumed']
 for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv','completion.json'):before.append(entry(oldentries,contexts[0]['native']/leaf))
 expected=np.sort(np.r_[np.arange(1800),(1800,1852,1904,1956,2008),np.arange(2060,7060)]).astype('uint32');history=[];focus=[];extrema=[];pairrows=[];last={};scalar=float(contexts[0]['done']['source_actual_time_s']);P0=None
 for part in range(51):
  for _ in range(4000):scalar+=DT
  for ctx in contexts:
   a,slots=inspect(ctx,part,scalar,expected);base=a['PorePress0'].view('<u4');P0=base.copy() if P0 is None else P0;need(np.array_equal(base,P0),'Immutable source P0 bits differ');last[ctx['label']]=measure(ctx,a,slots,part,scalar,scalar-float(ctx['done']['source_actual_time_s']),history,focus,extrema,pairrows)
 files=[write('history',history),write('focus',focus),write('extrema',extrema),write('pairs',pairrows,('group','part','time_s','tau_s','id_i','id_j','r_over_dp','net_normal_Pa'))];colors={'total_n3':'C0','effective_n3':'C1'};series={ctx['label']:[q for q in history if q['group']==ctx['label']] for ctx in contexts}
 def curves(ax,keys,scale=1.):
  for label,rows in series.items():
   for key,style in zip(keys,('-','--',':','-.')):ax.plot([q['tau_s'] for q in rows],[q[key]*scale for q in rows],color=colors[label],ls=style,lw=.9,label=label+' '+key)
 def finish(fig,leaf):
  p=Path(str(PREFIX)+'_'+leaf+'.png');fig.savefig(p,dpi=165);plt.close(fig);files.append(p)
 fig,axes=plt.subplots(3,2,figsize=(14,10),constrained_layout=True);curves(axes[0,0],('p_Pa_min','p_Pa_max','p_RMS_Pa'),.001);curves(axes[0,1],('speed_m_s_max','velocity_RMS_m_s'));curves(axes[1,0],('J_min','J_max'));curves(axes[1,1],('kappa_max',));curves(axes[2,0],('effective_stress_Frobenius_RMS_Pa','total_stress_Frobenius_RMS_Pa'),.001);curves(axes[2,1],('x_m_max','z_m_max'))
 for ax,title,unit in zip(axes.ravel(),('Raw saved pressure','Speed','J','Plastic history','Effective / total stress RMS','Front center / top'),('p [kPa], signed symlog','Speed [m/s]','J','kappa','Frobenius RMS [kPa]','Position [m]')):ax.set(title=title,xlabel='Actual time minus actual PRE [s]',ylabel=unit);ax.ticklabel_format(axis='x',style='plain',useOffset=False);ax.grid(alpha=.2);ax.legend(fontsize=6)
 axes[0,0].set_yscale('symlog',linthresh=1.);fig.suptitle('Fresh GPU n3: total-AS versus effective-AS saved prefix only. Failed effective run is not relabelled success.');finish(fig,'history')
 fig,axes=plt.subplots(2,2,figsize=(14,9),constrained_layout=True)
 for j,identity in enumerate(FOCUS):
  for label,style in (('total_n3','--'),('effective_n3','-')):
   rr=[q for q in focus if q['group']==label and q['native_ID']==identity]
   for ax,key,scale in zip(axes.ravel(),('p_Pa','J','speed_m_s','kappa'),(.001,1.,1.,1.)):ax.plot([q['tau_s'] for q in rr],[q[key]*scale for q in rr],color='C'+str(j),ls=style,lw=.8,label=str(identity)+' '+label)
 for ax,title in zip(axes.ravel(),('p [kPa], signed symlog','J','Speed [m/s]','kappa')):ax.set(xlabel='Actual elapsed from PRE [s]',ylabel=title);ax.grid(alpha=.2);ax.legend(fontsize=6,ncol=2);ax.ticklabel_format(axis='x',style='plain',useOffset=False)
 axes[0,0].set_yscale('symlog',linthresh=1.);fig.suptitle('Fixed material IDs. All-particle extrema and their migrating IDs are separately retained.');finish(fig,'focus')
 fig,axes=plt.subplots(2,2,figsize=(14,9),constrained_layout=True);curves(axes[0,0],('NN_min_over_dp','NN_p01_over_dp','NN_median_over_dp'));curves(axes[0,1],('pairs_below_0p7dp','pair_closing','pair_attractive_shadow','pair_repulsive_shadow'))
 for label,rows in series.items():
  xx=[q['tau_s'] for q in rows];axes[1,0].plot(xx,[1000*q['next_predictor_margin_z_min_m'] for q in rows],color=colors[label],label=label+' z margin');axes[1,0].plot(xx,[1000*q['next_predictor_margin_x_min_m'] for q in rows],color=colors[label],ls='--',label=label+' x margin')
  for key,style in (('p_Pa_min_ID','-'),('speed_m_s_max_ID','--')):axes[1,1].step(xx,[q[key] for q in rows],where='post',color=colors[label],ls=style,lw=.8,label=label+' '+key)
 for ax,title,unit in zip(axes.ravel(),('Nonself soil NN','Strict r < .7dp pair descriptions','Sufficient NEXT predictor exclusion','All5000 extrema-ID migration'),('NN / dp','Count','min(gap - dt/2 * abs(v)) [mm]','Native ID')):ax.set(title=title,xlabel='Actual elapsed from PRE [s]',ylabel=unit);ax.grid(alpha=.2);ax.legend(fontsize=6);ax.ticklabel_format(axis='x',style='plain',useOffset=False)
 fig.suptitle('Pair score is a frozen radial stress shadow, not actual GPU force. Saved predictor margin does not prove unsaved corrector behavior.');finish(fig,'spacing')
 fig,axes=plt.subplots(2,4,figsize=(17,8),constrained_layout=True)
 for col,(field,scale,title) in enumerate((('p',.001,'p [kPa]'),('kappa',1.,'kappa'),('J',1.,'J'),('speed',1.,'Speed [m/s]'))):
  lo=min(a[field].min()*scale for a in last.values());hi=max(a[field].max()*scale for a in last.values());hi=hi if hi>lo else lo+np.finfo(float).eps*max(1.,abs(lo))
  for row,label in enumerate(('total_n3','effective_n3')):a=last[label];ax=axes[row,col];sc=ax.scatter(a['x'][:,0],a['x'][:,2],c=a[field]*scale,s=5,cmap='coolwarm' if field=='p' else 'viridis',vmin=lo,vmax=hi);ax.set(title=label+' tau .51: '+title,xlabel='x [m]',ylabel='z [m]',aspect='equal');fig.colorbar(sc,ax=ax,label=title)
 fig.suptitle('Last shared actual saved state; all5000 particles, complete shared raw ranges, no clipping or smoothing.');finish(fig,'fields')
 need(all(stat(e['path'])==e for e in before),'Closed consumed file changed');summary={}
 for label,rows in series.items():
  summary[label]=dict(saved_frames=51,soil_observations=255000,next_predictor_sufficient_exclusions=sum(q['next_predictor_excluded_both'] for q in rows),next_predictor_not_excluded=sum(q['next_predictor_not_excluded_both'] for q in rows),next_predictor_trial_hits_x=sum(q['next_predictor_trial_hit_x'] for q in rows),next_predictor_trial_hits_z=sum(q['next_predictor_trial_hit_z'] for q in rows),minimum_x_margin_m=min(q['next_predictor_margin_x_min_m'] for q in rows),minimum_z_margin_m=min(q['next_predictor_margin_z_min_m'] for q in rows),saved_extrema={field+'_'+direction:min((q for q in extrema if q['group']==label and q['field']==field and q['direction']==direction),key=lambda q:q['value']) if direction=='min' else max((q for q in extrema if q['group']==label and q['field']==field and q['direction']==direction),key=lambda q:q['value']) for field,direction in (('p_Pa','min'),('p_Pa','max'),('speed_m_s','max'),('J','min'),('J','max'),('kappa','max'))})
 result=dict(stage=TAG,passed=True,analysis_completed=True,actual_common_saved_frames=51,original_headers={'total_n3':[N,22,90],'effective_n3':[N,22,51]},actual_step_clock_match=True,P0_bits_equal=True,summary=summary,fixed_material_focus_IDs=list(FOCUS),all_fields_extrema_IDs_exported=True,AS_spectral_inputs={'total_n3':'sigma_effective-pI','effective_n3':'sigma_effective'},momentum_raw_tensor_both='sigma_effective-pI',AS_epsilon_once=True,AS_exponent=EXP,pair_double_saved_shadow_not_GPU_float_replay=True,pair_float_screen_not_certified_error_budget=True,pair_positive_score_means_attractive=True,pair_score_not_actual_acceleration=True,NN_thresholds_descriptive_not_admission=True,predictor_exclusion_is_saved_state_next_stage_only=True,unsaved_corrector_contact_excluded=False,unsaved_failure_reconstructed=False,effective_runtime_success=False,effective_first_engine_exception=contexts[1]['run'].get('first_engine_exception_text'),smaller_saved_peak_is_not_accuracy=True,physical_acceptance=False,other_psi_admitted=False,visual_QA_pending=True,consumed=before,consumed_stats_unchanged=True,files=[stat(p) for p in files],solver_invocations=0,decoder_invocations=0,VTK_invocations=0,build_invocations=0,SHA_scans=0)
 with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
 print('EFFECTIVE_AS_PARTIAL_REVIEW_READY',CHECK,flush=True)

if __name__=='__main__':main()
