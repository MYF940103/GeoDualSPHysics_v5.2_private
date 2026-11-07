"""Offline description of a Release PRE advanced by Debug; no bitwise-build claim."""
import json
import upl_material_release_native_r1_review as base
T=base.T;tag='upl_material_old_pre_gpu_review_r1';check=T/'logs'/(tag+'.json');assert not check.exists()
a=base.load('source','GPU',True);b=base.load('receive_old','GPU');keys=set(b['frames']);assert keys<=set(a['frames']) and len(keys)==11
# Select actual common observations in memory; raw states/clock records are untouched.
a['frames']={k:a['frames'][k] for k in keys}
rows,fields,fail=base.compare(a,b,False,'old_release_PRE_to_Debug_GPU')
assert len(rows)==11
csv=T/'figures'/(tag+'_pairs.csv');base.write(csv,rows)
native=base.read(T/'logs/upl_material_release_native_r1_receive_old_GPU.native.check.json')
assert native['passed'] and native['actual_completion']['source_material_law_version']==1
result=dict(stage=tag,passed=not fail,comparison='same old Release PRE, Release continuation vs Debug continuation',actual_matched_states=11,original_5Pa_005mm_comparison_passed=not fail,max_pressure_RMS_difference_Pa=max(r['pressure_RMS_difference_Pa'] for r in rows),max_material_XYZ_difference_mm=max(r['material_XYZ_max_difference_mm'] for r in rows),old_typed_PRE_native_import_qualified=True,all_typed_arrays_bit_equal=all(r['typed22_bit_equal'] for r in rows),same_configuration_bitwise_proof=False,physical_acceptance=False,interpolated_or_rewritten_native_states=False,outputs=[base.stat(csv)],consumed=a['consumed']+b['consumed'],failures=fail,SHA_scans=0)
assert all(base.stat(e['path'])==e for e in result['consumed']);base.save(check,result)
print(json.dumps({k:v for k,v in result.items() if k not in ('outputs','consumed')}));raise SystemExit(0 if result['passed'] else 1)
