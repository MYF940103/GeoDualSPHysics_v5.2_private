"""Saved-state wall/C proxy only; does not reconstruct the unsaved GPU rejection."""
import os
for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_name, '1')
import argparse
import csv
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import c08_h18_storage_review_r2 as native

T = Path(__file__).resolve().parents[1]
TAG = 'c08_h18_hg_wall_saved_proxy_r1'
JOB = 'c08_h18_hg_opt_full3_GPU_r1'
NOTE = T / 'notes' / (TAG + '.md')
CHECK = T / 'logs' / (TAG + '.check.json')
PREFIX = T / 'figures' / TAG
need, read, stat, bind = native.need, native.read, native.stat, native.bind
PARTS, WALL_ID = tuple(range(89, 99)), 894
f32 = np.float32


def write(path, rows):
    need(rows, 'No diagnostic rows')
    with path.open('x', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def inputs(consumed):
    receipt = T / 'logs' / (JOB + '.native_failed99_r1.check.json')
    q = read(receipt)
    need(q['diagnostic_passed'] and not q['whole_run_passed'] and q['reader_invocations'] == 1,
         'Only the genuine independently decoded failed99 prefix is admitted')
    consumed.append(stat(receipt))
    for key in ('original_failed_run', 'native_completion'):
        bind(q[key]); consumed.append(q[key])
    run, done = read(q['original_failed_run']['path']), read(q['native_completion']['path'])
    need(not run['passed'] and not run['solver_completed'] and run['actual_exit'] == 1
         and run['actual_Win32_exit'] == 1 and run['ownership_failure'] is None,
         'Original failed physical job must remain failed')
    need(done['partial'] and done['saved_prefix_native_passed'] and not done['passed']
         and not done['whole_run_native_passed'] and not done['full_run_completed']
         and done['samples'] == 99 and done['last_saved_part'] == 98
         and done['last_saved_completed_step'] == 2196001
         and done['typed_arrays'] == 22 and done['actual_native_IDs_per_frame'] == 6805
         and not done['native_rewritten'] and not done['unsaved_state_reconstructed'],
         'The full99 partial/native scope differs')
    root = Path(q['native_completion']['path']).parent
    for leaf in ('typed22.bin', 'typed22_layout.csv', 'clocks.csv'):
        refs = [v for v in q['files'] if Path(v['path']).resolve() == (root / leaf).resolve()]
        need(len(refs) == 1, 'Missing exact native export seal: ' + leaf)
        bind(refs[0]); consumed.append(refs[0])
    bundle = native.typed(root, 6805, 99, consumed)
    xml = Path(run['input_xml']['path']); bind(run['input_xml']); consumed.append(run['input_xml'])
    tree = ET.parse(xml).getroot()
    value = lambda name: float(tree.find('execution/constants/' + name).get('value'))
    h = f32(value('h')); mass = f32(value('massfluid')); rho0 = f32(value('rhop0'))
    n0 = f32(tree.find('execution/special/hydromechanics/Porosity').get('value'))
    need(float(h) == done['H'] and h == f32(.072) and mass == f32(3.316)
         and rho0 == f32(2072.5), 'Actual closed H/mass/rho constants differ')
    size = f32(f32(2) * h)
    constants = dict(h=h, radius=float(size), radius2=f32(size * size),
        awen=f32(.557 / (float(h) * float(h))),
        bwen=f32(-2.7852 / (float(h) * float(h) * float(h))),
        volume0=float(mass) / float(rho0), solid0=1. - float(n0),
        almostzero=f32(1e-18), threshold=0.)
    runout = Path(run['output']) / 'Run.out'; consumed.append(stat(runout))
    text = runout.read_text(encoding='utf-8-sig')
    lines = [v for v in text.splitlines() if v.startswith('DynamicPoreWall rejected:')]
    need(len(lines) == 1 and 'stage=1 ' in lines[0] and 'native_id=894 ' in lines[0]
         and 'step_start=10.983389999668779 step=2196678 ' in lines[0]
         and 'mDBC-Threshold=0' in text and 'Finished execution (code=1).' in text,
         'Actual reported wall failure/threshold differs')
    normal = np.array([f32(v) for v in re.search(r'normal=\(([^)]+)\)', lines[0])[1].split(',')], dtype=float)
    need(np.array_equal(normal, np.array([0., 0., float(f32(.04))])), 'Reported axis-plane mirror vector differs')
    return bundle, constants, normal, float(done['source_actual_time_s'])


def kernel(rr2, c, combined):
    """Explicit float32 source operation order; CUDA fast sqrt/FMA is NOT reproduced."""
    rr2 = np.asarray(rr2, dtype=np.float32)
    rad = np.sqrt(rr2).astype(np.float32)
    qq = (rad / c['h']).astype(np.float32)
    one = (f32(1) - f32(.5) * qq).astype(np.float32)
    square = (one * one).astype(np.float32)
    wqq = ((qq + qq).astype(np.float32) + f32(1)).astype(np.float32)
    wab = (((c['awen'] * wqq).astype(np.float32) * square).astype(np.float32) * square).astype(np.float32)
    fac = np.zeros_like(rr2)
    at = rad != 0
    if combined:
        a = (((c['bwen'] * qq[at]).astype(np.float32) * square[at]).astype(np.float32) * one[at]).astype(np.float32)
    else:
        a = ((((c['bwen'] * qq[at]).astype(np.float32) * one[at]).astype(np.float32) * one[at]).astype(np.float32) * one[at]).astype(np.float32)
    fac[at] = (a / rad[at]).astype(np.float32)
    return wab.astype(float), fac.astype(float)


def matrix_metrics(a):
    if not np.all(np.isfinite(a)):
        return dict(det=None, sym_defect=None, sym_eig_min=None, sym_eig_max=None)
    eig = np.linalg.eigvalsh(.5 * (a + a.T))  # Diagnostic only; do not symmetrize interpolation inputs.
    return dict(det=float(a[0, 0] * a[1, 1] - a[0, 1] * a[1, 0]),
        sym_defect=float(abs(a[0, 1] - a[1, 0])), sym_eig_min=float(eig[0]), sym_eig_max=float(eig[1]))


def soil_c(index, pos, J, tree, c, cache):
    if index in cache:
        return cache[index]
    at = np.sort(np.asarray(tree.query_ball_point(pos[index], c['radius'] * (1 + 8 * np.finfo(np.float32).eps)), dtype=np.intp))
    dr = (pos[index] - pos[at]).astype(np.float32)
    rr2 = (dr[:, 0] * dr[:, 0] + dr[:, 1] * dr[:, 1]).astype(np.float32)
    use = (rr2 <= c['radius2']) & (rr2 >= c['almostzero'])
    at, dr, rr2 = at[use], dr[use].astype(float), rr2[use]
    _, fac = kernel(rr2, c, False)
    L = np.zeros((2, 2), dtype=float)
    count = 0
    for displacement, f, j in zip(dr, fac, J[at]):
        volume = c['volume0'] * j
        if volume > 0:
            gradient = f * displacement
            L += -np.outer(displacement, gradient) * volume
            count += 1
    det = float(L[0, 0] * L[1, 1] - L[0, 1] * L[1, 0])
    if det != 0:
        C = np.array([[L[1, 1], -L[0, 1]], [-L[1, 0], L[0, 0]]]) / det
    else:
        C = np.eye(2)  # Original KerFsCorrMatInverse branch, not a proposed repair.
    result = dict(C=C, L=L, moment_det=det, neighbors=count, original_identity_branch=(det == 0), **matrix_metrics(C))
    cache[index] = result
    return result


def collect(bundle, c, normal, source_time):
    attempts, donors = [], []
    for part in PARTS:
        frame = native.core.read22(bundle, part)
        ids = np.array(frame['Idp'][:, 0]); pos3 = np.array(frame['Posd']); pos = pos3[:, (0, 2)]
        J = np.array(frame['PoroVolumeRatio'][:, 0]); tree = cKDTree(pos)
        wall = np.flatnonzero(ids == WALL_ID); need(len(wall) == 1 and ids[wall[0]] < 1805, 'Actual fixed wall894 missing')
        B = pos[wall[0]].copy(); need(abs(B[0] - 4.9) < 1e-12 and abs(B[1] + .02) < 1e-12, 'Actual saved wall894 geometry differs')
        origin = B + normal[[0, 2]]; G = origin.copy(); shift = np.zeros(2); cache = {}
        clock = bundle['clocks'][part]; base = dict(part=part, actual_time_s=float(clock['time_s']),
            actual_tau_s=float(clock['time_s']) - source_time, completed_step=int(clock['completed_step']),
            wall_native_id=WALL_ID, Bx_m=float(B[0]), Bz_m=float(B[1]), saved_state_proxy=True,
            actual_unsaved_GPU_C=False, stored_fixed_J_used=True)
        for attempt in (0, 1):
            at = np.sort(np.asarray(tree.query_ball_point(G, c['radius'] * (1 + 8 * np.finfo(np.float32).eps)), dtype=np.intp))
            at = at[ids[at] >= 2060]
            dx = G - pos[at]; rr2 = np.asarray(dx[:, 0] * dx[:, 0] + dx[:, 1] * dx[:, 1], dtype=np.float32)
            use = rr2 <= c['radius2']; at, dx, rr2 = at[use], dx[use], rr2[use]
            wab, fac = kernel(rr2, c, True); volume = c['volume0'] * J[at]
            w, vx, vz = wab * volume, fac * dx[:, 0] * volume, fac * dx[:, 1] * volume
            M = np.zeros((3, 3)); sums = np.zeros((3, 4)); local = []
            for index, displacement, wi, vxi, vzi in zip(at, dx, w, vx, vz):
                info = soil_c(int(index), pos, J, tree, c, cache); field = info['C'].reshape(4)
                M[0] += [wi, displacement[0] * wi, displacement[1] * wi]
                M[1] += [vxi, displacement[0] * vxi, displacement[1] * vxi]
                M[2] += [vzi, displacement[0] * vzi, displacement[1] * vzi]
                sums[0] += wi * field; sums[1] += vxi * field; sums[2] += vzi * field
                local.append(info)
            detM = float(np.linalg.det(M)); sumw = float(M[0, 0])
            submerged = float(-sum(np.dot(d, [x, z]) for d, x, z in zip(dx, vx, vz)))
            active = submerged > 0 or sumw >= c['threshold'] or (c['threshold'] >= 2 and sumw + 2 >= c['threshold'])
            geometry = active and sumw > 0 and math.isfinite(detM) and abs(detM) >= .001
            near = int(np.argmin(np.sum(dx * dx, axis=1))) if len(at) else None
            nearestfinite = bool(near is not None and np.all(np.isfinite(dx[near]))
                and math.isfinite(float(np.dot(dx[near], dx[near])))
                and np.all(np.isfinite(local[near]['C'])))
            metrics = dict(det=None, sym_defect=None, sym_eig_min=None, sym_eig_max=None)
            Cfit = np.full((2, 2), np.nan); alpha = np.full(len(at), np.nan)
            gradient = np.full((2, 4), np.nan); anchored_dot_residual = None
            if geometry:
                inv = np.linalg.inv(M)  # Independent double proxy inverse, not actual cumath/FMA sequence.
                gradient = inv[1:] @ sums
                fit = local[near]['C'].reshape(4) - gradient[0] * dx[near, 0] - gradient[1] * dx[near, 1]
                if attempt:
                    fit += gradient[0] * shift[0] + gradient[1] * shift[1]
                Q = np.diag([1., -1.]); Cfit = Q @ fit.reshape(2, 2) @ Q; metrics = matrix_metrics(Cfit)
                Gx = inv[1, 0] * w + inv[1, 1] * vx + inv[1, 2] * vz
                Gz = inv[2, 0] * w + inv[2, 1] * vx + inv[2, 2] * vz
                alpha = (shift[0] - dx[near, 0]) * Gx + (shift[1] - dx[near, 1]) * Gz; alpha[near] += 1.
                anchored_dot_residual = float(np.max(abs(sum((a * q['C'].reshape(4) for a, q in zip(alpha, local)), np.zeros(4)) - fit)))
            finite_eigs = [q['sym_eig_min'] for q in local if q['sym_eig_min'] is not None]
            row = dict(**base, attempt=attempt, Gx_m=float(G[0]), Gz_m=float(G[1]),
                shiftx_m=float(shift[0]), shiftz_m=float(shift[1]), real_soil_donors=len(at),
                nearest_saved_native_id=None if near is None else int(ids[at[near]]),
                nearest_distance_m=None if near is None else float(np.linalg.norm(dx[near])),
                original_nearest_finite_on_proxy=nearestfinite,
                original_geometry_predicate_on_proxy=bool(geometry), raw_M_det=detM,
                raw_M_condition=float(np.linalg.cond(M)) if len(at) else None, sumW=sumw, submerged=submerged,
                donor_J_domain_valid=bool(np.all(np.isfinite(J[at]) & (J[at] > c['solid0']))),
                donor_min_C_sym_eig=None if not finite_eigs else min(finite_eigs),
                donor_original_identity_branches=sum(q['original_identity_branch'] for q in local),
                fitted_Cxx=None if not geometry else float(Cfit[0, 0]),
                fitted_Cxz=None if not geometry else float(Cfit[0, 1]),
                fitted_Czx=None if not geometry else float(Cfit[1, 0]),
                fitted_Czz=None if not geometry else float(Cfit[1, 1]),
                fitted_C_det=metrics['det'], fitted_C_sym_defect=metrics['sym_defect'],
                fitted_C_sym_eig_min=metrics['sym_eig_min'], fitted_C_sym_eig_max=metrics['sym_eig_max'],
                negative_alpha_count=None if not geometry else int(np.count_nonzero(alpha < 0)),
                min_alpha=None if not geometry else float(alpha.min()),
                alpha_L1=None if not geometry else float(np.sum(abs(alpha))),
                alpha_sum=None if not geometry else float(alpha.sum()), anchored_dot_residual=anchored_dot_residual)
            attempts.append(row)
            for k, (index, wi, info) in enumerate(zip(at, w, local)):
                donors.append(dict(part=part, actual_time_s=base['actual_time_s'], actual_tau_s=base['actual_tau_s'],
                    attempt=attempt, wall_native_id=WALL_ID, donor_native_id=int(ids[index]),
                    donor_saved_x_m=float(pos[index, 0]), donor_saved_z_m=float(pos[index, 1]), donor_saved_J=float(J[index]),
                    W_times_V=float(wi), alpha=None if not geometry else float(alpha[k]),
                    proxy_Cxx=float(info['C'][0, 0]), proxy_Cxz=float(info['C'][0, 1]),
                    proxy_Czx=float(info['C'][1, 0]), proxy_Czz=float(info['C'][1, 1]),
                    proxy_C_det=info['det'], proxy_C_sym_defect=info['sym_defect'],
                    proxy_C_sym_eig_min=info['sym_eig_min'], proxy_soil_moment_det=info['moment_det'],
                    proxy_soil_neighbors=info['neighbors'], original_identity_branch=info['original_identity_branch'],
                    saved_state_proxy=True, actual_unsaved_GPU_C=False))
            if geometry or not nearestfinite or attempt or not np.any(dx[near] != 0):
                break
            shift -= dx[near]; G -= dx[near]  # Only the original geometry-triggered nearest retry.
    return attempts, donors


def plot(rows):
    last = {q['part']: q for q in rows}; data = [last[p] for p in PARTS]
    t = [q['actual_tau_s'] for q in data]
    val = lambda name: [np.nan if q[name] is None else q[name] for q in data]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
    axes[0, 0].plot(t, np.abs(val('raw_M_det')), 'o-'); axes[0, 0].axhline(.001, c='r', ls='--', label='Original geometry limit')
    axes[0, 0].set(title='Proxy |det MLS M|', yscale='log'); axes[0, 0].legend()
    axes[0, 1].plot(t, val('donor_min_C_sym_eig'), 'o-', label='Minimum donor eigenvalue')
    axes[0, 1].plot(t, val('fitted_C_sym_eig_min'), 's-', label='Fitted wall minimum eigenvalue')
    axes[0, 1].axhline(0, c='k', lw=.8); axes[0, 1].set(title='Symmetric-part eigenvalues (diagnostic only)'); axes[0, 1].legend()
    axes[1, 0].plot(t, val('fitted_C_det'), 'o-'); axes[1, 0].axhline(0, c='r', ls='--', label='Original stage1 determinant rejection')
    axes[1, 0].set(title='Proxy det fitted wall C'); axes[1, 0].legend()
    axes[1, 1].plot(t, val('alpha_L1'), 'o-', label='Sum |alpha|')
    axes[1, 1].plot(t, val('negative_alpha_count'), 's-', label='Negative alpha count'); axes[1, 1].set(title='Anchored extrapolation coefficients'); axes[1, 1].legend()
    for ax in axes.flat:
        ax.set_xlabel('Actual saved tau [s]'); ax.grid(alpha=.2)
    fig.suptitle('Wall 894 saved-state proxy: not the actual unsaved GPU C or rejection branch')
    fig.supxlabel('Stored fixed J; approximate float displacements; native-ID reduction order; independent inverse.\nPosCell/BoundMode/C and the rejected substage were not exported. No operator change or physical acceptance.', fontsize=9)
    out = Path(str(PREFIX) + '_trends.png'); fig.savefig(out, dpi=170); plt.close(fig)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--execution-authorized', action='store_true'); args = parser.parse_args()
    need(args.execution_authorized, 'Root full read and independent offline execution authorization required')
    need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG + '_*')), 'Existing complete/partial artifacts protected')
    consumed = [stat(Path(__file__)), stat(NOTE), stat(Path(native.__file__)), stat(Path(native.core.__file__))]
    result = dict(stage=TAG, analysis_passed=False, saved_state_proxy=True, physical_acceptance=False,
        actual_failure_branch_confirmed=False, actual_unsaved_GPU_C=False, solver_invocations=0,
        native_decodes=0, build_invocations=0, VTK_invocations=0, SHA_scans=0)
    try:
        bundle, constants, normal, source_time = inputs(consumed)
        rows, donor_rows = collect(bundle, constants, normal, source_time)
        need(set(q['part'] for q in rows) == set(PARTS) and 10 <= len(rows) <= 20, 'Closed ten-state/at-most-one-retry scope differs')
        files = [Path(str(PREFIX) + '_attempts.csv'), Path(str(PREFIX) + '_donors.csv')]
        write(files[0], rows); write(files[1], donor_rows); files.append(plot(rows))
        need(all(stat(q['path']) == q for q in consumed), 'An immutable input binding changed')
        result.update(analysis_passed=True, analysis_complete=True, consumed_stats_unchanged=True,
            original_solver_still_failed=True, actual_saved_parts=list(PARTS), attempts=len(rows),
            donor_rows=len(donor_rows), constants={k:float(v) for k,v in constants.items()},
            limitations=['PosCell not exported: proxy uses f32(double position difference) for soil C',
                'Actual GPU cell/sorted-neighbor reduction order unavailable: sums use native ID order',
                'CUDA fast sqrt/FMA and device inverse are not bit-reproduced',
                'Stored fixed J is not a freshly reconstructed stage0 J at the next force call',
                'Saved full-step states are not the rejected unsaved stage1 state',
                'BoundMode not exported; this is not an actual activation-mask audit'],
            files=[stat(x) for x in files], visual_QA_pending=True)
    except Exception as error:
        result['first_failure'] = str(error)
    result['consumed'] = consumed
    CHECK.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    need(result['analysis_passed'], result.get('first_failure', 'Proxy analysis incomplete; preserve partials'))


if __name__ == '__main__':
    main()
