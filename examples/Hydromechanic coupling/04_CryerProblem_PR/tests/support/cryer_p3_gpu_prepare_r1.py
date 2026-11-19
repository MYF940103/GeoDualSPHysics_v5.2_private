"""Construct a private Cryer candidate from the tested XYZ row and C02 P3 transaction."""
from pathlib import Path
import json
import re
import shutil

T = Path(__file__).resolve().parents[1]
C2 = T.parents[1] / '02_TerzaghiConsolidation_q0_PR' / 'tests'
BASE = T / 'outputs/upl_tpi_cryer_gpu_r2_source/source'
COLUMN = C2 / 'outputs/upl_tpi_p3_full_GPU_r1_source'
DST = T / 'outputs/cryer_p3_gpu_r2_source'
NS = 'upl_tpi_cryer_gpu_r1'
P3 = 'upl_tpi_gpu_r1'


def read(p):
    return p.read_bytes().decode('latin1').replace('\r\n','\n')


def write(p, data):
    p.write_bytes(data.replace('\n','\r\n').encode('latin1'))


def change(s, old, new):
    if s.count(old) != 1:
        raise ValueError('Nonunique anchor: '+old[:100])
    return s.replace(old,new)


def span(s,a,b):
    return s[s.index(a):s.index(b,s.index(a)+len(a))]


def body(s,a,b,text):
    return change(s,span(s,a,b),text)


def prepare():
    if DST.exists():
        raise FileExistsError(DST)
    shutil.copytree(BASE,DST)
    policy=read(C2/'support/upl_tpi_p3_dt_r1.h')
    policy=change(policy,'event==.0100002288818359375&&Bits(dt,event/1000.)','Bits(event,.0078125)&&Bits(dt,.0000019073486328125)')
    write(DST/'upl_tpi_m0_dt_r2.h',policy)
    old=read(BASE/'upl_tpi_cryer_gpu_r1.h')
    template=read(C2/'support/upl_tpi_p3_gpu_r1.h')
    # Use the frozen XYZ device interface intact; only new declarations are host calls.
    s=old[:old.index('static unsigned Scheme()')]
    s=change(s,'void WriteFinal(View v);','''unsigned EndpointPhase();
void ValidateProvisionalEndpoint(const void* owner,View v,bool drain,unsigned loadmode);
void NextEndpoint(const void* owner,View v,double time,unsigned long long step,double dt,const JSphHourglassGpu* hg);
void WriteFinal(View v);''')
    s=change(s,'#include <climits>','#include "upl_tpi_m0_dt_r2.h"\n#include <algorithm>\n#include <climits>')
    s=change(s,'unsigned long long step,double dt);','unsigned long long step,double dt,bool fullOutput);')
    host=template[template.index('static unsigned Scheme()'):]
    host=change(host,'  unsigned *hgSlots=nullptr,*hgError=nullptr; cuhg::StReduce *hgPartial=nullptr,*hgResult=nullptr;','  bool fullOutput=false; unsigned long long writtenPerRound=0; std::ofstream audit;')
    host=change(host,'  std::vector<double> stats,rateInfo; ','  ')
    host=body(host,'static void HostRoleFixtures()','void FreeOwner(',span(old,'static void HostRoleFixtures()','void FreeOwner('))
    host=body(host,'s.allocations.clear();','  for(auto& p:s.csv)', 's.allocations.clear();s.d=DeviceState{};s.collected=nullptr;for(auto& p:s.provisionalRows)p=nullptr;\n')
    host=body(host,'double time,unsigned long long step,double dt){\n  State& s=state;Need(Enabled()', '  HostRoleFixtures();','''double time,unsigned long long step,double dt,bool fullOutput){
  State& s=state;Need(Enabled()&&!s.owner&&owner&&time==0.&&step==0
    &&upl_tpi_m0_dt_r2::Enabled(true)&&upl_tpi_m0_dt_r2::AllowedDt(dt,.0078125)
    &&v.np==37181&&v.npb==8,"Cryer P3 requires a fresh B 2^-19 owner and complete XYZ body");
  s.fullOutput=fullOutput;
''')
    host=body(host,'  s.d.hgHistory=', '  s.collected=', '')
    host=re.sub(r'\b1040\b','37181',host)
    host=re.sub(r'\b1000\b','37173',host)
    host=change(host,'s.d.fixed=40','s.d.fixed=8')
    host=change(host,'  const std::string policy=', '''  const std::string auditPath=directory+"UplTpiP3GpuR1.body.csv";
  Need(!std::ifstream(auditPath).good(),"GPU P3 body audit exists");
  s.audit.open(auditPath);Need(bool(s.audit),"GPU P3 body audit open failed");
  s.audit<<std::setprecision(17)<<"part,time_s,body_checked,exported_per_round,max_abs_p2_minus_p1_Pa,max_abs_p3_minus_p2_Pa\\n";
  const std::string policy=''')
    host=change(host,'\\"native_count\\":37181,\\"soil_count\\":37173', '\\"native_count\\":37181,\\"soil_count\\":37173,\\"output_all_ids\\":"<<(s.fullOutput?"true":"false")<<",\\"long_output_center_count\\":18')
    host=body(host,'Need(hg&&hg->GetFirstId()', '  if(s.endpointRound==0)', 'Need(!hg,"Cryer P3 requires HG0");\n')
    host=body(host,'s.stats=Stats(*hg);','  PublishEndpoint(s.d,v.id,true);','\n')
    host=body(host,'void AddReadonlyHG(','void PrepareFinal(','')
    host=change(host,'!s.prepared&&hg&&','!s.prepared&&!hg&&')
    host=body(host,'  const auto a=Stats(*hg)', 's.prepared=true;', '  PrepareDevice(v,s.d);Check();s.coreChecks+=7ull*37173;')
    # Do not replace C counts via substring (21000 contains 1000).
    host=host.replace('21000*','(21ull*37173)*').replace('7000*','(7ull*37173)*')
    host=re.sub(r's\.hgChecks==(?:2000|6000)\*(?:\([^)]*\)|s\.commits)', 's.hgChecks==0',host)
    host=host.replace('n+40','n+8')
    center=json.loads((T/'logs/cryer_radial_layout_r1.check.json').read_text(encoding='utf-8-sig'))['native_identity']['center_ids']
    assert len(set(center))==18 and center==sorted(center)
    host=change(host,'  for(unsigned n=0;n<37173;n++){const auto& r=rows[n];','  static const unsigned center[18]={'+','.join(map(str,center))+'};\n  unsigned written=0; double delta2=0.,delta3=0.;\n  for(unsigned n=0;n<37173;n++){const auto& r=rows[n];')
    host=change(host,'    WriteObservation(*s.csv[0]', '''    delta2=std::fmax(delta2,std::fabs(double(p2)-p1));delta3=std::fmax(delta3,std::fabs(double(r.finalP)-p2));
    if(!s.fullOutput&&!std::binary_search(center,center+18,n+8))continue;
    written++;
    WriteObservation(*s.csv[0]''')
    host=change(host,'  for(auto* p:s.csv){p->flush();','''  Need(written==(s.fullOutput?37173u:18u),"Cryer P3 exported material count differs");
  s.audit<<part<<','<<time<<",37173,"<<written<<','<<delta2<<','<<delta3<<'\\n';s.audit.flush();Need(bool(s.audit),"Cryer P3 body audit write failed");
  s.writtenPerRound+=written;
  for(auto* p:s.csv){p->flush();''')
    host=change(host,'<<37173*s.saves','<<s.writtenPerRound')
    assert 'hg->' not in host and 'cuhg::' not in host and 's.hgSlots' not in host
    s+=host.replace(P3,NS)
    write(DST/'upl_tpi_cryer_gpu_r1.h',s)
    # Keep each original free-body force, load, and boundary path; introduce only the P3 transaction.
    gpu=read(BASE/'JSphGpu.cpp')
    dt=span(read(COLUMN/'JSphGpu.cpp'),'double JSphGpu::DtVariable(bool final){','//================').replace(P3,NS)
    gpu=body(gpu,'double JSphGpu::DtVariable(bool final){','//================',dt)
    write(DST/'JSphGpu.cpp',gpu)
    single=read(BASE/'JSphGpuSingle.cpp')
    single=change(single,'#include "upl_tpi_cryer_gpu_r1.h"','#include "upl_tpi_cryer_gpu_r1.h"\n#include "upl_tpi_m0_dt_r2.h"')
    single=change(single,'NstepsBreak>0 && NstepsBreak<=128','NstepsBreak>0 && NstepsBreak<=481685')
    single=single.replace('0.00000095367431640625','0.0000019073486328125').replace('XYZ startup128 owners','XYZ Cryer owners')
    single=change(single,'Nstep,SymplecticDtPre);\n    Log->Print(','''Nstep,SymplecticDtPre,NstepsBreak<=64);
    upl_tpi_m0_dt_r2::Init(UPL_TPI_CRYER_GPU_OWNER,DirOut,"GPU",std::getenv("UPL_TPI_GPU_R1"),TimeStep,Nstep,SymplecticDtPre,HydroMechDrainageStartTime);
    Log->Print(''')
    single=single.replace('XYZ HG0 startup128 only; alpha.5/0 beta0 single defect correction, not literal LF/implicit/second-order/physical acceptance.', 'XYZ HG0 P3, three endpoint pressure corrections and five-phase Eq40/Rh1 step bounds.')
    column=read(COLUMN/'JSphGpuSingle.cpp')
    three=span(column,'        for(unsigned round=0;round<3;', '      }catch(...){upl_tpi_gpu_r1::AbortEndpoint()').replace(P3,NS).replace('UPL_TPI_GPU_','UPL_TPI_CRYER_GPU_')
    single=body(single,'        upl_tpi_cryer_gpu_r1::StartEndpoint(', '      }catch(...){upl_tpi_cryer_gpu_r1::AbortEndpoint()',three)
    for operation in ['Finish','Saved']:
        line=next(l for l in column.splitlines() if 'upl_tpi_m0_dt_r2::'+operation+'(' in l).replace(P3,NS)
        anchor=next(l for l in single.splitlines() if NS+'::'+operation+'(' in l)
        single=change(single,anchor,anchor+'\n'+line)
    write(DST/'JSphGpuSingle.cpp',single)
    print(DST)


if __name__=='__main__':
    prepare()

