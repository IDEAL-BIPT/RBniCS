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
## @file config.py
#  @brief Configuration
#
#  @author Francesco Ballarin <francesco.ballarin@sissa.it>
#  @author Gianluigi Rozza    <gianluigi.rozza@sissa.it>
#  @author Alberto   Sartori  <alberto.sartori@sissa.it>

from __future__ import print_function

# Override the print() method to print only from process 0 in parallel
import __builtin__
from dolfin import *

def print(*args, **kwargs):
    if MPI.rank(print.mpi_comm) == 0:
        return __builtin__.print(*args, **kwargs)

print.mpi_comm = mpi_comm_world() # from dolfin

# Declare matrix type (PETSc)
TruthMatrix = PETScMatrix
TruthVector = PETScVector

# Declare eigen solver type (SLEPc)
TruthEigenSolver = SLEPcEigenSolver
