# MCC

> Auto-converted from PDF for Codex/code-reference reading. Formatting, equations, figures, and tables may require checking against the original PDF.

- Source PDF: `MCC.pdf`
- Pages: 38

## Extracted Text

### Page 1

Available online at www.sciencedirect.com
                        ScienceDirect

                              Comput. Methods Appl. Mech. Engrg. 390 (2022) 114356
                                                                                                         www.elsevier.com/locate/cma

  An open-source unconstrained stress updating algorithm for the
                   modified Cam-clay model
        Xin Zhoua, Dechun Lua,∗, Yaning Zhanga, Xiuli Dua, Timon Rabczukb

 a Key Laboratory of Urban Security and Disaster Engineering of Ministry of Education, Beijing University of Technology, Beijing 100124, China
                              b Institute of Structural Mechanics, Bauhaus-Universität Weimar, Weimar 99423, Germany

                   Received 6 September 2021; received in revised form 10 November 2021; accepted 11 November 2021
                                                    Available online 30 November 2021

Abstract

   This paper presents an unconstrained stress updating algorithm for a critical state plastic model of clay soil, where the
loading/unloading estimations and the consideration of the stress behaviour transition from elasticity to plasticity can be
bypassed by using the Fischer–Burmeister smoothing function instead of the Kuhn–Tucker complementarity conditions. A
smoothing tangent operator consistent with the unconstrained stress updating strategy is derived from preserving the quadratic
convergence speed for the global solution. Specifically, the relationship and difference between the consistent and continuum
tangent operators are analysed from the perspectives of algebra and geometry. In addition, the nonlinear constitutive equations
obtained by the backward Euler integration scheme are solved by the double dogleg trust region method (improved by nonmonotonic technology), where a larger strain increment than that of the newton method is allowed for the stress updating.
Then, the modified Cam-clay model for soil is implemented in ABAQUS/Standard by the proposed algorithm. The results
of numerical examples show that the algorithm has significant advantages in terms of computation efficiency and robustness
in contrast to the ABAQUS/Standard default integration algorithm, especially for the condition of large load increments and
cyclic loadings. More than twice the computational efficiency of the ABAQUS/Standard default integration algorithm can be
observed in the representative numerical examples. The source code of the proposed algorithm is freely available at https://git
hub.com/zhouxin615/NMTR_Method.
© 2021 Elsevier B.V. All rights reserved.

Keywords: Constitutive model integration; Trust region method; Smoothing function; Modified Cam-clay model; Consistent tangent operator;
UMAT

1. Introduction

  As the landmark product for the development of critical state soil mechanics [1], the modified Cam clay (MCC)
model is one of the origins of numerous elastoplastic models for soil [2–5] and plays an essential role in the
numerical analysis of geotechnical engineering problems [6]. Accordingly, the stress updating algorithm serving
used for numerical implementations of the MCC model has always been considered [7–9], as it provides a crucial
tool for local calculations in finite element analysis.

  ∗Corresponding author.
    E-mail address:  dechun@bjut.edu.cn (D. Lu).

https://doi.org/10.1016/j.cma.2021.114356
0045-7825/© 2021 Elsevier B.V. All rights reserved.

### Page 2

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

  Due to the presence of the plastic deformation mechanism of soil, the MCC model is presented in the form of rate
constitutive equations that are constrained by Kuhn–Tucker (KT) complementary conditions, where the deformation
behaviour of the material is constrained by the loading/unloading inequality. During the stress updating process,
the rate constitutive equations are first discretized into nonlinear algebraic equations in time by certain integration
schemes, e.g., the forward Euler approach, modified Euler approach, Runge–Kutta technique [9], and Next Increment
Corrects Error method following the explicit scheme [10], as well as the backward Euler method and trapezoidal
and midpoint rules following the implicit scheme [11]. Then, the updated stress can be obtained at the material point
after the following two crucial issues are addressed: (i) How can the updating process of state variables satisfy the
constraints of the loading/unloading inequality? (ii) How can nonlinear constitutive equations be solved efficiently
and robustly when the implicit integration scheme is used?
  The most commonly used method for addressing loading/unloading inequality constraints is the operator splitting
technique [11]. Namely, the elastic prediction is first completed by freezing the plastic flow, and then whether to
accept the trial stress as the new stress or to carry out a plastic correction depends on whether the trial stress
violates the KT conditions. Operator splitting technology provides a standard computational paradigm for the
elastoplastic model, but as necessary efforts, i.e., loading/unloading judgments based on the trial stress, need to be
done, additional consideration is required for the case in which the stress point undergoes a transition from elastic to
plastic behaviour when the explicit integration scheme is used. There are also some alternatives to this computational
framework. In Zheng et al.’s recent pioneering work [12], the control equations of the Mohr–Coulomb model with
perfect plasticity were cast as a certain variational inequality that is equivalent to the mixed complementarity
problem and was then solved effectively by the projection and contraction method [13]. However, the ability of
this projection and contraction method [13] in dealing with the softening problem remains to be explored. Another
more common idea is to transform inequality constraints into equality constraints using specific functions, such
as the penalty function [8,14,15] and the smoothing function [16–18]. The former is typically used in conjunction
with the interior point method in analysis dealing with elastoplastic problems from the perspective of mathematical
programming [19], where the constitutive model is recast in terms of a variational principle, and then the inequality
constraints are transformed into equality constraints by introducing the appropriate penalty functions. The details
of applying this method to the MCC model can be found in the literature [8]. The latter uses a smoothing function
to replace non-smoothing KT conditions, which makes the elastic and plastic behaviours uniformly described by
a set of smooth nonlinear equations. In contrast to that of the penalty function, the advantage of the smoothing
function is that it does not increase the number of required nonlinear equations. Notably, there is also no need for
additional computational effort to address the loading/unloading judgment and stress behaviour transition processes
in the operator splitting technique. Smoothing functions have been successfully used in the analysis of both crystal
plasticity [16,20] and finite strain plasticity [17,18,21] due to their attractive simplicity and effectiveness. There is
no doubt that such a function also provides a concise and valid computational framework for the implementation
of the MCC model based on plastic flow theory. It is also a prospective research direction for solving the stress
updating problem faced by the plastic models of geotechnical materials.
   For obtaining the solutions of nonlinear equations, the newton method is one of the most commonly used mathematical tools due to its quadratic convergence rate. It has been widely used in some representative implicit stress
updating algorithms, such as the fully implicit return-mapping algorithm [22], the cutting-plane algorithm [23,24],
and the semi-implicit algorithm [25]. However, the convergence behaviour of the newton method relies crucially
on the proximity of the initial iteration point to the convergence point [26]. The pure newton method is not
guaranteed to converge for a large time step or complex models with strong nonlinearity, although this drawback
can be compensated to a certain extent by breaking a large input load into a series of smaller load increments
and sequentially solving the sub-loadings [27]. From the perspective of mathematical programming, the nonlinear
equation problem is equivalent to an unconstrained minimization problem [28], which can be solved effectively
by some mature optimization methods, e.g., the line search method and the trust region method [29,30]. In some
sense, the search strategies for the two methods are dual to each other. The former optimizes the step size with the
given search direction, while the latter first choose the step size (i.e., trust region radius) and then determines the
search direction. The two methods have been utilized to attempt to solve the stress updating issue of elastoplastic
problems due to their better convergence than that of the classical Newton method. Some very valuable studies in
this field can be found in the literature [30–35]. Compared with the line search method, however, the application
of trust region method in the stress updating calculation is rarely explored. To the authors’ knowledge, it seems

                                                          2

### Page 3

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

that no one studied the performance of this method in the elastoplastic soil models. Especially, Nocedal and Wright
also pointed out that trust region algorithms may have certain theoretical advances in solving nonlinear equations
problem compared with the line search method in their monograph on the numerical optimization methods [28].
Although the trust region method has shown excellent convergence and robustness in solving the problem of the
nonlinear equation, the tentative application of the trust region method to elastoplastic models still encounters some
expected computation difficulties in some cases [30,33] (e.g., high curvature and poor scaling problems) due to the
limitation existing in the original version of trust region method. These computational difficulties can also be solved
by introducing some improvement techniques from the optimization field [30,36–38] to obtain a more satisfactory
algorithmic stress updating performance for elastoplastic problems.
   After the stress in the local calculation is updated, the consistent tangent operator (CTO) from the material point
is required to form the global stiffness of the structure, which is capable of preserving the asymptotic quadratic
convergence speed of the global solution. The origin of the concept of the CTO can be traced back to work by
Hughes [39]. It was then discussed in the analysis of inelastic large strain problems by Nagtegaal [40] and was
developed in the small strain framework by Simo [41]. In some follow-up studies, the CTO has always been an
important component of stress updating algorithms [23,27,42–44]. Specifically, for the MCC model, the CTO in
conjunction with the implicit return-mapping stress updating algorithm was derived in a study by Borja and his
co-workers [7,45] and appeared to have excellent numerical performance. However, one must realize that within
the computational framework of the operator splitting technique, the CTO needs to be derived respectively by
elastic and elastoplastic constitutive equations to address loading and unloading problems. Under repeated loading
and unloading conditions, the convergence of global solution may also be difficult to the optimal state. The reason
for this is that the non-smoothness of the elastoplastic problem resulting from the loading/unloading constraint
inequalities is not truly eliminated by the operator splitting technique, and it may impede the convergence of the
global solution under repeated loading and unloading conditions. However, this limitation can also be addressed by
using a smoothing function instead of non-smooth KT conditions.
   In this paper, an unconstrained stress updating strategy without the need for loading/unloading judgments is
proposed. The nonlinear constitutive equations are solved by the non-monotonic trust region (NMTR) method
with strong convergence and robustness. The poor scaling problem encountered by the  trust region method
according to the literature [33] is eliminated by introducing a diagonal scaling matrix without requiring additional
parameters [36,37]. The smoothing CTO corresponding to the unconstrained stress updating strategy is derived to
preserve the quadratic convergence speed of the global solution when using the newton method. After applying the
proposed algorithm to the MCC model, a numerical validation shows that its performance is superior to that of the
default algorithm (ABAQUS/Standard). The remainder of the paper is organized as follows: Section 2 focuses on
the elaboration of the basic idea of an unconstrained stress updating strategy with a simple 1D elastoplastic physical
model, in which the operator splitting technique is briefly reviewed as a comparison. Section 3 briefly restates the
MCC model and provides the integration formulas derived by the backward Euler scheme. The double dogleg trust
region method is improved by the non-monotonic technique and presented in Section 4. In Section 5, the algebraic
and geometric interpretations of the CTO and continuum tangent operator (CON) are discussed in depth, and the
two tangent operators that are consistent with the unconstrained stress updating strategy are derived. Section 6 gives
the necessary numerical validation and performance analysis for the proposed algorithm based on the user-defined
material subroutine (UMAT). Some important conclusions are contained in Section 7. In the Appendices, we give
some derivation details and the matrix representation of tensors, which is convenient for programming. Finally, we
add a simple clarification to the following contents. The constitutive models targeted by the algorithm are in a small
strain theory framework. This paper takes pressure as positive. Tensors are represented in bold. Matrices and vectors
are denoted by [·] and {·}, respectively. The three indices n, i, and k are used to denote the incremental load step,
the global equilibrium iteration, and the local stress updating iteration, respectively.

2. Computational framework of the unconstrained stress updating strategy

  To completely describe the material’s mechanical response, a basic elastoplastic model is required to answer
the following questions: What is the stress–strain relationship of the material? How to determine the proportional
relationship between plastic strain increment components? How to record the loading history related to plastic

                                                          3

### Page 4

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

                           Fig. 1. Influence law of the parameter β on the FB smoothing function (with cd = 1).

deformation? What situations will trigger the plastic deformation mechanism? The answers to these questions
constitute the basic mathematical formula of the elastoplastic model:
   ⎧ ˙σ = D: ˙εe = D: (˙ε −˙εp) ,           Hooke′s law
            ˙εp = ˙φr,                              Plastic  f low rule                  ⎪⎪⎪⎪⎪⎨                                                                                                                     (1)
           ˙α = ˙φh,                         Hardening law
                  ⎪⎪⎪⎪⎪⎩ ˙φ ≥0, f (σ, α) ≤0, ˙φ f (σ, α) = 0,  Kuhn-Tucker complementary conditions
where ˙σ and ˙ε denote the rates of stress tensor and strain tensor, respectively. The latter includes recoverable elastic
part ˙εe and unrecoverable plastic part ˙εp. D is the elastic stiffness tensor. ˙φ and r are the rate of the plastic multiplier
and the plastic flow direction, respectively. ˙α and h are the rate of plastic internal variable and its gradient.  f denotes
the yield function defining the elastic and plastic boundary. In the numerical implementation, these rate equations
are transformed into the algebraic equations by time integral:
   ⎧ σn+1 = σn + D: ( ∆εn+1 −∆εpn+1 )
      ∆εpn+1 = ∆φn+1rn+1                  ⎪⎪⎪⎪⎪⎨                                                                                                                     (2)
      ∆αn+1 = ∆φn+1hn+1
                  ⎪⎪⎪⎪⎪⎩ ∆φn+1 ≥0, fn+1 ≤0, ∆φn+1 fn+1 = 0
where the backward Euler integration scheme is used as an example. As can be noticed, the above equations are nonsmooth due to the constraints of inequalities. Alternatively, the KT conditions in Eq. (2) can be replaced equivalently
by the smooth function in the optimization theory:
   ⎧ σn+1 = σn + D: ( ∆εn+1 −∆εpn+1 )
      ∆εpn+1 = ∆φn+1rn+1                  ⎪⎪⎪⎪⎪⎨                                                                                                                     (3)
      ∆αn+1 = ∆φn+1hn+1
    √                   2           +  f n+1 + 2β −cd∆φn+1 + fn+1 = 0                  ⎪⎪⎪⎪⎪⎩  (cd∆φn+1)2
where Eq. (3)4  is the Fischer–Burmeister (FB) smooth function [46,47]. β  is the parameter controlling the
approximation degree of Eq. (3)4 to Eq. (2)4, as shown in Fig. 1. The parameter cd is used to balance the dimensional
relationship between ∆φn+1 and  fn+1. Then, the non-smoothness of the elastoplastic problem is eliminated in
Eq. (3). The original constrained problem is transformed into the equivalent unconstrained problem.
   In what follows, a 1D spring-slider physical model shown in Fig. 2 is used as an example to further illustrate
the computational framework of the unconstrained stress updating strategy. The classical splitting stress updating

                                                          4

### Page 5

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

                                                   Fig. 2. 1D spring-slider physical model.

strategy is also briefly reviewed for comparison. Corresponding to Eq. (2), the integral equations of the 1D physical
model are given:
   ⎧ σn+1 = σn + E ( ∆εn+1 −∆εpn+1 )
      ∆εpn+1 = ∆φn+1sign (σn+1)                  ⎪⎪⎪⎪⎪⎨                                                                                                                     (4)
      ∆αn+1 = ⏐⏐∆εpn+1 ⏐⏐
                  ⎪⎪⎪⎪⎪⎩ ∆φn+1 ≥0, f (σn+1, αn+1) ≤0, and ∆φn+1 f (σn+1, αn+1) = 0
where  f (σ, α) = |σ|−σY −K pα and the simple linear hardening law is assumed. E and K p are the spring stiffness
and the hardening modulus of the slider. σY  is the initial sliding stress. sign (·) is the sign function and Eq. (4)2
denotes that the direction of ∆εpn+1 is the same as that of stress in the 1D condition. When only the compression
situation is considered, the sign and absolute value functions can be omitted.
  The key to solving the elastoplastic problem defined by Eq. (4) is to determine ∆φn+1 under the action of
an external load. However, for the given ∆εn+1, three loading/unloading cases may need to be estimated before
calculating ∆φn+1 due to the presence of KT conditions, as demonstrated in Fig. 3.

2.1. Operator splitting stress updating strategy

   In the classical return-mapping stress updating algorithm, the operator splitting technique [11] is used to address
KT conditions. First, the trial stress σn+1trial = σn + E∆εn+1 is determined based on the elastic Hooke’s Law. Then,
the loading and unloading cases under the current increment step can be estimated by the values of  f (σn, αn) and
 f ( σn+1,trial αn ) as follows:
   ⎧ case a : pure elastic loading/unloading              if  f (σn, αn) ≤0 and  f ( σn+1,trial αn ) ≤0
         ⎪⎪⎨                                                                                                                               trial       case b: pure elastoplastic loading                     if  f (σn, αn) = 0 and  f ( σn+1, αn ) > 0                 (5)
                                                                                           ) > 0         ⎪⎪⎩ case c: elastic and elastoplastic mixed loading   if  f (σn, αn) < 0 and  f ( σn+1,trial αn
   For case a, that the current increment step is purely elastic. ∆φn+1 = 0 and the σn+1trial is accepted as the σn+1.
For case b, the plastic deformation mechanism is triggered under the current increment step. The plastic corrector
needs to be used to pull the trial stress back toward the real stress σn+1, as shown in Fig. 4. ∆φn+1 can be obtained
by substituting Eq. (4)1∼3 and σn = σY + K pαn into the equation  f (σn+1, αn+1) = σn+1 −σY −K pαn+1 as follows:

            E∆εn+1
                                                                                                                     (6)    ∆φn+1 =
           E + K p

  Case c indicates that the stress point undergoes a mechanical behaviour transition from elasticity to plasticity
at the current increment step. The partial strain increment ξ∆εn+1 corresponding to the pure elastic loading in
Fig. 3(c) needs to be determined in advance. The scale factor ξ (0 < ξ < 1) is determined by solving the equation
 f (σint, αn) = 0 and considering the condition σn < σY + K pαn, where σint is the largest historical yield stress:
          σY + K pαn −σn
      ξ =                                                                                                           (7)
           E∆εn+1
                                                          5

### Page 6

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

Fig. 3. Different loading/unloading cases: (a) pure elastic loading/unloading; (b) pure elastoplastic loading; (c) mixed elastic and elastoplastic
loading.

   Then, ∆φn+1 corresponding to case c can be obtained by replacing ∆εn+1 in Eq. (6) with (1 −ξ) ∆εn+1:
            E∆εn+1 −(σY + αnK p −σn)
                                                                                                                     (8)    ∆φn+1 =
                  E + K p
   Finally, the updating of state variables for the different loading and unloading cases can be obtained by
substituting ∆φn+1 = 0, Eqs. (6) and (8) into Eq. (4) as follows:
For case a:
   ⎧ σn+1 = σn + E∆εn+1
         ⎪⎪⎨       αn+1 = αn                                                                                                   (9)
         ⎪⎪⎩ ∆φn+1 = 0
For case b:
   ⎧         E K p∆εn+1
       σn+1 = σn +
               E + K p                     ⎪⎪⎪⎪⎪⎪⎨          E∆εn+1                                                                                                            (10)       αn+1 = αn +
               E + K p
              E∆εn+1
      ∆φn+1 =                     ⎪⎪⎪⎪⎪⎪⎩            E + K p
                                                          6

### Page 7

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

                                  Fig. 4. Stress update procedure for the purely elastoplastic loading case.

For case c:
   ⎧         E K p∆εn+1   E (σY + αnK p −σn)
                  +       σn+1 = σn +
               E + K p                             E + K p
                   + αnK p −σn)                     ⎪⎪⎪⎪⎪⎪⎨          E∆εn+1 −(σY                                                                                                            (11)       αn+1 = αn +
                      E + K p
              E∆εn+1 −(σY + αnK p −σn)
      ∆φn+1 =                     ⎪⎪⎪⎪⎪⎪⎩                   E + K p

   In the operator splitting stress updating strategy, the loading/unloading judgment is achieved by the elastic
predictor. Although this method provides an excellent distinction between the different loading/unloading cases,
it leads to non-smoothness in the calculation. Additional attention needs to be paid to case c  (if the explicit
integration scheme is adopted). It can be found that the root of the non-smoothness in the KT conditions arises
from the inequality constraints. Replacing the inequality constraints with a smoothing function to eliminate the
non-smoothness in the calculation becomes the biggest motivation of this paper.

2.2. Unconstrained stress updating strategy based on a smoothing function

   Replacing Eq. (4)4 with the FB smooth function, the elastoplastic problem constrained by the loading/unloading
inequalities can be transformed into the following unconstrained form:
   ⎧ σn+1 = σn + E ( ∆εn+1 −∆εpn+1 )
      ∆εpn+1 = ∆φn+1                  ⎪⎪⎪⎪⎪⎨                                                                                                            (12)
      ∆αn+1 = ∆εpn+1
    √
        (cd∆φ)2 +  f 2 (σn+1, αn+1) + 2β −cd∆φn+1 +  f (σn+1, αn+1) = 0                  ⎪⎪⎪⎪⎪⎩

  Now, the elastoplastic problem depicted by Fig. 2 can be solved directly by Eq. (12) without dealing with
inequality constraints. For Eq. (12)4, we have:

    β = −cd∆φn+1 f (σn+1, αn+1)                                                                         (13)

                                                          7

### Page 8

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

   Substituting the condition  f (σn+1, αn+1) = σn + E (∆εn+1 −∆φn+1) −σY −K p (αn + ∆φn+1) into Eq. (13),
we can obtain:
     cd∆φ2n+1 ( E + K p) −cd∆φn+1 ( σn + E∆εn+1 −σY −αnK p) −β = 0                                  (14)

   Utilizing the root of the quadratic equation, the nonnegative solutions of ∆φn+1 can be obtained as follows:

                         √
                 cd (σn + E∆εn+1 −σY −αnK p) +   c2d (σn + E∆εn+1 −σY −αnK p)2 + 4cd (E + K p) β
    ∆φn+1 =                                                                                              (15)
                                                   2cd (E + K p)
  When β is close to 0, the following solutions for ∆φn+1 can be automatically obtained for a given ∆εn+1 and
σn:
           ⎧ 0,                             σn ≤σY + αnK p and σn + E∆εn+1 ≤σY + αnK p
                 E∆εn+1                                             p                                   p                                       ,                      σn = σY + αnK  and σn + E∆εn+1 > σY + αnK + E∆εn+1                                                      ⎪⎪⎪⎪⎨      lim ∆φn+1 =                E + K p
    β→0
                                                                  ,  σn < σY + αnK  and σn + E∆εn+1 > σY + αnK + E∆εn+1                                            p                                                      ⎪⎪⎪⎪⎩ E∆εn+1 −(σYE + +K αnK p −σn)                     p                                   p
                                                                                                            (16)

where there is no need to perform the loading/unloading judgment in advance or to calculate the intersection point
σint in Fig. 3(c). Substituting Eq. (16) into Eq. (12), the updating formulas of the same state variable as Eqs. (9),
(10), and (11) can be obtained correctly for the given ∆εn+1 even if the operator splitting technique is not used.
The non-smoothness of the elastoplastic problem is bypassed by the FB smoothing function.
    It is noted that the constitutive equations for the elastoplastic problems in this section are solved manually due
to the simplicity of the 1D physical model. However, the mechanical behaviours of most materials, especially
for geomaterials, are often complex and exhibit highly nonlinear characteristics. The nonlinear stress integrations
need to be solved by iteration. In addition, the smoothing function also results in a problem that we must face,
that  is, the smoothing function may have a higher curvature near the origin than elsewhere. In turn, the high
curvature phenomenon appears in the area near fn+1 = 0 and ∆φn+1 = 0 when β trends to 0. This makes it more
difficult to address the problem of neutral loading and elastic unloading, where the initial stress point appears on the
yield surface. Therefore, an efficient and robust numerical algorithm is required to solve the nonlinear constitutive
equations of the complex elastoplastic model containing the smoothing function.

3. Backward Euler integral scheme of the MCC model based on the smoothing function

  The initial Cam-clay model was proposed by Roscoe and his co-workers in the 1960s [48], and it has directly
affected the beginning and development of critical state soil mechanics and became a standard paradigm for the
successor to establish the elastoplastic model of soils [49,50]. In this section, the MCC model developed further by
Roscoe and Burland [51] is considered as the application object of the proposed algorithm. The rate constitutive
equations are integrated by the backward Euler scheme within the framework of an unconstrained stress updating
strategy.

3.1. Kernel ingredients of the model

  The basic architecture of the MCC model can be represented by four key ingredients, including the nonlinear
elastic law for soil, the elliptic yield function, the associated flow rule, and the hardening law.

3.1.1. Elastic law
  Under isotropic conditions, the fourth-order elastic stiffness tensor in Eq. (1) is expressed as follows:

          (     )   D = 3Ivol K −2  + 2IsymG                                                                       (17)              3G
where Ivol and Isym are the volume part and symmetric part of the fourth-order unit tensor I, respectively. G and K
denote the shear modulus and the bulk modulus, respectively. G = Kr, and r = 1.5 (1 −2ν) / (1 + ν) where ν is

                                                          8

### Page 9

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

Poisson’s ratio. In the MCC model, the following expression is employed to describe the nonlinear elastic behaviour
of the soil:

    K = ck p                                                                                              (18)

where ck = (1 + e0) /κ. e0 is the initial void ratio, and κ is the swell index under isotropic compression. p = σ: 1/3
denotes the hydrostatic pressure where 1 denotes the second-order unit tensor.

3.1.2. Yield function
  The following elliptic yield function is used in the MCC model:
          q2
         f =   + p (p −pc)                                                                                (19)
       M2
where M is the slope of the critical state line. q = √3/2 ∥s∥denotes the generalized shear stress, and s = σ −p1
is the deviatoric stress tensor. pc denotes the pre-consolidation pressure, which defines the diameter along the
hydrostatic axis of the ellipsoid yield surface.

3.1.3. Flow rule
   For the MCC model, the associated flow rule, which assumes that the plastic potential function and the yield
function have the same form, is used. Therefore, the rate of plastic strain can be expressed as follows:
            ∂f
         ˙εp = ˙φ                                                                                                (20)
          ∂σ
where the expression for the gradient of the yield function is:
      ∂f    3     (2p −pc)
     =     s +         1                                                                             (21)
     ∂σ   M2       3

3.1.4. Hardening law
  The plastic volume strain is used as the hardening parameter in the MCC model to record the loading history of
the soil. The following hardening law in rate form can be obtained from the isotropic compression test of soil:
         ˙pc = cp pc˙εpv                                                                                           (22)
where cp = (1 + e0) / (λ −κ). λ is the compression index, and
           ∂f
         ˙εpv =      ˙φ = (2p −pc) ˙φ                                                                              (23)         ∂p

3.2. Integral scheme

   In the previous section, the MCC model was presented in rate form. For the stress updating procedure, the rate
constitutive equations need to be discretized in time. By utilizing the backward Euler scheme, the integral scheme
of stress can be obtained by integrating Eq. (1).
     σn+1 = σn + D ( K, G ) : ( ∆εn+1 −∆εpn+1 )                                                             (24)

where the secant bulk modulus K and secant shear modulus G are used [7]. The expression of K is
            pn
    K =      [exp ( ck∆εev,n+1 ) −1 ]                                                                       (25)
            ∆εev
where ∆εev,n+1 = ∆εv,n+1 −∆εpv,n+1 = ∆εv,n+1 −∆φn+1 ( 2pn+1 −pc,n+1 ) . Referring to Borja’s practice [7], the
integral formula of σ can be replaced by those of p and q. This practice can effectively reduce the number of
nonlinear equations in the iterative calculation process. The following expressions can be obtained by evaluating
the volumetric and deviatoric parts of σn+1:
            1
      pn+1 = 3σn+1 : 1 = pn exp { ck [∆εv,n+1 −∆φn+1 ( 2pn+1 −pc,n+1 )]}                                   (26)
                                                          9

### Page 10

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

       √ 3
     qn+1 =    ∥sn+1∥                                                                                    (27)
             2
where the deviatoric stress tensor sn+1 is determined by:
      sn+1 = sn + 2G ( ∆γn+1 −∆γpn+1 )                                                                     (28)
where ∆γn+1 and ∆γpn+1 are the total and plastic deviatoric strain increment tensors, respectively. ∆γpn+1  is
determined by:
                ∂f          3∆φn+1sn+1
    ∆γpn+1 =     ∆φn+1 =                                                                              (29)               ∂sn+1          M2
   Substituting Eq. (29) into Eq. (28) and reorganizing the new equation, we can obtain:
                 sn + 2G∆γn+1
      sn+1 =                                                                                                (30)
           1 + 6G∆φn+1/M2
   Substituting Eq. (30) into Eq. (27), the expression of qn+1 can be rewritten as follows:
       √ 3              √ 3  sn + 2G∆γn+1                                                                                                             (31)     qn+1 =              ∥sn+1∥=
             2           2 1 + 6G∆φn+1/M2
  Once pn+1 and qn+1 are determined, σn+1 can be obtained as follows:
     σn+1 = pn+11 + sn+1                                                                                  (32)

  The evaluation of pc,n+1 can be obtained by integrating Eq. (22):
       pc,n+1 = pc,n exp [cp∆φn+1 ( 2pn+1 −pc,n+1 )]                                                          (33)

  Combining the FB smoothing function composed of the yield function fn+1 and the plastic multiplier ∆φn+1,
                                                         can be obtained as follows:the closed control equations {f (x)}n+1 = { f1    f2    f3    f4 }Tn+1
          ⎧cd { pn+1 −pn exp [ck∆εv,n+1 −ck∆φn+1 ( 2pn+1 −pc,n+1 )]} ⎫
   ⎧ f1 ⎫                                      ⎧0⎫
              (                √ 3                                               sn                     + 2G∆γn+1  )                     cd                       qn+1 −                                                                        0          f2                  ⎪⎪⎪⎪⎪⎨                                                                                                                                                                                                                                                                                                                                              ⎪⎪⎪⎪⎪⎪⎪⎬                               ⎪⎪⎪⎪⎪⎬                                                                                                                                                                                                                                                                          ⎪⎪⎪⎪⎪⎨                                                                             ⎪⎪⎪⎪⎪⎪⎪⎨                                                                                                                                                                                                                                                                                    ⎪⎪⎪⎪⎪⎬                            2 1                    + 6G∆φn+1/M2                                            =        =                                                                                                            (34)
                                                                        0          f3                     cd { pc,n+1 −pc,n exp [cp∆φn+1 ( 2pn+1 −pc,n+1 )]}
          √                                                                        0⎪⎪⎪⎪⎪⎭                  ⎪⎪⎪⎪⎪⎩ f4 ⎪⎪⎪⎪⎪⎭n+1              ⎪⎪⎪⎪⎪⎪⎪⎩                    (cd∆φn+1)2 +  f n+12 + 2β −cd∆φn+1 + fn+1                                                           ⎪⎪⎪⎪⎪⎪⎪⎭          ⎪⎪⎪⎪⎪⎩
where   fn+1  =    q2n+1/M2 +  pn+1 (pn+1 −pc).  There  are  four  independent  variables  {xn+1}  =
                                                                     ∆εn+1 out of consideration{pn+1  qn+1   pc,n+1  ∆φn+1 }T in Eq. (34). It is recommended that cd = σn + D:
the magnitude difference of residual errors between f1∼3 and  f4. There are also other forms of smooth functions,
e.g., Chen-Mangasarian and Chen–Harker–Kanzow–Smale smooth functions [19]. The former employs an approximation form with exponential function, and the function form of the latter is similar to that of the FB function. Both
of them can reasonably approximate the KT conditions. However, it is easy to suffer from a floating-point overflow
problem when the yield function is used as a variable in the exponential function, at least for the MCC model.
Therefore, the FB function is used in this paper. A more detailed discussion on the different smooth functions can
be found in the literature [19].

4. Implementation of the MCC model based on the non-monotonic trust region method

  The problem with nonlinear equations in Eq. (34) is equivalent to an unconstrained minimization problem, which
corresponds to a merit function constructed by Eq. (34) and written as follows:
                      1           T
     min  ψ ({x}n+1 ) = 2{ f (x)}n+1  { f (x)}n+1                                                           (35)
where solving the nonlinear equations is equivalent to minimizing the merit function. For convenience, the subscript
n+1 is omitted in the remainder of this section. The solution of Eq. (35) can be obtained by performing the following

                                                          10

### Page 11

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

iteration:
      {x}k+1 = {x}k + α {d}                                                                                 (36)

where α and {d} are the step size and variables direction vector, respectively. In the trust region method, the step
size is limited first by the trust region radius. Then, the search direction {d} is determined by the descent direction
of a model function that is the approximation of the original merit function in a region around the current point.
Generally, the trust region method uses a quadratic model to approximate the original merit function as follows:
                                  1
     min  mk ({d}) = ψk + {g}Tk {d} +   {d}T [B]k {d}
                                  2                                                                                                            (37)
                             s.t. ∥{d}∥≤∆k
where {g}k  is the gradient of ψk and {g}k = {f}Tk {∇f}k. The details of the Jacobian matrix {∇f} corresponding
to Eq. (34) are presented in Appendix A. [B]k = {∇f}Tk {∇f}k is the Hessian matrix. ∆k is the region radius, and
∆k ≤∆max. Eq. (37) is called a trust region subproblem, where the variable vector {d} can be determined by
minimizing the quadratic function mk in the trust region. To ensure that the trust region method is still effective
in dealing with an optimization problem that has poor scaling, Eq. (37) is usually recast by a scaling matrix as
follows:
                                1
                   +                                             k     min  mk ({˜d}) = ψk + {˜g}T                                2 {˜d}T [˜B]k {˜d}                                                                                                            (38)
                          s.t.    {˜d}≤∆k

                                                                                                   is a diagonal scaling matrix. In the                                      and [˜B]k = [Ds]−1 [B]k [Ds]−1. [Ds]where {˜g}k = [Ds]−1 {g}k, {˜d}k = [Ds] {d}k,
literature [36,37], it is recommended to set the scaling matrix to [ Dsii ] = [Bii]0. This can be interpreted as follows:
if B0ii is large, then it is likely that the merit function ψ is more sensitive to changes in certain components xi. The
approximation of m to ψ is questionable, and thus, the search area should be restricted along the ith coordinate. In
addition, the advantage of this approach is that there is no need to customize the elements of the diagonal scaling
matrix according to specific physical problems, so it is universal than other methods. The poor scaling problems
reported in the literature [30,33] can also be avoided when the trust region method is applied to stress updating.
  Once the trust region subproblem in Eq. (38) is solved, the quality of the trial step {x∗}k+1 = {x}k + {d} can be
evaluated by the following ratio:
       ψ ({x}k) −ψ ({x}k + {d})
     ρk =                                                                                                  (39)
           mk ({0}) −mk ({d})
where the numerator denotes the actual reduction of the merit function and the denominator denotes the predicted
reduction of the model function. If ρk is close to 1, this shows that the model function and the merit function are
very good approximations in the trust region. The trial point {x∗}k+1 can be accepted as the next iteration point
{x}k+1, and the trust region radius ∆k is amplified for the next iterative calculation. If ρk is close to 0 or even less
than 0, then one should consider rejecting the trial step and reducing the trust region radius to resolve the trust
region subproblem in Eq. (38). It is observed from the basic idea of the trust region method that three areas need
to be addressed for the successful application of the trust region method: (i) How can the trust region radius be
determined? (ii) What are the criteria for accepting the trial point? (iii) How can the trust region subproblem be
solved?

4.1. Determination of the trust region radius

  The reasonable choice of the trust region radius, including the initial trust region radius ∆0 and the maximum
trust region radius ∆max, has a great influence on the convergence speed and stability of the trust region method [52].
Utilizing too small a trust region radius reduces the convergence speed. If the trust region radius is too large, it
will lose meaning. The reliability of the approximation of the model function to the merit function also decreases.
In numerous studies regarding the trust region method that do not involve practical physical problems [29,53,54],
there is little evidence to support a particular setting of the trust region radius, or additional calculation efforts are
required to provide a reasonable constraint range for the trust region radius. However, for the elastoplastic stress
updating problem based on an incremental calculation, the maximum admissible stress increment can be determined

                                                          11

### Page 12

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

by the difference between the converged stresses of step n and the elastic trial stress of step n + 1. The upper limit
of the allowable plastic strain increment is the total strain increment. Therefore, the maximum change among the
four variables in Eq. (34) can be determined as follows:

         ⎧   pn exp ( ck∆εv,n+1 ) −pn ⎫
          √ 3
                   2 sn + 2G∆γn+1 −qn                                                                                         ⎪⎪⎪⎪⎪⎪⎪⎪⎪⎨                                                                                                                                                         ⎪⎪⎪⎪⎪⎪⎪⎪⎪⎬
     {∆x}max =     pc,n exp ( cp∆εv,n+1 ) −pc,n                                                              (40)
        
                                              /3                            v,n+1                + 2 ∆γn+1 2                  √∆ε2                      ( 2pn −pc,n )2 + ( 2qn/M2)  ⎪⎪⎪⎪⎪⎪⎪⎪⎪⎭                                                                                         ⎪⎪⎪⎪⎪⎪⎪⎪⎪⎩

and considering the influence of the diagonal scaling matrix on the trust region radius, the upper limit of the trust
region radius can be determined by:
     ∆max = [Ds] {∆x}max                                                                                (41)
  The initial trust region radius ∆0 can be set to ∆max to consider the situation involving single-step iterative
convergence.

4.2. Non-monotonic trust region method

   In the basic trust region method, the criteria for accepting the trial point is determined by considering only the
reduction in the current iteration step. Trial points that cause increases in the merit function are not allowed to
be accepted. The basic framework of the trust region method following this monotonic search strategy is detailed
below:
Step 0. Initialization. The initial iteration point {x}0, the trust region radius ∆0, and the small positive tolerance
FT OL are given. ∆max is chosen as the upper limit of the trust region radius. Set k = 0.
Step 1. Convergence judgment. Compute the norm of the residual vector f ({x}k). If f ({x}k)≤FT OL, the
iterative process is terminated.
Step 2. Step calculation. Solve the trust region subproblem in Eq. (38) and obtain the trial point {x∗}k+1.
Step 3. Estimation of the trial point. Compute the ratio ρk by using Eq. (39).
    If ρk > 0.1, accepted the trial point and set {x}k+1 = {x∗}k+1; otherwise, set {x}k+1 = {x}k.
Step 4. Adjustment of the region radius. Adjust the trust region radius in the next iteration step as follows:

       ⎧ 0.5∆k            ρk < 0.1
                      ⎪⎪⎨     ∆k+1 =  ∆k                0.1 ≤ρk ≤0.75                                                          (42)
                      ⎪⎪⎩ min ( 2∆k, ∆max )  ρk > 0.75
   Set k = k + 1 and go to Step 1.
  Based on the ratio ρk of predicted reduction and actual reduction, the quality of the trial step is divided into three
kinds: ‘bad’, ‘good’, and ’very good’. If the trial step is ‘bad’, discard it and reduce the trust region radius. If the
trial step is ‘good’ or ‘very good’, accept it. The difference is that the trust region radius will remain constant for the
‘good’ case and be enlarged for the ‘very good’ case. As seen from Step 3, however, in the monotonic trust region
(MTR) method, the merit function is required to decrease continuously in each successful iteration because the trial
point can be accepted only when ρk is greater than 0. However, this condition is too harsh for practical physical
problems, and it may lead the search to fall into a local optimum and reduce the possibility of finding the optimal
solution. Therefore, some researchers try to introduce a non-monotonic strategy in the acceptance criteria for trial
points [38,55,56]. For the non-monotonic strategy, the merit function in the search process is allowed a limited
increase, but the overall trend needs to remain downward. This treatment can effectively enhance the robustness of
the trust region method with very little extra calculation cost. In this paper, the non-monotonic strategy proposed
by Toint [38] is used to improve the monotonic trust region method above, where only Step 3 needs to be adjusted.

                                                          12

### Page 13

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

Step 3 of the non-monotonic trust region method. Estimation of the trial point. Compute the largest index such that

   ψ M(k) =     max      ψi                                                                          (43)
                  i=max[l−Mmax,0],··· ,l
where ψi = ψ ({x}i) is the sequence of values of the merit function at the ends of successful iterations. Mmax
is a positive integer indicating the maximum number of previously successful iterations that are considered when
evaluating the trial point. It is recommended to set Mmax to 10 [38]. l denotes the number of successful iterations
and is initialized to 0 in Step 0.
   Then, compute ψ ({x}k + {d}) and the following ratio:
      ⎧ ψ M(k) −ψ ({x}k + {d})
            ⎪⎨                                    if l > 0,
     ρk1 =      ∑li=M(k) dl                                                                              (44)
            ⎪⎩         0             otherwise
  Compute the ratio of the actual reduction to the predicted reduction at the current step:
       ψ ({x}k) −ψ ({x}k + {d})
     ρk2 =                                                                                                  (45)           mk ({0}) −mk ({d})
   Finally, the ratio used to evaluate the trial point is determined by:
     ρk = max ( ρk1, ρk2 )                                                                                    (46)
    If ρk < 0.1, then set {x}k+1 = {x}k. Otherwise, set {x}k+1 = {x∗}k+1, increment l by one and set
     ψl = ψ ({x}k + {d}) and dl = mk ({0}) −mk ({d})                                                     (47)

4.3. Double dogleg method for solving the trust region subproblem

  Methods for solving trust region subproblems have been widely studied [57], such as the singular dogleg
method [58], double dogleg method [59], two-dimensional subspace minimization method [60], and conjugate
gradient method [61]. Herein, the double dogleg method is used to approximate the solution of the trust region
subproblem. The double dogleg method is an improved version of the single dogleg method. In both methods, the
dogleg step is determined by a combination of the Cauchy step and Newton step. According to the relative positions
of the Cauchy point and the Gauss–Newton point to the trust region boundary, three cases for the determination of
the dogleg step are schematically represented in Fig. 5.
   First, the Cauchy point {xC}k+1 = {x}k + {dC} is determined in the steepest descent direction, where {dC} =
−{˜g}k. Then, the position of the Cauchy point relative to the trust region boundary needs to be estimated. If∥{dC}∥≥∆k, the intersection point between the Cauchy step and trust region boundary is used as the minimum
point of the quadratic model, as shown in Fig. 5(a). If the Cauchy point is interior, we continue to calculate the
                                                                                        If the Newton point is interior, as shown inNewton point {xGN}k+1 = {x}k + {dGN}, where {dGN} = − [˜B]−1k   {˜g}k.
Fig. 5(b), it is used as the minimum point of the quadratic model. If ∥{dGN}∥> ∆k, the dogleg step is calculated,
as shown in Fig. 5(c). In the single dogleg method, the minimum point of the quadratic model is determined by
the intersection point of between the trust region boundary and the dogleg segment, which is a segment connecting
the Cauchy point and Newton point. In the double dogleg method, the position of the point connecting the Cauchy
point to form the dogleg segment is moved towards the trust region boundary, as shown in Fig. 5(c). The search
direction generated by the double dogleg method is more inclined to the newton direction than that produced by
the single dogleg step. Numerical experimental results have shown that the performance of the algorithm can be
improved to a certain extent by this treatment [59].
  The double dogleg method is detailed below to complete Step 2 in the non-monotonic trust region method:
Step 2.0. Calculate the gradient and Hessian of the merit function at the current point {x}k  and scale them diagonally
as follows:
             = [Ds]−1 {f}Tk [∇f]k                                                                 (48)        {˜g}k = [ Ds]−1 {g}k
                                                         [Ds]−1                                                (49)                           [Ds]−1 = [Ds]−1 [∇f]Tk [∇f]k       [˜B]k = [ Ds]−1 [B]k
                                                          13

### Page 14

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

                Fig. 5. Three cases of the dogleg method: (a) Cauchy step; (b) Newton step; (c) Single/double dogleg step.

Step 2.1. Calculate the Cauchy step:

     {dC} = −τ 1k ∆k  {˜g}k                                                                                 (50)
                               {˜g}k
where the coefficient τ 1k guarantees that the Cauchy step does not exceed the trust region boundary and is expressed
as follows:

           [             ]
      τ 1k = min  1,       {˜g}k3                                                                            (51)
               ∆k {˜g}T                                    k [˜B]k {˜g}k
    If ∥{dC}∥= ∆k, set {d} = [Ds]−1 {dC} and go to Step 2.4.
Step 2.2. If {dC}k< ∆k, then calculate the Newton step:

                   ]−1
                            k     {dGN} = − [˜B                               {˜g}k                                                                                 (52)
    If ∥{dGN}∥≤∆k, set {d} = [Ds]−1 {dGN} and go to Step 2.4.
Step 2.3. If {dGN}k> ∆k, then calculate the double dogleg step:

     {dD} = {dC} + τ 2k ( τ 3k {dGN} −{dC})                                                                   (53)

                                                          14

### Page 15

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

where τ 3k ∈ ( τ4k , 1) and τ 4k is obtained as follows:
      τ 4k =                   {˜g}k4                                                                            (54)
                                    ]−1
                                                  k                                           k [˜B                                              {˜g}k)         ( {˜g}T                     k [˜B]k {˜g}k) ({˜g}T
where τ 3k is usually set to 0.8τ 4k +0.2. The double dogleg method degenerates into the single dogleg method under the
condition where τ 3k = 1. τ2k can be obtained by solving the quadratic equation {dC} + τ 2k ( τ 3k {dGN} −{dC})= ∆k
as follows:
         −{v}Tk {dC} ± √({v}Tk {dC})2          k                      − {v}k2 (∥{dC}∥2 −∆2k )      τ 2 =                                                                                                  (55)
                                           {v}k2
where {v}k = τ 3k {dGN} −{dC}, and the positive root of Eq. (55) is always chosen due to 0 ≤τ2k ≤1. Finally, set
{d} = [Ds]−1 {dD}.
Step 2.4. Exit with {x∗}k+1 = {x}k + {d}.
  The implementation of the MCC model based on the proposed algorithm is briefly summarized as follows: First,
the rate constitutive equations of the MCC model constrained by the loading/unloading equality are discretized into
a set of nonlinear algebraic equations by the backward Euler scheme. Then, the nonlinear equations constrained by
the loading/unloading equality are transformed into a smooth form by using the FB smoothing function instead of
the non-smooth KT conditions. Finally, the smooth nonlinear constitutive equations are considered as an equivalent
unconstrained minimization problem, which is solved further by the double dogleg trust region method (improved
by the non-monotonic strategy). The computation procedures of the proposed stress updating algorithm for the MCC
model are presented in Fig. 6. It should be emphasized that the proposed algorithm can work for all elastoplastic
models. For the numerical implementation of soil models based on the critical state concept, there are typically
nonlinear and non-smooth characteristics, which can be addressed better by the proposed algorithm. In addition,
the smooth function and trust region method can work for the finite strain plasticity [62,63] because they are
essentially used to address common computational difficulties in the numerical implementation of the plastic model,
i.e., the nonsmoothness and nonlinearity. In this paper, the MCC model with the small formulation is used as an
example.

5. Consistent and continuum tangent operators

  Under the framework of solid mechanics, a nonlinear boundary value problem can be solved by the finite element
method. The external load acting on the given structure is applied incrementally. The change in the internal force
comes from the updates of the state variables at the material point. The unbalanced forces of the element nodes are
minimized iteratively by the newton method so that the structure transitions from the previous equilibrium state n
to the next equilibrium state n + 1. When the internal force and external force reach equilibrium on each element
node, the following equation holds:
     {F (σ)}n+1 = {Fext} n+1 − {Fint}n+1 = {0}                                                              (56)
where {F}n+1, {Fint}n+1, and { Fext} n+1 denote the global residual force vector, the global internal force vector,
and the global external force vector, respectively. By utilizing the displacement-based finite method with σin+1 =
σ ( εin+1 ) = σ ( ε ( Uin+1 )) , Eq. (56) is solved by the following linearized form:

                                                                                                            (57)      [K]in+1 {δU}i+1n+1 = − ({Fext} n+1 − {Fint}in+1 )
where {δU}i+1n+1 is a displacement correction. The global stiffness matrix [K]in+1 can be determined by:
           [∂F ]i  [∂σ ]i  [ ∂ε ]i
      [K]in+1 =                                                                                             (58)
             ∂σ  n+1  ∂ε  n+1 ∂U  n+1
where [∂σ/∂ε]in+1 is determined by the constitutive equations at the material point scale. [∂σ/∂ε]in+1 is called the
CTO [41]. As a spare option, the CON is sometimes used for some highly complex constitutive models when the
determination of the second derivatives of the yield function and plastic potential function is exceedingly laborious.

                                                          15

### Page 16

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

                                             Fig. 6. Flow chart of the stress updating algorithm.

However, it has been reported that the use of the CON affects the quadratic convergence speed of the global solution
and requires a much higher calculation cost. In what follows, the algebraic and geometric interpretations of the CTO
and CON are discussed first by a simple descriptive example that is analogous to Eq. (56). Then, the CTO and CON
of the MCC model, which is consistent with the unconstrained stress updating scheme, are derived.

5.1. Algebraic and geometric interpretations

  We specify a simple vector function {F} = { Fext} − {g0.51     g0.82 }T = {0} as an analog of the residual force
equation, in which {g0.51     g0.82 }T and {g} are used as the analog of {Fint} and {σ} in Eq. (56), respectively. The
constitutive equation used to evaluate {g} is defined by the following differential form:

      {dg} = [D (x)] {dx}                                                                                    (59)

where {x} is used as an analog of the strain {ε} (or displacement {U}). [D (x)] can be called the CON and is defined
in this descriptive example as follows:

           [ 1 + x1 + x2   0.2 + x1 + x2 ]
     [D (x)] =                                                                                             (60)
                 0.2 + x1 + x2   1 + x1 + x2

                                                          16

### Page 17

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

    If the state variables in the previous step are known, for the given {∆x}in+1, {g}in+1 can be determined based on
the backward Euler scheme as follows:
       {g}in+1 = [D (x)]in+1 ({x}in+1 −{x}n ) + {g}n                                                             (61)

  To facilitate the description of the differences and relations between the two tangent operators, the theoretical
solution of Eq. (59) (usually unknown) can be given as follows due to its simplicity:
          {x1 + 0.2x2 + 0.5 (x1 + x2)2 }
      {g} =                                                                                                 (62)
             0.2x1 + x2 + 0.5 (x1 + x2)2

   Then, the strain (displacement) correction can be obtained by:
      {δx}in+1 = − ( [K]in+1 )−1 {F}in+1                                                                        (63)
where [K]in+1 = [∂F/∂g]in+1 [∂g/∂x]in+1. The expression of [∂F/∂g]in+1 is:
    [∂F ]i        [0.5g−0.51       0   ]i
        = −                                                                                        (64)
      ∂g  n+1         0      0.8g−0.21     1,n+1
and the CTO of this example is:
    [∂g ]i            [∂D (x)    ]i    [ 1 + x1 + x2   0.2 + x1 + x2 ]i
        = [D (x)]in+1 +      ∆x   =
      ∂x  n+1                ∂x       n+1     0.2 + x1 + x2   1 + x1 + x2  n+1
                                        [1  1]
         + ( xi1,n+1 + xi2,n+1 −x1,n+1 −x2,n+1 )                                                       (65)
                                              1  1
    It is easy to see the differences and relations between the CTO ([∂g/∂x]in+1) and CON ([D (x)]in+1) from Eq. (65).
From the perspective of algebra, the CTO is the partial derivative of the numerical expression of stress (i.e., Eq. (61))
obtained by the backward Euler scheme to the strain, whereas the CON is the partial derivative of the theoretical
expression of stress (i.e., Eq. (62)) to the strain. The difference between the two tangent operators comes from the
approximation of the integral scheme to the constitutive equation in differential (or rate) form, and this difference
increases with increasing step size. In turn, the CTO degenerates to the CON when the step size tends to zero.
   In what follows, the influence of the CTO and CON on the convergence speed and stability of the global solution
is explored with different step sizes. The state variables of the previous equilibrium state are set to {x}n = {0.1, 0.2}T ,
{g}n = {0.23, 0.31}T , {Fint}n = { Fext}n = {0.230.5, 0.310.8}T and {F}n = {0, 0}T . The theoretical solution regarding
the global external force { Fext}    in the next equilibrium state can be obtained by substituting {∆x} into Eq. (61)                              n+1
and solving the force residual equation {F}n+1 = {0}. Then, the obtained theoretical solution of {Fext}n+1 is used
again as the applied external load. Fig. 7 shows the search paths with the two tangent operators and the corresponding
convergence maps, where the search behaviour is terminated once {F}n+1 ≤10−3.
  The results of the figures demonstrate that the term [(∂D (x) /∂x) ∆x]in+1 that causes differences between the CTO
and CON has little influence on the search direction when the step size is small. The search paths and iterations
based on the CON are similar to those based on the CTO, as shown in Fig. 7(a). With increasing step size, the
search direction based on the CON gradually deviates from the Newton direction. More iterations are required
compared to the same process with the CTO due to the lost quadratic convergence speed of the newton method, as
shown in Fig. 7(b) and (c). When {∆x} = {1.6, 1.6}T , the iterative search process with the CTO still converges to a
pre-defined value, but the iterative search with the CON diverges, as shown in Fig. 7(d). The reason for this is that
the initial point of the iteration is outside the convergence radius of the “newton method” perturbed by the CON.
Therefore, in applications, the use of the CON may necessitate rather small time steps to achieve the convergence
of the global equilibrium iteration.

5.2. Smoothing consistent and continuum tangent operators

   In the computational framework of the operator splitting technique, the expressions of the CTO and CON needed
to be determined by the different constitutive equations (the elastic equation or plastic equation) based on the

                                                          17

### Page 18

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

 Fig. 7. Search paths for global iteration: (a) {∆x} = {0.2, 0.2}T ; (b) {∆x} = {0.4, 0.4}T ; (c) {∆x} = {0.8, 0.8}T ; (d) {∆x} = {1.6, 1.6}T .

loading/unloading states of the material at the current incremental step. For the stress updating algorithm presented
in this paper, the two tangent operators can be derived in a unified framework due to the use of a smoothing function.
Taking the total differential of Eq. (34)4, we can obtain:

     ( ∂fn+1           ∂fn+1  ∂pc,n+1     )
     χ0             : dσn+1 +             d∆φn+1 + χ1d∆φn+1 = 0                                       (66)
         ∂σn+1           ∂pc,n+1 ∂∆φn+1

          √                   2                  √                   2where χ0 =  fn+1/  (cd∆φn+1)2 +  f n+1 + 2β + 1 and χ1 =  c2d∆φn+1/  (cd∆φn+1)2 +  f n+1 + 2β −cd  for
convenience when writing. dσn+1 can be expressed by:

           (                ∂fn+1 )
     dσn+1 = D:  dεn+1 −d∆φn+1                                                                         (67)
                                ∂σn+1
                                                          18

### Page 19

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

where the expression for d∆φn+1 can be obtained by putting Eq. (67) into Eq. (66) as follows:
                         χ0 ∂fn+1 : D: dεn+1
     d∆φn+1 =                 ∂σn+1                                                                         (68)
               χ0 ∂fn+1 : D: ∂fn+1 −χ0 ∂fn+1  ∂pc,n+1 −χ1                      ∂σn+1      ∂σn+1        ∂pc,n+1 ∂∆φn+1
   Substituting Eq. (66) back into Eq. (67) yields the expression of the CON:
                            χ0 ∂fn+1 : D: ∂fn+1
    DCON = D −                 ∂σn+1      ∂σn+1                                                            (69)
                  χ0 ∂fn+1 : D: ∂fn+1 −χ0 ∂fn+1  ∂pc,n+1 −χ1                         ∂σn+1      ∂σn+1        ∂pc,n+1 ∂∆φn+1
  As discussed in Section 4.1, the CTO of the MCC model based on the unconstrained integral scheme can be
obtained by computing the partial derivative of Eq. (24) to the strain εn+1 as follows:
        O   ∂σn+1    DCT =    = c0P + c11 ⊗1 + c21 ⊗ˆn + c3∆γn+1 ⊗1 + c4∆γn+1 ⊗ˆn + c5 ˆn ⊗1 + c6 ˆn ⊗ˆn       (70)
              ∂εn+1
where the derivation details of Eq. (70) are presented in Appendix B for the readability of the paper. The matrix
representation for the fourth-order tensor can be found in Appendix C.
    It is noteworthy that there is an interesting property regarding the CTO and CON based on the unconstrained
stress updating strategy. Taking the CON as an example, if the current step is elastoplastic loading, then ∆φn+1 > 0
and  fn+1 = 0. The result by which χ0 = 0 + 1 = 1 and χ1 = cd −cd = 0 is obtained when β is close to 0.
Substituting the conditions χ0 = 1 and χ1 = 0 into Eq. (69), Eq. (69) will degenerate into the plastic form of the
CON within the computational framework of operator splitting technique as follows:
                                  ∂fn+1 : D: ∂fn+1
    DCON = D −          ∂σn+1      ∂σn+1                                                                  (71)
                        ∂fn+1 : D: ∂fn+1 −  ∂fn+1  ∂pc,n+1                       ∂σn+1      ∂σn+1     ∂pc,n+1 ∂∆φn+1
   Similarly, ∆φn+1 = 0 and  fn+1 < 0 when the current step is elastic loading. Substituting the corresponding
results χ0 = 0 and χ1 = −cd into Eqs. (69). Eq. (69) can also degenerate into the elastic form of the CON based
on the operator splitting technique as follows:

    DCON = D                                                                                            (72)

   This property is also true for the smoothing CTO, which also means that the smoothing CTO is capable of
providing a smoothing transition for the description of mechanical behaviour of elastoplastic material even under
repeated loading and unloading conditions.

6. Numerical validation

  As mature finite-element simulation software, ABAQUS is an excellent analysis platform for assessing algorithm
performance. In this section, the MCC model is implemented in ABAQUS based on the proposed unconstrained
stress updating algorithm. Then, the performance of the proposed algorithm is analysed and discussed in depth with
a series of drained and undrained boundary value problems and is compared with the ABAQUS/Standard default
algorithm. As a necessary statement, the following numerical examples are run on a single processor of the same
computer. The computer configuration includes an Intel Core i7-9750 processor @ 2.60 GHz, 16 GB of RAM, and
the Windows 10 Ultimate 64-bit operating system. The tolerance of the proposed algorithm is set to FT OL = 10−6.

6.1. Element test

   First, to evaluate the convergence performance of the proposed algorithm in the local calculation, a simple
numerical example with only a single element is performed, where the possibility of calculation interruption caused
by newton iteration failure at the global scale is minimized. The parameters of the MCC model used for the
numerical example are given as follows: M = 1, λ = 0.15, κ = 0.03, ν = 0.3, and e0 = 0.5. The initial
stress state and the pre-consolidation pressure are set to σ1 = σ2 = σ3 = 200 kPa and pc = 200 kPa. Note that
the σn is used as the initial point for iteration to create a more demanding iteration condition in this subsection.
The loading paths of the element are shown in Fig. 8(a). During the loading process, a condition requiring equal

                                                          19

### Page 20

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

time step sizes is imposed. Following the unconstrained stress updating strategy presented in Section 2.2, the stress
and strain results for the Newton method and the non-monotonic trust region method are presented in Fig. 8(b)
to (f). The minimum number of load steps needed to achieve convergence for the two methods are first explored,
and then, for the NMTR method, the prediction results under the same steps as that used by the Newton method
are also presented. The N denotes the number of the load increment. Smaller N means greater load increment and
higher convergence challenges. As expected, the two different implementations give rise to the same results under
the same number of load steps, whereas a larger loading increment size is allowed for the NMTR method on the
premise of calculation convergence.
   Then, the effect of the non-monotonic technique on the trust region method in terms of improvement is presented
by two loading and unloading examples. The initial stress state of the numerical examples is represented by the point
A in Fig. 9(a). The parameters of the MCC model in the last example are also used here, but the pre-consolidation
pressure is set to pc = 218 kPa to ensure that the current yield curve passes through the initial stress point. The
strain increments are set to ∆ε1 = ∆ε2 = −0.015 and ∆ε3 = 0 for the unloading case and to ∆ε1 = ∆ε2 = 0.03
and ∆ε3 = 0 for the loading case. Only a single load step is considered. Fig. 9(b) and (c) show the changes
in {f (x)}n+1 as the number of iterations increases for the MTR method and the NMTR method under loading
and unloading cases, respectively. The two methods converge to results satisfying the tolerance requirement under
loading conditions, but a distinct computational challenge arises in the unloading case for the MTR method. The
reason for this result has been mentioned at the end of Section 2. Namely, for the unloading situation where the
initial stress point is on the yield surface, the smoothing function has a very large curvature due to the fact that
 f = 0 and ∆φ = 0, which easily causes the search behaviour based on the monotonic strategy to fall into a local
optimum. A similar phenomenon in which the MTR method may suffer from computational difficulty near areas of
high curvature has also been reported in the Ref. [30]. The search ability of the NMTR method is enhanced because
the merit function is allowed to increase limitedly at the local scope to achieve a better decline at the global scope.
Therefore, the convergence of the algorithm can be guaranteed even under the condition of high curvature. Notably,
the computational difficulty of the smoothing function near areas of high curvature can also be solved by choosing
an appropriate initial iteration point. For instance, the stress update in the unloading cases can be realized directly
without the need for second iterations when the elastic trial point is set to the initial iteration point.

6.2. Collapse of a rigid strip footing

   In this subsection, the effectiveness of the smoothing CTO and CON derived by the proposed algorithm is
investigated by simulating the collapse of a rigid strip footing, which is a well-known boundary value problem
for evaluating the stress updating algorithm used in the constitutive models of soils [8,12,64]. The ABAQUS
6.14/Standard default stress updating algorithm can be used as an objective standard for the validation of the
effectiveness of the smoothing CTO since the MCC model has been added to the ABAQUS/Standard Material
Library.
  The geometry information and element mesh of the footing are shown in Fig. 10(a) and (b), respectively. The
element 4 will be used for the following stress path analysis. The material parameters used for the MCC model are
obtained from the literature [64] as follows: M = 0.898, λ = 0.25, κ = 0.05, ν = 0.3, and e1 = 1.6, where e1 is
the critical state void ratio at p = 1 kPa. The submerged weight of the soil is set to 6 kN/m3. In the numerical
simulation, three analysis steps are used, including the geostatic stress analysis step, the unloading analysis step, and
the loading analysis step. In the geostatic stress analysis step, the initial stress field is generated by the self-weight
of the soil and the pre-load 50 kPa imposed on the surface of the soil, which is then removed completely with
2 equal time increment steps to generate the over-consolidation of the soil layer in the unloading analysis step.
Finally, in the load analysis step, the vertical displacement U3 = −0.16 m is imposed on the footing with 10 equal
time increment steps. The displacement field at the end of the loading process is presented in Fig. 10(b). In Fig. 11,
identical load–displacement responses and the stress paths are noted for the ABAQUS/Standard default algorithm
and the proposed algorithm, which further proves the reasonability of the proposed algorithm and the correctness
of UMAT. In addition, the shrinkage of the yield surface indicates that the soil near the integral point has softened
obviously, which also validates the effectiveness of the proposed algorithm in the softening stage. On the other
hand, the agreement between the results of the CTO and the CON shows that the control equations of the global
problem guarantee that the search behaviour based on these two tangent operators will reach the same optimal point

                                                          20

### Page 21

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

Fig. 8. Convergence test with a single element: (a) considered loading paths; (b) result in of path 1; (c) result of path 2; (d) result of path
3; (e) result of path 4; (f) result of in path 5.

after iterative convergence; namely, the use of the CON does not affect the calculation results on the premise of
convergence. However, it must be pointed out that the selections of the two tangent operators lead to differences in
computational efficiency.
   Fig. 12 shows the convergence process of the normalized largest residual force at the critical node. It is observed
that the convergence speed of the NMTR method with the CON is much slower than the ABAQUS/Standard
default algorithm and the NMTR method with the CTO. Compared with the examples using CTO, more than three

                                                          21

### Page 22

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

   Fig. 9. Comparison between the non-monotonic strategy and monotonic strategy: (a) load paths; (b) loading case; (c) unloading case.

                           Fig. 10. Collapse of a rigid strip footing: (a) model geometry; (b) finite element mesh.

                                                          22

### Page 23

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

Fig. 11. Comparison between the different algorithm for the strip footing example: (a) footing load versus footing displacement; (b) the
stress path of integral point 1 of element 4.

                  Fig. 12. Change in the normalized largest residual force with the iterations at each time increment step.

times the CPU time is required for the example using the CON. On the other hand, the convergence rates of the
ABAQUS/Standard default algorithm and the NMTR method with the CTO are basically the same, which further
verifies the effectiveness of smoothing CTO. The number of iterations needed to achieve global equilibrium at each
time step is presented in Fig. 13. The comparison result is consistent with the law shown in Fig. 12. Compared with
that for the CTO, more than three the number of global equilibrium iterations are required for the CON. Therefore,
it is probably best to use the CTO to achieve newton searches of global problems instead of the CON.

6.3. Undrained vertical compressive capacity test of pile foundation

  To further assess the algorithm’s effectiveness in addressing the geotechnical problems, a vertical compressive
capacity  test of pile foundation under the undrained condition  is simulated. The pile  is set in the normally
consolidated saturated clay and subjected to vertical displacement load. The pile in the problem is 10 m long
with a cross section of diameter 0.5 m. The vertical compressive capacity test of pile foundation can be regarded as
an axisymmetric problem. Therefore, the numerical model is simplified as a 2D numerical model shown in Fig. 14
where the geometry information and finite element mesh of the numerical model are presented. The four-node
axisymmetric element (CAX4) and four-node axisymmetric pore pressure element (CAX4P) are used for the pile

                                                          23

### Page 24

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

                                          Fig. 13. Number of iterations at each time increment step.

                Fig. 14. Vertical compressive capacity test of pile foundation: (a) model geometry; (b) finite element mesh.

and the soil, respectively, to implement such geometric simplification and to consider the pore pressure development.
The contact between the pile and the soil is considered as the frictional contact. The friction coefficient is 0.577.
  The MCC elastoplastic model and linear elastic model are employed for the soil and the pile, respectively. The
material parameters of the pile are set to: E = 20 GPa and ν = 0.2. The parameters of the MCC model are set to:
M = 1.2, λ = 0.2, κ = 0.04, ν = 0.35, e1 = 2, and kp = 3.6 × 10−4 m/h where kp is the permeability [65]. The
submerged weight of the soil and the weight of the water are set to 8 kN/m3 and 10 kN/m3, respectively. In the
numerical simulation, the initial stress field is generated in the geostatic stress analysis step where the except that
the pore water pressure boundary condition on the top of the soil is set to u p = 0 kPa, the other boundaries are

                                                          24

### Page 25

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

Fig. 15. Comparison between the different algorithms for the pile foundation example: (a) reaction force versus displacement; (b) distributions
of pore pressure, hydrostatic pressure, and generalized shear stress along the radial direction.

set to undrained. The vertical displacement load is applied on the top of the pile in the loading analysis step of the
soils type. The total time is set to 1 h to approximate undrained loading condition. The initial time increment and
the maximum time increment are set to 0.05 h and 0.5 h, respectively. The pore pressure field at the end of loading
is shown in Fig. 14(b). The identical reaction force and displacement curves of the top of the pile are presented
in Fig. 15(a) for the two algorithms. Fig. 15(b) shows the change of pore pressure and the stress along the radial
direction at ten metres depth. It can also be found that the results of the proposed algorithm are in good agreement
with that of the ABAQUS/Standard default algorithm.

6.4. Cylindrical sample with cyclically combined tension and shear

   Finally, the improvement of the proposed algorithm on the convergence behaviour of the global solution is
further investigated. Here, a problem involving cylinder sample with combined tension and shear is considered;
this problem has been used to evaluate the performance of the MTR method in Shterenlikht and Alexander’s [33]
and Lester and Scherzinger’s [30] works. One major difference between the question in this section and the one
in the literature [30,33] is that cyclic loading with more demand is used instead of monotonic loading to obtain
more complex stress conditions. In addition, the ABAQUS/Standard default stress updating algorithm is used as a
comparison object.
  The cylinder in the problem is 0.2 m long with a cross section of diameter 0.1 m, as shown in Fig. 16. The
initial stress state, the pre-consolidation pressure, and material parameters of the first example in Section 6.1 are
also used here. The origin of the global coordinate system is at the centre of the bottom face of the cylinder. All
degrees of freedom of the bottom face of the cylinder are fixed. The top face of the cylinder is fully coupled to
a reference point (0, 0, 0.25). The displacement load in the 1-direction is imposed on the top face of the cylinder
by the reference point. In this example, two load cases and three discretization types are used to evaluate the
performance of the algorithm. Fig. 17(a) shows the displacement time–history curve in the loading case a, which
is applied in a single load analysis step with 40 equidistant time steps. For the example analysis in the loading
case a, only the discretization a is used. The loading condition repeatedly suffering the stress behaviour transition
from elasticity to plasticity can be realized by the gradually increasing cyclic load in Fig. 17(a). The time–history
curves of the reaction force of the reference point for the two algorithms are demonstrated in Fig. 17(b). The results
obtained from the two algorithms are in good agreement, which also shows that the smoothing function is effective
in replacing the KT conditions.
  The numbers of global equilibrium iterations at each time step for the two algorithms are depicted in Fig. 18.
An oscillating number of iterations is observed for the ABAQUS/Standard default algorithm, while almost all
global equilibrium iterations can converge in two steps for the proposed algorithm. This trend may indicate that
the smoothing CTO seems to perform better than the CTO that follows the operator splitting technique under

                                                          25

### Page 26

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

                        Fig. 16. Geometry and discretization of the cylinder sample: (a) geometry; (b) discretization.

the condition of repeated loading/unloading because the smooth function eliminates the non-smoothness of the
elastoplastic problem.
   Furthermore, to investigate the influence of the NMTR method on the global calculation, the displacement
time history presented in Fig. 19(a) is imposed on the top face of the cylinder by the reference point. During
the calculation process, a total of 10 load analysis steps are used, where the new analysis step is activated once
the direction of the displacement load changes. During each analysis step, the initial time step is set to 0.1 s. The
adjustment of the following time step size is controlled by ABAQUS default automatic time stepping, and the
maximum time step size is the total time of the current load analysis step. In addition, all three discretization types
in Fig. 16(b) are used to further assess the algorithm performance.
  The reaction displacement curves of the reference point in the 1-direction are demonstrated for the different
discretizations types in Fig. 19(b) to (d). The Job information with the different discretizations is summarized in

                                                          26

### Page 27

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

                Fig. 17. Load and response in case a: (a) displacement load; (b) reaction force response in the 1-direction.

Fig. 18. Global equilibrium iterations at each time step: (a) NMTR with the smoothing CTO; (b) ABAQUS/Standard default integration
algorithm.

Table 1
Job information with the different discretizations.

 Discretization  Algorithms         Job status         CPU      Elements    Number of total/failed     Number of
                                         (Total time/s)          time/s     number       load increments               total/failed iterations

              ABAQUS/Standard                        428.2                 587          118        793          140
 a                               Completed (51)                2520
          NMTR with CTO                         192.4                 150          14         376          21

              ABAQUS/Standard                        315.9                 1102         240        1370         254
 b                               Completed (51)                2628
          NMTR with CTO                          98.3                  170          19         467          31

              ABAQUS/Standard  Aborted (10.2964)     376.9                 404          97         588          151
 c                                                           2771
          NMTR with CTO   Aborted (12.1412/     227.8                 140          30         356          97
                                    10.2964)               (133.7)                   (84)            (13)         (210)           (26)

Table 1. It should be noted that, in the case of the discretization c, the ABAQUS/Standard default algorithm is
aborted earlier than the proposed algorithm. Therefore, Table 1 additionally supplements the Job information of
the proposed algorithm under the same analysis step time as the ABAQUS/Standard default algorithm so as to
compare the computational efficiency difference between them under the same condition. It can be found that the
reaction displacement curves obtained by the proposed algorithm are in good agreement with those obtained by

                                                          27

### Page 28

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

Fig. 19. Load and response in case b: (a) displacement load; (b) reaction force versus displacement for discretization a; (c) reaction force
versus displacement for discretization b; (d) reaction force versus displacement for discretization c.

the ABAQUS algorithm, while the former has significant computational savings compared with the latter. In what
follows, the result with the discretization a is used as an example to present the convergence advantages of the
proposed algorithm in more detail. Fig. 20(a) shows that the changes in the time step size for the two algorithms
for the discretization a. During the initial loading period, the time step sizes of the two algorithms are basically
the same. Then, compared with those of the ABAQUS/Standard default algorithm, larger time steps are allowed
for the proposed stress updating algorithm. The CPU time consumed by the proposed algorithm is only 44.9%
of that of the ABAQUS/Standard default algorithm. There are a few main reasons for this difference. On the one
hand, in contrast to the ABAQUS/Standard default algorithm, a local problem may be solved by the NMTR method
even under larger, more complex loadings, thereby enabling the global solution to be found. On the other hand, as
discussed earlier, the use of the smoothing CTO is capable of effectively guaranteeing the convergence behaviour of
the global solution even under repeated loading and unloading conditions because the smoothing function eliminates
the non-smoothness of the elastoplastic problem. Based on these two improvements, costly cutbacks to the time
step size are avoided due to the effective treatment of the non-smoothness and nonlinearity of the initial value
problem by the proposed algorithm. As shown in Fig. 20(b) and (c), the number of failed attempts encountered by
the proposed algorithm is only 11.9% of that of the ABAQUS/Standard default algorithm, and for the number of
global equilibrium iterations wasted on the failed attempts, the former is only 15.0% of the latter. Therefore, during
each load analysis step, the displacement load can be applied in fewer incremental steps by the proposed algorithm,
as shown in Fig. 20(d). During the whole loading process, the number of total load increment steps required by the
proposed algorithm is only 25.6% of that required by the ABAQUS/Standard default algorithm. Correspondingly, the
number of global equilibrium iterations occupying the main computing resources can be reduced by the proposed
algorithm, as shown in Fig. 20(e). The number of total global equilibrium iterations required by the proposed
algorithm is only 47.4% of that required by the ABAQUS/Standard default algorithm.

                                                          28

### Page 29

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

Fig. 20. Convergence behaviour at each load analysis step: (a) change in the time step size; (b) the number of load increments in the failed
attempts; (c) the number of global equilibrium iterations in the failed attempts; (d) the number of total load increments; (e) the number of
total global equilibrium iterations.

7. Conclusion

  A stress updating algorithm for evaluating internal state variables and the CTO for forming global stiffness play a
striking role in nonlinear finite-element analysis involving a constitutive model. In this paper, an unconstrained stress
updating strategy is proposed based on the FB smoothing function. The smoothing CTO and CON corresponding
to this strategy are derived. In particular, the algebraic and geometric interpretations of the two tangent operators
are discussed and analysed in depth. Furthermore, the NMTR method with strong convergence and robustness
is used to solve the nonlinear governing equations of the MCC model. Finally, the MCC model is implemented
in ABAQUS via UMAT based on the proposed algorithm to analyse a series of boundary value problems. The
correctness and computational efficiency of the proposed algorithm are proven and evaluated via a comparison with
the ABAQUS/Standard default stress updating algorithm.
  From the perspective of algorithmic structure, there is no need for the loading/unloading judgment step, and the
additional consideration of the stress behaviour transition from elasticity to plasticity for the unconstrained stress
updating strategy, where the only adjustment made is to use the FB smoothing function equivalently instead of
KT conditions. The elastic CTO and the plastic CTO within the computational framework of the operator splitting
technique can be united by the smoothing CTO derived by the unconstrained stress updating strategy. Therefore,
the stress update process of the constitutive model can be realized in a simpler procedure. From the perspective of
computational efficiency and robustness, larger strain increments are allowed for stress updating in local calculations
due to the use of the NMTR method. The non-smoothness in the elastic to plastic transition is also eliminated by
the smoothing function. This makes the computational efficiency and robustness of the proposed algorithm under
the condition of large time increments and cyclic loadings better than those of the ABAQUS/Standard default. The
representative numerical examples show that the CPU time consumed by the proposed algorithm is less than half
of that consumed by the ABAQUS/Standard default.
  The proposed algorithm presents an exciting possibility for the improvement of the stress updating procedure
used for the elastoplastic model. The ability of this algorithm to further address the implementation of more

                                                          29

### Page 30

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

challenging models (e.g., a multi-yield surface or coupled physics) remains to be explored, whereas it is certain that
the result is undoubtedly very promising because the proposed algorithm catches hold of the key to solve initial
value problems, i.e., non-smoothness and nonlinearity. The source code provided is capable of creating an easier
research environment for these promising works.

Declaration of competing interest

  The authors declare that they have no known competing financial interests or personal relationships that could
have appeared to influence the work reported in this paper.

Acknowledgements

   This work was supported by the National Natural Science Foundation of China (Grant Nos., 52025084 and
51778026).

Appendix A. Elements in a Jacobian matrix

  To facilitate the derivation of the Jacobian matrix {∇f} of residual equations in Eq. (34), the derivatives of ∆εev
with respect to the unknown variables pn+1, qn+1, pc,n+1, and ∆φn+1 are derived first. ∆εev can be expressed as
follows:
    ∆εev,n+1 = ∆εv,n+1 −∆εpv,n+1 = ∆εv,n+1 −∆φn+1 ( 2pn+1 −pc,n+1 )                                  (A.1)

   Taking the derivative of Eq. (A.1), we can obtain:
   ⎧ ∂∆εpv,n+1
          = 2∆φn+1
        ∂pn+1
      ∂∆εpv,n+1
          = 0                                       ⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎨  ∂qn+1                                                                                                        (A.2)
      ∂∆εpv,n+1
          = −∆φn+1
         ∂pc,n+1
      ∂∆εpv,n+1
          = 2pn+1 −pc,n+1                                       ⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎩ ∂∆φn+1

   Then, the derivatives of the secant shear modulus G with respect to the unknown variables pn+1, qn+1, pc,n+1,
and ∆φn+1 can be easily obtained. The expression of G is:
              pn     [(1 + e     )   ]
   G =        exp       ∆εev,n+1 −1  r                                                          (A.3)
         ∆εev,n+1        κ

   Taking the derivatives of Eq. (A.3) and based on the chain rule, we can obtain:

   ⎧ ∂G          Kn+1 −K
        = −2               r∆φn+1
       ∂pn+1      ∆εv,n+1 −∆εpv,n+1
      ∂G
        = 0                                          ⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎨ ∂qn+1
                            k                                                                                   (A.4)
      ∂G    K n+1 −K
         =         r∆φn+1
        ∂pc,n+1    ∆εev,n+1
       ∂G          n+1k −K         = −K         r ( 2pn+1 −pc,n+1 )                                          ⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎩ ∂∆φn+1     ∆εev,n+1
                                                          30

### Page 31

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

   In what follows, the elements in the Jacobian matrix of the residual equation are given successively. The
derivatives of  f1 are
   ⎧        ∂f1           f1,1 =    = cd (1 + 2∆φn+1Kn+1)
             ∂pn+1
                ∂f1
           f1,2 =    = 0                                 ⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎨      ∂qn+1                                                                                                        (A.5)
                ∂f1
           f1,3 =     = −cd∆φn+1Kn+1
               ∂pc,n+1
                 ∂f1
           f1,4 =     = cd ( 2pn+1 −pc,n+1 ) Kn+1                                 ⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎩            ∂∆φn+1

where

     Kn+1 = cκ pn exp {cκ [∆εv,n+1 −∆φn+1 ( 2pn+1 −pc,n+1 )]}                                          (A.6)

  The derivatives of  f2 are
   ⎧        ∂f2   √ 3     (                         )           f2,1 =    = −               2ˆn: ∆γn+1 −6η∆φn+1  + 2G∆γn+1                                                                                 sn                                 ∂pn+1      2cdη∂G∂p             M2
                ∂f2
           f2,2 =    = cd
             ∂qn+1                                          ⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎨                                                                                                        (A.7)                ∂f2    √ 3    ∂G  (                         )           f2,3 =     = −                   2ˆn: ∆γn+1 −6η∆φn+1  + 2G∆γn+1               ∂pc,n+1       2cdη ∂pc,n+1            M2     sn                    
                 ∂f2    √ 3   [        ∂G                 (      ∂G     )]           f2,4 =     = −          2ˆn: ∆γn+1     −6η   + 2G∆γn+1   ∆φn+1     + G                                       M2 sn                           ∂∆φn+1                                          ⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎩      ∂∆φn+1       2cdη          ∂∆φn+1
where ∥·∥is the 2-norm, ˆn: ∆γn+1 = ˆni jγi j = n11γ11 + n22γ22 + n33γ33 + 2 (n12γ12 + n23γ23 + n13γ13), and

   ⎧           1      η =
      ⎪⎨    1 + 6G∆φn+1/M2                                                                           (A.8)              sn+1
           ˆn =
      ⎪⎩    ∥sn+1∥
  The derivatives of  f3 are
   ⎧        ∂f3           f3,1 =    = cd { −2cp∆φn+1 pc,n exp [ cp∆φn+1 ( 2pn+1 −pc,n+1 )]}
             ∂pn+1
                ∂f3
           f3,2 =    = 0                                 ⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎨      ∂qn+1                                                                                                        (A.9)
                ∂f3
           f3,3 =     = cd {1 + cp∆φn+1 pc,n exp [cp∆φn+1 ( 2pn+1 −pc,n+1 )]}
               ∂pc,n+1
                 ∂f3
           f3,4 =     = −cdcp ( 2pn+1 −pc,n+1 ) pc,n exp [cp∆φn+1 ( 2pn+1 −pc,n+1 )]                                 ⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎩            ∂∆φn+1
  The derivatives of  f4 are
   ⎧        ∂f4
           f4,1 =    = χ0 ( 2pn+1 −pc,n+1 )
             ∂pn+1
                ∂f4       2qn+1
           f4,2 =    = χ0                                    ⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎨      ∂qn+1     M2                                                                                                    (A.10)
                ∂f4
           f4,3 =     = −χ0 pn+1
               ∂pc,n+1
                 ∂f4
           f4,4 =     = χ1                                    ⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎩      ∂∆φn+1
                                                          31

### Page 32

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

where⎧       ∂f4                 fn+1
       χ0 =    =               + 1
             ∂fn+1  √                      (cd∆φn+1)2 +  f n+12 + 2β                  ⎪⎪⎪⎪⎪⎨                                                                                                    (A.11)
               ∂f4               c2d∆φn+1
           ∂∆φn+1  √                        (cd∆φn+1)2 +  f n+12 + 2β                  ⎪⎪⎪⎪⎪⎩ χ1 =     =                    −cd

Appendix B. Smoothing consistent tangent operator

   Taking the derivative of Eq. (A.3), we can obtain:
     ∂σn+1                ∂sn+1       = 1 ⊗∂pn+1 +                                                                               (B.1)
      ∂εn+1        ∂εn+1   ∂εn+1
where ∂pn+1/∂εn+1 is:
     ∂pn+1       [       (           )                ∂∆φn+1 ]       = Kn+1  1 −∆φn+1  2∂pn+1 −∂pc,n+1 − ( 2pn+1 −pc,n+1 )                                 (B.2)
      ∂εn+1                       ∂εn+1    ∂εn+1                      ∂εn+1
where
      ∂pc,n+1         [    (           )                ∂∆φn+1 ]        = pc,n+1cp ∆φn+1  2∂pn+1 −∂pc,n+1 + ( 2pn+1 −pc,n+1 )                                 (B.3)
      ∂εn+1                      ∂εn+1    ∂εn+1                      ∂εn+1
  By simultaneously addressing Eqs. (B.2) and (B.3), the following expressions can be obtained with the only
∂∆φn+1/∂εn+1 unknown as follows:
     ∂pn+1                  ∂∆φn+1
       = a1Kn+11 + a2Kn+1                                                                          (B.4)
      ∂εn+1                      ∂εn+1
      ∂pc,n+1                  ∂∆φn+1
        = a3Kn+11 + a4Kn+1                                                                        (B.5)
      ∂εn+1                       ∂εn+1
where the coefficients a1, a2, a3, and a4 are expressed by:
   ⎧a0 = 1 + pc,n+1cp∆φn+1 + 2∆φn+1Kn+1
       a1 = ( 1 + pc,n+1cp∆φn+1 ) /a0                           ⎪⎪⎪⎪⎪⎪⎪⎪⎨       a2 = − ( 2pn+1 −pc,n+1 ) /a0                                                                        (B.6)
       a3 = 2pc,n+1cp∆φn+1/a0
                           ⎪⎪⎪⎪⎪⎪⎪⎪⎩a4 = pc,n+1cp ( 2pn+1 −pc,n+1 ) / (a0Kn+1)
  ∂∆φn+1/∂εn+1 can be derived by imposing the consistency condition of Eq. (34)4. Taking the differentiation of
Eq. (34)4 can yield:
      ∂f4 (  ∂f    ∂sn+1     ∂f  ∂pn+1     ∂f   ∂pc,n+1 )     ∂f4  ∂∆φn+1
                           :    +       +          +          = 0                       (B.7)
      ∂f   ∂sn+1  ∂εn+1   ∂pn+1 ∂εn+1    ∂pc,n+1 ∂εn+1     ∂∆φn+1  ∂εn+1
where the partial derivatives of the yield function with respect to sn+1, pn+1, and pc,n+1 are:
   ⎧  ∂f      3
        =     sn+1
                     ⎪⎪⎪⎪⎪⎪⎨ ∂sn+1∂f    M2        = 2pn+1 −pc,n+1                                                                            (B.8)
       ∂pn+1
         ∂f
         = −pn+1                     ⎪⎪⎪⎪⎪⎪⎩ ∂pc,n+1
   Taking the derivative of Eq. (28) with respect to εn+1 and noticing that ∆φn+1 and G are also functions of εn+1
can yield:
      ∂sn+1    (       ∂G     )               ( 6G ∂∆φn+1   6∆φn+1 ∂G )
       = 2η  ∆γn+1 ⊗    + GP −η2 ( sn + 2G∆γn+1 ) ⊗        +                       (B.9)
      ∂εn+1                 ∂εn+1                       M2  ∂εn+1     M2   ∂εn+1

                                                          32

### Page 33

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

  The expression of ∂G/∂εn+1 is as follows:
     ∂G    ∂G  ∂pn+1    ∂G   ∂∆εev,n+1    (r Kn+1 −G ) (       ∂∆φn+1 )
       =       +           =              a11 + a2                            (B.10)
      ∂εn+1   ∂pn+1 ∂εn+1   ∂∆εev,n+1  ∂εn+1      ∆εev,n+1              ∂εn+1
   Putting Eq. (B.10) into Eq. (B.9) can obtain the new expression of ∂sn+1/∂εn+1 with the only unknown
∂∆φn+1/∂εn+1 as follows:
      ∂sn+1      [    ∆γn+1    Kn+1 −G (       ∂∆φn+1 )]       = 2Gη P +    ⊗r           a11 + a2
      ∂εn+1          G      ∆εev,n+1             ∂εn+1
         √
              6qGη   [ ∂∆φn+1   ∆φn+1 r Kn+1 −G (       ∂∆φn+1 )]        −2            ˆn ⊗      +                   a11 + a2                                (B.11)
             M2          ∂εn+1    G    ∆εev,n+1             ∂εn+1

   Then, substituting Eqs. (B.4), (B.5), and (B.11) into Eq. (B.7) and rearranging the expression can yield
     ∂∆φn+1
        = b11 + b2 ˆn                                                                            (B.12)
       ∂εn+1
where
   ⎧     {[(  ˆn             )   r Kn+1 −G     ] 12qη        b0 = χ0   √   : ∆γn+1 −q∆φn+1  a2      −qG
                   6         M2       ∆εev,n+1    M2  M2
                             }
      + [(2a2 −a4) pn+1 −a2 pc,n+1 ] Kn+1 + χ1                                                   ⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎨
            [(  ˆn             ) 12qa1η r Kn+1 −G                 ]/        b1 = −χ0  √   : ∆γn+1 −q∆φn+1            + (2a1 −a3) pn+1Kn+1 −a1 pc,n+1Kn+1     b0
                    6         M2     M2   ∆εev,n+1
          √
                2 6qGη /
        b2 = −χ0             b0                                                   ⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎩         M2

                                                                                                       (B.13)

   Putting Eq. (B.12) into Eq. (B.4) and Eq. (B.9) can yield:
     ∂pn+1
       = a1Kn+11 + a2Kn+1 ( b11 + b2 ˆn)                                                          (B.14)
      ∂εn+1
      ∂sn+1     {     r Kn+1 −G                          }
       = 2Gη P +             [(a1 + a2b1) ∆γn+1 ⊗1 + a2b2∆γn+1 ⊗ˆn]
      ∂εn+1           G∆εev,n+1
         √
               6qGη [(      (r Kn+1 −G ) ∆φn+1       )         −2           b1 +                      (a1 + a2b1)   ˆn ⊗1                              (B.15)
              M2            G∆εev,n+1
           (          (r Kn+1 −G ) ∆φn+1 )    ]
         +  b2 + a2b2                                  ˆn ⊗ˆn
                        G∆εev,n+1

   Finally, putting Eqs. (B.14) and (B.14) into Eq. (B.1), the CTO can result in the following:

     ∂σn+1                                                  Kn+1 −G       = 2GηP + (a1 + a2b1) Kn+11 ⊗1 + a2b2Kn+11 ⊗ˆn + 2ηr           (a1 + a2b1) ∆γn+1 ⊗1
      ∂εn+1                                               ∆εev,n+1
                         √
                           r Kn+1 −G              6qη [        (r Kn+1 −G ) ∆φn+1        ]             +2a2ηb2         ∆γn+1 ⊗ˆn −2      b1G +                      (a1 + a2b1)   ˆn ⊗1
                     ∆εev,n+1            M2              ∆εev,n+1
         √
                 6qη (            (r Kn+1 −G ) ∆φn+1 )         −2      b2G + a2b2                                  ˆn ⊗ˆn
             M2                 ∆εev,n+1

                                                                                                       (B.16)

                                                          33

### Page 34

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

  Based on Eq. (B.16), the coefficients of the tensor in Eq. (70) can be given as follows:
   ⎧ c0 = 2Gη
        c1 = (a1 + a2b1) Kn+1
        c2 = a2b2Kn+1
                               r Kn+1 −G
        c3 = 2 (a1η + a2ηb1)
                        ∆εev,n+1
                     r Kn+1 −G                                                                ⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎨        c4 = 2a2ηb2                                                                                                       (B.17)
                 ∆εev,n+1
        √
              6qη [                    (r Kn+1 −G ) ∆φn+1 ]        c5 = −2      b1G + (a1 + a2b1)
           M2                       ∆εev,n+1
        √
              6qη [            (r Kn+1 −G ) ∆φn+1 ]        c6 = −2      b2G + a2b2
           M2                 ∆εev,n+1                                                                ⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎪⎩

Appendix C. Matrix representation of tensors

   In the numerical implementation of the model, the second-order tensor and fourth-order tensor can be expanded
into a 6-by-1 matrix and a 6-by-6 matrix, respectively, for more efficient computing due to their inherent symmetry.
  The matrix expressions of the second order in this paper are given as follows:
  1 = δi jei ⊗e j, where ei and e j are the orthonormal bases of the second-order tensor, and the component δi j is
the Kronecker delta, which can be expressed by:
        δi j = [1  1  1  0  0  0]T                                                                          (C.1)
  ∂f/∂σ = ∂f/∂σi jei ⊗e j, where the components of ∂f/∂σi j can be expressed by:
      ∂f
      = [∂f/∂σ11  ∂f/∂σ22  ∂f/∂σ33  2∂f/∂σ12  2∂f/∂σ23  2∂f/∂σ13 ]T                            (C.2)
      ∂σi j
  ∆σ = ∆σi jei ⊗e j, where the components of ∆σi j can be expressed by:
     ∆σi j = [∆σ11  ∆σ22  ∆σ33  ∆σ12  ∆σ23  ∆σ13 ]T                                                 (C.3)
  ∆εn+1 = ∆εi jei ⊗e j, where the components of ∆εi j can be expressed by:
     ∆εi j = [∆ε11  ∆ε22  ∆ε33  ∆ε12  ∆ε23  ∆ε13 ]T                                                  (C.4)
  ∆γn+1 = ∆γi jei ⊗e j, where the components of ∆γi j = ∆εi j −δi j∆εv/3 can be expressed by:
     ∆γi j = [∆γ11  ∆γ22  ∆γ33  ∆γ12  ∆γ23  ∆γ13 ]T                                                 (C.5)
    ˆn = ˆni jei ⊗e j, where the components of ˆni j can be expressed by:
                                          1
          ˆni j = [ˆn11   ˆn22   ˆn33   ˆn12   ˆn23   ˆn13 ]T =      [s11   s22   s33   s12   s23   s13 ]T                       (C.6)
                                            ∥s∥
  The matrix expression of the fourth order is:
   I = 1 ⊗1 = δi jδklei ⊗e j ⊗ek ⊗el, where ei, e j, ek, and el are the orthonormal bases of the fourth-order tensor
and the components δi jδkl can be expressed by:
        ⎡1  1  1  0  0  0 ⎤

             1  1  1  0  0  0

             1  1  1  0  0  0
        δi jδkl =                                                                                              (C.7)
             0  0  0  0  0  0

             0  0  0  0  0  0                                                                                                ⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎣                                                                                                                                    ⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎦
             0  0  0  0  0  0

                                                          34

### Page 35

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

    Ivol = 131 ⊗1 = 13δi jδklei ⊗e j ⊗ek ⊗el, where the components 3δi1   jδkl can be expressed by:

          ⎡ 1  1  1  0  0  0 ⎤

                1  1  1  0  0  0

     1       1  1  1  1  0  0  0
      3δi jδkl = 3  0  0  0  0  0  0                                                                    (C.8)

                0  0  0  0  0  0                                                                                                                           ⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎣                                                                                                                                    ⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎦
                0  0  0  0  0  0

   Isym = 12 ( δikδ jl + δilδ jk ) ei ⊗e j ⊗ek ⊗el, where the components 12 ( δikδ jl + δilδ jk ) can be expressed by:

               ⎡ 1  0  0  0    0    0 ⎤

                        0  1  0  0    0    0

     1                 0  0  1  0    0    0
        ( δikδ jl + δilδ jk ) =                                                                                  (C.9)
     2                 0  0  0  1/2  0    0

                        0  0  0  0    1/2  0                                                                                                                                                                                      ⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎣                                                                                                                                                                                    ⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎦
                        0  0  0  0    0    1/2

  D = 3Ivol ( K −23G ) + 2IsymG = Di jklei ⊗e j ⊗ek ⊗el, where the components Di jkl can be expressed by:

                               ⎡    1                     ⎤                                    K +    K −2   K −2    0   0   0                                      3G     3G     3G
                                    K −2   K + 1   K −2    0   0   0                                      3G     3G     3G
            (     )     Di jkl = δi jδkl  K −2                                                                          jl + δilδ jk ) G =                                    K −2   K −2   K + 1    0   0   0      (C.10)                3G + ( δikδ                                      3G     3G     3G
                                                  0        0        0    G  0   0
                                                  0        0        0     0  G  0                                                                                                                                                                                                                                                                                                                                                                                                                         ⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎣                                                                                                                                                                                                                                                                                                                                       ⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎦
                                                  0        0        0     0   0  G

  P is the fourth-order projection tensor and P = ( δikδ jl −13δi jδkl ) ei ⊗e j ⊗ek ⊗el where the components
δikδ jl −13δi jδkl can be expressed by:

              ⎡ 2  −1  −1  0  0  0 ⎤
                      3     3    3
               −1   2  −1  0  0  0
                       3   3     3
               −1  −1   2   0  0  0
                       3    3   3      δikδ jl −1   jδkl =              3δi                      1                                                           (C.11)
                      0    0    0       0  0
                                     2
                                        1
                      0    0    0   0      0
                                        2                                                                                                                                                                                                                                                       ⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎣                      1   ⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎦
                      0    0    0   0  0
                                            2
                                                          35

### Page 36

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

  1 ⊗ˆn = δi j ˆnklei ⊗e j ⊗ek ⊗el, where the components δi j ˆnkl can be expressed by:

        ⎡ˆn11   ˆn22   ˆn33   ˆn12   ˆn23   ˆn13 ⎤
                     ˆn11   ˆn22   ˆn33   ˆn12   ˆn23   ˆn13
                     ˆn11   ˆn22   ˆn33   ˆn12   ˆn23   ˆn13
        δi j ˆnkl =                                                                                          (C.12)
              0    0    0    0    0    0

              0    0    0    0    0    0                                                                                                  ⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎣                                                                                                                                                                                                                  ⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎦
              0    0    0    0    0    0

  ∆γn+1 ⊗1 = γi jδklei ⊗e j ⊗ek ⊗el, where the components γi jδkl can be expressed by:

         ⎡ ∆γ11  ∆γ11  ∆γ11  0  0  0⎤

               ∆γ22  ∆γ22  ∆γ22  0  0  0

               ∆γ33  ∆γ33  ∆γ33  0  0  0
     ∆γi jδkl =                                                                                        (C.13)
               ∆γ12  ∆γ12  ∆γ12  0  0  0

               ∆γ23  ∆γ23  ∆γ23  0  0  0                                                                                                               ⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎣                                                                                                                                                                                                                 ⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎦
               ∆γ13  ∆γ13  ∆γ13  0  0  0

  ∆γn+1 ⊗ˆn = ∆γi j ˆnklei ⊗e j ⊗ek ⊗el, where the components ∆γi j ˆnkl can be expressed by:

         ⎡ ∆γ11 ˆn11  ∆γ11 ˆn22  ∆γ11 ˆn33  ∆γ11 ˆn12  ∆γ11 ˆn23  ∆γ11 ˆn13 ⎤
               ∆γ22 ˆn11  ∆γ22 ˆn22  ∆γ22 ˆn33  ∆γ22 ˆn12  ∆γ22 ˆn23  ∆γ22 ˆn13
               ∆γ33 ˆn11  ∆γ33 ˆn22  ∆γ33 ˆn33  ∆γ33 ˆn12  ∆γ33 ˆn23  ∆γ33 ˆn13
     ∆γi j ˆnkl =                                                                                       (C.14)
               ∆γ12 ˆn11  ∆γ12 ˆn22  ∆γ12 ˆn33  ∆γ12 ˆn12  ∆γ12 ˆn23  ∆γ12 ˆn13
               ∆γ23 ˆn11  ∆γ23 ˆn22  ∆γ23 ˆn33  ∆γ23 ˆn12  ∆γ23 ˆn23  ∆γ23 ˆn13                                                                                                                 ⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎣                                                                                                                                                                                                                                                                                                                                                                                                                               ⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎦
               ∆γ13 ˆn11  ∆γ13 ˆn22  ∆γ13 ˆn33  ∆γ13 ˆn12  ∆γ13 ˆn23  ∆γ13 ˆn13

    ˆn ⊗1 = ˆni jδklei ⊗e j ⊗ek ⊗el, where the components ˆni jδkl can be expressed by:

        ⎡ ˆn11   ˆn11   ˆn11  0  0  0⎤
                     ˆn22   ˆn22   ˆn22  0  0  0
                     ˆn33   ˆn33   ˆn33  0  0  0
          ˆni jδkl =                                                                                          (C.15)
                     ˆn12   ˆn12   ˆn12  0  0  0
                     ˆn23   ˆn23   ˆn23  0  0  0                                                                                                  ⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎣                                                                                                                                                                           ⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎦
                     ˆn13   ˆn13   ˆn13  0  0  0

    ˆn ⊗ˆn = ˆni j ˆnklei ⊗e j ⊗ek ⊗el, where the components ˆni j ˆnkl can be expressed by:

        ⎡ ˆn11 ˆn11   ˆn11 ˆn22   ˆn11 ˆn33   ˆn11 ˆn12   ˆn11 ˆn23   ˆn11 ˆn13 ⎤
                      ˆn22 ˆn11   ˆn22 ˆn22   ˆn22 ˆn33   ˆn22 ˆn12   ˆn22 ˆn23   ˆn22 ˆn13
                      ˆn33 ˆn11   ˆn33 ˆn22   ˆn33 ˆn33   ˆn33 ˆn12   ˆn33 ˆn23   ˆn33 ˆn13
          ˆni j ˆnkl =                                                                                         (C.16)
                      ˆn12 ˆn11   ˆn12 ˆn22   ˆn12 ˆn33   ˆn12 ˆn12   ˆn12 ˆn23   ˆn12 ˆn13
                      ˆn23 ˆn11   ˆn23 ˆn22   ˆn23 ˆn33   ˆn23 ˆn12   ˆn23 ˆn23   ˆn23 ˆn13                                                                                                    ⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎣                                                                                                                                                                                                                                                                                                                                                  ⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎦
                      ˆn13 ˆn11   ˆn13 ˆn22   ˆn13 ˆn33   ˆn13 ˆn12   ˆn13 ˆn23   ˆn13 ˆn13

                                                          36

### Page 37

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

References

  [1] A. Schofield, P. Wroth, Critical State Soil Mechanics, Cambridge University Press, 1968, <http://www.geotechnique.info/>.
  [2]  J.D. Zhao, Z.W. Gao, Unified anisotropic elastoplastic model for sand, J. Eng. Mech. 142 (1) (2016) 4015056.
  [3] Z.W. Gao, J.D. Zhao, X.S. Li, et al., A critical state sand plasticity model accounting for fabric evolution, Int. J. Numer. Anal. Methods
     Geomech. 38 (4) (2014) 370–390.
  [4] Z.W. Gao, A. Diambra, A multiaxial constitutive model for fibre-reinforced sand, Géotechnique 71 (6) (2021) 548–560.
  [5]  Y.P. Yao, L. Niu, W.J. Cui, Unified hardening (UH) model for overconsolidated unsaturated soils, Can. Geotech.  J. 51 (7) (2014)
     810–821.
  [6] D.M. Potts, W.J. Cui, L. Zdravkovi´c, A coupled THM finite element formulation for unsaturated soils and a strategy for its nonlinear
      solution, Comput. Geotech. 136 (2021) 104221.
  [7]  R.I. Borja, Cam-Clay  plasticity, Part  II: Implicit integration of constitutive equation based on a nonlinear elastic stress predictor,
     Comput. Methods Appl. Mech. Engrg. 88 (2) (1991) 225–240.
  [8] K. Krabbenhoft, A.V. Lyamin, Computational Cam clay plasticity using second-order cone programming, Comput. Methods Appl.
     Mech. Engrg. 209–212 (2012) 239–249.
  [9] S.W. Sloan, A.J. Abbo, D. Sheng, Refined explicit integration of elastoplastic models with automatic error control, Eng. Comput. 18
      (1/2) (2001) 121–194.
[10] M. Haliloviˇc, M. Vrh, B. Štok, NICE—an explicit numerical scheme for efficient integration of nonlinear constitutive equations, Math.
     Comput. Simulation 80 (2) (2009) 294–313.
[11]  J.C. Simo, T.J. Hughes, Computational Inelasticity, Springer Science & Business Media, New York, 2006.
[12] H. Zheng, T. Zhang, Q.S. Wang, The mixed complementarity problem arising from non-associative plasticity with non-smooth yield
      surfaces, Comput. Methods Appl. Mech. Engrg. 361 (2020) 112756.
[13] B.S. He, A class of projection and contraction methods for monotone variational inequalities, Appl. Math. Optim. 35 (1) (1997) 69–76.
[14] K. Krabbenhoft, A.V. Lyamin, S.W. Sloan, et al., An interior-point algorithm for elastoplasticity, Internat. J. Numer. Methods Engrg.
     69 (3) (2007) 592–626.
[15] L. Scheunemann, P. Nigro,  J. Schröder, et  al., A novel algorithm for rate independent small strain crystal plasticity based on the
      infeasible primal–dual interior point method, Int. J. Plast. 124 (2020) 1–19.
[16] H.K. Akpama, M.B. Bettaieb,  F. Abed Meraim, Numerical integration of rate-independent BCC single crystal  plasticity models:
      comparative study of two classes of numerical algorithms, Internat. J. Numer. Methods Engrg. 108 (5) (2016) 363–422.
[17]  P. Areias, One-step semi-implicit integration of general finite-strain plasticity models, Int. J. Mech. Mater. Des. 17 (1) (2021) 73–87.
[18]  P. Areias, K. Matouš, Finite element formulation for modeling nonlinear viscoelastic elastomers, Comput. Methods Appl. Mech. Engrg.
     197 (2008) 4702–4717.
[19] G. Scalet, F. Auricchio, Computational methods for elastoplasticity: an overview of conventional and less-conventional approaches,
     Arch. Comput. Methods Eng. 25 (3) (2018) 545–589.
[20] M. Schmidt-Baldassari, Numerical concepts for rate-independent single crystal plasticity, Comput. Methods Appl. Mech. Engrg. 192
      (2003) 1261–1280.
[21]  P. Areias, D. Dias-da-Costa, E.B. Pires, et al., A new semi-implicit formulation for multiple-surface flow rules in multiplicative plasticity,
     Comput. Mech. 49 (5) (2012) 545–564.
[22] M. Ortiz, J.C. Simo, An analysis of a new class of integration algorithms for elastoplastic constitutive relations, Internat. J. Numer.
     Methods Engrg. 23 (3) (1986) 353–366.
[23] B. Starman, M. Haliloviˇc, M. Vrh, et al., Consistent tangent operator for cutting-plane algorithm of elasto-plasticity, Comput. Methods
     Appl. Mech. Engrg. 272 (2014) 214–232.
[24]  J.C. Simo, M. Ortiz, A unified approach to  finite deformation elastoplastic analysis based on the use of hyperelastic constitutive
      equations, Comput. Methods Appl. Mech. Engrg. 49 (2) (1985) 221–245.
[25] B. Moran, M. Ortiz, C.F. Shih, Formulation of implicit finite element methods for multiplicative finite deformation plasticity, Internat.
        J. Numer. Methods Engrg. 29 (3) (1990) 483–514.
[26]  D.J. Geng, N. Dai, P.J. Guo, et al., Implicit numerical integration of highly nonlinear plasticity models, Comput. Geotech. 132 (2021)
     103961.
[27] A. Pérez-Foguet, A. Rodrıguez-Ferran, A. Huerta, Consistent tangent matrices for substepping schemes, Comput. Methods Appl. Mech.
      Engrg. 190 (2001) 4627–4647.
[28]  J. Nocedal, S. Wright, Numerical Optimization, Springer Science & Business Media, New York, 2006.
[29] A.R. Conn, N.I. Gould, P.L. Toint, Trust Region Methods, Society for Industrial and Applied Mathematics, Philadelphia, 2000.
[30] B.T. Lester, W.M. Scherzinger, Trust region based return mapping algorithm for implicit integration of elastic-plastic constitutive
     models, Internat. J. Numer. Methods Engrg. 112 (3) (2017) 257–282.
[31]  S.Y. Yoon, S.Y. Lee, F. Barlat, Numerical integration algorithm of updated homogeneous anisotropic hardening model through finite
     element framework, Comput. Methods Appl. Mech. Engrg. 372 (2020) 113449.
[32] H. Choi, J.W. Yoon, Stress integration-based on finite difference method and its application for anisotropic plasticity and distortional
      hardening under associated and non-associated flow rules, Comput. Methods Appl. Mech. Engrg. 345 (2019) 123–160.
[33] A. Shterenlikht, N.A. Alexander, Levenberg–marquardt vs Powell’s dogleg method for Gurson-Tvergaard-Needleman plasticity model,
     Comput. Methods Appl. Mech. Engrg. 237–240 (2012) 1–9.
[34] W.M. Scherzinger, A return mapping algorithm for isotropic and anisotropic plasticity models using a line search method, Comput.
     Methods Appl. Mech. Engrg. 317 (2017) 526–553.

                                                          37

### Page 38

X. Zhou, D. Lu, Y. Zhang et al.                        Computer Methods in Applied Mechanics and Engineering 390 (2022) 114356

[35]  T. Seifert,  I. Schmidt, Line-search methods in general return mapping algorithms with application to porous plasticity, Internat.  J.
     Numer. Methods Engrg. 73 (10) (2008) 1468–1495.
[36]  J.J. Moré, Recent developments in algorithms and software for trust region methods, in: Mathematical Programming the State of the
      Art, Springer-Verlag, Berlin, Germany, 1983, pp. 258–287.
[37]  J.J. Moré, The Levenberg–Marquardt algorithm: implementation and theory, in: Numerical Analysis, Springer, 1978, pp. 105–116.
[38]  P.L. Toint, Non-monotone trust-region algorithms for nonlinear optimization subject to convex constraints, Math. Program. 77 (3) (1997)
     69–94.
[39]  T.J. Hughes, K.S. Pister, Consistent linearization in mechanics of solids and structures, Comput. Struct. 8 (3–4) (1978) 391–397.
[40]  J.C. Nagtegaal, On the implementation of inelastic constitutive equations with special reference to large deformation problems, Comput.
     Methods Appl. Mech. Engrg. 33 (1) (1982) 469–484.
[41]  J.C. Taylor, R.L. Simo, Consistent tangent operators for rate-independent elastoplasticity, Comput. Methods Appl. Mech. Engrg. 48 (1)
      (1985) 101–118.
[42] Q. Gu, J.P. Conte, Z. Yang, et al., Consistent tangent moduli for multi-yield-surface J2 plasticity model, Comput. Mech. 48 (1) (2011)
     97–120.
[43] N. Achour, G. Chatzigeorgiou, F. Meraghni, et  al., Implicit implementation and consistent tangent modulus of a viscoplastic model
      for polymers, Int. J. Mech. Sci. 103 (2015) 297–305.
[44]  J.Y. Wu, J. Li, R. Faria, An energy release rate-based plastic-damage model for concrete, Int. J. Solids Struct. 43 (3–4) (2006) 583–612.
[45]  R.I. Borja, S.R. Lee, Cam-clay plasticity, part 1: implicit integration of elasto-plastic constitutive relations, Comput. Methods Appl.
     Mech. Engrg. 78 (1) (1990) 49–72.
[46] A. Fischer, A special Newton-type optimization method, Optimization 24 (3–4) (1992) 269–284.
[47] C. Kanzow, Some noninterior continuation methods for linear complementarity problems, SIAM J. Matrix Anal. Appl. 17 (4) (1996)
     851–868.
[48] K.H. Roscoe, A. Schofield, A. Thurairajah, Yielding of clays in states wetter than critical, Geotechnique 13 (3) (1963) 211–240.
[49] Y. Xiao, C.S. Desai, Constitutive modeling for overconsolidated clays based on disturbed state concept. II: Validation, Int. J. Geomech.
     19 (9) (2019) 4019102.
[50] Y. Xiao, C.S. Desai, Constitutive modeling for overconsolidated clays based on disturbed state concept. I: Theory, Int. J. Geomech.
     19 (9) (2019) 4019101.
[51] K.H. Roscoe, J.B. Burland, On the generalized stress–strain behaviour of wet clay, in: Engineering Plasticity, Cambridge University
      Press, Cambridge, 1968, pp. 535–609.
[52] J.M.B. Walmag, É.J.M. Delhez, A note on trust-region radius update, SIAM J. Optim. 16 (2) (2005) 548–562.
[53] L. Hei, A self-adaptive trust region algorithm, J. Comput. Math. 21 (2) (2003) 229–236.
[54] X.S. Zhang, J.L. Zhang, L.Z. Liao, An adaptive trust region method and its convergence, Sci. China A 45 (5) (2002) 620–631.
[55] M. Ahookhosh, K. Amini, An efficient nonmonotone trust-region method for unconstrained optimization, Numer. Algorithms 59 (4)
      (2012) 523–540.
[56] W.Y. Sun, Nonmonotone trust region method for solving optimization problems, Appl. Math. Comput. 156 (1) (2004) 159–174.
[57] Y.X. Yuan, Recent advances in trust region algorithms, Math. Program. 151 (1) (2015) 249–281.
[58] M.J. Powell, A hybrid method for nonlinear equations, in: Numerical Methods for Nonlinear Algebraic Equations, 1970.
[59]  J.E. Dennis, H.H.W. Mei, Two new unconstrained optimization algorithms which use function and gradient values, J. Optim. Theory
     Appl. 28 (4) (1979) 453–482.
[60] R.H. Byrd, R.B. Schnabel, G.A. Shultz, Approximate solution of the trust region problem by minimization over two-dimensional
      subspaces, Math. Program. 40 (1) (1988) 247–263.
[61]  T. Steihaug, The conjugate gradient method and trust regions in large scale optimization, SIAM J. Numer. Anal. 20 (3) (1983) 626–637.
[62]  P. Areias, T. Rabczuk, Smooth finite strain plasticity with non-local pressure support, Internat. J. Numer. Methods Engrg. 81 (1) (2010)
     106–134.
[63]  P. Areias, T. Rabczuk,  J. César De Sá, Semi-implicit finite strain constitutive integration of porous plasticity models, Finite Elem.
      Anal. Des. 104 (2015) 41–55.
[64] D. Sheng, S.W. Sloan, H.S. Yu, Aspects of  finite element implementation of critical state models, Comput. Mech. 26 (2) (2000)
     185–196.
[65]  J. Yu, W. Yao, K. Duan, et al., Experimental study and discrete element method modeling of compression and permeability behaviors
      of weakly anisotropic sandstones, Int. J. Rock Mech. Min. Sci. 134 (2020) 104437.

                                                          38
