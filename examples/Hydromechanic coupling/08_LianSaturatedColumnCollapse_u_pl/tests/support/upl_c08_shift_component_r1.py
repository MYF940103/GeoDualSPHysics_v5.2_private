"""One saved total-n3 state, one restricted shift proposal; no state update or solver."""
import argparse,csv,json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import upl_c08_shift_frozen_r1 as shift
import upl_c08_as_effective_partial_review_r1 as native

T=shift.T;TAG='upl_c08_shift_component_r1';PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json');PART=50
FIELDS=('p_Pa','J','sigmaeff_xx_Pa','sigmaeff_yy_Pa','sigmaeff_zz_Pa','sigmaeff_xy_Pa','sigmaeff_yz_Pa','sigmaeff_xz_Pa','kappa','P0_Pa')
UNITS=('Pa','1','Pa','Pa','Pa','Pa','Pa','Pa','1','Pa')
need,stat= native.need,native.stat

def write(leaf,rows):
 p=Path(str(PREFIX)+'_'+leaf+'.csv')
 with p.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 return p

def coverage(x,V):
 """Soil-only V0J W coverage, including self; not full wall quadrature."""
 tree=cKDTree(x);out=np.zeros(len(x))
 for i in range(len(x)):
  js=np.asarray(sorted(tree.query_ball_point(x[i],shift.kernel.SEARCH)),dtype=int);d=(x[i]-x[js]).astype(np.float32);rr=(d[:,0]*d[:,0]+d[:,1]*d[:,1]).astype(np.float32);keep=rr<=shift.R2;js,rr=js[keep],rr[keep]
  out[i]=np.dot(V[js],np.asarray([shift.kernel.cubic(float(r))[0] for r in rr]))
 return out

def derivatives(q,V,values,delta,eligible):
 """Same full-fluid stencil/C for native fields, displacement and affine checks."""
 x=q['x'];tree=cKDTree(x);count=len(x);transport=np.full((count,len(FIELDS)),np.nan);div=np.full(count,np.nan);det=np.full(count,np.nan);affine=np.full(count,np.nan);constant=np.full(count,np.nan);condition=np.full(count,np.nan)
 for i in np.flatnonzero(eligible):
  need(q['fixed_hits'][i]==q['fs_hits'][i]==0,'Complete-interior receiver must have no fixed or true-FS source')
  js=np.asarray(sorted(tree.query_ball_point(x[i],shift.kernel.SEARCH)),dtype=int);d=(x[i]-x[js]).astype(np.float32);rr=(d[:,0]*d[:,0]+d[:,1]*d[:,1]).astype(np.float32);keep=(rr<=shift.R2)&(rr>=shift.kernel.LOWER);js,d,rr=js[keep],d[keep],rr[keep]
  g=(d*np.asarray([shift.kernel.cubic(float(r))[1] for r in rr],dtype=np.float32)[:,None]).astype(float);moment=-np.einsum('i,ij,ik->jk',V[js],d.astype(float),g);C=np.linalg.inv(moment);gi=g@C.T;condition[i]=np.linalg.cond(moment)
  grad=np.einsum('i,ij,ik->kj',V[js],gi,values[js]-values[i]);transport[i]=grad@delta[i]
  dgrad=np.einsum('i,ij,ik->kj',V[js],gi,delta[js]-delta[i]);div[i]=np.trace(dgrad);det[i]=np.linalg.det(np.eye(2)+dgrad)-1.
  agrad=np.einsum('i,ij,ik->kj',V[js],gi,x[js]-x[i]);affine[i]=np.max(np.abs(agrad-np.eye(2)));constant[i]=np.linalg.norm(np.sum(V[js,None]*gi*(np.ones(len(js))-1.)[:,None],axis=0))
 return transport,div,det,affine,constant,condition

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Author-only until root full review');need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial outputs protected')
 before=[stat(__file__),stat(T/'notes'/(TAG+'.md')),stat(shift.__file__),stat(shift.cluster.__file__),stat(shift.c.__file__),stat(shift.kernel.__file__),stat(native.__file__),stat(T/'support/upl_c08_fsmask_r1.py')];files=[]
 result=dict(stage=TAG,passed=False,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,build_invocations=0,SHA_scans=0)
 try:
  ctx=native.load(native.SPECS[0],before);need(ctx['label']=='total_n3' and ctx['count']==90,'Only sealed total-AS n3 causal native is admitted');expected=np.sort(np.r_[np.arange(1800),(1800,1852,1904,1956,2008),np.arange(2060,7060)]).astype('uint32');a,slots=native.inspect(ctx,PART,float(ctx['clocks'][PART]['time_s']),expected);original=a.tobytes();q=shift.cloud(a)
  need(float(shift.kernel.H)==shift.H and shift.kernel.R2==shift.R2,'Audited Cubic constants differ');eligible=q['interior']&(q['x'][:,0]>shift.R)&(q['x'][:,1]>shift.R);need(eligible.any(),'No complete interior survives the frozen bands')
  delta=q['proposals'][0].copy();delta[~eligible]=0.;xafter=q['x']+delta;V=a['PoroCurrentVolume'][slots,0].copy();need(np.array_equal(V,shift.V0*q['J']),'Actual soil V0J differs');need(np.all(delta[~eligible]==0),'Frozen soil displacement differs')
  values=np.column_stack((a['PorePress'][slots,0],a['PoroVolumeRatio'][slots,0],a['SigmaState_kk'][slots],a['SigmaState_ij'][slots],a['Kplastic'][slots,0],a['PorePress0'][slots,0])).astype(float)
  transport,div,det,affine,constant,condition=derivatives(q,V,values,delta,eligible);need(all(np.isfinite(v[eligible]).all() for v in (transport,div,det,affine,constant,condition)),'Nonfinite eligible reconstruction');cov0,cov1=coverage(q['x'],V),coverage(xafter,V);nn0=cKDTree(q['x']).query(q['x'],k=2,workers=1)[0][:,1]/shift.DP;nn1=cKDTree(xafter).query(xafter,k=2,workers=1)[0][:,1]/shift.DP
  common=dict(part=PART,completed_step=int(ctx['clocks'][PART]['completed_step']),time_s=float(a['time']),tau_s=float(a['time'])-float(ctx['done']['source_actual_time_s']));points=[]
  for i,identity in enumerate(q['ids']):
   row=dict(native_id=int(identity),x_m=float(q['x'][i,0]),z_m=float(q['x'][i,1]),FSType=int(a['FSType'][slots[i],0]),eligible=bool(eligible[i]),raw_delta_x_m=float(q['proposals'][0,i,0]),raw_delta_z_m=float(q['proposals'][0,i,1]),delta_x_m=float(delta[i,0]),delta_z_m=float(delta[i,1]),after_x_m=float(xafter[i,0]),after_z_m=float(xafter[i,1]),before_NN_over_dp=float(nn0[i]),after_NN_over_dp=float(nn1[i]),before_soil_kernel_coverage=float(cov0[i]),after_soil_kernel_coverage=float(cov1[i]))
   for name,arr in (('div_delta',div),('det_I_plus_grad_delta_minus1',det),('C_moment_condition',condition),('affine_gradient_max_error',affine)):row[name]=float(arr[i]) if eligible[i] else None
   for k,name in enumerate(FIELDS):row['native_'+name]=float(values[i,k]);row['Taylor_needed_'+name]=float(transport[i,k]) if eligible[i] else None
   points.append(row)
  summaries=[]
  for label,x,cover in (('before',q['x'],cov0),('after_one_proposal',xafter,cov1)):
   row=dict(**common,state=label,soil_count=5000,eligible_count=int(eligible.sum()),FS23_count=int(q['surface'].sum()),**shift.geometry(x,eligible,q['surface']));row.update({'soil_kernel_coverage_'+k:v for k,v in shift.qstats(cover).items()});row.update({'interior_kernel_coverage_'+k:v for k,v in shift.qstats(cover[eligible]).items()});summaries.append(row)
  fields=[]
  for k,(name,units) in enumerate(zip(FIELDS,UNITS)):
   v=transport[eligible,k];fields.append(dict(field=name,units=units,eligible_count=len(v),min=float(v.min()),mean=float(v.mean()),RMS=float(np.sqrt(np.mean(v*v))),max=float(v.max()),max_abs=float(np.max(np.abs(v))),negative_Taylor_increment_count=int(np.count_nonzero(v<0)),actual_field_changed=False))
  for leaf,rows in (('points',points),('summary',summaries),('transport',fields)):files.append(write(leaf,rows))
  fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained');lo=min(nn0.min(),nn1.min());hi=max(nn0.max(),nn1.max())
  for ax,x,nn,title in ((axes[0,0],q['x'],nn0,'Before: soil NN / dp'),(axes[0,1],xafter,nn1,'After one proposal: soil NN / dp')):
   sc=ax.scatter(x[:,0],x[:,1],c=nn,s=5,vmin=lo,vmax=hi,cmap='viridis');fig.colorbar(sc,ax=ax,label='Nonself NN / dp');ax.set_title(title)
  sc=axes[1,0].scatter(q['x'][:,0],q['x'][:,1],c=np.linalg.norm(delta,axis=1)/shift.H,s=5,cmap='magma');fig.colorbar(sc,ax=axes[1,0],label='Proposed |delta| / h');axes[1,0].set_title('Frozen bands have exact zero proposal')
  lim=float(np.max(np.abs(div[eligible])));sc=axes[1,1].scatter(q['x'][eligible,0],q['x'][eligible,1],c=div[eligible],s=5,vmin=-lim if lim else -1.,vmax=lim if lim else 1.,cmap='coolwarm');fig.colorbar(sc,ax=axes[1,1],label='div(delta), eligible receivers');axes[1,1].set_title('Geometric map defect; fields are carried unchanged')
  for ax in axes.ravel():ax.set(xlabel='x [m]',ylabel='z [m]',aspect='equal',xlim=(q['x'][:,0].min()-.04,q['x'][:,0].max()+.04),ylim=(q['x'][:,1].min()-.04,q['x'][:,1].max()+.04))
  fig.suptitle('Total-AS n3, actual tau %.9f s: one proposal, no evolution or transport'%common['tau_s']);p=Path(str(PREFIX)+'.png');fig.savefig(p,dpi=165);plt.close(fig);files.append(p)
  drift=np.sum(V[:,None]*delta,axis=0)/V.sum();need(a.tobytes()==original and all(stat(e['path'])==e for e in before),'Original state/helper/input changed')
  result.update(passed=True,analysis_completed=True,selected_state=common,original_header=[6805,22,90],actual_native_records_examined=1,soil_IDs=5000,proposal_count=1,proposal_weight='V0J',ShiftCoef=shift.COEF,dt_s=shift.DT,h_m=shift.H,freeze_radius_m=shift.R,component_cap_m=shift.CAP,eligible_count=int(eligible.sum()),original_fields_and_coordinates_unchanged=True,transport_applied=False,physical_volume_update_applied=False,FS23_displacement_max_m=float(np.linalg.norm(delta[q['surface']],axis=1).max()),all_soil_weighted_displacement_drift_xz_m=drift.tolist(),eligible_div_delta=shift.qstats(div[eligible]),eligible_det_map_minus1=shift.qstats(det[eligible]),eligible_linear_geometric_area_defect_m2=float(np.dot(V[eligible],div[eligible])),eligible_determinant_area_defect_m2=float(np.dot(V[eligible],det[eligible])),geometric_measure='2D xz area, volume per unit out-of-plane thickness',geometric_defects_are_subset_only_not_global_conservation=True,constant_gradient_max=float(constant[eligible].max()),affine_gradient_max_error=float(affine[eligible].max()),affine_float_condition_scale_max=float((32*np.finfo(np.float32).eps*np.maximum(condition[eligible],1.)).max()),affine_error_within_reported_roundoff_scale=bool(np.all(affine[eligible]<=32*np.finfo(np.float32).eps*np.maximum(condition[eligible],1.))),same_full_fluid_stencil_and_C_for_all_fields=True,C_reconstructed_not_native_export=True,GPU_float_replay_claimed=False,kappa_and_P0_Taylor_terms_are_interpretation_risks_not_updates=True,unchanged_J_ledger_is_not_conservation_proof=True,physical_shift_admitted=False,visual_QA_pending=True)
 except Exception as error:result['first_failure']=str(error)
 result.update(consumed=before,consumed_stats_unchanged=bool(before) and all(stat(e['path'])==e for e in before),files=[stat(p) for p in files])
 with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
 print(json.dumps(dict(passed=result['passed'],check=str(CHECK),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
