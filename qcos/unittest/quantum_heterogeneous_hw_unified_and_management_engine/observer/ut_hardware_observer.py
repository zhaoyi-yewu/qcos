#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd.
# All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-10
# ------------------------


import unittest
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    observer.hardware_observer import HardwareObserver


class TestHardwareObserver(unittest.TestCase):
    '''
    测试HardwareObserver抽象基类，确保无法直接实例化
    '''

    def test_cannot_instantiate_abstract_class(self):
        '''
        测试HardwareObserver类不能被实例化
        '''
        # 尝试实例化HardwareObserver，应该抛出TypeError
        with self.assertRaises(TypeError):
            HardwareObserver()


# 运行所有单元测试
if __name__ == '__main__':
    unittest.main()

