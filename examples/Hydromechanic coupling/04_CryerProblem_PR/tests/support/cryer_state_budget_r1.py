"""Saved CSV state/strain diagnostics only. No BI4, subprocess, integration or source edit."""
import os
for key in ['OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'OMP_NUM_THREADS']:
    os.environ[key] = '1'
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

TESTS = Path(__file__).resolve().parents[1]
TAG = 'cryer_state_budget_r1'
NOTE = TESTS/'notes'/(TAG+'.json')
CHECK = TESTS/'logs'/(TAG+'.check.json')
FIG = TESTS/'figures'
SIGMA = ['sigma_xx', 'sigma_yy', 'sigma_zz', 'sigma_xy', 'sigma_yz', 'sigma_xz']


def bound(path):
    p = Path(path); data = p.read_bytes()
    return dict(path=str(p.resolve()), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def verify(entry):
    assert bound(entry['path']) == entry, 'Changed input: '+entry['path']


def affine(x0, x, weights):
    design = np.column_stack([x0, np.ones(len(x0))]); root = np.sqrt(weights)[:, None]
    coef, _, rank, _ = np.linalg.lstsq(design*root, x*root, rcond=None)
    assert rank == 4, 'Rank-deficient fixed center cloud'
    F, intercept = coef[:3].T, coef[3]; determinant = float(np.linalg.det(F))
    assert determinant > 0, 'Affine log-volume is undefined'
    stretches = np.linalg.svd(F, compute_uv=False)
    return dict(affine_trace_F_minus_I=float(np.trace(F)-3), affine_logdet_F=float(np.log(determinant)),
        affine_det_F=determinant, affine_fit_rms_mm=float(1000*np.sqrt(np.sum(weights*np.sum((design@coef-x)**2, axis=1)))),
        stretch_anisotropy=float(np.linalg.norm(stretches-stretches.mean())),
        intercept_norm_mm=float(1000*np.linalg.norm(intercept)),
        **{'F'+str(i)+str(j):float(F[i,j]) for i in range(3) for j in range(3)},
        **{'intercept_'+k+'_m':float(intercept[i]) for i,k in enumerate('xyz')})


def suffix(a):
    """First index of final exact-equality suffix; not proof of unsaved-step constancy."""
    change = np.flatnonzero(np.any(a[1:] != a[:-1], axis=1))
    first = int(change[-1]+1) if len(change) else 0
    return first, len(a)-first


def selftest():
    x = np.array([[1.,0,0],[-1.,0,0],[0,1.,0],[0,-1.,0],[0,0,1.],[0,0,-1.]])
    w = np.full(6, 1/6); F = np.diag([.99, .98, 1.01]); b = np.array([.1,-.2,.3])
    a = affine(x, x@F.T+b, w)
    assert abs(a['affine_logdet_F']-np.log(np.linalg.det(F))) < 1e-14
    assert a['affine_fit_rms_mm'] < 1e-11 and abs(a['intercept_x_m']-.1) < 1e-14
    rotation = np.array([[0.,-1,0],[1.,0,0],[0,0,1.]])
    r = affine(x, x@rotation.T, w)
    assert abs(r['affine_logdet_F']) < 1e-14 and r['stretch_anisotropy'] < 1e-14
    assert suffix(np.array([[1,2],[2,2],[2,2]])) == (1,2)
    assert suffix(np.ones((3,2))) == (0,3)
    assert np.spacing(np.float32(2100.)) == 2.**-12
    assert float(np.spacing(np.float32(2100.)))/2/(2.**-20) == 128
    print('Pure selftest passed; no files read/written and no child process.')


def run():
    outputs = {k:FIG/(TAG+suffix) for k,suffix in [('history','_history.csv'),('center','_center.csv'),('radial','_radial_stagnation.csv'),('plot','.png')]}
    assert not CHECK.exists() and not any(p.exists() for p in outputs.values()), 'Refuse retained outputs'
    review_path = TESTS/'logs/cryer_full_review_r1.check.json'; review = read(review_path)
    assert review['passed'] and review['analysis_checks_passed'] and review['native_safety_adopted']
    links = {str(Path(e['path']).resolve()):e for e in review['inputs']+review['artifacts']}
    native_path = TESTS/'logs/cryer_full_native_r1.check.json'; verify(links[str(native_path.resolve())]); native = read(native_path)
    assert native['passed'] and native['native_safety_passed'] and native['checked_frames'] == 1065
    paths = {k:FIG/('cryer_full_native_r1_'+k+'.csv') for k in ['center','radial','summary','initial_cloud']}
    paths['history'] = FIG/'cryer_full_review_r1_history.csv'
    for path in paths.values(): verify(links[str(path.resolve())])
    for e in native['artifacts']:
        if Path(e['path']).resolve() in paths.values(): assert e == links[str(Path(e['path']).resolve())]
    finite_path = TESTS/'logs/cryer_finite_storage_r1.check.json'; note = read(NOTE)
    assert bound(finite_path)['sha256'] == note['finite_reference_sha256']
    finite = read(finite_path); assert finite['analysis_checks_passed'] and finite['reference_derivation_verified']
    parameters = finite['numeric_reference']['parameters']; K = parameters['K']; dt = review['server_dt_s']
    assert K == parameters['E']/(3*(1-2*parameters['nu'])) and dt == 2.**-20
    inputs = [bound(p) for p in [Path(__file__),NOTE,review_path,native_path,finite_path]]+[links[str(p.resolve())] for p in paths.values()]
    stamps = {e['path']:(Path(e['path']).stat().st_size,Path(e['path']).stat().st_mtime_ns) for e in inputs}
    data = {k:pd.read_csv(p,float_precision='round_trip') for k,p in paths.items()}
    h = data['history'].loc[lambda a:a.dataset.eq('server')].sort_values('part').reset_index(drop=True)
    summary = data['summary'].sort_values('part').reset_index(drop=True); center = data['center'].sort_values(['part','id']).reset_index(drop=True)
    ids = np.asarray(native['center_fixed_material_ids']); ids.sort(); cloud = data['initial_cloud'].set_index('id').loc[ids]
    assert len(h) == len(summary) == 1065 and len(center) == 1065*18 and not center.duplicated(['part','id']).any()
    assert np.array_equal(h.part,np.arange(1065)) and np.array_equal(summary[['part','time_s','saved_step']],h[['part','time_s','saved_step']])
    assert np.array_equal(center.id.to_numpy().reshape(1065,18),np.tile(ids,(1065,1)))
    assert np.array_equal(center.time_s.to_numpy().reshape(1065,18),np.repeat(h.time_s.to_numpy()[:,None],18,axis=1))
    assert np.array_equal(center.saved_step.to_numpy().reshape(1065,18),np.repeat(h.saved_step.to_numpy()[:,None],18,axis=1))
    x0 = cloud[['x0','y0','z0']].to_numpy(); rho0 = np.tile(cloud.rho0.to_numpy(),1065); weights = cloud.volume0_m3.to_numpy(); weights /= weights.sum()
    stress = center[SIGMA].to_numpy(); assert np.isfinite(stress).all() and center.rho.gt(0).all()
    assert np.array_equal(center.loc[center.part.eq(0),['x','y','z']],x0)
    center['epsv_rho_log'] = -np.log(center.rho.to_numpy()/rho0)
    sigma_trace = stress[:,:3].sum(axis=1).reshape(1065,18)
    center['epsv_sigma_increment'] = ((sigma_trace-sigma_trace[0])/(3*K)).ravel()
    rows = []
    for part, a in center.groupby('part',sort=True):
        row = dict(part=int(part),time_s=float(a.time_s.iloc[0]),saved_step=int(a.saved_step.iloc[0]))
        row.update(affine(x0,a[['x','y','z']].to_numpy(),weights))
        for col in ['rho','pressure','epsv_rho_log','epsv_sigma_increment']: row[col+'_mean'] = float(weights@a[col].to_numpy())
        rows.append(row)
    result = pd.DataFrame(rows); result['tau_s'] = h.tau_s; result['legacy_Tv'] = h.legacy_Tv
    result['finite_radius_pressure_pa'] = h.finite_radius_pressure_pa
    result['global_rho_mean_kg_m3'] = summary.rho_mean_kg_m3
    result['rho_minus_initial_kg_m3'] = result.rho_mean-result.rho_mean.iloc[0]
    result['global_rho_minus_initial_kg_m3'] = result.global_rho_mean_kg_m3-result.global_rho_mean_kg_m3.iloc[0]
    result['epsv_sigma_minus_rho'] = result.epsv_sigma_increment_mean-result.epsv_rho_log_mean
    span = result.time_s.diff(); result['secant_left_time_s'] = result.time_s.shift(); result['secant_interval_s'] = span
    for col in ['pressure_mean','rho_mean','epsv_rho_log_mean','epsv_sigma_increment_mean','affine_logdet_F']:
        result['saved_interval_secant_'+col+'_per_s'] = result[col].diff()/span
    assert span.iloc[1:].gt(0).all()
    radial = data['radial'].loc[lambda a:a['count'].gt(0)].copy(); radial_rows = []
    rho_cols = ['rho_'+s+'_kg_m3' for s in ['mean','rms','std','min','max']]
    for index, a in radial.groupby('r0_bin',sort=True):
        a = a.sort_values('part'); assert len(a) == 1065 and np.array_equal(a.time_s,h.time_s)
        first, count = suffix(a[rho_cols].to_numpy()); last = a.iloc[-1]
        radial_rows.append(dict(r0_bin=int(index),native_nodes=int(last['count']),r0_mean_m=float(last.r0_mean_m),constant_statistics_from_part=int(a.part.iloc[first]),constant_saved_states=count,
            constant_statistics_from_time_s=float(a.time_s.iloc[first]),**{c:float(last[c]) for c in rho_cols}))
    assert len(radial_rows) == 20
    cfirst, ccount = suffix(center.rho.to_numpy().reshape(1065,18))
    for path, stamp in stamps.items(): assert (Path(path).stat().st_size,Path(path).stat().st_mtime_ns) == stamp
    for key, table in [('history',result),('center',center),('radial',pd.DataFrame(radial_rows))]: table.to_csv(outputs[key],index=False,float_format='%.17g',mode='x')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2,3,figsize=(16,9),constrained_layout=True); t = result.time_s
    panels = [(['pressure_mean','finite_radius_pressure_pa'],1e-3,'Center pressure (kPa)'),
        (['epsv_rho_log_mean','epsv_sigma_increment_mean','affine_logdet_F','affine_trace_F_minus_I'],1e3,'Volumetric measures (10^-3)'),
        (['rho_minus_initial_kg_m3','global_rho_minus_initial_kg_m3'],1.,'Density change (kg/m3)'),
        (['affine_fit_rms_mm','intercept_norm_mm'],1.,'Affine fit / translation (mm)'),
        (['stretch_anisotropy'],1e3,'Stretch anisotropy (10^-3)'),
        (['saved_interval_secant_pressure_mean_per_s'],1e-3,'Saved-interval pressure secant (kPa/s)')]
    td = float((h.time_s-h.tau_s).iloc[0])
    for ax,(columns,scale,label) in zip(axes.ravel(),panels):
        for col in columns: ax.plot(t,result[col]*scale,label=col,linewidth=1.2)
        ax.axvline(td,color='0.5',linestyle=':',linewidth=.8); ax.set(xlabel='Actual saved time t (s)',ylabel=label); ax.grid(alpha=.25); ax.legend(fontsize=7)
    fig.suptitle('Cryer saved-state density and deformation budget. Secants are not integrator RHS.'); fig.savefig(outputs['plot'],dpi=220); plt.close(fig)
    receipt = dict(analysis_checks_passed=True,inputs=inputs,artifacts=[bound(p) for p in outputs.values()],saved_states=1065,center_ids=ids.astype(int).tolist(),
        K_pa=K,dt_s=dt,center_density_constant_from_part=cfirst,center_constant_saved_states=ccount,nonempty_radial_layers=20,
        density_ulp_near_2100_kg_m3=2.**-12,full_step_half_ulp_rate_kg_m3_s=128.,predictor_half_step_half_ulp_rate_kg_m3_s=256.,
        limitations=note['limitations'],native_safety_adopted=True,solver_program_attribution_proven=False,physical_acceptance=False,full_cycle_acceptance=False,solver_started=False)
    with CHECK.open('x',encoding='utf8') as f: json.dump(receipt,f,indent=2,allow_nan=False)
    print(json.dumps(dict(check=str(CHECK),saved_states=1065,physical_acceptance=False)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); group = parser.add_mutually_exclusive_group()
    group.add_argument('--selftest',action='store_true'); group.add_argument('--run',action='store_true'); args = parser.parse_args()
    if args.selftest: selftest()
    elif args.run: run()
    else: parser.print_help()
