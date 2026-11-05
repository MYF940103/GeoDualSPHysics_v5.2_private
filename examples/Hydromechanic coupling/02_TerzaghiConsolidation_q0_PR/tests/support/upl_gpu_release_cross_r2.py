"""Offline Release/CPU comparison; preserve the rejected all-field initial bit check."""
from pathlib import Path
import csv
import json
import os
os.environ['OPENBLAS_NUM_THREADS'] = os.environ['MKL_NUM_THREADS'] = '1'
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

T = Path(__file__).resolve().parents[1]
TAG = 'upl_gpu_stabilizers_release_cross_r2'
CPU = T / 'outputs/upl_bigstep_2tv_CPU1_r1_native_r1'
GPU = T / 'outputs/upl_gpu_stabilizers_release_short_r1_native'
LOG = T / 'logs'


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def stat(p):
    s = p.stat()
    return dict(path=str(p.resolve()), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def main():
    check = LOG / (TAG + '.json')
    plot, table = [T / 'figures' / (TAG + x) for x in ('.png', '.csv')]
    assert not any(p.exists() for p in (check, plot, table))
    run = read(LOG / 'upl_gpu_stabilizers_release_short_r1.run.json')
    native = read(LOG / 'upl_gpu_stabilizers_release_short_r1.native.json')
    assert run['passed'] and native['passed'] and native['original_native_guards_passed']
    assert read(Path(run['call']['path']))['exit_code'] == 0
    assert read(Path(native['call']['path']))['exit_code'] == 0
    assert all(stat(Path(v['path'])) == v for v in native['files'])
    assert read(CPU / 'completion.json')['passed']
    fields = list(csv.DictReader((GPU / 'columns.csv').open(newline='')))
    assert fields == list(csv.DictReader((CPU / 'columns.csv').open(newline='')))
    for leaf in ('native_ids.csv', 'fixed_ids.csv'):
        assert (CPU / leaf).read_bytes() == (GPU / leaf).read_bytes()

    def arrays(directory, count):
        p = directory / 'physical.bin'
        assert tuple(np.fromfile(p, '<u4', 3)) == (1000, 26, count)
        assert p.stat().st_size == 12 + 208008 * count
        return np.memmap(p, dtype=np.dtype([('t', '<f8'), ('q', '<f8', (1000, 26))]),
                         offset=12, shape=(count,), mode='r')[:150]

    def clocks(directory, count):
        p = directory / 'clock.bin'
        assert tuple(np.fromfile(p, '<u4', 2)) == (count, 28)
        return np.memmap(p, dtype=np.dtype([('t', '<f8'), ('step', '<u4'),
                         ('dt', '<f8'), ('signed_error', '<f8')]), offset=8, shape=(count,), mode='r')[:150]

    a, b = arrays(CPU, 1682), arrays(GPU, 150)
    ca, cb = clocks(CPU, 1682), clocks(GPU, 150)
    assert np.array_equal(a['t'], b['t']) and np.array_equal(ca['t'], a['t'])
    assert np.array_equal(cb['t'], b['t']) and np.array_equal(ca['step'], cb['step'])
    assert np.array_equal(ca['dt'], cb['dt']) and np.all(ca['dt'] == 6.250143051147461e-6)
    q, v = a['q'], b['q']
    assert np.isfinite(q).all() and np.isfinite(v).all()
    # These are input/initial physical states. The three normals are derived
    # backend outputs, retained and measured below, not silently zeroed/masked.
    input_columns = list(range(18)) + list(range(21, 26))
    assert q[0][:, input_columns].tobytes() == v[0][:, input_columns].tobytes()
    initial_bits = q[0].view('<u8') != v[0].view('<u8')
    initial_differences = [{**f, 'differing_material_count': int(initial_bits[:, i].sum()),
                            'maximum_absolute_difference': float(np.abs(v[0, :, i] - q[0, :, i]).max())}
                           for i, f in enumerate(fields)]
    x0 = q[0, :, :3]
    top, bottom = x0[:, 2] == x0[:, 2].max(), x0[:, 2] == x0[:, 2].min()
    assert top.sum() == bottom.sum() == 10
    rows = []
    v0 = float(np.float32(.21)) / 2100.
    for i in range(150):
        d = v[i] - q[i]
        active = (q[i, :, 17] != 0) | (v[i, :, 17] != 0)
        proxy = [np.sum((v0 * (1100. + 1000. * s[:, 8]))[:, None] * s[:, 22:25], axis=0)
                 for s in (q[i], v[i])]
        row = dict(part=i, actual_time_s=float(a['t'][i]), saved_step=int(ca['step'][i]),
            pressure_RMS_Pa=float(np.sqrt(np.mean(d[:, 6] ** 2))),
            material_XYZ_max_mm=float(np.linalg.norm(d[:, :3], axis=1).max() * 1000),
            stress6_RMS_Pa=float(np.sqrt(np.mean(np.sum(d[:, 10:16] ** 2 * [1, 2, 2, 1, 2, 1], axis=1)))),
            J_max_difference=float(np.abs(d[:, 8]).max()),
            FSType_different_count=int(np.count_nonzero(d[:, 17])),
            FSNormal_all_max_difference=float(np.abs(d[:, 18:21]).max()),
            FSNormal_active_max_difference=float(np.abs(d[active, 18:21]).max()),
            saved_proxy_backend_difference_N_m=float(np.linalg.norm(proxy[1] - proxy[0])))
        for label, s, clock, load in [('CPU', q[i], ca, proxy[0]), ('GPU', v[i], cb, proxy[1])]:
            row.update({label + '_mean_pressure_Pa': float(s[:, 6].mean()),
                label + '_top_settlement_mm': float((x0[top, 2] - s[top, 2]).mean() * 1000),
                label + '_bottom_settlement_mm': float((x0[bottom, 2] - s[bottom, 2]).mean() * 1000),
                label + '_signed_dterror_s': float(clock['signed_error'][i]),
                label + '_saved_load_proxy_z_N_m': float(load[2])})
        rows.append(row)
    with table.open('x', newline='', encoding='utf-8') as stream:
        w = csv.DictWriter(stream, fieldnames=rows[0]); w.writeheader(); w.writerows(rows)
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), constrained_layout=True)
    times = [r['actual_time_s'] for r in rows]
    for ax, key, title in zip(axes[0], ['mean_pressure_Pa', 'top_settlement_mm', 'bottom_settlement_mm'],
                             ['Mean pore pressure (Pa)', 'Top material settlement (mm)', 'Bottom material settlement (mm)']):
        for label in ['CPU', 'GPU']:
            ax.plot(times, [r[label + '_' + key] for r in rows], label=label)
        ax.set_title(title); ax.legend()
    for ax, key, title in zip(axes[1], ['pressure_RMS_Pa', 'material_XYZ_max_mm', 'FSNormal_active_max_difference'],
                             ['Pressure RMS difference (Pa)', 'Maximum per-ID XYZ difference (mm)', 'Active FS normal maximum difference']):
        ax.plot(times, [r[key] for r in rows]); ax.set_title(title)
    for ax in axes.flat:
        ax.set_xlabel('Actual saved time (s)'); ax.grid(alpha=.25)
    fig.suptitle('GPU Release / retained CPU: 150 actual shared saves\nDerived normals differ; initial physical inputs are exact. No full-cycle acceptance.')
    with plot.open('xb') as stream: fig.savefig(stream, dpi=150, format='png')
    plt.close(fig)
    maxima = {k: max(r[k] for r in rows) for k in ['pressure_RMS_Pa', 'material_XYZ_max_mm',
              'stress6_RMS_Pa', 'J_max_difference', 'FSNormal_all_max_difference',
              'FSNormal_active_max_difference', 'saved_proxy_backend_difference_N_m']}
    passed = (maxima['pressure_RMS_Pa'] <= 5 and maxima['material_XYZ_max_mm'] <= .005
              and maxima['saved_proxy_backend_difference_N_m'] <= .001
              and all(r['FSType_different_count'] == 0 for r in rows))
    result = dict(stage=TAG, passed=passed, physical_acceptance=False, samples=150,
        original_initial_common26_bit_gate_passed=False,
        original_review_failure_retained='logs/upl_gpu_stabilizers_release_short_r1.review_failure.json',
        initial_input_physical_columns_bit_exact=input_columns,
        initial_all_26_column_bit_differences=initial_differences, maxima=maxima,
        original_numeric_budgets=dict(pressure_RMS_Pa=5, per_material_XYZ_mm=.005, actual_clock_s=1e-14,
                                     saved_proxy_backend_N_m=.001),
        all_150_actual_times_identical=True, all_1040_IDs_and_22_native_arrays_checked=True,
        original_fields_records_or_signed_diagnostics_removed=False,
        true_force_stage_budget_observed=False, source_run=stat(LOG / 'upl_gpu_stabilizers_release_short_r1.run.json'),
        source_native=stat(LOG / 'upl_gpu_stabilizers_release_short_r1.native.json'),
        outputs=[stat(table), stat(plot)], fresh_SHA_scans=0)
    with check.open('x', encoding='utf-8') as stream: json.dump(result, stream, indent=2)
    print(json.dumps(dict(passed=passed, maxima=maxima)))
    assert passed, 'Preserve failed analysis and completed native solve'


if __name__ == '__main__':
    main()
