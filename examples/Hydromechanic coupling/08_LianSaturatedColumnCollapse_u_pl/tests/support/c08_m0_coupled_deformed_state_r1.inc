  // Called after the genuine schema2 PRE loader and the original one-time wall removal.
  // The packed input is the actual finite-Kw PART sorted by original IDs.
  if(!GravityPreloadReleased || Np!=6805 || Npb!=1805 || Nstep!=2000000
    || SoilDamping || PoreShepardRegularization || !NoPenetration || !ArtificialStress)
    Run_Exceptioon("Unexpected original released geometry or physics in private snapshot.");
  struct Initial {
    struct Header {unsigned count,step;double time,releaseTime;};
    struct Row {
      unsigned id;tdouble3 pos;tfloat3 velocity;float density;
      tdouble3 sigmaKK,sigmaIJ;float kappa,p,p0;double J,theta;unsigned fs;tfloat3 normal;float posDiv;
    };
  };
  const char* file=std::getenv("C08_RELEASED_NATIVE_ROWS");
  if(!file)Run_Exceptioon("Missing checked released-state input.");
  std::ifstream input(file,std::ios::binary);
  Initial::Header hd{};
  input.read(reinterpret_cast<char*>(&hd),sizeof(hd));
  if(!input || hd.count!=6805 || hd.step!=2076001 || hd.time<=10.38 || hd.time>=10.381
    || hd.releaseTime!=GravityPreloadActualTime)Run_Exceptioon("Released-state plan mismatch.");
  std::vector<Initial::Row> rows(CaseNp);
  for(unsigned i=0;i<hd.count;++i){
    Initial::Row r{};
    const auto read=[&](auto& val){input.read(reinterpret_cast<char*>(&val),sizeof(val));};
    read(r.id);read(r.pos);read(r.velocity);read(r.density);read(r.sigmaKK);read(r.sigmaIJ);
    read(r.kappa);read(r.p);read(r.p0);read(r.J);read(r.theta);read(r.fs);read(r.normal);read(r.posDiv);
    if(!input || r.id!=(i<1805?i:i+255))Run_Exceptioon("Released original ID mismatch.");
    rows.at(r.id)=r;
  }
  if(input.peek()!=std::ifstream::traits_type::eof())Run_Exceptioon("Excess released-state data.");
  const auto apply=[&](){
    for(unsigned i=0;i<Np;i++){
      const auto& r=rows.at(Idpc[i]);
      if(r.id!=Idpc[i] || (i<Npb && memcmp(Posc+i,&r.pos,sizeof(r.pos)))
        || memcmp(PorePress0c+i,&r.p0,sizeof(float)))Run_Exceptioon("Deformed state reference or fixed position mismatch.");
      Posc[i]=r.pos;Velrhopc[i]=TFloat4(r.velocity.x,r.velocity.y,r.velocity.z,r.density);
      Sigmac[i]=TSymMatrix3d(r.sigmaKK.x,r.sigmaIJ.x,r.sigmaIJ.z,r.sigmaKK.y,r.sigmaIJ.y,r.sigmaKK.z);
      Kplasticc[i]=r.kappa;PorePressc[i]=r.p;PorePress0c[i]=r.p0;PoroJc[i]=r.J;PoroThetac[i]=r.theta;
      FSTypec[i]=r.fs;FSNormalc[i]=r.normal;PosDivc[i]=r.posDiv;
    }
  };
  apply();LoadDcellParticles(Np,Codec,Posc,Dcellc);
  TpiEndpoint=true;BoundChanged=true;RunCellDivide(true);TpiEndpoint=false;
  if(Np!=6805 || Npb!=1805 || CellDivSingle->GetNpfOut() || CellDivSingle->GetNpfOutIgnore())
    Run_Exceptioon("Deformed rebuild changed native ownership.");
  apply();
  InitTpiPressure();
  for(unsigned i=0;i<Np;i++){
    const auto& r=rows.at(Idpc[i]);
    const tdouble3 kk={Sigmac[i].xx,Sigmac[i].yy,Sigmac[i].zz},ij={Sigmac[i].xy,Sigmac[i].yz,Sigmac[i].xz};
    if(memcmp(Posc+i,&r.pos,sizeof(r.pos)) || memcmp(&Velrhopc[i].x,&r.velocity,sizeof(r.velocity))
      || memcmp(&Velrhopc[i].w,&r.density,sizeof(float)) || memcmp(&kk,&r.sigmaKK,sizeof(kk)) || memcmp(&ij,&r.sigmaIJ,sizeof(ij))
      || memcmp(Kplasticc+i,&r.kappa,sizeof(float)) || memcmp(PorePressc+i,&r.p,sizeof(float)) || memcmp(PorePress0c+i,&r.p0,sizeof(float))
      || memcmp(PoroJc+i,&r.J,sizeof(double)) || memcmp(PoroThetac+i,&r.theta,sizeof(double))
      || FSTypec[i]!=r.fs || memcmp(FSNormalc+i,&r.normal,sizeof(r.normal)) || memcmp(PosDivc+i,&r.posDiv,sizeof(float))
      || (i>=Npb && memcmp(&TpiPrevious.at(r.id),&r.p,sizeof(float))))Run_Exceptioon("Deformed pre-update bit check failed.");
  }
  Nstep=hd.step;TimeStep=TimeStepIni=TimeStepM1=hd.time;LastDt=SymplecticDtPre=5e-6;
  PartNstep=int(Nstep)-1;Part=1;PartDtMin=DBL_MAX;PartDtMax=-DBL_MAX;
  TimePartNext=TimeStep;FixedDt->GetDtError(true);
  Log->Printf("C08M0Deformed import_exact=%u fixed=%u soil=%u source_t=%.17g completed=%u previous=cold_actual_p release_t=%.17g",Np,Npb,Np-Npb,TimeStep,unsigned(Nstep),GravityPreloadActualTime);
