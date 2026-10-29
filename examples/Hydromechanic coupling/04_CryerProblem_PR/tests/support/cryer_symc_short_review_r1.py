"""Offline figures and scope review for the completed CPU symmetric-Darcy shorts."""
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

TAG = 'cryer_symc_short_review_r1'
OLD = 'cryer_symc_short_r1'
CHECK = TESTS/'logs'/(TAG+'.check.json')
FIGURES = [TESTS/'figures'/(TAG+'_'+suffix+'.png') for suffix in ['history', 'opening']]


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    assert not CHECK.exists() and not any(p.exists() for p in FIGURES), 'Preserve prior review'
    status = read(TESTS/'logs'/(OLD+'.status.json'))
    check_path = TESTS/'logs'/(OLD+'.check.json'); completed = read(check_path)
    run_path = TESTS/'logs'/(OLD+'.run.json')
    assert status['status'] == completed['status'] == 'short_pairs_passed_pending_physical_review'
    assert completed['passed'] and not completed['physical_accepted']
    assert bound(run_path) == completed['run']
    for entry in completed['artifacts']:
        assert bound(Path(entry['path'])) == entry
    summary_path = TESTS/'figures'/(OLD+'_summary.csv')
    pair_path = TESTS/'figures'/(OLD+'_comparisons.csv')
    a = pd.read_csv(summary_path, float_precision='round_trip')
    b = pd.read_csv(pair_path, float_precision='round_trip')
    assert len(a) == 276 and len(b) == 414
    assert not a.duplicated(['run', 'part']).any() and not b.duplicated(['comparison', 'part']).any()
    runs = {}
    for receipt in completed['runs']:
        name = receipt['name']; v = a[a.run.eq(name)].sort_values('part')
        assert receipt['passed'] and receipt['exit_code'] == 0 and receipt['owned_exited']
        assert not receipt['observed_surviving_solvers']
        assert len(v) == 69 and np.array_equal(v.part, np.arange(69))
        assert np.array_equal(v.time_s, np.arange(69)*2.**-13)
        stride = 512 if name.endswith('_h') else 256
        assert np.array_equal(v.saved_step, np.maximum(np.arange(69)*stride-1, 0))
        assert v.true_surface_count.eq(5153).all() and v.changed_fstype_count.eq(0).all()
        assert v.center_fixed_material_count.eq(18).all()
        assert v.loc[v.time_s.gt(2.**-7), 'true_surface_pressure_absmax_pa'].eq(0).all()
        assert v.dterror_s.le(1e-14).all() and v.fixed_to_pore_dt_ratio.le(1).all()
        assert receipt['equilibrium']['equilibrium_diagnostic_passed']
        for key in ['same_physics_cpu_gpu', 'independent_half', 'option_change']:
            if key not in receipt:
                continue
            r = receipt[key]; pair = b[b.comparison.eq(r['meaning'])]
            assert len(pair) == 69 and pair.part.nunique() == 69
            assert np.isclose(pair.pressure_rms_pa.max(), r['max_pressure_rms_pa'], rtol=1e-14, atol=1e-14)
            assert np.isclose(pair.material_displacement_max_mm.max(), r['max_displacement_mm'], rtol=1e-14, atol=1e-14)
            if key != 'option_change':
                assert r['passed'] and pair.guarded.eq(True).all()
                assert pair.pressure_rms_pa.le(5).all() and pair.material_displacement_max_mm.le(.005).all()
                assert pair.fstype_mismatches.eq(0).all() and pair.drained_mask_mismatches.eq(0).all()
            else:
                assert r['passed'] is None and pair.guarded.eq(False).all()
        runs[name] = v
    plt.rcParams.update({'font.family':'Arial', 'font.size':10, 'axes.grid':True,
                         'grid.alpha':.2, 'figure.dpi':150})
    styles = [('off_c', '#1f77b4', '-', 'Receiver C, coarse'),
              ('off_h', '#1f77b4', '--', 'Receiver C, half'),
              ('on_c', '#d95f02', '-', 'Symmetric C, coarse'),
              ('on_h', '#d95f02', '--', 'Symmetric C, half')]
    metrics = [('center_pressure_mean_pa', 1e-3, 'Fixed 18-ID center pressure (kPa)'),
               ('pressure_mean_pa', 1e-3, 'Volume-weighted pressure (kPa)'),
               ('shell_inward_mean_mm', 1., 'Material shell inward displacement (mm)'),
               ('total_stress_target_six_rms_pa', 1., 'Total-stress target residual, six-component RMS (Pa)'),
               ('speed_max_m_s', 1., 'Maximum particle speed (m/s)')]
    for opening, output in [(False, FIGURES[0]), (True, FIGURES[1])]:
        fig, axes = plt.subplots(2, 3, figsize=(14, 8.5))
        ax = axes.ravel()
        for suffix, color, line, label in styles:
            v = runs[OLD+'_'+suffix]
            if opening:
                v = v[v.part.ge(64)]
            x = (v.time_s-(2.**-7 if opening else 0))*1000
            for panel, (column, scale, ylabel) in zip(ax, metrics):
                panel.plot(x, v[column]*scale, line, color=color, lw=1.5,
                           marker='o' if opening else None, markersize=3, label=label)
                panel.set_ylabel(ylabel)
        if opening:
            for suffix, color, line, label in [styles[2], styles[3]]:
                pair = b[b.comparison.eq(OLD+'_'+suffix+':symmetric_vs_receiver_C') & b.part.ge(64)]
                ax[5].plot((pair.time_s-2.**-7)*1000, pair.pressure_rms_pa, line,
                           color=color, marker='o', ms=3, label=label.replace('Symmetric C', 'Option difference'))
            ax[5].set_ylabel('Same-dt option pressure-field RMS difference (Pa)')
            caption = 'Only four post-opening saves. The point at tau=0 is pre-open; no Mandel-peak accuracy claim.'
            title = 'Cryer: first 0.488 ms after drainage opening'
        else:
            for suffix, color in [('off_h', '#1f77b4'), ('on_h', '#d95f02')]:
                pair = b[b.comparison.eq(OLD+'_'+suffix+':own_half')]
                ax[5].plot(pair.time_s*1000, pair.pressure_rms_pa, color=color,
                           label=('Receiver C' if suffix.startswith('off') else 'Symmetric C')+' half difference')
            ax[5].set_ylabel('Own coarse/half pressure-field RMS difference (Pa)')
            ax[5].legend(fontsize=8)
            for panel in ax:
                panel.axvline(2.**-8*1000, color='.5', ls=':', lw=1)
                panel.axvline(2.**-7*1000, color='.25', ls='-.', lw=1)
            caption = 'Vertical lines: ramp end 3.90625 ms; drainage event 7.8125 ms. Full startup retained.'
            title = 'Cryer: preload and drainage-opening short comparison'
        for panel in ax:
            panel.set_xlabel('Time since drainage event, tau (ms)' if opening else 'Actual saved time (ms)')
        handles, labels = ax[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='upper center', ncol=4, bbox_to_anchor=(.5, .955), frameon=False)
        fig.suptitle(title, y=.994, fontsize=14)
        fig.text(.5, .012, caption, ha='center', fontsize=9)
        fig.tight_layout(rect=(0, .045, 1, .92))
        fig.savefig(output, dpi=180); plt.close(fig)
    final = {}
    for suffix in ['c', 'h']:
        off, on = runs[OLD+'_off_'+suffix], runs[OLD+'_on_'+suffix]
        endpoint = {}
        for column, _, _ in metrics:
            x, y = float(off.iloc[-1][column]), float(on.iloc[-1][column])
            endpoint[column] = dict(receiver=x, symmetric=y, difference=y-x)
        final[suffix] = endpoint
    result = dict(utc=utc(), analysis_checks_passed=True, visual_review_passed=False,
        sources=[bound(q) for q in [Path(__file__), check_path, run_path, summary_path, pair_path]],
        artifacts=[bound(p) for p in FIGURES],
        checked_csv_rows=dict(summary=len(a), comparisons=len(b)),
        all_saved_times_s=dict(start=0., end=.00830078125, drainage=2.**-7,
                              last_tau=.00048828125, post_opening_saves=4),
        endpoint_same_dt_changes=final,
        limits='Original 5-Pa field RMS / .005-mm material maximum independent half and OFF CPU/GPU checks unchanged.',
        conclusion='Short safety and temporal/backend checks pass; option differences are not accuracy gains. No peak/formal acceptance.',
        limitations=['Four post-opening points only, far short of the reference Mandel peak near tau=.04205s.',
                     'CPU/GPU agreement covers these69 saves, not the full peak trajectory.',
                     'Native particle safety/hash re-audit is separately required; CSV reconciliation alone is not independent physical validation.'])
    with CHECK.open('x', encoding='utf8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(dict(analysis_checks_passed=True, figures=[str(p) for p in FIGURES], endpoint=final), indent=2))


if __name__ == '__main__':
    main()
