"""Reload only pressure history in a live private P3 solver, then carry on from the same mechanics."""
import argparse
import shutil

import cryer_live_history as writer
from cryer_row_gpu_r1 import need
from cryer_xml_prepare_r1 import edit, replace

NAME="cryer_hist_restore_{}_r1"
CPU="""
void cryer_history::Install(const std::vector<float>& previous,const std::vector<float>& current,unsigned fixed){
  upl_tpi_cpu_r1::State& s=upl_tpi_cpu_r1::state;
  Require(s.ready && !s.pending && !s.endpoint && s.commits==2 && s.fixedCount==fixed
    && s.previous.size()==current.size() && s.soilCount==previous.size(),"Invalid CPU restore point");
  const size_t length=previous.size()*sizeof(float);
  Require(!std::memcmp(current.data()+fixed,s.finalP.data()+fixed,length)
    && !std::memcmp(previous.data(),s.previous.data()+fixed,length),"CPU checkpoint differs from commit");
  // The predictor indexes this buffer by native ID after the next cell sort.
  std::copy(previous.begin(),previous.end(),s.previous.begin()+fixed);
}
"""
GPU="""
void cryer_history::Install(const std::vector<float>& previous,const std::vector<float>& current,unsigned fixed){
  using namespace upl_tpi_cryer_gpu_r1;
  State& s=state;
  Require(s.ready && !s.pending && !s.endpoint && s.commits==2 && s.d.fixed==fixed
    && s.d.total==current.size() && s.d.total-fixed==previous.size(),"Invalid GPU restore point");
  std::vector<Observation> rows(previous.size());
  Cuda(cudaMemcpy(rows.data(),s.d.rows+fixed,rows.size()*sizeof(Observation),cudaMemcpyDeviceToHost));
  for(unsigned i=0;i<rows.size();i++){
    Require(Bits(rows[i].finalP,current[fixed+i]) && Bits(rows[i].pn,previous[i]),
      "GPU checkpoint differs from commit");
  }
  // Install into the actual persistent device buffer consumed by BeginDevice.
  Cuda(cudaMemcpy(s.d.previous+fixed,previous.data(),previous.size()*sizeof(float),cudaMemcpyHostToDevice));
}
"""


def build(backend):
    label=NAME.format(backend)
    source=writer.old.OUT/(label+"_source")
    shutil.copytree(writer.old.OUT/(writer.NAME.format(backend)+"_source"),source)
    unit=source/"source" if backend=="cpu" else source
    shutil.copyfile(writer.SUPPORT/"CryerTpiLoadHistory.h",unit/"CryerTpiLoadHistory.h")
    def hook(text):
        text=replace(text,writer.INCLUDE,'#include "CryerTpiLoadHistory.h"')
        original='      if(hasHistory)DataBi4->GetPart()->RemoveItem("TpiPressureHistory");'
        extra="""
      if(hasHistory && Part==2){
        cryer_history::Reload(*DataBi4,DirDataOut,Part,NoRtimes);
        Log->Print("Restored committed pressure history by native ID at PART 2.");
      }"""
        return replace(text,original,original+extra)
    edit(unit/"JSph.cpp",hook)
    leaf="JSphCpuSingle.cpp" if backend=="cpu" else "JSphGpu.cpp"
    edit(unit/leaf,lambda text:text+'\n#include "CryerTpiLoadHistory.h"\n'+(CPU if backend=="cpu" else GPU))
    writer.old.build(backend,label,source)


def run(backend):
    writer.NAME=NAME
    writer.run(backend,"dense4")
    output=writer.old.OUT/(NAME.format(backend)+"_dense4")
    log=(output/"Run.out").read_text(errors="replace")
    need(log.count("Restored committed pressure history by native ID at PART 2.")==1,"Missing load hook")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["build","run"])
    parser.add_argument("backend",choices=["cpu","gpu"])
    args=parser.parse_args()
    if args.action=="build":build(args.backend)
    else:run(args.backend)
