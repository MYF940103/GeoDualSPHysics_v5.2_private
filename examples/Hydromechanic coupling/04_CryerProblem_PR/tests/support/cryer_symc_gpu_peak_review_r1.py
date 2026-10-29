"""Offline review of one completed symmetric-Darcy GPU peak; never runs a solver."""
import os
for name in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ[name] = '1'
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from cryer_start_r1 import TESTS, bound, native, utc
from cryer_radial_consistency_r1 import Reference, selftest

TAG = 'cryer_symc_gpu_peak_review_r1'
NEW = 'cryer_symc_gpu_peak_r1'
TAGS = ['cryer_preload_peak_r1', 'cryer_preload_peak_half_r1', NEW]
LABELS = ['Receiver C, coarse', 'Receiver C, half (retained)', 'Symmetric C, coarse']
COLORS, LINES = ['#1f77b4', '#777777', '#d95f02'], ['-', ':', '-']
TD, INTERVAL, LEGACY_CV = 2.**-7, 2.**-13, .0027444522857366896
CHECK = TESTS/'logs'/(TAG+'.check.json')
CSVS = [TESTS/'figures'/(TAG+s+'.csv') for s in ['', '_profiles']]
PNGS = [TESTS/'figures'/(TAG+'_'+s+'.png') for s in ['pressure', 'state', 'profiles']]


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    assert not any(p.exists() for p in [CHECK, *CSVS, *PNGS]), 'Fresh offline artifacts only'
    paths = [TESTS/'logs'/(NEW+s) for s in ['.status.json', '.run.json', '.check.json', '.completion.json', '.prefix.json']]
    status, run, check, completion, prefix = [read(p) for p in paths]
    assert status['status'] == check['status'] == 'symc_gpu_peak_completed_pending_physical_review'
    assert check['passed'] and check['checked_frames'] == check['option_samples'] == 577
    assert bound(paths[1]) == status['run_manifest'] == check['run_manifest']
    assert bound(paths[3]) == check['sealed_completion'] and bound(paths[4]) == check['prefix_receipt']
    assert run['owned_exited'] and run['exit_code'] == 0 and not run['observed_terminal_solvers']
    assert completion['solver_finished'] and completion['owned_exited'] and completion['exit_code'] == 0
    assert run['actual_last_saved_time_s'] == .0703125 and not check['physical_accepted']
    assert check['closed_equilibrium_diagnostics']['equilibrium_diagnostic_passed']
    assert prefix['checked_samples'] == 69 and prefix['all35_columns0ulp_passed'] and prefix['excluded_columns'] == []
    assert len(prefix['samples']) == 69 and all(s['all_35_columns0ulp'] and len(s['compared_columns']) == 35
        and 'dterror_s' in s['compared_columns'] and not s['differences'] for s in prefix['samples'])
    frames, sources = [], [bound(p) for p in [Path(__file__), *paths]]
    for tag, stride in zip(TAGS, [256, 512, 256]):
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
    option_path = TESTS/'figures'/(NEW+'_options.csv')
    assert bound(option_path) in run['artifacts']
    option = pd.read_csv(option_path, float_precision='round_trip')
    assert len(option) == 577 and np.array_equal(option.time_s, frames[0].time_s)
    assert np.array_equal(option.raw_time_s, option.time_s)
    assert not option.guarded.any() and not option.is_half_or_theory_error.any()
    assert option.fstype_mismatches.eq(0).all() and option.drained_mask_mismatches.eq(0).all()
    sources.append(bound(option_path))
    ref = Reference(); reference_selftest = selftest(ref)
    exact_peak = minimize_scalar(lambda t: -float(ref.field(np.array([.0025]), t)['p'][0]),
        bounds=(.02, .07), method='bounded', options={'xatol': 1e-14})
    assert exact_peak.success
    theory_peak = dict(tau_s=float(exact_peak.x), pressure_pa=float(-exact_peak.fun), initial_radius_m=.0025)
    tau = frames[0].time_s.to_numpy()-TD; post = tau > 0; window = LEGACY_CV*tau/.05**2 >= .005
    theory = np.full(577, np.nan); theory_origin = theory.copy()
    for i in np.flatnonzero(post):
        theory[i], theory_origin[i] = ref.field(np.array([.0025, 0.]), float(tau[i]))['p']
    peaks, derived = {}, pd.DataFrame(dict(part=np.arange(577), time_s=frames[0].time_s,
        tau_from_drainage_s=tau, finite_storage_theta=ref.cv*tau/.05**2,
        theory_fixed_radius_pressure_pa=theory, theory_exact_origin_pressure_pa=theory_origin))
    for key, a in zip(['raw_coarse', 'raw_half', 'symC_coarse'], frames):
        row = a.loc[a.loc[window, 'center_pressure_mean_pa'].idxmax()]
        error = a.center_pressure_mean_pa.to_numpy()-theory
        peaks[key] = dict(part=int(row.part), time_s=float(row.time_s), tau_s=float(row.time_s-TD), pressure_pa=float(row.center_pressure_mean_pa),
            amplitude_error_percent=100*(float(row.center_pressure_mean_pa)/theory_peak['pressure_pa']-1),
            peak_time_error_percent=100*(float(row.time_s-TD)/theory_peak['tau_s']-1),
            center_mandel_window_rms_error_pa=float(np.sqrt(np.mean(error[window]**2))),
            center_mandel_window_absmax_error_pa=float(abs(error[window]).max()),
            endpoint_error_pa=float(error[-1]), sampled_peak_is_interior=bool(row.part < 576))
        assert peaks[key]['sampled_peak_is_interior']
        for col in ['saved_step', 'center_pressure_mean_pa', 'pressure_mean_pa', 'pressure_max_pa', 'total_mean_compression_pa',
                'total_stress_target_six_rms_pa', 'shell_inward_mean_mm', 'rho_mean_kg_m3', 'speed_max_m_s',
                'actual_radial_force_N', 'load_virial_over_3qVnative']:
            derived[key+'_'+col] = a[col]
        derived[key+'_center_error_pa'] = error
    for col in option.columns:
        if col not in ['part', 'time_s', 'raw_time_s', 'comparison', 'guarded', 'is_half_or_theory_error']:
            derived['option_'+col] = option[col]
    plt.rcParams.update({'font.family': 'Arial', 'font.size': 10, 'axes.grid': True, 'grid.alpha': .2})
    fig, ax = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
    for a, label, color, line in zip(frames, LABELS, COLORS, LINES):
        ax[0, 0].plot(a.time_s, a.center_pressure_mean_pa/1000, line, color=color, label=label)
        ax[0, 1].plot(tau[post], a.center_pressure_mean_pa[post]/10000, line, color=color, label=label)
        ax[1, 0].plot(tau[window], (a.center_pressure_mean_pa.to_numpy()-theory)[window], line, color=color, label=label)
    ax[0, 0].axvline(TD, color='.4', ls=':', label='Drain event (saved tD pre-open)')
    ax[0, 0].set(xlabel='Actual saved time (s)', ylabel='Fixed 18-ID pressure (kPa)', title='Full loading and opening history')
    ax[0, 1].plot(tau[post], theory[post]/10000, 'k--', label='Finite-Kw reference, r0/a=.05')
    ax[0, 1].axvline(theory_peak['tau_s'], color='.3', ls=':')
    ax[0, 1].set(xlabel='tau = t - tD (s)', ylabel='p / q', title='Post-opening history, no fitted time shift')
    ax[1, 0].axhline(0, color='.3', ls=':')
    ax[1, 0].set(xlabel='tau = t - tD (s)', ylabel='Native minus finite-radius reference (Pa)', title='Declared Mandel window: legacy Tv >= .005')
    ax[1, 1].plot(option.time_s, option.pressure_rms_pa, color='#d95f02', label='Same-dt option field RMS difference')
    ax[1, 1].set(xlabel='Actual saved time (s)', ylabel='Pressure difference (Pa)', title='Option change, not a half-step/theory error')
    for panel in ax.flat:
        panel.legend(fontsize=8)
    fig.suptitle('Cryer: symmetric Darcy coarse peak versus retained receiver-C controls\nNative peaks stay on the saved grid; only the analytical reference is optimized.', fontsize=12)
    fig.savefig(PNGS[0], dpi=180); plt.close(fig)
    initial = native(TESTS/'outputs'/NEW, 0)
    x0 = initial[['x', 'y', 'z']].to_numpy(); r0 = np.linalg.norm(x0, axis=1)
    volume = initial.mass.to_numpy()/initial.rho.to_numpy(); weights = volume/volume.sum()
    shell = r0 >= .05-2*float(initial.h.iloc[0]); shell_weights = volume[shell]/volume[shell].sum()
    final_ref = ref.field(r0, float(tau[-1]))
    endpoint_reference = dict(total_mean_compression_pa=float(weights@(-(final_ref['tr']+2*final_ref['tt'])/3)),
        shell_inward_mean_mm=float(shell_weights@(-1000*r0[shell]*final_ref['u_over_r'][shell])),
        pressure_mean_pa=float(weights@final_ref['p']))
    endpoint_errors = {}
    for key, a in zip(['raw_coarse', 'raw_half', 'symC_coarse'], frames):
        endpoint_errors[key] = {col: float(a.iloc[-1][col])-value for col, value in endpoint_reference.items()}
    for col, value in endpoint_reference.items():
        derived['reference_native_endpoint_'+col] = np.nan
        derived.loc[576, 'reference_native_endpoint_'+col] = value
    derived.to_csv(CSVS[0], index=False, float_format='%.17g')
    fig, ax = plt.subplots(2, 3, figsize=(14, 8), layout='constrained')
    metrics = [('total_mean_compression_pa', .001, 'Native mean total compression (kPa)'),
        ('shell_inward_mean_mm', 1., 'Fixed material shell inward motion (mm)'), ('pressure_mean_pa', .001, 'Native volume-weighted pressure (kPa)'),
        ('rho_mean_kg_m3', 1., 'Native mean density (kg/m3)'), ('speed_max_m_s', 1., 'Maximum speed (m/s)'),
        ('load_virial_over_3qVnative', 1., 'Load virial / (3 q Vnative)')]
    for a, label, color, line in zip(frames, LABELS, COLORS, LINES):
        for panel, (column, scale, ylabel) in zip(ax.flat, metrics):
            panel.plot(a.time_s, a[column]*scale, line, color=color, label=label)
            panel.set(xlabel='Actual saved time (s)', ylabel=ylabel)
    for panel, (column, scale, _) in zip(ax.flat, metrics):
        if column in endpoint_reference:
            panel.plot([.0703125], [endpoint_reference[column]*scale], 'kx', ms=7, label='Reference at native points (endpoint only)')
    for panel in ax.flat:
        panel.axvline(TD, color='.4', ls=':', alpha=.5); panel.legend(fontsize=8)
    fig.suptitle('Cryer: native state and load histories\nClosed uniform targets are not post-opening stress gates; native shell/volume averages are not continuum surface integrals.', fontsize=12)
    fig.savefig(PNGS[1], dpi=180); plt.close(fig)
    center = r0 <= .0025+1e-12
    assert initial.id[center].tolist() == run['center_fixed_material_ids']
    assert np.allclose(r0[center], .0025, rtol=0, atol=1e-16)
    select = abs(x0[:, 1]) <= .5*float(initial.dp.iloc[0]); assert select.any()
    profile_rows = []; fig, ax = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
    requested = [.005, .02, theory_peak['tau_s'], .0625]; parts = []
    for panel, target in zip(ax.flat, requested):
        part = int(np.argmin(abs(tau-target))); actual = float(tau[part]); parts.append(part)
        theory_points = ref.field(r0[select], actual)['p']
        table = pd.DataFrame(dict(part=part, time_s=float(frames[0].time_s.iloc[part]), tau_from_drainage_s=actual,
            requested_tau_s=target, id=initial.id.to_numpy()[select], initial_radius_m=r0[select], initial_y_m=x0[select, 1],
            theory_pressure_pa=theory_points))
        for tag, key, label, color in [(TAGS[0], 'raw_coarse', LABELS[0], COLORS[0]), (NEW, 'symC_coarse', LABELS[2], COLORS[2])]:
            a = native(TESTS/'outputs'/tag, part)
            assert np.array_equal(a.id, initial.id) and a.time_s.eq(part*INTERVAL).all()
            table[key+'_pressure_pa'] = a.pressure.to_numpy()[select]
            panel.scatter(r0[select]/.05, table[key+'_pressure_pa']/10000, s=4, alpha=.25, color=color, label=label, rasterized=True)
            sources.append(bound(TESTS/'outputs'/tag/'data'/f'Part_{part:04d}.bi4'))
        curve = np.linspace(0, .05, 257)
        panel.plot(curve/.05, ref.field(curve, actual)['p']/10000, 'k--', lw=1.2, label='Finite-Kw quasi-static reference')
        panel.set(xlabel='Fixed initial material radius r0 / a', ylabel='p / q', title=f'Actual tau={actual:.8f} s; finite theta={ref.cv*actual/.05**2:.5f}')
        panel.legend(fontsize=8); profile_rows.append(table)
    pd.concat(profile_rows, ignore_index=True).to_csv(CSVS[1], index=False, float_format='%.17g')
    fig.suptitle('Cryer: actual-matched radial pressure profiles\nFixed initial |y0| <= dp/2 material slice; every selected point shown without smoothing.', fontsize=12)
    fig.savefig(PNGS[2], dpi=180); plt.close(fig)
    sources += [bound(TESTS/'support/cryer_radial_consistency_r1.py'), bound(TESTS/'outputs'/NEW/'data/Part_0000.bi4')]
    improvement = {key: 100*(1-abs(peaks['symC_coarse'][key])/abs(peaks['raw_coarse'][key]))
        for key in ['amplitude_error_percent', 'peak_time_error_percent', 'center_mandel_window_rms_error_pa']}
    result = dict(utc=utc(), analysis_checks_passed=True, visual_review_passed=False, solver_executed=False,
        physical_accepted=False, full_cycle_accepted=False, peak_half_tested=False, formal_admitted=False,
        original_single_run_safety_adopted=True, exact_own69_all35_prefix_adopted=True,
        sources=sources, artifacts=[bound(p) for p in [*CSVS, *PNGS]], reference_selftest=reference_selftest,
        theory_peak=theory_peak, native_peaks=peaks, same_dt_error_magnitude_reduction_percent=improvement,
        endpoint_reference_at_initial_native_sampling=endpoint_reference, endpoint_native_errors=endpoint_errors,
        endpoint_reference_shell_count=int(shell.sum()),
        saved_time_interval_s=INTERVAL, mandel_window='legacy Cv*(t-tD)/a^2>=.005; all startup rows retained',
        actual_end_time_s=.0703125, profile_parts=parts, profile_points_per_time=int(select.sum()),
        candidate_loop_seconds=run['observed_loop_seconds'],
        conclusions=['Isolated symmetric-Darcy coarse peak is compared only with same-dt raw coarse for attributed changes.',
            'Retained raw half is temporal-sensitivity context, not candidate half or exact truth.',
            'No fitted time shift, radius, pressure scale, native interpolation or smoothing.'],
        limitations=['Independent full native/hash audit and actual PNG viewing are separately required.',
            'No new candidate peak-half or full-cycle convergence is established.',
            'Finite-Kw reference is quasi-static/small-strain at the fixed initial material radius, not exact dynamic SPH truth.',
            'Radial profiles are a documented material slice; shell/volume averages are native diagnostics, not exact continuum integrals.'])
    with CHECK.open('x', encoding='utf8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(dict(analysis_checks_passed=True, theory_peak=theory_peak, native_peaks=peaks, improvement=improvement, artifacts=result['artifacts']), indent=2))


if __name__ == '__main__':
    main()
