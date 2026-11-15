"""Build only the bounded two-state plastic-HG CPU-stage prototype; never run it."""
import argparse
import os
import shutil
import struct
import subprocess
from pathlib import Path
import c08_h18_as03_step_r1_build as prior

m, T, L, S = prior.m, prior.T, prior.L, prior.S
TAG = 'c08_h18_plastic_hg_stage_r1'
CPP, HDR, NOTE = T/'support'/(TAG+'.cpp'), T/'support'/(TAG+'.hpp'), T/'notes'/(TAG+'.md')
OUT = T/'outputs'/(TAG+'_build')
BASE = L/'c08_h18_as03_step_r1.build.json'
GEOMETRY = L/'c08_h18_hg_saved_geometry_r1.check.json'
ENERGY = L/'c08_h18_hg_energy_memory_r1.check.json'
OLD_RHS = L/'c08_h18_as03_rhs_r1.build.json'
OLD_CPP = T/'support/c08_h18_as03_step_r1.cpp'
RHS_CPP = T/'support/c08_h18_as03_rhs_r1.cpp'


def generate():
    rhs, step = RHS_CPP.read_bytes(), OLD_CPP.read_bytes()
    anchor = b'class Probe:public JSphCpuSingle{'
    app = b'JAppInfo AppInfo("C08H18As03Rhs","r1","14-11-2026");'
    m.need(rhs.count(anchor) == rhs.count(app) == 1 and
           b'Parts[2]={38,76},Steps[2]={2076001,2152001}' in rhs,
           'Exact previously qualified AS03 loader/profile required')
    shared = rhs.replace(anchor, anchor+b'\nprotected:', 1).replace(
        app, b'JAppInfo AppInfo("C08H18PlasticHgStage","r1","15-11-2026");', 1)
    begin, end = b'struct StepState{', b'\npublic:\n  void ExecuteStep('
    m.need(step.count(begin) == step.count(end) == 1,
           'Unique actual stage capture/material-shadow prefix required')
    block = step[step.index(begin):step.index(end)]
    access = b'class StepProbe:public Probe{'
    m.need(block.count(access) == 1 and block.count(b'Capture(') == 1
           and block.count(b'MaterialShadow(') == 1, 'Original helper prefix differs')
    helpers = block.replace(access, access+b'\nprotected:', 1)+b'\n};\n'
    m.need(helpers.replace(access+b'\nprotected:', access, 1)[:-4] == block,
           'Capture/material numeric helper derivation is not reversible')
    authored = CPP.read_text(encoding='utf-8')
    m.need(authored.count('ComputeStep_Sym()') == 1
           and authored.count('ComputeDynamicPorePressureRateCpu();') == 1
           and authored.count('model.Evaluate(') == 1
           and authored.count('ComputeSymplecticPre(dt);') == 1
           and authored.count('ComputeSymplecticCorr(dt);') == 1
           and authored.count('stageFile.open("NUL")') == 1,
           'Closed actual/original/manual/HG lifecycle or output scope differs')
    return shared, helpers, dict(shared_source=m.stat(RHS_CPP), helper_source=m.stat(OLD_CPP),
        shared_changes=['Probe protected access only', 'diagnostic AppInfo only'],
        helper_changes=['exact prefix through SameJP', 'StepProbe protected access only', 'close helper class'],
        helper_numeric_prefix_exact=True, helper_prefix_bytes=len(block),
        original_snapshot_parts=[38,76], original_snapshot_steps=[2076001,2152001],
        original_physical_TU_changed=False, original_class_ABI_changed=False,
        source_data_or_material_parameters_changed=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execution-authorized',action='store_true')
    m.need(p.parse_args().execution_authorized,'Independent root build admission required; no program follows')
    receipt=L/(TAG+'.build.json'); labels=[TAG+'.compile',TAG+'.link']
    m.need(not OUT.exists() and not receipt.exists() and all(not (L/(q+ext)).exists()
           for q in labels for ext in ('.call.json','.log')),'Existing complete/partial build protected')
    consumed,calls=[],[]
    try:
        base,rhs,geometry,energy=map(m.read,(BASE,OLD_RHS,GEOMETRY,ENERGY))
        m.need(base['passed'] and base['configuration']=='DebugCPU' and base['consumed_stats_unchanged']
               and base['actual_link_objects']==87 and base['physical_objects_compiled']==0
               and base['original_Single_no_hook'] and base['source']==m.stat(OLD_CPP),
               'Exact original AS03 one-step/no-hook build required')
        m.need(rhs['passed'] and rhs['consumed_stats_unchanged'] and rhs['source_archive']==base['source_archive']
               and rhs['retained_physical_objects']==base['retained_physical_objects'],
               'Original 86-object/current archive closure differs')
        m.need(geometry['passed'] and geometry['analysis_complete'] and geometry['consumed_stats_unchanged']
               and geometry['parts']==[0,38,60,83,87,300] and geometry['receiver_rows']==30000
               and geometry['rank_failure_total']==0 and geometry['all_necessary_geometry_dt_gates_pass']
               and geometry['new_energy_active_graph_all_pass'] and geometry['xi_prescribed_double']==.1
               and geometry['constants']['G_float_Pa']==7518796.5
               and geometry['constants']['H_m']==struct.unpack('<f',struct.pack('<f',.072))[0],
               'Already completed actual saved-state HG geometry/5us screen required')
        edone=m.read(m.bind(energy['completion'])['path'])
        m.need(energy['passed'] and energy['consumed_stats_unchanged'] and energy['component_invocations']==1
               and edone['passed'] and edone['active_edge_only_energy_state_new_model']
               and edone['same_current_P_S_in_drive_and_force']
               and edone['fixed_interval_contract_and_lifecycle_ledger']
               and not edone['actual_Symplectic_qualified'],'Passed bounded normalized-memory mathematics required')
        consumed=[m.stat(q) for q in (Path(__file__),CPP,HDR,NOTE,BASE,OLD_RHS,GEOMETRY,ENERGY,
                    OLD_CPP,RHS_CPP,Path(prior.__file__))]
        for part in (38,76):
            qpath=L/('c08_h18_as03_step_r1_p'+str(part)+'.check.json');q=m.read(qpath)
            dref=m.bind(q['completion']);d=m.read(dref['path'])
            m.need(q['passed'] and q['consumed_stats_unchanged'] and q['physical_steps']==1
                   and d['passed'] and d['source_part']==part
                   and d['all6_material_sigma_and_policy_kappa_bits_matched']
                   and d['sorted_predictor_scalar_bases_bit_equal']
                   and d['positive_only_completed_cap_verified'], 'Original actual one-step/mat/pore safety proof required')
            consumed += [m.stat(qpath),dref,m.bind(q['actual_call'])]
        consumed += [m.bind(energy[k]) for k in ('completion','actual_call')]
        shared,helpers,proof=generate()
        objects=[m.bind(q) for q in base['retained_physical_objects']]
        headers=[m.bind(q) for q in base['archived_headers']]
        runtime=[m.bind(q) for q in base['runtime']]
        m.need(len(objects)==86 and len(headers)==160 and len(runtime)==7,
               'Exactly86 original physical objects/160 archive headers/7 companions required')
        consumed += objects+headers+runtime
        consumed += [m.bind(base[k]) for k in ('source_build','source_capture','source_archive')]
        inventory=m.bind(rhs['original_object_list']);object_list=m.read(inventory['path']);tlog=m.bind(object_list['resolved_library_tlog'])
        libraries=[Path(q.strip('"')).resolve() for q in Path(tlog['path']).read_text(encoding='utf-16').splitlines()
                   if not q.startswith('^') and q.lower().endswith('.lib')]
        consumed += [inventory,tlog]+[m.stat(q) for q in libraries]
        ccpath,lcpath=L/'c08_h18_as03_step_r1.compile.call.json',L/'c08_h18_as03_step_r1.link.call.json'
        cc,lc=m.read(ccpath),m.read(lcpath)
        m.need(all(q['actual_Popen_wait_exit']==q['actual_Win32_exit']==0 and q['ownership_failure'] is None for q in (cc,lc)),
               'Actual original compiler/linker calls required')
        consumed += [m.stat(q) for q in (ccpath,lcpath,cc['program'],lc['program'])]
        oldout=Path(base['program']['path']).parent
        ca=[str(CPP) if q==str(OLD_CPP) else q if q.lower().startswith('/i') else q.replace(str(oldout),str(OUT)) for q in cc['arguments']]
        exe=OUT/'C08H18PlasticHgStageR1.exe'
        la=[q.replace(str(oldout),str(OUT)).replace(Path(base['program']['path']).name,exe.name) for q in lc['arguments']]
        roots=[Path(q[2:]).resolve() for q in ca if q.startswith('/I')]
        final=[Path(q).resolve() for q in la if q.lower().endswith('.obj')]
        m.need(ca.count(str(CPP))==1 and len(roots)==1 and all(q in ca for q in
               ('/Od','/MTd','/RTC1','/fp:precise','/openmp','/std:c++17'))
               and len(final)==len(set(final))==87
               and set(final)=={Path(q['path']).resolve() for q in objects}|{(OUT/'entry.obj').resolve()},
               'Original archived-header ABI and exactly86+1 object closure required')
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        m.need(setup.returncode==0,'Original MSVC environment unavailable')
        env={k.upper():v for k,v in os.environ.items()}
        env.update((k.upper(),v) for k,v in (q.split('=',1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION']=='14.36.32532' and libraries,'Original MSVC/library ABI differs')
        env.pop('CL',None);env.pop('_CL_',None);env['LIB']=';'.join(dict.fromkeys(str(q.parent) for q in libraries))
        m.verify(consumed);OUT.mkdir()
        generated=[]
        for leaf,data in (('shared.inc',shared),('step_helpers.inc',helpers)):
            with (OUT/leaf).open('xb') as f:f.write(data)
            generated.append(m.stat(OUT/leaf))
        consumed += generated
        calls.append(m.invoke(labels[0],[str(cc['program']),*ca],S/'VS',env))
        dep=m.read(OUT/'dependencies.json')['Data'];included={Path(q).resolve() for q in dep['Includes']};root=roots[0]
        names={Path(q['path']).name.lower() for q in headers}
        m.need(Path(dep['Source']).resolve()==CPP.resolve() and HDR.resolve() in included
               and all(Path(q['path']).resolve() in included for q in generated)
               and all((root/q).resolve() in included for q in ('JSph.h','JSphCpu.h','JSphCpuSingle.h','JDsFixedDt.h','FunSoilMaterial.h','FunSphKernel.h'))
               and all(q.is_relative_to(root) for q in included if q.name.lower() in names)
               and all(not q.is_relative_to((S/'source').resolve()) for q in included),
               'Compilation missed frozen implementation/shared helpers or leaked public headers')
        calls.append(m.invoke(labels[1],[str(lc['program']),*la],S/'VS',env))
        copied=[]
        for q in runtime:
            dest=OUT/Path(q['path']).name;shutil.copy2(q['path'],dest)
            m.need(dest.read_bytes()==Path(q['path']).read_bytes(),'Original runtime copy differs');copied.append(m.stat(dest))
        m.verify(consumed)
        m.save(receipt,dict(stage=TAG+'.build',passed=True,configuration='DebugCPU',source=m.stat(CPP),header=m.stat(HDR),note=m.stat(NOTE),program=m.stat(exe),
            original_step_build=m.stat(BASE),source_build=base['source_build'],source_capture=base['source_capture'],source_archive=base['source_archive'],
            generated_includes=generated,entry_derivation=proof,retained_physical_objects=objects,archived_headers=headers,
            original_Single_no_hook=True,actual_link_objects=87,new_entry_objects=1,physical_objects_compiled=0,
            allowed_parts=[38,76],max_total_actual_updates=8,original_complete_method_steps=2,manual_OFF_steps=2,ON_steps=4,
            independent_constant_FixedDt_scopes_required=6,baseline_CPU22_equivalent_comparison_required=True,
            same_input_material_re_evaluation_required=True,extra_complete_Darcy_re_evaluation_required=True,
            actual_Symplectic_or_coupled_energy_acceptance=False,new_native22_series=False,
            dependencies=m.stat(OUT/'dependencies.json'),runtime=copied,calls=calls,consumed=consumed,consumed_stats_unchanged=True,
            compile_invocations=1,link_invocations=1,component_invocations=0,solver_invocations=0,reader_invocations=0,GPU_actions=0,SHA_scans=0,
            no_automatic_component_or_solver=True,public_source_changed=False,physical_acceptance=False))
    except Exception as error:
        if not receipt.exists():m.save(receipt,dict(stage=TAG+'.build',passed=False,first_failure=str(error),calls=calls,consumed=consumed,
            partial_outputs_preserved=True,component_invocations=0,solver_invocations=0,GPU_actions=0,SHA_scans=0,physical_acceptance=False))
        raise

if __name__=='__main__':main()
