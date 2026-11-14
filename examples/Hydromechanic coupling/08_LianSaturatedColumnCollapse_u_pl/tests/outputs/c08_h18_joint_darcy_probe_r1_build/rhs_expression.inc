        // Literal original raw-FS source operation order, including its final float commit.
        const double lap=(sf?z.lp+rho*(ai.x*z.lx.x+ai.y*z.lx.y+ai.z*z.lx.z+z.da):z.lp-z.gp.x*z.lx.x-z.gp.y*z.lx.y-z.gp.z*z.lx.z+rho*z.da);
        const double chain=dk*(z.gradj.x*(z.gp.x+rho*ai.x)+z.gradj.y*(z.gp.y+rho*ai.y)+z.gradj.z*(z.gp.z+rho*ai.z));const double literal=kw/n*(-PoroThetac[i]+k/gamma*lap+chain/gamma);
        std::array<std::array<double,7>,3> pieces{};for(unsigned g=0;g<3;g++){const auto& t=r[g];auto& q=pieces[g];q[0]=g?0:-B*PoroThetac[i];q[1]=B*k/gamma*t.lp;q[2]=sf?0:-B*k/gamma*Dot(z.gp,t.lx);q[3]=B*k/gamma*rho*t.da;q[4]=sf?B*k/gamma*rho*Dot(ai,t.lx):0;q[5]=B/gamma*dk*Dot(t.gradj,z.gp);q[6]=B/gamma*dk*rho*Dot(t.gradj,ai);}
        double expanded=0,partition=0;for(unsigned t=0;t<7;t++){expanded+=pieces[0][t];partition+=pieces[1][t]+pieces[2][t];}partition+=pieces[0][0];
        const double magnitude=B*fabs(PoroThetac[i])+B/gamma*(k*(z.lpabs+(sf?0:Dot(z.gpabs,z.lxabs))+rho*(z.daabs+(sf?Dot(Abs(ai),z.lxabs):0)))+dk*Dot(z.jabs,z.gpabs+Abs(ai)*rho));const double dbudget=2*RoundoffGamma(64*(z.count+1))*magnitude;
