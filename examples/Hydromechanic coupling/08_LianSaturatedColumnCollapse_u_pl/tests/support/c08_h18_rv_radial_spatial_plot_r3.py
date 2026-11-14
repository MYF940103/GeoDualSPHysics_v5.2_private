"""New P76/P90 plots with explicit axes/colorbar rectangles; preserve r1/r2."""
import argparse
import json
import math
from pathlib import Path
import c08_h18_rv_radial_spatial_plot_r2 as base

TAG = 'c08_h18_rv_radial_spatial_plot_r3'
T, L, NOTE = base.T, base.L, base.T / 'notes' / (TAG + '.md')
R2 = L / 'c08_h18_rv_radial_spatial_plot_r2.check.json'
need, stat, read, bind = base.need, base.stat, base.read, base.bind


def render(part, groups, fixed, target):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize

    states = []
    for case in base.CASES:
        rows = groups[case, part]
        pos = np.array([[float(row[axis + '_m']) for axis in 'xyz'] for row in rows])
        pressure = np.array([float(row['p_Pa']) for row in rows]) / 1000.
        nearest = np.array([float(row['NN_over_dp']) for row in rows])
        need(np.isfinite(pos).all() and np.isfinite(pressure).all() and np.isfinite(nearest).all(),
             'No nonfinite or excluded spatial values')
        states.append((pos, pressure, nearest))
    times = [(groups[case, part][0]['actual_time_s'], groups[case, part][0]['tau_s']) for case in base.CASES]
    need(all(tuple(map(base.bits, value)) == tuple(map(base.bits, times[0])) for value in times),
         'Three original actual saved times must agree')
    pos = np.concatenate([state[0] for state in states])
    pressure = np.concatenate([state[1] for state in states])
    nearest = np.concatenate([state[2] for state in states])
    xlim = (float(pos[:, 0].min()) - base.DP, float(pos[:, 0].max()) + base.DP)
    ylim = (float(pos[:, 2].min()) - base.DP, float(pos[:, 2].max()) + base.DP)
    limits = ((float(pressure.min()), float(pressure.max())),
              (float(nearest.min()), float(nearest.max())))
    need(all(math.isfinite(a) and math.isfinite(b) and a < b for a, b in limits),
         'Original nonconstant full-range color limits required')
    norms = tuple(Normalize(vmin=a, vmax=b, clip=False) for a, b in limits)
    time, tau = float(times[0][0]), float(times[0][1])

    fig = plt.figure(figsize=(18, 12))
    fig.suptitle('C08: native pressure and particle spacing\n'
                 'All 5000 original soil IDs per case; unchanged values, limits and view',
                 fontsize=15, y=.985)
    fig.text(.5, .935, f'P{part}; actual t={time:.17g} s; actual tau={tau:.17g} s',
             ha='center', fontsize=10)
    fig.text(.5, .912, 'Row labels round tau to 6 decimals only; original CSV/native clocks are unchanged.',
             ha='center', fontsize=9)
    images = [None, None]
    # Independent rectangles reserve real horizontal space between bar1 and right y labels.
    rows_y, columns_x, width, height = (.65, .37, .09), (.055, .565), .335, .22
    for i, (case, title, state) in enumerate(zip(base.CASES, base.TITLES, states)):
        positions, values_p, values_nn = state
        for j, (values, cmap, field) in enumerate(((values_p, 'coolwarm', 'Native signed pressure'),
                                                  (values_nn, 'viridis', 'Nearest neighbour / dp'))):
            ax = fig.add_axes((columns_x[j], rows_y[i], width, height))
            walls = fixed[case, part]
            ax.scatter(walls[:, 0], walls[:, 2], s=3, color='.72', edgecolors='none', rasterized=True)
            images[j] = ax.scatter(positions[:, 0], positions[:, 2], c=values, cmap=cmap, norm=norms[j],
                                   s=6, edgecolors='none', rasterized=True)
            ax.set(xlim=xlim, ylim=ylim, xlabel='Actual x [m]', ylabel='Actual z [m]')
            ax.set_aspect('equal', adjustable='box')
            ax.set_title(f'{title} | {field}\nP{part}; tau={tau:.6f} s (rounded label)', fontsize=10, pad=9)
            ax.tick_params(labelsize=9)
    for j, label in enumerate(('Native p [kPa]\n(full signed linear range)',
                               'Nonself soil NN / dp\n(full range)')):
        bar = fig.colorbar(images[j], cax=fig.add_axes(((.435, .925)[j], .09, .012, .78)))
        bar.set_label(label, fontsize=10, labelpad=12)
        bar.ax.tick_params(labelsize=9)
    need(not target.exists(), 'Existing plot/partial protected: ' + str(target))
    fig.savefig(target, dpi=180)
    plt.close(fig)
    return dict(part=part, actual_time_s=time, tau_s=tau, row_label_decimals=6,
                native_pressure_kPa_limits=list(limits[0]), nearest_neighbor_over_dp_limits=list(limits[1]),
                xlim_m=list(xlim), ylim_m=list(ylim), case_count=3, soil_IDs_each_case=base.N,
                fixed_IDs_each_case=base.FIXED, soil_markers_per_figure=3*2*base.N,
                fixed_markers_per_figure=3*2*base.FIXED,
                interpolation=False, smoothing=False, clipping=False,
                original_colormaps=True, original_marker_areas=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    need(parser.parse_args().execution_authorized, 'Author-only until independent root plot-only admission')
    targets = [T / 'figures' / (TAG + f'_P{part}.png') for part in base.PARTS]
    check = L / (TAG + '.check.json')
    need(not check.exists() and not any(path.exists() for path in targets), 'Existing complete/partial r3 outputs protected')
    consumed, files = [], []
    result = dict(stage=TAG, passed=False, plot_only=True, physical_acceptance=False,
                  solver_invocations=0, reader_invocations=0, native_decode_invocations=0,
                  build_invocations=0, VTK_invocations=0, SHA_scans=0,
                  original_data_or_plots_rewritten=False, visual_QA_pending=True)
    try:
        gate, old = read(base.SOURCE), read(R2)
        need(gate['passed'] and gate['analysis_complete'] and gate['actual_cases'] == 3 and
             gate['actual_matched_native_states'] == 91 and gate['spatial_rows'] == 45000 and old['passed'],
             'Completed sealed original science and r2 plot generation required; no r2 visual pass implied')
        helper = base.sealed(old['consumed'], Path(base.__file__))
        consumed = [stat(Path(__file__)), stat(NOTE), helper, stat(base.SOURCE), stat(R2)]
        consumed.extend(bind(value) for value in old['files'])
        consumed.extend(bind(value) for value in gate['files'] if Path(value['path']).suffix == '.png')
        groups = base.load_spatial(gate, consumed)
        fixed = {(case, part): base.fixed_positions(root, part, groups[case, part], gate, consumed)
                 for case, root in zip(base.CASES, base.ROOTS) for part in base.PARTS}
        need(all(stat(value['path']) == value for value in consumed), 'Protected data/helper/old plot changed')
        figures = []
        for part, target in zip(base.PARTS, targets):
            figure = render(part, groups, fixed, target)
            previous = [value for value in old['figures'] if value['part'] == part]
            need(len(previous) == 1 and figure == previous[0],
                 'Plot-only repair changed original data limits/times/point counts')
            figures.append(figure)
            files.append(stat(target))
        need(all(stat(value['path']) == value for value in consumed), 'Protected inputs changed while plotting')
        result.update(passed=True, source_scientific_review=stat(base.SOURCE), prior_plot_generation=stat(R2),
                      prior_r2_visual_pass_claimed=False, source_spatial_rows=45000, selected_spatial_rows=30000,
                      figures=figures, exact_r2_limits_times_points_preserved=True,
                      source_native_records_read=6, source_native_arrays_read=['Idp', 'Posd'],
                      source_native_clock_payloads_read=6, consumed=consumed,
                      consumed_stats_unchanged=True, files=files)
    except Exception as error:
        result.update(first_failure=str(error), consumed=consumed, files=files, partial_outputs_preserved=True)
        raise
    finally:
        with check.open('x', encoding='utf-8', newline='\n') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.write('\n')


if __name__ == '__main__':
    main()
