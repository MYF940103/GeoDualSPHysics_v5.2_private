"""Matched saved early AS controls: fixed7011/7012 pair, no new solver or tensile-cause verdict."""
import argparse,csv,json,struct
from pathlib import Path
import upl_c08_pair_mechanism_r1 as pair
import upl_c08_asn4_partial_compare_r1 as n4
np,c,plt,native=pair.np,pair.c,pair.plt,pair.native
T=c.T;TAG='upl_c08_early_as_compare_r1';PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json');PARTS=(14,29,59);COMMON=66;DP=.04;FOCUS=(7011,7012);F=np.float32
def write(leaf,rows):
 path=Path(str(PREFIX)+'_'+leaf+'.csv')
 with path.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 return path
def sources(before):
 ap=T/'logs/upl_c08_as05_compare_r1.check.json';ac=c.read(ap);c.need(ac['passed'] and ac['actual_matched_samples']==66 and ac['clock_and_steps_exact'] and ac['P0_bits_equal'],'Retained epsilon-control comparison required');before.append(c.stat(ap));g3=native.load(native.SPECS[0],before);g3.update(dtype=g3['frames'].dtype,history=c.table(g3['native']/'history.csv'));r3=c.read(T/'logs'/native.SPECS[0][1]);before.append(native.entry(r3['outputs'],g3['native']/'history.csv'));reference=n4.full.load(n4.full.SPECS[1]);g4=n4.load_n4(reference);g5=c.load(c.SPECS[1]);g2=c.load(c.SPECS[0]);before.extend(reference['before'])
 groups=(g3,g4,g5,g2);specs=(('eps0p2_n3','upl_c08_causal_window_GPU_r1.native_r1.json',.2,3.,90),('eps0p2_n4_failed_prefix','upl_c08_asn4_window_GPU_r1.native_partial_r1.json',.2,4.,66),('eps0p5_n2p55','upl_c08_as05_window_GPU_r2.native_r1.json',.5,2.55,66),('eps0p2_n2p55','upl_c08_stage_trace_window_GPU_r1.native_r1.json',.2,2.55,66))
 for g,(label,leaf,epsilon,exponent,count) in zip(groups,specs):
  if 'before' in g:before.extend(g['before'])
  rp=T/'logs'/leaf;r=c.read(rp);me=c.bind(r['metadata']);m=c.read(me['path']);before.extend((c.stat(rp),me));c.need(r['passed'] and r['consumed_stats_unchanged'] and g['done']['samples']==count and m['passed'] and m['samples']==count and m['AS_policy']=='ReleaseOnly' and m['AS_coefficient_float_reference']==float(F(epsilon)) and m['AS_exponent_float_reference']==float(F(exponent)),'Actual per-group native AS metadata differs');g.update(label=label,epsilon=epsilon,exponent=exponent,eps_actual=m['AS_coefficient_float_reference'],exp_actual=m['AS_exponent_float_reference'],count=count)
 c.need(g5['native'].resolve()==Path(ac['native_directories']['epsilon0p5']).resolve() and g2['native'].resolve()==Path(ac['native_directories']['epsilon0p2']).resolve(),'Use actual AS05 r2 receipt/r1 output and retained epsilon baseline paths');c.need(all(g['run']['source_pre_file']==g3['run']['source_pre_file'] and native.bits(g['done']['source_actual_time_s'])==native.bits(g3['done']['source_actual_time_s']) and g['dtype']==g3['dtype'] for g in groups),'Same actual PRE/source clock/literal22 layout required')
 signatures=[]
 from upl_c08_shepard_jobs_r1 import signature
 for g in groups:
  root=c.ET.parse(g['run']['input_xml']['path']).getroot();params={q.get('key'):q for q in root.findall('execution/parameters/parameter')};c.need(float(params['ArtificialStressCoef'].get('value'))==g['epsilon'] and float(params['ArtificialStressExp'].get('value'))==g['exponent'],'Actual XML AS parameters differ')
  for key in ('ArtificialStressCoef','ArtificialStressExp','TimeMax','TimeOut'):params[key].set('value','DECLARED_AS_OR_WINDOW')
  signatures.append(tuple(signature(root.find('execution/'+k)) for k in ('special','parameters')))
 c.need(all(s==signatures[0] for s in signatures),'Only declared AS/window controls may differ in XML; observer programs are independently bound');return groups
def fixed_pair(a,g,part,time,tau,step):
 slots=np.searchsorted(a['Idp'][:,0],FOCUS);c.need(np.array_equal(a['Idp'][slots,0],FOCUS),'Fixed7011/7012 identities missing');x=a['Posd'][slots];v=a['Vel'][slots].astype(float);p=a['PorePress'][slots,0].astype(float);eff=pair.tensor(a,slots);total=eff.copy();total[:,range(3),range(3)]-=p[:,None];eigen=np.linalg.eigvalsh(total);ASinput=total.astype('f4').astype('f8');ev,Q=np.linalg.eigh(ASinput);positive=(Q*np.maximum(ev,0)[:,None,:])@Q.transpose(0,2,1);Ras=(-g['eps_actual']*positive).astype('f4').astype('f8');dr=x[0]-x[1];distance=float(np.linalg.norm(dr));c.need(distance>0,'Fixed pair line-of-centers undefined');normal=dr/distance;tangent=np.array([-normal[2],0.,normal[0]]);dv=v[0]-v[1];active=distance<pair.R
 if active:
  drf=dr.astype('f4');rr2=F(F(drf[0]*drf[0])+F(drf[2]*drf[2]));wab,fac=pair.kernel(rr2);wdp,_=pair.kernel(F(F(DP)*F(DP)));ratio=F(wab*F(F(1)/wdp));power=float(F(np.power(ratio,F(g['exp_actual']))));grad=(F(fac)*drf).astype('f4').astype('f8')
 else:wab=fac=ratio=power=0.;grad=np.zeros(3)
 effective_raw=eff[0].astype('f4').astype('f8')+eff[1].astype('f4').astype('f8');raw=effective_raw.copy();raw[range(3),range(3)]-=p.sum();as_tensor=power*(Ras[0]+Ras[1]);V=a['PoroCurrentVolume'][slots,0];rho=a['PoroMixtureDensity'][slots,0];ci=float(V[1]/rho[0]);cj=float(V[0]/rho[1]);eraw=float(normal@effective_raw@normal);pnormal=-float(p.sum());qraw=float(normal@raw@normal);qas=float(normal@as_tensor@normal);araw=float(normal@(raw@grad));aas=float(normal@(as_tensor@grad));row=dict(group=g['label'],epsilon_nominal=g['epsilon'],exponent_nominal=g['exponent'],epsilon_float=g['eps_actual'],exponent_float=g['exp_actual'],part=part,time_s=time,tau_s=tau,completed_step=step,id_i=7011,id_j=7012,r_m=distance,r_over_dp=distance/DP,within_kernel_support=active,nx=float(normal[0]),nz=float(normal[2]),relative_vx_m_s=float(dv[0]),relative_vz_m_s=float(dv[2]),relative_normal_v_m_s=float(dv@normal),relative_tangent_v_m_s=float(dv@tangent),relative_tangent_speed_m_s=float(np.linalg.norm(dv-(dv@normal)*normal)),raw_effective_normal_Pa=eraw,pressure_normal_minus_pi_pj_Pa=pnormal,raw_total_normal_Pa=qraw,native_double_total_normal_Pa=float(normal@(total[0]+total[1])@normal),AS_normal_proxy_Pa=qas,net_normal_proxy_Pa=qraw+qas,raw_decomposition_roundoff_Pa=qraw-eraw-pnormal,kernel_W_float=float(wab),kernel_fac_float=float(fac),kernel_ratio_float=float(ratio),kernel_power_float=power,epsilon_in_R_once=g['eps_actual'],Vj_over_rhoi=ci,Vi_over_rhoj=cj,raw_relative_radial_accel_proxy_m_s2=(ci+cj)*araw,AS_relative_radial_accel_proxy_m_s2=(ci+cj)*aas,net_relative_radial_accel_proxy_m_s2=(ci+cj)*(araw+aas))
 for suffix,i in (('i',0),('j',1)):
  norm=float(np.abs(eigen[i]).sum());row.update({key+'_'+suffix:value for key,value in dict(x_m=float(x[i,0]),z_m=float(x[i,2]),vx_m_s=float(v[i,0]),vz_m_s=float(v[i,2]),p_Pa=float(p[i]),P0_Pa=float(a['PorePress0'][slots[i],0]),p_minus_fixed_P0_Pa=float(p[i]-a['PorePress0'][slots[i],0]),FS=int(a['FSType'][slots[i],0]),kappa=float(a['Kplastic'][slots[i],0]),J=float(a['PoroVolumeRatio'][slots[i],0]),principal_min_Pa=float(eigen[i,0]),principal_max_Pa=float(eigen[i,2]),positive_spectral_fraction=float(np.maximum(eigen[i],0).sum()/norm) if norm else 0.,AS_positive_rank=int(np.count_nonzero(ev[i]>0))).items()})
 return row
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();c.need(args.execution_authorized,'Root full-read before one offline early comparison');c.need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial products protected');before=[c.stat(p) for p in (Path(__file__),T/'notes'/(TAG+'.md'),Path(pair.__file__),Path(native.__file__),Path(n4.__file__),Path(n4.full.__file__),Path(pair.cluster.__file__),Path(c.__file__),T/'support/upl_c08_fsmask_r1.py',T/'support/upl_c08_shepard_jobs_r1.py')];groups=sources(before);history=[];fixed=[];morph=[];pictures={};summaries=[];times=[];P0=None
 for gi,g in enumerate(groups):
  first_any=first_fixed=None;scalar=float(g['done']['source_actual_time_s'])
  with (g['native']/'typed22.bin').open('rb') as stream:
   c.need(stream.read(12)==struct.pack('<III',6805,22,g['count']),'Keep each original90/66 native header unchanged')
   for part in range(COMMON):
    raw=stream.read(g['dtype'].itemsize);c.need(len(raw)==g['dtype'].itemsize,'Short original common saved record');a=np.frombuffer(raw,dtype=g['dtype'],count=1)[0];time,tau,step=c.inspect(a,g,part)
    for _ in range(4000):scalar+=.0000025
    c.need(native.bits(time)==native.bits(scalar),'Actual scalar clock differs')
    if gi==0:times.append((time,step))
    else:c.need(native.bits(time)==native.bits(times[part][0]) and step==times[part][1],'Compare exact common actual saved clocks/steps, no interpolation')
    p0=a['PorePress0'].view('<u4');P0=p0.copy() if P0 is None else P0;c.need(np.array_equal(p0,P0),'All original fixed-material P0 bits must match across groups/saves');slots,ids,x,nn,near,pairs=pair.geometry(a);i=int(np.argmin(nn));q=fixed_pair(a,g,part,time,tau,step);fixed.append(q);row=dict(group=g['label'],epsilon_nominal=g['epsilon'],exponent_nominal=g['exponent'],part=part,time_s=time,tau_s=tau,completed_step=step,min_rNN_over_dp=float(nn.min()),median_rNN_over_dp=float(np.median(nn)),unique_pairs_lt0p7dp=len(pairs),nearest_native_id=int(ids[i]),nearest_other_native_id=int(ids[near[i]]),fixed7011_7012_r_over_dp=q['r_over_dp']);history.append(row)
    if first_any is None and len(pairs):first_any=dict(row)
    if first_fixed is None and q['r_over_dp']<.7:first_fixed=dict(q)
    if part in PARTS:
     pictures[(g['label'],part)]=dict(x=x.copy(),fixed=a['Posd'][a['Idp'][:,0]<2060][:,[0,2]].copy(),nn=nn.copy(),pairs=pairs.copy(),tau=tau)
     for k,identity in enumerate(ids):morph.append(dict(group=g['label'],part=part,time_s=time,tau_s=tau,completed_step=step,native_ID=int(identity),x_m=float(x[k,0]),z_m=float(x[k,1]),rNN_over_dp=float(nn[k]),p_Pa=float(a['PorePress'][slots[k],0]),kappa=float(a['Kplastic'][slots[k],0]),J=float(a['PoroVolumeRatio'][slots[k],0]),FSType=int(a['FSType'][slots[k],0])))
    if (part+1)%22==0:print('EARLY_AS_PREFIX',g['label'],part+1,flush=True)
   c.need(stream.tell()==12+COMMON*g['dtype'].itemsize and (g['count']!=66 or stream.read(1)==b''),'Exact66 prefix required; n3 retains24 unconsumed records')
  summaries.append(dict(group=g['label'],epsilon_nominal=g['epsilon'],exponent_nominal=g['exponent'],original_native_samples=g['count'],source_solver_passed=g['run']['passed'],source_solver_exit=g['run']['actual_exit'],source_native_last_completed_step=g['done']['completed_steps'],compared_samples=66,first_saved_any_close_pair=first_any,first_saved_fixed7011_7012_close_pair=first_fixed,first_saved_observation_not_continuous_onset=True))
 c.need(len(history)==len(fixed)==264 and len(morph)==60000,'Four groups66 common records and3x5000 morphology accounting differs');files=[write('spacing_history',history),write('fixed7011_7012',fixed),write('morphology',morph)];fig,axes=plt.subplots(3,3,figsize=(16,11),layout='constrained')
 for gi,g in enumerate(groups):
  label=g['label'];hh=[q for q in history if q['group']==label and q['part']<30];qq=[q for q in fixed if q['group']==label];early=[q for q in qq if q['part']<30];color='C'+str(gi)
  for ax,key in ((axes[0,0],'min_rNN_over_dp'),(axes[0,1],'unique_pairs_lt0p7dp')):ax.plot([q['tau_s'] for q in hh],[q[key] for q in hh],c=color,label=label)
  axes[0,2].plot([q['tau_s'] for q in early],[q['r_over_dp'] for q in early],c=color,label=label)
  for key,style in (('raw_effective_normal_Pa','--'),('pressure_normal_minus_pi_pj_Pa',':'),('net_normal_proxy_Pa','-')):axes[1,0].plot([q['tau_s'] for q in early],[q[key] for q in early],style,c=color,label=label+' '+key)
  for key,style in (('relative_normal_v_m_s','-'),('relative_tangent_v_m_s','--')):axes[1,1].plot([q['tau_s'] for q in early],[q[key] for q in early],style,c=color,label=label+' '+key)
  axes[1,2].plot([q['tau_s'] for q in early],[q['net_relative_radial_accel_proxy_m_s2'] for q in early],c=color,label=label)
  for ax,key,scale in ((axes[2,0],'p_Pa',.001),(axes[2,1],'kappa',1.),(axes[2,2],'J',1.)):
   for suffix,style in (('i','-'),('j','--')):ax.plot([q['tau_s'] for q in qq],[q[key+'_'+suffix]*scale for q in qq],style,c=color,label=label+' '+('7011' if suffix=='i' else '7012'))
 for ax,title in zip(axes.ravel(),('All-soil spacing: first.30s','Unique soil pairs r<.7dp: first.30s','Fixed7011/7012 separation / dp','Fixed-pair stress decomposition [Pa]','Relative normal/tangent v [m/s]','Fixed-pair radial acceleration proxy [m/s2]','Absolute p, common66 saves [kPa]','Plastic history, common66 saves','J, common66 saves')):ax.set(title=title,xlabel='Actual saved tau [s]');ax.grid(alpha=.2);ax.legend(fontsize=4.5)
 for ax in (axes[0,0],axes[0,2]):ax.axhline(.7,c='k',ls=':',lw=.6)
 for ax in (axes[1,0],axes[1,2],axes[2,0]):ax.set_yscale('symlog',linthresh=1.)
 fig.suptitle('Early AS controls: fixed material pair; saved-state proxies, no tensile-cause or repair verdict');png=Path(str(PREFIX)+'_early.png');fig.savefig(png,dpi=170);plt.close(fig);files.append(png)
 fig,axes=plt.subplots(3,4,figsize=(18,13),sharex=True,sharey=True,layout='constrained');allx=np.concatenate([q['x'] for q in pictures.values()]);limits=(float(allx[:,0].min()-.08),float(allx[:,0].max()+.08),float(allx[:,1].min()-.08),float(allx[:,1].max()+.08));norm=plt.Normalize(min(q['nn'].min() for q in pictures.values()),max(q['nn'].max() for q in pictures.values()),clip=False)
 from matplotlib.collections import LineCollection
 for row,part in enumerate(PARTS):
  for col,g in enumerate(groups):
   q=pictures[(g['label'],part)];ax=axes[row,col];ax.scatter(q['fixed'][:,0],q['fixed'][:,1],s=1,c='.7');sc=ax.scatter(q['x'][:,0],q['x'][:,1],c=q['nn'],norm=norm,s=3,cmap='viridis');ax.add_collection(LineCollection(q['x'][q['pairs']],colors='red',linewidths=.4));ax.scatter(q['x'][np.array(FOCUS)-2060,0],q['x'][np.array(FOCUS)-2060,1],s=35,facecolors='none',edgecolors='black',lw=.8);ax.set(xlim=limits[:2],ylim=limits[2:],aspect='equal',title=g['label']+' actual tau %.9f'%q['tau'],xlabel='x [m]',ylabel='z [m]')
 fig.colorbar(sc,ax=axes.ravel().tolist(),label='Nearest other soil / dp; common full raw range',shrink=.7);fig.suptitle('Actual matched .15/.3/.6 saves; red r<.7dp links, circles fixed7011/7012; n4 is a failed saved prefix');png=Path(str(PREFIX)+'_morphology.png');fig.savefig(png,dpi=160);plt.close(fig);files.append(png);c.need(all(c.stat(e['path'])==e for e in before),'Closed input/helper changed');result=dict(stage=TAG,passed=True,analysis_completed=True,groups=summaries,actual_matched_samples=66,early_spacing_samples_per_group=30,fixed_material_pair=list(FOCUS),morphology_parts=list(PARTS),native_payload_passes_per_group=1,n3_original90_header_preserved=True,n3_unconsumed_tail_records=24,n4_runtime_remains_failed=True,n4_original_planned_samples=90,n4_last_saved_completed_step=4264000,n4_failure_reported_step=4265004,n4_unsaved_failure_time_reconstructed=False,all22_finite_ID_and_shared_actual_clock_P0_checks=True,group_AS_parameters_from_actual_native_metadata=True,group_selected_nearest_pairs_are_not_material_controls=True,AS_epsilon_in_R_once=True,double_spectral_float_formula_pair_proxy_not_GPU_replay=True,proxy_excludes_other_neighbors_AV_gravity_and_walls=True,no_new_PRE_ring_fit=True,physical_acceptance=False,tensile_cause_claimed=False,repair_selected=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed=before,consumed_stats_unchanged=True,files=[c.stat(p) for p in files])
 with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
 print('EARLY_AS_COMPARE_READY',CHECK,flush=True)
if __name__=='__main__':main()
