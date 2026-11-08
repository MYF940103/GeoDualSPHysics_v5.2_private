"""Closed4000-step AS-definition intervention versus retained CPU total-AS; endpoint geometry is descriptive."""
import argparse,csv,json,math,struct
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from upl_c08_asn4_coupled_review_r1 import STATES,POINTS,FIELDS
T=Path(__file__).resolve().parents[1];TAG='upl_c08_as_effective_review_r1';PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json');NATIVE=T/'outputs/upl_c08_asn4_window_GPU_r1/native_partial_r1';FOCUS=(7013,7015,6963,7014);DP=.04;DT=.0000025
SPECS=(('CPU_total','upl_c08_asn4_coupled_cpu_r1'),('CPU_effective','upl_c08_as_effective_cpu_r1'))
GLOBAL=('p_Pa_min','p_Pa_max','p_RMS_Pa','speed_m_s_max','velocity_RMS_m_s','J_min','J_max','kappa_min','kappa_max','effective_trace_Pa_min','effective_trace_Pa_max','total_trace_Pa_min','total_trace_Pa_max','last_cor_rate_Pa_s_min','last_cor_rate_Pa_s_max','last_cor_theta_s_min','last_cor_theta_s_max','FS23_count')

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
def save(p,j):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(j,f,indent=2,allow_nan=False);f.write('\n')
def csvfile(leaf,rows):
 p=Path(str(PREFIX)+'_'+leaf+'.csv')
 with p.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 return p

def load_case(label,tag,before):
 path=T/'logs'/(tag+'.check.json');r=read(path);need(r['passed'] and r['consumed_stats_unchanged'] and r['physical_trajectory_completed'] and r['actual_integrated_updates']==4000 and r['actual_end_completed_step']==4264000 and r['actual_exit']==r['actual_Win32_exit']==0 and not r['physical_acceptance'],'Closed normal4000-update trajectory required: '+label);before.extend((stat(path),bind(r['actual_call']),bind(r['component_completion'])));call=read(r['actual_call']['path']);need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None,'Actual target closure differs');done=read(r['component_completion']['path']);need(done['passed'] and done['source_part']==64 and done['source_completed_step']==4260000 and done['physical_updates']==4000 and done['states_rows']==4000 and done['focus_rows']==16000 and done['AS_exponent']==4 and done['native_IDs']==6805 and done['soil']==5000 and done['fixed']==1805 and done['last_cor_rate_is_not_completed_state_RHS'] and not done['physical_acceptance'],'Actual completed profile differs')
 files={name:bind(next(e for e in r['files'] if Path(e['path']).name==name)) for name in ('states.csv','focus.csv')};before.extend(files.values());states=table(files['states.csv']['path']);focus=table(files['focus.csv']['path']);need(len(states)==4000 and len(focus)==16000 and list(states[0])==list(STATES) and list(focus[0])==list(POINTS),'Original62/23 schemas and4000/16000 rows required');fm={}
 for q in focus:need(None not in q and all(v is not None and math.isfinite(float(v)) for v in q.values()),'Malformed/nonfinite focus');key=(int(q['completed_step']),int(q['native_id']));need(key not in fm,'Duplicate focus');fm[key]=q
 scalar=done['source_saved_time_s'];pre=done['elastic_PRE_actual_time_s']
 for update,q in enumerate(states,1):
  scalar+=DT;step=4260000+update;need(None not in q and all(v is not None and math.isfinite(float(v)) for v in q.values()) and int(q['completed_step'])==step and int(q['updates'])==update and bits(q['time_s'])==bits(scalar) and bits(q['tau_s'])==bits(scalar-pre) and bits(q['dt_s'])==bits(DT) and -np.finfo(float).max<float(q['signed_dterror_new_window_s'])<=1e-14 and float(q['max_ledger_relative_error'])<=5e-13,'Original completed scalar+=dt/signed/finite/ledger differs')
  for identity in FOCUS:
   z=fm[(step,identity)];need(int(z['updates'])==update and bits(z['time_s'])==bits(scalar) and bits(z['tau_s'])==bits(scalar-pre),'Actual focus clock differs')
 need(bits(done['actual_end_s'])==bits(scalar),'Actual end clock differs');bp=T/'logs'/(tag+'.build.json');before.append(entry(r['consumed'],bp));return dict(label=label,check=r,done=done,states=states,focus=fm,build=read(bp),source_time=float(done['source_saved_time_s']),pre_time=float(pre))

def native_states(case,before):
 from upl_c08_fsmask_r1 import SCHEMA,TYPES
 before.append(stat(T/'support/upl_c08_fsmask_r1.py'));before.extend(entry(case['check']['consumed'],NATIVE/q) for q in ('typed22.bin','typed22_layout.csv','clocks.csv','completion.json'));d=read(NATIVE/'completion.json');need(d['passed'] and d['samples']==66 and d['typed_arrays']==22 and d['actual_native_IDs_per_frame']==6805 and d['kept_bed_IDs']==[1800,1852,1904,1956,2008],'Closed original n4/keep5 native scope differs');layout=table(NATIVE/'typed22_layout.csv');clocks=table(NATIVE/'clocks.csv');need(len(layout)==22 and len(clocks)==66,'Actual22/66 extent differs');fields=[('time','<f8')]
 for row,(name,kind,width) in zip(layout,SCHEMA):need((row['array'],row['type'],int(row['components']),int(row['bytes_per_particle']))==(name,kind,width,TYPES[kind].itemsize*width),'Original typed22 layout differs');fields.append((name,TYPES[kind],(6805,width)))
 dtype=np.dtype(fields);need(dtype.itemsize==8+6805*212,'Original native stride differs');out={};expected=np.sort(np.r_[np.arange(1800),(1800,1852,1904,1956,2008),np.arange(2060,7060)]).astype('uint32')
 with (NATIVE/'typed22.bin').open('rb') as f:
  need(struct.unpack('<III',f.read(12))==(6805,22,66) and (NATIVE/'typed22.bin').stat().st_size==12+66*dtype.itemsize,'Original native header/extent differs')
  for part,label,time in ((64,'initial_n4_part64',case['source_time']),(65,'GPU_total_part65',float(case['states'][-1]['time_s']))):
   need(int(clocks[part]['completed_step'])==4000000+4000*(part+1) and bits(clocks[part]['time_s'])==bits(time),'GPU endpoint actual clock mismatch; no interpolation');f.seek(12+part*dtype.itemsize);raw=f.read(dtype.itemsize);need(len(raw)==dtype.itemsize,'Incomplete selected native record');a=np.frombuffer(raw,dtype=dtype,count=1)[0];need(np.array_equal(a['Idp'][:,0],expected) and bits(a['time'])==bits(time),'Original selected IDs/time differ');soil=a['Idp'][:,0]>=2060;out[label]=dict(label=label,ids=a['Idp'][soil,0].copy(),x=a['Posd'][soil].copy(),vel=a['Vel'][soil].astype(float),p=a['PorePress'][soil,0].astype(float),J=a['PoroVolumeRatio'][soil,0].copy(),kappa=a['Kplastic'][soil,0].astype(float),fs=a['FSType'][soil,0].copy())
 return out

def geometry(a):
 need(np.array_equal(a['ids'],np.arange(2060,7060)) and np.isfinite(a['x']).all() and np.all(a['x'][:,1]==0),'Full5000 finite planar native positions required');x=a['x'][:,[0,2]];tree=cKDTree(x);dist,index=tree.query(x,k=2);own=np.arange(5000);which=np.where(index[:,0]!=own,0,1);nearest=index[own,which];nn=np.linalg.norm(x-x[nearest],axis=1);need(np.all(nearest!=own) and np.isfinite(nn).all(),'Invalid nonself nearest neighbor');pairs=tree.query_pairs(.7*DP,output_type='ndarray');distance=np.linalg.norm(x[pairs[:,0]]-x[pairs[:,1]],axis=1) if len(pairs) else np.empty(0);subsets={}
 for label,mask in (('all',np.ones(5000,dtype=bool)),('FS0_receivers',a['fs']==0),('FS23_receivers',np.isin(a['fs'],(2,3)))):
  v=nn[mask]/DP;subsets[label]=dict(receivers=int(mask.sum()),min=float(v.min()) if len(v) else None,median=float(np.median(v)) if len(v) else None,p05=float(np.quantile(v,.05)) if len(v) else None,p95=float(np.quantile(v,.95)) if len(v) else None,max=float(v.max()) if len(v) else None,NN_below_0p5dp=int(np.count_nonzero(v<.5)),NN_below_0p7dp=int(np.count_nonzero(v<.7)))
 stats=dict(label=a['label'],NN_over_dp=subsets,unique_soil_pairs_strict_below_0p5dp=int(np.count_nonzero(distance<.5*DP)),unique_soil_pairs_strict_below_0p7dp=int(np.count_nonzero(distance<.7*DP)),closest_receiver_ID=int(a['ids'][int(np.argmin(nn))]),closest_neighbor_ID=int(a['ids'][nearest[int(np.argmin(nn))]]),all5000_soil_only_not_force_support=True,thresholds_are_descriptive_not_acceptance_limits=True)
 return dict(nn=nn,nearest=nearest,stats=stats)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read before one offline review');need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial derived outputs protected');before=[stat(__file__),stat(T/'notes'/(TAG+'.md')),stat(T/'support/upl_c08_asn4_coupled_review_r1.py')];total,effective=[load_case(label,tag,before) for label,tag in SPECS]
 need(bits(total['source_time'])==bits(effective['source_time']) and bits(total['pre_time'])==bits(effective['pre_time']) and effective['build']['baseline_source_capture']==total['build']['source_capture'] and effective['build']['baseline_source_archive']==total['build']['source_archive'],'Declared same starting state/source baseline differs');r=effective['check'];need(r['AS_stress_space']=='effective_test_only' and r['AS_definition_probe_passed'] and effective['done']['AS_stress_space']=='effective_test_only','Intervention definition not verified');before.append(bind(r['AS_probe']));probe=read(r['AS_probe']['path']);need(probe['passed'] and probe['AS_stress_space']=='effective_test_only' and probe['actual_first_predictor_rows']==4 and probe['matches_effective_reference'] and probe['at_least_one_sample_distinguishes_total_reference'],'Existing actual-definition probe failed; do not recompute it')
 history=[];focus=[];extrema={};migrations={}
 for old,new in zip(total['states'],effective['states']):
  need(int(old['completed_step'])==int(new['completed_step']) and bits(old['time_s'])==bits(new['time_s']) and bits(old['tau_s'])==bits(new['tau_s']),'Actual CPU completed clocks differ; no interpolation');step=int(old['completed_step']);row=dict(completed_step=step,time_s=float(old['time_s']),tau_s=float(old['tau_s']),updates=int(old['updates']),elapsed_from_part64_ms=1000*(float(old['time_s'])-total['source_time']))
  for prefix,q in (('total',old),('effective',new)):
   for key in GLOBAL:row[prefix+'_'+key]=float(q[key])
   for key in GLOBAL:
    if key+'_ID' in q:row[prefix+'_'+key+'_ID']=int(q[key+'_ID'])
  history.append(row)
  for identity in FOCUS:
   a=total['focus'][(step,identity)];b=effective['focus'][(step,identity)];q=dict(completed_step=step,time_s=row['time_s'],tau_s=row['tau_s'],elapsed_from_part64_ms=row['elapsed_from_part64_ms'],native_ID=identity)
   for prefix,z in (('total',a),('effective',b)):
    for key in ('p_Pa','J','kappa','effective_trace_Pa','total_trace_Pa','completed_FS','last_cor_theta_s','last_cor_rate_Pa_s','vx','vy','vz'):q[prefix+'_'+key]=float(z[key])
    q[prefix+'_speed_m_s']=math.sqrt(sum(float(z[key])**2 for key in ('vx','vy','vz')))
   focus.append(q)
 for case in (total,effective):
  ext=[]
  for field in FIELDS:
   for direction,choose in (('min',min),('max',max)):
    key=field+'_'+direction;q=choose(case['states'],key=lambda z:float(z[key]));ext.append(dict(field=key,value=float(q[key]),native_ID=int(q[key+'_ID']),completed_step=int(q['completed_step']),time_s=float(q['time_s']),tau_s=float(q['tau_s'])))
  extrema[case['label']]=ext;migrations[case['label']]={}
  for key in ('p_Pa_min_ID','speed_m_s_max_ID'):
   values=[int(q[key]) for q in case['states']];migrations[case['label']][key]=dict(unique_native_IDs=sorted(set(values)),adjacent_ID_changes=sum(a!=b for a,b in zip(values,values[1:])),sample_occupancy_by_ID={str(identity):values.count(identity) for identity in sorted(set(values))})
 frames=native_states(effective,before);end=bind(r['endpoint_soil']);before.append(end);ep=table(end['path']);need(len(ep)==5000 and [int(q['native_id']) for q in ep]==list(range(2060,7060)) and list(ep[0])=='native_id,x,y,z,vx,vy,vz,p_Pa,kappa,J,n,rho,k,sxx,syy,szz,sxy,syz,sxz,P0_Pa,FS'.split(',') and all(math.isfinite(float(v)) for q in ep for v in q.values()),'Closed effective5000/21 endpoint differs');frames['CPU_effective_endpoint']=dict(label='CPU_effective_endpoint',ids=np.arange(2060,7060,dtype=np.uint32),x=np.asarray([[float(q[k]) for k in ('x','y','z')] for q in ep]),vel=np.asarray([[float(q[k]) for k in ('vx','vy','vz')] for q in ep]),p=np.asarray([float(q['p_Pa']) for q in ep]),J=np.asarray([float(q['J']) for q in ep]),kappa=np.asarray([float(q['kappa']) for q in ep]),fs=np.asarray([int(q['FS']) for q in ep]));geom={key:geometry(a) for key,a in frames.items()};initial=frames['initial_n4_part64'];gpu=frames['GPU_total_part65'];cpu=frames['CPU_effective_endpoint'];endpoint_rows=[]
 for i,identity in enumerate(cpu['ids']):
  delta=cpu['x'][i]-gpu['x'][i];q=dict(native_ID=int(identity),CPU_effective_minus_GPU_total_dx_mm=1000*float(delta[0]),CPU_effective_minus_GPU_total_dy_mm=1000*float(delta[1]),CPU_effective_minus_GPU_total_dz_mm=1000*float(delta[2]),CPU_effective_minus_GPU_total_distance_mm=1000*float(np.linalg.norm(delta)))
  for prefix,a in frames.items():
   q.update({prefix+'_'+key:float(value) for key,value in dict(x_m=a['x'][i,0],z_m=a['x'][i,2],p_Pa=a['p'][i],J=a['J'][i],kappa=a['kappa'][i],FS=a['fs'][i],speed_m_s=np.linalg.norm(a['vel'][i]),NN_over_dp=geom[prefix]['nn'][i]/DP).items()});q[prefix+'_nearest_soil_ID']=int(a['ids'][geom[prefix]['nearest'][i]])
  endpoint_rows.append(q)
 files=[csvfile('matched_history',history),csvfile('matched_focus',focus),csvfile('endpoint_pairs',endpoint_rows)];x=np.asarray([q['elapsed_from_part64_ms'] for q in history]);colors={'total':'C0','effective':'C1'};styles={'total':'--','effective':'-'}
 fig,axes=plt.subplots(3,2,figsize=(14,10),constrained_layout=True)
 for prefix in ('total','effective'):
  get=lambda key:np.asarray([float(q[prefix+'_'+key]) for q in history]);c=colors[prefix]
  for key,style in (('p_Pa_min','-'),('p_Pa_max','--'),('p_RMS_Pa',':')):axes[0,0].plot(x,get(key)*.001,color=c,ls=style,lw=.8,label=prefix+' '+key)
  for key,style in (('speed_m_s_max','-'),('velocity_RMS_m_s','--')):axes[0,1].plot(x,get(key),color=c,ls=style,lw=.8,label=prefix+' '+key)
  for key,style in (('J_min','-'),('J_max','--')):axes[1,0].plot(x,get(key),color=c,ls=style,lw=.8,label=prefix+' '+key)
  axes[1,1].plot(x,get('kappa_max'),color=c,lw=.8,label=prefix+' kappa max')
  for key,style in (('effective_trace_Pa_min','-'),('effective_trace_Pa_max','--'),('total_trace_Pa_min',':'),('total_trace_Pa_max','-.')):axes[2,0].plot(x,get(key)*.001,color=c,ls=style,lw=.7,label=prefix+' '+key)
  for key,style in (('p_Pa_min_ID','-'),('speed_m_s_max_ID','--')):axes[2,1].step(x,get(key),where='post',color=c,ls=style,lw=.7,label=prefix+' '+key)
 for ax,title,unit in zip(axes.ravel(),('All5000 pressure','All5000 speed','All5000 J range','All5000 plastic history','Effective/total stress traces','Global extremum-ID migration'),('p [kPa], signed symlog','Speed [m/s]','J','kappa','Trace [kPa], signed symlog','Recorded native ID')):ax.set(title=title,xlabel='Actual elapsed from imported part64 [ms]',ylabel=unit);ax.ticklabel_format(axis='x',style='plain',useOffset=False);ax.grid(alpha=.2);ax.legend(fontsize=6)
 axes[0,0].set_yscale('symlog',linthresh=1.);axes[2,0].set_yscale('symlog',linthresh=1.);fig.suptitle('Same CPU4000 completed clocks: retained total-AS versus private effective-AS intervention. Smaller peaks are not accuracy proof.');p=Path(str(PREFIX)+'_global.png');fig.savefig(p,dpi=165);plt.close(fig);files.append(p)
 fig,axes=plt.subplots(3,2,figsize=(14,10),constrained_layout=True)
 for j,identity in enumerate(FOCUS):
  rr=[q for q in focus if q['native_ID']==identity];xx=[q['elapsed_from_part64_ms'] for q in rr]
  for prefix in ('total','effective'):
   for ax,key,scale in ((axes[0,0],'p_Pa',.001),(axes[0,1],'J',1),(axes[1,0],'speed_m_s',1),(axes[1,1],'kappa',1),(axes[2,0],'total_trace_Pa',.001)):ax.plot(xx,[q[prefix+'_'+key]*scale for q in rr],color='C'+str(j),ls=styles[prefix],lw=.7,label=str(identity)+' '+prefix)
   axes[2,1].step(xx,[q[prefix+'_completed_FS'] for q in rr],where='post',color='C'+str(j),ls=styles[prefix],lw=.7,label=str(identity)+' '+prefix)
 for ax,title,unit in zip(axes.ravel(),('Fixed material pressure','Fixed material J','Fixed material speed','Fixed material kappa','Fixed material total trace','Completed FS classification'),('p [kPa], signed symlog','J','Speed [m/s]','kappa','Trace [kPa], signed symlog','FSType')):ax.set(title=title,xlabel='Actual elapsed from imported part64 [ms]',ylabel=unit);ax.ticklabel_format(axis='x',style='plain',useOffset=False);ax.grid(alpha=.2);ax.legend(fontsize=6,ncol=2)
 axes[0,0].set_yscale('symlog',linthresh=1.);axes[2,0].set_yscale('symlog',linthresh=1.);axes[2,1].set_yticks((0,1,2,3));fig.suptitle('Four material IDs, not a substitute for all-particle extrema. Cor theta/rate in CSV are retained, not completed-state RHS.');p=Path(str(PREFIX)+'_focus.png');fig.savefig(p,dpi=165);plt.close(fig);files.append(p)
 fig,axes=plt.subplots(2,2,figsize=(13,9),constrained_layout=True);lo=min(geom[key]['nn'].min()/DP for key in ('GPU_total_part65','CPU_effective_endpoint'));hi=max(geom[key]['nn'].max()/DP for key in ('GPU_total_part65','CPU_effective_endpoint'));need(hi>=lo,'Invalid NN display range');hi=hi if hi>lo else lo+np.finfo(float).eps
 for ax,key in zip(axes[0],('GPU_total_part65','CPU_effective_endpoint')):
  a=frames[key];sc=ax.scatter(a['x'][:,0],a['x'][:,2],c=geom[key]['nn']/DP,s=5,vmin=lo,vmax=hi,cmap='viridis');ax.set(title=key+'; actual5000 soil',xlabel='x [m]',ylabel='z [m]',aspect='equal');fig.colorbar(sc,ax=ax,label='Nonself soil NN / dp')
 for color,(key,a) in enumerate(frames.items()):values=np.sort(geom[key]['nn']/DP);axes[1,0].step(values,np.arange(1,5001)/5000,where='post',color='C'+str(color),lw=.9,label=key)
 axes[1,0].set(title='Empirical NN distribution; initial inherited clumping retained',xlabel='NN / dp',ylabel='Fraction of5000 soil');axes[1,0].grid(alpha=.2);axes[1,0].legend(fontsize=7);axes[1,1].axis('off');labels=list(frames);cell=[]
 for key in labels:
  g=geom[key]['stats'];n=g['NN_over_dp']['all'];cell.append([key,f"{n['min']:.5g}",f"{n['median']:.5g}",str(n['NN_below_0p5dp']),str(n['NN_below_0p7dp']),str(g['unique_soil_pairs_strict_below_0p7dp'])])
 display=axes[1,1].table(cellText=cell,colLabels=['State','NN min/dp','median','NN<.5dp','NN<.7dp','pairs<.7dp'],cellLoc='center',loc='center',colWidths=[.37,.13,.12,.13,.13,.13]);display.auto_set_font_size(False);display.set_fontsize(7);display.scale(1,1.5);axes[1,1].set_title('Geometric descriptions, not physical acceptance thresholds');fig.suptitle('Endpoint all-particle comparison is CROSS BACKEND / different definition. Old CPU total has no5000 endpoint.');p=Path(str(PREFIX)+'_endpoint_spacing.png');fig.savefig(p,dpi=165);plt.close(fig);files.append(p)
 fig,axes=plt.subplots(2,3,figsize=(15,8),constrained_layout=True)
 for col,(field,label,scale) in enumerate((('p','Absolute pressure [kPa]',.001),('kappa','kappa',1.),('J','J',1.))):
  vmin=min(float(a[field].min()*scale) for a in (gpu,cpu));vmax=max(float(a[field].max()*scale) for a in (gpu,cpu));vmax=vmax if vmax>vmin else vmin+np.finfo(float).eps*max(1.,abs(vmin))
  for row,a in enumerate((gpu,cpu)):ax=axes[row,col];sc=ax.scatter(a['x'][:,0],a['x'][:,2],c=a[field]*scale,s=5,cmap='coolwarm' if field=='p' else 'viridis',vmin=vmin,vmax=vmax);ax.set(title=a['label']+' '+field,xlabel='Native x [m]',ylabel='Native z [m]',aspect='equal');fig.colorbar(sc,ax=ax,label=label)
 fig.suptitle('All5000 raw endpoint fields, shared complete ranges per field; no smoothing/clipping. Not same-CPU field equivalence.');p=Path(str(PREFIX)+'_endpoint_fields.png');fig.savefig(p,dpi=165);plt.close(fig);files.append(p)
 need(all(stat(e['path'])==e for e in before),'Sealed input changed');save(CHECK,dict(stage=TAG,passed=True,analysis_completed=True,matched_CPU_completed_steps=4000,matched_focus_rows=16000,actual_start_part64_time_s=total['source_time'],actual_end_time_s=float(total['states'][-1]['time_s']),elastic_PRE_actual_time_s=total['pre_time'],AS_definition_probe_consumed=r['AS_probe'],probe_reference_not_recomputed=True,all_particle_global_extrema=extrema,extremum_ID_migration=migrations,geometry={key:g['stats'] for key,g in geom.items()},endpoint_dataset_scope='initial GPU part64; original GPU total-AS part65; new CPU effective-AS endpoint; no old CPU total full-field endpoint',endpoint_5000_record_rows=len(endpoint_rows),endpoint_position_difference_max_mm=max(q['CPU_effective_minus_GPU_total_distance_mm'] for q in endpoint_rows),new_definition_intervention_not_fresh_release=True,smaller_pressure_peaks_not_accuracy_proof=True,last_Cor_rate_theta_not_completed_state_RHS=True,no_full_coupled_causation_or_paper_validation_claim=True,no_new_physical_acceptance_threshold=True,physical_acceptance=False,other_psi_admitted=False,visual_QA_pending=True,consumed=before,consumed_stats_unchanged=True,files=[stat(p) for p in files],solver_invocations=0,decoder_invocations=0,VTK_invocations=0,build_invocations=0,SHA_scans=0));print('EFFECTIVE_AS_REVIEW_READY',CHECK,flush=True)

if __name__=='__main__':main()
