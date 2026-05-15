# Two-phase fully-coupled smoothed particle hydrodynamics (SPH) model for unsaturated soils and its application to rainfall-induced slope collapse

> Auto-converted from PDF for Codex/code-reference reading. Formatting, equations, figures, and tables may require checking against the original PDF.

- Source PDF: `Feng 2022_CG.pdf`
- Pages: 18
- PDF metadata author: Ruofeng Feng

## Extracted Text

### Page 1

Computers and Geotechnics 151 (2022) 104964

                                                 Contents lists available at ScienceDirect
                        Computers and Geotechnics

                                          journal homepage: www.elsevier.com/locate/compgeo

Two-phase fully-coupled smoothed particle hydrodynamics (SPH) model
for unsaturated soils and its application to rainfall-induced slope collapse
Ruofeng Feng *, Georgios Fourtakas , Benedict D. Rogers , Domenico Lombardi
Department of Mechanical, Aerospace & Civil Engineering, Faculty of Science and Engineering, The University of Manchester, M13 9PL, UK

A R T I C L E  I N F O                  A B S T R A C T

Keywords:                                          In this paper, a new fully-coupled Smoothed Particle Hydrodynamics (SPH) formulation for unsaturated soils is
Smoothed particle hydrodynamics (SPH)             developed to study the influence of rainfall infiltration on slope stability. The single-layer two-phase formulation
Unsaturated soils                                              is investigated in SPH for the first time to simulate the response of unsaturated soils. The use of a single set of
Numerical diffusion term                                                       particles improves the computational efficiency and facilitates the implementation of infiltration boundaryWall boundary conditions                                                    conditions. The Drucker–Prager strain-softening model, with the use of Bishop’s effective stress, is adopted as theRainfall-induced landslides
                                                             soil’s constitutive model. New extensions of a first-order consistent wall boundary treatment are proposed for the
                                              coupled hydro-mechanical problem to enforce non-slip/free-slip conditions for the soil phase and water phase. A
                                               novel stress diffusion algorithm for general application is introduced to smooth out the numerical noise in the
                                                         stress field under large deformation. The accuracy of the formulated SPH model is examined with available
                                                     analytical solutions and experimental data. The proposed numerical scheme is finally applied to the simulation of
                                                    rainfall-induced slope collapse of an unsaturated slope with two different bedrock geometries. Results demon
                                                        strate that the geometry of the bedrock is shown to play an important role in the failure initiation and propa
                                                 gation of the collapse. It is found that the proposed model allows the investigation of both triggering and post-
                                                        failure mechanism, providing a smooth stress field even at large deformations.

1. Introduction                                                        leading to a gradual development of one or more sliding surfaces. The
                                                                                  failure initiates once a continuous sliding surface is formed. This is fol
   Water infiltration such as rainfall can be considered as one of the    lowed by the post-failure stage, which is characterized by the rapid
main triggering factors of the slope failure. The process of water infil     accumulation of plastic strains and the sudden acceleration of the failed
tration leads to the rise of pore water pressure and the decrease of matric      soil mass moving downslope.
suction in unsaturated soils, which in turns decreases the effective stress.        Apart from experimental works, predictive (e.g., Guzzetti et  al.,
As a consequence, the soil strength is weakened, and the equilibrium    2008, Wu et  al., 2015, Sasahara, 2017), statistical (e.g., Ibsen and
may not able to be maintained, resulting in instability of slopes such as     Casagli, 2004, Chang and Chiang, 2009, Kristo et al., 2017), probabi
landslides. Rainfall-induced slope failures involve complex hydrological      listic (e.g., Zhang et al., 2010, Ering and Babu, 2016), and numerical
and geomechanical processes that depend on the geometries and the    methods (e.g., Cai and Ugai, 2004, Yoo and Jung, 2006, Davies et al.,
initial state of the slope, the hydro-mechanical properties of the soils and    2014, Leshchinsky et al., 2015) have been used to assess the stability of
the infiltration parameters (Sorbino and Nicotera, 2013). In the last     unsaturated slopes, and to provide insights into the failure mechanism.
decades, substantial experimental efforts have been carried out to        In the early days of the development of numerical approaches, the
advance the understanding of the physics involved in rainfall-induced     seepage analysis and slope stability analysis were performed separately
slope instabilities (e.g., Ochiai et al., 2004, Huang et al., 2008, Cui      (e.g., Cai and Ugai, 2004, Yoo and Jung, 2006). The accuracy and
et al., 2014, Wang et al., 2020). It is recognised that a typical rainfall-     computational  efficiency  of  this  uncoupled framework depended
induced landslide process can be divided into two main stages: onset     strongly on the selected time increments. The integrated analysis of
of failure and post-failure stage (Cascini et al., 2010). Before the onset of     hydraulic and mechanical response of unsaturated soil were imple
failure, water infiltration modifies the stress state within the material,    mented in later research works using a coupled framework (e.g., Yang

 * Corresponding author.
    E-mail address: ruofeng.feng@postgrad.manchester.ac.uk (R. Feng).
https://doi.org/10.1016/j.compgeo.2022.104964
Received 21 January 2022; Received in revised form 4 August 2022; Accepted 5 August 2022
Available online 22 August 2022
0266-352X/© 2022 The Author(s). Published by Elsevier Ltd. This is an open access article under the CC BY license (http://creativecommons.org/licenses/by/4.0/).

### Page 2

R. Feng et al.                                                                                                                 Computers and Geotechnics 151 (2022) 104964

et al., 2017, Senthilkumar et al., 2018). It was found that the coupled     solve hydro-mechanical problems involving large deformations and
scheme was able to produce an accurate prediction of the wetting front     free-surface flows, their applications to the study of rainfall-induced
and better assessment of slope stability when compared to uncoupled     slope instability are less common. Zhang et al. (2016) made the first
scheme (Qi and Vanapalli, 2015, Oh and Lu, 2015).                      attempt to adopt a double layer approach within SPH for modelling
   In routine practice, conventional mesh-based methods (e.g., finite-     rainfall-induced failure of an unsaturated dike. The rainfall event was
element method) are usually adopted to solve the coupled governing    reproduced by generating rain particles with controlled time interval
equations for the slope stability analysis especially if the failure trig    and velocities. Though satisfactory results were achieved in comparison
gering mechanism is of interest. Typical examples of the numerical     with experimental observations, the algorithms for treating boundary
programs for such types of analysis include Plaxis (Galavi, 2010), Geo     condition were still cumbersome, and the computational costs were
studio (Krahn, 2012), and ICFEP (Potts et al., 2001). However, such    demanding. Another difficulty associated with the use of a double layer
methods may not be suitable to simulate the large deformation achieved    approach is the treatment of unsaturated soils in the capillary region.
in the post-failure stage since they tend to become unstable, and suffer    The kernel interpolation was commonly used to estimate the degree of
from mesh distortions problems. Nevertheless, the post-failure analysis     saturation once a water particle was found at the kernel support of a soil
of a slope is of particular interest for disaster prevention and mitigation     particle (e.g., Zhang et al., 2016, Bui and Nguyen, 2017). As a result, the
planning when assessing the potential consequences of landslides (e.g.,     dimensions of the capillary rise were linked with the radius of the kernel
run-out distance, landslide volumes and its potential impact on infra     support (or the smoothing length). The reliability of this treatment re
structure). Therefore, there is a need to investigate novel numerical    mains unclear as the smoothing length is a numerical parameter con
schemes that can capture the initiation of the slope failure as well as its      trolling the accuracy of SPH interpolations. Wang et al. (2018) proposed
post-failure response.                                                a single layer two-phase coupled MPM formulation to model the rainfall-
   The emergence of meshless methods provides a promising solution    induced slope collapse. The  infiltration process was simulated by
for such analyses owing to their ability to incorporate the coupled multi-     assigning zero pore water pressure to the free-surface particles. How
physics and capability of simulating large deformations. Examples of     ever, since the particles with prescribed zero pressure were allowed to
meshless methods used for geotechnical applications include: smoothed    move outside of the boundary regions, the prescribed pressure condi
particle hydrodynamics (SPH), the material point method (MPM), and     tions along the free surface could not be maintained throughout the
the particle finite element method (PFEM). Among them, SPH can be     simulation. Consequently, an additional surface boundary algorithm
regarded as a truly meshless technique, whereas the other methods are    was required to identify the locations of free-surface boundary cells/
still, to some extent, dependent of the background mesh. It is also worth     nodes/particles at each time step, and to re-apply pressure conditions for
mentioning the discrete element method (DEM), which is another pop     those particles (e.g., Bandara et al., 2016, Ceccato et al., 2021).
ular numerical method in geomechanics to treat large deformation.       So far, the majority of particle-based continuum approaches for
However, compared to continuum-based methods such as SPH, the DEM     coupled hydro-mechanical problems tend to focus on the prediction of
simulation  is computationally demanding, especially  for  real-scale     kinematics, resulting in reasonable predictions of the sliding surface and
problems involving millions of particles. SPH was originally invented     evolution of surface morphology (Bui and Nguyen, 2021). However,
to solve astrophysical problems by Gingold and Monaghan (1977), and     numerical oscillations and noise in the stress field were an issue in the
Lucy (1977). Following the success of SPH application to fluid and solid     post-failure stage (Wang et al., 2018), which could possibly undermine
mechanics (Libersky et al., 1993, Monaghan, 1994), more and more     the accuracy of the simulation and consequently reduce the predictive
applications of SPH have been made in recent years for a vast range of     capability of the model, especially for the applications involving soilengineering problems, such as fracture of solids (Benz and Asphaug,     structure interactions, in which accurate predictions of forces/stress
1995), multi-phase flow (Colagrossi and Landrini, 2003), plastic flow     are of particular importance.
(Zhou et al., 2007), and geophysical flows (Bui and Nguyen, 2021).           This work develops a new SPH formulation for unsaturated soils to
   For the coupled hydro-mechanical problems, two types of SPH     study the slope instability induced by rainfall infiltration. The singleframework are available to describe the soil–water interactions. The first     layer approach is adopted as it is known to be well suited for solving
framework is the so-called two-phase double layer approach, which uses     multi-physics problems. It is the first time for the single-layer formula
two layers of SPH particles to represent the soil phase and water phase     tion applied in SPH to analyse the coupling of unsaturated seepage flow
respectively. The fluid particles and solid particles are overlapped, and    and soil deformation. The advantages of the proposed method compared
move according to their own governing equations. The second frame     to  existing  double-layer SPH  formulations  include  the improved
work is the two-phase single layer approach, in which the computational     computational efficiency, the reasonable description of the capillary
domain is discretized into a single set of particles carrying the infor     region, a simple implementation of hydraulic boundary conditions, and
mation of both soil and water phases that moves according to the ma    more importantly a noise-free stress treatment. A first-order consistent
terial velocity of the soil phase. The two-phase double layer formulation     wall boundary treatment developed by Feng et al. (2021) is extended for
is able to reproduce the fluid regime both inside and outside of the     the boundary conditions of the coupled soil–water problem, including
porous material and can be extended to a non-laminar fluid flow. It has     non-slip/free-slip conditions for both soil and water phase. It is shown
been successfully used in several applications, including simulations of     that the zero-pressure boundary conditions are implicitly satisfied using
liquefied soils (Huang et al., 2013), wave-porous structure interaction     the proposed formulation without the need of a surface boundary al
(Ren  et  al., 2014), seepage  failure  of  dikes  subjected  to water     gorithm, thus simplifying the model’s implementation. A new stress
impoundment and rainfall (Zhang et al., 2016), stability analysis of soil     diffusion term is investigated to smooth out the numerical noise in the
slope (Bui et al., 2011, Zhang et al., 2019), submerged granular column      stress field at large deformation. Compared to the formulation by Feng
collapse (Wang et al., 2017) and flow through porous media (Bui and     et al. (2021), which is limited to the gravity-dominated failure (e.g.,
Nguyen, 2017, Peng et al., 2017). However, the use of the two-phase     granular flow), the new method is more general and thus is applicable
double layer formulation is computational demanding, thus hindering     for diverse scenarios involving the rainfall-induced landslides, seepageits application to large-scale problems. By contrast, the use of two-phase    induced dam  instabilities, or any other coupled hydro-mechanical
single layer approach (e.g., Pastor et al., 2009, Blanc and Pastor, 2013) is     problems. The validity of the present numerical scheme is examined
computationally efficient. With the single layer approach, the boundary    through the infiltration test and drainage test; both cases show good
conditions, such as infiltration/evaporation or hydraulic head bound    agreement with the analytical solutions and experimental data. Finally,
aries, can be easily implemented and it is straightforward to account for     the proposed model is applied to study the rainfall-induced slope failure.
coupled multi-physics processes (Pinyol et al., 2018).                       Results show that the failure process from initiation to post-failure is
   Although numerous mesh-free formulations have been proposed to     well captured by the proposed model.

                                                                        2

### Page 3

R. Feng et al.                                                                                                                 Computers and Geotechnics 151 (2022) 104964

   The remaining part of this paper is organised as follows: In Section 2,     2.1. Mass balance equations
the two-phase coupled hydro-mechanical formulation for saturated/
unsaturated soils and the adopted mechanical/hydraulic constitutive       The material derivative with respect to the soil phase takes the
models are presented. This is followed by the SPH discretisation of     following generic form,
governing equations together with the numerical implementation of
initial/boundary condition, development of a numerical diffusion term,     Ds(⋅) = ∂(⋅) + vs⋅∇(⋅),                                                (1)
and time stepping scheme, given in Section 3. The validity of the pro      Dt      ∂t
posed methodology is assessed in Section 4 where several validation    where superscript s denotes soil phase, and vs is the soil phase velocity.
cases, including infiltration test and drainage test of soil columns, are       The mass balance equation of soil phase can be written as,
presented. In Section 5, the applications of the present SPH scheme to
study the rainfall-induced slope failure are investigated. Section 6 pro     ∂nsρs + ∇⋅(nsρsvs) = 0,                                             (2)
vides a discussion of the limitations of the present model with sugges        ∂t
tions for future works. Finally, some conclusions are drawn in Section 7.                                                              where ρs is intrinsic density of soil grains, ns is the volumetric fraction of
                                                                                        soil phase, and it can be related to porosity n by ns = 1 – n.2. Governing equations                                                                  Assuming the soil grain to be incompressible (hence ρs is a constant)
                                                              and neglecting the spatial variation of porosity, Eq. (2) can be rewritten   Unsaturated  soils  are  generally  constituted by  three  phases,                                                                                     as,including soil phase, s, water phase, w, and air phase, a, as shown in
Fig. 1. The soil phase formulates the soil skeleton, while the water and    Dsn = (1 −n)∇⋅vs.                                                   (3)air phase fill the voids between the soil particles. In many applications,     Dt
the presence of the air phase can be considered in a simplified way by       The mass balance equation of water phase is given by,
assuming that the air pressure is zero and the air density is negligible
compared to those of the water and soil phases (Bandara et al., 2016,     ∂nwρw + ∇⋅(nwρwvw) = 0,                                          (4)
Wang et al., 2018, Lei et al., 2020, and Ceccato et al., 2021). Thus, the        ∂t
governing equations for air phase can be omitted and the three-phase                                                              where ρw is the water density, nw is the volumetric fraction of watermixture can be described using a two-phase model. Unsaturated con                                                                        phase, which can be related to porosity by the degree of saturation Sditions are taken into account by considering the evolution of the water                                                                       using nw = nS, and vw is the water velocity.content and the presence of capillary pressure.                                                                            Including Eq. (3) into Eq. (4), and rearranging the obtained equation   The two-phase formulations for the unsaturated soil can be derived                                                                           gives (Ceccato et al. 2021),based on the mixture theory as described by Wang et al. (2018), Lei et al.
(2020), Ceccato et al. (2021). Alternatively, the formulation can be      Ds(ρwS)                                                                    n     = ∇⋅(ρwnSvsw) −Sρw∇⋅vs.                                  (5)derived based on Biot’s formulation (Biot, 1941) and its extensions        Dt
(Zienkiewicz et al., 1990) as in the works by Sheng et al. (2003), Khalili                                                                                                           If the spatial variation of water density is further considered to be
et al. (2008), Schrefler and Scotta (2001), Bandara et al. (2016). In this                                                                              negligible (e.g., Lei et al., 2020), taking into account the definitions of
study, the mixture theory is adopted, the governing equations are ob                                                                    seepage discharge, i.e., qw = nSvws, Eq. (5) can be rewritten as,tained based on the mass balances of both water phase and soil phase,
dynamic momentum balance of the mixture, the linear momentum    −n ∂S Dspw + nS 1 Dsρw + S∇⋅vs = −∇⋅qw,                         (6)
equation, i.e., Darcy’s law, of the water, and the hydraulic/mechanical         ∂pc  Dt      ρw  Dt
constitutive relationships. The material coordinates are assumed to be
                                                                      = pa-pw, which is taken asattached to the soil skeleton and the motion of fluid flow is described    where pc is the suction pressure, defined as pc
with respect to the soil skeleton. The derivation of the governing     -pw since the air pressure pa is assumed to be zero in the analysis. Note
equations is based on the following sign convention: (i) the compressive     that equation (6) has three storage terms on the left-hand side, related to
stress and strains are negative for the soil phase; (ii) pore water pressures     retention curve, water compressibility, and soil skeleton compress
in the water phase are assumed to be positive in compression; (iii) the      ibility, respectively, from left to right.
flow discharge is considered to be positive for inflow.                          In this study, density rather than pressure is taken as the state vari
                                                                               able.  This  selection  is  consistent  with  the weakly  compressible
                                                                   assumption of the water, in which water density shows a slight variation
                                                              due to the movement of water (Monaghan, 1994). The equation of state

                           Fig. 1. Representation of unsaturated soils (the hatched regions in the water phase represent the air phase).

                                                                        3

### Page 4

R. Feng et al.                                                                                                                 Computers and Geotechnics 151 (2022) 104964

is adopted to link density with pressure. The following relationship is                                                                          ρmas = ∇⋅σ + ρmb.                                              (13)established for the first term on the left-hand side of Eq. (6), given by,
                                                                The variation of hydraulic conductivity with respect to the degree ofDspw   Kw Dsρw   =                          ,                                                    (7)     saturation (or suction pressure) is governed by the hydraulic conduc Dt       ρw  Dt
                                                                                      tivity curve (HCC) given later in Section 2.4.
where Kw is the bulk modulus of water.
   Substituting Eq. (7) into Eq. (6), yields the equation of liquid density
                                                                                 2.3. Mechanical constitutive equationsderivative,
 (      )
         ∂S  Dsρw                                                                The total stress tensor σ is calculated using the concept of Bishop’sn S −Kw           = −ρw(∇⋅qw + S∇⋅vs).                          (8)
          ∂pc   Dt                                                              effective stress for unsaturated soils, taking the form,

                                                                                                                                                                                                                                                                            ′   The derivative of the saturation degree with respect to the suction     σ = σ −χpwI,                                                  (14)
pressure is governed by the soil–water characteristic curve (SWCC)
given later in Section 2.4.                                                   in which σ′ is the effective stress tensor, χ is an effective stress parameter
    It is noted that the final formulations of the mass balance equation     that varies from 0 to 1 to account for the dry to fully saturated condi
for water phase, i.e., Eq. (8) are the similar to that presented by Bandara      tions; for convenience, the value of χ can be taken equal to the degree of
et al., (2016) if the Biot’s coefficient is set to 1, and similar to that based     saturation S; I is the unit vector.
on the mixture theory as in Lei et al., (2020). Differences from other        In this study, the two stress variables σ′ and pw are evaluated sepa
established formulations, such as those by Gatmiri et al. (1998), Sheng      rately. The effective stress is computed from strain increment based on
et al. (2003), Khalili et al. (2008), Tsiampousi et al. (2017a) lie in the     the elasto-plastic analysis, while the pore pressure is computed from the
expressions of the storage term related to soil skeleton compressibility or     density variation assuming the pore fluid is weakly compressible. The
retention curve. In addition, the formulation of mass balance equation is      stress increment is calculated by,
consistent with the adopted SWCC model where the degree of saturation                          ′
is solely related to the suction pressure, as shown in Tsiampousi et al.    Dσ = DepDε                                                    (15)                                                                    Dt       Dt,(2017a,b). However, Eq. (8) should be modified to implement more
complex SWCC models, such as those that consider the effect of volume                                                              where Dep is the elasto-plastic stiffness tensor, which depends on thechange on the degree of saturation (See Tsiampousi et al., 2017a).                                                                              constitutive model adopted, ε is the strain tensor. The elastoplastic
                                                                              constitutive model is used in present analysis with Drucker-Prager yield2.2. Momentum balance equations                                                                                   criterion, in which the yield function and plastic potential function are
                                                                      given by,
   The momentum conservation for the water phase can be written as,       √̅̅̅̅
                                                                                                                                    (16a)ρwaw = −∇pw −f d + ρwb,                                           (9)        f = αϕI1 +   J2 −kc,
                                      √̅̅̅̅
where aw is the water acceleration, fd is the drag force exerted on solid    g = αψI1 +   J2 ,                                              (16b)
phase which describes the solid–fluid interaction, pw is the pore water
pressure, and b is the body force.                                   where I1 and J2 are respectively the first principal stress invariant and
                                                                                            αϕ and kc are Drucker-Prager constants,   The flow within the porous material is assumed to be laminar and     the second deviatoric stress;
                                                                                                       ϕstationary. Thus, the drag force term is governed by the Darcy’s law,    which can be related to Coulomb’s material constants c (cohesion) and
taking the following form,                                                    (internal friction) according to,
    nwγw
f d =          (vw −vs),                                             (10)     αϕ = √̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅tanϕ        ,                                           (17a)
    K                                                                   9 + 12tan2ϕ
where K is the hydraulic conductivity at a given degree of saturation S               3c
and γw is the unit weight of the water.                                             kc = √̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅9 + 12tan2ϕ,                                           (17b)
   The momentum conservation for the mixture is given by,
                                                                                                             ψ innsρsas + nwρwaw = ∇⋅σ + ρmb,                                   (11)     and, αψ is a dilatancy factor. Its value is related to the dilation angle
                                                                  a similar manner to that between αϕ and friction angle φ (Bui et al.,
where as is the soil acceleration, and ρm = nsρs + nwρw is the density of    2014, Nguyen et al., 2017).
the mixture and σ is the total stress tensor.                            To account for the decrease of strength due to the large deformations
   The above momentum equations are established based on the ve    developed at the post-failure stage, the cohesion is assumed to decrease
locities of the soil phase and the velocities of water phase, in which the     exponentially with the plastic strain according to the non-linear cohe
dynamic terms for both the water phase and soil phase are taken into     sion-softening relationship (Bui et al., 2021),
account. In this study, to simplify the formulation and for the conve                             (       )                                                                                c(κ) = cr +  cp −cr e−ηcκ,                                        (18)nience of the wall boundary treatment, the Darcy’s velocity qw and soil
velocity vs are taken as primary unknown instead of water velocity vw.                                                              where cp and cr denote the peak and residual cohesion, respectively. ηc is   Under the assumption that the relative acceleration of water with                                                                        the softening coefficient that controls the rate of strength degradationrespect to the soil skeleton is neglected and rearranging Eq. (9), the                                                              and κ is the internal variable, which is related to the equivalent plasticmomentum equations for water phase and the mixture are respectively                                                                       shear strain tensor according to,
given by,                                √̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅
                                                                          2    K                                                                                                                                       (19)qw =             [ −∇pw + ρw(b −as) ],                                   (12)     dκ =   3 dep : dep ,
     γw
                                                              where dep is the deviatoric plastic strain increment.and,                                                                               In the present work the strain-softening response is modelled for the
                                                                     cohesion strength only. Yet, the same strain-softening response can be

                                                                        4

### Page 5

R. Feng et al.                                                                                                                 Computers and Geotechnics 151 (2022) 104964

extended to the angle of shearing resistance using the formulation pre     3. Numerical implementations: Two-phase single layer
sented in Bui et al. (2021). It is also worth mentioning that meshless    formulation
approaches, such as SPH, have a distinct attraction in comparison to
traditional mesh-based approaches with their ability to handle large     3.1. SPH discretization
deformations efficiently. This advantage provides benefits in predicting
phenomena such as strain-softening since the strain-softening behaviour       The applied the governing equations are summarised as follows,
of soils is linked to the post-failure that naturally involves large de                                                                  Dsn
formations. The use of meshless methods therefore enables the strain-     = (1 −n)∇⋅vs,                                            (24a)
softening at post-failure to be easily simulated without extra computa     Dt
tional effort (such as coupling with another methodology or a remeshing    (      ∂S ) Dsρw                                                                    n S −Kw      = −ρw(∇⋅qw + S∇⋅vs),                     (24b)technique). A typical example is the simulation of retrogressive slope               ∂pc   Dt
failure of clayey slopes, which is challenging for mesh-based methods
but can be easily achieved in meshless methods (e.g., Wang et al., 2016,       K                                                                      qw =     [ −∇pw + ρw(b −as) ],                                  (24c)Bui et al., 2021).                                                               γw
   Compressibility is introduced such that the pressure can be linked to
density. A compressible equation of state (EoS) presented by Morris et al.     ρmas = ∇⋅σ + ρmb.                                            (24d)
(1997) is adopted to calculate pressure as,                                                                               In SPH, the approximation of gradient of a scalar field f and diver
pw = c20(ρw −ρw0),                                              (20)    gence of a vector field f can be defined as (Mayrhofer et al., 2013),
where ρw0 is the reference density of the water and c0 is the numerical     〈∇f〉i = ∑N  mj ( fj + fi )∇iWij,                                    (25a)
speed of sound. The bulk modulus of water Kw for Morris EoS is given by,                  j=1 ρj
Kw = c20ρw0.                                                     (21)     ∑N  mj (      )                                                                                 〈∇⋅f〉i =  −            f i −f j ⋅∇iWij,                              (25b)
                                                                                                                     j=1 ρj2.4. Hydraulic constitutive equations
                                                              where 〈…〉stands for the SPH interpolation, the subscript i and j denote   In addition to the mechanical constitutive model, the constitutive                                                                        the interpolating particle and its neighbours, respectively, Wij = W(xi-xj,relationship between the degree of saturation and the suction pressure is                                                                           h) and fj = f(xj) are respectively the value of the kernel function W andneeded to complete the governing equations. This  is given by the                                                                        the function f at the particle j with the position xj, N is the number ofsoil–water characteristic curve (SWCC) for a particular soil. Two alter                                                                                 particles distributed in the support domain, and mj is the mass of thenative models,  i.e.,  linear model and Van Genuchten model, are                                                                                particle  j. The reader is referred to Violeau (2012) and Violeau andconsidered in present analysis, whose formulations are given by Eqs.                                                                    Rogers (2016) for more detail on the derivation of the discrete SPH(22a) and (22b), respectively,
  ⎧                                                                      operators.
  ⎨    Smax        pc⩽0                                         By using the SPH  gradient operator and divergence operator
S =       Smax −avpc  0 < pc < pcs ,                                (22a)     expressed in Eqs. (25a) and (25b), and the Bishop’s effective stress  ⎩
            Smin         pc⩾pcs                                             formulation expressed in Eq. (14), the discretised form of Eqs. (24a) -
                                                                     (24d) takes following form, where the indicial notation is applied for
               ⎡  (  ) 1 ⎤−λ                                                     1−λ                                    convenience to represent the equations, in which α and β stand for the
S = Smin + (Smax −Smin)⎣1 +                                 pc   ⎦   ,                       (22b)     Cartesian coordinates,                                          pref
                                                          〈dn 〉    ∑                                                                                                  N  mmj (     ) ∂Wij                                                =  (ni −1)          vαi −vαj           ,                       (26a)where av, λ, and pref are fitting parameters, Smin is the residual saturation        dt     i                 j=1 ρmj            ∂xαi
degree, Smax is the maximum saturation degree, and pcs is the threshold
                                 ∑N  mmj (      ) ∂Wijsuction value to reach the residual saturation degree, whose value is    〈dρw 〉  (      ∂S )−1 ρwi (
                                                                                                                                                                        wi −qαwj                                                                                                                                   ∂xαiequal to pcs = (Smax - Smin)/ av.                                                       dt      i =  S −Kw ∂pc    i   ni    j=1 ρmj  qα   To take into account the effect of the degree of saturation on the                                                                          )       (26b)
hydraulic conductivity of the soil, the permeability of the unsaturated             ∑N  mmj (     ) ∂Wij
                                                                                                                                                                                                                             ,                                                                                                                                    vαi −vαjsoil is expressed using the relative hydraulic conductivity Krel, which is                                  +Si                                                                                                                                       ∂xαi                                                                                                                                                     j=1 ρmjdefined as the ratio of the hydraulic conductivity at a given degree of
                                                (                                                                      )saturation to the saturated hydraulic conductivity, Krel = K/Ksat. The
                                                                        〈  〉    Ki                                                                                 1 ∑N  mmj (      ) ∂Wijhydraulic conductivity curve (HCC) for linear relation model and Van      qαw   i =         −                 pi + pj   + gαi −aαsi    ,              (26c)
Genuchten model are given by Eqs (23a) and (23b), respectively,                 g      ρwi  j=1 ρmj          ∂xαi
   ⎧
          1                   pc⩾0   ⎪⎪⎨               (             ) pc
Krel =         Kr                            pcr  0 <                         pc < pcr  ,                                (23a)                     rel                                                                                                                                                                          (                                                                            1 ∑                                                                                                      1 ∑                                                                                           N mmj                                                                                                       ) ∂Wij                                                                                                                         N mmj                                                                                                                                                 ∂Wij   ⎪⎪⎩                                                                                〈dvα                                                                                                                                                                                                      −                                                                                                                                                         (Sipi + Sjpj)                                                                                      σ ′ αβi + σ ′αβj                                                                                                                                           s 〉i =                                                                                 + gαi ,          Kr                     pc⩾pcr                                                                                        dt                      rel                                                                                                                                              ∂xαi                                                                                                  ρmi                                                                                                        ρmj                                                                                                                                    ρmi                                                                                                                                       ρmj                                                                                                                     j=1                                                                                                                                                            j=1                                                                                                                   ∂xβi
   √[̅̅         (           ]2                                                                                                         (26d)
Krel =  S 1 −  1 −S1/λ)λ    ,                                   (23b)
                                                              and the position of the particles is updated according to the following
                                                                         equation,where pcr is the value of suction at which the relative permeability is
reduced to the residual permeability Krelr  . The value of Krelr  can be taken     dxαi   〈  〉                                                                                                                                                    s  i,                                                   (26e)as 10-4 as suggested by Galavi (2010).                                            dt =  vα
                                                              where mm represents the mass of the mixture.

                                                                        5

### Page 6

R. Feng et al.                                                                                                                 Computers and Geotechnics 151 (2022) 104964

                                                                                     hvαijxαij                                                                                                                  μij =                                                        (28b)                                                                                         xαijxαij + η2,

                                                                                                                             cij = 0.5(ci + cj),                                               (28c)

                                                                                                                     ρij = 0.5(ρi + ρj),                                             (28d)

                                                              αП is the viscous constant controlling the magnitude of dissipation and
                                                                    normally takes values of 0.1 (Bui and Nguyen, 2021), η = 0.1 h is the
                                                                    numerical parameter introduced to avoid numerical singularity and c is
                                                                        the speed of sound. For soil materials it is computed by,
                                    √̅̅̅̅̅̅̅̅̅̅
                                                                                                           ci =   Ei/ρi ,                                                    (29)

                                                              where E is Young’s modulus of the soil.
Fig. 2. Illustrative diagrams of boundary conditions for a slope subjected to
rainfall-induced infiltration.
                                                                                 3.2. Boundary conditions

                                                                             Specifying conditions on the boundaries of a problem is an essential
                                                              component of the numerical analysis to constrain the solution. Fig. 2
                                                                          presents the typical boundary conditions used to simulate the rainfall
                                                                                     infiltration in a slope; these include  infiltration and impermeable
                                                                     boundaries for the water phase, and free-roller/fully-fixed boundaries
                                                                                for the soil phase. In general, the applied boundary conditions can be
                                                                       divided into two types, i.e., solid boundary conditions and free-surface
                                                                boundary conditions.

                                                                              3.2.1 Solid boundary condition

                                                    A well-recognised issue of SPH is the truncation of kernel interpo
                                                                               lation support of the particles near the boundary (Vacondio et al., 2020).
                                                             The  truncated  interpolation may  lead  to  inaccurate  results and
                                                                       unphysical effects. These can be addressed by introducing boundary
                                                                                 particles to complete the kernel support of the domain particles near the
            Fig. 3. Generation of the interpolation ghost nodes g.              boundary. Herein, a particle-based boundary methodology proposed by
                                                                Feng et al. (2021) for the simulation of granular flow is extended for the
                                                                    coupled soil–water problem to impose the free-slip/non-slip conditions
                                                             on the solid boundaries.
   Due to the zero-energy mode inherent to the SPH method, the so        In this treatment, fixed dummy boundary particles, b, are created
lution is prone to unphysical oscillations and numerical instabilities     near the boundaries to characterize the physical boundary of the
when the numerical dissipative term is not included in the governing     simulated domain, and for each boundary particles, a ghost node, g, is
equations. This limitation can be overcome by introducing an artificial     mirrored into the domain perpendicular to the boundary surface to
viscosity term into the momentum equation. This term was firstly pro     interpolate field variables from surrounding domain particles,  j, as
posed by Monaghan (1992) and has been found to stabilise the numer    shown in Fig. 3. More details of the implementation can be found in Feng
ical algorithm. The  artificial viscous term  is introduced  into the     et al. (2021).
momentum equation as shown below,                                 The value and gradient of a field property f (i.e., fluid density and
   ∑N          ∑N                                 stress) of the ghost nodes are computed using the first order consistent
                               ′αβ                                                  i + σ ′αβj + Πijδαβ) ∂Wij −      mmj  (Sipi             SPH interpolation proposed by Liu and Liu (2006) according to,〈dvα 〉i =     mmj  (σ
  dt        j=1 ρmiρmj                      ∂xβi      j=1 ρmiρmj                        ⎡ ∑     ⎤
                ∂Wij                                                                                       fjWgjVj     + Sjpj)   + gαi ,                                        (27)                                                       j
                ∂xαi                                         ⎡   ⎤ ∑
                                                                                                                         fg            fj∂xWgjVj
                            ∑where,                                                                                            ∂xfg                    j                                                                                                                                                                           ,                                    (30)                                                                            Ag⋅ ⎢⎢⎣ ∂yfg ⎥⎥⎦=                                                                                                          fj∂yWgjVj  ⎧
                                                                                                                                                                                                                                   j                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             ⎥⎥⎥⎥⎥⎥⎥⎥⎥⎦  ⎪⎨ αΠcijμij   vαijxαij < 0                                                                         ∂zfg                              ⎢⎢⎢⎢⎢⎢⎢⎢⎣ ∑
                                                                                                            fj∂zWgjVj =Π              ρij                     ,                                      (28a) ij                                                                                                                                                                                                                                   j  ⎪⎩
         0      vαijxαij > 0
                                                              where the renormalisation matrix Ag is,

                                                                        6

### Page 7

R. Feng et al.                                                                                                                 Computers and Geotechnics 151 (2022) 104964

   ∑   ∑(      )   ∑(      )   ∑(      )
     ⎡    WgjVj              xj −xg WgjVj            yj −yg WgjVj             zj −zg WgjVj ⎤
   ∑j   ∑j (     ∑j (     ∑j (            ∂xWgjVj          xj −xg )∂xWgjVj          yj −yg )∂xWgjVj          zj −zg )∂xWgjVj
Ag = ∑j   ∑j   (     ∑j   (     ∑j   (                           .                                                        (31)            ∂yWgjVj         xj −xg )∂yWgjVj          yj −yg )∂yWgjVj          zj −zg )∂yWgjVj                                         ⎢⎢⎢⎢⎢⎢⎢⎢⎣ ∑                         j   ∑j   (     ∑j   (     ∑j   (                                                                                                    ⎥⎥⎥⎥⎥⎥⎥⎥⎥⎦            ∂zWgjVj          xj −xg )∂zWgjVj          yj −yg )∂zWgjVj          zj −zg )∂zWgjVj
                         j                              j                                                  j                                                  j

                                                                   second approach is used whereby a zero-pressure boundary condition is
   The fluid density and stress of the boundary particle denoted by     applied along the free surface. This approach simulates the case of
subscript b is then evaluated according to the interpolated values and     excessive amount of rainwater that results in ponding and water runoff,
gradients at ghost nodes using a Taylor series expansion given by,          resulting in a certain pore water pressure maintained at ground level. It
                    (                           (                           (                                         is an extreme scenario occurring during heavy rainfall events, when theσαβb = σαβg +  xb −xg )∂xσαβg +  yb −yg )∂yσαβg +  zb −zg )∂zσαβg  ,         (32a)                                                                                    rainfall intensity is higher than the saturated hydraulic conductivity
                 (                         (                         (                                     (Martinelli et al., 2020), and the suction pressure at the ground surfaceρb = ρg +  xb −xg )∂xρg +  yb −yg )∂yρg +  zb −zg )∂zρg.            (32b)                                                            become zero. Examples of the application of this type of boundary
                                                                        condition for landslide failures are studied by Cuomo and Della Sala   To enforce a no-slip boundary condition for the water phase and soil
                                                                        (2013), Wang et al. (2018), Lee et al. (2019), and Lei et al. (2020).phase (or impermeable boundary  for water phase and  fully-fixed
                                                                However, it will be demonstrated later that with the present SPH forboundary for soil phase), the boundary particles obtain the velocity of
                                                                        mulations, zero-pressure boundary conditions are implicitly satisfied atghost nodes with reversed direction,
                                                                        the free surface  (i.e., natural boundary condition) and there  is no
vαb = −vαg,                                                    (33a)     requirement of applying zero-pressure to the free-surface particles (e.g.,
                                                     Wang et al., 2018) or implementing a surface boundary algorithm (e.g.,
qαwb = −qαwg,                                                 (33b)    Bandara et al., 2016), which simplifies the boundary treatment.
                                                                               In addition, periodic boundary condition (PBC) is also used in this
where the velocity at the ghost nodes is calculated using Shepard cor     study (Domínguez et al., 2021) for the simulation of 1-D infiltration test
rected summation,                                               and Liakopoulos’s drainage test to produce a uniform seepage flow, as
  ∑                                                                        described in Section 4. The PBC is achieved by allowing particles near         jvαj WgjVj
vαg = ∑           ,                                               (34a)     the lateral open boundary to interact with the particles near the com
         jWgjVj                                                         plimentary lateral open boundary on the other side.
   ∑
          jqαwjWgjVjqαwg = ∑           .                                            (34b)           jWgjVj                                                                 3.3.  Initial conditions
   For the free-slip boundary condition, the off-diagonal components of       Reasonable initial conditions are required to achieve reliable and
the stress tensor found at the ghost nodes are reversed to create a fric     accurate results. In this study, the initial stress distributions are gener
tionless condition along the boundaries as follows,                        ated by applying gravity to the soil domain with the given pore pressure
   ⎧                       (                                                                                distribution, in which the suction pressure is calculated from the initial
   ⎨ σαβg +                xb −xg )∂xσαβg + ( yb −yg )∂yσαβg + ( zb −zg )∂zσαβg  α = β                                                                   water content using the soil–water retention properties. To achieve fastσαβb =                                                                                               ,   (35)
   ⎩                    −σαβg                   α ∕= β               stabilization in the stress field, a damping term is introduced into the
                                                     momentum equation (e.g., Bui and Fukagawa, 2013), according to,
while the fluid density (or pressure) remains the same as those for no-    ∑N          ∑N
slip boundary using Eq. (32b).                                                〈dvα 〉i =     mmj  (σ ′αβi + σ ′αβj + Πijδαβ) ∂Wij −      mmj  (Sipi
                                                                                                                 j=1 ρmiρmj                      ∂xβi      j=1 ρmiρmj   To impose the free-slip condition, the velocities of boundary particles        dt
are constructed using,                                    + Sjpj) ∂Wij + gαi + dαi ,                                    (37)
                                                                                                ∂xαivαb = vαg −2vαg.n,                                                (36a)
                                                              where d is the damping force term given by,
qαwb = qαwg −2qαwg.n.                                            (36b)      √̅̅̅̅̅̅̅
   The soil density and porosity of boundary particles are set to remain     dαi = −ξ  E vαi ,                                               (38)
constant to the reference density ρ0 and reference porosity n0 during                ρh2
simulation in current application.                                                                              in which, ξ, is the damping coefficient, and its value is commonly taken
                                                                          as 0.02 (Bui and Fukagawa, 2013).   3.2.2 Infiltration free-surface boundary condition                                                               Once the state of equilibrium is achieved and the initial conditions
                                                                         are obtained, the damping term is “switched off” and the water infil   For modelling the process of water infiltration in a slope, the infil                                                                               tration is allowed.tration boundary condition needs to be applied to the free surface of the
computational domain. The infiltration boundary can be achieved by
assigning a  prescribed  discharge, or  pressure, on the  infiltration     3.4.  Stress diffusive term
boundaries, or by using a dual boundary condition that enables an
automatic change between the discharge-based condition and the      One of the key challenges of the application of SPH, or other particle
pressure-based condition (e.g., Smith et al., 2008). In this study, the    methods such as MPM, to geomechanics problems is the presence of

                                                                        7

### Page 8

R. Feng et al.                                                                                                                 Computers and Geotechnics 151 (2022) 104964

                                                                        the modified diffusion operator, the stress gradient at geostatic condi
                                                                             tion is required for restoring consistency at the free-surface as shown by
                                                                Feng et al. (2021). This is convenient for a single-phase problem or total
                                                                                    stress analysis in which the stress is the only state variable, but for a two-
                                                                   phase coupled problem, as the stress profile of unsaturated soils is
                                                                         influenced by the soil hydraulics and hydrological conditions,  it  is
                                                                                       difficult to obtain a unique solution of stress gradient in static condition
                                                                                for the stress diffusion operator. In this study, following the method
                                                                       presented by Antuono et al. (2010), a general type of diffusion term is
                                                                     formulated for the purpose of diffusing stress for the coupled hydro-
                                                                   mechanical analysis, which reads,
                                                                                                                                                  (         )   (〈          〈     )
                                                                           ψαβij =  σαβi −σαβj  −1   ∇σαβ〉Lj +  ∇σαβ〉Li   ⋅xij,                   (41)                                                                                     2
                                                                               〈∇σαβ〉L                                                                                             〈∇σαβ〉L                                                              where                                                                                                                                                                                                                  j  and                                                                                                                                                                                                                                                          i  are the renormalised  stress gradients
                                                                        defined as,
                                                                        〈 ∇σαβ〉Lj = ∑( σαβj −σαβi )Li∇iWij mmj ,                            (42a)
                                                                                                                                                                                                                         j                      ρmj
                                (∑(      )        mmj )−1                                                                                     Li =         xj −xi ⊗∇iWij            .                             (42b)Fig. 4. Numerical configuration and boundary conditions used in the infiltra                                j                    ρmj
tion test case.

                                                                                 3.5. Time integration scheme

                                                                The stability of a numerical algorithm is dependent of the time
                                                                            integration scheme. In the present work, the time stepping scheme is an
                                                                                   explicit second-order predictor–corrector scheme (Crespo et al., 2015).
                                                                        This scheme predicts the evolution in time at the middle of the time step
                                                                                                     (i.e., predictor step); the obtained values are then corrected using the
                                                                  updated forces at half time steps (i.e., corrector step), followed by the
                                                                  computation of the values at the end of the time step.
                                                                  However, explicit time integration schemes are conditionally stable.
                                                            Commonly, the Courant–Friedrichs–Lewy (CFL) stability condition is
                                                                      introduced to prescribe the maximum allowable time step, in which the
                                                                                        critical time step needs to be less than the time for a compression wave
                                                                            to travel through the characteristic length of the discretized system, but
                                                                                for the two-phase problem, the influence of permeability K needs also to
                                                                 be accounted for (Mieremet et al., 2016). In this study, the length of time    Fig. 5. SWCC adopted in the numerical simulation of infiltration test.
                                                                            step is restricted by the CFL condition, the maximum force term, the
                                                                    numerical speed of sound, and the diffusion of seepage flow. The criticalnumerical oscillations and noise in the stress field when large de                                                                    time step is computed as (Feng et al., 2021, Lian et al., 2021),
formations are achieved, which may affect the accuracy of the numerical           (√ ̅̅̅̅̅̅̅̅̅̅̅ )
analysis. One simple way to improve the spurious stress field is to adopt      Δtf = min                                                                                                   h/|f i|   ,                                          (43a)                                                                                                                                                                                                             ithe stress diffusion algorithm proposed by Feng et al., (2021), which
requires including a diffusion term in the stress updating, taking form as,                                                                                   h
                                                                                     Δtcv = min                                                                                                                                                                       ,                                    (43b)                                                                                                                                                                                                               i                 hvαijxαijDσαβi                                                                                                                                                                                                                                                                                                                                                                                          ⃒⃒⃒ xαijxαij+η2 ⃒⃒⃒   = Dep ˙εαβi + Dαβi  ,                                            (39)                    cs + maxj Dt
                                                    (    )
                                                                                                                                                             ,                                           (43c)where Dep is the elasto-plastic stiffness matrix and Dαβi   is the stress      Δtsp = mini   γw h2cv2Kdiffusion term defined for each stress component as,
                                                                                                  )                                                                                                                                                           (    ∑                        xij⋅∇iWij    mmj                                                                                                       Δtcv, Δtf , Δtsp                                                                                                                                                                       ,                                    (43d)Dαβi = 2ζhc0               ψαβij                                                           ,                             (40)    Δt = C0min                                j         ⃒⃒xij ⃒⃒2 + 0.01h2  ρmj
                                                              where C0 is the Courant number,
where ζ is the diffusion coefficient and normally take values as 0.1. The       ( S   ∂S )
parameter ψji is the diffusion operator that has the dimension of the      cv = n   +       .                                               (44)
physical quantities to be diffused.                                        Kw   ∂p
   The idea behind Eq. (40) is to approximate the Laplacian of stress to       The implementation of the fully coupled hydro-mechanical model
achieve a smooth stress profile. The stress diffusion operator should be     described above is achieved in the CPU branch of open-source SPH code
constructed to restore the global convergence and consistency over the    DualSPHysics (Domínguez et al., 2021).
whole domain (Antuono et al., 2012). Feng et al. (2021) proposed a
stress diffusion operator modified from Fourtakas et al. (2019), and it     4. Validation cases
was shown that the formulated diffusion operator is able to smooth out
the stress profile with good accuracy and convergence. In order to adopt       The validity of the numerical scheme is examined in this section

                                                                        8

### Page 9

R. Feng et al.                                                                                                                 Computers and Geotechnics 151 (2022) 104964

Table 1                                                                   zero-pressure boundary condition  is implicitly satisfied at the top.
Material and hydraulic properties for the 1-D infiltration test.                   Gravity is not considered in this application. Once the seepage flow is
  Paramters                                  Unit                     Value          allowed, the wetting process starts at the top of the soil column. To
                                                                        obtain an analytical solution, the permeability is assumed to be con  h/dp                                     –                         1.8
  Courant number                           –                         0.2              stant. The linearized SWCC model expressed in Eq. (23a) is used, taking
  Soil density ρs                         kg/m3                 2100          Smax = 1.0 and Smin = 0.0. The illustrative diagram of the adopted SWCC
  Water density ρw                       kg/m3                 1000         model is shown in Fig. 5.
  Porosity n                                –                         0.3             The 1-D vertical water infiltration within a rigid unsaturated soil  Water bulk modulus Kw                   Pa                        8.0 × 106                                                             column can be mathematically expressed by,  Hydraulic conductivity K                 m/s                       5.0 × 10-3
 SWCC constant av                        Pa−1                      1.0 × 10-4

using an infiltration test and a drainage test of a soil column. Numerical
results are compared against available analytical solutions and experi
mental data.

4.1.  Infiltration test

   The infiltration test is used to examine the infiltration boundary
condition and the ability of the proposed scheme to solve the transient
unsaturated seepage problem. More specifically, the infiltration test
simulates the water infiltration along the top surface of a rigid unsatu
rated soil column (see Fig. 4). This test case has been used for validation
purposes by Yerro (2015) and Lei et al. (2020) since an analytical so
lution is available for comparison.
   The geometries and boundary conditions of the infiltration test are
presented in Fig. 4. The soil column is assumed to be initially unsatu
rated with a constant suction pressure of pc = 5 kPa. Periodic boundary                                                                                     Fig. 7. Convergence plot for the infiltration test: the normalised L2 norm errorconditions are applied to both sides to achieve one-dimensional water                                                                                      of the suction pressure at 10 s.flow. The bottom boundary of soil column is impermeable, while the

                                Fig. 6. Evolution of suction pressure along depth z (a) dp = 0.1, (b) dp = 0.05, and (c) dp = 0.02.

                                                                        9

### Page 10

R. Feng et al.                                                                                                                 Computers and Geotechnics 151 (2022) 104964

                                      ⎧
                                      ⎨  p(z, t) |t=0 = pc
                                                                                            p(z, t) |z=h = 0     ,                                           (47)                                      ⎩
                                                                                      ∂p(z, t)/∂z |z=0 = 0

                                                                        the analytical solution for Eq. (45) is equivalent to the solution of 1-D
                                                                          consolidation problem in saturated porous media, known as the Terza
                                                                               ghi’s solution. The dimensionless time T used for the analytical solution
                                                                                                is defined in the conventional way as,

                                                                                          Cit                                                             T =     .                                                        (48)                                                                                      h2
                                                                The model parameters used in the simulation are listed in Table 1.
                                                                  Three sets of particle resolutions of 0.1, 0.05 and 0.02 m are adopted,
                                                                              resulting  in  10, 20 and 50  particles  along  the column  height,
                                                                               respectively.
                                                                                      Fig. 6 shows the comparison of the suction pressure evolution against
                                                                        the analytical solutions for three particle resolutions, i.e., dp = 0.1, 0.05
                                                              and 0.02 m. Agreements between numerical and analytical results are
                                                                     achieved with the L2 norm error less than 5 %. The calculated suction
                                                                                 profile fluctuates when a large value of dp is used, resulting in slight
Fig. 8. Drainage test: schematic diagram of (a) the experimental configuration     deviations from the analytical solution near the top of the soil column.and (b) the numerical configuration.                                                                        This can be attributed to the local inconsistency near the free-surface of
                                                                        the enforcement the zero-pressure boundary condition, which become
                                                                          noticeable for a coarse resolution. For smaller dp, the solution convergesTable 2
Material properties and numerical parameters for the Liakopoulos’ test.          towards the analytical solution.
                                                                                      Fig. 7 shows the results from a convergence study on the suction  Paramters                                 Unit                    Value                                                                             pressure, from which it can be seen that a satisfactory order of conver
  h/dp                                     –                         1.3            gence of 1.604 is achieved.
  Courant number                          –                         0.2
  Artificial viscosity α                       –                         0.1
  Soil density ρs                         kg/m3                2000
  Young’s modulus E                      Pa                       1.3 × 106         4.2. Liakopoulos’s drainage test
  Poisson’s ratio ν                          –                         0.4
  Water density ρw                       kg/m3                1000            The drainage  test described by Liakopoulos (1964)  is used to
                                           –  Porosity         n                                                                 0.2975                                                                examine the validity of the proposed scheme for the coupling of unsat  Water bulk                                                                       2.0                                             × 107           modulus Kw                  Pa
  Hydraulic conductivity K                 m/s                     4.41 × 10-6      urated seepage flow and soil deformation. This case refers to the desa
                                                                            turation process of an initially fully saturated soil column due to gravity,
                                                              and has been investigated by Bandara et al. (2016), Wang et al. (2018)
∂p     ∂2p                                                     and Lei et al. (2020) to verify the implementation of coupled hydro-  = Ci                                                        (45)∂t      ∂z2,                                                         mechanical frameworks for unsaturated soils.
                                                                                      Fig. 8(a) shows a schematic diagram of the Liakopoulos’ test. Before
where z is the distance in the infiltration direction and the coefficient Ci     the experiment starts, a uniform water flow condition with zero pressure
can be written as,                                                        gradient is achieved by adding a constant water inflow at the top of the
     K                                                             specimen, after which the water inflow at top is stopped and the bottom
Ci =                 .                                                     (46)     drainage is opened to initiate the test. The moisture tension along the     nγwav
                                                                        height was monitored during the experiments.
   Considering the initial and boundary conditions, given by,                   Fig. 8(b) presents the initial and boundary conditions applied in the
                                                                           simulation. The initial suction pressure is set as zero across the domain

           Fig. 9. Comparisons of the hydraulic model used in simulation against the experiment data by Liakopoulos (1964): (a) SWCC and (b) HCC.

                                                                        10

### Page 11

R. Feng et al.                                                                                                                 Computers and Geotechnics 151 (2022) 104964

           Fig. 10. Comparisons between SPH results and experimental data: (a) pore water pressure with height (b) water outflow rate at the bottom.

                       Fig. 11. Comparison between predicted and experimental vertical displacement for the Liakopoulos’s drainage test.

                  Fig. 12. Illustrative diagram of the slope models: (a) Slope A with a deep soil cover and (b) Slope B with a shallow soil cover.

                                                                        11

### Page 12

R. Feng et al.                                                                                                                 Computers and Geotechnics 151 (2022) 104964

Table 3                                                              pore water pressure. It can be noted that the predicted water outflow
Material and hydraulic properties for the slope failure test.                        rates are in overall agreement with experimental observations.
  Paramters                                  Unit                     Value           The predicted vertical displacement profiles along the height of the
                                                             column are plotted in Fig. 11; results from Wang et al., (2018) are also  h/dp                                     –                         1.3
  Courant number                           –                         0.2            plotted on the same figure for comparison. Note that the effective
  Artificial viscosity α                        –                         0.1             stresses are modified during the drainage as the suction pressure in
  Soil density ρs                         kg/m3                 2650           creases. The deformation of the soil skeleton due to the changes in the
  Young’s modulus E                   MPa                     10.0            effective stress accumulates with time, resulting in the settlement profile  Poisson’s ratio ν                           –                         0.3                                                                              of the soil column shown in Fig. 11. Although slight fluctuations are  Friction angle ϕ                                       ◦                        21.0
  Peak cohesion cp                        kPa                      10.0          observed in the settlement profile, the computed results are in agree
  Residual cohesion cr                      kPa                       3.0          ment with those reported by Wang et  al., (2018), confirming the
  Softening coefficient ηc                     –                         5.0             applicability of the present framework for the treatment of transient
  Water         density                                                            1000              ρw                       kg/m3                                                                  problems in unsaturated soils.                                           –  Porosity         n                                                                        0.3
  Water bulk modulus Kw                   Pa                        3.0 × 107
 SWCC constant av                        Pa−1                      1.0 × 10-5       5. Application example: slope failure due to rainfall infiltration
  Hydraulic conductivity K                 m/s                       1.0 × 10-3
                                                                The proposed numerical scheme is used to simulate an initially un
                                                                          saturated slope that becomes unstable due to water infiltration, for
                                                                    example, caused by a heavy rainfall event. The case study aims at pre
                                                                             dicting both the onset of failure as well as the post-failure deformation.
                                                                   Schematic diagrams of the slope geometries are plotted in Fig. 12. It is
                                                                   noted that all slopes have the same heights (15 m), widths (15 m) and
                                                                          lengths (40 m) and inclination of 1:1.67. To examine the influence of the
                                                                                        soil cover depth on the post-failure motion of the landslides, two slope
                                                                      geometries with bedrock inclinations of 1:2 and 1:1 are considered;
                                                                          these slope models are hereafter referred to as slope A and slope B.
                                                                The bedrock is modelled as an impermeable material, using the solid
                                                                        wall boundary condition; no-slip boundaries are adopted to simulate a
                                                                              perfectly rough interaction between bedrock and the above soil layer.
                                                                                Free-slip conditions are used to the left sides of the domain to enforce
                                                                                    frictionless conditions. The water infiltration initiates once the seepage
                                                                     flow is allowed in the computational domain thanks to the dynamic free-
                                                                           surface boundary condition.  Fig. 13. SWCC adopted in the simulation of rainfall-induced slope failure.
                                                                The soil behaviour is simulated using the elastic–plastic Drucker-
                                                                      Prager model with strain-softening. The linear SWCC model is used to(i.e., fully saturated). The top of the soil column is set as zero normal-                                                                            characterise the hydraulic properties of the soils. Material and hydraulicflux (or impermeable), while the zero-pressure boundary condition is                                                                            properties are listed in Table 3.applied to the bottom. The initial stress profile and particle positions are                                                                The adopted SWCC is plotted in Fig. 13. It is found that, with theobtained by applying the gravitational field to the soil column with the                                                                  adopted linear SWCC model, air will significantly penetrate the soil at pcuse of damping term. Numerical experiments show that the damping                                            = 1 kPa while the water content reaches its residual value at pc = 100process helps to reduce the initial oscillations and errors in the predic                                                                       kPa. Similar trends can be found in the literature for silty soils as showntion of particles’ displacements.                                                                              in Stange and Horne (2005). Nevertheless, to reduce the computational  A linear elastic model is adopted to simulate the soil behaviour. The                                                                    time of the simulation, the selected hydraulic conductivity may be at therelationship between saturation and suction pressure, saturation and                                                                       higher end of the typical values for silty soils. This approximation speedsrelative permeability are taken as (Schrefler and Scotta, 2001),                                                            up the wetting process and allows our model to be tested until very large
          (                           )2.4279                                            deformations are achieved in the sliding mass without demanding                      pcS = 1.0 −0.10152                  ,                                  (49a)                 ρwg                                                 computational costs.
                                                                The initial particle spacings of 0.5 m, 0.2 m, and 0.1 m are adopted,
Krel = 1.0 −2.207(1.0 −S)1.0121.                                (49b)     resulting a total of 1037, 6524, and 26,175 particles for slope A and 835,
                                                                   5275, and 21,175 particles for slope B. The value of dp adopted in this
   The material and hydraulic properties are listed in Table 2, which are     case is larger than those used in the element tests as shown in Section 4.
taken from Schrefler and Scotta (2001), and Bandara et al. (2016). The       It is noted that a larger dimension of the physical domain is involved in
comparisons of the fitted SWCC and HCC against experiment data are      this case. Since the proposed numerical scheme is converging, the se
plotted in Fig. 9. The initial particle spacings are set to 0.05 m, resulting     lection of a relatively coarse resolution enables both an acceptable
in 20 particles over the height of the domain.                            computational cost while ensuring the computation error of the nu
    Fig. 10 compares the experimental data and SPH results. The evo     merical solution is within a predefined range. The slope is assumed to be
lutions of pore water pressure along the column are presented in Fig. 10      initially unsaturated, with the initial ground water surface located at the
(a). It can be seen that the desaturation process results in a gradual in    bottom of the slope. The initial distribution of pore water pressure is set
crease of suction pressure along the column. For the first 10 mins, the     as hydrostatic, while the initial stress profile is generated by applying a
calculated results overestimate the build-up of the suction pressure,     gravitational field and using the damping term to achieve the fast
which  is consistent with results observed in previous FEM studies     equilibrium. Water infiltration is then allowed to initiate the simula
(Schrefler and Scotta 2001) and the MPM analysis (Bandara et al.,      tions. In the following, the results from the medium particle resolution
2016); while satisfactory agreement with experimental results is ach     (dp = 0.2 m) are presented.
ieved after about 20 mins of physical time. Fig. 10(b) shows the water         Fig. 14 shows the temporal evolution of the accumulated deviatoric
outflow rate recorded at the bottom, which shows a decreasing trend     plastic strain and pore water pressure in slope A. It can be seen that the
with time caused by the corresponding decrease in the rate of change of     failure starts at a time t = 101 s near the slope’s toe, where the moisture

                                                                        12

### Page 13

R. Feng et al.                                                                                                                 Computers and Geotechnics 151 (2022) 104964

       Fig. 14. Pore pressure contour (left column) and accumulated deviatoric plastic strain contour (right column) at different time instants for slope A.

content first reaches the saturation condition while the remaining soil is     the shear plane. At the onset of the instability these shear stresses attain
still unsaturated. Due to the loss of the support at the slope toe, and the     their maximum values, before decreasing as the sliding mass moves
continuous reduction in soil strength (softening) due to water infiltra    downslope.
tion, a successive concave-upward circular failure surface forms at t =       Another test scenario is investigated using the geometry of slope B,
123 s. This retrogressive-type of failure pattern is commonly observed in    with a shallower soil cover compared to that in slope A. The failure
the real field (Orense et al., 2004, Tohari et al., 2007, Regmi et al., 2014,     behaviour of slope B is presented in Fig. 17 using the contour plots of
Chueasamat et al., 2018) as the instability developed at the slope’s toe    accumulated  deviatoric  plastic  strain and pore water pressure  at
influences the stability of the upper portion of the slope, resulting in     different time instants. Evidently, a different failure mechanism can be
instabilities of relatively large volume of soil.                           observed due to the presence of a shallow soil cover. The slope remains
   In Fig. 14, the evolution of pore water pressure due to heavy rainfall     stable for 79 s, after which relatively large plastic strains develop at the
is clearly reproduced with the adopted free-surface boundary condition.     toe of the slope. This is followed by the rapid formation of the integral
Saturated wetting fronts are advancing from the ground surface at the     failure across the main slope. Once the failure surface is well developed,
start of simulation, and the toe of the slope is already saturated when the     the soils above the failure surface becomes unstable and starts to move
first slide initiates at t = 101 s. The wetting front continuously pro    downslope along the failure surface. With the gradual movement of the
gresses from the failure region towards the centre of the slope, while the     sliding mass, the second failure develops within the moving mass at t =
suction pressure dissipates simultaneously, contributing to the failure    99 s. The failure propagates further downwards the slope toe at t = 150
propagation.                                                                                   s, in which a third sliding surface is observed. This type of failure
   The calculated results of vertical and shear effective stress profiles    mechanism is consistent with the experimental observations by Regmi
obtained with and without the diffusion term are shown in Fig. 15 and     et al. (2014) for a shallow slope subjected to rainfall.
Fig. 16, respectively. It is found that without the use of diffusion term,        Unlike slope A, where a global stability is maintained for a certain
numerical noise and fluctuations develop within the simulation domain,     time after the local failure at the toe and before the initiation of the
which is a common issue in other particle-based methods, including     global slide, for slope B the global slide across the main slope develops at
MPM and SPH. However, these deficiencies can be much improved by     the onset of instability without any observation of local failure. This
introducing numerical diffusion in  stress, resulting in a noise-free     finding may indicate that the onset of integral failure in shallow-seated
smooth stress distribution.                                                 slopes may give fewer warning signs than in deep-seated slopes. Another
    Fig. 16 shows that, at the start of the simulation, the maximum shear     difference in failure mechanism is the shape of the global sliding surface.
stresses develop at the interface between the slope and the underlying     In slope A, it is a continuous circular arc, which is a typical type of failure
boundary, providing resistance against horizontal slip. Before the onset     surface in homogeneous materials; the  failure surface of slope B
of failure, there is a rapid development of shear stresses above and below     involved a combination of curved and planar slip surfaces. The presence

                                                                        13

### Page 14

R. Feng et al.                                                                                                                 Computers and Geotechnics 151 (2022) 104964

Fig. 15. Vertical effective stress contour at different time instants for slope A with the diffusion term (left column) and without the diffusion term (right column).

of a shallow bedrock which limits the propagation of the sliding surface    method enables the simulation of water infiltration at the free surface
to greater depths while forcing the sliding mass to move parallel to the     without a surface searching algorithm and it avoids the problem that
impermeable ground along a planar slip surface. As a consequence, the    boundary conditions do not align well with the boundary (e.g., the MPM
motion of sliding mass for slope A is purely rotational while for slope B it    model by Wang et al. 2018). It is shown that the stress field in present
involves both translational and rotational slips.                             analysis is smooth at all stages of the failure process, even at large de
    It is well known that the accuracy of SPH interpolation is dependent     formations. However, the proposed formulations still present a number
of the particle spacing (Quinlan et al., 2006). With the refinement of dp,     of limitations due to the assumptions made and simplifications applied.
the SPH error is reduced until the discretisation error dominates. The    They are discussed in the following together with suggestions for future
influence of spatial discretisation on the post-failure motion is also     works.
investigated and the results at t = 120 s are presented in Fig. 18. The       The method adopted the natural zero-pressure free-surface boundary
locations of main shear band are similar for the three simulations but     condition to simulate the water infiltration process. This boundary
more sub-slides can be found at the slope toe when decreasing dp. This     treatment simplifies the algorithm since it avoids the complex surface
observation has also been reported by Bui and Nguyen (2021) for the     searching algorithm (e.g., Bandara et al., 2016, Ceccato et al., 2021) but
case of retrogressive failures of slopes in sensitive clays. The discrep       it assumes a fully saturated condition along the free surface and satu
ancies in the failure surfaces can be attributed to the accumulation of     rated wetting fronts advancing from the ground surface. It may result in
numerical  errors, which may be become  significant  at  large de    an extreme infiltration rate that could lead to conservative failure pre
formations. As the particle resolution is refined, the magnitude of the     diction. However, in order to enforce a prescribed infiltration rate along
error from SPH interpolation is reduced, thus providing the ability to     the free surface to predict slope instability with a given rainfall data or to
capture more broken blocks, which may not be able to be reflected with     investigate the influence of infiltration parameters (e.g., rainfall in
a large dp.                                                                     tensity and duration) on the failure mechanism of the slope, additional
                                                                 development is required to identify free-surface particles for SPH. It is
6. Discussion                                                              also noted that, with the use of discharge-based condition, ponding may
                                                                        take place if the inflow rate exceeds the storage capacity of the soil. In
   Rainfall-induced  slope  instability  involves  the development  of    such a case, a new algorithm is required to enable a switch between
continuous sliding surfaces at the pre-failure stage, and the subsequent     discharge-based condition and pressure-based condition in SPH. Future
motion of sliding masses at the post-failure stage. The integrated anal    developments are required for a more advanced infiltration boundary
ysis of the failure and post-failure behaviour, which is challenging for     condition in SPH.
traditional mesh-based methods, has been implemented in this study       The present numerical frameworks are formulated based on a
using a new single-layer multi-phase coupled SPH model. The proposed     generalised elastic–plastic soil model with the assumption of a constant

                                                                        14

### Page 15

R. Feng et al.                                                                                                                 Computers and Geotechnics 151 (2022) 104964

 Fig. 16. Shear effective stress contour at different time instants for slope A with the diffusion term (left column) and without the diffusion term (right column).

air pressure. To simulate the behaviour of unsaturated soils, the SWCC      soils. Its potential applications are broader, going beyond the test case of
model is combined with a strain-softening Drucker-Prager soil model     rainfall-induced landslides presented here. For example,  it can be
that is formulated using Bishop’s effective stress with the effective stress     applied to the study of seepage flow through a dam where the boundary
parameter χ equal to the degree of saturation S (e.g., Bandara et al.,     conditions defining the hydraulic head, seepage front are correctly
2016, Wang et al., 2018, Lei et al., 2020, Ceccato et al., 2021). It is noted    implemented.
that this type of effective stress reduces to Terzaghi’s effective stress at
fully saturated condition, providing a smooth transition of stress state     7. Conclusions
between the unsaturated and saturated condition. The dependency of
soil strength on suction is taken into account since the evolution of        This paper has presented a new two-phase single-layer SPH formu
effective stress with suction is linked to the SWCC model. This numerical     lation for unsaturated  soils to study the infiltration-induced slope
configuration provides a simple but realistic representation of unsatu     collapse. A new extension of the first-order consistent wall boundary
rated  soil behaviour and the common features of rainfall-induced     treatment by Feng et al. (2021) has been proposed for the coupled
landslides are captured as shown in the present work. Nevertheless, to    problem to enforce no-slip/free-slip boundary conditions in fluid/solid
account for other features relevant to unsaturated soils, such as the     phase. It is found that the proposed formulations provide an implicit
wetting induced volume change or collapse that result in initial failures    implementation of zero-pressure boundary condition at the free-surface.
(Gens, 2010), the proposed formulation requires the implementation of     This surface boundary condition avoids the use of complex particle
more advanced unsaturated soil constitutive models, such as those that     searching algorithms (e.g., Bandara et al. 2016, Ceccato et al. 2021), and
incorporate SWCC within the constitutive model (Wheeler et al., 2003),    can be conveniently adopted to simulate water infiltration problems,
or those that adopt more sophisticated stress variables (Sheng et al.,    such as the ones described in the present manuscript. A new formulation
2008). An overview of the constitutive modelling of unsaturated soils     of stress diffusion term is presented to reduce numerical noise in the
can be found in D’Onza et al. (2011). In addition, the proposed formu      stress field at large deformations. Comparing to the formulation by Feng
lations can be further extended to consider the air pressure variation by     et al. (2021), which is limited to gravity-dominated failure, the new
including the momentum/mass balance laws of air phase, for the case    method is general and can be adopted for any scenarios, which is wellthat air pressure plays a role.                                               suited for the coupled problem. The proposed model is validated for two
   Another limitation of the present model that will be addressed in      tests cases, representing the infiltration test and the drainage test of a
future work are extending the implementation to 3-D using hardware      soil column.
acceleration.                                                                       Finally, the proposed model is employed for the analysis of rainfall-
   Despite the limitations mentioned above, the proposed formulation    induced slope collapse. The analysis results show that the geometries of
provides a new route for the analysis of large deformation of unsaturated    bedrock or the depth of slope play an important role in the failure

                                                                        15

### Page 16

R. Feng et al.                                                                                                                 Computers and Geotechnics 151 (2022) 104964

       Fig. 17. Pore pressure contour (left column) and accumulated deviatoric plastic strain contour (right column) at different time instants for slope B.

Fig. 18. Contour plot of accumulated deviatoric plastic strain with different particle resolutions: dp = 0.5 (first row), dp = 0.2 (second row), and dp = 0.1 (third row).

                                                                        16

### Page 17

R. Feng et al.                                                                                                                 Computers and Geotechnics 151 (2022) 104964

evolution and post-failure mechanisms. Due to the possible truncation of      Bui, H.H., Fukagawa, R., Sako, K., Wells, J.C., 2011. Slope stability analysis and
the failure surface, the geometries of bedrock could affect the shape and          discontinuous slope failure simulation by elasto-plastic smoothed particle                                                                                    hydrodynamics (SPH). Geotechnique 61 (7), 565–574.
the movement of the slides. For the slope with deep soil cover, the local       Cai, F., Ugai, K., 2004. Numerical analysis of rainfall effects on slope stability. Int. J.
failure initiates at the toe of the slope and then propagates toward the         Geomech. 4 (2), 69–78.
crest; differently, for the slope with shallow soil covers, the global failure       Cascini, L., Cuomo, S., Pastor, M., Sorbino, G., 2010. Modeling of rainfall-induced                                                                                           shallow landslides of the flow-type. J. Geotech. Geoenviron. Eng. 136 (1), 85–98.
already develops at the onset of instability, indicating that the integral      Ceccato, F., Yerro, A., Girardi, V., Simonini, P., 2021. Two-phase dynamic MPM
failure in shallow-seated slopes may give fewer warning signs than in          formulation for unsaturated soil. Comput. Geotech. 129, 103876.
deep-seated slopes. It should be noted that the results are also dependent     Chang, K.-T., Chiang, S.-H., 2009. An integrated model for predicting rainfall-induced                                                                                                        landslides. Geomorphology 105 (3–4), 366–373.
of the hydrogeological characteristic of the slope and the hydro-     Chueasamat, A., Hori, T., Saito, H., Sato, T., et al., 2018. Experimental tests of slope
mechanical properties of the soil. Further analyses can be investigated           failure due to rainfalls using 1g physical slope models. Soils Found. 58 (2), 290–305.
to provide general guidelines for the evaluation of slope stability. In      Colagrossi, A., Landrini, M., 2003. Numerical simulation of interfacial flows by smoothed
addition, the proposed method is shown to be capable of capturing both      Crespo,particleA.J.,hydrodynamics.Domínguez, J.M.,J. Comput.Rogers, B.D.,Phys.G´omez-Gesteira,191 (2), 448–475.M., et al., 2015.
the triggering of slope instability and its subsequent collapse while          DualSPHysics: Open-source parallel CFD solver based on Smoothed Particle
providing a smooth stress profile even at large deformation. Information         Hydrodynamics (SPH). Comput. Phys. Commun. 187, 204–216.
after failure initiation can be predicted with this method and the      Cui, P., Guo, C.-X., Zhou, J.-W., Hao, M.-H., et al., 2014. The mechanisms behind shallow                                                                                                           failures in slopes comprised of landslide deposits. Eng. Geol. 180, 34–44.
consequence of the landslides is allowed to be evaluated.                  Cuomo, S., Della Sala, M., 2013. Rainfall-induced infiltration, runoff and failure in steep
                                                                                            unsaturated shallow soil deposits. Eng. Geol. 162, 118–127.
                                                                                            Davies, O., Rouainia, M., Glendinning, S., Cash, M., et al., 2014. Investigation of a pore
                                                                                                pressure driven slope failure using a coupled hydro-mechanical model. Eng. Geol.
CRediT authorship contribution statement                                             178, 70–81.
                                                                                Domínguez, J.M., Fourtakas, G., Altomare, C., Canelas, R.B., et al., 2021. DualSPHysics:
   Ruofeng Feng: Conceptualization, Methodology, Software, Valida         from fluid dynamics to multiphysics problems. Computational Particle Mechanics
tion, Investigation, Writing – original draft, Writing – review & editing.      D’onza,1–29.F., Gallipoli, D., Wheeler, S., Casini, F., et al., 2011. Benchmark of constitutive
Georgios  Fourtakas:  Conceptualization,  Methodology,  Software,         models for unsaturated soils. Gцotechnique 61 (4), 283–302.
Writing – review & editing. Benedict D. Rogers: Conceptualization,      Ering, P., Babu, G.S., 2016. Probabilistic back analysis of rainfall induced landslide-A
Methodology, Resources, Writing – review & editing. Domenico Lom          case study of Malin landslide, India. Eng. Geol. 208, 154–164.                                                                                        Feng, R., Fourtakas, G., Rogers, B.D., Lombardi, D., 2021. Large deformation analysis of
bardi: Conceptualization, Resources, Writing – review &  editing,          granular materials with stabilized and noise-free stress treatment in smoothed
Supervision.                                                                                         particle hydrodynamics (SPH). Comput. Geotech. 138, 104356.
                                                                                           Fourtakas, G., Dominguez, J.M., Vacondio, R., Rogers, B.D., 2019. Local uniform stencil
                                                                                     (LUST) boundary condition for arbitrary 3-D boundaries in parallel smoothed
                                                                                                         particle hydrodynamics (SPH) models. Comput. Fluids 190, 346–361.
Declaration of Competing Interest                                                 Galavi, V. 2010. Groundwater flow, fully coupled flow deformation and undrained
                                                                                               analyses in PLAXIS 2D and 3D. PLAXIS internal research report.
   The authors declare that they have no known competing financial      Gatmiri,for theB., analysisDelage, ofP., unsaturatedCerrolaza, M.,porous1998.media.UDAM:Adv.A powerfulEng. Softw.finite29 element(1), 29–43.software
interests or personal relationships that could have appeared to influence      Gens, A., 2010. Soil-environment interactions in geotechnical engineering. Gцotechnique
the work reported in this paper.                                               60 (1), 3–74.
                                                                                         Gingold, R.A., Monaghan, J.J., 1977. Smoothed particle hydrodynamics: theory and
                                                                                                  application to non-spherical stars. MNRAS 181 (3), 375–389.
Data availability                                                                          Guzzetti, F., Peruccacci, S., Rossi, M., Stark, C.P., 2008. The rainfall intensity-duration
                                                                                                  control of shallow landslides and debris flows: an update. Landslides 5 (1), 3–17.
   Data will be made available on request.                                  Huang, C.-C., Lo, C.-L., Jang, J.-S., Hwu, L.-K., 2008. Internal soil moisture response to                                                                                                    rainfall-induced slope failures and debris discharge. Eng. Geol. 101 (3–4), 134–145.
                                                                               Huang, Y., Zhang, W., Dai, Z., Xu, Q., 2013. Numerical simulation of flow processes in
Acknowledgements                                                                           liquefied soils using a soil-water-coupled smoothed particle hydrodynamics method.                                                                                               Nat. Hazards 69 (1), 809–827.
                                                                                                 Ibsen, M.-L., Casagli, N., 2004. Rainfall patterns and related landslide incidence in the
   The first author would like to acknowledge the financial support          Porretta-Vergato region. Italy. Landslides 1 (2), 143–150.
provided by the China Scholarship Council.                                             Khalili, N., Habte, M., Zargarbashi, S., 2008. A fully coupled flow deformation model for                                                                                                         cyclic analysis of unsaturated soils including hydraulic and mechanical hystereses.
                                                                                  Comput. Geotech. 35 (6), 872–889.
References                                                                        Krahn, J., 2012. Seepage modeling with SEEP/W: An engineering methodology. GEO-
                                                                           SLOPE International Ltd., Calgary, Alberta, Canada.
                                                                                                      Kristo, C., Rahardjo, H., Satyanaga, A., 2017. Effect of variations in rainfall intensity onAntuono, M., Colagrossi, A., Marrone, S., Molteni, D., 2010. Free-surface flows solved by                                                                                                slope stability in Singapore. International Soil and Water Conservation Research 5   means of SPH schemes with numerical diffusive terms. Comput. Phys. Commun. 181                                                                                                               (4), 258–264.     (3), 532–549.                                                                                              Lee, W.-L., Martinelli, M. & Shieh, C.-L. 2019. Modelling rainfall-induced landslides withAntuono, M., Colagrossi, A., Marrone, S., 2012. Numerical diffusive terms in weakly-                                                                                              the material point method: the Fei Tsui Road case. Proceedings of the XVII ECSMGE.    compressible SPH schemes. Comput. Phys. Commun. 183 (12), 2570–2580.                                                                                                         Lei, X., He, S., Chen, X., Wong, H., et al., 2020. A generalized interpolation material pointBandara, S., Ferrari, A., Laloui, L., 2016. Modelling landslides in unsaturated slopes                                                                               method for modelling coupled seepage-erosion-deformation process within    subjected to rainfall infiltration using material point method. Int. J. Numer. Anal.                                                                                            unsaturated soils. Adv. Water Resour. 141, 103578.    Meth. Geomech. 40 (9), 1358–1380.                                                                                          Leshchinsky, B., Vahedifard, F., Koo, H.-B., Kim, S.-H., 2015. Yumokjeong Landslide: anBenz, W., Asphaug, E., 1995. Simulations of brittle solids using smooth particle                                                                                                    investigation of progressive failure of a hillslope using the finite element method.    hydrodynamics. Comput. Phys. Commun. 87 (1–2), 253–265.                                                                                               Landslides 12 (5), 997–1005.Biot, M.A., 1941. General theory of three-dimensional consolidation. J. Appl. Phys. 12                                                                                          Liakopoulos, A.C., 1964. Transient flow through unsaturated porous media. University of     (2), 155–164.                                                                                                        California, Berkeley. PhD thesis.Blanc, T., Pastor, M., 2013. A stabilized smoothed particle hydrodynamics, Taylor-                                                                                                Lian, Y., Bui, H.H., Nguyen, G.D., Tran, H.T., et al., 2021. A general SPH framework for    Galerkin algorithm for soil dynamics problems. Int. J. Numer. Anal. Meth. Geomech.                                                                                                      transient seepage flows through unsaturated porous media considering anisotropic   37 (1), 1–30.                                                                                                         diffusion. Comput. Methods Appl. Mech. Eng. 387, 114169.Bui, H.H., Fukagawa, R., 2013. An improved SPH method for saturated soils and its                                                                                               Libersky, L., Petschek, A., Carney, T., Hipp, J., et al., 1993. High strain Lagrangian    application to investigate the mechanisms of embankment failure: Case of                                                                                       hydrodynamics: a three dimensional SPH code for dynamic material response.    hydrostatic pore-water pressure. Int. J. Numer. Anal. Meth. Geomech. 37 (1), 31–50.                                                                                                                   J. Comput. Phys. 109 (1), 67–75.Bui, H.H., Kodikara, J.K., Bouazza, A., Haque, A., et al., 2014. A novel computational                                                                                                    Liu, M., Liu, G.-R., 2006. Restoring particle consistency in smoothed particle    approach for large deformation and post-failure analyses of segmental retaining wall                                                                                       hydrodynamics. Appl. Numer. Math. 56 (1), 19–36.    systems. Int. J. Numer. Anal. Meth. Geomech. 38 (13), 1321–1340.                                                                                         Lucy, L.B., 1977. A numerical approach to the testing of the fission hypothesis. TheBui, H.H., Nguyen, G.D., 2017. A coupled fluid-solid SPH approach to modelling flow                                                                                          Astronomical Journal 82, 1013–1024.    through deformable porous media. Int. J. Solids Struct. 125, 244–264.                                                                                                    Martinelli, M., Lee, W.-L., Shieh, C.-L. & Cuomo, S. Rainfall boundary condition in aBui, H.H., Nguyen, G.D., 2021. Smoothed particle hydrodynamics (SPH) and its                                                                                          multiphase Material Point Method. Workshop on World Landslide Forum, 2020.    applications in geomechanics: From solid fracture to granular behaviour and                                                                                                  Springer, 303-309.    multiphase flows in porous media. Comput. Geotech. 138, 104315.

                                                                        17

### Page 18

R. Feng et al.                                                                                                                 Computers and Geotechnics 151 (2022) 104964

Mayrhofer, A., Rogers, B.D., Violeau, D., Ferrand, M., 2013. Investigation of wall             Sorbino, G., Nicotera, M.V., 2013. Unsaturated soil mechanics in rainfall-induced flow
   bounded flows using SPH and the unified semi-analytical wall boundary conditions.            landslides. Eng. Geol. 165, 105–132.
   Comput. Phys. Commun. 184 (11), 2515–2527.                                         Stange, C.F., Horn, R., 2005. Modeling the soil water retention curve for conditions of
Mieremet, M., Stolle, D., Ceccato, F., Vuik, C., 2016. Numerical stability for modelling of           variable porosity. Vadose Zone J. 4 (3), 602–613.
   dynamic two-phase interaction. Int. J. Numer. Anal. Meth. Geomech. 40 (9),             Tohari, A., Nishigaki, M., Komatsu, M., 2007. Laboratory rainfall-induced slope failure
    1284–1294.                                                                          with moisture content measurement. J. Geotech. Geoenviron. Eng. 133 (5),
Monaghan, J.J., 1992. Smoothed particle hydrodynamics. Ann. Rev. Astron. Astrophys.          575–587.
   30 (1), 543–574.                                                                    Tsiampousi, A., Smith, P.G., Potts, D.M., 2017a. Coupled consolidation in unsaturated
Monaghan, J.J., 1994. Simulating free surface flows with SPH. J. Comput. Phys. 110 (2),              soils: An alternative approach to deriving the governing equations. Comput.
    399–406.                                                                              Geotech. 84, 238–255.
Morris, J.P., Fox, P.J., Zhu, Y., 1997. Modeling low Reynolds number incompressible        Tsiampousi, A., Smith, P.G., Potts, D.M., 2017b. Coupled consolidation in unsaturated
    flows using SPH. J. Comput. Phys. 136 (1), 214–226.                                                  soils: From a conceptual model to applications in boundary value problems. Comput.
Nguyen, C.T., Nguyen, C.T., Bui, H.H., Nguyen, G.D., et al., 2017. A new SPH-based             Geotech. 84, 256–277.
    approach to simulation of granular flows using viscous damping and stress              Vacondio, R., Altomare, C., De Leffe, M., Hu, X., et al., 2020. Grand challenges for
    regularisation. Landslides 14 (1), 69–81.                                           Smoothed Particle Hydrodynamics numerical schemes. Computational Particle
Ochiai, H., Okada, Y., Furuya, G., Okura, Y., et al., 2004. A fluidized landslide on a             Mechanics 1–14.
    natural slope by artificial rainfall. Landslides 1 (3), 211–219.                            Violeau, D., 2012. Fluid mechanics and the SPH method: theory and applications. Oxford
Oh, S., Lu, N., 2015. Slope stability analysis under unsaturated conditions: Case studies of           University Press.
    rainfall-induced failure of cut slopes. Eng. Geol. 184, 96–103.                            Violeau, D., Rogers, B.D., 2016. Smoothed particle hydrodynamics (SPH) for free-surface
Orense, R.P., Shimoma, S., Maeda, K., Towhata, I., 2004. Instrumented model slope               flows: past, present and future. J. Hydraul. Res. 54 (1), 1–26.
     failure due to water seepage. Journal of Natural Disaster Science 26 (1), 15–26.        Wang, F., Dai, Z., Takahashi, I., Tanida, Y., 2020. Soil moisture response to water
Pastor, M., Haddad, B., Sorbino, G., Cuomo, S., et al., 2009. A depth-integrated, coupled             infiltration in a 1-D slope soil column model. Eng. Geol. 267, 105482.
   SPH model for flow-like landslides and related phenomena. Int. J. Numer. Anal.        Wang, B., Vardon, P., Hicks, M., 2016. Investigation of retrogressive and progressive
    Meth. Geomech. 33 (2), 143–172.                                                           slope failure mechanisms using the material point method. Comput. Geotech. 78,
Peng, C., Xu, G., Wu, W., Yu, H.-S., et al., 2017. Multiphase SPH modeling of free surface          88–98.
    flow in porous media with variable porosity. Comput. Geotech. 81, 239–248.          Wang, B., Vardon, P., Hicks, M., 2018. Rainfall-induced slope collapse with coupled
Pinyol, N., Alvarado, M., Alonso, E., Zabala, F., 2018. Thermal effects in landslide                material point method. Eng. Geol. 239, 1–12.
    mobility. Geotechnique 68 (6), 528–545.                                       Wang, C., Wang, Y., Peng, C., Meng, X., 2017. Two-fluid smoothed particle
Potts, D. M., Zdravkovi´c, L., Addenbrooke, T. I., Higgins, K. G., et al. 2001. Finite element          hydrodynamics simulation of submerged granular column collapse. Mech. Res.
    analysis in geotechnical engineering: application, Thomas Telford London.               Commun. 79, 15–23.
Qi, S., Vanapalli, S.K., 2015. Hydro-mechanical coupling effect on surficial layer stability      Wheeler, S., Sharma, R., Buisson, M., 2003. Coupling of hydraulic hysteresis and stress-
    of unsaturated expansive soil slopes. Comput. Geotech. 70, 68–82.                              strain behaviour in unsaturated soils. Gцotechnique 53 (1), 41–54.
Quinlan, N.J., Basa, M., Lastiwka, M., 2006. Truncation error in mesh-free particle         Wu, Y.-M., Lan, H.-X., Gao, X., Li, L.-P., et al., 2015. A simplified physically based
    methods. Int. J. Numer. Meth. Eng. 66 (13), 2064–2085.                                  coupled rainfall threshold model for triggering landslides. Eng. Geol. 195, 63–69.
Regmi, R.K., Jung, K., Nakagawa, H., Kang, J., 2014. Study on mechanism of               Yang, K.-H., Uzuoka, R., Lin, G.-L., Nakai, Y., 2017. Coupled hydro-mechanical analysis
    retrogressive slope failure using artificial rainfall. Catena 122, 27–41.                         of two unstable unsaturated slopes subject to rainfall infiltration. Eng. Geol. 216,
Ren, B., Wen, H., Dong, P., Wang, Y., 2014. Numerical simulation of wave interaction           13–30.
    with porous structures using an improved smoothed particle hydrodynamic method.       Yerro, 2015. MPM modelling of landslides in brittle and unsaturated soils. Polytechnic
    Coast. Eng. 88, 88–100.                                                                     University of Catalonia. PhD thesis.
Sasahara, K., 2017. Prediction of the shear deformation of a sandy model slope generated      Yoo, C., Jung, H.-Y., 2006. Case history of geosynthetic reinforced segmental retaining
   by rainfall based on the monitoring of the shear strain and the pore pressure in the           wall failure. J. Geotech. Geoenviron. Eng. 132 (12), 1538–1548.
    slope. Eng. Geol. 224, 75–86.                                                      Zhang, W., Maeda, K., Saito, H., Li, Z., Huang, Y.u., 2016. Numerical analysis on seepage
Schrefler, B.A., Scotta, R., 2001. A fully coupled dynamic model for two-phase fluid flow            failures of dike due to water level-up and rainfall using a water-soil-coupled
    in deformable porous media. Comput. Methods Appl. Mech. Eng. 190 (24–25),             smoothed particle hydrodynamics model. Acta Geotech. 11 (6), 1401–1418.
    3223–3246.                                                                     Zhang, J., Tang, W.H., Zhang, L., 2010. Efficient probabilistic back-analysis of slope
Senthilkumar, V., Chandrasekaran, S., Maji, V., 2018. Rainfall-induced landslides: case             stability model parameters. J. Geotech. Geoenviron. Eng. 136 (1), 99–109.
    study of the Marappalam landslide, Nilgiris District, Tamil Nadu. India. International      Zhang, W., Zheng, H., Jiang, F., Wang, Z., et al., 2019. Stability analysis of soil slope
    Journal of Geomechanics 18 (9), 05018006.                                              based on a water-soil-coupled and parallelized Smoothed Particle Hydrodynamics
Sheng, D., Sloan, S. W., Gens, A. & Smith, D. W. 2003. Finite element formulation and          model. Comput. Geotech. 108, 212–225.
    algorithms for unsaturated soils. Part I: Theory. International journal for numerical      Zhou, C., Liu, G., Lou, K., 2007. Three-dimensional penetration simulation using
   and analytical methods in geomechanics, 27(9), 745-765.                              smoothed particle hydrodynamics. Int. J. Comput. Methods 4 (04), 671–691.
Sheng, D., Fredlund, D.G., Gens, A., 2008. A new modelling approach for unsaturated        Zienkiewicz, O. C., Xie, Y., Schrefler, B., Ledesma, A., et al. 1990. Static and dynamic
     soils using independent stress variables. Can. Geotech. J. 45 (4), 511–534.                  behaviour of soils: a rational approach to quantitative solutions. II. Semi-saturated
Smith, P.G.C., Potts, D.M., Addenbrook, T.I., 2008. A precipitation boundary condition           problems. Proceedings of the Royal Society of London. A. Mathematical and Physical
    for finite element analysis. In: Proceedings of the 1st European Conference on                Sciences, 429(1877), 311-321.
    Unsaturated Soils, Durham, UK. Taylor & Francis Group, pp. 773–778.

                                                                        18
