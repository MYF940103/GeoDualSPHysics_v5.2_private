"""New combined overview from sealed clear-r1 CSVs; no solver, native reader or refitting."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

CASE = Path(__file__).resolve().parents[1]
FIGURES = CASE / 'figures'
NAME = 'CaseSelfWeightConsolidation_Scenario2_FreshPR'
SOURCE = NAME + '_compare_clear_r1_'
TARGET = NAME + '_compare_combined_r1'
PARTS = [1, 10, 20, 50, 80, 100, 140, 200, 300, 402]
NAVY, RED = '#1F3A5F', '#D55E00'
MARKERS = ['o', 's', '^', 'D', 'v', 'P', 'X', '<', '>', 'h']


def bound(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def verify(record):
    assert bound(record['path']) == record, ('Sealed input changed', record['path'])


def errors(history, profiles):
    h, p = history.copy(), profiles.copy()
    for label, sim, ref, unit in [
            ('fixed_p0_excess', 'bottom_excess_native_pa', 'H1_finite_bottom_q_pa', 'pa'),
            ('total_p', 'bottom_pressure_pa', 'H1_finite_bottom_p_pa', 'pa'),
            ('settlement', 'top_settlement_increment_mm', 'H1_finite_top_settlement_increment_mm', 'mm')]:
        h['combined_' + label + '_signed_error_' + unit] = h[sim] - h[ref]
    for label, sim, ref, unit in [
            ('fixed_p0_excess', 'excess_native_pa', 'H1_finite_q_pa', 'pa'),
            ('total_p', 'pressure_pa', 'H1_finite_p_pa', 'pa'),
            ('settlement', 'settlement_increment_mm', 'H1_finite_settlement_increment_mm', 'mm')]:
        p['combined_' + label + '_signed_error_' + unit] = p[sim] - p[ref]
    return h, p


def plot(h, p, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    plt.rcParams.update({'font.size': 14, 'axes.titlesize': 16, 'axes.labelsize': 14})
    fig, axes = plt.subplots(2, 3, figsize=(21, 11.5))
    fig.subplots_adjust(left=.06, right=.985, top=.78, bottom=.13, hspace=.34, wspace=.25)
    colors = plt.get_cmap('viridis')(np.linspace(.04, .82, len(PARTS)))
    handles, labels = [], []
    specs = [('excess_native_pa', 'H1_finite_q_pa', 1000., 'Fixed-p0 excess [kPa]'),
             ('pressure_pa', 'H1_finite_p_pa', 1000., 'Total pore pressure [kPa]'),
             ('settlement_increment_mm', 'H1_finite_settlement_increment_mm', 1., 'Settlement increment [mm]')]
    for index, part in enumerate(PARTS):
        b = p[p.part.eq(part)].sort_values('layer'); color, marker = colors[index], MARKERS[index]
        for col, (sim, ref, scale, title) in enumerate(specs):
            axes[0, col].plot(b[ref] / scale, b.z0_m, '--', color=color, lw=2.3, zorder=2)
            axes[0, col].plot(b[sim] / scale, b.z0_m, '-', color=color, lw=1., marker=marker,
                              mfc='white', mec=color, ms=4.5, mew=.9, markevery=8, zorder=3)
        handles.append(Line2D([], [], color=color, lw=2., marker=marker, mfc='white', ms=5))
        labels.append(f'Tv={float(b.finite_Kw_Tv.iloc[0]):.4g}')
    for col, (_, _, _, title) in enumerate(specs):
        axes[0, col].set(title=title, xlabel=title, ylabel='Initial material z0 / H')
    bottom = [('bottom_excess_native_pa', 'H1_finite_bottom_q_pa', 1000., 'Bottom fixed-p0 excess', 'kPa', 'fixed_p0_excess', 'pa'),
              ('bottom_pressure_pa', 'H1_finite_bottom_p_pa', 1000., 'Bottom total pore pressure', 'kPa', 'total_p', 'pa'),
              ('top_settlement_increment_mm', 'H1_finite_top_settlement_increment_mm', 1., 'Top material settlement', 'mm', 'settlement', 'mm')]
    for col, (sim, ref, scale, title, unit, error, error_unit) in enumerate(bottom):
        ax = axes[1, col]
        ax.plot(h.finite_Kw_Tv, h[ref] / scale, '--', color=NAVY, lw=2.4, label='H1 finite-Kw', zorder=2)
        ax.plot(h.finite_Kw_Tv, h[sim] / scale, '-', color=RED, lw=1.5, marker='o', mfc='white',
                mec=RED, ms=4.3, markevery=20, label='SPH', zorder=3)
        value = float(h['combined_' + error + '_signed_error_' + error_unit].iloc[-1])
        ax.text(.98 if col < 2 else .5, .68 if col < 2 else .06,
                f'Final SPH − H1: {value:+.6g} {"Pa" if error_unit == "pa" else "mm"}',
                transform=ax.transAxes, ha='right' if col < 2 else 'center', fontsize=13,
                bbox=dict(facecolor='white', alpha=.85, edgecolor='none'))
        ax.set(title=title, xlabel='Actual finite-Kw Tv', ylabel=f'{title} [{unit}]')
        ax.legend(loc='upper right' if col < 2 else 'upper left', fontsize=13)
    for ax in axes.flat:
        ax.grid(True, alpha=.20); ax.tick_params(labelsize=12)
    fig.suptitle('Self-weight consolidation: SPH and H1 finite-Kw reference', fontsize=20, y=.985)
    style = [Line2D([], [], color='black', lw=2.3, ls='--', label='H1 quasi-static'),
             Line2D([], [], color='black', lw=1., marker='o', mfc='white', label='SPH')]
    fig.legend(handles=style, loc='upper center', bbox_to_anchor=(.5, .947), ncol=2, frameon=False, fontsize=14)
    fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(.5, .906), ncol=5, frameon=False,
               fontsize=13, title='Profiles: actual finite-Kw Tv at saved states', columnspacing=2.)
    fig.text(.5, .060, 'Native excess = float32(p − p0), fixed initial p0; not moving-hydro excess. H=1 m; profiles use initial material z0/H.',
             ha='center', fontsize=12)
    fig.text(.5, .035, 'H1 finite-Kw is quasi-static, not exact dynamic startup truth. All actual saves; no smoothing/interpolation or acceptance change.',
             ha='center', fontsize=12)
    fig.savefig(path, dpi=250); plt.close(fig)


def run():
    paths = dict(png=FIGURES / (TARGET + '.png'), history=FIGURES / (TARGET + '_history.csv'),
                 profiles=FIGURES / (TARGET + '_profiles.csv'), manifest=FIGURES / (TARGET + '_manifest.json'))
    assert not any(p.exists() for p in paths.values()), 'Fresh label only; retained evidence must not be overwritten'
    oldpath = FIGURES / (SOURCE + 'manifest.json'); old = json.loads(oldpath.read_text(encoding='utf8'))
    assert old['passed'] and old['analysis_checks_passed'] and not old['physical_acceptance'] and not old['formal_acceptance']
    inputs = [bound(__file__), bound(oldpath)]; tables = []
    for kind in ['history', 'profiles']:
        path = FIGURES / (SOURCE + 'matching_' + kind + '.csv')
        record = next(r for r in old['artifacts'] if Path(r['path']).resolve() == path.resolve())
        verify(record); inputs.append(record); tables.append(pd.read_csv(path, float_precision='round_trip'))
    h, p = errors(*tables)
    assert len(h) == 403 and h.dataset.eq('fresh').all() and np.array_equal(h.part, np.arange(403)) and np.all(np.diff(h.time_s) > 0)
    assert abs(float(h.finite_Kw_Tv.iloc[-1]) - 2) < 1e-6
    assert len(p) == 1100 and p.dataset.eq('fresh').all() and set(p.part) == set(PARTS + [400])
    assert p.groupby('part').size().eq(100).all() and all(np.array_equal(np.sort(b.layer), np.arange(100)) for _, b in p.groupby('part'))
    used = p[p.profile_used]; assert len(used) == 1000 and set(used.part) == set(PARTS)
    plot(h, used, paths['png'])
    for kind, frame in [('history', h), ('profiles', p)]:
        with paths[kind].open('x', encoding='utf8', newline='') as stream:frame.to_csv(stream, index=False, float_format='%.17g')
    for record in inputs:verify(record)
    result = dict(passed=True, analysis_checks_passed=True, inputs=inputs, artifacts=[bound(paths[k]) for k in ['png', 'history', 'profiles']],
                  history_states=403, retained_profile_rows=1100, plotted_profile_rows=1000, plotted_parts=PARTS, retained_not_plotted_parts=[400], H_m=1.,
                  actual_final_finite_Tv=float(h.finite_Kw_Tv.iloc[-1]), actual_final_time_s=float(h.time_s.iloc[-1]),
                  definitions=dict(excess='Native float32(p−p0), fixed initial p0, not moving-hydro q', reference='Existing H1_finite_ columns, quasi-static at actual saved times',
                                   settlement='Own-initial fixed-material increment; signed errors are simulation minus H1'),
                  residual_floor_budget_diagnostic_met=old['residual_floor_budget_diagnostic_met'], physical_acceptance=False, formal_acceptance=False,
                  no_physical_acceptance_change=True, native_reader_started=False, solver_started=False)
    with paths['manifest'].open('x', encoding='utf8') as stream:json.dump(result, stream, indent=2, allow_nan=False)
    return dict(manifest=str(paths['manifest']), passed=True, physical_acceptance=False)


def selftest():
    h = pd.DataFrame(dict(bottom_excess_native_pa=[3.], H1_finite_bottom_q_pa=[1.], bottom_pressure_pa=[7.], H1_finite_bottom_p_pa=[5.],
                         top_settlement_increment_mm=[.5], H1_finite_top_settlement_increment_mm=[.4]))
    p = pd.DataFrame(dict(excess_native_pa=[3.], H1_finite_q_pa=[1.], pressure_pa=[7.], H1_finite_p_pa=[5.],
                         settlement_increment_mm=[.5], H1_finite_settlement_increment_mm=[.4]))
    a, b = errors(h, p); np.testing.assert_allclose(a.filter(like='combined_'), [[2., 2., .1]])
    np.testing.assert_allclose(b.filter(like='combined_'), [[2., 2., .1]]); assert len(set(PARTS)) == 10 and 400 not in PARTS and 402 in PARTS
    return dict(passed=True, files_written=False, native_reader_started=False, programs_started=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--selftest', action='store_true'); mode.add_argument('--run', action='store_true'); args = parser.parse_args()
    if args.selftest:print(json.dumps(selftest()))
    elif args.run:print(json.dumps(run()))
    else:parser.print_help()
