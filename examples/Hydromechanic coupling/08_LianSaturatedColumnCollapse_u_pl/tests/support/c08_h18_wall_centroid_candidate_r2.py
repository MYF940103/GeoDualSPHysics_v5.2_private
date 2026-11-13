"""One offline nearest-donor W*V centroid candidate at two final saved wall stencils."""
import argparse,json
from pathlib import Path
import c08_h18_wend_options_review_r1 as options
import c08_h18_wend_partial_review_r1 as replay

old=replay.old
np,T,need,stat,read=old.np,old.T,old.need,old.stat,old.read
TAG='c08_h18_wall_centroid_candidate_r2'
NAMES=('J','p_head_removed','vx','vy','vz','sigma_xx','sigma_yy','sigma_zz','sigma_xy','sigma_xz','sigma_yz')
CASES=(('a03',893,'c08_h18_wend_a03_partial_review_r1','native_partial_r1'),('a07',803,'c08_h18_wend_a07_partial_review_r2','native_partial_r2'))

def support(pos,J,centre,h):
    dr=centre-pos;rr2=np.float32(np.sum(dr*dr,axis=1));ks=np.float32(2*h);at=np.flatnonzero(rr2<=np.float32(ks*ks))
    wab,_=replay.kernel(rr2[at],h,np.float32(.557/(h*h)),np.float32(-2.7852/(h*h*h)))
    return at,wab*(float(np.float32(3.316))/2072.5*J[at])

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args()
    need(args.execution_authorized,'Root must fully read before one unique offline candidate study')
    prefix=T/'figures'/TAG;check=T/'logs'/(TAG+'.check.json');need(not check.exists() and not list(prefix.parent.glob(TAG+'*')),'Existing complete or partial candidate artifact is protected')
    consumed=[stat(p) for p in (__file__,T/'notes'/(TAG+'.md'),options.__file__,replay.__file__,old.__file__)];files=[]
    result=dict(stage=TAG,analysis_complete=False,physical_acceptance=False,winner_selected=False,candidate_only=True,implemented_in_solver=False,consumed=consumed)
    try:
        rows=[];tests=[];donors=[];contexts=[];h=old.f32(.072);solid=1-old.f32(.35);cc=1.+.125*np.arange(11);bx=.10+.013*np.arange(11);bz=-.05+.007*np.arange(11)
        for label,wall,review_tag,native in CASES:
            tag='c08_h18_wend_psi0_'+label+'_w09_r1';qpath=T/'logs'/(review_tag+'.check.json');prior=read(qpath)
            option=options.load_option(dict(tag=tag,kind='partial',review_check=str(qpath),history_csv=str(T/'figures'/(review_tag+'_history.csv')),native_dir=str(T/'outputs'/tag/native)),consumed)
            contexts.append(option['context']);bundle=option['bundle'];part=bundle['count']-1;x=old.read22(bundle,part);failure=prior['reported_failure'];need(failure['native_id']==wall and bundle['done']['H']==h,'Expected original last-saved wall/H identity differs')
            ids=x['Idp'][:,0];wi=np.flatnonzero(ids==wall);need(len(wi)==1 and np.array_equal(x['Posd'][wi[0]],np.array(failure['B'])),'Original fixed B differs from its reported coordinate')
            B=x['Posd'][wi[0]][[0,2]];G=B+np.array(failure['normal'])[[0,2]];threshold=float(failure['MdbcThreshold']);soil=ids>=2060;sid=ids[soil];pos=x['Posd'][soil][:,[0,2]];J=x['PoroVolumeRatio'][soil,0];si=x['SigmaState_ij'][soil]
            fields=np.column_stack((J,x['PorePress'][soil,0].astype(float)-1000*old.f32(-9.81)*pos[:,1],x['Vel'][soil].astype(float),x['SigmaState_kk'][soil],si[:,0],si[:,2],si[:,1]))
            primary=replay.fit(pos,J,fields,G,G,h,threshold);need(primary['invalid_source_J']==0 and not primary['geometry_pass'] and primary['nearest'] is not None,'Study requires the known valid-donor primary geometry rejection and existing nearest retry')
            near=pos[primary['nearest']];need(np.any(near!=G) and np.isfinite(fields[primary['nearest']]).all(),'Original nearest retry requires a finite source and nonzero shift');nearest=replay.fit(pos,J,fields,near,G,h,threshold);seed_at,seed_weights=support(pos,J,near,h)
            positive=seed_weights>0;need(nearest['invalid_source_J']==0 and np.isfinite(seed_weights).all() and positive.any(),'Positive valid native-J nearest-donor weights required')
            centre=np.sum(pos[seed_at[positive]]*seed_weights[positive,None],axis=0)/seed_weights[positive].sum()
            candidate=replay.fit(pos,J,fields,centre,G,h,threshold);methods=(('GP',G,primary),('nearest',near,nearest),('centroid_candidate',centre,candidate));near_ids=set(int(v) for v in sid[seed_at])
            for method,C,fit in methods:
                at,weights=support(pos,J,C,h);valid=fit['invalid_source_J']==0;finite=fit['value'] is not None and np.isfinite(fit['value']).all();value=float(fit['value'][0]) if valid and finite else None;selected=set(int(v) for v in sid[at])
                common=dict(case=label,solver_tag=tag,wall_id=wall,part=part,completed_step=int(bundle['clocks'][part]['completed_step']),time_s=float(x['time']),tau_s=float(x['time'])-bundle['done']['source_actual_time_s'],method=method)
                rows.append(dict(**common,B_x_m=float(B[0]),B_z_m=float(B[1]),original_GP_x_m=float(G[0]),original_GP_z_m=float(G[1]),fit_centre_x_m=float(C[0]),fit_centre_z_m=float(C[1]),centre_to_original_GP_over_h=float(np.linalg.norm(C-G)/h),centre_to_nearest_over_h=float(np.linalg.norm(C-near)/h),sources=fit['sources'],positive_weight_sources=fit['positive_weight_sources'],invalid_donor_J=fit['invalid_source_J'],sumwab=fit['sumwab'],submerged=fit['submerged'],abs_determinant=float(abs(fit['determinant'])),abs_det_margin=fit['abs_det_minus_original_limit'],raw_moment_condition2=fit['raw_moment_condition2'],geometry_pass=fit['geometry_pass'],J_at_original_GP=value,J_minus_solid0=None if value is None else value-solid,donor_J_min=None if not len(at) else float(J[at].min()),donor_J_max=None if not len(at) else float(J[at].max()),J_and_geometry_admissible=bool(fit['geometry_pass'] and valid and finite and value>solid),added_sources_vs_nearest=len(selected-near_ids),lost_sources_vs_nearest=len(near_ids-selected),nearest_ties=fit['nearest_ties'],centroid_seed_positive_sources=int(positive.sum())))
                seed_map={int(sid[i]):float(w) for i,w in zip(seed_at,seed_weights)}
                for i,w in zip(at,weights):donors.append(dict(**common,native_id=int(sid[i]),x_m=float(pos[i,0]),z_m=float(pos[i,1]),J=float(J[i]),W_times_V=float(w),in_nearest_seed_set=int(sid[i]) in near_ids,nearest_seed_W_times_V=seed_map.get(int(sid[i]))))
                for kind in ('constant','affine'):
                    eligible=valid and fit['geometry_pass'];manufactured=np.broadcast_to(cc,(len(pos),11)).copy()
                    if kind=='affine':manufactured+=(pos[:,0]-G[0])[:,None]*bx+(pos[:,1]-G[1])[:,None]*bz
                    trial=replay.fit(pos,J,manufactured,C,G,h,threshold) if eligible else None
                    if trial is not None:need(trial['determinant']==fit['determinant'] and trial['geometry_pass'],'Manufactured test must retain identical original native-J geometry')
                    for k,name in enumerate(NAMES):
                        got=None if trial is None else float(trial['value'][k]);error=None if got is None else got-float(cc[k]);tests.append(dict(**common,test=kind,component=name,tested=eligible,expected_at_original_GP=float(cc[k]),recovered_at_original_GP=got,absolute_error=None if error is None else abs(error)))
        need(contexts[0]==contexts[1],'Both saved stencils must share the same original source/PRE/material/program/plan context')
        for suffix,records in (('comparison',rows),('donors',donors),('consistency',tests)):
            dest=Path(str(prefix)+'_'+suffix+'.csv');old.write_csv(dest,records);files.append(dest)
        fig,axes=old.plt.subplots(2,2,figsize=(12,8),layout='constrained');order={'GP':0,'nearest':1,'centroid_candidate':2}
        for label,wall,_,_ in CASES:
            rr=[r for r in rows if r['case']==label];xx=[order[r['method']] for r in rr];legend=label+' wall'+str(wall)
            for ax,key,title in ((axes[0,0],'abs_determinant','Absolute moment determinant'),(axes[0,1],'J_minus_solid0','Native J at unchanged GP minus solid0'),(axes[1,0],'raw_moment_condition2','Raw moment condition2 (descriptive)')):
                ax.plot(xx,[r[key] for r in rr],marker='o',label=legend);ax.set(title=title,xticks=[0,1,2],xticklabels=['GP','nearest','centroid candidate'])
        axes[0,0].axhline(.001,color='k',ls='--',lw=.8);axes[0,1].axhline(0,color='k',ls='--',lw=.8)
        for label,wall,_,_ in CASES:
            tt=[r for r in tests if r['case']==label and r['tested']];axes[1,1].scatter([order[r['method']] for r in tt],[r['absolute_error'] for r in tt],s=8,label=label+' constant/affine')
        axes[1,1].set(title='Manufactured component errors (separate test)',xticks=[0,1,2],xticklabels=['GP','nearest','centroid candidate'])
        for ax in axes.flat:ax.grid(alpha=.2);ax.legend(fontsize=8)
        fig.suptitle('Two last-saved wall stencils: one nearest-donor positive W*V centroid candidate\nOriginal target/gates retained; no unsaved reproduction or solver implementation',fontsize=11);dest=Path(str(prefix)+'.png');fig.savefig(dest,dpi=170,bbox_inches='tight',pad_inches=.12);old.plt.close(fig);files.append(dest)
        need(all(stat(entry['path'])==entry for entry in consumed),'Sealed case review/export or pure helper changed')
        result.update(analysis_complete=True,actual_saved_stencils=2,source_context=contexts[0],comparisons=rows,original_abs_det_limit=.001,original_solid0=solid,centroid_seed='existing nearest donor set; positive original W*V',candidate_neighborhood_recomputed_with_original_kernel=True,original_GP_evaluation_target_unchanged=True,manufactured_tests_are_not_native_accuracy=True,no_error_or_condition_gate_added=True,no_threshold_or_domain_relaxation=True,positive_centroid_weights_do_not_make_MLS_weights_positive=True,conservation_or_stability_proven=False,unsaved_failure_state_reconstructed=False,CUDA_cell_traversal_PosCell_FMA_reproduced=False,no_automatic_solver_or_parameter_choice=True,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,SHA_scans=0,consumed_stats_unchanged=True,visual_QA_pending=True,files=[stat(p) for p in files])
    except Exception as error:
        result.update(first_failure=str(error),partial_outputs_preserved=True);raise
    finally:
        with check.open('x',encoding='utf-8') as handle:json.dump(result,handle,indent=2,allow_nan=False);handle.write('\n')

if __name__=='__main__':main()
