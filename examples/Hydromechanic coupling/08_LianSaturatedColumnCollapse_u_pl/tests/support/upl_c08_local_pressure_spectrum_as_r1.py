"""Add only the frozen real AS pressure derivative to sealed local raw matrices."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,csv,json,math
from pathlib import Path
import numpy as np
import upl_c08_local_pressure_spectrum_r1 as base

old,p,ace=base.old,base.p,base.ace
need,read,stat=base.need,base.read,base.stat
T=base.T;TAG='upl_c08_local_pressure_spectrum_as_r1';PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json')

def as_increment(cloud,art,i):
    # Reuse the same complete Darcy-to-Ace map with AS-only B. The direct row
    # returned internally by probe is discarded; no saved baseline is replaced.
    rows,unused,description=ace.probe(cloud,art,i)
    return ace.combine(rows['via_divAce'],rows['via_FS_Ace_lx'],rows['via_chain_Ace']),description

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read before one offline AS matrix extension')
    need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial AS spectrum protected')
    proof=read(base.CHECK);need(proof['passed'] and proof['analysis_completed'] and proof['requested_saved_state_blocks']==proof['evaluated_saved_state_blocks']==8 and proof['not_evaluated_WallStencil_blocks']==0 and not proof['ASJac_included'] and proof['all_original_WallStencil_guards_kept'],'Sealed eight-block raw analysis required')
    previous=T/'logs/upl_c08_r5_pressure_probe_r2.check.json';oldproof=read(previous);need(oldproof['passed'] and oldproof['AS1_pressure_dependent_spectral_real_derivative_included'],'Passed existing real-spectral AS provider required')
    data,done,clocks,before=old.load();before.extend(stat(q) for q in (Path(__file__),T/'notes'/(TAG+'.md'),base.CHECK,previous))
    before.append(old.bind(next(e for e in proof['consumed'] if Path(e['path']).samefile(base.__file__))))
    raw_summary=Path(str(base.PREFIX)+'_summary.csv');before.append(old.bind(next(e for e in proof['files'] if Path(e['path']).samefile(raw_summary))))
    with raw_summary.open(encoding='utf-8',newline='') as f:baseline={(int(r['part']),r['patch'],r['variant'],r['variable_view']):r for r in csv.DictReader(f)}
    summary=[];modes=[];spectra=[];files=[];skips=[];matrix_count=0
    for part in base.PARTS:
        frame=data[part];cloud=p.Cloud(frame);time=float(frame['time']);tau=time-done['source_actual_time_s']
        for label,focus in base.FOCI:
            print('LOCAL_AS_PRESSURE_BLOCK',part,label,flush=True)
            raw_path=Path(str(base.PREFIX)+'_part'+str(part).zfill(3)+'_'+label+'.npz');before.append(old.bind(next(e for e in proof['files'] if Path(e['path']).samefile(raw_path))))
            with np.load(raw_path,allow_pickle=False) as q:
                ids=q['target_native_IDs'].copy();pressure_ids=q['pressure_native_IDs'].copy();weights=q['storage_W_nV_over_Kw'].copy();rawR=q['full_direct_plus_rawAce_rows'].copy();rawA=q['A_direct_plus_rawAce'].copy();directA=q['A_direct'].copy()
                need(float(q['time_s'])==time and float(q['tau_s'])==tau and int(q['completed_step'])==int(clocks[part]['completed_step']),'Sealed matrix actual clock differs')
                targets=np.asarray([base.at(cloud,int(identity)) for identity in ids]);need(len(ids)==proof['patch_sizes'][label] and np.all(np.diff(ids.astype(np.int64))>0) and np.array_equal(q['target_FSType'],cloud.fs[targets]) and np.array_equal(q['target_p_Pa'],cloud.p[targets]) and np.array_equal(q['target_xz_m'],cloud.x[targets]),'Original fixed material patch/state differs')
            pressure_nodes=np.asarray([base.at(cloud,int(identity)) for identity in pressure_ids]);columns={int(j):k for k,j in enumerate(pressure_nodes)};inside=np.asarray([columns[int(i)] for i in targets])
            need(rawR.shape==(len(targets),len(columns)) and rawA.shape==directA.shape==(len(targets),len(targets)) and np.array_equal(rawR[:,inside],rawA) and np.array_equal(weights,cloud.n[targets]*cloud.V[targets]/p.KW),'Sealed raw matrices/storage weights inconsistent')
            context=dict(part=part,time_s=time,tau_s=tau,completed_step=int(clocks[part]['completed_step']),patch=label,focus_IDs=';'.join(map(str,focus)),all_patch_variables=len(ids))
            raw=ace.Mechanical(cloud,frame);art=old.SpectralAS(cloud,frame,raw);increments=[];descriptions=[]
            try:
                for i in targets:
                    row,desc=as_increment(cloud,art,int(i));need(set(row)<=set(columns),'AS derivative escaped the original complete raw two-hop pressure column set');increments.append(row);descriptions.append(desc)
            except p.WallStencil as error:
                skips.append(dict(**context,status='not_evaluated_WallStencil',failed_row_native_ID=int(cloud.ids[i]),reason=str(error)));continue
            AS=base.matrix_rows(increments,pressure_nodes);augR=rawR+AS;augA=rawA+AS[:,inside];need(np.isfinite(augR).all() and np.isfinite(augA).all(),'Nonfinite raw+AS frozen matrix')
            nodes=sorted(art.used);need(nodes,'Missing AS spectral nodes');tensor={j:art.tensors(j) for j in nodes};zeros=sum(t['zeros'] for t in tensor.values());zero_nodes=sum(t['zeros']>0 for t in tensor.values());minj=min(nodes,key=lambda j:tensor[j]['minabs'])
            info=dict(AS_required_tensor_nodes=len(nodes),AS_exact_zero_eigenvalues=zeros,AS_kink_nodes=zero_nodes,AS_classical_pressure_derivative_unique_at_all_required_nodes=not bool(zeros),AS_min_abs_eigenvalue_Pa=float(tensor[minj]['minabs']),AS_min_abs_eigenvalue_native_ID=int(cloud.ids[minj]),AS_max_total_stress_input_float32_delta_Pa=max(t['total_stress_input_float32_max_delta_Pa'] for t in tensor.values()),AS_max_R_output_float32_cast_delta_Pa=max(t['R_output_float32_cast_max_delta_Pa'] for t in tensor.values()))
            info.update({'AS_positive_rank'+str(rank)+'_nodes':sum(t['rank']==rank for t in tensor.values()) for rank in range(4)})
            info.update(AS_B_expansion_roundoff_m_s2_max=max(d['mechanical_B_expansion_roundoff_m_s2'] for d in descriptions),AS_Ace_to_Darcy_expansion_roundoff_Pa_s_max=max(abs(d['Ace_to_Darcy_expansion_roundoff_Pa_s']) for d in descriptions))
            matrix_path=Path(str(PREFIX)+'_part'+str(part).zfill(3)+'_'+label+'.npz');need(not matrix_path.exists(),'Existing AS matrix protected')
            np.savez(matrix_path,target_native_IDs=ids,pressure_native_IDs=pressure_ids,target_xz_m=cloud.x[targets],target_FSType=cloud.fs[targets],target_p_Pa=cloud.p[targets],storage_W_nV_over_Kw=weights,full_AS_increment_rows=AS,full_direct_plus_rawAce_plus_ASJac_rows=augR,A_direct_copied_from_baseline=directA,A_direct_plus_rawAce_copied_from_baseline=rawA,A_direct_plus_rawAce_plus_ASJac=augA,time_s=np.asarray(time),tau_s=np.asarray(tau),completed_step=np.asarray(int(clocks[part]['completed_step'])))
            files.append(matrix_path);matrix_count+=1
            for j,t in tensor.items():
                spectra.append(dict(**context,native_ID=int(cloud.ids[j]),x_m=float(cloud.x[j,0]),z_m=float(cloud.x[j,1]),FSType=int(cloud.fs[j]),p_Pa=float(cloud.p[j]),positive_rank=t['rank'],exact_zero_eigenvalues=t['zeros'],min_abs_eigenvalue_Pa=t['minabs'],lambda0_Pa=float(t['values'][0]),lambda1_Pa=float(t['values'][1]),lambda2_Pa=float(t['values'][2]),total_stress_input_float32_max_delta_Pa=t['total_stress_input_float32_max_delta_Pa'],R_output_float32_cast_max_delta_Pa=t['R_output_float32_cast_max_delta_Pa']))
            for view,selected in (('all_patch_variables',np.arange(len(ids))),('FS0_principal',np.flatnonzero(cloud.fs[targets]==0))):
                b=dict(**context,variant='direct_plus_rawAce_plus_ASJac',variable_view=view,variables=len(selected),**info)
                if not len(selected):summary.append(dict(**b,status='not_evaluated_empty_FS0'));continue
                reference=baseline[(part,label,'direct_plus_rawAce',view)];diffusion=baseline[(part,label,'direct',view)];need(reference['status']==diffusion['status']=='evaluated_frozen_outside_held' and int(reference['variables'])==int(diffusion['variables'])==len(selected),'Baseline view/count differs')
                sub=augA[np.ix_(selected,selected)];stats,mode=base.spectral(sub,weights[selected]);pivot=stats.pop('selected_mode_peak_local_index');outside=np.ones(len(pressure_nodes),dtype=bool);outside[inside[selected]]=False;outside_rows=augR[selected][:,outside]
                comparison={key+'_minus_raw':stats[key]-float(reference[key]) for key in ('max_real_eigenvalue_per_s','imag_of_max_real_eigenvalue_per_s','midpoint_R_spectral_radius','max_frozen_storage_symmetric_eigenvalue_per_s')}
                summary.append(dict(**b,status='evaluated_frozen_outside_held',**stats,**comparison,baseline_direct_max_real_eigenvalue_per_s=float(diffusion['max_real_eigenvalue_per_s']),baseline_raw_max_real_eigenvalue_per_s=float(reference['max_real_eigenvalue_per_s']),baseline_raw_midpoint_R_spectral_radius=float(reference['midpoint_R_spectral_radius']),selected_mode_peak_native_ID=int(ids[selected[pivot]]),full_stencil_constant_1Pa_response_max_abs_Pa_s=float(np.max(np.abs(augR[selected].sum(axis=1)))),held_outside_block_constant_1Pa_response_max_abs_Pa_s=float(np.max(np.abs(sub.sum(axis=1)))),outside_pressure_column_IDs=int(np.count_nonzero(np.any(outside_rows!=0,axis=0))),outside_coupling_abs_sum_per_s=float(np.abs(outside_rows).sum()),outside_coupling_max_row_abs_sum_per_s=float(np.max(np.abs(outside_rows).sum(axis=1))),pressure_rows_npz=matrix_path.name))
                for k,j in enumerate(selected):
                    q=targets[j];modes.append(dict(**context,variable_view=view,native_ID=int(ids[j]),x_m=float(cloud.x[q,0]),z_m=float(cloud.x[q,1]),FSType=int(cloud.fs[q]),native_p_Pa=float(cloud.p[q]),mode_real=float(mode[k].real),mode_imag=float(mode[k].imag),mode_max_abs_normalization_Pa=1.))
    for leaf,rows in (('summary',summary),('modes',modes),('AS_spectra',spectra),('not_evaluated',skips)):
        if rows:
            path=Path(str(PREFIX)+'_'+leaf+'.csv');base.write(path,rows);files.append(path)
    need(matrix_count+len(skips)==8,'Every original saved-state block must be accounted for');need(all(stat(Path(e['path']))==e for e in before),'Sealed baseline/native/helper changed')
    result=dict(stage=TAG,passed=True,analysis_completed=True,requested_saved_state_blocks=8,evaluated_saved_state_blocks=matrix_count,not_evaluated_WallStencil_blocks=len(skips),selected_parts=list(base.PARTS),patch_sizes=proof['patch_sizes'],baseline_matrices_and_spectra_read_not_recomputed=True,baseline_direct_and_raw_NPZ_preserved=True,only_added_variant='direct_plus_rawAce_plus_ASJac',AS_source='Existing SpectralAS: float32(double sigmaeff - absolute p I), real double eigh and derivative epsilon*positive projector',AS_epsilon_float=old.AS_EPS,AS_exponent_float=float(old.AS_EXP),AS_exact_zero_policy='positive eigenvalue projector excludes exact zero; selected nonsmooth convention, not a unique derivative',AS_quantizing_cast_or_GPU_iterative_eigen_derivative_claimed=False,AS_nonlinear_force_is_not_Jacobian_times_saved_pressure=True,raw_guard_used_for_every_AS_mechanical_stencil=True,all_original_WallStencil_guards_kept=True,C_Darcy_and_mechanical_stencils_not_truncated=True,AS_pressure_dependency_does_not_add_a_third_hop=True,variable_views=['all_patch_variables','FS0_principal'],outside_pressure_perturbations_held_zero=True,principal_blocks_not_global_coupled_spectrum=True,positive_or_negative_spectrum_not_actual_pulse_causation_proof=True,FS23_zero_pressure_projection_not_linearized=True,geometry_J_n_k_sigmaeff_theta_velocity_and_FS_frozen=True,AV_effective_stress_and_velocity_response_not_included=True,midpoint_R='Frozen pressure-only polynomial, not full integrator stability',storage_W='nV/Kw pressure-storage norm, not full-state energy',physical_acceptance=False,thresholds_changed=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0,consumed=before,files=[stat(q) for q in files])
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('LOCAL_AS_PRESSURE_SPECTRUM_READY',CHECK,flush=True)

if __name__=='__main__':main()
