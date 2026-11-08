"""Sealed330-call CPU pressure responses: local finite-h matrices, never a coupled stability verdict."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,csv,json,math,struct
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
T=Path(__file__).resolve().parents[1];TAG='upl_c08_asn4_pressure_review_r1';PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json')
SOURCE=T/'logs/upl_c08_asn4_pressure_cpu_r1.check.json'
FIELDS={'compression':'compression_Pa_s','LP':'LP_Pa_s','defect':'defect_Pa_s','divAce':'divAce_Pa_s','chain':'chain_Pa_s'}
CHANNELS=('actual_full','compression','LP','defect','divAce','chain','LP_plus_defect','full_minus_divAce','shadow5')
LABELS={'actual_full':'Actual full','compression':'Compression','LP':'LP','defect':'Defect','divAce':'divAce','chain':'Chain','LP_plus_defect':'LP + defect','full_minus_divAce':'Full - divAce','shadow5':'Five-term sum'}

def need(x,s):
 if not x:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def bind(e):need(stat(e['path'])==e,'Closed input changed: '+e['path']);return e
def table(p):
 with Path(p).open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def write(leaf,rows):
 need(rows,'Empty derived table');p=Path(str(PREFIX)+'_'+leaf+'.csv')
 with p.open('x',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 return p
def save(p,obj):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(obj,f,indent=2,allow_nan=False);f.write('\n')
def bits(x):return struct.unpack('<I',struct.pack('<f',float(x)))[0]
def norms(a):return dict(Fro=float(np.linalg.norm(a,'fro')),inf=float(np.linalg.norm(a,np.inf)),maxabs=float(np.abs(a).max()))
def relative(delta,a,b,which):
 den=max(float(np.linalg.norm(a,which)),float(np.linalg.norm(b,which)));return float(np.linalg.norm(delta,which))/den if den else (0. if not np.any(delta) else None)

def spectrum(a):
 values,vectors=np.linalg.eig(a);need(np.isfinite(values).all() and np.isfinite(vectors).all(),'Nonfinite finite-h eigensystem');k=max(range(len(values)),key=lambda j:(values[j].real,values[j].imag));v=vectors[:,k];pivot=int(np.argmax(np.abs(v)));v=v*np.exp(-1j*np.angle(v[pivot]))/abs(v[pivot]);den=float(np.vdot(v,v).real)
 symmetric=.5*(a+a.T);off=a[~np.eye(len(a),dtype=bool)];negative=off[off<0];positive=off[off>0]
 residual=float(np.linalg.norm(a@v-values[k]*v));scale=float(np.linalg.norm(a,'fro')*np.linalg.norm(v)+abs(values[k])*np.linalg.norm(v))
 return dict(max_Re_per_s=float(values[k].real),imag_at_max_Re_per_s=float(values[k].imag),min_Re_per_s=float(values.real.min()),max_abs_imag_per_s=float(np.abs(values.imag).max()),Euclidean_symmetric_part_maxeig_per_s=float(np.linalg.eigvalsh(symmetric)[-1]),offdiag_negative_count=len(negative),offdiag_positive_count=len(positive),negative_offdiag_abs_sum_per_s=float(-negative.sum()),positive_offdiag_abs_sum_per_s=float(positive.sum()),min_offdiag_per_s=float(off.min()),max_offdiag_per_s=float(off.max()),min_diagonal_per_s=float(np.diag(a).min()),max_diagonal_per_s=float(np.diag(a).max()),held_patch_constant_response_maxabs_per_s=float(np.abs(a.sum(axis=1)).max()),selected_eigenpair_relative_residual=residual/scale if scale else 0.,**norms(a)),values,v,den

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read before one offline review');need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial review protected')
 proof=read(SOURCE);need(proof['passed'] and proof['consumed_stats_unchanged'] and proof['force_evaluations']==330 and proof['selected_soil_pressure_rows_and_columns']==41 and proof['central_column_h_groups']==164 and proof['actual_physical_steps']==0 and not proof['full_coupled_stability_claimed'] and not proof['physical_acceptance'],'Closed actual330-call component check required')
 before=[stat(Path(__file__)),stat(T/'notes'/(TAG+'.md')),stat(SOURCE),bind(proof['actual_call']),bind(proof['component_completion']),bind(proof['prior_zero_step'])];actual=read(proof['actual_call']['path']);need(actual['actual_Popen_wait_exit']==actual['actual_Win32_exit']==0 and actual['ownership_failure'] is None,'Actual component typed exits differ');done=read(proof['component_completion']['path'])
 need(done['passed'] and done['source_part']==64 and done['source_completed_step']==4260000 and done['actual_ct_calls']==done['actual_Darcy_calls']==330 and done['baseline_calls']==2 and done['central_calls']==328 and done['rate_rows']==13530 and done['FSType_baseline_checks']==1640000 and done['physical_steps']==done['material_return_calls']==0 and done['only_selected_float_pressure_perturbed'] and done['wall_state_C_Ace_rebuilt_each_call'],'Actual frozen response scope differs')
 paths={leaf:bind(next(e for e in proof['files'] if Path(e['path']).name==leaf)) for leaf in ('rates.csv','calls.csv')};before.extend(paths.values());rates=table(paths['rates.csv']['path']);calls=table(paths['calls.csv']['path']);ids=np.asarray(done['selected_native_IDs'],dtype=np.uint32);need(len(ids)==len(set(map(int,ids)))==41 and np.all(ids>=2060) and len(calls)==330 and len(rates)==13530,'Actual41/330/13530 extents differ')
 rows={i:[] for i in range(1,331)}
 for q in rates:need(int(q['evaluation']) in rows,'Unknown response evaluation');rows[int(q['evaluation'])].append(q)
 baselines={};groups={}
 for index,q in enumerate(calls,1):
  exp,h,sign=float(q['AS_exp']),int(q['requested_h_Pa']),int(q['sign']);column=int(q['column_native_id']);need(int(q['evaluation'])==index and exp in (4.,3.) and [int(r['row_native_id']) for r in rows[index]]==ids.tolist() and int(q['FS_baseline_changed'])==0,'Actual call/row order/FS differs')
  if q['kind']=='baseline':need(exp not in baselines and column==-1 and h==sign==0,'Duplicate/invalid baseline');baselines[exp]=index
  else:need(q['kind']=='central' and column in ids and h in (16,32) and sign in (-1,1),'Unplanned column/h/sign');key=(exp,h,column);need(sign not in groups.setdefault(key,{}),'Duplicate finite difference sign');groups[key][sign]=q
 need(set(baselines)=={4.,3.} and len(groups)==164 and all(set(g)=={-1,1} for g in groups.values()),'Complete central pairs required; no omitted columns')
 prior=read(proof['prior_zero_step']['path']);need(prior['passed'] and prior['consumed_stats_unchanged'],'Passed retained r2 zero-step required');ref=bind(next(e for e in prior['files'] if Path(e['path']).name=='receivers.csv'));before.append(ref);reference=table(ref['path']);baseline_comparison={}
 for exp in (4.,3.):
  rr=[q for q in reference if int(q['part'])==64 and float(q['AS_exp'])==exp];need([int(q['native_id']) for q in rr]==ids.tolist(),'Retained part64 baseline ID order differs');comparison=[]
  for current,old in zip(rows[baselines[exp]],rr):
   a,b=float(current['actual_rate_Pa_s']),float(old['actual_rate_Pa_s']);comparison.append(dict(native_ID=int(current['row_native_id']),current_rate_Pa_s=a,retained_r2_rate_Pa_s=b,floatbits_equal=bits(a)==bits(b),difference_Pa_s=a-b))
  baseline_comparison[str(int(exp))]=dict(floatbits_equal_rows=sum(q['floatbits_equal'] for q in comparison),rows=41,maxabs_difference_Pa_s=max(abs(q['difference_Pa_s']) for q in comparison),details=comparison,comparison_is_descriptive_not_a_new_physical_gate=True)
 matrices={};matrix_rows=[];eigen_rows=[];mode_rows=[];case_summary=[];fd_comparison=[];spectra={};modes={};rayleighs={}
 for exp in (4.,3.):
  base=rows[baselines[exp]];xz=np.asarray([[float(q['x']),float(q['z'])] for q in base]);fs=np.asarray([int(q['actual_FS']) for q in base])
  for h in (16,32):
   field_matrices={k:np.empty((41,41)) for k in ('actual_full',*FIELDS)};logged=np.empty((41,41));budgets=np.empty((41,41));denominators=[]
   for col,identity in enumerate(map(int,ids)):
    pair=groups[(exp,h,identity)];plus,minus=pair[1],pair[-1];den=float(plus['actual_column_p_Pa'])-float(minus['actual_column_p_Pa']);need(math.isfinite(den) and den>0 and float(plus['actual_column_delta_Pa'])>0 and float(minus['actual_column_delta_Pa'])<0,'Actual float pressure denominator invalid');denominators.append(den);rp,rm=rows[int(plus['evaluation'])],rows[int(minus['evaluation'])]
    for row,(p,m) in enumerate(zip(rp,rm)):
     need(int(p['actual_FS'])==int(m['actual_FS'])==int(fs[row]),'FSType differs from actual exponent baseline');field_matrices['actual_full'][row,col]=(float(p['actual_rate_Pa_s'])-float(m['actual_rate_Pa_s']))/den
     for key,field in FIELDS.items():field_matrices[key][row,col]=(float(p[field])-float(m[field]))/den
     logged[row,col]=(float(p['shadow_sum_Pa_s'])-float(m['shadow_sum_Pa_s']))/den;budgets[row,col]=(float(p['shadow_budget_Pa_s'])+float(m['shadow_budget_Pa_s']))/den
   a=field_matrices; a['LP_plus_defect']=a['LP']+a['defect'];a['full_minus_divAce']=a['actual_full']-a['divAce'];a['shadow5']=sum((a[key] for key in FIELDS),np.zeros((41,41)));need(all(np.isfinite(x).all() for x in a.values()) and np.isfinite(logged).all() and np.all(budgets>0),'Nonfinite matrix or arithmetic budget')
   matrices[(exp,h)]=a;fullstats,fullvalues,v,vnorm=spectrum(a['actual_full']);spectra[(exp,h)]={};modes[(exp,h)]=(xz,fs,v);rayleigh={key:float(np.real(np.vdot(v,a[key]@v)/vnorm)) for key in CHANNELS};residual=a['actual_full']-a['shadow5'];rayleigh['arithmetic_sum_residual']=float(np.real(np.vdot(v,residual@v)/vnorm));rayleighs[(exp,h)]=rayleigh
   for key in CHANNELS:
    stats,values,unused,unusednorm=spectrum(a[key]);spectra[(exp,h)][key]=values;case_summary.append(dict(AS_exp=exp,h_Pa=h,channel=key,**stats,Rayleigh_on_same_actual_full_leading_mode_per_s=rayleigh[key]))
    for j,value in enumerate(sorted(values,key=lambda z:(-z.real,-z.imag))):eigen_rows.append(dict(AS_exp=exp,h_Pa=h,channel=key,index_descending_Re=j,real_per_s=float(value.real),imag_per_s=float(value.imag)))
   modal={key:np.real(np.conj(v)*(a[key]@v))/vnorm for key in FIELDS};modal['arithmetic_sum_residual']=np.real(np.conj(v)*(residual@v))/vnorm
   for row,identity in enumerate(map(int,ids)):
    q=dict(AS_exp=exp,h_Pa=h,native_ID=identity,x_m=float(xz[row,0]),z_m=float(xz[row,1]),baseline_CPU_FS=int(fs[row]),baseline_p_Pa=float(base[row]['p_Pa']),mode_real=float(v[row].real),mode_imag=float(v[row].imag),mode_abs=float(abs(v[row])),leading_lambda_real_per_s=fullstats['max_Re_per_s'],leading_lambda_imag_per_s=fullstats['imag_at_max_Re_per_s']);q.update({key+'_modal_Rayleigh_node_per_s':float(value[row]) for key,value in modal.items()});mode_rows.append(q)
    for col,column in enumerate(map(int,ids)):
     q=dict(AS_exp=exp,h_Pa=h,row_native_ID=identity,column_native_ID=column,actual_float_central_denominator_Pa=denominators[col]);q.update({key+'_per_s':float(a[key][row,col]) for key in CHANNELS});q.update(logged_shadow_sum_FD_per_s=float(logged[row,col]),sum5_minus_logged_shadow_FD_per_s=float(a['shadow5'][row,col]-logged[row,col]),actual_full_minus_shadow5_per_s=float(residual[row,col]),propagated_rate_sum_arithmetic_budget_per_s=float(budgets[row,col]));matrix_rows.append(q)
   case_summary.append(dict(AS_exp=exp,h_Pa=h,channel='arithmetic_closure_only',actual_minus_shadow5_norms=norms(residual),sum5_minus_logged_shadow_norms=norms(a['shadow5']-logged),max_logged_shadow_FD_arithmetic_budget_fraction=float(np.max(np.abs(a['actual_full']-logged)/budgets)),Rayleigh_shadow5_plus_residual_minus_full_per_s=rayleigh['shadow5']+rayleigh['arithmetic_sum_residual']-rayleigh['actual_full'],compression_FD_norms=norms(a['compression'])))
  for key in CHANNELS:
   a,b=matrices[(exp,16)][key],matrices[(exp,32)][key];delta=a-b;where=np.unravel_index(int(np.argmax(np.abs(delta))),delta.shape);fd_comparison.append(dict(AS_exp=exp,channel=key,difference_h16_minus_h32=norms(delta),relative_Fro_difference=relative(delta,a,b,'fro'),relative_inf_difference=relative(delta,a,b,np.inf),maxabs_difference_row_ID=int(ids[where[0]]) if np.any(delta) else None,maxabs_difference_column_ID=int(ids[where[1]]) if np.any(delta) else None,finite_h_agreement_is_descriptive_no_acceptance_threshold=True))
 files=[write('matrices',matrix_rows),write('eigenvalues',eigen_rows),write('modes',mode_rows)]
 fig,axes=plt.subplots(2,2,figsize=(13,8),constrained_layout=True)
 for row,exp in enumerate((4.,3.)):
  ax=axes[row,0]
  for key,color in (('actual_full','C0'),('LP_plus_defect','C1'),('full_minus_divAce','C2')):
   for h,marker in ((16,'o'),(32,'x')):
    values=spectra[(exp,h)][key];ax.scatter(values.real,values.imag,s=18,marker=marker,color=color,alpha=.65,label=LABELS[key]+' h'+str(h))
  ax.axvline(0,color='k',lw=.7);ax.axhline(0,color='k',lw=.5);ax.set_xscale('symlog',linthresh=1.);ax.set_yscale('symlog',linthresh=1.);ax.set(title='AS exponent '+str(int(exp))+'; local finite-h eigenvalues',xlabel='Re(lambda) [1/s], signed symlog',ylabel='Im(lambda) [1/s], signed symlog');ax.legend(fontsize=6);ax.grid(alpha=.25)
  ax=axes[row,1]
  for h,marker in ((16,'o'),(32,'x')):
   values=[next(q['max_Re_per_s'] for q in case_summary if q['AS_exp']==exp and q['h_Pa']==h and q['channel']==key) for key in CHANNELS];ax.plot(range(len(CHANNELS)),values,marker=marker,lw=.7,label='h'+str(h)+' Pa')
  ax.axhline(0,color='k',lw=.7);ax.set_yscale('symlog',linthresh=1.);ax.set_xticks(range(len(CHANNELS)),[LABELS[k] for k in CHANNELS],rotation=35,ha='right',fontsize=7);ax.set(title='Largest real eigenvalue by named matrix',ylabel='max Re(lambda) [1/s], signed symlog');ax.legend(fontsize=7);ax.grid(alpha=.25)
 fig.suptitle('41-pressure local conditional matrices; outside soil pressure held; walls rebuilt. Not full coupled stability.');path=Path(str(PREFIX)+'_spectrum.png');fig.savefig(path,dpi=170);plt.close(fig);files.append(path)
 fig,axes=plt.subplots(2,3,figsize=(15,8),constrained_layout=True)
 for row,exp in enumerate((4.,3.)):
  xz,fs,v=modes[(exp,32)]
  for col,values,label in ((0,v.real,'real'),(1,v.imag,'imaginary')):
   ax=axes[row,col];sc=ax.scatter(xz[:,0],xz[:,1],c=values,s=20+40*np.abs(v),cmap='coolwarm',vmin=-1,vmax=1);mask=np.isin(fs,(2,3));ax.scatter(xz[mask,0],xz[mask,1],s=70,facecolors='none',edgecolors='k',linewidths=.7,label='CPU baseline FS2/3');ax.set(title='AS'+str(int(exp))+' h32 leading mode: '+label,xlabel='Native x [m]',ylabel='Native z [m]',aspect='equal');ax.grid(alpha=.2);ax.legend(fontsize=6);fig.colorbar(sc,ax=ax,label='Mode component, max|v|=1',shrink=.75)
  ax=axes[row,2];keys=(*FIELDS,'arithmetic_sum_residual')
  for h,marker in ((16,'o'),(32,'x')):
   r=rayleighs[(exp,h)];ax.plot(range(len(keys)),[r[k] for k in keys],marker=marker,lw=.7,label='Own full leading mode, h'+str(h));ax.axhline(r['actual_full'],lw=.7,ls='--' if h==16 else ':',label='Re(lambda), h'+str(h))
  ax.axhline(0,color='k',lw=.7);ax.set_yscale('symlog',linthresh=1.);ax.set_xticks(range(len(keys)),['Compression','LP','Defect','divAce','Chain','Arithmetic\nresidual'],rotation=30,ha='right',fontsize=7);ax.set(title='Same-mode real Rayleigh values; additive, not causal fractions',ylabel='Re(v* A_channel v / v* v) [1/s]');ax.legend(fontsize=6);ax.grid(alpha=.25)
 fig.suptitle('Actual-full right mode per case. h32 spatial points only; no interpolation. Five terms + residual close full.');path=Path(str(PREFIX)+'_modes.png');fig.savefig(path,dpi=170);plt.close(fig);files.append(path)
 summary=dict(stage=TAG,analysis_completed=True,scope='part64 .65s,41 soil-pressure rows/columns; full wall/force/Darcy CPU evaluations; local conditional FD only',AS_exponents=[4,3],finite_h_Pa=[16,32],actual_float_denominators=True,all41_columns_retained=True,baseline_r2_comparison=baseline_comparison,matrices=case_summary,finite_h_comparison=fd_comparison,channel_definitions=dict(compression='-(Kw/n)*theta; pressure FD reported, not forced zero',LP='actual ki/gamma LP term',defect='FS2/3 contains rho_w*A_i dot Lx; otherwise -Gp dot Lx',divAce='actual complete divergence of finished solid Ace',chain='combined gradJ dot(Gp+rho_w Ace), not static-only',LP_plus_defect='sum of named terms; FS rows can contain Ace',full_minus_divAce='actual full minus divAce only; still has Ace via chain/FS defect',shadow5='sum of five shadow FD matrices; actual-full residual includes arithmetic/float-rate effects'),symmetric_part='(A+A.T)/2, Euclidean local pressure norm; not full mechanical/pressure energy',same_mode_Rayleigh='Re(v.conj().T A_channel v)/(v.conj().T v), using actual-full leading right mode for that AS,h; overlapping composites are not additive causal fractions',outside_soil_pressure_perturbations_held_zero=True,wall_states_rebuilt_not_independent_fixed_unknowns=True,FSclassification_frozen_verified_upstream=True,CompletedOnly_ponding_projection_not_linearized=True,geometry_J_velocity_sigma_kappa_frozen=True,full_coupled_spectrum_claimed=False,original_GPU_or_failed_stage_replay=False,finite_h_convergence_acceptance_threshold=None,physical_acceptance=False,no_eigenvalue_difference_causal_apportionment=True,plot_symlog_linthresh_per_s=1.,plot_visual_QA_pending=True,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0)
 path=Path(str(PREFIX)+'_summary.json');save(path,summary);files.append(path);need(all(stat(e['path'])==e for e in before),'Sealed consumed input changed');save(CHECK,dict(stage=TAG,passed=True,analysis_completed=True,source_component_check=stat(SOURCE),component_calls=330,pressure_unknowns=41,matrix_entries=len(matrix_rows),eigenvalue_rows=len(eigen_rows),mode_rows=len(mode_rows),physical_acceptance=False,full_coupled_stability_claimed=False,visual_QA_pending=True,consumed=before,consumed_stats_unchanged=True,files=[stat(p) for p in files],solver_invocations=0,decoder_invocations=0,SHA_scans=0));print('FROZEN_PRESSURE_REVIEW_READY',CHECK,flush=True)

if __name__=='__main__':main()
