"""One literature-based AS coefficient comparison on sealed matrices, not a solver run."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

T=Path(__file__).resolve().parents[1];TAG='upl_c08_as_epsilon_frozen_r1';F=T/'figures'

def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args()
 if not args.execution_authorized:raise RuntimeError('Root review required')
 prefix=F/TAG
 if list(F.glob(TAG+'*')):raise RuntimeError('Existing derived results protected')
 receipt=T/'logs/upl_c08_local_pressure_spectrum_as_r1.check.json';parent=json.loads(receipt.read_text(encoding='utf-8'));assert parent['passed'] and parent['evaluated_saved_state_blocks']==8
 before=[stat(receipt),stat(__file__),stat(T/'notes'/(TAG+'.md'))];old=float(np.float32(.2));new=float(np.float32(.5));factor=new/old;assert parent['AS_epsilon_float']==old
 table=F/'upl_c08_local_pressure_spectrum_as_r1_summary.csv';entry=next(e for e in parent['files'] if Path(e['path']).resolve()==table.resolve());assert stat(table)==entry;before.append(entry)
 with table.open(encoding='utf-8') as f:baseline={(int(r['part']),r['patch'],r['variable_view']):r for r in csv.DictReader(f)}
 rows=[]
 for part in (60,61,62,63):
  for patch in ('5809','4956_4959'):
   path=F/('upl_c08_local_pressure_spectrum_as_r1_part%03d_%s.npz'%(part,patch));entry=next(e for e in parent['files'] if Path(e['path']).resolve()==path.resolve());assert stat(path)==entry;before.append(entry)
   with np.load(path,allow_pickle=False) as z:
    ids=z['target_native_IDs'];columns=z['pressure_native_IDs'];inside=np.searchsorted(columns,ids);assert np.array_equal(columns[inside],ids)
    raw=z['A_direct_plus_rawAce_copied_from_baseline'];newA=raw+factor*z['full_AS_increment_rows'][:,inside];weights=z['storage_W_nV_over_Kw'];fs=z['target_FSType'];tau=float(z['tau_s'])
    for view,keep in (('all_patch_variables',np.arange(len(ids))),('FS0_principal',np.flatnonzero(fs==0))):
     sub=newA[np.ix_(keep,keep)];ev=np.linalg.eigvals(sub);w=np.sqrt(weights[keep]);weighted=w[:,None]*sub/w[None,:];ref=baseline[(part,patch,view)]
     rows.append(dict(part=part,tau_s=tau,patch=patch,variable_view=view,variables=len(keep),epsilon_old=old,epsilon_new=new,AS_block_scale=factor,epsilon0_raw_max_Re_lambda_per_s=float(ref['baseline_raw_max_real_eigenvalue_per_s']),epsilon02_max_Re_lambda_per_s=float(ref['max_real_eigenvalue_per_s']),epsilon05_max_Re_lambda_per_s=float(ev.real.max()),epsilon05_max_storage_symmetric_eigenvalue_per_s=float(np.linalg.eigvalsh((weighted+weighted.T)*.5)[-1]),AS_required_exact_zero_eigenvalues=int(ref['AS_exact_zero_eigenvalues'])))
 path=Path(str(prefix)+'.csv')
 with path.open('x',encoding='utf-8',newline='') as f:writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
 fig,axes=plt.subplots(1,2,figsize=(11,4.2),layout='constrained')
 for ax,patch in zip(axes,('5809','4956_4959')):
  own=[r for r in rows if r['patch']==patch and r['variable_view']=='FS0_principal']
  for field,label,style in (('epsilon0_raw_max_Re_lambda_per_s','epsilon 0 (raw)','--'),('epsilon02_max_Re_lambda_per_s','epsilon 0.2','-'),('epsilon05_max_Re_lambda_per_s','epsilon 0.5','-')):ax.plot([r['tau_s'] for r in own],[r[field] for r in own],style,marker='o',label=label)
  ax.axhline(0,color='grey',lw=.8);ax.set(title=patch+' fixed FS0 block',xlabel='Actual saved tau [s]',ylabel='Conditional max Re(lambda) [1/s]');ax.grid(alpha=.25);ax.legend()
 fig.suptitle('Frozen pressure-only AS sensitivity; outside perturbations held, not a trajectory or full-system stability test')
 image=Path(str(prefix)+'.png');fig.savefig(image,dpi=170);plt.close(fig)
 assert all(stat(e['path'])==e for e in before)
 result=dict(stage=TAG,passed=True,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,source_geometric_material_and_pressure_states_frozen=True,only_AS_Jacobian_scaled=True,whole_operator_not_scaled=True,actual_float_parameter_ratio=factor,AS_quantization_or_GPU_bit_replay_claimed=False,consumed=before,files=[stat(path),stat(image)],visual_QA_pending=True)
 with Path(str(prefix)+'.check.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)
 print('AS_EPSILON_FROZEN_COMPARISON_COMPLETE')

if __name__=='__main__':main()
