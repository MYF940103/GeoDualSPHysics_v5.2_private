// Frozen-geometry evaluation of three pressure defects. No simulation time advance.
#define main unused_retained_rhs_entry
#include "../outputs/c08_tpi_state_r1_build/shared.inc"
#undef main
#include "../outputs/c08_tpi_state_r1_build/reference.inc"

class FrozenRounds : public Probe {
  void CompareBaseline(unsigned id,const Snapshot& initial,unsigned slot,
                       const RhsReference& reference) const {
    Need(reference.present && reference.step==initial.completed && Bits(initial.time,reference.time)
      && reference.fs==FSTypec[slot] && Bits(reference.ace,Acec[slot])
      && Bits(reference.theta,PoroThetac[slot]) && Bits(reference.rs,Rsigmac[slot])
      && Bits(reference.rate,PorePressRatec[slot]),"Baseline force mismatch, ID "+std::to_string(id));
  }

  void RunRounds(const Snapshot& initial,const std::vector<RhsReference>& reference,
                 double beta,double rho,double gamma,std::ostream& rows) {
    Restore(initial);
    Snapshot stage=initial;
    std::vector<float> next(Soil);
    const double dt=FixedDt->GetFixedValue();
    // The retained snapshots do not carry the immediately preceding pressure.
    // Use one cold history per state; retain p_alpha across every defect.
    for(unsigned pass=0;pass<=3;pass++){
      Copy(stage);
      if(pass==3){
        ApplyPorePressureBoundaries();
        for(unsigned slot=Npb;slot<Np;slot++){
          const unsigned s=initial.byid[Idpc[slot]];
          const bool fs=stage.fs[s]==2 || stage.fs[s]==3;
          const float target=fs && stage.p[s]>0.f ? 0.f : stage.p[s];
          Need(Bits(target,PorePressc[slot]) && FSTypec[slot]==stage.fs[s],"Completed free-surface boundary changed unexpectedly");
          stage.p[s]=PorePressc[slot];
          stage.excess[s]=stage.p[s]-stage.p0[s];
        }
      }
      Unchanged(stage);
      Interaction_Forces(INTERSTEP_SymCorrector);
      try{
        for(unsigned slot=Npb;slot<Np;slot++){
          const unsigned id=Idpc[slot],s=initial.byid[id];
          const auto groups=Assemble(slot);
          const auto& z=groups[0];
          const auto ai=ToTDouble3(Acec[slot]);
          const bool fs=IsFreeSurfaceParticle(slot,Codec,FSTypec);
          const bool drained=IsHydroMechDrainageActive() && IsHydroMechDrainedParticle(slot,Posc,Codec,FSTypec);
          const double k=GetDynamicConductivityCpu(slot);
          const double dk=k/((1.-double(SoilCte.Porosity))*DynamicPoreConductivityCk);
          const double lap=fs ? z.lp+rho*(ai.x*z.lx.x+ai.y*z.lx.y+ai.z*z.lx.z+z.da)
            : z.lp-z.gp.x*z.lx.x-z.gp.y*z.lx.y-z.gp.z*z.lx.z+rho*z.da;
          const double chain=dk*(z.gradj.x*(z.gp.x+rho*ai.x)+z.gradj.y*(z.gp.y+rho*ai.y)+z.gradj.z*(z.gp.z+rho*ai.z));
          const double residual=-gamma*PoroThetac[slot]+k*lap+chain;
          const double diagonal=-k*z.sumw;
          const float pn=initial.p[s],q=PorePressc[slot];
          const double c=pn<0.f ? beta/dt : 0.;
          Need(Finite(residual) && Finite(diagonal) && diagonal>0. && Finite(ai) && !drained,"Invalid frozen C08 spatial row");
          if(pass==0) CompareBaseline(id,initial,slot,reference[id]);
          const double corrected=pass<3 ? double(q)+(residual+c*(double(pn)-double(q)))/(diagonal+c) : double(q);
          Need(Finite(corrected) && fabs(corrected)<=FLT_MAX,"Frozen defect overflowed");
          next[id-2060]=float(corrected);
          rows<<initial.part<<','<<initial.time<<','<<beta<<','<<pass<<','<<id<<','<<FSTypec[slot]<<','<<pn<<','<<q<<','<<diagonal<<','<<residual<<','<<next[id-2060]<<','<<ai.x<<','<<ai.y<<','<<ai.z<<'\n';
        }
        Unchanged(stage);
      }catch(...){PosInteraction_Forces();throw;}
      PosInteraction_Forces();
      if(pass<3) for(unsigned id=2060;id<Original;id++){
        const unsigned s=initial.byid[id];
        stage.p[s]=next[id-2060]; stage.excess[s]=stage.p[s]-stage.p0[s];
      }
    }
    Restore(initial);
    Unchanged(initial);
  }
public:
  void Run(const JSphCfgRun* cfg,JLog2* log,const pf::path& native,const pf::path& referenceFile){
#include "../outputs/c08_tpi_state_r1_build/setup.inc"
    const auto references=ReadReference(referenceFile);
    std::ofstream rows(pf::path(cfg->DirOut)/"rows.csv");
    Need(bool(rows),"Cannot open rows.csv");
    rows<<std::setprecision(17)<<"part,time_s,beta,pass,id,fs,pn,q,S,R,q_next,ax,ay,az\n";
    for(unsigned which=0;which<2;which++){
      const Snapshot initial(native,which);
      for(double beta:{0.,.04}) RunRounds(initial,references[which],beta,rho,gamma,rows);
    }
    rows.flush();Need(bool(rows),"Could not flush rows");
  }
};
int main(int argc,char** argv){
  try{
    const auto tests=pf::path(__FILE__).parent_path().parent_path();
    const auto run=tests/"outputs/c08_h18_as03n255_full3_r1";
    AppInfo.ConfigRunPaths(argv[0]);JSphCfgRun cfg;cfg.LoadArgv(argc,argv);
    Need(cfg.Cpu && !cfg.PartBegin && pf::absolute(cfg.CaseName)==run/"c08_h18_as03n255_full3_r1"
      && pf::absolute(cfg.DirOut)==tests/"outputs/c08_tpi_eq47_rounds_r1" && !pf::exists(cfg.DirOut),"Expected retained case and fresh diagnostic directory");
    AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);
    AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    FrozenRounds probe;
    probe.Run(&cfg,AppInfo.LogPtr(),run/"native_r1",tests/"outputs/c08_h18_as03_rhs_r1/soil_rhs.csv");
    return 0;
  }catch(const JException& e){std::cerr<<e.ToStr()<<'\n';}
   catch(const std::exception& e){std::cerr<<e.what()<<'\n';}
  return 1;
}
