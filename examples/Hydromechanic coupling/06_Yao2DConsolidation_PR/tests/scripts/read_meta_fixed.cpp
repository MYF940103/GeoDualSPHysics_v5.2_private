// Read-only saved PART metadata. Does not create or modify simulation state.
#include "JPartDataBi4.h"
#include <iomanip>
#include <iostream>
#include <stdexcept>

int main(int argc,char** argv){
  try{
    if(argc!=3)throw std::runtime_error("Usage: ReadPartMetadata DATA_DIR FRAME_COUNT");
    const unsigned count=unsigned(std::stoul(argv[2]));
    std::cout<<std::setprecision(17)<<"part,time_s,saved_step,native_count,nout,has_dterror,dterror_s,dt_min_s,dt_max_s,mass_fluid,dp_m,h_m\n";
    for(unsigned i=0;i<count;i++){
      JPartDataBi4 p;p.LoadFilePart(argv[1],i,0,1);const JBinaryData* part=p.GetPart();
      std::cout<<i<<','<<p.Get_TimeStep()<<','<<p.Get_Step()<<','<<p.Get_Npok()<<','<<p.Get_Nout()<<','
        <<part->ExistsValue("dterror")<<','<<part->GetvDouble("dterror",true,0)<<','
        <<part->GetvDouble("dtmin",true,0)<<','<<part->GetvDouble("dtmax",true,0)<<','
        <<p.Get_MassFluid()<<','<<p.Get_Dp()<<','<<p.Get_H()<<'\n';
    }
    return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"PART metadata read failed\n";return 2;}
}
