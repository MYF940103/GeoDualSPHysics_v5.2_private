"""Read-only saved-state and frozen-pair Cryer diagnostics; never runs a solver.

A is the current momentum algebra in double offline arithmetic, B changes only
its load, C is a receiver-gradient coupled extension of Zhao's dry expression,
and D is a separately defined pair-symmetric mathematical screen. None is an
implemented or physically accepted replacement integrator.
"""
from pathlib import Path
import hashlib
import json
import sys
import time
import traceback
import numpy as np
from scipy.spatial import cKDTree

CASE = Path(__file__).resolve().parents[2]
TESTS = CASE/'tests'
REPO = CASE.parents[2]
LIAN = CASE.parent/'05_LianFlexibleStrip2D_PR/tests/scripts'
sys.path.insert(0, str(LIAN))
from lian_release_r1 import native, bound, write_json, READER

TAG = 'cryer_load_pair_r1'
Q = 10000.
R = .05
DP = .0025
BATCH = 65536
VARIANTS = ['A_current_raw', 'B_load_only_receiver_C',
            'C_receiver_C_coupled_extension', 'D_pair_adjoint_extension']
FIELDS = ['uniform_drained', 'uniform_shared_total_p06q', 'nonuniform_symmetric']
# Anisotropic 3D affine velocity, including shear, spin and nonzero divergence.
AFFINE_L = np.array([[.7, -.3, .2], [.4, -.5, .1], [-.2, .6, .9]])


def say(message):
    print(message, flush=True)


def tensor(a):
    s = np.empty((len(a), 3, 3))
    s[:, 0, 0], s[:, 1, 1], s[:, 2, 2] = a.sigma_xx, a.sigma_yy, a.sigma_zz
    s[:, 0, 1] = s[:, 1, 0] = a.sigma_xy
    s[:, 0, 2] = s[:, 2, 0] = a.sigma_xz
    s[:, 1, 2] = s[:, 2, 1] = a.sigma_yz
    return s


def weighted(values, weights):
    return float(np.average(values, weights=weights))


def region(a, initial, mask, er):
    x = a[['x', 'y', 'z']].to_numpy()
    x0 = initial[['x', 'y', 'z']].to_numpy()
    s = tensor(a)[mask]
    p = a.pressure.to_numpy()[mask]
    weights = (initial.mass/initial.rho).to_numpy()[mask]
    e = er[mask]
    trace = np.trace(s, axis1=1, axis2=2)
    radial = np.einsum('ni,nij,nj->n', e, s, e)
    comp = -trace/3
    total_comp = comp+p
    inward = -np.sum((x-x0)[mask]*e, axis=1)
    speed = np.linalg.norm(a[['vx', 'vy', 'vz']].to_numpy()[mask], axis=1)
    drained = a.fstype.isin([2, 3]).to_numpy()[mask]
    return dict(count=int(mask.sum()), initial_volume_m3=float(weights.sum()),
        pressure_mean_pa=weighted(p, weights), pressure_min_pa=float(p.min()),
        pressure_max_pa=float(p.max()), pressure_rms_pa=float(np.sqrt(np.average(p*p, weights=weights))),
        effective_mean_compression_pa=weighted(comp, weights),
        total_mean_compression_pa=weighted(total_comp, weights),
        total_mean_minus_q_pa=weighted(total_comp, weights)-Q,
        effective_radial_compression_pa=weighted(-radial, weights),
        effective_tangent_compression_pa=weighted(-(trace-radial)/2, weights),
        total_radial_compression_pa=weighted(-radial+p, weights),
        total_tangent_compression_pa=weighted(-(trace-radial)/2+p, weights),
        material_inward_displacement_mm=weighted(inward, weights)*1000,
        displacement_max_mm=float(np.linalg.norm((x-x0)[mask], axis=1).max())*1000,
        speed_rms_m_s=float(np.sqrt(np.average(speed*speed, weights=weights))),
        speed_max_m_s=float(speed.max()), density_mean_kg_m3=weighted(a.rho.to_numpy()[mask], weights),
        drained_count=int(drained.sum()),
        drained_pressure_abs_max_pa=float(np.abs(p[drained]).max()) if drained.any() else None)


def force_metrics(x, mass, rho, acceleration):
    force = mass[:, None]*acceleration
    radius = np.linalg.norm(x, axis=1)
    er = x/np.where(radius > 0, radius, 1)[:, None]
    volume = 4*np.pi*R**3/3
    area = 4*np.pi*R**2
    net = force.sum(axis=0)
    torque = np.cross(x, force).sum(axis=0)
    work = -force.T@x/(Q*volume)
    native_volume = float(np.sum(mass/rho))
    volume_norm = mass/rho*np.linalg.norm(acceleration, axis=1)
    norm_sum = float(volume_norm.sum())
    return dict(component_rms_m_s2=float(np.sqrt(np.mean(acceleration**2))),
        vector_rms_m_s2=float(np.sqrt(np.mean(np.sum(acceleration**2, axis=1)))),
        vector_max_m_s2=float(np.linalg.norm(acceleration, axis=1).max()),
        net_force_N=net.tolist(), net_force_over_qA=float(np.linalg.norm(net)/(Q*area)),
        torque_N_m=torque.tolist(), torque_over_qV=float(np.linalg.norm(torque)/(Q*volume)),
        radial_force_over_qA=float(-np.sum(force*er)/(Q*area)),
        moment_tensor_over_qV=work.tolist(), isotropic_compressive_work_over_3qV=float(np.trace(work)/3),
        native_volume_m3=native_volume,
        isotropic_compressive_work_over_3q_nativeV=float(np.trace(work)/3*volume/native_volume),
        affine_power_over_qV_per_s=float(np.sum(force*(x@AFFINE_L.T))/(Q*volume)),
        affine_power_over_q_nativeV_per_s=float(np.sum(force*(x@AFFINE_L.T))/(Q*native_volume)),
        inner_half_radius_volume_weighted_acc_norm_fraction=(
            float(volume_norm[radius <= .5*R].sum()/norm_sum) if norm_sum else None),
        full_support_core_volume_weighted_acc_norm_fraction=(
            float(volume_norm[radius <= R-.009].sum()/norm_sum) if norm_sum else None))


def add_pair(out, i, j, ai, aj):
    # A batch has at most65,536 pairs. No Npairs x3x3 tensor is retained.
    for axis in range(3):
        out[:, axis] += np.bincount(i, weights=ai[:, axis], minlength=len(out))
        out[:, axis] += np.bincount(j, weights=aj[:, axis], minlength=len(out))


def batches(x, pairs, h):
    for first in range(0, len(pairs), BATCH):
        i, j = pairs[first:first+BATCH].T
        d = x[i]-x[j]
        r = np.linalg.norm(d, axis=1)
        g = (-2.08891/h**5*(1-.5*r/h)**3)[:, None]*d
        yield i, j, d, g


def correction(x, mass, rho, h, pairs):
    moment = np.zeros((len(x), 3, 3))
    gradient = np.zeros_like(moment)
    v = x@AFFINE_L.T
    for i, j, d, g in batches(x, pairs, h):
        for row in range(3):
            for col in range(3):
                term = -d[:, row]*g[:, col]
                moment[:, row, col] += np.bincount(i, weights=mass[j]/rho[j]*term, minlength=len(x))
                moment[:, row, col] += np.bincount(j, weights=mass[i]/rho[i]*term, minlength=len(x))
                dv = v[j, row]-v[i, row]
                gradient[:, row, col] += np.bincount(i, weights=mass[j]/rho[j]*dv*g[:, col], minlength=len(x))
                gradient[:, row, col] += np.bincount(j, weights=mass[i]/rho[i]*dv*g[:, col], minlength=len(x))
    corr = np.linalg.inv(moment)
    corrected = gradient@np.swapaxes(corr, 1, 2)
    raw_error = gradient-AFFINE_L
    error = corrected-AFFINE_L
    scale = np.linalg.norm(AFFINE_L)
    evidence = dict(moment_eigenvalue_min=float(np.linalg.eigvalsh(moment).min()),
        moment_eigenvalue_max=float(np.linalg.eigvalsh(moment).max()),
        moment_condition_max=float(np.linalg.cond(moment).max()),
        moment_minus_identity_component_rms=float(np.sqrt(np.mean((moment-np.eye(3))**2))),
        raw_affine_gradient_component_rms_per_s=float(np.sqrt(np.mean(raw_error**2))),
        raw_affine_gradient_max_frobenius_per_s=float(np.linalg.norm(raw_error, axis=(1, 2)).max()),
        corrected_affine_gradient_component_rms_per_s=float(np.sqrt(np.mean(error**2))),
        corrected_affine_gradient_max_frobenius_per_s=float(np.linalg.norm(error, axis=(1, 2)).max()),
        affine_closure_relative_max=float(np.linalg.norm(error, axis=(1, 2)).max()/scale),
        matrix_symmetry_max=float(np.abs(moment-np.swapaxes(moment, 1, 2)).max()))
    assert evidence['affine_closure_relative_max'] < 1e-10, 'Offline affine closure failed'
    return corr, evidence


def fields(x):
    n = len(x)
    stress = np.zeros((3, n, 3, 3))
    pressure = np.zeros((3, n))
    stress[0] = -Q*np.eye(3)
    pressure[1] = .6*Q
    stress[1] = -.4*Q*np.eye(3)
    u = x/R
    stress[2, :, 0, 0] = Q*(-.7+.2*u[:, 0])
    stress[2, :, 1, 1] = Q*(-.5+.1*u[:, 2])
    stress[2, :, 2, 2] = Q*(-.6+.15*u[:, 1])
    stress[2, :, 0, 1] = stress[2, :, 1, 0] = .07*Q*(u[:, 0]+u[:, 1])
    stress[2, :, 0, 2] = stress[2, :, 2, 0] = .05*Q*(u[:, 2]+u[:, 0])
    stress[2, :, 1, 2] = stress[2, :, 2, 1] = .09*Q*(u[:, 1]-u[:, 2])
    pressure[2] = .2*Q*(1+.1*u[:, 0]+.05*u[:, 2])
    return stress, pressure


def pair_components(si, sj, pi, pj, ri, rj, ci, cj, g):
    """Return per-neighbour coefficients BEFORE multiplying the other mass.

    Rows0/1/2 are effective stress, external load, negative pore pressure.
    ai and minus_aj may differ for receiver-C; A/D have identical pair values.
    """
    gi = np.einsum('nij,nj->ni', ci, g)
    gj = np.einsum('nij,nj->ni', cj, g)
    invii = 1/(ri*ri)
    invjj = 1/(rj*rj)
    invij = 1/(ri*rj)
    prod = lambda s, v: np.einsum('nij,nj->ni', s, v)
    a = np.stack((prod(si*invii[:, None, None]+sj*invjj[:, None, None], g),
        (Q*(invii+invjj))[:, None]*g, (-(pi+pj)*invij)[:, None]*g))
    c_i = np.stack((prod(si+sj, gi)*invij[:, None], 2*Q*invij[:, None]*gi,
        (-(pi+pj)*invij)[:, None]*gi))
    c_j = np.stack((prod(si+sj, gj)*invij[:, None], 2*Q*invij[:, None]*gj,
        (-(pi+pj)*invij)[:, None]*gj))
    # D is the negative discrete adjoint of the corrected velocity gradient.
    # All three terms have the SAME ViVj force weight, including unequal density.
    d = np.stack(((prod(si, gi)+prod(sj, gj))*invij[:, None],
        Q*(gi+gj)*invij[:, None],
        -(pi[:, None]*gi+pj[:, None]*gj)*invij[:, None]))
    return [(a, a), (c_i, c_j), (d, d)]


def selftest():
    rng = np.random.default_rng(22027)
    n = 11
    si = rng.normal(size=(n, 3, 3));si = si+si.swapaxes(1, 2)
    sj = rng.normal(size=(n, 3, 3));sj = sj+sj.swapaxes(1, 2)
    g = rng.normal(size=(n, 3));p = rng.uniform(0, Q, size=n)
    rho = np.full(n, 2100.);identity = np.broadcast_to(np.eye(3), (n, 3, 3))
    a, c, d = pair_components(si, sj, p, p/2, rho, rho, identity, identity, g)
    for pair in [c]:
        for value in pair:assert np.allclose(value, a[0], rtol=2e-14, atol=1e-17)
    # D also reduces to A with C=I and uniformrho, including nonuniform pressure.
    for value in d:assert np.allclose(value, a[0], rtol=2e-14, atol=1e-17)
    # Independent explicit2particle calculation of current three separate terms.
    k = 3
    direct = np.stack(((si[k]/rho[k]**2+sj[k]/rho[k]**2)@g[k],
        Q*(2/rho[k]**2)*g[k], -(p[k]+p[k]/2)/rho[k]**2*g[k]))
    assert np.allclose(a[0][:, k], direct, rtol=2e-14, atol=1e-17)
    # Swapping the two ends must reverse every D pair force, even for unequalrho/C.
    ci = identity.copy();cj = identity.copy();ci[:, 0, 0] = .6;cj[:, 1, 1] = 1.7
    forward = pair_components(si, sj, p, p/2, rho, rho*1.02, ci, cj, g)[2][0]
    reverse = pair_components(sj, si, p/2, p, rho*1.02, rho, cj, ci, -g)[2][0]
    assert np.allclose(forward, -reverse, rtol=2e-14, atol=1e-17)
    return dict(passed=True, checks=['All four definitions reduce to currentraw for C=I and uniformrho.',
        'Independent explicit two-particle stress/load/pore arithmetic matches A.',
        'D pair force reverses under receiver/neighbour exchange with unequalrho/C.'],
        note='These are mathematical implementation checks, not physical acceptance.')


def frozen_screen(initial, later):
    x = initial[['x', 'y', 'z']].to_numpy()
    mass = initial.mass.to_numpy()
    h = float(initial.h.iloc[0])
    pairs = cKDTree(x).query_pairs(2*h, output_type='ndarray')
    assert len(pairs) > 0
    # Unique soil positions were checked previously; enforce no zero pair here.
    assert np.all(np.sum((x[pairs[:, 0]]-x[pairs[:, 1]])**2, axis=1) >= 1e-18)
    sigma, pore = fields(x)
    result = dict(geometry='All variants use the same Part0 float-saved sphere coordinates.',
        pair_count=len(pairs), batch_pairs=BATCH, pair_array_bytes=pairs.nbytes,
        kernel='3D Wendland rounded constant -2.08891, evaluated offline in double.',
        affine_L_per_s=AFFINE_L.tolist(), density_cases={})
    for name, rho in [('initial_uniform_rho', initial.rho.to_numpy()),
                      ('Part50_saved_rho_on_initial_geometry', later.rho.to_numpy())]:
        say('Frozen algebra: '+name)
        corr, affine = correction(x, mass, rho, h, pairs)
        # axes: A/C/D, manufacturedfield, stress/load/pore, soilnode, XYZ.
        acc = np.zeros((3, 3, 3, len(x), 3))
        for batch_index, (i, j, d, g) in enumerate(batches(x, pairs, h)):
            for field in range(3):
                vectors = pair_components(sigma[field, i], sigma[field, j], pore[field, i], pore[field, j],
                    rho[i], rho[j], corr[i], corr[j], g)
                for operator, (vi, vj) in enumerate(vectors):
                    for component in range(3):
                        add_pair(acc[operator, field, component], i, j,
                            mass[j, None]*vi[component], -mass[i, None]*vj[component])
            if batch_index % 20 == 0:say('  pair batch '+str(batch_index)+' / '+str((len(pairs)+BATCH-1)//BATCH))
        cases = {}
        for field, field_name in enumerate(FIELDS):
            a, c, d = acc[:, field]
            b = a.copy()
            b[1] = np.einsum('nij,nj->ni', corr, a[1])
            variants = {}
            for label, values in zip(VARIANTS, [a, b, c, d]):
                # Sum three independently accumulated arrays: zero is never assigned.
                total = values.sum(axis=0)
                variants[label] = dict(total=force_metrics(x, mass, rho, total),
                    effective_stress=force_metrics(x, mass, rho, values[0]),
                    external_load=force_metrics(x, mass, rho, values[1]),
                    negative_pore_pressure=force_metrics(x, mass, rho, values[2]))
                if label == VARIANTS[3]:
                    t = sigma[field]+(Q-pore[field])[:, None, None]*np.eye(3)
                    expected = -float(np.sum((mass/rho)*np.einsum('nij,ij->n', t, AFFINE_L)))
                    measured = float(np.sum((mass[:, None]*total)*(x@AFFINE_L.T)))
                    variants[label]['affine_discrete_work_identity'] = dict(
                        direct_power_W=measured, negative_native_volume_stress_gradient_power_W=expected,
                        difference_W=measured-expected,
                        dimensionless_difference_over_q_nativeV=float((measured-expected)/(Q*np.sum(mass/rho))),
                        definition='T=sigma_effective+(q-p)I; sum(m v.a)=-sum(V T:L), with L the affine-exact corrected gradient. No continuum geometry-volume normalization.')
            cases[field_name] = variants
        result['density_cases'][name] = dict(rho_min=float(rho.min()), rho_max=float(rho.max()),
            rho_relative_range=float(np.ptp(rho)/rho.mean()), affine=affine, fields=cases,
            provenance=('Physical initial uniform density.' if name=='initial_uniform_rho' else
                'Hybrid diagnostic only: Part50 saved density values attached by fixed nativeID to Part0 coordinates; not an actual coupled state.'))
    return result


def main():
    target = TESTS/'logs'/(TAG+'.check.json')
    assert not target.exists(), 'Never overwrite an earlier receipt'
    started = time.perf_counter()
    result = dict(scope='Offline native-history and frozen-neighbour algebra only.',
        physical_acceptance=False, production_implemented=False, solver_executed=False,
        analysis_checks_passed=False)
    try:
        result['selftest'] = selftest()
        folder = CASE/'CaseCryerProblem_PR_out'
        files = sorted((folder/'data').glob('Part_*.bi4'))
        desired = [0, 1, 10, 50, 100, 200, 500, 1000]
        selected = [min(desired_part, len(files)-1) for desired_part in desired]
        assert len(set(selected)) == len(selected), 'Requested native frames not all available; choose explicit new audit instead'
        inputs = [Path(__file__), TESTS/'notes'/(TAG+'.md'), READER, LIAN/'lian_release_r1.py',
            LIAN/'read_hydro_native.cpp', folder/'Run.out', folder/'CaseCryerProblem_PR.xml',
            CASE/'CaseCryerProblem_PR_Def.xml', TESTS/'logs/cryer_load_audit_r1.json']
        inputs += [REPO/'src/source'/name for name in ['JSphCpu.cpp', 'JSphGpu_ker.cu',
            'JSph.cpp', 'JSphCpuSingle.cpp', 'FunSphKernel.h', 'DualSphDef.h']]
        inputs += [REPO/'src/papers/PDF'/name for name in [
            '2019 - Zhao - A generic approach to modelling flexible confined boundary conditions in SPH and.pdf',
            'An SPH framework for drained and undrained loading.pdf']]
        inputs += [REPO/'src/papers/u-pw'/name for name in [
            '2019 - Zhao - A generic approach to modelling flexible confined boundary conditions in SPH and.md',
            'An SPH framework for drained and undrained loading.md']]
        inputs += [files[p] for p in selected]
        result['inputs'] = [bound(p) for p in inputs]
        initial = native(folder, 0)
        assert len(initial) == 37173 and initial.id.nunique() == len(initial)
        assert np.isfinite(initial.to_numpy(dtype='<f8')).all()
        x0 = initial[['x', 'y', 'z']].to_numpy()
        r0 = np.linalg.norm(x0, axis=1)
        er = x0/np.where(r0 > 0, r0, 1)[:, None]
        center = r0 <= DP+1e-12
        assert center.any(), 'No declared fixed-material center-ball IDs'
        result['native_identity'] = dict(soil_count=len(initial), ids_sha256=hashlib.sha256(
            initial.id.to_numpy(dtype='<u4').tobytes()).hexdigest(),
            center_radius_m=DP, center_tolerance_m=1e-12, center_count=int(center.sum()),
            center_ids=[int(v) for v in initial.id[center]],
            center_rmin_m=float(r0[center].min()), center_rmax_m=float(r0[center].max()),
            zero_center_count=int((r0 < 1e-10).sum()),
            initial_position_double=int(initial.position_double.min()),
            initial_stress_double=int(initial.stress_double.min()),
            initial_volume_over_geometric_sphere=float((initial.mass/initial.rho).sum()/(4*np.pi*R**3/3)))
        rows = []
        later = None
        edges = [0, .005, .01, .02, .03, .04, .045, .05000001]
        for part in selected:
            say('Reading native PART'+str(part))
            a = initial if part == 0 else native(folder, part)
            assert np.array_equal(a.id, initial.id) and np.isfinite(a.to_numpy(dtype='<f8')).all()
            assert a.rho.gt(0).all() and a.load_available.eq(1).all()
            if part == 50:later = a.copy()
            drained = a.fstype.isin([2, 3]).to_numpy()
            row = dict(part=part, actual_time_s=float(a.time_s.iloc[0]),
                saved_step=int(a.saved_step.iloc[0]), position_double=int(a.position_double.min()),
                stress_double=int(a.stress_double.min()), pressure_storage='Native DatFloat (reader-enforced)',
                nout_max=int(a.nout.max()), kplastic_max=float(a.kplastic.max()),
                fstype_counts={str(int(k)): int(v) for k, v in a.fstype.value_counts().items()},
                changed_fstype_count=int((a.fstype.to_numpy() != initial.fstype.to_numpy()).sum()),
                drained_pressure_abs_max_pa=float(np.abs(a.pressure.to_numpy()[drained]).max()) if drained.any() else None,
                center=region(a, initial, center, er),
                whole=region(a, initial, np.ones(len(a), dtype=bool), er), shells=[])
            for left, right in zip(edges[:-1], edges[1:]):
                mask = (r0 >= left) & (r0 < right)
                if mask.any():row['shells'].append(dict(initial_rleft_m=left, initial_rright_m=right,
                    **region(a, initial, mask, er)))
            row['saved_external_load'] = force_metrics(a[['x', 'y', 'z']].to_numpy(),
                a.mass.to_numpy(), a.rho.to_numpy(), a[['load_ax', 'load_ay', 'load_az']].to_numpy())
            rows.append(row)
            say('  t='+str(row['actual_time_s'])+' center p='+str(row['center']['pressure_mean_pa'])+
                ' total compression='+str(row['center']['total_mean_compression_pa']))
        result['native_history'] = rows
        assert later is not None
        result['frozen_pair_screen'] = frozen_screen(initial, later)
        for evidence in result['inputs']:
            assert bound(evidence['path'])['sha256'] == evidence['sha256'], evidence['path']
        result['analysis_checks_passed'] = True
    except Exception as error:
        result.update(error=repr(error), traceback=traceback.format_exc())
    result['wall_seconds'] = time.perf_counter()-started
    result['limitations'] = [
        'No solver/source/formal/Git change, physical trajectory or physical acceptance in this stage.',
        'Old native history is not a stress-precision-only A/B experiment; old executable identity is not inferred from the current source.',
        'Effective stress is tensile-positive. Total stress is sigma_effective-pI. Pressure/q is not a load-bearing fraction; transient total stress need not equal-qI.',
        'All radial profiles and the center ball use fixed initial nativeIDs/radii; there is no native r=0 node assumed.',
        'Current production matrix sign/orientation is reproduced mathematically, not bitwise: float kernel/position/density arithmetic and cell order differ.',
        'C adds pore coupling/common density denominator to a Zhao-style receiver correction; it is not a complete reproduction of the dry-paper model.',
        'D is a pair-symmetric negative-adjoint extension with commonViVj weights, not Zhao original. Its discrete linear/angular/work properties do not prove continuum traction accuracy or stable coupled dynamics.',
        'Nonuniform-field resultant/work are algebra descriptors, not theory errors: its boundary stress does not equal the declared uniform exterior pressure.',
        'Uniform-total-stress cancellation alone is insufficient because a common bracket can vanish identically. The nonuniform field and affine gradient are also examined.',
        'Force and volume/quadrature ratios are reported, never automatically normalized. No geometry/mass correction is inferred from volume ratio alone.',
        'RMS acceleration is labelled both component and particle-vector RMS; initial0 residuals are computed by summing independent arrays, never hard-assigned.']
    write_json(target, result)
    say(json.dumps(dict(analysis_checks_passed=result['analysis_checks_passed'],
        physical_acceptance=False, wall_seconds=result['wall_seconds'], error=result.get('error'))))
    if not result['analysis_checks_passed']:raise SystemExit(1)


if __name__ == '__main__':
    main()
