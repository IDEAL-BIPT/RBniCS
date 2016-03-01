# Copyright (C) 2015-2016 by the RBniCS authors
#
# This file is part of RBniCS.
#
# RBniCS is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RBniCS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with RBniCS. If not, see <http://www.gnu.org/licenses/>.
#
## @file solve_gaussian.py
#  @brief Example 5: gaussian EIM test case
#
#  @author Francesco Ballarin <francesco.ballarin@sissa.it>
#  @author Gianluigi Rozza    <gianluigi.rozza@sissa.it>
#  @author Alberto   Sartori  <alberto.sartori@sissa.it>

from dolfin import *
from RBniCS import *

#~~~~~~~~~~~~~~~~~~~~~~~~~     EXAMPLE 5: GAUSSIAN EIM CLASS     ~~~~~~~~~~~~~~~~~~~~~~~~~# 
class Gaussian(EllipticCoerciveProblem):
    
    ###########################     CONSTRUCTORS     ########################### 
    ## @defgroup Constructors Methods related to the construction of the reduced order model object
    #  @{
    
    ## Default initialization of members
    def __init__(self, V, subd, bound):
        # Call the standard initialization
        super(Gaussian, self).__init__(V, bc_list)
        # ... and also store FEniCS data structures for assembly
        self.u = TrialFunction(V)
        self.v = TestFunction(V)
        self.dx = Measure("dx")(subdomain_data=subd)
        self.ds = Measure("ds")(subdomain_data=bound)
        # Finally, initialize an EIM object for the interpolation of the forcing term
        self.EIM_obj = EIM(self)
        self.EIM_obj.parametrized_function = "exp( - 2*pow(x[0]-mu_1, 2) - 2*pow(x[1]-mu_2, 2) )"
        self.EIM_N = None # if None, use the maximum number of EIM basis functions, otherwise use EIM_N
        
    #  @}
    ########################### end - CONSTRUCTORS - end ########################### 
    
    ###########################     SETTERS     ########################### 
    ## @defgroup Setters Set properties of the reduced order approximation
    #  @{
    
    # Propagate the values of all setters also to the EIM object
    
    def setNmax(self, nmax):
        EllipticCoerciveRBBase.setNmax(self, nmax)
        self.EIM_obj.setNmax(2*nmax)
    def setmu_range(self, mu_range):
        EllipticCoerciveRBBase.setmu_range(self, mu_range)
        self.EIM_obj.setmu_range(mu_range)
    def setxi_train(self, ntrain, enable_import=False, sampling="random"):
        EllipticCoerciveRBBase.setxi_train(self, ntrain, enable_import, sampling)
        self.EIM_obj.setxi_train(ntrain, enable_import, sampling)
    def setxi_test(self, ntest, enable_import=False, sampling="random"):
        EllipticCoerciveRBBase.setxi_test(self, ntest, enable_import, sampling)
        self.EIM_obj.setxi_test(ntest, enable_import, sampling)
    def setmu(self, mu):
        EllipticCoerciveRBBase.setmu(self, mu)
        self.EIM_obj.setmu(mu)
        
    #  @}
    ########################### end - SETTERS - end ########################### 
    
    ###########################     PROBLEM SPECIFIC     ########################### 
    ## @defgroup ProblemSpecific Problem specific methods
    #  @{
    
    ## Return the alpha_lower bound.
    def get_alpha_lb(self):
        return 1.
    
    ## Return theta multiplicative terms of the affine expansion of the problem.
    def compute_theta(self, term):
        if term == "a":
            return (1., )
        elif term == "f":
            self.EIM_obj.setmu(self.mu)
            return self.EIM_obj.compute_interpolated_theta(self.EIM_N)
        elif term == "dirichlet_bc":
            return (0.,)
        else:
            raise RuntimeError("Invalid term for compute_theta().")
                
    ## Return forms resulting from the discretization of the affine expansion of the problem operators.
    def assemble_operator(self, term):
        if term == "a":
            return (self.S,)
        elif term == "f":
            v = self.v
            dx = self.dx
            # Call EIM
            self.EIM_obj.setmu(self.mu)
            interpolated_gaussian = self.EIM_obj.assemble_mu_independent_interpolated_function()
            # Assemble
            all_f = ()
            for q in range(len(interpolated_gaussian)):
                all_f += (interpolated_gaussian[q]*v*dx,)
            # Return
            return all_f
        elif term == "dirichlet_bc":
            bc0 = [(self.V, Constant(0.0), self.bound, 1),
                   (self.V, Constant(0.0), self.bound, 2),
                   (self.V, Constant(0.0), self.bound, 3)]
            return (bc0,)
        elif term == "inner_product":
            x0 = inner(grad(u),grad(v))*dx
            return (x0,)
        else:
            raise RuntimeError("Invalid term for assemble_operator().")
            
    #  @}
    ########################### end - PROBLEM SPECIFIC - end ########################### 
    
    ###########################     OFFLINE STAGE     ########################### 
    ## @defgroup OfflineStage Methods related to the offline stage
    #  @{
    
    ## Perform the offline phase of the reduced order model
    def offline(self):
        # Perform first the EIM offline phase, ...
        self.EIM_obj.offline()
        # ..., and then call the parent method.
        EllipticCoerciveRBBase.offline(self)
    
    #  @}
    ########################### end - OFFLINE STAGE - end ###########################
    
    ###########################     ERROR ANALYSIS     ########################### 
    ## @defgroup ErrorAnalysis Error analysis
    #  @{
    
    # Compute the error of the reduced order approximation with respect to the full order one
    # over the test set
    def error_analysis(self, N=None):
        # Perform first the EIM error analysis, ...
        self.EIM_obj.error_analysis(N)
        # ..., and then call the parent method.
        EllipticCoerciveRBBase.error_analysis(self, N)        
        
    #  @}
    ########################### end - ERROR ANALYSIS - end ########################### 

#~~~~~~~~~~~~~~~~~~~~~~~~~     EXAMPLE 5: MAIN PROGRAM     ~~~~~~~~~~~~~~~~~~~~~~~~~# 

# 1. Read the mesh for this problem
mesh = Mesh("data/gaussian.xml")
subd = MeshFunction("size_t", mesh, "data/gaussian_physical_region.xml")
bound = MeshFunction("size_t", mesh, "data/gaussian_facet_region.xml")

# 2. Create Finite Element space (Lagrange P1)
V = FunctionSpace(mesh, "Lagrange", 1)

# 3. Allocate an object of the Gaussian class
gaussian = Gaussian(V, subd, bound)

# 4. Choose PETSc solvers as linear algebra backend
parameters.linear_algebra_backend = 'PETSc'

# 5. Set mu range, xi_train and Nmax
mu_range = [(-1.0, 1.0), (-1.0, 1.0)]
gaussian.setmu_range(mu_range)
gaussian.setxi_train(50)
gaussian.setNmax(20)

# 6. Perform the offline phase
first_mu = (0.5,1.0)
gaussian.setmu(first_mu)
gaussian.offline()

# 7. Perform an online solve
online_mu = (0.3,-1.0)
gaussian.setmu(online_mu)
gaussian.online_solve()

# 8. Perform an error analysis
gaussian.setxi_test(50)
gaussian.error_analysis()
