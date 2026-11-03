"""Offline exported-neighborhood arithmetic review; never invokes the static executable."""
from pathlib import Path
import csv
import hashlib
import json
import sys
import numpy as np

T = Path(__file__).resolve().parents[1]
TAG = 'upl_cryer_scalar3d_review_r1'
OUT = T / 'outputs/upl_cryer_scalar3d_r1'
CHECK, PNG = T / 'logs' / (TAG + '.check.json'), T / 'figures' / (TAG + '.png')
LOCKS = {
    'logs/upl_cryer_scalar3d_r1.build.json': '8fa724f52cfeaa825d5087587f6e3d7080a9ded89bbf6b5b4c605140ff6a89eb',
    'notes/upl_cryer_scalar3d_run_r1_record_audit.json': 'fff781b8ba00cde5de2f01e055ad4ef95219088dcae1054f866f470774df6a13',
    'support/upl_cryer_scalar3d_r1.cpp': 'f73f0ceed8e863d8d3574efee9aef42dc52c72863181359bcf1fffca8dd606ab',
    'notes/upl_cryer_scalar3d_r1.json': '6a552840f2aa711ed09beb146c629bfa724847d0f4e73339a88572f983a414a2',
}
LEAVES = {'fields.csv': 672, 'moments.csv': 48, 'neighbors.csv': 1855,
          'budgets.csv': 224, 'arithmetic.csv': 432, 'isotropic_clone.csv': 4}
FIELDS = ('constant affine_x affine_y affine_z affine_xyz quadratic_x quadratic_y quadratic_z '
          'quadratic_xy quadratic_xz quadratic_yz quadratic_mix quadratic_isotropic smooth_cos_xyz').split()
METHODS = ('receiverC_star', 'symC_star')
DP, H, V, ALPHA = .01, float(np.float32(.018)), .01 * .01 * .01, 2.
ETA = float(np.float32((H * .1) ** 2))
EPS, BOUND, RATIOS = np.finfo(np.float64).eps, {}, {}


def need(ok, why):
    if not ok:
        raise ValueError(why)


def gamma(n):
    return n * EPS / (1. - n * EPS)


def measure(path):
    p = Path(path).resolve()
    digest = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    return {'path': str(p), 'bytes': p.stat().st_size, 'sha256': digest.hexdigest()}


def bind(value):
    expected = value if isinstance(value, dict) else None
    path = Path(expected['path'] if expected else value).resolve()
    key = str(path).casefold()
    if key not in BOUND:
        BOUND[key] = measure(path)
    actual = BOUND[key]
    if expected:
        need(actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256'].lower(),
             'Binding conflict or changed artifact: ' + str(path))
    return actual


def readjson(path):
    return json.loads(Path(bind(path)['path']).read_text(encoding='utf-8-sig'))


def table(name):
    path = OUT / name
    bind(path)
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        need(reader.fieldnames and len(reader.fieldnames) == len(set(reader.fieldnames)), 'CSV header: ' + name)
        rows = list(reader)
    need(len(rows) == LEAVES[name] and all(None not in r and None not in r.values() for r in rows), 'CSV rows: ' + name)
    return rows


def num(row, *keys):
    a = np.asarray([float(row[k]) for k in keys], dtype=np.float64)
    need(np.isfinite(a).all(), 'Nonfinite export: ' + ','.join(keys))
    return a


def mat(row, prefix):
    return num(row, *(prefix + str(a) + str(b) for a in range(3) for b in range(3))).reshape(3, 3)


def group(row, with_method=True):
    base = (row['shape'], int(row['disorder']), int(row['receiver_id']))
    return base + (int(row['eta']), row['method']) if with_method else base


def close(actual, reference, budget, label, key):
    a, b, lim = np.broadcast_arrays(np.asarray(actual, dtype=float), np.asarray(reference, dtype=float), np.asarray(budget, dtype=float))
    need(np.isfinite(a).all() and np.isfinite(b).all() and np.isfinite(lim).all() and (lim >= 0).all(), 'Nonfinite arithmetic: ' + label)
    err = np.abs(a - b)
    ratio = np.divide(err, lim, out=np.zeros_like(err), where=lim > 0)
    need(not np.any((lim == 0) & (err != 0)), 'Nonzero error with zero majorant: ' + label + ' ' + str(key))
    worst = float(np.max(ratio))
    stat = RATIOS.setdefault(label, {'comparisons': 0, 'max_ratio': 0., 'max_abs_difference': 0., 'worst_key': None})
    stat['comparisons'] += int(err.size)
    stat['max_abs_difference'] = max(stat['max_abs_difference'], float(np.max(err)))
    if worst > stat['max_ratio']:
        stat['max_ratio'], stat['worst_key'] = worst, str(key)
    need(worst <= 1., 'Predeclared arithmetic propagation budget exceeded: ' + label + ' ' + str(key))


def analytic(field, x):
    """Independent c+l.x+1/2 x.H.x representation, or a separable cosine."""
    x = np.asarray(x, dtype=float)
    c, l, h = 0., np.zeros(3), np.zeros((3, 3))
    if field == 'smooth_cos_xyz':
        k = np.pi / (12. * DP)
        co, si = np.cos(k * x), np.sin(k * x)
        val = np.prod(co, axis=-1)
        grad = -k * np.stack([si[..., a] * co[..., (a + 1) % 3] * co[..., (a + 2) % 3] for a in range(3)], axis=-1)
        return val, grad, -3. * k * k * val, np.ones_like(val), l, h
    if field == 'constant':
        c = 7.
    elif field.startswith('affine_'):
        if field == 'affine_xyz':
            c, l = 1., np.array([3., -2., .5])
        else:
            l['xyz'.index(field[-1])] = 1.
    elif field in ('quadratic_x', 'quadratic_y', 'quadratic_z'):
        a = 'xyz'.index(field[-1]); h[a, a] = ALPHA
    elif field in ('quadratic_xy', 'quadratic_xz', 'quadratic_yz'):
        a, b = ('xyz'.index(s) for s in field[-2:]); h[a, b] = h[b, a] = ALPHA
    elif field == 'quadratic_mix':
        h = ALPHA * np.array([[1., .3, -.2], [.3, 2., .4], [-.2, .4, 3.]])
    else:
        need(field == 'quadratic_isotropic', 'Unknown manufactured field')
        h = ALPHA * np.eye(3)
    val = c + x @ l + .5 * np.einsum('...a,ab,...b->...', x, h, x)
    major = abs(c) + np.abs(x) @ np.abs(l) + .5 * np.einsum('...a,ab,...b->...', np.abs(x), np.abs(h), np.abs(x))
    return val, l + x @ h.T, np.full(np.shape(val), np.trace(h)), major, l, h


def reconstruct(m, edges, field_rows):
    key, ci = group(m), mat(m, 'Ci')
    n = len(edges); gN = gamma(64 * (n + 1))
    d = np.array([num(e, 'dx', 'dy', 'dz') for e in edges])
    rr = np.array([float(e['rr2_double']) for e in edges])
    fac = np.array([float(e['kernel_fac_float']) for e in edges])
    cj = np.array([mat(e, 'Cj') for e in edges]); ca = np.array([mat(e, 'Cavg') for e in edges])
    need(len({int(e['neighbor_id']) for e in edges}) == n and int(m['neighbors']) == n, 'Neighbor count/identity: ' + str(key))
    need(np.isfinite(rr).all() and (rr > 0).all() and (rr <= float(np.float32(np.float32(2 * H) ** 2))).all(), 'Neighbor support: ' + str(key))
    need(np.array_equal(fac, fac.astype(np.float32).astype(float)), 'Kernel factor is not exported float')
    close(rr, np.sum(d * d, axis=1), gamma(8) * np.sum(d * d, axis=1), 'rr2', key)
    close(ca, .5 * (ci + cj), gamma(4) * .5 * (np.abs(ci) + np.abs(cj)), 'Cavg', key)
    eta = ETA if key[3] else 0.
    need(float(m['eta2']) == eta, 'Eta2 recipe changed')
    g = fac[:, None] * d
    raw = -V * np.einsum('na,nb->ab', d, g)
    rawmajor = V * np.einsum('na,nb->ab', np.abs(d), np.abs(g))
    close(float(m['receiver_moment_determinant']), np.linalg.det(raw),
          gN * 6 * np.prod(np.max(rawmajor, axis=1)), 'moment_determinant', key)
    close(ci @ raw, np.eye(3), gN * (np.abs(ci) @ rawmajor + np.eye(3)), 'Ci_moment_residual', key)
    cg = g @ ci.T
    cgmajor = np.abs(g) @ np.abs(ci).T
    if key[4] == 'symC_star':
        cg = .5 * (cg + np.einsum('nab,nb->na', cj, g))
        cgmajor = .5 * (cgmajor + np.einsum('nab,nb->na', np.abs(cj), np.abs(g)))
    w = 2 * V * np.sum(d * cg, axis=1) / (rr + eta)
    wm = 2 * V * np.sum(np.abs(d) * cgmajor, axis=1) / (rr + eta)
    lx, lm = np.sum(w[:, None] * d, axis=0), np.sum(wm[:, None] * np.abs(d), axis=0)
    lb = gN * lm
    b, bm = V * (g @ ci.T), V * (np.abs(g) @ np.abs(ci).T)
    a = -w - b @ lx
    am = wm + bm @ np.abs(lx)
    ab = gN * am + bm @ lb
    first = -np.sum(a[:, None] * d, axis=0)
    second = .5 * np.einsum('n,na,nb->ab', a, d, d)
    sb = .5 * np.einsum('n,na,nb->ab', gN * am + ab, np.abs(d), np.abs(d))
    gx = -np.einsum('na,nb->ab', b, d)
    close(num(m, 'lx', 'ly', 'lz'), lx, lb, 'lx', key)
    close(mat(m, 'Gx'), gx, gN * np.einsum('na,nb->ab', bm, np.abs(d)), 'Gx', key)
    close(num(m, 'Lstar_first_x', 'Lstar_first_y', 'Lstar_first_z'), first,
          np.sum((gN * am + ab)[:, None] * np.abs(d), axis=0), 'first_moment', key)
    close(mat(m, 'Lstar_second'), second, sb, 'second_moment', key)
    close(float(m['second_minus_I_Frobenius']), np.linalg.norm(second - np.eye(3)),
          np.linalg.norm(sb) + gamma(32) * np.linalg.norm(np.abs(second) + np.eye(3)), 'second_error', key)
    cdelta = np.max(np.abs(ci - cj))
    close(float(m['neighbor_C_max_difference']), cdelta, gamma(4) * np.max(np.abs(ci) + np.abs(cj)), 'C_variation', key)
    reverse_cg = np.einsum('nab,nb->na', cj, g)
    wr = w if key[4] == 'symC_star' else 2 * V * np.sum(d * reverse_cg, axis=1) / (rr + eta)
    wrm = 2 * V * np.sum(np.abs(d) * np.einsum('nab,nb->na', np.abs(cj), np.abs(g)), axis=1) / (rr + eta)
    close(float(m['raw_pair_volume_defect_max']), V * np.max(np.abs(w - wr)),
          gN * V * np.max(wm + wrm), 'raw_pair_defect', key)
    pair = num(m, 'star_pair_volume_defect_max', 'star_pair_volume_defect_sumabs', 'star_pair_relative_max')
    need((pair >= 0).all() and pair[0] <= pair[1] and pair[2] <= 1 + gamma(8), 'Descriptive reverse-star pair sanity')
    result = {}
    for f in FIELDS:
        r = field_rows[f]; xi = num(r, 'x', 'y', 'z'); xj = xi - d
        fi, eg, el, fim, _, _ = analytic(f, xi)
        fj, _, _, fjm, l, h = analytic(f, xj)
        dx = gamma(4) * (np.abs(xi) + np.abs(d) + np.abs(xj))
        if f == 'smooth_cos_xyz':
            coord = (np.pi / (12 * DP)) * np.sum(dx, axis=1)
        else:
            coord = np.sum((np.abs(l) + np.abs(xj) @ np.abs(h).T) * dx, axis=1) + .5 * np.einsum('na,ab,nb->n', dx, np.abs(h), dx)
        df, fm = fj - fi, fjm + fim
        gp, lp = np.sum(b * df[:, None], axis=0), -np.sum(w * df)
        gpb = gN * np.sum(bm * fm[:, None], axis=0) + np.sum(bm * coord[:, None], axis=0)
        lpb = gN * np.sum(wm * fm) + np.sum(wm * coord)
        star = lp - gp @ lx
        stb = lpb + np.sum(np.abs(lx) * gpb + np.abs(gp) * lb + gpb * lb) + gamma(8) * np.sum(np.abs(gp * lx))
        action = a @ df
        acb = gN * np.sum(am * fm) + np.sum(ab * np.abs(df) + np.abs(a) * coord)
        # Analytic closures use a separate, fixed 128-operation binary64 majorant.
        egm = np.abs(l) + np.abs(h) @ np.abs(xi) if f != 'smooth_cos_xyz' else np.full(3, np.pi / (12 * DP))
        elm = np.sum(np.abs(np.diag(h))) if f != 'smooth_cos_xyz' else 3 * (np.pi / (12 * DP)) ** 2
        close(float(r['input']), fi, gamma(128) * fim, 'field_input', (key, f))
        close(num(r, 'exact_grad_x', 'exact_grad_y', 'exact_grad_z'), eg, gamma(128) * egm, 'exact_gradient', (key, f))
        close(float(r['exact_lap']), el, gamma(128) * elm, 'exact_laplacian', (key, f))
        close(num(r, 'grad_x', 'grad_y', 'grad_z'), gp, gpb, 'gradient', (key, f))
        close(float(r['lp']), lp, lpb, 'lp', (key, f))
        close(float(r['Lstar']), star, stb, 'Lstar', (key, f))
        close(float(r['error']), star - el, stb + gamma(128) * elm + gamma(4) * (abs(star) + abs(el)), 'analytic_error_identity', (key, f))
        ge = np.linalg.norm(gp - eg)
        close(float(r['grad_error']), ge, np.linalg.norm(gpb + gamma(128) * egm) + gamma(32) * (np.linalg.norm(gp) + np.linalg.norm(eg)), 'gradient_error', (key, f))
        close(float(r['coefficient_action_error']), action - star, acb + stb, 'coefficient_action', (key, f))
        close(float(r['local_max_abs_field']), max(abs(fi), np.max(np.abs(fj))),
              gamma(128) * max(fim, float(np.max(fjm))) + np.max(coord), 'field_scale', (key, f))
        result[f] = {'star': float(star), 'star_budget': float(stb), 'gradient_error': float(ge),
                     'laplacian': float(el), 'source': r}
    return result


def review():
    for relative, sha in LOCKS.items():
        need(bind(T / relative)['sha256'] == sha, 'Pinned input changed: ' + relative)
    bind(__file__); bind(T / 'notes' / (TAG + '.json'))
    build = readjson(T / 'logs/upl_cryer_scalar3d_r1.build.json')
    audit = readjson(T / 'notes/upl_cryer_scalar3d_run_r1_record_audit.json')
    need(build['passed'] is True and build['actual_headers_archived_not_live'] is True and len(build['actual_archived_project_headers']) == 11, 'Build identity')
    call = build['compiler_call']
    need(call['direct_native_call'] is True and call['typed_LASTEXITCODE_captured_immediately'] is True and call['owned_call_exited'] is True and type(call['exit_code']) is int and call['exit_code'] == 0 and call['invocation_failure'] is None, 'Compiler call is not owned exit0')
    need('/MT' in call['arguments'] and '/fp:precise' in call['arguments'], 'Actual compiler flags changed')
    for e in [*build['inputs'], *build['author_files'], *build['actual_archived_project_headers'], build['source_recipe'], build['program'], build['object'], build['compiler_dependency_record'], call['program'], call['log']]:
        bind(e)
    need(audit['native_exit_proven'] is False and audit['native_exit_code'] is None and audit['outer_shell_exit_code'] == 1 and audit['program_sha256'] == build['program']['sha256'], 'Runtime evidence qualification changed')
    need(audit['physical_solver_started'] is False and audit['observed_outputs']['files'] == 7, 'Original record audit scope')
    need(sorted(p.name for p in OUT.iterdir()) == sorted([*LEAVES, 'completion.json']), 'Seven retained output leaves differ')
    done = readjson(OUT / 'completion.json')
    need(done['stage'] == 'upl_cryer_scalar3d_r1' and done['passed'] is True and done['diagnostic_only'] is True, 'Original completion')
    for flag in ('production_call_regression', 'physical_acceptance', 'public_3D_admitted', 'quadratic_or_smooth_accuracy_gate', 'global_conservation_or_surface_flux_proved', 'full_matrix_or_spectrum_formed'):
        need(done[flag] is False, 'Original scope flag changed: ' + flag)
    need(done['physical_steps_advanced'] == 0 and done['actual_force_or_complete_rate_calls'] == 0, 'Static diagnostic only')
    expected = {'field_rows': 672, 'moment_rows': 48, 'neighbor_rows': 1855, 'budget_rows': 224, 'isotropic_clone_rows': 4, 'arithmetic_rows': 432, 'arithmetic_failures': 0, 'receiver_instances': 12}
    need(all(done[k] == v for k, v in expected.items()), 'Completion counts')
    need(done['dp_m'] == DP and done['h_m'] == H and done['uniform_volume_m3'] == V and done['current_Eta2_float'] == ETA, 'Manufactured constants')
    need(done['field_storage_binary64_not_production_pressure_float'] is True and done['kernel_3D_awen_float'] == 71635.8125 and done['kernel_3D_bwen_float'] == -19898932., 'Declared float-kernel/double-field storage')
    data = {name: table(name) for name in LEAVES}
    fs, ms, ns = {}, {}, {}
    for r in data['fields.csv']:
        k = group(r); need((k, r['field']) not in fs, 'Duplicate field key'); fs[k, r['field']] = r
    for r in data['moments.csv']:
        k = group(r); need(k not in ms, 'Duplicate moment key'); ms[k] = r
    for r in data['neighbors.csv']:
        ns.setdefault(group(r, False), []).append(r)
    shape_ids = {'full_support': {3429}, 'sphere_cut': {3429, 3433, 3505, 4873, 4572}}
    expected_keys = {(s, d, i, e, m) for s, ids in shape_ids.items() for d in (0, 1) for i in ids for e in (0, 1) for m in METHODS}
    need(set(ms) == expected_keys and set(fs) == {(k, f) for k in expected_keys for f in FIELDS} and set(ns) == {k[:3] for k in expected_keys}, 'Complete predeclared case/field coverage')
    rebuilt = {}
    for k, m in ms.items():
        baseline = ms[k[:3] + (0, METHODS[0])]
        need(np.array_equal(mat(m, 'Ci'), mat(baseline, 'Ci')), 'Receiver C changes with eta/method')
        need(all(np.array_equal(num(fs[k, f], 'x', 'y', 'z'), num(fs[k, FIELDS[0]], 'x', 'y', 'z')) for f in FIELDS), 'Receiver position changes across fields')
        need(np.array_equal(num(fs[k, FIELDS[0]], 'x', 'y', 'z'), num(fs[k[:3] + (0, METHODS[0]), FIELDS[0]], 'x', 'y', 'z')), 'Receiver position changes across method/eta')
        rebuilt[k] = reconstruct(m, ns[k[:3]], {f: fs[k, f] for f in FIELDS})
    gates = {}; independent = []; maxima = {'constant_abs_max': 0., 'affine_gradient_abs_max': 0., 'affine_star_abs_max': 0.}
    for k in expected_keys:
        for f in FIELDS[:5]:
            r, ref = fs[k, f], rebuilt[k][f]
            tests = [('constant', abs(float(r['Lstar'])), abs(ref['star']), 1e-10)] if f == 'constant' else [('affine_gradient', float(r['grad_error']), ref['gradient_error'], 1e-10), ('affine_star', abs(float(r['Lstar'])), abs(ref['star']), 1e-8)]
            for name, source_error, reference_error, limit in tests:
                gates[k, f, name] = (source_error, limit)
                need(source_error <= limit and reference_error <= limit, 'Unchanged original arithmetic gate failed: ' + str((k, f, name)))
                independent.append(reference_error / limit)
            if f == 'constant':
                maxima['constant_abs_max'] = max(maxima['constant_abs_max'], abs(float(r['Lstar'])))
            else:
                maxima['affine_gradient_abs_max'] = max(maxima['affine_gradient_abs_max'], float(r['grad_error']))
                maxima['affine_star_abs_max'] = max(maxima['affine_star_abs_max'], abs(float(r['Lstar'])))
    seen = set()
    for r in data['arithmetic.csv']:
        key = (group(r), r['field'], r['gate']); need(key not in seen and key in gates, 'Arithmetic gate key'); seen.add(key)
        need((float(r['error']), float(r['threshold'])) == gates[key] and r['pass'] == '1', 'Arithmetic row does not match original field/limit')
    need(len(seen) == len(gates) == len(independent) == 432 and all(done[k] == v for k, v in maxima.items()), 'Original arithmetic counts/maxima')
    budget_seen = set()
    for r in data['budgets.csv']:
        prefix = (r['shape'], int(r['disorder']), int(r['eta']), r['method'], r['field'])
        need(prefix not in budget_seen, 'Duplicate selected budget'); budget_seen.add(prefix)
        keys = [k for k in expected_keys if (k[0], k[1], k[3], k[4]) == prefix[:4]]
        need(r['global_or_boundary_flux_proof'] == '0' and int(r['selected_receivers']) == len(keys), 'Selected budget scope')
        vals = np.array([float(fs[k, r['field']]['Lstar']) for k in keys]); exact = np.array([float(fs[k, r['field']]['exact_lap']) for k in keys])
        a, b = V * np.sum(vals), V * np.sum(exact); lim = gamma(64 * (len(keys) + 1)) * V * np.sum(np.abs(vals) + np.abs(exact))
        close(num(r, 'selected_volume', 'selected_V_Lstar', 'selected_V_exact', 'selected_budget_difference'), [len(keys) * V, a, b, a - b], [gamma(8) * len(keys) * V, lim, lim, 2 * lim], 'selected_volume_sum', prefix)
    need(len(budget_seen) == 224, 'Selected budget coverage')
    clone = []; clone_seen = set()
    for r in data['isotropic_clone.csv']:
        d, e = int(r['disorder']), int(r['eta']); need((d, e) not in clone_seen and d in (0, 1) and e in (0, 1), 'Clone coverage'); clone_seen.add((d, e))
        k = ('full_support', d, 3429, e, METHODS[0]); sym = k[:-1] + (METHODS[1],)
        cv, sv = rebuilt[k]['quadratic_isotropic'], rebuilt[sym]['quadratic_isotropic']
        need(float(r['eta2']) == (ETA if e else 0.) and r['common_Cj_equals_Ci_counterfactual'] == '1' and int(r['conditional_regular_eta0_identity']) == int(d == 0 and e == 0), 'Clone conditional label')
        need(float(r['alpha']) == ALPHA and float(r['expected_3alpha']) == 6. and float(r['expected_coefficient3_4p5alpha']) == 9., 'Trace3 clone constants')
        close(num(r, 'clone_receiverC_Lstar', 'clone_error', 'real_symC_Lstar', 'coefficient3_counterfactual'), [cv['star'], cv['star'] - 6, sv['star'], 1.5 * cv['star']], [cv['star_budget'], cv['star_budget'] + gamma(4) * (abs(cv['star']) + 6), sv['star_budget'], 1.5 * cv['star_budget'] + gamma(4) * abs(cv['star'])], 'clone_export', (d, e))
        need(float(r['neighbor_C_variation']) == float(ms[sym]['neighbor_C_max_difference']), 'Clone C variation')
        if d == 0 and e == 0:
            close(cv['star'], 6., cv['star_budget'] + gamma(64) * 6, 'conditional_trace3_identity', (d, e))
        clone.append({'disorder': d, 'eta': e, 'receiverC_Lstar': cv['star'], 'real_symC_Lstar': sv['star'], 'coefficient3_counterfactual': 1.5 * cv['star'], 'only_regular_eta0_requires_6': d == 0 and e == 0})
    need(len(clone_seen) == 4, 'Four clone cases')
    graph = []
    for d in (0, 1):
        for e in (0, 1):
            for method in METHODS:
                for i in (3429, 3433, 3505, 4873, 4572):
                    k = ('sphere_cut', d, i, e, method)
                    graph.append({'disorder': d, 'eta': e, 'method': method, 'receiver_id': i, 'isotropic_absolute_relative_error_percent': abs(float(fs[k, 'quadratic_isotropic']['Lstar']) - 6) / 6 * 100, 'second_minus_I_Frobenius': float(ms[k]['second_minus_I_Frobenius'])})
    plot(graph)
    return {'coverage': expected, 'independent_original_gate_rechecks': len(independent), 'independent_original_gate_max_ratio': max(independent), 'original_export_maxima': maxima, 'arithmetic_reconstruction': RATIOS, 'isotropic_clone': clone, 'plot_values_40': graph, 'reported_not_rebuilt_cloud_counts': {k: done[k] for k in ('source_cloud_max_nodes', 'total_source_nodes_four_clouds', 'lazy_correction_matrices')}, 'source_build': bind(T / 'logs/upl_cryer_scalar3d_r1.build.json'), 'original_run_record_audit': bind(T / 'notes/upl_cryer_scalar3d_run_r1_record_audit.json'), 'original_wrapper_error': audit['reported_error'], 'compiler_exit_proven': True}


def plot(rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    colors, markers = ('#0072B2', '#56B4E9', '#D55E00', '#CC79A7'), ('o', 's', '^', 'D')
    with plt.rc_context({'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False, 'savefig.dpi': 180}):
        fig, ax = plt.subplots(2, 2, figsize=(10.8, 6.8), sharex=True, sharey='col')
        for d in (0, 1):
            for j, (e, m) in enumerate((e, m) for e in (0, 1) for m in METHODS):
                selected = [r for r in rows if (r['disorder'], r['eta'], r['method']) == (d, e, m)]
                label = ('receiver C' if m == METHODS[0] else 'real pair-sym C') + ('; Eta2' if e else '; eta=0')
                for col, field in enumerate(('isotropic_absolute_relative_error_percent', 'second_minus_I_Frobenius')):
                    ax[d, col].plot(range(5), [r[field] for r in selected], color=colors[j], marker=markers[j], lw=.8, ms=4, label=label)
                    ax[d, col].grid(alpha=.22); ax[d, col].yaxis.set_major_locator(MaxNLocator(5))
            ax[d, 0].set_ylabel(('Regular' if d == 0 else 'Disordered') + '\nsphere-cut receivers')
        ax[0, 0].set_title(r'Isotropic quadratic: $|L^*p-6|/6$ (%)')
        ax[0, 1].set_title(r'Second moment: $\|M_2-I\|_F$ (dimensionless)')
        for a in ax.flat:
            a.set_xticks(range(5), ['center', 'x=4dp', 'y=4dp', 'z=4dp', '(3,3,3)dp'])
            a.axhline(0, color='.5', lw=.5)
        fig.legend(*ax[0, 0].get_legend_handles_labels(), loc='upper center', ncol=4, bbox_to_anchor=(.5, .975), frameon=False)
        fig.suptitle('Frozen 3-D scalar arithmetic — coarse spherical truncation', y=1.015, fontsize=12)
        fig.text(.5, .012, 'dp=0.01 m, R=0.06 m; binary64 crop may break axis-permutation symmetry at boundary points.\nStatic exported-neighbor calculation, not Cryer pressure/rotation validation; native exit is unproven.', ha='center', fontsize=8)
        fig.tight_layout(rect=(0, .07, 1, .92)); PNG.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(PNG, bbox_inches='tight'); plt.close(fig)


def main():
    need(not CHECK.exists() and not PNG.exists(), 'Fresh review/check/figure required; retained artifacts protected')
    result = {'stage': TAG, 'passed': False, 'offline_artifact_arithmetic_review_only': True,
              'native_exit_proven': False, 'native_exit_code': None, 'original_outer_shell_exit_code': 1,
              'physical_acceptance': False, 'production_call_regression': False, 'public_3D_admitted': False,
              'native_or_solver_programs_invoked_by_review': 0, 'visual_review_performed': False,
              'limits': ['Conditional on exported d/fac/Ci/Cj; not a second kernel, point-cloud or production parser.',
                         'Full reverse-neighbor Lx is absent: corrected star-pair defects get finite/scope sanity checks only, not independent reconstruction.',
                         'Selected-receiver volume sums do not prove global conservation or boundary flux.',
                         'The sphere-cut nominal cloud is not the real Cryer annular cloud; dp=.01 m, R=.06 m is coarse curvature.',
                         'Binary64 sphere cutoff at boundary lattice points can differ under axis permutation; no rotational-covariance failure is inferred.',
                         'Double manufactured fields test arithmetic only; no quadratic/smooth accuracy, trajectory, physical or public-3D acceptance.']}
    try:
        result.update(review())
        for e in list(BOUND.values()):
            need(measure(e['path']) == e, 'Consumed artifact changed during independent final rehash: ' + e['path'])
        result.update(passed=True, bindings_unchanged=True, unique_bound_artifacts=len(BOUND), inputs=list(BOUND.values()), files=[measure(PNG)])
    except Exception as exc:
        result.update(failure=str(exc), inputs=list(BOUND.values()), files=[measure(PNG)] if PNG.exists() else [])
    CHECK.parent.mkdir(parents=True, exist_ok=True)
    with CHECK.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(result, f, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps({'check': str(CHECK), 'passed': result['passed'], 'native_exit_proven': False}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
