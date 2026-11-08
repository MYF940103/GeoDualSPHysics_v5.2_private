"""Summarize the sealed r5 full collapse; no solver, native decoder or VTK invocation."""
import importlib.util,json,sys
from datetime import datetime,timezone
from pathlib import Path
import numpy as np

T=Path(__file__).resolve().parents[1];C=T.parent
TAG='upl_c08_r5_physical_review_r1'
target=T/'logs'/(TAG+'.check.json')
assert not target.exists(),'Existing physical review is protected'
spec=importlib.util.spec_from_file_location('r5post',C/'support/postprocess_lian_collapse_r5.py')
post=importlib.util.module_from_spec(spec);spec.loader.exec_module(post)
O=C/'CaseLianSaturatedColumnCollapse_psi0_shared_r5_GPU_out'
inputs=[T/'logs/upl_c08_formal_psi0_r5_r1.terminal_audit.json',T/'logs/upl_c08_formal_psi0_r5_r1.run.json',O/'postprocess_r5.json',O/'native/completion.json',O/'native/typed22.bin',C/'figures/collapse_psi0_r5/figures_r5.json']
before=[post.stat(x) for x in inputs]
audit,run,pp,fig=[post.read(p) for p in (inputs[0],inputs[1],inputs[2],inputs[5])]
assert audit['passed'] and audit['actual_wrapper_and_children_exits_zero']
assert audit['original_60_frame_prefix']['all22_actual_time_payload_byte_exact'] and audit['original_60_frame_prefix']['signed_clock_rows_exact']
assert run['passed'] and run['solver_completed'] and run['postprocess_completed'] and pp['passed'] and fig['passed']
post.verify(fig['files'])
d,a,soil,names,table=post.bundle(O/'native')
tau=np.asarray(a['time'])-d['source_actual_time_s'];ids=a[0]['Idp'][soil]
p=a['PorePress'][:,soil].astype(float);v=a['Vel'][:,soil].astype(float)
speed=np.linalg.norm(v,axis=2);J=a['PoroVolumeRatio'][:,soil];k=a['PoroHydraulicConductivity'][:,soil]
q={key:table[:,i] for i,key in enumerate(names)}
def extreme(flat):
    part,node=np.unravel_index(flat,p.shape);f=a[part];j=int(np.flatnonzero(f['Idp']==ids[node])[0])
    return dict(part=int(part),actual_time_s=float(f['time']),tau_s=float(tau[part]),native_ID=int(ids[node]),p_Pa=float(p[part,node]),FSType=int(f['FSType'][j]),position_m=f['Posd'][j].tolist())
summaries=[]
for request in (.3,.6,1.,1.2,2.,3.):
    part=int(np.argmin(abs(tau-request)))
    summaries.append(dict(requested_tau_s=request,actual_tau_s=float(tau[part]),part=part,p_RMS_Pa=float(np.sqrt(np.mean(p[part]**2))),p_min_Pa=float(p[part].min()),p_max_Pa=float(p[part].max()),v_RMS_m_s=float(np.sqrt(np.mean(speed[part]**2))),v_max_m_s=float(speed[part].max()),front_particle_center_x_m=float(q['front_x_m'][part]),mean_PRE_material_settlement_mm=float(q['mean_material_settlement_from_PRE_mm'][part])))
final=p[-1];result=dict(stage=TAG,utc=datetime.now(timezone.utc).isoformat(),numerical_run_and_postprocessing_passed=True,physical_acceptance=False,other_psi_admitted=False,all_original_300_state_native_guards_reference=str(inputs[3]),actual_end_s=float(a[-1]['time']),actual_tau_end_s=float(tau[-1]),soil_ID_count=int(soil.sum()),fixed_ID_count=int((~soil).sum()),saved_frames=len(a),pressure_min=extreme(int(np.argmin(p))),pressure_max=extreme(int(np.argmax(p))),summary=summaries,final_negative_pressure_count=int((final<0).sum()),final_pressure_below_minus10kPa_count=int((final<-10000).sum()),final_pressure_below_minus20kPa_count=int((final<-20000).sum()),J_range=[float(J.min()),float(J.max())],k_range_m_s=[float(k.min()),float(k.max())],min_soil_z_m=float(a['Posd'][:,soil,2].min()),original_60_frame_prefix_reference=str(inputs[0]),no_new_solver_or_decode_or_VTK=True,SHA_scans=0,physical_review='Pressure pulses and premature arrest remain unresolved. Saved-field channels are conditional diagnostics; no cause or paper equivalence is established.',paper_pressure_reference='Native excess is p minus fixed material P0; paper Fig14 excess reference is not uniquely specified.',r1_offline_probe_failure=dict(observed_tool_exit=1,first_error="TypeError: dict() got multiple values for keyword argument 'nearest_fixed_B_m'",outputs_written=False,solver_data_affected=False,source_file_edited_by_author_during_first_execution=True,failed_loaded_source_identity_not_reconstructed=True,remedy='Preserve r1 source/note; separately review a frozen r2 derived analysis before execution.'),visual_QA=dict(history_and_paper_composite_viewed=True,single_field_tau_s_viewed=[.1,.3,.5,.6,1.,1.2,2.,3.],raw_global_pressure_range_retained=True),consumed=before)
assert all(post.stat(p)==s for p,s in zip(inputs,before))
with target.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps({key:result[key] for key in ('stage','saved_frames','actual_tau_end_s','pressure_min','pressure_max','final_negative_pressure_count','physical_acceptance')},indent=2))
