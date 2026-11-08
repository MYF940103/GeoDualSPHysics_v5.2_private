"""Compare retained n3 particle-center front with a coarse Fig14 visible-outline reference."""
import argparse,csv,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
T=Path(__file__).resolve().parents[1]; C=T.parent; TAG='upl_c08_lian14_front_compare_r1'
def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def table(p):
 with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();assert a.execution_authorized
 out=T/'figures';check=T/'logs'/(TAG+'.check.json');targets=[out/(TAG+'.csv'),out/(TAG+'.png'),check];assert not any(p.exists() for p in targets)
 paths=[Path(__file__),T/'notes'/(TAG+'.md'),C/'figures/collapse_psi0_r6/history.csv',C/'figures/collapse_psi0_r6/source.json',T/'figures/upl_c08_lian14_outline_r1_summary.csv',T/'logs/upl_c08_lian14_outline_r1.check.json'];before=[stat(p) for p in paths]
 h=table(paths[2]);meta=json.loads(paths[3].read_text());ref=table(paths[4]);proof=json.loads(paths[5].read_text());assert len(h)==300 and all(int(r['soil_IDs'])==5000 for r in h) and meta['AS_exponent_float']==3 and meta['group']=='psi0' and proof['passed'] and not proof['pressure_values_sampled'] and len(ref)==3
 rows=[]
 for r in ref:
  t=float(r['requested_tau_s']);q=min(h,key=lambda q:abs(float(q['tau_s'])-t));assert abs(float(q['tau_s'])-t)<1e-8
  rows.append(dict(requested_tau_s=t,actual_native_tau_s=float(q['tau_s']),native_part=int(q['part']),n3_particle_center_front_m=float(q['front_x_m']),paper_visible_bulk_front_m=float(r['front_colored_extent_m']),paper_digitization_allowance_m=float(r['front_digitization_allowance_m']),center_vs_extent_representation_scale_m=.02,unadjusted_center_minus_visible_extent_m=float(q['front_x_m'])-float(r['front_colored_extent_m'])))
 with targets[0].open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 fig,ax=plt.subplots(figsize=(8,4.8),layout='constrained');ax.plot([float(q['tau_s']) for q in h],[float(q['front_x_m']) for q in h],lw=1.5,label='Retained n3 GPU: particle-center maximum x')
 ax.errorbar([q['requested_tau_s'] for q in rows],[q['paper_visible_bulk_front_m'] for q in rows],yerr=[q['paper_digitization_allowance_m'] for q in rows],fmt='o',capsize=4,color='C1',label='Lian Fig14: visible bulk outline (raster)')
 ax.set(xlabel='Elapsed time after gate removal [s]',ylabel='Front x [m]',xlim=(0,3.05),title='C08 psi=0: retained result and coarse paper-shape reference');ax.grid(alpha=.25);ax.legend(fontsize=8)
 fig.text(.5,.005,'Different representations: no radius correction, time fit or pressure-color comparison.',ha='center',fontsize=8);fig.savefig(targets[1],dpi=180);plt.close(fig)
 assert all(stat(e['path'])==e for e in before)
 check.write_text(json.dumps(dict(stage=TAG,passed=True,consumed=before,files=[stat(p) for p in targets[:2]],rows=rows,visual_QA_pending=True,physical_acceptance=False,theory_error_claimed=False,SHA_scans=0),indent=2)+'\n',encoding='utf-8');print(check)
if __name__=='__main__':main()
