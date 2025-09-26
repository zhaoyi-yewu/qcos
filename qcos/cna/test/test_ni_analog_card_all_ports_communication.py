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


# 向NI板卡6738的所有通道发送数据
# 实例化4个NI模拟板卡设备
ni6738_ao0 = NI("ni6738_ao0", "Dev1/ao0", 1)
ni6738_ao1 = NI("ni6738_ao1", "Dev1/ao1", 1)
ni6738_ao2 = NI("ni6738_ao2", "Dev1/ao2", 1)
ni6738_ao3 = NI("ni6738_ao3", "Dev1/ao3", 1)

data = [1.1, 2.2, 3.3, 4.4, 5.5]

for i in range (0, 1000000):
    # 发送数据
    ni6738_ao0.send(data)    
    ni6738_ao1.send(data)    
    ni6738_ao2.send(data)   
    ni6738_ao3.send(data)
    # 暂停100us
    time.sleep(0.0001)

ni6738_ao0.close()
ni6738_ao1.close()
ni6738_ao2.close()
ni6738_ao3.close()

input("Press any key to exit...")
