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

import os
from sympy import python
from rbnics.shape_parametrization.utils.symbolic.sympy_exec import sympy_exec
from rbnics.utils.mpi import is_io_process

class SympyIO(object):
    # Save a variable to file
    @staticmethod
    def save_file(content, directory, filename):
        if not filename.endswith(".sym"):
            filename = filename + ".sym"
        if is_io_process():
            with open(os.path.join(str(directory), filename), "w") as outfile:
                outfile.write(python(content))
        is_io_process.mpi_comm.barrier()
    
    # Load a variable from file
    @staticmethod
    def load_file(directory, filename):
        if not filename.endswith(".sym"):
            filename = filename + ".sym"
        with open(os.path.join(str(directory), filename), "r") as infile:
            content = infile.read()
            return sympy_exec(content, {})
            
    # Check if the file exists
    @staticmethod
    def exists_file(directory, filename):
        if not filename.endswith(".sym"):
            filename = filename + ".sym"
        exists = None
        if is_io_process():
            exists = os.path.exists(os.path.join(str(directory), filename))
        exists = is_io_process.mpi_comm.bcast(exists, root=is_io_process.root)
        return exists
