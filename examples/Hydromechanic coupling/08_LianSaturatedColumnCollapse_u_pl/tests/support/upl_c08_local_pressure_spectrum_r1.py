"""Frozen saved-state local pressure blocks; no solver, BI4 reader or physical admission."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,csv,json,math
from pathlib import Path
import numpy as np
import upl_c08_r5_pressure_probe_r2 as old

T=Path(__file__).resolve().parents[1];TAG='upl_c08_local_pressure_spectrum_r1';PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json')
PARTS=(60,61,62,63);FOCI=(('5809',(5809,)),('4956_4959',(4956,4959)));DT=.0000025
p,ace=old.p,old.ace
need,read,stat=old.need,old.read,old.stat

def write(path,rows):
    need(rows,'Empty derived table: '+str(path));fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def at(cloud,identity):
    match=np.flatnonzero(cloud.ids==identity);need(len(match)==1,'Focus material ID missing');return int(match[0])

def matrix_rows(rows,pressure_nodes):
    columns={int(j):k for k,j in enumerate(pressure_nodes)};R=np.zeros((len(rows),len(columns)))
    for i,row in enumerate(rows):
        for j,value in row.items():R[i,columns[int(j)]]=value
    need(np.isfinite(R).all(),'Nonfinite assembled frozen coefficient');return R

def spectral(A,weights):
    values,vectors=np.linalg.eig(A);k=int(np.argmax(values.real));value=values[k];mode=vectors[:,k]
    pivot=int(np.argmax(np.abs(mode)));amplitude=float(abs(mode[pivot]));need(amplitude>0,'Zero eigensolver mode')
    mode=mode*np.exp(-1j*np.angle(mode[pivot]))/amplitude
    midpoint=1.+DT*values+.5*(DT*values)**2
    # E_p=.5 dp^T W dp, with frozen W=nV/Kw; this is not the full coupled energy.
    root=np.sqrt(weights);B=(root[:,None]*A)/root[None,:];H=.5*(B+B.T)
    symmetric=float(np.linalg.eigvalsh(H)[-1])
    need(np.isfinite(values).all() and np.isfinite(mode).all() and np.isfinite(midpoint).all() and math.isfinite(symmetric),'Nonfinite eigensolver result')
    return dict(max_real_eigenvalue_per_s=float(value.real),imag_of_max_real_eigenvalue_per_s=float(value.imag),max_abs_imag_eigenvalue_per_s=float(np.max(np.abs(values.imag))),min_real_eigenvalue_per_s=float(np.min(values.real)),midpoint_R_spectral_radius=float(np.max(np.abs(midpoint))),max_frozen_storage_symmetric_eigenvalue_per_s=symmetric,selected_mode_peak_local_index=pivot),mode

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read before one offline matrix analysis')
    need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial spectrum outputs protected')
    previous=T/'logs/upl_c08_r5_pressure_probe_r2.check.json';proof=read(previous)
    need(proof['passed'] and proof['analysis_completed'] and proof['evaluated_receivers']==18 and proof['not_evaluated_receivers']==0 and proof['mechanical_complete_two_hop_stencils'] and proof['all_original_WallStencil_guards_kept'],'Sealed passed r5 probe required')
    data,done,clocks,before=old.load();before.extend(stat(q) for q in (Path(__file__),T/'notes'/(TAG+'.md'),Path(old.__file__),previous))
    clouds={part:p.Cloud(data[part]) for part in PARTS};patches={};patch_rows=[]
    # Fixed material variables per group: union of every selected saved-state 2R focus ball.
    # This selection never truncates C, Darcy, raw-mechanical or two-hop pressure stencils.
    for label,focus in FOCI:
        chosen=set()
        for part,cloud in clouds.items():
            for identity in focus:
                i=at(cloud,identity)
                chosen.update(int(cloud.ids[j]) for j in cloud.tree.query_ball_point(cloud.x[i],2*p.R) if cloud.ids[j]>=2060)
        need(chosen and set(focus)<=chosen,'Empty/focus-incomplete diagnostic material patch');patches[label]=tuple(sorted(chosen))
        for identity in patches[label]:patch_rows.append(dict(patch=label,native_ID=identity,patch_origin='union of the four saved-state2R focus balls',focus_IDs=';'.join(map(str,focus))))
    summary=[];modes=[];rowinfo=[];files=[];skips=[];matrix_count=0
    for part,cloud in clouds.items():
        mechanical=ace.Mechanical(cloud,data[part]);time=float(data[part]['time']);tau=time-done['source_actual_time_s']
        for label,focus in FOCI:
            print('LOCAL_PRESSURE_BLOCK',part,label,len(patches[label]),flush=True)
            ids=np.asarray(patches[label],dtype=np.uint32);targets=np.asarray([at(cloud,int(identity)) for identity in ids]);direct=[];coupled=[];desc=[]
            base=dict(part=part,time_s=time,tau_s=tau,completed_step=int(clocks[part]['completed_step']),patch=label,focus_IDs=';'.join(map(str,focus)),all_patch_variables=len(ids))
            try:
                for i in targets:
                    rows,unused,observations=ace.probe(cloud,mechanical,int(i));direct.append(rows['direct_pressure']);coupled.append(rows['composite_pressure_channel']);desc.append(observations)
            except p.WallStencil as error:
                # A whole block is unavailable. Never delete an offending row, wall or neighbor.
                skips.append(dict(**base,status='not_evaluated_WallStencil',reason=str(error),failed_row_native_ID=int(cloud.ids[i])));continue
            pressure_nodes=np.asarray(sorted(set().union(*(set(row) for row in direct+coupled))),dtype=int)
            need(np.all(cloud.ids[pressure_nodes]>=2060),'A fixed pressure source escaped the original WallStencil guard')
            D=matrix_rows(direct,pressure_nodes);F=matrix_rows(coupled,pressure_nodes);column_of={int(j):k for k,j in enumerate(pressure_nodes)};inside=np.asarray([column_of[int(i)] for i in targets]);A_D=D[:,inside];A_F=F[:,inside]
            weights=cloud.n[targets]*cloud.V[targets]/p.KW;need(np.isfinite(weights).all() and np.all(weights>0),'Saved saturated storage weights invalid')
            matrix_path=Path(str(PREFIX)+'_part'+str(part).zfill(3)+'_'+label+'.npz');need(not matrix_path.exists(),'Existing matrix protected')
            np.savez(matrix_path,target_native_IDs=ids,pressure_native_IDs=cloud.ids[pressure_nodes],target_xz_m=cloud.x[targets],target_FSType=cloud.fs[targets],target_p_Pa=cloud.p[targets],storage_W_nV_over_Kw=weights,full_direct_rows=D,full_direct_plus_rawAce_rows=F,A_direct=A_D,A_direct_plus_rawAce=A_F,time_s=np.asarray(time),tau_s=np.asarray(tau),completed_step=np.asarray(int(clocks[part]['completed_step'])))
            files.append(matrix_path);matrix_count+=1
            for i,q in enumerate(targets):
                rowinfo.append(dict(**base,native_ID=int(cloud.ids[q]),x_m=float(cloud.x[q,0]),z_m=float(cloud.x[q,1]),FSType=int(cloud.fs[q]),p_Pa=float(cloud.p[q]),storage_W_nV_over_Kw=float(weights[i]),C11=desc[i]['C11'],C13=desc[i]['C13'],C31=desc[i]['C31'],C33=desc[i]['C33'],C_moment_det=desc[i]['C_moment_det'],C_moment_condition=desc[i]['C_moment_condition'],C_exact_zero_identity_fallback=desc[i]['C_exact_zero_identity_fallback'],nearest_fixed_B_m=desc[i]['nearest_fixed_B_m'],complete_two_hop_pressure_nodes=desc[i]['two_hop_pressure_nodes'],mechanical_B_expansion_roundoff_m_s2=desc[i]['mechanical_B_expansion_roundoff_m_s2'],Ace_to_Darcy_expansion_roundoff_Pa_s=desc[i]['Ace_to_Darcy_expansion_roundoff_Pa_s']))
            for variant,R,A in (('direct',D,A_D),('direct_plus_rawAce',F,A_F)):
                for view,selected in (('all_patch_variables',np.arange(len(ids))),('FS0_principal',np.flatnonzero(cloud.fs[targets]==0))):
                    b=dict(**base,variant=variant,variable_view=view,variables=len(selected),nonselected_patch_variables_held=bool(len(selected)!=len(ids)),all_outside_pressure_perturbations_held_zero=True)
                    if not len(selected):summary.append(dict(**b,status='not_evaluated_empty_FS0'));continue
                    sub=A[np.ix_(selected,selected)];selected_pressure_columns=inside[selected];outside=np.ones(len(pressure_nodes),dtype=bool);outside[selected_pressure_columns]=False
                    outside_rows=R[selected][:,outside];full_constant=R[selected].sum(axis=1);block_constant=sub.sum(axis=1);stats,mode=spectral(sub,weights[selected]);pivot=stats.pop('selected_mode_peak_local_index')
                    summary.append(dict(**b,status='evaluated_frozen_outside_held',**stats,selected_mode_peak_native_ID=int(ids[selected[pivot]]),full_stencil_constant_1Pa_response_max_abs_Pa_s=float(np.max(np.abs(full_constant))),held_outside_block_constant_1Pa_response_max_abs_Pa_s=float(np.max(np.abs(block_constant))),outside_pressure_column_IDs=int(np.count_nonzero(np.any(outside_rows!=0,axis=0))),outside_coupling_abs_sum_per_s=float(np.abs(outside_rows).sum()),outside_coupling_max_row_abs_sum_per_s=float(np.max(np.abs(outside_rows).sum(axis=1))),pressure_rows_npz=matrix_path.name,FS23_zero_pressure_variables=int(np.count_nonzero(np.isin(cloud.fs[targets[selected]],(2,3))&(cloud.p[targets[selected]]==0)))))
                    for k,j in enumerate(selected):
                        q=targets[j];modes.append(dict(**b,native_ID=int(ids[j]),x_m=float(cloud.x[q,0]),z_m=float(cloud.x[q,1]),FSType=int(cloud.fs[q]),native_p_Pa=float(cloud.p[q]),mode_real=float(mode[k].real),mode_imag=float(mode[k].imag),mode_max_abs_normalization_Pa=1.))
    for leaf,rows in (('patch_IDs',patch_rows),('summary',summary),('row_geometry',rowinfo),('modes',modes),('not_evaluated',skips)):
        if rows:
            path=Path(str(PREFIX)+'_'+leaf+'.csv');write(path,rows);files.append(path)
    need(matrix_count+len(skips)==8,'Eight explicit saved-state/focus blocks must be accounted for');need(all(stat(Path(e['path']))==e for e in before),'Sealed native data or helper changed')
    result=dict(stage=TAG,passed=True,analysis_completed=True,selected_parts=list(PARTS),nominal_selected_tau_s=[.61,.62,.63,.64],actual_times_are_saved_native_clock=True,focus_groups=[list(v) for k,v in FOCI],patch_variables_fixed_across_saved_states=True,patch_selection='four-time union of2R focus balls; all rows use complete original Cloud stencils',patch_sizes={k:len(v) for k,v in patches.items()},requested_saved_state_blocks=8,evaluated_saved_state_blocks=matrix_count,not_evaluated_WallStencil_blocks=len(skips),spectral_variants=['direct','direct_plus_rawAce'],variable_views=['all_patch_variables','FS0_principal'],ASJac_included=False,actual_r5_AS1_was_active=True,raw_mechanical_pressure_self_terms_retained=True,all_original_WallStencil_guards_kept=True,C_Darcy_and_mechanical_stencils_not_truncated=True,outside_pressure_perturbations_held_zero=True,principal_block_is_not_global_coupled_spectrum=True,positive_real_part_is_not_causation_or_full_instability_proof=True,no_positive_real_part_does_not_exclude_nonnormal_transients_or_stage_switches=True,midpoint_R='1+dt*lambda+.5*(dt*lambda)^2; frozen pressure-only explicit midpoint surrogate, not full integrator eigenvalues',midpoint_dt_s=DT,storage_symmetric_part='sym(W^.5 A W^-.5), W=nV/Kw; frozen pressure-storage norm only, not full-state energy',FS23_zero_pressure_projection_not_linearized=True,geometry_J_n_k_sigmaeff_theta_velocity_and_FS_frozen=True,AS_AV_effective_stress_and_velocity_response_not_included=True,saved_C_reconstruction_not_unsaved_GPU_C_or_float_AD=True,physical_acceptance=False,thresholds_changed=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0,consumed=before,files=[stat(q) for q in files])
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('LOCAL_PRESSURE_SPECTRUM_READY',CHECK,flush=True)

if __name__=='__main__':main()
