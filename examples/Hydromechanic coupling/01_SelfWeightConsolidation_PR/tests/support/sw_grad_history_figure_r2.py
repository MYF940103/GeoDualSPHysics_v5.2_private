"""Render a clearer history PNG from the sealed G0/G1 review CSV; no native/solver."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import sw_grad_equilibrium_review_r1 as review


def render():
    import sw_grad_stage1_r1 as worker
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    tests = review.TESTS
    source = tests/'logs/sw_grad_equilibrium_review_r1.check.json'
    check = worker.read(source)
    assert check['analysis_checks_passed'] and check['matched_frames'] == 61
    worker.verify(check['inputs'] + check['artifacts'])
    csv = next(r for r in check['artifacts'] if Path(r['path']).name.endswith('_history.csv'))
    h = pd.read_csv(csv['path'], float_precision='round_trip')
    assert len(h) == 122 and set(h.job) == set(review.LABELS)
    png = tests/'figures/sw_grad_equilibrium_review_r2_history.png'
    receipt = tests/'logs/sw_grad_equilibrium_review_r2.visual.json'
    assert not png.exists() and not receipt.exists()
    plt.rcParams.update({'font.size': 9, 'axes.grid': True, 'grid.alpha': .25})
    fig, axes = plt.subplots(3, 2, figsize=(12, 10), constrained_layout=True)
    for label, color in zip(review.LABELS, ['tab:orange', 'tab:blue']):
        a = h[h.job == label].sort_values('part')
        assert np.array_equal(a.part, np.arange(61))
        t = a.time_s
        axes[0, 0].plot(t, a.bottom_p_pa/1000, color=color, label=label+' p')
        axes[0, 0].plot(t, a.bottom_q_native_pa/1000, '--', color=color, label=label+' q')
        axes[0, 1].plot(t, a.top_settlement_mm, color=color, label=label+' top')
        axes[0, 1].plot(t, a.bottom_settlement_mm, '--', color=color, label=label+' bottom')
        axes[1, 0].plot(t, a.speed_max_m_s, color=color, label=label)
        axes[1, 1].plot(t, a.native_990_r_rms_pa, color=color, label=label)
        late = a[a.time_s >= .25-1e-14]
        axes[2, 0].plot(late.time_s, late.bottom_p_pa-late.bottom_p_pa.iloc[0], color=color, label=label)
        for column, style, name in [('top_settlement_mm', '-', 'top'), ('bottom_settlement_mm', '--', 'bottom')]:
            axes[2, 1].plot(late.time_s, late[column]-late[column].iloc[0], style, color=color, label=label+' '+name)
    titles = ['Bottom material p and native q [kPa]', 'Material downward settlement [mm]',
              'Maximum native soil speed [m/s]', 'R RMS: native non-top 990 particles [Pa]',
              'Late bottom pressure change [Pa]', 'Late material settlement change [mm]']
    for ax, title in zip(axes.flat, titles):
        ax.set(title=title, xlabel='Actual saved time [s]'); ax.legend(fontsize=7)
    fig.suptitle('G0/G1, both ShepardOFF; 61 actual samples each; no interpolation or smoothing')
    fig.savefig(png, dpi=180); plt.close(fig)
    worker.seal(receipt, dict(render_completed=True, visual_inspection_still_required=True,
        source_review=worker.bound(source), source_csv=csv, renderer=worker.bound(__file__),
        output=worker.bound(png), same_122_csv_rows=True, data_changed=False, solver_started=False,
        note='Only non-top native R is shown in the history panel; all 100 layers remain in the source review/CSV/profile PNG.'))
    return dict(png=str(png), receipt=str(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render', action='store_true')
    args = parser.parse_args()
    if args.render: print(json.dumps(render()))
    else: parser.print_help()
