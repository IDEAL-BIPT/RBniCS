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

import pytest
from numpy import isclose
from dolfin import assemble, Constant, derivative, DirichletBC, DOLFIN_EPS, dx, Expression, Function, FunctionSpace, grad, inner, IntervalMesh, pi, plot, project, TestFunction, TrialFunction
import matplotlib
import matplotlib.pyplot as plt
from rbnics.backends.abstract import TimeDependentProblem2Wrapper
from rbnics.backends.dolfin import TimeStepping as SparseTimeStepping

"""
Solve
    u_tt - ((1 + u^2) u_x)_x = g,   (t, x) in [0, 1] x [0, 2*pi]
    u = sin(t),                     (t, x) in [0, 1] x {0, 2*pi}
    u = sin(x),                     (t, x) in {0}    x [0, 2*pi]
    u_t = cos(x),                   (t, x) in {0}    x [0, 2*pi]
for g such that u = u_ex = sin(x+t)
"""

# ~~~ Sparse case ~~~ #
def _test_time_stepping_4_sparse(callback_type):
    # Create mesh and define function space
    mesh = IntervalMesh(132, 0, 2*pi)
    V = FunctionSpace(mesh, "Lagrange", 1)

    # Define Dirichlet boundary (x = 0 or x = 2*pi)
    def boundary(x):
        return x[0] < 0 + DOLFIN_EPS or x[0] > 2*pi - 10*DOLFIN_EPS
        
    # Define time step
    dt = 0.01
    T = 1.

    # Define exact solution
    exact_solution_expression = Expression("sin(x[0]+t)", t=0, element=V.ufl_element())
    # ... and interpolate it at the final time
    exact_solution_expression.t = T
    exact_solution = project(exact_solution_expression, V)

    # Define exact solution dot
    exact_solution_dot_expression = Expression("cos(x[0]+t)", t=0, element=V.ufl_element())
    # ... and interpolate it at the final time
    exact_solution_dot_expression.t = T
    exact_solution_dot = project(exact_solution_dot_expression, V)

    # Define exact solution dot dot
    exact_solution_dot_dot_expression = Expression("-sin(x[0]+t)", t=0, element=V.ufl_element())
    # ... and interpolate it at the final time
    exact_solution_dot_dot_expression.t = T
    exact_solution_dot_dot = project(exact_solution_dot_dot_expression, V)

    # Define variational problem
    du = TrialFunction(V)
    du_dot_dot = TrialFunction(V)
    v = TestFunction(V)
    u = Function(V)
    u_dot = Function(V)
    u_dot_dot = Function(V)
    g = Expression("-1./2.*sin(t+x[0])*(3*cos(2*(t+x[0]))+1)", t=0., element=V.ufl_element())
    r_u = inner((1+u**2)*grad(u), grad(v))*dx
    j_u = derivative(r_u, u, du)
    r_u_dot_dot = inner(u_dot_dot, v)*dx
    j_u_dot_dot = derivative(r_u_dot_dot, u_dot_dot, du_dot_dot)
    r = r_u_dot_dot + r_u - g*v*dx
    x = inner(du, v)*dx
    def bc(t):
        exact_solution_expression.t = t
        return [DirichletBC(V, exact_solution_expression, boundary)]

    # Assemble inner product matrix
    X = assemble(x)
    
    # Define callback function depending on callback type
    assert callback_type in ("form callbacks", "tensor callbacks")
    if callback_type == "form callbacks":
        def callback(arg):
            return arg
    elif callback_type == "tensor callbacks":
        def callback(arg):
            return assemble(arg)
            
    # Define problem wrapper
    class SparseProblemWrapper(TimeDependentProblem2Wrapper):
        # Residual and jacobian functions
        def residual_eval(self, t, solution, solution_dot, solution_dot_dot):
            g.t = t
            return callback(r)
        def jacobian_eval(self, t, solution, solution_dot, solution_dot_dot, solution_dot_coefficient, solution_dot_dot_coefficient):
            return callback(Constant(solution_dot_dot_coefficient)*j_u_dot_dot + j_u)
            
        # Define boundary condition
        def bc_eval(self, t):
            return bc(t)
            
        # Define initial condition
        def ic_eval(self):
            exact_solution_expression.t = 0.
            sparse_solution = project(exact_solution_expression, V)
            exact_solution_dot_expression.t = 0.
            sparse_solution_dot = project(exact_solution_dot_expression, V)
            return (sparse_solution, sparse_solution_dot)
            
        # Define custom monitor to plot the solution
        def monitor(self, t, solution, solution_dot, solution_dot_dot):
            if matplotlib.get_backend() != "agg":
                plt.subplot(1, 3, 1).clear()
                plot(solution, title="u at t = " + str(t))
                plt.subplot(1, 3, 2).clear()
                plot(solution_dot, title="u_dot at t = " + str(t))
                plt.subplot(1, 3, 3).clear()
                plot(solution_dot_dot, title="u_dot_dot at t = " + str(t))
                plt.show(block=False)
                plt.pause(DOLFIN_EPS)
            else:
                print("||u|| at t = " + str(t) + ": " + str(solution.vector().norm("l2")))
                print("||u_dot|| at t = " + str(t) + ": " + str(solution_dot.vector().norm("l2")))
                print("||u_dot_dot|| at t = " + str(t) + ": " + str(solution_dot_dot.vector().norm("l2")))

    # Solve the time dependent problem
    sparse_problem_wrapper = SparseProblemWrapper()
    (sparse_solution, sparse_solution_dot, sparse_solution_dot_dot) = (u, u_dot, u_dot_dot)
    sparse_solver = SparseTimeStepping(sparse_problem_wrapper, sparse_solution, sparse_solution_dot, sparse_solution_dot_dot)
    sparse_solver.set_parameters({
        "initial_time": 0.0,
        "time_step_size": dt,
        "final_time": T,
        "exact_final_time": "stepover",
        "integrator_type": "alpha2",
        "problem_type": "nonlinear",
        "snes_solver": {
            "linear_solver": "mumps",
            "maximum_iterations": 20,
            "report": True
        },
        "monitor": sparse_problem_wrapper.monitor,
        "report": True
    })
    all_sparse_solutions_time, all_sparse_solutions, all_sparse_solutions_dot, all_sparse_solutions_dot_dot = sparse_solver.solve()
    assert len(all_sparse_solutions_time) == int(T/dt + 1)
    assert len(all_sparse_solutions) == int(T/dt + 1)
    assert len(all_sparse_solutions_dot) == int(T/dt + 1)
    assert len(all_sparse_solutions_dot_dot) == int(T/dt + 1)

    # Compute the error
    sparse_error = Function(V)
    sparse_error.vector().add_local(+ sparse_solution.vector().get_local())
    sparse_error.vector().add_local(- exact_solution.vector().get_local())
    sparse_error.vector().apply("")
    sparse_error_norm = sparse_error.vector().inner(X*sparse_error.vector())
    sparse_error_dot = Function(V)
    sparse_error_dot.vector().add_local(+ sparse_solution_dot.vector().get_local())
    sparse_error_dot.vector().add_local(- exact_solution_dot.vector().get_local())
    sparse_error_dot.vector().apply("")
    sparse_error_dot_norm = sparse_error_dot.vector().inner(X*sparse_error_dot.vector())
    sparse_error_dot_dot = Function(V)
    sparse_error_dot_dot.vector().add_local(+ sparse_solution_dot_dot.vector().get_local())
    sparse_error_dot_dot.vector().add_local(- exact_solution_dot_dot.vector().get_local())
    sparse_error_dot_dot.vector().apply("")
    sparse_error_dot_dot_norm = sparse_error_dot_dot.vector().inner(X*sparse_error_dot_dot.vector())
    print("SparseTimeStepping error (" + callback_type + "):", sparse_error_norm, sparse_error_dot_norm, sparse_error_dot_dot_norm)
    assert isclose(sparse_error_norm, 0., atol=1.e-5)
    assert isclose(sparse_error_dot_norm, 0., atol=1.e-5)
    assert isclose(sparse_error_dot_dot_norm, 0., atol=1.e-4)
    return (sparse_error_norm, sparse_error_dot_norm, sparse_error_dot_dot_norm)
    
# ~~~ Test function ~~~ #
@pytest.mark.time_stepping
def test_time_stepping_4():
    error_sparse_tensor_callbacks = _test_time_stepping_4_sparse("tensor callbacks")
    error_sparse_form_callbacks = _test_time_stepping_4_sparse("form callbacks")
    assert isclose(error_sparse_tensor_callbacks, error_sparse_form_callbacks).all()
