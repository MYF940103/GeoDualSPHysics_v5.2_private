"""Prepare only one original-physics GPU observer smoke; no tool/program invocation."""
import argparse
import csv
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import c08_h18_wend_matrix_r1 as m

T, C, L = m.T, m.C, m.L
TAG = 'c08_h18_storage_short_r1'
NOTE = T / 'notes' / (TAG + '.md')
CONTROL = 'c08_h18_as03_n255_r1'
JOBS = {
    'debug2': dict(tag='c08_h18_storage_debug2_GPU_r1', configuration='Debug',
                   steps=(2000001, 2000002), new_updates=2, frames=2),
    'short3': dict(tag='c08_h18_storage_short3_GPU_r1', configuration='Release',
                   steps=(2000001, 2002001, 2004001), new_updates=4001, frames=3),
}
DT, PRESTEP = .000005, 2000000


def copy_exact(source, target):
    m.need(not target.exists(), 'Existing copied input is protected')
    shutil.copy2(source, target)
    m.need(target.read_bytes() == Path(source).read_bytes(), 'Copied input bytes differ')
    return m.stat(target)


def prepare(profile):
    job = JOBS[profile]; tag = job['tag']
    out = T / 'outputs' / tag
    config, plan = [T / 'configs' / (tag + suffix) for suffix in ('_Def.xml', '.steps.csv')]
    check = L / (tag + '.prepare.json')
    m.need(not out.exists() and not config.exists() and not plan.exists() and not check.exists()
           and all(not (L / (tag + suffix)).exists() for suffix in
                   ('.run.json', '.call.json', '.start.json', '.status.json', '.admission.json')),
           'Existing preparation, job or partial output is protected')
    before = [m.stat(p) for p in (Path(__file__), NOTE, Path(m.__file__))]
    try:
        run_path = L / (CONTROL + '.run.json')
        prep_path = L / (CONTROL + '.prepare.json')
        native_path = L / 'c08_h18_as03_n255_native_r1.check.json'
        review_path = L / 'c08_h18_as03n255_review_r1.check.json'
        run, prepared, native, review = map(m.read, (run_path, prep_path, native_path, review_path))
        m.need(run['passed'] and run['solver_completed'] and run['consumed_stats_unchanged']
               and run['actual_exit'] == run['actual_Win32_exit'] == run['actual_tool_exit'] == 0
               and run['actual_steps'] == 2180000 and run['saved_frames'] == 91
               and run['AS_coefficient'] == .3 and run['AS_exponent'] == 2.55
               and run['fixed_dt_s'] == DT and run['hdp'] == 1.8 and not run['keep_bed_overlap'],
               'Only the genuinely completed original AS03/n255 control is admitted')
        m.need(prepared['prepared_only'] and prepared['consumed_stats_unchanged'] and
               native['passed'] and native['reader_invocations'] == 1 and native['consumed_stats_unchanged']
               and review['analysis_complete'] and review['consumed_stats_unchanged']
               and not review['physical_acceptance'], 'Original prepared/native/review closure required')
        before += [m.stat(p) for p in (run_path, prep_path, native_path, review_path)]
        before += [m.bind(run[k]) for k in ('program', 'source_build', 'source_capture',
                    'source_archive', 'source_pre_file', 'source_run', 'source_native', 'input_xml',
                    'planned_steps', 'native_profile', 'actual_call')]
        before += [m.bind(native[k]) for k in ('actual_call', 'native_completion', 'metadata', 'reader_build')]
        original_call = m.read(run['actual_call']['path'])
        m.need(original_call['actual_solver_Win32_exit'] == original_call['actual_Popen_wait_exit'] ==
               original_call['actual_Win32_exit'] == 0 and not original_call['ownership_errors'],
               'Actual original solver ownership/exit receipt required')
        original_native = m.read(native['native_completion']['path'])
        m.need(original_native['passed'] and original_native['samples'] == 91 and
               original_native['completed_steps'] == 2180000 and original_native['typed_arrays'] == 22
               and original_native['actual_native_IDs_per_frame'] == 6805,
               'Original full91 typed native reference required')
        source_native = m.read(run['source_native']['path'])
        m.need(source_native['passed'] and source_native['certified_PRE'] and
               source_native['expected_handoff_schema'] == 2 and source_native['same_material_plastic_PRE']
               and source_native['completed_steps'] == PRESTEP and source_native['samples'] == 1001
               and source_native['soil_IDs'] == 5000 and source_native['fixed_IDs'] == 2060
               and source_native['declared_Kernel_XML_CSV'] == 2,
               'Original certified same-material Wendland PRE required')

        build_path = L / ('c08_h18_storage_trace_' + job['configuration'] + '_r1.build.json')
        build = m.read(build_path); before.append(m.stat(build_path))
        m.need(build['passed'] and build['consumed_stats_unchanged'] and
               build['configuration'] == job['configuration'] and build['allowed_runtime_backend'] == 'GPU'
               and build['actual_link_objects'] == 114 and build['original_main_unchanged']
               and build['original_physical_CUDA_objects_retained'] and
               build['original_physical_CUDA_recompiled'] == 0 and build['physical_host_TUs_recompiled'] == 1
               and build['new_observer_CUDA_TUs'] == 1 and build['macro'] == 'C08_STORAGE_TRACE'
               and build['macro_enabled_in_host_and_observer_TUs'] and
               not build['class_layout_changed'] and not build['production_source_changed'],
               'Separately passed exact private observer backend build required')
        m.need(build['base_original_source_capture'] == run['source_capture'] and
               build['base_original_source_archive'] == run['source_archive'],
               'Private observer and certified original PRE must share the actual original source')
        before += [m.bind(build[k]) for k in ('program', 'source_capture', 'source_archive', 'preparation')]
        runtime = [m.bind(q) for q in build['runtime']]; before += runtime
        capture = m.read(build['source_capture']['path'])
        m.need(capture['passed'] and capture['primary_expression_bytes_retained'] and
               capture['exact_inverse_original_bytes'] and capture['all_other_archived_bytes_identical']
               and not capture['physical_equations_changed'], 'Output-only source capture required')
        definition = Path(m.bind(prepared['configuration'])['path'])
        source_seed = Path(run['input_xml']['path']).with_suffix('')
        m.need(len(run['seed']) == 3, 'Original generated seed triple required')
        for suffix in ('.xml', '.bi4', '_Normals.nbi4'):
            p = Path(str(source_seed) + suffix)
            entry = next(q for q in run['seed'] if Path(q['path']).resolve() == p.resolve())
            before.append(m.bind(entry))
        before.append(m.stat(definition))
        actual = ET.parse(run['input_xml']['path']).getroot()
        pars = {q.get('key'): q.get('value') for q in actual.findall('execution/parameters/parameter')}
        m.need(len(pars) == len(actual.findall('execution/parameters/parameter')) and
               all(m.f32(pars[k]) == m.f32(v) for k, v in dict(Kernel=2, Visco=.1,
                   DtFixed=DT, ArtificialStressCoef=.3, ArtificialStressExp=2.55,
                   TimeMax=10.9, TimeOut=.01).items()), 'Original physical XML/cadence must remain unchanged')
        g = actual.find('execution/special/gravitypreload')
        m.need(g is not None and Path(g.get('statefile')).resolve() == Path(run['source_pre_file']['path']).resolve()
               and g.get('elastic_source') == g.get('keep_bed_overlap') == 'false',
               'Original same-material history import must remain untouched')

        old_plan = m.table(run['planned_steps']['path'])
        m.need(len(old_plan) == 91 and list(old_plan[0]) ==
               ['part', 'completed_step', 'saved_step', 'time_s', 'dt_s'], 'Original91 plan required')
        clock = float(source_native['actual_end_s']); previous = PRESTEP; rows = []
        for part, step in enumerate(job['steps']):
            for _ in range(previous, step): clock += DT
            rows.append(dict(part=part, completed_step=step, saved_step=step - 1,
                             time_s=clock, dt_s=DT))
            previous = step
        m.need(previous - PRESTEP == job['new_updates'], 'New-update/global-limit distinction differs')
        shared = 1 if profile == 'debug2' else 3
        for part in range(shared):
            old = old_plan[part]; new = rows[part]
            m.need(int(old['completed_step']) == new['completed_step'] and
                   abs(float(old['time_s']) - new['time_s']) <= 1e-14,
                   'Original genuinely shared saved clock/step differs')
        m.verify(before)
        out.mkdir()
        copied_definition = copy_exact(definition, config)
        # Preserve generated basename and all embedded labels/references. The
        # output directory is new; no generated XML/date/seed data is rewritten.
        input_prefix = out / source_seed.name
        copied_seeds = [copy_exact(Path(str(source_seed) + suffix), Path(str(input_prefix) + suffix))
                        for suffix in ('.xml', '.bi4', '_Normals.nbi4')]
        profile_path = out / 'native_profile.csv'
        copied_profile = copy_exact(run['native_profile']['path'], profile_path)
        with plan.open('x', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
        program = build['program']['path']
        argv = [program, '-gpu:0', '-stable', '-mdbc_freeslip:1', str(input_prefix), str(out),
                '-dirdataout', 'data', '-svres', '-nsteps:' + str(job['steps'][-1])]
        m.verify(before)
        m.save(check, dict(stage=tag + '.prepare', passed=True, prepared_only=True, profile=profile,
            configuration=job['configuration'], program=build['program'], source_build=m.stat(build_path),
            source_capture=build['source_capture'], source_archive=build['source_archive'], runtime=runtime,
            base_original_source_capture=run['source_capture'], base_original_source_archive=run['source_archive'],
            source_pre_file=run['source_pre_file'], source_run=run['source_run'], source_native=run['source_native'],
            control_run=m.stat(run_path), control_native=m.stat(native_path), control_review=m.stat(review_path),
            control_input=run['input_xml'], control_original_plan=run['planned_steps'],
            configuration_xml=copied_definition, input_xml=copied_seeds[0], seed=copied_seeds,
            native_profile=copied_profile, planned_steps=m.stat(plan), planned_rows=rows,
            new_updates=job['new_updates'], global_nsteps_limit=job['steps'][-1],
            expected_saved_frames=job['frames'], actual_source_time_s=source_native['actual_end_s'],
            planned_actual_end_s=clock, fixed_dt_s=DT, output_interval_s=.01,
            original_TimeMax_s=10.9, output=str(out), argv=argv, cwd=str(C),
            seed_copied_byte_identical=True, generated_seed_basename_preserved=source_seed.name,
            definition_copied_byte_identical=True, profile_copied_byte_identical=True,
            separate_root_run_admission_required=True, root_direct_invoke_only=True,
            new_owner_or_notifier_created=False, automatic_next_job=False,
            pending_after_run=['Actual owned tool/solver exits, unchanged inputs and native runtime gates',
                'Separate unique native admission for this exact debug2 or short3 profile',
                'Storage sidecar original arithmetic/cumulative checks independent of native reader',
                'Debug2 memcheck; Debug is not Release bit truth' if profile == 'debug2' else
                'After native: compare all22/time/layout/signed first3 to the genuine original AS03 control'],
            consumed=before, consumed_stats_unchanged=True, GenCase_invocations=0,
            program_invocations=0, solver_invocations=0, reader_invocations=0,
            build_invocations=0, VTK_invocations=0, physical_acceptance=False, SHA_scans=0))
        print('STORAGE_SHORT_PREPARED', profile, str(check), flush=True)
    except Exception as error:
        if not check.exists():
            m.save(check, dict(stage=tag + '.prepare', passed=False, prepared_only=True,
                first_failure=str(error), consumed=before, partial_outputs_preserved=True,
                GenCase_invocations=0, program_invocations=0, solver_invocations=0,
                reader_invocations=0, build_invocations=0, VTK_invocations=0,
                physical_acceptance=False, SHA_scans=0))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('prepare',), required=True)
    parser.add_argument('--job', choices=tuple(JOBS), required=True)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    m.need(args.execution_authorized, 'Root full-read and independent preparation admission required')
    prepare(args.job)
