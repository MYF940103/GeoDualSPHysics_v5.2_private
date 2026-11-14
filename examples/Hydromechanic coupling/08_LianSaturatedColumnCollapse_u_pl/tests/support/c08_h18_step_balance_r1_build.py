"""Build only: one new entry plus86 sealed original CPU objects; never run it."""
from pathlib import Path
import zipfile
import c08_h18_storage_rhs_r1_build as base

TAG = 'c08_h18_step_balance_r1'


def main():
    m, t, logs = base.m, base.T, base.L
    source = t / 'support/c08_h18_storage_rhs_r2.cpp'
    note = t / 'notes/c08_h18_storage_rhs_r2.md'
    checkfile = logs / 'c08_h18_storage_rhs_r2.check.json'
    buildfile = logs / 'c08_h18_storage_rhs_r2.build.json'
    complete = t / 'outputs/c08_h18_storage_rhs_r2/completion.json'
    checked, built, done = (m.read(p) for p in (checkfile, buildfile, complete))
    m.need(checked['passed'] and checked['consumed_stats_unchanged']
           and checked['component_invocations'] == 1 and checked['physical_steps'] == 0
           and checked['GPU_actions'] == 0 and built['passed'] and built['original_Single_no_hook']
           and built['actual_link_objects'] == 87 and built['physical_objects_compiled'] == 0
           and done['passed'] and done['source_parts'] == [30, 60, 90]
           and done['actual_force_calls'] == done['actual_Darcy_calls'] == 3
           and done['soil_rows'] == done['literal_final_float_bits_matched'] == 15000
           and done['physical_steps'] == done['material_return_calls'] == done['extra_Darcy_calls'] == 0,
           'Qualified original three zero-step probes required before a one-step build')
    call = m.read(m.bind(checked['actual_call'])['path'])
    m.need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0,
           'Successful actual owned zero-step call required')
    m.need(Path(built['source']['path']).resolve() == source.resolve()
           and Path(built['note']['path']).resolve() == note.resolve(), 'Retained r2 source binding differs')
    extra = [m.stat(Path(__file__)), m.stat(checkfile), m.stat(buildfile), m.stat(complete),
             m.bind(built['source']), m.bind(built['note']), m.bind(checked['actual_call']),
             m.bind(checked['completion']), m.bind(built['source_archive'])]
    # Read/freeze two existing entries; the sole harness delta is protected access.
    original = (t / 'support/c08_h18_storage_rhs_r1.cpp').read_bytes()
    shared_source = source.read_bytes()
    m.need(original.count(b'Gamma(') == 3 and original.count(b'c08_h18_storage_rhs_r1') == 3
           and shared_source == original.replace(b'Gamma(', b'RoundoffGamma(').replace(
               b'c08_h18_storage_rhs_r1', b'c08_h18_storage_rhs_r2'), 'Frozen r2 helper/tag delta differs')
    extra.append(m.stat(t / 'support/c08_h18_storage_rhs_r1.cpp'))
    access = b'class Probe:public JSphCpuSingle{'
    app = b'JAppInfo AppInfo("C08H18StorageRhs","r1","14-11-2026");'
    m.need(shared_source.count(access) == shared_source.count(app) == 1, 'Unique shared class/app anchors required')
    shared = shared_source.replace(access, access + b'\nprotected:', 1).replace(
        app, b'JAppInfo AppInfo("C08H18StepBalance","r1","14-11-2026");', 1)
    # Actual original CPU implementations and their public layouts must remain frozen.
    with zipfile.ZipFile(built['source_archive']['path']) as archive:
        for leaf in ('JSphCpuSingle.cpp', 'JSphCpu.cpp', 'JSphCpuSingle.h', 'JSphCpu.h', 'JSph.h'):
            public = base.S / 'source' / leaf
            m.need(public.read_bytes() == archive.read('src/source/' + leaf),
                   'Current public source differs from original schema2: ' + leaf)
            extra.append(m.stat(public))
    base.TAG = TAG
    base.OUT = t / 'outputs' / (TAG + '_build')
    base.CPP = t / 'support' / (TAG + '.cpp')
    base.NOTE = t / 'notes' / (TAG + '.md')
    include = base.OUT / 'shared.inc'
    m.need(not base.OUT.exists(), 'Fresh fixed step build output required')
    cpp = base.CPP.read_text(encoding='utf-8')
    m.need(cpp.count('#define main c08_storage_rhs_unused_main') == 1
           and cpp.count('#include "../outputs/' + TAG + '_build/shared.inc"') == 1
           and cpp.count('#undef main') == 1, 'Exact local shared-source include required')
    original_invoke, original_save = m.invoke, m.save
    generated = []

    def invoke(label, args, cwd, env):
        m.verify(extra + generated)
        if label == TAG + '.compile':
            m.need(not generated and base.OUT.is_dir() and not include.exists(), 'One fresh shared include required')
            include.write_bytes(shared)
            m.need(include.read_bytes() == shared, 'Generated shared include differs')
            generated.append(m.stat(include))
        m.need(len(generated) == 1, 'Shared include must precede the one compile/link')
        result = original_invoke(label, args, cwd, env)
        m.verify(extra + generated)
        m.need(include.read_bytes() == shared, 'Shared include changed during compilation')
        return result

    def save(path, value):
        if value.get('stage') == TAG + '.build':
            if value.get('passed'):
                m.verify(extra + generated)
                dependencies = m.read(base.OUT / 'dependencies.json')['Data']
                m.need(len(generated) == 1 and include.resolve() in {
                    Path(p).resolve() for p in dependencies['Includes']}, 'Actual entry did not consume frozen shared include')
                value['consumed'] += extra + generated
                value.update(shared_source=m.stat(source), generated_shared_include=generated[0],
                             shared_transform=['insert protected access in Probe', 'diagnostic AppInfo name only'],
                             zero_step_qualification=m.stat(checkfile), physical_steps_authorized_by_build=0,
                             program_basename_retained='C08H18StorageRhsR1.exe',
                             diagnostic_output=str(t / 'outputs' / TAG), original_step_calls_unmodified=True,
                             custom_RHS=False, public_source_byte_equal_to_schema2=True)
            else:
                value.update(shared_partial_outputs_preserved=True)
        return original_save(path, value)

    try:
        m.verify(extra)
        m.invoke, m.save = invoke, save
        base.main()  # Retains explicit --execution-authorized gate and all86-object closure checks.
    finally:
        m.invoke, m.save = original_invoke, original_save


if __name__ == '__main__':
    main()
