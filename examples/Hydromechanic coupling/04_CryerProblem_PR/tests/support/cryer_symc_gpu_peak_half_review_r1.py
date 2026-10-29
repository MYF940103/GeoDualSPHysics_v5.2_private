"""Offline peak-half review; reuses the frozen reference and never starts a solver."""
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
from cryer_start_r1 import TESTS, bound, native, utc
from cryer_symc_gpu_peak_review_r1 import read, Reference, TD, INTERVAL, LEGACY_CV

TAG = 'cryer_symc_gpu_peak_half_review_r1'
NEW = 'cryer_symc_gpu_peak_half_r1'
OLD_REVIEW = 'cryer_symc_gpu_peak_review_r1'
TAGS = ['cryer_preload_peak_r1', 'cryer_preload_peak_half_r1', 'cryer_symc_gpu_peak_r1', NEW]
KEYS = ['raw_coarse', 'raw_half', 'symC_coarse', 'symC_half']
LABELS = ['Receiver C, coarse', 'Receiver C, half', 'Symmetric C, coarse', 'Symmetric C, half']
COLORS = ['#1f77b4', '#777777', '#d95f02', '#16853b']
LINES = ['-', ':', '-', '--']
CHECK = TESTS/'logs'/(TAG+'.check.json')
CSVS = [TESTS/'figures'/(TAG+s+'.csv') for s in ['', '_profiles']]
PNGS = [TESTS/'figures'/(TAG+'_'+s+'.png') for s in ['pressure', 'state', 'profiles']]


def main():
    assert not any(p.exists() for p in [CHECK, *CSVS, *PNGS]), 'Fresh offline artifacts only'
    paths = [TESTS/'logs'/(NEW+s) for s in ['.status.json', '.run.json', '.check.json', '.completion.json', '.prefix.json']]
    status, run, check, completion, prefix = [read(p) for p in paths]
    assert status['status'] == check['status'] == 'symc_gpu_peak_half_passed_pending_physical_review'
    assert check['passed'] and check['half_screen_passed']
    assert check['checked_frames'] == check['paired_samples'] == 577 and check['prefix_samples'] == 69
    assert bound(paths[1]) == status['run_manifest'] == check['run_manifest']
    assert bound(paths[3]) == check['sealed_completion'] and bound(paths[4]) == check['prefix_receipt']
    assert run['owned_exited'] and run['exit_code'] == 0 and not run['observed_terminal_solvers']
    assert completion['solver_finished'] and completion['owned_exited'] and completion['exit_code'] == 0
    assert run['actual_last_saved_time_s'] == .0703125 and run['half_failures'] == []
    assert check['closed_equilibrium_diagnostics']['equilibrium_diagnostic_passed']
    assert prefix['checked_samples'] == 69 and prefix['all35_columns0ulp_passed'] and prefix['excluded_columns'] == []
    assert len(prefix['samples']) == 69 and all(s['all_35_columns0ulp'] and len(s['compared_columns']) == 35
        and 'dterror_s' in s['compared_columns'] and not s['differences'] for s in prefix['samples'])
    old_paths = [TESTS/'logs'/(OLD_REVIEW+s) for s in ['.check.json', '.visual.json']]
    old, old_visual = [read(p) for p in old_paths]
    assert old['analysis_checks_passed'] and old_visual['visual_review_passed']
    assert old_visual['review_check'] == bound(old_paths[0])
    old_csv = TESTS/'figures'/(OLD_REVIEW+'.csv')
    old_profiles = TESTS/'figures'/(OLD_REVIEW+'_profiles.csv')
    assert bound(old_csv) in old['artifacts'] and bound(old_profiles) in old['artifacts']
    derived = pd.read_csv(old_csv, float_precision='round_trip')
    profiles = pd.read_csv(old_profiles, float_precision='round_trip')
    sources = [bound(p) for p in [Path(__file__), *paths, *old_paths, old_csv, old_profiles,
        TESTS/'support/cryer_symc_gpu_peak_review_r1.py', TESTS/'support/cryer_radial_consistency_r1.py']]
    frames = []
    for tag, key, stride in zip(TAGS, KEYS, [256, 512, 256, 512]):
        rp, cp = [TESTS/'logs'/(tag+s) for s in ['.run.json', '.check.json']]
        rr, cc = read(rp), read(cp)
        assert cc['passed'] and rr['owned_exited'] and rr['exit_code'] == 0
        path = TESTS/'figures'/(tag+'_summary.csv')
        assert bound(path) in rr['artifacts']
        a = pd.read_csv(path, float_precision='round_trip')
        assert len(a) == 577 and np.array_equal(a.part, np.arange(577))
        assert np.array_equal(a.time_s, np.arange(577)*INTERVAL)
        assert np.array_equal(a.saved_step, np.maximum(np.arange(577)*stride-1, 0))
        assert a.true_surface_count.eq(5153).all() and a.changed_fstype_count.eq(0).all()
        assert a.center_fixed_material_count.eq(18).all()
        assert np.array_equal(a.drainage_active, a.time_s > TD)
        assert a.loc[a.time_s.gt(TD), 'true_surface_pressure_absmax_pa'].eq(0).all()
        assert a.dterror_s.le(1e-14).all() and a.fixed_to_pore_dt_ratio.le(1).all()
        frames.append(a); sources += [bound(p) for p in [rp, cp, path]]
        if key == 'symC_half':
            for col in a.columns:
                derived[key+'_'+col] = a[col]
    pair_path = TESTS/'figures'/(NEW+'_half.csv')
    assert bound(pair_path) in run['artifacts']
    pairs = pd.read_csv(pair_path, float_precision='round_trip')
    assert len(pairs) == 577 and np.array_equal(pairs.part, np.arange(577))
    assert np.array_equal(pairs.time_s, frames[-1].time_s) and np.array_equal(pairs.coarse_time_s, pairs.time_s)
    assert pairs.screen_passed.all() and pairs.pressure_rms_pa.le(5).all() and pairs.material_displacement_max_mm.le(.005).all()
    assert pairs.fstype_mismatches.eq(0).all() and pairs.drained_mask_mismatches.eq(0).all()
    assert not pairs.is_theory_error.any() and pairs.comparison.eq('independent_candidate_half').all()
    for col in pairs.columns:
        if col not in ['part', 'time_s', 'coarse_time_s', 'comparison']:
            derived['candidate_half_'+col] = pairs[col]
    sources.append(bound(pair_path))
    tau = derived.tau_from_drainage_s.to_numpy()
    assert np.array_equal(tau, np.arange(577)*INTERVAL-TD)
    post = tau > 0; window = LEGACY_CV*tau/.05**2 >= .005
    theory = derived.theory_fixed_radius_pressure_pa.to_numpy()
    ref = Reference(); theory_peak = old['theory_peak']
    # Reuse the unchanged full reference, with direct independent time/radius spot checks.
    for part in [65, 105, 408, 422, 576]:
        expected = float(ref.field(np.array([.0025]), float(tau[part]))['p'][0])
        assert abs(expected-theory[part]) < 1e-8
    peaks = {}
    for key, a in zip(KEYS, frames):
        row = a.loc[a.loc[window, 'center_pressure_mean_pa'].idxmax()]
        error = a.center_pressure_mean_pa.to_numpy()-theory
        peaks[key] = dict(part=int(row.part), time_s=float(row.time_s), tau_s=float(row.time_s-TD),
            pressure_pa=float(row.center_pressure_mean_pa),
            amplitude_error_percent=100*(float(row.center_pressure_mean_pa)/theory_peak['pressure_pa']-1),
            peak_time_error_percent=100*(float(row.time_s-TD)/theory_peak['tau_s']-1),
            center_mandel_window_rms_error_pa=float(np.sqrt(np.mean(error[window]**2))),
            center_mandel_window_absmax_error_pa=float(abs(error[window]).max()),
            endpoint_error_pa=float(error[-1]), sampled_peak_is_interior=bool(row.part < 576))
        assert peaks[key]['sampled_peak_is_interior']
        derived[key+'_center_error_pa'] = error
    initial = native(TESTS/'outputs'/NEW, 0)
    coarse_initial = native(TESTS/'outputs'/TAGS[2], 0)
    assert np.array_equal(initial.id, np.arange(8, 37181))
    assert np.array_equal(initial[['id', 'x', 'y', 'z', 'mass', 'rho', 'dp', 'h']],
        coarse_initial[['id', 'x', 'y', 'z', 'mass', 'rho', 'dp', 'h']])
    x0 = initial[['x', 'y', 'z']].to_numpy(); r0 = np.linalg.norm(x0, axis=1)
    center = r0 <= .0025+1e-12
    assert initial.id[center].tolist() == run['center_fixed_material_ids']
    assert np.allclose(r0[center], .0025, rtol=0, atol=1e-16)
    endpoint_reference = old['endpoint_reference_at_initial_native_sampling']
    endpoint_errors = {key: {col: float(a.iloc[-1][col])-value for col, value in endpoint_reference.items()}
        for key, a in zip(KEYS, frames)}
    for part in old['profile_parts']:
        a = native(TESTS/'outputs'/NEW, part)
        assert np.array_equal(a.id, initial.id) and a.time_s.eq(part*INTERVAL).all() and a.saved_step.eq(part*512-1).all()
        selected = profiles.part.eq(part)
        ids = profiles.loc[selected, 'id'].to_numpy()
        positions = initial.set_index('id').loc[ids, ['x', 'y', 'z']].to_numpy()
        assert np.allclose(np.linalg.norm(positions, axis=1), profiles.loc[selected, 'initial_radius_m'], rtol=0, atol=1e-16)
        profiles.loc[selected, 'symC_half_pressure_pa'] = a.set_index('id').loc[ids, 'pressure'].to_numpy()
        sources.append(bound(TESTS/'outputs'/NEW/'data'/f'Part_{part:04d}.bi4'))
    assert len(profiles) == 6836 and profiles.symC_half_pressure_pa.notna().all()
    sources += [bound(TESTS/'outputs'/tag/'data/Part_0000.bi4') for tag in [TAGS[2], NEW]]
    half_metrics = {}
    for col in ['pressure_rms_pa', 'material_displacement_max_mm', 'total_stress_six_component_rms_pa', 'density_rms_kg_m3']:
        row = pairs.loc[pairs[col].idxmax()]
        half_metrics[col] = dict(maximum=float(row[col]), part=int(row.part), time_s=float(row.time_s))
    improvement = {key: 100*(1-abs(peaks['symC_half'][key])/abs(peaks['raw_half'][key]))
        for key in ['amplitude_error_percent', 'peak_time_error_percent', 'center_mandel_window_rms_error_pa']}
    # All calculations and new-native profile reads finish before authoring artifacts.
    derived.to_csv(CSVS[0], index=False, float_format='%.17g', mode='x')
    profiles.to_csv(CSVS[1], index=False, float_format='%.17g', mode='x')
    plt.rcParams.update({'font.family': 'Arial', 'font.size': 10, 'axes.grid': True, 'grid.alpha': .2})
    fig, ax = plt.subplots(3, 2, figsize=(12, 11), layout='constrained')
    for a, key, label, color, line in zip(frames, KEYS, LABELS, COLORS, LINES):
        ax[0, 0].plot(a.time_s, a.center_pressure_mean_pa/1000, line, color=color, label=label)
        ax[0, 1].plot(tau[post], a.center_pressure_mean_pa[post]/10000, line, color=color, label=label)
        ax[1, 0].plot(tau[window], derived[key+'_center_error_pa'][window], line, color=color, label=label)
    ax[0, 0].axvline(TD, color='.4', ls=':', label='Drain event (saved tD pre-open)')
    ax[0, 0].set(xlabel='Actual saved time (s)', ylabel='Fixed 18-ID pressure (kPa)', title='Full loading and opening history')
    ax[0, 1].plot(tau[post], theory[post]/10000, 'k--', label='Finite-Kw reference, r0/a=.05')
    ax[0, 1].axvline(theory_peak['tau_s'], color='.4', ls=':')
    ax[0, 1].set(xlabel='tau = t - tD (s)', ylabel='p / q', title='Peak improvement retained under half step')
    ax[1, 0].axhline(0, color='.4', ls=':')
    ax[1, 0].set(xlabel='tau = t - tD (s)', ylabel='Native minus reference (Pa)', title='Declared Mandel window: legacy Tv >= .005')
    for panel, col, label, limit in [(ax[1, 1], 'pressure_rms_pa', 'Pressure-field RMS difference (Pa)', 5.),
        (ax[2, 0], 'material_displacement_max_mm', 'Material displacement max difference (mm)', .005),
        (ax[2, 1], 'total_stress_six_component_rms_pa', 'Total-stress six-component RMS difference (Pa)', None)]:
        panel.plot(pairs.time_s, pairs[col], color=COLORS[-1], label='Independent symmetric-C coarse / half')
        if limit is not None:
            panel.axhline(limit, color='#a02020', ls='--', label='Original half-step limit')
        panel.set(xlabel='Actual saved time (s)', ylabel=label,
            title='All 577 actual-matched samples' if limit is not None else 'Recorded stress difference; no extra gate')
    for panel in ax.flat:
        panel.legend(fontsize=8)
    fig.suptitle('Cryer: symmetric Darcy independent peak-half review\nNo fitted time shift, radius, pressure scale or smoothing; full-cycle acceptance remains pending.', fontsize=12)
    fig.savefig(PNGS[0], dpi=180); plt.close(fig)
    fig, ax = plt.subplots(2, 3, figsize=(14, 8), layout='constrained')
    metrics = [('total_mean_compression_pa', .001, 'Native mean total compression (kPa)'),
        ('shell_inward_mean_mm', 1., 'Fixed material shell inward motion (mm)'),
        ('pressure_mean_pa', .001, 'Native volume-weighted pressure (kPa)'),
        ('rho_mean_kg_m3', 1., 'Native mean density (kg/m3)'),
        ('speed_max_m_s', 1., 'Maximum speed (m/s)'),
        ('actual_radial_force_N', 1., 'Actual radial load resultant (N)')]
    for a, label, color, line in zip(frames, LABELS, COLORS, LINES):
        for panel, (col, scale, ylabel) in zip(ax.flat, metrics):
            panel.plot(a.time_s, a[col]*scale, line, color=color, label=label)
            panel.set(xlabel='Actual saved time (s)', ylabel=ylabel)
    for panel, (col, scale, _) in zip(ax.flat, metrics):
        if col in endpoint_reference:
            panel.plot([.0703125], [endpoint_reference[col]*scale], 'kx', ms=7, label='Reference at native points (endpoint only)')
        panel.axvline(TD, color='.4', ls=':', alpha=.5); panel.legend(fontsize=8)
    fig.suptitle('Cryer: pressure, material motion, stress and actual load\nClosed uniform targets are not post-opening guards; native-point quadrature matches endpoint references.', fontsize=12)
    fig.savefig(PNGS[1], dpi=180); plt.close(fig)
    fig, ax = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
    for panel, part in zip(ax.flat, old['profile_parts']):
        table = profiles.loc[profiles.part.eq(part)]; actual = float(table.tau_from_drainage_s.iloc[0])
        for key, label, color in [('raw_coarse', LABELS[0], COLORS[0]), ('symC_coarse', LABELS[2], COLORS[2]), ('symC_half', LABELS[3], COLORS[3])]:
            panel.scatter(table.initial_radius_m/.05, table[key+'_pressure_pa']/10000,
                s=4, alpha=.25, color=color, label=label, rasterized=True)
        curve = np.linspace(0, .05, 257)
        panel.plot(curve/.05, ref.field(curve, actual)['p']/10000, 'k--', lw=1.2, label='Finite-Kw quasi-static reference')
        panel.set(xlabel='Fixed initial material radius r0 / a', ylabel='p / q', title=f'Actual tau={actual:.8f} s; finite theta={ref.cv*actual/.05**2:.5f}')
        panel.legend(fontsize=8)
    fig.suptitle('Cryer: radial pressure under independent half step\nSame fixed initial |y0| <= dp/2 material slice; every selected native point shown.', fontsize=12)
    fig.savefig(PNGS[2], dpi=180); plt.close(fig)
    result = dict(utc=utc(), analysis_checks_passed=True, visual_review_passed=False,
        solver_executed=False, original_all577_safety_adopted=True, independent_all577_half_gate_adopted=True,
        exact_own69_all35_prefix_adopted=True, peak_half_checked=True,
        physical_accepted=False, full_cycle_accepted=False, formal_admitted=False,
        sources=sources, artifacts=[bound(p) for p in [*CSVS, *PNGS]],
        theory_peak=theory_peak, native_peaks=peaks, half_metrics=half_metrics,
        same_dt_half_error_magnitude_reduction_percent=improvement,
        endpoint_reference_at_initial_native_sampling=endpoint_reference,
        endpoint_native_errors=endpoint_errors, actual_end_time_s=.0703125,
        mandel_window_samples=int(window.sum()), reference_reused_from=bound(old_paths[0]),
        profile_parts=old['profile_parts'], profile_points_per_time=1709,
        observed_loop_seconds=run['observed_loop_seconds'],
        conclusions=['Peak amplitude/timing improvement is compared at the same dt; halving preserves it.',
            'Independent577-sample half agreement is temporal sensitivity evidence, not exact theory or full-cycle acceptance.',
            'Native shell/mean references use identical initial material sampling and weights; continuum integrals differ.'],
        limitations=['Original full native safety/pair results are adopted from the sealed worker; separate audit states independent reread/hash coverage.',
            'Quasi-static small-strain reference is not exact dynamic SPH truth; residual spatial and state-integration errors remain.',
            'No new source/formal input change, solver, full decay or server run is admitted by this offline script.'])
    with CHECK.open('x', encoding='utf8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(dict(analysis_checks_passed=True, native_peaks=peaks, half_metrics=half_metrics,
        endpoint_native_errors=endpoint_errors, artifacts=result['artifacts']), indent=2))


if __name__ == '__main__':
    main()
