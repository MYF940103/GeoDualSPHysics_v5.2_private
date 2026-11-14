"""Author-only build recipe: one finite-Kw CN test entry +86 original CPU objects."""
from pathlib import Path
import c08_h18_late_rhs_r1_build as base

TAG = 'c08_h18_cn_step_r1'


def main():
    m, t, logs = base.m, base.T, base.L
    rhs_source = t/'support/c08_h18_late_rhs_r1.cpp'
    step_source = t/'support/c08_h18_late_step_r1.cpp'
    row_source = t/'support/c08_h18_pressure_row_r1.cpp'
    step_build = logs/'c08_h18_late_step_r1.build.json'
    step_check = logs/'c08_h18_late_step_r1_p300.check.json'
    row_build = logs/'c08_h18_pressure_row_r1.build.json'
    row_check = logs/'c08_h18_pressure_row_r1.check.json'
    scope = t/'notes/c08_pressure_integration_scope_r1.md'
    sb, sc, rb, rc = (m.read(p) for p in (step_build, step_check, row_build, row_check))
    for build, source in ((sb, step_source), (rb, row_source)):
        m.need(build['passed'] and build['source'] == m.stat(source) and build['original_Single_no_hook']
               and build['physical_objects_compiled'] == 0 and build['actual_link_objects'] == 87,
               'Closed original CPU fixture/source binding required')
    m.need(sc['passed'] and sc['consumed_stats_unchanged'] and sc['physical_steps'] == 1,
           'Already-completed original Part300 one-step control required; never run OFF again')
    m.need(rc['passed'] and rc['consumed_stats_unchanged'] and rc['component_invocations'] == 1
           and rc['physical_steps'] == 0, 'Passed complete frozen pressure-row component required')
    sd, rd = (m.read(m.bind(q['completion'])['path']) for q in (sc, rc))
    m.need(sd['passed'] and sd['source_part'] == 300 and sd['source_completed_step'] == 2600000
           and sd['completed_step'] == 2600001 and sd['actual_force_calls'] == 2
           and sd['all6_material_sigma_and_policy_kappa_bits_matched'] and sd['positive_only_completed_cap_verified'],
           'Original Part300 completion differs')
    m.need(rd['passed'] and rd['source_part'] == 300 and rd['source_completed_step'] == 2600000
           and rd['literal_final_float_bits_matched'] == rd['row_records'] == 5000
           and rd['actual_force_calls'] == 1 and rd['physical_steps'] == 0,
           'Original Part300 row completion differs')
    extra = [m.stat(p) for p in (Path(__file__), Path(base.__file__), rhs_source, step_source, row_source,
                                step_build, step_check, row_build, row_check, scope)]
    for checked in (sc, rc):
        call = m.read(m.bind(checked['actual_call'])['path'])
        m.need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0,
               'Actual retained owned component failed')
        extra += [m.bind(checked[k]) for k in ('actual_call', 'completion', 'build')]
    extra += [m.bind(q) for q in sc['outputs']]
    rhs_proof = base.entry_proof()
    raw_rhs, raw_step, raw_row = (p.read_bytes() for p in (rhs_source, step_source, row_source))
    access = b'class Probe:public JSphCpuSingle{'
    app = b'JAppInfo AppInfo("C08H18LateRhs","r1","14-11-2026");'
    m.need(raw_rhs.count(access) == raw_rhs.count(app) == 1, 'Unique inherited RHS access/app anchors required')
    shared_rhs = raw_rhs.replace(access, access+b'\nprotected:', 1).replace(
        app, b'JAppInfo AppInfo("C08H18CnStep","r1","14-11-2026");', 1)
    old_include = b'#include "../outputs/c08_h18_late_step_r1_build/shared.inc"'
    step_access = b'class StepProbe:public Probe{'
    step_main = b'int main(int argc,char** argv)'
    m.need(raw_step.count(old_include) == raw_step.count(step_access) == raw_step.count(step_main) == 1,
           'Unique original StepProbe/include/main anchors required')
    shared_step = raw_step.replace(old_include, ('#include "../outputs/'+TAG+'_build/shared.inc"').encode(), 1)
    shared_step = shared_step.replace(step_access, step_access+b'\nprotected:', 1).replace(
        step_main, b'int c08_original_late_step_unused_main(int argc,char** argv)', 1)
    base.TAG = TAG; base.OUT = t/'outputs'/(TAG+'_build')
    base.CPP = t/'support'/(TAG+'.cpp'); base.NOTE = t/'notes'/(TAG+'.md')
    include, step_include = base.OUT/'shared.inc', base.OUT/'shared_step.inc'
    entry = base.CPP.read_bytes()

    def section(raw, begin, end):
        m.need(raw.count(begin) == raw.count(end) == 1, 'Unique original section anchors required')
        return raw[raw.index(begin):raw.index(end)+len(end)]

    stencil_begin = b'  std::vector<QuadDonor> Stencil(unsigned i,unsigned& fixed,unsigned& almost)const{'
    stencil_end = b'    }Need(!out.empty(),"Empty actual force stencil");return out;\n  }'
    budget_begin = b'  static double RateBudget('
    budget_end = b'    return fbudget+2*RoundoffGamma(64*(z.count+1))*magnitude;\n  }'
    toy_begin = b'static unsigned RowCoupledManufacture('
    toy_end = b'  }return rows;\n}'
    original_sections = []
    for begin, end in ((stencil_begin, stencil_end), (budget_begin, budget_end), (toy_begin, toy_end)):
        old = section(raw_row, begin, end)
        m.need(section(entry, begin, end) == old, 'Original pressure stencil/rate envelope/CN toy body changed')
        original_sections.append(len(old))
    m.need(entry.count(('#include "../outputs/'+TAG+'_build/shared_step.inc"').encode()) == 1
           and entry.count(b'Interaction_Forces(INTERSTEP_SymPredictor)') == 1
           and entry.count(b'Interaction_Forces(INTERSTEP_SymCorrector)') == 1
           and entry.count(b'ComputeSymplecticPre(dt)') == 1
           and entry.count(b'ComputeSymplecticCorr(dt)') == 1
           and entry.count(b'CommitCn(midpoint,off)') == 1
           and entry.index(b'midpoint=MidpointRows(n,fh,rows,constant)') < entry.index(b'ComputeSymplecticCorr(dt)')
           < entry.index(b'CommitCn(midpoint,off)') < entry.index(b'next=Capture("completed_cap"'),
           'One actual midpoint, one original corrector and one pre-cap pressure intervention required')
    original_invoke, original_save, original_proof = m.invoke, m.save, base.entry_proof
    generated = []

    def proof():
        m.need(base.CPP.read_bytes() == entry, 'Reviewed CN entry changed before compile')
        return dict(original_late_RHS_derivation=rhs_proof, original_step_source=m.stat(step_source),
                    original_pressure_row_source=m.stat(row_source), original_exact_section_bytes=original_sections,
                    exact_original_stencil_rate_budget_and_CN_toy=True,
                    actual_one_step_call_order_preserved_with_pressure_intervention=True,
                    whole_original_step_block_byte_equal=False, single_changed_state_field='soil pressure',
                    true_midpoint_capacity_before_corrector=True, physical_steps_authorized_by_build=0)

    def invoke(label, argv, cwd, env=None, target=None):
        m.verify(extra+generated)
        if label == TAG+'.compile':
            m.need(not generated and base.OUT.is_dir() and not include.exists() and not step_include.exists(),
                   'Fresh generated shared fixtures required')
            for path, content in ((include, shared_rhs), (step_include, shared_step)):
                path.write_bytes(content); m.need(path.read_bytes() == content, 'Generated fixture differs')
                generated.append(m.stat(path))
        m.need(len(generated) == 2, 'Both reviewed includes must precede compile/link')
        call = original_invoke(label, argv, cwd, env, target)
        m.verify(extra+generated)
        m.need(include.read_bytes() == shared_rhs and step_include.read_bytes() == shared_step,
               'Generated fixture changed during build')
        return call

    def save(path, value):
        if value.get('stage') == TAG+'.build':
            if value.get('passed'):
                m.verify(extra+generated)
                deps = {Path(q).resolve() for q in m.read(base.OUT/'dependencies.json')['Data']['Includes']}
                m.need(include.resolve() in deps and step_include.resolve() in deps
                       and (base.OUT/'headers/src/source/FunSoilMaterial.h').resolve() in deps,
                       'Actual compiler missed archived material/shared fixtures')
                value['consumed'] += extra+generated
                value.update(generated_shared_includes=generated,
                             inherited_source_transforms=['protected Probe and StepProbe access',
                                 'diagnostic AppInfo', 'fresh shared include path', 'unused original main name'],
                             retained_original_Part300_control=m.stat(step_check), pressure_row_qualification=m.stat(row_check),
                             only_admitted_part=300, expected_component_force_calls=2,
                             each_component_max_physical_steps=1, physical_steps_authorized_by_build=0,
                             default_production_solver_unchanged=True, no_extra_OFF_trajectory=True,
                             global_implicit_or_TPI=False, no_automatic_component_or_solver=True)
            else: value['shared_partial_outputs_preserved'] = True
        return original_save(path, value)

    try:
        m.verify(extra); m.invoke, m.save, base.entry_proof = invoke, save, proof
        base.main()
    finally:
        m.invoke, m.save, base.entry_proof = original_invoke, original_save, original_proof


if __name__ == '__main__': main()
