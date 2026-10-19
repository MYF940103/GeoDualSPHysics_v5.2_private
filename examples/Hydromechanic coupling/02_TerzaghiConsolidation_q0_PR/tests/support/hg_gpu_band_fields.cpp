// Offline only: reuse typed production BI4 decoding, retain double stress state.
#define main retained_export_unused_main
#include "pore_double_vel0/export_state.cpp"
#undef main

int main(int argc,char** argv){
  try{
    Require(argc==2,"Use hg_gpu_band_fields DATA_DIR");
    const fs::path dir=fs::absolute(argv[1]);
    Require(Discover(dir).size()==21,"Expected PART0..20 only");
    std::cout<<std::setprecision(17)<<"[";
    for(unsigned index=0;index<=20;index++){
      JPartDataBi4 file;file.LoadFilePart(dir.string(),index,0,1);
      const unsigned n=file.Get_Npok();
      Require(n==1040&&file.GetNpiece()==1&&file.Get_CaseNfixed()==40&&file.Get_CaseNfluid()==1000&&!file.Get_Nout(),"Native geometry/count mismatch");
      Require(!file.Get_NpDynamic()&&!file.Get_ReuseIds()&&!file.Get_CaseNmoving()&&!file.Get_CaseNfloat(),"Unsupported native lifecycle");
      Require(file.Get_Step()==(index?index-1:0)&&std::abs(file.Get_TimeStep()-index*1e-5)<1e-12,"Actual time/step mismatch");
      Require(file.GetArray("SigmaState_kk")->GetType()==JBinaryDataDef::DatDouble3&&file.GetArray("SigmaState_ij")->GetType()==JBinaryDataDef::DatDouble3,"Persistent stress is not double3");
      const char* pn=file.ArrayExists("Posd")?"Posd":"Pos";
      const auto ids=Integers(file,"Idp",n);const auto pos=Triple(file,pn,n);
      const auto p=Scalar(file,"PorePress",n),p0=Scalar(file,"PorePress0",n);
      const auto kk=Triple(file,"SigmaState_kk",n),ij=Triple(file,"SigmaState_ij",n);
      std::vector<unsigned> slots(n,~0u);
      for(unsigned k=0;k<n;k++){Require(ids[k]<n&&slots[unsigned(ids[k])]==~0u,"Missing/duplicate native IDs");slots[unsigned(ids[k])]=k;}
      if(index)std::cout<<',';
      std::cout<<"{\"part\":"<<index<<",\"time_s\":"<<file.Get_TimeStep()<<",\"position_type\":\""<<Type(file,pn)<<"\",\"rows\":[";
      for(unsigned id=0;id<n;id++){
        Require(slots[id]!=~0u,"Native ID missing");const unsigned k=slots[id];if(id)std::cout<<',';
        std::cout<<'['<<id<<','<<pos[k].x<<','<<pos[k].y<<','<<pos[k].z<<','<<p[k]<<','<<p0[k]
          <<','<<kk[k].x<<','<<kk[k].y<<','<<kk[k].z<<','<<ij[k].x<<','<<ij[k].y<<','<<ij[k].z<<']';
      }
      std::cout<<"]}";
    }
    std::cout<<"]\n";return 0;
  }catch(const std::exception& e){std::cerr<<"READ ERROR: "<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"Production BI4 reader exception\n";return 1;}
}
