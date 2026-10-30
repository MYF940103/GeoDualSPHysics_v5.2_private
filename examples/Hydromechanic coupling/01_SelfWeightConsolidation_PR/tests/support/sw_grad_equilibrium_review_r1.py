"""Offline G0/G1, both ShepardOFF, Stage1 diagnostics; default help, no solver."""
import argparse
import ast
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import sw_stage1_equilibrium_review_r1 as base

TESTS = Path(__file__).resolve().parents[1]
TAG = 'sw_grad_equilibrium_review_r1'
LABELS = ['G0_ShepardOFF', 'G1_ShepardOFF']


def relative_material_displacements(a):
    final = a[a.part == 60].sort_values('layer').set_index('layer'); result = []
    for lower, upper in [(0, 99), (1, 98), (2, 97), (10, 89)]:
        row = dict(lower_material_layer=lower, upper_material_layer=upper,
                   observed_relative_settlement_mm=float(final.loc[upper, 'settlement_mm']-final.loc[lower, 'settlement_mm']))
        for prefix in ['ideal_H1', 'ideal_HD']:
            ref = float(final.loc[upper, prefix+'_settlement_mm']-final.loc[lower, prefix+'_settlement_mm'])
            row[prefix+'_relative_mm'] = ref
            row[prefix+'_error_percent'] = 100*(row['observed_relative_settlement_mm']/ref-1)
        result.append(row)
    return result


def plots(profiles, histories, paths):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 9, 'axes.grid': True, 'grid.alpha': .25})
    colors = dict(zip(LABELS, ['tab:orange', 'tab:blue']))
    fig, axes = plt.subplots(2, 3, figsize=(13, 8), constrained_layout=True)
    for label, a in profiles.items():
        b = a[a.part == 60].sort_values('layer'); z, color = b.z0_m, colors[label]
        axes[0, 0].plot(b.pressure_pa/1000, z, color=color, label=label+' p')
        axes[0, 0].plot(b.porepress0_pa/1000, z, ':', color=color, label=label+' p0')
        axes[0, 1].plot(b.excess_native_pa/1000, z, color=color, label=label+' native q')
        axes[0, 1].plot(b.q_current_pa/1000, z, '--', color=color, label=label+' current q')
        axes[0, 2].plot(b.sigma_zz, z, color=color, label=label)
        axes[1, 0].plot(b.total_sigma_zz_pa/1000, z, color=color, label=label)
        axes[1, 1].plot(b.settlement_mm, z, color=color, label=label)
        axes[1, 2].plot(b.r_native_pa/1000, z, color=color, label=label+' all layers')
        interior = b.layer < 99
        axes[1, 2].plot(b.r_native_pa[interior]/1000, z[interior], '--', color=color, label=label+' without top')
    for prefix, style in [('ideal_H1', '-.'), ('ideal_HD', ':')]:
        for index, key, scale in [(0, 'p_pa', 1000), (1, 'q_pa', 1000), (2, 'sigma_zz_pa', 1),
                                  (3, 'total_sigma_zz_pa', 1000), (4, 'settlement_mm', 1)]:
            axes.flat[index].plot(b[prefix+'_'+key]/scale, z, style, color='black', label=prefix)
    titles = ['Total p and fixed p0 [kPa]', 'Native/current hydro excess [kPa]', 'Effective sigma zz [Pa]',
              'Total sigma zz [kPa]', 'Downward material settlement [mm]', 'R = q + Mf trace(sigma)/(3K) [kPa]']
    for ax, title in zip(axes.flat, titles):
        ax.set(title=title, ylabel='Initial material z [m]'); ax.legend(fontsize=6)
    fig.suptitle('Final actual saved states: G0/G1, both ShepardOFF; ideal curves are diagnostics')
    fig.savefig(paths['profiles_png'], dpi=180); plt.close(fig)
    fig, axes = plt.subplots(3, 2, figsize=(12, 10), constrained_layout=True)
    r_detail = axes[1, 1].inset_axes([.40, .43, .57, .52])
    for label, h in histories.items():
        t, color = h.time_s, colors[label]
        for key, style, name in [('bottom_p_pa', '-', 'p'), ('bottom_q_native_pa', '--', 'q')]:
            axes[0, 0].plot(t, h[key]/1000, style, color=color, label=label+' '+name)
        axes[0, 1].plot(t, h.top_settlement_mm, color=color, label=label+' top')
        axes[0, 1].plot(t, h.bottom_settlement_mm, '--', color=color, label=label+' bottom')
        axes[1, 0].plot(t, h.speed_max_m_s, color=color, label=label)
        axes[1, 1].plot(t, h.layer_mean_r_rms_pa, color=color, label=label+' all-layer mean RMS')
        axes[1, 1].plot(t, h.native_990_r_rms_pa, '--', color=color, label=label+' native 990 RMS')
        r_detail.plot(t, h.native_990_r_rms_pa, color=color, label=label)
        late = h.time_s >= .25-1e-14
        axes[2, 0].plot(t[late], h.bottom_p_pa[late]-h.bottom_p_pa[late].iloc[0], color=color, label=label)
        axes[2, 1].plot(t[late], h.top_settlement_mm[late]-h.top_settlement_mm[late].iloc[0], color=color, label=label+' top')
        axes[2, 1].plot(t[late], h.bottom_settlement_mm[late]-h.bottom_settlement_mm[late].iloc[0], '--', color=color, label=label+' bottom')
    for ax, title in zip(axes.flat, ['Bottom material pressure [kPa]', 'Material settlement [mm]', 'Maximum native soil speed [m/s]',
                                    'All-layer / non-top R RMS [Pa]', 'Late bottom pressure change [Pa]', 'Late material settlement change [mm]']):
        ax.set(title=title, xlabel='Actual saved time [s]'); ax.legend(fontsize=6)
    r_detail.set(title='Native non-top 990 only [Pa]', xlabel='Actual time [s]')
    r_detail.tick_params(labelsize=6); r_detail.title.set_fontsize(7); r_detail.xaxis.label.set_fontsize(6)
    fig.suptitle('All 61 histories; late panels start at first actual saved time >= .25 s; no fits')
    fig.savefig(paths['history_png'], dpi=180); plt.close(fig)


def review(tag):
    import sw_grad_stage1_r1 as worker
    read, bound, verify = worker.read, worker.bound, worker.verify
    paths = {key: TESTS/folder/(tag+suffix) for key, folder, suffix in [
        ('check', 'logs', '.check.json'), ('note', 'notes', '.md'), ('profiles_png', 'figures', '_profiles.png'),
        ('history_png', 'figures', '_history.png'), ('profiles_csv', 'figures', '_profiles.csv'), ('history_csv', 'figures', '_history.csv')]}
    assert not any(p.exists() for p in paths.values()), 'Fresh analysis tag required'
    check = read(worker.CHECK)
    assert check['passed'] and len(check['jobs']) == 1
    records = [bound(worker.CHECK), check['run'], check['analysis']] + check['jobs']; verify(records)
    run, analysis = read(check['run']['path']), read(check['analysis']['path'])
    assert run['status'] == 'g1_shepard_off_stage1_complete_pending_root_review' and analysis['passed']
    assert analysis['execution_receipt'] == check['jobs'][0] and run['jobs'] == check['jobs']
    verify([run['prepared']]); prepared = read(run['prepared']['path'])
    oldprepared = read(worker.stage.PREP); oldcheck = read(worker.stage.CHECK)
    assert oldcheck['passed'] and len(oldcheck['jobs']) == 4
    g0 = next(j for j in oldprepared['jobs'] if j['suffix'] == 'off'); g1 = prepared['job']
    assert g0['program'] == g1['program'] and g0['runtime'] == g1['runtime']
    assert prepared['g0']['receipt'] in oldcheck['jobs']
    records += [run['prepared'], bound(worker.stage.PREP), bound(worker.stage.CHECK), oldcheck['run'], bound(__file__), bound(base.__file__)]
    critical = [r for r in prepared['inputs'] if Path(r['path']).suffix.lower() in ['.py', '.cpp', '.cu', '.h']]
    reader = next(r for r in prepared['inputs'] if Path(r['path']).resolve() == Path(worker.event.READER).resolve())
    records += critical + [reader] + analysis['artifacts']; verify(records)
    profiles, histories, results, trees, common = {}, {}, {}, [], None
    pairs_record = next(r for r in analysis['artifacts'] if Path(r['path']).name.endswith('_g1_g0_pairs.csv'))
    pair_data = pd.read_csv(pairs_record['path'], float_precision='round_trip')
    assert len(pair_data) == 61 and np.array_equal(pair_data.part, np.arange(61))
    assert pair_data.time_eligible.eq(True).all() and pair_data.gate_applied.eq(False).all()
    for label, job, receipt_record in [(LABELS[0], g0, prepared['g0']['receipt']), (LABELS[1], g1, check['jobs'][0])]:
        verify([receipt_record]); receipt = read(receipt_record['path']); assert receipt['passed'] and receipt['error'] is None
        verify([receipt['sealed_completion']]); done = read(receipt['sealed_completion']['path'])
        assert done['exit_code'] == 0 and done['solver_finished'] and done['owned_exited'] and not done['surviving_owned']
        assert len(receipt['rows']) == 61 and [r['part'] for r in receipt['rows']] == list(range(61))
        assert all(r['exit_code'] == 0 for r in receipt['reader_exits']) and all(r['passed'] for r in receipt['pairs'])
        job_records = [receipt['sealed_completion'], job['config'], job['bat'], job['program']] + job['runtime'] + done['outputs'] + receipt['artifacts']
        verify(job_records); records += [receipt_record] + job_records
        config = Path(job['config']['path']); trees.append(ET.parse(config))
        text = (worker.OUTPUTS/job['name']/'Run.out').read_text(errors='replace')
        assert 'PoreShepardRegularization="Disabled"' in text and 'PoreCompressionGradCorr="KernelGradient"' in text
        assert ('SoilStressRateGradCorr="'+('None' if label == LABELS[0] else 'KernelGradient')+'"') in text
        p = base.parameters(config)
        assert {key: p[key] for key in ['K', 'Mf']} == prepared['parameters']
        if common is None: common = p
        else: assert p == common
        clock = worker.stage.clock_table(job['dt'], job['steps']); rows = receipt['rows']
        assert rows[-1]['natural_step'] == job['steps'] == 300001
        assert np.all(np.diff([r['natural_step'] for r in rows]) > 0) and np.all(np.diff([r['time_s'] for r in rows]) > 0)
        assert all(abs(r['time_s']-clock[r['natural_step']]) <= 1e-14 and r['saved_step'] == (r['natural_step']-1 if r['part'] else 0) for r in rows)
        source = next(r for r in receipt['artifacts'] if Path(r['path']).name == job['name']+'_profiles.csv')
        raw = pd.read_csv(source['path'], float_precision='round_trip')  # Numeric execution CSV, never the string-containing profiles_r CSV.
        a, hd = base.enrich(raw, rows, p, label); h = base.history(a, rows, label)
        assert np.array_equal(h.time_s, pair_data.reference_time_s if label == LABELS[0] else pair_data.time_s)
        h['native_990_r_rms_pa'] = pair_data['reference_r_excluding_top_rms_pa' if label == LABELS[0] else 'r_excluding_top_rms_pa'].to_numpy()
        final, changes, errors = base.final_summary(a, h)
        results[label] = dict(final_native=final, initial_to_final_layer_changes=changes, final_vs_ideal=errors,
            last_window=base.last_window(a, h), initial_drained_node_plane_m=hd, original_complete_profiles=source,
            relative_material_displacements=relative_material_displacements(a), final_native_990_r_rms_pa=float(h.native_990_r_rms_pa.iloc[-1]),
            independently_redecoded=base.native_endpoints(worker.stage, job, receipt, raw))
        profiles[label], histories[label] = a, h
    signature = lambda tree: [(e.tag, sorted(e.attrib.items())) for e in tree.iter() if e.get('key') != 'SoilStressRateGradCorr']
    assert signature(trees[0]) == signature(trees[1])
    assert trees[0].find('.//PoreShepardRegularization').get('value') == trees[1].find('.//PoreShepardRegularization').get('value') == '0'
    flags = [t.findall('.//parameter[@key="SoilStressRateGradCorr"]') for t in trees]
    assert len(flags[0]) <= 1 and (not flags[0] or flags[0][0].get('value') == '0')
    assert len(flags[1]) == 1 and flags[1][0].get('value') == '1'
    assert np.array_equal(histories[LABELS[0]].time_s, histories[LABELS[1]].time_s)
    assert np.array_equal(histories[LABELS[0]].saved_step, histories[LABELS[1]].saved_step)
    records = worker.unique(records); verify(records)
    final_table = pd.concat([a[a.part == 60] for a in profiles.values()], ignore_index=True)
    history_table = pd.concat(histories.values(), ignore_index=True)
    assert len(final_table) == 200 and len(history_table) == 122
    final_table.to_csv(paths['profiles_csv'], index=False); history_table.to_csv(paths['history_csv'], index=False)
    plots(profiles, histories, paths)
    note = '# G0/G1 Stage1 diagnostic, both ShepardOFF\n\n'
    note += 'All 61 actual matched frames per variant passed their existing sealed execution/safety checks. Four native first/final states were independently decoded. No new physical gate is introduced.\n\n'
    note += '| Variant | Bottom p / q [kPa] | Top / bottom s [mm] | All-layer R RMS [Pa] | Native non-top R RMS [Pa] |\n| --- | ---: | ---: | ---: | ---: |\n'
    for label, r in results.items():
        f = r['final_native']
        note += f"| {label} | {f['bottom_p_pa']/1000:.9g} / {f['bottom_q_native_pa']/1000:.9g} | {f['top_settlement_mm']:.9g} / {f['bottom_settlement_mm']:.9g} | {f['layer_mean_r_rms_pa']:.9g} | {r['final_native_990_r_rms_pa']:.9g} |\n"
    note += '\nH1/HD errors and multiple material endpoint pairs are diagnostics, not tuned references or 5-Pa theory gates. All-layer R RMS uses 100 layer means; non-top R RMS is the sealed direct 990-particle metric. The excluded top layer is still plotted and retained in CSV. Complete 6100-row source profiles remain linked in JSON, not duplicated. No smoothing, clipping or interpolation is used.\n\n'
    note += '\n'.join('- '+x.replace('not ON/OFF or ideal-theory differences', 'not gradient-option or ideal-theory differences')
                      for x in base.LIMITATIONS if 'Shepard' not in x and '61x100' not in x)+'\n'
    note += '\nBoth runs disable Shepard; this option comparison changes only stress-rate gradient correction. No solver, restart, automatic full-consolidation or formal acceptance is admitted. The two PNGs still require visual inspection.\n'
    with paths['note'].open('x', encoding='utf8') as stream: stream.write(note)
    verify(records)
    worker.seal(paths['check'], dict(analysis_checks_passed=True, original_single_run_safety_passed=True, inputs=records, parameters=common, jobs=results,
        matched_frames=61, independent_native_frames=4, source_profile_rows_retained_each=6100, output_profile_rows=200, output_history_rows=122,
        option_comparison_is_descriptive=True, original_safety_inherited_and_endpoint_rechecked=True, physical_acceptance=False,
        restart_admitted=False, automatic_full_consolidation_admitted=False, solver_started=False, production_changed=False,
        figures_require_visual_review=True, artifacts=[bound(p) for k, p in paths.items() if k != 'check']))
    return dict(check=str(paths['check']), analysis_checks_passed=True, physical_acceptance=False)


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8')); base.selftest()
    dummy = pd.DataFrame(dict(part=60, layer=np.arange(100), settlement_mm=np.arange(100.)**2,
        ideal_H1_settlement_mm=np.arange(100.)**2, ideal_HD_settlement_mm=np.arange(100.)**2))
    result = relative_material_displacements(dummy)
    assert len(result) == 4 and all(r['ideal_H1_error_percent'] == r['ideal_HD_error_percent'] == 0 for r in result)
    return dict(passed=True, files_written=False, native_reader_started=False, solver_started=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); group = parser.add_mutually_exclusive_group()
    group.add_argument('--selftest', action='store_true'); group.add_argument('--review', action='store_true'); parser.add_argument('--tag', default=TAG)
    args = parser.parse_args(); assert args.tag and Path(args.tag).name == args.tag and args.tag.replace('_', '').isalnum()
    if args.selftest: print(json.dumps(selftest()))
    elif args.review: print(json.dumps(review(args.tag)))
    else: parser.print_help()
