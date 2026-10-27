"""Offline radial static patch on saved Cryer geometry; explicit --run only."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import traceback
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from cryer_load_pair_r1 import (CASE, TESTS, REPO, LIAN, READER, Q, R, DP,
    VARIANTS, AFFINE_L, native, bound, write_json, batches, correction,
    pair_components, add_pair, force_metrics, selftest)

TAG = 'cryer_radial_patch_r1'
E, NU = 2e6, .3
K = E/(3*(1-2*NU))
G = E/(2*(1+NU))
LAM = K-2*G/3
M = K+4*G/3
P_OVER_Q = [0., .6, 1.2]


def field(x, peak):
    """Tension-positive Hooke stress from the prescribed smooth radial u."""
    r2 = np.sum(x*x, axis=1)
    c = (-3*M*Q+8*G*peak/5)/(3*K)
    ur = (c+peak)/(3*M)-peak*r2/(5*M*R*R)
    uprime = (c+peak)/(3*M)-3*peak*r2/(5*M*R*R)
    eps = (c+peak-peak*r2/(R*R))/M
    srr, stt = 2*G*uprime+LAM*eps, 2*G*ur+LAM*eps
    outer = x[:, :, None]*x[:, None, :]
    radial_tensor = outer/np.where(r2 > 0, r2, 1)[:, None, None]
    sigma = stt[:, None, None]*np.eye(3)+(srr-stt)[:, None, None]*radial_tensor
    pressure = peak*(1-r2/(R*R))
    return sigma, pressure, dict(c_pa=c, ur=ur, uprime=uprime, eps=eps)


def analytic_checks():
    x = np.array([[0., 0., 0.], [.011, -.013, .017], [R, 0., 0.]])
    evidence = []
    for ratio in P_OVER_Q:
        p0 = ratio*Q
        sigma, p, f = field(x, p0)
        h = 4*G*p0/(5*M)
        r2 = np.sum(x*x, axis=1)
        total = sigma-p[:, None, None]*np.eye(3)
        polynomial = ((-Q-h+2*h*r2/R**2)[:, None, None]*np.eye(3)
            -h/R**2*x[:, :, None]*x[:, None, :])
        # Differentiate the Hooke-derived r² coefficients, including -grad(p).
        trr_r2 = -(6*G+5*LAM)*p0/(5*M*R**2)+p0/R**2
        radial_divergence = (2*trr_r2-8*G*p0/(5*M*R**2))*np.sqrt(r2)
        errors = dict(stress_polynomial_max_pa=float(np.abs(total-polynomial).max()),
            strain_trace_max=float(np.abs(f['uprime']+2*f['ur']-f['eps']).max()),
            surface_traction_error_pa=float(abs(total[-1, 0, 0]+Q)),
            surface_pressure_pa=float(p[-1]),
            analytic_div_total_max_pa_m=float(np.abs(radial_divergence).max()))
        assert errors['stress_polynomial_max_pa'] < 1e-9
        assert errors['strain_trace_max'] < 1e-14
        assert errors['surface_traction_error_pa'] < 1e-9 and p[-1] == 0
        assert errors['analytic_div_total_max_pa_m'] < 1e-8
        evidence.append(dict(p_over_q=ratio, **errors))
    s0, p0, _ = field(x, 0.)
    s1, p1, _ = field(x, .6*Q)
    s2, p2, _ = field(x, 1.2*Q)
    assert np.allclose(s0, -Q*np.eye(3), rtol=0, atol=1e-10)
    assert np.allclose(s1-s0, .5*(s2-s0), rtol=0, atol=1e-10)
    assert np.array_equal(p1, .5*p2) and not p0.any()
    return dict(implementation_checks_passed=True, cases=evidence,
        identity='Trr=-q-H+H r²/a²; Ttt=-q-H+2H r²/a²; H=4GP/(5M).',
        uniform_and_linear_P_checks=True,
        note='Analytic algebra checks only; no discrete-force or physical accuracy threshold.')


def regional(values, mask, volume):
    a = values[mask]
    norm = np.linalg.norm(a, axis=1)
    return dict(count=int(mask.sum()), native_volume_m3=float(volume[mask].sum()),
        component_rms_m_s2=float(np.sqrt(np.mean(a*a))),
        vector_rms_m_s2=float(np.sqrt(np.mean(norm*norm))),
        volume_weighted_vector_rms_m_s2=float(np.sqrt(np.average(norm*norm, weights=volume[mask]))),
        vector_max_m_s2=float(norm.max()))


def main():
    target = TESTS/'logs'/(TAG+'.check.json')
    csv = TESTS/'figures'/(TAG+'_metrics.csv')
    assert not target.exists() and not csv.exists(), 'Never overwrite retained evidence'
    started = time.perf_counter()
    result = dict(scope='Offline nonuniform static manufactured fields on one saved geometry.',
        physical_acceptance=False, production_implemented=False, solver_executed=False,
        analysis_checks_passed=False)
    rows = []
    try:
        folder = TESTS/'outputs/cryer_grad_peak_r1'
        peak_check = TESTS/'logs/cryer_grad_peak_r1.check.json'
        assert json.loads(peak_check.read_text())['passed']
        inputs = [Path(__file__), TESTS/'notes'/(TAG+'.md'),
            Path(__file__).with_name('cryer_load_pair_r1.py'), READER,
            LIAN/'lian_release_r1.py', LIAN/'read_hydro_native.cpp',
            folder/'data/Part_0000.bi4', peak_check,
            TESTS/'logs/cryer_grad_peak_r1.run.json',
            TESTS/'configs/cryer_grad_peak_r1_Def.xml',
            REPO/'bin/windows/DualSPHysics5.2_GEO_win64.exe']
        inputs += [REPO/'src/source'/n for n in ['JSphCpu.cpp', 'JSphGpu_ker.cu',
            'JSph.cpp', 'JSphCpuSingle.cpp', 'FunSphKernel.h', 'DualSphDef.h']]
        for name in ['a-coupled-u-p-sph-formulation-for-hydromechanical-modeling-of-retrogressive-landslides-and-comparison-with-a-penalty-based-approach',
                     '2019 - Zhao - A generic approach to modelling flexible confined boundary conditions in SPH and']:
            inputs += [REPO/'src/papers/PDF'/(name+'.pdf'), REPO/'src/papers/u-pw'/(name+'.md')]
        result['inputs'] = [bound(p) for p in inputs]
        result['analytic'] = analytic_checks()
        result['pair_arithmetic_selftest'] = selftest()
        a = native(folder, 0)
        assert len(a) == 37173 and a.id.nunique() == len(a)
        assert np.isfinite(a.to_numpy(dtype='<f8')).all()
        assert a.position_double.eq(1).all() and a.rho.eq(2100).all()
        assert a.nout.eq(0).all() and a.kplastic.eq(0).all()
        x = a[['x', 'y', 'z']].to_numpy()
        mass, rho = a.mass.to_numpy(), a.rho.to_numpy()
        h = float(a.h.iloc[0]); radius = np.linalg.norm(x, axis=1); volume = mass/rho
        masks = dict(whole=np.ones(len(a), dtype=bool), center=radius<=DP+1e-12,
            interior=radius<R-2*h, outer_shell=radius>=R-2*h,
            true_surface=a.fstype.isin([2, 3]).to_numpy())
        assert masks['center'].sum() == 18 and all(mask.any() for mask in masks.values())
        result['native_identity'] = dict(soil_count=len(a), actual_time_s=float(a.time_s.iloc[0]),
            ids_sha256=hashlib.sha256(a.id.to_numpy(dtype='<u4').tobytes()).hexdigest(),
            center_ids=list(map(int, a.id[masks['center']])), initial_position_double=1,
            fstype_counts={str(int(k)):int(v) for k,v in a.fstype.value_counts().items()},
            rho_kg_m3=2100., h_m=h, native_volume_m3=float(volume.sum()),
            geometric_volume_m3=4*np.pi*R**3/3)
        pairs = cKDTree(x).query_pairs(2*h, output_type='ndarray')
        corr, matrix = correction(x, mass, rho, h, pairs)
        result.update(pair_count=len(pairs), correction=matrix,
            material=dict(E_pa=E, nu=NU, K_pa=K, G_pa=G, lambda_pa=LAM, M_pa=M, q_pa=Q, R_m=R, dp_m=DP))
        fields = [field(x, ratio*Q)[:2] for ratio in P_OVER_Q]
        # Operator A/C/D, P case, independent stress/load/pore, particle, XYZ.
        acc = np.zeros((3, 3, 3, len(x), 3))
        for i, j, d, g in batches(x, pairs, h):
            for k, (s, p) in enumerate(fields):
                vectors = pair_components(s[i], s[j], p[i], p[j], rho[i], rho[j], corr[i], corr[j], g)
                for op, (vi, vj) in enumerate(vectors):
                    for comp in range(3):
                        add_pair(acc[op, k, comp], i, j, mass[j, None]*vi[comp], -mass[i, None]*vj[comp])
        result['cases'] = []
        for k, ratio in enumerate(P_OVER_Q):
            raw, receiver, adjoint = acc[:, k]
            load_only = raw.copy(); load_only[1] = np.einsum('nij,nj->ni', corr, raw[1])
            s, p = fields[k]; variants = {}
            for name, values in zip(VARIANTS, [raw, load_only, receiver, adjoint]):
                total = values.sum(axis=0)  # Actual separate accumulation, including P=0.
                variants[name] = dict(total=force_metrics(x, mass, rho, total),
                    external_load=force_metrics(x, mass, rho, values[1]))
                for region, mask in masks.items():
                    rows.append(dict(p_over_q=ratio, variant=name, region=region,
                        radius_min_m=float(radius[mask].min()), radius_max_m=float(radius[mask].max()),
                        manufactured_p_min_pa=float(p[mask].min()), manufactured_p_max_pa=float(p[mask].max()),
                        **regional(total, mask, volume)))
                if name == VARIANTS[3]:
                    shifted_total = s+(Q-p)[:, None, None]*np.eye(3)
                    expected = -float(np.sum(volume*np.einsum('nij,ij->n', shifted_total, AFFINE_L)))
                    measured = float(np.sum((mass[:, None]*total)*(x@AFFINE_L.T)))
                    variants[name]['native_affine_work_identity'] = dict(measured_W=measured,
                        expected_W=expected, difference_W=measured-expected,
                        difference_over_q_nativeV=float((measured-expected)/(Q*volume.sum())),
                        external_load_expected_power_W=float(-Q*np.trace(AFFINE_L)*volume.sum()))
            result['cases'].append(dict(p_over_q=ratio, variants=variants))
        for evidence in result['inputs']:
            assert bound(evidence['path'])['sha256'] == evidence['sha256'], evidence['path']
        result['analysis_checks_passed'] = True
    except Exception as error:
        result.update(error=repr(error), traceback=traceback.format_exc())
    if rows:
        table = pd.DataFrame(rows)
        raw_rms = table[table.variant==VARIANTS[0]].set_index(['p_over_q','region']).vector_rms_m_s2
        table['vector_rms_over_A'] = [row.vector_rms_m_s2/raw_rms.loc[(row.p_over_q,row.region)]
            if raw_rms.loc[(row.p_over_q,row.region)] else np.nan for row in table.itertuples()]
        table.to_csv(csv, index=False, float_format='%.17g'); result['metrics_csv'] = bound(csv)
    result.update(wall_seconds=time.perf_counter()-started,
        limitations=['Offline double algebra, rounded Wendland constant and saved geometry; not production0ULP or a solver.',
        'Continuum div(sigma-pI)=0 and traction=-q n; truncated/irregular SPH quadrature need not reproduce this quadratic stress exactly.',
        'C is a coupled receiver-C extension, not the dry Zhao paper; D is a pair-adjoint experiment, not an implemented method.',
        'D conservation/affine work does not imply lower local error; each center/interior/shell/surface RMS/max is reported without a new physical threshold.',
        'Initial mass/rho is used unchanged; geometric and native-volume normalizations are both reported, never force-renormalized.'])
    write_json(target, result)
    print(json.dumps(dict(analysis_checks_passed=result['analysis_checks_passed'], physical_acceptance=False,
        wall_seconds=result['wall_seconds'], error=result.get('error'))), flush=True)
    if not result['analysis_checks_passed']: raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    if parser.parse_args().run: main()
    else: parser.print_help()
