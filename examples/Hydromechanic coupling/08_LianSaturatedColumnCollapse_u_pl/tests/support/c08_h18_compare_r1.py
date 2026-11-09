"""Offline source/receiver review of explicit C08 H1.8 native bundles; never selects a winner."""
import os
for _key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ.setdefault(_key,'1')
import argparse,csv,json,re,struct,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize,TwoSlopeNorm
T=Path(__file__).resolve().parents[1];C=T.parent;DP=.04;FOCUS=(7010,7011,7012,6230,6231)
SCHEMA=(('Idp','uint32',1),('Posd','float64',3),('Vel','float32',3),('Sigma_kk','float32',3),('Sigma_ij','float32',3),('FSNormal','float32',3),('HydroMechLoadAce','float32',3),('native_Rhop','float32',1),('Kplastic','float32',1),('PorePress','float32',1),('PorePress0','float32',1),('ExcessPorePress','float32',1),('SigmaState_kk','float64',3),('SigmaState_ij','float64',3),('FSType','uint32',1),('PoroVolumeRatio','float64',1),('PoroPorosity','float64',1),('PoroThetaLastStage','float64',1),('PoroCurrentVolume','float64',1),('PoroMixtureDensity','float64',1),('PoroHydraulicConductivity','float64',1),('PosDiv','float32',1))
TYPES={'uint32':np.dtype('<u4'),'float32':np.dtype('<f4'),'float64':np.dtype('<f8')}
def need(ok,text):
 if not ok:raise RuntimeError(text)
def path(value):
 p=Path(value);return (p if p.is_absolute() else C/p).resolve()
def stat(value):
 p=path(value);q=p.stat();return dict(path=str(p),bytes=q.st_size,mtime_ns=q.st_mtime_ns)
def read(value):return json.loads(path(value).read_text(encoding='utf-8'))
def table(value):
 with path(value).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def bind(entry):
 need(stat(entry['path'])==entry,'Consumed stat differs: '+entry['path']);return entry
def write_csv(p,rows):
 need(bool(rows),'Empty derived table')
 with p.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def f32(value):return float(np.float32(value))
def load_bundle(spec,consumed):
 """Load schema/maps and small qualification records; does not scan the payload."""
 for key in ('tag','native_dir','source','group','actualAS','H','input_xml','native_call'):need(key in spec,'Missing explicit case key: '+key)
 root=path(spec['native_dir']);d=read(root/'completion.json');need(d['passed'] and d['typed_arrays']==22 and d['typed_bytes_per_particle']==212 and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13,'Original native qualification/budgets differ');source=d['stage']=='c08_h18_native_r1.source';need(source or d['stage']=='c08_h18_native_r1.receiver','Only the shared H1.8 native schema is supported');count=int(d['samples']);nodes=7060 if source else 6805;need(count>0 and (1<=count<=1001 if source else count in (91,301)) and int(d['native_IDs'] if source else d['actual_native_IDs_per_frame'])==nodes and d['soil_IDs']==5000 and d['ledger_checks']==count*5000 and d['P0_bits_checks']==count*nodes,'Original actual count/coverage differs');need(float(d['H'])==f32(spec['H'])==f32(.072),'Actual H/native/profile differ')
 call=read(spec['native_call']);need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and not call.get('ownership_failure') and path(call['arguments'][-1])==root,'Actual successful typed reader call/output binding required');consumed += [stat(root/'completion.json'),stat(spec['native_call']),stat(spec['input_xml'])]
 if 'run' in spec:
  r=read(spec['run']);consumed.append(stat(spec['run']));need(r.get('actual_exit') in (0,1) and r.get('actual_Win32_exit')==r.get('actual_exit'),'Real runtime exits required when supplied')
  if not source or not d['partial']:need(r['passed'] and r['actual_exit']==0,'Normal receiver/full source runtime cannot be relabelled')
 xml=ET.parse(path(spec['input_xml'])).getroot();pars={q.get('key'):q.get('value') for q in xml.findall('execution/parameters/parameter')};hyd=xml.find('execution/special/hydromechanics');need(hyd is not None and f32(xml.find('execution/constants/h').get('value'))==float(d['H']) and float(pars['DtFixed'])==5e-6,'Actual generated XML H/fixed dt required');kw=f32(hyd.find('PoreWaterBulkModulus').get('value'));need(kw>0,'Actual water bulk modulus required')
 if source:
  need(spec['group']=='psi0' and spec['actualAS'] is None and int(float(pars.get('ArtificialStress','0')))==0 and d['kappa_zero_checks']==count*nodes and d['max_noninitial_signed_dterror_s']<=1e-14,'Source must retain its elastic/ASoff qualification')
 else:
  m=read(root/'bedkeep_metadata.json');a=spec['actualAS'];need(m['passed'] and m['stage']=='c08_h18_native_r1.metadata' and m['samples']==count and m['group']==d['group']==spec['group'] and m['AS_coefficient_float_reference']==f32(a['coefficient'])==f32(pars['ArtificialStressCoef']) and m['AS_exponent_float_reference']==f32(a['exponent'])==f32(pars['ArtificialStressExp']) and m['expected_ponding_policy']=='CompletedOnly' and m['ponding_policy_keys_absent_headers']==count,'Explicit actual AS/group/CompletedOnly metadata differs');need(d['completed_runtime_Run_csv_checked'] and d['actual_fixed_IDs']==1805 and d['fixed_marker_checks']==count*1805 and d['kappa_nondecreasing_from_PRE_checks']==count*5000 and d['plane_gap_checks']==count*10000 and d['max_signed_dterror_s']<=1e-14,'Receiver coverage/original signed/contact guards differ');consumed.append(stat(root/'bedkeep_metadata.json'))
 expected=np.arange(7060,dtype=np.uint32) if source else np.sort(np.concatenate((np.arange(1800,dtype=np.uint32),np.array([1800,1852,1904,1956,2008],dtype=np.uint32),np.arange(2060,7060,dtype=np.uint32))))
 layout=table(root/'typed22_layout.csv');fields=[('time','<f8')];need(len(layout)==22,'22 literal layout rows required')
 for q,(name,kind,width) in zip(layout,SCHEMA):need((q['array'],q['type'],int(q['components']),int(q['bytes_per_particle']))==(name,kind,width,TYPES[kind].itemsize*width),'Native layout differs');fields.append((name,TYPES[kind],(nodes,width)))
 raw=root/'typed22.bin';dtype=np.dtype(fields)
 with raw.open('rb') as f:need(struct.unpack('<III',f.read(12))==(nodes,22,count),'Preserve genuine actual native headers')
 need(raw.stat().st_size==12+count*dtype.itemsize,'Actual payload extent differs');clocks=table(root/'clocks.csv');need(len(clocks)==count,'Actual clock coverage differs');consumed += [stat(root/q) for q in ('typed22.bin','typed22_layout.csv','clocks.csv')]
 for extra in spec.get('evidence',[]):consumed.append(bind(extra) if isinstance(extra,dict) else stat(extra))
 yield_rows={}
 if source:
  consumed.append(stat(root/'summary.csv'));yield_rows={int(q['part']):q for q in table(root/'summary.csv') if q['initial_material_group']=='all'};need(len(yield_rows)==count,'Source all-soil summary coverage differs')
 return dict(spec=spec,root=root,done=d,source=source,count=count,nodes=nodes,expected=expected,frames=np.memmap(raw,dtype=dtype,offset=12,mode='r',shape=(count,)),clocks=clocks,kw=kw,yield_rows=yield_rows,runtime_observed=None if 'run' not in spec else dict(passed=bool(r['passed']),solver_completed=bool(r.get('solver_completed',False)),actual_exit=r['actual_exit'],actual_Win32_exit=r['actual_Win32_exit']))
def read22(bundle,part):
 """Return one unchanged record; validate all22 finite values and its real saved clock/IDs."""
 x=bundle['frames'][part];q=bundle['clocks'][part];need(np.array_equal(x['Idp'][:,0],bundle['expected']) and all(np.isfinite(x[name]).all() for name,_,_ in SCHEMA),'Nonfinite/missing native ID or22 array');need(int(q['part'])==part and float(x['time'])==float(q['time_s']) and float(q['dt_s'])==5e-6 and float(q['signed_dterror_s'])<=1e-14,'Actual saved clock/original signed guard differs');return x
def reference_from(bundle):
 need(bundle['source'] and bundle['done']['certified_PRE'] and not bundle['done']['partial'] and bundle['done']['completed_steps']==2000000,'Receiver requires an existing full certified source native reference');a=read22(bundle,0);b=read22(bundle,bundle['count']-1);return dict(initial_pos=np.array(a['Posd']),pos=np.array(b['Posd']),p0=np.array(b['PorePress0'][:,0]),time=float(b['time']),source=bundle['spec']['source'])
def analyze_case(bundle,reference=None,snapshots_tau_s=None):
 """Analyze every actual save once; no plots/files/solver calls are made here."""
 spec=bundle['spec'];source=bundle['source'];first=read22(bundle,0);soil=first['Idp'][:,0]>=2060;ids=first['Idp'][soil,0];need(np.array_equal(ids,np.arange(2060,7060)),'Exactly5000 original soil IDs required')
 if source:initial=np.array(first['Posd'][soil]);ref=initial.copy();p0=np.array(first['PorePress0'][:,0]);base_time=0.
 else:
  need(reference is not None and reference['source']==spec['source'] and reference['time']==bundle['done']['source_actual_time_s'],'Same actual PRE reference/source clock required');initial=reference['initial_pos'][2060:];ref=reference['pos'][2060:];p0=reference['p0'][bundle['expected']];base_time=reference['time']
 zlevels,layer_index=np.unique(initial[:,2],return_inverse=True);need(len(zlevels)==50 and np.all(np.bincount(layer_index)==100),'Original fixed fifty100-ID material layers required');top=initial[:,2]==zlevels[-1];bottom=initial[:,2]==zlevels[0];clocks=bundle['clocks'];times=np.array([float(q['time_s']) for q in clocks]);tau=times-base_time;need(np.all(np.diff(times)>0),'Actual saved times must increase');requests=([float(tau[-1])] if snapshots_tau_s is None else snapshots_tau_s);selected=sorted({int(np.argmin(abs(tau-v))) for v in requests if tau[0]-5e-6<=v<=tau[-1]+5e-6});tail_start=max(float(times[0]),float(times[-1])-(1. if source or bundle['count']==301 else .3));tail_at=int(np.flatnonzero(times>=tail_start)[0]);tail_pos=None;rows=[];extrema=[];layers=[];tracks=[];snaps={};last_kappa=None
 for part in range(bundle['count']):
  x=first if part==0 else read22(bundle,part);pos=x['Posd'][soil];v=x['Vel'][soil].astype(float);p=x['PorePress'][soil,0].astype(float);ex=x['ExcessPorePress'][soil,0].astype(float);kap=x['Kplastic'][soil,0].astype(float);J=x['PoroVolumeRatio'][soil,0];n=x['PoroPorosity'][soil,0];rho=x['PoroMixtureDensity'][soil,0];volume=x['PoroCurrentVolume'][soil,0];k=x['PoroHydraulicConductivity'][soil,0];sk=x['SigmaState_kk'][soil];si=x['SigmaState_ij'][soil];total=sk-p[:,None];speed=np.linalg.norm(v,axis=1);ft=x['FSType'][soil,0];fs=(ft==2)|(ft==3);du=pos-ref;need(np.array_equal(x['PorePress0'][:,0].view('<u4'),p0.view('<u4')) and np.array_equal(x['ExcessPorePress'][:,0],np.float32(x['PorePress'][:,0]-x['PorePress0'][:,0])),'Fixed native P0/excess definition differs')
  need(last_kappa is None or np.all(kap>=last_kappa),'Original material kappa nondecrease differs');last_kappa=kap.copy();nn=None;pairs=None
  if not source:
   tree=cKDTree(pos[:,(0,2)]);dist,idx=tree.query(pos[:,(0,2)],k=2,workers=1);nn=np.min(np.where(idx!=np.arange(5000)[:,None],dist,np.inf),axis=1)/DP;pair=tree.query_pairs(.7*DP,output_type='ndarray');pairs=int(np.count_nonzero(np.linalg.norm(pos[pair[:,0]]-pos[pair[:,1]],axis=1)<.7*DP)) if len(pair) else 0
  row=dict(tag=spec['tag'],source=spec['source'],group=spec['group'],part=part,time_s=float(times[part]),tau_s=float(tau[part]),completed_step=int(clocks[part]['completed_step']),H_m=float(bundle['done']['H']),AS_coefficient=None if spec['actualAS'] is None else f32(spec['actualAS']['coefficient']),AS_exponent=None if spec['actualAS'] is None else f32(spec['actualAS']['exponent']),p_min_Pa=float(p.min()),p_max_Pa=float(p.max()),p_mean_Pa=float(p.mean()),p_RMS_Pa=float(np.sqrt(np.mean(p*p))),negative_p_soil=int(np.count_nonzero(p<0)),native_p_minus_fixedP0_min_Pa=float(ex.min()),native_p_minus_fixedP0_max_Pa=float(ex.max()),native_p_minus_fixedP0_RMS_Pa=float(np.sqrt(np.mean(ex*ex))),effective_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(sk*sk,axis=1)+2*np.sum(si*si,axis=1)))),total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(total*total,axis=1)+2*np.sum(si*si,axis=1)))),effective_zz_mean_Pa=float(sk[:,2].mean()),total_zz_mean_Pa=float(total[:,2].mean()),velocity_RMS_m_s=float(np.sqrt(np.mean(speed*speed))),max_speed_m_s=float(speed.max()),current_mixture_KE_J_per_m=float(.5*np.sum(rho*volume*speed*speed)),current_pressure_storage_quadratic_J_per_m=float(.5*np.sum(n*volume/bundle['kw']*p*p)),max_kappa=float(kap.max()),plastic_soil=int(np.count_nonzero(kap>0)),min_J=float(J.min()),max_J=float(J.max()),min_n=float(n.min()),max_n=float(n.max()),min_rho=float(rho.min()),max_rho=float(rho.max()),min_k_m_s=float(k.min()),max_k_m_s=float(k.max()),front_x_m=float(pos[:,0].max()),runout_from_initial_front_m=float(pos[:,0].max()-initial[:,0].max()),max_height_m=float(pos[:,2].max()),mean_settlement_reference_mm=float(-1000*du[:,2].mean()),material_displacement_RMS_mm=float(1000*np.sqrt(np.mean(np.sum(du*du,axis=1)))),top_material_settlement_mm=float(-1000*du[top,2].mean()),bottom_material_settlement_mm=float(-1000*du[bottom,2].mean()),min_soil_x_m=float(pos[:,0].min()),min_soil_z_m=float(pos[:,2].min()),soil_x_below0=int(np.count_nonzero(pos[:,0]<0)),soil_z_below0=int(np.count_nonzero(pos[:,2]<0)),saved_plane_x_within_4e_minus8=int(np.count_nonzero(pos[:,0]<=4e-8)),saved_plane_z_within_4e_minus8=int(np.count_nonzero(pos[:,2]<=4e-8)),FS23_soil=int(fs.sum()),saved_FS23_positive=int(np.count_nonzero(fs&(p>0))),saved_FS23_negative=int(np.count_nonzero(fs&(p<0))),saved_FS23_zero=int(np.count_nonzero(fs&(p==0))),NN_min_over_dp=None if nn is None else float(nn.min()),NN_q05_over_dp=None if nn is None else float(np.quantile(nn,.05)),NN_median_over_dp=None if nn is None else float(np.median(nn)),NN_q95_over_dp=None if nn is None else float(np.quantile(nn,.95)),NN_sqrtJ_q05=None if nn is None else float(np.quantile(nn/np.sqrt(J),.05)),pairs_r_lt_0p7dp=pairs,saved_f_max_Pa=None if not source else float(bundle['yield_rows'][part]['f_max_Pa']),saved_f_max_ID=None if not source else int(bundle['yield_rows'][part]['f_max_ID']))
  rows.append(row);values=(('p',p,'Pa'),('native_p_minus_fixedP0',ex,'Pa'),('speed',speed,'m/s'),('kappa',kap,'1'),('J',J,'1'),('n',n,'1'),('rho',rho,'kg/m3'),('k',k,'m/s'),('effective_trace',sk.sum(axis=1),'Pa'),('total_trace',total.sum(axis=1),'Pa'),('effective_zz',sk[:,2],'Pa'),('total_zz',total[:,2],'Pa'))
  for name,val,unit in values:
   for kind,at in (('min',int(val.argmin())),('max',int(val.argmax()))):extrema.append(dict(tag=spec['tag'],part=part,time_s=float(times[part]),tau_s=float(tau[part]),field=name,extreme=kind,value=float(val[at]),unit=unit,native_id=int(ids[at]),x_m=float(pos[at,0]),z_m=float(pos[at,2])))
  count=np.bincount(layer_index)
  for li,z in enumerate(zlevels):
   at=layer_index==li;layers.append(dict(tag=spec['tag'],part=part,time_s=float(times[part]),tau_s=float(tau[part]),initial_z_m=float(z),fixed_IDs=int(count[li]),p_mean_Pa=float(p[at].mean()),native_p_minus_fixedP0_mean_Pa=float(ex[at].mean()),effective_zz_mean_Pa=float(sk[at,2].mean()),total_zz_mean_Pa=float(total[at,2].mean()),velocity_RMS_m_s=float(np.sqrt(np.mean(speed[at]**2))),mean_settlement_reference_mm=float(-1000*du[at,2].mean()),mean_J=float(J[at].mean()),max_kappa=float(kap[at].max())))
  for identity in FOCUS:
   at=identity-2060;tracks.append(dict(tag=spec['tag'],part=part,time_s=float(times[part]),tau_s=float(tau[part]),native_id=identity,x_m=float(pos[at,0]),z_m=float(pos[at,2]),dx_reference_m=float(du[at,0]),dz_reference_m=float(du[at,2]),p_Pa=float(p[at]),native_p_minus_fixedP0_Pa=float(ex[at]),speed_m_s=float(speed[at]),J=float(J[at]),n=float(n[at]),k_m_s=float(k[at]),kappa=float(kap[at]),FS_type=int(ft[at]),effective_trace_Pa=float(sk[at].sum()),total_trace_Pa=float(total[at].sum())))
  if part==tail_at:tail_pos=pos.copy()
  if part in selected:snaps[part]=dict(pos=pos.copy(),fixed=x['Posd'][~soil].copy(),p=p.copy(),excess=ex.copy(),kappa=kap.copy(),J=J.copy(),time_s=float(times[part]),tau_s=float(tau[part]))
 move=pos-tail_pos;tail=rows[tail_at:];firsttail,last=tail[0],tail[-1];width=last['time_s']-firsttail['time_s'];changes={key:dict(first=firsttail[key],last=last[key],delta=last[key]-firsttail[key],min=min(q[key] for q in tail),max=max(q[key] for q in tail),endpoint_secant_per_s=(last[key]-firsttail[key])/width if width else None) for key in ('p_mean_Pa','p_RMS_Pa','effective_stress_Frobenius_RMS_Pa','total_stress_Frobenius_RMS_Pa','velocity_RMS_m_s','current_mixture_KE_J_per_m','mean_settlement_reference_mm','min_J','max_J','max_kappa','front_x_m')}
 summary=dict(tag=spec['tag'],runtime_observed=bundle['runtime_observed'],runtime_success_claimed=False,source_partial=bool(bundle['done'].get('partial',False)),actual_samples=bundle['count'],actual_first_time_s=float(times[0]),actual_end_time_s=float(times[-1]),maximum_actual_tau_s=float(tau[-1]),source_certificate_observed=bool(bundle['done'].get('certified_PRE',False)),source_equilibrium_accepted=False,late_interval=dict(requested_duration_s=1. if source or bundle['count']==301 else .3,actual_first_time_s=firsttail['time_s'],actual_last_time_s=last['time_s'],actual_duration_s=width,samples=len(tail),same_material_movement_RMS_mm=float(1000*np.sqrt(np.mean(np.sum(move*move,axis=1)))),maximum_same_material_movement_mm=float(1000*np.linalg.norm(move,axis=1).max()),metrics=changes),first_saved_near_pair=next((q for q in rows if q['pairs_r_lt_0p7dp'] is not None and q['pairs_r_lt_0p7dp']>0),None),end_saved=last,pressure_excess_reference='Native float(p - fixed initial P0); not established as the paper excessive-pressure field',energy_scope='Current mixture KE and pressure-storage quadratics per unit depth; not full u-pl energy or a conservation theorem',arrest_or_winner_selected=False)
 return dict(bundle=bundle,history=rows,extrema=extrema,layers=layers,tracks=tracks,snapshots=snaps,summary=summary)
def history_plot(results,prefix,tail=False):
 fig,axes=plt.subplots(5,3,figsize=(15,16),layout='constrained');charts=(('Absolute p min/max/RMS [kPa]',('p_min_Pa','p_max_Pa','p_RMS_Pa'),.001),('Native p-P0 min/max/RMS [kPa]',('native_p_minus_fixedP0_min_Pa','native_p_minus_fixedP0_max_Pa','native_p_minus_fixedP0_RMS_Pa'),.001),('Effective/total stress RMS [kPa]',('effective_stress_Frobenius_RMS_Pa','total_stress_Frobenius_RMS_Pa'),.001),('Speed RMS/max [m/s]',('velocity_RMS_m_s','max_speed_m_s'),1.),('KE/pressure quadratics [J/m]',('current_mixture_KE_J_per_m','current_pressure_storage_quadratic_J_per_m'),1.),('Maximum kappa',('max_kappa',),1.),('J min/max',('min_J','max_J'),1.),('Porosity min/max',('min_n','max_n'),1.),('Conductivity min/max [m/s]',('min_k_m_s','max_k_m_s'),1.),('Mean/top/bottom settlement [mm]',('mean_settlement_reference_mm','top_material_settlement_mm','bottom_material_settlement_mm'),1.),('Front x / height [m]',('front_x_m','max_height_m'),1.),('NN min/q05/median over dp',('NN_min_over_dp','NN_q05_over_dp','NN_median_over_dp'),1.),('Soil pairs r<.7dp [count]',('pairs_r_lt_0p7dp',),1.),('Minimum x/z [m]',('min_soil_x_m','min_soil_z_m'),1.),('Negative p / positive saved FS23 [count]',('negative_p_soil','saved_FS23_positive'),1.))
 for panel,(title,keys,scale) in enumerate(charts):
  axis=axes.flat[panel]
  for ci,a in enumerate(results):
   rows=[q for q in a['history'] if not tail or q['time_s']>=a['summary']['late_interval']['actual_first_time_s']]
   for ki,key in enumerate(keys):
    if rows[0][key] is not None:axis.plot([q['tau_s'] for q in rows],[q[key]*scale for q in rows],color='C'+str(ci),ls=('-','--',':')[ki],label=a['summary']['tag'] if ki==0 else None)
  axis.set(title=title,xlabel='Actual tau [s]');axis.grid(alpha=.2)
  if axis.get_legend_handles_labels()[0]:axis.legend(fontsize=7)
  if panel in (0,1):axis.set_yscale('symlog',linthresh=1.)
  if panel in (11,12) and all(a['bundle']['source'] for a in results):axis.text(.5,.5,'Not computed for source review',ha='center',transform=axis.transAxes,fontsize=8)
 fig.suptitle(('Actual last review interval; endpoint secants, no fitted trend or equilibrium gate' if tail else 'All actual saves; no half/accuracy or winner claim')+'\nColor=case; solid/dashed/dotted follow the metric order in each panel title');p=Path(str(prefix)+('_tail.png' if tail else '_history.png'));fig.savefig(p,dpi=170);plt.close(fig);return p
def plot_results(results,prefix):
 """Write figures only; callers retain control of output path and any later physical decision."""
 files=[history_plot(results,prefix),history_plot(results,prefix,True)]
 if results[0]['bundle']['source']:
  fig,axes=plt.subplots(2,3,figsize=(14,9),layout='constrained');fields=('p_mean_Pa','effective_zz_mean_Pa','total_zz_mean_Pa','velocity_RMS_m_s','mean_J','mean_settlement_reference_mm')
  for ci,a in enumerate(results):
   start=a['summary']['late_interval']['actual_first_time_s'];times=sorted({q['time_s'] for q in a['layers'] if q['time_s']>=start});chosen=sorted({times[0],times[len(times)//2],times[-1]})
   for ti,time in enumerate(chosen):
    rr=[q for q in a['layers'] if q['time_s']==time]
    for axis,key in zip(axes.flat,fields):axis.plot([q[key] for q in rr],[q['initial_z_m'] for q in rr],color='C'+str(ci),ls=('-','--',':')[ti],label=a['summary']['tag']+f' actual t={time:.9f}');axis.set(xlabel=key,ylabel='Fixed material initial z [m]');axis.grid(alpha=.2)
  for axis in axes.flat:axis.legend(fontsize=6)
  fig.suptitle('Fifty original100-ID material layers; actual first/middle/last saves in the last review interval');p=Path(str(prefix)+'_layers.png');fig.savefig(p,dpi=170);plt.close(fig);files.append(p)
 else:
  groups=[[(a,part,s) for part,s in a['snapshots'].items()] for a in results];columns=[item for group in groups for item in group];need(columns,'At least one actual saved field state required');xmin=min(s['pos'][:,0].min() for _,_,s in columns);xmax=max(s['pos'][:,0].max() for _,_,s in columns);zmin=min(s['pos'][:,2].min() for _,_,s in columns);zmax=max(s['pos'][:,2].max() for _,_,s in columns)
  for si in range(max(len(g) for g in groups)):
   current=[g[si] for g in groups if si<len(g)];fig,axes=plt.subplots(4,len(current),figsize=(4*len(current)+1,13),squeeze=False,layout='constrained')
   for row,(field,title) in enumerate((('p','Native absolute p [kPa]'),('excess','Native p-fixed P0 [kPa], not paper-defined excess'),('kappa','Kappa'),('J','J'))):
    lo=min(float(s[field].min()) for _,_,s in columns);hi=max(float(s[field].max()) for _,_,s in columns);norm=TwoSlopeNorm(vmin=lo,vcenter=0.,vmax=hi) if lo<0<hi else Normalize(vmin=lo,vmax=hi)
    for col,(a,part,s) in enumerate(current):axis=axes[row,col];axis.scatter(s['fixed'][:,0],s['fixed'][:,2],c='.7',s=4);im=axis.scatter(s['pos'][:,0],s['pos'][:,2],c=s[field],norm=norm,cmap='coolwarm' if field in ('p','excess') else 'viridis',s=6,rasterized=True);axis.set(xlim=(xmin-DP,xmax+DP),ylim=(zmin-DP,zmax+DP),xlabel='x [m]',ylabel='z [m]');axis.set_aspect('equal');axis.set_title(a['summary']['tag']+f"\npart{part}, actual tau={s['tau_s']:.9f}s",fontsize=9)
    if lo<hi:
     ticks=sorted(set([lo,hi,0.]+([lo/2.,hi/2.] if lo<0<hi else list(np.linspace(lo,hi,5))))) if lo<=0<=hi else list(np.linspace(lo,hi,5));ticks=[v for v in ticks if lo<=v<=hi];scale=1000. if field in ('p','excess') else 1.;bar=fig.colorbar(im,ax=list(axes[row]),ticks=ticks,label=title);bar.set_ticks(ticks,labels=[format(v/scale,'.4g') for v in ticks]);bar.ax.set_ylim(lo,hi)
    else:axes[row,0].text(.02,.94,title+f' constant={lo:.7g}',transform=axes[row,0].transAxes,fontsize=8)
   fig.suptitle('Raw5000 soil points; all selected states share full min/max, no clipping/smoothing\nZero-centered pressure color halves have different negative/positive scales');p=Path(str(prefix)+f'_fields_{si:02d}.png');fig.savefig(p,dpi=170);plt.close(fig);files.append(p)
 return files
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--execution-authorized',action='store_true');args=p.parse_args();need(args.execution_authorized,'Author-only until root full-read');manifest=read(args.manifest);tag=manifest['tag'];need(re.fullmatch(r'[A-Za-z0-9_]+',tag) is not None,'Safe exclusive output tag required');prefix=T/'figures'/tag;check=T/'logs'/(tag+'.check.json');need(not check.exists() and not list(prefix.parent.glob(tag+'_*')),'Existing complete/partial review protected');consumed=[stat(args.manifest),stat(__file__),stat(T/'notes/c08_h18_compare_r1.md')];result=dict(stage='c08_h18_compare_r1',passed=False,physical_acceptance=False,consumed=consumed)
 try:
  need(manifest['schema']==1 and manifest['mode'] in ('source','receiver') and manifest['cases'],'Explicit source/receiver cases required');bundles=[load_bundle(q,consumed) for q in manifest['cases']];need(len({q['spec']['tag'] for q in bundles})==len(bundles) and all(q['source']==(manifest['mode']=='source') for q in bundles),'Unique tags and one review mode required');reference=None
  if manifest['mode']=='receiver':ref=load_bundle(manifest['source_reference'],consumed);reference=reference_from(ref)
  analyses=[analyze_case(q,reference,manifest.get('snapshots_tau_s')) for q in bundles];files=[]
  for key in ('history','extrema','layers','tracks'):
   rows=[r for a in analyses for r in a[key]];out=Path(str(prefix)+'_'+key+'.csv');write_csv(out,rows);files.append(out)
  matched=[]
  if 'reference_tag' in manifest:
   base=next(a for a in analyses if a['summary']['tag']==manifest['reference_tag']);lookup={(q['completed_step'],q['time_s']):q for q in base['history']}
   for a in analyses:
    if a is base:continue
    for q in a['history']:
     key=(q['completed_step'],q['time_s'])
     if key not in lookup:continue
     b=lookup[key];r=dict(reference_tag=manifest['reference_tag'],tag=q['tag'],completed_step=key[0],time_s=key[1],tau_s=q['tau_s'])
     for name in ('p_RMS_Pa','p_min_Pa','p_max_Pa','velocity_RMS_m_s','current_mixture_KE_J_per_m','max_kappa','min_J','max_J','front_x_m','mean_settlement_reference_mm','top_material_settlement_mm','bottom_material_settlement_mm'):r[name+'_minus_reference']=q[name]-b[name]
     matched.append(r)
   if matched:out=Path(str(prefix)+'_matched.csv');write_csv(out,matched);files.append(out)
  files += plot_results(analyses,prefix);need(all(stat(q['path'])==q for q in consumed),'Consumed input changed');result.update(passed=True,mode=manifest['mode'],original_headers={q['spec']['tag']:[q['nodes'],22,q['count']] for q in bundles},actual_samples={q['spec']['tag']:q['count'] for q in bundles},summaries=[q['summary'] for q in analyses],matched_exact_clock_rows=len(matched),native_excess_is_fixed_P0_difference_not_paper_equivalence=True,source_equilibrium_gate_added=False,winner_selected=False,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,SHA_scans=0,runtime_admission_claimed=False,visual_QA_pending=True,consumed_stats_unchanged=True,files=[stat(q) for q in files])
 except Exception as error:result.update(first_failure=str(error),partial_outputs_preserved=True);raise
 finally:
  with check.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
if __name__=='__main__':main()
