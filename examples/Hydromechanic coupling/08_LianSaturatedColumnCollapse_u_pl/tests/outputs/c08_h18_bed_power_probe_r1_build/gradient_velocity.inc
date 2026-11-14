          float dvx_rhop=velp1.x-velrhop2.x, dvy_rhop=velp1.y-velrhop2.y, dvz_rhop=velp1.z-velrhop2.z;
          float dvx_visc=dvx_rhop, dvy_visc=dvy_rhop, dvz_visc=dvz_rhop;
          if(mdbc2p2 && TangenVelc){
            tfloat3 tangentvelp2=TangenVelc[p2];
            if(rsym)tangentvelp2.y=-tangentvelp2.y; //<vs_syymmetry>
            dvx_visc=velp1.x-tangentvelp2.x;
            dvy_visc=velp1.y-tangentvelp2.y;
            dvz_visc=velp1.z-tangentvelp2.z;
          }
          //-SPR changes derivatives, not physical wall velocities or viscous forces.
          const bool sprwall=(boundp2 && !ftp2 && BoundDerivativeVelc
            && !(mdbc2p2 && BoundModec && BoundModec[p2]==BMODE_MDBC2OFF));
          const float dvx_rhop_deriv=(sprwall? velp1.x-BoundDerivativeVelc[p2].x: dvx_rhop);
          const float dvy_rhop_deriv=(sprwall? velp1.y-BoundDerivativeVelc[p2].y: dvy_rhop);
          const float dvz_rhop_deriv=(sprwall? velp1.z-BoundDerivativeVelc[p2].z: dvz_rhop);
          const float dvx_grad_deriv=(sprwall? dvx_rhop_deriv: dvx_visc);
          const float dvy_grad_deriv=(sprwall? dvy_rhop_deriv: dvy_visc);
          const float dvz_grad_deriv=(sprwall? dvz_rhop_deriv: dvz_visc);
