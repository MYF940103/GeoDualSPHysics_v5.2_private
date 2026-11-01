// Offline regular-lattice linear symbol, using the actual project kernel header.
// No solver, source patch, threshold change, or new physical candidate.
#include "FunSphKernel.h"
#include <array>
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>
namespace fs=std::filesystem;
static void Check(bool yes,const char* why){if(!yes)throw std::runtime_error(why);}
struct Symbol{double mxx=0,mxz=0,mzz=0,cxx=0,cxz=0,raw=0,corr=0,rawfloat=0;unsigned neighbours=0;};
int main(int argc,char** argv){
  try{
    Check(argc==15,"Use STATES MODES NEW_PREFIX H K G KW N RHO0 MASS LX LZ AMPLITUDE SAMPLES");
    const fs::path prefix=argv[3],csv=prefix.string()+".csv",json=prefix.string()+".json";
    Check(!fs::exists(csv)&&!fs::exists(json),"Retained output protected");
    const double hinput=std::stod(argv[4]),h=double(float(hinput)),K=std::stod(argv[5]),G=std::stod(argv[6]),kw=std::stod(argv[7]),n=std::stod(argv[8]),rho=std::stod(argv[9]),V=std::stod(argv[10])/rho,Lx=std::stod(argv[11]),Lz=std::stod(argv[12]),A=std::stod(argv[13]);
    const unsigned samples=unsigned(std::stoul(argv[14]));
    const auto kc=fsph::GetKernelWendland_Ctes(true,h);const float hf=float(h),support=2*hf,support2=support*support;
    Check(2*h<Lx*.5&&2*h<Lz*.5,"Minimum image is not unique within support");
    std::ifstream bin(argv[1],std::ios::binary);unsigned head[3];double t0;
    bin.read(reinterpret_cast<char*>(head),sizeof(head));bin.read(reinterpret_cast<char*>(&t0),sizeof(t0));
    Check(bin&&head[0]==128&&head[1]==26&&head[2]==samples&&t0==0,"Unexpected existing wave state header");
    std::vector<std::array<double,26>> states(head[0]);
    for(auto& row:states)bin.read(reinterpret_cast<char*>(row.data()),sizeof(double)*26);
    Check(bool(bin),"Initial-state read failed");
    const double k=2*acos(-1.)/Lx,cu=sqrt((K+4*G/3+kw/n)/rho);std::vector<Symbol> symbols;
    for(unsigned i=0;i<head[0];i++){
      Symbol s;double rawz=0;
      for(unsigned j=0;j<head[0];j++)if(i!=j){
        double dx=states[i][0]-states[j][0],dz=states[i][2]-states[j][2];
        dx-=Lx*std::round(dx/Lx);dz-=Lz*std::round(dz/Lz);
        const float rr2=float(dx*dx+dz*dz);if(rr2>support2||rr2<ALMOSTZERO)continue;
        const float fac=fsph::GetKernelWendland_Fac(kc,hf,rr2);
        const double gx=double(fac)*dx,gz=double(fac)*dz;
        s.mxx-=V*dx*gx;s.mxz-=V*dx*gz;s.mzz-=V*dz*gz;
        s.raw-=V*sin(k*dx)*gx;rawz-=V*sin(k*dx)*gz;
        s.rawfloat-=V*sin(k*dx)*double(fac*float(dx));s.neighbours++;
      }
      const double det=s.mxx*s.mzz-s.mxz*s.mxz;Check(det>0,"Singular initial x-z moment");
      s.cxx=s.mzz/det;s.cxz=-s.mxz/det;s.corr=s.cxx*s.raw+s.cxz*rawz;symbols.push_back(s);
    }
    const Symbol s=symbols.front();double variation=0;
    for(const auto& q:symbols){
      Check(q.neighbours==s.neighbours,"Initial neighbour count varies by receiver");
      variation=(std::max)(variation,(std::max)(fabs(q.raw-s.raw),fabs(q.corr-s.corr)));
    }
    Check(variation<1e-10&&s.raw>0&&s.corr>0,"Not the declared translation-invariant lattice symbol");
    const double omega_double=cu*sqrt(s.raw*s.corr),omega_forcebound=cu*sqrt(s.rawfloat*s.corr),stresscorr=s.cxx*s.rawfloat;
    const double omega=sqrt(s.rawfloat*((K+4*G/3)*stresscorr+(kw/n)*s.corr)/rho),omega_cont=cu*k;
    std::ifstream mode(argv[2]);std::string line;std::getline(mode,line);unsigned count=0;
    std::ofstream out(csv);out<<std::setprecision(17)<<"step,time_s,v_actual,v_discrete,v_continuum,p_actual_Pa,p_discrete_Pa,p_continuum_Pa,u_actual_m,u_discrete_m,u_continuum_m,phase_actual,phase_discrete_proxy,phase_continuum,v_residual,p_residual_Pa,u_residual_m,phase_residual_rad\n";
    double maxv=0,maxp=0,maxu=0,maxphase=0;std::array<double,12> final{};double vd=0,pd=0,ud=0,phase=0;
    while(std::getline(mode,line)){
      std::replace(line.begin(),line.end(),',',' ');std::istringstream input(line);std::array<double,12> row{};
      for(auto& value:row)Check(bool(input>>value),"Incomplete retained modes row");
      Check(fabs(row[2]-cu)<1e-10,"Loaded material differs from retained cu_actual");
      const double time=row[1];vd=A*cos(omega*time);pd=-(kw/n)*s.corr*A/omega*sin(omega*time);ud=A/omega*sin(omega*time);
      phase=atan2(-n*cu*pd/kw,vd);maxv=(std::max)(maxv,fabs(row[3]-vd));maxp=(std::max)(maxp,fabs(row[5]-pd));maxu=(std::max)(maxu,fabs(row[7]-ud));maxphase=(std::max)(maxphase,fabs(row[9]-phase));
      out<<row[0]<<','<<time<<','<<row[3]<<','<<vd<<','<<row[4]<<','<<row[5]<<','<<pd<<','<<row[6]<<','<<row[7]<<','<<ud<<','<<row[8]<<','<<row[9]<<','<<phase<<','<<row[10]<<','<<row[3]-vd<<','<<row[5]-pd<<','<<row[7]-ud<<','<<row[9]-phase<<'\n';
      final=row;count++;
    }
    Check(count==samples&&out.good(),"Retained mode count/output differs from recipe");out.flush();
    std::ofstream result(json);result<<std::setprecision(17)
      <<"{\"offline_completed\":true,\"physical_acceptance\":false,\"samples\":"<<count<<",\"native_ids\":"<<head[0]<<",\"neighbours_per_receiver\":"<<s.neighbours
      <<",\"h_input_double\":"<<hinput<<",\"h_double_from_production_float\":"<<h<<",\"h_float_used_by_kernel\":"<<hf<<",\"awen_float\":"<<kc.awen<<",\"bwen_float\":"<<kc.bwen<<",\"V0\":"<<V<<",\"K_loaded\":"<<K<<",\"G_loaded\":"<<G<<",\"Kw\":"<<kw<<",\"n0\":"<<n<<",\"rho0\":"<<rho
      <<",\"Mxx\":"<<s.mxx<<",\"Mxz\":"<<s.mxz<<",\"Mzz\":"<<s.mzz<<",\"Cxx\":"<<s.cxx<<",\"Cxz\":"<<s.cxz<<",\"Kraw\":"<<s.raw<<",\"Kcorr\":"<<s.corr<<",\"Kraw_float_momentum_product\":"<<s.rawfloat<<",\"symbol_receiver_maxvariation\":"<<variation
      <<",\"k_continuum\":"<<k<<",\"cu\":"<<cu<<",\"omega_all_double_gradient\":"<<omega_double<<",\"omega_float_force_bound\":"<<omega_forcebound<<",\"Kcorr_stress_float_gradient\":"<<stresscorr<<",\"omega_discrete_mixed_linear_approx\":"<<omega<<",\"omega_continuum\":"<<omega_cont<<",\"omega_ratio\":"<<omega/omega_cont
      <<",\"max_v_actual_minus_discrete_m_s\":"<<maxv<<",\"max_p_actual_minus_discrete_Pa\":"<<maxp<<",\"max_u_actual_minus_discrete_m\":"<<maxu<<",\"max_phase_actual_minus_discrete_rad\":"<<maxphase
      <<",\"final_time_s\":"<<final[1]<<",\"final_v_actual\":"<<final[3]<<",\"final_v_discrete\":"<<vd<<",\"final_v_continuum\":"<<final[4]<<",\"final_p_actual_Pa\":"<<final[5]<<",\"final_p_discrete_Pa\":"<<pd<<",\"final_p_continuum_Pa\":"<<final[6]<<",\"final_u_actual_m\":"<<final[7]<<",\"final_u_discrete_m\":"<<ud<<",\"final_u_continuum_m\":"<<final[8]<<",\"final_phase_actual\":"<<final[9]<<",\"final_phase_discrete_proxy\":"<<phase<<",\"final_phase_continuum\":"<<final[10]<<"}\n";
    result.flush();Check(result.good(),"Offline summary output failed");return 0;
  }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
