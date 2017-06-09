# Copyright (C) 2015-2017 by the RBniCS authors
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

from __future__ import print_function
from rbnics.problems.base import LinearReducedProblem
from rbnics.problems.elliptic_optimal_control.elliptic_optimal_control_problem import EllipticOptimalControlProblem
from rbnics.backends import LinearSolver, product, sum, transpose
from rbnics.backends.online import OnlineFunction
from rbnics.utils.decorators import Extends, override
from rbnics.reduction_methods.elliptic_optimal_control import EllipticOptimalControlReductionMethod
from rbnics.utils.mpi import print

def EllipticOptimalControlReducedProblem(ParametrizedReducedDifferentialProblem_DerivedClass):
    
    EllipticOptimalControlReducedProblem_Base = LinearReducedProblem(ParametrizedReducedDifferentialProblem_DerivedClass)

    # Base class containing the interface of a projection based ROM
    # for saddle point problems.
    @Extends(EllipticOptimalControlReducedProblem_Base)
    class EllipticOptimalControlReducedProblem_Class(EllipticOptimalControlReducedProblem_Base):
        
        class ProblemSolver(EllipticOptimalControlReducedProblem_Base.ProblemSolver):
            def matrix_eval(self):
                problem = self.problem
                N = self.N
                assembled_operator = dict()
                for term in ("a", "a*", "c", "c*", "m", "n"):
                    assembled_operator[term] = sum(product(self.compute_theta(term), self.operator[term][:N, :N]))
                return (
                      assembled_operator["m"]                           + assembled_operator["a*"]
                                              + assembled_operator["n"] - assembled_operator["c*"]
                    + assembled_operator["a"] - assembled_operator["c"]
                )
                
            def vector_eval(self):
                problem = self.problem
                N = self.N
                assembled_operator = dict()
                for term in ("f", "g"):
                    assembled_operator[term] = sum(product(self.compute_theta(term), self.operator[term][:N]))
                return (
                      assembled_operator["g"]
                    
                    + assembled_operator["f"]
                )
                            
        # Perform an online evaluation of the cost functional
        @override
        def _compute_output(self, N):
            assembled_operator = dict()
            for term in ("g", "h", "m", "n"):
                assert self.terms_order[term] in (0, 1, 2)
                if self.terms_order[term] == 2:
                    assembled_operator[term] = sum(product(self.compute_theta(term), self.operator[term][:N, :N]))
                elif self.terms_order[term] == 1:
                    assembled_operator[term] = sum(product(self.compute_theta(term), self.operator[term][:N]))
                elif self.terms_order[term] == 0:
                    assembled_operator[term] = sum(product(self.compute_theta(term), self.operator[term]))
                else:
                    raise AssertionError("Invalid value for order of term " + term)
            self._output = (
                0.5*(transpose(self._solution)*assembled_operator["m"]*self._solution) + 
                0.5*(transpose(self._solution)*assembled_operator["n"]*self._solution) - 
                transpose(assembled_operator["g"])*self._solution + 
                0.5*assembled_operator["h"]
            )
        
        # If a value of N was provided, make sure to double it when dealing with y and p, due to
        # the aggregated component approach
        @override
        def _online_size_from_kwargs(self, N, **kwargs):
            all_components_in_kwargs = all([c in kwargs for c in self.components])
            if N is None:
                # then either,
                # * the user has passed kwargs, so we trust that he/she has doubled y and p for us
                # * or self.N was copied, which already stores the correct count of basis functions
                return EllipticOptimalControlReducedProblem_Base._online_size_from_kwargs(self, N, **kwargs)
            else:
                # then the integer value provided to N would be used for all components: need to double
                # it for y and p
                N, kwargs = EllipticOptimalControlReducedProblem_Base._online_size_from_kwargs(self, N, **kwargs)
                for component in ("y", "p"):
                    N[component] *= 2
                return N, kwargs
        
    # return value (a class) for the decorator
    return EllipticOptimalControlReducedProblem_Class
