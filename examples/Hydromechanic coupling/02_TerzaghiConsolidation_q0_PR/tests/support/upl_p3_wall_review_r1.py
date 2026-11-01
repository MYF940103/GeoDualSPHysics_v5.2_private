"""Read-only independent wall-r4 receipt/binary review; prints JSON, starts no programs."""
import csv
import hashlib
import json
import math
from pathlib import Path
import struct
import numpy as np
from scipy.linalg import expm

T = Path(__file__).resolve().parent.parent
L = T / 'logs'
O = T / 'outputs'
DP, A, LX, WIDTH = 2.0**-9, 2.0**-9, 0.125, 0.0625
M, B, RHO, RW = 89478488.0 + 4.0 * 134217728.0 / 3.0, 67108864.0 / .25, 2048., 1000.
KAPPA = 2.0 * math.pi / LX
CU = math.sqrt((M+B)/RHO)
PS, US = B*A/CU, A/(CU*KAPPA)

def need(x, text):
    if not bool(x):
        raise AssertionError(text)

def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def rows(p):
    with Path(p).open(newline='', encoding='utf-8-sig') as stream:
        return list(csv.DictReader(stream))

cache, bindings, archives, substituted, visited, retained_names = {}, [], {}, [], set(), {}
def identity(path):
    p = Path(path)
    key = str(p).casefold()
    if key not in cache:
        digest = hashlib.sha256()
        with p.open('rb') as stream:
            for block in iter(lambda: stream.read(1024*1024), b''):
                digest.update(block)
        cache[key] = (p.stat().st_size, digest.hexdigest())
    return cache[key]

def archive_pairs(value):
    if isinstance(value, dict):
        if 'original' in value and 'snapshot' in value:
            a, b = value['original'], value['snapshot']
            if isinstance(a, dict) and isinstance(b, dict) and 'sha256' in a:
                need((a['bytes'],a['sha256']) == (b['bytes'],b['sha256']), 'Archive pair is not exact')
                archives[(a['path'].casefold(),a['sha256'])] = b
        for child in value.values():
            archive_pairs(child)
    elif isinstance(value, list):
        for child in value:
            archive_pairs(child)

for path in L.glob('upl_p3_wall_build_r*.json'):
    archive_pairs(load(path))

def verify(entry):
    expected = (int(entry['bytes']), entry['sha256'].lower())
    actual_path = Path(entry['path'])
    if not actual_path.exists() or identity(actual_path) != expected:
        replacement = archives.get((entry['path'].casefold(), expected[1]))
        if replacement is None:
            name = actual_path.name
            if name not in retained_names:
                retained_names[name] = list(O.rglob(name))
            for candidate in retained_names[name]:
                if candidate.stat().st_size == expected[0] and identity(candidate) == expected:
                    replacement = dict(path=str(candidate), bytes=expected[0], sha256=expected[1])
                    break
        need(replacement is not None, 'Unresolved historical/current binding: '+str(actual_path)+' '+expected[1])
        actual_path = Path(replacement['path'])
        need(identity(actual_path) == expected, 'Archive mismatch: '+str(actual_path))
        substituted.append(dict(original=entry['path'], snapshot=str(actual_path), sha256=expected[1]))
    bindings.append((entry['path'], expected[0], expected[1]))
    return actual_path

def walk(value, parent=''):
    if isinstance(value, dict):
        if {'path','bytes','sha256'} <= set(value):
            actual = verify(value)
            # Do not expand the entire older accepted spatial experiment's mutable build inputs.
            # Its sealed receipt and each retained comparison output are verified directly.
            if actual.suffix.lower() == '.json' and parent not in ('retained_controls','inputs'):
                name = str(actual).casefold()
                if name not in visited:
                    visited.add(name)
                    walk(load(actual))
        else:
            for key, child in value.items():
                walk(child, key)
    elif isinstance(value, list):
        for child in value:
            walk(child, parent)

roots = [L/'upl_p3_wall_wave_ReleaseCPU_r4.check.json', L/'upl_p3_wall_wave_DebugCPU_r4.smoke.check.json',
         L/'upl_p3_wall_build_r3.json', L/'upl_p3_wall_off_r2.check.json',
         L/'upl_p3_wall_periodic_ReleaseCPU_r2.check.json']
for path in roots:
    visited.add(str(path).casefold())
    walk(load(path))
for path in roots[:2]:
    for entry in load(path)['receipts']:
        receipt = load(entry['path'])
        need(receipt['exit_code']==0 and receipt['owned_call_exited'], 'Wall owned call did not exit normally')
for path in L.glob('upl_p2_*_p3_wall_r2*.run.json'):
    job = load(path)
    need(job['exit_code'] == 0 and job['owned_call_exited'], 'OFF owned call did not exit normally')
    walk(job)

def physical(folder):
    path = folder/'physical.bin'
    with path.open('rb') as stream:
        n, c, samples = struct.unpack('<III', stream.read(12))
    need(c == 26, 'Unexpected physical column count')
    need(path.stat().st_size == 12+samples*8*(1+n*c), 'Physical length/trailing frame mismatch')
    data = np.fromfile(path, dtype='<f8', offset=12).reshape(samples, 1+n*c)
    need(np.isfinite(data).all(), 'Nonfinite physical values')
    return data[:,0].copy(), data[:,1:].reshape(samples,n,c).copy()

def reference(time, kh):
    diffusivity = B*kh/(RW*9.80665)
    mat = np.array([[0.,1.,0.,0.], [0.,0.,-KAPPA/RHO,KAPPA/RHO],
                    [0.,M*KAPPA,0.,0.],
                    [0.,-B*KAPPA,-diffusivity*RW*KAPPA*KAPPA/RHO,
                     -diffusivity*KAPPA*KAPPA*(1.-RW/RHO)]])
    return np.array([expm(mat*t) @ np.array([0.,A,0.,0.]) for t in time])

def job_review(name, steps, samples, dt, k0):
    folder = O/name
    done = load(folder/'complete.json')
    t, x = physical(folder)
    need(x.shape == (samples,1024,26), 'Actual wall record shape')
    need(done['steps']==steps and done['samples']==samples and done['dt_actual']==dt and done['actual_end_s']==steps*dt, 'Completion time metadata')
    need(done['passed'] and done['actual_ComputeStep_Sym'] and not done['physical_acceptance'], 'Completion scope')
    need(done['native_ids']==1024 and done['fixed_ids']==256 and done['k0']==k0 and done['smoke']==(samples==3), 'Completion identity/physics')
    need(np.array_equal(t, np.arange(samples)*steps/(samples-1)*dt), 'Actual binary clocks not exact')
    native, fixed = rows(folder/'native_ids.csv'), rows(folder/'fixed_ids.csv')
    ids = np.array([int(r['native_id']) for r in native]); wallids = np.array([int(r['native_id']) for r in fixed])
    need(len(native)==1024 and len(fixed)==256 and len(set(ids)&set(wallids))==0 and set(ids)|set(wallids)==set(range(1280)), 'Real ID ledgers')
    x0 = np.array([[float(r[k]) for k in ['x0','y0','z0']] for r in native])
    need(np.array_equal(x[0,:,:3],x0), 'Initial material coordinate alignment')
    need(np.array_equal(np.sort(np.unique(x0[:,0])),(np.arange(32)+.5)*DP) and np.array_equal(np.sort(np.unique(x0[:,2])),(np.arange(32)+.5)*DP), 'Native 32x32 tensor lattice')
    band = np.minimum(x0[:,0],WIDTH-x0[:,0]) <= float(np.float32(2*1.8*DP))
    need(band.sum()==256 and np.array_equal(band,np.array([int(r['wall_band']) for r in native],bool)), 'Fixed material band')
    need(np.all(x[:,:,0]>0) and np.all(x[:,:,0]<WIDTH) and np.all(x[:,:,7]==0) and np.all(x[:,:,16]==0), 'Elastic/domain/p0')
    j = x[:,:,8]; n = 1.-.75/j; vol = DP*DP*j; rho = RW+(RHO-RW)/j
    need(np.all(j>.75) and np.max(abs(j-1))<=1e-4 and np.max(abs((1-n)*j-.75))<=5e-13, 'J/solid ledger')
    need(np.all((x[:,:,25]>=700)&(x[:,:,25]<=3000)), 'Passive old density')
    kh = 0. if k0 else float(np.float32(.0001))
    need(done['hydraulic_conductivity']==kh, 'Actual k')
    hkernel=float(np.float32(1.8*DP)); current_b=67108864./n
    cu=np.sqrt((M+current_b)/rho); diffusion=current_b*kh/(RW*9.80665)
    need(np.max(cu*dt/hkernel)<=.01 and np.max(diffusion*dt/hkernel**2)<=.01, 'Independent saved-state necessary scales')
    if kh:
        margin=rho*current_b/(M+current_b)-RW
        need(np.all(margin>64*np.finfo(float).eps*np.maximum(rho,RW)) and np.all(dt<=.1*hkernel**2/diffusion), 'Saved-state RH/pore bound')
    ref = reference(t,kh); sn, cs = np.sin(KAPPA*x0[:,0]), np.cos(KAPPA*x0[:,0])
    dp = x[:,:,6]-ref[:,3,None]*cs
    dv = x[:,:,3:6].copy(); dv[:,:,0] -= ref[:,1,None]*sn
    du = x[:,:,:3]-x0; du[:,:,0] -= ref[:,0,None]*sn
    normalized = np.stack([np.sqrt(np.mean(dp*dp,axis=1))/PS,np.sqrt(np.mean(np.sum(dv*dv,axis=2),axis=1))/A,np.sqrt(np.mean(np.sum(du*du,axis=2),axis=1))/US],axis=1)
    banderror = np.stack([np.sqrt(np.mean(dp[:,band]**2,axis=1))/PS,np.sqrt(np.mean(np.sum(dv[:,band]**2,axis=2),axis=1))/A,np.sqrt(np.mean(np.sum(du[:,band]**2,axis=2),axis=1))/US],axis=1)
    need(normalized.max()<=.01 and banderror.max()<=.01, 'Independent full XYZ continuum1%')
    pm = 2*np.mean(x[-1,:,6]*cs); endpoint = pm/ref[-1,3]-1
    if not k0 and samples>3:
        need(abs(endpoint)<=.01, 'Independent endpoint1%')
    sigma = x[:,:,10:16]; tr = sigma[:,:,0]+sigma[:,:,3]+sigma[:,:,5]; mean=tr/3
    dev=(sigma[:,:,0]-mean)**2+(sigma[:,:,3]-mean)**2+(sigma[:,:,5]-mean)**2+2*(sigma[:,:,1]**2+sigma[:,:,2]**2+sigma[:,:,4]**2)
    energy = np.sum(vol*(.5*rho*np.sum(x[:,:,3:6]**2,axis=2)+dev/(4*134217728.)+tr*tr/(18*89478488.)+n*x[:,:,6]**2/(2*67108864.)),axis=1)
    need(np.max(energy/energy[0])<=1.1, 'Independent energy')
    mc = rows(folder/'modes.csv'); need(len(mc)==samples, 'Mode rows')
    reported = np.array([[float(r[k]) for k in ['p_continuum_RMS_over_Pstar','v_continuum_RMS_over_A','u_continuum_RMS_over_Ustar']] for r in mc])
    need(np.max(abs(reported-normalized))<2e-11, 'Expm versus RK4/field reconstruction mismatch')
    policy = rows(folder/'endpoint_policy.csv'); need(len(policy)==steps, 'Every-step policy missing')
    need(all(float(r['used_dt_s'])==dt and dt<=float(r['complete_bound_s']) and abs(float(r['cumulative_fixed_error_s']))<=1e-14 for r in policy), 'Every-step necessary bound')
    need(all(int(r['step'])==i+1 and float(r['time_s'])==(i+1)*dt and float(r['energy_ratio'])<=1.1 for i,r in enumerate(policy)), 'Every-step clocks/energy')
    need(abs(min(float(r['complete_bound_s']) for r in policy)-done['min_endpoint_bound_s'])<=1e-20, 'Complete min-bound metadata')
    audit = rows(folder/'wall_audit.csv'); need(len(audit)==2*samples, 'Missing two-face audit rows')
    qratio=max(abs(float(r['face_qn']))/float(r['qn_bound']) for r in audit) if kh else 0.
    vratio=max(abs(float(r['face_vn']))/float(r['vn_bound']) for r in audit)
    fratio=max(float(r['force_residual'])/float(r['force_bound']) for r in audit)
    need(max(qratio,vratio,fratio)<=1, 'Direct face/instantaneous force audit')
    for it in range(samples):
        need(all(int(r['step'])==it*steps/(samples-1) and float(r['time_s'])==t[it] for r in audit[2*it:2*it+2]), 'Face clocks')
    for prefix, off in [('component',False),('offgrid_component',True)]:
        comp = rows(folder/(prefix+'.csv')); check=load(folder/(prefix+'.check.json'))
        need(len(comp)==256 and check['passed'] and check['nonvacuous']==256 and check['all_normal_bytes_restored'] and check['real_geometry_and_clock_unchanged'], 'Affine component/restore')
        for r in comp:
            td,tf=float(r['double_base_tol']),float(r['float_base_tol'])
            need(float(r['J_error'])<=2*td and float(r['p_error'])<=256*tf and float(r['v_error'])<=tf and float(r['ace_error'])<=tf and float(r['sigma_error'])<=128*td and float(r['C_error'])<=4*td, 'Component original tolerances')
            if off: need(float(r['nearest_distance_m'])==DP/8, 'Off-grid anchor is vacuous')
        if off: need(check['noncoincident_fixed_native']==256, 'Off-grid count')
    return dict(job=name,steps=steps,samples=samples,actual_end_s=float(t[-1]),dt=dt,records=samples*1024,
                full_XYZ_normalized_RMS_max=normalized.max(axis=0).tolist(),wall_band_normalized_RMS_max=banderror.max(axis=0).tolist(),
                endpoint_p_mode_relative_error=float(endpoint),max_energy_ratio=float(np.max(energy/energy[0])),
                expm_vs_saved_metric_max_abs=float(np.max(abs(reported-normalized))),max_face_qn=max(abs(float(r['face_qn'])) for r in audit),
                face_qn_budget_max_ratio=qratio,face_vn_budget_max_ratio=vratio,force_budget_max_ratio=fratio,
                offgrid_samples=256), (t,x)

jobs, traces = [], {}
for label,steps,samples,dt,k0 in [('DebugCPU_r4_smoke',2,3,2.**-25,False),('ReleaseCPU_r4_k0_c',16,17,2.**-25,True),('ReleaseCPU_r4_k0_h',32,17,2.**-26,True),('ReleaseCPU_r4_k1_c',1024,257,2.**-25,False),('ReleaseCPU_r4_k1_h',2048,257,2.**-26,False)]:
    item, trace = job_review('upl_p3_wall_wave_'+label,steps,samples,dt,k0); jobs.append(item); traces[label]=trace

halves=[]
for k in ['k0','k1']:
    tc,c=traces['ReleaseCPU_r4_'+k+'_c'];th,h=traces['ReleaseCPU_r4_'+k+'_h']
    need(np.array_equal(tc,th) and c[0].tobytes()==h[0].tobytes(), 'Half clocks/initial26')
    dp=np.sqrt(np.mean((c[:,:,6]-h[:,:,6])**2,axis=1)); dr=np.linalg.norm(c[:,:,:3]-h[:,:,:3],axis=2)
    dv=np.sqrt(np.mean(np.sum((c[:,:,3:6]-h[:,:,3:6])**2,axis=2),axis=1))/A
    du=np.sqrt(np.mean(dr**2,axis=1))/US
    need(dp.max()<=5 and 1000*dr.max()<=.005 and (dp/PS).max()<=1e-4 and dv.max()<=1e-4 and du.max()<=1e-4, 'Independent all-sample half')
    saved=load(L/('upl_p3_wall_wave_ReleaseCPU_r4_'+k+'_half.check.json'))
    need(abs(saved['max_pressure_RMS_Pa']-dp.max())<1e-15 and abs(saved['max_material_displacement_mm']-1000*dr.max())<1e-18, 'Half receipt remeasurement')
    halves.append(dict(physics=k,samples=len(tc),pressure_RMS_Pa=float(dp.max()),displacement_vector_max_mm=float(1000*dr.max()),velocity_XYZ_RMS_over_A=float(dv.max()),displacement_XYZ_RMS_over_Ustar=float(du.max())))

periodic=load(roots[-1]);need(periodic['solver_jobs']==2 and periodic['native_field_pairs']==2*257*512*26, 'Periodic count')
for entry in periodic['comparisons']:
    compare=load(entry['path'])
    for pair in compare['equal_files']:
        need(identity(pair['current']['path'])==identity(pair['retained']['path']), 'Periodic actual outputs not byte identical')
off=load(L/'upl_p3_wall_off_r2.check.json')
need(sum(g['frames'] for g in off['groups'])==140 and off['exclusions']==0, 'OFF aggregation count')
offframes=0
for group in off['groups']:
    check=load(group['check']['path']);need(check['actual_native_samples']==group['frames'], 'OFF group count')
    for entry in check['receipts']:
        part=load(entry['path']);need(part['native_count']==1040 and part['arrays']==15 and part['all_original_physical_array_bits_identical'] and part['saved_time_step_dterror_exact'] and part['no_exclusions'], 'OFF frame receipt')
        offframes+=1
need(offframes==140, 'OFF frame count')
result=dict(passed=True,offline_only=True,project_solver_started=False,hash_bindings=len(bindings),unique_hashed_files=len(cache),
            historical_snapshot_resolutions=len(substituted),historical_resolution_examples=list({r['original']+r['sha256']:r for r in substituted}.values()),
            hash_mismatches=0,actual_jobs=jobs,independent_halves=halves,wall_records_reviewed=sum(j['records'] for j in jobs),
            off_receipt_frames=offframes,off_arrays_per_frame=15,off_native_ids_per_frame=1040,off_raw_BI4_redecoded_by_this_script=False,
            periodic_field_pairs=2*257*512*26,periodic_exact_output_pairs=8,
            physical_acceptance=False,limitations=['Only the actual private CPU weak elastic fixed parallel FreeSlip/g0/constant-k bounded window is reviewed.',
            'Independent expm/XYZ and half calculations use native physical.bin; raw BI4 OFF comparisons are source-reviewed sealed comparator receipts, not independently reparsed here.',
            'All direct frozen input entries are checked, but JSON inputs are not recursively expanded into older build/prior-program graphs; retained spatial outputs are checked explicitly.',
            'Direct face MLS includes the predeclared truncation budget; saved-point force audits are additional calls and not automatic-stage counters.',
            'Lstar is not generally conservative; no general wall/GPU/plasticity/long-cycle/public-model acceptance follows.'])
print(json.dumps(result,indent=2,allow_nan=False))
