# Lian 2023 u-pl

> Auto-converted from PDF for Codex/code-reference reading. Formatting, equations, figures, and tables may require checking against the original PDF.

- Source PDF: `Lian 2023 u-pl.pdf`
- Pages: 33

## Extracted Text

### Page 1

Available online at www.sciencedirect.com
                        ScienceDirect

                              Comput. Methods Appl. Mech. Engrg. 408 (2023) 115967
                                                                                                         www.elsevier.com/locate/cma

   An effective and stabilised (u −pl) SPH framework for large
     deformation and failure analysis of saturated porous media
            Yanjian Liana, Ha H. Buia,∗, Giang D. Nguyenb, Asadul Haquea

                                                 a Department of Civil Engineering, Monash University, Australia
                              b School of Civil, Environmental & Mining Engineering, University of Adelaide, Australia

                     Received 17 October 2022; received in revised form 27 January 2023; accepted 17 February 2023
                                                       Available online 3 March 2023

Abstract

   Particle-based methods such as SPH have been proven to be powerful numerical tools for addressing challenges in solving
coupled large deformation and failure of porous materials. In these applications, explicit time integration schemes are commonly
adopted to integrate the coupled pore-water pressure equation. The Courant–Friedrichs–Lewy condition is required and imposes
a strong restriction on the time increment, which is inversely proportional to the water bulk modulus, leading to a significant
increase in the overall computational costs. This affects successful applications of SPH in solving field-scale fully coupled large
deformation and failure of porous media. To address this problem, this study proposes a computationally efficient three-point
integration (TPI) scheme that removes the influence of water bulk modulus from the pore-water pressure equation, enabling
larger time increments for the time integration and hence saving computational costs for field-scale applications. Furthermore,
a stabilised method is proposed to enable SPH to solve coupled flow-deformation of saturated porous media involving negative
excess pore-water developments for the first time. The proposed SPH algorithm is verified against analytical and finite element
solutions for small deformation ranges. Thereafter, it is applied to predict challenging problems involving large deformation
and retrogressive failure of saturated porous materials, where contractive and dilative responses of porous materials can cause
significant variations and instabilities in the development of excess pore-water pressure. The results suggest that the proposed
SPH algorithm is stable and suitable for handling field-scale applications.
© 2023 Elsevier B.V. All rights reserved.

Keywords: SPH; Three-point integration (TPI); Large deformation; Coupled flow-deformation analysis; Retrogressive failure

1. Introduction

   Developments of safety assessment and disaster prevention guidelines for engineering earth structures require a
sound knowledge of coupled flow deformation analysis in saturated and unsaturated porous media and advanced
computational tools that can foresee the worst-case scenarios should they happen (e.g., the impact of landslides
or embankment failures should they occur). The Finite Element Method (FEM)  is one of the most popular
computational tools that are robust and could give satisfactory results for fully coupled problems involving small
deformation analysis [1]. However, when dealing with large deformation and post-failure behaviour of materials,

  ∗Corresponding author.
    E-mail address:  ha.bui@monash.edu (H.H. Bui).

https://doi.org/10.1016/j.cma.2023.115967
0045-7825/© 2023 Elsevier B.V. All rights reserved.

### Page 2

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

the standard FEM becomes less competitive due to the inherent severe mesh distortion issue [1–3]. Recent
advanced mesh-based FEM methods have resulted in several powerful numerical methods capable of handling large
deformation and post-failure behaviour of porous materials, such as the particle finite element method (PFEM) and
material point method (MPM) [4–8]. An alternative approach to the FEM-based methods is the fully mesh-free
methods, such as the Smoothed Particle Hydrodynamics (SPH) method, which offer an excellent capability to handle
large deformation and post-failure problems.
  As the eldest truly continuum-based mesh-free method, the SPH method was initially developed for astrophysical
applications [9,10]. Since its successful applications in solving large deformation of elastoplastic materials [11], SPH
has been widely used to solve a range of challenging geotechnical problems, including granular flows [12–15], slope
failures [16–21], soil–structure interactions [22–25], desiccation cracking in soils [26,27] and rock fractures [28–30],
to name a few. Besides, there exist two SPH approaches for solving coupled fluid–solid interaction problems, namely
the multi-layer approach [1,31–33] and the single-layer scheme [3,34–39]. In the first approach, the multiphase
porous media is represented by multiple layers of particles, each of which follows its governing equations. The
governing equations of each phase are solved separately on their own set of Lagrangian SPH particles. In the latter
approach, the porous media is represented by a single layer of Lagrangian SPH particles, each of which carries all
field information. The fully coupled governing equations are then established and solved on a single set of SPH
particles [34–37,39].
  The single-layer approach for coupled flow-deformation analysis is computationally cheaper than the multi-layer
scheme. However, several challenges still exist in terms of numerical stabilities or computational costs associated
with this approach when used for large-scale applications. For example, in the earliest attempt to solve the fully
coupled problems of fluid-saturated porous media using the single-layer SPH approach (i.e., fully explicit) based
on the (u −pl) formulation (u stands for solid displacement and  pl  indicates pore-water pressure), Bui and
Fukagawa [34] reported that strong fluctuation in the development of excess pore-water pressure was observed and
attributed to large water bulk modulus and small water permeabilities. This instability in the pore-water pressure
field is also a common issue in other Galerkin-based numerical methods (e.g., FEM and MPM) when applied to
the coupled flow-deformation analysis of saturated porous media in the limit of undrained condition (i.e., very
low permeability) with incompressible pore-fluid. It is often referred to as the inf-sup condition or Lady zenskaja–
Babuˇska–Brezzi (LBB) condition in the literature [40,41], and advanced integration methods (e.g., direct α-method
or the fractional-step method) are commonly used in FEM or MPM simulations [2,41–43] to address this issue. In
this study, stabilised techniques are also proposed to address this challenge within the context of the SPH method.
   Apart from the first attempt at solving the coupled flow-deformation problem in saturated media [34], Blanc and
Pastor [44] also presented a single-layer SPH model (u −pl) adopting the so-called stress point approach and a
fractional-time integration scheme based on the Runge–Kutta Taylor SPH algorithm, promising results were obtained
when compared to analytical solutions. Recently, more attempts based on the single-layer SPH approach have been
reported in the literature. For instance, Morikawa and Asai [38] presented a single-layer SPH approach based on
the (u −w −pl) formulation (w is the water flow velocity) to solve coupled flow-deformation of saturated soils,
adopting an incompressible SPH (ISPH) approach to solve the pore-pressure equation (i.e., implicit) and achieved
promising results, particularly for 1D consolidation problems compared to analytical solutions. Lian et al. [36,37]
proposed an efficient single-layer SPH framework based on the (u−pa−pl) formulation (pa is the pore air pressure)
for describing the dynamics flows and fully coupled deformation of unsaturated porous media (i.e., fully explicit),
which were fully validated against analytical solutions and experiments. Ma et al. [39] extended the single-layer
SPH approach proposed by Lian et al. [36,37] to solve their five-phase mathematical model to describe a complex
seepage-induced internal erosion and failure of porous media process and achieve promising results compared to
both analytical solutions and experiments. Overall, the single-layer SPH approach has been proven to be a robust
method to deal with field-scale and complex coupled problems of saturated and unsaturated porous media. However,
existing fully explicit SPH solvers are restricted by the CFL condition, which imposes a strong constraint on the
timestep increment, which is inversely proportional to the water bulk modulus [2,45,46], hence causing a significant
increase in the overall computational costs. Therefore, an alternative time integrations scheme is still needed to
improve its computational efficiency.
   This paper aims to address the above limitations of the fully explicit SPH solver in solving the fully coupled
problems of saturated porous media by proposing an efficient and stabilised SPH framework. The paper is organised
as follows: first, the fully coupled two-phase SPH computational framework based on the (u −pl) formulation for

                                                          2

### Page 3

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

saturated porous media is briefly introduced. Thereafter, a three-point integration (TPI) scheme is proposed and
verified by means of a range of 1D consolidation and 2D bearing capacity problems. Finally, the enhanced SPH
framework is applied to predict the granular collapse of fully saturated soils and retrogressive failure problems to
illustrate the capability of the model in the fully coupled flow-large deformation analysis.

2. Governing equations of the framework

2.1. Governing differential equations

   In this study, the following assumptions are used in the derivation of the mathematical framework for the fully
saturated porous medium:

       i. The saturated medium consists of a solid skeleton and a connected void filled with water.
      ii. The solid grain and the water phase are assumed to be incompressible.
    iii. The system is isothermal, and no mass exchange among phases.
    iv. Terzaghi’s effective stress concept is assumed to be acceptable.

Based on the above assumptions, a brief introduction of the governing equations (i.e., u −pl formulation) for fully
coupled flow-deformation analysis is given in this section. The behaviour of saturated porous media is governed by
the interaction between solid skeleton and pore-fluids, each of which is considered as a homogenised continuum
that follows its governing equations, which take the forms of:
       dαvα
     ρα   = ∇· σ α + ραb − ∑ Rs                                                                           (1)
          dt
where ρα = nαρα is the partial density of phase α; b is the body force vector; σ α is the partial stress for each
phase, which is given for solid and water phases as follows, respectively:
    σ s = σ ′ −(1 −n) plI
                                                                                                                     (2)
    σ l = −nplI
where n is the porosity; I is the second-order unity identity tensor; pl the pore-water pressure; σ ′ = σ + plI is
Terzaghi’s effective Cauchy stress, which is valid for saturated porous media with incompressible solid grains; and
σ = σ s + σ l is the total Cauchy stress tensor.
  The drag force vector between fluid and solid phases Rs in Eq. (1) takes the following form:
           nρlg
     Rs =     nwαβ −pl∇n                                                                                     (3)
           kα
where kα denotes the second-order permeability tensor of the fluid phase α, which is a function of void ratio
following the form of [37,47]:
               (e −e0 )
     ka (e) = k0sat exp                                                                                              (4)
                      Ck
where k0sat = ksatI is the permeability tensor; e and e0 are the current and initial void ratio, which can be linked to
porosity change; Ck is the Kozeny–Carman coefficient; and ρl stands for the intrinsic mass density of water. The
last term on the right-hand side in Eq. (3) is known as the Buoyancy force acting on the solid phase.
   Substituting Eq. (3) into the momentum balance equation for the water phase, the following relative velocity
between the solid and water phase in fully saturated soil can be obtained [36,37,46,47]:
               kl (                 dsvs )
      wls =     −∇pl + ρlb −ρl                                                                                (5)
             nγl                    dt
The momentum equation for the entire mixture can be obtained by adding the momentum equation for each phase,
and after neglecting the relative acceleration between solid and water, yielding [46]:
      dsvs    1
      =  ∇· σ + b                                                                                          (6)
       dt      ρt
where ρt is the total density.

                                                          3

### Page 4

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

   Different from the double-layer SPH approach, where the motion of the mixture is achieved by solving each
phase’s momentum equation [1], in this single-layer SPH model, the motion of the mixture is achieved by solving
Eq. (6). The behaviour of the water phase is described by the evolution of pore-water pressure as an additional
variable to the solid particle. The governing equation for the pore-water pressure evolution can be derived from the
mass balance equations. The general form of the mass balance equation for each phase in the mixture is given as:
     dαρα
      + ρα∇· vα = 0                                                                                        (7)
       dt
By substituting the partial density of the solid phase into Eq. (7), the mass balance equation for the solid phase in
terms of the time derivative of porosity can be obtained:
     dsn
      = (1 −n) ∇· vs                                                                                         (8)
       dt
It is noted that Eq. (8) is obtained by enforcing the incompressibility of the solid grain. Similarly, the following mass
conservation equations for the water phase can be obtained by introducing the partial density in Eq. (7) as [36,37]:

      n ds pl
        + ∇· vs + ∇· (nwls) = 0                                                                           (9)
      Kl  dt
where Kl stands for the fluid bulk modulus. By introducing Eq. (5) into Eq. (9), the general equations governing
the seepage flow through deformable saturated porous media can be obtained as follows:
      ds pl    Kl {         1                     1  (  dsvs )}
      =   −∇· vs +  ∇· [kl∇(pl + ρlgz)] +  ∇·  kl                                            (10)
       dt     n                 γl                     g         dt
where z is the elevation, which becomes zero if the gravity is neglected.
   Equation (10) governs the evolution of pore water pressure in the deformable saturated porous media, and together
with Eqs. (6) and (8), they form three fundamental governing equations, also known as the (u−pl) formulation, for
the coupled flow-deformation framework of saturated porous media. Besides the (u−pl) formulation, another form
of formulation, namely (u−w), can also be obtained using the same derivation process by neglecting the convective
term or the relative acceleration term. Thus, (u −w) and (u −pl) formulations share similar features and are more
appropriate for low-frequency dynamics problems [46,48,49], which is the focus of this study. For high-frequency
problems, such as earthquake-induced failure problems, the (u−w−pl) formulation was often recommended [46].

2.2. Constitutive equation

  A constitutive relation is required to describe the soil’s deformation behaviour or to compute the effective stress in
the above governing equations. Detailed descriptions of how to implement a material constitutive model in SPH can
be found in Bui and Nguyen [3]. In this study, only essential formulations are summarised to provide background
for our SPH development. The effective stress increment is updated using the following equation:
    dσ J = De ( dϵ −dϵ p) = dσ ′ + dω · σ ′ −σ ′ · dω                                                       (11)

where De is the elastic stiffness matrix; dσ J is the increment of the Zaremba–Jaumann stress tensor of the effective
Cauchy stress tensor according to the updated Lagrangian approach using small strains; dω stands for the spin
increment tensor; and dϵ p is the plastic strain increment, which takes the form of:
     dϵ p = dλ∂g0′                                                                                         (12)            ∂σ
where g0 is the plastic potential function; and dλ is the non-negative plastic multiplier, which can be computed
using the semi-implicit stress return mapping algorithm given by [3] :
                                      f
    dλ =                                                                                                 (13)
                 ∂f        ∂g0     ∂f √ 2 ∂g0  ∂g0
              ∂σ ′                       : De : ∂σ ′ + ∂κ   3 ∂s  :  ∂s

with  f being the trial value of a plastic-yielding function caused by an elastic stress increment, assuming no plastic
deformation. The Drucker Prager (DP) strain-softening constitutive model [3,37,50,51] is adopted in this study. The

                                                          4

### Page 5

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

yielding and plastic potential functions of this model take the following forms, respectively:
          f = ξφ I1 + √ J2 −κc                                                                                 (14)
      g0 = ξψ I1 + √ J2                                                                                      (15)

where I1 and J2 are the first and second invariants of the effective stress tensor; ξφ and κc are DP constitutive
parameters related to the friction (φ) and cohesion (c) of the soil. Under the plane strain condition, these parameters
are defined by:
             tanφ                     3c
      ξφ =                        κc =                                                                      (16)
      √ 9 + 12tanφ2       √9 + 12tanφ2
Finally, the following softening laws are adopted to replicate the critical state behaviour of the soil subjected to
large shear deformation [3,37,50,51]:
    φ = φr + ( φp −φr ) exp ( −ηεeqp )                                                                      (17)
      c = cr + ( cp −cr ) exp ( −ηεeqp )                                                                       (18)
   ψ = ψ0 exp ( −s f εeqp )                                                                                  (19)
where the subscripts p and r denote the peak and residual strengths of the material, respectively; η is the softening
coefficient controlling the rate of shear strength degradation with the plastic strain of the material; εeqp   is the
accumulated equivalent plastic strain; ψ is the dilation angle; ψ0 is the initial dilation angle; and s f  is a constant
controlling the rate of dilatancy reduction.

3. SPH discretisation for the governing equations

3.1. A brief overview of SPH

   In SPH, the computational domain is discretised into a finite number of particles, with each particle carrying
the field quantity, including mass, density, velocity and pressure [11]. These variables and their gradients at a given
particle location are then computed by means of an integral process that uses the information from its surrounding
particles by a kernel function. Let us first consider an arbitrary field quantity function  f (x) at any point x in the
computational domain, the integral representation of this function can be written as follows:

                N
      ⟨f (xi)⟩= ∑ Vj f ( x j ) W ( xi −x j, hsml )                                                              (20)
                  j=1
where the angle bracket ⟨  ⟩indicates the kernel approximation operator; Vj is the volume occupied by particle j;
W ( xi −x j, hsml ) is a symmetric smoothed (or kernel) function, which has a characteristic length hsml defining
an effective domain Ωof the smoothing function. Among several popular kernel functions reported in the
literature [3,52], the cubic spline kernel function is adopted in this paper, which takes the following forms:
            ⎧ 2       1                 −q2 +      0 ≤q < 1                     3       3q3                                               ⎪⎪⎪⎨    W(q, hsml) = αd  1                                                                                   (21)
                         (2 −q)3     1 ≤q < 2
                                               ⎪⎪⎪⎩ 06            q > 2

where αd is the dimensional normalising factor defined by αd = [1/h, 15/7πh2, 3/2πh3] for one, two and three-

                                                                                                                                                                          jdimensions, respectively; and q is the normalised distance defined as q = ⏐⏐xi −x                                                                                        ⏐⏐/hsml where hsml = 1.2dx with
dx being the initial distance between particles.
  The SPH approximation for both the first-order and second-order gradient of function  f (xi) can be obtained by
applying the Taylor series expansion of function  f ( x j ) about xi, and there exist several formulations reported in
the literature [3,36]. In this work, the following corrected SPH formulation for the first-order gradient of  f (xi) is
adopted [53,54]:

                 N
    ∇m                i   f (xi) = ∑ Vj [ f ( x j ) −f (xi)] ˆ∇mi Wi j                                                            (22)
                    j=1

                                                          5

### Page 6

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

                                                                 ]−1                                                                       being the normalised matrix, and mwhere ˆ∇mi Wi j = Lmni j ∇ni Wi j with Lmni j = [∑Nj=1 Vj ( x j −xi )m ∇ni Wi j
and n indicate coordinate direction with repeated indices implying summation. Similarly, several robust SPH
approximations exist for the second-order derivatives in the literature [3,36,55,56]. In this work, the general SPH
approximation for the second-order derivatives, recently proposed by the authors and achieved excellent accuracy
for highly disordered particle systems, is adopted and takes the forms of [36]:
       ∂2 fi      N                           N        = ∑ Vj ( f j −fi ) Dmn ˜Fi j −∂fi              ∑ Vjrm′ji Dmn ˜Fi j                                           (23)     ∂xm∂xn                              ∂rm′
                   j=1                               j=1
                  rmjirnji                                                                        rmjiwhere Dmn = 4    −δmn with δmn being the Kronecker delta function; and  ˜Fi j =          · ˆ∇mi Wi j  is the scalar                       |r ji|2                                                                                           |r ji|2
part of the normalised kernel gradient, with r ji = x j −xi being the distance vector, and ∂f/∂rm′ is the firstorder spatial gradient calculated from Eq. (22). It is noted that Eq. (23) shares a similar form to that proposed
by Espa˜nol & Revenga (2003) [56], except the last term on the right-hand side of the equation, which helps to
remove approximation errors caused by particle distortion  [36]. In this work, Eqs. (20), and (22)–(23) are adopted
to discrete the governing equations for the coupled seepage-deformation framework, which is given in the next
section.

3.2. SPH discretisation of the governing equations

  The change of porosity determined by Eq. (8) can now be converted into the SPH approximation form. This can
be achieved by applying Eq. (22) to the divergence term in Eq. (8), leading to the following SPH approximation
for the porosity:

             N
      dni
      = ∑ Vj ( 1 −n j ) vsji ˆ∇iWi j                                                                       (24)
      dt
              j=1
where vsji is the velocity difference between two particles. Once the porosity of the soil skeleton is determined from
Eq. (24), the variation of saturated permeability and the specific moisture term can be updated. Similarly, the SPH
approximation for the time derivative of pore-water pressure can be obtained:
         ⎧    N                    N
                                                       ji      dpl             Kl ⎨ 1 ∑      =                      Vjk mn                           plji Dmn ˜Fi j + ∑ Vjk mnzji  jiDmn ˜Fi j
      dt  i    n    γl
         ⎩    j=1                      j=1
                       N                N
                    ∂pli ∑                           Vjrm′ji Dmn ˜Fi j                      − ∑ Vjvsji ˆ∇iWi j         −kmni                   ∂rm′
                           j=1                  j=1
                 N            ⎫
                                                            ji )                                     ˆ∇iWi j ⎬                                                                (25)        +1 ∑ Vjk mnji (dvs
             g              dt
                    j=1           ⎭

where k mn               ji = ( kimn + k mnj ) /2 is the arithmetically mean value of water permeability; plji = (plj −pil ) is the pressure
difference; z ji in the second term of Eq. (25) is the elevation difference between particles, which could vanish if
gravity is not considered.
  The motion of the solid particle is described by the momentum equation of the whole mixture in terms of total
stress, i.e., Eq. (6), which is given as follows:

                N
               (σ i + σ j    )    (dvs )
        = ∑ Vj      + Ci j  ∇iWi j + b                                                        (26)
        dt      i    j=1         ρti
where ρt  is the total density of particle i, which varies over time with the degree of saturation; and Ci j  is a
stabilisation term consisting of the artificial viscosity and artificial stress commonly adopted in SPH to remove
stress fluctuation and tensile instability, respectively [11,14,18,57,58]. In this paper, the same formulations and
recommended parameters for the stabilisation term previously reported in [11,18] for geomechanics applications
are adopted, except that the sound speed of soil required for the artificial viscosity is computed following [18].

                                                          6

### Page 7

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

3.3. SPH time discretisation

  The Leap-Frog (LF) algorithm is usually used to integrate the SPH approximation equations developed in the
preceding section. In this approach, the state variables (Υ), including porosity (n), water pressure (pl), effective
stress (σ ′) and velocity (vs), are updated at the mid-step in time, while the displacement vector is updated at the
full-time step as follows:

                  (dΥ )
     Υt+∆t/2 = Υt−∆t/2 + ∆t                                                                              (27)
                                dt      t
      xst+∆t = xst + ∆t · ( vs) t+∆t/2

The stability of the LF time integration scheme is maintained by the Courant–Friedrichs–Lewy (CFL) condition.
The commonly-used CFL criterion to ensure the stability of the fully explicit time integration scheme for the fully
coupled analysis of saturated porous media is [2,42,46] :
                     l
     ∆ts ≤                                                                                                 (28)
              csp
where l is the length scale, which can be taken as the initial distance between SPH particles; and csp is the sound
              √( Klspeed defined as csp =                                n                + 43G ) /(nρl + nsρs).
  The time step size given in Eq. (28) is inversely proportional to the fluid bulk modulus (Kl); thus it is often very
small if an actual value of fluid bulk modulus is adopted, causing a significant increase in the overall computational
costs. This issue can be addressed using the proposed TPI algorithm, which will be described in the next section.

3.4. Three-point integration (TPI) scheme

  To address the issue associated with the large water bulk modulus and enable a larger time step size, let us first
recast the seepage flow governing equation, i.e., Eq. (10), into the following forms:
      n ds pl                           (  dsvs )        + ∇· vs −1 ∇· [kl∇(pl + ρlgz)] −1 ∇·  kl    = 0                                     (29)
      Kl  dt                γl                     g         dt
Next, to remove the influence of the water bulk modulus from the above equation, one could enforce the
incompressibility condition to the water phase, leading to the vanishing of the specific storage term Cl = n/Kl.
Accordingly, the governing equation for seepage flow in deformable porous media is reduced to:
                           (  dsvs )    ∇· vs −1 ∇· [kl∇(pl + γlz)] −1 ∇·  kl    = 0                                                 (30)
                  γl                   g         dt
The key question now is how to find the solution for the pore-water pressure pl in Eq. (30), and this can be achieved
in several ways. By expanding the second derivative term, Eq. (30) can be rewritten as follows:
                                      (  dsvs )
    ∇· ( kl∇pl t+1)i = γl (∇· vs)i −γl∇· [kl∇(z)]i −ρl∇·  kl                                            (31)                                                                dt       i
  The second derivative of the pore-water pressure in Eq. (31) can be discretised using the recently proposed SPH
approximation (23) [36], which leads to:

             ⎡ N               ⎤
                                                                                                            (32)    ∇· ( kl∇pt+1l   )i = ⎣ ∑ (                                      pl t+1j  −pl it+1 ) Ai j −Ei ⎦
                            j=1

where the operator Ai j and the error source term Ei j are given as follows:
      Ai j = Vjk mnDmnji         ˜Fi j                                                                                   (33)
                    N
                 ∂pli ∑       Ei = kmni                        Vjrm′ji Dmn ˜Fi j                ∂rm′
                       j=1

                                                          7

### Page 8

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

where k mn               ji = ( kimn + k mnj ) /2 is the arithmetically mean value of water permeability. By substituting the above SPH
approximation into Eq. (31), the following equation can be obtained:

      N
  ∑ (                                           + Ei                       (34)              pl t+1j  −pl it+1 ) Ai j = γl (∇· vs)i −γl∇· [kl∇(z)]i −ρl∇· ( kl dsvs )
                                                                        dt       i       j=1
The above equation was written in the form of a linear system equation of unknown variables being pt+1l    . This linear
system equation can be solved using a precondition conjugate gradient iterative method [59]. However, this method
requires very high memory storage to store the particle matrix and appropriate free-surface pressure boundary
conditions; thus,  it is limited to a small number of particles. Alternatively, a more straightforward approach is
used in this study to solve the above pore-water pressure equations. This can be achieved by further expanding
Eq. (34), giving:
         t+1    Bi j + ∑Nj=1 Ai j pl t+1j
       pl i  =                                                                                               (35)
           ∑Nj=1 Ai j
where Bi j is the source term for pl it+1 defined as follows:
                               (  dsvs )
      Bi j = −γl (∇· vs)i + γl∇· [kl∇(z)]i + ρl∇·  kl     −Ei                                          (36)
                                                      dt       i
For a small-time increment, the unknown pt+1l   on the right-hand side of Eq. (35) can be approximately assumed
equal to ptl from the previous time step, i.e., pt+1l  ≈ptl , [1,59–61], leading to:
         t+1    Bi j + ∑Nj=1 Ai j pltj
       pl i  =                                                                                               (37)
          ∑Nj=1 Ai j
Both two terms on the right-hand side of Eq. (37) are known at instant t, and thus the pressure pt+1l    at time t + 1
can be explicitly calculated. Eq. (37) removes the pore-water pressure dependence from the water bulk modulus,
thus enabling a larger time step size for the time integration of the pore pressure equation. However, some cares
still need to be taken to obtain a stable and accurate solution. This is because Eq. (37) makes use of pl t+1j  ≈pltj,
and thus could only produce accurate results for a small time increment [1,59–61]. Hence, this assumption might
lead to accumulated errors in the numerical solution when a large time increment is used [61]. To mitigate this
issue, the above pore-pressure update equation can be revised as follows:
         t+1    Bi j + ∑Nj=1 Ai j pl t+αj
       pl i  =                                                                                               (38)
           ∑Nj=1 Ai j
where pl t+αj    is an “intermediate” pressure, which can be evaluated using the following linear approximation:
       pl t+αj  = pl tj + α ( pl tj −pl t−1j  )                                                                        (39)

with α being a corrected coefficient, whose value should be in a range of 0 – 1. For α = 0, the proposed formulation
(38) for the pore-pressure update returns to the fully explicit form (37), whereas for α = 1, it replicates the fully
implicit form (35), which is unconditionally stable [62]. To avoid these two limiting cases, the value of pl t+αj   needs
to be evaluated and the proposed formulation (39) represents the key concept of the three-point integration (TPI)
scheme, where the value of pl t+αj    at time (t + α) is estimated from the previously known pore-pressures at times
(t −1) and t. The accuracy of the proposed TPI algorithm depends on the selection of α, whose optimal value also
depends on the timestep size adopted in the simulation. Our numerical investigation suggests that α = 0.5 could
provide reasonably accurate and stable solutions for the pore-water pressure, and this value of α is adopted in all
applications in this study.
  Compared to the fully explicit time integration for the pore-fluid pressure equation reported in [35] or [36], the
proposed TPI scheme removes the dependence of the pore-fluid pressure equation from the fluid bulk modulus, thus
offering a more computationally efficient approach with a larger timestep size for the numerical solution. However,
because the value of pl t+αj    is not directly evaluated at time (t + α), the proposed TPI approach only approximates

                                                          8

### Page 9

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

the fully implicit solution, and hence it is not unconditionally stable and its stability is still constrained by a specific
condition. In this study, the following criterion for the timestep is adopted:

    ∆t ≤min (∆ts, R∆tl)                                                                                 (40)

where ∆ts is the mechanical timestep for the solid phase; ∆tl is the critical timestep for the fluid phase defined in
the standard explicit SPH formulation, and R is the amplifier coefficient offered by the proposed TPI scheme, and
its magnitude is proportional to permeability for the same particle resolution. The larger permeability is, the higher
value of R can be adopted.
   For the solid phase, the timestep is restricted by:
                   hsml
     ∆ts ≤CsC FL                                                                                           (41)
                     csp
where CsC FL is a constant, which is taken to be 0.1 throughout this paper; csp = √Es/ρs is the speed of sound in
the solid phase with Es being Young’s modulus of the solid material; and hsml is the smoothing length.
  On the other hand, for the fluid phase in saturated soils, the timestep is given by [36]:
                 nγlh2sml      ∆tl ≤ClC FL                                                                                           (42)
                   Klksat
Unlike other criteria reported in the literature [1,39], the critical timestep is designed to fulfil the CFL conditions for
both the solid and fluid phases in this study. The hydraulic time step is inversely proportional to the production of
fluid bulk modulus (Kl) and saturated permeability of soil (ksat). As a result, a larger critical hydraulic timestep size
can be adopted in applications with small permeabilities. However, the critical timestep required for the solid phase
is restricted by the CFL condition (41), which usually results in a relatively small timestep. Thus, the mechanical
time step will serve as the cap value to ensure the stability of the entire integration process. In this scenario, the
fully explicit time integration scheme is still recommended for applications with very small permeabilities. On the
other hand, for highly-permeable soils, the critical timestep will be dominated by the hydraulic one, which is always
insignificantly small. In this scenario, the proposed method can overcome the timestep restriction by the fluid phase,
thus enabling a larger timestep size to be used in the simulation and serving as an alternative time integration scheme
to save computational costs.
   Fig. 1 shows the SPH computational procedure for solving coupled flow-deformation problems using the
proposed TPI algorithms. Compared to the fully explicit time integration scheme, we only modify how the porewater pressure is calculated using the newly proposed formulation. All other variables are still updated following
the standard LF integration algorithm. The advantage of the proposed time integration is that it partially eliminates
the CFL constraint for the fluid phase, enabling a larger time step to be used for applications involving relatively
high hydraulic permeabilities. Verification examples will be demonstrated in Sections 4.1 and 4.2.

3.5. Stabilised procedure

3.5.1. Global viscosity damping
   In the current SPH framework for fully coupled flow-deformation problems, the motion of particles is governed
by their fully dynamic momentum equation,  i.e., Eq. (6). As a result, SPH particles may be subjected to free
vibration due to inertial force or sudden external loads. Although the artificial viscosity is often incorporated
in SPH simulations to smear out the sock,  i.e., Eq. (26), thus acting as viscous damping in the momentum
equation, it is insufficient to mitigate large fluctuations caused by sudden applied external loads in non-dissipative
materials (or elastic materials). To remove this oscillation in non-dissipative materials to obtain smooth and accurate
stress/pressure fields, the widely used stabilised procedure, namely the global viscous damping [14,63], is applied
in this study. This global damping force is related to the particle velocity but acts in the opposite direction to the
particle itself and takes the following forms [14,63]:

     Fd = −cd · vs                                                                                         (43)

where cd is the damping coefficient, determined from solid properties following the approach proposed by Bui et al.
(2013) [63] as follows:
       √
      cd = ηd  Es/(ρsh2sml)                                                                                 (44)

                                                          9

### Page 10

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

                              Fig. 1. SPH computational procedure for fully coupled flow-deformation analysis.

where ηd is a non-dimensional damping coefficient, of which the value is range from 0.02 to 0.1 as recommended
by Bui et al. (2013) [63]. After adding the global viscous damping force, the final momentum equation is given as
follows:

                N
               (σ i + σ j    )    (dvs )
        = ∑ Vj      + Ci j  ∇iWi j + Fd + b                                                   (45)
        dt      i    j=1         ρti

It is noted that the global viscosity damping force is only applied to non-dissipative or elastic materials. Additional
stabilisation methods are required for elastoplastic materials undergoing large deformation, and these will be
discussed in the following sections.

3.5.2. Stabilisation of pore-water pressure
   Non-physical spatial oscillation in the fluid pressure field is often reported when solving the fully coupled flowdeformation governing equations. This well-known instability issue is commonly found in continuum methods,
including FEM and other mesh-based methods, and is mainly attributed to the  stiff response of the material,
i.e., incompressible or nearly incompressible fluid, causing pore-water pressure fluctuation [42,46]. In the proposed
SPH framework, this pressure noise issue is only found in the coupled flow-deformation analysis of low-permeable
soils, where the fluid is treated as an incompressible or nearly incompressible fluid. To overcome this issue, the
moving least square (MLS) stress regulations technique proposed in [14] can be used to smooth out the noise in
the pore water pressure field. In this study, a simpler and straightforward approach that makes use of the Shepard
regularisation technique is adopted:
      ∑Nj=1 VjWi j plj
       pil =                                                                                                  (46)
       ∑Nj=1 VjWi j

Eq. (46) is applied to each particle after every m computational cycle, which may vary from different applications [14,39]. In this study m = 20∼40 is adopted, and it is only applied to coupled flow-deformation problems
involving low permeable materials undergoing large deformation, i.e., demonstration cases in Section 4.5.

                                                          10

### Page 11

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

3.5.3. Negative pore water pressure stabilisation
  The newly proposed integration scheme captures well the pore-water pressure evolution in the fully saturated
soils undergoing non-volumetric deformation (i.e., zero dilatancies) or plastic contraction. However,  it becomes
challenging when dealing with dilative soils, where the negative excess pore-water pressure develops due to plastic
dilations. This is because Eq. (38) can overestimate the increased negative excess pore-water pressure when the
soil is subjected to shearing dilation, a specific response of porous granular materials. This overestimated negative
excess pore pressure could further lead to tensile stress in fully saturated soils, which facilitates the well-known
tensile instability problems in SPH. To tackle this issue, a negative pore-water pressure cut-off could be applied by
setting the pore-water pressure to zero once the negative pore-water pressure takes place. The disadvantage of this
approach is that the proposed computational model is no longer capable of capturing the development of negative
excess pore-water pressure and thus fails to capture the essential physics of saturated porous granular materials.
Alternatively, another set of formulations can be used to specially treat the negative excess pore pressure associated
with plastic dilation and is given as follow:
       ⎧ Bi j + ∑Nj=1 Ai j pl t+αj
                                                            ptl > 0         t+1         ⎪⎪⎪⎪⎨   ∑Nj=1 Ai j
       pl i  =                     t+α                                                                        (47)
                 Bi j + ∑Nj=1 Ai j pl j  + βpt+αli  /∆t
                  + β/∆t                                     ⎪⎪⎪⎪⎩    ∑Nj=1 Ai j                      ptl < 0
where β is the stabilisation coefficient governing the increasing rate of the negative pore-water pressure associated
with plastic volumetric dilation, and its value can be calibrated from the standard triaxial tests, where the negative
excess pore-water pressure caused by shear-induced dilation can be measured and compared with the numerical
solutions. In this study, β = 0.04 is adopted in all simulation. Eq. (47) slows down the increase rate in the negative
pore-water pressure as the soil undergoes plastic dilation, thus providing sufficient time for SPH particles to respond
to the development of negative excess pore-water pressure and achieving stabilised solutions. It is noted that Eq. (47)
should only be adopted when plastic deformation is considered in the soil.

4. Verifications and applications

4.1. Verification through 1D Terzaghi’s consolidation problem

  The proposed integration scheme is first verified against the 1D Terzaghi’s consolidation problem by comparing
the predicted results with the theoretical solutions and those of the fully explicit LF algorithm previously reported
by the authors [37]. Thereafter, the simulation is repeated by increasing the time increment to demonstrate the
performance of the proposed time integration scheme.
   In this test, a fully saturated soil column, previously reported in [37] as shown in Fig. 2(a), is modelled by
1000 particles with an initial particle spacing of 0.01 m. The material is considered isotropic linear elastic with the
following properties: Young’s modulus of solid E = 20 MPa, Poison’s ratio v = 0.33, void fraction n = 0.4, fluid
bulk modulus Kl = 1 GPa and density ρs = 2000 kg/m3. The water density ρl = 1000 kg/m3, and the saturated
permeability ksat = 2 × 10−4 m/s, which remains unchanged in the simulation. The soil column is initialised with
zero pore-water pressure and zero effective stress, and the gravity is also disregarded in this case. Then, a ramp load
with a magnitude of 10 kPa is applied to the soil column within tL = 0.01 s (see Fig. 2(b)). During this loading
stage, all boundaries are kept impervious so that the excess pore water pressure can build up. After that, a zero pore
pressure is assigned to the soil column surface to trigger the pore-pressure dissipation process. No pore-pressure
regularisation technique is applied in this case.
  The suitability of the global damping stabilisation technique is first verified. Fig. 2(c) shows the evolution of the
excess pore-water pressure during the loading stage. It can be seen that the model overly predicts the excess porewater pressure when the global damping force is not considered. However, after being adopted in the simulation,
the global damping technique (ηd = 0.02) helped achieve the desirable excess pore-water pressure, equal to the
surcharge loading on the upper surface.
  The proposed integration scheme is then verified by comparing the consolidation results with those obtained by
the fully explicit integration method reported in [37], as shown in Fig. 3. The timestep is set to ∆t = 2.88×10−7 s,
which is the same with [37] defined from the condition (42). It is seen that both integration schemes yield the same

                                                          11

### Page 12

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

Fig. 2. SPH simulation of 1D consolidation (a) Geometry and boundary conditions; (b) the surcharge loading curve; (c) excess pore-water
pressure built-up.

Fig. 3. SPH simulation of 1D consolidation with ∆t = 2.88 × 10−7 s: (a) The evolution of the excess pore-water pressure for different time
intervals; (b) The evolution of the surface settlement.

results, which agree well with the analytical solutions for both the excess pore-pressure and deformation, as shown
in Fig. 3.
  The 1D consolidation problem is then re-analysed by increasing the timestep size to demonstrate the capability
of the proposed TPI time integration technique in saving computational costs. The timestep size is first increased
by R = 17 times to ∆t = 5 × 10−6 s, and all other conditions are kept the same. It is worth noting that the fully
explicit time integration scheme [37] could not handle the problem with such a significant timestep size since it
violates the CFL condition (42) for solving the flow phase. Three simulations using Eqs. (37) and (38) with different
values of α (i.e., α = 0.0, 0.5 and 0.7) are conducted for the dissipation stage, and the predicted results are shown
in Fig. 4(a). The solution predicted by Eq. (37), corresponding to coefficient α = 0, introduced noticeable errors at
the later stage of the consolidation process, which indicates that the assumption of pl t+1j  ≈pltj introduced errors to
the numerical solutions when the timestep size increased by 17 times. On the contrary, the proposed TPI scheme
Eq. (38) produces a well-matched result with the analytical solutions for both α = 0.5 and 0.7. In addition to the
excess pore-water pressure, the effective stress is also in good agreement with the theoretical solution, as shown in
Fig. 5.
  An extreme case is also considered by increasing the time step size by R = 35 times to ∆t = 1 × 10−5 s
(i.e., compared to the fully explicit solution), which is close to the capped timestep size defined by the CFL condition

                                                          12

### Page 13

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

Fig. 4. The SPH simulation with the proposed time integration scheme of the evolution of the excess pore-water pressure for different time
intervals: (a) ∆t = 5 × 10−6 s; (b) ∆t = 1 × 10−5 s.

(41) for the solid phase. The results of this simulation with different values of α are reported in Fig. 4(b). Higher
errors can be noticed in the result predicted by Eq. (37), which is expected since the assumption of pl t+1j  ≈pltj is
less acceptable in such large timestep size. On the other hand, the proposed formulation (38) with α = 0.5 produces
a comparable result with some minor errors, and these errors can be removed by further increasing the value of
α to 0.7. The result indicates that the proposed TPI can handle a large timestep size that is close to the capped
timestep size defined by the CFL condition (41) for the solid phase in the fully coupled flow-deformation analysis.
As we continue to increase the timestep size, the accuracy of the TPI scheme will further reduce, and the numerical
solution becomes unstable for α = 0 (i.e., R > 250) and for a larger α value (e.g., R = 98 and α > 0.75). However,
because the maximum timestep size in the current SPH application is capped by the timestep size defined by the
CFL condition (41) for the solid phase, the adopted timestep must not violate this condition. The above results
suggest that the proposed TPI integration technique offers an excellent way to achieve stable solutions and reduce
the computational cost compared to the fully explicit time integration method (i.e., at least an order of magnitude
faster for high permeability applications and even much higher for applications with larger permeabilities). The
computational efficiency of the proposed TPI algorithm could be much higher than those reported in this paper if
one adopts a higher CFL coefficient (CC FL), which is 0.1 in our work compared to 0.5 adopted in other works [38].
Given that the current paper adopts the small-strain formulation, a small CFL coefficient is recommended to ensure
the objectivity of stress increments when dealing with large deformation problems. With such a small CC FL, the
proposed TPI scheme can be confidentially used with α = 0.5 −0.7 as demonstrated above, although α = 0.5 is
recommended for applications involving fast loading rate. In the rest of applications presented in this paper, the
proposed TPI scheme with α = 0.5 is adopted to demonstrate the effectiveness and stability of the proposed TPI
scheme.

                                                          13

### Page 14

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

                                       Fig. 5. The evolution of the effective stress in the soil column.

Fig. 6. SPH model of the 1D harmonic consolidation problem. (a) The geometry condition; (b) the diagram of the harmonic loading function.

4.2. Verifications through 1D harmonic consolidation problem

   In this case, a more challenging coupled flow-deformation problem, namely 1D harmonic consolidation, is
considered. The challenge of this example lies in how the proposed model predicts the excess pore-water pressure
in the soil against complex dynamic loading and drained conditions. This interesting test was first studied in [64]
and later in [46,65], to name a few, where the analytical solution based on the (u−w−pl) formulation are available.
Numerical studies have also been conducted based on either (u−w−pl) formulation [66] or (u−w) version [48,67],
and these existing results will be used as reference solutions.
  The geometry of the problem and the period loading function is given in Fig. 6(a). The soil column is initialised
with a zero effective stress and a zero pore-water pressure. The zero value of pore-water pressure on the top surface
is kept unchanged during the computation to simulate the fully drained condition. The soil sample is modelled using
2000 particles with an initial space distance of 0.04 m. For a comparison purpose, all the material properties are set

                                                          14

### Page 15

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

                           Fig. 7. The evolution of excess pore water pressure in the harmonic consolidation test.

Fig. 8. The settlement profile along the soil column at different time intervals: (a) t = 0.135 s; (b) t = 0.155 s.  (For interpretation of the
references to colour in this figure legend, the reader is referred to the web version of this article.)

as the same as the early study in [65] as follows: Young’s modulus E = 30 MPa, Poison’s ratio v = 0.2, porosity
n = 0.33, fluid bulk modulus Kl = 1 GPa, and density ρs = 2000 kg/m3. The water density ρl = 1000 kg/m3,
and the saturated permeability ksat = 1 × 10−2 m/s, which is kept constant for the entire computation. The soil is
treated as an elastic homogenous material, and gravity is neglected. The global damping coefficient ηd = 0.02 is
considered. The simulation is conducted with a time step size of ∆t = 4 × 10−7 s and the stabilisation coefficient
α = 0.5. It is worth noting that the timestep adopted in this case is about R ≈5 times larger than that given by
the fully explicit integration algorithm defined in Eq. (42) for the flow phase. It is also noted that no pore-pressure
regularisation technique is applied in this case.
   Fig. 7 shows the predicted evolution of excess pore-water pressure at various depths in the soil column. It is
seen that the result obtained using the proposed SPH method agrees reasonably well with the FEM and other
reference solutions [68]. For example, a sinusoidal shape curve of the excess pore-water pressure corresponding to
the harmonic loading is observed, in which different peak values associated with the various depth are also captured.
The peak excess pore-water pressure at each location gradually decreased due to the dissipation on the upper surface.
It is also interesting to find some negative excess pore-water pressure in the vicinity of the upper surface (i.e., mostly
with z = 0.4 m and 1.0 m). This negative excess pressure is computed because the gravity acceleration and the initial
condition from the geostatic loading were neglected. At the same time, it also can be attributed to the recovery of
the elastic deformation near the surface of the soil column, i.e., the relief of compression can cause the expansion
of the pore, which subsequently leads to the absorption of the water content, causing negative excess-pore water
pressure [66]. The marginal difference among results presented in Fig. 7 is mainly due to the difference in the time
integration scheme and formulation used to achieve numerical solutions of the coupled problems.
   Besides the prediction of excess pore-water pressure, the settlement along the soil column is also well captured
by the model, as shown in Fig. 8. In two different instances, i.e., t = 0.135 s and 0.155 s, the predicted deformations

                                                          15

### Page 16

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

    Fig. 9. The diagram of the 2D flexible strip footing problem. (a) Geometry and boundary conditions (b) the ramp loading process.

by the proposed coupled SPH framework agree well with the reference solutions [65,67]. For example, the present
framework yields close results to the ones by FEM [68] and Navas et al. [67], which are based on the (u −pl) and
(u −w) formulations, respectively. This is because the current application is classified as a low-frequency dynamic
consolidation problem [46], where the dynamic term (i.e., the relative acceleration term in Eq. (6)) can be neglected;
therefore, both (u −pl) and (u −w) formulations share similar results [67]. Some noticeable differences lie in the
maximum settlement, which may be attributed to the volumetric locking effect associated with the incompressible
fluid and grain, different coupling formulations or large strain deformation formulation [67]. For example, the
analytical solution in Fig. 8 given by De Boer and his co-workers [65] was obtained by using the (u −w −pl)
formulation, whereas the present solution is obtained by using the (u−pl) formulation, which is also similar to the
(u −w) formulation. To mitigate this error in the maximum surface displacement, the (u −w −pl) formulation or
other stabilisation methodologies, i.e., large strain concept to address the volumetric locking (i.e., FBar −u −w
formulation in the figure) [67], could be considered, which is out of the scope of this study. Nevertheless, our
proposed method effectively captures the evolution of excess pore-water pressure and deformation in this challenging
harmonic consolidation problem, which are the first ever achieved solutions by SPH to our best knowledge.

4.3. 2D flexible strip loading

  A flexible strip footing problem on the fully saturated soil layer is considered in this section. The geometry of
this problem is given in Fig. 9. The soil layer is 8a in-depth and 16a in width and is large enough to eliminate
the boundary effect [69]. The width of the strip footing is a, and a = 1.25 m is used in this simulation. The left
and the right boundaries are free-slip and can be modelled by ghost particles [11]. The bottom boundary is fixed
in horizontal and vertical directions, which can also be modelled by the solid boundary particles [11]. Besides,
all the boundaries, including the bottom of the strip footing, are impervious within the ramp-load stage (i.e., when
t ≤tL in Fig. 9(b)). After completing the ramp-loading process, a fully permeable condition is enforced to the upper
open surface of the soil layer by imposing a zero pore-water pressure condition to trigger the pore-water pressure
dissipation process, whereas other boundaries are kept as impermeable. The following material properties are used:
Young’s modulus E = 20 MPa, Poison’s ratio v = 0.33, porosity n = 0.40, fluid bulk modulus Kl = 1 GPa, and
density ρs = 2650 kg/m3. The water density ρl = 1000 kg/m3 and the saturated permeability ksat = 1 × 10−3 m/s.
The global damping coefficient ηd is 0.04. A total of 20,000 particles with an initial particle spacing of dx = 0.1
m are used, and due to the high permeability, the time step size is dominated by the flow phase. This simulation
is conducted using the proposed TPI algorithm (α = 0.5) with a constant timestep size ∆t = 1 × 10−4 s, which is
nearly R = 15 times larger than the explicit CFL time step size (condition (42)) for the flow phase. Additionally,
no pore-pressure regularisation technique is required and the gravity acceleration is ignored in this case.
   Fig. 10 shows the contour plot of the excess pore-water pressure development and dissipation in the soil layer
predicted by SPH and FEM. The FEM solutions were obtained using the commercial ABAQUS software package.
The same boundary conditions and soil parameters given in Fig. 9 were adopted in the FEM simulation, with
numerical solutions obtained using the standard/explicit solver provided by ABAQUS. It can be observed that the

                                                          16

### Page 17

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

                            Fig. 10. The evolution of excess pore water pressure in the 2D flexible strip footing.

excess pore-water pressure builds up under the footing within the loading compression stage and dissipates after the
drained condition is applied. The proposed SPH model obtains a very stable and smooth pore pressure distribution
thanks to the adopted stabilisation technique (i.e., the global damping force), which dissipates the unwanted dynamic
energy of solid particles, thus enabling the current framework to be free from the pressure fluctuation reported in
the earliest coupled flow-deformation SPH framework [34]. The evolution of excess pore water pressure at Points
A and B are given in Fig. 11, where the results match well with the reference FEM solutions, indicating that our
model could capture well both the excess pore water pressure built-up and dissipation. For example, within the
ramp-load stage (t ≤tL), excess pore-water pressure is generated due to the volumetric compaction and reaches
its peak value when t = tL. The peak value of excess pore water pressure at Point B is less than that at Point A

                                                          17

### Page 18

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

                            Fig. 11. The evolution of excess pore-water pressure in the 2D flexible strip footing..

Fig. 12. SPH prediction on the deformation in the 2D strip footing test: (a) settlement at Points A and B; (b) horizontal displacement versus
depth along the vertical section passing Point B under the right edge of the footing.

because Point B is located deeper and further from the strip centre. After completing the ramp load, the excess
pore water pressure starts to dissipate and entirely dissipates at t = 100 s, during which the predicted excess pore
water pressure matches well with the reference solutions (see Fig. 11). The settlement at Points A and B are shown
in Fig. 12(a), where the predicted deformation by the proposed SPH method again agrees well with the reference
FEM solution. More convincingly, the calculated horizontal displacement along the section under the right edge of
footing (Marked by the red ‘–’ line in Fig. 8(a)) is also well matched with the FEM solution, as shown in Fig. 12(b).
   These excellent agreements against FEM solutions suggest that the proposed SPH framework utilising the TPI
algorithm could capture well the coupling behaviour of saturated soils and is ready for more complex coupled
hydromechanical analysis involved with large deformation, which will be presented in the next section.

4.4. Granular collapse of saturated soils

   In this example, the simulation of granular collapse on saturated soil columns is considered to demonstrate
the capability of the proposed method for fully coupled analysis involving large deformation in geotechnical
applications. The same geometry as the earliest work on SPH modelling of granular collapse by Bui et al. [11]
is considered and shown in Fig. 13(a). However, different from the work by Bui et al. [11], in this study, the soil
is considered initially fully saturated with a pre-described water table on the upper surface (see Fig. 13(b)). The
importance of this example lies in how the proposed model predicts the excess pore water pressure that varies
against the dilatancy angle and the deformation pattern of the shear band. To replicate these phenomena, three
dilatancy angles of ψ peak = 0◦, 2.5◦and −5◦, corresponding to non-dilative soils, purely dilative soils, and purely
contractive soils, are considered.
  The simulations are performed using 5000 particles with an initial spacing distance of 0.04 m. Three walls are
modelled by either the free-slip boundary (the left and the right walls) or the solid boundary (the bottom) [11], and

                                                          18

### Page 19

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

                            Fig. 13. Schematic of the geometry for the granular collapse of fully saturated soil.

            Table 1
              Material properties of the granular column collapse of saturated soil.

               Material properties                                         Soil types

              Young’s modulus (Es), MPa                         20                 20                 20
               Solid density, (ρs), kg/m3                           2650               2650               2650
               Poison’s ratio, v                                        0.33                 0.33                 0.33
                Porosity, (n)                                            0.35                 0.35                 0.35
              Water bulk modulus, (Kl), GPa                      1                  1                  1
              Water density, (ρl), kg/m3                           1000               1000               1000
               Saturated permeability, (ksat), m/s                      0.0002              0.0002              0.0002
            Kozeny–Carman coefficient, (Ck)                     2                  2                  2
             Peak or residual friction angle, (φp, φr), ◦             25                 25                 25
             Peak cohesion, (cp), kPa                            5                  5                     7.5
               Residual cohesion, (cr), kPa                         1                  1                  1
               Softening constant, (η)                              5                  5                  5
                Dilation angle, (ψ0), ◦                              0                     2.5             −5
                Dilation softening constant, (s f )                   N/A                  0.2                   0.2
                 Stabilisation coefficient, (α)                               0.5                   0.5                   0.5

all the walls are impermeable, of which the condition can be modelled following the work recently proposed by
the authors [36]. As for the hydraulic condition on the free surface, the proposed free-seepage surface boundary
treatment in [36] and the ponding condition of pl ≤0 are also adopted in this study. The soil behaviour is modelled
by the elasto-plastic Drucker–Prager (DP) softening model for the demonstration purpose, though more advanced
constitutive models can be readily incorporated in SPH [3], and the material properties are given in Table 1. Due to
the large permeability of the soil, the proposed semi-implicit integration scheme is adopted in this example. After
the initial in-situ total and effective stress conditions are obtained by applying gravitational load to the soil column
(see Fig. 13(c) and (d)), the right wall is then suddenly removed to trigger the collapse. The simulation is conducted
with a time increment as 2 × 10−5 s, which is nearly 5 times larger than the fully explicit CFL time step given in
condition (42).
  The first simulation is carried out with a zero dilatancy angle. The shear band development and the evolution
of excess pore water pressure induced by plastic volumetric deformation are shown in Fig. 14. After removing the
right wall, the reduction of lateral pressure resulted in a circular shape shear band that developed and propagated
backward the back scarp, forming multiple failure surfaces. A retrogressive failure was then observed, with the

                                                          19

### Page 20

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

                             Fig. 14. Granular collapse of fully saturated soil with dilatancy angle ψ peak = 0◦.

soil column undergoing flow-sliding behaviour. No excess pore water pressure is generated in the shear band zone,
which can be attributed to the fact that a zero dilatancy angle was adopted in this simulation. The proposed model
accurately predicted this response of excess pore-water pressure for no volumetric plastic strain developed in the
model. Despite this fact, the failure pattern of the saturated soil column in this fully coupled analysis is different
from that in the dry soil by Bui et al. [11], which can be attributed to pore-water pressure in the current simulation.
  The second simulation is performed with a positive dilatancy angle of 2.5◦, i.e., dilatative soils. Fig. 15 shows
the equivalent accumulated plastic strain profiles and the evolution of excess pore-water pressure caused by plastic
volumetric dilation of the simulated soil during the post-failure process. The proposed method captures the intended
negative excess pore-water pressure developing inside the shear band caused by volumetric plastic dilation. For
example, the negative excess pore-water pressure is first observed along the shear band and continually increases as
the shear band further develops (i.e., from 0.3 s to 0.6 s). However, at the final stage, when the collapse stopped at
t = 1.2 s, the excess pore-water pressure inside the shear band undergoes some dissipation, which can be attributed
to the increase of porosity caused by large shearing deformation and thus increasing the permeability, facilitating
the excess pore-water pressure dissipation process. It is noted that even though the same parameters with the first
case (except the dilatancy angle) are used, a different failure pattern is observed in this case. This can be attributed
to the development of negative excess pore-water pressure, causing an increase in the mean effective stress, and
thus affecting the final deformation pattern. As the positive dilatancy angle is further increased, for example, to 5◦,
no collapse was observed in the simulation, which can be again attributed to the development of negative excess
pore-water pressure.
  The effectiveness of the proposed negative pore-water pressure stabilised technique is demonstrated in Fig. 16,
in which a comparison is made between the stabilised and non-stabilised cases. After releasing the gate, water flows
out of the soil column due to the relatively high permeability adopted in this example. This forms a well-defined
curvature phreatic line, above which the pore-water pressure is zero because unsaturated seepage was not considered
in the current water-saturated SPH formulation. The soil above the phreatic line subsequently underwent volumetric
dilation, and thus negative pore-water pressure (i.e., equal to excess pore-water pressure in this case) was predicted.
The development of negative pore-water pressure is over-predicted in the SPH model without adopting the stabilised
procedure, resulting in non-physical behaviours of the soil, as shown in Fig. 16(b). On the contrary, the proposed

                                                          20

### Page 21

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

                            Fig. 15. Granular collapse of fully saturated soil with dilatancy angle ψ peak = 2.5◦.

                                             Fig. 16. Pore fluid pressure field in the dilative soil.

stabilisation technique helps maintain the change rate of the negative excess pore-water pressure and thus stabilises
the SPH solution, where the collapse of the soil column is still processed.

                                                          21

### Page 22

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

                              Fig. 17. Granular collapse of fully saturated soil with dilatancy angle ψ p = −5◦.

   In the last example, a negative dilatancy angle −5◦standing for the contractive soils is considered, and the
simulated results are presented in Fig. 17. In contrast to the dilative soil, the positive excess pore-water pressure
caused by volumetric plastic contraction is now observed within the shear band, as shown at the beginning at
t = 0.2 s. The development of positive excess pore-water pressure reduces the effective stress to nearly zero
(i.e., liquefaction), which subsequently triggers a rapid flow of the sliding band at  t =  0.5  s. As the soil
undergoes large shearing deformation associated with high volumetric compaction, more excess pore water pressure
is generated, weakening the soil, and eventually leading to complete liquefaction (i.e., the shear strength could drop
to zero). As a result, a very rapid liquid-like sliding failure behaviour characterised by a longer run-out distance is
observed, as shown in Fig. 17 at t = 1.6 s. As the liquefied sliding mass flows away, the back scarp soils lost their
lateral support and continued to collapse, undergoing liquefaction, and replicating the fluid-like behaviour until the
complete failure stopped at around t = 3.0 s.
   Overall, the above simulations demonstrated the capability of the proposed computational approach in handling
the complicated coupling mechanisms associated with large soil deformation and failure relevant to geotechnical
engineering applications.

4.5. Coupled modelling of retrogressive failure of sensitive clay

   In this section, the capability of the computational framework in predicting coupled behaviour of geomaterials
undergoing large deformation and post-failure is further demonstrated through the modelling of retrogressive failure
of slope in sensitive clays. This large-scale progressive failure of quick clays frequently occurs worldwide, especially

                                                          22

### Page 23

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

                               Fig. 18. Geometry and boundary condition of a slope made of sensitive clays.

in eastern Canada and Scandinavia [70], where sensitive clays are commonly found. The collapse of this clay slope
is often characterised by its rapid motion, long travel distance, and the strong strain-softening behaviour of the
soil [70]. Field observations, conceptional modelling, and analysis have been frequently reported in the past several
decades [70–73]. Among these studies, retrogressive landslides are often classified into three main types: flow,
translational and spreading failures [70,71]. On the other hand, modelling of retrogressive failure has also gained
much interest, and several advanced numerical methods, i.e., SPH, Material Point Method (MPM), and Smoothed
Particle Finite Element Method (PFEM), to name a few, have been applied to analyse these challenging problems
with certain successes recently [3,74–79]. In those attempts, the initially stiff state of the clay was always assumed
to turn into the semi-liquid or liquid state quickly, and this “assumed” transition state was achieved by imposing
the undrained condition using a zero-friction angle and a large Poison’s ratio (i.e., v = 0.495). Thereafter, a strainsoftening model was adopted to describe the rapid motion and long run-out distance [3,74–79]. The key limitation of
these works is that the development of excess pore-water pressure and its influence on retrogressive failure was not
considered, which might not be reasonable for sensitive clays [45]. More recently, Jin & Yin (2022) [45] investigated
the effect of excess pore water pressure on the retrogressive failure mechanism. However, the excess pore water
pressure in their approach was computed from the Effective Stress Analysis Method instead of by solving the fully
coupled pore-water pressure equation; thus, improvement is still needed to better understand the pore-water pressure
generation and dissipation processes during the post-failure process. This study applies the proposed coupled flowdeformation SPH framework to investigate this problem further. To our best knowledge, this will be the first attempt
to solve this retrogressive failure of clays using the fully coupled hydromechanical approach, in which the evolution
of excess pore-water pressure and its dissipation is fully described and kept track during the entire failure process.
  The geometry for the representative cross-section of a slope made of sensitive clays is outlined in Fig. 18.
The slope is 20 m in height and 180 m in length, with the slope angle being 27◦. A pre-described water table
is introduced to the ground surface to replicate the fully saturated condition of the clay, as shown in Fig. 18. The
material properties of the saturated sensitive clay are given as follows: Young’s modulus E = 12.5 MPa; solid-phase
density ρs = 2650 kg/m3; Poison’s ratio v = 0.33; the initial peak shear strength φ′p = 10◦and cpeak = 55 kPa;
the residual shear strength φres = 5◦and cres = 0.7 kPa, with the softening coefficient η being 5; water density
ρl = 1000 kg/m3; porosity n = 0.4; fluid bulk modulus Kl = 1 × 108 Pa; permeability ksat = 5 × 10−8m/s,
with the coefficient Ck = 2. As reported in the field observations [70], the angle of horsts formed in the field
ranges from θ = 50◦to 68◦, indicating that the effective friction angle of sensitive clays ranges from φ′p = 10◦
to 46◦(i.e., based on the Mohr–Coulomb failure theory θ = 45◦+ φ′p/2). Therefore, in this paper, the effective
friction angle of φ′p = 10◦is selected for the demonstration purpose. On the other hand, the permeability of clay
soil is usually very low (∼10−8 m/s), thus the fully explicit time integration scheme is suitable and chosen in this
case. It is also noted that the shear strength of the sensitive clay might increase among the depth [80]. In this
study, it is simplify assumed to be uniformly distributed across the entire slope. More importantly, different from
all previous studies which imposed the undrained condition by having a zero friction and dilatancy angles [3,74–79],
the drained analysis with extremely low permeability is considered herein, and a negative dilatancy angle ψ = −5◦
with softening coefficient sd being 0.50 is further adopted, thus the influence of excess pore-water pressure on the
failure mechanism can be assessed.
  The studied slope is modelled using 20349 SPH particles, with an initial particle spacing of 0.4 m. The freeslip vertical and fixed-bottom boundaries are modelled respectively by the ghost and virtual particles [11], where
the undrained boundary condition is also enforced following the original approach reported in [36]. Due to the
relatively low permeability in the clay, the time step size will be capped by the solid phase given in condition

                                                          23

### Page 24

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

                    Fig. 19. Stabilised SPH prediction of the retrogressive failure of sensitive clay slope with K0 = 0.5.

(38), where the time step size is 4 × 10−4 s. The simulation is performed in two steps. First, a global water table
is assigned to the slope to obtain the steady-state hydraulic condition, followed by gravitational loading to obtain
the initial in-situ stress conditions. It is reported that the lateral pressure coefficient at rest (K0) highly influences
the successive retrogressive failure of the sensitive clay, but investigations on its influence in sensitive clay is still
limited [79]. Therefore, the simulation is performed with different K0 values to investigate its influence on the types
of retrogressive failure. Based on some field tests, K0 of sensitive clay is ranged from around 0.6 to 3.5 [81]. In
this study, K0 = 0.5 and 1.5 are considered. After the initial stress condition is achieved (which will be given in
the result analysis below), a portion of the slope toe is removed to mimic the erosion induced retrogressive failure,
which is commonly adopted in the literature [45,74,79].
   Fig. 19 shows the progressive failure of the slope predicted by the proposed SPH model with the lateral earth
pressure coefficient of K0 = 0.5. The corresponding pore-water pressure and mean effective stress profiles are given
in Figs. 20 and 21, respectively. The proposed framework successfully captures a flow-sliding type retrogressive
failure without requiring the undrained assumption commonly adopted in the literature, with a stable description
of the pore-water pressure and effective stress in this case. For example, after removing the erodible soil block
from the slope toe, a horizontal shear band develops inward the slope at the bottom, propagating upward and
forming the 1st rotational sliding surface at t = 2.0 s. The moving soil mass is also strongly remoulded and rapidly
flowing out of the crater. This flowing debris removed the lateral support to the remaining slope, leaving an unstable
scarp, where subsequently the 2nd rotational slide occurs in a similar way at t = 7.0 s. At the same time, similar
behaviour of pore water pressure and effective stress is again observed in the sensitive clay, as shown in Figs. 20
and 21, respectively. The same failure process is repeated for subsequent sliding blocks until the volume of debris
materials building up in front of the crater is large enough to provide sufficient lateral support to the remaining
slope, thus forming a final stable back scarp at t = 40 s. A total of 6 rotational slides are observed, with the size
of each sliding mass being similar to each other, which is mainly attributed to the assumed homogeneous material
properties. The final run-out distance reaches 192 m. It is worth noting that the above results can only qualitatively

                                                          24

### Page 25

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

Fig. 20. Stabilised SPH prediction of the pore water pressure induced by contraction in the retrogressive failure of sensitive clay slope with
K0 = 0.5.

predict the shear band formation and evolution process. To adequately capture this process, one needs to consider
the bifurcation condition to initiate the localised failure and suitable constitutive models to account for the length
scale of the problems (i.e., the shear band orientation and thickness). Such considerations are beyond the scope of
the current paper.
   Nevertheless, it is interesting to notice the dissipation of excess pore-water pressure within the flowing debris
(see Fig. 20), which can be attributed to the porosity change in the soil after undergoing large deformation, thus
causing permeability to increase, facilitating the dissipation process of excess pore water pressure. This dissipation
process can represent the consolidation stage associated with an increase in effective stress (see Fig. 21), which
gradually stops the flowing behaviour of the clay soil. It is worth noting that this dissipation/consolidation process
within the clay slope failure could only be achieved by the fully coupled flow-deformation framework, which
outperforms the undrained approaches [70–73]. Overall, the predicted failure mode is well consistent with the
flowing failure from the on-site observation [70], as shown in Fig. 19. On the other hand, the retrogressive failure
of sensitive clay slopes (K0 = 0.5) predicted using the non-stabilised SPH model is shown in Fig. 22. This result
demonstrates the effectiveness of the proposed stabilisation technique to achieve a smooth pore-water pressure field
for the proposed water-saturated SPH formulation achieved in Fig. 20. For non-stabilised solutions, the instability
in the development of pore-water pressure (i.e., pressure noise) is noticeable across the computational domain as
soon as the 1st slide failure occurs, with more severity concentrated on the areas where the soil undergoes large
deformation. The instability in the pore water pressure field becomes more apparent, especially in the area close to
the left boundary, as the retrogressive failure processing (i.e., t = 14.0 s and 27.4 s).

                                                          25

### Page 26

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

Fig. 21. Stabilised SPH modelling the evolution of mean effective stress in the flow retrogressive failure of sensitive clay slope with K0 =
0.5.

Fig. 22. Non-stabilised SPH prediction of the pore water pressure induced by contraction in the retrogressive failure of sensitive clay slope
with K0 = 0.5.

   Figs. 23–25 show the progressive failure of the slope predicted by the proposed SPH model with the lateral earth
pressure coefficient of 1.5. A different failure process, namely spreading failure, is observed in this case. Unlike the
first case, a horizontal shear band first develops and propagates inward the slope after removing the erodible soil
block. This is because a larger value of K0, in this case, is associated with more reduction of the lateral stress in the
back scarp soils when the slope toe is eroded [79]. More loss in the lateral stress to the back scarp then leads to the

                                                          26

### Page 27

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

                Fig. 23. Stabilised SPH modelling the spreading retrogressive failure of sensitive clay slope with K0 = 1.5.

deeply-propagated horizontal shear band that triggers the spreading failure [70]. In this process, the very first curved
failure plane with two competitive shear bands takes place at t = 2 s. This result is consistent with the conclusion
reported by Odenstad (1951) [82], who pointed out that a circular slide could have first triggered the spreading
failure. Competitive shear bands exist at the earlier failure stage due to the more lateral stress reduction in the back
scarp soil [83]. As the first sliding block flows out of the crater, the horizontal shear band at the level of the bottom
continuously propagates deep inside the remaining slope at t = 6.0 s, which then actives the 1st “V-shaped” failure
surface that dislocates the sliding mass into a “∆-shaped” horst and a “∇-shaped” grabens along with the horizontal
shear band, as shown in Fig. 23.
   Again, during the failure process, high excess pore-water pressure is also generated within the shear band due to
the plastic volumetric contraction (see Fig. 24), which strongly softens the shear strength of the materials (i.e., zero
effective stress is observed in Fig. 25), facilitating the rapid movement of the soil mass. The subsidence of the
graben is intensively-remoulded at the bottom associated with intense excess pore-water pressure built-up, leaving
an unstable slope face that can be pushed down the slope by another graben upslope, and forming another horst,
thus the succession of horsts and graben in the scarp is triggered, i.e., at t = 11 s, 17.4 s and 23 s. This failure
process continues along with the horizontal failure surface at the bottom level until a stable back scarp is reached.
The final run-out distance at t = 40 s is up to about 186 m in this case. Moreover, it is noted that the predicted
spreading failure of sensitive clay slope is close to the conceptual modelling results [70], as shown in Fig. 23.
   Fig. 26 shows a qualitative comparison between the proposed SPH model, conceptional model and  field
observations for the formation of horst and graben [70,72]. The predicted results in this study are close to the
reference results. For example, the proposed method captured well the remoulded soil at the base of grabens
squeezing out of the cracks between grabens and horsts [72]. Moreover, the proposed model also captures the wellshape and intact horsts with a sharp wedge pointing upward. More importantly, the predicted angle of the sliding
surface between grabens and horsts is around 45◦+ φ′p/2, which is close to the result given in [72]. Overall, the
above modelling examples demonstrate that the proposed fully coupled SPH framework has a powerful capability in

                                                          27

### Page 28

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

Fig. 24. The evolution of excess pore-water pressure induced by volumetric contraction in the spreading retrogressive failure of sensitive
clay slope with K0 = 1.5 predicted by the stabilised SPH model.

handling complex and large-scale coupled flow-deformation problems involving large deformation and post-failure
processes.

5. Conclusion

   This paper presents an effective and stabilised SPH computational framework for solving fully coupled flowdeformation problems in saturated porous media undergoing large deformations and failures. The newly proposed
time integration scheme enables a larger timestep size for integrating the governing equation of the fluid phase,
thus providing a more computationally efficient tool for field-scale applications. Compared with the existing fully
explicit time integration scheme, the paper demonstrates that the proposed method helps save computational costs
(i.e., potentially up to 5∼15 times in this study) when solving coupled flow-deformation problems, particularly for
saturated porous media with large water bulk modulus or high permeability. Furthermore, the proposed stabilisation
procedures help to obtain a stable solution for the fluid pressure field in saturated porous media when large
deformation and post-failure behaviour are considered. The newly developed SPH framework enables the prediction
of several challenging problems that were not achieved in the past. For example, to the best of the authors’
knowledge, this is the first time the fully coupled analysis of the retrogressive failure of sensitive clay has been
achieved. Compared to the commonly adopted “undrained” analysis, the current SPH model can capture the entire
process of excess pore-water pressure development and dissipation during the post-failure process, thus offering an
excellent way to have further insights into the failure mechanisms of sensitive clays. To this end, it is suggested that
the proposed coupled SPH framework could be considered a useful computational tool to deal with a wide range

                                                          28

### Page 29

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

Fig. 25. Stabilised SPH prediction of the evolution of effective stress in the spreading retrogressive failure of sensitive clay slope with K0 =
1.5.

Fig. 26. SPH modelling the retrogressive flow failure of sensitive clay slope with K0 = 1.5 (Reference result after [72]; Field photos after
Locat et al. [70]).

                                                          29

### Page 30

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

of coupled flow-deformation problems in saturated porous media, particularly those involving large deformation
and post-failure processes. However, additional work is required to adequately describe the localisation and shear
band evolution processes, including bifurcation conditions to initiate localised failure and its associated shear band
orientation and thickness. Such considerations, recently shown in [26–29] for fracturing applications, are in progress
for soils and will be reported in the future.

Declaration of competing interest

  The authors declare that they have no known competing financial interests or personal relationships that could
have appeared to influence the work reported in this paper.

Data availability

  No data was used for the research described in the article.

Acknowledgements

  The authors gratefully acknowledge support from the Australian Research Council via Discovery Projects
DP170103793 (Nguyen, Bui), DP190102779 (Bui & Nguyen) and FT200100884 (Bui). Part of this research
was undertaken with the assistance of resources and services from the National Computational Infrastructure
(NCI), supported by the Australian Government. The support of the China Scholarship Council, China (CSC, No.
201906050025) is also gratefully acknowledged.

References

  [1] H.H. Bui, G.D. Nguyen, A coupled fluid-solid SPH approach to modelling flow through deformable porous media, Int. J. Solids Struct.
     125 (2017) 244–264, http://dx.doi.org/10.1016/j.ijsolstr.2017.06.022.
  [2]  S. Bandara, K. Soga, Coupling of soil deformation and pore fluid flow using material point method, Comput. Geotech. 63 (2015)
     199–214, http://dx.doi.org/10.1016/j.compgeo.2014.09.009.
  [3] H.H. Bui, G.D. Nguyen, Smoothed particle hydrodynamics (SPH) and its applications in geomechanics: From solid fracture to granular
      behaviour and multiphase flows in porous media, Comput. Geotech. 138 (2021) 104315, http://dx.doi.org/10.1016/j.compgeo.2021.
     104315.
  [4] H. Sabetamal, M. Nazem, J.P. Carter, S.W. Sloan, Large deformation dynamic analysis of saturated porous media with applications to
      penetration problems, Comput. Geotech. 55 (2014) 117–131, http://dx.doi.org/10.1016/j.compgeo.2013.08.005.
  [5] L. Monforte, M. Arroyo, J.M. Carbonell, A. Gens, Numerical simulation of undrained insertion problems in geotechnical engineering
      with the Particle Finite Element Method (PFEM), Comput. Geotech. 82 (2017) 144–156, http://dx.doi.org/10.1016/j.compgeo.2016.08.
      013.
  [6]  Y.F. Jin, W.H. Yuan, Z.Y. Yin, Y.M. Cheng, An edge-based strain smoothing particle finite element method for large deformation
     problems in geotechnical engineering, Int. J. Numer. Anal. Methods Geomech. 44 (2020) 923–941, http://dx.doi.org/10.1002/NAG.3016.
  [7] E. Oñate, S.R. Idelsohn, F. Del Pin, R. Aubry, The particle finite element method — an overview, Int. J. Comput. Methods 01 (2004)
     267–307, http://dx.doi.org/10.1142/s0219876204000204.
  [8] W.H. Yuan, J.X. Zhu, K. Liu, W. Zhang, B.B. Dai, Y. Wang, Dynamic analysis of large deformation problems in saturated porous
     media by smoothed particle finite element method, Comput. Methods Appl. Mech. Engrg. 392 (2022) 114724, http://dx.doi.org/10.
      1016/j.cma.2022.114724.
  [9] L.B. Lucy, A numerical approach to the testing of the fission hypothesis, 82 (1977) 1013–1024.
[10] A.R. Gingold, J.J. Monaghan, Smoothed particle hydrodynamics: theory and application to non-spherical stars, 181 (1977) 375–389.
[11] H.H.  Bui, R. Fukagawa, K.  Sako,  S. Ohno, Lagrangian meshfree  particles method (SPH)  for  large  deformation and  failure
      flows of geomaterial using elastic–plastic soil constitutive model,  Int.  J. Numer. Anal. Methods Geomech. 32 (2008) 1537–1570,
      http://dx.doi.org/10.1002/nag.
[12] A.H. Fávero Neto, R.I. Borja, Continuum hydrodynamics of dry granular flows employing multiplicative elastoplasticity, Acta Geotech.
     13 (2018) 1027–1040, http://dx.doi.org/10.1007/s11440-018-0700-3.
[13] C.M. Chalk, M.  Pastor,  J. Peakall, D.J. Borman, P.A. Sleigh, W. Murphy,  Stress-particle smoothed  particle hydrodynamics: An
      application  to  the  failure and  post-failure behaviour of  slopes, Comput. Methods Appl. Mech. Eng. 366 (2020) 113034,  http:
      //dx.doi.org/10.1016/j.cma.2020.113034.
[14] C.T. Nguyen, C.T. Nguyen, H.H. Bui, G.D. Nguyen, R. Fukagawa, A new SPH-based approach to simulation of granular flows using
      viscous damping and stress regularisation, Landslides 14 (2017) 69–81, http://dx.doi.org/10.1007/s10346-016-0681-y.
[15] E. Yang, H.H. Bui, H. De Sterck, G.D. Nguyen, A. Bouazza, A scalable parallel computing SPH framework for predictions of
      geophysical granular flows, Comput. Geotech. 121 (2020) 103474, http://dx.doi.org/10.1016/j.compgeo.2020.103474.
[16] H.H. Bui, R. Fukagawa, K. Sako, J.C. Wells, Slope stability analysis and discontinuous slope failure simulation by elasto-plastic
     smoothed particle hydrodynamics (SPH), Geotechnique 61 (2011) 565–574, http://dx.doi.org/10.1680/geot.9.P.046.

                                                          30

### Page 31

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

[17] X. He, D. Liang, M.D. Bolton, Run-out  of  cut-slope  landslides: Mesh-free  simulations, Geotechnique 68 (2018) 50–63,  http:
      //dx.doi.org/10.1680/jgeot.16.P.221.
[18] H.H.  Bui, R. Fukagawa, An improved SPH method  for  saturated  soils and  its  application  to  investigate  the mechanisms  of
     embankment  failure: Case of  hydrostatic pore-water  pressure,  Int.  J. Numer. Anal. Methods Geomech. 37 (2013) 31–50,  http:
      //dx.doi.org/10.1002/nag.1084.
[19] M. Pastor, T. Blanc, B. Haddad, S. Petrone, M. Sanchez Morles, V. Drempetic, D. Issler, G.B. Crosta, L. Cascini, G. Sorbino, S.
     Cuomo, Application of a SPH depth-integrated model to landslide run-out analysis, Landslides 11 (2014) 793–812, http://dx.doi.org/
     10.1007/s10346-014-0484-y.
[20]  T. Blanc, M. Pastor, A stabilized runge-kutta, taylor smoothed particle hydrodynamics algorithm for large deformation problems
      indynamics, Internat. J. Numer. Methods Engrg. 91 (2012) 1427–1458, http://dx.doi.org/10.1002/nme.4324.
[21]  S. Zhao, H.H. Bui, V. Lemiale, G.D. Nguyen, F. Darve, A generic approach to modelling flexible confined boundary conditions in
    SPH and its application, Int. J. Numer. Anal. Methods Geomech. 43 (2019) 1005–1031, http://dx.doi.org/10.1002/nag.2918.
[22] E. Yang, H.H. Bui, G.D. Nguyen, C.E. Choi, C.W.W. Ng, H. De Sterck, A. Bouazza, Numerical investigation of the mechanism of
      granular flow impact on rigid control structures, Acta Geotech. (2021) http://dx.doi.org/10.1007/s11440-021-01162-4.
[23] B. Sheikh, T. Qiu, A. Ahmadipur, Comparison of SPH boundary approaches in simulating frictional soil–structure interaction, Acta
     Geotech. (2020) 1–20, http://dx.doi.org/10.1007/s11440-020-01063-y.
[24] H.H. Bui, J.K. Kodikara, A. Bouazza, A. Haque, P.G. Ranjith, A novel computational approach for large deformation and post-failure
      analyses of segmental retaining wall systems, Int. J. Numer. Anal. Methods Geomech. 38 (2014) 1321–1340, http://dx.doi.org/10.1002/
      nag.2253.
[25] D.S. Morikawa, M. Asai, Coupling total Lagrangian SPH–EISPH for fluid–structure interaction with large deformed hyperelastic solid
      bodies, Comput. Methods Appl. Mech. Engrg. 381 (2021) 113832, http://dx.doi.org/10.1016/j.cma.2021.113832.
[26] H.T. Tran, Y. Wang, G.D. Nguyen, J. Kodikara, M. Sanchez, H.H. Bui, Modelling 3D desiccation cracking in clayey soils using a
      size-dependent SPH computational approach, Comput. Geotech. 116 (2019) 103209, http://dx.doi.org/10.1016/j.compgeo.2019.103209.
[27] H.T. Tran, N.H.T. Nguyen, G.D. Nguyen, H.H. Bui, Meshfree SPH modelling of shrinkage induced cracking in clayey soils, Lect.
     Notes Civ. Eng. 54 (2020) 889–894, http://dx.doi.org/10.1007/978-981-15-0802-8_142.
[28] Y. Wang, H.T. Tran, G.D. Nguyen, P.G. Ranjith, H.H. Bui, Simulation of mixed-mode fracture using SPH particles with an embedded
      fracture process zone, Int. J. Numer. Anal. Methods Geomech. 44 (2020) 1417–1445, http://dx.doi.org/10.1002/nag.3069.
[29] Y. Wang, H.H. Bui, G.D. Nguyen, P.G. Ranjith, A new SPH-based continuum framework with an embedded fracture process zone for
     modelling rock fracture, Int. J. Solids Struct. 159 (2019) 40–57, http://dx.doi.org/10.1016/j.ijsolstr.2018.09.019.
[30]  S. Gharehdash, L. Shen, Y. Gan, Numerical study on mechanical and hydraulic behaviour of blast-induced fractured rock, Eng. Comput.
     36 (2020) 915–929, http://dx.doi.org/10.1007/s00366-019-00740-1.
[31] H.H. Bui, K. Sako, R. Fukagawa, Numerical simulation of soil–water interaction using smoothed particle hydrodynamics (SPH) method,
        J. Terramech. 44 (2007) 339–346, http://dx.doi.org/10.1016/j.jterra.2007.10.003.
[32] H.H. Bui, Lagrangian Mesh-Free Particle Method (SPH) for Large Deformation and Post-Failure of Geomaterial using Elasto-Plastic
      Constitutive Models (Doctoral dissertation), Ritsumeikan Univ, 2006, http://r-cube.ritsumei.ac.jp/repo/repository/rcube/9152/k_466_e.
     htm.
[33] K. Maeda, H. Sakai, M. Sakai, Development of seepage failure analysis method of ground with smoothed particle hydrodynamics,
       Struct. Eng. Earthq. Eng. 23 (2006) 307s–319s, http://dx.doi.org/10.2208/JSCESEEE.23.307S.
[34] H.H. Bui, R. Fukagawa, A first attempt to solve soil water coupled problems by SPH, Jpn. Terramech. 29 (2008) 30–38.
[35] M. Pastor, B. Haddad, G. Sorbino, S. Cuomo, V. Drempetic, A depth-integrated, coupled SPH model for flow-like landslides and
      related phenomena, Int. J. Numer. Anal. Methods Geomech. 33 (2009) 143–172, http://dx.doi.org/10.1002/NAG.705.
[36] Y. Lian, H.H. Bui, G.D. Nguyen, H.T. Tran, A. Haque, A general SPH framework for transient seepage flows through unsaturated
     porous media considering anisotropic features of diffusion, Comput. Methods Appl. Mech. Engrg. 387 (2021) 114169, http://dx.doi.
      org/10.1016/j.cma.2021.114169.
[37] Y. Lian, H.H. Bui, G.D. Nguyen, S. Zhao, A. Haque, A computationally efficient SPH framework for unsaturated soils and its application
      to predicting the entire rainfall-induced slope failure process, Géotechnique (2022) 1–60, http://dx.doi.org/10.1680/jgeot.21.00349.
[38] D.S. Morikawa, M. Asai, Soil-water strong coupled ISPH based on u-w-p formulation for large deformation problems, Comput. Geotech.
     142 (2022) 104570, http://dx.doi.org/10.1016/j.compgeo.2021.104570.
[39] G. Ma, H.H. Bui, Y. Lian, K.M. Tran, G.D. Nguyen, A.five-phase. approach, SPH framework and applications for predictions of
      seepage-induced internal erosion and failure in unsaturated/saturated porous media, Comput. Methods Appl. Mech. Engrg. 401 (2022)
     115614, http://dx.doi.org/10.1016/j.cma.2022.115614.
[40]  F. Brezzi, On.the. existence, Uniqueness and approximation of saddle-point problems arising from Lagrangian multipliers, Rev. Fr.
     D’Autom. Inform. Rech. Oper. 8 (1974) 129–151.
[41] M. Huang, Z.Q. Yue, L.G. Tham, O.C. Zienkiewicz, On the stable finite element procedures for dynamic problems of saturated porous
     media, Internat. J. Numer. Methods Engrg. 61 (2004) 1421–1450, http://dx.doi.org/10.1002/nme.1115.
[42]  S. Kularathna, W. Liang, T. Zhao, B. Chandra,  J. Zhao, K. Soga, A semi-implicit material point method based on fractional-step
     method for saturated soil, Int. J. Numer. Anal. Methods Geomech. 45 (2021) 1405–1436, http://dx.doi.org/10.1002/nag.3207.
[43] D. Mašín, C. Tamagnini, G. Viggiani, D. Costanzo, Directional response of a reconstituted fine-grained soil - Part II: Performance of
      different constitutive models, Int. J. Numer. Anal. Methods Geomech. 30 (2006) 1303–1336, http://dx.doi.org/10.1002/nag.
[44]  T. Blanc, M. Pastor, A.stabilized.Fractional. Step, Runge–Kutta taylor SPH algorithm for coupled problems in geomechanics, Comput.
     Methods Appl. Mech. Engrg. 221–222 (2012) 41–53, http://dx.doi.org/10.1016/j.cma.2012.02.006.
[45]  Y.F. Jin, Z.Y. Yin, Two-phase PFEM with stable nodal integration for large deformation hydromechanical coupled geotechnical problems,
     Comput. Methods Appl. Mech. Engrg. 392 (2022) 114660, http://dx.doi.org/10.1016/j.cma.2022.114660.

                                                          31

### Page 32

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

[46] O.C. Zienkiewicz, A.H.C. Chan, M.  Pastor, B.A.  Schrefler,  T. Shiomi, Computational Geomechanics, Wiley,  Chichester, 1999,
      http://dx.doi.org/10.1016/0148-9062(96)84010-1.
[47]  F. Oka, B. Shahbodagh, S. Kimoto, A computational model for dynamic strain localization in unsaturated elasto-viscoplastic soils, Int.
        J. Numer. Anal. Methods Geomech. 43 (2019) 138–165, http://dx.doi.org/10.1002/nag.2857.
[48]  P. Navas, L. Sanavia, S. López-Querol, R.C. Yu, U–W formulation for dynamic problems in large deformation regime solved through
     an implicit meshfree scheme, Comput. Mech. 62 (2018) 745–760, http://dx.doi.org/10.1007/s00466-017-1524-y.
[49]  P. Navas, M. Molinos, M.M. Stickle, D. Manzanal, A. Yagüe, M. Pastor, Explicit meshfree u- pw solution of the dynamic Biot
      formulation at large strain, Comput. Part. Mech. (2021) http://dx.doi.org/10.1007/s40571-021-00436-8.
[50]  F. Zabala, E.E. Alonso, Progressive failure of aznalcó llar dam using the material point method, Geotechnique 61 (2011) 795–808,
      http://dx.doi.org/10.1680/geot.9.P.134.
[51] A. Yerro, E.E. Alonso, N.M. Pinyol, The material point method  for unsaturated  soils, Geotechnique 65 (2015) 201–217,  http:
      //dx.doi.org/10.1680/geot.14.P.163.
[52]  J.J. Monaghan,  Extrapolating B  splines  for  interpolation,  J. Comput. Phys. 60 (1985) 253–262,  http://dx.doi.org/10.1016/0021-
     9991(85)90006-3.
[53] G. Oger, M. Doring, B. Alessandrini, P. Ferrant, An improved SPH method: Towards higher order convergence, J. Comput. Phys. 225
      (2007) 1472–1492, http://dx.doi.org/10.1016/j.jcp.2007.01.039.
[54] P.W. Randles, L.D. Libersky, Smoothed particle hydrodynamics: Some recent improvements and applications, Comput. Methods Appl.
     Mech. Engrg. 139 (1996) 375–408, http://dx.doi.org/10.1016/S0045-7825(96)01090-0.
[55] P.W. Cleary, J.J. Monaghan, Conduction modelling using smoothed particle hydrodynamics, J. Comput. Phys. 148 (1999) 227–264,
      http://dx.doi.org/10.1006/jcph.1998.6118.
[56]  P. Español, M. Revenga, Smoothed dissipative particle dynamics, Phys. Rev. E 67 (2003) 12, http://dx.doi.org/10.1103/PhysRevE.67.
     026705.
[57] H.H. Bui, R. Fukagawa, K. Sako, J.C. Wells, Slope stability analysis and discontinuous slope failure simulation by elasto-plastic
     smoothed particle hydrodynamics (SPH), Geotechnique 61 (2011) 565–574, http://dx.doi.org/10.1680/geot.9.P.046.
[58] H.H.  Bui, R. Fukagawa, An improved SPH method  for  saturated  soils and  its  application  to  investigate  the mechanisms  of
     embankment  failure: Case  of  hydrostatic pore-water  pressure,  Int.  J. Numer. Anal. Methods Geomech. 30 (2011) 1303–1336,
      http://dx.doi.org/10.1002/nag.
[59]  S. Shao, E.Y.M. Lo, Incompressible SPH method for simulating Newtonian and non-Newtonian flows with a free surface, Adv. Water
      Resour. 26 (2003) 787–800, http://dx.doi.org/10.1016/S0309-1708(03)00030-7.
[60] Nomeritae E. Daly, S. Grimaldi, H.H. Bui, Explicit incompressible SPH algorithm for free-surface flow modelling: A comparison with
     weakly compressible schemes, Adv. Water Resour. 97 (2016) 156–167, http://dx.doi.org/10.1016/j.advwatres.2016.09.008.
[61] D.A. Barcarolo, Improvement of the precision and the efficiency of the SPH method: theoretical and numerical study, Fluids Mech.
      [Physics. Class-Ph]. Ec. Cent. Nantes (2013).
[62] M. Hopp-Hirschler, U. Nieken, Fully implicit time integration in truly incompressible SPH, Eur. Phys.  J. Spec. Top. 227 (2019)
     1501–1514, http://dx.doi.org/10.1140/epjst/e2019-800152-6.
[63] H.H.  Bui, R. Fukagawa, An improved SPH method  for  saturated  soils and  its  application  to  investigate  the mechanisms  of
     embankment  failure: Case of  hydrostatic pore-water  pressure,  Int.  J. Numer. Anal. Methods Geomech. 37 (2013) 31–50,  http:
      //dx.doi.org/10.1002/NAG.1084.
[64] O.C. Zienkiewicz, C.T. Chang, P. Bettess, Drained, undrained, Consolidating and dynamic behaviour assumptions in soils, Geotechnique
     30 (1980) 385–395, http://dx.doi.org/10.1680/geot.1980.30.4.385.
[65] R. de Boer, W. Ehlers, Z. Liu, One-dimensional transient wave propagation in fluid-saturated incompressible porous media, Arch. Appl.
     Mech. 63 (1993) 59–72, http://dx.doi.org/10.1007/BF00787910.
[66] H. Sabetamal, M. Nazem, S.W. Sloan, J.P. Carter, Frictionless contact formulation for dynamic analysis of nonlinear saturated porous
     media based on the mortar method, Int. J. Numer. Anal. Methods Geomech. 40 (2016) 25–61, http://dx.doi.org/10.1002/nag.2386.
[67]  P. Navas, M. Pastor, A. Yagüe, M.M. Stickle, D. Manzanal, M. Molinos, Fluid stabilization of the u-w Biot’s formulation at large
       strain, Int. J. Numer. Anal. Methods Geomech. 45 (2021) 336–352, http://dx.doi.org/10.1002/nag.3158.
[68] Abaqus 6.11 Theory manual, (n.d.)..
[69] N. Manoharan, S.P. Dasgupta, Consolidation analysis of elasto-plastic soil, Comput. Struct. 54 (1995) 1005–1021, http://dx.doi.org/10.
     1016/0045-7949(94)00403-P.
[70] A. Locat, S. Leroueil, S. Bernander, D. Demers, H.P. Jostad, L. Ouehb, Progressive failures in eastern canadian and scandinavian
      sensitive clays, Can. Geotech. J. 48 (2011) 1696–1712, http://dx.doi.org/10.1139/t11-059.
[71] D.M. Cruden, D.J. Varnes, Chapter 3 Landslide Types and Processes, Landslides Investig. Mitigation, Transp. Res. Board Spec. Rep.
      247, Washingt. D.C, 1996, pp. 36–75.
[72] M.A. Carson, On the retrogression of landslides in sensitive muddy sediments, Can. Geotech. J. 14 (1977) 582–602, http://dx.doi.org/
      10.1139/t77-059.
[73]  S. Bernander, Progressive Landslides in Long Natural Slopes, Luleå University ofTechnology, Luleå, Sweden, 2011.
[74] R. Dey, B. Hawlader, R.  Phillips, K. Soga, Numerical modeling  of combined  effects  of upward and downward  propagation
      of shear bands on  stability of slopes with  sensitive  clay,  Int.  J. Numer. Anal. Methods Geomech. 40 (2016) 2076–2099,  http:
      //dx.doi.org/10.1002/nag.2522.
[75] X. Zhang, S.W. Sloan, E. Oñate, Dynamic modelling of retrogressive landslides with emphasis on the role of clay sensitivity, Int. J.
     Numer. Anal. Methods Geomech. 42 (2018) 1806–1822, http://dx.doi.org/10.1002/nag.2815.
[76] B. Wang, P.J. Vardon, M.A. Hicks, Investigation of retrogressive and progressive slope failure mechanisms using the material point
     method, Comput. Geotech. 78 (2016) 88–98, http://dx.doi.org/10.1016/j.compgeo.2016.04.016.

                                                          32

### Page 33

Y. Lian, H.H. Bui, G.D. Nguyen et al.                   Computer Methods in Applied Mechanics and Engineering 408 (2023) 115967

[77]  Y.F. Jin, Z.Y. Yin, W.H. Yuan, Simulating retrogressive slope failure using two different smoothed particle finite element methods: A
      comparative study, Eng. Geol. 279 (2020) 105870, http://dx.doi.org/10.1016/j.enggeo.2020.105870.
[78] W.H. Yuan, K. Liu, W. Zhang, B. Dai, Y. Wang, Dynamic modeling of large deformation slope failure using smoothed particle finite
     element method, Landslides 17 (2020) 1591–1603, http://dx.doi.org/10.1007/s10346-020-01375-w.
[79] C. Wang, B. Hawlader, D. Perret, K. Soga,  J. Chen, Modeling of initial stresses and seepage for large deformation finite-element
      simulation of sensitive clay landslides,  J. Geotech. Geoenviron. Eng. 147 (2021) 04021111, http://dx.doi.org/10.1061/(asce)gt.1943-
     5606.0002626.
[80]  F. Tremblay-Auger, A. Locat,  S.  Leroueil,  P. Locat, D. Demers,  J. Therrien, R. Mompin, The 2016  landslide  at  saint-luc-de-
      vincennes, quebec: Geotechnical and morphological analysis of a combined flowslide and spread, Can. Geotech. J. 58 (2021) 295–304,
      http://dx.doi.org/10.1139/cgj-2019-0671.
[81] K.K. Hamouche, S. Leroueil, M. Roy, A.J. Lutenegger, In situ evaluation of K0 in eastern Canada clays, Can. Geotech. J. 32 (1995)
     677–688, http://dx.doi.org/10.1139/t95-067.
[82]  S. Odenstad, The landslide in Skoptrop on the Lidan river, in: R. Swedish Geotech. Inst. Proc. No. (4), 1951.
[83] D.M.  Potts, N. Kovacevlc, P.R. Vaughan, Delayed collapse of cut slopes  in  stiff  clay, Geotechnique 47 (1997) 953–982,  http:
      //dx.doi.org/10.1680/geot.1997.47.5.953.

                                                          33
