// Read-only sequential BI4 reduction. No solver, restart or physical state editing.
#include "JPartDataBi4.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
namespace fs=std::filesystem;
static void Check(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
template<class T>static std::vector<T> Read(JPartDataBi4& p,const char* name,unsigned n,JBinaryDataDef::TpData type){const auto* a=p.GetArray(name,type);Check((a->DataInPointer()?a->GetCount():a->GetFileDataCount())==n,"Wrong native array length");std::vector<T> v(n);a->GetDataCopy(n,v.data());return v;}
static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}static double Norm(tdouble3 a){return std::sqrt(Dot(a,a));}
int main(int argc,char** argv){try{
  Check(argc==5,"Usage: cryer_nu_native DATA_DIR FRAME_COUNT NEW_SUMMARY_CSV NEW_CENTER_CSV");
  const unsigned frames=unsigned(std::stoul(argv[2]));Check(frames==1065,"Exactly1065 expected native frames");Check(!fs::exists(argv[3])&&!fs::exists(argv[4]),"Retained output protected");
  std::ofstream out(argv[3]),center(argv[4]);out<<std::setprecision(17);center<<std::setprecision(17);Check(bool(out)&&bool(center),"Cannot create fresh CSV");
  out<<"part,time_s,saved_step,symplectic_dt_s,dterror_s,native_soil_count,center_count,center_pressure_pa,center_pressure_std_pa,pressure_mean_pa,pressure_min_pa,pressure_max_pa,shell_inward_mm,material_inward_mean_mm,total_mean_compression_pa,effective_mean_compression_pa,rho_mean_kg_m3,speed_max_m_s,radius_max_m,true_surface_count,true_surface_p_absmax_pa,actual_radial_force_N,net_force_norm_N,load_virial_N_m,volume0_m3,current_volume_m3,mass_kg,dp_m,h_m\n";
  center<<"part,time_s,saved_step,id,x0,y0,z0,r0_m,x,y,z,pressure_pa,rho_kg_m3,inward_mm,total_mean_compression_pa\n";
  std::vector<tdouble3> x0;std::vector<double> r0,weight;std::vector<unsigned> selected;double shellWeight=0,volume0=0,last=-1;
  for(unsigned part=0;part<frames;part++){
    JPartDataBi4 p;p.LoadFilePart(argv[1],part,0,1);const unsigned n=p.Get_Npok(),nb=unsigned(p.Get_CaseNfixed());
    Check(n==37181&&nb==8&&p.Get_CaseNfluid()==37173&&n==p.Get_CaseNp()&&p.GetNpiece()==1&&!p.Get_Nout()&&!p.Get_NpDynamic()&&!p.Get_ReuseIds(),"Native set/count changed");
    Check(p.ArrayExists("Posd")&&p.ArrayExists("SigmaState_kk")&&p.ArrayExists("SigmaState_ij")&&p.ArrayExists("HydroMechLoadAce"),"Required double state/load telemetry missing");
    const auto id=Read<unsigned>(p,"Idp",n,JBinaryDataDef::DatUint),ft=Read<unsigned>(p,"FSType",n,JBinaryDataDef::DatUint);std::vector<unsigned> slot(n,~0u);for(unsigned i=0;i<n;i++){Check(id[i]<n&&slot[id[i]]==~0u,"Duplicate or invalid ID");slot[id[i]]=i;}
    const auto x=Read<tdouble3>(p,"Posd",n,JBinaryDataDef::DatDouble3),s=Read<tdouble3>(p,"SigmaState_kk",n,JBinaryDataDef::DatDouble3),t=Read<tdouble3>(p,"SigmaState_ij",n,JBinaryDataDef::DatDouble3);
    const auto v=Read<tfloat3>(p,"Vel",n,JBinaryDataDef::DatFloat3),load=Read<tfloat3>(p,"HydroMechLoadAce",n,JBinaryDataDef::DatFloat3),normal=Read<tfloat3>(p,"FSNormal",n,JBinaryDataDef::DatFloat3);
    const auto pw=Read<float>(p,"PorePress",n,JBinaryDataDef::DatFloat),rho=Read<float>(p,"Rhop",n,JBinaryDataDef::DatFloat),plastic=Read<float>(p,"Kplastic",n,JBinaryDataDef::DatFloat);
    const auto* meta=p.GetPart();const double time=p.Get_TimeStep(),dt=meta->GetvDouble("SymplecticDtPre",true,0),error=meta->GetvDouble("dterror",true,0),mass=p.Get_MassFluid();
    Check(std::isfinite(time)&&time>last&&std::isfinite(error)&&(!part||meta->ExistsValue("dterror"))&&error<=1e-14,"Invalid time/natural-step telemetry");last=time;
    Check(p.Get_Dp()==.0025&&mass>0&&p.Get_H()>0,"Unexpected geometry metadata");
    if(!part){x0.resize(n);r0.resize(n);weight.resize(n);for(unsigned a=nb;a<n;a++){const unsigned i=slot[a];Check(i!=~0u&&rho[i]>0,"Missing initial soil ID");x0[a]=x[i];r0[a]=Norm(x[i]);weight[a]=mass/rho[i];volume0+=weight[a];if(r0[a]<=.0025+1e-12)selected.push_back(a);if(r0[a]>=.05-2*p.Get_H())shellWeight+=weight[a];}Check(selected.size()==18&&shellWeight>0,"Wrong fixed center18/shell definition");for(auto a:selected)Check(std::abs(r0[a]-.0025)<1e-15,"Center18 not at original r/a=.05");}
    double psum=0,pmin=1e300,pmax=-1e300,inward=0,shell=0,total=0,effective=0,rhosum=0,speed=0,rmax=0,sp=0,radial=0,virial=0,currentVolume=0;unsigned surfaces=0;tdouble3 net=TDouble3(0);
    for(unsigned a=nb;a<n;a++){
      const unsigned i=slot[a];Check(i!=~0u,"Missing soil ID");const double values[]={x[i].x,x[i].y,x[i].z,s[i].x,s[i].y,s[i].z,t[i].x,t[i].y,t[i].z,v[i].x,v[i].y,v[i].z,load[i].x,load[i].y,load[i].z,normal[i].x,normal[i].y,normal[i].z,pw[i],rho[i],plastic[i]};for(double z:values)Check(std::isfinite(z),"Nonfinite native state");Check(rho[i]>0&&plastic[i]==0,"Nonelastic or invalid density");
      const double r=Norm(x[i]),u=(r0[a]-r)*1000,w=weight[a],mean=(s[i].x+s[i].y+s[i].z)/3.;Check(r>0&&r<=.0525,"Native radius safety failed");
      psum+=w*pw[i];pmin=(std::min)(pmin,double(pw[i]));pmax=(std::max)(pmax,double(pw[i]));inward+=w*u;if(r0[a]>=.05-2*p.Get_H())shell+=w*u;effective-=w*mean;total+=w*(pw[i]-mean);rhosum+=w*rho[i];speed=(std::max)(speed,std::sqrt(double(v[i].x)*v[i].x+double(v[i].y)*v[i].y+double(v[i].z)*v[i].z));rmax=(std::max)(rmax,r);currentVolume+=mass/rho[i];
      const auto force=TDouble3(mass*load[i].x,mass*load[i].y,mass*load[i].z);net=net+force;radial-=Dot(force,x[i])/r;virial-=Dot(force,x[i]);if(ft[i]==2||ft[i]==3){surfaces++;sp=(std::max)(sp,std::abs(double(pw[i])));}
    }
    Check(surfaces>0&&(time<=1./128.||sp==0)&&(!part||radial>0),"True drained surface/load guard failed");double cp=0,variance=0;for(auto a:selected)cp+=pw[slot[a]]/double(selected.size());for(auto a:selected)variance+=(pw[slot[a]]-cp)*(pw[slot[a]]-cp)/double(selected.size());
    out<<part<<','<<time<<','<<p.Get_Step()<<','<<dt<<','<<error<<','<<n-nb<<','<<selected.size()<<','<<cp<<','<<std::sqrt(variance)<<','<<psum/volume0<<','<<pmin<<','<<pmax<<','<<shell/shellWeight<<','<<inward/volume0<<','<<total/volume0<<','<<effective/volume0<<','<<rhosum/volume0<<','<<speed<<','<<rmax<<','<<surfaces<<','<<sp<<','<<radial<<','<<Norm(net)<<','<<virial<<','<<volume0<<','<<currentVolume<<','<<mass<<','<<p.Get_Dp()<<','<<p.Get_H()<<'\n';
    for(auto a:selected){const unsigned i=slot[a];center<<part<<','<<time<<','<<p.Get_Step()<<','<<a<<','<<x0[a].x<<','<<x0[a].y<<','<<x0[a].z<<','<<r0[a]<<','<<x[i].x<<','<<x[i].y<<','<<x[i].z<<','<<pw[i]<<','<<rho[i]<<','<<(r0[a]-Norm(x[i]))*1000<<','<<pw[i]-(s[i].x+s[i].y+s[i].z)/3.<<'\n';}
    if(part%200==0)std::cerr<<"Read "<<part<<'/'<<frames<<" t="<<time<<'\n';
  }
  out.flush();center.flush();Check(bool(out)&&bool(center),"CSV write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Read-only native reduction failed\n";return 2;}}
