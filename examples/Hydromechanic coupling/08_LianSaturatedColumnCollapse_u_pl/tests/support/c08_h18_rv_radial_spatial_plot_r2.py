"""Plot-only repair of sealed C08 P76/P90 spatial figures; no numerical analysis."""
import argparse
import csv
import json
import math
import struct
from pathlib import Path

TAG = 'c08_h18_rv_radial_spatial_plot_r2'
T = Path(__file__).resolve().parents[1]
L = T / 'logs'
NOTE = T / 'notes' / (TAG + '.md')
SOURCE = L / 'c08_h18_rv_radial_window_review_r1.check.json'
CASES = ('Retained original AS03', 'Vector RV alpha0.1', 'Radial RV alpha0.1')
TITLES = ('Original (RV off)', 'Vector RV alpha=0.1', 'Radial RV alpha=0.1')
ROOTS = tuple(T / 'outputs' / name / 'native_r1' for name in
              ('c08_h18_as03_n255_r1', 'c08_h18_rv_window_GPU_r2',
               'c08_h18_rv_radial_window_GPU_r1'))
PARTS, ALL_PARTS, N, FIXED, DP = (76, 90), (38, 76, 90), 5000, 1805, .04


def need(test, message):
    if not test:
        raise RuntimeError(message)


def stat(path):
    path = Path(path).resolve()
    s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def bind(value):
    need(stat(value['path']) == value, 'Sealed input changed: ' + value['path'])
    return value


def same(a, b):
    return Path(a).resolve() == Path(b).resolve()


def sealed(entries, path):
    matches = [value for value in entries if same(value['path'], path)]
    need(matches and all(value == matches[0] for value in matches),
         'Missing/ambiguous original seal: ' + str(path))
    return bind(matches[0])


def bits(value):
    return struct.pack('<d', float(value))


def load_spatial(gate, consumed):
    path = T / 'figures' / 'c08_h18_rv_radial_window_review_r1_spatial.csv'
    consumed.append(sealed(gate['files'], path))
    groups = {(case, part): [] for case in CASES for part in ALL_PARTS}
    with path.open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            key = row['case'], int(row['part'])
            need(key in groups, 'Unexpected sealed spatial case/frame')
            groups[key].append(row)
    need(sum(map(len, groups.values())) == 45000, 'Original 45000 spatial rows required')
    for key, rows in groups.items():
        need(len(rows) == N and [int(row['native_id']) for row in rows] == list(range(2060, 7060)),
             'All original 5000 ordered material IDs required: ' + str(key))
        need(len({(row['completed_step'], row['actual_time_s'], row['tau_s']) for row in rows}) == 1,
             'Mixed clocks in one original spatial frame')
    return {key: rows for key, rows in groups.items() if key[1] in PARTS}


def fixed_positions(root, part, rows, gate, consumed):
    """Read only original time/Idp/Posd bytes at two already decoded records."""
    import numpy as np
    raw, layout, clocks = (root / leaf for leaf in
                           ('typed22.bin', 'typed22_layout.csv', 'clocks.csv'))
    consumed.extend(sealed(gate['consumed'], path) for path in (raw, layout, clocks))
    with layout.open(encoding='utf-8-sig', newline='') as f:
        fields = list(csv.DictReader(f))
    need(len(fields) == 22 and
         [(row['array'], row['type'], int(row['components']), int(row['bytes_per_particle']))
          for row in fields[:2]] == [('Idp', 'uint32', 1, 4), ('Posd', 'float64', 3, 24)] and
         sum(int(row['bytes_per_particle']) for row in fields) == 212,
         'Original sealed Idp/Posd record layout differs')
    nodes, record_bytes = 6805, 8 + 6805 * 212
    need(raw.stat().st_size == 12 + 91 * record_bytes, 'Original 91-record native extent differs')
    with raw.open('rb') as f:
        need(struct.unpack('<III', f.read(12)) == (nodes, 22, 91), 'Original native header differs')
        f.seek(12 + part * record_bytes)
        clock = f.read(8)
        ids = np.frombuffer(f.read(nodes * 4), dtype='<u4').copy()
        pos = np.frombuffer(f.read(nodes * 24), dtype='<f8').reshape(nodes, 3).copy()
    expected = np.r_[np.arange(FIXED, dtype=np.uint32), np.arange(2060, 7060, dtype=np.uint32)]
    need(np.array_equal(ids, expected) and np.isfinite(pos).all(), 'Original native identity/position differs')
    need(clock == bits(rows[0]['actual_time_s']), 'Unchanged CSV/native actual clock differs')
    csvpos = np.array([[float(row[axis + '_m']) for axis in 'xyz'] for row in rows], dtype='<f8')
    need(pos[FIXED:].tobytes() == csvpos.tobytes(), 'CSV/native original soil positions differ')
    with clocks.open(encoding='utf-8-sig', newline='') as f:
        saved = list(csv.DictReader(f))
    need(len(saved) == 91 and int(saved[part]['part']) == part and
         saved[part]['completed_step'] == rows[0]['completed_step'] and
         bits(saved[part]['time_s']) == clock, 'Original saved-clock record differs')
    return pos[:FIXED]


def render(part, groups, fixed, target):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize

    states = []
    for case in CASES:
        rows = groups[case, part]
        pos = np.array([[float(row[axis + '_m']) for axis in 'xyz'] for row in rows])
        pressure = np.array([float(row['p_Pa']) for row in rows]) / 1000.
        nearest = np.array([float(row['NN_over_dp']) for row in rows])
        need(np.isfinite(pos).all() and np.isfinite(pressure).all() and np.isfinite(nearest).all(),
             'No nonfinite spatial values may be hidden')
        states.append((pos, pressure, nearest))
    times = [(groups[case, part][0]['actual_time_s'], groups[case, part][0]['tau_s']) for case in CASES]
    need(all(tuple(map(bits, value)) == tuple(map(bits, times[0])) for value in times),
         'Three actual saved times must remain identical')
    allpos = np.concatenate([state[0] for state in states])
    fullp = np.concatenate([state[1] for state in states])
    fullnn = np.concatenate([state[2] for state in states])
    xlim = (float(allpos[:, 0].min()) - DP, float(allpos[:, 0].max()) + DP)
    ylim = (float(allpos[:, 2].min()) - DP, float(allpos[:, 2].max()) + DP)
    limits = ((float(fullp.min()), float(fullp.max())), (float(fullnn.min()), float(fullnn.max())))
    need(all(math.isfinite(a) and math.isfinite(b) and a < b for a, b in limits),
         'Original nonconstant full-range color limits required')
    norms = tuple(Normalize(vmin=a, vmax=b, clip=False) for a, b in limits)

    # Fixed margins avoid constrained-layout collapse at these equal-aspect spans.
    fig = plt.figure(figsize=(18, 14))
    grid = fig.add_gridspec(3, 4, width_ratios=(1., .035, 1., .035),
                           left=.055, right=.915, bottom=.065, top=.825,
                           wspace=.24, hspace=.45)
    fig.suptitle('C08: native pressure and particle spacing\n'
                 'All 5000 original soil IDs per case; unchanged values, limits and view',
                 fontsize=16, y=.985)
    time, tau = float(times[0][0]), float(times[0][1])
    fig.text(.5, .935, f'P{part}; actual t={time:.17g} s; actual tau={tau:.17g} s',
             ha='center', fontsize=11)
    fig.text(.5, .907, 'Row labels round tau to 6 decimals only; source CSV and native clocks are unchanged.',
             ha='center', fontsize=10)
    images = [None, None]
    for i, (case, title, state) in enumerate(zip(CASES, TITLES, states)):
        pos, pressure, nearest = state
        for j, (values, cmap, field) in enumerate(((pressure, 'coolwarm', 'Native signed pressure'),
                                                  (nearest, 'viridis', 'Nearest neighbour / dp'))):
            ax = fig.add_subplot(grid[i, 2*j])
            walls = fixed[case, part]
            ax.scatter(walls[:, 0], walls[:, 2], s=3, color='.72', edgecolors='none', rasterized=True)
            images[j] = ax.scatter(pos[:, 0], pos[:, 2], c=values, cmap=cmap, norm=norms[j],
                                   s=6, edgecolors='none', rasterized=True)
            ax.set(xlim=xlim, ylim=ylim, xlabel='Actual x [m]', ylabel='Actual z [m]')
            ax.set_aspect('equal', adjustable='box')
            ax.set_title(f'{title} | {field}\nP{part}; tau={tau:.6f} s (rounded label)', fontsize=10, pad=10)
            ax.tick_params(labelsize=9)
    for j, label in enumerate(('Native p [kPa]\n(full signed linear range)',
                               'Nonself soil NN / dp\n(full range)')):
        bar = fig.colorbar(images[j], cax=fig.add_subplot(grid[:, 2*j+1]))
        bar.set_label(label, fontsize=10, labelpad=14)
        bar.ax.tick_params(labelsize=9)
    need(not target.exists(), 'Existing plot/partial is protected: ' + str(target))
    fig.savefig(target, dpi=180)
    plt.close(fig)
    return dict(part=part, actual_time_s=time, tau_s=tau, row_label_decimals=6,
                native_pressure_kPa_limits=list(limits[0]), nearest_neighbor_over_dp_limits=list(limits[1]),
                xlim_m=list(xlim), ylim_m=list(ylim), case_count=3, soil_IDs_each_case=N,
                fixed_IDs_each_case=FIXED, soil_markers_per_figure=3*2*N,
                fixed_markers_per_figure=3*2*FIXED,
                interpolation=False, smoothing=False, clipping=False,
                original_colormaps=True, original_marker_areas=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    need(parser.parse_args().execution_authorized, 'Author-only until independent root plot-only admission')
    prefix, check = T / 'figures' / TAG, L / (TAG + '.check.json')
    targets = [Path(str(prefix) + f'_P{part}.png') for part in PARTS]
    need(not check.exists() and not any(path.exists() for path in targets), 'Existing complete/partial plot-only outputs protected')
    consumed, files = [], []
    result = dict(stage=TAG, passed=False, plot_only=True, physical_acceptance=False,
                  solver_invocations=0, reader_invocations=0, native_decode_invocations=0,
                  build_invocations=0, VTK_invocations=0, SHA_scans=0,
                  original_data_or_plots_rewritten=False, visual_QA_pending=True)
    try:
        gate = read(SOURCE)
        need(gate['passed'] and gate['analysis_complete'] and gate['actual_cases'] == 3 and
             gate['actual_matched_native_states'] == 91 and gate['spatial_rows'] == 45000,
             'Passed sealed three-case scientific review required')
        consumed = [stat(Path(__file__)), stat(NOTE), stat(SOURCE)]
        for value in gate['files']:
            if Path(value['path']).suffix == '.png':
                consumed.append(bind(value))
        groups = load_spatial(gate, consumed)
        fixed = {(case, part): fixed_positions(root, part, groups[case, part], gate, consumed)
                 for case, root in zip(CASES, ROOTS) for part in PARTS}
        need(all(stat(value['path']) == value for value in consumed), 'Protected input changed before plotting')
        figures = []
        for part, target in zip(PARTS, targets):
            figures.append(render(part, groups, fixed, target))
            files.append(stat(target))
        need(all(stat(value['path']) == value for value in consumed), 'Protected input changed while plotting')
        result.update(passed=True, source_scientific_review=stat(SOURCE), source_spatial_rows=45000,
                      selected_spatial_rows=30000, figures=figures, source_native_records_read=6,
                      source_native_arrays_read=['Idp', 'Posd'], source_native_clock_payloads_read=6,
                      all_source_values_and_actual_times_preserved=True, consumed=consumed,
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
