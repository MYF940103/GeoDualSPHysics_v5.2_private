"""Offline GPU tangent-wall pairs; no solver, interpolation or source-data edits."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import struct

import numpy as np

N, C, S = 1024, 33, 257
CAD, END, DC, DH = 2.0**-23, 2.0**-15, 2.0**-25, 2.0**-26
TIMES = np.arange(S, dtype=np.float64)*CAD
A, PSTAR, USTAR, GZ = 2.0**-9, 1023.9999974568686, 7.589099058944216e-8, -8.0
LIMIT, EPS = 1e-4, np.finfo(np.float64).eps
N0, RHO0, RHOW, KW = .25, 2048., 1000., 67108864.
V0, BULK, SHEAR = 2.0**-18, 89478488., 134217728.
K0, CK, H = float(np.float32(1e-4)), 2.0**-13, float(np.float32(1.8*2.0**-9))
FIELDS = ['x','y','z','vx','vy','vz','p','p0','J','theta_last_stage','sigma_xx','sigma_xy','sigma_xz','sigma_yy','sigma_yz','sigma_zz','plastic','FSType','normal_x','normal_y','normal_z','load_x','load_y','load_z','passive_legacy_Rhop','material_u_x','material_u_y','material_u_z','native_float_excess','native_n','current_V','mixture_rho','current_k']
EXACT_CORE = [7,16,21,22,23]
EXACT_GPU = EXACT_CORE+[24]


def need(ok, message):
    if not bool(ok):
        raise ValueError(message)


def binding(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def table(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        need(reader.fieldnames and len(reader.fieldnames) == len(set(reader.fieldnames)), 'Invalid CSV header')
        return rows


def binary(path):
    need(path.stat().st_size == 12+S*(1+N*C)*8, 'Truncated/trailing field file')
    with path.open('rb') as stream:
        need(struct.unpack('<III', stream.read(12)) == (N,C,S), 'Expected1024 x33 x257')
    raw = np.fromfile(path, dtype='<f8', offset=12).reshape(S, 1+N*C)
    need(np.isfinite(raw).all() and np.array_equal(raw[:,0], TIMES), 'Nonfinite or unmatched actual times')
    return raw[:,1:].reshape(S,N,C)


def load(folder, model, role, dt):
    folder = folder.resolve()
    need(role in ('GPU_gravity','GPU_g0','CPU_gravity'), 'Unknown explicit data role')
    gravity = role != 'GPU_g0'
    names = ['physical.bin','native_ids.csv','history.csv','completion.json']
    if gravity:
        names.insert(1,'frame.bin')
    inputs = [binding(folder/name) for name in names]
    with (folder/'completion.json').open(encoding='utf-8-sig') as stream:
        done = json.load(stream)
    need(done.get('passed') is True and done.get('physical_acceptance') is False and done.get('model') == model and done.get('samples') == S and done.get('common_columns') == C and done.get('native_count') == N and done.get('fixed_count') == 256 and done.get('total_native_count') == 1280, 'Passed native-reader completion/schema required')
    need(done.get('original_arrays') == 15 and done.get('native_J_arrays') == 3 and done.get('conductivity_Ck') == (CK if model == 'variable' else 0), 'Private3J/material attribution required')
    if role == 'GPU_gravity':
        need(done.get('stage') == 'upl_gravity_wall_gpu_r1' and done.get('backend') == 'GPU' and done.get('gravity_z_m_s2') == GZ and done.get('GPU_V_rho_k_derived_not_native') is True and done.get('fixed_frame_transform_applied') is False and done.get('energy_gate_is_soil_accelerating_frame') is True and done.get('frame_columns_zero_based') == [2,5,27], 'Wrong new GPU gravity reader attribution')
    elif role == 'GPU_g0':
        need(done.get('stage') == 'upl_gpu_wall_actual_r1' and done.get('backend') == 'GPU' and done.get('GPU_V_rho_k_derived_not_native') is True, 'Retained old GPU g0 private3J reader required')
        if 'gravity_z_m_s2' in done:
            need(done['gravity_z_m_s2'] == 0, 'Retained g0 gravity contradicts its reader contract')
        # Old g0 completion has no gravity field/frame file: source/owned receipt
        # identity must separately prove its g0 contract; never infer it from a filename.
    else:
        need(done.get('stage') == 'upl_gravity_wall_cpu_r1' and done.get('backend') == 'CPU_private_tangential_gravity' and done.get('gravity_z_m_s2') == GZ and done.get('V_rho_k_derived_not_native') is True and done.get('native_PosDiv_available') is False and done.get('public_dynamic_metadata') is False and done.get('fixed_frame_transform_applied') is False, 'Retained CPU gravity must use its own private3J reader')
    need(done.get('window') == (('coarse' if dt == DC else 'half') if role == 'CPU_gravity' else 'full'), 'Wrong full-window reader attribution')
    need(done.get('dt_s') == dt and done.get('cadence_s') == CAD and done.get('actual_end_s') == END, 'Reader clocks differ from admission')
    lab = binary(folder/'physical.bin')
    expected = lab.copy()
    if gravity:
        expected[:,:,2] -= (.5*GZ*TIMES*TIMES)[:,None]
        expected[:,:,5] -= (GZ*TIMES)[:,None]
        expected[:,:,27] -= (.5*GZ*TIMES*TIMES)[:,None]
        frame = binary(folder/'frame.bin')
        need(np.array_equal(expected.view(np.uint64), frame.view(np.uint64)), 'Frame is not exactly the declared soil-only transform on columns2/5/27')
    else:
        frame = expected  # In-memory g0 identity, not an invented/read frame.bin.
    ids = table(folder/'native_ids.csv')
    need(len(ids) == N and [int(row['id']) for row in ids] == list(range(256,1280)), 'Native material ID order differs')
    initial = np.asarray([[float(row[k]) for k in ('x0','y0','z0')] for row in ids])
    need(np.array_equal(initial.view(np.uint64), lab[0,:,:3].copy().view(np.uint64)), 'Initial material coordinates differ')
    consistency = float(np.abs(frame[:,:,25:28]-(frame[:,:,:3]-initial)).max())
    need(consistency <= 16*EPS, 'Material u and current position differ beyond roundoff')
    history = table(folder/'history.csv')
    need(len(history) == S, 'Incomplete native history')
    steps = np.rint(TIMES/dt).astype(np.int64)-1
    steps[0] = 0
    need(np.array_equal([float(r['time_s']) for r in history], TIMES) and np.array_equal([int(r['saved_step']) for r in history], steps), 'Actual saved clock/step mismatch')
    error_key = 'signed_dterror_s' if role == 'CPU_gravity' else 'dterror_s'
    energy_key = 'energy_ratio' if role == 'GPU_g0' else 'frame_energy_ratio'
    need(all(float(r['dt_s']) == dt and np.isfinite(float(r[error_key])) and float(r[error_key]) <= 1e-14 and np.isfinite(float(r[energy_key])) and float(r[energy_key]) <= 1.1 for r in history), 'Original locked-step/signed-dterror/frame-energy safety failed')
    need((lab[:,:,0]>0).all() and (lab[:,:,0]<1.0/16).all() and (lab[:,:,1]==0).all() and (lab[:,:,2]>0).all() and (lab[:,:,2]<1.0/16).all(), 'Original actual inertial soil no-wrap/slab domain failed')
    need((lab[0,:,8]==1).all() and (lab[0,:,9]==0).all() and (lab[0,:,6]==0).all() and (lab[0,:,10:16]==0).all() and (lab[0,:,4:6]==0).all() and (lab[0,:,24]==RHO0).all(), 'Original zero/J1/rho initial physical state differs')
    j, n = frame[:,:,8], frame[:,:,29]
    rn = 1-(1-N0)/j
    rv, rr = V0*j, RHOW+(RHO0-RHOW)/j
    rk = K0*np.exp((j-1)/((1-N0)*CK)) if model == 'variable' else np.full_like(j,K0)
    ledger = np.stack([np.abs(n-rn)/rn,np.abs(frame[:,:,30]-rv)/rv,np.abs(frame[:,:,31]-rr)/rr,np.abs(frame[:,:,32]-rk)/rk])
    need(np.isfinite(ledger).all() and (ledger<=5e-13).all() and (j>1-N0).all() and (np.abs(j-1)<=1e-4).all() and (n>0).all() and (n<1).all(), 'Original saturated ledger/domain failed')
    need((frame[:,:,7]==0).all() and (frame[:,:,16]==0).all() and (frame[:,:,21:24]==0).all() and (frame[:,:,24]>=700).all() and (frame[:,:,24]<=3000).all(), 'p0/plastic/load/passive-density safety failed')
    need(np.array_equal(frame[:,:,28],(frame[:,:,6].astype(np.float32)-frame[:,:,7].astype(np.float32)).astype(np.float32).astype(float)), 'Native float excess differs')
    tr = frame[:,:,10]+frame[:,:,13]+frame[:,:,15]
    dev = ((frame[:,:,[10,13,15]]-tr[:,:,None]/3)**2).sum(2)+2*(frame[:,:,[11,12,14]]**2).sum(2)
    energy = (rv*(.5*rr*(frame[:,:,3:6]**2).sum(2)+dev/(4*SHEAR)+tr*tr/(18*BULK)+n*frame[:,:,6]**2/(2*KW))).sum(1)
    ratio = energy/energy[0]
    cu = np.sqrt((BULK+4*SHEAR/3+KW/rn)/rr)*dt/H
    diffusion = KW/rn*rk/(RHOW*9.80665)*dt/(H*H)
    margin = rr*(KW/rn)/(BULK+4*SHEAR/3+KW/rn)-RHOW
    need(energy[0]>0 and np.isfinite(ratio).all() and (ratio<=1.1).all() and (cu<=.01).all() and (diffusion<=.01).all() and (margin>64*EPS*np.maximum(rr,RHOW)).all(), 'Original energy/necessary-step/domain screen failed')
    need(np.abs(j-1).max()>1e-8 and (model != 'variable' or ((rk.max(1)-rk.min(1))/K0).max()>=.005), 'Original full natural J/k activation screen failed')
    return lab, frame, initial, inputs, {'role':role,'max_ledger_relative_error':float(ledger.max()),'max_frame_energy_ratio':float(ratio.max()),'material_position_consistency_m':consistency,'frame_transform_bit_verified':gravity,'retained_g0_frame_is_in_memory_inertial_identity':not gravity,'legacy_g0_source_and_owned_receipt_identity_required':not gravity}


def vrms(delta):
    return np.sqrt((delta*delta).sum(2).mean(1))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', choices=['constant','variable'], required=True)
    parser.add_argument('--pair', choices=['half','frame_c','frame_h','cpu_c','cpu_h'], required=True)
    for name in ('a','b','out'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    prefix = args.out.resolve()
    paths = {'check':Path(str(prefix)+'.check.json'),'history':Path(str(prefix)+'.csv'),'fields':Path(str(prefix)+'_fields.csv')}
    need(prefix.parent.is_dir() and not any(p.exists() for p in paths.values()), 'Fresh offline check/CSV paths required')
    source = binding(__file__)
    da = DH if args.pair in ('frame_h','cpu_h') else DC
    db = DH if args.pair == 'half' else da
    role_b = 'GPU_gravity' if args.pair == 'half' else ('CPU_gravity' if args.pair.startswith('cpu_') else 'GPU_g0')
    al, a, ax, ia, ma = load(args.a,args.model,'GPU_gravity',da)
    bl, b, bx, ib, mb = load(args.b,args.model,role_b,db)
    need(np.array_equal(ax.view(np.uint64),bx.view(np.uint64)) and np.array_equal(a[0].view(np.uint64),b[0].view(np.uint64)), 'Exact common initial33 fields required')
    delta = a-b
    pressure = np.sqrt((delta[:,:,6]**2).mean(1))
    velocity, displacement = vrms(delta[:,:,3:6]), vrms(delta[:,:,25:28])
    umax = 1000*np.linalg.norm(delta[:,:,25:28],axis=2).max(1)
    exact_columns = EXACT_CORE if role_b == 'CPU_gravity' else EXACT_GPU
    exact = bool(np.array_equal(a[:,:,EXACT_CORE].copy().view(np.uint64),b[:,:,EXACT_CORE].copy().view(np.uint64)))
    passive_equal = bool(np.array_equal(a[:,:,24].copy().view(np.uint64),b[:,:,24].copy().view(np.uint64)))
    gates = {'pressure_RMS_5Pa':bool((pressure<=5).all()),'material_u_max_0p005mm':bool((umax<=.005).all()),'pressure_normalized_1e4':bool((pressure/PSTAR<=LIMIT).all()),'velocity_normalized_1e4':bool((velocity/A<=LIMIT).all()),'material_u_normalized_1e4':bool((displacement/USTAR<=LIMIT).all()),'p0_plastic_load_bits_exact':exact}
    if role_b != 'CPU_gravity':
        gates['passive_legacy_rho_bits_exact'] = passive_equal
    body = None
    missing = doubled = None
    if args.pair.startswith('frame_'):
        expected = np.zeros((S,1,3)); expected[:,0,2] = GZ*TIMES
        dv = al[:,:,3:6]-bl[:,:,3:6]
        body = vrms(dv-expected)/A
        missing = float(np.sqrt((dv[-1]**2).sum(1).mean())/(A*LIMIT))
        doubled = float(np.sqrt(((dv[-1]-2*expected[-1])**2).sum(1).mean())/(A*LIMIT))
        gates.update(body_gravity_XYZ_RMS_1e4=bool((body<=LIMIT).all()),missing_g_formula_gt100=missing>100,doubled_g_formula_gt100=doubled>100)
    rms, maximum = np.sqrt((delta*delta).mean(1)),np.abs(delta).max(1)
    mismatches = (a.view(np.uint64)!=b.view(np.uint64)).sum(1)
    with paths['fields'].open('x',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream); writer.writerow(['part','time_s','column','field','RMS_difference','maximum_absolute_difference','binary64_bit_mismatch_nodes','interpretation'])
        for p,t in enumerate(TIMES):
            for c,name in enumerate(FIELDS):
                writer.writerow([p,t,c,name,rms[p,c],maximum[p,c],int(mismatches[p,c]),'strict_bit_gate' if c in exact_columns else ('descriptive_backend_passive_not_exact_gate' if c==24 and role_b=='CPU_gravity' else 'descriptive_not_new_precision_gate')])
    with paths['history'].open('x',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream); writer.writerow(['part','time_s','pressure_RMS_Pa','velocity_XYZ_RMS_m_s','material_u_XYZ_RMS_m','material_u_max_mm','pressure_RMS_over_Pstar','velocity_RMS_over_A','u_RMS_over_Ustar','body_gravity_RMS_over_A'])
        for p,t in enumerate(TIMES):
            writer.writerow([p,t,pressure[p],velocity[p],displacement[p],umax[p],pressure[p]/PSTAR,velocity[p]/A,displacement[p]/USTAR,'' if body is None else body[p]])
    inputs = ia+ib+[source]
    for item in inputs:
        need(binding(item['path'])==item,'Input changed during offline comparison')
    result = {'stage':'upl_gravity_wall_gpu_pair_r1','passed':all(gates.values()),'model':args.model,'pair':args.pair,'samples':S,'native_ids':N,'columns':C,'roles':['GPU_gravity',role_b],'dt_s':[da,db],'gates':gates,'initial_all33_bit_gate_passed':True,'comparison_space':'soil_accelerating_frame_or_retained_g0_inertial_identity','passive_legacy_rho_bits_equal_descriptive':passive_equal,'passive_legacy_density_wholehistory_cross_backend_exact_gate':role_b!='CPU_gravity','max_pressure_RMS_Pa':float(pressure.max()),'max_velocity_RMS_over_A':float((velocity/A).max()),'max_material_u_RMS_over_Ustar':float((displacement/USTAR).max()),'max_material_u_mm':float(umax.max()),'max_body_gravity_RMS_over_A':None if body is None else float(body.max()),'missing_g_formula_final_over_original_budget':missing,'doubled_g_formula_final_over_original_budget':doubled,'all33_bitwise_equal':bool((mismatches==0).all()),'single_run_metrics':[ma,mb],'inputs':inputs,'files':[binding(paths['history']),binding(paths['fields'])],'native_owned_solver_and_reader_receipts_require_separate_review':True,'saved_face_or_force_stage_observed_by_this_script':False,'public_gravity_accepted':False,'wall_trajectory_accepted':False,'physical_acceptance':False}
    with paths['check'].open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2,allow_nan=False); stream.write('\n')
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError,KeyError,OSError) as error:
        print('GPU tangent-wall pair rejected: '+str(error)); raise SystemExit(1)

