"""One separately admitted read of the completed Wendland psi2p5 source; no build or solve."""
import argparse
import csv
import os
import xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import c08_h18_wend_branches_pre_r1 as source

T, C, L = source.T, source.C, source.L
need, read, stat, bind, save = source.need, source.read, source.stat, source.bind, source.save
TAG = 'c08_h18_wend_psi2p5_native_r1'
SOURCE = 'c08_h18_wend_branches_psi2p5_pre_r1'
SELF = Path(__file__).resolve()
NOTE = T / 'notes' / (TAG + '.md')
ADMISSION = L / (TAG + '.root_admission.json')
RUN = L / (SOURCE + '.run.json')
TERMINAL = L / (SOURCE + '.terminal_review_r1.json')
BUILD = L / 'c08_h18_wend_native_r1.build.json'
OUT = T / 'outputs' / SOURCE
NATIVE = OUT / 'native_r1'
PROFILE = T / 'configs' / (TAG + '.material.csv')
KEYS = ('Kernel','group','ModulusE','PRvs','DPCtes','phi','phi_r','n_phi','coh','coh_r',
        'n_coh','dlt','DilationDecay','SoilTriggerFos','fresh_trigger_active')


def material_profile(xml_path):
    root = ET.parse(xml_path).getroot()
    soil = root.find('execution/special/soils')
    pairs = [(q.get('key'),q.get('value')) for q in root.findall('execution/parameters/parameter')]
    pars = dict(pairs)
    need(soil is not None and len(pars) == len(pairs), 'Actual generated soil/unique parameters required')
    result = {}
    for key in KEYS:
        if key in ('Kernel','DPCtes'): result[key] = pars[key]
        elif key == 'group': result[key] = 'psi2p5'
        elif key == 'fresh_trigger_active': result[key] = '0'
        else:
            nodes = soil.findall(key)
            need(len(nodes) <= 1, 'Duplicate actual material field: ' + key)
            result[key] = nodes[0].get('value') if nodes else '1.65' if key == 'SoilTriggerFos' else None
            need(result[key] is not None, 'Actual material field missing: ' + key)
    wanted = dict(Kernel=2,DPCtes=3,ModulusE=20e6,PRvs=.33,phi=25,phi_r=25,n_phi=0,
                  coh=5000,coh_r=1000,n_coh=5,dlt=2.5,DilationDecay=.2,SoilTriggerFos=1.65)
    for key,value in wanted.items():
        need(source.f32(result[key]) == source.f32(value), 'Actual source material differs: ' + key)
    # Native Parameters() itself performs the frozen float(TORAD*XML-float) conversion.
    g = root.find('execution/special/gravitypreload')
    need(g is not None and g.get('elastic_source') == g.get('keep_bed_overlap') == 'false'
         and not g.get('statefile') and float(g.get('time')) == 10, 'Fresh same-material source contract differs')
    need(float(pars['Kernel']) == 2 and float(pars['DtFixed']) == .000005
         and float(pars['TimeOut']) == .01 and float(pars['TimeMax']) == 13
         and float(pars.get('ArtificialStress','0')) == float(pars.get('NoPenetration','0')) == 0,
         'Actual source kernel/step/cadence/phase differs')
    return result


def run():
    check = L / (TAG + '.check.json')
    need(not check.exists(), 'Existing terminal native receipt protected; no repeat')
    before, calls = [], []
    result = dict(stage=TAG,passed=False,reader_invocations=0,solver_invocations=0,build_invocations=0,
                  VTK_invocations=0,physical_acceptance=False,equilibrium_acceptance=False,SHA_scans=0)
    try:
        ad = read(ADMISSION)
        need(ad['authorized'] and ad['allowed_stage'] == TAG and ad['group'] == 'psi2p5'
             and ad['script'] == stat(SELF) and ad['note'] == stat(NOTE)
             and ad['source_run'] == stat(RUN) and ad['terminal_review'] == stat(TERMINAL)
             and ad['native_build'] == stat(BUILD) and ad['root_thread_id'] == os.environ.get('CODEX_THREAD_ID') == source.THREAD
             and ad['reader_once_only'] and not ad['automatic_solver'] and not ad['automatic_VTK'],
             'Exact current-root single native read admission required')
        need(not NATIVE.exists() and not PROFILE.exists() and not (L / (TAG + '.call.json')).exists(),
             'Existing native directory/profile/call protected; never repeat partial decode')
        b, r, terminal = read(BUILD), read(RUN), read(TERMINAL)
        need(b['passed'] and b['consumed_stats_unchanged'] and b['actual_link_objects'] == 7
             and b['JSph_objects_linked'] is False and b['source_material_CSV_keys'] == 15
             and b['declared_Kernel_XML_CSV'] == 2, 'Existing exact Wendland native utility required')
        program = Path(bind(b['program'])['path'])
        need(terminal['passed'] and terminal['source_run'] == stat(RUN)
             and terminal['all_actual_tool_solver_exits_zero'] and terminal['owned_identity_and_argv_verified']
             and terminal['source_steps'] == 2000000 and terminal['saved_frames'] == 1001
             and terminal['native_reader_invocations'] == 0
             and terminal['complete_material_tuple'] == source.material('psi2p5'), 'Current root terminal audit differs')
        need(r['passed'] and r['solver_completed'] and r['actual_exit'] == r['actual_Win32_exit'] == 0
             and r['group'] == 'psi2p5' and r['material'] == source.material('psi2p5')
             and r['actual_steps'] == 2000000 and r['saved_frames'] == 1001 and r['reader_invocations'] == 0
             and r['kernel'] == 2 and r['elastic_source'] is False and r['keep_bed_overlap'] is False,
             'Completed matching psi2p5 source required')
        original = read(bind(r['actual_call'])['path'])
        need(original['actual_solver_Win32_exit'] == original['actual_Popen_wait_exit'] == original['actual_Win32_exit'] == 0
             and not original['ownership_errors'] and original['arguments'] == r['argv']
             and Path(original['actual_solver']['exe']).samefile(bind(r['program'])['path']),
             'Actual original solver ownership/exits/argv differ')
        seal = read(bind(r['solver_completed_seal'])['path'])
        need(seal['solver_completed'] and seal['actual_call'] == r['actual_call']
             and seal['actual_steps'] == 2000000 and seal['saved_frames'] == 1001, 'Original solver completion seal differs')
        for p in psutil.process_iter(['exe','cmdline']):
            try:
                exe,argv = p.info['exe'],p.info['cmdline'] or []
                need(not(exe and Path(exe).name.lower() == program.name.lower())
                     and not(any(Path(q).resolve() == NATIVE.resolve() for q in argv[1:] if not q.startswith('-'))),
                     'Existing active source reader/native output owner; no duplicate')
            except (psutil.NoSuchProcess,psutil.AccessDenied): pass
        xml = Path(bind(r['input_xml'])['path'])
        need(xml.parent.samefile(OUT), 'Actual generated source XML must belong to this output')
        values = material_profile(xml)
        plan = Path(bind(r['planned_steps'])['path'])
        rows = source.plan_records(plan)
        need(rows[-1]['completed_step'] == 2000000, 'Original complete1001 scalar plan required')
        before = [stat(q) for q in (SELF,NOTE,ADMISSION,RUN,TERMINAL,BUILD,Path(source.__file__),xml,plan)]
        before += [bind(r[k]) for k in ('actual_call','owner_admission','solver_completed_seal','program',
                                      'source_build','source_capture','source_archive','Run_out','Run_csv','source_head')]
        before += [stat(L / (SOURCE + '.start.json')),bind(b['program']),bind(b['source']),bind(b['core_derivation'])]
        before += [bind(q) for q in b['generated']] + [bind(q) for q in b['calls']]
        parts = r['PARTs']
        need(len(parts) == 1001 and [Path(q['path']).name for q in parts] == ['Part_%04d.bi4'%i for i in range(1001)]
             and all(Path(q['path']).parent.samefile(OUT / 'data') for q in parts), 'Original sealed1001 native file identities differ')
        # The current root terminal seal already stat-checked these exact run-bound PARTs.
        # Reuse those identities; one final stat pass detects any change before/during this read.
        with PROFILE.open('x',encoding='utf-8',newline='') as f:
            writer = csv.writer(f); writer.writerow(('key','value')); writer.writerows(values.items())
        before.append(stat(PROFILE))
        argv = [str(program),'--source','full',str(OUT / 'data'),str(PROFILE),str(plan),str(NATIVE)]
        result['reader_invocations'] = 1
        calls.append(source.invoke(TAG,argv,C))
        actual = read(calls[-1]['path'])
        need(actual['actual_Popen_wait_exit'] == actual['actual_Win32_exit'] == 0 and actual['ownership_failure'] is None,
             'Actual unique native reader exits/ownership failed; preserve partial output')
        done = read(NATIVE / 'completion.json')
        need(done['passed'] and done['stage'] == 'c08_h18_wend_native_r1.source' and done['profile'] == 'full'
             and not done['partial'] and done['certified_PRE'] and done['group'] == 'psi2p5'
             and done['samples'] == 1001 and done['completed_steps'] == 2000000 and done['native_IDs'] == 7060
             and done['fixed_IDs'] == 2060 and done['soil_IDs'] == 5000 and done['typed_arrays'] == 22
             and done['expected_handoff_schema'] == 2 and done['source_material_CSV_keys'] == 15,
             'Original full source native completion shape/group/schema differs')
        need(done['ledger_checks'] == done['rho_cache_bits_checks'] == done['kappa_nondecreasing_checks'] == 5005000
             and done['P0_bits_checks'] == 7067060 and done['fixed_marker_checks'] == done['fixed_kappa_zero_checks'] == 2062060
             and done['noninitial_signed_intervals'] == 1000 and done['max_scalar_clock_error_s'] <= 1e-14
             and done['max_noninitial_signed_dterror_s'] <= 1e-14 and done['max_ledger_relative_error'] <= 5e-13,
             'Original all-ID safety/clock/ledger coverage differs')
        source.verify(before + parts)
        files = [stat(NATIVE / q) for q in ('completion.json','typed22.bin','typed22_layout.csv','clocks.csv',
                                           'summary.csv','layers.csv','snapshots.csv')]
        result.update(passed=True,call=calls[0],completion=stat(NATIVE / 'completion.json'),files=files,
                      source_run=stat(RUN),terminal_review=stat(TERMINAL),material_csv=stat(PROFILE),material_values=values,
                      planned_steps=stat(plan),source_PART_stats_inherited_from_current_terminal_seal=True,
                      actual_read_body='Existing h18_source_core_r1.cpp; all original gates unchanged',
                      whole_material_contract_independently_reconstructed=False,
                      saved_FS23_sign_observational_except_original_nonempty_final_certificate_gate=True,
                      source_native_certificate_not_equilibrium=True,consumed_stats_unchanged=True)
    except Exception as error:
        result.update(first_failure=str(error),partial_outputs_preserved=True,automatic_retry=False)
        actual_path = L / (TAG + '.call.json')
        if actual_path.is_file():
            actual = read(actual_path)
            result.update(call=stat(actual_path),actual_Popen_wait_exit=actual.get('actual_Popen_wait_exit'),
                          actual_Win32_exit=actual.get('actual_Win32_exit'),ownership_failure=actual.get('ownership_failure'))
    result.update(calls=calls,consumed=before,source_PART_stat_seal=read(RUN).get('PARTs',[]))
    save(check,result)
    need(result['passed'],result.get('first_failure','Native read failed'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized',action='store_true')
    args = parser.parse_args()
    need(args.execution_authorized,'Author-only until root full read and separate one-reader admission')
    run()
