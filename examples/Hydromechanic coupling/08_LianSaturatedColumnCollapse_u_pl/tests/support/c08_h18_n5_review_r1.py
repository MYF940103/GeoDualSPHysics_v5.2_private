"""Offline all47 N5 saved-state comparison against exact-time first47 original AS.5 states; never decode/run."""
import argparse, json, xml.etree.ElementTree as ET
from pathlib import Path
import c08_h18_centroid_partial_review_r1 as retained
import c08_h18_wend_matrix_r1 as matrix

old, np, T, stat, read = retained.old, retained.np, retained.T, retained.stat, retained.read
TAG = 'c08_h18_n5_review_r1'
RUN, CONTROL = 'c08_h18_as05_n5_r1', 'c08_h18_wend_psi0_a05_w09_r1'
NOTE = T / 'notes' / (TAG + '.md')


def validate_native(done, count):
    assert done['samples'] == count and done['typed_arrays'] == 22 and done['typed_bytes_per_particle'] == 212
    assert done['actual_native_IDs_per_frame'] == 6805 and done['soil_IDs'] == 5000 and done['actual_fixed_IDs'] == 1805
    assert done['ledger_checks'] == done['rho_cache_bits_checks'] == done['kappa_nondecreasing_from_PRE_checks'] == 5000*count
    assert done['P0_bits_checks'] == 6805*count and done['fixed_marker_checks'] == 1805*count
    assert done['plane_gap_checks'] == 10000*count and done['nonempty_signed_intervals'] == count
    assert done['max_scalar_clock_error_s'] <= 1e-14 and done['max_signed_dterror_s'] <= 1e-14
    assert done['max_ledger_relative_error'] <= 5e-13 and done['FS23_pressure_checks'] >= count
    assert done['source_handoff_schema'] == 2 and done['same_material_plastic_PRE'] and done['source_PREs_read'] == 1
    assert done['H'] == old.f32(.072) and done['fixed_dt_s'] == 5e-6 and done['group'] == 'psi0'
    assert done['geometry_profile'] == 'bedroles' and not done['keep_bed_overlap'] and done['NoPenOn_argument']


def layout(root):
    rows = old.table(root/'typed22_layout.csv')
    assert len(rows) == 22
    for row, (name, kind, width) in zip(rows, old.SCHEMA):
        assert (row['array'], row['type'], int(row['components']), int(row['bytes_per_particle'])) == (
            name, kind, width, old.TYPES[kind].itemsize*width)
    assert sum(old.TYPES[kind].itemsize*width for _, kind, width in old.SCHEMA) == 212


def history(frames, clocks, pre, initial, source_time, tag, exponent):
    expected = np.r_[np.arange(1805, dtype=np.uint32), np.arange(2060, 7060, dtype=np.uint32)]
    ppos, ipos = pre['Posd'][2060:], initial['Posd'][2060:]
    z0 = ipos[:, 2]; top, bottom = z0 == z0.max(), z0 == z0.min()
    fixed_p0 = pre['PorePress0'][2060:, 0]
    rows = []
    for part, frame in enumerate(frames):
        clock = clocks[part]
        assert np.array_equal(frame['Idp'][:, 0], expected) and float(frame['time']) == float(clock['time_s'])
        soil = frame['Idp'][:, 0] >= 2060
        pos, velocity = frame['Posd'][soil], frame['Vel'][soil].astype(float)
        p, p0 = frame['PorePress'][soil, 0].astype(float), frame['PorePress0'][soil, 0]
        assert np.array_equal(p0.view(np.uint32), fixed_p0.view(np.uint32))
        excess = p-p0.astype(float)
        sk, si = frame['SigmaState_kk'][soil], frame['SigmaState_ij'][soil]
        j, kappa = frame['PoroVolumeRatio'][soil, 0], frame['Kplastic'][soil, 0]
        speed2 = np.sum(velocity*velocity, axis=1); du, total_du = pos-ppos, pos-ipos
        tree = retained.cKDTree(pos[:, [0, 2]])
        nn = tree.query(pos[:, [0, 2]], k=2)[0][:, 1]/.04
        pairs = tree.query_pairs(.7*.04, output_type='ndarray')
        rows.append(dict(tag=tag, part=part, completed_step=int(clock['completed_step']), saved_step=int(clock['saved_step']),
            time_s=float(frame['time']), tau_s=float(frame['time'])-source_time, AS_coefficient=.5, AS_exponent=exponent,
            p_min_Pa=float(p.min()), p_max_Pa=float(p.max()), p_mean_Pa=float(p.mean()),
            p_RMS_Pa=float(np.sqrt(np.mean(p*p))), negative_p_IDs=int(np.count_nonzero(p < 0)),
            fixed_P0_RMS_Pa=float(np.sqrt(np.mean(p0.astype(float)**2))),
            p_minus_fixed_P0_min_Pa=float(excess.min()), p_minus_fixed_P0_max_Pa=float(excess.max()),
            p_minus_fixed_P0_mean_Pa=float(excess.mean()), p_minus_fixed_P0_RMS_Pa=float(np.sqrt(np.mean(excess*excess))),
            native_excess_rounding_maxabs_Pa=float(np.abs(frame['ExcessPorePress'][soil, 0].astype(float)-excess).max()),
            effective_stress_Frob_RMS_Pa=float(np.sqrt(np.mean(np.sum(sk*sk, axis=1)+2*np.sum(si*si, axis=1)))),
            total_stress_Frob_RMS_Pa=float(np.sqrt(np.mean(np.sum((sk-p[:, None])**2, axis=1)+2*np.sum(si*si, axis=1)))),
            J_min=float(j.min()), J_max=float(j.max()), J_mean=float(j.mean()),
            kappa_max=float(kappa.max()), kappa_mean=float(kappa.mean()), nonzero_kappa_IDs=int(np.count_nonzero(kappa)),
            top_material_settlement_mm=float(-1000*du[top, 2].mean()),
            bottom_material_settlement_mm=float(-1000*du[bottom, 2].mean()),
            top_material_settlement_including_PRE_mm=float(-1000*total_du[top, 2].mean()),
            bottom_material_settlement_including_PRE_mm=float(-1000*total_du[bottom, 2].mean()),
            front_advance_from_PRE_m=float(pos[:, 0].max()-ppos[:, 0].max()),
            speed_RMS_m_s=float(np.sqrt(np.mean(speed2))), speed_max_m_s=float(np.sqrt(speed2.max())),
            mixture_KE_J_per_m=float(.5*np.sum(frame['PoroMixtureDensity'][soil, 0]*frame['PoroCurrentVolume'][soil, 0]*speed2)),
            NN_min_over_dp=float(nn.min()), NN_q05_over_dp=float(np.quantile(nn, .05)),
            NN_median_over_dp=float(np.median(nn)), pairs_le_0p7dp=int(len(pairs))))
    return rows


def plot(histories, destination):
    fig, axes = old.plt.subplots(2, 4, figsize=(20, 9), layout='constrained')
    colors = ('#D55E00', '#0072B2')
    def lines(ax, keys, scale=1., styles=None):
        for rows, color, label in zip(histories, colors, ('n=5', 'n=3.825')):
            for index, key in enumerate(keys):
                ax.plot([q['tau_s'] for q in rows], [scale*q[key] for q in rows], color=color,
                        linestyle=(styles or ('-', '--', ':'))[index], label=label+' '+key.replace('_Pa', ''))
    def finish(ax, title, right=None):
        ax.set(title=title, xlabel='Actual saved time after PRE [s]'); ax.grid(alpha=.2)
        handles, labels = ax.get_legend_handles_labels()
        if right is not None:
            h, l = right.get_legend_handles_labels(); handles += h; labels += l
        ax.legend(handles, labels, fontsize=6.5, loc='best')
    a = axes.flat
    lines(a[0], ('p_min_Pa', 'p_RMS_Pa'), .001); finish(a[0], 'Absolute p: minimum / RMS [kPa]')
    lines(a[1], ('p_minus_fixed_P0_RMS_Pa',), .001); finish(a[1], 'p minus immutable material P0: RMS [kPa]')
    lines(a[2], ('total_stress_Frob_RMS_Pa',), .001); finish(a[2], 'Total stress Frobenius RMS [kPa]')
    lines(a[3], ('kappa_max',)); right = a[3].twinx()
    lines(right, ('J_min', 'J_max'), styles=('--', ':')); right.set_ylabel('J')
    finish(a[3], 'Maximum plastic history; volume-ratio range', right)
    lines(a[4], ('top_material_settlement_mm', 'bottom_material_settlement_mm'))
    finish(a[4], 'Fixed material-layer settlement from PRE [mm]')
    lines(a[5], ('NN_min_over_dp', 'NN_q05_over_dp')); right = a[5].twinx()
    lines(right, ('pairs_le_0p7dp',), styles=(':',)); right.set_ylabel('Pairs at r <= 0.7dp')
    finish(a[5], 'Nearest spacing / dp; descriptive close pairs', right)
    lines(a[6], ('front_advance_from_PRE_m',)); right = a[6].twinx()
    lines(right, ('speed_RMS_m_s',), styles=('--',)); right.set_ylabel('RMS speed [m/s]')
    finish(a[6], 'Front advance from PRE [m]; speed', right)
    lines(a[7], ('mixture_KE_J_per_m',)); finish(a[7], 'Current mixture kinetic energy [J/m]')
    fig.suptitle('AS epsilon 0.5: exponent 5 failed saved prefix versus original exponent 3.825\n'
                 'All 47 exact-time saved states; physical acceptance pending', fontsize=13)
    fig.savefig(destination, dpi=170); old.plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args(); assert args.execution_authorized
    prefix, check = T/'figures'/TAG, T/'logs'/(TAG+'.check.json')
    assert not check.exists() and not list(prefix.parent.glob(TAG+'*'))
    nr, cr = T/'outputs'/RUN/'native_partial_r1', T/'outputs'/CONTROL/'native_r1'
    sr = T/'outputs/c08_h18_wend_psi0_pre_r2/native_r1'
    paths = [Path(__file__), NOTE, Path(retained.__file__), Path(retained.previous.__file__), Path(old.__file__),
             Path(matrix.__file__), T/'logs'/(RUN+'.run.json'), T/'logs'/(CONTROL+'.run.json'),
             T/'logs'/(RUN+'.native_r1.check.json'), T/'logs/c08_h18_wend_a05_native_r1.check.json']
    paths += [root/name for root in (nr, cr, sr) for name in ('completion.json', 'typed22.bin', 'typed22_layout.csv', 'clocks.csv')]
    paths += [root/'bedkeep_metadata.json' for root in (nr, cr)]
    consumed = [stat(q) for q in paths]
    result = dict(stage=TAG, analysis_complete=False, physical_acceptance=False, whole_run_passed=False, consumed=consumed)
    try:
        nrun, control = read(paths[6]), read(paths[7])
        ncheck, ccheck = read(paths[8]), read(paths[9])
        assert not nrun['passed'] and not nrun['solver_completed'] and nrun['actual_exit'] == nrun['actual_Win32_exit'] == 1
        assert control['passed'] and control['solver_completed'] and control['actual_exit'] == control['actual_Win32_exit'] == 0
        assert control['saved_frames'] == 91 and ncheck['passed'] and ncheck['saved_prefix_only'] and ncheck['samples'] == 47 and ccheck['passed']
        for key in ('program', 'source_build', 'source_capture', 'source_archive', 'source_pre_file', 'planned_steps'):
            assert nrun[key] == control[key]; consumed += [old.bind(nrun[key])]
        for run, code in ((nrun, 1), (control, 0)):
            call = read(old.bind(run['actual_call'])['path']); consumed += [old.bind(run['actual_call'])]
            assert call['actual_solver_Win32_exit'] == call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == code
            assert not call['ownership_errors'] and Path(call['actual_solver']['exe']).samefile(run['program']['path'])
            consumed += [old.bind(run[q]) for q in ('input_xml', 'native_profile')]
        for entry in (ncheck['native_build'], ncheck['native_call'], ncheck['completion'], ncheck['metadata'],
                      ccheck['actual_call'], ccheck['native_completion']):
            consumed.append(old.bind(entry))
        prep_path = T/'logs'/(RUN+'.prepare.json'); prepared = read(prep_path); consumed.append(stat(prep_path))
        assert prepared['prepared_only'] and prepared['consumed_stats_unchanged'] and prepared['control_run'] == stat(paths[7])
        for key in ('program', 'source_build', 'source_capture', 'source_archive', 'source_pre_file', 'planned_steps'):
            assert prepared[key] == nrun[key]
        consumed += [old.bind(prepared[q]) for q in ('configuration', 'control_configuration')]
        profiles = [{q['key']:q['value'] for q in old.table(run['native_profile']['path'])} for run in (nrun, control)]
        assert len(profiles[0]) == len(profiles[1]) == 17 and set(profiles[0]) == set(profiles[1])
        for key in profiles[0]:
            assert key == 'ArtificialStressExp' or profiles[0][key] == profiles[1][key]
        assert all(float(p['ArtificialStressCoef']) == .5 for p in profiles)
        assert old.f32(profiles[0]['ArtificialStressExp']) == 5 and old.f32(profiles[1]['ArtificialStressExp']) == old.f32(3.825)
        comparisons = [(nrun['input_xml']['path'], control['input_xml']['path'],
                        ('execution/special', 'execution/parameters', 'execution/constants', 'execution/particles')),
                       (prepared['configuration']['path'], prepared['control_configuration']['path'], (None,))]
        for nxml, cxml, sections in comparisons:
            nx, cx = ET.parse(nxml).getroot(), ET.parse(cxml).getroot()
            exponent = nx.findall("execution/parameters/parameter[@key='ArtificialStressExp']")
            assert len(exponent) == 1 and old.f32(exponent[0].get('value')) == 5
            exponent[0].set('value', '3.825')
            assert all(matrix.signature(nx if q is None else nx.find(q)) == matrix.signature(cx if q is None else cx.find(q))
                       for q in sections)
        done, cd, source = read(nr/'completion.json'), read(cr/'completion.json'), read(sr/'completion.json')
        validate_native(done, 47); validate_native(cd, 91)
        assert done['saved_prefix_native_passed'] and done['diagnostic_complete'] and not done['passed'] and not done['full_run_completed']
        assert done['completed_steps'] == 2092001 and cd['passed'] and cd['completed_steps'] == 2180000
        assert source['passed'] and source['samples'] == 1001 and source['completed_steps'] == 2000000
        for root, count, exp in ((nr, 47, 5.), (cr, 91, old.f32(3.825))):
            meta = read(root/'bedkeep_metadata.json')
            assert meta['samples'] == count and meta['AS_coefficient_float_reference'] == .5 and meta['AS_exponent_float_reference'] == exp
            layout(root)
        layout(sr)
        frames, reference, pre = retained.mapped(nr, 6805, 47), retained.mapped(cr, 6805, 91), retained.mapped(sr, 7060, 1001)
        assert np.array_equal(pre[0]['Idp'][:, 0], np.arange(7060, dtype=np.uint32))
        assert np.array_equal(pre[-1]['Idp'][:, 0], np.arange(7060, dtype=np.uint32))
        clocks, rc, plan = old.table(nr/'clocks.csv'), old.table(cr/'clocks.csv'), old.table(nrun['planned_steps']['path'])
        assert len(clocks) == 47 and len(rc) == len(plan) == 91
        for part, (n, r, p) in enumerate(zip(clocks, rc, plan)):
            assert int(n['part']) == int(r['part']) == int(p['part']) == part
            assert int(n['completed_step']) == int(r['completed_step']) == int(p['completed_step'])
            assert int(n['saved_step']) == int(r['saved_step']) == int(p['saved_step'])
            assert float(n['time_s']) == float(r['time_s']) == float(p['time_s']) == float(frames[part]['time']) == float(reference[part]['time'])
        assert len(clocks) == 47 and float(pre[-1]['time']) == done['source_actual_time_s'] == cd['source_actual_time_s']
        rows = history(frames, clocks, pre[-1], pre[0], float(pre[-1]['time']), RUN, 5.)
        baseline = history(reference[:47], rc[:47], pre[-1], pre[0], float(pre[-1]['time']), CONTROL, old.f32(3.825))
        matched = []
        keys = [q for q in rows[0] if q not in ('tag', 'part', 'completed_step', 'saved_step', 'time_s', 'tau_s', 'AS_coefficient', 'AS_exponent')]
        for n, r in zip(rows, baseline):
            row = {q:n[q] for q in ('part', 'completed_step', 'saved_step', 'time_s', 'tau_s')}
            for key in keys:
                row['n5_'+key], row['n3p825_'+key], row['n5_minus_n3p825_'+key] = n[key], r[key], n[key]-r[key]
            matched.append(row)
        csv, comparison, png = (Path(str(prefix)+q) for q in ('_history.csv', '_matched47.csv', '.png'))
        old.write_csv(csv, rows); old.write_csv(comparison, matched); plot((rows, baseline), png)
        assert all(stat(q['path']) == q for q in consumed)
        result.update(analysis_complete=True, samples=47, exact_time_step_matched_rows=47,
            only_numerical_input_difference='ArtificialStressExp 3.825 -> 5', same_actual_PRE_program_plan=True,
            source_samples=1001, native_headers=[[6805, 22, 47], [6805, 22, 91], [7060, 22, 1001]],
            last_saved_n5=rows[-1], matched_control_last_saved=baseline[-1],
            saved_prefix_only=True, fixed_P0_difference_is_not_paper_or_release_excess=True,
            material_layers_from_source_initial_IDs=True, close_pairs_are_descriptive_not_tensile_causation=True,
            mixture_KE_is_not_total_energy_balance=True, no_half_or_ULP_equivalence_claim=True,
            unsaved_failure_state_reconstructed=False, no_winner_selected=True, consumed_stats_unchanged=True,
            visual_QA_pending=True, solver_invocations=0, decoder_invocations=0, VTK_invocations=0, SHA_scans=0,
            files=[stat(csv), stat(comparison), stat(png)])
    except Exception as error:
        result.update(first_failure=str(error), partial_outputs_preserved=True); raise
    finally:
        with check.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')


if __name__ == '__main__':
    main()
