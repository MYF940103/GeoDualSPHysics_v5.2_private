"""Existing Wendland receiver analysis with honest same-AS FS-closure plot labels only."""
import argparse, json
from pathlib import Path
import c08_h18_wend_receiver_review_r1 as core

TAG = 'c08_fs_normal_window_review_r1'
NOTE = core.T / 'notes' / (TAG + '.md')
LABELS = {'c08_h18_wend_psi0_a05_w09_r1': 'Original raw FS closure',
          'c08_fs_normal_window_GPU_r1': 'Normal Taylor FS closure'}


def metrics_plot(analyses, prefix):
    core.need({a['summary']['tag'] for a in analyses} == set(LABELS) and len(analyses) == 2
              and all(a['history'][0]['AS_coefficient'] == core.old.f32(.5) and a['history'][0]['AS_exponent'] == core.old.f32(3.825) for a in analyses), 'Plot labels require exactly the same-AS raw/normal pair')
    fig, axes = core.old.plt.subplots(2, 3, figsize=(13, 8), layout='constrained')
    charts = (('runout_from_PRE_front_m', 'Front advance from PRE [m]', 1.), ('NN_q05_over_dp', '5% nearest distance / dp', 1.), ('pairs_r_lt_0p7dp', 'Pairs at r < .7dp', 1.), ('current_mixture_KE_J_per_m', 'Current mixture KE [J/m]', 1.), ('p_min_Pa', 'Minimum absolute p [kPa]', .001), ('p_RMS_Pa', 'Absolute p RMS [kPa]', .001))
    for ax, (key, title, scale) in zip(axes.flat, charts):
        for a in analyses: ax.plot([q['tau_s'] for q in a['history']], [q[key] * scale for q in a['history']], label=LABELS[a['summary']['tag']])
        ax.set(title=title, xlabel='Actual time since PRE release [s]'); ax.grid(alpha=.2); ax.legend(fontsize=7)
    fig.suptitle('Wendland psi0: raw versus normal Taylor FS closure\nBoth use AS coefficient 0.5 / exponent 3.825; inspect pressure, spacing and motion together')
    destination = Path(str(prefix) + '_selection.png'); fig.savefig(destination, dpi=170); core.old.plt.close(fig)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--manifest', type=Path, required=True); parser.add_argument('--execution-authorized', action='store_true'); args = parser.parse_args()
    core.need(args.execution_authorized, 'Author-only until root full-read and separate offline-analysis authorization')
    manifest = core.read(args.manifest); tag = manifest['tag']; core.need(core.re.fullmatch(r'[A-Za-z0-9_]+', tag), 'Safe fresh analysis tag required')
    receipt = core.T / 'logs' / (tag + '.adapter.json'); core.need(not receipt.exists(), 'Existing adapter record protected')
    before = [core.stat(q) for q in (Path(__file__), NOTE, Path(core.__file__), args.manifest)]
    original_plot = core.metrics_plot; core.metrics_plot = metrics_plot
    try: core.main()
    finally: core.metrics_plot = original_plot
    after = [core.stat(q['path']) for q in before]; core.need(before == after, 'Adapter/helper/manifest changed during analysis')
    check = core.T / 'logs' / (tag + '.check.json')
    with receipt.open('x', encoding='utf-8') as handle:
        json.dump(dict(stage=TAG + '.adapter', analysis_check=core.stat(check), before=before, after=after, stats_unchanged=True, only_metrics_plot_replaced=True, physical_acceptance=False), handle, indent=2, allow_nan=False); handle.write('\n')


if __name__ == '__main__': main()
