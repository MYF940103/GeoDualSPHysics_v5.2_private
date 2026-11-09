"""Readable diagnostic plot from sealed rvisc30 CSVs; no raw decode or solver."""
import argparse,csv,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

T=Path(__file__).resolve().parents[1]
F=T/'figures';TAG='upl_c08_rvisc_plot_r1'
def stamp(p):
 s=p.stat();return dict(path=str(p.resolve()),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def table(p):
 with p.open(encoding='utf8',newline='') as f:return list(csv.DictReader(f))
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--execution-authorized',action='store_true');args=a.parse_args();assert args.execution_authorized
 inputs=[T/'logs/upl_c08_rvisc_review_r1.check.json',F/'upl_c08_rvisc_review_r1_history.csv',F/'upl_c08_rvisc_review_r1_extrema.csv']
 before=[stamp(p) for p in inputs];receipt=json.loads(inputs[0].read_text(encoding='utf8'));assert receipt['passed'] and receipt['actual_common_frames']==30
 expected={Path(q['path']).name:q for q in receipt['files']}
 assert all(stamp(p)==expected[p.name] for p in inputs[1:])
 history,extrema=map(table,inputs[1:]);assert len(history)==60
 groups=('baseline_residual_OFF','residual_alpha0p1');names=('Baseline','Residual viscosity, alpha=0.1')
 total={k:0. for k in ((g,i) for g in groups for i in range(30))};counts={k:0 for k in total}
 for q in extrema:
  if q['field'].startswith('total_'):
   key=q['group'],int(q['part']);total[key]=max(total[key],abs(float(q['value'])));counts[key]+=1
 assert all(n==12 for n in counts.values())
 rows=[]
 for q in history:
  key=q['group'],int(q['part']);rows.append(dict(group=key[0],part=key[1],time_s=float(q['time_s']),tau_s=float(q['tau_s']),max_abs_total_stress_component_Pa=total[key]))
 csvout=F/(TAG+'_stress_history.csv');png=F/(TAG+'_diagnosis.png');check=T/'logs'/(TAG+'.check.json')
 assert not any(p.exists() for p in (csvout,png,check))
 with csvout.open('x',encoding='utf8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 plt.rcParams.update({'font.size':10,'axes.titlesize':11})
 fig,axes=plt.subplots(2,3,figsize=(14,8),layout='constrained')
 specs=(('p_min_Pa',.001,'Minimum pore pressure','p [kPa]'),('stress',.001,'Maximum absolute total-stress component','Stress [kPa]'),('soil_pairs_r_lt_0p7dp',1,'Soil pairs with r < 0.7 dp','Pair count'),('pair7011_7012_r_over_dp',1,'Fixed material pair 7011 / 7012','Separation / dp'),('current_mixture_KE_J_per_m',1,'Current mixture kinetic quadratic','KE [J/m]'),('front_particle_center_x_m',1,'Front particle-center position','x [m]'))
 for axis,(field,scale,title,ylabel) in zip(axes.flat,specs):
  for g,name,color,style in zip(groups,names,('#3568a2','#d95f02'),('--','-')):
   series=sorted((q for q in history if q['group']==g),key=lambda q:int(q['part']));assert len(series)==30
   y=[total[g,int(q['part'])] if field=='stress' else float(q[field]) for q in series]
   axis.plot([float(q['tau_s']) for q in series],[v*scale for v in y],style,color=color,lw=1.8,label=name)
  if field=='pair7011_7012_r_over_dp':axis.axhline(.7,color='.5',lw=.8,ls=':',label='Descriptive 0.7 dp level')
  axis.set(title=title,xlabel='Actual time since release [s]',ylabel=ylabel);axis.grid(alpha=.25);axis.legend(fontsize=8)
 fig.suptitle('C08: 30 saved states, identical inputs; one added residual-viscosity operator\nWindow extremes and endpoint behavior differ; no physical acceptance',fontsize=13)
 fig.savefig(png,dpi=180);plt.close(fig)
 assert all(stamp(p)==q for p,q in zip(inputs,before))
 result=dict(stage=TAG,passed=True,source_review=before[0],source_CSVs=before[1:],actual_rows=60,total_stress_extrema_per_state=12,raw_data_reads=0,solver_invocations=0,decoder_invocations=0,SHA_scans=0,no_clipping_or_smoothing=True,physical_acceptance=False,visual_review_pending=True,files=[stamp(csvout),stamp(png)])
 with check.open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
 print('DIAGNOSTIC_PLOT_COMPLETE',png)
if __name__=='__main__':main()
