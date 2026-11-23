// One fully walled finite-storage PRE spatial evaluation. No time integration.
#define main unused_postrelease_rhs_main
#include "../outputs/c08_tpi_state_r1_build/shared.inc"
#undef main
#include "JGravityPreloadState.h"

class ClosedPreProbe : public Probe {
public:
  void Evaluate(const JSphCfgRun* cfg, const pf::path& pre) {
    AppName=AppInfo.GetFullName(); Log=AppInfo.LogPtr(); CfgRun=cfg; Timersc->Config(false);
    LoadConfig(cfg); LoadCaseParticles(); VisuConfig(); ConfigDomain(); ConfigRunMode(); InitRunCpu();
    Need(!IsGravityPreloadHandoff() && !GravityPreloadReleased && GravityPreload && !GravityPreloadElasticSource
      && SoilDamping && SoilDampingCoef==.03f && PoreShepardRegularization && PoreShepardInterval==40
      && !ArtificialStress && !NoPenetration && !HourglassCpu && !SoilHourglassXi && !PeriActive
      && DynamicPorePressure && DynamicPoreConductivity && DynamicPoreConductivityCk==2.
      && !HydroMechDrainage && HydroMechFreeSeepage && KernelH==.072f && Dp==.04
      && TKernel==KERNEL_Wendland && TStep==STEP_Symplectic,"Wrong PRE controls");
    // Use the schema2 reader and the owner's complete field/ID restoration; keep original PRE controls and wall.
    GravityPreloadStateFile=pre.string();
    JGravityPreloadState raw; LoadGravityPreloadState(raw); RunGravityPreloadHandoffCpu();
    GravityPreloadStateFile.clear(); FreePartsInit();
    Need(Np==7060 && Npb==2060 && Nstep==2000000 && raw.Schema==2 && raw.Dt==5e-6 && Bits(TimeStep,raw.Time)
      && !GravityPreloadReleased && !PorePressPrec && SoilDamping && PoreShepardRegularization,"Wrong walled PRE clock/geometry");
    std::ofstream rows(pf::path(cfg->DirOut)/"rows.csv");
    rows<<std::setprecision(17)<<"id,x_m,z_m,FS_saved,FS_fresh,wall_neighbors,p_Pa,p0_Pa,J,n,V_m2,k_m_s,kappa,sxx_Pa,syy_Pa,szz_Pa,sxz_Pa,vx_m_s,vz_m_s,theta_saved_s_1,theta_fresh_s_1,compression,Darcy,gradk,Rgamma,S_LP,actual_finite_kw_rate_Pa_s,roundoff_bound\n";
    Interaction_Forces(INTERSTEP_SymCorrector);
    try {
      for(unsigned i=Npb;i<Np;i++){
        const unsigned id=Idpc[i],s=raw.ById[id];
        const auto kk=raw.SigmaKK[s],ij=raw.SigmaIJ[s];
        const auto sigma=TSymMatrix3d(kk.x,ij.x,ij.z,kk.y,ij.y,kk.z);
        Need(Bits(Posc[i],raw.Pos[s]) && Bits(Velrhopc[i],raw.VelRhop[s]) && Bits(Sigmac[i],sigma)
          && Bits(PoroJc[i],raw.J[s]) && Bits(Kplasticc[i],raw.Kplastic[s]) && Bits(PorePressc[i],raw.PorePress[s])
          && Bits(PorePress0c[i],raw.PorePress0[s]),"Spatial operator changed primary state");
        const auto sums=Assemble(i);const auto& z=sums[0];
        const bool fs=IsFreeSurfaceParticle(i,Codec,FSTypec);
        const auto ai=ToTDouble3(Acec[i]);double n,V,rhot;GetPorosityFeedbackStateCpu(i,n,V,rhot);
        const double rho=SoilCte.PoreWaterRho,gamma=rho*9.80665,kw=SoilCte.PoreWaterBulkModulus;
        const double k=GetDynamicConductivityCpu(i),dk=k/((1.-double(SoilCte.Porosity))*DynamicPoreConductivityCk);
        const double lap=fs ? z.lp+rho*(Dot(ai,z.lx)+z.da) : z.lp-z.gp.x*z.lx.x-z.gp.y*z.lx.y-z.gp.z*z.lx.z+rho*z.da;
        const double chain=dk*Dot(z.gradj,z.gp+ai*rho);
        const double compression=-gamma*PoroThetac[i],darcy=k*lap,residual=compression+darcy+chain,diagonal=-k*z.sumw;
        const double literal=kw/n*(-PoroThetac[i]+k/gamma*lap+chain/gamma);
        Need(Bits(float(literal),PorePressRatec[i]) && std::isfinite(residual) && diagonal>0.,"Actual finite-Kw RHS or positive diagonal differs");
        const double terms=std::abs(compression)+k*(z.lpabs+(fs?0:Dot(z.gpabs,z.lxabs))+rho*(z.daabs+(fs?Dot(Abs(ai),z.lxabs):0)))+dk*Dot(z.jabs,z.gpabs+Abs(ai)*rho);
        const double roundoff=2*RoundoffGamma(64*(z.count+1))*terms;
        rows<<id<<','<<Posc[i].x<<','<<Posc[i].z<<','<<raw.FSType[s]<<','<<FSTypec[i]<<','<<sums[2].count
          <<','<<PorePressc[i]<<','<<PorePress0c[i]<<','<<PoroJc[i]<<','<<n<<','<<V<<','<<k<<','<<Kplasticc[i]
          <<','<<kk.x<<','<<kk.y<<','<<kk.z<<','<<ij.z<<','<<Velrhopc[i].x<<','<<Velrhopc[i].z<<','<<raw.Theta[s]
          <<','<<PoroThetac[i]<<','<<compression<<','<<darcy<<','<<chain<<','<<residual<<','<<diagonal
          <<','<<PorePressRatec[i]<<','<<roundoff<<'\n';
      }
    } catch(...) {PosInteraction_Forces();throw;}
    PosInteraction_Forces();rows.flush();
    Need(bool(rows) && Bits(TimeStep,raw.Time) && Nstep==2000000 && !GravityPreloadReleased,"Unexpected clock or output change");
  }
};

int main(int argc,char** argv) {
  try {
    const pf::path tests=pf::path(__FILE__).parent_path().parent_path();
    const auto run=tests/"outputs/c08_h18_wend_psi0_pre_r2",pre=run/"data/Part_1000.bi4";
    AppInfo.ConfigRunPaths(argv[0]);JSphCfgRun cfg;cfg.LoadArgv(argc,argv);
    Need(cfg.Cpu && !cfg.PartBegin && pf::absolute(cfg.CaseName)==run/run.filename()
      && pf::absolute(cfg.DirOut)==tests/"outputs/c08_pre_m0_r1" && !pf::exists(cfg.DirOut),"Expected original PRE seed and fresh diagnostic output");
    const Stamp retained(pre);
    AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);
    AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    ClosedPreProbe probe;probe.Evaluate(&cfg,pre);retained.Check();return 0;
  }catch(const JException& e){std::cerr<<e.ToStr()<<'\n';}catch(const std::exception& e){std::cerr<<e.what()<<'\n';}
  return 1;
}
