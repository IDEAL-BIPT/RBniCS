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
## @file test_v1_dot_v2.py
#  @brief Test v1 dot v2 
#
#  @author Francesco Ballarin <francesco.ballarin@sissa.it>
#  @author Gianluigi Rozza    <gianluigi.rozza@sissa.it>
#  @author Alberto   Sartori  <alberto.sartori@sissa.it>

from __future__ import print_function
from test_main import TestBase
from RBniCS.linear_algebra.online_vector import OnlineVector_Type as OnlineVector
from RBniCS.linear_algebra.transpose import transpose

class Test(TestBase):
    def run(self):
        N = self.N
        test_id = self.test_id
        test_subid = self.test_subid
        if test_id >= 0:
            if not self.index in self.storage:
                # Generate random vectors
                v1 = OnlineVector(self.rand(N)).transpose() # as column vector
                v2 = OnlineVector(self.rand(N)).transpose() # as column vector
                self.storage[self.index] = (v1, v2)
            else:
                (v1, v2) = self.storage[self.index]
            self.index += 1
        if test_id >= 1:
            if test_id > 1 or (test_id == 1 and test_subid == "a"):
                # Time using built in methods
                v1_dot_v2_builtin = v1.T*v2
            if test_id > 1 or (test_id == 1 and test_subid == "b"):
                # Time using transpose() method
                v1_dot_v2_transpose = transpose(v1)*v2
        if test_id >= 2:
            return (v1_dot_v2_builtin - v1_dot_v2_transpose)/v1_dot_v2_builtin

for i in range(4, 15):
    N = 2**i
    test = Test(N)
    print("N =", N)
    
    test.init_test(0)
    (usec_0_build, usec_0_access) = test.timeit()
    print("Construction:", usec_0_build, "usec", "(number of runs: ", test.number_of_runs(), ")")
    print("Access:", usec_0_access, "usec", "(number of runs: ", test.number_of_runs(), ")")
    
    test.init_test(1, "a")
    usec_1a = test.timeit()
    print("Builtin method:", usec_1a - usec_0_access, "usec", "(number of runs: ", test.number_of_runs(), ")")
    
    test.init_test(1, "b")
    usec_1b = test.timeit()
    print("transpose() method:", usec_1b - usec_0_access, "usec", "(number of runs: ", test.number_of_runs(), ")")
    
    print("Relative overhead of the transpose() method:", (usec_1b - usec_1a)/(usec_1a - usec_0_access))
    
    test.init_test(2)
    error = test.average()
    print("Relative error:", error)
    
