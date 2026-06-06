# Single-layer soil-water coupled SPH method and its application to sinkhole simulation

> Auto-converted from PDF for Codex/code-reference reading. Formatting, equations, figures, and tables may require checking against the original PDF.

- Source PDF: `Single-layer soil-water coupled SPH method and its application.pdf`
- Pages: 28
- PDF metadata author: Xiaoyu Chen

## Extracted Text

### Page 1

Acta Geotechnica
https://doi.org/10.1007/s11440-023-02063-4    (0123456789().,-volV)(0123456789().,- volV)

 RESEARCH PAPER

Single-layer soil-water coupled SPH method and its application
to sinkhole simulation

Xiaoyu Chen1  • Yat Fai Leung1      • Hirotoshi Mori2  • Shun Uchida3  • Kazuhiro Takumi2

Received: 18 February 2023 / Accepted: 19 August 2023
   The Author(s), under exclusive licence to Springer-Verlag GmbH Germany, part of Springer Nature 2023

Abstract
In this study, a single-layer SPH approach that takes into account full soil-water interactions is proposed. The approach
updates the propagation of pore pressure through combination of volumetric strain and Darcy’s law, accounting for the
momentum equation, soil constitutive behavior, and the development of pore pressure at each timestep of the simulation.
The proposed method  is validated by analytical solutions of consolidation problems. To showcase  its capability in
simulating large-deformation problems with hydro-mechanical interactions, a physical test of a seepage-induced sinkhole
was simulated using the proposed SPH method. The good agreements suggest that the proposed method can capture the key
features of sinkhole developments and serve as a promising tool to explore the associated failure mechanism. A series of
parametric studies are then conducted to reveal the inﬂuences of material properties and hydraulic conditions on the failure
behavior of sinkholes, including failure patterns, inﬂuence zone, and surface settlement.

Keywords Consolidation  Large-strain problem  Parametric analysis  Sinkhole  Smoothed particle hydrodynamics
Soil-water coupling

1 Introduction                                   model domain reﬁned during the calculation steps as the
                                                                    particles displace. Among these, smoothed particle hydroMesh-based numerical methods, such as the ﬁnite element    dynamics (SPH) is a popular and relatively mature method,
method (FEM) and the ﬁnite difference method (FDM),    which was originally applied to astrophysical phenomena
have been widely applied  in geotechnical engineering.    and was later extended to a vast range of problems in both
However, these models undergo severe mesh distortion    ﬂuid and solid mechanics [27, 28, 34, 35, 38]. Instead of
when simulating large-deformation problems, which may    solving the governing equations on predeﬁned grids, SPH
lead to non-physical numerical results [33, 34, 50]. To    solves the equations based on dynamic particle connections
circumvent this problem, various meshfree methods based    and therefore has obvious advantages in handling problems
on continuum mechanics have been developed and applied    associated with large deformations and evolving free surto geotechnical problems associated with large deforma-    faces [34]. As a Lagrangian numerical method, this method
tions [1, 6, 35, 56, 57]. Meshfree methods characterize the     utilizes particles that carry the physical parameters and
materials by a series of particles, with the geometry of the     stress conditions which  are updated as  the simulation
                                                               progresses. The method avoids the need to transfer infor-
                                                       mation between particles and a background mesh, thereby
& Yat Fai Leung                                                       improving computational efﬁciency. Over the past few
    andy.yf.leung@polyu.edu.hk
                                                            decades, some previous shortcomings of the SPH, such as
1   Department of Civil and Environmental Engineering, The           tensile instability and inaccuracies at the model boundaries,
   Hong Kong Polytechnic University, Hung Hom, Kowloon,        have been resolved by techniques such as the introduction
   Hong Kong, Special Administrative Region of China              of artiﬁcial viscosity, artiﬁcial stress and virtual particles
2   Graduate School of Science and Technology for Innovation,       near the boundaries [11, 32, 39, 43].
   The Yamaguchi University, Yamaguchi, Japan                Due to the ability of the SPH approach to incorporate
3   Department of Civil and Environmental Engineering,           complex physics [33], the method has been extended to
    Rensselaer Polytechnic Institute, Troy, USA

                                  123

### Page 2

Acta Geotechnica

describe the large deformation of geomaterials since the    layers SPH method in geotechnical engineering in the past,
early 2000s [4, 10, 12, 13, 20–22, 63, 67]. Applications of    including the modelling of excavation by water jet in dry
the SPH method in geotechnical engineering, particularly    and saturated soils [12]; seepage failure of a dike due to the
those considering soil-water interactions with large defor-     rise in water level and rainfall [66]; stability analysis of soil
mations, can be broadly categorized into single-layer based    slopes considering soil and water interactions [22, 68];
SPH and two-layer based SPH. Single-layer based SPH    seepage ﬂows through  rockﬁll dams and embankment
uses a single type of particle that integrates information of     failures [8]; the dam break problem on a horizontal plane
both the solid (soil skeleton) and ﬂuid (water) phases and is    with a frictional soil phase, and a debris ﬂow that happened
relatively easy to implement, with low computational cost.    in Hong Kong [49].
Bui et al. [9] made the ﬁrst attempt to solve the soil-water       Sinkholes and ground collapse are common geotechnicoupled problem by a fully coupled ðu   pÞ SPH model,    cal large-deformation problems and are normally attributed
and the performance of the proposed method was evaluated    to variations in hydraulic conditions such as underground
by a plane-strain problem of saturated soils. Afterward, an    pipe leakage [23], intense rainfall [54], water drawdown
improved SPH method for saturated soils was proposed to    [24] and ﬂooding [36]. Sinkholes often appear suddenly
simulate the behavior of embankments [13], where the pore    and are associated with signiﬁcant economic loss, public
water pressure  is calculated as the product of the unit    inconvenience, and even human  fatalities, especially in
weight of water and the vertical distance of a particle   crowded urban spaces [3, 19, 26]. Due to the signiﬁcant
below a ﬁxed groundwater table. Lian et al. [30] extended    soil-water interaction effects, complex failure mechanism
the previous formulations to a three-phase single-layer SPH    and the involvement of multiple parameters in this largemodel, which captured soil-water interactions in unsatu-    deformation problem, it is difﬁcult to capture or predict the
rated soils and predicted the process of rainfall-induced    extent of subsurface cavity and the overburden collapse
slope instability. This was achieved by incorporating the    process. Some traditional continuum methods, such as the
general SPH  framework  for  transient  seepage ﬂows  FDM and FEM, had been adopted  to  investigate  the
through unsaturated porous media, considering anisotropic    inﬂuences of mechanical and hydraulic properties on the
diffusion as proposed by Lian et al. [29]. Recently, Lian    ground settlements and to simulate the internal erosion
et al. [31] introduced an effective and stable u   pl SPH    process using advanced constitutive models [53, 55]. These
framework  to  analyze  large  deformation  and  failure    studies considered hydro-mechanical interactions  at the
in saturated porous media. The framework eliminates the    early stage of sinkhole formation (small-strain stage), but
inﬂuence  of water bulk modulus from  the pore-water    the inherent disadvantage of mesh-based approaches makes
pressure equation, leading to reduced computational times.      it difﬁcult to capture the entire failure process. On the other
On the other hand, Morikawa and Asai [44] introduced a    hand, distinct element method (DEM) has been adopted to
strong coupled soil-water interaction formulation based on    simulate  internal erosion  of  the sinkhole  triggered by
the u  w  p   Biot’s   formulation   for incompressibil-    defective pipelines [2, 15, 36, 60]. This is an important
ity condition of pore water and soil grains. Pastor et al.    research topic, but a signiﬁcant challenge is to capture the
[47] presented a single-layer, depth-integrated soil-water     entire failure process of sinkholes by DEM, due to the scale
coupled SPH approach to simulate ﬂow-like landslides,    of the problem which often requires a massive numbers of
combining the velocity-pressure version of the Biot-Zien-  DEM particles. An efﬁcient and robust method is necessary
kiewicz equation with rheological models. This method    to capture the development of a subsurface cavity and the
was  later updated by  incorporating a  depth-integrated    subsidence of the sinkhole from a macroscopic aspect. It is
description of the soil–pore ﬂuid mixture with a set of 1D    worth noting that ground subsidence due to caldera formodels to account for pore pressure evolution within the    mation  has been  successfully modeled by SPH  [45],
soil mass [48].                                             although similar studies on seepage-induced sinkholes are
  The two-layer SPH formulation utilizes two types of    limited.
Lagrangian particles to simulate the ﬂuid and solid phases      Considering the unique features of sinkhole developseparately. The  ﬂuid  phase  is  normally  modeled  as    ments and features of the SPH method, this study proposes
incompressible or weakly compressible material and the    a single-layer two-phase (SPH) method for modeling soilsoil skeleton is modeled with an elastic or elasto-plastic    water interactions in saturated soils. All mechanical and
constitutive model. The interaction between the two phases    hydraulic properties are incorporated and updated within a
is modelled through the seepage force or drag force. The    single particle type, thereby eliminating the need for contwo-layer method can consider the relative accelerations    sidering interaction forces between soil and water particles
between the solid and ﬂuid phases, while the hydraulic and    in a two-layer approach. The method accounts for mass
mechanical boundary conditions can be applied indepen-    conservation,  momentum  equation,   soil   constitutive
dently. There have been several applications of the two-    behavior, and the development of pore pressure at each

123

### Page 3

Acta Geotechnica

timestep of the simulation. The pore water pressure  is     (4)  No mass exchange and heat transfer between two
derived from volumetric strains and Darcy’s law, instead of           constituents are considered.
being ﬁxed to speciﬁc values as proposed by Bui et al. [13]
                                                   The mass conservation of the solid phase in a unit volor incorporated with Biot-Zienkiewicz equations as pre-
                                            ume can be represented by:
sented by Pastor et  al. [47, 48]. The proposed method
attempts to strike a balance between simulation accuracy    d ð nsqs Þ                                      þ nsqsr  vs ¼ 0                             ð1Þ
and computational demands. In this paper, the formulations        dt
and governing functions of the proposed approach are   where qs denotes the density of the solid; ns is the volume
described with details of boundary treatments, determina-    fraction of the solid (i.e., ns ¼ 1  n where n is the soil
tion of critical timestep, and computational implementa-    porosity); vs is the velocity vector of solid in the porous
tions. One-dimensional consolidation problems with one-   medium   and  r  vs    refers    to    its   divergence
dimensional and two-dimensional ﬂows are simulated and                    ovs     ovs     ovs
                                            (r  vs ¼ oxa þ oxb þ oxc); xa; xb; xc are distances between
compared with analytical and numerical solutions to vali-
                                                                    particles in the x; y; z directions, respectively. Likewise, the
date the proposed SPH method. A physical experiment of a
                                                   mass conservation of the ﬂuid phase  is considered as
seepage-induced sinkhole is then presented and compared
                                                              follows:
with the simulations by the proposed SPH method. The
comparisons between the physical experiment and SPH    dðnwqwÞ
                                      þ nwqwr  vw ¼ 0                           ð2Þ
model demonstrate the capabilities of the proposed model        dt
to investigate seepage-induced sinkholes from a macro-                                                    where qw denotes the density of the ﬂuid phase; nw is the
scopic  perspective. To  further  investigate  the sinkhole                                                   volume fraction of ﬂuid; vw refers to the seepage velocity
formation mechanism, a series of parametric studies are                                                                 vector, which  is also the relative velocity between the
conducted using the proposed method. The inﬂuences of                                                          water and solid phases, and r vw refers to its divergence
soil shear strength parameters, Young’s modulus, as well as                                                     and a positive value is associated with a reduction in water
the groundwater levels around the sinkhole on the devel-                                                   mass in the SPH particle. The relationship between the
opment of the failure patterns, shear strains, and surface                                                   volume fractions of water and solid for a saturated material
displacements of sinkholes are assessed and discussed.                                                                                 is:
  The novelty of this study  lies on the application of
single-layer soil-water coupled SPH to model seepage-in-    nw ¼ 1   ns ¼ n                                     ð3Þ
duced sinkhole formation, with two main contributions:                                                                                       It should be noted that the volumetric strain increment
(i) To the best of the authors’ knowledge, this is the ﬁrst                                                                 (dev) equals the negative change in void volume dn as this
attempt to model the large deformations of such sinkholes,                                                           study adopts the sign convention with compression being
and to compare the numerical results with experimental                                                                   positive. In addition, considering the relationship between
data; (ii) The failure mechanism of seepage-induced sink-                                                          water bulk modulus (Kw), pore pressure (Pw) and qw, i.e.,
holes and the key factors governing their formations are                                            Kw ¼ dPw= ð dqw=qw Þ, the pore pressure response can be
investigated based on a series of parametric studies.                                                          formulated based on Eqs. (2) and (3):

                                                    n dPw              dev
                                      ¼ r qw þ                                ð4Þ
                                     Kw  dt                 dt2 Formulation of the SPH method for soil-
  water coupling                                 where qw represents the vectors of Darcy velocity (ﬂux,
                                                   qw ¼ nwvw).
2.1 Governing equations of mass conservation         The velocities of solids are evaluated in the SPH model
   and momentum balance                         by  the momentum  equation,  represented by  the  total
                                                                   stresses and total density of the mixture, which is deﬁned as
The formulations presented in this study are based on the   q ¼ nqw þ ð 1  n Þqs, in a way similar to the approach by
following assumptions:                                   Lian et al. [30]:
(1)  The porous medium is assumed to consist of two     dvs   1                                   ¼ r r þ F                                    ð5Þ
      constituents, namely the solid  (soil skeleton) and     dt   q
     ﬂuid (water).                                                    where r represents the total stress tensor with F being the
(2)   Terzaghi’s effective stress principle is assumed to be                                                   body force vector. The effective stress principle states that:
       valid, and the soil skeleton  is modelled using an
       elastoplastic constitutive model.
(3)   Solid grains are assumed to be incompressible.

                                  123

### Page 4

Acta Geotechnica

r ¼ r0 þ IPw                                        ð6Þ    methods, this study implements the approach into the SPH
                                                   method for simulations of a large-strain problems involvwith r0 being the effective stress tensor and I the unit                                                            ing sinkhole developments.
tensor. The  stress-strain response  in  effective  stress  is
captured by the soil constitutive model, discussed in more                                                       2.2 SPH formulation of the governing equations
details  later. Through Eq. (5), the velocity ﬁeld can be
evaluated which gives rise to the strain ﬁeld and hence                                                 The SPH method represents the problem domain by arbieffective stresses across the domain.                                                                         trarily or uniformly distributed particles, each with a ﬁxed
  The momentum balance of water is usually represented                                                         mass. As shown in the left corner of Fig. 1, the problem
by the Navier-Stokes equation, which is reduced into the                                                   domain of a slope is initially discretized into uniformly
Darcy’s law for laminar ﬂows. Following Eq. (4), the pore                                                                  distributed particles. The properties and/or state variables
pressure response involves effects of both seepage and soil                                                                            (e.g., stresses, density, velocities) of each particle  i are
volumetric  strains, and  its increment in fully saturated                                                               calculated by weighted summation of those at neighboring
porous material can be expressed as:                                                                    particles j over the support domain U. The kernel function,
dPw  Kw             dev                                   as shown in Fig. 1, is a weight function that describes the
   ¼    r qw þ                               ð7Þ
  dt    n                dt                                      interactions among SPH particles by deﬁning the smooth-
                                                            ing length h and a constant j (hence the size of the support
  According to Darcy’s law, the component of ﬂux qw                                                   domain U ¼ jh). Several kernel functions have been proalong the direction of gravity (b in this paper) and other
                                                       posed and adopted to deﬁne h and the interaction function
directions can be expressed as:
                                                     between neighboring particles [33]. The most widely used
                  1 oPw  dHe       kb oPw            smoothing kernel function is the B-splines function [40],
qbw ¼   kbib ¼  kb          ¼      þ kb
                  cw oxb   dxb       cw oxb            which is stable and has low computational demands since it
                                                         resembles a Gaussian  function while having narrower                                                     ð8Þ
                                                     compact support [34]. Another popular one is the Wend-
                  ka oPw
qaw ¼   kaia ¼                                       ð9Þ    land function [64]. With an adequate number of neigh-
               cw oxa                                    boring  particles,  this function  is a good candidate  for
                  kc oPw                                  problems involving highly nonuniformly distributed parti-
                                                  ð10Þqcw ¼   kcic ¼                                                                       cles, since it has a non-negative Fourier transform in each               cw oxc
                                                       dimension [11, 16].
where ka, kb and kc represent the hydraulic conductivity,                                                   The properties fðxÞ of the material at position vector x
and ia, ib and ic represent the hydraulic gradients in the    can be converted into the SPH form based on the kernel
x; y; z directions, respectively; cw represents the unit weight    approximation and particle approximation:
of water; He is the elevation head and hence dHe between         Z                       Ntwo particles equals the particle interval in that direction           X mj                                                                                           f ð x Þ         f ðx0 ÞW ðx    x0; h Þdx0               f  xj W x    xj; h
(dxb).                                                                                                       j¼1 qj
                                                         U
  Assuming isotropic hydraulic properties (i.e.,ka ¼ kb ¼                                                                                                            ð12Þ
kc ¼ k)  that remain constant throughout the simulation
(dkb=dt ¼ 0), the pore pressure increment dPw=dt can be   where region U is the support domain of particle i, x0 is the
expressed by combining Eqs. (7) to (10):                     position vector of neighboring particles inside the domain,
                               W represents the kernel function and h is the smoothing
dPw    Kwk       Kw dev
   ¼      r2Pw þ                            ð11Þ    length, which determines the effective range of the kernel
  dt     ncw          n  dt                                 function, N is the number of neighboring particles inside
where r2 represents the Laplace operator.                    the smoothing length of particle i, mj is the mass of par-
    It should be noted  that the above equation will be     ticle j, and  qj  is the density of neighboring  particle j.
modiﬁed at an undrained boundary, as will be explained in    Following the same concept, the properties f ð x Þ at particle i
detail in the following section. The soil-water interaction is    can be approximated as:
therefore manifested in the incorporation of seepage effects            N                            P mjand pore water pressure response into the equation of       f ð xi Þ             f  xj W  xi    xj; h                     ð13Þ
                                                                                j¼1 qjmotion and mass conservation of the continuum. While
similar formulations have been used  in ﬁnite element

123

### Page 5

Acta Geotechnica

Fig. 1  Illustration of the concept of SPH method and kernel function

                                                                  N "     !
  The divergence of function  f ðxi Þ can be represented      dvai  X   rai   raj                                                                mi     þ  rW  xai    xaj ; husing the same transformation:                                    dt                                                                          q2i   q2j                                                                                    j¼1
                                            !     PN mjr   f ð xi Þ                          f  xj rW  xi    xj; h              ð14Þ                rabi    rabj              j¼1 qj                             þ   þ   rW  xbi   xbj ; h              ð17Þ                                                                     q2i    q2j
                                            !            #
and the partial derivative of the function  f ð xi Þ  is then                raci    racjexpressed as:                               þ   þ   rW  xci    xcj ; h  þ Fa
                                                                    q2i    q2j
of ð xi Þ XN mj
                        f  xj rW xxi   xxj ; h                ð15Þ   where rai  is the total stress in x-direction for particle, Fa oxx           j¼1 qj                                               represents external forces along the x-direction. The total
                                                                     stress includes the contributions from pore water pressure,where the Greek  superscript x  is used  to denote the
                                                               Pwi, and effective stress of soil skeleton, r0ai  ,  i.e., rai ¼Cartesian components a, b, c, and rW  xi    xj; h   is the
                                                          Pwi þ r0ai  following Eq. (6).gradient of kernel function W with respect to the distance
                                                   The strains ei at particle i is evaluated from the velocity
vector between particles i and j, while rW xxi   xxj ; h   is    differences between particles. Taking the x-direction for
the derivative of kernel function W with respect to the    instance, the normal strain along is formulated as:
distance between particle i and j in x-direction.                    N                                                             deai X mj  Based on mass conservation of the mixture, the density                  vaijrW  xai    xaj ; h                     ð18Þ                                                                   dt                                                                               j¼1 qjincrements dq of the mixture can be represented through
the SPH approximation:                                                   The shear strain is formulated as below, taking the xydqi  XN mj                                                 direction as example:
             vijrW  xi    xj; h                    ð16Þ        qi
 dt           j¼1 qj                                                              deabi XN mj                                                                                vaijrW  xbi   xbj ; h þ vbijrW  xai    xaj ; h                                                                   dt                                                                                j¼1 qjwhere vij ¼ vi    vj denotes the velocity difference between
particles i and j of the model domain in x; y; z directions.                                                      ð19Þ
Likewise, the equation of motion (Eq. (5)) can be repre-
                                                    where eai  is the strain at particle i in x-direction, eabi   is thesented in SPH form. Taking x-direction as an example:
                                                             shear strain in xy- direction, vaij is the velocity differences
                                                     between particles i and j in the x-direction. The effective
                                                                     stress r0i of particle  i at each timestep is then calculated
                                                          through the soil constitutive model represented by D:

                                  123

### Page 6

Acta Geotechnica

Fig. 2 Flowchart of implementation of single-layer soil-water coupled SPH at one timestep

dr 0i ¼ D : dei                                      ð20Þ    quantities are incorporated into the SPH implementation
                                                            discussed below.
   Equation (11) involves the second derivatives of Pw and
various approaches have been proposed to approximate the
second derivatives in the SPH method [7, 14, 65]. In this   3 Implementation of the proposed SPH
study, the classical approach proposed by Brookshaw [7] is    method
adopted to evaluate the second derivatives associated with
pore pressure response, since it is not sensitive to irregular    3.1 Flowchart of the simulation step
particle distributions [51]. Consequently, Eq. (11) can be
formulated in the SPH method as follows:                   Figure 2 outlines the sequence of calculations for each
     dPwi   2Kwk XN mj dPw h                              timestep of the coupled SPH approach, which is divided
                      dxarW  xai    xaj ; h             into three main parts. Part 1 introduces the updating pro-
       dt     ncw  j¼1 qj  r2ij
                                                 i      cess of densities, pore pressures and velocities of particles
       þdxbrW  xbi    xbj ; h þ dxcrW  xci    xcj ; h       by a  half-timestep ðdt=2Þ based on  the corresponding
                     !                   increments from the last timestep (or initial values) while                              debi                                      deci           þKw  dea                                                        i þ                  þ                                                          updating position of particles by one-timestep ðdt). Part 2
                 n    dt    dt    dt
                                                            focuses on the calculation of pore pressures from the vol-
                                                  ð21Þ    umetric strains and hydraulic gradients, and the calculation
                                                             of particle accelerations from the equation of motion. Inwhere dxa, dxb and dxc are the sepation distances between
                                                                Part 3, the densities and velocities of the particles are
particles i and j in different directions; dea; deb; dec are the
                                                        updated by a second half-timestep ðdt=2Þ based on the
strain  increments  in  different  directions.  Combining
                                                                     results from Part 1 and increment/acceleration from Part 2,
Eqs.  (16) and  (21),  the  discretized forms  of  various

123

### Page 7

Acta Geotechnica

but pore pressure and the increments are both obtained                    !                                                                                ðdxÞ2
from Part 2. Within each time step, the proposed approach      tk ¼                                              ð25Þ
                                                        k=ðn=Kw þ 1=ðK þ 4G=3ÞÞ
considers the coupling of  soil and water response by
evaluating the mechanical behavior through mass conser-   where tm is the timestep determined from the CFL critevation equation, momentum equation, and the seepage     rion,  tk  is the timestep from von Neumann  instability
response through the Darcy’s law and mass conservation    method, K and G are the bulk modulus and the shear
relationship.                                          modulus of soil, respectively. It should be noted that  tcri
  The  initial  velocities,  positions,  densities and  pore    above serves as a reference value to ensure numerical
pressures of particles are speciﬁed before the ﬁrst part of     stability,  but  the  timesteps adopted  in  the subsequent
the ﬂowchart. For each time step, the simulation results    simulations are not always identical to this reference value.
(i.e., particle velocity, pore pressure effective stress and   The adopted timestep values are adjusted to balance the
density) obtained from Part 3 of the ﬂowchart are carried    numerical stability and the computational time, as will be
forward to the next time step. In this study, the velocity    discussed in later sections and Appendix 2.
Verlet scheme is adopted for the time integration [58, 62].
However, the particle velocity lags behind the position by    3.3 Boundary treatment
half-timestep when forces are computed in the original
Verlet scheme, which may lead to poor conservation of    Near the domain boundary, there are insufﬁcient particles
total mass and energy in the numerical approximation    within the smoothing length and this leads to inaccurate
process of SPH [18]. Therefore, this study also adopts the     results in SPH approximations. Many techniques have been
recommendation by Ganzenmuller et al. [18], utilizing an    proposed thus  far for the boundary treatments in SPH
extrapolated velocity (vest) to update density, strain, pore    [32, 38,  42]. In  this  study,  virtual  particles (VP)  are
pressure and acceleration, and stabilize the time-stepping    introduced as ‘mirror images’ of the real particles across
algorithm. This extrapolated velocity of particle i at t1þn is    the domain boundary  to circumvent  the  limitation  of
deﬁned as follows:                                            insufﬁcient particles near the boundaries. For example, the
                       dvi                                        full-ﬁxity mechanical boundary can be modeled by the
 vest;i ð tnþ1 Þ ¼ vi ð tn Þ þ    ðtnÞdt                      ð22Þ
                       dt                                  approach proposed by Libersky [32], where the strains and
                                                                   stresses of virtual particles are equal to those of the corwhere vi ðtn Þ is the velocity of particle i at time tn; dvi=dtðtnÞ
                                                         responding real particles, while the forces and velocities of
is its velocity increment at time tn.
                                                                    virtual particles have the same magnitudes but act in the
  The proposed approach is implemented into LAMMPs
                                                            opposite direction as their counterparts (Fig. 3a). To model
[61], which has an efﬁcient built-in algorithm to search for
                                                                       roller boundaries, the boundary treatment proposed by
neighboring particles and facilitate parallel processing to
                                                   Mori [42] is adopted in this study (Fig. 3b), which also
enhance computational efﬁciency.
                                                                    entails modiﬁed virtual particles (MVP). However, along
                                                               the direction parallel to the roller boundary, the velocities
3.2 Critical timestep
                                                     and forces of those virtual particles act in the same direc-
                                                                  tions and magnitudes as real particles.
The choice of timestep in SPH method has a signiﬁcant
                                                          For hydraulic boundary conditions, the drained boundimpact on simulation  stability, accuracy, and computa-
                                                            ary is usually modeled by ﬁxing the pore pressure at the
tional efﬁciency. To ensure numerical stability in solving
                                                      boundary  as  a  certain  value,  whereas  the  undrained
the partial differential equations of seepage analysis, this
                                                      boundary is modeled using virtual particles that carry the
study considers both the Courant-Friedrichs-Levy (CFL)
                                                  same values of pore pressure as their counterparts across
criterion [33] and the Von Neumann instability method
                                                               the boundary. Hence, at the undrained boundaries (Fig. 4),
proposed by Anderson and Wendt [5]. The critical timestep
                                                               the ﬂow ﬂux arising from gravity qbw ð g Þ ¼  k has the sametcri for the soil-water coupled SPH method is determined by
                                                      magnitude but acts in opposite direction across the domaincombining these criteria as follows:
                                                         boundary. The derivative of ﬂow ﬂux associated with
 tcri ¼ min ðtm; tk Þ                                  ð23Þ                                                               gravity at the undrained boundaries can be represented as:
             dx                                                                       k                                                                            2k                                                        oqb                                                                                       ð k Þ                                                     w ð g Þ                                                                                                            ð26Þtm ¼ r ﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃ                                      ¼                                             ¼         4G  Kw                             ð24Þ                                                                        dxb                                                                                 dxb                                                           oxb      ðK þ  þ   Þ=q
            3    n
                                                               Therefore, considering gravity, the derivative of total
                                                 ﬂux at the undrained boundary would be:

                                  123

### Page 8

Acta Geotechnica

Fig. 3  Illustrations of mechanical boundary treatments a ﬁxed boundary and b roller boundary

                                                         dPwi   2Kwk XN mj dPw
                                                                   dt     ncw  j¼1 qj  r2ij
                                                           h
                                               dxarW  xai    xaj ; h þ dxbrW  xbi   xbj ; h
                                                                               i                        ð29Þ
                                    þ dxcrW  xci    xcj ; h
                                                    !
                                                     2Kwk  Kw  deai   debi    deci                                    þ   þ     þ  þ
                                                               ndxb    n    dt    dt    dt

                                                       3.4 Soil constitutive model

                                                 The constitutive model deﬁnes the relationship between
                                                                     stress and strain for a given material. Various constitutive
                                                         models, including  elastic,  elastoplastic, Cam-Clay, and
Fig.4 Diagram of ﬂow ﬂux at undrained boundary with consideration     critical state soil models, have been developed and sucof gravity                                                        cessfully implemented with FEM/FDM to model different
                                                             types of soil. Recently, Bui et al. [10, 13] presented the
                                                         implementation  of  the Drucker-Prager model  in SPH,
                                                             applied to capture large soil deformations during land-
                                                                       slides. The proposed method in this study employs an eoqbw     k   o2Pw    2k                                        lasto-plastic model to capture the large deformations of   ¼       þ                             ð27Þ
 oxb     cw  o ðxb Þ2   dxb                                      materials, where the yield function is deﬁned by the Mohr-
                                                Coulomb yield  criterion with non-associated ﬂow. The
  The pore pressure increments at the undrained boundary                                                                detailed formulations and validations of this constitutive
are deﬁned as:                                                   model were presented in Mori’s work [41], and now are
dPw    Kwk        2Kwk  Kw  d v                    brieﬂy illustrated in the Appendix 1.
   ¼      r2Pw þ    þ                    ð28Þ
  dt     ncw          ndxb    n    dt
                                                       3.5 Artificial viscosity and velocity damping
  Compared with Eq. (11), there  is an additional term                                                               for numerical stability
(2Kwk=ndxb)  for  particles  located  at  the  ﬁxed  and
undrained boundaries when considering  gravity, where                                                 The artiﬁcial viscosity Pij[41] is a commonly-used techdxb represents the separation distance between the bottom    nique in the SPH method to stabilize the calculations and
boundary and the particle immediately above the bound-    reduce numerical oscillations, while also preventing partiary,  along  the  direction  of  gravity. Hence,  the  pore    cle penetration. This viscosity is designed to only affect
pressure response at undrained boundaries at particle i. is     particles that are moving toward each other, and has no
written as:                                                        effect when particles move away from each other, as shown
                                                                  in the following equation:

123

### Page 9

Acta Geotechnica

   8
   <  aP/ijcij þ bP/2ij ; vijxij\0                                 vi ¼ 0:99vi                                       ð32Þ
Pij ¼              qij                                ð30Þ       vest;i ¼ 0:99vest;i                                   ð33Þ   :                   0; vijxij  0

           hijvijxij
/ij ¼     2                                        ð31Þ
          xij þ w2                            4 Validation of soil-water coupled SPH

where aP is used to reduce the acceleration of particles                                              To validate the proposed SPH algorithm  in soil-water
when they move toward each other, bP is used to avoid the                                                          coupling problems, a series of SPH simulations on selfinter-penetration of particles. In this study, aP is taken as                                                        weight  consolidation  problems  are  performed.  These
0.01, and bP is taken as 0.0; cij ¼ ðci þ cjÞ=2 is the mean
                 p ﬃﬃﬃﬃﬃﬃﬃﬃﬃ             include one-dimensional (1D) self-weight consolidations
value of c for particles i and j, where c ¼  K=P ; w is the    with different mechanical and hydraulic parameters, rangfactor to prevent numerical divergence which  is set to    ing from small-strain to large-strain conditions. This is then
around one-tenth of the smoothing length; hij ¼ ðhi þ hjÞ=2    extended to simulations of one-dimensional self-weight
is the mean smoothing length of particles  i and  j; qij ¼    consolidation problems with two-dimensional ﬂow. The
ðqi þ qjÞ=2 is the mean density of particle i and j; vij and xij    computed distributions of the pore pressure, strain proﬁle,
represent the velocity and position differences of particles i    and the average degree of consolidation are compared with
and  j. Therefore, vijxij\0 indicates two particles moving    the analytical solutions, other traditional numerical methtoward each other, and  vijxij  0 indicates two particles    ods or published results.
moving away from each other.
   In addition, ‘pre-steps’ are introduced at the model ini-    4.1 1D self-weight consolidation under small
tialization to allow the system to reach equilibrium before        strains
the subsequent simulations (of consolidation or sinkhole
                                    A soil column with height H ¼ 1 m and width D ¼ 0:2 mdevelopments) to ensure accurate results. In this study,
                                                                             is considered in the SPH model, as shown in Fig. 5. Thevelocity damping is employed during the pre-step to ensure
                                                                            initial spacing of the model is set as 0.02 m and the modelstability of stresses and strains at the initial stages of the
                                                   domain is discretized into 785 SPH particles including 224simulation, where the velocity and extrapolated velocity
                                                                    virtual particles. The soil is assumed to be an isotropic,are adjusted to 99% of their original values at each time-
                                                                      elastic material for comparisons between SPH simulationstep during the pre-step stage.
                                                                     results and analytical solutions. Particles along the lateral

Fig. 5 Geometry and boundary conditions of 1D self-weight consolidation

                                  123

### Page 10

Acta Geotechnica

Table 1 Parameters adopted in SPH model for self-weight consolidation

Parameter                            Value

Saturated density q (kg/m3)            1800
Poisson’s ratio m                     0
Porosity n                                0.4
Unit weight of water cw (N/m3)          10,000
                                     Small strain                                              Large strain
Saturated permeability k (m/s)          10-4         10-5         10-6         10-5           10-3         10-4         10-5
Young’s modulus of soil E (Pa)         25   106                                             25   103
Bulk modulus of water Kw (Pa)         2   109                                2   107         2   107
Timestep dt (s)                       10-6         10-5         10-5         10-4           10-4         10-4         10-4

Initial particle spacing (m)               0.02                                                        0.05

The selection of Poisson’s ratio, timestep and initial particle spacing are illustrated in Appendix 2. The base case refers to the small-strain case
with k ¼ 10  5 m/s, Kw ¼ 2   109 Pa, and dt ¼ 1  10  5 s

boundaries  are allowed  to move only  in  the  vertical    case under a different bulk modulus of water Kw are condirection. The particles along the bottom boundaries are    sidered  to  validate  the proposed model under various
ﬁxed in  all directions and undrained during the entire    conditions. The pore pressure proﬁle, strain proﬁle at iniconsolidation process. The cubic spline kernel function is      tial, transient processes and ﬁnal  state, as well as the
adopted in this study [38]. The parameters adopted in the    average degree of consolidation, are compared with the
simulations are shown in Table 1. The Poisson’s ratio is set    analytical solutions. The average degree of consolidation is
as 0 in this 1D case, since only the vertical stresses and   computed from the ratio of settlements ðSt   St0Þ=Sf , where
strains  are  relevant. The  timestep and  initial  particle     St and St0 are the settlements at  t and t0, and Sf  is the
spacing are chosen to balance the model  stability and    settlement at the ﬁnal state,  i.e., completion of the concomputation time.                                              solidation process.
  The simulation of 1D self-weight consolidation pro-       Figure 6 shows that the proﬁles of pore pressures and
cesses can be represented in two stages. Initially, the elastic     strains obtained by the proposed SPH approach under the
immediate deformation of the soil due to its own weight    base case, the case with Kw ¼ 2 MPa and the case with
produces volumetric strains across the model that result in    lower permeability k ¼ 1  10  6 m/s. All the SPH simudevelopments of pore water pressures and effective stres-    lation results are consistent with the analytical solutions at
ses, according to the following equations:                      different times, with the pore water pressure at its highest
     Kw               4   Kw                       value at the  initial state of the consolidation, and then
Pw0 ¼   qgðH   zÞ= K þ G þ                  ð34Þ    gradually reducing and approaching the hydrostatic state.       n                3     n
                                                          This indicates the proposed SPH approach is capable of
           4                  4    Kwrb0 ¼  K þ G qgðH   zÞ= K þ G þ           ð35Þ    matching the analytical solutions throughout the  entire
           3                  3     n                   transient process. In addition, as described in Sect. 3.3,
                                                             smaller Kw  normally  associates  with  large  timestep,where q is the saturated density of the soil and g represents
                                                            thereby  less computational  time. The good agreementgravitational acceleration, H is the height of the model and
                                                           provide reference for the selection of the bulk modulus ofz represents the elevation along the vertical direction of the
                                                          water in large-deformation simulations.model. The stress conditions represented by Eqs. (34) and
                                                             Figure 7 shows the average degrees of consolidation(35) constitute the ‘initial’ state (t ¼ t0) of the consolida-
                                                            evaluated by the proposed SPH method under differenttion, after which ﬂuid ﬂow is activated in the SPH simu-
                                                             hydraulic conductivities, and the results also agree verylations by ﬁxing the pore pressure at the top surface of the
                                                           well with the  analytical  solutions. Smaller timestep  ismodel as zero. During the consolidation process, the ﬂuid
                                                             required for case with larger hydraulic conductivity basedﬂow occurs toward the top surface, resulting in the dissi-
                                                   on the Von Neumann instability method. Despite differ-pation of excess pore water pressures which is balanced by
                                                          ences in the rates of consolidation and timesteps adoptedthe increase in the effective stresses. With time, the pore
                                                                  for cases with varying hydraulic conductivity, all simula-pressures gradually approach the hydrostatic conditions.
                                                                  tions reach the same hydrostatic state, as shown in Fig. 6a.  As shown in Table 1, besides the base case, two cases
under different values of hydraulic conductivity k, and one

123

### Page 11

Acta Geotechnica

Fig. 6 a Comparisons of development of pore pressure and strain between SPH and analytical solutions under base case and cases with different
permeabilities. b Comparisons of development of pore pressure and strain between SPH and analytical solutions under Kw ¼ 20 MPa

4.2 1D self-weight consolidation under large         modulus of water Kw is set as 20 MPa and initial particle
    strains                                            dx is set as 0.05 m, as shown in Table 1. A total of 205
                                                                    particles are included in the model with 100 virtual partiThe main advantage of the SPH method centers on  its     cles. In addition, three different hydraulic conductivities
capability to simulate large-deformation problems. This    are adopted to test the feasibility of the proposed method in
section presents the validation of the proposed approach for    handling large-deformation problems. For this large-strain
such problems, by adopting a small value of soil Young’s    simulation with k ¼ 10  4 m/s, it took 2300 min to reach
modulus 25 kPa in the self-weight consolidation analysis.    the  stable  ﬁnal  state  using  a  desktop computer  with
To  speed up  the  computational  calculation,  the  bulk    Inter(R) Core (TM) i9-10900 K CPU of 2.80 GHz.

                                  123

### Page 12

Acta Geotechnica

                                                              ﬁnite difference analyses. The model has a width of 10 m
                                                     and a height of 1 m, with the initial particle spacing set as
                                                           0.02 m, as shown in Fig. 10. The parameters adopted in
                                                                       this case are similar to the small-strain case in Table 1,
                                                          with v ¼ 0:25, Kw ¼ 2   109 Pa, k ¼ 1  10  4 m/s and
                                                                  dt ¼ 10  5 s. Similar to the one-dimensional ﬂow case, the
                                                                            initial state is obtained through the elastic deformation of
                                                               the soil domain. The pore pressure is then ﬁxed as zero at
                                                               the top surface and in the middle of the two-dimensional
                                                   model to activate the consolidation process. The horizontal
                                                     and bottom boundaries are undrained. Figure 11 presents
                                                               the strain distribution with time, showing that the strains in
                                                               the middle increase with the consolidation process. Fig-
                                                            ure 12 compares the pore pressure distribution in SPH
                                                             simulations with the ﬁnite difference method, which shows
                                                   good agreement and indicates that the proposed method
Fig. 7 Average degree of consolidation under different hydraulic
                                                     works well for 2D ﬂow problems, setting a solid foundation
conductivities
                                                                  for further extensions to the 2D sinkhole simulations in the
                                                           next section.   Figure 8 summarizes the development of pore pressures
with  soil  deformations, showing  that  the  excess pore
pressure dissipates as surface settlement increases during
                                       5 Simulation of sinkhole formationthe consolidation process. Figure 9 compares the results of
                                            experimentthe SPH simulations with the traditional numerical solutions, by solving the governing equations of large-strain
                                                         Sinkhole formations may be attributed to a number ofconsolidation using the ﬁnite difference method [52]. At
                                                                     factors, such as cracks and defects in the undergroundboth the initial state and ﬁnal state of the analysis, the
                                                                              utilities, and in some cases internal erosion of soils couldproﬁles of pore pressures and vertical strains are consistent
                                                         occur where the ﬁnes contents are removed from the soilwith ﬁnite difference solutions. Similar to the previous
                                                           matrix by seepage phenomena. As noted by Mukunokidiscussions, the hydraulic conductivity would inﬂuence the
                                                                      et al. [46] and Indiketiya et al. [23], the defect size (ortimestep adopted in the simulation and consolidation speed.
                                                           crack width) on the pipeline greatly affects the scale of soilDespite these variations, the ﬁnal state of the consolidation
                                                                  loss and ground failure, and continuous migration of soilremains nearly identical, as depicted in Fig. 9.
                                                   would occur  if the crack width exceeds the maximum
                                                                    particle size, in which case internal erosion may not be the4.3 1D self-weight consolidation with 2D flow
                                                   main cause of sinkhole formation. According to reports by
                                                               the Japanese government [37], several thousands of sink-To further validate the proposed soil-water coupled SPH
                                                           hole incidents occur every year and many of these failuresmethod, the one-dimensional consolidation problem with
                                                          involved cracks and defects in underground utilities withtwo-dimensional ﬂow  is simulated and compared with
                                                                  sizes larger than particle sizes of overlying soil materials.

Fig. 8 Development of pore water pressure with consolidation time t with k ¼ 10  4 m/s

123

### Page 13

Acta Geotechnica

Fig. 9 Comparisons of pore pressure proﬁle and strain proﬁle at initial and ﬁnal states between SPH and FDM solutions with different hydraulic
conductivities

Fig. 10 Geometry and boundary conditions of 2D ﬂow problem

Those ﬁndings indicate that, besides internal erosion with    of 500 mm and height of 200 mm with model thickness (in
the loss of ﬁnes, the sinkhole could also be initiated from a    direction perpendicular to the cross-section) of 150 mm.
large crack/opening, which was the scenario captured by   The variation of groundwater level in the soil is controlled
the physical tests (Fig. 13) and SPH simulations in this   by the water tank at two sides of the soil model, and
work (Fig. 16).                                          changes in pore pressures at the bottom of the model were
                                                          recorded every 60 s by manometers installed at an interval
5.1 Outline of sinkhole experiment                      of 50 mm. The surface displacements in the middle section
                                                             of the model (with a width of 70 mm) were measured every
A physical model test of sinkhole formation induced by    second by a multi-point laser placed as shown in Fig. 13.
seepage was conducted [59], and the test setup is shown   The   multi-point   laser  (KEYENCE  IX360-S)  was
schematically in Fig. 13. The physical model has a width

                                  123

### Page 14

Acta Geotechnica

Fig. 11  Strain contours at different consolidation times from SPH model

Fig. 12 Comparisons of pore pressure proﬁle at different locations and consolidation times between SPH and FDM solutions

manufactured by KEYENCE and the accuracy of the laser    distribution is illustrated in Fig. 14. Based on the results of
measurement is   0.15 mm [25].                              three drained triaxial tests with effective conﬁning pres-
  The soil used in the experiment is a sandy soil with a dry    sures of 50, 100 and 150 kPa, the cohesion and friction
density of 1320 kg/m3 and saturated density of 1830 kg/    angle were determined to be 0 and 34.5  , respectively.
m3, and the hydraulic conductivity was determined to be     The sinkhole experiment can be roughly divided into
2  10  4 m/s by constant head  test. The  particle  size   ﬁve main steps, as shown in Fig. 15. Step i: the soil was

123

### Page 15

Acta Geotechnica

Fig. 13 Schematic of the experiment modeling in section A   A0

                                                   50 mm (100 mm from the bottom), which initiated a larger
                                                                       soil deformation.

                                                       5.2 SPH model of sinkhole

                                                          This study simulates the phenomena observed in the center
                                                               section of the physical model. Figure 16 shows a schematic
                                                       diagram of the geometry and boundary conditions under
                                                               the initial condition of SPH simulations (Stage 0). A total
                                                             of 2975 particles are included in this numerical model with
                                                                            initial interval of 0.00625 m in both vertical and horizontal
                                                                   directions. The simulation is performed with a timestep of
                                                   10  7 s. The bottom boundary is ﬁxed in all directions with
                                                         undrained hydraulic condition, and the two sides boundFig. 14  Particle size distribution of the sand for drained triaxial test
                                                                    aries are roller boundaries with pore pressure ﬁxed as the
                                                               hydrostatic  state based on the phreatic surfaces  at the
                                                          corresponding  stages. The  techniques  to model  those
fully saturated by immersing the entire soil tank in water
                                                          boundaries are described in Sect. 3.3. For the top free
for 30 min; Step ii: the water levels in the water tank on the
                                                         boundary, the updating process for the pore pressure at the
two side boundaries were lowered to 50 mm and main-
                                                            top boundary at the onset of sinkhole formation will be
tained for another 30 min, Step iii: A 5-mm wide slit at the
                                                            presented later in this section.
bottom of soil tank was then uncovered to allow the ﬂow of
                                                To replicate the initial stress conditions of the experiwater and sand particles through it, initiating the formation
                                                   ment (Step  ii), the simpliﬁed self-weight consolidation
of a sinkhole, which is regarded as the initial condition of
                                                            process described in Sect. 4.1 is modeled in SPH. During
sinkhole formation in the SPH simulations (stage 0 in
                                                               the  pre-steps, the pore pressures throughout the  entire
Fig. 18); Step iv: the water table of the two sides of the
                                                   model are assigned and ﬁxed as the hydrostatic state based
water tank is ﬁxed as 50 mm and kept for 10 min; Step v:
                                                   on a water table of 50 mm above the bottom. Afterward,
the water table in the two sides of water tank was raised by
                                                               the stresses and strains develop according to the proposed

                                  123

### Page 16

Acta Geotechnica

Fig. 15 Diagram of the process of sinkhole experiment

Fig. 16 Schematic diagram of SPH model under the initial condition of simulations (Stage 0)

method  until  it reaches the stable  state, which  is also     The  Mohr-Coulomb  model  with   strain-softening
regarded as the initial stress condition in SPH model. To    behavior, which has been successfully used to simulate
simulate the initiation of sinkhole in experiment (Step iii),    landslides in the previous work [43], is adopted as follows:
ﬁve SPH particles (around 30 mm) at the bottom of the     8
                                                                                                                                                                                                                                                                                              0                                >< 1   ð 1  k Þ e   e0 /                                                                                                                                     if    e0   e   e1SPH model are removed in the simulation to activate the                   0
                                       / r ¼                  e1   e0sinkhole.       The             water table                             at the                          two                                     sides is                                    ﬁxed                                                as                                          50                             mm                                                                                                                                                                                                                                 0                                >: k/                                                                                                                                      if   e [ e1and the pore             pressure                   around                             the                             opening                                                   is                                    ﬁxed                                                as                                                 zero                                                           to
allow ﬂow out of the particles. Following Step (iv) of the                                                      ð36Þ
experiment, the lateral pore pressure of the SPH model is
                                                    where k is the strain-softening factor and is taken as 0.7; /0rupdated and ﬁxed as the hydraulic state under the water
                                                                             is the reduced friction angle; e0 and e1 are strain levels attable of 100 mm.  It is noted that since the  slit in SPH
                                                               the start and the end of the strain-softening stage, which are
model is bigger than that of the physical model, to ensure
                                      6% and 20%, respectively.
the same hydraulic gradient between the side boundaries to
                                                          Table 2 summarizes the SPH model parameters for
the  slit of the physical model, the SPH model is set as
                                                            sinkhole  simulation.  Apart  from  the  shear  strength
slightly wider than the physical model (with side bound-
                                                            parameters, the soil modulus was also inferred from triaxial
aries 25 mm further away from the center).

123

### Page 17

Acta Geotechnica

Table  2 Parameters  adopted  in SPH  simulation  of  sinkhole     1.0. Hence, in this SPH model, the magnitude of the negexperiment                                                        ative pore water pressures above the phreatic surface are
Parameter                                  SPH       simply calculated by multiplying the unit weight of water
                                                      cw with the distance to the phreatic surface. As the position
Saturated density q (kg/m3)                          1830                                                             of phreatic surface changes during the simulation of the
Saturated permeability k (m/s)                        2  10  4                                                        coupled process  of  soil deformation and seepage,  the
Poisson’s ratio m                                        0.25        detailed processes to determine the location of phreatic
Porosity n                                                 0.5         surface  at  a  certain  timestep, and  the  pore  pressure
Unit weight of water cw (N/m3)                         10,000      response at the top surface are as follows:
Young’s modulus of soil E (Pa)                       5  106
                                                                  (1)  Based on the pore pressure values and positions of all
Bulk modulus of water Kw (Pa)                       2  109
                                                                             particles, the coordinates with zero pore pressure
Cohesion c ðPaÞ                                    0
                                                                    across the model are interpolated.
Friction angle / ðoÞ                                      34.5
                                                                  (2)  The phreatic surface  is determined by ﬁtting the
Strain-softening factor k                                   0.7                                                                   coordinates with zero pore pressure into a quadratic
Timestep (s)                                       1  10  7                                                             polynomial function.
Initial particle spacing (m)                             0.0065       (3)  The elevation differences between the top surface
                                                          and the phreatic surface are used to calculate the
                                                                  negative pore pressures at the top surface of the
                                                             model. Negative pore pressures for other particles
                                                           above the phreatic surface is updated based on the
                                                              seepage analysis proposed in this method.

                                                       5.3 Experimental observations and simulation
                                                                results

                                                 The displacement proﬁles were not  strictly two-dimen-
                                                                sional (plane-strain) in the experiment; instead, the center
                                                             of the model (along the longitudinal direction) tends to
                                                 show larger deformation at several stages, as shown in
                                                                 Fig. 18b. This is possibly due to the inﬂuence of friction
                                                     between the soil and walls of the model tank. By com-
                                                            bining both front views (Fig. 18a) and top views (Fig. 18b)
                                                             of the experiment, as well as the measurements of the
Fig.17 Relationship between Young’s modulus and effective conﬁn-    multi-point laser in the middle of the physical model, the
ing stress from triaxial test and SPH model
                                                              surface displacements in the middle of the physical model
                                                     were obtained and are depicted by the dotted lines in
test data. The E50 values (secant Young’s modulus at 50%
                                                                 Fig. 18c, which are regarded as the actual outlines of the
peak strength) were obtained from three sets of triaxial
                                                            sinkhole and serve as the benchmark for comparisons with
tests, and plotted in Fig. 17 in a log–log scale, following a
                                                               the SPH simulation.
similar concept of the Duncan-Chang model [17].  It  is
worth noting that the physical model of the sinkhole was
                                                       5.4 Failure process of sinkhole
around 200 mm in height, with effective stress levels in the
order of 1 kPa, and much lower than those in the triaxial
                                                           Figure 19 presents the overall development process of the
tests. The Young’s modulus adopted in the SPH model
                                                            sinkhole and the associated  failure pattern observed  at
(5000 kPa) is also plotted on Fig. 17 and it appears to form
                                                               several key stages of the experiment, in comparison with
a reasonable overall trend with the test data.
                                                               the simulation  results by the proposed SPH approach.
   Since the physical model had a total height of only
                                                           Figure 19a shows the overall failure process of the physical
200 mm and the hydraulic conductivity of the soil is rel-
                         4                                    experiment obtained from the above ﬁgures. Figure 19batively large (2  10    m/s), the pore pressure above the
                                                              presents the pore pressure development of the sinkhole
phreatic  surface  can  remain  at  or  quickly  reach  the
                                                     from SPH simulation. Figure 19c illustrates the develophydrostatic pressure. The degree of saturation for the soil
                                                   ment of axial strains with the legend from 0.2 to 7.0. Note
above the phreatic surface can be assumed to be close to
                                                                    that these are the strain levels beyond the end of the strain-

                                  123

### Page 18

Acta Geotechnica

Fig. 18 Snapshots of the failure process of sinkhole observed from a front view b top view and c middle-section view of the experiment

softening  stage  in  the  stress-strain model described n    development of the sinkhole, the subsurface cavity at the
Eq. (35). Besides, the inﬂuence zone of the sinkhole failure    bottom of the model expanded until it failed to sustain the
can be identiﬁed based on the characteristics of the soil    overburden and collapsed. Meanwhile, signiﬁcant shear
displacement proﬁles as shown in Fig. 19d, where the     strains and displacements had developed in the center of
inﬂuence zone  is speciﬁed as the regions with vertical    the SPH model, and a notable collapse of the soils was also
displacement greater than 10 mm. The corresponding mass    observed in the experiment and SPH model.
loss ratio R ¼ Nloss=Ntotal at different stages of the sinkhole      At Stage 3, the water levels at the two side boundaries
experiment is also presented in the SPH model, where Nloss    were raised to 100 mm above the bottom of the model. The
is the number of particles that left the SPH model domain,    water table inside the model was raised accordingly and
and Ntotal is the total number of particles at the initial state    caused a  larger hydraulic gradient between the model
of the simulation.                                          boundaries and the opening. A more dramatic collapse of
   Stage 0 represents the initial condition of the sinkhole    the sinkhole was then observed both in the experiments and
formation, where the slit has just been removed to initiate   SPH model, leading to a wider but shallower settlement at
the failure. No visible shear stress or surface displacement    the surface that was eventually observed at the end of the
is observed at this stage. At Stage 1 and Stage 2, the water    experiment (Stage 4). Similar patterns are also observed
levels at the side boundaries were maintained at the same    from the shear strain proﬁles and displacement proﬁles
level. Water started to ﬂow into the opening and led to a    obtained from the SPH model, where the failure surface
lower phreatic surface as indicated by the pore pressure    and inﬂuence zone become wider after raising the water
proﬁles. The soil around the opening was washed away     table.
with the seepage ﬂow to form a small arch at the bottom of         It is important to note that the SPH model results not
the model and a shallow subsidence trough at the top    only match  with  the observed  failure  process  in  the
surface of the model  at Stage  1. With the continuous    experiment but also provide insights into the evolution of

123

### Page 19

Acta Geotechnica

Fig. 19 Comparison of sinkhole developments observed in physical experiments and SPH simulations: a snapshots from experiment;
b development of pore water pressure from SPH model; c development of shear strain from SPH model; d development of vertical displacement
from SPH model

Fig. 20 Development of phreatic surface under water level of 50 mm and water level of 100 mm at side boundaries

pore water pressures, shear strains, and soil displacements    from the experiment are deduced based on the pore presaround the sinkhole. This information allows for a thor-    sure measurements by the manometer. From the experiough investigation of the failure mechanism. Thus, the    ment, after removing the slit at the bottom, water ﬂowed
model serves as an effective tool to capture the progression    from the  lateral boundaries toward the opening in the
of sinkhole failures under varying hydraulic conditions and    middle, while the phreatic surface changed according to the
to explore the root causes and processes of failure.           hydraulic gradient. From Stage 0 to Stage 2, the phreatic
                                                              surface gradually dropped with time, and it was raised from
5.5 Development of phreatic lines and surface         Stage 2 to Stage 4 after the water table at the boundary
    settlement                                               sides was raised to 100 mm. These trends and changes in
                                                          pore pressure responses are reasonably captured by the
While the previous section provides a qualitative compar-   SPH model, which indicates that the hydraulic aspects of
ison of the SPH model and experimented results. Figure 20    the process are properly modeled in the simulations.
presents the proﬁles of phreatic lines at different stages of      Comparisons of surface settlements between the physisinkhole formation, comparing the experimental and SPH    cal model and SPH simulation are shown in Fig. 21. The
simulation results, where the proﬁles of the phreatic line    experimental observations and simulation results showed

                                  123

### Page 20

Acta Geotechnica

Fig. 21 Surface displacement proﬁles at different stages of sinkhole development

similar trends of settlement response at various stages of    porosities during the displacement process, (3) Stress-dethe test. As described earlier, the soil deformations grad-    pendency of soil stiffness and strength as the stresses vary
ually developed after the opening of the slit, compounded    signiﬁcantly throughout the process, (4) Simpliﬁcation of
by changes  in  the seepage  conditions and  eventually    boundary treatment around the sinkhole opening. Further
resulted in a wide settlement at ﬁnal stages of the experi-    investigation  of  these  factors  is  warranted  in  future
ments. The good agreements with experimental data show    research.
that the mechanical aspects of the sinkhole development
process are also reasonably captured by the proposed soilwater coupled SPH approach.                    6 Parametric study of sinkhole formation
   Despite the generally good agreements between SPH     process
model and experiment at the key failure stages of sinkhole,
some discrepancies are observed between the physical    6.1 Variation of parameters
model and SPH simulations from Figs. 19, 20 and 21,
which may be attributed to these factors: (1) The hetero-   To further explore the failure mechanism of the sinkhole
geneity  of  soil  properties  in  the  physical model,  (2)    collapse and assess the inﬂuence of  different material
Alterations in soil permeability as a result of evolving soil    parameters and groundwater conditions on the failure pat-
                                                                      terns, a parametric study by SPH simulations is presented
                                                                 here, where the shear strength parameters, Young’s modTable 3 Parameters adopted in parametric study of sinkholes          ulus of the  soil, and the groundwater conditions were
                                                                 varied. A total of seven numerical cases are established, asCase      Friction      Cohesion   Young’s modulus   Water
number   angle / ðoÞ   c ðPaÞ       of soil E (Pa)        table (mm)   summarized in Table 3. Cases 1, 2, and 3 are established to
                                                           study the  effects of  soil shear strength parameters on
Base     34.5        0         5   106           50                                                            sinkhole formation; the results from Case 4 and Case 5 are
  case
                                                    compared with the base case to reveal the inﬂuences of
1        31.5        0         5   106           50
                                                    Young’s modulus of soils; Case 6 and Case 7 focus on the
2        37.5        0         5   106           50                                                                   effects of the groundwater conditions. For each of Cases 1
3        34.5        50        5   106           50            to 7, except the speciﬁc factors being studied, all other
4        34.5        0         5   105           50           conditions are kept the same as the base case. Note that in
5        34.5        0         1   107           50          Case 3, the cohesion value is assigned by matching the
6        34.5        0         5   106           100          shear strength with that of Case 2 (with zero cohesion) to
7        34.5        0         5   106           150           investigate the relative contributions of friction angle and
                                                         cohesion to sinkhole occurrences.

123

### Page 21

Acta Geotechnica

Fig. 22 Comparison of the maximum surface displacements under different a shear strength parameters, b Young’s moduli, c water levels

6.2 Development of surface settlements                trough but slightly smaller maximum surface displacement.
                                                                                   It should be noted that the comparisons in Fig. 22c focus
The relationships between the maximum surface displace-   on inﬂuence of water levels on settlements at the same
ment with the mass loss ratio R are adopted in this study to   mass loss, which does not necessarily occur at the same
characterize the development of sinkholes, as shown in    time across different models. The rate of development for
Fig. 22. The maximum  surface  displacements  in  all    surface displacement (i.e., settlement with time) is another
numerical models were observed directly above the open-    topic that has been investigated by a number of researchers
ing of the sinkhole (i.e., at center of model). The maximum    [19, 36, 53].
surface displacement caused by sinkholes tends to increase
with the mass loss. However, their magnitudes vary under    6.3 Effects on failure mechanism of sinkholes
different conditions, even at the same mass loss.
  The developments of the maximum surface displace-    Considering  different sinkhole simulations  at the same
ment in Case 1 (/=31:5 ) and the base case (/=34.5 ) are   mass loss ratio, the models with small surface settlements
similar. However, as the friction angle (/) increases further    are generally associated with formations of subsurface
to 37:5  ,  the maximum  surface  displacement  starts  to    cavities below the model ground surface. To  facilitate
develop slowly with mass loss, particularly for the stage    comparative  analysis  of  various  scenarios,  the model
when R\3%. With an increased cohesion value of 50 Pa,    response is evaluated at a reference point of 5% mass loss
the surface deformation  is restricted, and the numerical     ratio ð R Þ. Figures 23, 24 and 25 present a visual repremodel remains stable once R reaches 2%, without further    sentation of the displacement ﬁelds and shear strain ﬁelds
displacement at higher R. The comparisons suggest that    across different conditions.
high shear strength parameters of soil correspond to a small      Comparing the failure patterns, it is evident that as the
surface deformation under the same mass loss. In addition,    shear strength parameters or Young’s modulus of soils
with  the same  effective shear  strength,  the impact of    increase, the surface subsidence  is suppressed, while a
cohesion on sinkhole formation is greater than that of the    small subsurface cavity is observed near the bottom of the
friction angle. Similar to shear strength parameters, an   SPH model. This helps to explain the differences in the
increase  in  the  material  stiffness  generally  results  in    development of maximum surface displacement shown in
reduced maximum settlements at the same loss ratio, as    Fig. 22. Higher shear strength/Young’s modulus provides
demonstrated in Fig. 22b. However, the differences caused    resistance against soil collapse by forming a subsurface
by various water levels are minor compared to those of the    cavity within the soil. As the soil around the opening leaves
soil properties, according to Fig. 22c. The development of    the model, the soil displacements propagate to the surface
the maximum surface displacement is relatively consistent    only when the subsurface cavity can no longer sustain the
at the early stage of sinkhole formation ðR\3%Þ, while a    load. As a result, cases with higher shear strength and
higher water table tend to result in a wider settlement

                                  123

### Page 22

Acta Geotechnica

Fig. 23 a Displacement ﬁelds and b shear strains of sinkhole under different shear strength parameters at mass loss ratio R of 5%

Fig. 24 a Displacement ﬁelds and b shear strains of sinkhole simulations with different Young’s moduli at mass loss ratio R of 5%

Young’s modulus generally exhibit smaller surface dis-    water levels are high, due to the high hydraulic gradient
placements for a given mass loss ratio.                    between the model boundaries and the sinkhole opening.
  The inﬂuence zones of sinkhole failures under different    This trend is also reﬂected in the failure surfaces depicted
conditions are shown in Fig. 23a to Fig. 25a. As the shear    in Fig. 23b to Fig. 25b, where a high shear strength and
strength parameters and Young’s modulus  of  the  soil   Young’s modulus are correlated with narrow failure volincrease, the inﬂuence zone becomes smaller. On the other    umes, while a higher water table results in wider, extended
hand, the inﬂuence zone expands when the surrounding     failure surfaces.

123

### Page 23

Acta Geotechnica

Fig. 25 a Displacement ﬁelds and b shear strains for sinkhole simulations with different water levels at mass loss ratio R of 5%

7 Conclusions                                          and Young’s modulus parameters are more suscep-
                                                                              tible  to surface deformation and  larger inﬂuence
This study introduces a fully-coupled SPH model to cap-          zone. The groundwater level primarily impacts the
ture the behavior of large soil deformations associated with           size of the inﬂuence zone in sinkhole development,
soil-water  interactions, where  the  soil movement and         with higher water levels resulting in a wider and
seepage across the model are regarded by a continuum           larger inﬂuence zone.
approach. The pore pressure response is accurately represented by considering both the hydraulic gradient and
volumetric strain through a single layer of SPH particles, to   Appendix 1
strike a balance between model accuracy and computational efﬁciency. The key contributions and ﬁndings of the                                                 The theory, implementation and validation of the Mohrstudy are summarized as follows:                                                Coulomb model in SPH method were elaborated by Mori
(1)  A  single-layer  soil-water coupled SPH model  is    [42]. The main concepts and example validations would be
     proposed and validated through comparison with    brieﬂy presented here.
      analytical  solutions  of  self-weight  consolidation
      problems. These demonstrates the validity of the    Elastic response
     approach and lays the foundation for its application
      to other geotechnical problems.                         Prior to the plastic regime, an isotropic linear elastic model
(2)  The method is applied to simulate physical experi-     is adopted:
     ments of seepage-induced sinkholes, to demonstrate     dee ¼ D 1dr                                      ð37Þ
        its capacity to handle large-deformation problems      2          3
      involving  soil-water  interactions. The  numerical           a1 a2 a2 0 0 0
                                                                   a2 a1 a2 0 0 0     approach is shown to be able to capture the critical
                                                                   a2 a2 a1 0 0 0       failure process of such sinkholes.             D ¼                                              ð38Þ
                                                          0 0 0 G 0 0(3)  A parametric study was conducted to examine the                                                                                                                                                                                                                                                                                                         6666664 0 0 0 0 G 0   7777775     impact of material properties and groundwater levels
                                                          0 0 0 0 0 G
     on sinkhole formation. The results show that, at the
     same mass loss ratio, cases with low shear strength   where a1 ¼ K þ 4G=3, a2 ¼ K   2G=3.

                                  123

### Page 24

Acta Geotechnica

Yield function                                    Hardening law

This study adopts the Mohr-Coulomb yield function to    In the elasto-plastic analysis process, an initial assumption
deﬁne the onset of plastic straining, with the center position     is made with all the strain components being elastic, in
ro and radius r of the Mohr-circle formulated as:            order to obtain the ‘trial stresses’ (r ). A plastic correction
     1                                                                    is subsequently made if r   is found to exceed the yield
ro ¼   ra þ rb                                   ð39Þ     criterion, in which case the corrected principal stresses are     2
    1 q ﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃ                               given by:
r ¼     ð ra   rb Þ2þ4 ðrab Þ2                        ð40Þ
    2                                                    r1 ¼ r1   ks a1  a2Nw                           ð51Þ

where ra, rb, rab are the effective stresses in x, y; and xy    r2 ¼ r2   ks a2  a2Nw                           ð52Þ
directions when rc is the intermediate effective stress. The
                                                         r3 ¼ r3   ks a2  a1Nw                           ð53Þprincipal effective stresses are then formulated as:
                                                To satisfy the consistency condition, Eqs. (51) to (53)
r1 ¼ ro þ r                                       ð41Þ                                                                                  s                                                       can be substituted into Eqs. (43) and (44) with f ¼ 0, in
r3 ¼ ro   r                                       ð42Þ   which case the plastic multiplier ks is formulated as:
                                    p ﬃﬃﬃﬃﬃﬃ                                                                 N/  The Mohr-Coulomb failure criterion is deﬁned as:              r1  r 3N/   2c                                                                   ks ¼                                             ð54Þ  s        p ﬃﬃﬃﬃﬃﬃ f ¼ r1  r3N/   2c  N/                         ð43Þ         a1  a2Nw    a2  a1Nw N/

     1 þ sin /                                         With the corrected principal stresses, the normal and
N/ ¼                                            ð44Þ
     1   sin /                                             shear  stresses  in Cartesian directions can be obtained.
                                                      These updated stress values are used in Step 2.e of Fig. 2
where r1 and r3 are the major and minor principal effec-                                                     and are updated at each step.
tive stresses, and c; / represent the cohesion and friction
angle of the soil, respectively.
                                                          Verification

Flow rule
                                    A 1D compression test in plane strain condition is simu-
                                                                 lated to test the implementation of Mohr-Coulomb models
This study adopts the non-associated ﬂow rule, with the
                                                     and boundary treatments in the SPH method, with the
plastic potential function deﬁned as follows:
                                                          parameters adopted shown in Table 4, and geometry and
gs ¼ r1  r3Nw                                   ð45Þ    boundary conditions shown in Fig. 26a. The model consists
                                                             of 153 soil particles with uniform initial interval of 0.01 m.     1 þ sin w
Nw ¼                                            ð46Þ     The relationship between the axial strain and axial stress     1   sin w
                                                             of the particle located at the model center are illustrated in
and w is the dilatation angle. The ﬂow rule determines the
magnitude and direction of plastic strain increments. For
the elastic behavior, the directions of elastic strains are     Table 4 Parameters adopted in SPH model for compression test
governed by direction of stress increment dr; while for    Parameter         Value        Parameter
plastic behavior, the direction of plastic strains is governed
                                                                        Saturated density        1800    Dilation    0by the current stress state r and the plastic potential gs:
                                                        q (kg/m3)                        angle
         ogs                                                     Shear modulus of   5:56   106    Gravity    Nodep ¼ ks                                          ð47Þ
       or                                                                     soil G (Pa)
                                                              Bulk modulus of    4:17   106    Total        5:0   106
where ks is the plastic multiplier to be elaborated in the        soil K (Pa)                         steps
next section. The incremental plastic strains in the principal                                                                        Porosity n                    0.3  Time step   2:0  10  6
directions are derived as follows:                                                                                    (s)
dep1 ¼ ks                                          ð48Þ     Unit weight of         10; 000    Total time  10.0                                                                     water cw (N/m3)                       (s)
d p2 ¼ 0                                          ð49Þ    Cohesion c (Pa)           105     Artiﬁcial   Yes
                                                                                                                   viscosity     ð a ¼ 1:0; b ¼ 1:0Þ
dep3 ¼  ksNw                                     ð50Þ     Friction angle /           30o

123

### Page 25

Acta Geotechnica

Fig. 26 a Geometry of the compression test; b Comparison of SPH simulation results with theoretical values

Fig. 26b. Upon yielding, the axial strains develop further   Appendix 2
without an increase  in axial  stress, which follows the
plastic behavior of the model under drained conditions. The   The Poisson’s ratio was set as zero in the simulations of 1D
results of SPH simulation in the response of volumetric    consolidation  in Sects. 4.1 and  4.2. To investigate the
strain of the particle located at the model center are plotted    inﬂuence of the Poisson’s ratio on simulation results, a case
in Fig. 26c. The volumetric strains stay constant in the    with  Poisson’s  ratio  of 0.25  is conducted with  other
plastic region with zero dilation angle. The simulations    parameters being the same as the base case. The comparresults by the SPH method are almost identical to the    isons of pore water pressure and strain proﬁles with anatheoretical values.                                                   lytical solutions are illustrated in Fig. 27. Compared with
                                                                 Fig. 6a, changing the Poisson’s ratio of material would
                                                                   affect material response and the SPH simulation results, but
                                                               the response from SPH simulations still match very well
                                                          with the analytical solutions.

Fig. 27 Comparisons of pore pressure and strain proﬁles between SPH and analytical solutions with Poisson’s ratio of 0.25

                                  123

### Page 26

Acta Geotechnica

                                                        computation time increases signiﬁcantly in the meantime.
                                              To  strike a balance between  the model accuracy and
                                                          computational  efﬁciency,  the  small-strain  consolidation
                                                             cases involve initial particle spacing of 0.02 m.

                                                             Acknowledgements The work presented in this paper  is ﬁnancial
                                                                     supported by the Research Grants Council of the Hong Kong Special
                                                                      Administrative Region (Project No. R5037-18). The code for SPH
                                                                       analyses in this study can be accessible by contacting the authors.

                                            References

Fig. 28 Inﬂuences of the timestep on surface settlement at the ﬁnial
                                                                                  1. Abe K, Soga K, Bandara S (2014) Material point method for
state of the consolidation
                                                                      coupled hydromechanical problems. J Geotech Geoenviron Eng
                                                                     140(3):04013033
                                                                                  2. Al-Halbouni D, Holohan EP, Taheri A, Scho¨pfer MP, Emam S,
                                                    Dahm T (2018) Geomechanical modelling of sinkhole develop-
                                                               ment using distinct elements: model veriﬁcation for a single void
                                                                        space and  application  to  the Dead Sea  area.  Solid  Earth
                                                                     9(6):1341–1373
                                                                                  3. Alsaydalani MOA, Clayton CRI (2014) Internal ﬂuidization in
                                                                            granular soils. J Geotech Geoenviron Eng 140(3):04013024
                                                                                  4. An Y, Wu Q, Shi C, Liu Q (2016) Three-dimensional smoothed-
                                                                                    particle hydrodynamics simulation of deformation characteristics
                                                                                  in slope failure. Ge´otechnique 66(8):670–680
                                                                                  5. Anderson JD, Wendt J (1995) Computational ﬂuid dynamics.
                                                                   McGraw-Hill, New York
                                                                                  6. Belytschko T, Lu YY, Gu L (1994) Element-free Galerkin
                                                                      methods. Int J Numer Anal Methods Geomech 37(2):229–256
                                                                                  7. Brookshaw L (1985) A method of calculating radiative heat
Fig. 29 Inﬂuences of the initial particle spacing
                                                                               diffusion  in  particle  simulations. Proc Astron Soc  Australia
                                                                   6:207–210
  To  further  investigate  the inﬂuence  of timestep on       8. Bui HH, Giang DN (2017) A coupled ﬂuid-solid SPH approach to
simulation results, a series of cases with various timesteps        modelling ﬂow through deformable porous media. Int J Solids
                     6            5            5            4                Struct 125:244–264(dt ¼  5  10   s; 1  10   s; 5  10   s; 5  10   s; 1
                                                                                  9. Bui HH, Fukagawa R (2009) A ﬁrst attempt to solve soil water
10  3 s; 5  10  3 s) are simulated with other parameters        coupled problems by SPH. Terra Mech 29:33–38
same as the base case, and the results are illustrated in     10. Bui HH, Fukagawa R, Sako K, Ohno S (2008) Lagrangian
Fig. 28. The simulation results are not signiﬁcantly affec-        meshfree  particles method (SPH)  for  large deformation and
                                                                                     failure ﬂows of geomaterial using elastic–plastic soil constitutive
ted by the timestep when the SPH model is stable, but                                                                     model. Int J Numer Anal Meth Geomech 32(12):1537–1570
model collapse may occur when the timestep is too large.     11. Bui HH, Nguyen GD (2021) Smoothed particle hydrodynamics
As expected, the computation time increases with smaller        (SPH) and its applications in geomechanics: from solid fracture to
timesteps. As a result, the timesteps adopted in this study         granular behavior and multiphase ﬂows in porous media. Comput
                                                                   Geotech 138:104315
are in some cases larger than the values deﬁned by the tcr     12. Bui HH, Sako K, Fukagawa R (2007) Numerical simulation of
(Eq. 23), as the CFL [33] and Anderson and Wendt [5]         soil-water interaction using smoothed  particle hydrodynamics
criteria only provide reference values to enhance numerical        (SPH) method. J Terramech 44(5):339–346
stability. The values adopted in this work are adjusted to     13. Bui HH, Fukagawa R (2013) An improved SPH method for
                                                                               saturated soils and its application to investigate the mechanisms
balance the model stability and accuracy with demands on                                                                            of embankment failure: case of hydrostatic pore-water pressure.
the computational time.                                                       Int J Numer Anal Meth Geomech 37(1):31–50
  A  series  of  tests  with  different  particle  intervals     14. Chen JK, Beraun JE, Carney TC (1999) A corrective smoothed
(dx ¼ 0:01 m; 0:02 m; 0:04 m; 0:05 m)  are  conducted  to          particle method for boundary value problems in heat conduction.
                                                                                      Int J Numer Anal Methods Geomech 46:231–252
investigate their inﬂuences on consolidation simulations,                                                                        15. Cui X, Li J, Chan A, Chapman D (2014) Coupled DEM–LBM
with other parameters  identical  to the base  case. The         simulation of internal ﬂuidisation induced by a leaking pipe.
response of pore pressure and strain at the bottom of the       Powder Technol 254:299–306
model at time  t ¼ 10 s are shown in Fig. 29, with the     16. Dehnen W, Aly H (2012) Improving convergence in smoothed
                                                                                    particle hydrodynamics simulations without pairing instability.
corresponding computation time. The results indicate that                                                   Mon Not R Astron Soc 425(2):1068–1082
the accuracy of the simulation results improves slightly     17. Duncan JM, Chang CY (1970) Nonlinear Analysis of Stress and
with  reduction  in  the  initial  particle  spacing, but  the         Strain in Soils. J Soil Mech Found Div, ASCE 96(5):1629–1653

123

### Page 27

Acta Geotechnica

18. Ganzenmu¨ller GC, Steinhauser MO, Van VP, Leuven KU (2011)     40. Monaghan JJ, Lattanzio JC (1985) A reﬁned particle method for
   The  implementation  of  smooth  particle  hydrodynamics  in         astrophysical problems. Astron Astr 149(1):135–143
   LAMMPS. Katholieke Universiteit Leuven. pp 1–26                41. Monaghan JJ, Gingold RA (1983) Shock simulation by the par-
19. Guo S, Shao Y, Zhang TQ, Zhu DZ, Zhang YP (2013) Physical           ticle method SPH. J Comput Phys 52(2):374–389
    modeling on sand erosion around defective sewer pipes under the     42. Mori H (2008) The SPH method to simulate river levee failures.
    inﬂuence of groundwater. J Hydraul Eng 139(12):1247–1257            University of Cambridge, Cambridge
20. He XZ, Dong FL, Bolton MD (2018) Run-out of cut-slope     43. Mori H, Chen XY, Leung YF, Shimokawa D, Lo MK (2020)
    landslides: mesh-free simulations. Ge´otechnique 68(1):50–63            Landslide hazard assessment by smoothed  particle hydrody-
21. Huang Y, Dai Z, Zhang W, Chen Z (2011) Visual simulation of        namics with  spatially  variable  soil  properties and  statistical
    landslide  ﬂuidized  movement  based  on  smoothed  particle          rainfall distribution. Can Geotech J 57:1953–1969
    hydrodynamics. Nat Hazards 59:1225–1238                         44. Morikawa DS, Asai M (2022) Soil-water strong coupled ISPH
22. Huang Y, Zhang W, Dai Z, Xu Q (2013) Numerical simulation of        based on formulation for large deformation problems. Comput
   ﬂow  processes  in liqueﬁed  soils  using a  soil-water-coupled        Geotech 142:104570
    smoothed   particle  hydrodynamics  method.  Nat  Hazards     45. Mullet B, Segall P, Fa´vero Neto AH (2023) Numerical modeling
    69:809–827                                                             of caldera formation using Smoothed Particle Hydrodynamics
23. Indiketiya S, Jegatheesan P, Rajeev P, Kuwano R (2019) The        (SPH). Geophys J Int 234(2):887–902
    inﬂuence of pipe embedment material on sinkhole formation due     46. Mukunoki T, Kumano N, Otani J (2012) Image analysis of soil
    to erosion around defective sewers. Transp Geotech 19:110–125          failure on defective underground pipe due to cyclic water supply
24. Karimi H, Taheri K (2010) Hazards and mechanism of sinkholes        and drainage using X-ray CT. Front Struct Civ Eng 6(2):85–100
   on Kabudar Ahang and Famenin plains of Hamadan. Iran Nat     47. Pastor M, Haddad B, Sorbino G, Cuomo S, Drempetic V (2009)
    Hazards 55(2):481–499                             A depth-integrated, coupled SPH model for ﬂow-like landslides
25. KEYNECE. Laser 360mm IX360. Available from https://www.        and related phenomena. Int J Numer Anal Methods Geomech
    keyence.com/products/sensor/positioning/ix/models/ix-360/.             33(2):143–172
    Accessed 5 June 2022                                              48. Pastor M, Martin Stickle M, Dutto P, Mira P, Ferna´ndez Merodo
26. Kuwano R, Hiorii T, Kohashi H, Yamauchi K (2006) Defects of        JA, Blanc T, Benı´tez AS (2015) A viscoplastic approach to the
    sewer pipes causing cave-ins’ in the road. In: 5th International        behaviour  of ﬂuidized geomaterials with  application  to  fast
   symposium on new technologies for urban safety of mega cities          landslides. Continuum Mech Thermodyn 27:21–47
    in Asia (USMCA), Phuket, Thailan.                                 49. Pastor M, Yague A, Stickle MM, Manzanal D, Mira P (2018) A
27. Li SF, Liu KW (2002) Meshfree and particle methods and their        two-phase SPH model for debris ﬂow propagation. Int J Numer
    applications. Appl Mech Rev 55(1):1–34                           Anal Methods Geomech 42(3):418–448
28. Li SF, Liu KW (2007) Meshfree  particle methods. Springer     50. Potts DM, Zdravkovic´ L, Addenbrooke TI, Higgins KG, Kova-
    Science & Business Media, UK                                                        cˇevic´ N (2001) Finite element analysis in geotechnical engi-
29. Lian Y, Bui HH, Nguyen GD, Tran HT, Haque A (2021) A         neering: application (2). Thomas Telford, London
    general SPH framework  for  transient seepage ﬂows through     51. Price DJ (2012) Smoothed particle hydrodynamics and magne-
    unsaturated  porous media  considering  anisotropic  diffusion.        tohydrodynamics. J Comput Phys 231(3):759–794
   Comput Methods Appl Mech Eng 387:114169                      52. Pu H, Wang K, Qiu J, Chen X (2020) Large-strain numerical
30. Lian Y, Bui HH, Nguyen GD, Zhao S, Haque A (2022) A         solution for coupled self-weight consolidation and contaminant
    computationally efﬁcient SPH framework for unsaturated soils         transport considering nonlinear compressibility and permeability.
    and its application to predicting the entire rainfall-induced slope       Appl Math Model 88:916–932
     failure process. Ge´otechnique 9:1–19                                53. Rawal K, Hu LB, Wang ZM (2017) Numerical investigation of
31. Lian Y, Bui HH, Nguyen GD, Haque A (2023) An effective and         the geomechanics of sinkhole formation and subsidence. Geotech
     stabilised (u-  pl) SPH framework for large deformation and         Front 2017:480–487
     failure analysis of saturated porous media. Comput Methods Appl     54. Romanov D, Kaufmann G, Al-Halbouni D (2020) Basic pro-
   Mech Eng 408:115967                                                  cesses and factors determining the evolution of collapse sink-
32. Libersky LD, Petscheck AG, Carney TC, Hipp JR, Allahdadi FA         holes-a sensitivity study. Eng Geol 270:105589
    (1993) High strain lagrangian hydrodynamics: a three-dimen-     55. Scheperboer IC, Suiker AS, Bosco E, Clemens FH (2022) A
    sional SPH code for dynamic material responses. J Comput Phys        coupled hydro-mechanical model for subsurface erosion with
    109:67–75                                                             analyses of soil piping and void formation. Acta Geotech 17:1–30
33. Liu GR, Liu MB (2003) Smoothed particle hydrodynamics: a     56. Soga K, Alonso E, Yerro A, Kumar K, Bandara S, Kwan JSH,
    meshfree particle method. World Scientiﬁc, Singapore              Koo RCH, Law RPH, Yiuk J, Sze EHY (2018) Trends in large-
34. Liu MB, Liu G (2010) Smoothed particle hydrodynamics (SPH):        deformation analysis of landslide mass movements with partic-
    an overview and recent developments. Arch Comput Methods          ular emphasis on  the  material  point method.  Ge´otechnique
   Eng 17(1):25–76                                                   68(5):457–458
35. Lucy LB (1977) A numerical approach to the testing of the ﬁssion     57. Sulsky D, Zhen C, Howard LS (1994) A particle method for
    hypothesis. Astron J 82(12):1013–1024                                 history-dependent materials. Comput Methods Appl Mech Eng
36. Luu LH, Noury G, Benseghier Z, Philippe P (2019) Hydro-me-        118:179–196
    chanical modeling of sinkhole occurrence processes in covered     58. Swope WC, Andersen HC, Berens PH, Wilson KR (1982) A
    karst terrains during a ﬂood. Eng Geol 260:105249                   computer simulation method for the calculation of equilibrium
37. Ministry of Land, Infrastructure, Transport and Tourism (MLIT),         constants for the formation of physical clusters of molecules:
    (2002).  https://www.mlit.go.jp/road/sisaku/ijikanri/pdf/r1-r3kan         application to small water clusters. J Chem Phys 76(1):637–649
    botu.pdf                                                            59. Takumi K, Watanabe K, Nakagawa S, Mori H, Simokawa D
38. Monaghan JJ (1992) Smoothed particle hydrodynamics. Annu         (2020). Model experiments for the displacement of a ground
   Rev Astron Astr 30(1):543–574                                         surface on the process of a caving and a sinkhole. In: 55th Pro-
39. Monaghan JJ (2012) Smoothed particle hydrodynamics and its         ceedings  of  the  Japan  national  conference on  geotechnical
    diverse applications. Annual Rev Astron Astr 44:323–346               engineering

                                  123

### Page 28

Acta Geotechnica

60. Tang Y, Chan DH, Zhu DZ (2017) A coupled discrete element          rainfall using a water-soil-coupled smoothed particle hydrody-
   model for the simulation of soil and water ﬂow through an oriﬁce.        namics model. Acta Geotech 116:1401–1418
     Int J Numer Anal Methods Geomech 41(14):1477–1493             67. Zhang W, Xiao D (2019) Numerical analysis of the effect of
61. Thompson AP, Aktulga HM, Berger R, Bolintineanu DS, Brown         strength parameters on the large-deformation ﬂow process of
  WM, Crozier PS, Plimpton SJ (2022) LAMMPS-a ﬂexible sim-        earthquake-induced landslides. Eng Geol 260:s
    ulation tool for particle-based materials modeling at the atomic,     68. Zhang W, Zheng H, Jiang F, Wang Z, Gao Y (2019) Stability
    meso, and continuum scales. Comput Phys Commun 271:108171         analysis of soil slope based on a water-soil-coupled and paral-
62. Verlet L (1967) Computer ‘‘experiments’’ on classical ﬂuids.          lelized Smoothed Particle Hydrodynamics model. Comput Geo-
      I. Thermodynamical properties of Lennard-Jones molecules. Phys         tech 108:212–225
   Rev 159(1):98
63. Wang Y, Qin Z, Liu X, Li L (2019) Probabilistic analysis of post-                                                                             Publisher’s Note Springer Nature remains neutral with regard  to
     failure behavior of soil slopes using random smoothed particle                                                                                jurisdictional claims in published maps and institutional afﬁliations.
    hydrodynamics. Eng Geol 261:105266
64. Wendland H (1995) Piecewise polynomial, positive deﬁnite and
                                                                      Springer Nature or its licensor (e.g. a society or other partner) holds
    compactly  supported  radial  functions  of  minimal  degree.
                                                                        exclusive rights to this article under a publishing agreement with the
   Advances Comput Math 4(1):389–396
                                                                           author(s)  or  other  rightsholder(s);  author  self-archiving  of  the
65. Zhang GM,  Batra RC  (2004) Modiﬁed  smoothed  particle
                                                                     accepted manuscript version of this article is solely governed by the
    hydrodynamics method and its application to transient problems.
                                                                    terms of such publishing agreement and applicable law.
   Comput Mech 34:137–146
66. Zhang W, Maeda K, Saito H, Li Z, Huang Y (2016) Numerical
    analysis on seepage failures of dike due to water level-up and

123
