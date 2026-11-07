"""Prepare fresh root r5 GPU receiver inputs/runtime after review; never invoke any executable."""
import argparse,json,re,shutil,xml.etree.ElementTree as ET
from pathlib import Path
import mdbc_partition_components_r3 as e

T=Path(__file__).resolve().parents[1];C=T.parent;L=T/'logs';TAG='upl_c08_formal_psi0_r5_r1'
DECISION=L/'upl_c08_bedkeep_window_decision_r1.json';ADMISSION=L/'upl_c08_formal_r5_r1.admission.json';RECEIPT=L/'upl_c08_r5_prepare_r1.prepare.json'
BUILD=L/'upl_c08_bedkeep_Release_r1.build.json';NATIVE=L/'upl_c08_bedkeep_formal_native_r1.build.json';RUNTIME=C/'support/runtime_r5'
GROUPS=('psi0','psi2p5','psim5');need,read,stat=e.need,e.read,e.stat

def bound(entry):need(stat(entry['path'])==entry,'Closed binding changed: '+entry['path']);return entry
def write(path,text):
    with path.open('xb') as f:f.write(text.encode('utf-8'))
def stem(group,version):return 'CaseLianSaturatedColumnCollapse_'+group+'_shared_'+version

def xml_text(group):
    p=C/(stem(group,'r4')+'_Def.xml');old=p.read_bytes().decode('utf-8-sig');nl='\r\n' if '\r\n' in old else '\n';text=old
    text=text.replace('<!-- r4 receiver candidate: NoPen release-only operator split, artificial stress OFF; reuse a certified same-backend elastic PRE. Full 3 s collapse remains unreviewed. -->','<!-- r5 receiver: KeepBedOverlap, fixed-plane NoPen and release-only AS1; certified original GPU PRE. Only psi0 has one diagnostic admission; other groups are locked. -->')
    marker='release_mkbound="2" statefile="__GRAVITY_PRELOAD_STATE__"';need(text.count(marker)==1,'Exactly one unchanged PRE marker required');text=text.replace(marker,'release_mkbound="2" keep_bed_overlap="true" statefile="__GRAVITY_PRELOAD_STATE__"')
    pattern=r'(?m)^([ \t]*)<parameter key="ArtificialStress" value="0"[^\r\n]*?/>'
    def replacement(m):
        q=m[1];return nl.join((q+'<parameter key="ArtificialStress" value="1" comment="Release-only total-stress artificial stress; preload operator remains unchanged" />',q+'<parameter key="ArtificialStressCoef" value="0.2" comment="Explicit existing Bui artificial-stress coefficient" />',q+'<parameter key="ArtificialStressExp" value="2.55" comment="Explicit existing Bui artificial-stress exponent" />'))
    text,n=re.subn(pattern,replacement,text);need(n==1,'Exactly one AS0 parameter required')
    text=text.replace('Initial right wall layers; retired at t=10 s with soil history retained','Initial right wall normals retained for PRE identity; roles change only after certified release')
    text=text.replace('Right wall: free-slip during preload; retired at t=10 s','Right wall: preload free-slip; release retires255 and retains five shallow bed samples as NoSlip')
    a,b=ET.fromstring(old),ET.fromstring(text);need(ET.tostring(a.find('casedef'))==ET.tostring(b.find('casedef')),'Geometry or constants changed')
    need(ET.tostring(a.find('execution/special/soils'))==ET.tostring(b.find('execution/special/soils')) and ET.tostring(a.find('execution/special/hydromechanics'))==ET.tostring(b.find('execution/special/hydromechanics')),'Group material/hydraulics changed')
    p={x.get('key'):x.get('value') for x in b.findall('execution/parameters/parameter')};need(all(float(p[k])==v for k,v in dict(TimeMax=13,TimeOut=.01,DtFixed=.0000025,DtMin=1e-8,NoPenetration=1,ArtificialStress=1,ArtificialStressCoef=.2,ArtificialStressExp=2.55).items()),'Locked r5 parameters differ')
    return text

def launcher_text():
    text=(C/'support/run_lian_collapse_shared_r4_win64.bat').read_bytes().decode('utf-8-sig');nl='\r\n' if '\r\n' in text else '\n';text=text.replace('runtime_r4','runtime_r5').replace('shared_r4','shared_r5').replace('postprocess_lian_collapse_r4.py','postprocess_lian_collapse_r5.py')
    text=text.replace('    if /i "%%~A" == "--unattended" set "c08unattended=1"','    if /i "%%~A" == "--unattended" set "c08unattended=1"'+nl+'    if /i "%%~A" == "-unattended" set "c08unattended=1"')
    start=text.index('if /i "%backend%" == "CPU" (');end=text.index('if /i "%backend%" == "GPU" (',start)
    text=text[:start]+'rem Only the reviewed psi0 GPU diagnostic is admitted; prepared other groups stay locked.'+nl+'if /i not "%~1" == "psi0" goto locked'+nl+'if /i not "%backend%" == "GPU" goto fail'+nl+text[end:]
    text=text.replace(':exists'+nl,':locked'+nl+'echo This group is prepared but NOT admitted. No GenCase, solver or postprocessing was started.'+nl+'goto failed'+nl+nl+':exists'+nl)
    need(text.count(':locked')==1 and 'goto locked' in text and 'runtime_r4' not in text and 'shared_r4' not in text,'r5 launcher identity/lock differs');return text

README='''# r5: one psi0 GPU 3 s diagnostic, other groups locked

Double-click xCaseLianSaturatedColumnCollapse_psi0_shared_r5_win64_GPU.bat. It checks Python/NumPy/Matplotlib, runtime_r5 tools and the original source schedule before GenCase; then performs one fresh receiver, native review, separate PartFluid/PartBound series and PNG/CSV. Nothing is installed automatically. Python prefers D:/anaconda3/python.exe, otherwise PATH python. Runtime contains only the matched GPU Release solver, GenCase, PartVTK, new C08Native and their supplied configuration/DLLs; no old-exe fallback.

All three group XML/GPU BAT files are prepared with their original material values. Only psi0 is admitted. psi2p5 and psim5 stop before any GenCase, solver or postprocessing; there is no automatic three-group sequence. No CPU or new PRELOAD entry is provided.

The GPU wrapper explicitly binds CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4. Keep the entire original source folder. The loader imports actual time/p/p0/J/theta/stress/kappa and certifies the PRE; it does not rerun10 s, assign a geostatic stress field or provide a generic plastic PART restart.

Original geometry/materials/Model1-Ck2/free-seepage and required stability limits remain. New release choices are keep_bed_overlap=true, fixed-plane NoPen1 and AS1 with epsilon .2/exponent2.55, both release-only. Five original shallow fixed IDs1800,1852,1904,1956,2008 become the NoSlip bed with +DpZ normals;255 other right-wall IDs retire. Native counts are6805=5000soil+1805fixed. NoPen is FixedPlaneStageProjectionReleaseOnly; same-stage Darcy reaction is not closed. Initial CfgInit normals are not post-release boundary-normal telemetry.

dt2.5us/DtMin1e-8, event10, TimeMax13 and output .01 are unchanged. Actual imported scalar clock is retained; tau uses actual source time and Part0 is post-release, not PRE. The intended new updates are1.2M, global end5.2M and300 real saves, verified by actual native output. The original Run.csv registry remains7060/2060.

The prior .6 s/60-state diagnostic completed and crossed the old .53 wall-fit failure, with all original native guards. Negative-pressure transients remain a stated limitation. This admits one bounded extension, not equilibrium, full-collapse physical accuracy or paper acceptance. The independent decision is tests/logs/upl_c08_bedkeep_window_decision_r1.json.

Output is CaseLianSaturatedColumnCollapse_psi0_shared_r5_GPU_out. Existing output refuses a physical run. If the solver completes but postprocessing fails, repair derived outputs only and run the same BAT with --postprocess --unattended (either order; -unattended is also accepted). This mode never GenCases/restarts/solves and does not alter BI4. It resumes only compatible completed post-tool records; incompatible partial derived data are preserved for diagnosis.

particles/PartFluid_####.vtk contains5000soil; PartBound_####.vtk contains1805fixed, all actual frames, never PartAll. Native Posd/double stress remain available; official VTK storage precision is reported separately. Kplastic is scalar plastic history, not the full plastic strain tensor. Keep all source/receiver data and logs. Old r3/r4 inputs, runtimes, failed outputs and ZIP snapshots are unchanged.
'''

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read before one explicit preparation')
    targets=[C/(stem(g,'r5')+'_Def.xml') for g in GROUPS]+[C/('x'+stem(g,'r5')+'_win64_GPU.bat') for g in GROUPS]+[C/'support/run_lian_collapse_shared_r5_win64.bat',C/'README_server_r5.md']
    need(not RUNTIME.exists() and not ADMISSION.exists() and not RECEIPT.exists() and not any(p.exists() for p in targets) and not any((C/(stem(g,'r5')+'_GPU_out')).exists() for g in GROUPS),'Existing r5 input/runtime/output/receipt preserved')
    before=[];result=dict(stage='upl_c08_r5_prepare_r1',passed=False,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,queue_invocations=0,SHA_scans=0,physical_acceptance=False)
    try:
        decision=read(DECISION);need(decision['passed'] and decision['decision']=='admit_one_fresh_root_psi0_3s_diagnostic_only' and decision['allowed_job']==TAG and decision['root_3s_admitted'] and not decision['other_psi_admitted'] and not decision['physical_acceptance'],'Exact root psi0-only decision required');before.append(stat(DECISION))
        for key in ('source_run','source_native','review','visual'):before.append(bound(decision[key]))
        run,native,review=(read(decision[k]['path']) for k in ('source_run','source_native','review'));need(run['passed'] and run['actual_exit']==run['actual_Win32_exit']==0 and run['actual_steps']==4240000 and run['saved_frames']==60 and run['consumed_stats_unchanged'] and native['passed'] and native['original_native_guards_passed'] and native['consumed_stats_unchanged'] and review['passed'] and review['new_normal_frames']==60 and review['three_way_actual_common_steps']==53,'Closed .6s runtime/native/review required')
        build,nb=read(BUILD),read(NATIVE);need(build['passed'] and build['actual_typed_exit_code']==build['actual_Win32_exit']==0 and build['source_stats_unchanged'] and build['release_geometry_policy']=='KeepBedOverlapReleaseOnly' and len(build['project_objects'])==113,'Closed bedkeep GPU Release required');need(nb['passed'] and nb['consumed_stats_unchanged'],'Closed new formal native tool required')
        before.extend(stat(p) for p in (BUILD,NATIVE,Path(__file__),T/'support/upl_c08_formal_psi0_r5_r1.py',T/'notes/upl_c08_formal_r5_r1.md',C/'support/postprocess_lian_collapse_r5.py',C/'support/check_lian_preload_schedule_r1.ps1',C/'README_server_r4.md',C/'support/run_lian_collapse_shared_r4_win64.bat'))
        for g in GROUPS:before.extend(stat(C/name) for name in (stem(g,'r4')+'_Def.xml','x'+stem(g,'r4')+'_win64_GPU.bat'))
        before.extend(bound(build[k]) for k in ('program','source_capture','source_archive'));before.append(bound(nb['program']))
        sources={name:C/'support/runtime_r4'/name for name in ('GenCase_win64.exe','PartVTK_win64.exe','DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll')};sources.update({'DualSPHysics5.2_GEO_win64.exe':Path(build['program']['path']),'C08Native_win64.exe':Path(nb['program']['path'])});before.extend(stat(p) for p in sources.values())
        texts={C/(stem(g,'r5')+'_Def.xml'):xml_text(g) for g in GROUPS}
        for g in GROUPS:
            old=(C/('x'+stem(g,'r4')+'_win64_GPU.bat')).read_bytes().decode('utf-8-sig');texts[C/('x'+stem(g,'r5')+'_win64_GPU.bat')]=old.replace('r4','r5').replace('r5 NoPen receiver only; preserve and certify the original GPU elastic PRE.','r5 GPU receiver; only psi0 admitted, others locked; keep the original certified GPU PRE.')
        texts[C/'support/run_lian_collapse_shared_r5_win64.bat']=launcher_text();texts[C/'README_server_r5.md']=README
        for path,text in texts.items():write(path,text)
        RUNTIME.mkdir();runtime=[]
        for leaf,source in sources.items():
            old=stat(source);dest=RUNTIME/leaf;shutil.copy2(source,dest);entry=stat(dest);need((old['bytes'],old['mtime_ns'])==(entry['bytes'],entry['mtime_ns']),'New runtime copy differs: '+leaf);runtime.append(entry)
        inputs=[stat(p) for p in targets]+runtime+[stat(C/'support/postprocess_lian_collapse_r5.py'),stat(C/'support/check_lian_preload_schedule_r1.ps1'),stat(T/'support/upl_c08_formal_psi0_r5_r1.py'),stat(T/'notes/upl_c08_formal_r5_r1.md'),stat(T/'support/upl_c08_asplane_summary_r1.py')]
        need(all(stat(p['path'])==p for p in before),'Preparation consumed inputs changed');ad=dict(stage='upl_c08_formal_r5_r1.admission',passed=True,allowed_job=TAG,physical_acceptance=False,other_psi_admitted=False,decision=stat(DECISION),program=stat(RUNTIME/'DualSPHysics5.2_GEO_win64.exe'),source_build=stat(BUILD),source_capture=build['source_capture'],source_archive=build['source_archive'],native_build=stat(NATIVE),runtime=runtime,inputs=inputs,consumed=before)
        e.save(ADMISSION,ad);result.update(passed=True,formal_admission=stat(ADMISSION),generated=[stat(p) for p in targets],runtime=runtime,consumed_stats_unchanged=True)
    except Exception as error:result['first_failure']=str(error)
    result['consumed']=before;e.save(RECEIPT,result);print(json.dumps(dict(passed=result['passed'],receipt=str(RECEIPT),first_failure=result.get('first_failure'))));return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
