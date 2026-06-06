# Soil-water strong coupled ISPH based on [formula omitted] formulation for large deformation problems

> Auto-converted from PDF for Codex/code-reference reading. Formatting, equations, figures, and tables may require checking against the original PDF.

- Source PDF: `Morikawa u-w-p.pdf`
- Pages: 20
- PDF metadata author: Daniel S. Morikawa

## Extracted Text

### Page 1

Computers and Geotechnics 142 (2022) 104570

                                                 Contents lists available at ScienceDirect

                        Computers and Geotechnics

                                         journal homepage: www.elsevier.com/locate/compgeo

Research paper

Soil-water strong coupled ISPH based on u −w −𝑝formulation for large
deformation problems
Daniel S. Morikawa ∗, Mitsuteru Asai

Kyushu University, 744 Motooka Nishi-ku, Fukuoka, Japan

A R T I C L E   I N F O            A B S T R A C T

MSC:                                             This paper is dedicated to the introduction of a strong coupled soil–water interaction formulation based on an
00-01                                            incompressible smoothed particle hydrodynamics (ISPH) framework. The method is based on the u−w−𝑝Biot’s
99-00                                           formulation and adapted to a semi-implicit projection method for incompressibility condition of pore water
Keywords:                                   and soil grains. The SPH Lagrangian particles move according to the soil velocity, while water variables are
SPH method                                embedded into such soil particles. This allows to solve the pressure Poisson equation in a strong coupling
ISPH                                        way, in addition to enable to update the Darcy’s drag force implicitly. A simple boundary treatment on
Saturated soil                                       natural boundary conditions for soil particle is proposed to take into account both non-penetration and friction
Slope stability
                                                           effects. The proposed method was verified and validated through a series of numerical tests resulting in good
Incompressible pore fluid
                                             agreements with both theoretical and experimental results. Finally, we show the applicability of the proposed
                                         method in the famous Selborne experiment, a full-scale slope failure problem.

1. Introduction                                                                    soil as a fluid-like material. With this same approach, Cascini et al.
                                                                   (2014) utilized SPH for channelized landslides, and Lin et al. (2019)
   The  smoothed  particle  hydrodynamics  (SPH)  method   is  a     coupled partitioned finite elements and interface elements method to
Lagrangian mesh-less numerical method developed by Gingold and     predict whether a previously defined slip surface would fail with SPH
Monaghan (1977) and Lucy (1977). The greatest advantage of SPH over     to simulate the landslide flow as a fluid-like material.
mesh-based methods such as the finite element method (FEM) is the                                                           One problem of this approach is that it does not interact with the
free moving nature of its Lagrangian particles. Hence, the SPH does
                                                                           great achievements of Geomechanics material modeling, such as the
not suffer from usual difficulties caused by mesh distortion in highly
                                                                     concept of consolidation and drained/undrained behavior to predict
dynamic problems.
                                                                        the initiation of colloidal state for Geomaterials. Instead, it focuses on
   The current work is based on SPH’s incompressible form (ISPH),
                                                                      very specific behavior of soils under specific conditions. Hence, it iswhich was first developed by Cummins and Rudman (1999) and later
                                                                        impossible to verify and validate such formulations with typical Soilapplied and enhanced in many forms (Pozorski and Wawrenczuk, 2002;
Khayyer et al., 2008; Asai et al., 2012; Barcarolo et al., 2014; Morikawa    Mechanics benchmark tests.
et al., 2019, 2021; Morikawa and Asai, 2021; Asai et al., 2021). Its        Early attempts to derive purely Geomechanics formulations on SPH
main feature is to impose incompressibility from a projection method    can be retrieved from Bui et al. (2008), where they focus on the besimilar to the moving-particle semi-implicit method (MPS) (Koshizuka     havior of dry soil using elastoplastic material based on Drucker–Prager
and Oka, 1996), which results in a pressure Poisson equation (PPE).       constitutive model.  It was followed by Bui and Fukagawa (2009),
   Application of SPH to Geomechanics problems can probably be    where they conducted a first attempt of the soil–water coupled problem
dated back to 2004 with Maeda et al. (2004)’s work (later translated to    with the u-p formulation under the assumption of two phases–one
English in Maeda et al. (2006)). However, due to language barriers, this     point framework. Later, Bui and Nguyen (2017) coupled the previously
paper was restricted to the Japanese research scene. Internationally,                                                                mentioned dry soil SPH formulation with water SPH particles, which
one of the earlier works of SPH to Geomechanics problems can be cred-
                                                                  can be called a two points–two phases framework.
ited to Naili et al. (2005), who have used SPH with a non-Newtonian
                                                             From our point of view, although Bui and Nguyen (2017)’s method
rheology model to simulate liquefaction. Due to the Lagrangian nature
                                                            was a notable advance in the topic of application of SPH to Geomechanof SPH particles and its wide use in Fluid Mechanics, most applications
                                                                                             ics, we believe that this work has some important shortcomings. First,
of SPH to Geomechanics have focused on approximating the ‘colloidal’

  ∗Corresponding author.
     E-mail address:  daniel@civil.doc.kyushu-u.ac.jp (D.S. Morikawa).

https://doi.org/10.1016/j.compgeo.2021.104570
Received 16 July 2021; Received in revised form 21 November 2021; Accepted 23 November 2021
Available online 30 December 2021
0266-352X/©  2022  The  Authors.      Published  by   Elsevier   Ltd.      This   is  an  open  access   article  under  the  CC  BY-NC-ND   license
(http://creativecommons.org/licenses/by-nc-nd/4.0/).

### Page 2

D.S. Morikawa and M. Asai                                                                                                    Computers and Geotechnics 142 (2022) 104570

the behavior of pressure dissipation over time has not been assessed
by this method. Although it surely contains the necessary equations to
simulate it, the authors chose to not include any numerical test that
addresses this topic, which is an essential feature of Soil Mechanics. In
addition, the integration of permeability (the drag force) is necessarily
explicit, since the water and soil particles are separated, which makes
a large constraint on its value range in relation to time increment (as
explained in Section 3 and demonstrated in Section 8.2).
   Similarly to Bui and Fukagawa (2009), Blanc and Pastor (2012)
                                                                                                 Fig. 1. Schematic illustration of the soil skeleton velocity 𝐯and water velocity 𝐯𝑤.
developed a coupled SPH method for the 𝐮−𝑝formulation (Zienkiewicz
et al., 1999), in which it is assumed that the pore water undergoes as
static seepage, that is, the acceleration of water in relation to the soil
skeleton is neglected. Since then, there were some developments on     particles are updated according to the soil skeleton velocity, while the
this method, mainly coupling it with fluid-like rheology models (Pastor     pore water velocity is treated as an internal variable of the particle.
et al., 2015).                                                       Hence, we use the material time derivative of 𝐯and the local time
   Although not under the scope of this work, because  it does not     derivative of 𝐯𝑤.
consider the movement of the soil itself, it is important to cite the great       The material and local derivatives are defined as, respectively,
work of Lian et al. (2021) for having developed a SPH framework for                                                            𝐷( )    𝜕( )
dealing with the seepage flow through unsaturated soil. We recommend   𝐷𝑡= 𝜕𝑡,                                                         (1)
the recent paper from Bui and Bguyen (2021) for readers interested in
reviewing the state-of-art of SPH for Geomechanics problems.
                                                            𝐷( )    𝜕( )
   However, there is a vacuum of studies using SPH with the full   𝐷𝑡= 𝜕𝑡+ (𝐯⋅∇)( ),                                              (2)𝐮−𝐰−𝑝formulation (Biot, 1956), which might be important to
problems that involve high-frequency loadings such as earthquakes and    where 𝑡represents time.
problems with soil of low permeability (Zienkiewicz et al., 1999), since     We also define a third velocity-like parameter called Darcy’s velocthe relative acceleration of pore water with respect to the soil skeleton      ity 𝐰, which is defined as the average water discharge over a unit cross
is an important factor.                                                     section area (units of [length]3∕([time][length]2), in other words, volume
   In this work, we propose a strong coupling ISPH based on the 𝐮−     per time per area). The relationship between 𝐯, 𝐯𝑤and 𝐰for saturated
𝐰−𝑝Biot’s formulation (Biot, 1956) to expand application to dynamic      soils can be written as
seepage flow problems with low permeability. The incompressibility is
then applied to enforce both pore fluid and soil grains as incompress-   𝐰= 𝑛(𝐯𝑤−𝐯),                                                       (3)
ible, which results in a strong coupled PPE. A considerable amount of
                                                              where 𝑛is the porosity.
inspiration for this method has been taken from developments on the
                                                                    Given the density of soil grains 𝜌𝑠and the water density 𝜌𝑤, thematerial point method (MPM) with their great works in this topic such
                                                                    mixture density is defined asas Kularathna et al. (2021).
   The current formulation treats soil skeleton deformation in a La-
                                              𝜌= (1 −𝑛)𝜌𝑠+ 𝑛𝜌𝑤.                                                  (4)
grangian manner, while water variables are integrated into the soil
particles (called one point–two phases). The soil material is modeled         Finally, as common practice in Geotechnical Engineering, we split
with conventional elastoplastic constitutive laws and a return mapping     the Cauchy stress tensor 𝝈into the effective stress 𝝈′ and pore water
technique that can be easily adapted to any constitutive model (in this     pressure 𝑝as (Zienkiewicz et al., 1999)
work, we use only Mohr–Coulomb and modified Cam–Clay models).
The boundary treatment is heavily simplified due to simple constraints   𝝈= 𝝈′ −𝛼𝑝𝐈,                                                        (5)
on velocity and pressure, and numerical tests show a good applicability
                                                              where 𝐈is the identity matrix and 𝛼= 1 −𝐾𝑇∕𝐾𝑠is a scalar related toof this boundary condition. Finally, an example using the Selborne
                                                                        the ratio of soil skeleton bulk modulus 𝐾𝑇to solid grains bulk modulusexperiment (Cooper et al., 1998; Bromhead et al., 1998) is conducted
                                                                       𝐾𝑠. Notice that we use the traction positive sign convention for stress.to show the robustness of our proposed method.

2. Coupling porous media–water formulation                             2.2. Original governing equations

   This section  is devoted to define the essential variables for the
                                                                The original set of governing equations are: linear momentum equiGeomechanics analysis and its governing equations. We follow the so-
                                                                        librium of the mixture, linear momentum equilibrium of the internal
called Biot formulation (Biot, 1956) (also called 𝐮−𝐰−𝑝formulation)
                                                                    pore water and the conservation of mass for the water part. For
in a similar manner as explained in Zienkiewicz et al. (1999). The main
                                                                         readers interested in the derivation of such equations, please refer
difference is the constraint that both soil grains and pore water are
                                                                            to Zienkiewicz et al. (1999).
treated as incompressible in this study. Hence, all parameters related to
compressibility of grains and water are disregarded. Also, we are using
                                                                                                                      • Mixture linear momentum equilibrium
soil skeleton velocity 𝐯instead of displacement 𝐮and water velocity 𝐯𝑤
instead of Darcy’s velocity 𝐰to better adapt into the SPH framework.        𝜌𝐷𝐯  ∇⋅𝝈+ 𝜌𝐠−𝜌𝑤 𝐷𝐰                                     (6)                                                𝐷𝑡=            𝐷𝑡.
2.1. Background definitions                                                                               • Pore water linear momentum equilibrium

                                                          𝐷𝐯           𝐷𝐰   Here, we define the standard nomenclature and symbols of common         𝜌𝑤    ∇𝑝+ 𝜌𝑤𝐠−𝜌𝑤                                        (7)                                                 𝐷𝑡=            𝑛 𝐷𝑡−𝐑.
terms in Geomechanics used throughout the article. First, consider a
control volume of saturated soil as in Fig. 1. The average velocity of             • Pore water mass conservation
soil grains are represented as 𝐯, while the average velocity of pore                                                                                       1 𝜕𝑝    𝑛
water as 𝐯𝑤. Notice that the actual movement of the Lagrangian SPH      ∇⋅𝐰+ 𝛼∇⋅𝐯+ 𝑄 𝜕𝑡+ 𝜌𝑤 ̇𝜌𝑤+ ̇𝑠= 0.                         (8)

                                                                        2

### Page 3

D.S. Morikawa and M. Asai                                                                                                    Computers and Geotechnics 142 (2022) 104570

   In the above equations, 𝐠is the gravity acceleration vector, 𝐑is the     3. Projection method
Darcy’s drag force, 1∕𝑄= 𝑛∕𝐾𝑤+ (𝛼−𝑛)∕𝐾𝑠is a parameter related to
the mixture compressibility (𝐾𝑤is the water bulk modulus) and ̇𝑠is the        Here, we explain the projection method used in the present work.
rate of soil grains volume expansion due to external conditions such as    The basic idea is to project the velocity into an explicit predictor step,
temperature change.                                             where pressure is not taken into account, and then correct this velocity
  𝐑is defined as 𝐑= 𝜌𝑤𝑔𝐤−1𝐰, where 𝑔is the gravity accelera-    with the influence of pressure implicitly. Hence, its description as a
tion norm and 𝐤is the permeability tensor which takes into account     semi-implicit method. All time derivatives are evaluated with first order
anisotropic permeability. In this study, we consider the isotropic case;     symplectic operators, i.e.,
hence, 𝐤is simplified as a scalar 𝑘, and 𝐑becomes                                                                                𝜕( )     ( )𝛽+1 −( )𝛽
    𝜌𝑤𝑔                                         𝜕𝑡=     𝛥𝑡         ,                                             (16)
𝐑= 𝑘𝐰,                                                          (9)                                                              where 𝛥𝑡is the time increment, and the superscripts 𝛽and 𝛽+ 1
with 𝑘dimensions being [length]∕[time].                                   represent the current and next time steps, respectively.
  An additional equation must be defined for the mass conservation of        Before starting,  it  is necessary to derive the linear momentum
the solid skeleton in order to update the porosity 𝑛. Similarly to Bandara     equilibrium equations in terms of 𝐯𝑤and isolating water from soil
and Soga (2015) and Bui and Nguyen (2017), we define this equation     acceleration terms and vice-versa. Multiplying Eq. (12) by 1∕𝑛and
in terms of the soil skeleton density (1 −𝑛)𝜌𝑠and its velocity 𝐯,            subtracting by Eq. (7), we can eliminate the Darcy’s acceleration term
𝐷[(1 −𝑛)𝜌𝑠]                                                      (𝐷𝐰∕𝐷𝑡). Including Eqs. (3), (9) and the definition of the mixture
        + ∇⋅[(1 −𝑛)𝜌𝑠𝐯] = 0.                               (10)     density (Eq, (4)), after some algebra, we finally derive the linear    𝐷𝑡
                                                     momentum conservation for the soil skeleton as
2.3. Governing equations in the incompressibility limit                                                    𝐷𝐯          1                   𝑛2𝜌𝑤𝑔                                                    𝐠+       ∇⋅𝝈′ −1 ∇𝑝+                              (17)                                            𝐷𝑡=     (1 −𝑛)𝜌𝑠         𝜌𝑠       (1 −𝑛)𝜌𝑠𝑘(𝐯𝑤−𝐯).
   In the incompressibility limit, most of the equations explained until
                                                                                  Similarly, we derive the final form for the water conservation ofnow can be simplified, while maintaining Mathematical precision. Ba-
                                                                               linear momentum applying Eqs. (3), (9) on Eq. (7), and rememberingsically, 𝐾𝑠and 𝐾𝑤are regarded as infinite, while the time derivative
                                                                             that 𝐯𝑤is updated with the local derivative (Eq. (2)),of density is null. In addition, we are not considering any thermal
expansion in this study. As a consequence,                            𝜕𝐯𝑤                                                     = 𝐠−(𝐯⋅∇)𝐯𝑤−1 ∇𝑝−𝑛2𝜌𝑤𝑔                             (18)       1                                                                         𝜕𝑡                𝜌𝑤     𝑛𝜌𝑤𝑘(𝐯𝑤−𝐯).
𝛼= 1, 𝑄= ̇𝜌𝑤= ̇𝑠= 0                                         (11)       The drag force on Eq. (18) can be obviously further simplified, but
   The linear momentum equilibrium equation for the mixture (Eq. (6))   we are showing in this form to highlight the symmetry between soil
written as a function of effective stress (Eq. (5)) for incompressible soil     to water and water to soil forces. Classically, the drag force term is
particle (Eq. (11)) becomes                                             placed in the predictor step as an explicit force, so that the predictor
𝜌𝐷𝐯  ∇⋅𝝈′ −∇𝑝+ 𝜌𝐠−𝜌𝑤 𝐷𝐰                                 (12)     step becomes 𝐷𝑡=                 𝐷𝑡,                                                                    (                                                                                            )                                                     ⎧𝐯∗= 𝐯𝛽+ 𝛥𝑡                                                         𝐠+    1              𝑛2𝜌𝑤𝑔  𝑤−𝐯𝛽)while the linear momentum for the water phase (Eq. (7)) does not    ⎪               (1−𝑛)𝜌𝑠∇⋅𝝈′𝛽+ (1−𝑛)𝜌𝑠𝑘(𝐯𝛽
                                                     ⎨         (                    )                     (19)change       within              the incompressibility                                         limit.
   Using         Eq. (11)               on Eq. (8), mass                                   conservation for the water phase        ⎪⎩𝐯∗𝑤= 𝐯𝛽𝑤+ 𝛥𝑡 𝐠−(𝐯𝛽⋅∇)𝐯𝛽𝑤−𝑛𝑔𝑘(𝐯𝛽𝑤−𝐯𝛽)  ,
becomes                                                                  Notice that the drag force is composed by a scalar term multiplied
                                                              by a relative velocity. Hence, if explicitly integrated in time, such as
∇⋅𝐰+ ∇⋅𝐯= 0.                                                (13)                                                                              in Bui and Nguyen (2017), the conditions
   Exchanging 𝐰to 𝐯𝑤through Eq. (3), we derive                             𝑛2𝜌𝑤𝑔                                              𝑎= 𝛥𝑡            1 & 𝑏= 𝛥𝑡𝑛𝑔   1                             (20)                                                                                        (1 −𝑛)𝜌𝑠𝑘<     𝑘<𝑛∇⋅𝐯𝑤+ (1 −𝑛)∇⋅𝐯= 0.                                        (14)
                                                               must be verified for the drag force to maintain its stability (see Sec-
    Similarly, Eq. (10) might be simplified disregarding the time and                                                                             tion 8.2). This would lead to a critical constraint on 𝛥𝑡if 𝑘is very small.
spatial derivative of 𝜌𝑠, hence                                    To solve this problem, some studies such as Kularathna et al. (2021)
𝐷𝑛                                                                     include the drag force into the predictor step and make it implicit in
𝐷𝑡= ∇⋅[(1 −𝑛)𝐯].                                             (15)     relation to the predicted velocity, so that
Remark         1. The                incompressibility                                     limit does                                          not                                    mean that                                                          the                                                      whole                                                                    (                                                                                            )                                                     ⎧                                                      𝐯∗= 𝐯𝛽+ 𝛥𝑡soil skeleton                 is incompressible.                                  Instead,                                                          it only                                       means                                                         that                                                       pore                                                        wa-                                                         𝐠+ (1−𝑛)𝜌𝑠∇⋅𝝈′𝛽+1              (1−𝑛)𝜌𝑠𝑘(𝐯∗𝑛2𝜌𝑤𝑔  𝑤−𝐯∗)                                                     ⎪
ter and soil grains are incompressible. Soil skeleton compressibility    ⎨         (                    )                     (21)
depends on the constitutive model chosen and its parameters. The vari-        ⎪⎩𝐯∗𝑤= 𝐯𝛽𝑤+ 𝛥𝑡 𝐠−(𝐯𝛽⋅∇)𝐯𝛽𝑤−𝑛𝑔𝑘(𝐯∗𝑤−𝐯∗)  .
able controlling numerical density of the SPH particle is the porosity,                                                                     Although it can relief the above-mentioned constraint in the time inwhich is updated using Eq. (15).                                        crement, it loses Mathematical consistency since the predicted velocity
                                                                                                is not a proper physical quantity. Instead, we suggest to calculate theRemark 2.  In theory, to consider true compressibility of pore water
                                                                    drag force implicitly and include it into the correction step to maintainand/or soil grains, it would be necessary additional equations to ac-
                                                                                                 its physical meaning.count for the change in density, since we already have four equations
                                                                The predictor step in this proposed method is then defined as
(Eqs. (6), (7), (8) and (10)) and four unknowns (𝐯, 𝐯𝑤, 𝑛, 𝑝). Some stud-
                                                                    (ies   such         as the             book                      in                    which                      we                               based                                     our formulation                                                       (Zienkiewicz                                                                                                                   1                                                     ⎧                                                      𝐯∗= 𝐯𝛽+ 𝛥𝑡                                                         𝐠+                                                                                          (1−𝑛)𝜌𝑠∇⋅𝝈′𝛽)et al.,      1999),             as               well as                      Blanc                        and                                 Pastor                                     (2012)                                       and Bandara                                                  and Soga                                                     ⎪
                                                     ⎨         (          )                                  (22)(2015),       have considered                      an                           incomplete                                          incompressibility                                                               constraint,                                                                               𝑤   .
i.e., considering                the time                           derivative                                       of densities                                                 as zero while                                                         main-        ⎪⎩ 𝐯∗𝑤= 𝐯𝛽𝑤+ 𝛥𝑡 𝐠−(𝐯𝛽⋅∇)𝐯𝛽
taining the term 1∕𝑄. In such case, the term 1∕𝑄works similarly to a      A comparison between the three methods of drag force time intedamping parameter to the pressure estimation. However, this approach     gration above (here called ‘‘drag force explicit’’, ‘‘drag force predictorslightly reduces Mathematical precision and consistency.                     implicit’’ and ‘‘drag force implicit’’) is shown in Section 8.2.

                                                                        3

### Page 4

D.S. Morikawa and M. Asai                                                                                                    Computers and Geotechnics 142 (2022) 104570

   Then, corrector step including the implicit drag force term is calculated as
                                    )            (⎧ 𝐯𝛽+1 = 𝐯∗+ 𝛥𝑡           −1     +  𝑛2𝜌𝑤𝑔  𝑤  −𝐯𝛽+1)⎪                𝜌𝑠∇𝑝𝛽+1   (1−𝑛)𝜌𝑠𝑘(𝐯𝛽+1
⎨           (                    )                   (23)
                          𝑤  −𝐯𝛽+1)  .  𝑤  = 𝐯∗𝑤+ 𝛥𝑡 −1𝜌𝑤∇𝑝𝛽+1 −𝑛𝑔𝑘(𝐯𝛽+1 ⎪⎩ 𝐯𝛽+1
    Isolating the 𝛽+ 1 velocity terms of Eqs. (23) to the left-hand side,
we have
⎧
                                                                                                                 Fig. 2. Schematic illustration of the return mapping.⎪ (1 + 𝑎)𝐯𝛽+1 + (−𝑎)𝐯𝛽+1𝑤  = 𝐯∗−𝛥𝑡𝜌𝑠∇𝑝𝛽+1                          (24)
⎨ (−𝑏)𝐯𝛽+1 + (1 + 𝑏)𝐯𝛽+1𝑤  = 𝐯∗𝑤−𝛥𝑡𝜌𝑤∇𝑝𝛽+1, ⎪⎩
where 𝑎and 𝑏are defined in Eq. (20).                                        4.1. Return mapping
   Solving Eqs. (24) for velocity we derive the final form of the
                                                                          Before starting, we must define the yield function 𝜑, the flow rulecorrector step as
             1  (⎧  𝐯𝛽+1 =                                      )∇𝑝𝛽+1)               𝛹andconstitutiveany setmodelof hardeningchosen. Here,variableswe use𝜶, eitherwhich thedependMohr–Coulombon the plasticor                 (1 + 𝑏)𝐯∗+ 𝑎𝐯∗𝑤−𝛥𝑡(          1+𝑎+𝑏                                       1+𝑏𝜌𝑠+ 𝜌𝑤𝑎⎪
⎨           1  (                          𝑏    1+𝑎                      (25)     the modified Cam–Clay models depending on the problem.  𝐯𝛽+1𝑤  = 1+𝑎+𝑏 𝑏𝐯∗+ (1 + 𝑎)𝐯∗𝑤−𝛥𝑡( 𝜌𝑠+ 𝜌𝑤 )∇𝑝𝛽+1) ⎪⎩                                                                                          .                       Then, we define the elastic trial state for the effective stress 𝝈′trial,                                                               which depends on the elastic constitutive model. Here, it was chosen
   Next, we developed a pressure Poisson equation (PPE) as follows.     the hypoelastic material with the Jaumann rate update.
First, consider the incompressible conservation of mass for the water       Then, we check whether the trial state lies within the plastic yield
phase as in Eq. (14). The above equations of the corrector step (Eqs.     condition 𝜑(𝝈′trial, 𝜶trial) ≤0. If so, trial state is considered to be correct
(25)) can be applied into Eq. (14) directly, and, after some rearranging,    and the material is under pure elastic deformation. If not, the trial stress
we obtain                                                                                    is corrected as
∇2𝑝𝛽+1 = 1 −𝑛+ 𝑏 ∇⋅𝐯∗+ 𝑛+ 𝑎 ∇⋅𝐯∗𝑤,                           (26)     𝝈′𝛽+1 = 𝝈′trial −𝛥𝛾𝐂𝑒𝑙∶𝐍𝛽+1,                                    (29)         𝐶         𝐶
where                                                         where 𝛥𝛾is the plastic multiplier (amount of plastic correction) and
     ( 1 −𝑛+ 𝑏  𝑛+ 𝑎 )                          𝐍= 𝜕𝛹∕𝜕𝝈′ is the direction of the plastic flow. The superscript 𝛽+ 1 is
𝐶= 𝛥𝑡       +             ,                                      (27)     to represent that the correction is applied in order to accommodate the            𝜌𝑠      𝜌𝑤
                                                                             yield function to this new configuration (i.e., 𝜑𝛽+1 = 𝜑(𝝈′𝛽+1, 𝜶𝛽+1) =
which is an implicit equation that must be calculated through a linear                                                                                        0), as in Fig. 2.
solver. In this study, we have chosen the conjugate gradient method,
since the left hand side of Eq. (26) is positive and symmetric.                                                                                 4.2. Hypoelasticity
    Finally, with the pressure profile calculated, we update the velocities with the corrector step (Eq. (25)) and update the position of the       As usual in Soil Mechanics, the constitutive model is only applied to
particle with a first order symplectic time integration scheme (Eq. (16))     the effective stress, rather than the Cauchy stress. Our proposed method
as                                                                         describes the elastic behavior of the soil skeleton as a hypoelastic
𝐱𝛽+1 = 𝐱𝛽+ 𝛥𝑡𝐯𝛽+1.                                             (28)     material using the Jaumann rate for time integration. The Jaumann rate
                                                                              in terms of the effective stress can be expressed as
                                                            𝐷𝝈′
4. Effective stress update                          𝐷𝑡= 𝐂𝑒𝑙∶𝐃+ 𝐖⋅𝝈′ + 𝝈′ ⋅𝐖𝑇,                               (30)

   In this section, we explain the effective stress update and the return
                                                                        1
mapping technique used in this proposed method. Most previous works   𝐃=  (𝐋+ 𝐋𝑇),                                                 (31)
                                                                        2
such as Bui et al. (2008) derive an elastoplastic tangent moduli for an
specific constitutive model. Then, the stress is updated with a single
                                                                        1equation that incorporates both elastic and plastic parts.         𝐖=  (𝐋−𝐋𝑇),                                                (32)
                                                                        2
   In this work, however, we show a more generalized form of the
return mapping called elastic predictor/plastic corrector algorithm, as
explained in de Souza Neto et al. (2008). Here, the stress update is   𝐋= (∇⊗𝐯)𝑇,                                                  (33)
divided into two steps: an elastic predictor step (leading to a trial state
                                                              where 𝑇is the transpose operator, 𝐃and 𝐖are the rate-of-deformation𝝈′trial) and a plastic corrector step (return mapping leading to 𝝈′𝛽+1). A
                                                              and spin tensors related to the spatial gradient of velocity 𝐋, and 𝐂𝑒𝑙isschematic illustration of this method is shown in Fig. 2. In comparison,
                                                                        the Hookean elastic material tangent moduli.
the elastoplastic tangent moduli would be a straight line from 𝝈′𝛽to
                                                                               Integrating Eq. (30) explicitly, we have
𝝈′𝛽+1 in Fig. 2.
   The reason for choosing a more general technique is to make it     𝝈′𝛽+1 = 𝝈′𝛽+ 𝛥𝑡(𝐂𝑒𝑙∶𝐃𝛽+1 + 𝐖𝛽+1 ⋅𝝈′𝛽+ 𝝈′𝛽⋅(𝐖𝛽+1)𝑇).          (34)
easier to adapt to any plastic constitutive model as pleased. Also, this
                                                                The superscript 𝛽+ 1 for 𝐃and 𝐖in Eq. (34) are due to the fact
technique is very convenient for complex constitutive models such as
                                                                             that the stress is updated after the velocity (i.e., 𝐋𝛽+1 = (∇⊗𝐯𝛽+1)𝑇).
the modified Cam–Clay, in which a Newton–Raphson routine guar-
                                                                           This elastic stress update might be used exactly in this form as in
antees the stability and accuracy of the return mapping taking into
                                                                         Section 8.2 when the soil skeleton is considered to be purely elastic.
account any type of hardening rule (see Appendix B). The objective
                                                                              Alternatively, it is regarded as the trial state of the return mapping
here is to merely show the implementation of such techniques into
                                                                      algorithm in case of an elastoplastic material, i.e.,
the SPH framework, rather than deriving the formulation. Readers
interested in more details should refer to de Souza Neto et al. (2008).        𝝈′trial = 𝝈′𝛽+ 𝛥𝑡(𝐂𝑒𝑙∶𝐃𝛽+1 + 𝐖𝛽+1 ⋅𝝈′𝛽+ 𝝈′𝛽⋅(𝐖𝛽+1)𝑇).          (35)

                                                                        4

### Page 5

D.S. Morikawa and M. Asai                                                                                                    Computers and Geotechnics 142 (2022) 104570

   For a detailed explanation on the implementation of the return map-       As clearly seen in Eq. (44), the force exerted from particles 𝑖to 𝑗is
ping for Mohr–Coulomb and modified Cam–Clay, refer to Appendices A     the same as its counterpart from 𝑗to 𝑖.
and B, respectively.                                                The usage of Eqs. (40) and (43) as opposed to (38) and (39) is very
                                                                     important in the context of elasticity, since Eqs. (38) and (39) are not
5. The SPH method                                                                      capable of preserving angular momentum, as explained by Bonet and
                                                               Lok (1999) and Lee et al. (2016). Because of its first order consistency,
   The SPH method  is a numerical scheme in which the domain
                                                                        Eq. (40) is preferred over Eq. (43), except when applied to the stress
is discretized into Lagrangian particles in the context of Continuum
                                                                              tensor, where being conservative is crucial to the overall accuracy.
Mechanics. The general idea is to approximate a function 𝑓and its
spatial derivatives based on such function values contained in neigh-         Finally, the Laplacian of a function might be estimated as
boring particles according to a weight parameter 𝑊also called kernel.             𝑁
                                                                            2 ∑   𝐫𝑖𝑗⋅∇𝑊(𝐫𝑖𝑗, ℎ)
Mathematically, the primordial SPH approximation can be denoted as     ⟨∇2𝑓⟩𝑖=      𝑚𝑗              (𝑓𝑖−𝑓𝑗),                        (45)
                                                                                                        𝜌𝑖 𝑗=1         𝐫2𝑖𝑗     𝑁
  ∑ 𝑚𝑗
⟨𝑓⟩𝑖=       𝑓𝑗𝑊(𝐫𝑖𝑗, ℎ),                                        (36)    which is a combination of SPH and finite difference methods proposed
       𝑗=1 𝜌𝑗                                                              by Morris et al. (1997). Although there are some attempts to improve
where 𝑖and 𝑗represent a target and a neighbor particle, respectively,     the accuracy of SPH second derivatives such as Faheti and Manzari
𝑚the mass, 𝜌the density, 𝐫𝑖𝑗= 𝐱𝑖−𝐱𝑗the relative position vector, 𝑁     (2011), we decided to maintain using Eq. (45), since it already provide
the total number of particles and ℎthe smoothing length, which, in this     reasonable solutions for our numerical examples.
study, has been chosen to be ℎ= 1.2𝑑(𝑑is the particle diameter).                                                   𝜕   𝜕   𝜕
                                                                               In these equations, ∇=  ( 𝜕𝑥, 𝜕𝑦, 𝜕𝑧) is the nabla operator and ⟨⟩   Originally, the first derivative of a function in SPH is calculated as
                                                                          represent the SPH approximation. For all numerical analysis in this
   ∑𝑁 𝑚𝑗                                                             study, we have chosen the cubic spline (Schoenberg, 1964) for the
⟨∇𝑓⟩𝑖=       (𝑓𝑗)∇𝑊(𝐫𝑖𝑗, ℎ),                                   (37)     kernel 𝑊.         𝑗=1 𝜌𝑗

   However, as widely known in the SPH community,
        𝑁                                                             6. Application of SPH approximations on governing equations
        1 ∑
⟨∇𝑓⟩𝑖=      𝑚𝑗(𝑓𝑗−𝑓𝑖)∇𝑊(𝐫𝑖𝑗, ℎ),                             (38)
           𝜌𝑖 𝑗=1
                                                       Up to now, all equations were written in a generic form that could
and                                                             be applied to any numerical method. Here, we include some additional
    ∑𝑁   ( 𝑓𝑖    𝑓𝑗 )                                                   attributes of the proposed method such as stabilization procedures and
⟨∇𝑓⟩𝑖= 𝜌𝑖   𝑚𝑗   +    ∇𝑊(𝐫𝑖𝑗, ℎ)                            (39)    boundary conditions. In addition, we clearly show how to implement            𝑗=1     𝜌2𝑖    𝜌2𝑗
                                                       SPH approximations from Section 5 into the results of Sections 2–4 .
are usually much more stable than Eq. (37). Notice that Eqs. (38) and
(39) are easily derived from Eq. (37) taking the derivative of 𝜌𝑓and
𝑓∕𝜌, respectively (Monaghan, 1992).                                         6.1. Stabilization
  Many researchers have attempted to increase the accuracy of the
SPH first derivative approximation. As initially developed by Randles
                                                                               Similarly to previous works such as Lee et al. (2016) and Morikawa
and Libersky (1996) and followed by Bonet and Lok (1999), Eq. (38)
                                                              and Asai (2021), we include the JST stabilization term to avoid nu-can be expanded as
                                                                       merical instabilities in our elastoplastic model based on the Hypoelas-
        1 ∑𝑁                                                                            ticity. Since this procedure has already been well documented in both
⟨∇𝑓⟩𝑖=      𝑚𝑗(𝑓𝑗−𝑓𝑖)̃∇𝑊(𝐫𝑖𝑗, ℎ),                             (40)
           𝜌𝑖 𝑗=1                                                             references above, we abstain from longer explanations in this study.
                                                                            Including the stabilization parameter 𝐂JST in the predictor step ofwhere
                                                                        the linear momentum equation for the soil phase, it becomes
̃∇𝑊(𝐫𝑖𝑗, ℎ) = 𝐁𝑖∇𝑊(𝐫𝑖𝑗, ℎ),                                      (41)             (       1             )                                                     𝐯∗= 𝐯𝛽+ 𝛥𝑡 𝐠+                                                                        ∇⋅𝝈′𝛽+ 𝐂𝛽𝐽𝑆𝑇   ,                       (46)and                                                                                                   (1 −𝑛)𝜌𝑠
    ( 1 ∑𝑁                 )−1                                  where
𝐁𝑖=       𝑚𝑗∇𝑊(𝐫𝑖𝑗, ℎ) ⊗𝐫𝑗𝑖      .                              (42)
        𝜌𝑖 𝑗=1                                                   𝐂𝐽𝑆𝑇= 𝑐𝑝𝑑(𝜀(2)∇20𝐯),                                            (47)
   This formulation has the advantage of being first order consistent,
which means that it can solve the gradient of a linear function exactly.     𝑐𝑝is the p-wave velocity defined as
As a backside, it is not conservative, meaning that the effect of, say,    √
                                          𝐾+ 𝜇4∕3
particle 𝑖on particle 𝑗is not the same as of particle 𝑗on 𝑖. Hence, if used    𝑐𝑝=                       ,                                              (48)
                                                                                         (1 −𝑛)𝜌𝑠in the calculation of a force, it might not conserve linear momentum
exactly.                                                              and 𝜀(2) is a chosen coefficient.
   Ganzenmüller (2015) developed another formulation on the first
                                                                                  Differently than Lee et al. (2016) and Morikawa and Asai (2021),
derivative based on Eq. (39) expressed as
                                                     we do not include a fourth order term, since we concluded that it is
    ∑𝑁   ( 𝑓𝑖               𝑓𝑗        )                          not necessary for our purposes. In our numerical tests, this parameter
⟨∇𝑓⟩𝑖= 𝜌𝑖   𝑚𝑗    ̃∇𝑊(𝐫𝑖𝑗, ℎ) −   ̃∇𝑊(𝐫𝑗𝑖, ℎ)  ,                 (43)
            𝑗=1     𝜌2𝑖              𝜌2𝑗                                was sufficient to stabilize the whole formulation for a large number of
                                                                    time iterations. No stabilization in the water phase were necessary. In
which is conservative, but loses its first order consistency. To visualize
                                                                            general, we chose higher values of 𝜀(2) (as large as 0.5) for particles
the conservative property of Eq. (43), we can rewrite it as
                                                                    with elastic deformation, while we found to be important to maintain
    ∑𝑁   (   𝑓𝑖      𝑓𝑗 )                                        very small values (usually 0.01) when the particle is under plastic
⟨∇𝑓⟩𝑖= 𝜌𝑖   𝑚𝑗  𝐁𝑖  + 𝐁𝑗    ∇𝑊(𝐫𝑖𝑗, ℎ).                       (44)
            𝑗=1       𝜌2𝑖      𝜌2𝑗                                          deformation to avoid unphysical damping behavior.

                                                                        5

### Page 6

D.S. Morikawa and M. Asai                                                                                                    Computers and Geotechnics 142 (2022) 104570

                                                                               In other words, already exchanging the parameters 𝐚𝐧and 𝐟𝑓𝑟𝑖𝑐by
                                                                                their definitions (Eqs. (50) and (51)), the newly corrected velocity 𝐯′′′
                                                              due to friction can be defined as
                                  {                            𝐯′′
                                                                                                           𝐯′′′ =                                                                                                               𝐯′′ −𝜇𝑓𝑟𝑖𝑐|𝐧⋅𝐯′| |𝐯′′|,   if 𝜇𝑓𝑟𝑖𝑐|𝐧⋅𝐯′| < |𝐯′′|                (53)
                                                                                                    0,                    otherwise.

                                                                                     Finally, the corrected soil particle velocity is retrieved as

                                              𝐯= 𝐯′′′ + 𝐯wall.                                                 (54)

                                                              To increase clarity, algorithm 1 shows how this procedure is conFig. 3. Schematic illustration of essential (left) and natural (right) boundary conditions.
                                                                    ducted step-by-step. Consider the target particle 𝑖in position 𝐱𝑖ap-
                                                                    proaching a wall particle in position 𝐱𝑗with normal direction 𝐧𝑗. If the
                                                                          distance between them is smaller than 𝑑and the relative velocity 𝐯′𝑖𝑗
6.2. Boundary conditions                                                                           points to the wall, penetration is detected. Then, for the nearest wall
                                                                                particle j, correct the relative velocity (Eqs. (49) and (53)) and retrieve
   In this formulation, essential boundary conditions are trivially at-     the corrected soil particle velocity (Eq. (54)).
tributed simply assigning a specific value of a designated variable to the       The value of 𝜇fric might also be applied to impose some specific
particles in the boundary domain. For the natural boundary condition,    boundary conditions. For example, 𝜇fric = 0 can be applied for a freewe introduce a simplified wall boundary condition which takes into      slip condition, while an infinite value  (i.e., imposing  𝐯′′′ =  0) for
account both non-penetration and friction effects.                           non-slip. In general situations, we consider 𝜇fric = tan 𝜙, where 𝜙is
  A graphical representation of essential and natural boundary con-     the material internal friction angle.
ditions is shown in Fig. 3 exemplified as a cantilever beam fixed at
the left end and being supported by the floor at the right end. In
                                                               Algorithm 1 Boundary conditions
this example, the particles inside the left wall are assigned with zero
                                                                      Input: Target particle i: x𝑖, v𝑖, wall particles j: x𝑗, v𝑗, n𝑗velocity while the particles hitting the floor have their velocities in the
                                                                Output: corrected velocity v𝑖normal direction 𝐧erased (dashed velocity vector) as part of the non-
                                                                                                      if 𝑖is in the essential boundary domain then
penetration condition. This approach is the same as the one promoted
                                                                    Impose essential boundary condition
in Morikawa and Asai (2021).
                                                                            else
   Other instances of essential boundary conditions are zero pressure at
                                                                               for all wall neighbor particles 𝑗do
free-surfaces and zero water velocity at an impermeable wall boundary.
                                                                                                            if dist(x𝑖, x𝑗) ≤𝑑& v′𝑖𝑗⋅n𝑗≤0 then
In this work, we define a particle at the free-surface if there are less                                                                                 Penetration detected.
than a certain number of neighboring particles (for cubic spline kernel,
                                                                      Check minimum dist(x𝑖, x𝑗)
48 in 3-D simulations).                                                               end if
   Let us explain in more details the natural boundary conditions.       end for
First, a layer of wall particles is defined throughout the wall domain,         for nearest penetrated wall particle j do
each particle with a pre-defined normal direction pointing to the wall           Correct velocity for non-penetration condition: Eq. (49)
surface. Then, once the physical soil particle approaches the wall, its           Correct velocity for friction: Eq. (53)
velocity is numerically set to zero at the wall normal direction.                  Retrieve corrected velocity: Eq. (54)
   In mathematical terms, let us call 𝐯′ the relative velocity between       end for
soil particle and wall particle (𝐯′ = 𝐯−𝐯wall) before non-penetration      end if
correction and 𝐯′′ the corrected velocity. Then,

𝐯′′ = 𝐯′ −(𝐧⋅𝐯′)𝐧.                                              (49)     6.3. SPH approximations

   In this study, we also include the effect of wall friction on the
                                                                The equations introduced in this section suppress the superscript
natural boundary condition. First, notice that the term −(𝐧⋅𝐯′)𝐧from
                                                                                for time to facilitate visualization, since it is clearly discernible from
Eq. (49) can be interpreted as an acceleration 𝐚𝐧due to the applied                                                                        the context. For instance, a SPH approximation of the divergence of a
force from the wall, as
                                                                           variable in time 𝛽should use such variable in time 𝛽. Also, the so-called
                                                                    numerical density in SPH approximations are taken as the soil skeleton𝐚𝐧= −(𝐧⋅𝐯′) 𝐧.                                                 (50)
         𝛥𝑡                                                               density (not the mixture density), since we are solving all equations in
   The amplitude of the friction force 𝐟𝑓𝑟𝑖𝑐in terms of the Coulomb     terms of soil Lagrangian particles. For example, the numerical density
friction is defined as                                                         of a particle 𝑖is

|𝐟𝑓𝑟𝑖𝑐| = 𝜇𝑓𝑟𝑖𝑐𝑚|𝐚𝐧|,                                             (51)    𝜌𝑖= (1 −𝑛𝑖)𝜌𝑠,                                                  (55)

where 𝜇𝑓𝑟𝑖𝑐is the dynamic coefficient of friction. We could also easily    and its mass is
implement the effect of a static friction coefficient, but we decided
                                                   𝑚𝑖= 𝜌𝑖𝑑3,                                                      (56)to use exclusively the dynamic one, since there is high uncertainty in
obtaining such parameters.                                        where 𝑑3 is the particle volume.
   Given that the corrected velocity 𝐯′′ is already parallel to the wall        In the predictor step (Eq. (46)), the divergence of effective stress is
surface, we can finally derive 𝐟𝑓𝑟𝑖𝑐in both amplitude and direction as     evaluated using Eq. (43)
   {                                                                                           )                                                                                                               𝝈′𝑗                               ∑𝑁                                                                       ( 𝝈′𝑖                                      if |𝐟𝑓𝑟𝑖𝑐| < 𝑚|𝐯′′|∕𝛥𝑡         −𝜇𝑓𝑟𝑖𝑐𝑚|𝐚𝐧| |𝐯′′|,𝐯′′                                                                                                                                                                                                                                 ,               (57)𝐟𝑓𝑟𝑖𝑐=                                                                                  𝑚𝑗                                                                                                   ̃∇𝑊(𝐫𝑖𝑗, ℎ) −                                                                                                                   ̃∇𝑊(𝐫𝑗𝑖, ℎ)                                                               (52)    ⟨∇⋅𝝈′⟩𝑖= 𝜌𝑖
         −𝑚|𝐯′′|∕𝛥𝑡,       otherwise.                                                        𝑗=1     𝜌2𝑖              𝜌2𝑗

                                                                        6

### Page 7

D.S. Morikawa and M. Asai                                                                                                    Computers and Geotechnics 142 (2022) 104570

and the Laplacian of velocity for the JST stabilization term with    Algorithm 2 Initial conditions
Eq. (45) as
                                                                      Input: Initial x, v for all particles
         2 ∑𝑁    𝐫𝑖𝑗⋅∇𝑊(𝐫𝑖𝑗, ℎ)                                     Output: Effective stress distribution at the initial state 𝝈′
⟨∇2𝐯⟩𝑖=      𝑚𝑗               (𝐯𝑖−𝐯𝑗),                        (58)       Calculate kernel gradient correction (Eq. (42))
           𝜌𝑖 𝑗=1         𝐫2𝑖𝑗                                                                         Assign 𝝈′ = 0 for all particles
while the convection term for the water predictor step (Eq. (22)) with       for Iinit iterations do
Eq. (40)                                                                      Calculate the soil predictor step (Eqs. (46), (57), (47) and (58))
           𝑁                                                     Impose boundary condition (algorithm 1)
            1 ∑
                  𝑚𝑗̃∇𝑊(𝐫𝑖𝑗, ℎ) ⊗(𝐯𝑤,𝑗−𝐯𝑤,𝑖),                   (59)        Update trial effective stress (Eq. (35))⟨∇⊗𝐯𝑤⟩𝑖=
               𝜌𝑖 𝑗=1                                                       Return mapping (algorithm 4)
                                                           end for
                                                                         Reset velocity as v = 0 for all particles
⟨(𝐯⋅∇)𝐯𝑤⟩𝑖= 𝐯𝑖⋅⟨∇⊗𝐯𝑤⟩𝑖.                                     (60)

    Similarly, Eq. (40) is also used for the Jaumann rate stress update
in Eq. (33) as
                                                                           7. Proposed method overview
          1 ∑𝑁
⟨∇⊗𝐯⟩𝑖=      𝑚𝑗̃∇𝑊(𝐫𝑖𝑗, ℎ) ⊗(𝐯𝑗−𝐯𝑖).                        (61)
              𝜌𝑖 𝑗=1                                       We have already explained all features of the proposed method in
                                                                                     details. Now, we devote this section to facilitate understanding and
   Pressure gradient from the corrector step (Eq. (25)) is evaluated
                                                                      provide a guideline for those who desire to reproduce it. Algorithm 3
using equation Eq. (43)
                                                               shows in a step-by-step manner all procedure of this proposed method.
    ∑𝑁   ( 𝑝𝑖                𝑝𝑗        )                            Here, 𝛥𝑡is restricted by a simple Courant–Friedrichs–Lewy (CFL)
⟨∇⋅𝑝⟩𝑖= 𝜌𝑖   𝑚𝑗    ̃∇𝑊(𝐫𝑖𝑗, ℎ) −   ̃∇𝑊(𝐫𝑗𝑖, ℎ)  ,                (62)     condition as
             𝑗=1     𝜌2𝑖              𝜌2𝑗
                                                                        𝑑
   Eq. (40) is also used to approximate both the divergence of predictor    𝛥𝑡≤C𝐶𝐹𝐿     ,                                                   (66)                                                                                                  𝑐𝑝
velocity in the PPE (Eq. (26)) and the evolution of porosity in Eq. (15)
                                                               which the parameter C𝐶𝐹𝐿 =  0.5 showed to be sufficient in our
                                                                    numerical tests.
         1 ∑𝑁
⟨∇⋅𝐯⟩𝑖=      𝑚𝑗(𝐯𝑗−𝐯𝑖) ⋅̃∇𝑊(𝐫𝑖𝑗, ℎ),                          (63)
            𝜌𝑖 𝑗=1                                                  Algorithm 3 Proposed method overview

and                                                                  Input: Initial x, v for all particles
          𝑁                                                   Output: x, v, 𝝈′, 𝑝and 𝑛for all particles after I iterations
          1 ∑
⟨∇⋅𝐯𝑤⟩𝑖=      𝑚𝑗(𝐯𝑤,𝑗−𝐯𝑤,𝑖) ⋅̃∇𝑊(𝐫𝑖𝑗, ℎ),                      (64)       Define 𝛥𝑡restricted by (66)
              𝜌𝑖 𝑗=1                                                                        Initial effective stress state as algorithm 2
                                                                                       Initiate 𝛽= 0    Finally, the Laplacian of pressure for Eq. (26) is evaluated through
                                                                            for I iterations doEq. (45)
                                                                            a) Calculate kernel gradient correction (Eq. (42))
         2 ∑𝑁    𝐫𝑖𝑗⋅∇𝑊(𝐫𝑖𝑗, ℎ)                                           b) Predictor step (Eqs. (46), (47), (57) and (58))
             𝑚𝑗                               (𝑝𝑖−𝑝𝑗).                        (65)⟨∇2𝑝⟩𝑖=                                                                                c) Predictor step for water phase (Eqs. (22), (59) and (60))           𝜌𝑖 𝑗=1                        𝐫2𝑖𝑗
                                                                       d) Impose boundary condition (algorithm 1)
                                                                              e) Solve PPE (Eqs. (26), (27), (63) and (65))6.4. Initial conditions
                                                                                                 f) Corrector step (Eqs. (25) and (62))
                                                                            g) Impose boundary condition (algorithm 1)
   As usual in Geomechanics numerical simulations, the proposed
                                                                                                 f) Update porosity (Eqs. (15) and (63))
method requires an initial condition for the effective stress distribution
                                                                      h) Update trial effective stress (Eq. (35))
in the soil skeleton. Such initial condition might be evaluated through
                                                                                                                          if elastic body, 𝝈′𝛽+1 = 𝝈′trial and goto j)
in-site measurements, or by other methods such as the one explained
                                                                                                   i) Return mapping (algorithm 4 or 5)
in Bui and Fukagawa (2013), for example. However, given that the
                                                                                                    j) Update position (Eq. (28))
purpose of this paper  is to introduce the formulation rather than
                                                                         k) New time iteration: 𝛽= 𝛽+ 1
showing accurate applications, we simplify this assessment under the
                                                           end for
assumption that the program itself generate a reasonable effective stress
distribution after a number of iterations.
   More specifically, we start the simulation with a zero stress and     8. Numerical examples
zero velocity for all particles (unless otherwise predefined) and run the
stress update, predictor step for the soil phase and apply the boundary       Here we give a couple of numerical tests to demonstrate the rocondition a number of iterations, say, Iinit iterations (hence, we do not     bustness of the proposed method. First, we verify the strong coupling
update particle position for this initial phase). At the end, the generated   𝐮−𝐰−𝑝formulation with a hydrostatic problem. Then, with 1D
stress distribution is considered to be the initial condition and velocities     Terzaghi consolidation tests, we compare the three time integration
are once more set to zero. Algorithm 2 shows this process.                                                                schemes for the drag force as explained in Section 3 and assess its the
   Notice that this procedure is the same as running the proposed     sensitivity related to time increment and permeability. Following, we
method for dry soils without updating position vectors 𝐱. The fact that    show the capability of the proposed method to simulate both drained
it is not necessary to update pressure is due to the implicit nature of the    and undrained conditions in a triaxial compression test with the modcorrector step, which means that there is no need for an initial pressure      ified Cam–Clay yield criterion. Finally, we show the applicability of
profile to start the program.                                                                                    this method using the Selborne slope failure experiment (Cooper et al.,
                                                                1998) as a validation test in real scale.

                                                                        7

### Page 8

D.S. Morikawa and M. Asai                                                                                                    Computers and Geotechnics 142 (2022) 104570

Fig. 4. Hydrostatic  test: (a) geometry and (b) snapshots of the numerical test for
different time steps showing the pressure profile.

                                                                                                Fig. 6. Hydrostatic test: graphical representation of pressure profile at different time
                                                                                                       steps.

Fig. 5. Hydrostatic test: pressure as a function of time at the bottom center particle.

   Unless otherwise said, the JST coefficient is takes as 𝜀(2) = 0.5 for
particles under elastic deformation and 𝜀(2) = 0.01 for particles under
plastic deformation.

8.1. Hydrostatic pressure

   Here, we present a very simple verification test to check whether the
current formulation is capable of generating hydrostatic pressure field.
Although this test seems to be obvious at first glance, it is well-known
                                                                                                Fig. 7. Terzaghi consolidation problem: (a) geometry (in m) and (b) snapshots of the
in SPH community that SPH has some difficulties in dealing with static
                                                                                                  resulting numerical simulation for 𝑘= 10−3 m∕s and 𝛥𝑡= 10−5 s at different time steps
bodies due to the dynamic nature of the Lagrangian particles.              showing the pressure profile.
   The fully saturated material is confined into a squared container as
illustrated in Fig. 4a, and the parameters for this numerical test are
listed in Table 1. Mohr–Coulomb model is taken in its perfectly plastic
form. For the boundary conditions, all particles at either bottom or side
walls are set 𝐯𝑤= 0, and 𝑝= 0 is enforced at the free-surface. We
applied the natural boundary condition for 𝐯with 𝜇𝑓𝑟𝑖𝑐= tan 𝜙for all
walls.
    Fig. 4b illustrates some snapshots at different time steps and Figs. 5
and 6 show a graphical summary of our results. From the graphical
results, we conclude that our proposed method is capable of generating
a smooth and stable hydrostatic pressure distribution over an extended
period of time, as well as an almost indistinguishable pressure profile
from the theoretical solution.

8.2. One-dimensional Terzaghi consolidation

   The one-dimensional Terzaghi consolidation problem is probably
                                                                                                Fig. 8. Terzaghi consolidation problem: average values of effective stress, pressure and
to most widely used benchmark test in Geomechanics. It consists in
                                                                                                        total stress in relation to time factor 𝑇on the second layer of particles from bottom
a tall container filled with saturated soil, and a constant stress applied      to top for 𝑘= 10−3 m∕s and 𝛥𝑡= 10−5 s.
on the top free-surface. Here, we selected the same model parameters
as Bandara and Soga (2015), that is, a squared container 1 m tall and
0.06 m wide, as illustrated in Fig. 7a. The simulation is started with                                                                The gravity effect is neglected, that is, g=0, although the scalar 𝑔is
both pressure and effective stress set to 0, and the other parameters
are listed in Table 2. Exceptionally, the JST constant 𝜀(2) is set to 0.       maintained as 9.81 m/s2 in the drag force. To get the best accuracy

                                                                        8

### Page 9

D.S. Morikawa and M. Asai                                                                                                    Computers and Geotechnics 142 (2022) 104570

Fig. 9. Terzaghi consolidation problem: pressure profiles compared to the theoretical solution with 𝑘= 10−3 m∕s, 𝛥𝑡= 10−4 s (left) and 𝛥𝑡= 10−5 s (right) at T = 0.001, T = 0.01,
T = 0.05, T = 0.1, T = 0.2, T = 0.5 and T = 1.

possible, all boundary conditions are treated as essential boundary         Lastly, the upper stress of −10 kPa is applied at the free-surface
                                                                                 particles in the form of an acceleration
conditions. They are:
                                                                            10000
                                                                      𝑎1D = −                  ,                                             (67)
                                                                               𝑑(1 −𝑛)𝜌𝑠
      • 𝐯= 𝐯𝑤= 𝟎at the bottom;
      • 𝐯𝑤= 𝟎at the side walls (impermeable walls and no-slip condi-     in the 𝑦direction included in the predictor step of the soil linear
                                                     momentum equation, Eq. (46). As usual for this experiment, we present
      tion);
                                                                        the results in function of a dimensionless time parameter T, called time
      • 𝐯in the normal direction of the wall is zero at the side walls      factor, defined as

      (no-penetration);                                                𝑘𝑚v
                                                        T =            𝑡,                                                   (68)
      • 𝑝= 0 at the free-surface.                                        𝜌𝑤𝑔H2

                                                                        9

### Page 10

D.S. Morikawa and M. Asai                                                                                                    Computers and Geotechnics 142 (2022) 104570

Fig. 10. Terzaghi consolidation problem: pressure profiles compared to the theoretical solution with 𝑘= 10−4 m∕s, 𝛥𝑡= 10−4 s (left) and 𝛥𝑡= 10−5 s (right) at T = 0.001, T =
0.01, T = 0.05, T = 0.1, T = 0.2, T = 0.5 and T = 1.

where                                                                     Next, we show an analysis of the sensitivity of the proposed method
       𝐸(1 −𝜈)                                                             in relation to the time increment 𝛥𝑡and permeability 𝑘. Figs. 9 and 10
                                   ,                                            (69)𝑚v =                                                           show the pressure profiles for different times comparing the ‘‘drag force      (1 + 𝜈)(1 −2𝜈)
                                                                                          explicit’’ (as in Eq. (19)), ‘‘drag force predictor-implicit’’ (as in Eq. (21))
is the constrained modulus and H the height of the specimen.
                                                              and ‘‘drag force implicit’’ (proposed method) schemes, as explained in
    Fig. 7 shows some snapshots of this numerical test and Fig. 8 the     Section 3.
average stress values as a function of time at the second layer of     We hypothesize that the accuracy and stability of the method is
particles from bottom to top. From Fig. 8, it is possible to conclude that     directly linked to the scalar multipliers of the drag force, here denoted
the pressure dissipation followed by the effective stress increase acts     as 𝑎and 𝑏in Eq. (20), especially for the ‘‘drag force explicit’’ case.
almost exactly the same as the theory demands, that is, the total stress     Supporting this idea, for example, the solutions with the ‘‘drag force
𝜎′𝑦𝑦−𝑝is maintained as the applied vertical stress (−10 kPa) throughout      explicit’’ scheme are accurate for 𝑘= 10−3 m∕s and 𝑑𝑡= 10−4  s,
the whole process.                                               where both parameters are lower than 1 (𝑎= 0.0476 and 𝑏= 0.294),

                                                                        10

### Page 11

D.S. Morikawa and M. Asai                                                                                                    Computers and Geotechnics 142 (2022) 104570

                                                   Fig. 11. Triaxial compression: (a) boundary conditions and (b) particle model.

                                                                                Table 1
                                                                                           Material and numerical parameters of the hydrostatic test.

                                                                                     Parameter                           Symbol                 Value

                                                                                      Young’s modulus                𝐸                   10 MPa
                                                                                                 Poisson’s ratio                             𝜈                        0.3
                                                                                                       Soil density                                   𝜌𝑠                   2800 kg/m3
                                                                                     Cohesion                                     𝑐                    0
                                                                                                   Friction angle                    𝜙                      30◦
                                                                                            Dilatancy angle                   𝜓                        0◦
                                                                                                                 Initial porosity                              𝑛0                       0.3
                                                                                 Water density                         𝜌𝑤                   1000 kg/m3
                                                                                           Permeability                         𝑘                        10−3 m∕s
                                                                             Time increment                           𝛥𝑡                        10−5 s
                                                                                                      Particle size                          𝑑                       0.01 m
                                                                                                      Iterations at initial state                              Iinit                  1000
                                                                                                Constitutive model                                       Mohr–Coulomb

                                                                                Table 2
                                                                                           Material and numerical parameters of the Terzaghi consolidation test.

                                                                                     Parameter                         Symbol                    Value
Fig. 12. Triaxial compression: elements to define the velocity of lateral ghost particles.        Particle diameter                    𝑑                          0.01 m
                                                                                      Young’s modulus               𝐸                      10 MPa
                                                                                                 Poisson’s ratio                           𝜈                           0.3
                                                                                                       Soil density                                 𝜌𝑠                      2650 kg/m3
while it diverges the solution for 𝑘= 10−4 m∕s and 𝑑𝑡= 10−4 s, since         Initial porosity                            𝑛0                           0.3
𝑏= 2.943 > 1.                                                                   Water density                        𝜌𝑤                      1000 kg/m3
   Between the  three time  integration methods, the  ‘‘drag  force        Permeability                        𝑘                            10−3 m∕s
predictor-implicit’’ seems to be the most influenced by this constraint        Constitutive model                                                 Purely elastic
in terms of accuracy, given that the only solution with comparable
accuracy was the one with 𝑘= 10−3 m∕s and 𝑑𝑡= 10−5 s (𝑎= 0.0048
and 𝑏= 0.0294). On the other hand, it solves the problem present in
                                                                             that the ‘‘drag force implicit’’ integration scheme was the most robust
the ‘‘drag force explicit’’ scheme of having the numerical test being
                                                        among them, leading to accurate solutions for all pairs of 𝛥𝑡and 𝑘.diverged, as it can be seen in the simulation with 𝑘= 10−4 m∕s and
𝑑𝑡= 10−4 s (𝑎= 0.48 and 𝑏=  2.943). It is important to mention
that (Kularathna et al., 2021) was able to have very accurate solutions     8.3. Triaxial compression
with the ‘‘drag force predictor-implicit’’ time integration scheme, which
might be due to the their fractional-step algorithm or other specificity       The triaxial compression test  is a classical physical experiment
in their MPM formulation. Finally, with this example we demonstrated     widely used in Soil Mechanics. A few studies such as Pereira et al.

                                                                        11

### Page 12

D.S. Morikawa and M. Asai                                                                                                    Computers and Geotechnics 142 (2022) 104570

Fig. 13. Triaxial compression, CD-L: snapshots of the resulting numerical simulation showing the von Mises stress at the outer surface and centered cross section at half-way to
start yielding (a), right after yielding (b) and closest point to CSL (c) (left) and graphical representation of the (𝑝′, 𝑞) and (ln𝑝′, 𝑣) spaces (right).

(2017) and Zhao et al. (2019) have successfully used SPH to simulate    where 𝐯out is the velocity of the closest specimen particle to the virtual
it. The former used Drucker–Prager and the latter, Mohr–Coulomb    marker as represented in Fig. 12, and the second term is the SPH
yield criteria. Here we selected the modified Cam–Clay, as it is greatly     approximation (Eq. (36)) only at the soil specimen particles corrected
considered appropriate for this problem. In addition, both Pereira et al.     for the absence of a complete kernel. The proportion parameter 𝛾was
(2017), Zhao et al. (2019) have considered an uncoupled problem,     incorporated based on the fact that using exclusively 𝐯out makes the
which means that their solutions resemble the drained condition. In     simulation unstable, while using only the average velocity results in
this work, we devote special attention on using the proposed method    an additional strong stiffness in the lateral boundary. From experience,
to simulate both drained and undrained conditions.               𝛾= 0.8 resulted in the best solutions.
    Fig. 11a shows the boundary conditions for the triaxial test. The        In addition to the definitions on Fig. 11a, we selected a very
main difficulty in simulating this problem with SPH  is the lateral     large value of permeability 𝑘for drained and very low for undrained
                                                                         conditions to adapt our simulation to these conditions. However, theboundary condition, which can move sideways freely while maintain-
                                                                   undrained condition leads to a situation where there is no Dirichleting a constant confining pressure. Both Pereira et al. (2017), Zhao et al.
                                                                        condition on pressure, which makes the PPE to not converge. To fix(2019) simulated this condition with additional forces applied to the
                                                                                   that, we assign zero pressure to the outermost layer of lateral ghostSPH particles representing the specimen itself. As shown in Fig. 11b,
                                                                                    particles. As of the initial configuration, we started the simulation with
we chose to use ghost particles to simulate all boundary conditions,
                                                                                            all particles with 𝝈′ =  𝑝′0𝐈, zero pressure and velocity and slightlysince it is easier to arrange the conditions on the water phase.
                                                                randomly distributed particles (as in Fig. 11). Similarly to the previous
   In short, the ghost particles at the bottom are stationary while
                                                                    example, gravity is neglected.
those at the top have a constant velocity 𝑣0 =  −0.1 m∕s at the                                                                        Table 3 summarizes the parameters adopted in this simulation. The
vertical direction. The lateral ghost particles, on the other hand, are
                                                                 specimen is a cylinder with 0.06 m of diameter and 0.15 m height.
assigned with a virtual marker located at the interface between the
                                                           To facilitate the notation, we are going to refer to CD as the drained
SPH specimen particles and the ghost particles, as shown in Fig. 12.
                                                              and CU as the undrained tests. L represents lightly consolidated and
Then, its effective stress is kept constant as 𝝈′ = 𝑝′0𝐈, and its velocity is    H, highly consolidated. Figs. 13–16 show the graphical results of the
determined as                                                                             (𝑝′, 𝑞) and (ln 𝑝′, 𝑣) spaces and the simulations at three different stages:
                                                                                (a) half-way to start yielding, (b) right after yielding and (c) the closest
                            𝑚𝑗              ∑𝑁𝑠
                       𝑗=1                        𝜌𝑗𝐯𝑗𝑊(𝐫𝑖𝑗, ℎ)                                     point to the critical state line. The stresses and specific volume (𝑣=
𝐯g = 𝛾𝐯out + (1 −𝛾) ∑𝑁𝑠  𝑚𝑗                   ,                           (70)    1 + 𝑛∕(1 −𝑛)) are taken as the average of the particles located in
                        𝑗=1 𝜌𝑗𝑊(𝐫𝑖𝑗, ℎ)                                     the mid of the specimen (as in Fig. 11b). Notice that 𝑝′ is calculated

                                                                        12

### Page 13

D.S. Morikawa and M. Asai                                                                                                    Computers and Geotechnics 142 (2022) 104570

Fig. 14. Triaxial compression, CD-H: snapshots of the resulting numerical simulation showing the von Mises stress at the outer surface and centered cross section at half-way to
start yielding (a), right after yielding (b) and closest point to CSL (c) (left) and graphical representation of the (𝑝′, 𝑞) and (ln𝑝′, 𝑣) spaces (right).

as positive for tension (as in algorithm Appendix B) but exhibited as     Table 3
positive for compression to show it in the most familiar representation      Material and numerical parameters of the triaxial compression test.
                                                                                     Parameter                                   Symbol    Value
in the Geomechanics community.
                                                                                                      Particle size                                  𝑑          0.002 m
   As expected, the proposed method results are reasonable in compar-                                                                             Time increment                                    𝛥𝑡          10−6 s
ison with the theoretical solution for the stress path, that is, following       Gradient of swelling line                       𝜅          0.05
a straight line with slope of 1:3 (𝑝′ ∶𝑞) for CD, while being a straight       Gradient of the normal consolidation line         𝜆           0.2
                                                                                                 Poisson’s ratio                                      𝜈           0.3
vertical line at the (𝑝′, 𝑞) space before yielding for CU. In addition, it is
                                                                                                       Soil density                                             𝜌𝑠        3000 kg/m3
possible to conclude that the water pressure 𝑝also behaves naturally,         Initial porosity                                        𝑛0          0.5
being almost null for CD and absorbing the stresses that were not       Water density                                 𝜌𝑤        1000 kg/m3
contained in 𝑝′ for CU.                                                            Drained permeability                          𝑘           10−1 m∕s
                                                                                   Undrained permeability                        𝑘           10−8 m∕s
   Solutions were also very close to the theoretical solution for the         Initial pre-consolidation pressure                      𝑝𝑐        600 kPa
(ln 𝑝′, 𝑣) space, following the swelling line before yielding for CD and       Confining pressure for lightly consolidated soil      𝑝′0        400 kPa
                                                                                         Confining pressure for highly consolidated soil      𝑝′0        100 kPabeing basically incompressible for CU. For completeness, we plot the
                                                                                                Constitutive model                                          Modified Cam–Clay
stress–strain curves of our simulations in Fig. 17, which also shows
reasonable solutions, approaching a horizontal line once it reaches the
critical state line (CSL).
                                                                                 8.4. Slope failure with Selborne experiment
    All results in this section were obtained with a particle size of
𝑑= 0.002 m. As a simple analysis of the convergence of the proposed
method in relation to particle size, we conducted the CD-H numerical        This final numerical example  is to show an application to the
experiment for four different particle resolutions: 0.01, 0.005, 0.002    proposed method in a realistic scale. Here, we reproduce the Selborne
and 0.001 m. Fig. 18 shows these results in the  (𝑝′, 𝑞) space. As     experiment (Bromhead et  al., 1998; Cooper et  al., 1998) using the
expected, the numerical results approach the theoretical solution as    Mohr–Coulomb constitutive model with softening linearly dependent
particle size decreases.                                          on accumulated plastic strain. The geometry is illustrated in Fig. 19 and
   The only major problem was a divergence of the solution once it     the parameters are summarized in Table 4 (values of porosity, Poisson’s
approaches the CSL, which might be due to unsatisfactory boundary     ratio and density are taken as usual values for clay). From the on-site
conditions. Although not perfect, we consider that the proposed method     investigations, Cooper et al. (1998) have identified four strata of soil, as
was successful in reproducing the triaxial compression test.             shown in Fig. 19a. Given the deformation pattern from the experiment,

                                                                        13

### Page 14

D.S. Morikawa and M. Asai                                                                                                    Computers and Geotechnics 142 (2022) 104570

Fig. 15. Triaxial compression, CU-L: snapshots of the resulting numerical simulation showing the von Mises stress at the outer surface and centered cross section at half-way to
start yielding (a), right after yielding (b) and closest point to CSL (c) (left) and graphical representation of the (𝑝′, 𝑞) and (ln𝑝′, 𝑣) spaces (right).

we decided to model this problem using only the three upper layers as     Table 4
indicated in Fig. 19b and c.                                                          Material and numerical parameters of the slope failure test.
                                                                                     Parameter                            Symbol                Value
    Initially, the slope had a smooth inclination as shown in Fig. 19a
and it was later excavated to a 1:2 inclination. To approximate the       General parameters
                                                                                                      Particle size                           𝑑                       0.5 m
initial condition on the effective stress, we conducted the initial steps      Time increment                            𝛥𝑡                       10−3 s
(algorithm 2) including the excavated material shown in Fig. 19. Then,        Iterations at initial state                               Iinit                  2000
before starting the main loop, the excavated material is removed from       Water density                          𝜌𝑤                  1000 kg/m3
                                                                                      Young’s modulus                 𝐸                   20 MPa
the simulated domain.
                                                                                                 Poisson’s ratio                             𝜈                       0.4
   Cooper et al. (1998) induced the slope failure through a recharge        Soil density                                    𝜌𝑠                   2000 kg/m3
system that increased the pore pressure deep beneath the slope, as         Initial porosity                               𝑛0                      0.5
illustrated in Fig. 20a. The experiment lasted approximately 200 days,       Permeability                          𝑘                        10−8 m/s
                                                                                            Dilatancy angle                   𝜓                       0◦
and they induced pore pressures of 𝑝0 = 30 kPa, 𝑝0 = 42.5 kPa, 𝑝0 =        Constitutive model                                       Mohr–Coulomb
53.5 kPa and 𝑝0 = 70 kPa, when it finally failed.                                   Soliflucted clay
   Based on Fig. 20a, we implemented the essential boundary condi-       Peak cohesion                                𝑐                   5 kPa
tions as illustrated in Fig. 20b, where 𝑝0 represents the pore pressure       Residual cohesion                                  𝑐r                   0
                                                                                                   Friction angle                     𝜙                      21◦induced in the experiment. In addition, the slope site was laterally
isolated by low-friction panels to mimic a 2D problem. Hence, we      Weathered gault clay
                                                                                 Peak cohesion                                𝑐                   10 kPa
modeled the boundary conditions on the furthermost lateral particles
                                                                                           Residual cohesion                                  𝑐r                   0
in a Dirichlet manner, enforcing 𝐯and 𝐯𝑤in the 𝑧direction as zero.           Friction angle                     𝜙                      24◦
    First, we checked the capability of the proposed method to induce      Unweathered gault clay
the slope failure at the given 𝑝0 = 70 kPa while predicting no failure for       Peak cohesion                                𝑐                   25 kPa
the smaller values. Fig. 21 shows the simulation results at 𝑡= 50 s for       Residual cohesion                                  𝑐r                   0
                                                                                                   Friction angle                     𝜙                      26◦
three cases: dry soil, saturated soil with 𝑝0 = 53.5 kPa and saturated soil
with 𝑝0 = 70 kPa. As expected, slope failure was induced for the later.
For the dry case, basically no plastic deformations were found, while
for 𝑝0 = 53.5 kPa, one can see some plastic deformation at the interface           It is very complicated to validate our results comparing it with the
of the induced pressure zone, but not enough to cause a catastrophic     observed soil behavior in a quantitatively manner. Instead, we show
failure.                                                      some qualitative comparisons in Figs. 22 and 23.

                                                                        14

### Page 15

D.S. Morikawa and M. Asai                                                                                                    Computers and Geotechnics 142 (2022) 104570

Fig. 16. Triaxial compression, CU-H: snapshots of the resulting numerical simulation showing the von Mises stress at the outer surface and centered cross section at half-way to
start yielding (a), right after yielding (b) and closest point to CSL (c) (left) and graphical representation of the (𝑝′, 𝑞) and (ln𝑝′, 𝑣) spaces (right).

                                                                                                Fig. 18. Triaxial compression: graphical representation of the  (𝑝′, 𝑞) space with a
                                                                                  comparison of different particle sizes (particle sizes in m).

Fig. 17. Triaxial compression: graph  of the  stress–strain curve  for  all numerical     line at the right-side of the contour. Since the observed slip surface in
simulations (𝑑= 0.002 m).                                                    the experiment is not a perfectly precise data and that its shape varies
                                                              due to many uncertainties, we conclude that our simulation is able to
                                                                      reasonably predict this feature.
   In Fig. 22, the observed slip surface is plotted over our numerical        Next, Fig. 23 shows a picture taken after the slope collapse and
simulations with colors indicating the accumulated plastic strain. The     the 3D view of our numerical solution. In the picture, Fig. 23a, it is
slip surfaces roughly coincide, although the observed one shows a more     possible to see that the soil mass slipped over the slip surface while the
rounded and compact shape. In the numerical case, the slip surface    upper part roughly maintained its original shape. Similarly, as shown in
follows the interface between the tougher unweathered gault clay layer     Fig. 23b, our final numerical solutions with 𝑝0 = 70 kPa can be divided
and weaker weathered gault clay, which causes the seemingly straight     into three types: undeformed particles (I), particles with high plastic

                                                                        15

### Page 16

D.S. Morikawa and M. Asai                                                                                                    Computers and Geotechnics 142 (2022) 104570

                                                                                                Fig. 21. Slope failure test: comparison between different induced pressure boundary
                                                                                            conditions showing the accumulated plastic strain. Simulations at 𝑡= 50 s.

Fig. 19. Slope failure test: (a) actual cross section of the Selborne experiment as shown
in Cooper et al. (1998) and the SPH particle model in (b) 2D and (c) 3D views (lengths
in m).

                                                                                                Fig. 22. Slope failure  test: comparison between the interpreted  slip surface found
                                                                                                 in Cooper et al. (1998) and the accumulated plastic strain at time 𝑡= 11.5 s (𝑝0 = 70 kPa
                                                                                                    case).

Fig. 20. Slope failure  test: (a) Pore pressure recharge system as shown in Cooper
et al. (1998) and (b) Dirichlet boundary conditions imposed in the SPH particle model
(lengths in m).

deformation (II) and carried particles with low plastic deformation (III).
Again, it is very complicated to accurately state in what degree our
numerical solution follows the results found in Cooper et al. (1998).
However, we believe that the resemblance presented in Fig. 23 is a fair
evidence of the robustness of our proposed method.
   For completeness, Fig. 24 shows some screenshots of our numerical
simulation with 𝑝0 = 70 kPa at several time steps. Pressure and vertical
stress distributions seems to be fairly stable and smooth. The simulation
extended up to 100 s, and there were no major modifications except for
some numerical error accumulation.

9. Conclusion

   This paper presents a novel strong coupling technique for the 𝐮−
𝐰−𝑝formulation based on an one point–two phases ISPH method for
                                                                                                Fig. 23. Slope failure test: (a) picture of the slope after collapse (Bromhead et al.,
Geomechanics problems. The starting point is Biot’s formulation (Biot,     1998) and (b) the SPH particle distribution at 𝑡= 50 s, where the white particles (I)
1956) as explained in Zienkiewicz et  al. (1999). Then, we further      represent the undeformed area, dark brown (II), particles with 𝜖𝑝≥0.1 and light brown
increase Mathematical consistency applying the complete incompress-        (III), carried particles with 𝜖𝑝< 0.1 (𝑝0 = 70 kPa case).
ibility constraint on soil grains and pore water.
   The formulation is then adapted to the ISPH projection scheme,
resulting in a semi-implicit technique with strong coupling between soil     while natural boundary conditions are applied in the form of velocity
and water phases. Darcy’s drag force is updated implicitly to avoid large
                                                                               constraints, which include both non-penetration and friction effects.
restrictions on time increment due to small values of permeability. We
propose a simple yet robust boundary condition treatment where es-     We verified the strong coupling technique with hydrostatic and
sential boundary conditions are simply enforced in a Dirichlet manner,    1D Terzaghi consolidation. For both problems, we show exceptional

                                                                        16

### Page 17

D.S. Morikawa and M. Asai                                                                                                    Computers and Geotechnics 142 (2022) 104570

Fig. 24. Slope failure test: screenshots of the numerical simulation showing pressure, accumulated plastic strain and vertical stress at (a) 𝑡= 0 s, (b) 𝑡= 10 s, (c) 𝑡= 11.5 s and
(d) 𝑡= 50 s (𝑝0 = 70 kPa case).

agreement with the theoretical values in terms of pressure profile    Declaration of competing interest
as a function of height and pressure stability over time. Also, we
demonstrated the capability of the proposed ‘‘drag force implicit’’ time       The authors declare that they have no known competing finanintegration of relieving the dependency of time increment in relation      cial interests or personal relationships that could have appeared to
to the permeability.                                                       influence the work reported in this paper.
   Next, we demonstrated that our proposed method can simulate the
triaxial compression test with the modified Cam–Clay yield criterion                                                          Acknowledgments
in both drained and undrained conditions for lightly and highly consolidated soils. The authors are unaware of any application of SPH
                                                                The first author is supported by the Japan Society for the Promotion
soil–water coupling that can reproduce this problem at both drained
                                                                              of Science (JSPS) through the Research Fellowship for Young Scientists.
and undrained conditions with this degree of fidelity.
                                                                           This work was supported by the Japan Society for the Promotion
    Finally, we show the robustness of our proposed method with a
                                                                              of Science (JSPS) KAKENHI Grant Number 20J13114, JP-20H02418,
numerical test based on the well-known Selborne experiment. We could
                                                             19H01098, and 19H00812. We also received computational environmodel this experiment in a way that the slope failure occur at the
                                                            ment support through the Joint Usage/Research Center for Interdisdesignated pore pressure induced in the experiment (𝑝0 = 70 kPa),     ciplinary Large-scale Information Infrastructures (JHPCN) in Japan
while maintaining  its stability for the second highest value (𝑝0 =     (Project ID: jh200034-NAH and jh200015-NAH).
53.5 kPa). Then, we compared the shape of the slip surface and a 3D
view of the failed soil mass with those obtained in the experiment, and
                                                            Appendix A. Mohr–coulomb
we concluded that we could reasonably resemble what was observed.
It  is important to emphasize that this  is not a rigorous validation
test, since the exact conditions on the experiment are not given in a       Here we show the Mohr–Coulomb constitutive model with linear
way that we could implement directly in the method. Hence, some     hardening rule on the cohesion variable. It is defined in terms of the
model parameters and geometries had to be estimated, which might     principal stresses
contribute to some degree of uncertainties. However, we consider that   ∑3
the simulation was successful, since our results were meaningful in a     𝝈′ =    𝜎𝑖𝐞𝑖⊗𝐞𝑖,                                               (71)
qualitative way.                                                                             𝑖=1
   As for future works, we intend to apply this method for more    and the plastic parameters are 𝑐(varying from initial 𝑐0 to residual 𝑐r
complex problems, which takes into account more complicated soil     values), 𝜙and 𝜓. Yield function and flow rule are shown as follows.
behavior such as soil under earthquake, liquefaction and so on. For the
                                                                                                                      • Yield functiondevelopment of the method itself, we aim to expand its formulation to
contemplate unsaturated soil behavior as well, which would allow us to                                             𝜑= (𝜎1 −𝜎3) −(𝜎1 + 𝜎3) sin 𝜙−2𝑐cos 𝜙                     (72)
simulate the water infiltration process, scouring and piping, as well as
more realistic estimation of soil strength under a variety of scenarios.              • Flow rule

                                          𝛹= (𝜎1 −𝜎3) −(𝜎1 + 𝜎3) sin 𝜓−2𝑐cos 𝜓                     (73)
CRediT authorship contribution statement
                                                                                                                      • Hardening rule (linear hardening on cohesion)

   Daniel S. Morikawa: Conceptualization, Methodology, Software,       𝑐= 𝑐0 + 𝐻𝜖𝑝≥𝑐r                                          (74)
Formal analysis, Investigation, Resources, Data curation, Writing –
original draft, Writing – review & editing, Visualization, Project admin-        In Eq. (74), 𝜖𝑝refers to plastic strain and 𝐻is the hardening
istration, Funding acquisition. Mitsuteru Asai: Methodology, Software,     coefficient (𝐻negative for softening). The implementation of Mohr–
Formal analysis, Resources, Data curation, Writing – review & editing,    Coulomb is slightly more complicated than Drucker–Prager, as it reSupervision, Project administration, Funding acquisition.                   quires to check four different possibilities of return mapping: main

                                                                        17

### Page 18

D.S. Morikawa and M. Asai                                                                                                    Computers and Geotechnics 142 (2022) 104570

plane, right edge, left edge and apex. To simplify the notation, let us    Algorithm 4 Mohr–Coulomb return map
define
                                                                      Input:  𝝈′trial
          1
𝐴= 4𝜇(1 +               sin 𝜙sin 𝜓) + 4𝐾sin 𝜙sin 𝜓,                         (75)    Output: 𝝈′𝛽+1
          3
                                                                              Spectral decomposition
and                                                                                   Trial state: 𝜖trial𝑝  = 𝜖𝛽𝑝and 𝑐trial = 𝑐0 + 𝐻𝜖trial𝑝   ≥𝑐r
𝐵= 2𝜇(1 + sin 𝜙+ sin 𝜓−1 sin 𝜙sin 𝜓) + 4𝐾sin 𝜙sin 𝜓,            (76)       Calculate trial yield function 𝜑trial = 𝜑(𝜎′trial) with Eq. (72)
                       3                                                                                                      if 𝜑trial ≤0 then
or                                                                                       Elastic deformation: 𝝈′𝛽+1 = 𝝈′trial
                                                                            else𝐵= 2𝜇(1 −sin 𝜙−sin 𝜓−1 sin 𝜙sin 𝜓) + 4𝐾sin 𝜙sin 𝜓,            (77)
                       3                                                            Plastic deformation:
depending on the case, and                                                           (a) 𝝈′𝛽+1 is on the main plane of 𝜑
                                                        𝛥𝛾= 𝜑trial∕(𝐴+ 4𝐻cos2 𝜙)
̃𝜑(𝑓1, 𝑓2) = (𝑓1 −𝑓2) −(𝑓1 + 𝑓2) sin 𝜙−2𝑐cos 𝜙,                    (78)                    𝜎(𝑎)                                                                                                        1 = 𝜎trial1   −(2𝜇(1 + 13 sin 𝜓) + 2𝐾sin 𝜓)𝛥𝛾
for generic variables 𝑓1 and 𝑓2.                                                                   𝜎(𝑎)2 = 𝜎trial2  + ( 43𝜇−2𝐾) sin 𝜓𝛥𝛾
   Algorithm 4 summarizes its implementation.                                               𝜎(𝑎)                                                                                                        3 = 𝜎trial3  + (2𝜇(1 −13 sin 𝜓) −2𝐾sin 𝜓)𝛥𝛾
                                                                                                                             𝜖trial𝑝  = 𝜖𝛽𝑝+ 2 cos 𝜙𝛥𝛾Appendix B. Modified Cam–Clay
                                                                   Check (a): if 𝜎(𝑎)1  ≥𝜎(𝑎)2  ≥𝜎(𝑎)3  then
   The modified Cam–Clay model (MCC) is a yield criterion based on                              𝜎𝛽+1𝑖  = 𝜎(𝑎)𝑖  and go to (d)
critical state Soil Mechanics. As opposed to other classical models such            (b) if (1 −sin 𝜓)𝜎trial1   −2𝜎trial3  + (1 + sin 𝜓)𝜎trial2  > 0 then
as Mohr–Coulomb or Drucker–Prager, the MCC set equations not only                    𝝈′𝛽+1 is on the right edge of 𝜑(𝐵from Eq. (76))
for the stress–strain relationship, but also for the overall density of the                     ⎧
                                                                             ⎪(𝐴+ 4𝐻cos2 𝜙)𝛥𝛾1 + (𝐵+ 4𝐻cos2 𝜙)𝛥𝛾2 = ̃𝜑(𝜎trial1    , 𝜎trial3   )
material, here represented by the specific volume 𝑣= 1+𝑒= 1+𝑛∕(1−𝑛).                    Solve: ⎨
                                                                            (𝐵+ 4𝐻cos2 𝜙)𝛥𝛾1 + (𝐴+ 4𝐻cos2 𝜙)𝛥𝛾2 = ̃𝜑(𝜎trial1    , 𝜎trial2   )The two main variables related to the stress response of the material are                                          ⎪⎩
the mean effective stress                                                                                  𝜎(𝑏)                                                                                                             1 = 𝜎trial1   −((2𝜇(1 + 13 sin 𝜓) + 2𝐾sin 𝜓)(𝛥𝛾1 + 𝛥𝛾2)
     𝜎′𝑥𝑥+ 𝜎′𝑦𝑦+ 𝜎′𝑧𝑧                                                                                         𝜎(𝑏)2  =  𝜎trial2  + ( 43𝜇−2𝐾) sin 𝜓𝛥𝛾1 + (2𝜇(1 −13 sin 𝜓) −𝑝′ =                            ,                                            (79)
          3                                                      2𝐾sin 𝜓)𝛥𝛾2
                                                                                                                 𝜎(𝑏)and the von Mises stress                                                                                                              3  =  𝜎trial3  + (2𝜇(1 −13 sin 𝜓) −2𝐾sin 𝜓)𝛥𝛾1 + ( 43 𝜇−
  √                                                         2𝐾) sin 𝜓𝛥𝛾2
      1
𝑞=     3𝐬∶𝐬,                                                   (80)                else𝝈′𝛽+1 is on the left edge of 𝜑(𝐵from Eq. (77))
where s is the deviatoric effective stress tensor                                        ⎧
                                                                             ⎪(𝐴+ 4𝐻cos2 𝜙)𝛥𝛾1 + (𝐵+ 4𝐻cos2 𝜙)𝛥𝛾2 = ̃𝜑(𝜎trial1    , 𝜎trial3   )
                                                                                           Solve: ⎨𝐬= 𝝈′ −𝑝′𝐈.                                                    (81)
                                                                                                                                                          ⎪⎩(𝐵+ 4𝐻cos2 𝜙)𝛥𝛾1 + (𝐴+ 4𝐻cos2 𝜙)𝛥𝛾2 = ̃𝜑(𝜎trial2    , 𝜎trial3   )
   This constitutive model is based on an associative yield criterion                         𝜎(𝑏)                                                                                                              1  =  𝜎trial1   −(2𝜇(1 + 13 sin 𝜓) + 2𝐾sin 𝜓)𝛥𝛾1 + ( 43 𝜇−
that depends on the pre-consolidation pressure 𝑝𝑐and a parameter 𝑀,      2𝐾) sin 𝜓𝛥𝛾2
which, for the triaxial compression case, is 𝑀= 6 sin 𝜙∕(3 −sin 𝜙).                                 𝜎trial                                                                                                             2  +( 43𝜇−2𝐾) sin 𝜓𝛥𝛾1 −(2𝜇(1+ 13 sin 𝜓)+2𝐾sin 𝜓)𝛥𝛾2

      • Yield function and flow rule (associative flow rule)                                          𝜎(𝑏)                                                                                                             3 = 𝜎trial3  + ((2𝜇(1 −13 sin 𝜓) −2𝐾sin 𝜓)(𝛥𝛾1 + 𝛥𝛾2)
   𝜑= 𝛹= 𝑝′2 + 𝑝𝑐𝑝′ + (𝑞∕𝑀)2                                (82)            end if
                                                                                                                             𝜖trial𝑝  = 𝜖𝛽𝑝+ 2 cos 𝜙(𝛥𝛾1 + 𝛥𝛾2)
      • Hardening rule                                                                   Check (b): if 𝜎(𝑏)1  ≥𝜎(𝑏)2  ≥𝜎(𝑏)3  then
             𝑣      𝜕𝑝𝑐                                                                                                 𝜎𝛽+1𝑖  = 𝜎(𝑏)𝑖  and go to (d)       =                                                               (83)      𝜕𝜖𝑝𝑣   𝜆−𝜅𝑝𝑐                                                                     (c) 𝝈′𝛽+1 is on the apex of 𝜑
                                                        𝛥𝛾= sin 𝜙(𝑝′trial −𝑐cot 𝜙)∕(sin 𝜙𝐾+ 𝐻cos 𝜙cot 𝜙)
  𝜆and 𝜅are the gradient of the normal consolidation line (NCL) and
                                                                                                            𝜎(𝑐)                                                                                                        1 = 𝜎(𝑐)2 = 𝜎(𝑐)3 = 𝑝′trial −𝐾𝛥𝛾the swelling line, respectively. 𝜅is also important to define the bulk
modulus 𝐾= (𝑣∕𝜅)𝑝′, which, unlike other models, is variable according                       𝜖trial𝑝  = 𝜖𝛽𝑝+ (cos 𝜙∕sin 𝜙)𝛥𝛾
to the mean effective stress 𝑝′ and specific volume 𝑣. 𝜖𝑝𝑣represents the               𝜎𝛽+1𝑖  = 𝜎(𝑐)𝑖  and go to (d)
volumetric plastic strain.                                                           (d) End of return map
   Given its complexity, we need to use a Newton–Raphson routine          Reassemble stress tensor (Eq. (71))
to accomplish the return mapping. The strategy is to use the Newton–      end if
Raphson algorithm to find the root of the functions                      Update plastic strain: 𝜖𝛽+1𝑝  = 𝜖trial𝑝

𝑅1 = 𝜑,                                                        (84)

and
                                                                    with the partial derivatives
𝑅2 = 𝛥𝜖𝑝𝑣+ 𝛥𝛾(2𝑝′ + 𝑝𝑐),                                         (85)
                                                               𝜕𝑅1       12𝜇   ( 𝑞 )2
using 𝛥𝛾and 𝛥𝜖𝑝𝑣as the target variables. That is, the routine stops if 𝑅1    𝜕𝛥𝛾= − 𝑀2 + 6𝜇𝛥𝛾 𝑀     ,                                     (87)
and 𝑅2 become smaller than a threshold 𝛿(𝛿= 10−7 in our simulations).
Hence, we need to find the inverse of the Jacobian

      𝜕𝑅1             𝜕𝑅1    ⎡               ⎤      𝜕𝛥𝛾    𝜕𝛥𝜖𝑝                    𝑣                                                                                        𝑣𝐉=    ⎢               ⎥                                               (86)     𝜕𝑅1      𝜕𝑅2             𝜕𝑅2                                                     = 2𝑝′𝐾+ 𝑝𝑐𝐾+        ⎢⎣                                                                                                                                  (88)      𝜕𝛥𝛾    𝜕𝛥𝜖𝑝𝑣 ⎥⎦                                                       𝜕𝛥𝜖𝑝𝑣              𝜆−𝜅𝑝′𝑝𝑐,

                                                                        18

### Page 19

D.S. Morikawa and M. Asai                                                                                                    Computers and Geotechnics 142 (2022) 104570

Algorithm 5 Modified Cam–Clay return map                                     Barcarolo,  D., Touzé,  D.L., de Vuyst,  F., 2014. Validation of a new  fully-explicit
                                                                                             incompressible smoothed  particle hydrodynamics method. Mech. Eng. Proc. 1,
Input:  𝝈′trial                                                                         http://dx.doi.org/10.5151/meceng-wccm2012-16774.
Output: 𝝈′𝛽+1                                                                                   Biot, M., 1956. Theory of propagation of elastic waves in a fluid-saturated porous solid.
  Retrieve 𝑝′trial and 𝑞trial with Eqs. (79), (80) and (81) and set 𝑝trial𝑐  =                i.1121/1.1908239.low-frequency range. J. Acoust. Soc. Am. 28–2, 168–178. http://dx.doi.org/10.
  𝑝𝛽𝑐                                                                                        Blanc,  T.,  Pastor, M., 2012. A  stabilized  fractional  step, runge–kutta  taylor SPH
  Calculate trial yield function 𝜑trial = 𝜑(𝜎′trial) eith Eq. (82)                     algorithm for coupled problems in geomechanics. Comput. Methods Appl. Mech.
   if 𝜑trial ≤0 then                                                                      Engrg. 221–222, 41–53. http://dx.doi.org/10.1016/j.cma.2012.02.006.
        Elastic deformation: 𝝈′𝛽+1 = 𝝈′trial                                         Bonet, J., Lok, T.-S., 1999. Variational and momentum preservation aspects of smoothed
                                                                                                         particle hydrodynamics formulations. Comput. Methods Appl. Mech. Engrg. 180,
  else                                                                               97–115. http://dx.doi.org/10.1016/S0045-7825(99)00051-1.
        Plastic deformation:                                                   Bromhead,  E., Cooper, M.,  Petley,  D., 1998. The selborne  cutting slope  stability
       (a) Preparing for the Newton–Raphson:                                    experiment (CD-ROM). Selborne Data Collect. CD.
           Set 𝑝0𝑐, 𝑝′0 and 𝑞0 with their trial states                                 Bui, inH.,geomechanics:Bguyen, G., 2021.fromSmoothedsolid fractureparticleto granularhydrodynamicsbehaviour(SPH)andandmultiphaseits applicationsflows
           Set k = 0, 𝛥𝛾= 0 and 𝛥𝜖𝑝𝑣= 0                                                  in porous media. Comput. Geotech. 138, 104315. http://dx.doi.org/10.1016/j.
       (b) Newton–Raphson:                                                      compgeo.2021.104315.
        do while (𝑒𝑟𝑟𝑜𝑟> 𝛿)                                                        Bui, H., Fukagawa, R., 2009. A first attempt to solve soil-water coupled problem by
               Calculate 𝑅k1, 𝑅k2 with Eqs. (84) and (85)                         Bui, SPH.H., Jpn.Fukagawa,Terramech.R., 2013.29, 33–38.An improved SPH method  for saturated  soils and
              Calculate the Jacobian Jk with Eqs. (86), (87), (88), (89)              its application to investigate the mechanisms of embankment  failure: Case of
  and (90)                                                                                    hydrostatic pore-water pressure. Int. J. Numer. Anal. Methods Geomech. 37, 31–50.
             (                      )k+1  (                                                                                             http://dx.doi.org/10.1002/nag.1084.                               𝛥𝛾                    𝛥𝛾                              )k      (𝑅1 )k              Solve       =        −(Jk)−1                                 Bui, H., Fukagawa, R., Sako, K., Ohno, S., 2008. Lagrangian meshfree particles method
                     𝛥𝜖𝑝𝑣         𝛥𝜖𝑝𝑣           𝑅2                           (SPH) for large deformation and failure flows of geomaterial using elastic–plastic
             Update 𝑝′, 𝑞and 𝑝𝑐:                                                                soil constitutive model. Int. J. Numer. Anal. Methods Geomech. 32, 1537–1570.
                𝑝′k+1 = 𝑝trial + 𝐾𝛥𝜖𝑝𝑣                                                     http://dx.doi.org/10.1002/nag.688.                 (  𝑀2  )                                                      Bui, H., Nguyen, G., 2017. A coupled fluid-solid SPH approach to modelling flow              𝑞k+1 =                𝑞trial
                      𝑀2+6𝜇𝛥𝛾                                                     through deformable porous media. Int. J. Solids Struct. 125, 244–264. http://dx.
              𝑝k+1𝑐  = 1−𝛥𝜖𝑝𝑝𝑐trial𝑣𝑣∕(𝜆−𝜅)                                                       Cascini,doi.org/10.1016/j.ijsolstr.2017.06.022.L., Cuomo, S., Pastor, M., Sorbini, G., Piciullo, L., 2014. SPH Run-out modelling                √
               Calculate error: 𝑒𝑟𝑟𝑜𝑟=   (𝑅k+11   )2 + (𝑅k+12   )2                           of channelised landslides of the flow type. Geomorphology 214, 502–513. http:
                                                                                           //dx.doi.org/10.1016/j.geomorph.2014.02.031.
            k = k + 1                                                                                      Cooper, M., Bromhead, E., Petley, D., Grant, D., 1998. The selborne cutting stability
        end do                                                                       experiment. Geotechnique 48, 83–101. http://dx.doi.org/10.1680/geot.1998.48.1.
        (c) Retrieve the effective stress tensor and pre-consolidation          83.
  pressure:                                                                 Cummins, S., Rudman, M., 1999. An SPH projection method. J. Comput. Phys. 152,
                                                                                     584–607.                                                                                                       http://dx.doi.org/10.1006/jcph.1999.6246.
                          𝑝trial            𝑝′𝛽+1 =               + 𝐾𝛥𝜖𝑝
                                                                                                                 R., Manzari,                                                                                                            M., 2011. Error estimation in smoothed particle hydrodynamics             (                    ) 𝑣                                                          Faheti,                 𝑀2           s𝛽+1 =                 strial                                               and a new scheme for second derivatives. Comput. Math. Appl. 61 (2), 482–498.                  𝑀2+6𝜇𝛥𝛾
           𝝈′𝛽+1 = s𝛽+1 + 𝑝′𝛽+1I                                                        http://dx.doi.org/10.1016/j.camwa.2010.11.028.
                                                                                                                     G., 2015.                                                                                      An hourglass                                                                                                                                    control                                                                                                                                   algorithm                                                                                                                                                                 for                                                                                                                                             Lagrangian                                                                                                                                          smooth                                                                                                                                                                                           particle
                                                                                       hydrodynamics.                                                                                                Comput.                                                                                                       Methods                                                                                                                              Appl. Mech.                                                                                                                                         Engrg.                                                                                                                                            286,                                                                                                                                           87–106.                                                                                                                                                                             http://dx.doi.           𝑝𝛽+1𝑐  = 1−𝛥𝜖𝑝𝑝𝑐trial𝑣𝑣∕(𝜆−𝜅)                                                     Ganzenmüller,
       (d) End of return map                                                         org/10.1016/j.cma.2014.12.005.
  end if                                                                               Gingold,  R., Monaghan,  J., 1977. Smoothed  particle hydrodynamics:  theory and
                                                                                                  application to non-spherical stars. Astron. Soc. 181, 375–389. http://dx.doi.org/
                                                                                       10.1093/mnras/181.3.375.
                                                                                      Khayyer, A., Gotoh, H., Shao,  S., 2008. Corrected incompressible SPH method for
                                                                                              accurate water-surface tracking in breaking waves. Coast. Eng. 55 (3), 236–250.
                                                                                               http://dx.doi.org/10.1016/j.coastaleng.2007.10.001.
𝜕𝑅2                                                                                   Koshizuka, S., Oka, Y., 1996. Moving-particle semi-implicit method for fragmentation
                                                                                                     of incompressible fluid. Nucl. Sci. Eng. 123, 421–434. http://dx.doi.org/10.13182/𝜕𝛥𝛾= 2𝑝′ + 𝑝𝑐,                                                 (89)
                                                                                NSE96-A24205.
                                                                                          Kularathna, S., Liang, W., Zhao, T., Chandra, B., Zhao,  J., Soga, K., 2021. A semi-
                                                                                                       implicit material point method based on fractional-stepmethod for saturated soil. 𝜕𝑅2       (       𝑣   )
                                                                                                                    Int.                                                                                                                        J. Numer.                                                                                                             Anal.                                                                                                   Methods                                                                                                         Geomech. http://dx.doi.org/10.1002/nag.3207.    = 1 + 𝛥𝛾 2𝐾+ 𝜆−𝜅𝑝𝑐   .                                  (90)𝜕𝛥𝜖𝑝𝑣                                                                                              Lee,                                                                                                     C.H.,                                                                                                                        Gil,  A.J.,                                                                                                                  Greto,                                                                                                                                     G., Kulasegaram,                                                                                                                                                                                  S., Bonet,  J., 2016. A new jameson-
   With all parameters defined, algorithm 5 present a straight forward          Schmidt-Turkel smooth particle hydrodynamics algorithm for large strain explicit
                                                                                                                fast dynamics. Comput. Methods Appl. Mech. Engrg. 311, 71–111. http://dx.doi.
methodology to conduct the return mapping using the modified Cam–
                                                                                          org/10.1016/j.cma.2016.07.033.
Clay. In algorithm 5, the letter k represents the internal iterations of the      Lian, Y., Bui, H., Bguyen, G., Tran, H., Haque, A., 2021. A general SPH framework for
Newton–Raphson routine. Again, readers interested in understanding           transient seepage flows through unsaturated porous media considering anisotropic
the details of this algorithm should refer to de Souza Neto et  al.           diffusion. Comput. Method Appl. Mech. Engrg. 387, 114169. http://dx.doi.org/10.
                                                                                       1016/j.cma.2021.114169.
(2008), Zienkiewicz et al. (1999) or other classical authors in this
                                                                                                    Lin, C., Pastor, M., Li, T., Liu, X., Lin, C., Qi, H., Sheng, T., 2019. A PFE/IE – SPH joint
subject.                                                                              approach to model landslides from initiation to propagation. Comput. Geotech. 114,
                                                                                    103153. http://dx.doi.org/10.1016/j.compgeo.2019.103153.
References                                                                           Lucy, L., 1977. A numerical approach to the testing of the fusion process. Astron. J.
                                                                                              82, 1013–1024. http://dx.doi.org/10.1086/112164.
                                                                              Maeda, K., Sakai, H., Sakai, M., 2004. Development of seepage failure analysis method
Asai, M., Aly, A., Sonoda, Y., Sakai, Y., 2012. A stabilized incompressible SPH method           of ground with smoothed particle hydrodynamics (in Japanese). J. Appl. Mech. 7,
   by relaxing the density invariance condition. J. Appl. Math. 2012, http://dx.doi.         775–786.
    org/10.1155/2012/139583.                                                    Maeda, K., Sakai, H., Sakai, M., 2006. Development of seepage failure analysis method
Asai, M., Li, Y., Chandra, B., Takase, S., 2021. Fluid–rigid-body interaction simulations           of ground with smoothed particle hydrodynamics. Struct. Eng./Earthq. Eng. 23 (2),
   and validations using a coupled stabilized ISPH–DEM incorporated with the energy-         307–319. http://dx.doi.org/10.2208/jsceseee.23.307s.
    tracking impulse method for multiple-body contacts. Comput. Methods Appl. Mech.     Monaghan, J., 1992. Smoothed particle hydrodynamics. Annu. Rev. Astron. Astrophys.
    Engrg. 377 (15), http://dx.doi.org/10.1016/j.cma.2021.113681.                            30, 543–574. http://dx.doi.org/10.1146/annurev.aa.30.090192.002551.
Bandara, S., Soga, K., 2015. Coupling of soil deformation and pore fluid flow using     Morikawa, D., Asai, M., 2021. Coupling total lagrangian SPH-EISPH for fluid-structure
    material point method. Comput. Geotech. 63, 199–214. http://dx.doi.org/10.1016/           interaction with large deformed hyperelastic solid bodies. Comput. Methods Appl.
    j.compgeo.2014.09.009.                                                           Mech. Engrg. 381, http://dx.doi.org/10.1016/j.cma.2021.113832.

                                                                        19

### Page 20

D.S. Morikawa and M. Asai                                                                                                    Computers and Geotechnics 142 (2022) 104570

Morikawa, D., Asai, M., Idris, N., Imoto, Y., Isshiki, M., 2019. Improvements in highly      Pozorski, J., Wawrenczuk, A., 2002. SPH Computation of incompressible viscous flows.
    viscous fluid simulation using a fully implicit SPH method. Comput. Part. Mech.            J. Theoret. Appl. Mech. 40, 917–937.
    6, 529–544. http://dx.doi.org/10.1007/s40571-019-00231-6.                           Randles, P., Libersky,  L., 1996. Smoothed particle hydrodynamics: some recent imMorikawa, D., Senadheera, H., Asai, M., 2021. Explicit incompressible smoothed particle         provements and applications. Comput. Methods Appl. Mech. Engrg. 139, 375–408.
    hydrodynamics in a multi-gpu environment for large-scale simulations. Comput.          http://dx.doi.org/10.1016/S0045-7825(96)01090-0.
    Part. Mech. 8, 493–510. http://dx.doi.org/10.1007/s40571-020-00347-0.              Schoenberg, I.J., 1964. Spline interpolation and best quadrature formulae. Bull. Amer.
Morris, J., Fox, P., Zhu, Y., 1997. Modeling low Reynolds number incompressible flows         Math. Soc. 70 (1), 143–148. http://dx.doi.org/10.1090/S0002-9904-1964-11054-5.
    using SPH. J. Comput. Phys. 136 (1), 214–226. http://dx.doi.org/10.1006/jcph.     de Souza Neto, E., Perić, D., Owen, D., 2008. Computational Methods for Plasticity:
    1997.5776.                                                                       Theory and Applications. John Wiley & Sons,  Ltd, http://dx.doi.org/10.1002/
Naili, M., Matsushima, T., Yamada, Y., 2005. A 2D smoothed particle hydrodynamics         9780470694626.
   method  for liquefaction induced  lateral spreading  analysis.  J. Appl. Mech.  8,      Zhao, S., Bui, H., Lemiale, V., Nguyen, G., Darve, F., 2019. A generic approach to
    591–599. http://dx.doi.org/10.2208/journalam.8.591.                                    modelling flexible confined boundary conditions in SPH and its application. Int. J.
Pastor, M., Blanc, T., Drempetic, V., Dutto, P., Stickle, M.M., Yague, A., 2015. Modelling         Numer. Anal. Methods Geomech. 43, 1005–1031. http://dx.doi.org/10.1002/nag.
    of landslides: and SPH approach. CMES 109-110 (2), 183–220. http://dx.doi.org/         2918.
    10.3970/cmes.2015.109.183.                                                           Zienkiewicz, O., Chan, A., Pastor, M., Schrefler, B., Shiomi, T., 1999. Computational
Pereira, G., Cleary,  P., Lemiale, V., 2017. SPH Method applied to compression of         Geomechanics with Special Reference to Earthquake Engineering. John Wiley &
    solid materials for a variety of loading conditions. Appl. Math. 44, 72–90. http:          Sons, Ltd.
    //dx.doi.org/10.1016/j.apm.2016.12.009.

                                                                        20
