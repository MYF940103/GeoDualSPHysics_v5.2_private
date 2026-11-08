"""Local material-bond affine fits from six sealed records, not a tensile-cause test."""
import argparse,json,struct
from pathlib import Path
import upl_c08_clustering_r1 as old
import upl_c08_wall_geometry_r1 as kernel
np,c,T=old.np,old.c,old.T
TAG='upl_c08_affine_neighbor_r1';PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json')

def record(f,g,part):
    f.seek(12+part*g['dtype'].itemsize);raw=f.read(g['dtype'].itemsize);c.need(len(raw)==g['dtype'].itemsize,'Short selected record');a=np.frombuffer(raw,dtype=g['dtype'],count=1)[0];context=c.inspect(a,g,part);return a,context

def reference(a):
    soil=a['Idp'][:,0]>=2060;X=a['Posd'][soil][:,[0,2]].copy();V=a['PoroCurrentVolume'][soil,0];tree=old.cKDTree(X);fits=[]
    for i,near in enumerate(tree.query_ball_point(X,old.R,workers=1)):
        js=np.asarray(sorted(j for j in near if j!=i and float((X[j]-X[i])@(X[j]-X[i]))<old.R**2),dtype=int);d=X[js]-X[i];w=np.asarray([kernel.cubic(float(v@v))[0]*V[j] for j,v in zip(js,d)]);M=(d.T*w)@d;s=np.linalg.svd(M,compute_uv=False);tol=2*np.finfo(float).eps*s[0];rank=int(np.count_nonzero(s>tol));condition=float(s[0]/s[1]) if s[1]>0 else float('inf');inverse=None;status='rank_deficient'
        if rank==2:
            try:inverse=np.linalg.inv(M);status='rank2' if np.isfinite(inverse).all() else 'nonfinite_inverse'
            except np.linalg.LinAlgError:status='inverse_failed'
        effective=float(w.sum()**2/(w@w)) if len(w) and w@w>0 else 0.;fits.append((js,d,w,inverse,rank,condition,effective,status))
    return X,a['PoroVolumeRatio'][soil,0].copy(),fits

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();c.need(a.execution_authorized,'Root full-read before local affine diagnostic');c.need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial affine outputs protected')
    proof=c.read(c.CHECK);c.need(proof['passed'] and proof['clock_and_steps_exact'],'Sealed same-source parameter comparison required');groups=[old.formal(),c.load(c.SPECS[1])];groups[0]['parts']=(65,119,299);groups[1].update(frames=66,parts=(65,));c.need(groups[0]['run']['source_pre_file']==groups[1]['run']['source_pre_file'],'Different actual PRE source')
    c.need(2*float(kernel.H)==old.R,'Reference Cubic support differs');before=[c.stat(__file__),c.stat(T/'notes'/(TAG+'.md')),c.stat(old.__file__),c.stat(kernel.__file__),c.stat(c.CHECK),c.bind(next(e for e in proof['consumed'] if Path(e['path']).samefile(c.__file__)))]+[e for g in groups for e in g['before']];rows=[];summaries=[]
    for g in groups:
        with (g['native']/'typed22.bin').open('rb') as f:
            c.need(struct.unpack('<III',f.read(12))==(6805,22,g['frames']),'Original300/66 header required');ref,refclock=record(f,g,0);X,Jref,fits=reference(ref)
            for part in g['parts']:
                state,clock=record(f,g,part);soil=state['Idp'][:,0]>=2060;x=state['Posd'][soil][:,[0,2]];values={k:state[k][soil,0] for k in ('PoroVolumeRatio','Kplastic','PorePress','PoroPorosity','PoroMixtureDensity')};dist,index=old.cKDTree(x).query(x,k=2,workers=1);pick=np.where(index[:,0]==np.arange(5000),1,0);near=index[np.arange(5000),pick];nn=dist[np.arange(5000),pick];current=[]
                for i,(js,d,w,inverse,rank,condition,effective,status) in enumerate(fits):
                    F=None;det=None;residual=None;ratio=None;member=bool(np.any(js==near[i]));predicted=None
                    if status=='rank2':
                        dx=x[js]-x[i];F=((dx.T*w)@d)@inverse
                        if np.isfinite(F).all():
                            det=float(np.linalg.det(F));error=dx-d@F.T;residual=float(np.sqrt(np.sum(w*np.sum(error*error,axis=1))/w.sum())/old.DP)
                            if member:predicted=float(np.linalg.norm(F@(X[near[i]]-X[i])));ratio=float(nn[i]/predicted) if predicted>0 else None
                        else:status='nonfinite_fit';F=None
                    r=dict(group=g['label'],epsilon=g['epsilon'],part=part,time_s=clock[0],tau_s=clock[1],completed_step=clock[2],reference_time_s=refclock[0],reference_tau_s=refclock[1],reference_completed_step=refclock[2],native_ID=2060+i,reference_neighbors=len(js),reference_positive_weights=int(np.count_nonzero(w>0)),reference_effective_weight_count=effective,reference_moment_rank=rank,reference_moment_condition=condition,fit_status=status,Fxx=float(F[0,0]) if F is not None else None,Fxz=float(F[0,1]) if F is not None else None,Fzx=float(F[1,0]) if F is not None else None,Fzz=float(F[1,1]) if F is not None else None,detF=det,J_over_Jref=float(values['PoroVolumeRatio'][i]/Jref[i]),nonaffine_weighted_RMS_over_dp=residual,current_NN_native_ID=int(2060+near[i]),current_NN_over_dp=float(nn[i]/old.DP),current_NN_is_reference_neighbor=member,current_NN_new_neighbor=not member,predicted_NN_length_m=predicted,NN_over_predicted_affine_length=ratio,reference_neighbor_zero_prediction=bool(member and predicted==0),kappa=float(values['Kplastic'][i]),p_Pa=float(values['PorePress'][i]),J=float(values['PoroVolumeRatio'][i]),n=float(values['PoroPorosity'][i]),rho_native_kg_m3=float(values['PoroMixtureDensity'][i]));rows.append(r);current.append(r)
                for cohort in ('all_soil','kappa_ge_0p1f','kappa_lt_0p1f'):
                    rr=[r for r in current if cohort=='all_soil' or (r['kappa']>=old.KAPPA)==(cohort=='kappa_ge_0p1f')];s=dict(group=g['label'],epsilon=g['epsilon'],part=part,tau_s=clock[1],cohort=cohort,soil_count=len(rr),invalid_fit_count=sum(r['fit_status']!='rank2' for r in rr),infinite_condition_count=sum(not np.isfinite(r['reference_moment_condition']) for r in rr),new_neighbor_count=sum(r['current_NN_new_neighbor'] for r in rr),zero_prediction_count=sum(r['reference_neighbor_zero_prediction'] for r in rr),negative_detF_count=sum(r['detF'] is not None and r['detF']<0 for r in rr))
                    for key in ('reference_moment_condition','reference_effective_weight_count','detF','J_over_Jref','nonaffine_weighted_RMS_over_dp','current_NN_over_dp','NN_over_predicted_affine_length'):
                        values=np.asarray([r[key] if r[key] is not None else np.nan for r in rr],dtype=float);s[key+'_finite_count']=int(np.isfinite(values).sum());s.update({key+'_'+q:v for q,v in zip(('min','q05','median','q95','max'),old.quant(values))})
                    summaries.append(s)
    c.need(len(rows)==20000 and len(summaries)==12,'Four target states must retain every original5000 ID');files=[]
    for name,data in (('points',rows),('summary',summaries)):
        path=Path(str(PREFIX)+'_'+name+'.csv');c.write(path,data);files.append(c.stat(path))
    c.need(all(c.stat(e['path'])==e for e in before),'Sealed source/helper changed');result=dict(stage=TAG,passed=True,analysis_completed=True,typed_records_read=6,target_states=4,retained_material_rows=20000,reference='Each group own first saved tau~.01; not PRE/t0',reference_radius_m=old.R,weights='Cubic W0 times native reference V0J',fit_rank_tolerance='2eps*largest moment singular value; numerical rank description only',invalid_points_retained=True,no_condition_physical_gate=True,NN_new_neighbors_not_given_affine_ratio=True,native_rho_p_n_J_fields_not_remapped=True,large_shear_or_physical_slip_not_excluded=True,nonaffinity_not_tensile_causation=True,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0,consumed=before,files=files)
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('AFFINE_NEIGHBOR_DIAGNOSTIC_READY',CHECK,flush=True)

if __name__=='__main__':main()
