"""Offline HG0/HG=.1 review; both SPR1/G1/ShepardOFF, no solver or admission."""
import argparse
import ast
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import sw_hg_stage1_r1 as worker
import sw_stage1_equilibrium_review_r1 as base
import sw_spr_equilibrium_review_r1 as prior

TESTS, TAG = worker.TESTS, 'sw_hg_equilibrium_review_r1'
LABELS = [worker.REFERENCE, worker.VARIANT]


def figures(profiles, histories, paths):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 9, 'axes.grid': True, 'grid.alpha': .25})
    colors, names = ['tab:orange', 'tab:blue'], ['HG0', 'HG xi=.1']
    fig, axes = plt.subplots(2, 3, figsize=(13, 8), constrained_layout=True)
    for label, color, name in zip(LABELS, colors, names):
        b = profiles[label].query('part == 60').sort_values('layer'); z = b.z0_m
        for index, key, scale in [(0, 'pressure_pa', 1000), (1, 'excess_native_pa', 1000),
                                   (2, 'sigma_zz', 1), (3, 'total_sigma_zz_pa', 1000), (4, 'settlement_mm', 1), (5, 'r_native_pa', 1)]:
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
    fig.suptitle('HG0 / HG xi=.1, both SPR1/G1/ShepardOFF; final actual save; ideal curves diagnostic only')
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
    fig.suptitle('HG0 / HG xi=.1, both SPR1/G1/ShepardOFF; all 61 samples; no smoothing or interpolation')
    fig.savefig(paths['history_png'], dpi=180); plt.close(fig)


def review(tag):
    read, bound, verify = worker.read, worker.bound, worker.verify
    paths = {key: TESTS/folder/(tag+suffix) for key, folder, suffix in [
        ('check', 'logs', '.check.json'), ('profiles_png', 'figures', '_profiles.png'),
        ('history_png', 'figures', '_history.png'), ('profiles_csv', 'figures', '_profiles.csv'), ('history_csv', 'figures', '_history.csv')]}
    assert not any(p.exists() for p in paths.values()), 'Fresh analysis tag required; retained outputs never overwritten'
    check = read(worker.CHECK); assert check['passed'] and len(check['jobs']) == 1
    records = [bound(worker.CHECK), check['run']]+check['jobs']; verify(records); run = read(check['run']['path'])
    assert run['status'] == 'hg_stage1_complete_pending_root_physical_review' and run['jobs'] == check['jobs']
    verify([run['prepared']]); prepared = read(run['prepared']['path']); verify(prepared['inputs'])
    assert check['source_program_attribution'] == prepared['source_program_attribution']
    assert not prepared['source_program_attribution']['exact_HG_source_at_build_time_proven']
    oldcheck = read(worker.retained.CHECK); oldprep = read(worker.retained.PREP)
    assert oldcheck['passed'] and prepared['hg0']['receipt'] == oldcheck['jobs'][0]
    records += [run['prepared'], bound(worker.retained.CHECK), bound(worker.retained.PREP), oldcheck['run'], oldcheck['analysis']]
    records += [bound(p) for p in [__file__, base.__file__, prior.__file__, TESTS/'support/sw_grad_equilibrium_review_r1.py']]+prepared['inputs']
    oldanalysis = read(oldcheck['analysis']['path']); assert oldanalysis['passed']; records += oldanalysis['artifacts']
    newreceipt = read(check['jobs'][0]['path']); pair = pd.DataFrame(newreceipt['pairs'])
    assert len(pair) == 61 and np.array_equal(pair.part, np.arange(61)) and pair.time_eligible.all() and pair.same_saved_step.all() and not pair.gate_applied.any()
    pair_record = next(r for r in newreceipt['artifacts'] if Path(r['path']).name.endswith('_hg1_hg0_pairs.csv')); verify([pair_record])
    saved_pair = pd.read_csv(pair_record['path'], float_precision='round_trip')
    for key in ['part', 'time_s', 'reference_time_s', 'saved_step', 'reference_saved_step', 'r_excluding_top_rms_pa', 'reference_r_excluding_top_rms_pa']:
        assert np.array_equal(saved_pair[key], pair[key])
    profiles, histories, results, trees, common = {}, {}, {}, [], None
    for label, job, rr in [(LABELS[0], oldprep['job'], prepared['hg0']['receipt']), (LABELS[1], prepared['job'], check['jobs'][0])]:
        verify([rr]); receipt = read(rr['path']); rows = receipt['rows']
        assert receipt['passed'] and not receipt.get('errors', []) and receipt.get('error') is None and receipt['failed_part'] is None
        assert len(rows) == 61 and [r['part'] for r in rows] == list(range(61)) and len(receipt['reader_exits']) == 61 and all(r['exit_code'] == 0 for r in receipt['reader_exits'])
        verify([receipt['sealed_completion']]); done = read(receipt['sealed_completion']['path'])
        assert done['solver_finished'] and done['exit_code'] == 0 and done['owned_exited'] and not done['surviving_owned'] and done['program'] == job['program']
        records += [rr, receipt['sealed_completion'], job['config'], job['bat'], job['program']]+job['runtime']+done['outputs']+receipt['artifacts']; verify(records)
        tree = ET.parse(job['config']['path']); trees.append(tree); p = base.parameters(job['config']['path'])
        assert {key: p[key] for key in ['K', 'Mf']} == prepared['parameters']
        if common is None: common = p
        else: assert common == p
        text = (worker.OUTPUTS/job['name']/'Run.out').read_text(errors='replace')
        assert all(value in text for value in ['SoilBoundaryDerivativeSPR="MirroredWallDerivatives"', 'SoilStressRateGradCorr="KernelGradient"', 'PoreCompressionGradCorr="KernelGradient"', 'PoreShepardRegularization="Disabled"'])
        if label == LABELS[1]:assert worker.hg.parse_hg(text, job) == receipt['hg'] and receipt['hg']['passed'] and receipt['initial38_only']
        else: assert 'SoilHourglassXi:' not in text and 'SoilHourglass: forcecalls=' not in text
        clock = worker.stage.clock_table(job['dt'], job['steps']); assert rows[-1]['natural_step'] == job['steps'] == 300001
        assert np.all(np.diff([r['time_s'] for r in rows]) > 0) and all(abs(r['time_s']-clock[r['natural_step']]) <= 1e-14 and r['saved_step'] == (r['natural_step']-1 if r['part'] else 0) for r in rows)
        suffix = '_numeric_profiles.csv' if label == LABELS[1] else '_profiles.csv'
        source = next(r for r in receipt['artifacts'] if Path(r['path']).name == job['name']+suffix)
        raw = pd.read_csv(source['path'], float_precision='round_trip'); a, hd = base.enrich(raw, rows, p, label); h = base.history(a, rows, label)
        assert np.array_equal(h.time_s, pair.reference_time_s if label == LABELS[0] else pair.time_s)
        h['native_990_r_rms_pa'] = pair['reference_r_excluding_top_rms_pa' if label == LABELS[0] else 'r_excluding_top_rms_pa'].to_numpy()
        final, changes, errors = base.final_summary(a, h)
        results[label] = dict(final_native=final, initial_to_final_changes=changes, final_vs_ideal=errors, last_window=base.last_window(a, h),
            material_relative_settlement=prior.relative_material_displacements(a), staggering=prior.staggering(a), final_native_990_r_rms_pa=float(h.native_990_r_rms_pa.iloc[-1]),
            original_complete_profiles=source, independently_redecoded=base.native_endpoints(worker.stage, job, receipt, raw), initial_drained_plane_m=hd)
        profiles[label], histories[label] = a, h
    assert oldprep['job']['program'] == prepared['job']['program'] and oldprep['job']['runtime'] == prepared['job']['runtime']
    signature = lambda t: [(e.tag, sorted(e.attrib.items())) for e in t.iter() if e.get('key') != 'SoilHourglassXi']
    assert signature(trees[0]) == signature(trees[1]) and not trees[0].findall('.//parameter[@key="SoilHourglassXi"]')
    assert trees[1].find('.//parameter[@key="SoilHourglassXi"]').get('value') == '0.1'
    for tree in trees:
        assert tree.find('.//parameter[@key="SoilBoundaryDerivativeSPR"]').get('value') == tree.find('.//parameter[@key="SoilStressRateGradCorr"]').get('value') == '1'
    assert np.max(np.abs(histories[LABELS[0]].time_s.to_numpy()-histories[LABELS[1]].time_s.to_numpy())) <= 1e-14
    assert np.array_equal(histories[LABELS[0]].saved_step, histories[LABELS[1]].saved_step)
    final = pd.concat([a[a.part == 60] for a in profiles.values()], ignore_index=True); history = pd.concat(histories.values(), ignore_index=True)
    assert len(final) == 200 and len(history) == 122
    records = worker.unique([dict(r, sha256=r['sha256'].lower()) for r in records]); verify(records)
    final.to_csv(paths['profiles_csv'], index=False); history.to_csv(paths['history_csv'], index=False); figures(profiles, histories, paths); verify(records)
    worker.seal(paths['check'], dict(analysis_checks_passed=True, inputs=records, parameters=common, jobs=results, actual_matched_samples=61,
        independently_redecoded_frames=4, source_profile_rows_retained_each=6100, output_profile_rows=200, output_history_rows=122,
        hg_statistics=newreceipt['hg'], source_program_attribution=prepared['source_program_attribution'], own_short_comparison='initial38_only_not_prefix_or_half',
        comparison_labels=LABELS, both_variants='SPR1/G1/ShepardOFF', physical_acceptance=False, new_half_validation=False, restart_admitted=False,
        formal_acceptance=False, automatic_full_consolidation_admitted=False, solver_started=False, production_changed=False,
        reference_scope='Finite-Kw small-strain H1/HD diagnostics only; no fitted height or new theory threshold; only completed .3s Stage1 reviewed',
        R_scope='100 layer means including drained top versus direct990 non-top particles,never conflated',
        figures_require_visual_inspection=True, artifacts=[bound(v) for key, v in paths.items() if key != 'check']))
    return dict(check=str(paths['check']), analysis_checks_passed=True, physical_acceptance=False)


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8')); base.selftest()
    assert LABELS == ['HGxi0_SPR1_G1_ShepardOFF', 'HGxi0p1_SPR1_G1_ShepardOFF']
    for v, expected in [(np.arange(100.), 0.), (np.arange(100.)**2, 1.), ((-1.)**np.arange(100), 2.)]:
        dummy = pd.DataFrame(dict(part=60, layer=np.arange(100), settlement_mm=v, pressure_pa=v, total_sigma_zz_pa=v))
        assert all(abs(r['interior_1_to_98_rms']-expected) < 1e-12 and abs(r['bulk_10_to_89_rms']-expected) < 1e-12 for r in prior.staggering(dummy)['metrics'].values())
    dummy = pd.DataFrame(dict(part=60, layer=np.arange(100), settlement_mm=np.arange(100.)**2,
        ideal_H1_settlement_mm=np.arange(100.)**2, ideal_HD_settlement_mm=np.arange(100.)**2))
    assert all(r['ideal_H1_error_percent'] == r['ideal_HD_error_percent'] == 0 for r in prior.relative_material_displacements(dummy))
    return dict(passed=True, files_written=False, native_reader_started=False, solver_started=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--selftest', action='store_true'); modes.add_argument('--review', action='store_true'); parser.add_argument('--tag', default=TAG)
    args = parser.parse_args(); assert args.tag and Path(args.tag).name == args.tag and args.tag.replace('_', '').isalnum()
    if args.selftest: print(json.dumps(selftest()))
    elif args.review: print(json.dumps(review(args.tag)))
    else: parser.print_help()
