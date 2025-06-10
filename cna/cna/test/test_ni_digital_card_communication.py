#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd. All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Xu Dong at 2024-10
# ----------------------------------------------------------------------


from qcos.cna import NI
import time


# 向NI板卡6536的通道0~7发送数据
# 实例化1个NI数字板卡设备
ni6536 = NI("6536", "Dev2/port0/line0:7", 0)
data = [True, False, False, True, False, False, True, True]

for i in range (0, 1000000):
    # 发送数据
    ni6536.send(data)
    # 暂停100us
    time.sleep(0.0001)

#关闭设备
ni6536.close()

input("Press any key to exit...")
