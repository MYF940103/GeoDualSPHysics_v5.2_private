"""One offline, exact-time 33-field pair. No solver, interpolation or field masking."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import numpy as np

N, C, S = 512, 33, 257
DC, DH, CAD, END = 2.0**-24, 2.0**-25, 2.0**-23, 2.0**-15
TIMES = np.arange(S, dtype=np.float64)*CAD
A, PSTAR, USTAR, GX = 2.0**-9, 1023.9999974568686, 7.589099058944216e-8, -8.0
LIMIT, DP, N0, RHO0, RHOW, KW = 1e-4, 2.0**-8, .25, 2048., 1000., 67108864.
V0, BULK, SHEAR, K0, CK = DP*DP, 89478488., 134217728., float(np.float32(1e-4)), 2.0**-13
H, EPS = float(np.float32(1.8*DP)), np.finfo(np.float64).eps
FIELDS = ['x','y','z','vx','vy','vz','p','p0','J','theta_last_stage','sigma_xx','sigma_xy','sigma_xz','sigma_yy','sigma_yz','sigma_zz','plastic','FSType','normal_x','normal_y','normal_z','load_x','load_y','load_z','passive_legacy_Rhop','material_u_x','material_u_y','material_u_z','native_float_excess','native_n','derived_current_V','derived_mixture_rho','derived_current_k']
EXACT = [7, 16, 21, 22, 23, 24]  # Admission note; no added FSType/normal precision gate.
BOUND = {}

def need(ok, message):
    if not bool(ok):
        raise ValueError(message)

def entry(path):
    path = Path(path).resolve(); digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}

def verify(item):
    need(isinstance(item, dict) and {'path','bytes','sha256'} <= item.keys(), 'Explicit E binding required')
    expected = {'path': str(Path(item['path']).resolve()), 'bytes': item['bytes'], 'sha256': item['sha256'].lower()}
    key = expected['path'].casefold()
    if key not in BOUND:
        need(entry(expected['path']) == expected, 'Changed artifact: '+expected['path']); BOUND[key] = expected
    else:
        need(BOUND[key] == expected, 'Conflicting binding: '+expected['path'])
    return Path(expected['path'])

def read_json(path):
    with Path(path).open(encoding='utf-8-sig') as stream:
        return json.load(stream, parse_constant=lambda s: (_ for _ in ()).throw(ValueError('Nonfinite JSON: '+s)))

def table(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream); rows = list(reader)
        need(reader.fieldnames and len(reader.fieldnames) == len(set(reader.fieldnames)), 'Invalid CSV header')
    return rows

def values(rows, key):
    result = np.asarray([float(row[key]) for row in rows], dtype=np.float64)
    need(np.isfinite(result).all(), 'Nonfinite CSV: '+key); return result

def owned(item):
    call = read_json(verify(item))
    need(call.get('owned_call_exited') is True and call.get('exit_code') == 0, 'Owned native exit0 required')
    if 'typed_LASTEXITCODE_captured_immediately' in call:
        need(call['typed_LASTEXITCODE_captured_immediately'] is True, 'Typed native exit missing')
    verify(call['program']); verify(call['log']); return call

def proof(folder, check_path, gravity, dt):
    verify(entry(check_path)); check = read_json(check_path)
    need(check.get('passed') is True and check.get('physical_acceptance') is False, 'Passed bounded single-run check required')
    files = {str(verify(x)).casefold() for x in check['files']}
    required = ['completion.json','physical.bin','native_ids.csv','history.csv']+(['frame.bin'] if gravity else [])
    need(all(str((folder/x).resolve()).casefold() in files for x in required), 'Review exports not check-bound')
    need(verify(check['completion']) == folder/'completion.json', 'Wrong completion folder')
    reader = owned(check['reader_call'] if gravity else check['call']); argv = reader['arguments']
    if gravity:
        need(len(argv) == 5 and argv[:2] == ['--read', 'coarse' if dt == DC else 'half'], 'Wrong private reader window')
        data, xml, target = map(Path, argv[2:5])
    else:
        need(len(argv) == 7 and argv[:3] == ['--read','variable','CPU'] and float(argv[4]) == dt, 'Wrong retained CPU variable reader')
        data, xml, target = Path(argv[3]), Path(argv[5]), Path(argv[6])
    need(target.resolve() == folder, 'Reader target does not match supplied review')
    source = read_json(verify(check['source_run'])); need(source.get('owned_solver_exit0') is True, 'Sealed completed solver required')
    solver = owned(source['call'])
    if gravity:
        need(solver.get('actual_solver_call') is True and reader.get('pure_reader_only') is True, 'Actual solve/pure reader provenance required')
        actual = read_json(verify(check['actual_complete']))
        need(actual.get('passed') is True and actual.get('actual_production_Run') is True and actual.get('gravity_x_m_s2') == GX and actual.get('physical_fields_rewritten_by_fixture') is False and actual.get('predictor_histories_released') is True, 'Actual private Run/gravity completion required')
    raw_files = {str(verify(x)).casefold() for x in source['files']}
    parts = {str((data/f'Part_{p:04}.bi4').resolve()).casefold() for p in range(S)}
    need({str(p.resolve()).casefold() for p in data.glob('Part_*.bi4')} == parts and parts <= raw_files, '257 original raw PART bindings required')
    for record in (check, source):
        for key in ('helper','source_build','input','preflight','canonical_CPU_build'):
            if record.get(key):
                verify(record[key])  # Do not recursively reinterpret historical mutable source/Git metadata.
    inputs = source.get('selected_input', {})
    if gravity:
        preflight = read_json(verify(check['preflight'])); seed = preflight['inputs']
    else:
        seed = [inputs['xml'], inputs['bi4']]
    seed_paths = [verify(x) for x in seed]
    need(xml.resolve() in seed_paths and any(x['sha256'].lower() == '364c4421a8b539d0e8e5eb67e00c547657c9c65f48cd7e83168a4ad32cd5a8fa' and x['bytes'] == 23948 for x in seed), 'Exact runtime/retained geometry not bound')

def binary(path):
    need(path.stat().st_size == 12+S*(1+N*C)*8, 'Truncated/trailing binary')
    with path.open('rb') as stream:
        need(struct.unpack('<III', stream.read(12)) == (N,C,S), 'Expected512 x33 x257 schema')
    raw = np.fromfile(path, dtype='<f8', offset=12).reshape(S,1+N*C)
    need(np.isfinite(raw).all() and np.array_equal(raw[:,0], TIMES), 'All finite exact saved times required; no interpolation')
    return raw[:,1:].reshape(S,N,C)

def load(folder, check_path, gravity, dt):
    folder = folder.resolve(); proof(folder, check_path, gravity, dt); done = read_json(folder/'completion.json')
    need(done.get('passed') is True and done.get('native_count') == N and done.get('fixed_count') == 0 and done.get('samples') == S and done.get('common_columns') == C and done.get('dt_s') == dt and done.get('cadence_s') == CAD and done.get('actual_end_s') == END, 'Single-run schema/clock differs')
    need(done.get('backend') == ('CPU_private' if gravity else 'CPU'), 'Backend attribution differs')
    if gravity:
        need(done.get('stage') == 'upl_gravity_periodic_cpu_r1' and done.get('native_J_arrays') == 3 and done.get('V_rho_k_derived_not_native') is True and done.get('public_dynamic_metadata') is False, 'Private three-J schema required')
    else:
        need(done.get('model') == 'variable' and done.get('native_J_arrays') == 6 and done.get('conductivity_Ck') == CK, 'Retained native CPU variable-law schema required')
    lab = binary(folder/'physical.bin'); q = binary(folder/'frame.bin') if gravity else lab
    if gravity:
        transformed = lab.copy(); transformed[:,:,0] -= (.5*GX*TIMES*TIMES)[:,None]; transformed[:,:,3] -= (GX*TIMES)[:,None]; transformed[:,:,25] -= (.5*GX*TIMES*TIMES)[:,None]
        need(np.array_equal(transformed.view(np.uint64), q.view(np.uint64)), 'Frame export is not exactly its declared transform')
    ids, history = table(folder/'native_ids.csv'), table(folder/'history.csv')
    need(len(ids) == N and len(history) == S and np.array_equal(values(ids,'row'),np.arange(N)) and np.array_equal(values(ids,'id'),np.arange(N)), 'Exact native row/ID alignment required')
    x0 = np.column_stack([values(ids,k) for k in ('x0','y0','z0')]); need(np.array_equal(x0.view(np.uint64),lab[0,:,:3].copy().view(np.uint64)), 'Material reference differs')
    step = np.rint(TIMES/dt).astype(np.int64)-1; step[0] = 0
    need(np.array_equal(values(history,'part'),np.arange(S)) and np.array_equal(values(history,'time_s'),TIMES) and np.array_equal(values(history,'saved_step'),step) and np.array_equal(values(history,'dt_s'),np.full(S,dt)), 'Native history time/step/lockedDt differs')
    need((values(history,'signed_dterror_s' if gravity else 'dterror_s') <= 1e-14).all(), 'Original signed fixed-step safety failed')
    consistency = float(np.abs(q[:,:,25:28]-(q[:,:,:3]-x0)).max()); need(consistency <= 16*EPS, 'Material-u/position consistency beyond binary64 roundoff')
    j, n = q[:,:,8], q[:,:,29]; rn=1-(1-N0)/j; rv=V0*j; rr=RHOW+(RHO0-RHOW)/j; rk=K0*np.exp((j-1)/((1-N0)*CK))
    ledger = np.stack([np.abs(n-rn)/rn,np.abs(q[:,:,30]-rv)/rv,np.abs(q[:,:,31]-rr)/rr,np.abs(q[:,:,32]-rk)/rk])
    need((j>1-N0).all() and (np.abs(j-1)<=1e-4).all() and (n>0).all() and (n<1).all() and np.isfinite(ledger).all() and (ledger<=5e-13).all() and (np.abs((1-n)*j-(1-N0))<=5e-13).all(), 'Original independent saturated ledger/domain failed')
    need((q[:,:,7]==0).all() and (q[:,:,16]==0).all() and (q[:,:,21:24]==0).all() and (q[:,:,24]>=700).all() and (q[:,:,24]<=3000).all(), 'Original p0/plastic/load/passive-density safety failed')
    need(np.array_equal(q[:,:,28],(q[:,:,6].astype(np.float32)-q[:,:,7].astype(np.float32)).astype(np.float32).astype(float)), 'Native float excess inconsistent')
    trace=q[:,:,10]+q[:,:,13]+q[:,:,15]; dev=((q[:,:,[10,13,15]]-trace[:,:,None]/3)**2).sum(2)+2*(q[:,:,[11,12,14]]**2).sum(2)
    energy=(rv*(.5*rr*(q[:,:,3:6]**2).sum(2)+dev/(4*SHEAR)+trace**2/(18*BULK)+n*q[:,:,6]**2/(2*KW))).sum(1); ratio=energy/energy[0]
    cu=np.sqrt((BULK+4*SHEAR/3+KW/rn)/rr)*dt/H; diff=KW/rn*rk/(RHOW*9.80665)*dt/(H*H); margin=rr*(KW/rn)/(BULK+4*SHEAR/3+KW/rn)-RHOW
    need(energy[0]>0 and np.isfinite(ratio).all() and (ratio<=1.1).all() and (cu<=.01).all() and (diff<=.01).all() and (margin>64*EPS*np.maximum(rr,RHOW)).all(), 'Original energy/necessary saved-step/domain guard failed')
    return {'q':q,'lab':lab,'x0':x0,'ledger':float(ledger.max()),'energy':float(ratio.max()),'material_consistency_m':consistency}

def rms_vector(value):
    return np.sqrt((value*value).sum(2).mean(1))

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--pair',required=True,choices=['half','frame_c','frame_h'])
    for name in ('a','b','a-check','b-check','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--figure',action='store_true'); args=parser.parse_args()
    prefix=args.out.resolve(); figure_prefix=Path(__file__).resolve().parents[1]/'figures'/prefix.name
    paths={'check':Path(str(prefix)+'.check.json'), **{key:Path(str(figure_prefix)+suffix) for key,suffix in {'history':'.csv','fields':'_fields.csv','figure':'.png'}.items()}}
    need(prefix.parent.is_dir() and figure_prefix.parent.is_dir() and not any(path.exists() for path in paths.values()), 'Fresh log/figure output prefix required')
    admission=Path(__file__).resolve().parents[1]/'notes'/'upl_gravity_periodic_admission_r1.json'; verify(entry(admission)); declared=read_json(admission)
    need(declared['predeclared_comparisons']['scales']=={'velocity_m_s':A,'pressure_Pa':PSTAR,'material_displacement_m':USTAR,'normalized_limit':LIMIT} and declared['physical_acceptance'] is False, 'Prior admission scales/scope changed')
    verify(entry(__file__)); verify(entry(Path(__file__).resolve().parents[1]/'notes'/'upl_gravity_periodic_compare_r1.json'))
    da=DC if args.pair in ('half','frame_c') else DH; db=DH if args.pair=='half' else da
    left=load(args.a,args.a_check,True,da); right=load(args.b,args.b_check,args.pair=='half',db); x,y=left['q'],right['q']; delta=x-y
    need(np.array_equal(left['x0'].view(np.uint64),right['x0'].view(np.uint64)) and np.array_equal(x[0].view(np.uint64),y[0].view(np.uint64)), 'Exact common material IDs/initial33 state required')
    prms=np.sqrt((delta[:,:,6]**2).mean(1)); vrms=rms_vector(delta[:,:,3:6]); urms=rms_vector(delta[:,:,25:28]); umax=1000*np.linalg.norm(delta[:,:,25:28],axis=2).max(1)
    pair_consistency=float(np.abs(delta[:,:,25:28]-delta[:,:,:3]).max()); exact=bool(np.array_equal(x[:,:,EXACT].copy().view(np.uint64),y[:,:,EXACT].copy().view(np.uint64)))
    gates={'pressure_RMS_5Pa':bool((prms<=5).all()),'material_u_max_0p005mm':bool((umax<=.005).all()),'pressure_normalized_1e4':bool((prms/PSTAR<=LIMIT).all()),'velocity_normalized_1e4':bool((vrms/A<=LIMIT).all()),'material_u_normalized_1e4':bool((urms/USTAR<=LIMIT).all()),'fixed_p0_plastic_load_legacyrho_bits_exact':exact,'position_u_difference_consistent':bool(pair_consistency<=32*EPS)}
    body=np.full(S,np.nan); missing=None
    if args.pair!='half':
        dv=left['lab'][:,:,3:6]-right['lab'][:,:,3:6]; expected=np.zeros((S,1,3)); expected[:,0,0]=GX*TIMES
        body=rms_vector(dv-expected)/A; missing=float(np.sqrt((dv[-1]**2).sum(1).mean())/(A*LIMIT)); doubled=float(np.sqrt(((dv[-1]-2*expected[-1])**2).sum(1).mean())/(A*LIMIT))
        gates.update(body_gravity_native_XYZ_RMS_1e4=bool((body<=LIMIT).all()),missing_g_formula_negative_gt100=missing>100,doubled_g_formula_negative_gt100=doubled>100)
    else:
        doubled=None
    field_rms=np.sqrt((delta*delta).mean(1)); field_max=np.abs(delta).max(1); field_mean=delta.mean(1); mismatches=(x.view(np.uint64)!=y.view(np.uint64)).sum(1)
    with paths['fields'].open('x',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream); writer.writerow(['part','time_s','column','field','RMS_difference','maximum_absolute_difference','mean_signed_difference','binary64_bit_mismatch_nodes','interpretation'])
        for p,t in enumerate(TIMES):
            for c,name in enumerate(FIELDS):
                writer.writerow([p,t,c,name,field_rms[p,c],field_max[p,c],field_mean[p,c],int(mismatches[p,c]),'strict_bit_gate' if c in EXACT else 'all_fields_report_not_independent_accuracy_acceptance'])
    with paths['history'].open('x',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream); writer.writerow(['part','time_s','pressure_RMS_Pa','velocity_XYZ_RMS_m_s','material_u_XYZ_RMS_m','material_u_max_mm','pressure_RMS_over_Pstar','velocity_RMS_over_A','u_RMS_over_Ustar','body_gravity_XYZ_RMS_over_A'])
        for p,t in enumerate(TIMES): writer.writerow([p,t,prms[p],vrms[p],urms[p],umax[p],prms[p]/PSTAR,vrms[p]/A,urms[p]/USTAR,'' if args.pair=='half' else body[p]])
    if args.figure:
        import matplotlib; matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(3,1,figsize=(7,7),sharex=True)
        for ax,data,label in zip(axes,[prms/PSTAR,vrms/A,urms/USTAR],['Pressure RMS / Pstar','Velocity RMS / A','Material u RMS / Ustar']): ax.plot(TIMES*1e6,data); ax.axhline(LIMIT,color='r',ls='--',label='prior limit'); ax.set_ylabel(label); ax.grid(alpha=.25); ax.ticklabel_format(axis='y',style='sci',scilimits=(0,0))
        axes[0].set_title('Private CPU gravity: '+args.pair+' (bounded field comparison)'); axes[-1].set_xlabel('Actual saved time [microseconds]'); axes[0].legend(); fig.tight_layout(); fig.savefig(paths['figure'],dpi=170); plt.close(fig)
    for item in BOUND.values(): need(entry(item['path'])==item,'Input changed during offline analysis')
    files=[entry(paths['history']),entry(paths['fields'])]+([entry(paths['figure'])] if args.figure else [])
    result={'passed':all(gates.values()),'stage':'upl_gravity_periodic_compare_r1','pair':args.pair,'samples':S,'native_ids':N,'columns':C,'gates':gates,'max_pressure_RMS_Pa':float(prms.max()),'max_velocity_RMS_over_A':float((vrms/A).max()),'max_material_u_RMS_over_Ustar':float((urms/USTAR).max()),'max_material_u_mm':float(umax.max()),'max_body_gravity_XYZ_RMS_over_A':None if args.pair=='half' else float(body.max()),'missing_g_formula_final_over_original_budget':missing,'doubled_g_formula_final_over_original_budget':doubled,'position_u_difference_consistency_m':pair_consistency,'single_run_independent_checks':[{'max_ledger_relative_error':z['ledger'],'max_frame_energy_ratio':z['energy'],'material_position_consistency_m':z['material_consistency_m']} for z in (left,right)],'all_33_raw_bitwise_equal':bool((mismatches==0).all()),'all_33_field_accuracy_acceptance_claimed':False,'non_gated_fields_are_descriptive':True,'negative_controls_are_formula_only_not_faulty_solver_runs':True,'saved_flux_or_force_stage_independently_observed':False,'inputs':list(BOUND.values()),'files':files,'public_gravity_accepted':False,'wall_gravity_accepted':False,'physical_acceptance':False}
    with paths['check'].open('x',encoding='utf-8') as stream: json.dump(result,stream,indent=2,allow_nan=False); stream.write('\n')
    return 0 if result['passed'] else 1

if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (ValueError,KeyError,OSError) as error:
        print('Offline comparison rejected: '+str(error),file=sys.stderr); raise SystemExit(1)
