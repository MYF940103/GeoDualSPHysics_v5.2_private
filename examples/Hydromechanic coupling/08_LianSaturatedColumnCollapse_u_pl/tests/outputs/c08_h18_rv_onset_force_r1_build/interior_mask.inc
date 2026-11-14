  std::vector<byte> InteriorMask()const{
    std::vector<byte> inside(Original,0);
    for(unsigned i=Npb;i<Np;i++){
      inside[Idpc[i]]=1;const StNgSearch ngs=nsearch::Init(Dcellc[i],true,DivData);
      for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
        const tuint2 range=nsearch::ParticleRange(y,z,ngs,DivData);
        for(unsigned j=range.x;j<range.y;j++){Need(j<Npb&&CODE_IsFixed(Codec[j]),"Unexpected boundary cohort donor");const float dx=float(Posc[i].x-Posc[j].x),dy=float(Posc[i].y-Posc[j].y),dz=float(Posc[i].z-Posc[j].z),r2=dx*dx+dy*dy+dz*dz;if(r2<=KernelSize2)inside[Idpc[i]]=0;}
      }
    }
    return inside;
  }
