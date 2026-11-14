"""Build only: original one-step call block, new read-only material/trace attribution."""
from pathlib import Path
import c08_h18_late_rhs_r1_build as base

TAG = 'c08_h18_late_step_r1'


def main():
    m, t, logs = base.m, base.T, base.L
    source = t/'support/c08_h18_late_rhs_r1.cpp'
    original_step = t/'support/c08_h18_step_balance_r1.cpp'
    original_build = logs/'c08_h18_step_balance_r1.build.json'
    original_check = logs/'c08_h18_step_balance_r1.check.json'
    rhs_check = logs/'c08_h18_late_rhs_r1.check.json'
    rhs_build = logs/'c08_h18_late_rhs_r1.build.json'
    rhs_complete = t/'outputs/c08_h18_late_rhs_r1/completion.json'
    built, checked, rb, rc, rd = (m.read(p) for p in (original_build, original_check, rhs_build, rhs_check, rhs_complete))
    m.need(built['passed'] and built['source'] == m.stat(original_step) and built['original_Single_no_hook']
           and built['physical_objects_compiled'] == 0 and built['actual_link_objects'] == 87,
           'Original completed StepBalance build/source required')
    m.need(checked['passed'] and checked['consumed_stats_unchanged'] and checked['physical_steps'] == 1,
           'Original completed one-step qualification required')
    m.need(rb['passed'] and rb['source'] == m.stat(source) and rb['original_Single_no_hook']
           and rb['physical_objects_compiled'] == 0 and rc['passed'] and rc['consumed_stats_unchanged']
           and rc['component_invocations'] == 1 and rc['physical_steps'] == 0
           and rd['passed'] and rd['source_parts'] == [200, 250, 300] and rd['source_samples'] == 301
           and rd['literal_final_float_bits_matched'] == rd['soil_rows'] == 15000,
           'Completed original zero-step late qualification required')
    extra = [m.stat(Path(__file__)), m.stat(original_step), m.stat(original_build), m.stat(original_check),
             m.stat(rhs_check), m.stat(rhs_build), m.stat(rhs_complete), m.bind(rc['actual_call']),m.bind(checked['actual_call']),
             m.bind(rc['completion']), m.bind(checked['completion']),m.bind(rb['source']), m.bind(rb['note'])]
    for row in (m.read(rc['actual_call']['path']), m.read(checked['actual_call']['path'])):
        m.need(row['actual_Popen_wait_exit'] == row['actual_Win32_exit'] == 0, 'Actual original owned component failed')
    # Validate the already frozen late source BEFORE changing the builder globals.
    rhs_proof = base.entry_proof()
    shared_source = source.read_bytes()
    access = b'class Probe:public JSphCpuSingle{'
    app = b'JAppInfo AppInfo("C08H18LateRhs","r1","14-11-2026");'
    m.need(shared_source.count(access) == shared_source.count(app) == 1, 'Unique inherited source/app anchors required')
    shared = shared_source.replace(access, access+b'\nprotected:', 1).replace(
        app, b'JAppInfo AppInfo("C08H18LateStep","r1","14-11-2026");', 1)
    base.TAG = TAG
    base.OUT = t/'outputs'/(TAG+'_build')
    base.CPP = t/'support'/(TAG+'.cpp')
    base.NOTE = t/'notes'/(TAG+'.md')
    include = base.OUT/'shared.inc'
    original = original_step.read_bytes(); entry = base.CPP.read_bytes()
    begin = b'      // Original ComputeStep_Sym call order; only read-only captures are inserted.'
    end = b'    Need(Bits(ddtp,dt)'
    m.need(original.count(begin) == original.count(end) == entry.count(begin) == entry.count(end) == 1,
           'Unique original step-call block required')
    oldblock = original[original.index(begin):original.index(end)]
    newblock = entry[entry.index(begin):entry.index(end)]
    m.need(newblock == oldblock and entry.count(b'#define main c08_storage_rhs_unused_main') == 1
           and entry.count(('#include "../outputs/'+TAG+'_build/shared.inc"').encode()) == 1
           and entry.count(b'#undef main') == 1
           and entry.count(b'fsoil::EvaluateMaterial(input,SoilCte,DPCtes,StrainSoftening,trigger)') == 1,
           'Exact original physical step calls and one read-only shadow site required')
    original_invoke, original_save, original_proof = m.invoke, m.save, base.entry_proof
    generated = []

    def proof():
        m.need(base.CPP.read_bytes() == entry, 'Reviewed diagnostic entry changed before compilation')
        return dict(original_step=m.stat(original_step), original_step_build=m.stat(original_build),
                    original_late_RHS_derivation=rhs_proof, new_entry=m.stat(base.CPP),
                    actual_step_call_block_byte_equal=True, actual_step_call_block_bytes=len(oldblock),
                    capture_sigma_history_rate_read_only=True, shadows_after_all_original_step_calls=True,
                    public_physical_objects_compiled=0, physical_steps_authorized_by_build=0)

    def invoke(label, argv, cwd, env=None, target=None):
        m.verify(extra+generated)
        if label == TAG+'.compile':
            m.need(not generated and base.OUT.is_dir() and not include.exists(), 'One fresh shared include required')
            include.write_bytes(shared); m.need(include.read_bytes() == shared, 'Generated shared include differs')
            generated.append(m.stat(include))
        m.need(len(generated) == 1, 'Shared source must precede compile/link')
        call = original_invoke(label, argv, cwd, env, target)
        m.verify(extra+generated)
        m.need(include.read_bytes() == shared, 'Shared source changed during build')
        return call

    def save(path, value):
        if value.get('stage') == TAG+'.build':
            if value.get('passed'):
                m.verify(extra+generated)
                deps = m.read(base.OUT/'dependencies.json')['Data']
                includes = {Path(p).resolve() for p in deps['Includes']}
                m.need(len(generated) == 1 and include.resolve() in includes
                       and (base.OUT/'headers/src/source/FunSoilMaterial.h').resolve() in includes,
                       'Actual compilation missed frozen shared source/material header')
                value['consumed'] += extra+generated
                value.update(shared_source=m.stat(source), generated_shared_include=generated[0],
                    shared_transform=['insert protected access in Probe', 'diagnostic AppInfo name only'],
                    zero_step_qualification=m.stat(rhs_check), original_one_step_qualification=m.stat(original_check),
                    program_basename_retained='C08H18LateRhsR1.exe', physical_steps_authorized_by_build=0,
                    allowed_parts=[200,250,300], each_separate_component_max_physical_steps=1,
                    material_shadow_not_feedback=True, actual_step_call_block_byte_equal=True,
                    no_automatic_component_or_solver=True)
            else: value['shared_partial_outputs_preserved'] = True
        return original_save(path, value)

    try:
        m.verify(extra); m.invoke, m.save, base.entry_proof = invoke, save, proof
        base.main()  # Retains the explicit authorization flag and original86-object closure.
    finally:
        m.invoke, m.save, base.entry_proof = original_invoke, original_save, original_proof


if __name__ == '__main__': main()
