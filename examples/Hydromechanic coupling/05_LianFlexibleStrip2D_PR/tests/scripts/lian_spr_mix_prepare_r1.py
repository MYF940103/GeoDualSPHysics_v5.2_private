"""Prepare bounded mixed-slip diagnostics using retained project fixtures/style."""
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
from lian_release_r1 import CASE, TESTS, REPO, bound, write_json, utc

TAG='lian_spr_mix_r1'
OLD=REPO/'examples/Hydromechanic coupling/02_TerzaghiConsolidation_q0_PR/tests/support'
sys.path.insert(0,str(OLD))
from spr_planes_run import xml as field_xml


def fresh(path,text):
    assert not path.exists(),str(path)
    path.write_text(text,encoding='utf8')


def main():
    receipt=TESTS/'logs'/(TAG+'.prepare.json'); assert not receipt.exists()
    sources=[bound(__file__)]
    # Reuse existing all-wall production MLS/consumer fixtures; only oracle slip
    # selection changes from a global value to the actual per-particle mode.
    p=OLD/'spr_planes_test.cpp'; cpu=p.read_text();sources.append(bound(p))
    begin=cpu.index('  tfloat3 Oracle(');end=cpu.index('  void Interaction()',begin)
    block=cpu[begin:end].replace('const{\n','const{\n    const TpSlipMode mode=GetMdbcSlipModeByCode(Codec[p]);\n',1)
    block=block.replace('SlipMode>=','mode>=').replace('SlipMode==','mode==')
    cpu=cpu[:begin]+block+cpu[end:]
    cpu=cpu.replace('(SlipMode==SLIP_Vel0||BoundModec[p]!=BMODE_MDBC2OFF)',
        '(GetMdbcSlipModeByCode(Codec[p])==SLIP_Vel0||BoundModec[p]!=BMODE_MDBC2OFF)')
    fresh(TESTS/'scripts/lian_spr_mix_cpu_test.cpp',cpu)
    p=OLD/'spr_gpu_planes_test.cpp'; gpu=p.read_text();sources.append(bound(p))
    gpu=gpu.replace('  std::vector<byte> Modes;','  std::vector<byte> Modes,LocalSlip;')
    gpu=gpu.replace('(SlipMode==SLIP_Vel0||Modes[p]!=BMODE_MDBC2OFF)',
        '(LocalSlip[p]==SLIP_Vel0||Modes[p]!=BMODE_MDBC2OFF)')
    gpu=gpu.replace('    const auto b=Normals[p];','    const unsigned mode=LocalSlip[p];\n    const auto b=Normals[p];',1)
    gpu=gpu.replace('(SlipMode==SLIP_NoSlip?v*(-1.):(SlipMode==SLIP_FreeSlip?',
        '(mode==SLIP_NoSlip?v*(-1.):(mode==SLIP_FreeSlip?')
    gpu=gpu.replace('    Id=Down(Idpg,Np);Codes=Down(Codeg,Np);Normals=Down(BoundNormalg,Np);',
        '    Id=Down(Idpg,Np);Codes=Down(Codeg,Np);Normals=Down(BoundNormalg,Np);\n'
        '    LocalSlip=(BoundSlipModeg?Down(BoundSlipModeg,Np):std::vector<byte>(Np,byte(SlipMode)));')
    fresh(TESTS/'scripts/lian_spr_mix_gpu_test.cpp',gpu)
    for source,target in [('spr_planes_build.ps1','lian_spr_mix_cpu_build.ps1'),('gpu_fixture_build.ps1','lian_spr_mix_gpu_build.ps1')]:
        p=OLD/source; text=p.read_text(); sources.append(bound(p))
        if source.startswith('spr_planes'):text=text.replace('spr_planes','lian_spr_mix_cpu')
        fresh(TESTS/'scripts'/target,text)
    manufactured=[]
    for geometry in ['corner2','edge3']:
        for swapped in [False,True]:
            name=f'{TAG}_{geometry}_'+('swap' if swapped else 'mixed')
            root=ET.fromstring(field_xml(geometry,3))
            slip=ET.SubElement(root.find('execution/special'),'mdbcslip')
            ET.SubElement(slip,'bound',mkbound='0',slipmode='3' if swapped else '2')
            ET.SubElement(slip,'bound',mkbound='1',slipmode='2' if swapped else '3')
            ET.indent(root,space='  ')
            config=TESTS/'configs'/(name+'_Def.xml')
            fresh(config,'<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(root,encoding='unicode')+'\n')
            manufactured.append(dict(name=name,definition=bound(config)))
    base=(TESTS/'configs/lian_opt3_r1_grad_3s_Def.xml').read_text()
    # Same three boxes and material points. Split only the right-wall marker.
    needle='''                    <drawbox>
                        <boxfill>solid</boxfill>
                        <point x="#sizefx+Dp"'''
    assert base.count(needle)==1
    base=base.replace(needle,'                    <setmkbound mk="2" />\n'+needle)
    base=base.replace('<bound mkbound="0" slipmode="3" comment="Lateral walls: free-slip" />',
        '<bound mkbound="0" slipmode="3" comment="Left wall: free-slip" />\n'
        '                <bound mkbound="2" slipmode="3" comment="Right wall: free-slip" />')
    planes='''            <initialize>
                <boundnormal_plane mkbound="0">
                    <point x="0" y="0" z="0" />
                    <normal x="1" y="0" z="0" />
                    <maxdisth v="0" comment="All native wall layers; explicit inward plane normal" />
                    <clear v="true" />
                </boundnormal_plane>
                <boundnormal_plane mkbound="1">
                    <point x="0" y="0" z="0" />
                    <normal x="0" y="0" z="1" />
                    <maxdisth v="0" comment="All native wall layers; explicit inward plane normal" />
                    <clear v="true" />
                </boundnormal_plane>
                <boundnormal_plane mkbound="2">
                    <point x="20" y="0" z="0" />
                    <normal x="-1" y="0" z="0" />
                    <maxdisth v="0" comment="All native wall layers; explicit inward plane normal" />
                    <clear v="true" />
                </boundnormal_plane>
            </initialize>
'''
    base=base.replace('        <special>\n','        <special>\n'+planes,1)
    old_bat=(TESTS/'configs/xlian_opt3_r1_grad_smoke_win64.bat').read_text()
    jobs=[]
    for option,stage,duration,cadence in [('off','debug',.002,.001),('off','smoke',.15,.005),
        ('on','debug',.002,.001),('on','smoke',.15,.005),('off','3s',3.,.05),('on','3s',3.,.05)]:
        name=f'{TAG}_{option}_{stage}'; text=base
        for key,value in [('SoilBoundaryDerivativeSPR','1' if option=='on' else '0'),('TimeMax',str(duration)),('TimeOut',str(cadence))]:
            text,n=re.subn(r'(<parameter key="'+key+r'" value=")[^"]*(")',lambda m:m[1]+value+m[2],text);assert n==1
        config=TESTS/'configs'/(name+'_Def.xml'); fresh(config,text)
        bat=old_bat.replace('lian_opt3_r1_grad_smoke',name)
        if stage=='debug':
            bat=bat.replace('DualSPHysics5.2_GEO_win64.exe','DualSPHysics5.2CPU_win64_debug.exe')
            bat=bat.replace('-gpu -stable','-cpu -ompthreads:8 -stable')
        batpath=TESTS/'configs'/('x'+name+'_win64.bat');fresh(batpath,bat)
        jobs.append(dict(name=name,option=option,stage=stage,duration_s=duration,cadence_s=cadence,
            definition=bound(config),bat=bound(batpath)))
    write_json(receipt,dict(prepared=True,not_run=True,utc=utc(),sources=sources,manufactured=manufactured,jobs=jobs,
        baseline='lian_opt3_r1_grad_3s; same eta.04 and grad1. Analytic normal changes are isolated by the SPR-OFF control.',
        limits='Candidate mixed NoSlip/FreeSlip only; no Vel0 mixture, HG, modified material/load or automatic full run.'))
    print('Prepared',len(manufactured),'manufactured sets and',len(jobs),'Lian jobs; no solver launched')


if __name__=='__main__':main()
