"""Offline review of the completed isolated symmetric-Darcy GPU short pair."""
import os
for name in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ[name] = '1'
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from cryer_start_r1 import TESTS, bound, utc

TAG = 'cryer_symc_gpu_short_review_r1'
OLD = 'cryer_symc_gpu_short_r1'
CHECK = TESTS/'logs'/(TAG+'.check.json')
FIGURES = [TESTS/'figures'/(TAG+'_'+s+'.png') for s in ['history', 'opening']]


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    assert not CHECK.exists() and not any(p.exists() for p in FIGURES), 'Preserve prior review'
    status_path, check_path, run_path = [TESTS/'logs'/(OLD+s) for s in ['.status.json', '.check.json', '.run.json']]
    status, completed = read(status_path), read(check_path)
    assert status['status'] == completed['status'] == 'gpu_short_passed_pending_physical_review'
    assert completed['passed'] and not completed['physical_accepted'] and not completed['peak_or_formal_admitted']
    assert bound(run_path) == completed['run'] == status['run_manifest']
    for entry in completed['artifacts']:
        assert bound(Path(entry['path'])) == entry
    summary_path, pair_path = [TESTS/'figures'/(OLD+s) for s in ['_summary.csv', '_comparisons.csv']]
    a = pd.read_csv(summary_path, float_precision='round_trip')
    b = pd.read_csv(pair_path, float_precision='round_trip')
    assert len(a) == 140 and len(b) == 345
    assert not a.duplicated(['run', 'part']).any() and not b.duplicated(['comparison', 'part']).any()
    runs, sources, comparisons = {}, [bound(p) for p in [Path(__file__), status_path, check_path, run_path, summary_path, pair_path]], {}
    for receipt in completed['runs']:
        name = receipt['name']; v = a[a.run.eq(name)].sort_values('part')
        debug = name.endswith('_dbg'); count = 2 if debug else 69
        assert receipt['passed'] and receipt['exit_code'] == 0 and receipt['owned_exited']
        assert not receipt['observed_surviving_solvers'] and bound(Path(receipt['sealed_completion']['path'])) == receipt['sealed_completion']
        assert len(v) == count and np.array_equal(v.part, np.arange(count))
        assert np.array_equal(v.time_s, np.arange(count)*2.**-13)
        stride = 512 if name.endswith('_h') else 256
        assert np.array_equal(v.saved_step, np.maximum(np.arange(count)*stride-1, 0))
        assert v.true_surface_count.eq(5153).all() and v.changed_fstype_count.eq(0).all()
        assert v.center_fixed_material_count.eq(18).all()
        assert v.loc[v.time_s.gt(2.**-7), 'true_surface_pressure_absmax_pa'].eq(0).all()
        assert v.dterror_s.le(1e-14).all() and v.fixed_to_pore_dt_ratio.le(1).all()
        assert v.loc[v.part.gt(0), 'actual_radial_force_N'].gt(0).all()
        if debug:
            assert receipt['memcheck_zero_errors']
            continue
        assert receipt['equilibrium']['equilibrium_diagnostic_passed']
        for key in ['cpu_gpu', 'raw_option', 'independent_half']:
            if key not in receipt:
                continue
            r = receipt[key]; pair = b[b.comparison.eq(r['meaning'])].sort_values('part')
            assert len(pair) == 69 and np.array_equal(pair.part, np.arange(69))
            assert np.array_equal(pair.time_s, np.arange(69)*2.**-13)
            assert np.isclose(pair.pressure_rms_pa.max(), r['max_pressure_rms_pa'], rtol=1e-14, atol=1e-14)
            assert np.isclose(pair.material_displacement_max_mm.max(), r['max_displacement_mm'], rtol=1e-14, atol=1e-14)
            if key != 'raw_option':
                assert r['passed'] and pair.guarded.eq(True).all()
                assert pair.pressure_rms_pa.le(5).all() and pair.material_displacement_max_mm.le(.005).all()
                assert pair.fstype_mismatches.eq(0).all() and pair.drained_mask_mismatches.eq(0).all()
            else:
                assert r['passed'] is None and pair.guarded.eq(False).all()
            comparisons[r['meaning']] = r
        runs['on_'+name[-1]] = v
    for suffix, tag in [('c', 'cryer_preload_peak_r1'), ('h', 'cryer_preload_peak_half_r1')]:
        cp, rp = [TESTS/'logs'/(tag+s) for s in ['.check.json', '.run.json']]
        old_check, old_run = read(cp), read(rp)
        assert old_check['passed'] and bound(rp) == old_check['run_manifest']
        path = TESTS/'figures'/(tag+'_summary.csv')
        assert bound(path) in old_run['artifacts']
        v = pd.read_csv(path, float_precision='round_trip')
        assert len(v) == 577
        v = v[v.part.le(68)].sort_values('part')
        assert len(v) == 69 and np.array_equal(v.time_s, np.arange(69)*2.**-13)
        runs['off_'+suffix] = v
        sources += [bound(p) for p in [cp, rp, path]]
    plt.rcParams.update({'font.family': 'Arial', 'font.size': 10, 'axes.grid': True,
                         'grid.alpha': .2, 'figure.dpi': 150})
    styles = [('off_c', '#1f77b4', '-', 'Receiver C, coarse'), ('off_h', '#1f77b4', '--', 'Receiver C, half'),
              ('on_c', '#d95f02', '-', 'Symmetric C, coarse'), ('on_h', '#d95f02', '--', 'Symmetric C, half')]
    metrics = [('center_pressure_mean_pa', 1e-3, 'Fixed 18-ID center pressure (kPa)'),
               ('pressure_mean_pa', 1e-3, 'Volume-weighted pressure (kPa)'),
               ('shell_inward_mean_mm', 1., 'Material shell inward displacement (mm)'),
               ('total_stress_target_six_rms_pa', 1., 'Total-stress target residual, six-component RMS (Pa)'),
               ('speed_max_m_s', 1., 'Maximum particle speed (m/s)')]
    for opening, output in [(False, FIGURES[0]), (True, FIGURES[1])]:
        fig, axes = plt.subplots(2, 3, figsize=(14, 8.5)); ax = axes.ravel()
        for suffix, color, line, label in styles:
            v = runs[suffix]
            if opening:
                v = v[v.part.ge(64)]
            x = (v.time_s-(2.**-7 if opening else 0))*1000
            for panel, (column, scale, ylabel) in zip(ax, metrics):
                panel.plot(x, v[column]*scale, line, color=color, lw=1.5,
                           marker='o' if opening else None, markersize=3, label=label)
                panel.set_ylabel(ylabel)
        if opening:
            for suffix, line in [('c', '-'), ('h', '--')]:
                pair = b[b.comparison.eq(OLD+'_'+suffix+':symC_vs_raw_GPU') & b.part.ge(64)]
                ax[5].plot((pair.time_s-2.**-7)*1000, pair.pressure_rms_pa, line,
                           color='#d95f02', marker='o', ms=3, label='Option difference, '+('coarse' if suffix == 'c' else 'half'))
            ax[5].set_ylabel('Same-dt option pressure-field RMS difference (Pa)')
            title = 'Cryer GPU: first 0.488 ms after drainage opening'
            caption = 'Only four post-opening saves. The tau=0 point is pre-open; option differences are not theory errors.'
        else:
            for label, color, line, meaning in [
                    ('GPU half', '#d95f02', '-', OLD+'_h:GPU_half'),
                    ('GPU vs CPU coarse', '#2ca02c', '-', OLD+'_c:GPU_vs_CPU_symC'),
                    ('GPU vs CPU half', '#2ca02c', '--', OLD+'_h:GPU_vs_CPU_symC')]:
                pair = b[b.comparison.eq(meaning)]
                ax[5].plot(pair.time_s*1000, pair.pressure_rms_pa, line, color=color, label=label)
            ax[5].set_ylabel('Symmetric-C pressure-field RMS difference (Pa)')
            title = 'Cryer GPU: preload and drainage-opening short comparison'
            caption = 'Vertical lines: ramp end 3.90625 ms; drainage event 7.8125 ms. Full startup retained; no peak claim.'
            for panel in ax:
                panel.axvline(2.**-8*1000, color='.5', ls=':', lw=1)
                panel.axvline(2.**-7*1000, color='.25', ls='-.', lw=1)
        ax[5].legend(fontsize=8)
        for panel in ax:
            panel.set_xlabel('Time since drainage event, tau (ms)' if opening else 'Actual saved time (ms)')
        handles, labels = ax[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='upper center', ncol=4, bbox_to_anchor=(.5, .955), frameon=False)
        fig.suptitle(title, y=.994, fontsize=14); fig.text(.5, .012, caption, ha='center', fontsize=9)
        fig.tight_layout(rect=(0, .045, 1, .92)); fig.savefig(output, dpi=180); plt.close(fig)
    final = {}
    for suffix in ['c', 'h']:
        off, on = runs['off_'+suffix].iloc[-1], runs['on_'+suffix].iloc[-1]
        final[suffix] = {k: dict(receiver=float(off[k]), symmetric=float(on[k]), difference=float(on[k]-off[k])) for k, _, _ in metrics}
    result = dict(utc=utc(), analysis_checks_passed=True, visual_review_passed=False,
        sources=sources, artifacts=[bound(p) for p in FIGURES], comparisons=comparisons,
        checked_csv_rows=dict(summary=len(a), comparisons=len(b)), endpoint_same_dt_changes=final,
        actual_saved_window_s=dict(start=0., end=.00830078125, drainage=2.**-7, last_tau=.00048828125, post_opening_saves=4),
        conclusion='GPU short implementation checks pass; not a Mandel-peak improvement or physical/formal acceptance.',
        limitations=['Independent native/hash audit is separately required; CSV reconciliation alone is not sufficient.',
                     'Debug checks memory and startup only, not Release 0-ULP or temporal accuracy.',
                     'Only four post-opening saves, far earlier than the reference peak near tau=.04205s.',
                     'CPU/GPU and half-step bounds cover69 saves, not a peak or full trajectory.'])
    with CHECK.open('x', encoding='utf8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(dict(analysis_checks_passed=True, artifacts=result['artifacts'], endpoint=final), indent=2))


if __name__ == '__main__':
    main()
