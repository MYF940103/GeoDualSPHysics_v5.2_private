"""Direct raster sampling of visible paper strokes; offline only, no solver imports."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

CASE = Path(__file__).resolve().parents[1]
ROOT = CASE.parents[2]
OUT = CASE / 'figures'
TEST = CASE / 'tests'
TAG = 'lian_hgspr100_r3'
REF = {n: TEST / 'figures' / ('lian_server_return_r1_reference_fig' + n + '.png') for n in ('11', '12')}
ROWS = []


def bound(path):
    path = Path(path)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def masks(path):
    a = np.asarray(Image.open(path).convert('RGB')).astype(int)
    return {'SPH': (a[:, :, 0] > 160) & (a[:, :, 1] < 125) & (a[:, :, 2] < 125),
            'FEM': (a[:, :, 2] > 160) & (a[:, :, 0] < 125) & (a[:, :, 1] < 150)}


def groups(values):
    return [g for g in np.split(values, np.flatnonzero(np.diff(values) > 1) + 1) if len(g)]


def add(fig, method, point, x, y, uncertainty, trace, segment, sample_axis='x', xerr=None, yerr=None):
    row = dict(figure=fig, reference_method=method, paper_point=point, pixel_x=float(x), pixel_y=float(y),
               sample_axis=sample_axis, trace_kind=trace, segment_id=segment, source_page=18,
               source_xref=69 if fig == '11' else 71,
               source_image_sha256=bound(REF['11' if fig == '11' else '12'])['sha256'],
               source_pdf_sha256='c5bb5e8862c87893cd5891758df1d46ea47ddd498e1e61096554e0622756943b',
               branch_resolved=point != 'A/B unresolved')
    if fig == '11':
        row.update(quantity='excess pore pressure', units='kPa', time_s=.01 * 10 ** ((x - 102) / 218),
                   value=(441 - y) / 85.8, value_uncertainty=uncertainty / 85.8,
                   pixel_x_uncertainty=1., pixel_y_uncertainty=uncertainty,
                   time_low_s=.01 * 10 ** ((x - 103) / 218), time_high_s=.01 * 10 ** ((x - 101) / 218))
    elif fig == '12a':
        row.update(quantity='downward settlement', units='m', time_s=.01 * 10 ** ((x - 98) / 161.75),
                   value=(y - 120) * .002 / 307, value_uncertainty=uncertainty * .002 / 307,
                   pixel_x_uncertainty=1., pixel_y_uncertainty=uncertainty,
                   time_low_s=.01 * 10 ** ((x - 99) / 161.75), time_high_s=.01 * 10 ** ((x - 97) / 161.75))
    else:
        row.update(quantity='signed horizontal displacement', units='m', time_s=100.,
                   elevation_m=(428 - y) / 38.6, depth_from_top_m=10 - (428 - y) / 38.6,
                   value=(x - 1218) * 1e-4 / 137.5, value_uncertainty=uncertainty * 1e-4 / 137.5,
                   pixel_x_uncertainty=uncertainty if xerr is None else xerr,
                   pixel_y_uncertainty=1. if yerr is None else yerr)
    row['resolution_limited'] = abs(row['value']) <= row['value_uncertainty']
    ROWS.append(row)


def histories(fig, mm):
    # Legend masks; black/grey axes do not satisfy the colour threshold.
    for mask in mm.values():
        if fig == '11':
            mask[:170, 680:] = False
        else:
            mask[45:165, 485:750] = False
    for method, mask in mm.items():
        xs = range(220, 605, 6) if fig == '11' else range(244 if method == 'SPH' else 286, 740, 6)
        for x in xs:
            if method == 'FEM' and (fig, x) in [('11', 232), ('12a', 322)]:
                continue  # Visually audited marker occlusion: largest gap does not separate A/B.
            if fig == '11' and method == 'FEM' and x >= 534:
                continue  # Peak/falling blue bands overlap; a red occlusion is not an A/B separator.
            y0, y1 = (16, 451) if fig == '11' else (90, 415)
            yy = np.flatnonzero(mask[y0:y1 + 1, x]) + y0
            if len(yy) < 4:
                continue
            if method == 'SPH':
                gg = groups(yy)
                if len(gg) != 2 or min(map(len, gg)) < 2 or np.median(gg[1]) - np.median(gg[0]) < 9:
                    continue
            else:
                # Two separated marker/stroke envelopes, not underlying FEM nodes.
                gaps = np.diff(yy)
                split = int(np.argmax(gaps)) + 1
                if gaps[split - 1] < 7:
                    continue
                gg = [yy[:split], yy[split:]]
                if min(map(len, gg)) < 3 or max(g[-1] - g[0] for g in gg) > 36:
                    continue
                if np.mean([gg[1][0], gg[1][-1]]) - np.mean([gg[0][0], gg[0][-1]]) < 14:
                    continue
            for i, g in enumerate(gg):
                y = (g[0] + g[-1]) / 2
                point = ('A', 'B')[i] if fig == '11' else ('B', 'A')[i]
                trace = 'visible_red_stroke_midspan' if method == 'SPH' else 'visible_blue_marker_stroke_envelope_midspan'
                segment = 'rise' if fig == '11' and x <= 532 else ('fall' if fig == '11' else 'history')
                add(fig, method, point, x, y, max(3., (g[-1] - g[0]) / 2 + 1), trace, segment)
        if fig == '11':
            for x in range(622 if method == 'SPH' else 574, 952, 8):
                y0 = 340 if method == 'SPH' else 240
                yy = np.flatnonzero(mask[y0:453, x]) + y0
                if len(yy) < 2:
                    continue
                # One merged envelope: never assign it to two independent A/B branches.
                add(fig, method, 'A/B unresolved', x, (yy[0] + yy[-1]) / 2,
                    max(3., (yy[-1] - yy[0]) / 2 + 1), 'merged_branch_envelope', 'unresolved_tail')


def profile(mm):
    # The lower-left legend is away from the physical profile, whose x >= 1210 there.
    for method, mask in mm.items():
        for y in range(82, 429 if method == 'FEM' else 141, 4):
            xx = np.flatnonzero(mask[y, 1208:1455]) + 1208
            if len(xx) < (3 if method == 'FEM' else 2):
                continue
            add('12b', method, 'section', (xx[0] + xx[-1]) / 2, y,
                max(3., (xx[-1] - xx[0]) / 2 + 1),
                'visible_blue_profile_envelope_midspan' if method == 'FEM' else 'visible_red_upper_profile_fragment',
                'profile_rows', 'y')
        # Upper nearly-horizontal turn is sampled by columns, not by long horizontal row spans.
        for x in range(1000, 1380, 22):
            yy = np.flatnonzero(mask[43:90, x]) + 43
            if not len(yy):
                continue
            add('12b', method, 'section', x, (yy[0] + yy[-1]) / 2, 3.,
                'visible_red_upper_fragment_not_exact_center' if method == 'SPH' else 'visible_upper_profile_column',
                'upper_turn', 'x', yerr=max(2., (yy[-1] - yy[0]) / 2 + 1))
    # Clearly visible blue end diamond, not a fabricated red endpoint.
    add('12b', 'FEM', 'section', 931, 42, 5., 'visible_blue_endpoint_diamond', 'endpoint', 'manual', yerr=4.)


def main():
    names = ['reference.csv', 'comparison.csv', 'fig11_compare.png', 'fig12_compare.png']
    assert not (TEST / 'logs' / (TAG + '.final_review.json')).exists(), 'Sealed analysis must not be overwritten'
    if any((OUT / (TAG + '_' + n)).exists() for n in names):
        prior = json.loads((TEST / 'logs' / (TAG + '.plots.json')).read_text(encoding='utf8'))
        assert prior['visual_review_passed'] is False, 'Only this new, unsealed analysis can be revised'
    history_path = OUT / 'lian_hgspr100_r2_history.csv'
    profile_path = OUT / 'lian_hgspr100_r1_horizontal_profile.csv'
    h = pd.read_csv(history_path, float_precision='round_trip')
    p = pd.read_csv(profile_path, float_precision='round_trip')
    assert len(h) == 2081 and len(p) == 101 and h.time_s.is_monotonic_increasing
    old = json.loads((TEST / 'logs/lian_server_return_r1_reference_points.json').read_text(encoding='utf8'))
    for src in old['sources']:
        assert bound(src['path'])['sha256'] == src['sha256']
    histories('11', masks(REF['11']))
    histories('12a', masks(REF['12']))
    profile(masks(REF['12']))
    r = pd.DataFrame(ROWS).sort_values(['figure', 'reference_method', 'paper_point', 'time_s', 'elevation_m']).reset_index(drop=True)
    r.insert(0, 'reference_id', np.arange(1, len(r) + 1))
    assert not r.duplicated(['figure', 'reference_method', 'paper_point', 'pixel_x', 'pixel_y']).any()
    compare = []
    for row in r.to_dict('records'):
        if not row['branch_resolved']:
            continue
        if row['figure'] == '12b':
            row.update(current_value=float(np.interp(row['elevation_m'], p.z0_m, p.ux_m)),
                       comparison_basis='unchanged100s_initial_material_x0_1.25m_profile')
            # Propagate vertical pixel-coordinate uncertainty onto a separate native coordinate sensitivity.
            dz = row['pixel_y_uncertainty'] / 38.6
            z = row['elevation_m']
            row['native_coordinate_sensitivity'] = float(max(abs(np.interp(z + dz, p.z0_m, p.ux_m) - row['current_value']),
                                                            abs(np.interp(z - dz, p.z0_m, p.ux_m) - row['current_value'])))
        else:
            col = row['paper_point'] + ('_pressure_pa' if row['figure'] == '11' else '_settlement_mm')
            row['current_value'] = float(np.interp(row['time_s'], h.time_s, h[col] * .001))
            j = min(max(int(np.searchsorted(h.time_s, row['time_s'])), 1), len(h) - 1)
            row.update(native_before_time_s=float(h.time_s.iloc[j - 1]), native_after_time_s=float(h.time_s.iloc[j]),
                       source_before=h.source_tag.iloc[j - 1], source_after=h.source_tag.iloc[j],
                       comparison_basis='native_linear_time_interpolation_at_observed_raster_coordinate_only')
            lo, hi = row['time_low_s'], row['time_high_s']
            row['native_coordinate_sensitivity'] = float(max(abs(np.interp(lo, h.time_s, h[col] * .001) - row['current_value']),
                                                            abs(np.interp(hi, h.time_s, h[col] * .001) - row['current_value'])))
        row['current_minus_reference'] = row['current_value'] - row['value']
        compare.append(row)
    c = pd.DataFrame(compare)
    r.to_csv(OUT / (TAG + '_reference.csv'), index=False, float_format='%.17g')
    c.to_csv(OUT / (TAG + '_comparison.csv'), index=False, float_format='%.17g')
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10})
    styles = {'A': ('#245d88', '-'), 'B': ('#b36a26', '--')}
    def refs(ax, fig, scale=1):
        for method, color in [('SPH', '#d0342c'), ('FEM', '#6842ba')]:
            for point, marker in [('A', '^'), ('B', 'o')]:
                s = r[(r.figure == fig) & (r.reference_method == method) & (r.paper_point == point)]
                ax.errorbar(s.time_s, s.value * scale, yerr=s.value_uncertainty * scale,
                            fmt=marker, ms=3, lw=.5, mfc='none', color=color, alpha=.8,
                            label='Paper ' + method + ' ' + point + ' (raster)')
        ax.set_xscale('log')
        ax.set_xticks([.01, .1, 1, 10, 100], ['0.01', '0.1', '1', '10', '100'])
        ax.set_xlim(.01, 100)
        ax.grid(alpha=.2)
    pos = h.time_s > 0
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), layout='constrained')
    axes[0].imshow(Image.open(REF['11'])); axes[0].axis('off'); axes[0].set_title('Original paper Fig11 (embedded raster)')
    ax = axes[1]
    for point, (color, ls) in styles.items():
        ax.plot(h.time_s[pos], h.loc[pos, point + '_pressure_pa'] / 1000, ls, color=color, lw=1.8, label='Current ' + point)
    refs(ax, '11')
    for method, color in [('SPH', '#757575'), ('FEM', '#a58fcd')]:
        tail = r[(r.figure == '11') & ~r.branch_resolved & (r.reference_method == method)]
        ax.errorbar(tail.time_s, tail.value, yerr=tail.value_uncertainty, fmt='.', ms=3, color=color,
                    alpha=.65, lw=.5, label='Paper ' + method + ' A/B unresolved')
    ax.set(xlabel='Time (s)', ylabel='Excess pore pressure (kPa)', ylim=(-.12, 5))
    ax.legend(fontsize=8, loc='upper left')
    fig.suptitle('Lian Fig11: denser directly sampled SPH / FEM strokes; current solution unchanged\nError bars: raster stroke envelopes, not statistical confidence; hidden branches are not imputed.', fontsize=11)
    fig.savefig(OUT / (TAG + '_fig11_compare.png'), dpi=180); plt.close(fig)
    fig = plt.figure(figsize=(14, 9), layout='constrained')
    grid = fig.add_gridspec(2, 2, height_ratios=[.9, 1])
    ax = fig.add_subplot(grid[0, :]); ax.imshow(Image.open(REF['12'])); ax.axis('off'); ax.set_title('Original paper Fig12')
    ax = fig.add_subplot(grid[1, 0])
    for point, (color, ls) in styles.items():
        ax.plot(h.time_s[pos], h.loc[pos, point + '_settlement_mm'], ls, color=color, lw=1.8, label='Current ' + point)
    refs(ax, '12a', 1000)
    ax.set(xlabel='Time (s)', ylabel='Downward settlement (mm)', ylim=(2, -.5)); ax.legend(fontsize=8)
    ax = fig.add_subplot(grid[1, 1]); ax.plot(p.ux_m * 1000, p.z0_m, color='#245d88', label='Current material x0=1.25 m')
    for method, color, marker in [('SPH', '#d0342c', 'o'), ('FEM', '#6842ba', 'D')]:
        s = r[(r.figure == '12b') & (r.reference_method == method)]
        ax.errorbar(s.value * 1000, s.elevation_m, xerr=s.value_uncertainty * 1000,
                    yerr=s.pixel_y_uncertainty / 38.6, fmt=marker, ms=3, mfc='none', color=color, lw=.5,
                    label='Paper ' + method + ' visible raster')
    ax.set(xlabel='Signed horizontal displacement (mm)', ylabel='Initial elevation (m)', ylim=(0, 10))
    ax.grid(alpha=.2); ax.legend(fontsize=8, loc='lower left')
    fig.suptitle('Lian Fig12: dense raster reference comparison (100 s profile unchanged)\nLower SPH profile is obscured by FEM: no red trajectory was filled; coordinate uncertainty is retained.', fontsize=11)
    fig.savefig(OUT / (TAG + '_fig12_compare.png'), dpi=180); plt.close(fig)
    for number, image in REF.items():
        fig, ax = plt.subplots(figsize=(15 if number == '12' else 12, 6))
        ax.imshow(Image.open(image))
        for method, color in [('SPH', '#00a452'), ('FEM', '#d100b8')]:
            s = r[(r.figure == '11' if number == '11' else r.figure.isin(['12a', '12b'])) & (r.reference_method == method)]
            ax.scatter(s.pixel_x, s.pixel_y, s=12, facecolors='none', edgecolors=color, linewidths=.7, label=method + ' digitized midspan')
        ax.set(xlim=(0, Image.open(image).width), ylim=(Image.open(image).height, 0))
        ax.legend(fontsize=8); ax.set_title('Direct raster-coordinate audit; no smoothing or reconstructed paper values')
        fig.savefig(TEST / 'figures' / (TAG + '_fig' + number + '_overlay.png'), dpi=160); plt.close(fig)
    counts = r.groupby(['figure', 'reference_method', 'paper_point']).size()
    outputs = [OUT / (TAG + '_' + n) for n in names] + [TEST / 'figures' / (TAG + '_fig' + n + '_overlay.png') for n in ('11', '12')]
    for path in outputs:
        if path.suffix == '.png':
            with Image.open(path) as im:
                im.verify()
    result = dict(passed=True, visual_review_passed=False, utc=datetime.now(timezone.utc).isoformat(),
                  reference_rows=len(r), comparison_rows=len(c), old_reference_rows=25,
                  manually_excluded_fem_columns={'11': [232], '12a': [322]},
                  counts=[dict(figure=k[0], method=k[1], point=k[2], rows=int(v)) for k, v in counts.items()],
                  physical_solution_changed=False, cryer_files_or_processes_changed=False,
                  sources=[bound(x) for x in [Path(__file__), history_path, profile_path,
                           TEST / 'logs/lian_server_return_r1_reference_points.json', *REF.values(), ROOT / 'src/papers/PDF/Lian 2023 u-pl.pdf']],
                  artifacts=[bound(x) for x in outputs],
                  limitations=['Direct visible-pixel samples, not original SPH/FEM numerical output or independent statistical observations.',
                    'FEM marker/stroke envelope midpoint is approximate, with full envelope uncertainty; not a fitted hidden line.',
                    'Pressure branches merging in the tail are stored as unresolved, not independently assigned A/B.',
                    'Near-vertical FEM pressure peak omitted; falling FEM branches overlap and are unresolved. Red occlusion gaps are not treated as A/B separators.',
                    'Lower red horizontal-displacement profile is occluded; omitted, not interpolated from FEM or current solution.',
                    '3px minimum reading envelopes and separate time/elevation-coordinate uncertainties are not confidence intervals.',
                    'No interpolation of paper samples; native time/elevation interpolation is only for pointwise comparison, never a regression gate.',
                    'Initial-material profile is compared to paper section whose material/current coordinate convention is unspecified.',
                    'Current 2081-row merged history and 101-row 100s profile, formal inputs and solver output are unchanged.'])
    with (TEST / 'logs' / (TAG + '.plots.json')).open('w', encoding='utf8') as f:
        json.dump(result, f, indent=2, allow_nan=False)
    print(json.dumps({k: result[k] for k in ['reference_rows', 'comparison_rows', 'counts']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
