"""Author-reviewed r3 server candidate assembly. No build, GenCase or solver; ZIP is a separate explicit action."""
import argparse,hashlib,json,re,shutil,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
from upl_c08_release_package_r1 import CASE,TESTS,need,stat,bound,load,encoded
from upl_c08_shared_release_r2_prepare import schedule,launcher as retained_launcher
PACKAGE='LianCollapse_upl_win64_r3';SOURCE='CaseLianSaturatedColumnCollapse_shared_preload_r3'
CODE_CHECKPOINT='22723a1dd21a5be460a11b8da5c26194aa50c0e7'  # Later saved code checkpoint, NOT the build-time HEAD.
CAPTURE_BASE='6912e824b7cd15a4503097fb9c0d019e90ef2474'
GROUPS=[('psi0',0.,5000.,0.),('psi2p5',2.5,5000.,.2),('psim5',-5.,7500.,.2)]
RUNTIME=['DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','GenCase_win64.exe','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll']


def checked_delivery():
    builds={};inputs=[]
    for config in ('DebugCPU','ReleaseCPU','Debug','Release'):
        p=TESTS/'logs'/f'mdbc_partition_{config}_r1.build.json';b=load(p);need(b['passed']and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged']and b['canonical_and_package_stats_unchanged'],'A matching frozen partition build is not closed/passed');bound(b['program']);bound(b['source_capture']);builds[config]=b;inputs.append(p)
    capture_entry=builds['Release']['source_capture'];need(all(b['source_capture']==capture_entry for b in builds.values()),'Four binaries do not share the same frozen source capture');capture_path=bound(capture_entry);capture=load(capture_path);archive=bound(capture['archive']);need(capture['base_commit']==CAPTURE_BASE,'Actual build capture base changed; do not rewrite provenance')
    checks={}
    for key,name in [('partition_native','mdbc_admission_r2.check.json'),('new_gpu_branches','upl_c08_branches_r1.check.json'),('Version2_PRE_CPU','upl_material_release_native_r1_receive_new_CPU.review.json'),('Version2_PRE_GPU','upl_material_release_native_r1_receive_new_GPU.review.json'),('loader_policy','upl_material_loader_negative_r1.check.json'),('material_CPU_stage','upl_material_stage_cpu_r1.check.json'),('material_GPU_stage','upl_material_stage_gpu_r1.check.json'),('material_CPU_periodic','upl_material_periodic_copy_CPU_r1.check.json')]:
        p=TESTS/'logs'/name;d=load(p);need(d['passed']and d.get('physical_acceptance',False)is False,'A required bounded implementation gate is not passed');checks[key]=stat(p);inputs.append(p)
    branches=load(checks['new_gpu_branches']['path']);need(branches['actual_solver_and_reader_exits_zero']and len(branches['groups'])==2 and branches['new_server_package_created']is False,'New ReleaseGPU material handoff gate differs')
    for g in branches['groups']:
        need(g['all22_fields_and_signed_clock_exact']and g['pressure_RMS_difference_Pa']==g['material_XYZ_difference_mm']==0 and g['new_updates']==420 and g['final_global_completed_step']==800 and g['native_Version2_sf0p2_verified'],'A material branch lost its original strict state/clock gate')
    for backend in ('CPU','GPU'):
        d=load(checks['Version2_PRE_'+backend]['path']);need(d['all_typed22_bits_equal']and d['all_actual_signed_clock_fields_exact']and d['actual_matched_states']==11,'New Version2 PRE continuity not closed')
    partition=load(checks['partition_native']['path']);need(partition['implementation_compatibility_only']and partition['passed']and partition['max_pressure_RMS_difference_Pa']==partition['max_material_XYZ_difference_mm']==0,'Partition native compatibility gate differs')
    programs={'CPU':bound(builds['ReleaseCPU']['program']),'GPU':bound(builds['Release']['program'])};need(programs['CPU'].name=='DualSPHysics5.2CPU_win64.exe'and programs['GPU'].name=='DualSPHysics5.2_GEO_win64.exe','Only selected Release programs may be delivered')
    inputs.extend([capture_path,archive,*programs.values()]);return builds,programs,capture_entry,capture,checks,inputs


def physical_signature(node):
    # Comments may change; every actual XML value except the deprecated alias is retained.
    return (node.tag,tuple(sorted((k,v)for k,v in node.attrib.items()if k not in('comment','units_comment','_rem'))),tuple(physical_signature(x)for x in node if x.tag!='MaterialReturn'))


def definition(label,psi,cohesion,decay):
    oldstem='CaseLianSaturatedColumnCollapse_shared_preload_r2'if label=='PRELOAD'else f'CaseLianSaturatedColumnCollapse_{label}_shared_r2';path=CASE/(oldstem+'_Def.xml');text=path.read_text(encoding='utf-8');old=ET.fromstring(text);soil=old.find('./execution/special/soils');need(soil is not None and soil.find('MaterialReturn').get('value')=='1','Frozen r2 alias template differs')
    values={x.tag:x.attrib['value']for x in soil};need([float(values[k])for k in('dlt','coh','coh_r','n_coh','DilationDecay','phi','phi_r','n_phi')]==[psi,cohesion,1000.,5.,decay,25.,25.,0.],'Frozen material group differs')
    parameters={x.attrib['key']:x.attrib['value']for x in old.findall('./execution/parameters/parameter')};need(all(float(parameters[k])==v for k,v in {'DtFixed':.0000025,'TimeOut':.01,'TimeMax':13.,'Boundary':2.,'SlipMode':3.,'DPCtes':3.,'StepAlgorithm':2.,'SoilHourglassXi':0.,'SoilBoundaryDerivativeSPR':0.}.items()),'Frozen physical scheduling/mDBC configuration differs')
    hydro=old.find('./execution/special/hydromechanics');need(float(hydro.find('HydroMechConductivityModel').get('value'))==1 and float(hydro.find('HydroMechConductivityCk').get('value'))==2,'Frozen Ck2 model differs');event=old.find('./execution/special/gravitypreload');need(event.get('time')=='10.0'and event.get('release_mkbound')=='2'and(event.get('elastic_source')=='true'if label=='PRELOAD'else event.get('statefile')=='__GRAVITY_PRELOAD_STATE__'),'Frozen shared source/receiver contract differs')
    text,count=re.subn(r'^[ \t]*<MaterialReturn\b[^>]*/>\r?\n','',text,flags=re.M);need(count==1,'Exactly one deprecated algorithm alias must be removed')
    text=text.replace('r2 shared-preload calculation input; bounded handoff checked, the actual 10 s source must still certify elasticity and full collapse remains unaccepted.','r3 server validation candidate: unified DP v2 and bounded shared-PRE handoff checked; actual 10 s elasticity and full collapse remain unaccepted.').replace('admitted MR1 softening law','unified DP v2 softening law')
    new=ET.fromstring(text);need(new.find('./execution/special/soils/MaterialReturn')is None and physical_signature(old)==physical_signature(new),'A numerical XML node changed during r3 promotion');return encoded(text),path


def source_version(capture_entry,capture):
    return encoded(f'''r3 server validation candidate, not full-collapse acceptance.
Later saved code checkpoint: {CODE_CHECKPOINT}
The binaries were NOT claimed built at that later commit or the current repository HEAD.
Actual compiled frozen capture: {capture_entry['path']}
Capture base_commit: {capture['base_commit']} plus the then-uncommitted source captured in its immutable archive.
Actual capture archive: {capture['archive']['path']}
Build receipts: mdbc_partition_{{DebugCPU,ReleaseCPU,Debug,Release}}_r1.build.json.
The exact compiled archive remains retained locally; this runnable ZIP does not contain a complete source distribution.
Do not rebuild merely because documentation-only repository HEAD advances.
''')


def readme(proof,capture):
    return encoded(f'''# r3：服务器待完整物理验证的共享预载包

完整解压`{PACKAGE}.zip`后运行，不能在ZIP内双击。Windows x64，NVIDIA RTX A6000，CPU默认8线程，GPU默认GPU0；服务器需Windows UCRT及合适NVIDIA驱动，不需Python、Visual Studio或CUDA Toolkit。

先选择一个后端，运行`x{SOURCE}_win64_CPU.bat`或GPU入口。源成功结束后，再用同一个后端依次运行psi0、psi2p5、psim5三个`shared_r3` BAT。CPU/GPU源不混用，不要同时乱点8个入口；尤其同一GPU0上的三receiver应顺序运行。本启动器没有backend并发锁，保留已有输出拒绝覆盖、源完成记录和原生loader认证规则；不是自动顺次运行全部四流程的一键BAT。每个入口只启动一次目标，不删除、不重试、不自动续算。`--unattended`仅关闭结尾暂停。

源从零有效应力和ConstantZ H=2m静水p0开始真实重力预载。dt=2.5微秒，TimeOut=0.01s，event=10s/TimeMax=13s；源BAT用`-nsteps:4000000`停在完整PRE、尚未撤墙，预期{proof['part_files']}帧、末文件`{proof['last_part']}`。这是调度预期，不是已跑过10s。实际标量时钟预计{proof['actual_scalar_time']:.17g}s，接收必须继承实际值，不能强写为10或0。每个Pre/Cor材料trial都必须Elastic，保存κ=0本身不够；资格失败必须保留证据并停止，不能提高源强度或绕过loader。

三组共用φ=25°、cr=1kPa、黏聚衰减5。psi0为ψ0=0°/cp=5kPa/sf=0；psi2p5为+2.5°/cp=5kPa/sf=0.2；psim5为−5°/cp=7.5kPa/sf=0.2。新的统一DP v2替代旧算法选择，材料参数及保存κ仍为float，局部返回使用double；新XML不再带MaterialReturn选择项。本版κ历史处理和顶点修复可使结果与r2不同，完整软化响应需重新比较。源PRE为专用认证弹性状态，接收延续全部原生状态及真实时钟，在首循环仅撤去右mkbound2的260个样本，关闭预载阻尼0.02和Shepard40，保留Model1/Ck=2变k及自由渗流，继续到总时刻13s。τ按实际撤墙时刻计算；接收Part0不是伪t0或重复PRE。

其余物理配方保留：5000土+2060初始墙，dp=0.04m，Cubic核h/dp=1.2，E=20MPa、ν=0.33、n0=0.35、Kw=1GPa、k0=2e-4m/s，侧壁FreeSlip、底面NoSlip。保留负孔压，不引入论文额外负压松弛、TPI、HG、独立SPR、NoPen或shifting。公开u-pl塑性范围仍为该二维固定φ、DP_PS、Symplectic容器；没有任意塑性/HG/通用PART重启，也不声明三维动态塑性、曲墙或大转动已经验收。

已有CPU/GPU实际调用、Version2 PRE接续、分面mDBC与两ψ组短接收证据；本包仍是服务器待验证计算包。两ψ接续短窗κ始终0，不能当作非零塑性ψ衰减或完整塌陷精度。实际10s源能否全程满足弹性资格、三组完整塌陷与论文对比，仍须服务器结果审查。原必要稳定门失败同样停止，不自动换步长或方案。

源码来源分开记录：实际编译快照base={capture['base_commit']}加当时捕获的未提交修改；后来保存代码checkpoint={CODE_CHECKPOINT}。不声称程序在该后来提交或当前HEAD上重编。精确冻结快照及四build收据见SOURCE_VERSION_r3.txt/server_manifest_r3.json。r2程序、包和其结果保持原样，不应被本包覆盖或接续。

BAT只GenCase和求解，不做绘图、VTK或Python后处理。完成后复制完整源输出、三receiver输出及本包回来，包括初始BI4/Normals、全部PART、Run.out/Run.csv和日志；PNG/CSV及论文对比在本地完成。已有输出请保留，不能只拷最后一帧。
''')


def prepare(checkpoint):
    need(checkpoint==CODE_CHECKPOINT,'Use the reviewed later code checkpoint; do not substitute a newer documentation HEAD')
    builds,programs,capture_entry,capture,checks,inputs=checked_delivery();proof=schedule();old_manifest=CASE/'support/server_manifest_r2.json';old=load(old_manifest);old_hash={x['entry']:x['sha256']for x in old['files']};crt=old['runtime_CRT_source'];need(crt['mode']=='signed_MSVC_14_app_local_from_Visual_Studio_redist'and all(x['signature_status']=='Valid'and'Microsoft'in x['signer']for x in crt['files']),'Accepted frozen CRT provenance missing')
    payload={};expected={};retained=[];inputs.extend([old_manifest,Path(__file__),Path(__file__).with_name('upl_c08_shared_release_r2_prepare.py'),Path(__file__).with_name('upl_c08_release_package_r1.py')])
    for label,psi,cohesion,decay in [('PRELOAD',0.,5000.,0.)]+GROUPS:
        stem=SOURCE if label=='PRELOAD'else f'CaseLianSaturatedColumnCollapse_{label}_shared_r3';text,path=definition(label,psi,cohesion,decay);payload[stem+'_Def.xml']=text;inputs.append(path)
        for backend in('CPU','GPU'):payload[f'x{stem}_win64_{backend}.bat']=encoded(f'@echo off\nrem r3 server candidate: first finish this backend source, then run its receivers in order.\ncall "%~dp0support\\run_lian_collapse_shared_r3_win64.bat" {label} {backend} %*\nexit /b %ERRORLEVEL%\n')
    launcher=retained_launcher(proof).decode('utf-8').replace('_r2','_r3');need('runtime_r3'in launcher and'shared_preload_r3'in launcher and'@SOURCE@'not in launcher and'@PREPART@'not in launcher,'Retained launcher substitution failed');payload['support/run_lian_collapse_shared_r3_win64.bat']=encoded(launcher)
    for program in programs.values():payload['support/runtime_r3/'+program.name]=program
    for name in RUNTIME:
        src=CASE/'support/runtime_r2'/name;need(src.is_file(),'Accepted r2 runtime dependency missing');payload['support/runtime_r3/'+name]=src;expected['support/runtime_r3/'+name]=old_hash['support/runtime_r2/'+name];inputs.append(src)
    for relative in('LICENSE','support/lian2023_collapse_parameters.csv'):
        path=CASE/relative;need(path.is_file(),'Retained shared LICENSE/parameter CSV missing');payload[relative]=path;expected[relative]=old_hash[relative];retained.append(path);inputs.append(path)
    payload.update({'README_server_r3.md':readme(proof,capture),'support/preload_schedule_r3.json':encoded(json.dumps(proof,indent=2)+'\n'),'support/SOURCE_VERSION_r3.txt':source_version(capture_entry,capture),'support/THIRD_PARTY_NOTICES_r3.txt':encoded((CASE/'support/THIRD_PARTY_NOTICES_r2.txt').read_text(encoding='utf-8'))});inputs.append(CASE/'support/THIRD_PARTY_NOTICES_r2.txt')
    special=['support/server_manifest_r3.json','support/SHA256SUMS_r3.txt',f'support/{PACKAGE}.zip',f'support/{PACKAGE}.zip.sha256'];need(not(CASE/'support/runtime_r3').exists(),'Existing r3 runtime protected')
    for relative in list(payload)+special:need(CASE/relative in retained or not(CASE/relative).exists(),'Retained destination protected: '+relative)
    before=[stat(p)for p in dict.fromkeys(inputs)];(CASE/'support/runtime_r3').mkdir();files=[]
    for relative,src in payload.items():
        dst=CASE/relative
        if isinstance(src,bytes):
            with dst.open('xb')as f:f.write(src)
        elif dst!=src:
            with src.open('rb')as a,dst.open('xb')as b:shutil.copyfileobj(a,b)
            shutil.copystat(src,dst)
        digest=hashlib.sha256(dst.read_bytes()).hexdigest();need(relative not in expected or digest==expected[relative],'Accepted dependency payload changed: '+relative);s=dst.stat();files.append({'entry':relative,'bytes':s.st_size,'mtime_ns':s.st_mtime_ns,'sha256':digest})
    need(before==[stat(p)for p in dict.fromkeys(inputs)],'Consumed frozen files changed during preparation');manifest={'stage':'upl_c08_shared_release_r3','server_pending_full_physical_validation':True,'later_saved_code_checkpoint':CODE_CHECKPOINT,'compiled_from_capture':capture_entry,'capture_base_commit':capture['base_commit'],'capture_contains_then_uncommitted_source':True,'compiled_source_archive':capture['archive'],'compiled_at_later_checkpoint_or_current_HEAD_claimed':False,'builds':{k:stat(TESTS/'logs'/f'mdbc_partition_{k}_r1.build.json')for k in builds},'programs':{'CPU':builds['ReleaseCPU']['program'],'GPU':builds['Release']['program']},'bounded_implementation_checks':checks,'actual10s_source_already_certified':False,'full13s_collapse_physical_acceptance':False,'runtime_CRT_source':crt,'frozen_inputs':before,'files':files,'solver_GenCase_or_build_executed_by_packager':False,'raw_results_or_tests_included':False,'runtime_backend_lock_present':False,'source_dependency_and_output_refusal_retained':True,'ZIP_created_by_prepare':False}
    m=CASE/'support/server_manifest_r3.json'
    with m.open('x',encoding='utf-8',newline='\n')as f:json.dump(manifest,f,ensure_ascii=False,indent=2);f.write('\n')
    digest=hashlib.sha256(m.read_bytes()).hexdigest()
    with(CASE/'support/SHA256SUMS_r3.txt').open('x',encoding='ascii',newline='\n')as f:
        for row in files:f.write(row['sha256']+'  '+row['entry']+'\n')
        f.write(digest+'  support/server_manifest_r3.json\n')
    savepath=TESTS/'logs/upl_c08_shared_release_r3_prepare.check.json';need(not savepath.exists(),'Prior prepare receipt protected')
    with savepath.open('x',encoding='utf-8')as f:json.dump({'passed':True,'manifest':stat(m),'SHA256SUMS':stat(CASE/'support/SHA256SUMS_r3.txt'),'payload_files':len(files),'source_capture_preserved':capture_entry,'later_code_checkpoint':CODE_CHECKPOINT,'ZIP_created':False,'solver_GenCase_build_executed':False,'physical_acceptance':False},f,indent=2);f.write('\n')
    print(json.dumps({'prepared':True,'manifest':str(m),'ZIP_created':False,'physical_acceptance':False}))


def archive():
    cp=TESTS/'logs/upl_c08_shared_release_r3_prepare.check.json';receipt=load(cp);need(receipt['passed']and receipt['ZIP_created']is False,'Closed r3 payload preparation required');m=bound(receipt['manifest']);sums=bound(receipt['SHA256SUMS']);manifest=load(m);need(manifest['later_saved_code_checkpoint']==CODE_CHECKPOINT and manifest['server_pending_full_physical_validation']and manifest['full13s_collapse_physical_acceptance']is False,'r3 provenance/acceptance changed');entries=[x['entry']for x in manifest['files']]+['support/server_manifest_r3.json','support/SHA256SUMS_r3.txt'];need(len(entries)==len(set(entries)),'Duplicate archive member')
    for row in manifest['files']:
        actual=stat(CASE/row['entry']);need(actual['bytes']==row['bytes']and actual['mtime_ns']==row['mtime_ns'],'Prepared payload modified before archive: '+row['entry'])
    before=[stat(CASE/x)for x in entries];target=CASE/'support'/(PACKAGE+'.zip');side=target.with_suffix('.zip.sha256');need(not target.exists()and not side.exists(),'Existing archive protected')
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
        for relative in entries:z.write(CASE/relative,PACKAGE+'/'+relative)
    with zipfile.ZipFile(target)as z:need(z.namelist()==[PACKAGE+'/'+x for x in entries]and z.testzip()is None,'Archive whitelist/CRC verification failed')
    need(before==[stat(CASE/x)for x in entries],'Prepared files changed while archiving');digest=hashlib.sha256(target.read_bytes()).hexdigest()
    with side.open('x',encoding='ascii')as f:f.write(digest+'  '+target.name+'\n')
    print(json.dumps({'archived':True,'zip':str(target),'sha256':digest,'solver_GenCase_build_executed':False,'physical_acceptance':False}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);mode=parser.add_mutually_exclusive_group(required=True);mode.add_argument('--prepare',action='store_true');mode.add_argument('--archive',action='store_true');parser.add_argument('--code-checkpoint',default=CODE_CHECKPOINT);args=parser.parse_args();need(args.code_checkpoint==CODE_CHECKPOINT,'Do not substitute current documentation HEAD for the reviewed code checkpoint')
    if args.prepare:prepare(args.code_checkpoint)
    else:archive()