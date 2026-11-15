"""Plot sealed HG CSV columns only; no numerical review, decoder or solver."""
import argparse, csv, json
from pathlib import Path

T = Path(__file__).resolve().parents[1]
TAG = 'c08_h18_wall_c_retry_full3_hg_visual_r2'
BASE = 'c08_h18_wall_c_retry_full3_hg_review_r1'
SOURCE = T / 'logs' / (BASE + '.check.json')
PNG, CHECK = T / 'figures' / (TAG + '.png'), T / 'logs' / (TAG + '.check.json')
NOTE = T / 'notes' / (TAG + '.md')
CHARTS = [
    ('HG energy', 'Energy [J/m]', [('Eold', 'Old'), ('Enew', 'New')]),
    ('HG work', 'Work [J/m]', [('row_work', 'Row'), ('node_work', 'Node')]),
    ('Loading and rotation', 'Energy [J/m]', [('loading_loss', 'Loading'), ('rotation_change', 'Rotation'), ('ledger', 'Residual')]),
    ('Directed rows', 'Count', [('rows', 'Active'), ('accepted_dead', 'Deleted total')]),
    ('HG time-step ratio', 'dt / limit', [('dt_over_0p2_limit', 'dt / limit')]),
    ('Loading factor', 'Gamma', [('gamma_min', 'Min'), ('gamma_max', 'Max')]),
    ('Local spin', 'Half-angle [rad]', [('max_half_angle', 'Spin')]),
    ('Force writeback', 'Force [N/m]', [('max_commit_error', 'Error'), ('commit_budget', 'Budget')]),
    ('Diagnostic budget ratios', 'Absolute value / budget', [('ledger_over_recorded_budget', 'Ledger'), ('adjoint_over_recorded_budget', 'Adjoint'), ('torque_over_recorded_budget', 'Torque')]),
]


def stat(path):
    path = Path(path).resolve(); s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execution-authorized', action='store_true')
    assert p.parse_args().execution_authorized, 'Root must review and authorize plotting'
    assert not PNG.exists() and not CHECK.exists(), 'Protect existing derived output'
    source = json.loads(SOURCE.read_text(encoding='utf-8-sig'))
    assert source['passed'] and source['analysis_complete'] and source['HG']['reviewed_rows'] == 602
    paths = [T / 'figures' / (BASE + suffix) for suffix in ('_phases.csv', '_extrema.csv')]
    bound = [next(q for q in source['files'] if Path(q['path']).resolve() == path.resolve()) for path in paths]
    assert all(stat(q['path']) == q for q in bound), 'Sealed CSV stat changed'
    original = [stat(SOURCE), *bound]
    with paths[0].open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    with paths[1].open(encoding='utf-8-sig', newline='') as stream:
        extrema_rows = list(csv.DictReader(stream))
    assert len(rows) == 602 and extrema_rows and all(rows[2*i]['phase'] == 'Pre' and rows[2*i+1]['phase'] == 'Cor' for i in range(301))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 3, figsize=(18, 15), layout='constrained')
    for ax, (title, unit, columns) in zip(axes.flat, CHARTS):
        for phase, style in (('Pre', '--'), ('Cor', '-')):
            group = [r for r in rows if r['phase'] == phase]
            for column, label in columns:
                ax.plot([float(r['tau_s']) for r in group], [None if r[column] == '' else float(r[column]) for r in group],
                        style, linewidth=1, label=phase + ' ' + label)
        ax.set(title=title, xlabel='Actual time after release [s]', ylabel=unit)
        ax.grid(alpha=.2); ax.legend(fontsize=8)
    axes[1, 1].axhline(1, color='black', linewidth=.6)
    axes[2, 0].axhline(.005, color='black', linewidth=.6)
    fig.suptitle('C08 HG observations: full 3 s\nPre/Cor trials share committed energy; budget ratios are diagnostics', fontsize=15)
    fig.savefig(PNG, dpi=160); plt.close(fig)
    assert all(stat(q['path']) == q for q in original), 'Original check or CSV changed'
    result = dict(stage=TAG, passed=True, CSV_only_plot=True, source_check=original[0], source_CSVs=bound,
        original_inputs_unchanged=True, numerical_recalculation=False, same_series_and_reference_lines=True,
        phase_rows=602, extrema_rows=len(extrema_rows), charts=CHARTS, figure=stat(PNG), visual_QA_pending=True,
        author_files=[stat(Path(__file__)), stat(NOTE)], physical_acceptance=False,
        solver_invocations=0, reader_invocations=0, SHA_scans=0, original_figure_or_check_modified=False)
    with CHECK.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False); stream.write('\n')


if __name__ == '__main__':
    main()
