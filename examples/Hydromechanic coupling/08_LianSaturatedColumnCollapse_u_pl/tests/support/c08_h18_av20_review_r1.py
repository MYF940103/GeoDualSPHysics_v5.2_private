"""One future AV.2 candidate analysis versus sealed AV.1 CSVs; no solver or decoder."""
import argparse
import csv
import json
import math
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

T = Path(__file__).resolve().parents[1]
TAG = 'c08_h18_av20_review_r1'
RUN = 'c08_h18_av20_window_GPU_r1'
CONTROL = 'c08_h18_as03_n255_r1'
CONTROL_REVIEW = T/'logs/c08_h18_as03n255_review_r1.check.json'
SOURCE = 'c08_h18_wend_psi0_pre_r2'
ROOT = T/'outputs'/RUN/'native_r1'
READER_BUILD = T/'logs/c08_h18_av20_native_r1.build.json'
PARTS = (30, 60, 90)
REQUESTS = (.3, .6, .9)
PAIRS = ((6767, 6865), (4953, 4954))
METRICS = ('p_mean_Pa', 'p_RMS_Pa', 'p_min_Pa', 'p_max_Pa', 'native_p_minus_fixedP0_RMS_Pa',
           'effective_stress_Frobenius_RMS_Pa', 'total_stress_Frobenius_RMS_Pa',
           'top_material_settlement_mm', 'bottom_material_settlement_mm', 'mean_settlement_reference_mm',
           'runout_from_PRE_front_m', 'velocity_RMS_m_s', 'max_kappa', 'min_J', 'max_J',
           'NN_min_over_dp', 'NN_q05_over_dp', 'pairs_r_lt_0p7dp')


def need(value, text):
    if not bool(value): raise RuntimeError(text)


def stat(path):
    path = Path(path).resolve(); s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def table(path):
    with Path(path).open(newline='', encoding='utf-8-sig') as f: return list(csv.DictReader(f))


def write(path, rows):
    need(rows, 'Nonempty derived CSV required')
    with path.open('x', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native-receipt', type=Path, required=True)
    p.add_argument('--execution-authorized', action='store_true')
    args = p.parse_args(); need(args.execution_authorized, 'Root must separately admit this offline analysis')
    # Only pure existing dtype/read22/analyze_case primitives are reused; no old load_receiver policy gate.
    import c08_h18_compare_r2 as old
    np, plt = old.np, old.plt
    from matplotlib.colors import Normalize, TwoSlopeNorm
    prefix = T/'figures'/TAG; check = T/'logs'/(TAG+'.check.json')
    need(not check.exists() and not list(prefix.parent.glob(TAG+'_*')), 'Existing complete/partial review protected')
    run_path = T/'logs'/(RUN+'.run.json')
    consumed = [stat(Path(__file__)), stat(T/'notes'/(TAG+'.md')), stat(Path(old.__file__)),
                stat(CONTROL_REVIEW), stat(run_path), stat(args.native_receipt)]

    def bound(entry):
        need(stat(entry['path']) == entry, 'Bound input changed: '+entry['path'])
        consumed.append(entry); return Path(entry['path']).resolve()

    control_review, run, native = read(CONTROL_REVIEW), read(run_path), read(args.native_receipt)
    need(control_review['analysis_complete'] and control_review['consumed_stats_unchanged']
         and control_review['exact_matching_option_rows'] == 91 and not control_review['physical_acceptance'],
         'Sealed two-case short control review required')
    need(run['passed'] and run['solver_completed'] and run['actual_exit'] == run['actual_Win32_exit'] == 0
         and run['actual_steps'] == 2180000 and run['saved_frames'] == 91
         and run['job']['tag'] == RUN and run['job']['backend'] == 'GPU'
         and run['expected_release_AV'] == .2 and run['certified_input_AV'] == .1,
         'Only completed actual GPU AV.2 .90s window admitted')
    need(native['passed'] and native['consumed_stats_unchanged'] and native['reader_invocations'] == 1
         and Path(native['native_completion']['path']).resolve() == ROOT/'completion.json'
         and Path(native['metadata']['path']).resolve() == ROOT/'bedkeep_metadata.json'
         and Path(native['reader_build']['path']).resolve() == READER_BUILD.resolve(),
         'Unique passed AV20 native receipt bound to this fixed candidate required')
    done, meta = read(bound(native['native_completion'])), read(bound(native['metadata']))
    reader_call = read(bound(native['actual_call'])); rb = read(bound(native['reader_build']))
    need(reader_call['actual_Popen_wait_exit'] == reader_call['actual_Win32_exit'] == 0
         and reader_call['ownership_failure'] is None and rb['passed'], 'Actual unique reader/build exit failed')
    need(done['passed'] and done['samples'] == 91 and done['completed_steps'] == 2180000
         and done['backend_argument'] == 'GPU' and done['typed_arrays'] == 22
         and done['actual_native_IDs_per_frame'] == 6805 and done['soil_IDs'] == 5000
         and done['receiver_part0_is_real_post_not_t0_or_PRE'] and not done['keep_bed_overlap']
         and not done['reaction_J_Darcy_closed'], 'Original full91/22/bedroles numerical checks required')
    need(meta['passed'] and meta['stage'] == 'c08_h18_av20_native_r1.metadata' and meta['profile'] == 'window'
         and meta['backend_argument'] == 'GPU' and meta['samples'] == meta['AV_override_headers'] == 91
         and meta['AV_policy'] == 'ReleaseOnly' and meta['AV_override_active_expected']
         and meta['AV_coefficient_float_reference'] == old.f32(.2)
         and meta['AS_coefficient_float_reference'] == old.f32(.3)
         and meta['AS_exponent_float_reference'] == old.f32(2.55)
         and not meta['source_PRE_AV_metadata_required'], 'All91 typed actual AV.2/AS03 headers must pass first')
    # Private target program/capture and original certified PRE are different provenance roles.
    target_build = read(bound(run['source_build'])); private = read(bound(run['source_capture']))
    bound(run['program']); bound(run['source_archive']); bound(run['base_original_source_capture'])
    bound(run['base_original_source_archive']); bound(run['source_pre_file'])
    need(target_build['passed'] and target_build['consumed_stats_unchanged']
         and target_build['allowed_runtime_backend'] == 'GPU' and target_build['program'] == run['program']
         and target_build['source_capture'] == run['source_capture'] and target_build['source_archive'] == run['source_archive']
         and target_build['base_original_source_capture'] == run['base_original_source_capture']
         and target_build['base_original_source_archive'] == run['base_original_source_archive']
         and run['source_capture'] != run['base_original_source_capture']
         and private['archive'] == run['source_archive'] and private['baseline_archive'] == run['base_original_source_archive']
         and private['only_release_AV_override_and_actual_metadata_changed']
         and private['reverse_reconstruction_original_bytes_exact'] and private['released_AV_literal'] == '.2f'
         and private['preload_input_AV_literal'] == '.1f' and not private['class_layout_changed'],
         'Private AV.2 target build must not be mistaken for the original AV.1 PRE program')
    xml = ET.parse(bound(run['input_xml'])).getroot()
    pars = {q.get('key'): q.get('value') for q in xml.findall('execution/parameters/parameter')}
    need(all(old.f32(pars[k]) == old.f32(v) for k, v in dict(Kernel=2, Visco=.1, DtFixed=5e-6,
              ArtificialStressCoef=.3, ArtificialStressExp=2.55).items()), 'Certified XML remains original AV.1/AS03 input')
    kw = float(xml.find('execution/special/hydromechanics/PoreWaterBulkModulus').get('value'))
    need(kw == 1e9, 'Original finite Kw retained')
    sealed = {Path(q['path']).resolve(): q for q in control_review['consumed']}
    oldfiles = {Path(q['path']).resolve(): q for q in control_review['files']}
    need(sealed[Path(run['base_original_source_capture']['path']).resolve()] == run['base_original_source_capture']
         and sealed[Path(run['source_pre_file']['path']).resolve()] == run['source_pre_file'],
         'Original PRE origin must agree with retained control, not the private target source')
    controls = {}
    for name in ('history', 'fields', 'tracks'):
        path = T/'figures'/('c08_h18_as03n255_review_r1_'+name+'.csv')
        controls[name] = [q for q in table(bound(oldfiles[path.resolve()])) if q['tag'] == CONTROL]
    need(len(controls['history']) == 91 and len(controls['tracks']) == 455,
         'Only retained AS03 AV.1 history and original five tracks are controls')
    # Native receipt may bind these in consumed or files; never fall back to an unbound native payload.
    native_bindings = {Path(q['path']).resolve(): q for q in native.get('consumed', [])+native.get('files', [])}
    for leaf in ('typed22.bin', 'typed22_layout.csv', 'clocks.csv'):
        need((ROOT/leaf).resolve() in native_bindings, 'Unique native receipt lacks output stat: '+leaf)
        bound(native_bindings[(ROOT/leaf).resolve()])
    clocks = table(ROOT/'clocks.csv')
    need(len(clocks) == 91, 'Full91 actual clocks required')

    def mapped(root, nodes, count):
        layout = table(root/'typed22_layout.csv'); fields = [('time', '<f8')]
        need(len(layout) == 22, 'Original22 literal layout required')
        for row, (name, kind, width) in zip(layout, old.SCHEMA):
            need((row['array'], row['type'], int(row['components']), int(row['bytes_per_particle']))
                 == (name, kind, width, old.TYPES[kind].itemsize*width), 'Original22 dtype differs')
            fields.append((name, old.TYPES[kind], (nodes, width)))
        dtype = np.dtype(fields, align=False)
        with (root/'typed22.bin').open('rb') as f: need(struct.unpack('<III', f.read(12)) == (nodes, 22, count), 'Native header differs')
        need((root/'typed22.bin').stat().st_size == 12+count*dtype.itemsize, 'Native payload extent differs')
        return np.memmap(root/'typed22.bin', dtype=dtype, offset=12, mode='r', shape=(count,))

    source_root = T/'outputs'/SOURCE/'native_r1'
    for leaf in ('completion.json', 'typed22.bin', 'typed22_layout.csv'):
        bound(sealed[(source_root/leaf).resolve()])
    source_done = read(source_root/'completion.json')
    need(source_done['passed'] and source_done['certified_PRE'] and not source_done['partial']
         and source_done['samples'] == 1001 and source_done['completed_steps'] == 2000000,
         'Existing original same-material PRE reference required, no source reanalysis')
    frames = source_frames = None
    result = dict(stage=TAG, analysis_complete=False, physical_acceptance=False, winner_selected=False, consumed=consumed,
                  new_candidate_metric_analyses=0, retained_control_native_scans=0, retained_control_metric_reanalyses=0,
                  solver_invocations=0, decoder_invocations=0, VTK_invocations=0, SHA_scans=0)
    outputs = []
    try:
        frames = mapped(ROOT, 6805, 91); source_frames = mapped(source_root, 7060, 1001)
        expected = np.concatenate((np.arange(1805, dtype=np.uint32), np.arange(2060, 7060, dtype=np.uint32)))
        need(np.array_equal(source_frames[0]['Idp'][:, 0], np.arange(7060, dtype=np.uint32))
             and np.array_equal(source_frames[1000]['Idp'][:, 0], np.arange(7060, dtype=np.uint32)), 'Original source reference ID order required')
        reference = dict(initial_pos=np.array(source_frames[0]['Posd']), pos=np.array(source_frames[1000]['Posd']),
                         p0=np.array(source_frames[1000]['PorePress0'][:, 0]), time=float(source_frames[1000]['time']), source=SOURCE)
        need(reference['time'] == done['source_actual_time_s'], 'Candidate/control share actual PRE clock')
        bundle = dict(spec=dict(tag=RUN, source=SOURCE, group='psi0', actualAS=dict(coefficient=.3, exponent=2.55)),
                      source=False, root=ROOT, count=91, nodes=6805, expected=expected, done=done, frames=frames,
                      clocks=clocks, kw=kw, yield_rows={}, runtime_observed=dict(passed=True, solver_completed=True,
                          actual_exit=run['actual_exit'], actual_Win32_exit=run['actual_Win32_exit']))
        analysis = old.analyze_case(bundle, reference, REQUESTS)
        front_pre = float(reference['pos'][2060:, 0].max())
        for q in analysis['history']:
            q['runout_from_PRE_front_m'] = q['front_x_m']-front_pre; q['AV_coefficient'] = old.f32(.2)
        control_history = sorted(controls['history'], key=lambda q: int(q['part']))
        matched = []
        for a, b in zip(control_history, analysis['history']):
            need(int(a['part']) == b['part'] and int(a['completed_step']) == b['completed_step']
                 and float(a['time_s']) == b['time_s'] and float(a['tau_s']) == b['tau_s'],
                 'All91 option comparisons require genuine equal actual clocks/steps, no interpolation')
            row = dict(part=b['part'], time_s=b['time_s'], tau_s=b['tau_s'], completed_step=b['completed_step'])
            for key in METRICS:
                row['AV01_'+key], row['AV02_'+key] = float(a[key]), b[key]
                row['difference_AV02_minus_AV01_'+key] = b[key]-float(a[key])
            matched.append(row)
        fields, snapshot_pairs = [], {}
        for part in PARTS:
            base = [q for q in controls['fields'] if int(q['part']) == part]
            snap = analysis['snapshots'][part]; h = analysis['history'][part]
            need(len(base) == 5000 and {int(q['native_id']) for q in base} == set(range(2060, 7060))
                 and all(float(q['time_s']) == snap['time_s'] and float(q['tau_s']) == snap['tau_s'] for q in base),
                 'Three exact5000-ID actual-matched control field snapshots required')
            for q in base:
                fields.append(dict(tag=CONTROL, AV_coefficient=old.f32(.1), part=part, time_s=snap['time_s'], tau_s=snap['tau_s'],
                    completed_step=h['completed_step'], native_id=int(q['native_id']), x_m=float(q['x_m']), z_m=float(q['z_m']),
                    p_Pa=float(q['p_Pa']), native_p_minus_fixedP0_Pa=float(q['native_p_minus_fixedP0_Pa']),
                    kappa=float(q['kappa']), J=float(q['J'])))
            for i in range(5000):
                fields.append(dict(tag=RUN, AV_coefficient=old.f32(.2), part=part, time_s=snap['time_s'], tau_s=snap['tau_s'],
                    completed_step=h['completed_step'], native_id=i+2060, x_m=float(snap['pos'][i, 0]), z_m=float(snap['pos'][i, 2]),
                    p_Pa=float(snap['p'][i]), native_p_minus_fixedP0_Pa=float(snap['excess'][i]),
                    kappa=float(snap['kappa'][i]), J=float(snap['J'][i])))
            snapshot_pairs[part] = {int(q['native_id']): q for q in base}
        pair_rows = []
        for part, h in enumerate(analysis['history']):
            x = frames[part]  # Narrow four-ID extraction only; no second analyze_case/full-field safety pass.
            for a, b in PAIRS:
                ia, ib = a-255, b-255; delta = x['Posd'][ib]-x['Posd'][ia]; distance = float(np.linalg.norm(delta))
                closing = -float((x['Vel'][ib].astype(float)-x['Vel'][ia].astype(float))@(delta/distance)) if distance else None
                pair_rows.append(dict(tag=RUN, pair=f'{a}_{b}', part=part, time_s=h['time_s'], tau_s=h['tau_s'],
                    completed_step=h['completed_step'], distance_over_dp=distance/.04, closing_m_s=closing,
                    pressure_a_Pa=float(x['PorePress'][ia, 0]), pressure_b_Pa=float(x['PorePress'][ib, 0]),
                    kappa_a=float(x['Kplastic'][ia, 0]), kappa_b=float(x['Kplastic'][ib, 0]),
                    J_a=float(x['PoroVolumeRatio'][ia, 0]), J_b=float(x['PoroVolumeRatio'][ib, 0]),
                    baseline_has_only_three_position_snapshots=False))
                if part in PARTS:
                    aa, bb = snapshot_pairs[part][a], snapshot_pairs[part][b]
                    pair_rows.append(dict(tag=CONTROL, pair=f'{a}_{b}', part=part, time_s=h['time_s'], tau_s=h['tau_s'],
                        completed_step=h['completed_step'], distance_over_dp=math.hypot(float(bb['x_m'])-float(aa['x_m']), float(bb['z_m'])-float(aa['z_m']))/.04,
                        closing_m_s=None, pressure_a_Pa=float(aa['p_Pa']), pressure_b_Pa=float(bb['p_Pa']),
                        kappa_a=float(aa['kappa']), kappa_b=float(bb['kappa']), J_a=float(aa['J']), J_b=float(bb['J']),
                        baseline_has_only_three_position_snapshots=True))
        common_keys = list(analysis['history'][0])
        combined = [{key: old.f32(.1) if key == 'AV_coefficient' else q[key] for key in common_keys} for q in control_history]+analysis['history']
        for suffix, rows in (('history', combined), ('matched91', matched), ('fields', fields), ('pairs', pair_rows),
                             ('tracks', controls['tracks']+analysis['tracks'])):
            dest = Path(str(prefix)+'_'+suffix+'.csv'); write(dest, rows); outputs.append(dest)

        colors = {CONTROL: '#2467ac', RUN: '#c44721'}
        titles = {CONTROL: 'AV=0.1, retained', RUN: 'AV=0.2, release only'}
        cases = ((CONTROL, control_history), (RUN, analysis['history']))
        fig, axes = plt.subplots(3, 3, figsize=(16, 12), layout='constrained')
        panels = (('Pressure mean / RMS [kPa]', ('p_mean_Pa', 'p_RMS_Pa'), .001),
                  ('Pressure extrema [kPa]', ('p_min_Pa', 'p_max_Pa'), .001),
                  ('Effective / total stress RMS [kPa]', ('effective_stress_Frobenius_RMS_Pa', 'total_stress_Frobenius_RMS_Pa'), .001),
                  ('Fixed top / bottom settlement from PRE [mm]', ('top_material_settlement_mm', 'bottom_material_settlement_mm'), 1.),
                  ('Front advance from same PRE [m]', ('runout_from_PRE_front_m',), 1.),
                  ('Velocity RMS [m/s]', ('velocity_RMS_m_s',), 1.),
                  ('Nearest-distance min / 5% over dp', ('NN_min_over_dp', 'NN_q05_over_dp'), 1.),
                  ('Pairs at r < 0.7dp [count]', ('pairs_r_lt_0p7dp',), 1.),
                  ('Maximum plastic history', ('max_kappa',), 1.))
        for axis, (title, keys, scale) in zip(axes.flat, panels):
            for tag, rows in cases:
                for j, key in enumerate(keys):
                    axis.plot([float(q['tau_s']) for q in rows], [float(q[key])*scale for q in rows],
                              color=colors[tag], ls='-' if j == 0 else '--', label=titles[tag]+' '+key)
            axis.set(title=title, xlabel='Actual time since PRE [s]'); axis.grid(alpha=.2); axis.legend(fontsize=6.5)
        fig.suptitle('Same AS0.3/n2.55, Wendland H/dp1.8, PRE and 5us: release AV only\nParameter differences are not half-step errors, 5Pa equivalence or paper truth', fontsize=12)
        dest = Path(str(prefix)+'_history.png'); fig.savefig(dest, dpi=180, bbox_inches='tight'); plt.close(fig); outputs.append(dest)
        # Shared full ranges across both options and all three times; retain all extremes and positions.
        xlim = (min(q['x_m'] for q in fields)-.04, max(q['x_m'] for q in fields)+.04)
        zlim = (min(q['z_m'] for q in fields)-.04, max(q['z_m'] for q in fields)+.04)
        for suffix, variables in (('pressure', (('p_Pa', 'Native p [kPa]', .001), ('native_p_minus_fixedP0_Pa', 'Native p-P0 [kPa]', .001))),
                                  ('state', (('kappa', 'Plastic history kappa', 1.), ('J', 'J', 1.)))):
            fig, axes = plt.subplots(4, 3, figsize=(16, 15), layout='constrained')
            for vindex, (key, label, scale) in enumerate(variables):
                values = np.array([q[key]*scale for q in fields]); lo, hi = float(values.min()), float(values.max())
                if lo == hi: lo, hi = lo-1, hi+1
                norm = TwoSlopeNorm(vmin=lo, vcenter=0, vmax=hi) if lo < 0 < hi else Normalize(lo, hi)
                for option, tag in enumerate((CONTROL, RUN)):
                    for col, part in enumerate(PARTS):
                        selected = [q for q in fields if q['tag'] == tag and q['part'] == part]
                        axis = axes[vindex*2+option, col]
                        pc = axis.scatter([q['x_m'] for q in selected], [q['z_m'] for q in selected], c=[q[key]*scale for q in selected],
                                          s=4, cmap='coolwarm' if suffix == 'pressure' else 'viridis', norm=norm, rasterized=True)
                        axis.set(xlim=xlim, ylim=zlim, xlabel='x [m]', ylabel='z [m]',
                                 title=f"{titles[tag]}; actual tau={selected[0]['tau_s']:.6f}s")
                        axis.set_aspect('equal')
                fig.colorbar(pc, ax=axes[vindex*2:vindex*2+2, :], shrink=.7, label=label)
            fig.suptitle('Actual-matched saved material fields; common full color/position ranges\nNative fixed-P0 excess is not the paper plastic-volume excess; no smoothing/clipping', fontsize=12)
            dest = Path(str(prefix)+'_'+suffix+'.png'); fig.savefig(dest, dpi=180, bbox_inches='tight'); plt.close(fig); outputs.append(dest)
        fig, axes = plt.subplots(2, 2, figsize=(13, 8), layout='constrained')
        for col, (a, b) in enumerate(PAIRS):
            selected = [q for q in pair_rows if q['pair'] == f'{a}_{b}']
            new = [q for q in selected if q['tag'] == RUN]; baseline = [q for q in selected if q['tag'] == CONTROL]
            axes[0, col].plot([q['tau_s'] for q in new], [q['distance_over_dp'] for q in new], color=colors[RUN], label='AV.2 all91 saves')
            axes[0, col].scatter([q['tau_s'] for q in baseline], [q['distance_over_dp'] for q in baseline], color=colors[CONTROL], marker='x', s=40, label='AV.1 only3 actual snapshots')
            axes[0, col].axhline(.7, color='gray', ls=':', lw=.8); axes[0, col].set(title=f'Fixed pair {a}/{b}', ylabel='Distance/dp')
            axes[1, col].plot([q['tau_s'] for q in new], [q['closing_m_s'] for q in new], color=colors[RUN], label='AV.2 only; baseline velocity unavailable')
            axes[1, col].axhline(0, color='gray', lw=.8); axes[1, col].set(ylabel='Positive approach speed [m/s]')
            for row in range(2): axes[row, col].set_xlabel('Actual time since PRE [s]'); axes[row, col].grid(alpha=.2); axes[row, col].legend(fontsize=8)
        fig.suptitle('Two previously selected material pairs, not a complete clump detector\nControl closing histories are unavailable; saved correlations do not establish substage causation')
        dest = Path(str(prefix)+'_pairs.png'); fig.savefig(dest, dpi=180, bbox_inches='tight'); plt.close(fig); outputs.append(dest)
        summary = []
        for tag, rows in cases:
            summary.append(dict(tag=tag, p_RMS_peak_Pa=max(float(q['p_RMS_Pa']) for q in rows),
                p_min_Pa=min(float(q['p_min_Pa']) for q in rows), p_max_Pa=max(float(q['p_max_Pa']) for q in rows),
                final={key: float(rows[-1][key]) for key in METRICS}, source='sealed CSVs' if tag == CONTROL else 'one new native analysis'))
        pressure_extrema = [q for q in analysis['extrema'] if q['field'] == 'p']
        result.update(analysis_complete=True, new_candidate_metric_analyses=1, exact_matched_rows=91,
                      candidate_summary=analysis['summary'], option_summary=summary,
                      actual_AV_control_float=old.f32(.1), actual_AV_candidate_float=old.f32(.2),
                      candidate_pressure_extrema=[min(pressure_extrema, key=lambda q: q['value']),
                                                  max(pressure_extrema, key=lambda q: q['value'])],
                      source_native_reference_frames_only=[0, 1000], control_pair_position_snapshots_only=list(PARTS),
                      no_control_pair_closing_history_claim=True, ij_storage_order='xy,yz,xz',
                      native_p_minus_fixedP0_is_not_paper_plastic_excess=True, reaction_J_Darcy_closed=False,
                      parameter_difference_is_not_half_or_physical_error=True, visual_QA_pending=True,
                      outputs=[stat(q) for q in outputs])
    except Exception as error:
        result.update(first_failure=str(error), partial_outputs_preserved=True); raise
    finally:
        for mapping in (frames, source_frames):
            if mapping is not None: mapping._mmap.close()
        with check.open('x', encoding='utf-8') as f: json.dump(result, f, indent=2, allow_nan=False); f.write('\n')


if __name__ == '__main__': main()
