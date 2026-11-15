"""Offline cached-HG/HG0 actual91-frame comparison; never decode or solve."""
import argparse
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.ticker import MaxNLocator
import c08_h18_lstar_window_review_r1 as old

m, core, T, L = old.m, old.core, old.T, old.L
need, read, stat, bind, entry, owned, same, bits = old.need, old.read, old.stat, old.bind, old.entry, old.owned, old.same, old.bits
TAG = 'c08_h18_hg_cached_physical_r1'
SCRIPT, NOTE = Path(__file__).resolve(), T / 'notes' / (TAG + '.md')
CHECK, FIG = L / (TAG + '.check.json'), T / 'figures'
RUN = L / 'c08_h18_hg_cached_window_GPU_r1.run.json'
NATIVE = L / 'c08_h18_hg_cached_window_GPU_r1.native.check.json'
EXPORTS = L / 'c08_h18_hg_cached_window_GPU_r1.native.exports_r1.check.json'
BASE_RUN, BASE_NATIVE = old.OLD_RUN, old.OLD_NATIVE
CASES, SELECTED, DP = ('Retained HG0', 'Cached HG xi0.1'), (38, 76, 90), .04
OPERATOR = 'EnergyNormalizedAdjointLoadingOnlyCachedMaterial'


def consume_in(receipt, path, consumed):
    rows = [q for q in receipt['consumed'] if same(q['path'], path)]
    need(rows and all(q == rows[0] for q in rows), 'Original consumed identity missing/ambiguous: ' + str(path))
    consumed.append(bind(rows[0]))


def inputs(consumed):
    run, native, baseline, bn = map(read, (RUN, NATIVE, BASE_RUN, BASE_NATIVE))
    exports = read(EXPORTS)
    need(exports['passed'] and exports['original_native_check'] == stat(NATIVE)
         and exports['actual_call'] == native['actual_call'] and exports['native_completion'] == native['native_completion']
         and exports['actual_native_frames'] == 91 and exports['typed_arrays'] == 22 and exports['native_IDs'] == 6805
         and exports['reader_invocations_new'] == 0 and not exports['native_files_rewritten'],
         'New independent post-completion export seal required; original native receipt remains unchanged')
    consumed.append(stat(EXPORTS))
    for q in (run, baseline):
        need(q['passed'] and q['solver_completed'] and q['consumed_stats_unchanged']
             and q['actual_exit'] == q['actual_Win32_exit'] == q['actual_tool_exit'] == 0
             and q['actual_steps'] == 2180000 and q['saved_frames'] == 91,
             'Actual complete normal91-frame run required')
        consumed.append(entry(q, 'actual_call')); owned(read(q['actual_call']['path']))
        consumed.extend(entry(q, k) for k in ('program', 'source_build', 'source_archive', 'source_pre_file',
            'source_native', 'planned_steps', 'input_xml', 'native_profile', 'Run_out', 'Run_csv'))
    need(run['configuration'] == 'Release' and run['profile'] == 'window' and run['new_updates'] == 180000
         and run['operator'] == OPERATOR and run['policy_schema'] == 2
         and run['environment_override'] == {'C08_HG_CACHED_H18': '1'}, 'Actual cached Release window required')
    build = read(run['source_build']['path'])
    need(build['passed'] and build['consumed_stats_unchanged'] and build['operator'] == OPERATOR
         and build['policy_schema'] == 2 and build['retained_original_objects'] == 111
         and build['private_objects'] == 3 and build['actual_link_objects'] == 114
         and build['single_material_producer'] and not build['cache_consumer_writeback_is_independent_material_solve']
         and build['private_sources'] == run['private_sources']
         and set(build['private_sources']) == {'host', 'gpu_host', 'CUDA', 'header', 'integrators'},
         'Actual single-producer111+3 candidate source proof required')
    consumed.extend(entry(run, k) for k in ('source_capture', 'baseline_source_capture', 'solver_completion'))
    consumed.extend(bind(q) for q in run['private_sources'].values())
    need(all(run[k] == baseline[k] for k in ('source_pre_file', 'source_native', 'source_archive', 'planned_steps')),
         'Actual common PRE/archive/91plan identities required')
    for k in ('input_xml', 'native_profile'):
        need(Path(run[k]['path']).read_bytes() == Path(baseline[k]['path']).read_bytes(), 'Original physical input differs: ' + k)
    for n in (native, bn):
        need(n['passed'] and n['consumed_stats_unchanged'] and n['reader_invocations'] == 1
             and n['solver_invocations'] == 0, 'One completed independent native read required')
        consumed.append(entry(n, 'actual_call')); owned(read(n['actual_call']['path']))
        consumed.append(entry(n, 'native_completion'))
    consume_in(native, RUN, consumed)
    for key in ('source_pre_file', 'input_xml', 'native_profile', 'planned_steps'):
        consume_in(native, run[key]['path'], consumed)
    nd, bd = read(native['native_completion']['path']), read(bn['native_completion']['path'])
    old.previous.receiver_done(nd); old.previous.receiver_done(bd)
    nr, br = Path(native['native_completion']['path']).parent, Path(bn['native_completion']['path']).parent
    need(same(nr.parent, run['output']) and same(br.parent, Path(baseline['Run_out']['path']).parent),
         'Actual typed export/run roots differ')
    for leaf in ('typed22.bin', 'typed22_layout.csv', 'clocks.csv'):
        rows = [q for q in exports['files'] if same(q['path'], nr / leaf)]
        need(len(rows) == 1, 'Exactly one new completed native export seal required: ' + leaf)
        consumed.append(bind(rows[0]))
    old.seal(br, L / 'c08_h18_lstar_cpu_off_r1.build.json', consumed)
    bundles = (core.typed(br, 6805, 91, consumed), core.typed(nr, 6805, 91, consumed))
    need((nr / 'typed22_layout.csv').read_bytes() == (br / 'typed22_layout.csv').read_bytes(),
         'The actual22 typed layouts differ')
    plan = core.table(run['planned_steps']['path'])
    need(len(plan) == 91 and list(plan[0]) == ['part', 'completed_step', 'saved_step', 'time_s', 'dt_s'],
         'Original complete91 scalar plan required')
    for part, (a, b, p) in enumerate(zip(bundles[0]['clocks'], bundles[1]['clocks'], plan)):
        step = 2180000 if part == 90 else 2000001 + part * 2000
        need(int(a['part']) == int(b['part']) == int(p['part']) == part
             and int(a['completed_step']) == int(b['completed_step']) == int(p['completed_step']) == step
             and int(a['saved_step']) == int(b['saved_step']) == int(p['saved_step']) == step - 1
             and bits(a['time_s']) == bits(b['time_s']) == bits(p['time_s'])
             and bits(a['dt_s']) == bits(b['dt_s']) == bits(p['dt_s']) == bits(5e-6)
             and float(a['signed_dterror_s']) <= 1e-14 and float(b['signed_dterror_s']) <= 1e-14
             and a['dterror_interval_empty'] == b['dterror_interval_empty'] == '0',
             'Actual exact-time/step/signed91-frame join failed')
    source = read(run['source_native']['path'])
    need(source['passed'] and source['certified_PRE'] and not source['partial'] and source['samples'] == 1001
         and source['completed_steps'] == 2000000 and source['native_IDs'] == 7060 and source['typed_arrays'] == 22
         and source['same_material_plastic_PRE'], 'Full genuine schema2 source reference required')
    sr = Path(run['source_native']['path']).parent
    old.seal(sr, L / 'c08_h18_rv_window_review_r1.check.json', consumed)
    ref, cohorts = old.previous.source_reference(core.typed(sr, 7060, 1001, consumed), source)
    need(run['actual_source_time_s'] == nd['source_actual_time_s'] == bd['source_actual_time_s'] == ref['time'],
         'Shared actual PRE endpoint differs')
    consumed.extend(stat(q) for q in (RUN, NATIVE, BASE_RUN, BASE_NATIVE))
    return (baseline, run), bundles, ref, cohorts


def analyze(bundles, ref):
    history, matched, spatial, snapshots = [], [], [], {}
    last = {case: None for case in CASES}
    for part in range(91):
        current = {}
        for case, bundle in zip(CASES, bundles):
            frame = core.core.read22(bundle, part)  # Exactly one22-array read per case/time.
            d = old.frame_data(frame, ref, last[case])
            rows = old.aggregate(case, part, bundle['clocks'][part], d, ref, last[case])
            for row in rows:
                mask = d['masks'][row['cohort']]; count = int(mask.sum())
                row.update(negative_p_fraction=float(np.count_nonzero(mask & (d['p'] < 0)) / count) if count else None,
                    z_height_m=float(d['pos'][mask, 2].max()) if count else None,
                    height_change_from_PRE_m=float(d['pos'][mask, 2].max() - ref['pos'][mask, 2].max()) if count else None,
                    NN_over_dp_max=float(d['nn'][mask].max()) if count else None,
                    material_displacement_max_mm=float(1000 * np.linalg.norm(d['du'][mask], axis=1).max()) if count else None)
                if last[case] is None or not count:
                    row['saved_interval_material_motion_RMS_mm'] = None
                else:
                    delta = d['pos'][mask] - last[case]['pos'][mask]
                    row['saved_interval_material_motion_RMS_mm'] = float(1000*np.sqrt(np.mean(np.sum(delta*delta, axis=1))))
                need(all(math.isfinite(x) for x in row.values() if isinstance(x, float)),
                     'No nonfinite added scientific metric may be omitted')
            history.extend(rows); current[case] = d; last[case] = d
            if part in SELECTED:
                fixed = np.array(frame['Posd'][frame['Idp'][:, 0] < 2060])
                need(fixed.shape == (1805, 3), 'Every selected fixed boundary particle required')
                snapshots[(case, part)] = (d, fixed, float(bundle['clocks'][part]['time_s']) - ref['time'])
                for i, nid in enumerate(d['ids']):
                    row = dict(case=case, part=part, completed_step=int(bundle['clocks'][part]['completed_step']),
                        actual_time_s=float(bundle['clocks'][part]['time_s']), tau_s=float(bundle['clocks'][part]['time_s']) - ref['time'],
                        native_id=int(nid), x_m=float(d['pos'][i, 0]), y_m=float(d['pos'][i, 1]), z_m=float(d['pos'][i, 2]),
                        p_Pa=float(d['p'][i]), native_p_minus_fixedP0_Pa=float(d['ex'][i]), NN_over_dp=float(d['nn'][i]),
                        nearest_material_id=int(d['ids'][d['neighbor'][i]]), kappa=float(d['kappa'][i]), J=float(d['J'][i]),
                        n=float(d['n'][i]), V_m2=float(d['V'][i]), rho_kg_m3=float(d['rho'][i]), k_m_s=float(d['k'][i]),
                        speed_m_s=float(d['speed'][i]), effective_stress_Frobenius_Pa=float(d['effnorm'][i]),
                        total_stress_Frobenius_Pa=float(d['totalnorm'][i]), dx_from_PRE_mm=float(1000*d['du'][i, 0]),
                        dz_from_PRE_mm=float(1000*d['du'][i, 2]), initial_material_layer=int(ref['layer'][i]))
                    for j, axis in enumerate(('xx', 'yy', 'zz')):
                        row['effective_' + axis + '_Pa'] = float(d['kk'][i, j]); row['total_' + axis + '_Pa'] = float(d['total'][i, j])
                    for j, axis in enumerate(('xy', 'yz', 'xz')):
                        row['effective_' + axis + '_Pa'] = row['total_' + axis + '_Pa'] = float(d['ij'][i, j])
                    spatial.append(row)
        a, b = current[CASES[0]], current[CASES[1]]
        dp, du = b['p'] - a['p'], b['pos'] - a['pos']
        ds, de, di = b['total'] - a['total'], b['kk'] - a['kk'], b['ij'] - a['ij']
        matched.append(dict(part=part, completed_step=int(bundles[0]['clocks'][part]['completed_step']),
            actual_time_s=float(bundles[0]['clocks'][part]['time_s']), tau_s=float(bundles[0]['clocks'][part]['time_s']) - ref['time'],
            delta_p_RMS_Pa=float(np.sqrt(np.mean(dp*dp))), delta_p_absmax_Pa=float(np.abs(dp).max()),
            delta_XYZ_RMS_mm=float(1000*np.sqrt(np.mean(np.sum(du*du, axis=1)))),
            delta_XYZ_max_mm=float(1000*np.linalg.norm(du, axis=1).max()),
            delta_effective_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(de*de, axis=1) + 2*np.sum(di*di, axis=1)))),
            delta_total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(ds*ds, axis=1) + 2*np.sum(di*di, axis=1)))),
            delta_J_absmax=float(np.abs(b['J'] - a['J']).max()), delta_kappa_absmax=float(np.abs(b['kappa'] - a['kappa']).max())))
    need(len(history) == 1092 and len(matched) == 91 and len(spatial) == 30000,
         'All182 states/5000 material observations and selected30000 spatial rows required')
    return history, matched, spatial, snapshots


def window_summary(history, runs):
    rows = []
    for case, run in zip(CASES, runs):
        allrows = [r for r in history if r['case'] == case and r['cohort'] == 'all']; final = allrows[-1]
        row = dict(case=case, frames=91, soil_IDs=5000, final_tau_s=final['tau_s'],
            final_p_RMS_Pa=final['p_Pa_RMS'], final_min_p_Pa=final['p_Pa_min'], final_max_p_Pa=final['p_Pa_max'],
            final_negative_p_fraction=final['negative_p_fraction'], final_NN_min_dp=final['NN_over_dp_min'],
            final_NN_q05_dp=final['NN_over_dp_q05'], final_NN_q50_dp=final['NN_over_dp_q50'],
            final_NN_q95_dp=final['NN_over_dp_q95'], final_NN_max_dp=final['NN_over_dp_max'],
            final_unique_pairs_lt_0p5dp=final['unique_pairs_incident_lt_0p5dp'], final_front_x_m=final['x_front_m'],
            final_height_z_m=final['z_height_m'], final_speed_RMS_m_s=final['speed_m_s_RMS'],
            final_kinetic_proxy_J_per_m=final['mixture_kinetic_proxy_J_per_m'], final_J_min=final['J_min'],
            final_saved_interval_motion_RMS_mm=final['saved_interval_material_motion_RMS_mm'],
            final_J_max=final['J_max'], final_kappa_max=final['kappa_max'],
            final_effective_stress_RMS_Pa=final['effective_stress_Frobenius_Pa_RMS'],
            final_total_stress_RMS_Pa=final['total_stress_Frobenius_Pa_RMS'])
        for key, selector in (('p_Pa_min', min), ('p_Pa_max', max), ('NN_over_dp_min', min),
            ('unique_pairs_incident_lt_0p5dp', max), ('negative_p_fraction', max), ('speed_m_s_max', max),
            ('mixture_kinetic_proxy_J_per_m', max), ('J_min', min), ('J_max', max), ('kappa_max', max)):
            extreme = selector(allrows, key=lambda r: r[key]); row['window_' + key] = extreme[key]
            row['window_' + key + '_part'] = extreme['part']; row['window_' + key + '_tau_s'] = extreme['tau_s']
        s = run['summary']; loop = float(s['TSimul']); need(math.isfinite(loop) and loop > 0, 'Actual positive loop time required')
        row.update(TSimul_s=loop, TTotal_s=float(s['TTotal']), Hardware=s['Hardware'],
            observed_new_updates_per_s=180000/loop, controlled_benchmark=False)
        rows.append(row)
    for r in rows:
        r['loop_ratio_to_HG0'] = r['TSimul_s']/rows[0]['TSimul_s']
        r['final_pressure_RMS_ratio_to_HG0'] = r['final_p_RMS_Pa']/rows[0]['final_p_RMS_Pa']
    return rows


def plots(history, snapshots):
    groups = (
        ('pressure_motion', (('p_Pa_RMS', 'Pressure RMS [Pa]'), ('p_Pa_min', 'Minimum signed pressure [Pa]'),
            ('negative_p_fraction', 'Negative-pressure fraction'), ('x_front_m', 'Front maximum x [m]'),
            ('z_height_m', 'Maximum soil z [m]'), ('speed_m_s_RMS', 'Speed RMS [m/s]'),
            ('mixture_kinetic_proxy_J_per_m', 'Mixture kinetic proxy [J/m]'),
            ('settlement_from_PRE_mm_mean', 'Fixed initial top settlement [mm]'))),
        ('material_spacing', (('NN_over_dp_min', 'Minimum soil NN / dp'), ('NN_over_dp_q95', '95% soil NN / dp'),
            ('unique_pairs_incident_lt_0p5dp', 'Unique soil pairs < 0.5dp'), ('J_min', 'Minimum stored J'),
            ('J_max', 'Maximum stored J'), ('kappa_max', 'Maximum accumulated kappa'),
            ('effective_stress_Frobenius_Pa_RMS', 'Effective stress Frobenius RMS [Pa]'),
            ('total_stress_Frobenius_Pa_RMS', 'Total stress Frobenius RMS [Pa]'))))
    paths = []
    for suffix, panels in groups:
        fig, axes = plt.subplots(4, 2, figsize=(14, 16), layout='constrained')
        for ax, (key, title) in zip(axes.flat, panels):
            for case in CASES:
                cohort = 'fixed_initial_top' if key == 'settlement_from_PRE_mm_mean' else 'all'
                rows = [r for r in history if r['case'] == case and r['cohort'] == cohort]
                ax.plot([r['tau_s'] for r in rows], [r[key] for r in rows], label=case, lw=1.6)
            ax.set_title(title); ax.set_xlabel('Actual time after PRE release [s]'); ax.grid(True, alpha=.25)
            ax.xaxis.set_major_locator(MaxNLocator(nbins=6)); ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
        axes[0, 0].legend(fontsize=10)
        fig.suptitle('Actual91-frame cached HG vs HG0: all5000 soil IDs\nDifferent operators; no half-step/theory or clumping-repair acceptance', fontsize=13)
        path = FIG / (TAG + '_' + suffix + '.png'); fig.savefig(path, dpi=160); plt.close(fig); paths.append(path)
    positions = np.concatenate([d['pos'] for d, _, _ in snapshots.values()])
    for field, cmap, title, unit in (('p', 'coolwarm', 'Native signed pressure', 'Pa'), ('nn', 'viridis', 'True3D soil nearest-neighbor spacing', 'dp')):
        values = np.concatenate([d[field] for d, _, _ in snapshots.values()]); lo, hi = float(values.min()), float(values.max())
        norm = TwoSlopeNorm(vmin=lo, vcenter=0., vmax=hi) if field == 'p' and lo < 0 < hi else Normalize(vmin=lo, vmax=hi)
        fig, axes = plt.subplots(2, 3, figsize=(17, 9), layout='constrained')
        for row, case in enumerate(CASES):
            for col, part in enumerate(SELECTED):
                d, fixed, tau = snapshots[(case, part)]; ax = axes[row, col]
                ax.scatter(fixed[:, 0], fixed[:, 2], s=2, c='.6', marker='s', rasterized=True)
                sc = ax.scatter(d['pos'][:, 0], d['pos'][:, 2], c=d[field], s=4, cmap=cmap, norm=norm, rasterized=True)
                ax.set_aspect('equal'); ax.set_xlim(min(0, float(positions[:, 0].min())) - DP, float(positions[:, 0].max()) + DP)
                ax.set_ylim(min(0, float(positions[:, 2].min())) - DP, float(positions[:, 2].max()) + DP)
                ax.set_title(case + '\nP' + str(part) + ' actual tau=' + format(tau, '.9g') + ' s', fontsize=11)
                ax.set_xlabel('x [m]'); ax.set_ylabel('z [m]')
                ax.xaxis.set_major_locator(MaxNLocator(nbins=6)); ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
        fig.colorbar(sc, ax=axes.ravel().tolist(), label=title + ' [' + unit + ']', shrink=.86, pad=.025)
        fig.suptitle(title + '\nCommon full30000-soil-point scale and coordinates; original fixed particles shown in grey', fontsize=13)
        path = FIG / (TAG + '_' + field + '.png'); fig.savefig(path, dpi=160); plt.close(fig); paths.append(path)
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--execution-authorized', action='store_true')
    need(parser.parse_args().execution_authorized, 'Separate root offline-analysis authorization required')
    outputs = [FIG / (TAG + suffix) for suffix in ('_history.csv', '_matched.csv', '_spatial.csv', '_cohorts.csv',
        '_window_summary.csv', '_pressure_motion.png', '_material_spacing.png', '_p.png', '_nn.png')]
    need(not CHECK.exists() and all(not q.exists() for q in outputs), 'Existing complete/partial derived analysis protected')
    consumed = [stat(q) for q in (SCRIPT, NOTE, Path(old.__file__), Path(old.shared.__file__), Path(core.__file__),
        Path(core.core.__file__), Path(old.previous.__file__))]
    try:
        runs, bundles, ref, cohorts = inputs(consumed)
        history, matched, spatial, snapshots = analyze(bundles, ref); summary = window_summary(history, runs)
        old.shared.frozen(consumed)
        for path, rows in zip(outputs[:5], (history, matched, spatial, cohorts, summary)): old.write(path, rows)
        pictures = plots(history, snapshots); old.shared.frozen(consumed)
        m.save(CHECK, dict(stage=TAG, passed=True, analysis_complete=True, physical_acceptance=False,
            actual_states=182, frames_each=91, soil_IDs_each=5000, typed_arrays_each=22, history_rows=1092,
            matched_rows=91, spatial_rows=30000, source_cohort_rows=5000, window_summary_rows=2,
            scientific_PNGs=4, selected_parts=SELECTED, source_reference_initial_and_PRE_only=True,
            all91_frames_in_statistics=True, all_signed_points_retained=True, no_interpolation=True,
            cross_operator_differences_are_half_errors=False, paper_is_theory_truth=False,
            soil_NN_is_void_area=False, negative_triangle_is_stored_J=False, storage_is_fluid_mass=False,
            kinetic_proxy_is_complete_energy=False, native_proves_HG_operator=False,
            cache_coherence_is_independent_material_solve=False, old_reference_seals_are_original_decoder_exit=False,
            observed_timing_not_controlled_benchmark=True, new_solver_invocations=0, new_native_invocations=0,
            new_API_calls=0, SHA_scans=0, visual_QA_pending=True, consumed=consumed, consumed_stats_unchanged=True,
            files=[stat(q) for q in (*outputs[:5], *pictures)]))
    except Exception as error:
        if not CHECK.exists(): m.save(CHECK, dict(stage=TAG, passed=False, first_failure=str(error), consumed=consumed,
            partial_outputs_preserved=True, new_solver_invocations=0, new_native_invocations=0, physical_acceptance=False))
        raise


if __name__ == '__main__': main()
