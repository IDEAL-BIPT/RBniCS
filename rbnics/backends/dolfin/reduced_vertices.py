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
from numpy import ndarray as array
from dolfin import FunctionSpace
from rbnics.backends.abstract import ReducedVertices as AbstractReducedVertices
from rbnics.backends.dolfin.reduced_mesh import ReducedMesh
from rbnics.utils.decorators import BackendFor, ModuleWrapper
from rbnics.utils.io import Folders

def BasicReducedVertices(backend, wrapping):
    class _BasicReducedVertices(AbstractReducedVertices):
        def __init__(self, V, **kwargs):
            AbstractReducedVertices.__init__(self, V)
            self._V = V
            
            # Detect if **kwargs are provided by the copy constructor in __getitem__
            if "copy_from" in kwargs:
                copy_from = kwargs["copy_from"]
                assert "key_as_slice" in kwargs
                key_as_slice = kwargs["key_as_slice"]
                assert "key_as_int" in kwargs
                key_as_int = kwargs["key_as_int"]
            else:
                copy_from = None
                key_as_slice = None
                key_as_int = None
                
            # Storage for reduced mesh
            if copy_from is None:
                self._reduced_mesh = backend.ReducedMesh((V, ))
            else:
                self._reduced_mesh = backend.ReducedMesh((V, ), copy_from=copy_from._reduced_mesh, key_as_slice=key_as_slice, key_as_int=key_as_int)
            
        def append(self, vertex_and_component_and_dof):
            assert isinstance(vertex_and_component_and_dof, tuple)
            assert len(vertex_and_component_and_dof) == 3
            assert isinstance(vertex_and_component_and_dof[0], array)
            assert isinstance(vertex_and_component_and_dof[1], int)
            assert isinstance(vertex_and_component_and_dof[2], int)
            global_dof = vertex_and_component_and_dof[2]
            # Update reduced mesh
            self._reduced_mesh.append((global_dof, ))
            
        def save(self, directory, filename):
            # Get full directory name
            full_directory = Folders.Folder(os.path.join(str(directory), filename))
            full_directory.create()
            # Save reduced mesh
            self._reduced_mesh.save(directory, filename)
            
        def load(self, directory, filename):
            # Load reduced mesh
            return self._reduced_mesh.load(directory, filename)
            
        def __getitem__(self, key):
            assert isinstance(key, slice)
            assert key.start is None
            assert key.step is None
            output = _BasicReducedVertices.__new__(type(self), self._V, copy_from=self, key_as_slice=key, key_as_int=key.stop - 1)
            output.__init__(self._V, copy_from=self, key_as_slice=key, key_as_int=key.stop - 1)
            return output
            
        def get_reduced_mesh(self, index=None):
            return self._reduced_mesh.get_reduced_mesh(index)
        
        def get_reduced_function_space(self, index=None):
            output = self._reduced_mesh.get_reduced_function_spaces(index)
            assert isinstance(output, tuple)
            assert len(output) == 1
            return output[0]
            
        def get_reduced_subdomain_data(self, index=None):
            return self._reduced_mesh.get_reduced_subdomain_data(index)
            
        def get_dofs_list(self, index=None):
            return self._reduced_mesh.get_dofs_list(index)
            
        def get_reduced_dofs_list(self, index=None):
            return self._reduced_mesh.get_reduced_dofs_list(index)
            
        def get_auxiliary_reduced_function_space(self, auxiliary_problem, component, index=None):
            return self._reduced_mesh.get_auxiliary_reduced_function_space(auxiliary_problem, component, index)
            
        def get_auxiliary_basis_functions_matrix(self, auxiliary_problem, auxiliary_reduced_problem, component, index=None):
            return self._reduced_mesh.get_auxiliary_basis_functions_matrix(auxiliary_problem, auxiliary_reduced_problem, component, index)
            
        def get_auxiliary_function_interpolator(self, auxiliary_problem, component, index=None):
            return self._reduced_mesh.get_auxiliary_function_interpolator(auxiliary_problem, component, index)
    return _BasicReducedVertices

backend = ModuleWrapper(ReducedMesh)
wrapping = ModuleWrapper()
ReducedVertices_Base = BasicReducedVertices(backend, wrapping)

@BackendFor("dolfin", inputs=(FunctionSpace, ))
class ReducedVertices(ReducedVertices_Base):
    pass
