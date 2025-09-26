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


# 向NI板卡6738的通道0~7发送数据
# 实例化1个NI模拟板卡设备
ni6738 = NI("6738", "Dev1/ao0", 1) 
data = [1.1, 2.2, 3.3, 4.4, 5.5]

for i in range (0, 1000000):
    # 发送数据
    ni6738.send(data)
    # 暂停100us
    time.sleep(0.0001)

#关闭设备
ni6738.close()

input("Press any key to exit...")
