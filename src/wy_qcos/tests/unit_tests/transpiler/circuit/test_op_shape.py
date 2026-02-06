#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import pytest

from wy_qcos.transpiler.cmss.circuit.operators.op_shape import OpShape


class TestOpShape:
    @pytest.mark.smoke
    def test_op_shape(self):
        op_shape = OpShape(
            dims_l=(2, 2), dims_r=(2, 2), num_qargs_r=2, num_qargs_l=2
        )
        assert op_shape._dims_l == (2, 2)
        assert op_shape._dims_r == (2, 2)

        assert op_shape.dims_r() == (2, 2)
        assert op_shape.dims_l() == (2, 2)
        assert op_shape.size == 16
        assert op_shape.num_qubits is None
        assert op_shape.shape == (4, 4)
        assert op_shape.tensor_shape == (2, 2, 2, 2)
        assert op_shape.is_square is True

        op_shape = OpShape(num_qargs_r=2, num_qargs_l=2)
        assert op_shape.num_qubits == 2
        op_shape = OpShape(num_qargs_r=2, num_qargs_l=3)
        assert op_shape.num_qubits is None
        op_shape = OpShape(num_qargs_r=2)
        assert op_shape.num_qubits == 2

    def test_op_shape_compose(self):
        op_shape = OpShape()
        other_shape = OpShape()
        ret = op_shape.compose(other_shape)
        assert ret._num_qargs_l == 0 and ret._num_qargs_r == 0
        assert ret._dims_l is None and ret._dims_r is None

        ret = op_shape.compose(other_shape, front=True)
        assert ret._num_qargs_l == 0 and ret._num_qargs_r == 0
        assert ret._dims_l is None and ret._dims_r is None

        op_shape = OpShape(num_qargs_r=1, num_qargs_l=1)
        other_shape = OpShape()
        with pytest.raises(Exception) as e:
            ret = op_shape.compose(other_shape)

        err_msg = str(e.value)
        assert "Left and right compose dimensions don't match" in err_msg

        with pytest.raises(Exception) as e:
            ret = op_shape.compose(other_shape, front=True)

        err_msg = str(e.value)
        assert "Left and right compose dimensions don't match" in err_msg

        op_shape = OpShape(
            dims_l=(3, 2), dims_r=(3, 2), num_qargs_r=2, num_qargs_l=2
        )
        other_shape = OpShape(
            dims_l=(2, 3), dims_r=(2, 3), num_qargs_r=2, num_qargs_l=2
        )
        ret = op_shape.compose(other_shape, front=True, qargs=[1, 0])
        assert ret.dims_l() == (3, 2) and ret.dims_r() == (3, 2)
        with pytest.raises(Exception) as e:
            ret = op_shape.compose(other_shape, front=True, qargs=[0])
        err_msg = str(e.value)
        assert "Number of qargs does not match" in err_msg
        with pytest.raises(Exception) as e:
            ret = op_shape.compose(other_shape, front=True, qargs=[0, 1])
        err_msg = str(e.value)
        assert "Subsystem dimension do not match on specified qargs" in err_msg

        ret = op_shape.compose(other_shape, front=False, qargs=[1, 0])
        assert ret.dims_l() == (3, 2) and ret.dims_r() == (3, 2)
        with pytest.raises(Exception) as e:
            ret = op_shape.compose(other_shape, front=True, qargs=[0])
        err_msg = str(e.value)
        assert "Number of qargs does not match" in err_msg
        with pytest.raises(Exception) as e:
            ret = op_shape.compose(other_shape, front=True, qargs=[0, 1])
        err_msg = str(e.value)
        assert "Subsystem dimension do not match on specified qargs" in err_msg

    def test_op_shape_auto(self):
        # Initialize the shape
        shape = OpShape.auto(shape=(4, 4))
        assert shape._dims_l is None
        assert shape._num_qargs_l == 2

        # Initialize the num_qubits
        shape = OpShape.auto(num_qubits=2)
        assert shape._dims_l is None
        assert shape._num_qargs_l == 2

        # Initialize the
        shape = OpShape.auto(dims_l=(2,), dims_r=(2,))
        assert shape._dims_l is None
        assert shape._num_qargs_l == 1
        shape = OpShape.auto(dims_l=(4, 4), dims_r=(4, 4))
        assert shape._dims_l == (4, 4)
        assert shape._num_qargs_l == 2

        shape = OpShape.auto(dims=3)
        assert shape._dims_l == (3,)
        assert shape._num_qargs_l == 1

        with pytest.raises(Exception) as e:
            OpShape.auto(dims=2, dims_r=2)

        err_msg = str(e.value)
        assert err_msg == "dims cannot be used with dims_l or dims_r"

        with pytest.raises(Exception) as e:
            OpShape.auto(num_qubits=2, num_qubits_l=2)

        err_msg = str(e.value)
        assert "num_qubits cannot be used" in err_msg

    def test_shape_validate(self):
        with pytest.raises(Exception) as e:
            OpShape().validate_shape(shape=(2, 2, 2))

        err_msg = str(e.value)
        assert "Input shape is not 1 or" in err_msg
        res = OpShape()._validate(shape=(2, 2, 2))
        assert res is False

        with pytest.raises(Exception) as e:
            OpShape(dims_l=(2, 2)).validate_shape(shape=(2, 2))

        err_msg = str(e.value)
        assert "Output dimensions do not match" in err_msg
        res = OpShape(dims_l=(2, 2))._validate(shape=(2, 2))
        assert res is False

        with pytest.raises(Exception) as e:
            OpShape(num_qargs_l=2).validate_shape(shape=(2, 2))

        err_msg = str(e.value)
        assert "Number of left qubits" in err_msg
        res = OpShape(num_qargs_l=2)._validate(shape=(2, 2))
        assert res is False

        with pytest.raises(Exception) as e:
            OpShape(dims_r=(2, 2), num_qargs_l=1).validate_shape(shape=(2, 2))

        err_msg = str(e.value)
        assert "Input dimensions do not match matrix shape" in err_msg
        res = OpShape(dims_r=(2, 2), num_qargs_l=1)._validate(shape=(2, 2))
        assert res is False

        with pytest.raises(Exception) as e:
            OpShape(num_qargs_l=1, num_qargs_r=2).validate_shape(shape=(2, 2))

        err_msg = str(e.value)
        assert "Number of right qubits" in err_msg
        res = OpShape(num_qargs_l=1, num_qargs_r=2)._validate(shape=(2, 2))
        assert res is False

        with pytest.raises(Exception) as e:
            OpShape(num_qargs_l=1, num_qargs_r=2).validate_shape(shape=(2,))

        err_msg = str(e.value)
        assert "Input dimension should be" in err_msg
        res = OpShape(num_qargs_l=1, num_qargs_r=2)._validate(shape=(2,))
        assert res is False
