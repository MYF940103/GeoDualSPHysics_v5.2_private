"""Offline diagnostic review of sealed Stage1 ON/OFF results; default help only."""
import argparse
import ast
import importlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd

TESTS = Path(__file__).resolve().parents[1]
TAG, SEQUENCE = 'sw_stage1_equilibrium_review_r1', 'sw_stage1_current_r2'
SIGMA = ['sigma_xx', 'sigma_yy', 'sigma_zz', 'sigma_xy', 'sigma_yz', 'sigma_xz']
LIMITATIONS = [
    'Diagnostic small-strain, linear constrained-column references only; no new theory-error threshold or physical acceptance.',
    'H=1 is the physical geometry; HD is the initial drained material-node plane. Neither is fitted or used to shift saved data.',
    'The ideal undrained reference excludes Shepard. Enabled Shepard changes local excess pressure without changing effective stress.',
    'k=0 eliminates Darcy, including symC; this is not a symC accuracy test. The ten drained top nodes still have finite particle volume.',
    'p0 is a fixed material reference; native float excess and double(p)-double(p0) are reported separately.',
    'Current hydro uses the mean actual drained top-material plane, not a fitted boundary or a recomputed per-particle p0.',
    'Layer curves use fixed initial material IDs. All 61x100 layer means are retained; no smoothing, clipping or interpolation.',
    'Independent native redecoding covers first/final frames. Full 61-frame native safety/ID coverage comes from verified sealed receipts.',
    'Sealed owned-exit evidence is checked; this offline analysis does not launch a solver or perform a new process inventory.',
    'The original 5-Pa/.005-mm limit belongs to the short matched-time half comparison, not ON/OFF or ideal-theory differences.',
    'Completion is not equilibrium, restart interoperability, long-cycle or general constitutive acceptance.'
]


def parameters(config):
    tree = ET.parse(config)
    value = lambda name: float(tree.find('.//' + name).get('value'))
    var = lambda name: float(tree.find('.//newvarcte[@' + name + ']').get(name))
    e, nu = value('ModulusE'), value('PRvs')
    k, shear = e / (3 * (1 - 2 * nu)), e / (2 * (1 + nu))
    m, mf = k + 4 * shear / 3, value('PoreWaterBulkModulus') / value('Porosity')
    g = abs(float(tree.find('.//constantsdef/gravity').get('z')))
    assert value('HydraulicConductivity') == 0 and value('HydroMechInitMode') == 1
    assert tree.find('.//parameter[@key="SlipMode"]').get('value') == '1'
    return dict(E=e, nu=nu, K=k, G=shear, M=m, Mf=mf, B=mf / (m + mf),
                rho=value('rhop0'), rho_w=value('PoreWaterRho'), g=g, H=var('sizefz'), dp=var('Dp'))


def ideal(z, height, p):
    """Same-plane hydrostatic preinitialization; not the paper's zero-p initial state."""
    depth = np.maximum(height - np.asarray(z), 0.)
    gamma = (p['rho'] - p['rho_w']) * p['g']
    hydro, q = p['rho_w'] * p['g'] * depth, p['B'] * gamma * depth
    szz = -(1 - p['B']) * gamma * depth
    settlement = gamma / (p['M'] + p['Mf']) * (height * z - np.asarray(z) ** 2 / 2) * 1000
    return dict(p0_pa=hydro, q_pa=q, p_pa=hydro + q, sigma_zz_pa=szz,
                total_sigma_zz_pa=-p['rho'] * p['g'] * depth, settlement_mm=settlement)


def enrich(profile, rows, p, label):
    a = profile.copy()
    initial = a[a.part == 0].sort_values('layer')
    assert len(a) == 6100 and len(initial) == 100 and np.array_equal(initial.layer, np.arange(100))
    assert np.isfinite(a.to_numpy(dtype='<f8')).all() and not a.duplicated(['part', 'layer']).any()
    for row in rows:
        b = a[a.part == row['part']].sort_values('layer')
        assert len(b) == 100 and np.array_equal(b.layer, np.arange(100))
        assert b.time_s.eq(row['time_s']).all() and b.natural_step.eq(row['natural_step']).all()
        assert np.array_equal(b.z0_m, initial.z0_m) and np.array_equal(b.porepress0_pa, initial.porepress0_pa)
    hd = float(initial.z0_m.iloc[-1])
    assert abs(hd - (p['H'] - p['dp'] / 2)) < 1e-12
    a['job'] = label
    a['saved_step'] = a.part.map({r['part']: r['saved_step'] for r in rows})
    a['q_double_pa'] = a.pressure_pa - a.porepress0_pa
    a['native_excess_roundoff_pa'] = a.excess_native_pa - a.q_double_pa
    a['r_native_pa'] = a.excess_native_pa + p['Mf'] * (a.sigma_xx + a.sigma_yy + a.sigma_zz) / (3 * p['K'])
    a['drained_plane_now_m'] = a.part.map(a[a.layer == 99].set_index('part').z_m)
    a['hydro_now_pa'] = p['rho_w'] * p['g'] * np.maximum(a.drained_plane_now_m - a.z_m, 0.)
    a['q_current_pa'] = a.pressure_pa - a.hydro_now_pa
    a['reference_shift_pa'] = a.hydro_now_pa - a.porepress0_pa
    assert np.max(np.abs(a.q_double_pa - a.q_current_pa - a.reference_shift_pa)) < 1e-9
    for prefix, height in [('ideal_H1', p['H']), ('ideal_HD', hd)]:
        for key, values in ideal(a.z0_m.to_numpy(), height, p).items():
            a[prefix + '_' + key] = values
    return a, hd


def history(profile, rows, label):
    result = []
    for row in rows:
        b = profile[profile.part == row['part']].sort_values('layer')
        bottom, top = b.iloc[0], b.iloc[-1]
        r = dict(row, job=label, bottom_p_pa=bottom.pressure_pa, bottom_p0_pa=bottom.porepress0_pa,
                 bottom_q_native_pa=bottom.excess_native_pa, bottom_q_current_pa=bottom.q_current_pa,
                 bottom_reference_shift_pa=bottom.reference_shift_pa, bottom_sigma_zz_pa=bottom.sigma_zz,
                 bottom_total_sigma_zz_pa=bottom.total_sigma_zz_pa, top_settlement_mm=top.settlement_mm,
                 bottom_settlement_mm=bottom.settlement_mm, top_minus_bottom_settlement_mm=top.settlement_mm-bottom.settlement_mm,
                 layer_mean_r_rms_pa=float(np.sqrt(np.mean(b.r_native_pa ** 2))),
                 layer_mean_r_max_abs_pa=float(b.r_native_pa.abs().max()),
                 column_layer_mean_pressure_range_pa=float(b.pressure_pa.max()-b.pressure_pa.min()))
        result.append(r)
    return pd.DataFrame(result)


def last_window(profile, hist):
    """Keep the actual final .300001-s save; do not relabel it as exactly .3 s."""
    h = hist[hist.time_s >= .25 - 1e-14]
    assert len(h) >= 10 and h.part.iloc[-1] == 60
    first = profile[profile.part == h.part.iloc[0]].sort_values('layer')
    last = profile[profile.part == 60].sort_values('layer')
    keys = ['pressure_pa', 'excess_native_pa', 'q_current_pa', 'total_sigma_zz_pa', 'settlement_mm', 'rho_kg_m3', 'r_native_pa'] + SIGMA
    drift = {k: float(np.max(np.abs(last[k].to_numpy()-first[k].to_numpy()))) for k in keys}
    ranges = {k: float(profile[profile.part.isin(h.part)].groupby('layer')[k].agg(lambda x: x.max()-x.min()).max()) for k in keys}
    return dict(actual_start_s=float(h.time_s.iloc[0]), actual_end_s=float(h.time_s.iloc[-1]), samples=len(h),
                maximum_absolute_layer_endpoint_drift=drift, maximum_layer_window_range=ranges,
                speed_max_m_s=float(h.speed_max_m_s.max()), layer_span_max_mm=float(h.layer_span_max_mm.max()),
                periodic_dx_max_mm=float(h.periodic_dx_max_mm.max()),
                top_settlement_endpoint_delta_mm=float(h.top_settlement_mm.iloc[-1]-h.top_settlement_mm.iloc[0]),
                bottom_settlement_endpoint_delta_mm=float(h.bottom_settlement_mm.iloc[-1]-h.bottom_settlement_mm.iloc[0]))


def final_summary(profile, hist):
    first = profile[profile.part == 0].sort_values('layer')
    last = profile[profile.part == 60].sort_values('layer')
    bottom, row = last.iloc[0], hist.iloc[-1]
    keys = ['part', 'time_s', 'saved_step', 'natural_step', 'bottom_p_pa', 'bottom_p0_pa', 'bottom_q_native_pa',
            'bottom_q_current_pa', 'bottom_reference_shift_pa', 'bottom_sigma_zz_pa', 'bottom_total_sigma_zz_pa',
            'top_settlement_mm', 'bottom_settlement_mm', 'top_minus_bottom_settlement_mm',
            'layer_mean_r_rms_pa', 'layer_mean_r_max_abs_pa', 'speed_max_m_s']
    final = {k: float(row[k]) for k in keys}
    final['bottom_effective_stress_pa'] = {k: float(bottom[k]) for k in SIGMA}
    changes = {}
    for key in ['pressure_pa', 'porepress0_pa', 'excess_native_pa', 'total_sigma_zz_pa', 'settlement_mm', 'rho_kg_m3', 'r_native_pa'] + SIGMA:
        delta = last[key].to_numpy()-first[key].to_numpy()
        changes[key] = dict(rms=float(np.sqrt(np.mean(delta**2))), max_abs=float(np.max(np.abs(delta))),
                            mean=float(np.mean(delta)), bottom=float(delta[0]), top=float(delta[-1]))
    comparisons = {}
    for prefix in ['ideal_H1', 'ideal_HD']:
        errors = {}
        for observed, reference in [('pressure_pa', 'p_pa'), ('excess_native_pa', 'q_pa'),
                                    ('total_sigma_zz_pa', 'total_sigma_zz_pa'), ('settlement_mm', 'settlement_mm')]:
            delta = last[observed].to_numpy()-last[prefix+'_'+reference].to_numpy()
            errors[observed] = dict(rms=float(np.sqrt(np.mean(delta**2))), max_abs=float(np.max(np.abs(delta))),
                                    bottom=float(delta[0]), top=float(delta[-1]))
        comparisons[prefix] = dict(diagnostic_only=True, all_100_material_layers_including_drained_top=True, errors=errors)
    return final, changes, comparisons


def native_endpoints(worker, job, receipt, profile):
    initial = worker.current.native(worker.OUTPUTS / job['name'], 0)
    evidence = []
    for part in [0, 60]:
        a = initial if part == 0 else worker.current.native(worker.OUTPUTS / job['name'], part)
        measured = worker.measure(a, initial, part, job, worker.clock_table(job['dt'], job['steps']))
        row = receipt['rows'][part]
        assert measured['time_s'] == row['time_s'] and measured['saved_step'] == row['saved_step']
        assert np.array_equal(a.id.to_numpy(), np.arange(1040))
        # Reproduce all stored layer columns directly from fixed native material IDs.
        direct = pd.DataFrame(worker.profiles(a, initial, part)).sort_values('layer')
        saved = profile[profile.part == part].sort_values('layer')
        np.testing.assert_allclose(direct.to_numpy(), saved[direct.columns].to_numpy(), rtol=1e-12, atol=1e-10)
        soil = a[a.is_boundary == 0].copy()
        soil['material_layer'] = (soil.id.astype(int)-40) % 100
        variation = {key: float(soil.groupby('material_layer')[key].agg(lambda x: x.max()-x.min()).max()) for key in ['pressure'] + SIGMA}
        evidence.append(dict(part=part, actual_time_s=measured['time_s'], saved_step=measured['saved_step'],
                             ids_0_to_1039_exact=True, original_single_frame_safety_passed=True,
                             maximum_within_material_layer_range=variation))
    return evidence


def figures(profiles, histories, paths):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 9, 'axes.grid': True, 'grid.alpha': .25})
    fig, axes = plt.subplots(2, 3, figsize=(13, 8), constrained_layout=True)
    colors = {'on': 'tab:blue', 'off': 'tab:orange'}
    for label, a in profiles.items():
        b = a[a.part == 60].sort_values('layer'); z = b.z0_m
        for col, style, name in [('pressure_pa', '-', 'p'), ('porepress0_pa', ':', 'p0')]:
            axes[0, 0].plot(b[col]/1000, z, style, color=colors[label], label=label+' '+name)
        for col, style, name in [('excess_native_pa', '-', 'native q'), ('q_current_pa', '--', 'current q')]:
            axes[0, 1].plot(b[col]/1000, z, style, color=colors[label], label=label+' '+name)
        axes[0, 2].plot(b.sigma_zz/1000, z, color=colors[label], label=label+" effective zz")
        axes[0, 2].plot(b.total_sigma_zz_pa/1000, z, '--', color=colors[label], label=label+' total zz')
        axes[1, 0].plot(b.r_native_pa, z, color=colors[label], label=label)
        axes[1, 1].plot(b.settlement_mm, z, color=colors[label], label=label)
        axes[1, 2].plot(b.reference_shift_pa, z, color=colors[label], label=label)
    b = next(iter(profiles.values())); b = b[b.part == 60].sort_values('layer')
    for prefix, style in [('ideal_H1', '-.'), ('ideal_HD', ':')]:
        for ax, column, scale in [(axes[0, 0], 'p_pa', 1000), (axes[0, 1], 'q_pa', 1000), (axes[1, 1], 'settlement_mm', 1)]:
            ax.plot(b[prefix+'_'+column]/scale, b.z0_m, style, color='black', label=prefix)
        axes[0, 2].plot(b[prefix+'_total_sigma_zz_pa']/1000, b.z0_m, style, color='black', label=prefix+' total')
    titles = ['Total pressure and fixed p0 [kPa]', 'Native/current hydro excess [kPa]', 'Effective and total zz stress [kPa]',
              'R = native q + Mf trace(sigma)/(3K) [Pa]', 'Material downward settlement [mm]', 'Current hydro minus fixed p0 [Pa]']
    for ax, title in zip(axes.flat, titles):
        ax.set(title=title, ylabel='Initial material z [m]'); ax.legend(fontsize=7)
    fig.suptitle('Stage1 final actual saved states; ideal curves are diagnostics, not acceptance gates')
    fig.savefig(paths['profile_png'], dpi=180); plt.close(fig)
    fig, axes = plt.subplots(3, 2, figsize=(12, 10), constrained_layout=True)
    for label, h in histories.items():
        t, color = h.time_s, colors[label]
        for col, style, name in [('bottom_p_pa', '-', 'p'), ('bottom_p0_pa', ':', 'p0'), ('bottom_q_native_pa', '--', 'native q')]:
            axes[0, 0].plot(t, h[col]/1000, style, color=color, label=label+' '+name)
        for col, style, name in [('top_settlement_mm', '-', 'top'), ('bottom_settlement_mm', '--', 'bottom')]:
            axes[0, 1].plot(t, h[col], style, color=color, label=label+' '+name)
        axes[1, 0].plot(t, h.speed_max_m_s, color=color, label=label)
        axes[1, 1].plot(t, h.bottom_sigma_zz_pa/1000, color=color, label=label+' effective')
        axes[1, 1].plot(t, h.bottom_total_sigma_zz_pa/1000, '--', color=color, label=label+' total')
        axes[2, 0].plot(t, h.layer_mean_r_rms_pa, color=color, label=label+' layer-mean RMS')
        axes[2, 0].plot(t, h.layer_mean_r_max_abs_pa, '--', color=color, label=label+' layer-mean max')
        axes[2, 1].plot(t, h.layer_span_max_mm, color=color, label=label+' max layer z span')
        axes[2, 1].plot(t, h.periodic_dx_max_mm, '--', color=color, label=label+' periodic dx')
    for ax, title in zip(axes.flat, ['Bottom material pressure [kPa]', 'Top/bottom material settlement [mm]', 'Maximum native soil speed [m/s]',
                                    'Bottom material zz stress [kPa]', 'Undrained-relation diagnostic R [Pa]', 'Native geometric layer variation [mm]']):
        ax.set(title=title, xlabel='Actual saved time [s]'); ax.legend(fontsize=7)
    fig.suptitle('All 61 native saves per run; no interpolation or smoothing')
    fig.savefig(paths['history_png'], dpi=180); plt.close(fig)


def review(tag):
    worker = importlib.import_module(SEQUENCE)
    read, bound, verify = worker.read, worker.bound, worker.verify
    paths = {key: TESTS/folder/(tag+suffix) for key, folder, suffix in [
        ('check', 'logs', '.check.json'), ('note', 'notes', '.md'), ('profile_png', 'figures', '_profiles.png'),
        ('history_png', 'figures', '_history.png'), ('profile_csv', 'figures', '_profiles.csv'), ('history_csv', 'figures', '_history.csv')]}
    assert not any(p.exists() for p in paths.values()), 'Fresh analysis tag required; retained files are never overwritten'
    checkpath = TESTS/'logs'/(SEQUENCE+'.check.json'); check = read(checkpath)
    assert check['passed'] and len(check['jobs']) == 4 and not check['held_jobs']
    verify([check['run']]+check['jobs']); run = read(check['run']['path'])
    assert run['status'] == 'stage1_completed_pending_equilibrium_and_reference_review' and run['jobs'] == check['jobs']
    verify([run['prepared']]); prepared = read(run['prepared']['path'])
    assert [j['suffix'] for j in prepared['jobs']] == ['coarse', 'half', 'on', 'off']
    records = [bound(checkpath), check['run'], run['prepared'], bound(__file__)] + check['jobs']
    # Verify direct current helper/source bindings, not recursively unrelated historical run graphs.
    critical = [r for r in prepared['inputs'] if Path(r['path']).suffix.lower() in ['.py', '.cpp', '.cu', '.h']]
    reader = next(r for r in prepared['inputs'] if Path(r['path']).resolve() == Path(worker.event.READER).resolve())
    records += critical + [reader]
    verify(records)
    profiles, histories, results, common = {}, {}, {}, None
    for job, receipt_record in zip(prepared['jobs'], check['jobs']):
        receipt = read(receipt_record['path']); assert receipt['passed'] and receipt['error'] is None and receipt['failed_part'] is None
        verify([receipt['sealed_completion']]); done = read(receipt['sealed_completion']['path'])
        assert done['exit_code'] == 0 and done['solver_finished'] and done['owned_exited'] and not done['surviving_owned']
        assert len(receipt['rows']) == job['frames'] and all(r['exit_code'] == 0 for r in receipt['reader_exits'])
        assert all(r['passed'] for r in receipt['pairs']) and done['program'] == job['program']
        job_records = [receipt['sealed_completion'], job['program'], job['config'], job['bat']] + job['runtime'] + done['outputs'] + receipt['artifacts']
        verify(job_records); records += job_records
        if job['suffix'] not in ['on', 'off']: continue
        label, rows = job['suffix'], receipt['rows']
        assert len(rows) == 61 and [r['part'] for r in rows] == list(range(61)) and rows[-1]['natural_step'] == 300001
        clock = worker.clock_table(job['dt'], job['steps'])
        assert all(abs(r['time_s']-clock[r['natural_step']]) <= 1e-14 and r['saved_step'] == (r['natural_step']-1 if r['part'] else 0) for r in rows)
        artifact = next(r for r in receipt['artifacts'] if Path(r['path']).name == job['name']+'_profiles.csv')
        verify([artifact, job['config']]); p = parameters(job['config']['path'])
        if common is None: common = p
        else: assert p == common
        frame = pd.read_csv(artifact['path'], float_precision='round_trip')
        a, hd = enrich(frame, rows, p, label); h = history(a, rows, label)
        final, changes, ideal_comparisons = final_summary(a, h)
        results[label] = dict(final_actual_time_s=rows[-1]['time_s'], native_frames=61, material_layers=100,
                              initial_drained_node_plane_m=hd, last_window=last_window(a, h),
                              final_native=final, initial_to_final_layer_changes=changes, final_vs_ideal=ideal_comparisons,
                              independently_redecoded=native_endpoints(worker, job, receipt, frame))
        profiles[label], histories[label] = a, h
    records = worker.unique(records); verify(records)
    pd.concat(profiles.values(), ignore_index=True).to_csv(paths['profile_csv'], index=False)
    pd.concat(histories.values(), ignore_index=True).to_csv(paths['history_csv'], index=False)
    figures(profiles, histories, paths)
    ref = ideal(np.array([0., .005, .995, 1.]), common['H'], common)
    note = '# Stage1 ON/OFF equilibrium diagnostic\n\n'
    note += 'Both sealed 61-frame runs and all four prerequisite jobs passed their existing execution/safety gates. This review adds no physical acceptance gate.\n\n'
    note += 'Reference: M=K+4G/3, Mf=Kw/n, B=Mf/(M+Mf); ph=rho_w*g*(H-z), q=B*(rho-rho_w)*g*(H-z), sigma_zz=-(1-B)*(rho-rho_w)*g*(H-z). '
    note += 'R=q_native+Mf*trace(sigma)/(3K). H1 and HD curves use separate explicitly labelled reference planes.\n\n'
    note += '| Job | Actual final t [s] | Bottom p / native q [kPa] | Bottom effective zz [Pa] | Bottom total zz [kPa] | Top / bottom s [mm] | Max speed [m/s] |\n'
    note += '| --- | ---: | ---: | ---: | ---: | ---: | ---: |\n'
    for label, result in results.items():
        f = result['final_native']
        note += (f"| {label} | {f['time_s']:.12g} | {f['bottom_p_pa']/1000:.9g} / {f['bottom_q_native_pa']/1000:.9g} | "
                 f"{f['bottom_sigma_zz_pa']:.9g} | {f['bottom_total_sigma_zz_pa']/1000:.9g} | "
                 f"{f['top_settlement_mm']:.9g} / {f['bottom_settlement_mm']:.9g} | {f['speed_max_m_s']:.9g} |\n")
    note += '\n'
    for label, result in results.items():
        window = result['last_window']
        note += (f"{label}: final actual time {result['final_actual_time_s']:.17g} s; HD={result['initial_drained_node_plane_m']:.17g} m. "
                 f"Last-window {window['actual_start_s']:.17g}..{window['actual_end_s']:.17g} s, {window['samples']} samples; "
                 f"max speed {window['speed_max_m_s']:.9g} m/s; maximum layer pressure endpoint drift "
                 f"{window['maximum_absolute_layer_endpoint_drift']['pressure_pa']:.9g} Pa; final layer-mean R RMS / max "
                 f"{result['final_native']['layer_mean_r_rms_pa']:.9g} / {result['final_native']['layer_mean_r_max_abs_pa']:.9g} Pa. "
                 'Initial/final changes and both ideal-reference RMS/max errors are diagnostic JSON metrics, without pass thresholds.\n\n')
    note += '\n'.join('- '+s for s in LIMITATIONS)+'\n\n'
    note += 'Next decision remains a physical review of late drift, stress/weight balance and the chosen handoff state; only then a separate Scenario2 interoperability test. No automatic solver, restart or formal run is launched.\n'
    with paths['note'].open('x', encoding='utf8') as stream: stream.write(note)
    verify(records)
    result = dict(analysis_checks_passed=True, original_single_run_safety_passed=True, inputs=records, parameters=common,
                  ideal_H1_sample_z_m=[0., .005, .995, 1.], ideal_H1_samples={k: v.tolist() for k, v in ref.items()},
                  jobs=results, limitations=LIMITATIONS, artifacts=[bound(p) for k, p in paths.items() if k != 'check'],
                  solver_started=False, production_changed=False, physical_acceptance=False, restart_admitted=False,
                  automatic_full_consolidation_admitted=False, figures_require_visual_review=True)
    worker.seal(paths['check'], result)
    return dict(check=str(paths['check']), analysis_checks_passed=True, physical_acceptance=False)


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8'))
    p = dict(K=2e6/(3*.4), G=2e6/2.6, rho=2100., rho_w=1000., g=9.81)
    p.update(M=p['K']+4*p['G']/3, Mf=2e8/.3); p['B'] = p['Mf']/(p['M']+p['Mf'])
    a = ideal(np.array([0., 1.]), 1., p)
    assert abs(a['p_pa'][0]-20557.596245929897) < 1e-8 and a['p_pa'][1] == 0
    assert np.max(np.abs(a['sigma_zz_pa']-a['p_pa']-a['total_sigma_zz_pa'])) < 1e-8
    return dict(passed=True, files_written=False, solver_started=False, native_reader_started=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--selftest', action='store_true'); group.add_argument('--review', action='store_true')
    parser.add_argument('--tag', default=TAG)
    args = parser.parse_args()
    assert args.tag and Path(args.tag).name == args.tag and args.tag.replace('_', '').isalnum()
    if args.selftest: print(json.dumps(selftest()))
    elif args.review: print(json.dumps(review(args.tag)))
    else: parser.print_help()
