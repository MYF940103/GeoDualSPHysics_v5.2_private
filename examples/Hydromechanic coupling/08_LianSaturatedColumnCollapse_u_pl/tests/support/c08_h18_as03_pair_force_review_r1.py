"""Offline interpretation of the unique four-state original CPU force component."""
from pathlib import Path
import csv,json,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
T=Path(__file__).resolve().parents[1];TAG='c08_h18_as03_pair_force_review_r1'
O=T/'outputs/c08_h18_as03_pair_force_r1'
def st(p):
 s=p.stat();return dict(path=str(p.resolve()),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def table(p):
 with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def main():
 prefix=T/'figures'/TAG;check=T/'logs'/(TAG+'.check.json')
 assert not check.exists() and not list(prefix.parent.glob(TAG+'_*'))
 receipt=read(T/'logs/c08_h18_as03_pair_force_r1.check.json');done=read(O/'completion.json')
 assert receipt['passed'] and receipt['component_invocations']==1 and receipt['physical_steps']==0 and done['passed']
 assert done['actual_force_calls']==done['actual_Darcy_calls']==12 and done['soil_rows']==60000 and done['pair_rows']==24 and done['direct_pair_rows']==120
 assert done['all5000_soil_primary_bits_unchanged_per_call'] and done['physical_steps']==done['material_return_calls']==0
 files={Path(q['path']).name:q for q in receipt['files']}
 inputs=[T/'logs/c08_h18_as03_pair_force_r1.check.json',O/'completion.json']
 data={}
 for name in ['pairs.csv','direct_pairs.csv','calls.csv','focus.csv']:
  p=O/name;assert st(p)==files[name];inputs.append(p);data[name]=table(p)
 pairs,direct,calls,focus=[data[n] for n in ['pairs.csv','direct_pairs.csv','calls.csv','focus.csv']]
 assert len(pairs)==24 and len(direct)==120 and len(calls)==12 and len(focus)==48
 assert all(int(q['source_saved_FS_changes'])==int(q['baseline_FS_changes'])==0 and int(q['primary_bits_unchanged'])==1 for q in calls)
 rows=[]
 for part in [38,76,92,300]:
  for ia,ib in [(6767,6865),(4953,4954)]:
   pp={q['mode']:q for q in pairs if int(q['part'])==part and int(q['id_i'])==ia and int(q['id_j'])==ib}
   assert set(pp)=={'baseline','AS_off','AV_off'}
   dd={q['term']:q for q in direct if int(q['part'])==part and int(q['id_i'])==ia and q['mode']=='baseline'}
   assert len(dd)==5
   b=pp['baseline']; row=dict(part=part,time_s=float(b['time_s']),tau_s=float(b['tau_s']),completed_step=int(b['completed_step']),ID_a=ia,ID_b=ib,r_over_dp=float(b['r_m'])/.04,rdot_m_s=float(b['rdot_m_s']),all_neighbor_relative_radial_m_s2=float(b['relative_all_neighbor_a_radial_m_s2']),tangential_curvature_m_s2=float(b['tangential_curvature_m_s2']),rddot_m_s2=float(b['rddot_m_s2']))
   for name,key in [('total','literal_total_stress_commit'),('AS','literal_AS_commit'),('AV','literal_AV_commit')]:
    q=dd[key];row['direct_'+name+'_radial_m_s2']=float(q['relative_a_radial_m_s2']);row['direct_'+name+'_pair_power_W_m']=float(q['pair_power_W_per_m']);row['direct_'+name+'_force_balance_N_m']=float(q['force_balance_norm_N_per_m'])
   row['other_neighbors_and_accumulation_residual_m_s2']=row['all_neighbor_relative_radial_m_s2']-sum(row['direct_'+n+'_radial_m_s2'] for n in ['total','AS','AV'])
   for name,mode in [('AS','AS_off'),('AV','AV_off')]:
    row['all_neighbor_'+name+'_counterfactual_effect_m_s2']=-float(pp[mode]['minus_baseline_relative_a_radial_m_s2'])
    for endpoint in ['i','j']:row['pressure_rate_'+endpoint+'_'+mode+'_minus_baseline_Pa_s']=float(pp[mode]['pressure_rate_'+endpoint+'_Pa_s'])-float(b['pressure_rate_'+endpoint+'_Pa_s'])
   assert all(math.isfinite(v) for v in row.values());rows.append(row)
 csvpath=Path(str(prefix)+'_summary.csv')
 with csvpath.open('x',newline='',encoding='utf-8') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
 fig,axes=plt.subplots(3,2,figsize=(15,13),layout='constrained')
 for col,identity in enumerate([6767,4953]):
  rs=[r for r in rows if r['ID_a']==identity];x=np.arange(4);width=.2
  charts=[([('direct_total_radial_m_s2','Direct total stress'),('direct_AS_radial_m_s2','Direct AS'),('direct_AV_radial_m_s2','Direct AV'),('other_neighbors_and_accumulation_residual_m_s2','Other-neighbor remainder')],'Relative radial acceleration [m/s^2]'),([('all_neighbor_relative_radial_m_s2','Original all-neighbor'),('all_neighbor_AS_counterfactual_effect_m_s2','Original minus ASoff'),('all_neighbor_AV_counterfactual_effect_m_s2','Original minus AVoff')],'Counterfactual radial acceleration [m/s^2]'),([('direct_AS_pair_power_W_m','Direct AS'),('direct_AV_pair_power_W_m','Direct AV')],'Instantaneous pair power [W/m]')]
  for row,(series,ylabel) in enumerate(charts):
   ax=axes[row,col]
   for k,(key,label) in enumerate(series):ax.bar(x+(k-(len(series)-1)/2)*width,[r[key] for r in rs],width,label=label)
   ax.set_xticks(x,[f"{r['tau_s']:.3f}s\nr/dp={r['r_over_dp']:.3f}" for r in rs]);ax.axhline(0,color='black',lw=.6);ax.set_yscale('symlog',linthresh=.01 if row<2 else .001);ax.set_ylabel(ylabel);ax.grid(axis='y',alpha=.25);ax.legend(fontsize=8)
  axes[0,col].set_title(f"Saved material pair {rs[0]['ID_a']}/{rs[0]['ID_b']}\npositive radial acceleration = separation")
 fig.suptitle('Original CPU zero-step forces on saved AS0.3/n2.55 states\nCounterfactual toggles are not additive force parts or new trajectories; no GPU-substage or physical acceptance')
 png=Path(str(prefix)+'_forces.png');fig.savefig(png,dpi=170);plt.close(fig)
 result=dict(stage=TAG,analysis_complete=True,physical_acceptance=False,component_invocations=0,solver_invocations=0,decoder_invocations=0,SHA_scans=0,consumed=[st(p) for p in inputs],script=st(Path(__file__)),summary_rows=rows,source_saved_FS_changes=0,baseline_FS_changes=0,all_neighbor_remainder_is_descriptive=True,original_min_AV_pair_power_W_m=min(float(q['pair_power_W_per_m']) for q in direct if q['mode']=='baseline' and q['term']=='literal_AV_commit'),original_max_AV_pair_power_W_m=max(float(q['pair_power_W_per_m']) for q in direct if q['mode']=='baseline' and q['term']=='literal_AV_commit'),visual_QA_pending=True,files=[st(csvpath),st(png)])
 with check.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
if __name__=='__main__':main()
