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
from numpy import empty as NonAffineExpansionStorageContent_Base, nditer as NonAffineExpansionStorageContent_Iterator
from rbnics.backends.abstract import BasisFunctionsMatrix as AbstractBasisFunctionsMatrix, FunctionsList as AbstractFunctionsList, NonAffineExpansionStorage as AbstractNonAffineExpansionStorage, ParametrizedTensorFactory as AbstractParametrizedTensorFactory
from rbnics.backends.basic.wrapping import DelayedBasisFunctionsMatrix, DelayedFunctionsList, DelayedLinearSolver, DelayedTranspose
from rbnics.backends.online.basic.wrapping import slice_to_array
from rbnics.eim.utils.decorators import get_problem_from_parametrized_operator, get_problem_from_problem_name, get_reduced_problem_from_basis_functions, get_reduced_problem_from_error_estimation_inner_product, get_reduced_problem_from_problem, get_term_and_index_from_parametrized_operator
from rbnics.utils.decorators import overload, tuple_of
from rbnics.utils.io import Folders, TextIO as BasisFunctionsContentLengthIO, TextIO as BasisFunctionsProblemNameIO, TextIO as DelayedFunctionsProblemNameIO, TextIO as DelayedFunctionsTypeIO, TextIO as ErrorEstimationInnerProductIO, TextIO as TruthContentItemIO, TextIO as TypeIO

class NonAffineExpansionStorage(AbstractNonAffineExpansionStorage):
    def __init__(self, *shape):
        self._shape = shape
        self._type = "empty"
        self._content = dict()
        self._precomputed_slices = dict() # from tuple to NonAffineExpansionStorage
        assert len(shape) in (1, 2)
        if len(shape) is 1:
            self._smallest_key = 0
            self._largest_key = shape[0] - 1
        else:
            self._smallest_key = (0, 0)
            self._largest_key = (shape[0] - 1, shape[1] - 1)
            
    def save(self, directory, filename):
        # Get full directory name
        full_directory = Folders.Folder(os.path.join(str(directory), filename))
        full_directory.create()
        # Export depending on type
        TypeIO.save_file(self._type, full_directory, "type")
        assert self._type in ("basis_functions_matrix", "empty", "error_estimation_operators_11", "error_estimation_operators_21", "error_estimation_operators_22", "functions_list", "operators")
        if self._type in ("basis_functions_matrix", "functions_list"):
            # Save delayed functions
            delayed_functions = self._content[self._type]
            it = NonAffineExpansionStorageContent_Iterator(delayed_functions, flags=["c_index", "multi_index", "refs_ok"], op_flags=["readonly"])
            while not it.finished:
                delayed_function = delayed_functions[it.multi_index]
                delayed_function.save(full_directory, "delayed_functions_" + str(it.index))
                it.iternext()
        elif self._type == "empty":
            pass
        elif self._type in ("error_estimation_operators_11", "error_estimation_operators_21", "error_estimation_operators_22"):
            # Save delayed functions
            delayed_function_type = {
                DelayedBasisFunctionsMatrix: "DelayedBasisFunctionsMatrix",
                DelayedLinearSolver: "DelayedLinearSolver"
            }
            assert len(self._content["delayed_functions"]) is 2
            for (index, delayed_functions) in enumerate(self._content["delayed_functions"]):
                it = NonAffineExpansionStorageContent_Iterator(delayed_functions, flags=["c_index", "refs_ok"], op_flags=["readonly"])
                while not it.finished:
                    delayed_function = delayed_functions[it.index]
                    DelayedFunctionsTypeIO.save_file(delayed_function_type[type(delayed_function)], full_directory, "delayed_functions_" + str(index) + "_" + str(it.index) + "_type")
                    DelayedFunctionsProblemNameIO.save_file(delayed_function.get_problem_name(), full_directory, "delayed_functions_" + str(index) + "_" + str(it.index) + "_problem_name")
                    delayed_function.save(full_directory, "delayed_functions_" + str(index) + "_" + str(it.index) + "_content")
                    it.iternext()
            ErrorEstimationInnerProductIO.save_file(get_reduced_problem_from_error_estimation_inner_product(self._content["inner_product_matrix"]).truth_problem.name(), full_directory, "inner_product_matrix_problem_name")
        elif self._type == "operators":
            # Save truth content
            it = NonAffineExpansionStorageContent_Iterator(self._content["truth_operators"], flags=["c_index", "multi_index", "refs_ok"], op_flags=["readonly"])
            while not it.finished:
                operator = self._content["truth_operators"][it.multi_index]
                assert isinstance(operator, AbstractParametrizedTensorFactory)
                problem_name = get_problem_from_parametrized_operator(operator).name()
                (term, index) = get_term_and_index_from_parametrized_operator(operator)
                TruthContentItemIO.save_file((problem_name, term, index), full_directory, "truth_operator_" + str(it.index))
                it.iternext()
            assert "truth_operators_as_expansion_storage" in self._content
            # Save basis functions content
            assert len(self._content["basis_functions"]) in (1, 2)
            BasisFunctionsContentLengthIO.save_file(len(self._content["basis_functions"]), full_directory, "basis_functions_length")
            for (index, basis_functions) in enumerate(self._content["basis_functions"]):
                BasisFunctionsProblemNameIO.save_file(get_reduced_problem_from_basis_functions(basis_functions).truth_problem.name(), full_directory, "basis_functions_" + str(index) + "_problem_name")
                BasisFunctionsProblemNameIO.save_file(basis_functions._components_name, full_directory, "basis_functions_" + str(index) + "_components_name")
                basis_functions.save(full_directory, "basis_functions_" + str(index) + "_content")
        else:
            raise ValueError("Invalid type")
        
    def load(self, directory, filename):
        from rbnics.backends import BasisFunctionsMatrix
        if self._type != "empty": # avoid loading multiple times
            if self._type in ("basis_functions_matrix", "functions_list"):
                delayed_functions = self._content[self._type]
                it = NonAffineExpansionStorageContent_Iterator(delayed_functions, flags=["c_index", "multi_index", "refs_ok"], op_flags=["readonly"])
                while not it.finished:
                    if isinstance(delayed_functions[it.multi_index], DelayedFunctionsList):
                        assert self._type == "functions_list"
                        if len(delayed_functions[it.multi_index]) > 0: # ... unless it is an empty FunctionsList
                            return False
                    elif isinstance(delayed_functions[it.multi_index], DelayedBasisFunctionsMatrix):
                        assert self._type == "basis_functions_matrix"
                        if sum(delayed_functions[it.multi_index]._component_name_to_basis_component_length.values()) > 0: # ... unless it is an empty BasisFunctionsMatrix
                            return False
                    else:
                        raise TypeError("Invalid delayed functions")
                    it.iternext()
            else:
                return False
        # Get full directory name
        full_directory = Folders.Folder(os.path.join(str(directory), filename))
        # Detect trivial case
        assert TypeIO.exists_file(full_directory, "type")
        imported_type = TypeIO.load_file(full_directory, "type")
        self._type = imported_type
        assert self._type in ("basis_functions_matrix", "empty", "error_estimation_operators_11", "error_estimation_operators_21", "error_estimation_operators_22", "functions_list", "operators")
        if self._type in ("basis_functions_matrix", "functions_list"):
            # Load delayed functions
            assert self._type in self._content
            delayed_functions = self._content[self._type]
            it = NonAffineExpansionStorageContent_Iterator(delayed_functions, flags=["c_index", "multi_index", "refs_ok"])
            while not it.finished:
                delayed_function = delayed_functions[it.multi_index]
                delayed_function.load(full_directory, "delayed_functions_" + str(it.index))
                it.iternext()
        elif self._type == "empty":
            pass
        elif self._type in ("error_estimation_operators_11", "error_estimation_operators_21", "error_estimation_operators_22"):
            # Load delayed functions
            assert "delayed_functions" not in self._content
            self._content["delayed_functions"] = [NonAffineExpansionStorageContent_Base(self._shape[0], dtype=object), NonAffineExpansionStorageContent_Base(self._shape[1], dtype=object)]
            for (index, delayed_functions) in enumerate(self._content["delayed_functions"]):
                it = NonAffineExpansionStorageContent_Iterator(delayed_functions, flags=["c_index", "refs_ok"])
                while not it.finished:
                    assert DelayedFunctionsTypeIO.exists_file(full_directory, "delayed_functions_" + str(index) + "_" + str(it.index) + "_type")
                    delayed_function_type = DelayedFunctionsTypeIO.load_file(full_directory, "delayed_functions_" + str(index) + "_" + str(it.index) + "_type")
                    assert DelayedFunctionsProblemNameIO.exists_file(full_directory, "delayed_functions_" + str(index) + "_" + str(it.index) + "_problem_name")
                    delayed_function_problem_name = DelayedFunctionsProblemNameIO.load_file(full_directory, "delayed_functions_" + str(index) + "_" + str(it.index) + "_problem_name")
                    delayed_function_problem = get_problem_from_problem_name(delayed_function_problem_name)
                    assert delayed_function_type in ("DelayedBasisFunctionsMatrix", "DelayedLinearSolver")
                    if delayed_function_type == "DelayedBasisFunctionsMatrix":
                        delayed_function = DelayedBasisFunctionsMatrix(delayed_function_problem.V)
                        delayed_function.init(delayed_function_problem.components)
                    elif delayed_function_type == "DelayedLinearSolver":
                        delayed_function = DelayedLinearSolver()
                    else:
                        raise ValueError("Invalid delayed function")
                    delayed_function.load(full_directory, "delayed_functions_" + str(index) + "_" + str(it.index) + "_content")
                    delayed_functions[it.index] = delayed_function
                    it.iternext()
            # Load inner product
            assert ErrorEstimationInnerProductIO.exists_file(full_directory, "inner_product_matrix_problem_name")
            inner_product_matrix_problem_name = ErrorEstimationInnerProductIO.load_file(full_directory, "inner_product_matrix_problem_name")
            inner_product_matrix_problem = get_problem_from_problem_name(inner_product_matrix_problem_name)
            inner_product_matrix_reduced_problem = get_reduced_problem_from_problem(inner_product_matrix_problem)
            self._content["inner_product_matrix"] = inner_product_matrix_reduced_problem._error_estimation_inner_product
            # Recompute shape
            assert "delayed_functions_shape" not in self._content
            self._content["delayed_functions_shape"] = DelayedTransposeShape((self._content["delayed_functions"][0][0], self._content["delayed_functions"][1][0]))
            # Prepare precomputed slices
            self._precomputed_slices = dict()
            self._prepare_trivial_precomputed_slice()
        elif self._type == "empty":
            pass
        elif self._type == "operators":
            # Load truth content
            assert "truth_operators" not in self._content
            self._content["truth_operators"] = NonAffineExpansionStorageContent_Base(self._shape, dtype=object)
            it = NonAffineExpansionStorageContent_Iterator(self._content["truth_operators"], flags=["c_index", "multi_index", "refs_ok"])
            while not it.finished:
                assert TruthContentItemIO.exists_file(full_directory, "truth_operator_" + str(it.index))
                (problem_name, term, index) = TruthContentItemIO.load_file(full_directory, "truth_operator_" + str(it.index))
                truth_problem = get_problem_from_problem_name(problem_name)
                self._content["truth_operators"][it.multi_index] = truth_problem.operator[term][index]
                it.iternext()
            assert "truth_operators_as_expansion_storage" not in self._content
            self._prepare_truth_operators_as_expansion_storage()
            # Load basis functions content
            assert BasisFunctionsContentLengthIO.exists_file(full_directory, "basis_functions_length")
            basis_functions_length = BasisFunctionsContentLengthIO.load_file(full_directory, "basis_functions_length")
            assert basis_functions_length in (1, 2)
            assert "basis_functions" not in self._content
            self._content["basis_functions"] = list()
            for index in range(basis_functions_length):
                assert BasisFunctionsProblemNameIO.exists_file(full_directory, "basis_functions_" + str(index) + "_problem_name")
                basis_functions_problem_name = BasisFunctionsProblemNameIO.load_file(full_directory, "basis_functions_" + str(index) + "_problem_name")
                assert BasisFunctionsProblemNameIO.exists_file(full_directory, "basis_functions_" + str(index) + "_components_name")
                basis_functions_components_name = BasisFunctionsProblemNameIO.load_file(full_directory, "basis_functions_" + str(index) + "_components_name")
                basis_functions_problem = get_problem_from_problem_name(basis_functions_problem_name)
                basis_functions_reduced_problem = get_reduced_problem_from_problem(basis_functions_problem)
                basis_functions = BasisFunctionsMatrix(basis_functions_reduced_problem.basis_functions.space, basis_functions_components_name if basis_functions_components_name != basis_functions_problem.components else None)
                basis_functions.init(basis_functions_components_name)
                basis_functions_loaded = basis_functions.load(full_directory, "basis_functions_" + str(index) + "_content")
                assert basis_functions_loaded
                self._content["basis_functions"].append(basis_functions)
            # Recompute shape
            self._content["basis_functions_shape"] = DelayedTransposeShape(self._content["basis_functions"])
            # Reset precomputed slices
            self._precomputed_slices = dict()
            self._prepare_trivial_precomputed_slice()
        else:
            raise ValueError("Invalid type")
        return True
        
    def _prepare_trivial_precomputed_slice(self):
        empty_slice = slice(None)
        assert self._type in ("error_estimation_operators_11", "error_estimation_operators_21", "error_estimation_operators_22", "operators")
        if self._type == "error_estimation_operators_11":
            pass # nothing to be done (scalar content)
        elif self._type == "error_estimation_operators_21":
            assert "delayed_functions" in self._content
            assert len(self._content["delayed_functions"]) is 2
            assert "delayed_functions_shape" in self._content
            
            slice_ = slice_to_array(self._content["delayed_functions_shape"], empty_slice, self._content["delayed_functions_shape"]._component_name_to_basis_component_length, self._content["delayed_functions_shape"]._component_name_to_basis_component_index)
            self._precomputed_slices[slice_] = self
        elif self._type == "error_estimation_operators_22":
            assert "delayed_functions" in self._content
            assert len(self._content["delayed_functions"]) is 2
            assert "delayed_functions_shape" in self._content
            
            slice_ = slice_to_array(self._content["delayed_functions_shape"], (empty_slice, empty_slice), self._content["delayed_functions_shape"]._component_name_to_basis_component_length, self._content["delayed_functions_shape"]._component_name_to_basis_component_index)
            self._precomputed_slices[slice_] = self
        elif self._type == "operators":
            assert len(self._content["basis_functions"]) in (1, 2)
            assert "basis_functions_shape" in self._content
            
            if len(self._content["basis_functions"]) is 2:
                slices = slice_to_array(self._content["basis_functions_shape"], (empty_slice, empty_slice), self._content["basis_functions_shape"]._component_name_to_basis_component_length, self._content["basis_functions_shape"]._component_name_to_basis_component_index)
                self._precomputed_slices[slices] = self
            else:
                slice_ = slice_to_array(self._content["basis_functions_shape"], empty_slice, self._content["basis_functions_shape"]._component_name_to_basis_component_length, self._content["basis_functions_shape"]._component_name_to_basis_component_index)
                self._precomputed_slices[slice_] = self
        else:
            raise ValueError("Invalid type")
        
    @overload(slice, )
    def __getitem__(self, key):
        assert self._type in ("error_estimation_operators_21", "operators")
        if self._type == "error_estimation_operators_21":
            assert "delayed_functions" in self._content
            assert len(self._content["delayed_functions"]) is 2
            assert "delayed_functions_shape" in self._content
            
            slice_ = slice_to_array(self._content["delayed_functions_shape"], key, self._content["delayed_functions_shape"]._component_name_to_basis_component_length, self._content["delayed_functions_shape"]._component_name_to_basis_component_index)
            
            if slice_ in self._precomputed_slices:
                return self._precomputed_slices[slice_]
            else:
                output = NonAffineExpansionStorage.__new__(type(self), *self._shape)
                output.__init__(*self._shape)
                output._type = self._type
                output._content["inner_product_matrix"] = self._content["inner_product_matrix"]
                output._content["delayed_functions"] = [NonAffineExpansionStorageContent_Base(self._shape[0], dtype=object), NonAffineExpansionStorageContent_Base(self._shape[1], dtype=object)]
                for q in range(self._shape[0]):
                    output._content["delayed_functions"][0][q] = self._content["delayed_functions"][0][q][key]
                for q in range(self._shape[1]):
                    output._content["delayed_functions"][1][q] = self._content["delayed_functions"][1][q]
                output._content["delayed_functions_shape"] = DelayedTransposeShape((output._content["delayed_functions"][0][0], output._content["delayed_functions"][1][0]))
                self._precomputed_slices[slice_] = output
                return output
        elif self._type == "operators":
            assert "basis_functions" in self._content
            assert len(self._content["basis_functions"]) is 1
            assert "basis_functions_shape" in self._content
            
            slice_ = slice_to_array(self._content["basis_functions_shape"], key, self._content["basis_functions_shape"]._component_name_to_basis_component_length, self._content["basis_functions_shape"]._component_name_to_basis_component_index)
            
            if slice_ in self._precomputed_slices:
                return self._precomputed_slices[slice_]
            else:
                output = NonAffineExpansionStorage.__new__(type(self), *self._shape)
                output.__init__(*self._shape)
                output._type = self._type
                output._content["truth_operators"] = self._content["truth_operators"]
                output._content["truth_operators_as_expansion_storage"] = self._content["truth_operators_as_expansion_storage"]
                output._content["basis_functions"] = list()
                output._content["basis_functions"].append(self._content["basis_functions"][0][key])
                output._content["basis_functions_shape"] = DelayedTransposeShape(output._content["basis_functions"])
                self._precomputed_slices[slice_] = output
                return output
        else:
            raise ValueError("Invalid type")
        
    @overload(tuple_of(slice), )
    def __getitem__(self, key):
        assert self._type in ("error_estimation_operators_22", "operators")
        if self._type == "error_estimation_operators_22":
            assert len(key) is 2
            assert "delayed_functions" in self._content
            assert len(self._content["delayed_functions"]) is 2
            assert "delayed_functions_shape" in self._content
            
            slice_ = slice_to_array(self._content["delayed_functions_shape"], key, self._content["delayed_functions_shape"]._component_name_to_basis_component_length, self._content["delayed_functions_shape"]._component_name_to_basis_component_index)
            
            if slice_ in self._precomputed_slices:
                return self._precomputed_slices[slice_]
            else:
                output = NonAffineExpansionStorage.__new__(type(self), *self._shape)
                output.__init__(*self._shape)
                output._type = self._type
                output._content["inner_product_matrix"] = self._content["inner_product_matrix"]
                output._content["delayed_functions"] = [NonAffineExpansionStorageContent_Base(self._shape[0], dtype=object), NonAffineExpansionStorageContent_Base(self._shape[1], dtype=object)]
                for q in range(self._shape[0]):
                    output._content["delayed_functions"][0][q] = self._content["delayed_functions"][0][q][key[0]]
                for q in range(self._shape[1]):
                    output._content["delayed_functions"][1][q] = self._content["delayed_functions"][1][q][key[1]]
                output._content["delayed_functions_shape"] = DelayedTransposeShape((output._content["delayed_functions"][0][0], output._content["delayed_functions"][1][0]))
                self._precomputed_slices[slice_] = output
                return output
        elif self._type == "operators":
            assert len(key) is 2
            assert "basis_functions" in self._content
            assert len(self._content["basis_functions"]) is 2
            assert "basis_functions_shape" in self._content
            
            slices = slice_to_array(self._content["basis_functions_shape"], key, self._content["basis_functions_shape"]._component_name_to_basis_component_length, self._content["basis_functions_shape"]._component_name_to_basis_component_index)
            
            if slices in self._precomputed_slices:
                return self._precomputed_slices[slices]
            else:
                output = NonAffineExpansionStorage.__new__(type(self), *self._shape)
                output.__init__(*self._shape)
                output._type = self._type
                output._content["truth_operators"] = self._content["truth_operators"]
                output._content["truth_operators_as_expansion_storage"] = self._content["truth_operators_as_expansion_storage"]
                output._content["basis_functions"] = list()
                output._content["basis_functions"].append(self._content["basis_functions"][0][key[0]])
                output._content["basis_functions"].append(self._content["basis_functions"][1][key[1]])
                output._content["basis_functions_shape"] = DelayedTransposeShape(output._content["basis_functions"])
                self._precomputed_slices[slices] = output
                return output
        else:
            raise ValueError("Invalid type")
        
    @overload(int, )
    def __getitem__(self, key):
        assert self._type in ("basis_functions_matrix", "functions_list", "operators")
        if self._type in ("basis_functions_matrix", "functions_list"):
            return self._content[self._type][key]
        elif self._type == "operators":
            return self._delay_transpose(self._content["basis_functions"], self._content["truth_operators"][key])
        else:
            raise ValueError("Invalid type")
            
    @overload(tuple_of(int), )
    def __getitem__(self, key):
        assert self._type in ("error_estimation_operators_11", "error_estimation_operators_21", "error_estimation_operators_22")
        return self._delay_transpose(
            (self._content["delayed_functions"][0][key[0]], self._content["delayed_functions"][1][key[1]]),
            self._content["inner_product_matrix"]
        )
        
    def __iter__(self):
        assert self._type in ("basis_functions_matrix", "functions_list", "operators")
        if self._type in ("basis_functions_matrix", "functions_list"):
            return self._content[self._type].__iter__()
        elif self._type == "operators":
            return (self._delay_transpose(self._content["basis_functions"], op) for op in self._content["truth_operators"].__iter__())
        else:
            raise ValueError("Invalid type")

    @overload((int, tuple_of(int)), AbstractBasisFunctionsMatrix)
    def __setitem__(self, key, item):
        if self._type != "empty":
            assert self._type == "basis_functions_matrix"
        else:
            self._type = "basis_functions_matrix"
            self._content[self._type] = NonAffineExpansionStorageContent_Base(self._shape, dtype=object)
        self._content[self._type][key] = DelayedBasisFunctionsMatrix(item.space)
        self._content[self._type][key].init(item._components_name)
    
    @overload((int, tuple_of(int)), AbstractFunctionsList)
    def __setitem__(self, key, item):
        if self._type != "empty":
            assert self._type == "functions_list"
        else:
            self._type = "functions_list"
            self._content[self._type] = NonAffineExpansionStorageContent_Base(self._shape, dtype=object)
        self._content[self._type][key] = DelayedFunctionsList(item.space)
    
    @overload((int, tuple_of(int)), DelayedTranspose)
    def __setitem__(self, key, item):
        assert isinstance(item._args[0], (AbstractBasisFunctionsMatrix, DelayedBasisFunctionsMatrix, DelayedLinearSolver))
        if isinstance(item._args[0], AbstractBasisFunctionsMatrix):
            if self._type != "empty":
                assert self._type == "operators"
            else:
                self._type = "operators"
            # Reset attributes if size has changed
            if key == self._smallest_key: # this assumes that __getitem__ is not random acces but called for increasing key
                self._content.pop("truth_operators_as_expansion_storage", None)
                self._content["truth_operators"] = NonAffineExpansionStorageContent_Base(self._shape, dtype=object)
                self._content["basis_functions"] = list()
                self._content.pop("basis_functions_shape", None)
            # Store
            assert len(item._args) in (2, 3)
            if len(self._content["basis_functions"]) is 0:
                assert isinstance(item._args[0], AbstractBasisFunctionsMatrix)
                self._content["basis_functions"].append(item._args[0])
            else:
                assert item._args[0] is self._content["basis_functions"][0]
            self._content["truth_operators"][key] = item._args[1]
            if len(item._args) > 2:
                if len(self._content["basis_functions"]) is 1:
                    assert isinstance(item._args[2], AbstractBasisFunctionsMatrix)
                    self._content["basis_functions"].append(item._args[2])
                else:
                    assert item._args[2] is self._content["basis_functions"][1]
            # Recompute shape
            if "basis_functions_shape" not in self._content:
                self._content["basis_functions_shape"] = DelayedTransposeShape(self._content["basis_functions"])
            # Compute truth expansion storage and prepare precomputed slices
            if key == self._largest_key: # this assumes that __getitem__ is not random acces but called for increasing key
                self._prepare_truth_operators_as_expansion_storage()
                self._precomputed_slices = dict()
                self._prepare_trivial_precomputed_slice()
        elif isinstance(item._args[0], (DelayedBasisFunctionsMatrix, DelayedLinearSolver)):
            assert len(item._args) is 3
            assert isinstance(item._args[2], (DelayedBasisFunctionsMatrix, DelayedLinearSolver))
            if isinstance(item._args[0], DelayedLinearSolver):
                assert isinstance(item._args[2], DelayedLinearSolver)
                if self._type != "empty":
                    assert self._type == "error_estimation_operators_11"
                else:
                    self._type = "error_estimation_operators_11"
            elif isinstance(item._args[0], DelayedBasisFunctionsMatrix):
                if isinstance(item._args[2], DelayedLinearSolver):
                    if self._type != "empty":
                        assert self._type == "error_estimation_operators_21"
                    else:
                        self._type = "error_estimation_operators_21"
                elif isinstance(item._args[2], DelayedBasisFunctionsMatrix):
                    if self._type != "empty":
                        assert self._type == "error_estimation_operators_22"
                    else:
                        self._type = "error_estimation_operators_22"
                else:
                    raise TypeError("Invalid arguments to NonAffineExpansionStorage")
            else:
                raise TypeError("Invalid arguments to NonAffineExpansionStorage")
            # Reset attributes if size has changed
            if key == self._smallest_key: # this assumes that __getitem__ is not random acces but called for increasing key
                self._content["delayed_functions"] = [NonAffineExpansionStorageContent_Base(self._shape[0], dtype=object), NonAffineExpansionStorageContent_Base(self._shape[1], dtype=object)]
                self._content.pop("delayed_functions_shape", None)
                self._content.pop("inner_product_matrix", None)
            # Store
            if key[1] == self._smallest_key[1]: # this assumes that __getitem__ is not random acces but called for increasing key
                self._content["delayed_functions"][0][key[0]] = item._args[0]
            else:
                assert item._args[0] is self._content["delayed_functions"][0][key[0]]
            if "inner_product_matrix" not in self._content:
                self._content["inner_product_matrix"] = item._args[1]
            else:
                assert item._args[1] is self._content["inner_product_matrix"]
            if key[0] == self._smallest_key[0]: # this assumes that __getitem__ is not random acces but called for increasing key
                self._content["delayed_functions"][1][key[1]] = item._args[2]
            else:
                assert item._args[2] is self._content["delayed_functions"][1][key[1]]
            # Recompute shape
            if "delayed_functions_shape" not in self._content:
                self._content["delayed_functions_shape"] = DelayedTransposeShape((item._args[0], item._args[2]))
            else:
                assert DelayedTransposeShape((item._args[0], item._args[2])) == self._content["delayed_functions_shape"]
            # Prepare precomputed slices
            if key == self._largest_key: # this assumes that __getitem__ is not random acces but called for increasing key
                self._precomputed_slices = dict()
                self._prepare_trivial_precomputed_slice()
        else:
            raise TypeError("Invalid arguments to NonAffineExpansionStorage")
        
    def _prepare_truth_operators_as_expansion_storage(self):
        from rbnics.backends import NonAffineExpansionStorage
        assert self._type == "operators"
        assert self.order() is 1
        extracted_operators = tuple(op._form for op in self._content["truth_operators"])
        assert "truth_operators_as_expansion_storage" not in self._content
        self._content["truth_operators_as_expansion_storage"] = NonAffineExpansionStorage(extracted_operators)
        
    def __len__(self):
        assert self._type == "operators"
        assert self.order() is 1
        return self._shape[0]
    
    def order(self):
        assert self._type in ("error_estimation_operators_11", "error_estimation_operators_21", "error_estimation_operators_22", "operators")
        return len(self._shape)
        
    def _delay_transpose(self, pre_post, op):
        assert len(pre_post) in (1, 2)
        delayed_transpose = DelayedTranspose(pre_post[0])
        if len(pre_post) is 1:
            return delayed_transpose*op
        else:
            return delayed_transpose*op*pre_post[1]
        
class DelayedTransposeShape(object):
    def __init__(self, basis_functions):
        assert len(basis_functions) in (1, 2)
        component_name_to_basis_component_index = list()
        component_name_to_basis_component_length = list()
        found_delayed_linear_solver = False
        for basis_functions_i in basis_functions:
            assert isinstance(basis_functions_i, (AbstractBasisFunctionsMatrix, DelayedBasisFunctionsMatrix, DelayedLinearSolver))
            if isinstance(basis_functions_i, (AbstractBasisFunctionsMatrix, DelayedBasisFunctionsMatrix)):
                assert not found_delayed_linear_solver # delayed functions should come after basis functions
                component_name_to_basis_component_index.append(basis_functions_i._component_name_to_basis_component_index)
                component_name_to_basis_component_length.append(basis_functions_i._component_name_to_basis_component_length)
            elif isinstance(basis_functions_i, DelayedLinearSolver):
                found_delayed_linear_solver = True
            else:
                raise TypeError("Invalid basis functions")
        assert len(component_name_to_basis_component_length) in (0, 1, 2)
        if len(component_name_to_basis_component_length) is 0:
            pass
        elif len(component_name_to_basis_component_length) is 1:
            self.N = component_name_to_basis_component_length[0]
        elif len(component_name_to_basis_component_length) is 2:
            self.M = component_name_to_basis_component_length[0]
            self.N = component_name_to_basis_component_length[1]
        else:
            raise ValueError("Invalid length")
        self._component_name_to_basis_component_index = tuple(component_name_to_basis_component_index)
        self._component_name_to_basis_component_length = tuple(component_name_to_basis_component_length)
        
    def __eq__(self, other):
        return (
            self._component_name_to_basis_component_index == other._component_name_to_basis_component_index
                and
            self._component_name_to_basis_component_length == other._component_name_to_basis_component_length
        )
