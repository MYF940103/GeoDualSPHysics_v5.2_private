# jgeot.21.00349 787..805

> Auto-converted from PDF for Codex/code-reference reading. Formatting, equations, figures, and tables may require checking against the original PDF.

- Source PDF: `Lian 2022 unsaturated soil rainfall-induced slope failure.pdf`
- Pages: 19

## Extracted Text

### Page 1

Lian, Y. et al. (2024). Géotechnique 74, No. 8, 787–805 [https://doi.org/10.1680/jgeot.21.00349]

     A computationally efficient SPH framework for unsaturated soils
          and its application to predicting the entire rainfall-induced
                               slope failure process

        YANJIAN LIAN  , HA H. BUI†, GIANG D. NGUYEN‡, SHAOHAN ZHAO  and ASADUL HAQUE

              The first and fully validated smoothed particle hydrodynamics (SPH) model is presented to tackle
                coupled flow–deformation problems in unsaturated porous media that undergo large deformation and
                   post-failure behaviour. Unlike the commonly adopted double-layer SPH framework for saturated soils,
                    this paper presents a three-phase single-layer SPH model capable of predicting anisotropic seepage
                 flows through porous media and their complete time-dependent transition from unsaturated to
                  saturated states, as well as their influence on the mechanical behaviour of the porous media and vice
                   versa. The mathematical framework is developed based on Biot’s mixture theory and discretised using
                 the authors’ recently developed novel SPH approximation scheme for the second derivatives of a field
                  quantity. The soil is modelled using a suction-dependent elastoplastic constitutive model, expressed in
                terms of effective stress and suction. In addition, an adaptive two-timescale scheme is proposed for the
                       first time to address existing challenges in solving coupled-flow large-deformation problems that
                  involve a significant difference in the timescale required for the solid and fluid phases. The capability of
                 the proposed SPH model was demonstrated through fundamental consolidation tests and a large-scale
                  rainfall-induced slope  failure experiment. Very good agreements with theoretical solutions and
                 experimental results are achieved, suggesting that the proposed SPH model can be readily extended to
                  solve a wide range of large-scale geotechnical applications involving coupled unsaturated seepage–
                deformation problems.

           KEYWORDS: coupled flow–deformation analysis; landslides; large deformation; numerical modelling;
                   rainfall-induced slope failure; SPH; unsaturated soils

      INTRODUCTION                                                distortion, including the particle FEM (Oñate et al., 2004;
       The  design  of many  geotechnical  applications  requires     Jin et al., 2020) or the material point method (Bandara &
        knowledge of unsaturated soils and, in many cases, such    Soga, 2015; Yerro et al., 2015; Alonso, 2021). Nevertheless,
          applications  involve  large deformations and  failures  of     there is still a need to develop a more robust computational
          these materials. Rainfall-induced slope  failure  is one of    approach that can predict fully coupled seepage-induced
          these applications that has been extensively studied in the     large deformation and failure behaviour of geomaterials.
          past (Borja & White, 2010; Yerro et al., 2015; Switała & Wu,     Smoothed particle hydrodynamics (SPH)  is one of the
         2018; Alonso, 2021). When  rainfall water  infiltrates the     oldest truly mesh-free methods, and was originally developed
         ground, the accumulated rainwater can cause the ground-     for astrophysical applications (Gingold & Monaghan, 1977;
         water level to rise, leading to a reduction in soil suctions    Lucy, 1977). Since  its  first successful application for the
        and the shear strength of soils, threatening the performance    modelling of the elastoplastic behaviour of geomaterials (Bui
        and  safety  of  geo-infrastructures  or,  in  the  worst-case     et al., 2008a), SPH has been widely used to solve a range of
          scenarios, causing  severe damage and  failures  in  these    challenging geotechnical problems – for example, granular
           infrastructures. To predict these problems, the conventional    flows (Bui et al., 2008b; Peng et al., 2015, 2016; Nguyen
          finite-element method (FEM)  is often a popular choice     et al., 2017; Fávero Neto & Borja, 2018; Chalk et al., 2020;
        owing to  its  capability to provide robust and accurate   Yang et al., 2020), slope failures (Bui et al., 2011; Blanc &
          solutions for small-deformation analyses. However, when it     Pastor, 2012; Bui & Fukagawa, 2013; Pastor et al., 2014; He
        comes  to  large deformation and  failure  predictions  of     et al., 2018; Zhao et al., 2019), earthquake-induced soil slope
          geomaterials, FEM is well known for suffering from mesh     failure (Bui et al., 2010; Chen & Qiu, 2014; Bao et al., 2020),
          distortion issues (Bui & Nguyen, 2021). Recent advances in     soil–structure interactions (Bui et  al., 2008b, 2014; Zhan
     FEM modelling have led to several FEM-based modelling     et al., 2020; Sheikh et al., 2021; Yang et al., 2021), desi-
         approaches that could address issues associated with mesh    ccation cracking in soils (Tran et al., 2019, 2020) and rock
                                                                              fractures (Wang et al., 2019, 2020; Gharehdash et al., 2020;
                                                                           del Castillo et al., 2021). In addition, for coupled fluid–solid
                                                                            interaction problems in geomechanics, there exist two SPH
         Manuscript received 1 November 2021; revised manuscript accepted    approaches to solve governing equations for fully saturated
         19 May 2022. First published online ahead of print 28 June 2022.       soils: multi-layer particle and single-layer particle approaches
          Discussion on this paper closes on 1 November 2024, for further                                                                      (Bui & Nguyen, 2021). In the first SPH approach, a saturated
            details see p. ii.
                                                                 porous medium is represented by two layers of Lagrangian
           Department of Civil Engineering, Monash University, Australia.
                                                                                   particles, over which the governing equations of each phase         † Department of Civil Engineering, Monash University, Australia
          (Orcid:0000-0001-8071-5433).                                     are solved separately (Bui et al., 2007; Bui & Nguyen, 2017;
         ‡ School of Civil, Environmental & Mining Engineering, University    Pastor et  al., 2018). In the second SPH approach, the
           of Adelaide, Australia.                                            saturated porous medium is represented by a single layer of

                                                           787

Downloaded from http://www.emerald.com/jgeot/article-pdf/74/8/787/9585766/jgeot_21_00349.pdf by Kyushu University user on 06 May 2026

### Page 2

788                         LIAN, BUI, NGUYEN, ZHAO AND HAQUE

           Lagrangian particles, each of which carries the information      Expanding equation (1) for each phase component and
             of both water and  solid phases, and the  fully coupled     rewriting all resulting equations on the same solid phase
            governing equations of this two-phase system are solved on     reference  framework,  the  following  equations  can  be
           a single set of SPH particles (Bui & Fukagawa, 2009; Pastor    obtained after enforcing the incompressibility condition for
              et al., 2009). Both multi-layer and single-layer approaches     solid grains (Lian et al., 2021)
            have  their own advantages  in  specific  applications. For
                                                                           dsn
            example,  the  multi-layer method  is more  suitable  for      ¼ ð 1  n Þr  vs                                   ð2Þ
           problems where explicit interactions between the solid and        dt
              fluid phases are required (e.g. overtopping or internal piping
              failure  behaviour  of  saturated  soils).  In  contrast,  the
              single-layer approach is considered to be computationally         nl  dsρl                 dsSr
                                                þ ˉwls  rρl þ n   þ Srr
            cheaper and thus  is more suitable for solving large-scale         ρl   dt                   dt
           boundary  values  applications.  Recently,  based on  the
                                                         vsþr  ð nSr ˉwlsÞ ¼ 0                               ð3Þ              single-layer SPH particle approach, a robust SPH compu-
              tational  framework  for  solving  transient  seepage  flow
            through anisotropic unsaturated porous media has been        na  dsρa                  dsSr
                                                             þ ð 1   Sr Þr  vs                                                 þ ˉwas rρa    n
                                                                                                         dt               fully developed (Lian et al., 2021). However, its application        ρa   dt
             to solve fully coupled fluid–solid interaction problems in
                                             þ r  ð na ˉwasÞ ¼ 0                                  ð4Þ            unsaturated soils  is not attested, and to the best of the
             authors’ knowledge, no SPH attempts to solve these fully                                                                  where and ˉwαβ ¼ vα   vβ is the relative velocity between two
            coupled problems in unsaturated soils have been reported in                                                                             phases.
             the literature until today. To address this issue, the aim of the
                                                          By enforcing the  linear relationship between  (pl) and
             current paper is to further advance the application of the
                                                                         volumetric strain of water (εvl ) and adopting an ideal gas law              single-layer SPH approach to solving complex coupled flow–                                                                                 for the rate of change of fluid and gas density, the following
            deformation problems in unsaturated porous media.                                                                           evolution equations for the pore-water and pore-air pressures
                                                                  can be obtained (Lian et al., 2021)
                                                                                           dspl   1               dsSr
        GOVERNING EQUATIONS                                                  nlˆβ   þ   nl ˉwls  rρl þ n   þ Srr  vs
                                                                                  dt     ρl                dt                        ð5Þ          Mass conservation equations
            The mass balance equation for each phase in a unit volume      þ r  ðnl ˉwlsÞ ¼ 0
             of an unsaturated soil mixture consisting of air, water and
              solid phases can be written as follows (Bui & Nguyen, 2017)                                                                                     na   1 dspa                 dsSr   na
                                                        þ ˉwas rρa    n   þ  r  vs
                   dαˉρα                                                                 ρa RT  dt                    dt    n                    ð6Þ
           þ ˉραr  vα ¼ 0                                  ð1Þ
                 dt                                       þ r  ð na ˉwas Þ ¼ 0
           where α denotes the phase component (‘s’, ‘l’ and ‘a’ will be    where ˆβ ¼ 1=Ksatl   is the compressibility of the pore fluid with
            used to denote solid, water and air phases, respectively); ˉρα ¼     Ksatl  being the bulk modulus; R is the specific gas constant for
             nαρα is the partial densities for each component, with ρα being    the dry air; and T is the temperature. To close the above
             the intrinsic mass density of each constituent; and nα is the    equations, the definition of relative velocities between water
           volume fraction of each phase and related to porosity (n) and    and solid phases (nl ˉwls) and between air and solid phases
            degree of saturation (Sr) as follows (see Fig. 1): ns ¼ 1   n,     (na ˉwas) is required. These can be achieved by considering the
                nl ¼ nSr and na ¼ n ð 1   Sr Þ; vα  is the velocity vectors of   momentum balances of the unsaturated soil mixture, which
           phase α in the mixture; and dα=dt denotes the material    are derived in the next section.
              derivative of a field quantity on phase α.

                                                      Momentum balance equations
                                                             The behaviour of unsaturated porous media is governed by
                                                                           the interaction between solid skeleton and pore fluids, each
                                          Ωa                                                                            of which is considered as a homogenised continuum that                                                                     na = n(1 – Sr)
                                                                             follows its own governing equations. Thus, the general form
                                                                            of the linear momentum balance equation for each phase
                                                              component in the three-phase mixture can be written as
                                                                             follows
                                                     Ωl
                                                                                                nl = nSr               dαvα     X
                                                                                                                       ˉρα   ¼ r  ˉσα þ ˉραb      Rαβ                      ð7Þ
                                                                                 dt
                                                                  where ˉσα ¼ nασα is the partial stresses of each phase in the
                                                                          mixture; b ¼ ½ 0  g  is the body force vector with g being the
                                           Ωs                                 gravitational acceleration; and Rαβ is the drag force vector
                                                                          ns = 1 – n        between phases α and β and takes the following form
                                                                                                        ˉραg               REV of an                                                Rαβ ¼    nα ˉwαβ  pαrnα                             ð8Þ
                  unsaturated porous       Separation of each        Homogenisation                kα
                   medium                phase                  of each phase
                                                                  where kα is the permeability coefficient matrix of phase α.
               Fig. 1. Schematic diagram of a representative element volume (REV)     By expanding equation (7) and neglecting the interaction
               of an unsaturated porous medium and its homogenisation strategies for     force between water and air phases, the relative velocities
             continuum modelling                                        between the pore fluids  (i.e. water and air) and the solid

Downloaded from http://www.emerald.com/jgeot/article-pdf/74/8/787/9585766/jgeot_21_00349.pdf by Kyushu University user on 06 May 2026

### Page 3

A COMPUTATIONALLY EFFICIENT SPH FRAMEWORK FOR UNSATURATED SOILS         789

          skeleton can be written as follows, respectively (Lian et al.,    Therefore, in this paper, in an attempt to establish the first
         2021)                                      SPH framework to describe the coupled flow–deformation in
                                                                      unsaturated porous media, the evolution of pore-air pressure
                      kl                                        dsvs                                                                  ð9Þ      is neglected (i.e. pa ¼ 0). Furthermore, it is also assumed that                  ˉwls ¼                     rpl þ ρlb    ρl
                       nlγl                   dt                              the spatial gradient of fluid density is negligible, given the
                                                                                fluid phase is incompressible, although its compressibility is
                  ka                     dsvs                            controlled by  the  water  bulk modulus  in  the  present
                ˉwas ¼       rpa þ ρab   ρa                       ð10Þ    numerical  framework.  Again,   it  is  expected  that  this
                   naγa                    dt                                                                 assumption produces a negligible influence on the numerical
           In  contrast,  the momentum  equation  for  the  entire     results.  Therefore,  the above  general  equations  for  the
         unsaturated soil mixture can be derived by summing the     transient  seepage  flow  through  deformable  unsaturated
       momentum equation for each phase and neglecting the    porous media reduce to
           relative accelerations among the solid, water and air phases,       dsh    1                            1       dsvs
          yielding                                   ¼   r   ½klr ðh þ zÞ   Srr  vs þ r   kl
                                                                            dt    ˜CSr                           g        dt
             dsvs   1          ¼ r σ þ b                                 ð11Þ                                                         ð14Þ
             dt     ρt
                                                                 where ˜CSr ¼ ðCl þ Cs Þ denotes the summation of the specific
        where σ ¼ σ′    ½ Srpl þ ð1   Sr Þpa I is the total stress tensor     storage term Cl Ksatl  ¼ γlnlˆβ and  specific moisture term
         with σ′ being the effective stress; and ρt is the total density of    Cs ð h; Sr Þ, which can be determined from a hydraulic con-
         the  mixture. The assumption  of  neglecting  the  relative     stitutive model or a soil-water characteristic curve (SWRC); z
          acceleration is expected to produce a minimal influence on      is the elevation; and h ¼ pl=γl is the water pressure head. The
         the numerical results because the fluid acceleration is usually    above seepage flow equation shows strong couplings between
       much smaller than that of the solid phase (Zienkiewicz et al.,    the fluid flow and solid deformation, which play a critical role
          1999). Furthermore,  this assumption  is  valid  for most     in modelling coupled problems in unsaturated porous media
          practical engineering applications because the permeability    such as rainfall-induced landslides. To close this seepage flow
          of unsaturated porous media is generally very low. It is also    equation, a hydraulic constitutive model is required and will be
        worth noting here that, differently from the double-layer SPH     detailed in the next section. It is noted that the superscript ‘sl’
        approach (Bui & Nguyen, 2017), which separately solves the     will be dropped in the rest of this paper to simplify the
       momentum equation for each phase to determine the motion    mathematical expressions.
          of each layer of particles, the present single-layer SPH model
          solves the motion of the solid phase using the total stress of
         the entire mixture. Therefore, to close the above equation,    Hydraulic constitutive model
        one needs to define a constitutive model for the effective     Any existing hydraulic constitutive model or SWRC can be
            stress, and this will be detailed in the subsequent section.       incorporated into the present framework. Among the many
                                                                               existing SWRC models (van Genuchten, 1980; Fredlund &
                                                                  Xing, 1994; Kosugi, 1996), the van Genuchten model  is
        Seepage flow equations in deformable unsaturated porous        perhaps the most popular one, and thus is adopted in the
        media                                                          current paper. The van Genuchten SWRC and  its corre-
         The general equations governing the unsaturated seepage    sponding permeability function are given as
         flow through deformable porous media can be obtained by
        combining the mass and momentum conservation equations,       Sr ¼ Sres þ ðSsat    Sres Þ ½1 þ ð ga j  h j Þgn gc            ð15Þ
        and this can be achieved by substituting equations (9) and
                                                                                 h                             gc i2          (10) into equations (5) and (6)
                                                            k ¼ ksat ðe ÞSgle  1    1  Se ð1=gcÞ                     ð16Þ
                 dspl   1               dsSr
                 nlˆβ   þ   nl ˉwls  rρl þ n   þ Srr  vs
                dt     ρl                dt                           where Sres  is the residual degree of saturation; Ssat  is the
                                                              ð12Þ   maximum degree of saturation; Se is the effective degree of                1                          dsvs
         þ  r   kl   rpl þ ρlb    ρl     ¼ 0                 saturation defined as Se ¼ ð Sr    Sres Þ= ð Ssat    Sres Þ; ga,  gn
                            γl                          dt                    and gc are three empirical parameters with gc ¼ ð 1   gn Þ=gn;
                                                           and ksat ð eÞ is the saturated water permeability tensor, which
             na   1  dspa                  dsSr   na                   depends on the void ratio (Oka et al., 2019)
              þ ˉwas rρa    n   þ  r  vs
             ρa RT  dt                    dt    n                                                              ð13Þ                         e   e0               1                           dsvs                               ksat ð eÞ ¼ k0sat exp                                   ð17Þ
         þ r   ka   rpa þ ρab   ρa     ¼ 0                              Ck
                     γa                           dt
                                                                where k0sat ¼ ksatδmn with m and n indicating coordinate
           Equations (12) and (13) describe the time evolutions of     directions;  e and e0 are the current and initial void ratios,
         pore-water and pore-air pressures in the unsaturated porous     respectively; and Ck  is the Kozeny–Carman  coefficient.
         media, respectively, and, in principle, can be solved using any     Finally, to close the fully coupled flow–deformation govern-
         appropriate numerical method once an appropriate hydraulic    ing equations  for unsaturated porous media, a suction-
          constitutive model is provided. Together with equation (11),    dependent constitutive model is required to link the variation
         they form the u–pa–pl formulations for the coupled flow–    of soil suctions to the shear strength of the soil, and this will
         deformation analysis in unsaturated soils. These governing    be given in the next section.
         equations can be numerically solved using appropriate time
          integration schemes to obtain the evolution of air and water
          pressures as well as the solid motion in the unsaturated soil   A suction-dependent elastic–plastic constitutive model
         mixture. Nevertheless, for many practical engineering appli-     Any existing advanced elastic–plastic constitutive model
          cations, the pore-air pressure usually remains constant or can     for unsaturated soils (Alonso, 1991, 2021; Gens & Alonso,
        be treated as a prescribed function (Sheng et  al., 2003).    1992; Wheeler & Sivakumar, 1995; Khalili & Loret, 2001;

Downloaded from http://www.emerald.com/jgeot/article-pdf/74/8/787/9585766/jgeot_21_00349.pdf by Kyushu University user on 06 May 2026

### Page 4

790                         LIAN, BUI, NGUYEN, ZHAO AND HAQUE
           Sheng et  al., 2003) can be incorporated into the above    where De is the elastic stiffness tensor; dε  is the total strain
            numerical framework  to  describe  the  flow–stress–strain    increment tensor; and d˙ω is the spin increment tensor. It is
               relations. In this paper, in an attempt to establish the first    noted in the above stress–strain relation that the Jaumann
              single-layer SPH framework  for  solving coupled  flow–     stress rate has been adopted to maintain the objectivity of the
            deformation of unsaturated soils involving large deformation     constitutive relation. The selection of the Jaumann stress rate,
          and failure behaviour, a simple suction-dependent elastic–   among several others (e.g. the Truesdell stress rate and the
              plastic Drucker–Prager (DP) softening model is considered.    Green–Naghdi stress rate) in the literature is mainly for ease
          The effective stress of this model is defined as follows           of numerical implementation. Nevertheless, it is important to
                                                                       note that the Jaumann stress rate should only be used for
                σ′ ¼ σ þ SrplI                                     ð18Þ                                                                           simulations involving a small time increment or a small
           where I is the unit tensor, and the contribution of the pore air    deformation/rotation within a given time  interval. This
             to the effective stress has been neglected. The yield function    condition is usually satisfied in SPH because of the restriction
            defined in terms of the effective stress is written as follows      of the Courant–Friedrichs–Lewy (CFL) condition required
           p ﬃﬃﬃﬃ                                             to  integrate  the dynamic  governing  equations  (Bui &
                    f ¼ ξϕI1 þ   J2   κc                               ð19Þ    Nguyen, 2021), and the position of particles  is updated
                                                                                    after every time step. A more rigorous treatment to deal with
           where I1 and J2 are the first and second invariants of the     large deformation problems can be achieved by adopting the
              effective  stress  tensor;  ξϕ and  κc  are DP  constitutive     finite elastoplasticity theory (Chen & Mizuno, 1990; Song &
            parameters related to the friction (ϕ) and cohesion (c) of    Borja, 2014; Fávero Neto et al., 2020), the implementation of
             the soil. Under the plane strain condition, these parameters    which is outside the scope of this study.
             are defined by                                        The plastic strain increment tensor (dεp) can be defined by
                        tan ϕ                                             3c                                                                               @g0                                         κc ¼ qﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃ               ξϕ ¼ q ﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃ                                                                                                                               ð28Þ                                                                 ð20Þ      dεp ¼ dλ
                    9 þ 12 tan ϕ2         9 þ 12 tan ϕ2                           @σ′
                                                                  where dλ is the plastic multiplier and g is the plastic potential
            To describe the evolution of the yield surface with respect     function, which takes the following form
             to the soil suction, the strength parameters can be redefined        p ﬃﬃﬃﬃ
             as follows                                                         g0 ¼ ξψI1 þ   J2                                   ð29Þ
            ϕ ¼ ϕ′ þ ϕs                                        ð21Þ    where ξψ takes the same form as that of ξϕ with the friction
                                                                         angle ϕ being replaced by the dilatancy angle ψ. In addition,
               c ¼ c′ þ cs                                         ð22Þ    to properly describe the shearing behaviour of soils at the
                                                                            ultimate shearing stage or critical state (i.e. no volumetric           where ϕ′ and c′ are the effective friction angle and cohesion,
                                                                         change), the dilatancy angle ψ can be formulated as follows
              respectively; while ϕs and cs represent additional friction and                                                               (Nguyen et al., 2020)
            cohesion strengths gained due to the effect of suction when
               soils are under unsaturated conditions.
                                                       ψ ¼ ψ0 exp    sfεeqp                                  ð30Þ              In the absence of suction strength, large deformation of
               soils can cause localised failure and a strength-softening
                                                                    where ψ0  is the initial dilation angle and  sf  is a constant              process. To capture this behaviour, the following strength-
                                                                                controlling  the  rate  of  dilatancy  reduction. The  above
             softening laws for effective friction and cohesion are adopted
                                                                                   constitutive model can be integrated using the semi-implicit
            (Zabala & Alonso, 2011)
                                                                       time integration scheme (Bui & Nguyen, 2021). Readers are
                                                                                  referred to Appendix 1 for the detailed derivation of some
                 ϕ′ ¼ ϕr þ  ϕp   ϕr  exp    ηεeqp                      ð23Þ                                                                                     essential equations required for the stress update of this model.

                    c′ ¼ cr þ  cp    cr exp    ηεeqp                        ð24Þ                                                  SPH DISCRETISATIONS OF GOVERNING
                                                 EQUATIONS           where the subscripts ‘p’ and ‘r’ denote the peak and residual
                                                             Key SPH formulations              effective strengths of the soil, respectively; η is the softening
                                                                         In SPH, a continuum computation domain is discretised              coefficient controlling the rate of shear strength degradation
                                                                               into a finite number of particles, each of which carries field            with the accumulated equivalent  plastic  strain  (εeqp ). In
                                                                                 variables such as mass, density, velocity and pressure (Bui              contrast,  under  unsaturated  conditions,  the  suction-
                                                                                      et al., 2008a). These variables and their spatial gradients at a           dependent friction ϕs and cohesion cs can be written as
                                                                           given particle are calculated through an interpolation process             follows (Yerro et al., 2015)
                                                                           using  information from  its surrounding  particles and a
                             ps                                             weighted kernel function. Consider an arbitrary field function
                                                                 ð25Þ                ϕs ¼ A′                                                                                                     f ðx Þ at any point x in the computational domain, the SPH                          patm
                                                                      approximation of this function can be written as follows
                                               ps                                                                 ð26Þ     XN                   cs ¼ cmax 1  exp   B′
                                          patm                                      h f ðxi Þ i ¼    Vjf  xj W  xi    xj; hsml                ð31Þ
                                                                                                        j¼1
           where A′ and B′ are coefficients controlling the rate of
             variation of friction and cohesion with suction; cmax is the    where the angle bracket hi indicates the kernel approximation
         maximum cohesion caused by suction; patm and ps are the    operator;  Vj   is  the  volume  occupied  by  particle   j;
            atmospheric pressure and matrix suction, respectively.     W  xi    xj; hsml   is a symmetric smoothed (or kernel) func-
            The effective stress–strain relationship can be now written     tion; and hsml is a characteristic length, defining an effective
             as follows                                           domain Ω of the smoothing function W. Among several
                                                                     popular  kernel  functions  reported   in  the   literature
              dσ′ ¼ De : ð dε   dεp Þ  d ˙ω  σ′ þ σ′ d ˙ω           ð27Þ    (Monaghan, 1985; Bui & Nguyen, 2021), the Wendland C2

Downloaded from http://www.emerald.com/jgeot/article-pdf/74/8/787/9585766/jgeot_21_00349.pdf by Kyushu University user on 06 May 2026

### Page 5

A COMPUTATIONALLY EFFICIENT SPH FRAMEWORK FOR UNSATURATED SOILS         791
          kernel function  is adopted in this paper, which takes the    where vsji ¼ vsj   vsi  is the  relative velocity between two
         following form                                                        particles. Once the porosity is determined from the above
               (                                           equation, the variation of saturated permeability and the
                                 ð 1  0 5q Þ4 ð2q þ 1 Þ  0   q   2             specific moisture term can be updated.
     W ð q; hsml Þ ¼ αd                                    ð32Þ
                          0                 q . 2                    Similarly, the SPH approximation for the seepage flow
                                                                    equation can be obtained by applying equations (32) and (33)
        where αd  is the dimensional normalising factor defined    to discretise the spatial gradient terms in equation (14),
        by αd ¼  5=8h; 7=4πh2; 21=16πh3  for one, two and three    leading  to  the  following SPH  approximation  for  the
         dimensions, respectively; q is the normalised distance defined    evolution of the water pressure head
         as q ¼  xi    xj =hsml; and hsml ¼ 1 3d0  is chosen for this           2
                                                                      N                                                                                             N                           X          kernel                                                                          1                function with d0 being the initial spacing between        dhi                                                                                              @Hi X                                                          4                                              ¼                                                                                        Vj ˉk mnHji   jiDmn ˜Fij   kmni                                                                                                                                Vjrm′ji Dmn ˜Fij           particles.                                                                                                                        @rm′                                                                               dt                                                                                                     ˜CSr                                                                                                     j¼1                                                                                                                                        j¼1        SPH approximations for the first-order and second-order                                                                                         3
          gradients                   of function                                  be                                        obtained                                           by applying                                                            Taylor                                        f ð xi Þ can                          XN                                                                                           1 XN                                                                                                                dvsj   dvsi                                                   f           series               expansion                          of function                                     Among several                                               xj                                        about xi.                                                                                                                 riWij˜   5                                                                                                         Vj ˉk mnji                                                                                       Vjvsji riWij˜   þ                                                                                         Sir                                                                                           g            dt    dt         formulations reported in the literature (Bui & Nguyen, 2021;                    j¼1                  j¼1
        Lian et al., 2021), the following corrected SPH formulation for
                                                                                                                                 ð36Þ
          the first-order gradient of f ðxi Þ is adopted
                                                                                                                                                                                       ji
                                                                where ˉk mn ¼ ðkimn þ kjmnÞ=2 is the arithmetical mean value of      XN
             r˜ fi       Vj   fj     fi r˜ iWij  and  r˜ iWij ¼ Lij  riWij      water permeability, and Hi ¼ ðhi þ ziÞ  is the  total water
                                                                          pressure head.                       j¼1
                                                                                 Finally, once the water pressure head (h) is determined, the
                                                              ð33Þ    degree of saturation, pore-water pressure and total stress can
                    h                      i  1                    be determined. This information can be subsequently used to            PN        where Lij ¼     j¼1 Vj xj    xi mrni Wij      is the normalised    update the motion of solid particles by solving the momen-
          matrix; m and n indicate the coordinate direction with   tum equation equation (11), which can also be converted into
         repeated indices implying summation.                          the SPH approximation form as follows
                                                       !          There also exist, however, several robust SPH formulations                         XN
          for the approximation of the second-order derivatives of a        dvs ¼    mj  σj þ σi  riWij þ Cij þ b          ð37Þ
         function (Cleary & Monaghan, 1999; Chen & Beraun, 2000;         dt     I    j¼1     ρ2j   ρ2i
        Español & Revenga, 2003; Bui & Nguyen, 2021; Lian et al.,
          2021). In this work, the general SPH approximation for the    where Cij  is a  stabilisation term, which consists of the
         second-order derivatives, which was recently proposed by the     artificial viscosity, artificial stress and damping force, utilised
         authors and achieved excellent accuracy for highly disor-    to remove the stress fluctuation and tensile instability in SPH.
         dered particle systems, is adopted and takes the form of (Lian    Readers are referred to previous works (Bui et al., 2008b,
           et al., 2021)                                                 2011; Nguyen et al., 2017; Bui & Nguyen, 2021) for detailed
                                                                      formulations and selections of required parameters for these
                 @2fi  XN                          @fi XN                    terms.
           ¼    Vj   fj     fi Dmn ˜F ij            Vjrm′ji Dmn ˜F ij          @xm@xn                            @rm′                           j¼1                             j¼1

                                                              ð34Þ
                                                          Time integration
        where  Dmn ¼ 4ðrmjirnji= r ji 2Þ   δmn  with  δmn  being  the      In this study, the leap-frog (LF) algorithm  is used to
        Kronecker delta function;  ˜F ij ¼ ðr ji= r ji 2Þ  ˜riWij  is the     integrate the SPH approximation equations developed in the
          scalar part of the normalised kernel gradient with r ji ¼    preceding section. In this approach, the state variables (ϒ),
           xj    xi  being  the  distance  vector; and  @f =@rm′  is  the    including porosity (n), water pressure head (h), effective stress
           first-order spatial gradient calculated from equation (33).     (σ′) and velocity (v), are updated at the mid-step in time,
            It is noted that equation (34) shares a similar form to that    while the displacement vector is updated at the full timestep
         proposed by Español & Revenga (2003), except the last    as follows
        term on the right-hand side of the equation, which results                                                                      dϒ
        from the Taylor  series expansion and helps to remove        ϒtþΔt=2 ¼ ϒt  Δt=2 þ Δt
                                                                                                   dt    t                      ð38Þ         approximation errors caused by particle distortion (Lian
           et al., 2021). In this work, equations (31), (33) and (34) are        xstþΔt ¼xst þ Δt  ð vs ÞtþΔt=2
        adopted to approximate the governing equations for the
         coupled seepage–deformation framework in the next section.     The  stability  of  the LF  time  integration scheme  is
                                                                  maintained by the CFL condition. For the mechanical
                                                                             calculation, the timestep is restricted by

      SPH discretisation of the governing equations                                      hsml
         The mass balance equation for the solid phase in the       Δts   CCFL                                        ð39Þ                                                                                                        csp
         unsaturated soil mixture governs the variation of the solid
         void fraction and thus the porosity. To solve this equation,    where CCFL is a constant,p ﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃ which is taken to be 0·1 throughout
        one needs to convert it into the SPH approximation form,     this paper; csp ¼   Es=ρs is the speed of sound in the solid
        which can be achieved by applying equation (33) to the    phase with Es being Young’s modulus of the solid phase.
         divergence term in equation (2), leading to the following SPH      In contrast, for the hydraulic calculation of the seepage
         approximation for the porosity                                    flow, the timestep is restricted by the following condition
                                                                    (Lian et al., 2021)
             dni XN
         ¼                     Vj 1    nj vsji ˜riWij                       ð35Þ                                                                                                ˜CSrh2sml             dt                                                                                                                            ð40Þ                      j¼1                                                                                    Δtl   CCFL
                                                                                                              ksat

Downloaded from http://www.emerald.com/jgeot/article-pdf/74/8/787/9585766/jgeot_21_00349.pdf by Kyushu University user on 06 May 2026

### Page 6

792                         LIAN, BUI, NGUYEN, ZHAO AND HAQUE
               Therefore, the overall timestep required for both analyses is    undergoes large  plastic shear deformation,  εpeq  increases,
                                                                        causing ΔtDl  to reduce. During this process, there is a gradual              Δt  min ð Δts; Δtl Þ                                 ð41Þ                                                                                 transition from the loosely coupled scheme to the  fully
                                                                     coupled scheme, as shown in Fig. 2, where ΔtDl  gradually            The issue associated with the condition represented by
                                                                     approaches Δts as F reduces to 1. To be more specific, for a            equation (41) is that the mechanical timestep Δts  is often
                                                                           general case where ΔtDl     Δts and within a single SPH              several orders of magnitudes smaller than the hydraulic
                                                                     computational cycle of ΔtDl , the mechanical variables are             timestep Δtl. Thus, if one adopts Δts for a coupled analysis of
                                                                       only updated once after each ΔtDl  using the timestep Δts. All           a long-term diffusive process, an extremely high compu-
                                                                     mechanical parameters are subsequently kept unchanged              tational cost would be required and, in many cases, this is not
                                                                       during the rest of ΔtDl . This process is then repeated for the             necessarily essential when the deformation of the solid phase
                                                                          next increment of ΔtDl , in which the updated mechanical                 is negligible. To address this problem, an adaptive two-
                                                                      parameters obtained from the previous ΔtDl  increment are             timestep  coupling  technique  is  proposed and  will  be
                                                                       passed to the next ΔtDl  increment (i.e. beginning of the next            presented in the next section.
                                                                         increment) to update hydraulic variables.
                                                             The  above  adaptive  timestepping  technique  offers a
                                                                            superior way to balance the accuracy and computational
         An adaptive timestepping scheme for coupled flow–                                                                               cost for SPH simulations with coupled flow–deformation
            deformation analysis                                                                         problems. The suitability of this approach will be investigated
           As discussed in the preceding section, to reduce the overall                                                           when   applying   this   technique   for   studying   the
            computational cost required for coupled analysis of long-                                                                              rainfall-induced slope failure experiment.
           term  diffusive problems, such  as  rainfall-induced  slope
              failure or seepage flow through low-permeability materials,
           an adaptive timestepping scheme is proposed to enable the
                                                    VERIFICATIONS AND APPLICATIONS
            use of different timestep sizes for mechanical and hydraulic
                                                                              Terzaghi’s consolidation problem
             analyses. Fig. 2 shows a schematic diagram of the proposed
                                                             The proposed SPH framework is first validated against the
            time integration scheme. The mechanical timestep (Δts) will                                                                      one-dimensional Terzhaghi consolidation problem, whose
                strictly follow condition (39) and  is used to update the
                                                                                 theoretical solutions are available (see Appendix 2). In this
            mechanical  variables such as  effective  stresses and  soil
                                                                                                test, a fully saturated soil column 1·0 m high and 0·1 m wide
             displacements. However, depending on the magnitude of
                                                                                                     is modelled using 1000 particles with an  initial spacing
            deformation, fully coupled or loosely coupled schemes can
                                                                             distance of 0·01 m, as shown in Fig. 3(a). The boundary
           be adopted. In particular, when the soil undergoes large
                                                                           conditions are set to be smooth on both sides and fully fixed
            deformation, to describe properly the coupled flow–defor-
                                                                                    at the bottom (Bui et al., 2008a). The soil is modelled by an
           mation behaviour, the fully coupled scheme is adopted and
                                                                                 isotropic linear elastic material, whose properties are listed in
               this requires Δtl ¼ Δts, which strictly satisfies the condition                                                                        Table 1. Initially, the effective stress and excess pore-water
              (41).  In  contrast, when  the  soil  undergoes  negligible
                                                                             pressure are set to zero, while the gravity is disregarded in this
            deformation, the loosely coupled scheme can be adopted
                                                                                   case. The consolidation test is conducted in two stages –
          and the timestep Δtl required for the hydraulic computation                                                                       namely, the loading state and the dissipation stage. During
            could be defined as follows
                                                                           the loading stage, a ramp load was applied to the upper
                                         ˜CSrhsmlcsp                               surface (see Fig. 3(b)) by imposing the following vertical
             ΔtDl ¼ FΔts ¼ max           expð  DεpeqÞ; 1  Δts   ð42Þ     acceleration to the top surface particles                                                ksat
                                         8
                                                                                                 q0            t
           where  εpeq  is  the  accumulated  equivalent  plastic  shear      >><                                   t   tL                                                                      dx ½ð 1  n ÞρS þ nρl tL
              strain for the entire computation (see Appendix 1); D is a       ay ¼                                              ð43Þ
            parameter governing the rate of change of the adaptive      >>:            q0                t . tL
             hydraulic  timestep  or how  fast  the adapting  hydraulic              dx ½ ð1  n ÞρS þ nρl
             timestep   is  approaching  the  mechanical  one;  F ¼
            maxfðΔtl=ΔtsÞ expð  DεpeqÞ; 1g   defines   the  maximum    where dx is the particle spacing distance; q0 ¼ 10 kPa is the
                                                                         surcharge load; t is the computational time; and tL ¼ 0 01 s is          number of increments that the fluid timestep can be increased
                                                                           the  loading  time.  Furthermore,  to  suppress  the  stress           from the solid timestep.
                                                                               fluctuation caused by the applied load, a damping force             Equation (42) indicates that the accumulated equivalent
                                                                       with the non-dimensional damping coefficient ξ ¼ 0 04 is              plastic shear strain plays a crucial role in controlling the
                                                                   adopted (Bui & Fukagawa, 2013). During the loading stage,            adaptive  hydraulic  timestep. When  the  soil  undergoes
              negligible  plastic  shear  deformation   (i.e.  εpeq    0),  the     all boundaries are kept impervious to ensure no pressure
                                                                                  dissipation. The development  of  the  excess  pore-water             influence of soil deformation on the seepage flow is also
              negligible. Thus, the adaptive hydraulic timestep ΔtDl reaches    pressure is illustrated in Fig. 3(c), which indicates that all
                                                                           the applied load  is transferred to the excess pore-water                 its maximum value set by condition (40). However, as the soil
                                                                             pressure at the end of the loading process. Thereafter, a
                                                                        drainage condition (i.e. pl ¼ 0) is imposed on the top surface
                                                                            to trigger the dissipation process.                                                                                         Δtl               Seepage flow
                                                                         Figure 4 shows a comparison between the SPH and                          Fully coupled     t0
                                                                                 theoretical solutions for the variation of excess pore-water                                                               t1      t2      t3                                                                          Δts                 Mechanics
                                                                             pressure within  the  soil column during  the  dissipation
                 F = 1    F > 1              ΔtlD = FΔts                                      process. It can be seen that an excellent agreement between
                                                                        Seepage flow       the proposed SPH model and theoretical solutions was
                                                 Δts
                     Loosely coupled    tk                                tk + 1                             achieved. Along with the pore-water pressure dissipation, the                                                                                                                          tk + 2
                                                                               Mechanics       development of effective stress within the soil column, as
                                                             shown in Fig. 5, at three particular locations, also matches
               Fig. 2. Schematic diagram of the adaptive two-timestep scheme for     well with the analytical solutions. Furthermore, the surface
               the coupled flow–deformation analysis                              settlement predicted by the newly developed coupled SPH

Downloaded from http://www.emerald.com/jgeot/article-pdf/74/8/787/9585766/jgeot_21_00349.pdf by Kyushu University user on 06 May 2026

### Page 7

A COMPUTATIONALLY EFFICIENT SPH FRAMEWORK FOR UNSATURATED SOILS         793

                                                                                                                                                                                                            t = 0·00025 s
                                q0 = 10 kPa               q                                      1·0

                                      Permeable
                                                        pl = 0 kPa                   q0 = 10 kPa                 0·8
                                                                                                    tL = 0·01 s
               m                           q0                                     0·6  0·00125 s
               1                              m
               =                                                           z:            0·0025 s  0·005 s  0·0075 s   0·01 s
               L         pl = σ' = 0 kPa                                              0·4
                                                                                  Dissipation
                                                                                 applied
                                                                                                   0·2

                                                                                       0
                                      Impermeable                          tL                                t        0     2     4     6     8    10
                                                                                                              p1excess: kPa
                                          (a)                                              (b)                                                  (c)

           Fig. 3. Model test of one-dimensional consolidation: (a) geometryand boundary conditions; (b) ramp load applied on the soil column; (c) evolution
           of the excess pore-water pressure

          Table 1. Soil parameters used in the one-dimensional consolidation          0
           simulation
                                                                                                  SPH z = 0·8 m

           Parameter                                        Value               2                               SPH z = 0·5 m

            Soil density, ρs: kg=m3                           2000                                             SPH z = 0 m
          Water density, ρl: kg=m3                          1000                4
           Young’s modulus, Es: kPa                        2 0   104              kPa                                                     Analytical
            Poisson’s ratio, ν                                      0·3
          Water permeability, ksat: m/s                      2  10  4                                   stress:  6
           Equivalent elastic coefficient of water, Ksatl  =n: kPa    2 5   106
          Bulk modulus of solid grain, KS: kPa              1   1020             Porosity, n                                          0·40                                                                 Effective  8
         Damping coefficient, ξ                              0·04
         Kozeny–Carman coefficient, Ck                   10

                                                                                 10

                 1·0
                                                SPH                  12
                                                                                    0             0·5            1·0            1·5            2·0
                 0·9                                                      Analytical
                                                                                                                           Tv

                 0·8
                                                                                 Tv = 0·01          Fig. 5. Evolution of the effective stress at various elevations

                 0·7
                                                                    0·05

                 0·6                                                   Modelling rainfall-induced slope failure experiment       m
                                                           0·10                      Case description and model set-up.  The case studied here
                 0·5                                                                           is inspired by a large-scale rainfall-induced slope failure
                                                                   experiment previously reported by Danjo et al. (2012, 2013,                                                                    Elevation:                                0·25
                 0·4                                                        2015). Fig. 7 outlines the experimental set-up and testing
                                                                                       results. A shallow slope 4·0 m wide, 5·0 m high and 7·0 m
                 0·3               0·50                                       long was constructed on a non-deformable steel frame, as
                             1                                      shown in Fig. 7(a). The main body of this model slope was
                 0·2    2·0                                      made of unsaturated Masa sand (i.e. aweathered granite soil)
                                                           and formed a slope angle of 40° to the horizontal surface
                 0·1                                                (Danjo  et  al., 2012, 2013, 2015). Six tensiometers were
                                                                                installed at depths of 0·15 m, 0·45 m and 0·85 m in the lower
                 0                                              and middle sections of the  slope, marked by diamond
                  0        2        4        6        8        10
                                                                symbols in Fig. 7(c), to measure the evolution of pore-water
                                Excess pore-water pressure: kPa                   pressure within the slope. Several water gauges were also
                                                                                installed at the bottom to measure the increase in ground-
           Fig. 4. Evolution of the excess pore-water pressure
                                                                     water caused by rainfall infiltrated water. Furthermore, to
                                                               measure  the  surface  displacement  of  the  slope,  three
                                                                    displacement  gauges  were  also  installed on  the  slope
        model again showed excellent agreement with the analytical     surface, marked by the  triangular symbol  in  Fig.  7(c)
          solution, as illustrated in Fig. 6. These excellent agreements    (Danjo et al., 2012). To simulate the rainfall condition, an
         suggest that the proposed SPH framework could capture well     artificial rainfall machine was used to generate water flux on
         the coupled behaviour of saturated soils and is ready for more    the slope surface until the slope failure occurred. After the
        complex coupled hydro-mechanical problems, which will be    slope collapse, a three-dimensional (3D) laser scanner was
         presented in the next section.                               used  to  obtain  the  surface  morphology  and   final

Downloaded from http://www.emerald.com/jgeot/article-pdf/74/8/787/9585766/jgeot_21_00349.pdf by Kyushu University user on 06 May 2026

### Page 8

794                         LIAN, BUI, NGUYEN, ZHAO AND HAQUE

             configuration of the slope, which are presented in Figs 7(b)     virtual particles with either the fully fixed or the free-slip
          and 7(d), respectively. All other relevant experimental data    boundary (see Fig. 8(a)). Both types of boundaries can be
            were reported in Danjo et al. (2012, 2013, 2015) and are used    modelled using the standard approaches reported in Bui et al.
             to assess the performance of the proposed coupled SPH    (2008a). All hydraulic boundary conditions are modelled
           model and will be presented later, together with the authors’    following the work recently proposed by the authors (Lian
             predicted results.                                                     et al., 2021). It is noted that, although a drainage layer was
              In total, 5911 particles with an initial spatial distancing of     installed at the slope base in the experiment (Fig. 7(c)), the
            0·04 m are used to generate the above slope model, as shown    water gauges installed at A and B recorded a small amount of
              in Fig. 8(a). The rigid frame is modelled using five layers of    water accumulation. To reflect this condition in the exper-
                                                                          iment, an experimentally calibrated ‘ponding’ condition of
                                                                                               pl   0 25 kPa is imposed at the slope base. In addition, a
                    0                                                        prescribed negative pore-water pressure ranging from  2·75
                                                   SPH             to  2·95 kPa is linearly distributed along the slope elevation
                                                                                 Analytical         to generate an initially unsaturated soil condition, reflecting                     0·5
                                                                           the initial suction values measured at tensiometers. Before
                                                                           the water infiltration  is applied, an  initial  stress  field  is
                     1·0                                                    obtained by applying gravitational load to the slope model,
                             10–4                                                           as shown  in  Fig.  8(b).  Thereafter, a constant  negative
        ×
                     1·5                                                      pore-water  pressure  of   0·715 kPa   (i.e.  experimentally         m
                                                                        recorded values from tensiometers) is imposed on the slope
                     2·0                                                         surface to model the rainfall infiltration and is maintained on
                                                                           the ground surface during the entire computational process.                                                                                              settlement:
                                                          Owing to hydraulic gradient differences, a rainfall-induced
                     2·5
                                                                                       infiltrated seepage flow is achieved in the slope.                                                            Surface                                                          In contrast, the mechanical parameters of the soil slope
                     3·0                                                   were not reported in the series of studies by Danjo et al.
                                                                            (2012,  2013,  2015).  Therefore,  these  parameters  were
                     3·5                                                         extracted from the literature data reported on Masa soil
                                                                     (Kansai area, Japan) and are summarised in Table 2, some of
                     4·0                                                 which are calibrated for the suction-dependent elastoplastic
                      0             0·5            1·0            1·5            2·0   DP  softening model. In  addition, to  describe  the  link
                                                    Tv                          between suction and degree of saturation, three well-known
                                                                                          soil water retention curves (SWRCs) (van Genuchten, 1980;
               Fig. 6. Evolution of the surface settlement                        Fredlund & Xing, 1994; Kosugi, 1996) are considered in this

                             Before test                             After test                                                  0·5 m

                                                                         (a)                                                                               (b)

                                                  Upper

                                                                                      1·5
                                                   Middle    1·091
                                                                                                                                   1·0                                                   0·74 m
                                                          1·557(3)          F                                                                                                                                                 0·85
                                                   E     1·556                                         7·8     (2)          0·45
                           Lower     3·112                                                            Final configuration
                      Drained layer             D     1·556    Undrained layer (mortar)
                                                                                                                                                                                                 Initial configuration
                                             (1)          0·15 C     1·556            TensiometerMoisture sensor                             2·04
                                                            Water gauge
                         A    B     1·556 40°                Displacement gauge

                                       0·8
                                   1·6                                                           1·03 m

                                                               (c)                                                                                (d)

               Fig. 7. Slope configuration in the experiment: (a) view of the slope before and after the infiltration test; (b) 3D scanned data of the final
               configuration; (c) schematic diagram of the experimental set-up; (d) scanned configurations of the slope before and after failure (after Danjo et al.,
             2012)

Downloaded from http://www.emerald.com/jgeot/article-pdf/74/8/787/9585766/jgeot_21_00349.pdf by Kyushu University user on 06 May 2026

### Page 9

A COMPUTATIONALLY EFFICIENT SPH FRAMEWORK FOR UNSATURATED SOILS         795

                                                                   Free-slip boundary                 1·0

                                                       Infiltration boundary
                                                                                              0·8

                                                       MNo. 15
                                                                45
                                                                85        E Undrained solid               0·6          Fredlund & Xing (1994)                                                           boundary                                                                                    saturation              Kosugi (1996)
                                                    D                                of                                                                                                van                                                                                                  Genuchten                                                                                                                         (1980)
                                           BNo. 15                                                          Water level                    0·4             Drained solid boundary                                                45                                                                                                          Experimental                                                                                                                      data                                                85                       Suction                                                          Degree             Danjo et al. (2012)

                                                            Displacement                  0·2                                    Gauge A   B
                                                          (a)

                         Initial vertical total stress distribution       Upper                            0
                                                                                               10–3       10–2       10–1        100        101        102
                                                Middle
                                                                                                                                 Suction: kPa
                           Displacement
                                                                                                                                                     (a)
                           monitoring points                               0

                                                                                              2·0
                                                                   –5
                              Lower                                                                                           Fredlund & Xing (1994)
                                                                   –10               10–4                                      Kosugi (1996)
                                           ×  1·5
                                                                            σv: kPa    –15                                              van Genuchten (1980)
                                                                                                                                   m/s
                                                          (b)

                                                                                              1·0
           Fig.  8. Model  set-up:  (a)  the  initial  particle  configuration and
         boundary conditions of the SPH model; (b) initial in situ vertical            total stress distribution in the slope model                                                                                                                                                                                                                              permeability:

                                                                                              0·5                                                                                                                                                                                                                          Water

          Table  2. Material  parameters  for  rainfall-induced  slope  failure
           simulations
                                                                                   0
                                                                                               10–3       10–2       10–1        100        101        102
           Parameter                                       Value
                                                                                                                                 Suction: kPa
           Saturated residual cohesion, cr: kPa                  3·10                                                            (b)
           Saturated peak cohesion, c0: kPa                     4·15
                                                                                      Fig. 9. Hydraulic constitutive models adopted in the calculation:           Saturated residual friction angle, ϕr: degrees         16·5
                                                                                            (a)  fitting  of  soil  water  characteristic  curves (SWCCs)  to  the           Saturated peak friction angle, ϕ0: degrees            22·5
                                                                               experimental data; (b) water permeability curves              Initial dilation angle, ψ0: degrees                  5
            Scale factor for dilation angle, sf                  25
           Softening coefficient, η                           5
           Suction-dependent friction angle, ϕs: degrees       10              characteristics of seepage  flow,  in which the horizontal
           Suction-dependent cohesion, cmax: kPa            15            seepage  is expected to be larger than the  vertical one,
           Suction hardening factor, A′                          2·5             this study assumes that kx ¼ 1 2ksat and ky ¼ 0 8ksat. These
           Suction hardening factor, B′                      8            parameters are again calibrated to best fit the experimental
          Atmospheric pressure, patm: kPa                 101             data. Finally,  it  is noted that this rainfall-induced slope
           Young’s modulus, Es: kPa                             2·0  103                                                                                 failure simulation involved a long-term seepage infiltration
           Equivalent elastic coefficient of water,                 6·4  102
                                                                        process  (i.e. 167 min), but the slope failure process only
               Ksatl  =n: kPa                                                                             lasted a few seconds (Danjo et al., 2012, 2013, 2015). Thus, if          Bulk modulus of solid grain, KS: kPa             1   1020
             Porosity, n                                         0·382        a minimum timestep size satisfying condition (41) is applied,
            Poisson’s ratio, ν                                    0·33               it would take a few days to model such a long physical test.
            Soil density, ρs: kg=m3                        1773          To address this issue, the proposed adaptive timestepping
          Water density, ρl: kg=m3                       1000              integration scheme is adopted. The mechanical timestep is
           Residual saturation, Smin                             0·02           Δts ¼ 0 0003 s, while the maximum hydraulic timestep  is
        Maximum saturation, Smax                                                              0·985           Δtl ¼ 0 05 s, corresponding to a controlling parameter of                                             1
       SWRC parameter, ga: m                             6·24      D ¼ 5. Finally,  it  is worth noting that, to accelerate the
       SWRC parameter, gn                                2·15                                                                  computational speed, the water bulk modulus used in this
       SWRC parameter, gl                                3·25
                                                                       simulation has been deliberately reduced, and this enables the         Kozeny–Carman coefficient, Ck                   2
           Saturated water permeability, ksat: m/s           1 145  10  4      adoption of a larger hydraulic timestep according to the CFL
                                                                      condition (40). The authors have tested their simulations for
                                                                             larger values of the water bulk modulus and did not find any
                                                                               significant difference in the numerical results.
          study, as shown in Fig. 9. The current authors’ numerical
           tests confirmed that these hydraulic  constitutive models
         provide similar  results in predicting the rainfall-induced     Qualitative analysis of slope response to rainfall.  Attention
         seepage flow behaviour. Accordingly, only results predicted      is  first  paid  to  the  predicted  rainfall-induced  seepage
        by van Genutchen’s SWRC are presented in  this study,     infiltration and progressive failure of a slope, as shown in
        and the corresponding hydraulic constitutive parameters are    Fig. 10. The imposed rainfall, in the form of constant water
           listed in Table 2. Furthermore, to reflect the anisotropic     pressure, on the ground surface causes water flux to infiltrate

Downloaded from http://www.emerald.com/jgeot/article-pdf/74/8/787/9585766/jgeot_21_00349.pdf by Kyushu University user on 06 May 2026

### Page 10

796                         LIAN, BUI, NGUYEN, ZHAO AND HAQUE

                             Elapsed time = 44·42 min                                  Elapsed time = 44·42 min

                                             Wetting front                                         Stable state
                                                                                                   without any plastic
                                                                         3                                                        0·20
                                                                                                                     strain
                                                                                                                                          0·15
                               Water
                              accumulation                                    0                                                        0·10

                                                                                                                                                              p     0·05
                                                                                                                                                     ε eq
                                                                                    p1: kPa   –3                                                  0

                             Elapsed time = 145·92 min                                 Elapsed time = 145·92 min

                                             Water                                                      Plastic strain
                                             accumulation                      3               development                             0·20

                                                                                                                                          0·15

                                                                         0                                                        0·10

                                                                                                                                                              p     0·05
                                                                                                                                                     ε eq
                                                                                    p1: kPa    –3                                                 0

                             Elapsed time = 165·51 min                                 Elapsed time = 165·51 min

                                          Fully saturated                             3                                                        0·20
                                          region                                                     Sliding surface
                                                                                                                                          0·15
                                                                    Rising
                                                               water level         0                                                        0·10

                                                                                                                                                              p     0·05
                                                                                                                                                     ε eq
                                                                                    p1: kPa    –3                                                 0

                             Elapsed time = 166·03 min                                 Elapsed time = 166·03 min
                                                                                                  Development of
                                                                                                      detachment

                                    Coupling effect
                                                                         3                                                        0·20
                                  on excess                                                   Mobilised volume
                                   pore-water pressure                                                                                       0·15

                                                                         0                                                        0·10

                                                                                                                                                               p     0·05
                                                                                                                                                      ε eq
                                                                                    p1: kPa    –3                                                                                                                             0

                             Elapsed time = 166·06 min                                 Elapsed time = 166·06 min

                                                                                           Detachment from the
                                                                                                      non-deformation soil
                                                                          3                                                          2·0

                             Seepage water                                                                                                1·5
                                          re-distribution
                                                                          0                                                          1·0

                                                                                                                                                               p      0·5
                                                                                                                                                      ε eq
                                                                                    p1: kPa    –3                                                                                                                             0

               Fig. 10. SPH predictions of the evolutions of pore-water pressure and equivalent plastic strain at different time intervals

             into the soil. As the wetting front is processing in the slope, an    to the upper part of the slope crest, forming a well-defined
             increase in the negative pore-water pressure from around     failure surface. The development of plastic strain in the slope
               3·0 kPa to   0·72 kPa is observed within the wetting zone      is attributed to the reduction of soil suction caused by the
           (T   44 41 min). During this stage, the slope deformation is     increase in the degree of saturation. From this stage onward,
              negligible and no plastic deformation occurs. This suggests    as deformation develops, the hydraulic timestep is adaptively
             that the proposed adaptive timestepping scheme has helped    reduced and eventually reaches its minimum value corre-
             to significantly reduce the overall computational cost. At    sponding to the mechanical timestep size. As the entrapped
           around 145·92 min, the seepage flow reaches the rigid frame    water content continues accumulating at the base of the slope
              at the bottom slope and is subsequently trapped, forming a    and migrates downwards to the slope toe, an elliptic fully
               fully saturated region associated with positive pore-water    saturated region is observed in the slope (see Fig. 10 with
              pressure. At the same time, the plastic strain in the slope   T = 165·51 min). At the same time, the groundwater level
               starts to develop at the slope base and gradually propagates     rises  significantly, further reducing the  soil suction and

Downloaded from http://www.emerald.com/jgeot/article-pdf/74/8/787/9585766/jgeot_21_00349.pdf by Kyushu University user on 06 May 2026

### Page 11

A COMPUTATIONALLY EFFICIENT SPH FRAMEWORK FOR UNSATURATED SOILS         797

           facilitating the slope failure process. As a result, a clear    experimental data is achieved across all monitoring points,
          localised shear band (or sliding surface) is well developed,    suggesting  that the newly developed SPH model could
         connecting the toe and the crest of the slope, indicating an    capture well the unsaturated seepage flow through deform-
          acceleration of the slope failure. Suddenly, a quick movement    able media. For example, in the middle section of the slope
          of the mobilised volume occurs and slides rapidly along the      (i.e. MNo. 15, MNo. 45 and MNo. 85), suction starts to
         non-deformable frame bottom at T = 166·03 min, leading to    decrease at MNo. 15 nearly 10 min after the rainfall begins
        a detachment of the sliding body from the intact scarp on the    and gradually reaches  its temporary equilibrium state at
        upper supporting frame. Within the shear band, it is also    around  30 min,  corresponding  to  negative  pore-water
          interesting to see how the pore-water pressure changes are    pressure around 0·715 kPa. With further progression of the
         caused by the volumetric deformation (Fig. 10). Because of    wetting  front under  gravity,  suction  at  the  other two
         the soil dilation, volumetric expansion is expected to occur as    measuring points (i.e. MNo. 45 and MNo. 85) follows the
         the soil undergoes shearing, leading to a reduction of positive    same trends; they react to the wetting process and reach their
         pore water pressure (T = 166·03 min), all of which can be well    temporary equilibrium state at further delayed times because
         captured, thanks to the proposed fully coupled SPH frame-    these monitoring points are located at deeper locations from
         work. The landslide stops at 166·06 min, but the entire    the slope surface. During the temporary equilibrium state,
          sliding process lasts for only 0·04 min, which is a significantly    the soil at all monitoring points is still under the unsaturated
         small timescale compared with that of the whole rainfall    condition, which  is evidenced by the negative pore-water
           infiltration process. Even with such a significant difference in    pressure value at all points. As the infiltration seepage flow
         the timescale, the dynamic coupling process of both seepage     continues, seepage water reaches the impervious bottom
         flow and soil deformation can still be effectively captured,    boundary and gradually accumulates, forcing a transition
         thanks to the newly proposed adapting timestepping algor-    from partially saturated to fully saturated conditions and
         ithm. To further quantitatively verify the capability of the     raising the groundwater level inside the slope. At around
         proposed fully coupled SPH framework in predicting the    150 min, this rising groundwater level is first captured at
         seepage infiltration process and the failure response of the   MNo. 85, where the suction further decreases to nearly zero
          slope, the calculated evolutions of suction, water level and      (i.e. saturated). A similar evolution of suction also can be
        ground displacement are assessed against experimental data.    seen in other measuring points installed close to the slope toe
                                                                                                       (i.e. BNo. 15, BNo. 45 and BNo. 85). It is worth noting that
                                                                           there  still  exist some noticeable differences between the
                                                                                  results predicted by SPH and those in the experiment. For
          Quantitative analysis of seepage infiltration into the slope.      example, a faster seepage flow process is observed in SPH (i.e.
         Figure 11 shows a comparison between the SPH prediction   BNo. 85 in Fig. 11(a)). This can be attributed to the existence
        and experiment for the evolution of suction due to the    of air bubbles in the pores of the soil in the experiment, which
           rainfall infiltration, captured from six monitoring points.    would delay the penetration of the seepage flow. However,
          Fairly good agreement between the predicted results and     this delay effect caused by air bubbles was not considered in
                                                                        the present study. Another possible reason could be the
                                                                        highly anisotropic and random properties of the soil in the
                 0                                                      experiment, which were not considered either in the present
                 0·5                                                    numerical model. Nevertheless, a reasonably good agreement
                                                                             in the infiltration process and water level development can be
                 1·0                                                          seen, showing the effectiveness of the proposed framework.
                    kPa 1·5                                              The predicted water  level at the base of the slope  is
                                                            compared with the experimental data and shown in Fig. 12.
                 2·0
                                                                  Again,  very good agreements with  the experiment  are                                                      Suction: 2·5                                                     achieved by the proposed SPH framework. For example, it
                 3·0                                  BNo. 15     BNo. 15         is observed in both SPH and experiment that gauges A and B
                                                    BNo. 45     BNo. 45      respond to the water level change at around 65 min and
                 3·5                                  BNo. 85     BNo. 85
                                                               100 min, respectively. After that, the water level at these
                  0    20    40    60    80   100   120   140   160        locations gradually increases and reaches an equilibrium
                                      Elapsed time: min                               state,  corresponding  to  the  ‘ponding’  condition   (i.e.
                                                         (a)                              0·25 kPa). In contrast, the water level at both gauges D
                 0                                              and E increases rapidly at around 143–145 min when the

                 0·5

                                                                                             0·5
                 1·0
                                                                                                                         Experiment    SPH
                    kPa 1·5                                                                         0·4           Gauge A       Gauge A
                 2·0                                  m 0·3           Gauge B       Gauge B
                                                                                                      Gauge D       Gauge D                                                      Suction: 2·5                                                                                                                                                                                                                                                                    level: 0·2           Gauge E       Gauge E
                 3·0                               MNo. 15    MNo. 15
                                               MNo. 45    MNo. 45                 3·5                               MNo. 85    MNo. 85                         Water 0·1

                  0    20    40    60    80   100   120   140   160               0
                                      Elapsed time: min
                                                         (b)                                        –0·1
                                                                                    0     20    40    60    80    100   120   140   160
           Fig. 11. Comparison between the SPH predicted results and the                                  Elapsed time: min
          experimental data for the evolution of the active pore-water pressure
        (PWP) at several monitoring points in (a) the middle section and     Fig. 12. Comparison between the SPH predicted results and the
            (b) the lower section of the slope                                      experimental data for the water level at the slope base

Downloaded from http://www.emerald.com/jgeot/article-pdf/74/8/787/9585766/jgeot_21_00349.pdf by Kyushu University user on 06 May 2026

### Page 12

798                         LIAN, BUI, NGUYEN, ZHAO AND HAQUE

               infiltrated water flow reaches the undrained bottom bound-    bending upward trend in the displacement curves develops,
            ary and accumulates. The predicted water level at these two     indicating that the surface displacement starts to occur as
             locations also agrees well with the experimental counterparts,    the groundwater level grows (see Fig. 12). This gradually
             suggesting that the proposed SPH framework could capture    developed displacement prior to the quick sliding of the slope
             well the transition of seepage flow from the unsaturated to    can be attributed to the increase in the soil mass caused by
               fully saturated conditions.                                       increases in the degree of saturation and rainwater accumu-
                                                                                  lation inside the soil body. The minor slope deformation
                                                                           before its collapse is also known as the precursor state of
             Quantitative analysis of the failure response of the slope.       slope failure (Moriwaki, 2001; Moriwaki et al., 2004). As the
          Ground surface displacement monitoring is one of the most    groundwater level rises, the surface movement accelerates,
            important measures in slope failure forecast and prevention    and the slope moves into a warning state with a noticeable
             systems. Therefore, it is crucial to develop a robust compu-     sliding trend. This acceleration of soil movement is mainly
              tational  approach  capable  of  correctly  predicting  this    caused by the rising water level, leading to the loss of the
             information. In this section, the evolution of the ground    suction-dependent shear strength of the soil slope. As a
            displacement  predicted by the proposed SPH model  is     result, the slope cannot maintain its stable condition and thus
             quantitatively analysed to demonstrate its applicability for    suddenly collapses at around 166 min, indicated by a rapid
             future predictions of rainfall-induced  landslides. Fig. 13    upward (non-converged) trend in the displacement curve in
           shows a comparison between the numerical prediction and    Fig. 13. The timing of slope failure (or failure state) predicted
             the experiment for the surface displacement during rainfall    by the SPH model is nearly equivalent to the experimentally
             loading. It can be seen that very good agreements between    observed counterpart. Nevertheless, the SPH model under-
             the predicted results and experimental data are achieved,    estimated the surface displacement during the warning state,
             suggesting that the proposed SPH framework could capture    and this difference could be attributed to the suitability of
             well the time-dependent deformation response of the slope     constitutive models. In  particular, the suction-dependent
            caused by rainfall infiltration. For example, the slope remains     constitutive model adopted in the current SPH framework is
              essentially stable during the  first 140 min, thanks to the     relatively simple and thus may not be able to fully capture the
             contribution of suction to the overall shear strength of the    unsaturated soil behaviour in the experiment. To address this
               soil  slope. However, from around 140 min onward, a     issue, advanced unsaturated soil constitutive models should
                                                                   be adopted, along with tests to provide sufficient data for
                                                                                calibrating and validating those models, all of which are
                    0·08                                                       outside the scope of this paper.
                                                                         Figure 14 shows the progressive deformation patterns
        m
                    0·06            Lower (test)       Lower (SPH)        Failure             caused by the rainfall infiltration, visualised through the
                                          Middle (test)        Middle (SPH)        state            deformed grids of ‘tracers’ plotted on the slope body. The
                    0·04            Upper (test)       Upper (SPH)                          entire process of the slope collapsing lasts for a short period.
                                                                        Warning            At around T = 166 min, a noticeable settlement is observed
                                                                                         state                                                                                                            displacement:  0·02                                       Precursor                 on the crest of the slope, where minor shear deformation can
                                                                                                         Sliding
                                                                               state                       also be noticed in the zoomed-in figure inset. At this stage, no
                     0                                                   deformation occurs at the lower portion of the slope. After                                                          Surface
                                                                                     that, the soil deformation progresses rapidly, and at around                                                       Stable                      Accelerating
                   –0·02                                    T = 166·03 min, the mobilised soil volume detaches from the
                       0    20   40   60   80   100  120  140  160  180     upper non-deformable scarp. At this point, severe shear
                                            Elapsed time: min                      deformation is observed along with the sliding surface. The
                                                                                   sliding mass decelerates and stops at around T = 166·05 min,
               Fig. 13. Comparison between the SPH predicted  result and the    and the predicted final failure configuration matches well
              experimental data for the surface displacement against time
                                                                       with the longitudinal cross-section of the slope obtained by

                                                                                                               Settlement first occurs

                                         Elapsed time = 0 min                                                                                       Elapsed time = 166 min

                                                                                                                   0·82 m
                                        Elapsed time = 166·03 min                                                                                      Elapsed time = 166·06 min

                                                                    Shear failure
                                               Run-off                                            Final run-off
                                             distance, ~0·5 m                                   distance, ~0·95 m

                                                                                                                 Initial configuration (experiment)
                                                                                       Final configuration (experiment)

               Fig. 14. Progressive deformation patterns of the slope predicted by SPH and its comparison against the experiment for the final failure
               configuration

Downloaded from http://www.emerald.com/jgeot/article-pdf/74/8/787/9585766/jgeot_21_00349.pdf by Kyushu University user on 06 May 2026

### Page 13

A COMPUTATIONALLY EFFICIENT SPH FRAMEWORK FOR UNSATURATED SOILS         799

         the 3D laser scanner in the experiment (Danjo et al., 2012,    the materials at these two points undergo shear strength
         2013, 2015). The final run-off distance predicted by SPH is    reduction associated with suction-induced softening. On the
         about 0·95 m, which agrees well with the reported exper-    other hand, from T1 to T3, some noticeable fluctuations are
         imental data of 1·03 m. At the same time, the  largest    observed in the stress paths, which could be attributed to
          settlement of the slope surface predicted by SPH is around    the sudden change in the soil density caused by wetting and
         0·82 m depth, which is also close to the experimental data of    the dynamic nature of SPH modelling. The slide motion
         0·74 m. Therefore,  it can be concluded that the proposed    of the slope occurs at around T3, causing a sharp decrease in
         coupled flow–deformation SPH model could predict well the    the effective shear stress at all gauges D, E and MNo. 85,
          large deformation and failure responses of an unsaturated    which indicates that the soil at these locations undergoes
           soil slope caused by rainfall infiltration.                         further softening behaviour associated with increasing plastic
                                                                      shear deformation. The effective shear stress of particles
                                                                         located within the shear band (i.e. gauges D and E) is found
                                                                        to be larger than those outside this zone (i.e. MNo. 85), as
          Stress path analysis.  The capability of the proposed model    shown in the contour plots of deviatoric stress in Fig. 15(a),
          to provide insights into stress variations inside a deformable     indicating that  particles within the shear band undergo
         unsaturated porous medium is demonstrated in this section.    higher shear deformation. The difference in the effective
       The stress at several monitoring points in Fig. 8(a), corre-    shear stress of particles located inside and outside the shear
         sponding to the locations inside (i.e. gauges D and E) and    band could also be explained by the fact that they are located
         outside  (i.e. B, MNo. 85 and BNo. 45) the shear band,     at different locations and thus are subjected to different stress
           respectively, was monitored during the simulation. The stress    loading paths and different pore-water pressure development.
         paths in the deviatoric stress and effective mean stress (p–q)    Gauges D and E share nearly the same stress path since they
         plane are plotted in Fig. 15, where the DP yield surfaces    are both located inside the shear band. The final stress state
         corresponding to different suctions are also presented in the     at all measuring points is located below the DP0 line, which
           figure. During the first 45 min of rainfall loading (i.e. from     defines the peak shear strength envelope of the soil at the
        T1 to T2), the effective mean stress at all locations increases,     fully saturated condition, and this can be attributed to the
        which can be attributed to the increase of soil mass due to    softening behaviour of soils.
          wetting. Meanwhile, the shear stress at gauges D and E is     The evolution of the stress path at BNo. 45 and gauge B
       much higher than that at MNo. 85, indicating the precursor    monitoring points located at the slope toe, in general, shows
          of shear band localisation at gauges D and E. From T2 to T3,     similar responses to the rainfall infiltration process compared
         the reduction in soil suction due to water seepage causes the    to those monitoring points on the upper portion of the slope.
         shear stress to reduce, while the mean effective stress at these    However, different from the stress at gauges D and E, the
          locations continues to increase due to the increase of soil     stress loading path at gauge B, located below the shear band,
         mass. From T3 to T4, due to the water accumulation and      is mainly characterised by increasing mean stress, which can
          positive pore-water pressure generation, the effective mean    be attributed to the increase in compression caused by the
           stress at gauges D, E and MNo. 85 starts to decrease. The     sliding mass from T3 to T5. The evolution of shear stress at
         shear stress at these locations also decreases, indicating that    gauge B also  reflects the suction-dependent and  strain-
                                                                         softening  constitutive behaviour adopted  in  the model,
                                                                    evidenced by the increase and subsequent reduction of the
                 2·0
                                          T3                            16      Gauge E                            DP6000        shear stress. Outside the shear band at the slope toe, it is
                                 MNo. 85                          12                                                                                  8                 Gauge D                       interesting to notice that the stress loading path at BNo. 45
                                                                       T2                                             E                                                                                  4                                                                                                 DP3000       monitoring point follows more or less the same loading path,                                                      kPa                 1·5               D     q:                                                                               T2                                                                                  0  T1
                                                                            T1      T3       T3                       undergoing a loading and subsequent unloading process (i.e.
                 101                                                    T4                                                            T1 to T5). Compared to the stress loading paths at gauges D
      ×                                                                  DP0
                                                                            T4                           and E, it appears that the shear stress inside the shear band                                                                 T2    T3                   kPa 1·0                            T1
                                                                                        0                                                                                             min                                                                  undergoes                                                                              continuous                                                                                           loading                                                                                                 during                                                                                                              the                                                                                                                shearing                                                                                                                            process                                                                                                             T1:
            q:                                                                                                                                     16
                                                                                                  44·4                                                                                                min                                                                                                             T2:                                                                                 T4                                                           T5       T4
                                                                                                                                     12                                                      T5                                                                                                       (i.e. from                                                                                     to close to                                                                                                 while                                                                                                         the                                                                                                         shear                                                                                                                                      stress                                                                                                                        outside                                                                                                                               the                                                                    T1                                                                                                     T4),                                                                    MNo.                                                                              85                                                                                        145                                                                                               min                 0·5                                                                                                             T3:                                                                                                                                     8
                                                                             E                            MNo. 85                                                                band                                                                             undergoes                                                                                           loading                                                                                     and                                                                                                       unloading.                                                                                                                This                                                                                                                            obser-                                                                                                165·5                                                                                                 min       shear                                                                                                                                     4                                                                                                             T4:                                                         T5
                                                                   D     q: kPa   0      T5: 166·0 min       vation of the stress loading path inside and outside the
                0                                                             localisation zone  is well supported by the double-scale
                  0            0·5            1·0            1·5            2·0      constitutive theory (Nguyen et al., 2016; Nguyen & Bui,
                                                             p': kPa × 101                         2020; Bui & Nguyen, 2021).
                                                          (a)
                 2·0                                                                     DP6000

                                                                                    16
                                         T3                                                                                    12              Gauge B                       Influence of  spatial  discretisations.  The mesh-dependent                                     BNo.                                         45
                                                       BNo. 45
                                                                                    8
                                                                                               DP3000          solution is a well-known issue of continuum-based numerical                                                                         q: kPa                                                                                                 T4                                                                                    4
                 1·5                  B              0                                methods (e.g. FEM, material point method) when incorpor-
                                                                                      T3
                                                                           ating a classical strain-softening constitutive model (Bui &                 101                                                                                 DP0      ×                                                         T2                 1·0                                      T2      T1                                  T5            Nguyen, 2021). To overcome this issue, non-local plasticity
                                                             T3     T1                                    theory   (Bažant,   1991),   gradient   plasticity   theory                   kPa
                                                                                       0                                                                                            min                                                                                                            T1:
                                                                                                                            20            q:                                                                        T4                                                                                                 44·4                                                                                               min        (Vardoulakis & Aifantis, 1991) or a double-scale constitutive                                                                                                            T2:                                                      T4                                                                                                                            15                                                                    BNo. 45
                 0·5                                                                                     10           T3: 145 min        framework (Nguyen et al., 2016; Nguyen & Bui, 2020) is
                                                        T5                                                     5            T4: 165·5 min                                                                         usually adopted to provide a means to introduce a length                                                                     B   q: kPa    0            T5: 166·0 min
                                                                             scale into the computational model, helping to scale the
                0
                  0          0·5         1·0         1·5         2·0         2·5     material responses correctly with the  size of the spatial
                                                                                 discretisation. SPH is a continuum-based numerical method                                                              p': kPa × 101
                                                           (b)                        and thus, in principle, also suffers from the spatial discretisa-
                                                                           tion dependence. However, as pointed out by Bui & Nguyen
           Fig. 15. Calculated evolution of effective stress at several monitoring     (2021), the nature of SPH kernel approximations automati-
            points: (a) MNo. 85, gauges D and E; (b) BNo. 45 and gauge B         cally introduces a length scale (i.e. the size of kernel function)

Downloaded from http://www.emerald.com/jgeot/article-pdf/74/8/787/9585766/jgeot_21_00349.pdf by Kyushu University user on 06 May 2026

### Page 14

800                         LIAN, BUI, NGUYEN, ZHAO AND HAQUE

                  Elapsed time = 165·51 min                     Elapsed time = 165·566 min                     Elapsed time = 166·380 min

                  Water                                         Water                                       Water
                  pressure                                         pressure                                       pressure
                                                          0·20                                           0·20                                          0·20

                                                          0·15                                           0·15                                          0·15

                                                          0·10                                           0·10                                          0·10

                                                          0·05                                                                                                         0·05                                                                                                                                                       0·05
                                                          ε peq                                                                                                                ε peq                                                                                                                                                                    ε peq                                                    0                                                                                               0                                                                                                                                        0

                  Elapsed time = 166·06 min                     Elapsed time = 165·955 min                     Elapsed time = 166·929 min

                                                            2·0
                                                                                                             2·0                                             2·0
                                                            1·5
                                                                                                             1·5                                             1·5
                                                            1·0
                                                                                                             1·0                                             1·0
                                                            0·5
                                                                                                             0·5                                                                                                                                                             0·5                                                          ε peq                                                    0                                            ε peq                                                                                                                                                                    ε peq                                                                                               0                                                                                                                                        0

                                           (a)                                                          (b)                                                             (c)

               Fig. 16. SPH modelling of the rainfall-induced slope failure using different spatial discretisations: (a) dx = 4 cm; (b) dx = 5 cm; (c) dx = 6 cm

             into the SPH computational model. This ‘length scale’ works          0·08
              in a similar way to that of the non-local constitutive model,
            thus helping SPH to mitigate its mesh-dependent issue when   m 0·06          Experimentdx = 0·04 m
           combined with a softening constitutive model, although it will
            not completely remove this issue. To demonstrate this feature                          dx = 0·05 m
                                                                                              0·04          dx = 0·06 m
             of SPH, as well as the capability of the proposed SPH
           framework in dealing with coupled flow–large deformation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           displacement: 0·02            problems, a series of sensitivity tests is conducted to investigate
             the influence of spatial discretisations on the predicted results.          The above rainfall-induced slope failure test is repeated with                        Surface    0
           two different particle spacing distances of dx ¼ 5 cm and
          dx ¼ 6 cm, corresponding to a total number of 3706 and 2626         –0·02
         SPH particles, respectively. Other parameters are kept the              0    20   40   60   80   100  120  140  160  180
          same as the previous simulation using dx ¼ 4 cm. Fig. 16                                  Elapsed time: min
           shows a comparison of the numerical results for three different
              spatial discretisations at the sliding state and the final failure     Fig. 17. Influence of spatial discretisations on the SPH prediction of
                state. It can be seen that the proposed model produces very    ground surface displacement against the elapsed time
              similar  results  for  different  discretisation  resolutions. For
              instance, the predicted water table inside the slope body due
             to water content accumulation is almost the same in the three    of granular materials. In this section, a series of sensitivity tests
             simulations, as shown by the contour plots in Fig. 16. The      is conducted to investigate the influence of this technique on
               failure pattern and the predicted failure surface for different    the  predicted  results.  Fig.  18(a) shows the  influence  of
              spatial resolutions are very similar to each other, although    parameter D on the evolution of the adaptive hydraulic
          some minor discrepancies could still be noticed among the    timestep ΔtDl and how fast this hydraulic timestep approaches
             predicted results, confirming that the nature of SPH kernel    the mechanical one as the deviatoric plastic shear increases.
             interpolation mitigates the mesh-dependent issue but does not    Here, the adaptive hydraulic timestep ΔtDl  is shown to drop
            completely remove it. More importantly, the predicted time     rapidly and quickly approach the mechanical timestep Δts as
             evolution   of  ground   surface   displacement   in   this  D increases. In principle, the computational result will be
             rainfall-induced slope failure test over a long period of time     affected by the selection of D and will converge as D is large
                 is nearly the same for different discretisation resolutions,    enough. The authors’ aim is to minimise such influence by
             as shown in Fig. 17. To this end,  it is suggested that the    adopting the largest possible value of D, while still achieving
            proposed SPH model for rainfall-induced slope failure  is    reasonable accuracy. In order to investigate the validity of the
               less sensitive to the spatial discretisation resolutions, at least    proposed  technique, a convergence  test  is conducted by
              for the case currently studied. To completely remove the     repeating the above rainfall-induced slope failure simulation
             influence of discretisation solutions on the predicted results,    with a range of D values, and for the sake of convenience, this
             readers are referred to alternative approaches discussed in Bui    case is only conducted using 2626 particles.
       & Nguyen (2021), which are beyond the scope of this work.       Figure 18(b) shows the influence of D on the predicted
                                                                      time-dependent surface displacement caused by the rainfall
                                                                                       infiltration process. A similar trend in the evolution of the
                                                                  ground displacement is achieved for D ranging from 0 to 30,
             Influence of the adaptive timestepping scheme.  As discussed    and numerical results converge as D increases beyond 25 (i.e.
              in the early section, an adaptive timestepping integration     in a range of +1 5% compared to the experiment). Some
           scheme was proposed to facilitate the computational model-    noticeable differences in the timing of the sliding or failure
              ling of coupled flow–deformation problems involving the     state, where the sliding mass detaches from the slope body
            long-term diffusive process and short-term failure behaviour    and accelerates, are still observed for a smaller value of D,

Downloaded from http://www.emerald.com/jgeot/article-pdf/74/8/787/9585766/jgeot_21_00349.pdf by Kyushu University user on 06 May 2026

### Page 15

A COMPUTATIONALLY EFFICIENT SPH FRAMEWORK FOR UNSATURATED SOILS         801

                0·05                Δtl = 0·05 s                                                      2·0
                                                                              D = 1
                                                                              D = 3                                   Elapsed time = 165·89 min
                0·04                                                         DD == 510                                                             Experiment(Danjo et al., 2012)
                                                                              D                                                                                                   =                                                                                                         12      s                                           m 1·5
                                                                              D                                                                                                   =                                                                                                         16                                                                               ΔtlD = max                                                                                              Δtl exp –D εpeq  , 1  Δts
                                                                               Δts                     D                                                                                                   =                                                                                                         20                               size: 0·03                                                                                             SPH solutions
                                                                              D                                                                                                   =                                                                                                         25
                                                                              D = 30                                                                                                                                                                                                                                                                                                                                                                                                     distance:
                0·02                                                                        1·0                                                 Timestep

                                                                                                                                                                                                                                                                                                                                                                           2·0                                                                                                                                                                                                                                                                                                              run-off                    Elapsed time = 165·08 min              Elapsed time = 164·26 min
                0·01                                                                                                                                                                                                                                                                                                                           1·5
                                                                  Δts = 0·0003 s                                                                      Final 0·5                                                                                                                                            1·0
                 0                                                                                                                                                                                                                                                                                                                           0·5
                  0    0·2   0·4   0·6   0·8   1·0   1·2   1·4   1·6   1·8   2·0                                                                                                                            εpeq     0
                                                      ε peq                                     0
                                                           (a)                                      0        5       10       15       20       25       30
                0·08                                                                       D
                                      Experiment (Danjo et al., 2012)
                           D = 0 (SPH)
                                                                                      Fig. 19. Influence of the adaptive two-timestep coupling scheme on
      m 0·06     DD == 510(SPH)(SPH)
                           D = 15 (SPH)                                                   the SPH prediction of the final run-off distance of the rainfall-induced
                           D = 20 (SPH)                                                    slope failure test
                0·04     D = 25 (SPH)
                           D = 30 (SPH)                                                                                displacement: 0·02                                                             elastoplastic softening constitutive model, the proposed SPH
                                           Surface    0                                               frameworkrainfall-inducedcouldtransientcaptureseepagewell theflowcoupledand thebehavioursubsequentof
                                                                        slope failure process observed in the experiment. The frame-
              –0·02                                             work  is generic, given  it can be used with any existing
                   0    20    40    60    80   100   120   140   160   180      constitutive models for unsaturated  soils. Furthermore, a
                                        Elapsed time: min                        robust adaptive timestepping integration scheme was also
                                                           (b)                          proposed to address the existing computational challenge in
                                                                   modelling coupled flow–deformation problems involving a
           Fig. 18. Convergence analysis of the adaptive two-timestep coupling    long-term seepage diffusion process and short-term failure
          scheme: (a) influence of parameter D on the adaptive hydraulic    behaviour of  soils.  It  is demonstrated that the proposed
           timestep size; (b) influence of parameter D on the SPH prediction of    adaptive timestepping technique  facilitates SPH compu-
           surface displacement in the rainfall-induced slope failure test                                                                             tations for solving coupled flow–deformation problems by
                                                                        saving the huge computational costs required to describe the
                                                                    long-term  seepage  diffusion  process  while  still  proving
          resulting in the delay in the timing of failure. This result is
                                                                      reasonable accuracy when  it comes to the predictions of
         expected since a smaller value of D would delay the hydraulic
                                                                       rapid  flow  deformation.  Further advancements  to  the
         timestep to approach the mechanical one, causing a lack
                                                                 proposed SPH framework could be made by  explicitly
          of required coupling effect during the rapid flowing defor-
                                                                         solving the evolution of airflow in the unsaturated porous
        mation of the materials. Nevertheless,  if one is concerned
                                                                  media, and this will be addressed in future publications.
         with the precursor  state or the warning  state, which  is
         very important in establishing the early warning system, it
             is interesting to see that the proposed adaptive timestepping
         produces  negligible  effects.  Finally,  despite  the  above   ACKNOWLEDGEMENTS
        minor  differences,  the  predicted  final  run-out  distance     The authors  gratefully acknowledge support from the
        shows similar results for D larger than 15 and is very close    Australian Research Council by way of Discovery Projects
          to the experimental data (see Fig. 19). More importantly, the    DP170103793  (Nguyen,  Bui), DP190102779  (Bui  and
          entire simulation can be completed within less than 3 h,    Nguyen) and FT200100884 (Bui). Part of this research was
          instead  of  several  days without  adopting  the  adaptive    undertaken with the assistance of resources and services from
         timestepping scheme. Overall, the above sensitive analysis    the National Computational Infrastructure (NCI), which is
          suggests that the proposed adaptive timestepping technique is    supported by the Australian government. The authors would
           reliable and produces acceptable accuracy for analyses of     also like to thank Professor Kazunari Sako of Kagoshima
         coupled flow–deformation problems while saving substantial    University and Dr Toru Danjo of the National Research
         computational costs.                                                Institute for Earth Science and Disaster Resilience (NIED)
                                                                              for providing the experimental data. The support of the
                                                             China Scholarship Council (CSC, no. 201906050025) is also
      CONCLUSION                                                   gratefully acknowledged.
           This paper addresses one of the challenging geotechnical
         problems by  developing  a  robust and  advanced SPH
         computational framework for solving coupled flow–defor-
        mation problems in partially saturated porous media under-
                                              APPENDIX 1
         going large deformations and failures. Compared to existing                                                                  The general stress–strain relationship of the suction-dependent
         coupled SPH approaches, the newly proposed SPH frame-                                                                                           elastic–plastic DP softening model can be derived by considering the
        work is unique in the sense that it solves governing equations     Taylor series expansion of the yield surface at the correct stress state
          of multi-phase mixtures using a single set of Lagrangian    around the trial stress state
           particles, which  is more  computationally  efficient and
                                                                                                  @f                                                                                                               @f                                                                                                                         @f
                                                                                                                                                                         : dσ p′ þ         cheaper for large-scale applications. The paper demonstrates          f ð σ′; κc Þ ¼ f trial                                                                                                                                dps ¼ 0      ð44Þ                                                                                                                      dεpeq þ
           that, with a standard SWCC and a simple suction-dependent                       @σ′         @εpeq       @ps

Downloaded from http://www.emerald.com/jgeot/article-pdf/74/8/787/9585766/jgeot_21_00349.pdf by Kyushu University user on 06 May 2026

### Page 16

802                         LIAN, BUI, NGUYEN, ZHAO AND HAQUE

             where the incremental form of the accumulated equivalent strain is    where pl0 is the initial excess pore pressure; L is the consolidation
              given as                                                                  length; M ¼ 0 5 ð 2k  1 Þπ is a normalised factor; and the dimen-
           r ﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃ                                                sional time factor is given as
                         2 @g0  @g0
                 dεpeq ¼ dλ             :                                        ð45Þ               cvt
                         3 @s  @s                                          Tv ¼                                                    ð49Þ
                                                                               L2
             where s is the deviatoric shear stress tensor. Expanding equation (44)
                                                                          where
              leads to
                                                                                                                     ð                                                                                                                              ksat                                                                                           1                                                                                                                      ksat                                                                                                            νÞEs                         @f                                           @f                                                     @f                                                      ¼                                                                                               cv ¼                         f trial ¼                                                : ð De : dεp Þ                                                                                              : dps                                                dεpeq                                                         þ ν                                                                                                                      Þ                                                                                                               ð 1                                                                                                                       ð 1                                                                               γmv                                                                                                      2ν Þγl                        @σ′                                           @εp                                                     @ps                                                          eq
                        r ﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃ              where cv is the consolidation coefficient; ν is Poisson’s ratio; Es is
                                   trial   @f          @g0    @fNþ1trial     2 @g0  @g0   @f          Young’s modulus; and mv is the compression index defined by                Δf  ¼       :  De: dλ             dλ             :                 : dps
                        @σ′         @σ′     @εpeq     3 @s  @s   @ps
                                                                                                        ð 1 þ νÞ ð 1   2νÞ
                                                                          ð46Þ      mv ¼                                                    ð50Þ
                                                                                                            ð 1   ν ÞEs

               Re-arrange equation (46), leading to the expression of the plastic                                                                    The surface settlement of the soil column can be obtained using
               multiplier dλ                                                                                    the average degree of consolidation, which is given as follows
                              f trial þ ð@f =@psÞdps                                                                          ð47Þ        STv ¼ UaSf                                               ð51Þ               dλ ¼
                     He þ Hp
                                                                          where
             where
                                                                                    k¼1X 2
                 @f          s          @g0          s                     Ua ¼ 1         exp  M2Tv
                pﬃﬃﬃﬃ                               p ﬃﬃﬃﬃ                               and                                                     and                                                              M2            ¼ ξϕδ þ                           ¼ ξψδ þ                                                                                                                     k                @σ′                                        @σ′                          2                                                 2                                 J2                                                             J2
                                  I1                                                where Sf is the final surface settlement in the column after the excess
                s ¼ σ′    δ
                         3                                                     pore-water pressure is fully dissipated and could be obtained as
                                                                                      follows

                 @f                       @f @ϕ @ϕs                                   @f @c @cs                                            Sf ¼ q0mvL                                              ð52Þ            ¼                   þ
                 @ps  @ϕ @ϕs @ps   @c @cs @ps
                                                                          where q0 is the surcharge load and mv is the compression index.
             r ﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃ
                         @f   2 @g0  @g0
            Hp ¼                        :
                        @εpeq  3 @s  @s                        NOTATION
                                                                                    A′  parameter controlling the variation of friction angle
                      @f       @g0                                                      B′  parameter controlling the variation of cohesion
             He ¼       : De :                                                    b   gravitational force vector
                     @σ′      @σ′
                                                                                                  Cij   stabilisation term in SPH
                                                                        Ck  Kozeny–Carman coefficient
                  @f    @f @c    @f @ϕ                                                Cl   specific storage term in unsaturated soil (m 1)            ¼    þ
                 @εpeq   @c @εpeq  @ϕ @εpeq                                            Cs   specific moisture term (m 1)
                                                                                          cmax  maximum cohesion suction bring-up (kPa)
                                                                                                    cp; cr  peak and residual cohesion, respectively (kPa)
                 @f                                       3                       @f @kc                                                                                                           c; c′; cs   total cohesion, saturated cohesion, suction-dependent           ¼                 ¼ ð  1 Þ q ﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃ
               @c   @kc @c                                                                 cohesion, respectively (kPa)                                   9 þ 12 tan ϕ2
                                                                                                            csp  sound speed in the material (m/s)
                                                                                                     cv   consolidation coefficient
                 @f    @f @kc   @f @ξϕ   36c tan ϕ 1 þ tan2ϕ                D   adaptive hydraulic timestep parameter
            ¼                 þ                       ¼                                                                           De   elastic                                                                                                                         stiffness                                                                                                               tensor                                                                                                                 (kPa)
             @ϕ                     @kc @ϕ                             @ξϕ @ϕ                                       9 þ 12 tan ϕ2   3=2                     Dmn                                                                                                            δmn                                                                                                                        r ji 2Þ                                                                                            4ðrmjirnji=             8                  9
             ><                  >=                        d0   initial spacing between particles                           1 þ tan2ϕ     12tan2ϕ 1 þ tan2ϕ                     dαðÞ=dt   material derivative on component α (s 1)
             q ﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃ             þ I1                                                                                 dλ   plastic                                                                                                            multiplier             >:                           9 þ 12 tan ϕ2    9 þ 12 tan ϕ2   3=2 >;                                                                                       Young’s                                                                                       modulus of solid material (Pa)                                                                                     Es
                                                                                           e  void ratio
                                                                                                     e0   initial void ratio
                                       @ϕ                @c                                                                                                                                 eq             F   timestep adapting coefficient                                                                      eq  and            ¼  η cp    cr e  ηεp                              ¼  η ϕp   ϕr e  ηεp
                  @εeqp                               @εeqp                                                       ˜F ij   scalar part of the normalised kernel gradient
                                                                                                                           f   yield surface
                                                                                                                       f trial   yield surface with a trial stress
                @ϕs    A′          @cs         B′      B′ð ps=patmÞ            ¼      and    ¼ cmax     e                                 g   gravitational acceleration
              @ϕ    patm        @c         patm                                                                                            g0   plastic potential
                                                                                            ga   material parameter of soil water retention curve
                                                                     (SWRC) (m 1)
                                                                                                  gc   empirical parameters of SWRC
                                                                                         gn   material parameter of SWRC
        APPENDIX 2                                H   total water head (m)
               Within the context of Terzaghi’s one-dimensional consolidation        He   elastic modulus
               theory, the analytical solution of the excess pore-water pressure with        Hp   softening modulus
               respect to time is given as follows (Terzaghi, 1996)                         h  water pressure head (m)
                                                                                                     hsml  smoothing length (m)
                   k¼1X 2pl0   Mz                                                                                  I   unit tensor
                     pl ¼         sin      exp  M2Tv                        ð48Þ           J2  second invariant of the stress tensor           M    L
                      k¼1                                                   KS   bulk modulus of the soil skeleton (kPa)

Downloaded from http://www.emerald.com/jgeot/article-pdf/74/8/787/9585766/jgeot_21_00349.pdf by Kyushu University user on 06 May 2026

### Page 17

A COMPUTATIONALLY EFFICIENT SPH FRAMEWORK FOR UNSATURATED SOILS         803
                Ksatl    bulk modulus of water phase (kPa)                       Alonso,  E.  E.  (2021).  Triggering and motion  of  landslides.
                ka   permeability tensor of air phase (m=s)                        Géotechnique 71, No. 1, 3–59, https://doi.org/10.1680/jgeot.20.
                   kl   permeability tensor of water phase (m=s)                    RL.001.
                    ksat   saturated permeability of water phase (m=s)               Bandara, S. & Soga, K. (2015). Coupling of soil deformation and
           L   consolidation length                                        pore fluid flow using material point method. Comput. Geotech.
                     Lij   normalised matrix                                              63,  November,  199–214,  https://doi.org/10.1016/j.compgeo.
       M  normalisation factor                                          2014.09.009.
               mt   total mass (kg)                                       Bao, Y., Huang, Y., Liu, G. R. & Wang, G. (2020). SPH simulation
             mv   coefficient of volume change (kPa 1)                           of high-volume rapid landslides triggered by earthquakes based
                n   porosity of the mixture                                on a  unified  constitutive model. Part  I:  initiation process
             na; nl; ns   void fraction of air phase, water phase, solid phase,          and slope failure. Int. J. Comput. Methods 17, No. 4, 1850150,
                        respectively                                                   https://doi.org/10.1142/S0219876218501505.
                patm   the atmospheric pressure (kPa)                           Bažant,  Z.  P.  (1991). Why continuum damage  is  nonlocal:
            pa; pl; ps   pore-air pressure, pore-water pressure, suction (kg=m3)         micromechanics  arguments.  J. Engng Mech.  117, No.  5,
          Q  mixed volumetric stiffness of the mixture (kPa)               1070–1087,    https://doi.org/10.1061/(ASCE)0733-9399(1991)
                q  normalised distance (m)                                       117:5(1070).
              Rαβ   drag force vector between phases α and β (N)              Blanc, T. & Pastor, M. (2012). A stabilized Runge–Kutta, Taylor
                    r ji   distance vector between particle i and j (m)                 smoothed particle hydrodynamics algorithm for large defor-
                  Sf   final surface settlement                                   mation problems indynamics. Int. J. Numer. Methods Engng 91,
                 Sr   degree of saturation                                    No. 13, 1427–1458, https://doi.org/10.1002/nme.4324.
                   Sres   residual degree of saturation                               Borja, R. I. & White, J. A. (2010). Continuum deformation and
                   Ssat   saturated degree of saturation                                        stability  analyses  of a  steep  hillside  slope under  rainfall
                STv   surface settlement at Tv                                               infiltration. Acta  Geotech.  5, No.  1, 1–14,  https://doi.org/
               s   deviatoric shear stress tensor                                 10.1007/S11440-009-0108-1.
              Tv   dimensionless time factor                                  Bui, H. H. & Fukagawa, R. (2009). A first attempt to solve soil water
                Vj  volume occupied by particle j (m2)                          coupled problems by SPH. Terra Mech. 29, 33–38 (in Japanese).
                  vs   velocity tensor of the solid phase (m=s)                     Bui, H. H. & Fukagawa, R. (2013). An improved SPH method for
       W   symmetric smoothing kernel function                           saturated soils and its application to investigate the mechanisms
                      ˉwas   relative velocity between air and solid phase (m=s)              of embankment failure: case of hydrostatic pore-water pressure.
                          ˉwls   the relative velocity between water and solid phase (m=s)          Int. J. Numer. Analyt. Methods Geomech. 37, No. 1, 31–50,
              x   position vector (m)                                              https://doi.org/10.1002/nag.1084.
                  z   elevation (m)                                              Bui, H. H. & Nguyen, G. D. (2017). A coupled fluid–solid SPH
                αd   dimensional normalising factor                             approach to modelling flow through deformable porous media.
                              ˆα   compressibility of soil skeleton (kPa 1)                             Int.  J.  Solids  Structs 125, 244–264,  https://doi.org/10.1016/
                                ˆβ   compressibility of the water phase (kPa  1)                        j.ijsolstr.2017.06.022.
              Δts; Δtl   size of mechanics timestep and fluid flow timestep,         Bui, H. H. & Nguyen, G. D. (2021). Smoothed particle hydrodyn-
                        respectively (s)                                            amics (SPH) and its applications in geomechanics: from solid
              ΔtDl   adapted timestep size for fluid flow (s)                           fracture to granular behaviour and multiphase flows in porous
               δmn  Kronecker delta                                           media. Comput. Geotech. 138, 104315, https://doi.org/10.1016/
                εp   plastic strain tensor                                         j.compgeo.2021.104315.
                    εeqp   accumulated equivalent plastic strain                       Bui, H.  H.,  Sako, K. & Fukagawa, R.  (2007).  Numerical
                η   softening controlling coefficient                                simulation of soil-water interaction using smoothed particle
                  κc  Drucker–Prager (DP) constant                             hydrodynamics (SPH)  method.  J.  Terramech.  44, No.  5,
                  ν   Poisson’s ratio                                             339–346, https://doi.org/10.1016/j.jterra.2007.10.003.
                  ξ   coefficient for global dumping technique                   Bui, H. H., Fukagawa, R., Sako, K. & Ohno, S. (2008a). Lagrangian
               ξϕ; ξψ  DP constants                                              meshfree particles method (SPH) for large deformation and
             ρa; ρl; ρs   intrinsic mass density of air phase, water phase, solid             failure flows of geomaterial using elastic–plastic soil constitutive
                      phase, respectively (kg=m3)                                 model. Int. J. Numer. Analyt. Methods Geomech. 32, No. 13,
                           ˉρa   partial density of air phase (kg=m3)                         1537–1570, https://doi.org/10.1002/nag.
                                  ˉρl   partial density of water phase (kg=m3)                     Bui, H. H., Sako, K., Fukagawa, R. & Wells,  J. C. (2008b).
                               ˉρs   partial density of solid phase (kg=m3)                      SPH-based numerical simulations  for large deformation of
                     ρt   total density of the mixture (kg=m3)                           geomaterial considering soil–structure interaction. Proceedings
            σ   total stress tensor of the mixture (Pa)                            of the 12th international conference of the international associ-
                  σ′   effective stress tensor of the solid phase (Pa)                     ation  for computer methods and advances  in geomechanics
           σa; σl; σs   intrinsic stress tensor of air, water, solid phase,             (IACMAG), Goa, India, vol. 1, pp. 570–578.
                        respectively (Pa)                                           Bui, H. H., Fukagawa, R., Sako, K. & Okamura, Y. (2010).
                  σp′   plastic effective stress                                     Earthquake induced slope failure simulation by SPH. In 2010 –
                ˉσa; ˉσl; ˉσs   partial stress tensors of air, water and solid phases,              Fifth international conference on recent advances in geotechnical
                        respectively (Pa)                                             earthquake engineering and soil dynamics, session 04b, paper 14.
                 σv   vertical total stress (Pa)                                         Rolla, MO, USA:  Missouri  University  of  Science  and
           ϒ   state variables                                               Technology.
             ϕ; ϕ′; ϕs   total friction angle, saturated friction angle,                Bui, H. H., Fukagawa, R., Sako, K. & Wells, J. C. (2011). Slope
                     suction-dependent friction angle, respectively (degrees)           stability analysis and discontinuous slope failure simulation
              ϕp; ϕr  peak friction angle, residual friction angle, respectively        by  elasto-plastic smoothed  particle hydrodynamics  (SPH).
                      (degrees )                                                  Géotechnique 61, No. 7, 565–574, https://doi.org/10.1680/geot.
             ψ; ψ0    dilation angle, initial dilation angle, respectively                 9.P.046.
                       (degrees)                                                  Bui, H. H., Kodikara, J. K., Bouazza, A., Haque, A. & Ranjith, P.
          ω   rotation tensor                                         G. (2014). A novel computational approach for large defor-
                   h i   kernel approximation operator                             mation and post-failure analyses of segmental retaining wall
                                                                                       systems. Int. J. Numer. Analyt. Methods Geomech. 38, No. 13,
                                                                             1321–1340, https://doi.org/10.1002/nag.2253.
                                                                          Chalk, C. M., Pastor, M., Peakall, J., Borman, D. J., Sleigh, P. A.,
      REFERENCES                                               Murphy, W. & Fuentes, R. (2020). Stress-particle smoothed
          Alonso, E. E. (1991). A constitutive model for partially saturated          particle hydrodynamics: an application to the failure and post-
                  soils. Géotechnique 41, No. 2, 273–275, https://doi.org/10.1680/          failure behaviour of  slopes. Comput. Methods Appl. Mech.
               geot.1991.41.2.273.                                          Engng 366, 113034, https://doi.org/10.1016/j.cma.2020.113034.

Downloaded from http://www.emerald.com/jgeot/article-pdf/74/8/787/9585766/jgeot_21_00349.pdf by Kyushu University user on 06 May 2026

### Page 18

804                         LIAN, BUI, NGUYEN, ZHAO AND HAQUE

            Chen, J. K. & Beraun, J. E. (2000). A generalized smoothed particle     Lucy, L. B. (1977). A numerical approach to the testing of the fission
                hydrodynamics  method  for  nonlinear  dynamic  problems.         hypothesis. Astronom. J. 82, No. 12, 1013–1024.
               Comput. Methods Appl. Mech. Eng. 190, No. 1–2, 225–239,    Monaghan, J. J. (1985). Extrapolating B splines for interpolation. J.
                  https://doi.org/10.1016/S0045-7825(99)00422-3.                     Comput. Phys. 60, No.  2, 253–262,  https://doi.org/10.1016/
            Chen, W. F. & Mizuno, E. (1990). Nonlinear analysis in soil mech-        0021-9991(85)90006-3.
                   anics theory and implementation. Amsterdam, the Netherlands:    Moriwaki, H. (2001). A risk evaluation of landslides in use of critical
                    Elsevier.                                                               surface displacement. Landslides 38, No. 2, 115–122, https://doi.
            Chen, W. & Qiu, T. (2014). Simulation of earthquake-induced slope         org/10.3313/jls1964.38.2_115.
                 deformation using SPH method. Int. J. Numer. Analyt. Methods    Moriwaki, H., Inokuchi, T., Hattanji, T., Sassa, K., Ochiai, H. &
               Geomech. 38, No. 3, 297–330, https://doi.org/10.1002/nag.2218.       Wang, G. (2004). Failure processes in a full-scale landslide
               Cleary, P. W. & Monaghan, J. J. (1999). Conduction modelling using        experiment using a rainfall simulator. Landslides 1, No. 4,
               smoothed particle hydrodynamics. J. Comput. Phys. 148, No. 1,        277–288, https://doi.org/10.1007/s10346-004-0034-0.
                 227–264, https://doi.org/10.1006/jcph.1998.6118.                Nguyen, G. D. & Bui, H. H. (2020). A thermodynamics- and
             Danjo,  T., Sako, K., Fukagawa, R., Sakai, N., Iwasa, N. &        mechanism-based framework  for  constitutive  models  with
               Quang, N. M. (2012). Verification on the process of rainfall-         evolving thickness of localisation band. Int. J. Solids Structs
                 induced  surface  failure from  rainfall  intensity, unsaturated         187, 100–120, https://doi.org/10.1016/j.ijsolstr.2019.05.022.
                 seepage and deformation.  J. Japan. Soc. Civ. Engrs Ser. C    Nguyen, G. D., Nguyen, C. T., Nguyen, V. P., Bui, H. H. & Shen, L.
                (Geosph. Engng) 68, No. 3, 508–525.                                   (2016). A size-dependent constitutive modelling framework for
             Danjo,  T., Sako, K., Fujimoto, M., Iwasa, N., Sakai, N. &         localised failure analysis. Comput. Mech. 58, No. 2, 257–280,
               Fukagawa, R.  (2013). The  full  scale  rainfall experimental         https://doi.org/10.1007/s00466-016-1293-z.
                 study of fusion technology with monitoring and reinforcement    Nguyen, C.  T., Nguyen, C.  T., Bui, H. H., Nguyen, G. D. &
               method on slope. 8th International symposium on advanced       Fukagawa, R. (2017). A new SPH-based approach to simulation
                   science and  technology  in  experimental  mechanics,  Sendai,         of granular flows using viscous damping and stress regularis-
                 Japan.                                                                     ation. Landslides 14, No.  1, 69–81,  https://doi.org/10.1007/
             Danjo, T., Sako, K., Iwasa, N., Fujimoto, M. & Fukagawa, R.         s10346-016-0681-y.
                   (2015). Validation of deterrent effect of nailing sensor. 16th    Nguyen, N. H. T., Bui, H. H. & Nguyen, G. D. (2020). Effects of
                 Conference on current researches in geotechnical engineering in         material properties on the mobility of granular flow. Granul.
                 Taiwan, Kaohsiung, Taiwan.                                      Matter 22, No. 3, article 59, https://doi.org/10.1007/s10035-020-
               del Castillo, E. M., Fávero Neto, A. H. & Borja, R. I. (2021). Fault         01024-y.
                 propagation and surface rupture in geologic materials with a    Oka, F., Shahbodagh, B. & Kimoto, S. (2019). A computational
                 meshfree  continuum  method.  Acta  Geotech.  16,  No.  8,       model for dynamic strain localization in unsaturated elasto-
                2463–2486, https://doi.org/10.1007/s11440-021-01233-6.                  viscoplastic soils. Int. J. Numer. Analyt. Methods Geomech. 43,
             Español, P. & Revenga, M. (2003). Smoothed dissipative particle       No. 1, 138–165, https://doi.org/10.1002/nag.2857.
                 dynamics. Phys. Rev. E 67, No. 2, 12, https://doi.org/10.1103/     Oñate, E., Idelsohn, S. R., Del Pin, F. & Aubry, R. (2004). The
                PhysRevE.67.026705.                                                      particle finite element method — an overview. Int. J. Comput.
             Fávero Neto, A. H. & Borja, R. I. (2018). Continuum hydrodyn-       Methods   01,  No.   02,  267–307,   https://doi.org/10.1142/
                amics of dry granular flows employing multiplicative elasto-        s0219876204000204.
                      plasticity. Acta Geotech. 13, No. 5, 1027–1040, https://doi.org/     Pastor, M., Haddad, B., Sorbino, G., Cuomo, S. & Drempetic, V.
                 10.1007/s11440-018-0700-3.                                             (2009). A depth-integrated, coupled SPH model for flow-like
             Fávero Neto, A. H., Askarinejad, A., Springman, S. M. & Borja, R.         landslides and  related phenomena.  Int.  J. Numer.  Analyt.
                        I. (2020). Simulation of debris flow on an instrumented test slope       Methods Geomech. 33, No. 2, 143–172, https://doi.org/10.1002/
                  using an updated Lagrangian continuum particle method. Acta       NAG.705.
                 Geotech.  15,  No.  10,  2757–2777,  https://doi.org/10.1007/     Pastor, M., Blanc, T., Haddad, B., Petrone, S., Sanchez Morles, M.,
                 s11440-020-00957-1.                                              Drempetic, V., Issler, D., Crosta, G. B., Cascini, L., Sorbino, G.
             Fredlund, D. G. & Xing, A. (1994). Equations for the soil-water     & Cuomo, S. (2014). Application of a SPH depth-integrated
                    characteristic curve. Can. Geotech. J. 31, No. 4, 521–532.            model to landslide run-out analysis. Landslides 11, No.  5,
             Gens, A. & Alonso, E. E. (1992). A framework for the behaviour of        793–812, https://doi.org/10.1007/s10346-014-0484-y.
                  unsaturated  expansive  clays. Can.  Geotech.  J.  29, No.  6,     Pastor, M., Yague, A., Stickle, M. M., Manzanal, D. & Mira, P.
                1013–1032, https://doi.org/10.1139/t92-120.                             (2018). A two-phase SPH model for debris flow propagation.
            Gharehdash, S., Shen, L. & Gan, Y. (2020). Numerical study on          Int. J. Numer. Analyt. Methods Geomech. 42, No. 3, 418–448,
                mechanical and hydraulic behaviour of blast-induced fractured         https://doi.org/10.1002/nag.2748.
                   rock. Engng Comput.  36, No.  3, 915–929,  https://doi.org/     Peng, C., Wu, W., Yu, H. S. & Wang, C. (2015). A SPH approach for
                 10.1007/s00366-019-00740-1.                                            large deformation analysis with hypoplastic constitutive model.
             Gingold, A. R. & Monaghan,  J.  J. (1977). Smoothed particle        Acta Geotech.  10, No.  6, 703–717,  https://doi.org/10.1007/
                 hydrodynamics: theory and application to non-spherical stars.        s11440-015-0399-3.
              Mon. Not. R. Astr. Soc. 181, No. 3, 375–389.                     Peng, C., Guo, X., Wu, W. & Wang, Y. (2016). Unified modelling
            He, X., Liang, D. & Bolton, M. D. (2018). Run-out of cut-slope         of granular media with smoothed  particle hydrodynamics.
                    landslides: mesh-free  simulations. Géotechnique  68, No.  1,        Acta Geotech. 11, No. 6, 1231–1247, https://doi.org/10.1007/
                 50–63, https://doi.org/10.1680/jgeot.16.P.221.                          s11440-016-0496-y.
                Jin, Y. F., Yin, Z. Y. & Yuan, W. H. (2020). Simulating retrogressive     Sheikh, B., Qiu, T. & Ahmadipur, A. (2021). Comparison of SPH
                  slope failure using two different smoothed particle finite element       boundary approaches  in simulating  frictional  soil–structure
                methods: a comparative  study. Engng Geol. 279, October,         interaction. Acta  Geotech.  16, No.  8, 2389–2408,  https://
                 105870, https://doi.org/10.1016/j.enggeo.2020.105870.                  doi.org/10.1007/s11440-020-01063-y.
               Khalili, N. &  Loret,  B.  (2001). An  elasto-plastic model  for    Sheng, D., Sloan, S. W., Gens, A. & Smith, D. W. (2003). Finite
                 non-isothermal   analysis   of  flow  and  deformation   in        element formulation and algorithms for unsaturated soils. Part I:
                  unsaturated porous media: formulation. Int. J. Solids Structs         theory. Int. J. Numer. Analyt. Methods Geomech. 27, No. 9,
                  38, No. 46–47, 8305–8330, https://doi.org/10.1016/S0020-7683        745–765, https://doi.org/10.1002/nag.295.
                  (01)00081-6.                                                 Song, X. & Borja, R.  I. (2014). Mathematical framework for
             Kosugi, K. (1996). Lognormal distribution model for unsaturated         unsaturated flow in the finite deformation range. Int. J. Numer.
                     soil  hydraulic  properties. Water  Resour.  Res.  32, No.  9,       Methods Eng. 97, No. 9, 658–682, https://doi.org/10.1002/nme.
                2697–2703.                                                        4605.
              Lian, Y., Bui, H. H., Nguyen, G. D., Tran, H. T. & Haque, A. (2021).     Switała,  B. M. & Wu, W.  (2018). Numerical  modelling  of
          A general SPH framework for transient seepage flows through         rainfall-induced instability of vegetated slopes. Géotechnique
                  unsaturated porous media considering anisotropic features of         68, No. 6, 481–491, https://doi.org/10.1680/jgeot.16.P.176.
                    diffusion. Comput. Methods Appl. Mech. Engng 387, 114169,     Terzaghi, K.  (1996).  Soil  mechanics  in  engineering  practice.
                  https://doi.org/10.1016/j.cma.2021.114169.                   New York, NY, USA: John Wiley & Sons.

Downloaded from http://www.emerald.com/jgeot/article-pdf/74/8/787/9585766/jgeot_21_00349.pdf by Kyushu University user on 06 May 2026

### Page 19

A COMPUTATIONALLY EFFICIENT SPH FRAMEWORK FOR UNSATURATED SOILS         805

          Tran, H. T., Wang, Y., Nguyen, G. D., Kodikara, J., Sanchez, M. &     Wheeler, S. J. & Sivakumar, V. (1995). An elasto-plastic critical state
              Bui, H. H. (2019). Modelling 3D desiccation cracking in clayey        framework for unsaturated soil. Géotechnique 45, No. 1, 35–53,
                 soils using a size-dependent SPH computational approach.         https://doi.org/10.1680/geot.1995.45.1.35.
            Comput.  Geotech.  116,  December,  103209,  https://doi.org/    Yang, E., Bui, H. H., De Sterck, H., Nguyen, G. D. & Bouazza, A.
              10.1016/j.compgeo.2019.103209.                                        (2020). A scalable  parallel computing SPH framework for
          Tran, H. T., Nguyen, N. H. T., Nguyen, G. D. & Bui, H. H. (2020).         predictions of geophysical granular flows. Comput. Geotech.
             Meshfree SPH modelling of shrinkage induced cracking in         121, January, 103474, https://doi.org/10.1016/j.compgeo.2020.
               clayey soils. In CIGOS 2019, innovation for sustainable infra-        103474.
                structure:  proceedings  of  the  5th  international  conference    Yang, E., Bui, H. H., Nguyen, G. D., Choi, C. E., Ng, C. W. W., De
             on  geotechnics,  civil  engineering works and  structures  (eds         Sterck, H. & Bouazza, A. (2021). Numerical investigation of the
             C. Ha-Minh, D. V. Dao, F. Benboudjema, S. Derrible, D. V.       mechanism of granular flow impact on rigid control structures.
           K. Huynh and A. M. Tang), Lecture Notes in Civil Engineering        Acta Geotech. 16, 2505–2527, https://doi.org/10.1007/s11440-
                vol.  54,  pp.  889–894,  https://doi.org/10.1007/978-981-15-        021-01162-4.
              0802-8_142. Singapore: Springer Nature Singapore Pte Ltd.        Yerro, A., Alonso, E. E. & Pinyol, N. M. (2015). The material point
         van Genuchten, M. T. (1980). A closed-form equation for predicting       method for unsaturated soils. Géotechnique 65, No. 3, 201–217,
              the hydraulic conductivity of unsaturated soils. Soil Sci. Soc.         https://doi.org/10.1680/geot.14.P.163.
           Am. J. 44, No. 5, 892–898, https://doi.org/10.2136/sssaj1980.     Zabala, F. & Alonso, E. E. (2011). Progressive failure of Aznalcó
             03615995004400050002x.                                           Llar dam using the material point method. Géotechnique 61,
          Vardoulakis, I. & Aifantis, E. C. (1991). A gradient flow theory of       No. 9, 795–808, https://doi.org/10.1680/geot.9.P.134.
                 plasticity for granular  materials. Acta Mech. 87, No. 3–4,    Zhan, L., Peng, C., Zhang, B. & Wu, W. (2020). A SPH framework
             197–217, https://doi.org/10.1007/BF01299795.                            for dynamic interaction between soil and rigid body system with
         Wang, Y., Bui, H. H., Nguyen, G. D. & Ranjith, P. G. (2019).         hybrid contact method. Int. J. Numer. Analyt. Methods Geomech.
        A new SPH-based continuum framework with an embedded         44, No. 10, 1446–1471, https://doi.org/10.1002/nag.3070.
               fracture  process zone  for  modelling rock  fracture.  Int.  J.    Zhao, S., Bui, H. H., Lemiale, V., Nguyen, G. D. & Darve, F. (2019).
               Solids  Structs  159,  40–57,  https://doi.org/10.1016/j.ijsolstr.     A generic approach to modelling flexible confined boundary
              2018.09.019.                                                         conditions in SPH and its application. Int. J. Numer. Analyt.
         Wang, Y., Tran, H. T., Nguyen, G. D., Ranjith, P. G. & Bui, H. H.       Methods Geomech.  43, No.  5,  1005–1031,  https://doi.org/
               (2020). Simulation of mixed-mode fracture using SPH particles        10.1002/nag.2918.
              with an embedded fracture process zone. Int. J. Numer. Analyt.     Zienkiewicz, O. C., Chan, A. H. C., Pastor, M., Schrefler, B. A.
            Methods Geomech.  44, No.  10, 1417–1445,  https://doi.org/     & Shiomi, T. (1999). Computational geomechanics. Chichester,
              10.1002/nag.3069.                                   UK: Wiley.

Downloaded from http://www.emerald.com/jgeot/article-pdf/74/8/787/9585766/jgeot_21_00349.pdf by Kyushu University user on 06 May 2026
