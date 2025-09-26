#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd. All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Xu Dong at 2024-09
# ----------------------------------------------------------------------


import unittest
from qcos.cna.core.config import FpgaSetting
from qcos.cna.core.instrument.error import DeveiceParameterError


class Test(unittest.TestCase):

    def test_get_port(self):
        self.assertEqual(FpgaSetting.get_port(), "COM5")

    def test_set_port_upper_case(self):
        FpgaSetting.set_port("COM7")
        self.assertEqual(FpgaSetting.get_port(), "COM7")

    def test_set_port_lower_case(self):
        FpgaSetting.set_port("com99")
        self.assertEqual(FpgaSetting.get_port(), "com99")

    def test_set_invalid_port_value_type1(self):
        try:
            FpgaSetting.set_port("10COM")
        except DeveiceParameterError as e:
            assert e.code == 404
            assert e.msg == "invalid port value: 10COM"

    def test_set_invalid_port_value_type2(self):
        try:
            FpgaSetting.set_port("Com7")
        except DeveiceParameterError as e:
            assert e.code == 404
            assert e.msg == "invalid port value: Com7"

    def test_set_invalid_port_value_type3(self):
        try:
            FpgaSetting.set_port("COMM7")
        except DeveiceParameterError as e:
            assert e.code == 404
            assert e.msg == "invalid port value: COMM7"

    def test_get_clock_period(self):
        self.assertEqual(FpgaSetting.get_clock_period(), 1E06)

    def test_set_clock_period(self):
        FpgaSetting.set_clock_period(2E06)
        self.assertEqual(FpgaSetting.get_clock_period(), 2E06)

    def test_set_invalid_clock_period(self):
        try:
            FpgaSetting.set_clock_period(-99)
        except DeveiceParameterError as e:
            assert e.code == 404
            assert e.msg == "invalid clock_period value: -99"

    def test_get_test_time(self):
        self.assertEqual(FpgaSetting.get_test_time(), 0.5)

    def test_set_test_time(self):
        FpgaSetting.set_test_time(1.0)
        self.assertEqual(FpgaSetting.get_test_time(), 1.0)

    def test_set_invalid_test_time(self):
        try:
            FpgaSetting.set_test_time(-99.5)
        except DeveiceParameterError as e:
            assert e.code == 404
            assert e.msg == "invalid test_time value: -99.5"

    def test_get_bytes_returned(self):
        self.assertEqual(FpgaSetting.get_bytes_returned(), 12)

    def test_set_bytes_returned(self):
        FpgaSetting.set_bytes_returned(24)
        self.assertEqual(FpgaSetting.get_bytes_returned(), 24)

    def test_set_invalid_bytes_returned(self):
        try:
            FpgaSetting.set_bytes_returned(-99)
        except DeveiceParameterError as e:
            assert e.code == 404
            assert e.msg == "invalid bytes_returned value: -99"


if __name__ == '__main__':
    unittest.main()
