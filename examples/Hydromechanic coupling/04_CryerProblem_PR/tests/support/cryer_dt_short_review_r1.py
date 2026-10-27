"""Offline audit and two scientific figures for the retained five-sample CPU pair."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from pathlib import Path
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from cryer_start_r1 import CASE, TESTS, REPO, READER, READER_SOURCE, bound, native, utc, write_json
from cryer_dt_short_r1 import inspect

TAG = 'cryer_dt_short_review_r1'
RUNS = {'coarse': ('cryer_dt_short_r1_c', 2.5e-6), 'half': ('cryer_dt_short_r1_h', 1.25e-6)}
STYLE = {'coarse': ('#28618e', 'o', '-', 'Coarse: 2.5 us'),
         'half': ('#ae692c', 's', '--', 'Half: 1.25 us')}


def verify(items):
    for entry in items:
        actual = bound(entry['path'])
        assert actual['sha256'] == entry['sha256'] and actual['bytes'] == entry['bytes'], entry['path']


def close(actual, expected):
    assert math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-10), (actual, expected)


def rms(values):
    values = np.asarray(values, dtype=float).ravel()
    return math.sqrt(math.fsum(float(v)*float(v) for v in values)/len(values))


def main():
    check_path = TESTS/'logs'/(TAG+'.check.json')
    note_path = TESTS/'notes'/(TAG+'.md')
    assert not check_path.exists() and not note_path.exists()
    for label, extension in [('history', 'csv'), ('pairs', 'csv'), ('radial', 'csv'),
        ('radial_membership', 'csv'), ('center_ids', 'csv'), ('history', 'png'), ('radial', 'png')]:
        assert not (TESTS/'figures'/(TAG+'_'+label+'.'+extension)).exists()
    run_path = TESTS/'logs/cryer_dt_short_r1.run.json'
    original_check_path = TESTS/'logs/cryer_dt_short_r1.check.json'
    state, original_check = [json.loads(p.read_text()) for p in [run_path, original_check_path]]
    assert state['status'] == original_check['status'] == 'short_pair_rejected_or_interrupted'
    assert not original_check['passed'] and original_check['paired_samples'] == 5
    verify([original_check['run_manifest']]+state['inputs']+state['artifacts'])
    assert len(state['runs']) == 2 and all(r['passed'] and r['owned_exited'] and r['exit_code'] == 0 for r in state['runs'])
    sources = [bound(p) for p in [__file__, run_path, original_check_path, READER, READER_SOURCE,
        TESTS/'support/cryer_start_r1.py', TESTS/'support/cryer_dt_short_r1.py']]
    saved_history = pd.read_csv(TESTS/'figures/cryer_dt_short_r1_summary.csv', float_precision='round_trip')
    saved_pairs = pd.read_csv(TESTS/'figures/cryer_dt_short_r1_half.csv', float_precision='round_trip')
    for key, (name, dt) in RUNS.items():
        record = next(r for r in state['runs'] if r['name'] == name)
        assert record['steps'] == round(.0005/dt) and record['checked_frames'] == 5
        verify(record['outputs'])
        if 'retained_outputs' in record: verify(record['retained_outputs'])
        text = (TESTS/'outputs'/name/'Run.out').read_text(errors='replace')
        assert 'Finished execution (code=0)' in text and 'DBC' in text
        assert int(re.search(r'Steps of simulation\.*:\s*(\d+)', text)[1]) == record['steps']
    history = []; pairs = []; frames = {}; initial = None; center = None
    with ThreadPoolExecutor(max_workers=2) as pool:
        for part in range(5):
            data = dict(zip(RUNS, pool.map(lambda item: native(TESTS/'outputs'/item[0], part), RUNS.values())))
            if initial is None:
                initial = data['coarse']; xyz0 = initial[['x', 'y', 'z']].to_numpy()
                radius0 = np.sqrt(np.einsum('ij,ij->i', xyz0, xyz0))
                center = radius0 <= .0025+1e-12
                assert len(initial) == initial.id.nunique() == 37173 and center.sum() == 18
                assert list(map(int, initial.id.to_numpy()[center])) == state['center_material_ids']
                assert not (radius0 <= 1e-10).any()
            for key, a in data.items():
                assert np.array_equal(a.id, initial.id) and len(a) == 37173
                if part == 0: assert np.array_equal(a[['id', 'x', 'y', 'z']], initial[['id', 'x', 'y', 'z']])
                row, issues = inspect(a, initial, part, RUNS[key][1], center)
                assert not issues, (key, part, issues)
                stored = saved_history[saved_history.run.eq(RUNS[key][0]) & saved_history.part.eq(part)].iloc[0]
                for col, value in row.items():
                    if isinstance(value, bool): assert value == stored[col]
                    else: close(value, stored[col])
                # Independent norm/sum expressions cross-check the published helper's reductions.
                pressure = a.pressure.to_numpy(); position = a[['x', 'y', 'z']].to_numpy()
                independent_rms = rms(pressure)
                independent_center = math.fsum(map(float, pressure[center]))/int(center.sum())
                displacement = position-xyz0
                independent_displacement = 1000*float(np.sqrt(np.einsum('ij,ij->i', displacement, displacement)).max())
                close(independent_rms, row['pressure_rms_pa'])
                close(independent_center, row['center_pressure_mean_pa'])
                close(independent_displacement, row['material_displacement_max_mm'])
                row.update(run=key, output_name=RUNS[key][0], time_ms=row['time_s']*1000,
                    independently_recomputed_pressure_rms_pa=independent_rms,
                    independently_recomputed_center_mean_pa=independent_center,
                    independently_recomputed_material_displacement_mm=independent_displacement)
                history.append(row); frames[key, part] = a
            c, h = data['coarse'], data['half']; p = c.pressure.to_numpy()-h.pressure.to_numpy()
            delta_position = c[['x', 'y', 'z']].to_numpy()-h[['x', 'y', 'z']].to_numpy()
            row = dict(part=part, coarse_time_s=float(c.time_s.iloc[0]), half_time_s=float(h.time_s.iloc[0]),
                coarse_saved_step=int(c.saved_step.iloc[0]), half_saved_step=int(h.saved_step.iloc[0]),
                actual_time_difference_s=abs(float(c.time_s.iloc[0]-h.time_s.iloc[0])),
                pressure_rms_pa=rms(p), pressure_max_abs_pa=float(abs(p).max()),
                material_displacement_max_mm=1000*float(np.sqrt(np.einsum('ij,ij->i', delta_position, delta_position)).max()),
                center_mean_pressure_difference_pa=math.fsum(map(float, p[center]))/int(center.sum()))
            assert row['actual_time_difference_s'] < 1e-12, 'No interpolation or time shifting'
            for field in ['coarse_time_s', 'half_time_s', 'actual_time_difference_s', 'pressure_rms_pa',
                'material_displacement_max_mm', 'center_mean_pressure_difference_pa']:
                close(row[field], saved_pairs[field].iloc[part])
            row.update(time_ms=row['coarse_time_s']*1000,
                pressure_screen_passed=row['pressure_rms_pa'] <= 5,
                displacement_screen_passed=row['material_displacement_max_mm'] <= .005)
            pairs.append(row)
            print('Independently reread CPU pair', part, row['coarse_time_s'], flush=True)
    history = pd.DataFrame(history); pairs = pd.DataFrame(pairs)
    close(pairs.pressure_rms_pa.max(), original_check['max_pressure_rms_pa'])
    close(pairs.material_displacement_max_mm.max(), original_check['max_material_displacement_mm'])
    assert pairs.pressure_screen_passed.tolist() == [True, False, False, False, False]
    assert pairs.displacement_screen_passed.all()
    worst_part = int(pairs.loc[pairs.pressure_rms_pa.idxmax(), 'part']); assert worst_part == 2
    coarse, half = [frames[key, worst_part] for key in RUNS]
    ratio = radius0/.05; bin_index = np.minimum(np.floor(ratio*10).astype(int), 9)
    assert bin_index.min() >= 0 and bin_index.max() == 9
    membership = pd.DataFrame(dict(id=initial.id, initial_radius_m=radius0, initial_radius_over_R=ratio, radial_bin=bin_index))
    center_ids = membership.loc[center].copy()
    radial = []
    difference = coarse.pressure.to_numpy()-half.pressure.to_numpy()
    for index in range(10):
        mask = bin_index == index; assert mask.any()
        ids = np.asarray(initial.id.to_numpy()[mask], dtype='<u8')
        radial.append(dict(radial_bin=index, lower_r0_over_R=index/10, upper_r0_over_R=(index+1)/10,
            last_bin_right_closed=index == 9, native_count=int(mask.sum()),
            initial_radius_over_R_mean=float(ratio[mask].mean()), native_ids_sha256=hashlib.sha256(ids.tobytes()).hexdigest(),
            coarse_time_s=float(coarse.time_s.iloc[0]), half_time_s=float(half.time_s.iloc[0]),
            coarse_pressure_mean_pa=math.fsum(map(float, coarse.pressure.to_numpy()[mask]))/int(mask.sum()),
            half_pressure_mean_pa=math.fsum(map(float, half.pressure.to_numpy()[mask]))/int(mask.sum()),
            coarse_minus_half_mean_pa=math.fsum(map(float, difference[mask]))/int(mask.sum()),
            coarse_minus_half_rms_pa=rms(difference[mask]),
            coarse_minus_half_max_abs_pa=float(abs(difference[mask]).max())))
    radial = pd.DataFrame(radial)
    assert radial.native_count.sum() == 37173 and len(membership) == membership.id.nunique() == 37173
    reconstructed_rms = math.sqrt(float(np.sum(radial.native_count*radial.coarse_minus_half_rms_pa**2))/37173)
    close(reconstructed_rms, pairs.pressure_rms_pa.iloc[worst_part])
    artifacts = []
    def csv(label, data):
        path = TESTS/'figures'/(TAG+'_'+label+'.csv')
        data.to_csv(path, index=False, float_format='%.17g'); artifacts.append(bound(path))
    def png(label, fig):
        path = TESTS/'figures'/(TAG+'_'+label+'.png')
        fig.savefig(path, dpi=165, facecolor='white'); plt.close(fig); artifacts.append(bound(path))
    for label, frame in [('history', history), ('pairs', pairs), ('radial', radial),
        ('radial_membership', membership), ('center_ids', center_ids)]: csv(label, frame)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'axes.titlesize': 12,
        'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.3), layout='constrained')
    for key, (color, marker, line, label) in STYLE.items():
        h = history[history.run.eq(key)]
        axes[0].plot(h.time_ms, h.center_pressure_mean_pa/1000, color=color, marker=marker,
            ls=line, lw=1.6, ms=6, markerfacecolor='white' if key == 'half' else color, label=label)
    axes[0].set(title='Fixed 18-material-node center mean', ylabel='Pore pressure (kPa)')
    axes[0].legend(fontsize=10)
    axes[1].plot(pairs.time_ms, pairs.pressure_rms_pa, color='#28618e', marker='o', lw=1.6, label='Field RMS difference')
    axes[1].axhline(5, color='#353535', ls='--', lw=1.3, label='Original screen: 5 Pa')
    axes[1].set(title='Coarse minus half: all 37173 IDs', ylabel='Pressure RMS difference (Pa)', ylim=(0, 65))
    axes[1].legend(fontsize=10)
    axes[2].plot(pairs.time_ms, pairs.material_displacement_max_mm, color='#ae692c', marker='s', lw=1.6)
    axes[2].set(title='Material displacement difference', ylabel='Maximum vector difference (mm)',
        ylim=(0, float(pairs.material_displacement_max_mm.max())*1.25))
    axes[2].ticklabel_format(axis='y', style='sci', scilimits=(0, 0), useMathText=True)
    axes[2].text(.03, .96, 'Original limit: 0.005 mm\nAbove this zoomed scale; unchanged',
        transform=axes[2].transAxes, ha='left', va='top', fontsize=10)
    for ax in axes:
        ax.set(xlabel='Actual saved time (ms)', xlim=(0, .5), xticks=[0, .125, .25, .375, .5])
        ax.grid(alpha=.2)
    fig.suptitle('Cryer 0.5-ms abrupt-load startup | CPU Release coarse / half\n'
        'Five saved points only: connecting segments are not the resolved transient waveform. No full Cryer acceptance.', fontsize=13)
    png('history', fig)
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4), layout='constrained')
    x = radial.initial_radius_over_R_mean
    for key, (color, marker, line, label) in STYLE.items():
        axes[0].plot(x, radial[key+'_pressure_mean_pa']/1000, color=color, marker=marker, ls='none',
            ms=7, markerfacecolor='white' if key == 'half' else color, label=label)
    axes[0].set(ylabel='Radial-bin mean pressure (kPa)', title='Matched native material bins')
    axes[0].legend(fontsize=10)
    axes[1].plot(x, radial.coarse_minus_half_rms_pa, color='#28618e', marker='o', ls='none', ms=7, label='Bin RMS difference')
    axes[1].plot(x, radial.coarse_minus_half_mean_pa, color='#ae692c', marker='s', ls='none', ms=6,
        markerfacecolor='white', label='Signed bin mean difference')
    axes[1].axhline(0, color='#555555', lw=1.0)
    axes[1].set(ylabel='Coarse minus half (Pa)', title='Differences, not confidence intervals')
    axes[1].legend(fontsize=10)
    for ax in axes:
        ax.set(xlabel='Initial material radius / R (bin mean)', xlim=(0, 1), xticks=[0, .2, .4, .6, .8, 1])
        ax.grid(alpha=.2)
    counts = ', '.join(map(str, radial.native_count))
    fig.suptitle('Cryer abrupt-load startup: largest saved pressure difference at 0.25 ms\n'
        'Ten fixed 0.1R bins; native membership unchanged. No spatial smoothing or full Cryer acceptance.', fontsize=13)
    fig.supxlabel('Native counts, center to surface: '+counts+'\n'
        'Markers are bin aggregates; no shell spread is presented as statistical uncertainty.', fontsize=9)
    png('radial', fig)
    E=2e6; nu=.3; water=2e8; por=.3; density=2100.; radius=.05
    K=E/(3*(1-2*nu)); G=E/(2*(1+nu)); M=K+4*G/3; Mu=M+water/por; c=math.sqrt(Mu/density)
    acoustic = dict(conditional=True, Kd_pa=K, G_pa=G, M_pa=M, Mu_pa=Mu, c_m_s=c,
        R_over_c_us=radius/c*1e6, interpretation='Homogeneous small-strain alpha1/no-relative-flow continuum estimate; not a discrete spectrum, causal proof or timestep acceptance.')
    note = ('# Cryer短步长启动离线复核\n\n'
        f'两组CPU Release正常完成0.5ms，各5个保存帧、37173不变材料IDs。单run原有限值、无排除、弹性、自然步长、渗流步长和真实排水检查均通过。\n\n'
        f'原5Pa场RMS实施筛查未通过：最大{pairs.pressure_rms_pa.max():.9g}Pa，发生在0.25ms；4个非零采样点均超5Pa。'
        f'最大材料位移差{pairs.material_displacement_max_mm.max():.9g}mm，小于原0.005mm阈值。没有放宽门槛，也没有启动其他计算。\n\n'
        '中心量为初始r<=0.0025m+1e-12内固定18个材料点的算术均值，不是假定存在r=0粒子，也不是解析球心真值。'
        f'实际粗/半保存时间最大差{pairs.actual_time_difference_s.max():.9g}s，按保存索引匹配、未插值。\n\n'
        '两图分别显示5个保存点及最大场RMS差时的初始半径聚合；连线不代表完整波形，径向bin不是空间平滑，未提供或暗示置信区间。'
        'bin成员及人数在radial_membership/radial CSV中，中心18个IDs另存。未混用Debug5us或旧root结果。\n\n'
        f'条件性声学量级估算：Mu=M+Kw/n={Mu:.9g}Pa，c={c:.9g}m/s，R/c={radius/c*1e6:.9g}us。'
        '仅适用于均匀、小应变、alpha=1、近似无排水的连续体快速极限；不是离散临界步长、实际波形或因果证明。'
        '本5点数据不解析约0.1ms量级波形，不能只凭时间接近就归因为惯性波。\n\n'
        '这是已完成数据的离线复核，不是完整Cryer、峰值窗口、准静力解析精度或半周期验收。PNG尚待主agent实际view_image检查；记录中visual_review_passed=false。\n')
    note_path.write_text(note, encoding='utf8'); artifacts.append(bound(note_path))
    write_json(check_path, dict(passed=True, offline_audit_passed=True, visual_review_passed=False, utc=utc(),
        sources=sources, artifacts=artifacts, all_frozen_input_output_hashes_verified=True,
        single_runs_safety_passed=True, original_pressure_screen_passed=False,
        original_displacement_screen_passed=True, original_pair_check_passed=False,
        native_ids=37173, original_center_material_ids=state['center_material_ids'], center_material_count=18,
        actual_matched_pairs=5, max_actual_time_difference_s=float(pairs.actual_time_difference_s.max()),
        max_pressure_rms_pa=float(pairs.pressure_rms_pa.max()),
        max_material_displacement_mm=float(pairs.material_displacement_max_mm.max()),
        max_point_pressure_difference_pa=float(pairs.pressure_max_abs_pa.max()),
        worst_saved_part=worst_part, radial_bin_count=10, radial_counts=radial.native_count.tolist(),
        radial_weighted_rms_reconciled_pa=reconstructed_rms, conditional_acoustic_scale=acoustic,
        physical_accepted=False, peak_window_admitted=False,
        limits=['Offline audit passing is not the retained pair screen passing: all4 nonzero saved points exceed original5Pa.',
            'Only5saved points per run; no inferred intermediate peaks, resolved waveform or quasistatic theory truth.',
            'No new solver, reduced step, threshold, production change or use of Debug5us/oldroot comparison.',
            'PNG numerical content verified; rendered appearance remains for root view_image review.']))
    print('PASS offline audit; original5Pa screen FAILED:', pairs.pressure_rms_pa.max(), 'Pa', flush=True)
    print('Figures:', TESTS/'figures'/(TAG+'_history.png'), TESTS/'figures'/(TAG+'_radial.png'), flush=True)


if __name__ == '__main__': main()
