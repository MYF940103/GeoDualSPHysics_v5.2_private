// One pressure update on consecutive native histories at frozen geometry.
#define main unused_rhs_entry
#include "../outputs/c08_eq47_p3_warm_profile_r1/shared.inc"
#undef main
#include "../../../04_CryerProblem_PR/tests/support/TpiPressureRow.h"

struct Equation { double diagonal=0,residual=0; bool drained=false; };
using Field=std::vector<float>;

static bool Endpoint47(const Equation& row,float pn,double alpha,float q,double beta,double dt,float& dest) {
  if(!Finite(beta)||beta<0.||!Finite(dt)||dt<=0.||!Finite(pn)||!Finite(alpha)) return false;
  if(row.drained || beta==0. || pn>=0.f)
    return tpi_pressure::Endpoint(row.drained,q,row.diagonal,row.residual,dest);
  if(!Finite(q)||!Finite(row.diagonal)||row.diagonal<=0.||!Finite(row.residual)) return false;
  const double c=beta/dt,denominator=row.diagonal+c;
  if(!Finite(c)||!Finite(denominator)) return false;
  const double result=double(q)+(row.residual+c*(alpha-double(q)))/denominator;
  if(!Finite(result)||fabs(result)>FLT_MAX) return false;
  dest=tpi_pressure::WritePressure(result);
  return true;
}

template<class Evaluate,class Record,class Project>
static bool ThreeRounds(Field& previous,Field& current,double beta,double dt,Evaluate evaluate,Record record,Project project) {
  const size_t count=current.size();
  if(!count||previous.size()!=count||!Finite(beta)||beta<0.||!Finite(dt)||dt<=0.) return false;
  std::vector<double> alpha(count);
  Field q(count),next(count);
  std::vector<Equation> eq(count);
  for(size_t i=0;i<count;i++){
    if(!tpi_pressure::Predict(tpi_pressure::Predictor::Linear,current[i],previous[i],alpha[i])) return false;
    q[i]=tpi_pressure::WritePressure(alpha[i]);
  }
  for(unsigned pass=0;pass<3;pass++){
    if(!evaluate(pass,q,eq)) return false;
    for(size_t i=0;i<count;i++){
      if(!Endpoint47(eq[i],current[i],alpha[i],q[i],beta,dt,next[i])) return false;
      record(pass,i,previous[i],current[i],alpha[i],q[i],eq[i],next[i]);
    }
    q.swap(next);
  }
  if(!project(q)) return false;
  previous.swap(current);
  current.swap(q);
  return true;
}

static void CheckRejection(){
  const Field a={4.f,-4.f,2.f,-1.f,1.f},b={-1.f,1.f,0.f,-.1f,.1f};
  for(unsigned fault=0;fault<3;fault++){
    Field previous=a,current=b;
    auto equations=[&](unsigned pass,const Field&,std::vector<Equation>& eq){
      for(auto& e:eq) e={2.,pass==0?14.:-22.,false};
      eq[3].drained=true;
      if(fault==0 && pass==2) eq.back().diagonal=0.;
      return true;
    };
    auto verify=[](unsigned pass,size_t i,float,float pn,double alpha,float q,const Equation& e,float next){
      if(e.drained){Need(Bits(next,0.f),"Drained precedence");return;}
      if(!pass && i==0) Need(pn<0.f && alpha<0. && q<0.f && next>0.f,"Negative to positive fixture");
      if(pass==1 && i==1) Need(pn>0.f && q>0.f && next<0.f,"Positive to negative fixture");
      if(i==2) Need(pn==0.f,"Zero branch fixture");
    };
    const bool ok=ThreeRounds(previous,current,.04,1.,equations,verify,[&](Field&){return fault!=1;});
    Need(ok==(fault==2),"Unexpected transaction status");
    if(!ok) Need(previous==a && current==b,"Failure rotated or modified committed histories");
    else Need(previous==b && current!=b,"Successful rotation missing");
  }
}

class WarmComponent: public Probe {
public:
  void Run(const JSphCfgRun* cfg,JLog2* log,const pf::path& native){
#include "../outputs/c08_tpi_state_r1_build/setup.inc"
    const Snapshot pre(native,0),now(native,1);
    const double dt=FixedDt->GetFixedValue();
    Need(now.completed==pre.completed+1 && Bits(pre.time+dt,now.time),"Nonconsecutive native pressure histories");
    std::ofstream rows(pf::path(cfg->DirOut)/"rows.csv"),ends(pf::path(cfg->DirOut)/"endpoints.csv");
    rows<<std::setprecision(17)<<"beta,round,id,previous,pn,p_alpha,q,S,R,next\n";
    ends<<std::setprecision(17)<<"beta,id,fs,pn,third,projected,rotated_previous\n";
    for(double beta:{0.,.04}){
      Restore(now);
      Snapshot stage=now;
      Field previous(Soil),current(Soil),third(Soil);
      for(unsigned i=0;i<Soil;i++){
        const unsigned id=i+2060;
        previous[i]=pre.p[pre.byid[id]];
        current[i]=now.p[now.byid[id]];
      }
      auto load=[&](const Field& trial){
        for(unsigned i=0;i<Soil;i++){
          const unsigned s=stage.byid[i+2060];
          stage.p[s]=trial[i];stage.excess[s]=stage.p[s]-stage.p0[s];
        }
        Copy(stage);
        Unchanged(stage);
      };
      auto evaluate=[&](unsigned,const Field& q,std::vector<Equation>& eq){
        load(q);
        Interaction_Forces(INTERSTEP_SymCorrector);
        try{
          for(unsigned slot=Npb;slot<Np;slot++){
            const auto groups=Assemble(slot);
            const auto& z=groups[0];
            const auto ai=ToTDouble3(Acec[slot]);
            const bool fs=IsFreeSurfaceParticle(slot,Codec,FSTypec);
            const bool drained=IsHydroMechDrainageActive() && IsHydroMechDrainedParticle(slot,Posc,Codec,FSTypec);
            const double k=GetDynamicConductivityCpu(slot),dk=k/((1.-double(SoilCte.Porosity))*DynamicPoreConductivityCk);
            const double lap=fs ? z.lp+rho*(Dot(ai,z.lx)+z.da)
              : z.lp-z.gp.x*z.lx.x-z.gp.y*z.lx.y-z.gp.z*z.lx.z+rho*z.da;
            const double chain=dk*(z.gradj.x*(z.gp.x+rho*ai.x)+z.gradj.y*(z.gp.y+rho*ai.y)+z.gradj.z*(z.gp.z+rho*ai.z));
            eq[Idpc[slot]-2060]={-k*z.sumw,-gamma*PoroThetac[slot]+k*lap+chain,drained};
            Need(!drained,"Unexpected C08 prescribed drained receiver");
          }
          Unchanged(stage);
        }catch(...){PosInteraction_Forces();throw;}
        PosInteraction_Forces();return true;
      };
      auto record=[&](unsigned pass,size_t i,float prev,float pn,double alpha,float q,const Equation& e,float dest){
        if(beta==0.){
          float old;
          Need(tpi_pressure::Endpoint(e.drained,q,e.diagonal,e.residual,old)&&Bits(dest,old),"Legacy pressure row differs");
        }
        rows<<beta<<','<<pass<<','<<(i+2060)<<','<<prev<<','<<pn<<','<<alpha<<','<<q<<','<<e.diagonal<<','<<e.residual<<','<<dest<<'\n';
      };
      auto project=[&](Field& q){
        third=q;load(q);ApplyPorePressureBoundaries();
        for(unsigned slot=Npb;slot<Np;slot++) q[Idpc[slot]-2060]=PorePressc[slot];
        return true;
      };
      Need(ThreeRounds(previous,current,beta,dt,evaluate,record,project),"Pressure transaction failed");
      for(unsigned i=0;i<Soil;i++){
        const auto s=now.byid[i+2060];const bool fs=now.fs[s]==2||now.fs[s]==3;
        Need(Bits(previous[i],now.p[s]) && Bits(current[i],fs&&third[i]>0.f?0.f:third[i]),"Incorrect history/projection");
        ends<<beta<<','<<(i+2060)<<','<<now.fs[s]<<','<<now.p[s]<<','<<third[i]<<','<<current[i]<<','<<previous[i]<<'\n';
      }
      Restore(now);Unchanged(now);
    }
    rows.flush();ends.flush();Need(bool(rows)&&bool(ends),"Failed to write complete component outputs");
  }
};
int main(int argc,char** argv){try{
  CheckRejection();
  const auto tests=pf::path(__FILE__).parent_path().parent_path(),run=tests/"outputs/c08_h18_as03n255_full3_r1";
  AppInfo.ConfigRunPaths(argv[0]);JSphCfgRun cfg;cfg.LoadArgv(argc,argv);
  Need(cfg.Cpu && !cfg.PartBegin && pf::absolute(cfg.CaseName)==run/run.filename()
    && pf::absolute(cfg.DirOut)==tests/"outputs/c08_eq47_p3_warm_r1" && !pf::exists(cfg.DirOut),"Fresh component directory required");
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
  WarmComponent probe;probe.Run(&cfg,AppInfo.LogPtr(),tests/"outputs/c08_h18_storage_debug2_GPU_r1/native_r1");return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';}catch(const std::exception& e){std::cerr<<e.what()<<'\n';}return 1;}
