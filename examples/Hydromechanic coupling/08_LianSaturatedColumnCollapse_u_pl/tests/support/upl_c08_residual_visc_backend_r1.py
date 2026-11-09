"""Describe actual CPU-candidate versus GPU-math accelerations; no force or solver."""
import argparse,csv
from pathlib import Path
import numpy as np
import mdbc_partition_components_r3 as e
T=Path(__file__).resolve().parents[1];TAG='upl_c08_residual_visc_backend_r1'
def table(p):
 with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def run():
 check=T/'logs'/(TAG+'.check.json');out=T/'figures'/(TAG+'.csv')
 e.need(not check.exists() and not out.exists(),'Existing comparison protected')
 cp=T/'logs/upl_c08_residual_visc_cpu_r2.check.json';gp=T/'logs/upl_c08_residual_visc_gpu_math_r1.check.json'
 c,g=e.read(cp),e.read(gp);k=e.read(g['source_particle_check']['path'])
 e.need(c['passed'] and g['passed'] and c['alpha']==.1 and c['OFF_baseline_alignment']['mismatched_fields']==0 and g['memcheck_zero_errors_and_leaks'] and c['source_native']==k['source_native'],'Passed same-native CPU and GPU math required')
 cf=e.bind(next(q for q in c['files'] if Path(q['path']).name=='soil_force.csv'));gf=e.bind(next(q for q in g['files'] if Path(q['path']).name=='nodes.csv'))
 before=[e.stat(__file__),e.stat(cp),e.stat(gp),e.bind(g['source_particle_check']),e.bind(g['component_completion']),cf,gf]
 cpu={(int(q['part']),int(q['native_id'])):q for q in table(cf['path']) if q['mode']=='ON'}
 gpu=[q for q in table(gf['path']) if q['case']=='native'];e.need(len(cpu)==len(gpu)==10000,'Two complete native cohorts required')
 result=[]
 for part in (13,14):
  selected=sorted((q for q in gpu if int(q['part'])==part),key=lambda q:int(q['native_id']))
  e.need([int(q['native_id']) for q in selected]==list(range(2060,7060)),'Full material IDs required')
  delta=[];committed=[];same=0
  for q in selected:
   r=cpu[part,int(q['native_id'])]
   a=np.array([float(r['ideal_added_a_x_m_s2']),float(r['ideal_added_a_z_m_s2'])]);b=np.array([float(q['dax_gpu']),float(q['daz_gpu'])])
   aa=np.array([float(r['Ace_x_m_s2']),float(r['Ace_z_m_s2'])],dtype=np.float32);bb=np.array([float(q['added_ax_float']),float(q['added_az_float'])],dtype=np.float32)
   delta.append(np.linalg.norm(a-b));committed.append(np.linalg.norm(aa.astype(float)-bb.astype(float)));same+=int(np.array_equal(aa.view(np.uint32),bb.view(np.uint32)))
  delta=np.array(delta);committed=np.array(committed)
  result.append(dict(part=part,soil_IDs=5000,ideal_delta_a_RMS_difference_m_s2=float(np.sqrt(np.mean(delta**2))),ideal_delta_a_max_difference_m_s2=float(delta.max()),final_float_Ace_RMS_difference_m_s2=float(np.sqrt(np.mean(committed**2))),final_float_Ace_max_difference_m_s2=float(committed.max()),both_components_bit_exact_nodes=same))
 e.need(all(e.stat(q['path'])==q for q in before),'Consumed inputs changed')
 with out.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(result[0]));w.writeheader();w.writerows(result)
 e.save(check,dict(stage=TAG,passed=True,descriptive_only=True,new_numerical_threshold=False,full_GPU_force_or_Darcy_comparison=False,physical_acceptance=False,solver_invocations=0,force_evaluations=0,native_decodes=0,SHA_scans=0,results=result,consumed=before,consumed_stats_unchanged=True,output=e.stat(out)))
 print('BACKEND_MATH_COMPARISON_SAVED',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();e.need(a.execution_authorized,'Root-reviewed derived comparison only');run()
