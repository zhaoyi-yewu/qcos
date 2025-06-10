from .base_node import *

"""
校准节点定义，用户可按此格式定义自己的校准节点
"""
class LoadIonExp(CalibrationNode):
    """
    原子加载
    """
    def __init__(self):
        super().__init__('LoadIon', time_threshold=1)

    def run(self):
        pass

    def check(self):
        return State.in_spec

class DetectionExp(CalibrationNode):
    """
    测量
    """
    def __init__(self):
        super().__init__('Detection')
        self.dependency.add(LoadIonExp)
        
    def run(self):
        pass

    def check(self):
        return State.in_spec

class DopplerExp(CalibrationNode):
    """
    频率锁定和温度测量
    """
    def __init__(self):
        super().__init__('Doppler')
        self.dependency.add(LoadIonExp)
        
    def run(self):
        pass

    def check(self):
        return State.in_spec

class PumpingExp(CalibrationNode):
    """
    原子初始化
    """
    def __init__(self):
        super().__init__('Pumping')
        self.dependency.add(LoadIonExp)
        
    def run(self):
        pass

    def check(self):
        return State.out_of_spec

class EITExp(CalibrationNode):
    """
    激光的频率和强度的调整
    """
    def __init__(self):
        super().__init__('EIT')
        self.dependency.add(DopplerExp)
        self.dependency.add(DetectionExp)
        self.dependency.add(PumpingExp)
        
    def run(self):
        pass

    def check(self):
        return State.bad

class ModeFrequencyExp(CalibrationNode):
    """
    光腔中光模式的调节
    """
    def __init__(self):
        super().__init__('ModeFrequency')
        self.dependency.add(EITExp)
        
    def run(self):
        pass

    def check(self):
        return State.bad

class SideBandCoolingExp(CalibrationNode):
    """
    侧带冷却
    """
    def __init__(self):
        super().__init__('SideBandCooling')
        self.dependency.add(ModeFrequencyExp)
        
    def run(self):
        pass

    def check(self):
        return State.bad
