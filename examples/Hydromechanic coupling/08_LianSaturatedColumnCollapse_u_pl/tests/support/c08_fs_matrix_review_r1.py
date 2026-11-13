"""Offline descriptive review of the sealed corrected-r2 CPU pressure matrices."""
import argparse, csv, json, os
from pathlib import Path
for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_name, '1')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

T = Path(__file__).resolve().parents[1]
TAG, DT, N = 'c08_fs_matrix_review_r1', 5e-6, 81
SEEN = {}
def need(ok, message):
    if not ok: raise RuntimeError(message)
def key(path): return os.path.normcase(str(Path(path).resolve()))
def stamp(path):
    p = Path(path).resolve(); s = p.stat()
    need(p.is_file(), f'Not a file: {p}')
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)
def bound(entry):
    p = key(entry['path']); actual = stamp(entry['path'])
    need(actual['bytes'] == entry['bytes'] and actual['mtime_ns'] == entry['mtime_ns'], f'Binding changed: {p}')
    need(p not in SEEN or (SEEN[p]['bytes'], SEEN[p]['mtime_ns']) == (actual['bytes'], actual['mtime_ns']), f'Conflicting binding: {p}'); SEEN[p] = actual
    return Path(actual['path'])
def walk(value):
    if isinstance(value, dict):
        if {'path', 'bytes', 'mtime_ns'} <= value.keys(): bound(value)
        for child in value.values(): walk(child)
    elif isinstance(value, list):
        for child in value: walk(child)
def load(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def call_receipt(entry):
    c = load(bound(entry)); walk(c); child = c['child']; owner = c['owner']
    need(c['actual_Popen_wait_exit'] == c['actual_Win32_exit'] == 0 and c['ownership_failure'] is None, 'Recorded process failed ownership/exit')
    need(child['pid'] > 0 and child['creation_filetime_100ns'] > 0 and child['parent_pid'] == owner['pid'], 'Missing recorded actual child handle identity')
    need(key(child['exe']) == key(c['program']) and child['argv'] == [c['program'], *c['arguments']], 'Recorded executable/arguments differ')
    return c
def table(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f: rows = list(csv.DictReader(f))
    need(all(np.isfinite(float(v)) for r in rows for v in r.values()), f'Nonfinite CSV: {path}')
    return rows
def indexed(rows, columns):
    result = {tuple(int(r[c]) for c in columns): r for r in rows}
    need(len(result) == len(rows), 'Duplicate CSV keys'); return result
def write_csv(path, rows):
    with path.open('x', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def metrics(a, weights):
    values, vectors = np.linalg.eig(a)
    residual = np.max(np.linalg.norm(a @ vectors - vectors * values[None, :], axis=0) / np.linalg.norm(vectors, axis=0))
    eig = values[np.lexsort((values.imag, values.real))]
    diagonal = np.diag(a); off = a.copy(); np.fill_diagonal(off, 0)
    rowabs = np.abs(a).sum(axis=1); left = weights @ a
    m = np.eye(N) + DT*a + .5*DT*DT*(a @ a); roots = np.sqrt(weights)
    weighted_m = roots[:, None]*m/roots[None, :]; weighted_a = roots[:, None]*a/roots[None, :]
    result = dict(diagonal_min_per_s=float(diagonal.min()), diagonal_max_per_s=float(diagonal.max()),
        offdiagonal_negative_count=int(np.count_nonzero(off < 0)), offdiagonal_min_per_s=float(off.min()),
        row_abs_gain_max_per_s=float(rowabs.max()), gershgorin_right_max_per_s=float((diagonal+np.abs(off).sum(axis=1)).max()),
        right_null_absmax_per_s=float(np.abs(a.sum(axis=1)).max()), storage_left_defect_per_s=float(np.abs(left).max()/weights.sum()),
        storage_left_relative=float(np.abs(left).sum()/(weights.sum()*max(float(rowabs.max()), np.finfo(float).tiny))),
        eigen_max_real_per_s=float(eig.real.max()), eigen_min_real_per_s=float(eig.real.min()), eigen_max_abs_imag_per_s=float(np.abs(eig.imag).max()),
        eigen_residual_max_per_s=float(residual), midpoint_spectral_radius=float(np.abs(1+DT*eig+.5*(DT*eig)**2).max()),
        midpoint_inf_norm=float(np.linalg.norm(m, np.inf)), midpoint_storage_sigma_max=float(np.linalg.svd(weighted_m, compute_uv=False)[0]),
        storage_numerical_abscissa_per_s=float(np.linalg.eigvalsh(.5*(weighted_a+weighted_a.T)).max()))
    return result, eig
def figure(path, summaries, spectra):
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), constrained_layout=True)
    colors = dict(Raw='#2457a7', Normal='#c86718')
    for profile in (0, 1):
        ax = axes[0, profile]
        for label in ('Raw', 'Normal'):
            a, r = spectra[(label, profile)]
            ax.scatter(a.real, a.imag, s=18, color=colors[label], label=f'{label} actual')
            ax.scatter(r.real, r.imag, s=17, marker='x', color=colors[label], alpha=.65, label=f'{label} reference')
        ax.axvline(0, color='black', lw=.7); ax.set(title=('J=1' if profile == 0 else 'Fixed variable J')+' spectrum', xlabel='Re(lambda) [1/s]', ylabel='Im(lambda) [1/s]'); ax.legend(fontsize=7)
    real = np.concatenate([v.real for pair in spectra.values() for v in pair]); imag = np.concatenate([v.imag for pair in spectra.values() for v in pair])
    dx = max(float(np.ptp(real)), 1.)*.025; dy = max(float(np.ptp(imag)), 1.)*.05
    for ax in axes[0, :2]: ax.set_xlim(float(real.min()-dx), float(real.max()+dx)); ax.set_ylim(float(imag.min()-dy), float(imag.max()+dy))
    x = np.arange(4); labels = [f"{r['mode']}\nJ{r['profile']}" for r in summaries]
    ax = axes[0, 2]
    for prefix, marker in (('actual_', 'o'), ('reference_', 'x')):
        y = [r[prefix+'eigen_max_real_per_s'] for r in summaries]; ax.plot(x, y, marker=marker, label=prefix[:-1])
    ax.axhline(0, color='black', lw=.7); ax.set(title='Near-zero spectral edge (unthresholded)', ylabel='max Re(lambda) [1/s]'); ax.legend(fontsize=8)
    ax = axes[1, 0]
    for metric, marker, short in (('midpoint_spectral_radius', 'o', 'rho'), ('midpoint_inf_norm', 's', 'inf'), ('midpoint_storage_sigma_max', '^', 'storage SV')):
        for prefix, style in (('actual_', '-'), ('reference_', ':')):
            ax.plot(x, [r[prefix+metric]-1 for r in summaries], marker=marker, ls=style, label=short+' '+prefix[:-1])
    ax.set_yscale('symlog', linthresh=1e-10); ax.axhline(0, color='black', lw=.7); ax.set(title='Explicit midpoint, dt=5 microseconds', ylabel='gain - 1 (symlog display)'); ax.legend(fontsize=7, ncol=2)
    axes[1, 1].bar(x, [r['right_null_budget_ratio_max'] for r in summaries]); axes[1, 1].set(title='Right-null residual / propagated row budget', ylabel='maximum row ratio')
    for prefix, marker in (('actual_', 'o'), ('reference_', 'x')):
        axes[1, 2].plot(x, [r[prefix+'storage_left_relative'] for r in summaries], marker=marker, label=prefix[:-1])
    axes[1, 2].set(title='Storage-weighted left defect', ylabel='||w^T A||1 / (sum(w) ||A||inf)'); axes[1, 2].legend(fontsize=8)
    for ax in (axes[0, 2], *axes[1, :]): ax.set_xticks(x, labels, fontsize=8)
    for ax in axes.flat: ax.grid(alpha=.2)
    fig.suptitle('C08 frozen pressure matrices: corrected-r2 CPU data\n81 manufactured particles; no coupled or physical admission', fontsize=13)
    with path.open('xb') as f: fig.savefig(f, format='png', dpi=180)
    plt.close(fig)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--prefix', type=Path, default=T/'figures'/TAG); ap.add_argument('--check', type=Path, default=T/'logs'/f'{TAG}.check.json'); args = ap.parse_args()
    outputs = [Path(str(args.prefix)+s) for s in ('.summary.csv', '.eigenvalues.csv', '.png')] + [args.check]
    need(len({key(p) for p in outputs}) == 4 and all(not p.exists() for p in outputs), 'Fresh output paths required')
    rp = T/'logs/c08_fs_matrix_cpu_r2.run.json'; bp = T/'logs/c08_fs_matrix_cpu_r2.build.json'; run = load(rp); build = load(bp)
    for p in (rp, bp, Path(__file__), T/'notes'/f'{TAG}.md'): bound(stamp(p))
    walk(run); walk(build)
    need(run['stage'] == 'c08_fs_matrix_cpu_r2' and run['passed'] and run['consumed_stats_unchanged'] and not run['physical_acceptance'] and run['solver_invocations'] == 0, 'Unqualified run receipt')
    need(key(bound(run['build'])) == key(bp) and build['stage'] == 'c08_fs_matrix_cpu_r2.build' and build['passed'] and build['consumed_stats_unchanged'] and build['actual_typed_exit_code'] == build['actual_Win32_exit'] == 0, 'Unqualified build receipt')
    need(build['configuration'] == 'DebugCPU' and build['actual_link_objects'] == 87 and build['shared_entry_object'] and build['GPU_actions'] == build['solver_invocations'] == 0 and Path(build['fixture']['path']).name == 'c08_fs_matrix_cpu_r2.cpp', 'Wrong corrected CPU build')
    for c in build['calls']: call_receipt(c)
    objects = {mode: {key(e['path']) for e in build['project_objects'][mode]} for mode in ('Raw', 'Normal')}
    need(all(len(s) == 87 for s in objects.values()) and objects['Raw']-objects['Normal'] == {key(build['original_cpu_object']['path'])} and objects['Normal']-objects['Raw'] == {key(build['candidate_object']['path'])}, 'CPU object intervention differs')
    need(key(build['fixture_object']['path']) in objects['Raw'] & objects['Normal'] and all(Path(p).name.lower() != 'main.obj' for s in objects.values() for p in s), 'Entry/main object mismatch')
    completed = {e['label']: e for e in run['completed']}; need(set(completed) == {'Raw', 'Normal'} and len(run['completed']) == 2, 'Expected exactly two real CPU executions')
    data = {}
    for label in ('Raw', 'Normal'):
        e = completed[label]; folder = T/'outputs'/f'c08_fs_matrix_cpu_r2_{label.lower()}'; need(e['program'] == build['programs'][label], 'Program build/run binding differs')
        call = call_receipt(e['actual_call']); need(key(call['program']) == key(e['program']['path']) and call['arguments'][:3] == ['--expect', label.lower(), '--out'] and len(call['arguments']) == 4 and key(call['arguments'][3]) == key(folder), 'Wrong actual run arguments')
        comp = load(bound(e['completion'])); need(key(e['completion']['path']) == key(folder/'completion.json'), 'Completion folder differs')
        need(comp['stage'] == 'c08_fs_matrix_cpu_r2' and comp['formula_reference_matched'] and comp['expected_reference'] == label.lower() and not comp['reference_mode_changes_production'] and comp['operator_scope'] == 'frozen_pressure_only_prescribed_Ace_J' and comp['kernel'] == 'Wendland' and comp['production_FS_C'] and comp['completed_physical_steps'] == 0 and not comp['physical_acceptance'], 'Completion scope differs')
        need(comp['basis_base_Pa'] == -16 and comp['basis_delta_Pa'] == .25 and comp['Kw_Pa'] == 1e9 and comp['Ck'] == 2 and len(comp['profiles']) == 2, 'Unexpected fixed basis/material')
        need(comp['dp'] == .04 and comp['H_actual_m'] == float(np.float32(.072)) and comp['n0_actual'] == float(np.float32(.35)) and comp['k0_actual_m_s'] == float(np.float32(.0002)), 'C08 material/support differs')
        for profile, q in enumerate(comp['profiles']): need(q['profile'] == profile and (q['controls'], q['base_rows'], q['matrix_rows']) == (486, 81, 6561), 'Incomplete component counts')
        need({key(v['path']) for v in e['files']} == {key(folder/name) for name in ('matrix.csv', 'controls.csv', 'nodes.csv')}, 'Output receipt file set differs')
        m, c, n = (table(folder/name) for name in ('matrix.csv', 'controls.csv', 'nodes.csv')); need((len(m), len(c), len(n)) == (13122, 1134, 162), 'CSV counts differ')
        mi = indexed(m, ('profile', 'row_id', 'column_id')); ci = indexed(c, ('profile', 'field_0hydro_1Ace_2chain_3base', 'free_on', 'native_id')); ni = indexed(n, ('profile', 'native_id'))
        need(set(mi) == {(p,i,j) for p in (0,1) for i in range(N) for j in range(N)} and set(ni) == {(p,i) for p in (0,1) for i in range(N)}, 'Incomplete native ID coverage')
        expected_controls = {(p,f,on,i) for p in (0,1) for f in range(3) for on in (0,1) for i in range(N)} | {(p,3,1,i) for p in (0,1) for i in range(N)}
        need(set(ci) == expected_controls, 'Control/baseline coverage differs')
        for (p,f,on,i), r in ci.items():
            actual, reference, budget = (float(r[k]) for k in ('actual_rate_Pa_s', 'reference_rate_Pa_s', 'arithmetic_budget_Pa_s'))
            need(float(r['p_Pa']) < 0 and budget > 0 and abs(actual-reference) <= budget, 'Control formula/budget failed')
            need(int(r['fstype']) == int(ni[p,i]['fstype']), 'Control FS differs')
            if f == 0: need(abs(actual) <= 2*budget+float(r['input_quantization_budget_Pa_s']), 'F0 control failed')
            if f == 3: need(actual == reference == 0, 'Constant basis baseline is not zero')
            if on and f < 3 and int(r['fstype']) not in (2,3): need(r['actual_bits'] == ci[p,f,0,i]['actual_bits'], 'Inner OFF/ON bits differ')
        arrays = {}
        for p in (0,1):
            a, ref, b = (np.array([[float(mi[p,i,j][name]) for j in range(N)] for i in range(N)]) for name in ('actual_A_per_s', 'reference_A_per_s', 'propagated_entry_budget_per_s'))
            need(np.all(b > 0) and np.all(np.abs(a-ref) <= b), 'Matrix formula/entry budget failed')
            w = np.array([float(ni[p,i]['storage_weight_Vn_Kw']) for i in range(N)]); need(np.all(w > 0), 'Storage weights are not positive')
            rowb = b.sum(axis=1); need(np.all(np.abs(a.sum(axis=1)) <= rowb) and np.all(np.abs(ref.sum(axis=1)) <= rowb), 'Right-null exceeds propagated row budget')
            chain_count = sum(abs(comp['Kw_Pa']/float(ni[p,i]['n'])/(1000*9.80665)*float(ci[p,2,1,i]['chain'])) > float(ci[p,2,1,i]['arithmetic_budget_Pa_s']) for i in range(N) if int(ni[p,i]['fstype']) in (2,3))
            need(chain_count == comp['profiles'][p]['nonzero_FS_chain_witnesses'] and (chain_count > 0 if p else chain_count == 0), 'Variable-k FS chain witness differs')
            arrays[p] = (a, ref, b, w)
        data[label] = dict(folder=folder, comp=comp, controls=ci, nodes=ni, arrays=arrays)
    need((data['Raw']['folder']/'nodes.csv').read_bytes() == (data['Normal']['folder']/'nodes.csv').read_bytes(), 'Node CSVs differ bytewise')
    off_count = inner_count = 0
    for k, r in data['Raw']['controls'].items():
        if k[2] == 0 or int(r['fstype']) not in (2,3):
            need(r['actual_bits'] == data['Normal']['controls'][k]['actual_bits'], 'Cross-program OFF/inner ON bits differ')
            off_count += k[2] == 0; inner_count += k[2] == 1
    summaries, eigenrows, spectra = [], [], {}
    for label in ('Raw', 'Normal'):
        for p in (0,1):
            a, ref, b, w = data[label]['arrays'][p]; inner = [int(data[label]['nodes'][p,i]['fstype']) not in (2,3) for i in range(N)]
            need(np.array_equal(a[inner], data['Raw']['arrays'][p][0][inner]), 'Cross-program inner basis entries differ exactly')
            actual, ea = metrics(a, w); reference, er = metrics(ref, w); spectra[label,p] = ea, er
            row = dict(mode=label, profile=p, dt_s=DT, **{'actual_'+k:v for k,v in actual.items()}, **{'reference_'+k:v for k,v in reference.items()})
            off = ~np.eye(N, dtype=bool); row.update(entry_reference_ratio_max=float(np.max(np.abs(a-ref)/b)), right_null_budget_ratio_max=float(np.max(np.abs(a.sum(axis=1))/b.sum(axis=1))), budget_norm_inf_per_s=float(np.linalg.norm(b,np.inf)), budget_norm2_upper_per_s=float(np.sqrt(np.linalg.norm(b,1)*np.linalg.norm(b,np.inf))), actual_minus_reference_norm2_per_s=float(np.linalg.norm(a-ref,2)), budget_resolved_negative_offdiagonal_count=int(np.count_nonzero((a+b < 0)&off)))
            summaries.append(row)
            for i, (va, vr) in enumerate(zip(ea, er)): eigenrows.append(dict(mode=label, profile=p, independently_sorted_rank=i, actual_real_per_s=float(va.real), actual_imag_per_s=float(va.imag), reference_real_per_s=float(vr.real), reference_imag_per_s=float(vr.imag), actual_midpoint_modulus=float(abs(1+DT*va+.5*(DT*va)**2)), reference_midpoint_modulus=float(abs(1+DT*vr+.5*(DT*vr)**2))))
    need(len(summaries) == 4 and len(eigenrows) == 324, 'Incomplete spectral output')
    for p in outputs: p.parent.mkdir(parents=True, exist_ok=True)
    write_csv(outputs[0], summaries); write_csv(outputs[1], eigenrows); figure(outputs[2], summaries, spectra)
    for entry in list(SEEN.values()): bound(entry)
    result = dict(stage=TAG, analysis_complete=True, physical_acceptance=False, scientific_admission_decided=False, dt_s=DT, source_run_bindings_current=True, node_csv_byte_exact=True, cross_program_OFF_bit_checks=off_count, cross_program_inner_ON_control_bit_checks=inner_count, summary_rows=4, eigenvalue_rows=324, matrix_normalized_or_modified=False, M_matrix_assumed=False, eigenvalue_uncertainty_certified=False, uncertainty_note='Entry budgets bound operator differences; no eigenvalue shift bound or Bauer-Fike claim is inferred from a matrix norm.', consumed=list(SEEN.values()), outputs=[stamp(p) for p in outputs[:3]])
    with outputs[3].open('x', encoding='utf-8') as f: json.dump(result, f, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps(dict(analysis_complete=True, physical_acceptance=False, check=str(outputs[3]))))
if __name__ == '__main__': main()
