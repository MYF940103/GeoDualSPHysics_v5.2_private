"""Offline selected HG0/cached-HG fields at Fig14 times; no solver or native decoder."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import c08_h18_storage_review_r2 as native

T = Path(__file__).resolve().parents[1]
TAG = 'c08_h18_hg_paper06_r1'
NOTE = T / 'notes' / (TAG + '.md')
CHECK = T / 'logs' / (TAG + '.check.json')
PREFIX = T / 'figures' / TAG
CASES = ('HG0', 'Cached HG xi=0.1')
JOBS = ('c08_h18_as03_n255_r1', 'c08_h18_hg_cached_window_GPU_r1')
REQUESTS = (.3, .6)
need, read, stat, bind = native.need, native.read, native.stat, native.bind


def table(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write(path, rows):
    with path.open('x', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def sealed_file(receipt, path, consumed, key='consumed'):
    refs = [q for q in receipt[key] if Path(q['path']).resolve() == path.resolve()]
    need(refs and all(q == refs[0] for q in refs), 'Missing/ambiguous retained seal: ' + str(path))
    bind(refs[0]); consumed.append(refs[0])


def inputs(consumed):
    physical_path = T / 'logs/c08_h18_hg_cached_physical_r1.check.json'
    physical = read(physical_path)
    need(physical['passed'] and physical['analysis_complete'] and physical['consumed_stats_unchanged'],
         'Completed descriptive HG0/cached-HG review required')
    consumed.append(stat(physical_path))
    export_path = T / 'logs/c08_h18_hg_cached_window_GPU_r1.native.exports_r1.check.json'
    exports = read(export_path)
    need(exports['passed'] and not exports['native_files_rewritten'], 'Completed cached export seal required')
    consumed.append(stat(export_path))
    bundles, source_times = [], []
    for ci, job in enumerate(JOBS):
        runpath = T / 'logs' / (job + '.run.json')
        npth = T / 'logs' / ('c08_h18_as03_n255_native_r1.check.json' if ci == 0 else job + '.native.check.json')
        run, check = read(runpath), read(npth)
        need(run['passed'] and run['solver_completed'] and run['actual_steps'] == 2180000
             and run['saved_frames'] == 91 and check['passed'] and check['reader_invocations'] == 1
             and check['consumed_stats_unchanged'], 'Completed retained91/native pair required')
        need(all(run[k] == 0 for k in ('actual_exit', 'actual_Win32_exit', 'actual_tool_exit')),
             'Retained solver did not exit normally')
        donepath = Path(check['native_completion']['path']); bind(check['native_completion'])
        done = read(donepath)
        need(done['passed'] and done['samples'] == 91 and done['typed_arrays'] == 22
             and done['actual_native_IDs_per_frame'] == 6805 and done['soil_IDs'] == 5000
             and done['actual_fixed_IDs'] == 1805 and done['max_scalar_clock_error_s'] <= 1e-14
             and done['max_signed_dterror_s'] <= 1e-14 and not done['native_rewritten'],
             'Original native completion extent/guards differ')
        root = donepath.parent
        for leaf in ('typed22.bin', 'typed22_layout.csv', 'clocks.csv'):
            sealed_file(physical if ci == 0 else exports, root / leaf, consumed,
                        'consumed' if ci == 0 else 'files')
        bundles.append(native.typed(root, 6805, 91, consumed))
        source_times.append(float(done['source_actual_time_s']))
        consumed += [stat(runpath), stat(npth), check['native_completion']]
        if ci == 0:
            common_pre = run['source_pre_file']
        else:
            need(run['source_pre_file'] == common_pre, 'Different material PRE is not this comparison')
            need(exports['original_native_check'] == stat(npth), 'Cached seal/native receipt mismatch')
    need(source_times[0] == source_times[1], 'Different actual release clocks')
    opath = T / 'logs/upl_c08_lian14_outline_r1.check.json'; outlinecheck = read(opath)
    need(outlinecheck['passed'] and outlinecheck['analysis_completed']
         and not outlinecheck['pressure_values_sampled'], 'Retained descriptive outline required')
    consumed.append(stat(opath))
    paths = [T / 'figures' / ('upl_c08_lian14_outline_r1_' + q + '.csv') for q in ('outline', 'summary')]
    for path in paths:
        sealed_file(outlinecheck, path, consumed, 'outputs')
    return bundles, source_times[0], table(paths[0]), table(paths[1])


def collect(bundles, source_time, paper_summary):
    spatial, summary, selected = [], [], {}
    for request in REQUESTS:
        paper = next(q for q in paper_summary if float(q['requested_tau_s']) == request)
        pair_clock = None
        for case, bundle in zip(CASES, bundles):
            times = np.array([float(q['time_s']) - source_time for q in bundle['clocks']])
            part = int(np.argmin(abs(times - request)))
            clock = bundle['clocks'][part]
            need(abs(times[part] - request) <= 5.01e-6, 'No actual near-paper save within original cadence')
            identity = (int(clock['completed_step']), float(clock['time_s']), float(clock['dt_s']))
            need(pair_clock is None or pair_clock == identity, 'Cross-option actual clocks differ')
            pair_clock = identity
            f = native.core.read22(bundle, part)  # Four existing records total; no BI4 reader.
            soil = f['Idp'][:, 0] >= 2060
            ids = np.array(f['Idp'][soil, 0]); need(np.array_equal(ids, np.arange(2060, 7060)), 'All5000 material IDs required')
            pos = np.array(f['Posd'][soil]); fixed = np.array(f['Posd'][~soil])
            p = np.array(f['PorePress'][soil, 0]); p0 = np.array(f['PorePress0'][soil, 0])
            ex = np.array(f['ExcessPorePress'][soil, 0]); kap = np.array(f['Kplastic'][soil, 0])
            J = np.array(f['PoroVolumeRatio'][soil, 0]); por = np.array(f['PoroPorosity'][soil, 0])
            rho = np.array(f['PoroMixtureDensity'][soil, 0]); k = np.array(f['PoroHydraulicConductivity'][soil, 0]); vel = np.array(f['Vel'][soil])
            selected[(request, case)] = (pos, fixed, ex, float(times[part]))
            for i, nid in enumerate(ids):
                spatial.append(dict(case=case, requested_tau_s=request, part=part, completed_step=identity[0],
                    actual_time_s=identity[1], actual_tau_s=float(times[part]), native_id=int(nid),
                    x_m=float(pos[i, 0]), y_m=float(pos[i, 1]), z_m=float(pos[i, 2]),
                    total_p_Pa=float(p[i]), fixed_initial_P0_Pa=float(p0[i]), native_p_minus_fixedP0_Pa=float(ex[i]),
                    kappa=float(kap[i]), J=float(J[i]), porosity=float(por[i]), mixture_rho_kg_m3=float(rho[i]),
                    conductivity_m_s=float(k[i]), vx_m_s=float(vel[i, 0]), vy_m_s=float(vel[i, 1]), vz_m_s=float(vel[i, 2])))
            front = float(pos[:, 0].max()); below = int(np.count_nonzero(ex < -10000)); above = int(np.count_nonzero(ex > 10000))
            summary.append(dict(case=case, requested_tau_s=request, native_part=part, actual_tau_s=float(times[part]),
                actual_minus_requested_s=float(times[part] - request), material_IDs=len(ids),
                total_p_min_Pa=float(p.min()), total_p_max_Pa=float(p.max()), total_p_RMS_Pa=float(np.sqrt(np.mean(p.astype(float)**2))),
                native_excess_min_Pa=float(ex.min()), native_excess_max_Pa=float(ex.max()),
                native_excess_RMS_Pa=float(np.sqrt(np.mean(ex.astype(float)**2))), native_excess_below_minus10kPa=below,
                native_excess_above_plus10kPa=above, below_fraction=below/len(ids), above_fraction=above/len(ids),
                max_kappa=float(kap.max()), min_J=float(J.min()), max_J=float(J.max()), native_center_front_m=front,
                paper_visible_colored_front_m=float(paper['front_colored_extent_m']),
                center_minus_paper_visible_front_m=front-float(paper['front_colored_extent_m']),
                paper_raster_allowance_m=float(paper['front_digitization_allowance_m']),
                separate_particle_center_representation_scale_m=.02, difference_is_theory_error=False,
                native_excess_is_established_paper_excess=False))
    return spatial, summary, selected


def plots(selected, summary, outline):
    plt.rcParams.update({'font.size': 10})
    fig, axes = plt.subplots(2, 2, figsize=(16, 6.9), layout='constrained')
    norm = Normalize(-10, 10, clip=False)
    for ri, request in enumerate(REQUESTS):
        for ci, case in enumerate(CASES):
            pos, fixed, ex, tau = selected[(request, case)]; ax = axes[ri, ci]
            ax.scatter(fixed[:, 0], fixed[:, 2], s=2, c='.35', rasterized=True)
            image = ax.scatter(pos[:, 0], pos[:, 2], c=ex*.001, s=5, cmap='jet', norm=norm, rasterized=True)
            row = next(q for q in summary if q['case'] == case and q['requested_tau_s'] == request)
            ax.set(title=f'{case}; actual tau={tau:.9f} s\nBelow -10 / above +10 kPa: {row["native_excess_below_minus10kPa"]} / {row["native_excess_above_plus10kPa"]}',
                   xlim=(-.06, 8.04), ylim=(-.06, 2.18), xlabel='x [m]', ylabel='z [m]')
            ax.set_aspect('equal'); ax.grid(alpha=.15)
    fig.colorbar(image, ax=list(axes.flat), extend='both', label='Native p - fixed initial P0 [kPa]', shrink=.8)
    fig.suptitle('C08 psi=0: existing material states at Lian2023 Fig14 times', fontsize=13)
    fig.supxlabel('Native p-P0 is not established as the paper excess definition. Jet-style palette; fixed +/-10 kPa display only.\nAll raw values and over-range fractions retained; no smoothing, interpolation or pressure-error claim.', fontsize=9)
    pressure = Path(str(PREFIX) + '_native_excess.png'); fig.savefig(pressure, dpi=180); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(16, 3.9), layout='constrained')
    for ax, request in zip(axes, REQUESTS):
        for ci, case in enumerate(CASES):
            pos, _, _, tau = selected[(request, case)]
            ax.scatter(pos[:, 0], pos[:, 2], s=3, c=('C0', 'C1')[ci], alpha=.55, label=f'{case}; tau={tau:.6f}s', rasterized=True)
        edge = [q for q in outline if float(q['requested_tau_s']) == request]
        ax.scatter([float(q['x_m']) for q in edge], [float(q['z_m']) for q in edge], s=3, c='k', label='Paper visible bulk edge', rasterized=True)
        ax.set(title=f'Fig14 nominal {request:g} s', xlim=(-.06, 8.04), ylim=(-.06, 2.18), xlabel='x [m]', ylabel='z [m]')
        ax.set_aspect('equal'); ax.grid(alpha=.15); ax.legend(fontsize=8, loc='upper right')
    fig.suptitle('Particle centers versus retained paper raster outline', fontsize=13)
    fig.supxlabel('Raster reading scale about +/-0.036 m; separate center representation scale 0.02 m.\nNo shape fitting, time interpolation or exact theory-error claim.', fontsize=9)
    shape = Path(str(PREFIX) + '_paper_shape.png'); fig.savefig(shape, dpi=180); plt.close(fig)
    return [pressure, shape]


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--execution-authorized', action='store_true'); args = parser.parse_args()
    need(args.execution_authorized, 'Root review and independent offline execution authorization required')
    need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG + '_*')), 'Existing completed/partial outputs protected')
    consumed = [stat(Path(__file__)), stat(NOTE), stat(Path(native.__file__)), stat(Path(native.core.__file__))]
    result = dict(stage=TAG, passed=False, analysis_complete=False, physical_acceptance=False,
                  solver_invocations=0, native_decodes=0, VTK_invocations=0, SHA_scans=0)
    try:
        bundles, source_time, outline, paper_summary = inputs(consumed)
        spatial, summary, selected = collect(bundles, source_time, paper_summary)
        need(len(spatial) == 20000 and len(summary) == 4, 'Exactly four full5000-ID states required')
        files = [Path(str(PREFIX) + '_spatial.csv'), Path(str(PREFIX) + '_summary.csv')]
        write(files[0], spatial); write(files[1], summary); files += plots(selected, summary, outline)
        need(all(stat(q['path']) == q for q in consumed), 'An immutable input binding changed')
        result.update(passed=True, analysis_complete=True, consumed_stats_unchanged=True,
                      selected_records=4, material_rows=len(spatial), summary_rows=len(summary),
                      paper_pressure_values_digitized=False, native_excess_is_established_paper_excess=False,
                      all_raw_values_retained=True, palette='jet-style visual approximation, not extracted paper RGB',
                      display_range_kPa=[-10, 10], visual_QA_pending=True, files=[stat(q) for q in files], summary=summary)
    except Exception as error:
        result['first_failure'] = str(error)
    result['consumed'] = consumed
    CHECK.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    need(result['passed'], result.get('first_failure', 'Offline review failed; preserve partials'))


if __name__ == '__main__':
    main()
