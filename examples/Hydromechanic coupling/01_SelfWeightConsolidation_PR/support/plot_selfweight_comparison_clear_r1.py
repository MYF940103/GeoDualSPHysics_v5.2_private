"""Read sealed CSVs only; produce clearer new comparisons without changing physics/evidence."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

CASE = Path(__file__).resolve().parents[1]
FIGURES = CASE / 'figures'
NAME = 'CaseSelfWeightConsolidation_Scenario2_FreshPR'
SOURCE = NAME + '_nativepr_'
TARGET = NAME + '_compare_clear_r1_'
EARLY = [1, 10, 20, 50, 80, 100]
LATE = [140, 200, 300, 402]
NAVY, RED = '#1F3A5F', '#D55E00'
COLORS = ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#56B4E9', '#E69F00']
MARKERS = ['o', 's', '^', 'D', 'v', 'P']


def bound(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def verify(record):
    assert bound(record['path']) == record, ('Sealed input changed', record['path'])


def enrich(history, profiles):
    h, p = history.copy(), profiles.copy()
    h['bottom_total_p_sim_minus_H1_pa'] = h.bottom_pressure_pa - h.H1_finite_bottom_p_pa
    h['bottom_current_q_sim_minus_H1_intrinsic_pa'] = h.bottom_q_current_pa - h.H1_finite_bottom_q_pa
    for location in ['top', 'bottom']:
        h[location + '_settlement_sim_minus_H1_mm'] = h[location + '_settlement_increment_mm'] - h['H1_finite_' + location + '_settlement_increment_mm']
    h['H1_finite_top_minus_bottom_settlement_mm'] = h.H1_finite_top_settlement_increment_mm - h.H1_finite_bottom_settlement_increment_mm
    h['relative_settlement_sim_minus_H1_mm'] = h.top_minus_bottom_settlement_mm - h.H1_finite_top_minus_bottom_settlement_mm
    p['total_p_sim_minus_H1_pa'] = p.pressure_pa - p.H1_finite_p_pa
    p['settlement_sim_minus_H1_mm'] = p.settlement_increment_mm - p.H1_finite_settlement_increment_mm
    p['profile_used'] = p.part.isin(EARLY + LATE)
    p['plot_group'] = np.where(p.part.isin(EARLY), 'early', np.where(p.part.isin(LATE), 'late', 'retained_not_plotted'))
    return h, p


def pair(ax, x, sim, ref, sim_label='SPH', ref_label='H1 quasi-static'):
    ax.plot(x, ref, '--', color=NAVY, lw=2.4, label=ref_label, zorder=2)
    ax.plot(x, sim, '-', color=RED, lw=1.5, marker='o', mfc='white', mec=RED,
            ms=4.2, mew=1., markevery=max(1, len(x) // 20), label=sim_label, zorder=3)


def finish(fig, axes, path, title, footnote):
    fig.suptitle(title, fontsize=16, y=.985)
    for ax in axes.flat:
        ax.grid(True, alpha=.22)
        ax.tick_params(labelsize=11)
    fig.text(.5, .018, footnote, ha='center', va='bottom', fontsize=10)
    fig.savefig(path, dpi=220)
    import matplotlib.pyplot as plt
    plt.close(fig)


def histories(h, paths):
    import matplotlib.pyplot as plt
    x = h.finite_Kw_Tv
    fig, a = plt.subplots(2, 2, figsize=(16, 10))
    fig.subplots_adjust(left=.085, right=.98, top=.90, bottom=.12, hspace=.38, wspace=.25)
    pair(a[0, 0], x, h.bottom_pressure_pa / 1000, h.H1_finite_bottom_p_pa / 1000)
    a[0, 0].set(title='Bottom total pore pressure', ylabel='Total p [kPa]')
    pair(a[0, 1], x, h.bottom_q_current_pa / 1000, h.H1_finite_bottom_q_pa / 1000,
         'SPH: moving-hydro q', 'H1: intrinsic q')
    a[0, 1].set(title='Excess pressure: distinct hydro baselines', ylabel='q [kPa]')
    a[1, 0].plot(x, h.bottom_total_p_sim_minus_H1_pa, color=RED, lw=1.7, label='Bottom signed error')
    a[1, 0].plot(x, h.H1_finite_pressure_rms_pa, color=NAVY, ls=':', lw=2., label='All-layer RMS (not signed)')
    a[1, 0].axhline(0, color='.5', lw=.8)
    a[1, 0].set(title='Total-p comparison error', ylabel='SPH − H1 [Pa]')
    late = h[h.finite_Kw_Tv >= 1.25]
    pair(a[1, 1], late.finite_Kw_Tv, late.bottom_q_current_pa, late.H1_finite_bottom_q_pa,
         'SPH: moving-hydro q', 'H1: intrinsic q')
    a[1, 1].set(title='Late excess-pressure detail', ylabel='q [Pa]', xlim=(1.25, float(x.iloc[-1]) + .001))
    for ax in a.flat:
        ax.set_xlabel('Actual finite-Kw Tv')
        ax.legend(fontsize=11)
    finish(fig, a, paths['pressure_history'], 'Self-weight consolidation: pressure comparison',
           'H1 finite-Kw, H=1 m, quasi-static reference; all 403 actual saves. q uses different hydro baselines; no interpolation or acceptance change.')
    fig, a = plt.subplots(2, 2, figsize=(16, 10))
    fig.subplots_adjust(left=.085, right=.98, top=.90, bottom=.12, hspace=.38, wspace=.25)
    pair(a[0, 0], x, h.top_settlement_increment_mm, h.H1_finite_top_settlement_increment_mm)
    a[0, 0].set(title='Top material settlement', ylabel='Own-initial increment [mm]')
    late = h[h.finite_Kw_Tv >= 1.5]
    pair(a[0, 1], late.finite_Kw_Tv, late.top_settlement_increment_mm, late.H1_finite_top_settlement_increment_mm)
    a[0, 1].set(title='Top settlement: late detail', ylabel='Own-initial increment [mm]', xlim=(1.5, float(x.iloc[-1]) + .001))
    pair(a[1, 0], x, h.bottom_settlement_increment_mm, h.H1_finite_bottom_settlement_increment_mm)
    a[1, 0].set(title='Bottom material settlement', ylabel='Own-initial increment [mm]')
    for key, label, color, style in [('top', 'Top', RED, '-'), ('bottom', 'Bottom', NAVY, '--'), ('relative', 'Top − bottom', '#009E73', '-.')]:
        a[1, 1].plot(x, h[key + '_settlement_sim_minus_H1_mm'], color=color, ls=style, lw=1.8, label=label)
    a[1, 1].axhline(0, color='.5', lw=.8)
    a[1, 1].set(title='Signed settlement errors', ylabel='SPH − H1 [mm]')
    for ax in a.flat:
        ax.set_xlabel('Actual finite-Kw Tv')
        ax.legend(fontsize=11)
    finish(fig, a, paths['settlement_history'], 'Self-weight consolidation: settlement comparison',
           'H1 finite-Kw, H=1 m, quasi-static reference; fixed material IDs, own-initial increments. Bottom displacement is not forced to zero.')


def profiles(p, paths):
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    styles = [Line2D([], [], color='black', lw=2.4, ls='--', label='H1 quasi-static'),
              Line2D([], [], color='black', lw=1., marker='o', mfc='white', label='SPH')]
    for kind, observed, reference, error, scale, unit in [
            ('pressure', 'pressure_pa', 'H1_finite_p_pa', 'total_p_sim_minus_H1_pa', 1000., 'kPa'),
            ('settlement', 'settlement_increment_mm', 'H1_finite_settlement_increment_mm', 'settlement_sim_minus_H1_mm', 1., 'mm')]:
        fig, a = plt.subplots(2, 2, figsize=(16, 10))
        fig.subplots_adjust(left=.085, right=.98, top=.84, bottom=.10, hspace=.44, wspace=.25)
        fig.legend(handles=styles, loc='upper center', bbox_to_anchor=(.5, .965), ncol=2, frameon=False, fontsize=12)
        for row, parts in enumerate([EARLY, LATE]):
            handles, labels = [], []
            for i, part in enumerate(parts):
                b = p[p.part.eq(part)].sort_values('layer'); color, marker = COLORS[i], MARKERS[i]
                a[row, 0].plot(b[reference] / scale, b.z0_m, '--', color=color, lw=2.4, zorder=2)
                a[row, 0].plot(b[observed] / scale, b.z0_m, '-', color=color, lw=1., marker=marker,
                               mfc='white', mec=color, ms=4.2, mew=.9, markevery=7, zorder=3)
                a[row, 1].plot(b[error], b.z0_m, color=color, lw=1.5)
                handles.append(Line2D([], [], color=color, lw=2.))
                labels.append(f'Tv={float(b.finite_Kw_Tv.iloc[0]):.4g}')
            a[row, 0].set(title=('Early' if row == 0 else 'Late') + ' profiles', xlabel=f'{"Total p" if kind == "pressure" else "Settlement increment"} [{unit}]')
            a[row, 1].axvline(0, color='.5', lw=.8)
            a[row, 1].set(title='Signed profile error', xlabel='SPH − H1 [' + ('Pa' if kind == 'pressure' else 'mm') + ']')
            for ax in a[row]:ax.set_ylabel('Initial material z [m]')
            fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(.53, .915 if row == 0 else .47),
                       ncol=6 if row == 0 else 4, frameon=False, fontsize=11, title='Actual finite-Kw Tv')
        finish(fig, a, paths[kind + '_profiles'], f'Self-weight consolidation: {kind} profiles',
               'H1 finite-Kw, H=1 m, quasi-static reference at actual saved times; all 100 layers, no smoothing/interpolation. Acceptance unchanged.')


def run():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 12.5, 'axes.titlesize': 13, 'axes.labelsize': 12.5})
    paths = {k: FIGURES / (TARGET + k + '.png') for k in ['pressure_history', 'settlement_history', 'pressure_profiles', 'settlement_profiles']}
    paths.update({k: FIGURES / (TARGET + k + '.csv') for k in ['matching_history', 'matching_profiles']})
    destination = FIGURES / (TARGET + 'manifest.json')
    assert not any(p.exists() for p in [*paths.values(), destination]), 'New output label only; preserve retained figures/CSVs'
    manifest_path = FIGURES / (SOURCE + 'manifest.json'); source = json.loads(manifest_path.read_text(encoding='utf8'))
    assert all(source[k] for k in ['passed', 'analysis_checks_passed', 'postprocessing_completed', 'native_safety_passed'])
    inputs = [bound(__file__), bound(manifest_path)]; tables = []
    for kind in ['history', 'selected_profiles']:
        path = FIGURES / (SOURCE + kind + '.csv'); record = next(r for r in source['artifacts'] if Path(r['path']).resolve() == path.resolve())
        verify(record); inputs.append(record); frame = pd.read_csv(path, float_precision='round_trip')
        tables.append(frame[frame.dataset.eq('fresh')].copy())
    h, p = enrich(*tables); h = h.sort_values('part').reset_index(drop=True)
    assert len(h) == 403 and np.array_equal(h.part, np.arange(403)) and np.all(np.diff(h.time_s) > 0)
    assert abs(float(h.finite_Kw_Tv.iloc[-1]) - 2) < 1e-6
    assert len(p) == 1100 and set(p.part) == set(EARLY + LATE + [400]) and p.groupby('part').size().eq(100).all()
    assert all(np.array_equal(np.sort(b.layer), np.arange(100)) for _, b in p.groupby('part')) and int(p.profile_used.sum()) == 1000
    histories(h, paths); profiles(p, paths)
    for key, frame in [('matching_history', h), ('matching_profiles', p)]:
        with paths[key].open('x', encoding='utf8', newline='') as stream:frame.to_csv(stream, index=False, float_format='%.17g')
    for record in inputs:verify(record)
    result = dict(passed=True, analysis_checks_passed=True, inputs=inputs, artifacts=[bound(q) for q in paths.values()],
                  fresh_history_states=403, retained_profile_rows=1100, plotted_profile_rows=1000, profile_used_parts=EARLY + LATE,
                  retained_not_plotted_parts=[400], actual_final_finite_Tv=float(h.finite_Kw_Tv.iloc[-1]), actual_final_time_s=float(h.time_s.iloc[-1]),
                  definitions=dict(total_p_error='p − H1_finite_p', current_q='p − rho_w*g*max(current drained-material-plane z − z,0)',
                                   fixed_p0_excess='Native float32(p−p0); retained unchanged, not substituted for current q', settlement='Fixed-material own-initial increment',
                                   theory='H1 finite-Kw quasi-static at actual saved times, not exact dynamic startup truth'),
                  residual_floor_budget_diagnostic_met=source['residual_floor_budget_diagnostic_met'], physical_acceptance=False,
                  formal_acceptance=False, no_physical_acceptance_change=True, solver_started=False, native_reader_started=False)
    with destination.open('x', encoding='utf8') as stream:json.dump(result, stream, indent=2, allow_nan=False)
    return dict(manifest=str(destination), passed=True, physical_acceptance=False)


def selftest():
    h = pd.DataFrame(dict(bottom_pressure_pa=[10.], H1_finite_bottom_p_pa=[8.], bottom_q_current_pa=[4.], H1_finite_bottom_q_pa=[3.],
                         top_settlement_increment_mm=[2.], bottom_settlement_increment_mm=[.1], H1_finite_top_settlement_increment_mm=[1.8],
                         H1_finite_bottom_settlement_increment_mm=[.05], top_minus_bottom_settlement_mm=[1.9]))
    p = pd.DataFrame(dict(part=[1, 400, 402], pressure_pa=[3., 4., 5.], H1_finite_p_pa=[1., 1., 1.],
                         settlement_increment_mm=[.3, .4, .5], H1_finite_settlement_increment_mm=[.1, .1, .1]))
    a, b = enrich(h, p); assert a.bottom_total_p_sim_minus_H1_pa.iloc[0] == 2 and a.bottom_current_q_sim_minus_H1_intrinsic_pa.iloc[0] == 1
    np.testing.assert_allclose(a.relative_settlement_sim_minus_H1_mm, [.15]); assert b.profile_used.tolist() == [True, False, True]
    assert len(EARLY) == 6 and len(LATE) == 4 and len(set(EARLY + LATE)) == 10
    return dict(passed=True, files_written=False, programs_started=False, native_reader_started=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--selftest', action='store_true'); mode.add_argument('--run', action='store_true'); args = parser.parse_args()
    if args.selftest:print(json.dumps(selftest()))
    elif args.run:print(json.dumps(run()))
    else:parser.print_help()
