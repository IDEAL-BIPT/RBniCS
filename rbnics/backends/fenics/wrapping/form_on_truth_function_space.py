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

from ufl.algorithms.traversal import iter_expressions
from ufl.corealg.traversal import traverse_unique_terminals
from dolfin import assign, Function
from rbnics.backends.fenics.wrapping.function_from_subfunction_if_any import function_from_subfunction_if_any
from rbnics.utils.decorators import exact_problem, get_problem_from_solution, get_reduced_problem_from_problem, is_problem_solution, is_training_finished
from rbnics.utils.mpi import log, PROGRESS
from rbnics.eim.utils.decorators import get_EIM_approximation_from_parametrized_expression

def form_on_truth_function_space(form_wrapper):
    form = form_wrapper._form
    EIM_approximation = get_EIM_approximation_from_parametrized_expression(form_wrapper)
    
    if form not in form_on_truth_function_space__reduced_problem_to_truth_solution_cache:
        visited = list()
        truth_problem_to_truth_solution = dict() # from truth problem to solution
        reduced_problem_to_truth_solution = dict() # from reduced problem to solution
        
        # Look for terminals on truth mesh
        for integral in form.integrals():
            for expression in iter_expressions(integral):
                for node in traverse_unique_terminals(expression):
                    node = function_from_subfunction_if_any(node)
                    if node in visited:
                        continue
                    # ... problem solutions related to nonlinear terms
                    elif isinstance(node, Function) and is_problem_solution(node):
                        truth_problem = get_problem_from_solution(node)
                        if is_training_finished(truth_problem):
                            reduced_problem = get_reduced_problem_from_problem(truth_problem)
                            reduced_problem_to_truth_solution[reduced_problem] = node
                        else:
                            if not hasattr(truth_problem, "_is_solving"):
                                exact_truth_problem = exact_problem(truth_problem)
                                exact_truth_problem.init()
                                truth_problem_to_truth_solution[exact_truth_problem] = node
                            else:
                                truth_problem_to_truth_solution[truth_problem] = node
                        visited.append(node)
        
        # Cache the resulting dicts
        form_on_truth_function_space__truth_problem_to_truth_solution_cache[form] = truth_problem_to_truth_solution
        form_on_truth_function_space__reduced_problem_to_truth_solution_cache[form] = reduced_problem_to_truth_solution
        
    # Extract from cache
    truth_problem_to_truth_solution = form_on_truth_function_space__truth_problem_to_truth_solution_cache[form]
    reduced_problem_to_truth_solution = form_on_truth_function_space__reduced_problem_to_truth_solution_cache[form]
    
    # Solve truth problems (which have not been reduced yet) associated to nonlinear terms
    for (truth_problem, truth_solution) in truth_problem_to_truth_solution.iteritems():
        truth_problem.set_mu(EIM_approximation.mu)
        if not hasattr(truth_problem, "_is_solving"):
            log(PROGRESS, "In form_on_truth_function_space, requiring truth problem solve for problem " + str(truth_problem))
            assign(truth_solution, truth_problem.solve())
        else:
            log(PROGRESS, "In form_on_truth_function_space, loading truth problem solution for problem " + str(truth_problem))
            assign(truth_solution, truth_problem._solution)
    
    # Solve reduced problems associated to nonlinear terms
    for (reduced_problem, truth_solution) in reduced_problem_to_truth_solution.iteritems():
        reduced_problem.set_mu(EIM_approximation.mu)
        assert not hasattr(reduced_problem, "_is_solving")
        log(PROGRESS, "In form_on_truth_function_space, requiring reduced problem solve for problem " + str(reduced_problem))
        reduced_solution = reduced_problem.solve()
        assign(truth_solution, reduced_problem.Z[:reduced_solution.N]*reduced_solution)
    
    return form
    
form_on_truth_function_space__truth_problem_to_truth_solution_cache = dict()
form_on_truth_function_space__reduced_problem_to_truth_solution_cache = dict()