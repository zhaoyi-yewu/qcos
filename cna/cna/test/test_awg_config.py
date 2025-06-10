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
from qcos.cna.core.config import AwgSetting
from qcos.cna.core.instrument.error import DeveiceParameterError


class TestAwgSetting(unittest.TestCase):

    def test_get_sampling_rate(self):
        self.assertEqual(AwgSetting.get_sampling_rate(), 625)

    def test_set_sampling_rate(self):
        AwgSetting.set_sampling_rate(1000)
        self.assertEqual(AwgSetting.get_sampling_rate(), 1000)

    def test_set_invalid_sampling_rate(self):
        try:
            AwgSetting.set_sampling_rate(-200)
        except DeveiceParameterError as e:
            assert e.code == 404
            assert e.msg == "invalid sampling_rate value: -200"

    def test_get_delay(self):
        self.assertEqual(AwgSetting.get_delay(), 0)

    def test_set_delay(self):
        AwgSetting.set_delay(10)
        self.assertEqual(AwgSetting.get_delay(), 10)

    def test_set_invalid_delay_time(self):
        try:
            AwgSetting.set_delay(-200)
        except DeveiceParameterError as e:
            assert e.code == 404
            assert e.msg == "invalid delay value: -200"

    def test_get_test_time(self):
        self.assertEqual(AwgSetting.get_test_time(), 0.5)

    def test_set_test_time(self):
        AwgSetting.set_test_time(1.0)
        self.assertEqual(AwgSetting.get_test_time(), 1.0)

    def test_set_invalid_test_time(self):
        try:
            AwgSetting.set_test_time(-100.0)
        except DeveiceParameterError as e:
            assert e.code == 404
            assert e.msg == "invalid test_time value: -100.0"

    def test_get_awg_address(self):
        self.assertEqual(AwgSetting.get_awg_address(), '192.168.1.1')

    def test_set_awg_address(self):
        AwgSetting.set_awg_address('192.168.1.2')
        self.assertEqual(AwgSetting.get_awg_address(), '192.168.1.2')

    def test_set_invalid_awg_addresss(self):
        try:
            AwgSetting.set_awg_address('256.256.256.256')
        except DeveiceParameterError as e:
            assert e.code == 404
            assert e.msg == "invalid awg_address: 256.256.256.256"

    def test_is_valid_ip(self):
        self.assertTrue(AwgSetting.is_valid_ip('192.168.1.1'))
        self.assertFalse(AwgSetting.is_valid_ip('256.168.1.1'))
        self.assertFalse(AwgSetting.is_valid_ip('10.168.#.1'))
        self.assertFalse(AwgSetting.is_valid_ip('10.168.1000.1'))
        self.assertFalse(AwgSetting.is_valid_ip('a.b.c.d'))
        self.assertFalse(AwgSetting.is_valid_ip('192.168..1'))


if __name__ == '__main__':
    unittest.main()
