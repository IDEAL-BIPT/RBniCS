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
## @file parameter_space_subset.py
#  @brief Type for parameter space subsets
#
#  @author Francesco Ballarin <francesco.ballarin@sissa.it>
#  @author Gianluigi Rozza    <gianluigi.rozza@sissa.it>
#  @author Alberto   Sartori  <alberto.sartori@sissa.it>

###########################     OFFLINE STAGE     ########################### 
## @defgroup OfflineStage Methods related to the offline stage
#  @{

# Parameter space subsets
import itertools # for linspace sampling
import numpy
from RBniCS.io_utils.exportable_list import ExportableList

class ParameterSpaceSubset(ExportableList): # equivalent to a list of tuples
    def __init__(self):
        ExportableList.__init__(self, "pickle")
    
    # Method for generation of parameter space subsets
    # If the last argument is equal to "random", n parameters are drawn from a random uniform distribution
    # Else, if the last argument is equal to "linspace", (approximately) n parameters are obtained from a cartesian grid
    def generate(self, box, n, sampling):
        if sampling == "random":
            ss = "[("
            for i in range(len(box)):
                ss += "numpy.random.uniform(box[" + str(i) + "][0], box[" + str(i) + "][1])"
                if i < len(box)-1:
                    ss += ", "
                else:
                    ss += ") for _ in range(" + str(n) +")]"
            self._list = eval(ss)
        elif sampling == "linspace":
            n_P_root = int(np.ceil(n**(1./len(box))))
            ss = "numpy.itertools.product("
            for i in range(len(box)):
                ss += "linspace(box[" + str(i) + "][0], box[" + str(i) + "][1], num = " + str(n_P_root) + ").tolist()"
                if i < len(box)-1:
                    ss += ", "
                else:
                    ss += ")"
            self._list = eval(ss)
        else:
            raise RuntimeError("Invalid sampling mode.")
        
#  @}
########################### end - OFFLINE STAGE - end ########################### 

