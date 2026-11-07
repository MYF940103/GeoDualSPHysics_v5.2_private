// Offline basic-soil BI4 exporter: actual typed double stress where present, no solver.
#include "JPartDataBi4.h"
#include "JBinaryData.h"
#include "JAppInfo.h"
#include "JException.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cfloat>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
JAppInfo AppInfo("BasicMaterialNative","r2","07-11-2026");
namespace fs=std::filesystem;using TpData=JBinaryDataDef::TpData;
static constexpr TpData DatUint=JBinaryDataDef::DatUint,DatFloat=JBinaryDataDef::DatFloat,DatDouble=JBinaryDataDef::DatDouble,DatFloat3=JBinaryDataDef::DatFloat3,DatDouble3=JBinaryDataDef::DatDouble3;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
static bool Finite(unsigned){return true;}static bool Finite(float x){return std::isfinite(x);}static bool Finite(double x){return std::isfinite(x);}
template<class T>static bool Finite(T x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}
template<class T>static std::vector<T> Get(JPartDataBi4& f,const char* name,unsigned n,TpData type){const auto* a=f.GetArray(name,type);Need((a->DataInPointer()?a->GetCount():a->GetFileDataCount())==n,"Typed array native count differs");std::vector<T> v(n);Need(a->GetDataCopy(n,v.data())==n,"Incomplete typed array");for(auto x:v)Need(Finite(x),"Nonfinite native array");return v;}
static double Norm(tfloat3 x){return double(x.x)*x.x+double(x.y)*x.y+double(x.z)*x.z;}
int main(int argc,char** argv){unsigned active=~0u;try{
  Need(argc==6,"Use DATA SOIL FIXED SAMPLES FRESHOUT");const fs::path data=argv[1],out=argv[5];const unsigned soil=std::stoul(argv[2]),fixed=std::stoul(argv[3]),samples=std::stoul(argv[4]),total=soil+fixed;
  Need(soil>0&&samples>1&&!fs::exists(out)&&fs::create_directory(out),"Fresh native export required");unsigned found=0;for(const auto& p:fs::directory_iterator(data))if(p.is_regular_file()&&p.path().extension()==".bi4"&&p.path().filename().string().rfind("Part_",0)==0)found++;Need(found==samples,"Extra/missing native PART");
  std::ofstream bin(out/"states.bin",std::ios::binary),clock(out/"clocks.csv"),hist(out/"history.csv"),ids(out/"initial.csv");const unsigned h[]={soil,fixed,samples,14};bin.write(reinterpret_cast<const char*>(h),16);
  for(auto* s:{&clock,&hist,&ids})*s<<std::setprecision(17);
  clock<<"part,time_s,saved_step,completed_steps,dt_s,signed_dterror_s,stress_float64,position_float64\n";
  ids<<"id,is_fixed,x0,y0,z0\n";hist<<"part,time_s,velocity_RMS_m_s,max_velocity_m_s,sigma_Frobenius_RMS_Pa,sigma_zz_mean_Pa,kappa_max,kappa_nonzero,minimum_kappa_increment,mean_settlement_m,top_material_settlement_m,bottom_material_settlement_m,x_min_m,x_max_m,z_min_m,z_max_m\n";
  std::vector<tdouble3> initial(total);std::vector<float> previous(total,0.f);double prevtime=-1,zlo=DBL_MAX,zhi=-DBL_MAX;unsigned previousstep=0,doubleframes=0,posdoubleframes=0;double maxk=0;unsigned finalnz=0;
  for(unsigned part=0;part<samples;part++){active=part;JPartDataBi4 f;f.LoadFilePart(data.string(),part);Need(f.GetNpiece()==1&&f.Get_Npok()==total&&!f.Get_Nout()&&f.Get_CaseNp()==total&&f.Get_CaseNfixed()==fixed&&f.Get_CaseNfluid()==soil&&!f.Get_CaseNmoving()&&!f.Get_CaseNfloat(),"Native original IDs/counts/exclusion mismatch");
    const double time=f.Get_TimeStep();const unsigned step=f.Get_Step();Need(std::isfinite(time)&&time>prevtime&&(!part?time==0:step>previousstep),"Native clocks/steps not increasing");prevtime=time;previousstep=step;
    auto id=Get<unsigned>(f,"Idp",total,DatUint);std::vector<unsigned> slot(total,~0u);for(unsigned q=0;q<total;q++){Need(id[q]<total&&slot[id[q]]==~0u,"Duplicate/foreign ID");slot[id[q]]=q;}
    const bool pd=f.ArrayExists("Posd"),sd=f.ArrayExists("SigmaState_kk")&&f.ArrayExists("SigmaState_ij");posdoubleframes+=pd;doubleframes+=sd;
    std::vector<tdouble3> x(total),sk(total),si(total);if(pd)x=Get<tdouble3>(f,"Posd",total,DatDouble3);else{const auto a=Get<tfloat3>(f,"Pos",total,DatFloat3);for(unsigned q=0;q<total;q++)x[q]=TDouble3(a[q].x,a[q].y,a[q].z);}
    if(sd){sk=Get<tdouble3>(f,"SigmaState_kk",total,DatDouble3);si=Get<tdouble3>(f,"SigmaState_ij",total,DatDouble3);}else{const auto a=Get<tfloat3>(f,"Sigma_kk",total,DatFloat3),b=Get<tfloat3>(f,"Sigma_ij",total,DatFloat3);for(unsigned q=0;q<total;q++){sk[q]=TDouble3(a[q].x,a[q].y,a[q].z);si[q]=TDouble3(b[q].x,b[q].y,b[q].z);}}
    const auto v=Get<tfloat3>(f,"Vel",total,DatFloat3);const auto rho=Get<float>(f,"Rhop",total,DatFloat),k=Get<float>(f,"Kplastic",total,DatFloat);
    if(!part)for(unsigned n=0;n<total;n++){const unsigned q=slot[n];initial[n]=x[q];ids<<n<<','<<(n<fixed)<<','<<x[q].x<<','<<x[q].y<<','<<x[q].z<<'\n';if(n>=fixed){zlo=(std::min)(zlo,x[q].z);zhi=(std::max)(zhi,x[q].z);}}
    const auto* info=f.GetPart();const double dt=info->ExistsValue("SymplecticDtPre",DatDouble)?info->GetvDouble("SymplecticDtPre"):0.,err=info->ExistsValue("dterror",DatDouble)?info->GetvDouble("dterror"):0.;Need(std::isfinite(dt)&&std::isfinite(err),"Nonfinite native step diagnostic");clock<<part<<','<<time<<','<<step<<','<<(part?step+1:0)<<','<<dt<<','<<err<<','<<sd<<','<<pd<<'\n';bin.write(reinterpret_cast<const char*>(&time),8);
    double vv=0,vm=0,ss=0,szz=0,km=0,mink=0,settle=0,top=0,bottom=0,xmin=DBL_MAX,xmax=-DBL_MAX,zmin=DBL_MAX,zmax=-DBL_MAX;unsigned nz=0,nt=0,nb=0;
    for(unsigned n=0;n<total;n++){const unsigned q=slot[n];Need(rho[q]>0&&k[q]>=0,"Nonpositive density/negative history");if(n<fixed){Need(x[q].x==initial[n].x&&x[q].y==initial[n].y&&x[q].z==initial[n].z&&Norm(v[q])==0,"Fixed native state moved");continue;}const auto a=x[q],s=sk[q],t=si[q];
      const double row[]={a.x,a.y,a.z,double(v[q].x),double(v[q].y),double(v[q].z),rho[q],k[q],s.x,s.y,s.z,t.x,t.y,t.z};bin.write(reinterpret_cast<const char*>(row),sizeof(row));vv+=Norm(v[q]);vm=(std::max)(vm,Norm(v[q]));ss+=s.x*s.x+s.y*s.y+s.z*s.z+2*(t.x*t.x+t.y*t.y+t.z*t.z);szz+=s.z;km=(std::max)(km,double(k[q]));nz+=k[q]>0;mink=(std::min)(mink,double(k[q])-previous[n]);previous[n]=k[q];const double u=initial[n].z-a.z;settle+=u;if(std::abs(initial[n].z-zhi)<f.Get_Dp()*.25){top+=u;nt++;}if(std::abs(initial[n].z-zlo)<f.Get_Dp()*.25){bottom+=u;nb++;}xmin=(std::min)(xmin,a.x);xmax=(std::max)(xmax,a.x);zmin=(std::min)(zmin,a.z);zmax=(std::max)(zmax,a.z);
    }Need(nt&&nb,"Empty fixed material end layers");hist<<part<<','<<time<<','<<std::sqrt(vv/soil)<<','<<std::sqrt(vm)<<','<<std::sqrt(ss/soil)<<','<<szz/soil<<','<<km<<','<<nz<<','<<mink<<','<<settle/soil<<','<<top/nt<<','<<bottom/nb<<','<<xmin<<','<<xmax<<','<<zmin<<','<<zmax<<'\n';maxk=(std::max)(maxk,km);finalnz=nz;
  }
  for(auto* s:{&bin,&clock,&hist,&ids}){s->flush();Need(bool(*s),"Native export write failed");}std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"basic_native_r2\",\"passed\":true,\"samples\":"<<samples<<",\"soil\":"<<soil<<",\"fixed\":"<<fixed<<",\"native_end_s\":"<<prevtime<<",\"float64_stress_frames\":"<<doubleframes<<",\"float64_position_frames\":"<<posdoubleframes<<",\"max_kappa\":"<<maxk<<",\"final_nonzero_kappa\":"<<finalnz<<",\"no_exclusions\":true,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const JException& e){std::cerr<<"part="<<active<<' '<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<"part="<<active<<' '<<e.what()<<'\n';return 1;}}
