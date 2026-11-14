"""Build only one pressure-row diagnostic entry +86 original CPU physical objects."""
from pathlib import Path
import c08_h18_late_rhs_r1_build as base

TAG = 'c08_h18_pressure_row_r1'


def main():
    m, t, logs = base.m, base.T, base.L
    source = t/'support/c08_h18_late_rhs_r1.cpp'
    quadratic = t/'support/c08_h18_quadratic_r1.cpp'
    rhs_build, rhs_check = logs/'c08_h18_late_rhs_r1.build.json', logs/'c08_h18_late_rhs_r1.check.json'
    quad_build, quad_check = logs/'c08_h18_quadratic_r1.build.json', logs/'c08_h18_quadratic_r1.check.json'
    scope = t/'notes/c08_pressure_integration_scope_r1.md'
    rb, rc, qb, qc = (m.read(p) for p in (rhs_build, rhs_check, quad_build, quad_check))
    m.need(rb['passed'] and rb['source'] == m.stat(source) and rb['original_Single_no_hook']
           and rb['physical_objects_compiled'] == 0 and rb['actual_link_objects'] == 87
           and rc['passed'] and rc['consumed_stats_unchanged'] and rc['component_invocations'] == 1
           and rc['physical_steps'] == 0, 'Original completed full301 zero-step qualification required')
    m.need(qb['passed'] and qb['source'] == m.stat(quadratic) and qb['original_Single_no_hook']
           and qb['physical_objects_compiled'] == 0 and qc['passed'] and qc['consumed_stats_unchanged'],
           'Retained exact polynomial stencil qualification required')
    extra = [m.stat(p) for p in (Path(__file__), Path(base.__file__), source, quadratic,
                                rhs_build, rhs_check, quad_build, quad_check, scope)]
    extra += [m.bind(rc['actual_call']), m.bind(rc['completion']), m.bind(qc['actual_call']), m.bind(qc['completion'])]
    for q in (rc, qc):
        call = m.read(q['actual_call']['path'])
        m.need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0, 'Original owned component exit failed')
    rhs_proof = base.entry_proof()  # Validate the old completed entry before changing builder globals.
    raw = source.read_bytes(); access = b'class Probe:public JSphCpuSingle{'
    app = b'JAppInfo AppInfo("C08H18LateRhs","r1","14-11-2026");'
    m.need(raw.count(access) == raw.count(app) == 1, 'Unique archived fixture/app anchors required')
    shared = raw.replace(access, access+b'\nprotected:', 1).replace(
        app, b'JAppInfo AppInfo("C08H18PressureRow","r1","14-11-2026");', 1)
    base.TAG = TAG; base.OUT = t/'outputs'/(TAG+'_build')
    base.CPP = t/'support'/(TAG+'.cpp'); base.NOTE = t/'notes'/(TAG+'.md')
    include = base.OUT/'shared.inc'; entry = base.CPP.read_bytes(); old = quadratic.read_bytes()
    begin = b'  std::vector<QuadDonor> Stencil(unsigned i,unsigned& fixed,unsigned& almost)const{'
    end = b'    }Need(!out.empty(),"Empty actual force stencil");return out;\n  }'
    # Source files are intentionally compared bytewise, including the whole neighbour traversal.
    m.need(old.count(begin) == old.count(end) == entry.count(begin) == entry.count(end) == 1,
           'Unique retained neighbour method anchors required')
    old_stencil = old[old.index(begin):old.index(end)+len(end)]
    new_stencil = entry[entry.index(begin):entry.index(end)+len(end)]
    m.need(old_stencil == new_stencil and entry.count(b'#define main c08_storage_rhs_unused_main') == 1
           and entry.count(('#include "../outputs/'+TAG+'_build/shared.inc"').encode()) == 1
           and entry.count(b'#undef main') == 1 and entry.count(b'Interaction_Forces(INTERSTEP_SymCorrector)') == 1,
           'Exact original stencil and single original-force call required')
    original_invoke, original_save, original_proof = m.invoke, m.save, base.entry_proof
    generated = []

    def proof():
        m.need(base.CPP.read_bytes() == entry, 'Reviewed pressure-row entry changed before compile')
        return dict(original_late_RHS_derivation=rhs_proof, original_polynomial_source=m.stat(quadratic),
                    exact_original_stencil_bytes=len(old_stencil), original_stencil_byte_equal=True,
                    new_entry=m.stat(base.CPP), numerical_original_physical_TUs_unchanged=True,
                    pressure_manufactured_arrays_never_feed_back=True, physical_steps=0)

    def invoke(label, argv, cwd, env=None, target=None):
        m.verify(extra+generated)
        if label == TAG+'.compile':
            m.need(not generated and base.OUT.is_dir() and not include.exists(), 'One fresh shared include required')
            include.write_bytes(shared); m.need(include.read_bytes() == shared, 'Shared include differs')
            generated.append(m.stat(include))
        m.need(len(generated) == 1, 'Shared source must precede compile/link')
        call = original_invoke(label, argv, cwd, env, target)
        m.verify(extra+generated); m.need(include.read_bytes() == shared, 'Shared source changed during build')
        return call

    def save(path, value):
        if value.get('stage') == TAG+'.build':
            if value.get('passed'):
                m.verify(extra+generated)
                dependencies = m.read(base.OUT/'dependencies.json')['Data']
                m.need(len(generated) == 1 and include.resolve() in {Path(q).resolve() for q in dependencies['Includes']},
                       'Actual compile missed reviewed shared source')
                value['consumed'] += extra+generated
                value.update(shared_source=m.stat(source), generated_shared_include=generated[0],
                             shared_transform=['protected Probe access', 'diagnostic AppInfo name only'],
                             pressure_row_scope=m.stat(scope), zero_step_qualification=m.stat(rhs_check),
                             polynomial_qualification=m.stat(quad_check), original_stencil_byte_equal=True,
                             program_basename_retained='C08H18LateRhsR1.exe', allowed_source_part=300,
                             expected_force_calls=1, physical_steps_authorized_by_build=0,
                             wall_reconstruction_is_lagged=True, acceleration_is_frozen=True,
                             implicit_trajectory_or_TPI_implemented=False, no_automatic_component_or_solver=True)
            else: value['shared_partial_outputs_preserved'] = True
        return original_save(path, value)

    try:
        m.verify(extra); m.invoke, m.save, base.entry_proof = invoke, save, proof
        base.main()  # Keeps --execution-authorized, frozen headers, ABI and86-object closure.
    finally:
        m.invoke, m.save, base.entry_proof = original_invoke, original_save, original_proof


if __name__ == '__main__': main()
