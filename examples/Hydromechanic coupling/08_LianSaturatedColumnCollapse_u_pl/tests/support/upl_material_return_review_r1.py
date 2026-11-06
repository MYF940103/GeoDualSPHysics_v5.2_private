"""Offline independent tensor/compliance review; never calls a material or spatial program."""
from pathlib import Path
import csv,json,math,collections
import numpy as np
B=Path(__file__).resolve().parents[1]
D=B/'outputs/upl_material_return_CPU_result_r1'
OUT=B/'logs/upl_material_return_CPU_review_r1.check.json'
SUM=B/'figures/upl_material_return_CPU_review_r1.csv'
assert not OUT.exists() and not SUM.exists()
raw=D/'points.csv';before=(raw.stat().st_size,raw.stat().st_mtime_ns)
rows=list(csv.DictReader(raw.open(encoding='utf-8',newline='')))
completion=json.loads((D/'completion.json').read_text(encoding='utf-8'))
run=json.loads((B/'logs/upl_material_return_CPU_r1.run.json').read_text(encoding='utf-8'))
assert run['actual_exit']==0 and run['consumed_SMT_unchanged'] and run['objects']==85 and run['SHA_scans']==0
assert len(rows)==completion['rows']==132
E=np.float32(20e6);nu=np.float32(.33);K=float(np.float32(E/(np.float32(3)*(np.float32(1)-np.float32(2)*nu))));G=float(np.float32(E/(np.float32(2)*(np.float32(1)+nu))))
phi=float(np.float32(25*math.pi/180));t=math.tan(phi);den=math.sqrt(9+12*t*t);alpha=t/den;eps=np.finfo(float).eps
fields=['xx','yy','zz','xy','yz','xz']
def tensor(r,prefix):return np.array([float(r[prefix+x])for x in fields])
def inv(s):
 I=float(sum(s[:3]));dev=s[:3]-I/3
 return I,math.sqrt(.5*(float(dev@dev)+2*float(s[3:]@s[3:])))
def strength(r,k):return float(r['cr_Pa'])+(float(r['cp_Pa'])-float(r['cr_Pa']))*math.exp(-float(r['eta'])*k)
def yield_at(s,r,k):
 I,q=inv(s);return q+alpha*I-3*strength(r,k)/den
checked=collections.Counter();maxima=collections.defaultdict(float);groups=collections.defaultdict(list);failures=[]
for r in rows:
 branch=r['branch'];psi=float(r['psi0_deg']);key=(branch,round(psi,4));groups[key].append(r)
 available=r['return_available']=='1';candidate=branch!='linked_legacy';checked['rows']+=1
 if not candidate:
  checked['legacy_rows']+=1
  if not available:checked['observed_legacy_nonfinite']+=1
  continue
 if not available:
  checked['candidate_unsupported']+=1
  assert r['path'] in ('hydrostatic_apex_diagnostic','near_apex_diagnostic')
  continue
 s=tensor(r,'new_');tr=tensor(r,'trial_');old=float(r['kappa_old_float']);kc=float(r['kappa_continuous']);saved=float(r['kappa_saved_float']);lam=float(r['lambda_solved'])
 assert np.isfinite(s).all() and math.isfinite(kc) and saved==float(np.float32(kc)) and saved>=old
 if r['status']=='elastic_exact':
  checked['candidate_elastic']+=1
  assert np.array_equal(s,tr) and saved==old and kc==old and yield_at(s,r,old)<=1e-5
  continue
 checked['candidate_radial']+=1
 Itr,qtr=inv(tr);I,q=inv(s);sf=float(r['sf']);psi0=psi*math.pi/180;beta=math.tan(psi0*math.exp(-sf*kc));beta/=math.sqrt(9+12*beta*beta)
 # Recover plastic increments from the ACTUAL returned stress tensor through compliance.
 ds=tr-s;mean=float(sum(ds[:3]))/3;dv=ds[:3]-mean
 devnorm=math.sqrt((2/3)*(float(dv@dv)+2*float(ds[3:]@ds[3:]))/(4*G*G))
 fullnorm=math.sqrt(devnorm*devnorm+2*mean*mean/(9*K*K))
 h=float(r['h_history']);history=(fullnorm if branch=='consistent_full_constant_psi' else devnorm)
 normerror=abs(history-h*lam);normbudget=8192*eps*max(1,abs(h*lam))
 continuous=yield_at(s,r,kc);rootbudget=float(r['scalar_budget_Pa']);savedres=yield_at(s,r,saved)
 qerror=abs(q-(qtr-G*lam));Ierror=abs(I-(Itr-9*K*beta*lam))
 tensorbudget=8192*eps*max(1,abs(Itr),qtr,abs(I),q)
 assert normerror<=normbudget and abs(continuous)<=4*rootbudget and qerror<=tensorbudget and Ierror<=tensorbudget
 assert 0<=lam<=qtr/G and float(r['minus_dF_dlambda_Pa'])>0
 assert abs(kc-(old+h*lam))<=8192*eps*max(1,abs(kc))
 maxima['independent_continuous_yield_abs_Pa']=max(maxima['independent_continuous_yield_abs_Pa'],abs(continuous))
 maxima['independent_saved_float_yield_abs_Pa']=max(maxima['independent_saved_float_yield_abs_Pa'],abs(savedres))
 maxima['independent_norm_error']=max(maxima['independent_norm_error'],normerror)
 maxima['independent_norm_error_over_budget']=max(maxima['independent_norm_error_over_budget'],normerror/normbudget)
 maxima['independent_tensor_error_Pa']=max(maxima['independent_tensor_error_Pa'],qerror,Ierror)
 maxima['independent_continuous_yield_over_root_budget']=max(maxima['independent_continuous_yield_over_root_budget'],abs(continuous)/rootbudget)
 maxima['root_iterations']=max(maxima['root_iterations'],int(r['root_iterations']))
 if r['path']=='constant_strength_closed_control':
  ft=qtr+alpha*Itr-3*float(r['cp_Pa'])/den
  closed=ft/(G+9*K*alpha*beta);error=abs(lam-closed);budget=4096*eps*max(1,abs(closed));assert error<=budget
  checked['independent_constant_strength_closed']+=1;maxima['independent_closed_lambda_error']=max(maxima['independent_closed_lambda_error'],error)
assert checked['candidate_radial']==54 and checked['candidate_elastic']==27 and checked['candidate_unsupported']==18 and checked['legacy_rows']==33 and checked['observed_legacy_nonfinite']==3 and checked['independent_constant_strength_closed']==9
records=[]
plastic_paths={'first_yield_nonzero_shear','further_loading_nonzero_shear','preset_kappa_nonzero_shear'}
for (branch,psi),rs in groups.items():
 plast=[r for r in rs if r['path'] in plastic_paths and r['return_available']=='1']
 maxi=lambda name:max((abs(float(r[name]))for r in plast),default=None)
 presets=[r for r in rs if r['path']=='preset_kappa_nonzero_shear']
 records.append({'branch':branch,'psi0_deg':psi,'cp_Pa':float(rs[0]['cp_Pa']),'rows':len(rs),'ordinary_plastic_rows':len(plast),'max_ordinary_plastic_saved_yield_abs_Pa':maxi('f_return_saved_Pa'),'max_ordinary_plastic_continuous_yield_abs_Pa':maxi('f_return_continuous_Pa'),'preset_psi_end_deg':float(presets[0]['psi_at_continuous_deg']),'unsupported_rows':sum(r['return_available']=='0' for r in rs),'ordinary_max_root_iterations':max(int(r['root_iterations'])for r in plast)})
with SUM.open('x',encoding='utf-8',newline='')as f:
 w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
assert before==(raw.stat().st_size,raw.stat().st_mtime_ns)
result={'stage':'upl_material_return_CPU_review_r1','passed_bounded_radial_algebra_checks':True,'source':str(raw),'rows':132,'counts':dict(checked),'actual_float_K_G':[K,G],'independent_binary64_budgets':{'compliance_norm':'8192*eps*max(1,abs(h*lambda))','tensor_q_I':'8192*eps*max(1,abs(Itrial),qtrial,abs(Inew),qnew)','constant_strength_lambda':'4096*eps*max(1,abs(closed_lambda))','continuous_yield':'4 times predeclared scalar root budget; saved-float residual descriptive'},'maxima':dict(maxima),'groups':records,'summary_csv':str(SUM),'legacy_apex_nonfinite_and_candidate_apex_unsupported_preserved':True,'saved_float_residual_not_root_error':True,'raw_SMT_unchanged':True,'SHA_scans':0,'physical_or_constitutive_release_acceptance':False}
OUT.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
print(json.dumps({'counts':result['counts'],'maxima':result['maxima'],'check':str(OUT)},indent=2))
