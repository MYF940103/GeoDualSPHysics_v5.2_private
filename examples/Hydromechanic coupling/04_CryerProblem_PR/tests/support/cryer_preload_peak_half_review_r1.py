"""Offline physical review of sealed Cryer coarse/half peak windows; no solver."""
from pathlib import Path
import hashlib
import json
import subprocess
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from cryer_radial_consistency_r1 import Reference, selftest

TEST = Path(__file__).resolve().parents[1]
TAG = 'cryer_preload_peak_half_review_r1'
COARSE = 'cryer_preload_peak_r1'
HALF = 'cryer_preload_peak_half_r1'
TD = 2. ** -7


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def bound(path):
    p = Path(path)
    with p.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(p), bytes=p.stat().st_size, sha256=digest)


def bindings(obj):
    if isinstance(obj, dict):
        if {'path', 'sha256', 'bytes'} <= obj.keys():
            yield obj
        for value in obj.values():
            yield from bindings(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from bindings(value)


def peak(frame):
    window = frame[(frame.time_s - TD) * .0027444522857366896 / .05 ** 2 >= .005]
    row = window.loc[window.center_pressure_mean_pa.idxmax()]
    return dict(part=int(row.part), time_s=float(row.time_s), tau_s=float(row.time_s - TD),
                pressure_pa=float(row.center_pressure_mean_pa))


def main():
    receipt = TEST / 'logs' / (TAG + '.check.json')
    targets = [TEST / 'figures' / (TAG + suffix) for suffix in ['.csv', '_pressure.png', '_state.png']]
    assert not receipt.exists() and not any(p.exists() for p in targets), 'Fresh analysis only'
    paths = [TEST / 'logs' / (HALF + suffix) for suffix in
             ['.status.json', '.run.json', '.check.json', '.completion.json', '.prefix.json', '.inputs.json']]
    status, run, check, completion, prefix, inputs = [read(p) for p in paths]
    assert status['status'] == check['status'] == 'preload_peak_half_passed_pending_physical_review'
    assert run['owned_exited'] and run['exit_code'] == 0 and run['actual_last_saved_time_s'] == .0703125
    assert completion['owned_exited'] and completion['solver_finished'] and completion['exit_code'] == 0
    assert not completion['owned_gpu_processes_after_wrapper']
    assert check['passed'] and check['half_screen_passed'] and check['checked_frames'] == check['paired_samples'] == 577
    assert prefix['checked_samples'] == 69 and prefix['all35_columns0ulp_passed'] and not prefix['excluded_columns']
    assert len(prefix['samples']) == 69
    assert all(r['all_35_columns0ulp'] and len(r['compared_columns']) == 35 and not r['differences'] for r in prefix['samples'])
    assert all('dterror_s' in r['compared_columns'] for r in prefix['samples'])
    for key in ['half_equilibrium_diagnostics', 'coarse_equilibrium_diagnostics']:
        assert check[key]['equilibrium_diagnostic_passed'] and len(check[key]['samples']) == 4
        assert all(s['passed'] for s in check[key]['samples'])
    coarse_run = read(TEST / 'logs' / (COARSE + '.run.json'))
    records = list(bindings(inputs)) + list(bindings(completion)) + list(bindings(check)) + list(bindings(run))
    unique = {}
    for e in records:
        key = str(Path(e['path']).resolve()).lower()
        assert key not in unique or (unique[key]['sha256'], unique[key]['bytes']) == (e['sha256'], e['bytes']), key
        unique[key] = e
    for i, e in enumerate(unique.values(), 1):
        a = bound(e['path'])
        assert (a['sha256'], a['bytes']) == (e['sha256'], e['bytes']), e['path']
        if i % 250 == 0:
            print('Rehashed %d/%d frozen inputs/output files' % (i, len(unique)), flush=True)
    frames = [pd.read_csv(TEST / 'figures' / (tag + '_summary.csv'), float_precision='round_trip') for tag in [COARSE, HALF]]
    pair_path = TEST / 'figures' / (HALF + '_half.csv')
    pair = pd.read_csv(pair_path, float_precision='round_trip')
    for frame, stride in zip(frames, [256, 512]):
        assert len(frame) == 577 and np.array_equal(frame.part, np.arange(577))
        assert np.array_equal(frame.time_s, np.arange(577) / 8192)
        assert np.array_equal(frame.saved_step, np.r_[0, np.arange(1, 577) * stride - 1])
        assert frame.true_surface_count.eq(5153).all() and frame.changed_fstype_count.eq(0).all()
        assert frame.center_fixed_material_count.eq(18).all()
        assert np.array_equal(frame.drainage_active, frame.time_s > TD)
        assert frame.loc[frame.time_s > TD, 'true_surface_pressure_absmax_pa'].eq(0).all()
    assert len(pair) == 577 and pair.screen_passed.all() and np.array_equal(pair.time_s, frames[0].time_s)
    assert np.array_equal(pair.coarse_time_s, pair.time_s)
    assert pair.pressure_rms_pa.le(5).all() and pair.material_displacement_max_mm.le(.005).all()
    assert pair.fstype_mismatches.eq(0).all() and pair.drained_mask_mismatches.eq(0).all()
    ref = Reference()
    reference_math = selftest(ref)
    theoretical = minimize_scalar(lambda t: -float(ref.field(np.array([.0025]), t)['p'][0]),
                                  bounds=(.02, .07), method='bounded', options={'xatol': 1e-14})
    assert theoretical.success
    reference_peak = dict(tau_s=float(theoretical.x), pressure_pa=float(-theoretical.fun),
                          initial_radius_m=.0025, sphere_radius_m=.05)
    peaks = [peak(frame) for frame in frames]
    for item in peaks:
        item['amplitude_error_percent'] = 100 * (item['pressure_pa'] / reference_peak['pressure_pa'] - 1)
        item['peak_time_error_percent'] = 100 * (item['tau_s'] / reference_peak['tau_s'] - 1)
    tau = frames[0].time_s.to_numpy() - TD
    theoretical_p = np.full(577, np.nan)
    exact_center = np.full(577, np.nan)
    for i in np.flatnonzero(tau > 0):
        field = ref.field(np.array([.0025, 0.]), float(tau[i]))
        theoretical_p[i], exact_center[i] = field['p']
    derived = pd.DataFrame(dict(part=np.arange(577), time_s=frames[0].time_s, tau_from_drainage_s=tau,
                               theta_finite_storage=ref.cv * tau / .05 ** 2,
                               coarse_saved_step=frames[0].saved_step, half_saved_step=frames[1].saved_step,
                               theory_finite_radius_pressure_pa=theoretical_p, theory_exact_center_pressure_pa=exact_center))
    for tag, frame in zip(['coarse', 'half'], frames):
        for col in ['center_pressure_mean_pa', 'pressure_max_pa', 'pressure_mean_pa', 'total_mean_compression_pa',
                    'shell_inward_mean_mm', 'rho_mean_kg_m3', 'speed_max_m_s', 'actual_radial_force_N',
                    'load_virial_over_3qVnative', 'pressure_target_rms_pa', 'total_stress_target_six_rms_pa']:
            derived[tag + '_' + col] = frame[col]
    for col in pair.columns:
        if col not in ['part', 'time_s', 'coarse_time_s']:
            derived['pair_' + col] = pair[col]
    derived['half_minus_coarse_center_pressure_pa'] = frames[1].center_pressure_mean_pa - frames[0].center_pressure_mean_pa
    derived.to_csv(targets[0], index=False, float_format='%.17g')
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10})
    colors = ['#245d88', '#bd6c24']
    labels = ['Coarse dt=2^-21 s', 'Half dt=2^-22 s']
    fig, ax = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
    for frame, color, label in zip(frames, colors, labels):
        ax[0, 0].plot(frame.time_s, frame.center_pressure_mean_pa / 1000, color=color, label=label)
        ax[0, 1].plot(tau[tau >= 0], frame.center_pressure_mean_pa[tau >= 0] / 10000, color=color, label=label)
    ax[0, 0].axvline(TD, color='grey', ls=':', label='Drain opening tD (Part64 pre-open)')
    ax[0, 0].set(xlabel='Actual physical time (s)', ylabel='18-ID material pressure (kPa)', title='Complete saved loading / opening history')
    pos = tau > 0
    ax[0, 1].plot(tau[pos], theoretical_p[pos] / 10000, 'k--', label='Finite storage, r0/a=.05 reference')
    ax[0, 1].axvline(reference_peak['tau_s'], color='black', ls=':', alpha=.6)
    ax[0, 1].axvline(peaks[1]['tau_s'], color=colors[1], ls=':', alpha=.6)
    ax[0, 1].set(xlabel='tau = t - tD (s)', ylabel='p / q', title='Mandel peak: quasi-static reference', ylim=(.95, 1.28))
    ax[1, 0].plot(pair.time_s, pair.pressure_rms_pa, color=colors[0], label='Native pressure-field RMS difference')
    ax[1, 0].axhline(5, color='grey', ls='--', label='Original 5 Pa bound')
    ax[1, 0].plot(pair.time_s, abs(derived.half_minus_coarse_center_pressure_pa), color=colors[1], lw=.8, label='18-ID center absolute difference')
    ax[1, 0].set(xlabel='Actual physical time (s)', ylabel='Pressure difference (Pa)', title='All 577 actual-matched samples retained')
    ax[1, 1].plot(pair.time_s, pair.material_displacement_max_mm, color=colors[0], label='Native max material displacement difference')
    ax[1, 1].axhline(.005, color='grey', ls='--', label='Original .005 mm bound')
    ax[1, 1].set(xlabel='Actual physical time (s)', ylabel='Displacement difference (mm)', title='Peak-window half comparison, not full-cycle convergence')
    for a in ax.flat:
        a.grid(alpha=.2); a.legend(fontsize=8)
    fig.suptitle('Cryer: sealed coarse / half peak-window physical review\nStartup is retained; no fitted time shift, pressure scaling or smoothing.', fontsize=12)
    fig.savefig(targets[1], dpi=180); plt.close(fig)
    fig, ax = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
    for frame, color, label in zip(frames, colors, labels):
        ax[0, 0].plot(frame.time_s, frame.total_mean_compression_pa / 1000, color=color, label=label)
        ax[0, 1].plot(frame.time_s, frame.shell_inward_mean_mm, color=color, label=label)
        ax[1, 0].plot(frame.time_s, frame.rho_mean_kg_m3, color=color, label=label)
        ax[1, 1].plot(frame.time_s, frame.load_virial_over_3qVnative, color=color, label=label)
    ax[0, 0].axhline(10, color='grey', ls=':', label='10 kPa ideal continuum global balance')
    ax[0, 0].set(xlabel='Actual physical time (s)', ylabel='Native mean total compression (kPa)')
    ax[0, 1].set(xlabel='Actual physical time (s)', ylabel='Tracked shell mean inward displacement (mm)')
    ax[1, 0].set(xlabel='Actual physical time (s)', ylabel='Native mean density (kg/m3)', title='No claim of density time convergence')
    ax[1, 1].set(xlabel='Actual physical time (s)', ylabel='Load virial / (3 q Vnative)', title='Native force consistency, not a fitted effective radius')
    for a in ax.flat:
        a.axvline(TD, color='grey', ls=':', alpha=.5); a.grid(alpha=.2); a.legend(fontsize=8)
    fig.suptitle('Cryer: native stress, tracked-shell motion, density and applied-load histories\nClosed uniform targets are diagnostics only for Parts61-64; not post-opening error gates.', fontsize=12)
    fig.savefig(targets[2], dpi=180); plt.close(fig)
    for p in targets[1:]:
        with Image.open(p) as im:
            im.verify()
    pair_max = {}
    for col in ['pressure_rms_pa', 'material_displacement_max_mm', 'total_stress_six_component_rms_pa', 'density_rms_kg_m3']:
        r = pair.loc[pair[col].idxmax()]
        pair_max[col] = dict(value=float(r[col]), part=int(r.part), time_s=float(r.time_s))
    cmd = "Get-CimInstance Win32_Process -Filter 'ProcessId=59224 OR ProcessId=42452' | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    owned = subprocess.check_output(['powershell', '-NoProfile', '-Command', cmd], text=True).strip()
    assert not owned, 'Recorded owned solver/wrapper PID still present; inspect reuse rather than stopping it'
    result = dict(analysis_checks_passed=True, visual_review_passed=False, utc=datetime.now(timezone.utc).isoformat(),
                  solver_executed_this_review=False, source_or_physics_changed=False, formal_run_admitted=False,
                  physical_acceptance=False, peak_window_half_passed=True, full_cycle_half_tested=False,
                  actual_end_time_s=.0703125, native_safety_frames_adopted=577, native_frames_reread_by_root_review=0,
                  independent_native_spot_review='Independent agent reread end frame, prefix Parts0/68 and both worst pressure/displacement pair frames; no full-frame rerun.',
                  freshly_rehashed_unique_bound_files=len(unique), freshly_rehashed_bytes=sum(e['bytes'] for e in unique.values()),
                  exact_prefix_samples=69, exact_prefix_columns=35, prefix_exclusions=[], all_sample_pairs=577,
                  pair_maxima=pair_max, coarse_peak=peaks[0], half_peak=peaks[1], theory_peak=reference_peak,
                  half_minus_coarse_peak_pa=peaks[1]['pressure_pa'] - peaks[0]['pressure_pa'],
                  both_preopening_equilibrium_diagnostics_passed=True,
                  reference_selftest=reference_math, reference_theta='Cv_eff*(t-tD)/a^2; finite Kw, g=9.80665',
                  comparison_window='Legacy Cv=.0027444522857366896*(t-tD)/a^2>=.005; all startup rows remain in CSV/plots.',
                  reviewed_diagnosis=['Reducing dt changes peak pressure by only about2 Pa and leaves the sampled peak time unchanged.',
                    'Loading equilibrium is achieved before opening; tD is the time origin for drainage, not ramp end or first open save.',
                    'Pressure/material-displacement bounds pass, but density differs; not all-state temporal convergence or density-cause proof.',
                    'Prior frozen-field evidence prioritizes coupled mechanical/compression/Darcy spatial consistency, not correction of external load alone.'],
                  next_decision='Do not launch a formal run or symC from this notification. Next bounded diagnosis: review frozen-field candidate Darcy A/B together with mechanical balance, local moments and dissipation before any dynamic admission.',
                  sources=[bound(p) for p in [Path(__file__), *paths, pair_path,
                      TEST / 'figures' / (COARSE + '_summary.csv'), TEST / 'figures' / (HALF + '_summary.csv'),
                      TEST / 'support/cryer_radial_consistency_r1.py', TEST / 'notes/cryer_finite_storage_r1.md',
                      TEST / 'notes/cryer_radial_consistency_r1.json']],
                  artifacts=[bound(p) for p in targets],
                  limitations=['Finite-storage reference is quasistatic, small-strain and at initial r/a=.05; not exact dynamic SPH truth.',
                    'No PART restart, peak fitting, effective-radius fitting, time reorigining, source edit or new solver.',
                    '577 native single-run safety and 69 native prefix comparison are adopted from sealed worker evidence, not reread in full here.',
                    'The closed-state uniform target is not a valid post-drain exact stress distribution.',
                    'Tracked shell and native-volume stress averages are diagnostics, not exact continuum surface/volume integrals.'])
    with receipt.open('x', encoding='utf8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps({k: result[k] for k in ['analysis_checks_passed', 'freshly_rehashed_unique_bound_files', 'coarse_peak', 'half_peak', 'theory_peak', 'pair_maxima']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
