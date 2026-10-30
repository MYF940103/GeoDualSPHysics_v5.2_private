"""Offline SPR0/SPR1 review: both G1/ShepardOFF; no solver or automatic admission."""
import argparse
import ast
from pathlib import Path
import json
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import sw_spr_stage1_r1 as worker
import sw_stage1_equilibrium_review_r1 as base
from sw_grad_equilibrium_review_r1 import relative_material_displacements

TESTS, TAG = worker.TESTS, 'sw_spr_equilibrium_review_r1'
LABELS = [worker.REFERENCE, worker.VARIANT]


def staggering(a):
    """Descriptive adjacent-layer second difference, never a physical gate or a smoothed plot."""
    b = a[a.part == 60].sort_values('layer'); result = {}
    for key in ['settlement_mm', 'pressure_pa', 'total_sigma_zz_pa']:
        v = b[key].to_numpy(); d = v[1:-1]-.5*(v[:-2]+v[2:])
        result[key] = dict(interior_1_to_98_rms=float(np.sqrt(np.mean(d*d))),
                           bulk_10_to_89_rms=float(np.sqrt(np.mean(d[9:89]**2))))
    return dict(formula='f_i - (f_(i-1)+f_(i+1))/2', diagnostic_only=True, metrics=result)


def figures(profiles, histories, paths):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 9, 'axes.grid': True, 'grid.alpha': .25})
    colors, names = ['tab:orange', 'tab:blue'], ['SPR0 (G1)', 'SPR1 (G1)']
    fig, axes = plt.subplots(2, 3, figsize=(13, 8), constrained_layout=True)
    for label, color, name in zip(LABELS, colors, names):
        b = profiles[label].query('part == 60').sort_values('layer'); z = b.z0_m
        for index, key, scale in [(0, 'pressure_pa', 1000), (1, 'excess_native_pa', 1000),
                                   (2, 'sigma_zz', 1), (3, 'total_sigma_zz_pa', 1000),
                                   (4, 'settlement_mm', 1), (5, 'r_native_pa', 1)]:
            axes.flat[index].plot(b[key]/scale, z, color=color, label=name)
        axes[0, 0].plot(b.porepress0_pa/1000, z, ':', color=color, label=name+' fixed p0')
        axes[0, 1].plot(b.q_current_pa/1000, z, '--', color=color, label=name+' current hydro excess')
    for prefix, style in [('ideal_H1', '-.'), ('ideal_HD', ':')]:
        for index, key, scale in [(0, 'p_pa', 1000), (1, 'q_pa', 1000), (2, 'sigma_zz_pa', 1),
                                   (3, 'total_sigma_zz_pa', 1000), (4, 'settlement_mm', 1)]:
            axes.flat[index].plot(b[prefix+'_'+key]/scale, z, style, color='black', label=prefix)
    axes[1, 2].set_xscale('symlog', linthresh=1)
    titles = ['Total p / fixed p0 [kPa]', 'Native / current hydro excess [kPa]', 'Effective sigma zz [Pa]',
              'Total sigma zz [kPa]', 'Downward material settlement [mm]', 'All 100 layers R [Pa]; symlog, linear +/-1 Pa']
    for ax, title in zip(axes.flat, titles):
        ax.set(title=title, ylabel='Initial material z [m]'); ax.legend(fontsize=6)
    fig.suptitle('Final actual saved states; both G1/ShepardOFF; ideal curves are diagnostics')
    fig.savefig(paths['profiles_png'], dpi=180); plt.close(fig)
    fig, axes = plt.subplots(3, 2, figsize=(12, 10), constrained_layout=True)
    for label, color, name in zip(LABELS, colors, names):
        h = histories[label]; t = h.time_s
        axes[0, 0].plot(t, h.bottom_p_pa/1000, color=color, label=name+' p')
        axes[0, 0].plot(t, h.bottom_q_native_pa/1000, '--', color=color, label=name+' q')
        for key, style, title in [('top_settlement_mm', '-', 'top'), ('bottom_settlement_mm', '--', 'bottom')]:
            axes[0, 1].plot(t, h[key], style, color=color, label=name+' '+title)
        axes[1, 0].plot(t, h.speed_max_m_s, color=color, label=name)
        axes[1, 1].plot(t, h.native_990_r_rms_pa, color=color, label=name)
        late = h[h.time_s >= .25-1e-14]
        axes[2, 0].plot(late.time_s, late.bottom_p_pa-late.bottom_p_pa.iloc[0], color=color, label=name)
        for key, style, title in [('top_settlement_mm', '-', 'top'), ('bottom_settlement_mm', '--', 'bottom')]:
            axes[2, 1].plot(late.time_s, late[key]-late[key].iloc[0], style, color=color, label=name+' '+title)
    titles = ['Bottom material p / q [kPa]', 'Material downward settlement [mm]', 'Maximum native soil speed [m/s]',
              'Native non-top 990-particle R RMS [Pa]', 'Late bottom pressure change [Pa]', 'Late material settlement change [mm]']
    for ax, title in zip(axes.flat, titles):
        ax.set(title=title, xlabel='Actual saved time [s]'); ax.legend(fontsize=7)
    fig.suptitle('SPR0/SPR1, both G1/ShepardOFF; all 61 samples; no smoothing or interpolation')
    fig.savefig(paths['history_png'], dpi=180); plt.close(fig)


def review(tag):
    read, bound, verify = worker.read, worker.bound, worker.verify
    paths = {key: TESTS/folder/(tag+suffix) for key, folder, suffix in [
        ('check', 'logs', '.check.json'), ('profiles_png', 'figures', '_profiles.png'),
        ('history_png', 'figures', '_history.png'), ('profiles_csv', 'figures', '_profiles.csv'), ('history_csv', 'figures', '_history.csv')]}
    assert not any(p.exists() for p in paths.values()), 'New analysis tag required'
    check = read(worker.CHECK); assert check['passed'] and len(check['jobs']) == 1
    records = [bound(worker.CHECK), check['run'], check['analysis']]+check['jobs']; verify(records)
    run, analysis = read(check['run']['path']), read(check['analysis']['path'])
    assert run['status'] == 'spr1_g1_shepard_off_stage1_complete_pending_root_review' and analysis['passed']
    assert run['jobs'] == check['jobs'] and analysis['execution_receipt'] == check['jobs'][0]
    verify([run['prepared']]); prepared = read(run['prepared']['path']); verify(prepared['inputs'])
    oldcheck = read(worker.grad.CHECK); oldprep = read(worker.grad.PREP)
    assert oldcheck['passed'] and prepared['spr0']['receipt'] == oldcheck['jobs'][0]
    records += [run['prepared'], bound(worker.grad.CHECK), bound(worker.grad.PREP), bound(__file__), bound(base.__file__)]
    records += [bound(TESTS/'support/sw_grad_equilibrium_review_r1.py')]+prepared['inputs']+analysis['artifacts']
    pair_record = next(r for r in analysis['artifacts'] if Path(r['path']).name.endswith('_spr1_spr0_pairs.csv'))
    pair = pd.read_csv(pair_record['path'], float_precision='round_trip')
    assert len(pair) == 61 and np.array_equal(pair.part, np.arange(61))
    assert pair.time_eligible.all() and pair.same_saved_step.all() and not pair.gate_applied.any()
    profiles, histories, results, trees = {}, {}, {}, []
    for label, job, rr in [(LABELS[0], oldprep['job'], prepared['spr0']['receipt']), (LABELS[1], prepared['job'], check['jobs'][0])]:
        verify([rr]); r = read(rr['path']); assert r['passed'] and r['error'] is None and len(r['rows']) == 61
        verify([r['sealed_completion']]); done = read(r['sealed_completion']['path'])
        assert done['solver_finished'] and done['exit_code'] == 0 and done['owned_exited'] and not done['surviving_owned']
        records += [rr, r['sealed_completion'], job['config'], job['bat'], job['program']]+job['runtime']+done['outputs']+r['artifacts']
        verify(records); tree = ET.parse(job['config']['path']); trees.append(tree); p = base.parameters(job['config']['path'])
        assert {key: p[key] for key in ['K', 'Mf']} == prepared['parameters']
        text = (worker.OUTPUTS/job['name']/'Run.out').read_text(errors='replace')
        assert 'SoilStressRateGradCorr="KernelGradient"' in text and 'PoreShepardRegularization="Disabled"' in text
        clock = worker.stage.clock_table(job['dt'], job['steps']); rows = r['rows']
        assert rows[-1]['natural_step'] == job['steps'] == 300001
        assert all(abs(v['time_s']-clock[v['natural_step']]) <= 1e-14 for v in rows)
        src = next(v for v in r['artifacts'] if Path(v['path']).name == job['name']+'_profiles.csv')
        raw = pd.read_csv(src['path'], float_precision='round_trip'); a, hd = base.enrich(raw, rows, p, label); h = base.history(a, rows, label)
        assert np.array_equal(h.time_s, pair.reference_time_s if label == LABELS[0] else pair.time_s)
        h['native_990_r_rms_pa'] = pair['reference_r_excluding_top_rms_pa' if label == LABELS[0] else 'r_excluding_top_rms_pa'].to_numpy()
        final, changes, errors = base.final_summary(a, h)
        results[label] = dict(final_native=final, initial_to_final_changes=changes, final_vs_ideal=errors,
            last_window=base.last_window(a, h), material_relative_settlement=relative_material_displacements(a),
            staggering=staggering(a), final_native_990_r_rms_pa=float(h.native_990_r_rms_pa.iloc[-1]),
            original_profiles=src, independently_redecoded=base.native_endpoints(worker.stage, job, r, raw), initial_drained_plane_m=hd)
        profiles[label], histories[label] = a, h
    assert oldprep['job']['program'] == prepared['job']['program'] and oldprep['job']['runtime'] == prepared['job']['runtime']
    signature = lambda t: [(e.tag, sorted(e.attrib.items())) for e in t.iter() if e.get('key') != 'SoilBoundaryDerivativeSPR']
    assert signature(trees[0]) == signature(trees[1])
    assert not trees[0].findall('.//parameter[@key="SoilBoundaryDerivativeSPR"]')
    assert trees[1].find('.//parameter[@key="SoilBoundaryDerivativeSPR"]').get('value') == '1'
    assert np.array_equal(histories[LABELS[0]].time_s, histories[LABELS[1]].time_s)
    assert np.array_equal(histories[LABELS[0]].saved_step, histories[LABELS[1]].saved_step)
    pd.concat([a[a.part == 60] for a in profiles.values()]).to_csv(paths['profiles_csv'], index=False)
    pd.concat(histories.values()).to_csv(paths['history_csv'], index=False); figures(profiles, histories, paths)
    records = worker.unique(records); verify(records)
    worker.seal(paths['check'], dict(analysis_checks_passed=True, inputs=records, jobs=results, actual_matched_samples=61,
        independently_redecoded_frames=4, output_profile_rows=200, output_history_rows=122, physical_acceptance=False,
        new_half_validation=False, restart_admitted=False, solver_started=False, production_changed=False,
        reference_scope='Finite-Kw small-strain H1 and HD diagnostics, not a new theory gate or fitted height',
        R_scope='100 layer means including drained top versus direct 990 non-top particles; never conflated',
        figures_require_visual_inspection=True, artifacts=[bound(v) for key, v in paths.items() if key != 'check']))
    return dict(check=str(paths['check']), analysis_checks_passed=True, physical_acceptance=False)


def selftest():
    ast.parse(Path(__file__).read_text()); base.selftest()
    a = pd.DataFrame(dict(part=60, layer=np.arange(100), settlement_mm=np.arange(100.),
        pressure_pa=np.arange(100.), total_sigma_zz_pa=np.arange(100.)))
    assert all(v['interior_1_to_98_rms'] == v['bulk_10_to_89_rms'] == 0 for v in staggering(a)['metrics'].values())
    return dict(passed=True, files_written=False, native_reader_started=False, solver_started=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--selftest', action='store_true'); modes.add_argument('--review', action='store_true'); parser.add_argument('--tag', default=TAG)
    args = parser.parse_args(); assert args.tag and Path(args.tag).name == args.tag and args.tag.replace('_', '').isalnum()
    if args.selftest: print(json.dumps(selftest()))
    elif args.review: print(json.dumps(review(args.tag)))
    else: parser.print_help()
