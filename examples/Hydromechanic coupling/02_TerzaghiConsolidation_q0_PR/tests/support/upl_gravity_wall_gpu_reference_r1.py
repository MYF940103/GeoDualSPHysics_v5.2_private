"""Offline constant-wall 1% objective on new GPU accelerating-frame fields; no solver."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

T = Path(__file__).resolve().parents[1]
MODULE_SHA = '6d32ef164322e5d44a09f387a8af045880a1bcc0f263d9eaed99a2dfb80254be'
REF_SHA = {'coarse':'40d8179702e799c6f3789961e6d6c731e66e8adf6a51a407207a8677d0d648a6',
           'half':'a4adfcebbd2ae7fde76059cae6dbacc1083fac430ca8e94408f042c0a78fbe7d'}


def need(ok, message):
    if not bool(ok):
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--window', choices=('coarse','half'), required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--native-check', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True, help='fresh logs/TAG prefix; CSV goes in sibling figures')
    args = parser.parse_args()
    module_path = T/'support/upl_gravity_wall_gpu_pair_r1.py'
    # This frozen module has a guarded main; only neutral binding/table/load are called.
    need(hashlib.sha256(module_path.read_bytes()).hexdigest() == MODULE_SHA, 'Frozen neutral GPU frame loader changed before import')
    spec = importlib.util.spec_from_file_location('frozen_gpu_wall_reference_io', module_path)
    io = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(io)
    need(io.binding(module_path)['sha256'] == MODULE_SHA, 'Frozen neutral GPU frame loader changed')
    inputs = [io.binding(__file__),io.binding(T/'notes/upl_gravity_wall_gpu_reference_r1.json'),
              io.binding(module_path),io.binding(T/'notes/upl_gravity_wall_gpu_pair_r1.json')]
    check_path = Path(str(args.out.resolve())+'.check.json')
    csv_path = T/'figures'/(args.out.name+'.csv')
    need(check_path.parent.is_dir() and csv_path.parent.is_dir() and not check_path.exists() and not csv_path.exists(), 'Fresh check/CSV required')
    def bound(e):
        need(io.binding(e['path']) == e, 'Changed bound artifact: '+e['path'])
        inputs.append(e)
        return Path(e['path'])
    native_e = io.binding(args.native_check); inputs.append(native_e)
    native = json.loads(args.native_check.read_text(encoding='utf-8-sig'))
    need(native.get('passed') is True and native.get('physical_acceptance') is False and
         native.get('job') == 'constant_'+args.window and native.get('model') == 'constant' and
         native.get('window') == 'full' and native.get('samples') == 257 and native.get('common_columns') == 33 and
         native.get('actual_saved_final_matches_live') is True and
         native.get('initial_soil33_proof',{}).get('all_soil33_bits_identical') is True,
         'Own complete constant full native reader and strict initial proof required')
    need(bound(native['completion']).parent.resolve() == args.review.resolve(), 'Native check belongs to another review')
    # These direct sealed records are bound, not recursively treated as an independent owned-call audit.
    for key in ('source_run','call','helper','source_build'):
        bound(native[key])
    dt = io.DC if args.window == 'coarse' else io.DH
    lab, frame, initial, selected, single = io.load(args.review,'constant','GPU_gravity',dt)
    for e in selected:
        matches = [x for x in native['files'] if str(Path(x['path']).resolve()).casefold() == e['path'].casefold()]
        need(len(matches) == 1 and matches[0] == e, 'New actual field is not sealed by own native check')
        inputs.append(e)
    ref_path = T/'figures'/('upl_gpu_wall_constant_'+('c' if args.window == 'coarse' else 'h')+'_reference_r1.json')
    ref_e = io.binding(ref_path); need(ref_e['sha256'] == REF_SHA[args.window], 'Retained reference check changed'); inputs.append(ref_e)
    ref = json.loads(ref_path.read_text(encoding='utf-8-sig'))
    need(ref.get('passed') is True and ref.get('physical_acceptance') is False and ref.get('action') == 'Reference' and
         ref.get('model') == 'constant' and ref.get('constant_reference_used') is True and
         ref.get('original_one_percent_objective') is True and ref.get('samples') == 257 and
         ref.get('native_count') == 1024 and ref.get('fixed_count') == 256 and ref.get('common_columns') == 33 and
         ref.get('material_band_native_count') == 256 and ref.get('reference_crosscheck_limit') == 2e-11 and
         0 <= ref['expm_vs_physical_RK4_max_normalized_difference'] < 2e-11,
         'Original independently cross-checked constant-wall reference required')
    need(ref['normalizers']['Pstar_Pa'] == io.PSTAR and ref['normalizers']['A_m_s'] == io.A and ref['normalizers']['Ustar_m'] == io.USTAR, 'Original reference scales differ')
    ref_csv = [x for x in ref['files'] if Path(x['path']).suffix.lower() == '.csv']
    need(len(ref_csv) == 1, 'Exactly one bound original reference CSV required')
    rows = io.table(bound(ref_csv[0]))
    curves = np.array([[float(r[k]) for k in ('pressure_cosine_mode_over_Pstar_reference','vx_sine_mode_over_A_reference','ux_sine_mode_over_Ustar_reference')] for r in rows])
    need(len(rows) == 257 and np.array_equal([int(r['part']) for r in rows],np.arange(257)) and np.array_equal([float(r['time_s']) for r in rows],io.TIMES) and np.isfinite(curves).all() and curves[-1,0] != 0, 'Exact257 finite reference times required; interpolation prohibited')
    phase = 2*np.pi*initial[:,0]/.125
    near = np.minimum(initial[:,0],.0625-initial[:,0]) <= 2*float(np.float32(1.8/512))
    ids = io.table(args.review/'native_ids.csv')
    need(near.sum() == 256 and np.array_equal([int(r['wall_band']) for r in ids],near.astype(int)), 'Fixed256 original material near-wall band differs')
    p = frame[:,:,6]/io.PSTAR-curves[:,0,None]*np.cos(phase)
    v = frame[:,:,3:6].copy()/io.A; v[:,:,0] -= curves[:,1,None]*np.sin(phase)
    u = frame[:,:,25:28].copy()/io.USTAR; u[:,:,0] -= curves[:,2,None]*np.sin(phase)
    square = np.stack((p*p,(v*v).sum(2),(u*u).sum(2)),axis=2)
    global_error, near_error = np.sqrt(square.mean(1)), np.sqrt(square[:,near].mean(1))
    mode = 2*np.mean(frame[:,:,6]*np.cos(phase),axis=1)/io.PSTAR
    endpoint = float(mode[-1]/curves[-1,0]-1)
    gates = {'all257_global_p_vXYZ_uXYZ_le_1percent':bool((global_error<=.01).all()),
             'all257_fixed256_nearwall_p_vXYZ_uXYZ_le_1percent':bool((near_error<=.01).all()),
             'endpoint_pressure_cosine_relative_le_1percent':abs(endpoint)<=.01}
    with csv_path.open('x',encoding='utf-8',newline='') as stream:
        writer = csv.writer(stream); writer.writerow(['part','time_s','reference_p_over_Pstar','reference_v_over_A','reference_u_over_Ustar','global_p_RMS_over_Pstar','global_vXYZ_RMS_over_A','global_uXYZ_RMS_over_Ustar','nearwall256_p_RMS_over_Pstar','nearwall256_vXYZ_RMS_over_A','nearwall256_uXYZ_RMS_over_Ustar','actual_pressure_cosine_mode_over_Pstar'])
        for i,time in enumerate(io.TIMES):
            writer.writerow([i,float(time),*curves[i],*global_error[i],*near_error[i],mode[i]])
    for e in inputs:
        need(io.binding(e['path']) == e, 'Bound source/check/native/reference changed during offline analysis')
    result = dict(stage='upl_gravity_wall_gpu_reference_r1',passed=all(gates.values()),model='constant',window=args.window,
                  samples=257,native_count=1024,fixed_count=256,material_band_native_count=256,common_columns=33,
                  dt_s=dt,cadence_s=io.CAD,actual_end_s=io.END,gates=gates,original_one_percent_limit=.01,
                  max_global_normalized_p_vXYZ_uXYZ=global_error.max(0).tolist(),
                  max_nearwall256_normalized_p_vXYZ_uXYZ=near_error.max(0).tolist(),
                  endpoint_pressure_relative_error=endpoint,reference_check=ref_e,
                  inherited_expm_vs_RK4_normalized_gap=ref['expm_vs_physical_RK4_max_normalized_difference'],
                  actual_new_frame33_evaluated=True,only_reference_curve_inherited=True,half_error_used_as_reference=False,
                  single_run_metrics=single,inputs=inputs,files=[io.binding(csv_path)],
                  owned_solver_and_g0_source_require_separate_root_review=True,
                  raw_BI4_reparsed=False,endpoint_force_stage_observed=False,public_gravity_accepted=False,physical_acceptance=False)
    with check_path.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2,allow_nan=False); stream.write('\n')
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

