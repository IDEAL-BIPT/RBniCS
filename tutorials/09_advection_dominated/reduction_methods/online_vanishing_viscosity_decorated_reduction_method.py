# Copyright (C) 2015-2018 by the RBniCS authors
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

from rbnics.backends import BasisFunctionsMatrix, transpose
from rbnics.backends.online import OnlineEigenSolver
from rbnics.utils.decorators import PreserveClassName, ReductionMethodDecoratorFor
from rbnics.utils.io import ExportableList
from backends.online import OnlineSolveKwargsGenerator
from problems import OnlineVanishingViscosity

@ReductionMethodDecoratorFor(OnlineVanishingViscosity)
def OnlineVanishingViscosityDecoratedReductionMethod(EllipticCoerciveReductionMethod_DerivedClass):
    
    @PreserveClassName
    class OnlineVanishingViscosityDecoratedReductionMethod_Class(EllipticCoerciveReductionMethod_DerivedClass):
        
        def _offline(self):
            # Change default online solve arguments during offline stage to use online stabilization
            # instead of vanishing viscosity one (which will be prepared in a postprocessing stage)
            self.reduced_problem._online_solve_default_kwargs["online_stabilization"] = True
            self.reduced_problem._online_solve_default_kwargs["online_vanishing_viscosity"] = False
            self.reduced_problem.OnlineSolveKwargs = OnlineSolveKwargsGenerator(**self.reduced_problem._online_solve_default_kwargs)
            
            # Call standard offline phase
            EllipticCoerciveReductionMethod_DerivedClass._offline(self)
            
            print("==============================================================")
            print("=" + "{:^60}".format(self.label + " offline vanishing viscosity postprocessing phase begins") + "=")
            print("==============================================================")
            print("")
            
            # Prepare storage for copy of lifting basis functions matrix
            lifting_basis_functions = BasisFunctionsMatrix(self.truth_problem.V)
            lifting_basis_functions.init(self.truth_problem.components)
            # Copy current lifting basis functions to lifting_basis_functions
            N_bc = self.reduced_problem.N_bc
            for i in range(N_bc):
                lifting_basis_functions.enrich(self.reduced_problem.basis_functions[i])
            # Prepare storage for unrotated basis functions matrix, without lifting
            unrotated_basis_functions = BasisFunctionsMatrix(self.truth_problem.V)
            unrotated_basis_functions.init(self.truth_problem.components)
            # Copy current basis functions (except lifting) to unrotated_basis_functions
            N = self.reduced_problem.N
            for i in range(N_bc, N):
                unrotated_basis_functions.enrich(self.reduced_problem.basis_functions[i])
                
            # Prepare new storage for non-hierarchical basis functions matrix and
            # corresponding affine expansions
            self.reduced_problem.init("offline_vanishing_viscosity_postprocessing")
            
            # Rotated basis functions matrix are not hierarchical, i.e. a different
            # rotation will be applied for each basis size n.
            for n in range(1, N + 1):
                # Prepare storage for rotated basis functions matrix
                rotated_basis_functions = BasisFunctionsMatrix(self.truth_problem.V)
                rotated_basis_functions.init(self.truth_problem.components)
                # Rotate basis
                print("rotate basis functions matrix for n =", n)
                truth_operator_k = self.truth_problem.operator["k"]
                truth_operator_m = self.truth_problem.operator["m"]
                assert len(truth_operator_k) == 1
                assert len(truth_operator_m) == 1
                reduced_operator_k = transpose(unrotated_basis_functions[:n])*truth_operator_k[0]*unrotated_basis_functions[:n]
                reduced_operator_m = transpose(unrotated_basis_functions[:n])*truth_operator_m[0]*unrotated_basis_functions[:n]
                rotation_eigensolver = OnlineEigenSolver(unrotated_basis_functions[:n], reduced_operator_k, reduced_operator_m)
                parameters = {
                    "problem_type": "hermitian",
                    "spectrum": "smallest real"
                }
                rotation_eigensolver.set_parameters(parameters)
                rotation_eigensolver.solve()
                # Store and save rotated basis
                rotation_eigenvalues = ExportableList("text")
                rotation_eigenvalues.extend([rotation_eigensolver.get_eigenvalue(i)[0] for i in range(n)])
                for i in range(0, n):
                    print("lambda_" + str(i) + " = " + str(rotation_eigenvalues[i]))
                rotation_eigenvalues.save(self.folder["post_processing"], "rotation_eigs_n=" + str(n))
                for i in range(N_bc):
                    rotated_basis_functions.enrich(lifting_basis_functions[i])
                for i in range(0, n):
                    (eigenvector_i, _) = rotation_eigensolver.get_eigenvector(i)
                    rotated_basis_functions.enrich(unrotated_basis_functions[:n]*eigenvector_i)
                self.reduced_problem.basis_functions[:n] = rotated_basis_functions
                # Attach eigenvalues to the vanishing viscosity reduced operator
                self.reduced_problem.vanishing_viscosity_eigenvalues.append(rotation_eigenvalues)
                
            # Save basis functions
            self.reduced_problem.basis_functions.save(self.reduced_problem.folder["basis"], "basis")
            
            # Re-compute all reduced operators, since the basis functions have changed
            print("build reduced operators")
            self.reduced_problem.build_reduced_operators("offline_vanishing_viscosity_postprocessing")
            
            # Clean up reduced solution and output cache, since the basis has changed
            self.reduced_problem._solution_cache.clear()
            self.reduced_problem._output_cache.clear()
            
            print("==============================================================")
            print("=" + "{:^60}".format(self.label + " offline vanishing viscosity postprocessing phase ends") + "=")
            print("==============================================================")
            print("")
            
            # Restore default online solve arguments for online stage
            self.reduced_problem._online_solve_default_kwargs["online_stabilization"] = False
            self.reduced_problem._online_solve_default_kwargs["online_vanishing_viscosity"] = True
            self.reduced_problem.OnlineSolveKwargs = OnlineSolveKwargsGenerator(**self.reduced_problem._online_solve_default_kwargs)
            
        def update_basis_matrix(self, snapshot): # same as Parent, except a different filename is used when saving
            assert len(self.truth_problem.components) is 1
            self.reduced_problem.basis_functions.enrich(snapshot)
            self.GS.apply(self.reduced_problem.basis_functions, self.reduced_problem.N_bc)
            self.reduced_problem.N += 1
            self.reduced_problem.basis_functions.save(self.reduced_problem.folder["basis"], "unrotated_basis")
        
    # return value (a class) for the decorator
    return OnlineVanishingViscosityDecoratedReductionMethod_Class
