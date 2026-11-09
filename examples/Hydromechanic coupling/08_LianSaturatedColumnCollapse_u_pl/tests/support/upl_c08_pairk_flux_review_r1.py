"""Offline interpretation of sealed3-call hydraulic pair-k shadows; no raw/native/force run."""
import argparse,csv,json,math
from collections import defaultdict
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mdbc_partition_components_r3 as e
T=Path(__file__).resolve().parents[1];TAG='upl_c08_pairk_flux_review_r1';SOURCE='upl_c08_pairk_flux_cpu_r1';F=T/'figures';OUT=T/'outputs'/SOURCE;PARTS=(13,14,29);FOCUS=(7011,7012,6230,6231)
GROUPS=('FS0_halo_free','FS0_halo_near','FS23','FS1_other');COLORS=('#2166ac','#67a9cf','#d95f02','#666666')
def table(p):
 with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(p,rows):
 e.need(rows,'Empty derived table')
 with p.open('x',encoding='utf8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def cohort(q):
 fs=int(q['actual_FS']);return ('FS0_halo_free' if q['halo_free_FS_fixed_2R']=='1' else 'FS0_halo_near') if fs==0 else 'FS23' if fs in (2,3) else 'FS1_other'
def stats(values):
 a=np.asarray(values,dtype=float);e.need(len(a)>0 and np.isfinite(a).all(),'Empty/nonfinite derived sample');return dict(n=len(a),RMS=float(np.sqrt(np.mean(a*a))),maxabs=float(np.max(np.abs(a))),mean=float(np.mean(a)))

def plot_actual(rows,path):
 fig,axes=plt.subplots(3,3,figsize=(15,12),layout='constrained');channels=('current_compression_Pa_s','current_LP_Pa_s','current_defect_Pa_s','current_divAce_Pa_s','current_chain_Pa_s','pair_minus_current_Pa_s');labels=('compression','LP','defect','divAce','chain','pair-current')
 for col,part in enumerate(PARTS):
  r=[q for q in rows if int(q['part'])==part];tau=float(r[0]['tau_s']);ax=axes[0,col];allv=[float(q[k])/1000 for q in r for k in ('current_rate_Pa_s','pair_rate_Pa_s')];lo,hi=min(allv),max(allv);ax.plot([lo,hi],[lo,hi],color='black',lw=.7,label='equal')
  for group,color in zip(GROUPS,COLORS):
   a=[q for q in r if q['cohort']==group]
   if a:ax.scatter([float(q['current_rate_Pa_s'])/1000 for q in a],[float(q['pair_rate_Pa_s'])/1000 for q in a],s=24,color=color,label=group)
  ax.set(title=f'Actual frozen tau={tau:.2f}s, n={len(r)}',xlabel='Current rate [kPa/s]',ylabel='PairFlux shadow [kPa/s]');ax.ticklabel_format(style='sci',axis='both',scilimits=(0,0),useOffset=False)
  focus=[next(q for q in r if int(q['native_id'])==id) for id in FOCUS];x=np.arange(4);ax=axes[1,col];ax.bar(x-.18,[float(q['current_rate_Pa_s'])/1000 for q in focus],.36,label='current');ax.bar(x+.18,[float(q['pair_rate_Pa_s'])/1000 for q in focus],.36,label='pairFlux');ax.axhline(0,color='black',lw=.5);ax.set(xticks=x,xticklabels=[str(id) for id in FOCUS],ylabel='Rate [kPa/s]',title='Fixed material IDs; no state update');ax.ticklabel_format(style='sci',axis='y',scilimits=(0,0),useOffset=False)
  ax=axes[2,col];width=.12
  for j,(key,label) in enumerate(zip(channels,labels)):ax.bar(x+(j-2.5)*width,[float(q[key])/1000 for q in focus],width,label=label)
  ax.axhline(0,color='black',lw=.5);ax.set(xticks=x,xticklabels=[str(id) for id in FOCUS],ylabel='Channel [kPa/s]',title='Current channels and pairFlux change');ax.ticklabel_format(style='sci',axis='y',scilimits=(0,0),useOffset=False)
 axes[0,0].legend(fontsize=7);axes[1,0].legend(fontsize=8);axes[2,0].legend(fontsize=7,ncol=2);fig.suptitle('Frozen hydraulic rate shadows: SymC/Eta, mechanics/AS/AV unchanged\nDifferent rate is not an accuracy or coupled-stability verdict');fig.savefig(path,dpi=160);plt.close(fig)

def plot_manufactured(summary,quant,path):
 fig,axes=plt.subplots(3,3,figsize=(16,11),layout='constrained');cases=(('constant_null','float64','C0'),('affine_hydraulic','float64','A64'),('affine_hydraulic','float32','A32'),('nonconstant_potential','float64','Q64'),('nonconstant_potential','float32','Q32'))
 for col,part in enumerate(PARTS):
  for row,method in enumerate(('current','pairFlux')):
   ax=axes[row,col]
   for group,color in zip(GROUPS,COLORS):
    points=[]
    for index,(field,storage,label) in enumerate(cases):
     q=[v for v in summary if v['part']==part and v['cohort']==group and v['field']==field and v['storage']==storage and v['method']==method]
     if q:points.append((index,q[0]['RMS_Pa_s']))
    if points:ax.plot([q[0] for q in points],[q[1] for q in points],'o-',ms=3,color=color,label=group)
   ax.set(xticks=range(5),xticklabels=[q[2] for q in cases],ylabel='Zero-reference RMS [Pa/s]',title=f'part{part}: {method}');ax.set_yscale('symlog',linthresh=1.);ax.grid(alpha=.2)
  ax=axes[2,col];qcases=(('affine_hydraulic','current','A current'),('affine_hydraulic','pairFlux','A pair'),('nonconstant_potential','current','Q current'),('nonconstant_potential','pairFlux','Q pair'))
  for group,color in zip(GROUPS,COLORS):
   points=[]
   for index,(field,method,label) in enumerate(qcases):
    q=[v for v in quant if v['part']==part and v['cohort']==group and v['field']==field and v['method']==method]
    if q:points.append((index,q[0]['RMS_rate32_minus_rate64_Pa_s']))
   if points:ax.plot([q[0] for q in points],[q[1] for q in points],'o-',ms=3,color=color,label=group)
  ax.set(xticks=range(4),xticklabels=[q[2] for q in qcases],ylabel='Storage effect RMS [Pa/s]',title='Float32 minus float64 rate');ax.set_yscale('symlog',linthresh=1.);ax.grid(alpha=.2)
 axes[0,0].legend(fontsize=7);fig.suptitle('Conditional analytic-field/ghost oracle on fixed actual C/J/FS\nC0=constant; A=uniform-A affine p; Q=nonconstant potential. Symlog1Pa/s is display only.');fig.savefig(path,dpi=160);plt.close(fig)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();e.need(a.execution_authorized,'Root full-read before one derived-only review');check=T/'logs'/(TAG+'.check.json');paths={k:F/(TAG+'_'+k+ext) for k,ext in [('actual','.csv'),('manufactured','.csv'),('quantization','.csv'),('actual_plot','.png'),('manufactured_plot','.png')]};e.need(not check.exists() and not any(p.exists() for p in paths.values()),'Fresh derived outputs required; old results protected');before=[];result=dict(stage=TAG,passed=False,physical_acceptance=False,solver_invocations=0,force_invocations=0,decoder_invocations=0,VTK_invocations=0,build_invocations=0,SHA_scans=0,helper_outputs_rewritten=False)
 try:
  source=T/'logs'/(SOURCE+'.check.json');r=e.read(source);e.need(r['passed'] and r['consumed_stats_unchanged'] and r['actual_ct_calls']==r['actual_Darcy_calls']==3 and r['actual_physical_steps']==0 and r['source_parts']==list(PARTS) and not r['candidate_written_back'] and not r['Eta_changed'] and not r['AS_AV_changed'],'Sealed actual3-force/no-feedback component required');completion=e.bind(r['component_completion']);done=e.read(completion['path']);call=e.bind(r['actual_call']);c=e.read(call['path']);e.need(done['passed'] and done['receiver_rows']==96 and done['manufactured_rows']==576 and c['actual_Popen_wait_exit']==c['actual_Win32_exit']==0 and c['ownership_failure'] is None,'Actual terminal component/call coverage differs')
  before=[e.stat(__file__),e.stat(T/'notes'/(TAG+'.md')),e.stat(source),completion,call];files={Path(q['path']).name:q for q in r['files']}
  for leaf in ('receivers.csv','manufactured.csv','calls.csv'):entry=e.bind(files[leaf]);e.need(Path(entry['path']).samefile(OUT/leaf),'Unbound input CSV');before.append(entry)
  actual=table(OUT/'receivers.csv');m=table(OUT/'manufactured.csv');calls=table(OUT/'calls.csv');e.need(len(actual)==96 and len(m)==576 and len(calls)==3 and {int(q['part']) for q in actual}==set(PARTS),'Original row coverage differs')
  for q in actual:q['cohort']=cohort(q)
  for q in m:q['cohort']=cohort(q)
  grouped=defaultdict(list)
  for q in m:grouped[(int(q['part']),q['cohort'],q['field'],q['storage'])].append(q)
  summary=[]
  for (part,group,field,storage),rows in sorted(grouped.items()):
   methods=('pair_minus_current',) if field=='native_constant_k' else ('current','pairFlux')
   for method in methods:
    key={'current':'current_rate_Pa_s','pairFlux':'pair_rate_Pa_s','pair_minus_current':'pair_minus_current_Pa_s'}[method];s=stats([float(q[key]) for q in rows]);summary.append(dict(part=part,cohort=group,field=field,storage=storage,reference='constant_k_algebra_difference' if field=='native_constant_k' else 'continuous_zero_conditional_ghost_oracle',method=method,n=s['n'],RMS_Pa_s=s['RMS'],maxabs_Pa_s=s['maxabs'],mean_Pa_s=s['mean'],max_p_quantization_Pa=max(float(q['max_p_float_quantization_Pa']) for q in rows),max_A_quantization_m_s2=max(float(q['max_A_float_quantization_m_s2']) for q in rows),actual_wall_closure_replay=False))
  quant=[];lookup={(int(q['part']),int(q['native_id']),q['field'],q['storage']):q for q in m};g=defaultdict(list)
  for q in m:
   if q['storage']=='float32':g[(int(q['part']),q['cohort'],q['field'])].append((q,lookup[(int(q['part']),int(q['native_id']),q['field'],'float64')]))
  for (part,group,field),pairs in sorted(g.items()):
   for method,key in [('current','current_rate_Pa_s'),('pairFlux','pair_rate_Pa_s')]:
    s=stats([float(q[key])-float(v[key]) for q,v in pairs]);quant.append(dict(part=part,cohort=group,field=field,method=method,n=s['n'],RMS_rate32_minus_rate64_Pa_s=s['RMS'],maxabs_rate32_minus_rate64_Pa_s=s['maxabs'],mean_rate32_minus_rate64_Pa_s=s['mean'],max_p_float_quantization_Pa=max(float(q['max_p_float_quantization_Pa']) for q,v in pairs),max_A_float_quantization_m_s2=max(float(q['max_A_float_quantization_m_s2']) for q,v in pairs)))
  descriptive=[]
  for part in PARTS:
   for group in ('ALL',*GROUPS):
    rows=[q for q in actual if int(q['part'])==part and (group=='ALL' or q['cohort']==group)]
    if not rows:continue
    s=stats([float(q['pair_minus_current_Pa_s']) for q in rows]);descriptive.append(dict(part=part,cohort=group,n=s['n'],delta_RMS_Pa_s=s['RMS'],delta_maxabs_Pa_s=s['maxabs'],delta_mean_Pa_s=s['mean'],current_pair_rate_sign_changes=sum(float(q['current_rate_Pa_s'])*float(q['pair_rate_Pa_s'])<0 for q in rows)))
  write(paths['actual'],actual);write(paths['manufactured'],summary);write(paths['quantization'],quant);plot_actual(actual,paths['actual_plot']);plot_manufactured(summary,quant,paths['manufactured_plot']);e.need(all(e.stat(q['path'])==q for q in before),'Sealed inputs changed during offline review')
  result.update(passed=True,source_check=e.stat(source),actual_rows=96,manufactured_rows=576,calls=3,actual_descriptive=descriptive,focus_rows=[q for q in actual if int(q['native_id']) in FOCUS],manufactured_summary_rows=len(summary),quantization_summary_rows=len(quant),new_numerical_acceptance_gates=False,constant_k_is_algebra_not_automatic_bit_equivalence=True,hydrostatic_interior_depends_on_actual_first_gradient_closure=True,manufactured_ghosts_conditional=True,universal_improvement_claimed=False,full_coupled_stability_or_causality_claimed=False,consumed_stats_unchanged=True)
 except Exception as error:result['first_failure']=str(error)
 result.update(consumed=before,outputs=[e.stat(p) for p in paths.values() if p.exists()]);e.save(check,result);print(json.dumps(dict(passed=result['passed'],check=str(check),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
