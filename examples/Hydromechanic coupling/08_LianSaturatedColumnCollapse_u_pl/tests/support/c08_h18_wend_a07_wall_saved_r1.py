"""Wall803 geometry/J replay at sealed AS.7 saved34 states, never its unsaved rejection."""
import argparse,json,xml.etree.ElementTree as ET
from pathlib import Path
import c08_h18_wend_options_review_r1 as options
import c08_h18_wend_partial_review_r2 as review

old,replay=review.old,review.previous
np,T,need,path,stat,read,bind=old.np,old.T,old.need,old.path,old.stat,old.read,old.bind
TAG='c08_h18_wend_a07_wall_saved_r1'
CHECK=T/'logs/c08_h18_wend_a07_partial_review_r2.check.json'
NAMES=('J','p_normal_head_removed','vx','vy','vz','sigma_xx','sigma_yy','sigma_zz','sigma_xy','sigma_xz','sigma_yz')

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args()
    need(args.execution_authorized,'Root must fully read before one unique saved-state offline audit')
    prefix=T/'figures'/TAG;check=T/'logs'/(TAG+'.check.json');need(not check.exists() and not list(prefix.parent.glob(TAG+'*')),'Existing complete or partial audit output is protected')
    consumed=[stat(p) for p in (__file__,T/'notes'/(TAG+'.md'),options.__file__,review.__file__,replay.__file__,old.__file__)];files=[]
    result=dict(stage=TAG,analysis_complete=False,receiver_complete=False,whole_run_passed=False,physical_acceptance=False,winner_selected=False,consumed=consumed)
    try:
        prior=read(CHECK);need(prior['analysis_complete'] and prior['saved_prefix_native_qualified'] and prior['actual_saved_records']==34 and not prior['whole_run_passed'] and not prior['unsaved_failure_state_reconstructed'],'Only the already qualified actual AS.7 saved34 prefix is admitted')
        option=options.load_option(dict(tag=review.RUN,kind='partial',review_check=str(CHECK),history_csv=str(T/'figures/c08_h18_wend_a07_partial_review_r2_history.csv'),native_dir=str(T/'outputs/c08_h18_wend_psi0_a07_w09_r1/native_partial_r2')),consumed)
        bundle=option['bundle'];failure=prior['reported_failure'];need(failure['native_id']==803 and failure['stage']==0 and bundle['count']==34,'Only the reported wall803 and actual34 saved states are supported')
        manifest=read(prior['consumed'][0]['path']);xml=ET.parse(path(manifest['case']['input_xml'])).getroot();constants=xml.find('execution/constants');hyd=xml.find('execution/special/hydromechanics')
        h=old.f32(constants.find('h').get('value'));gz=old.f32(constants.find('gravity').get('z'));porosity=old.f32(hyd.find('Porosity').get('value'));rhow=float(hyd.find('PoreWaterRho').get('value'))
        need(h==old.f32(.072) and float(constants.find('rhop0').get('value'))==2072.5 and old.f32(constants.find('massfluid').get('value'))==old.f32(3.316) and gz==old.f32(-9.81) and porosity==old.f32(.35) and rhow==1000,'Constants must match the inherited verified fit/kernel/volume/head formula')
        solid=1-porosity;ks=np.float32(2*h);ks2=np.float32(ks*ks);threshold=float(failure['MdbcThreshold']);bn=np.array(failure['normal'])[[0,2]]
        rows=[];donors=[];tests=[];cc=1.+.125*np.arange(11);bx=.10+.013*np.arange(11);bz=-.05+.007*np.arange(11)
        for part in range(bundle['count']):
            x=old.read22(bundle,part);ids=x['Idp'][:,0];wall=np.flatnonzero(ids==803);need(len(wall)==1 and np.array_equal(x['Posd'][wall[0]],np.array(failure['B'])),'Original fixed wall803 B must equal the reported coordinate')
            B=x['Posd'][wall[0]][[0,2]];G=B+bn;soil=ids>=2060;sid=ids[soil];pos=x['Posd'][soil][:,[0,2]];J=x['PoroVolumeRatio'][soil,0];sk=x['SigmaState_kk'][soil];si=x['SigmaState_ij'][soil];vel=x['Vel'][soil].astype(float);pw=x['PorePress'][soil,0].astype(float)
            fields=np.column_stack((J,pw-rhow*gz*pos[:,1],vel,sk,si[:,0],si[:,2],si[:,1]));primary=replay.fit(pos,J,fields,G,G,h,threshold);fits=[('GP',G,primary)]
            nearest=primary['nearest']
            if primary['invalid_source_J']==0 and not primary['geometry_pass'] and nearest is not None and np.any(pos[nearest]!=G) and np.isfinite(fields[nearest]).all():
                centre=pos[nearest];fits.append(('nearest_retry',centre,replay.fit(pos,J,fields,centre,G,h,threshold)))
            delta=B-pos;double_rr=np.sum(delta*delta,axis=1);fd=np.float32(delta);float_rr=np.float32(fd[:,0]*fd[:,0]+fd[:,1]*fd[:,1]);lo=float(np.float32(1e-18));double_support=int(np.count_nonzero((double_rr<=float(ks2))&(double_rr>=lo)));float_support=int(np.count_nonzero((float_rr<=ks2)&(float_rr>=np.float32(lo))))
            clock=bundle['clocks'][part];common=dict(part=part,completed_step=int(clock['completed_step']),time_s=float(x['time']),tau_s=float(x['time'])-bundle['done']['source_actual_time_s'],wall_id=803,B_x_m=float(B[0]),B_z_m=float(B[1]),GP_x_m=float(G[0]),GP_z_m=float(G[1]),B_double_support=double_support,B_direct_float_shadow_support=float_support,saved_geometry_retry_taken=len(fits)>1,native_saved_wall_J=float(x['PoroVolumeRatio'][wall[0],0]))
            for method,centre,fitted in fits:
                dr=centre-pos;rr2=np.float32(np.sum(dr*dr,axis=1));at=np.flatnonzero(rr2<=ks2);need(len(at)==fitted['sources'],'Pure fit and donor-table support must agree')
                wab,_=replay.kernel(rr2[at],h,np.float32(.557/(h*h)),np.float32(-2.7852/(h*h*h)));weights=wab*(float(np.float32(3.316))/2072.5*J[at])
                value=fitted['value'];valid_donors=fitted['invalid_source_J']==0;finite=value is not None and np.isfinite(value).all();jvalue=float(value[0]) if valid_donors and finite else None
                jlo=float(J[at].min()) if len(at) else None;jhi=float(J[at].max()) if len(at) else None
                reason='donor_J_invalid' if not valid_donors else 'geometry_rejected' if not fitted['geometry_pass'] else 'fitted_nonfinite' if not finite else 'fitted_J_outside_saturated_domain' if jvalue<=solid else 'saved_J_geometry_admissible'
                row=dict(**common,method=method,centre_x_m=float(centre[0]),centre_z_m=float(centre[1]),centre_to_original_GP_over_h=float(np.linalg.norm(centre-G)/h),mirror_sources=fitted['sources'],positive_weight_sources=fitted['positive_weight_sources'],invalid_source_J=fitted['invalid_source_J'],donor_J_min=jlo,donor_J_max=jhi,sumwab=fitted['sumwab'],submerged=fitted['submerged'],active_mirror=fitted['active_mirror'],determinant=fitted['determinant'],abs_determinant=float(abs(fitted['determinant'])),abs_det_margin=fitted['abs_det_minus_original_limit'],raw_moment_condition2=fitted['raw_moment_condition2'],geometry_pass=fitted['geometry_pass'],nearest_ID=None if fitted['nearest'] is None else int(sid[fitted['nearest']]),nearest_ties=fitted['nearest_ties'],all11_fitted_values_finite=finite,J_at_original_GP=jvalue,J_minus_solid0=None if jvalue is None else jvalue-solid,J_outside_donor_range=None if jvalue is None or jlo is None else bool(jvalue<jlo or jvalue>jhi),descriptive_saved_branch=reason)
                rows.append(row)
                for index,weight in zip(at,weights):donors.append(dict(part=part,completed_step=common['completed_step'],time_s=common['time_s'],tau_s=common['tau_s'],method=method,native_id=int(sid[index]),x_m=float(pos[index,0]),z_m=float(pos[index,1]),J=float(J[index]),distance2_float_m2=float(rr2[index]),W_times_V=float(weight)))
                for kind in ('constant','affine'):
                    eligible=valid_donors and fitted['geometry_pass'];manufactured=np.broadcast_to(cc,(len(pos),11)).copy()
                    if kind=='affine':manufactured+=(pos[:,0]-G[0])[:,None]*bx+(pos[:,1]-G[1])[:,None]*bz
                    trial=replay.fit(pos,J,manufactured,centre,G,h,threshold) if eligible else None
                    if trial is not None:need(trial['determinant']==fitted['determinant'] and trial['geometry_pass'],'Manufactured fields must preserve original native-J weighted geometry exactly')
                    for component,name in enumerate(NAMES):
                        got=None if trial is None else float(trial['value'][component]);error=None if got is None else got-float(cc[component])
                        tests.append(dict(part=part,completed_step=common['completed_step'],time_s=common['time_s'],tau_s=common['tau_s'],method=method,test=kind,component=name,tested=eligible,expected_at_original_GP=float(cc[component]),recovered_at_original_GP=got,signed_error=error,absolute_error=None if error is None else abs(error)))
        for suffix,records in (('history',rows),('donors',donors),('consistency',tests)):
            if records:dest=Path(str(prefix)+'_'+suffix+'.csv');old.write_csv(dest,records);files.append(dest)
        fig,axes=old.plt.subplots(2,2,figsize=(12,8),layout='constrained')
        for method in ('GP','nearest_retry'):
            rr=[r for r in rows if r['method']==method]
            for ax,key,title in ((axes[0,0],'mirror_sources','Real mirror donor count'),(axes[0,1],'abs_determinant','Absolute moment determinant'),(axes[1,0],'J_minus_solid0','J at original GP minus original solid0')):
                ax.plot([r['tau_s'] for r in rr],[r[key] for r in rr],label=method);ax.set(title=title,xlabel='Actual saved tau [s]')
        axes[0,1].axhline(.001,color='k',ls='--',lw=.8);axes[1,0].axhline(0,color='k',ls='--',lw=.8)
        for kind in ('constant','affine'):
            points=[(r['tau_s'],r['absolute_error']) for r in tests if r['test']==kind and r['tested']];axes[1,1].scatter([p[0] for p in points],[p[1] for p in points],s=5,label=kind)
        axes[1,1].set(title='Manufactured component errors (separate test)',xlabel='Actual saved tau [s]')
        for ax in axes.flat:ax.grid(alpha=.2);ax.legend(fontsize=8)
        fig.suptitle('AS .7 saved34: wall803 original GP / existing nearest retry only\nNo unsaved rejection reconstruction or new geometry threshold',fontsize=11);dest=Path(str(prefix)+'.png');fig.savefig(dest,dpi=170,bbox_inches='tight',pad_inches=.12);old.plt.close(fig);files.append(dest)
        need(all(stat(entry['path'])==entry for entry in consumed),'Sealed review, export, source context or pure helpers changed')
        errors={kind:[r['absolute_error'] for r in tests if r['test']==kind and r['tested']] for kind in ('constant','affine')}
        result.update(analysis_complete=True,saved_prefix_native_qualified=True,actual_saved_records=34,wall_id=803,reported_unsaved_failure=failure,source_actual_time_s=bundle['done']['source_actual_time_s'],first_saved_time_s=float(bundle['clocks'][0]['time_s']),last_saved_time_s=float(bundle['clocks'][-1]['time_s']),actual_float_h=h,actual_float_KernelSize2=float(ks2),original_abs_det_limit=.001,original_solid0=solid,original_MdbcThreshold=threshold,primary_geometry_rejected_saved_states=sum(r['method']=='GP' and not r['geometry_pass'] for r in rows),saved_retry_states=sum(r['method']=='nearest_retry' for r in rows),invalid_donor_J_fit_records=sum(r['invalid_source_J']>0 for r in rows),nonpositive_J_margin_fit_records=sum(r['J_minus_solid0'] is not None and r['J_minus_solid0']<=0 for r in rows),manufactured_max_absolute_errors={kind:max(v) if v else None for kind,v in errors.items()},manufactured_tests_are_not_native_field_accuracy=True,no_error_or_condition_gate_added=True,no_centroid_candidate=True,unsaved_failure_state_reconstructed=False,CUDA_cell_traversal_PosCell_FMA_reproduced=False,B_participation_counts_are_shadows_not_exact_GPU_union=True,nearest_tie_order_is_saved_ID_order_not_GPU_visit_order=True,native_wall_value_not_same_stage_fit_equality_proof=True,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,SHA_scans=0,consumed_stats_unchanged=True,visual_QA_pending=True,files=[stat(p) for p in files])
    except Exception as error:
        result.update(first_failure=str(error),partial_outputs_preserved=True);raise
    finally:
        with check.open('x',encoding='utf-8') as handle:json.dump(result,handle,indent=2,allow_nan=False);handle.write('\n')

if __name__=='__main__':main()
