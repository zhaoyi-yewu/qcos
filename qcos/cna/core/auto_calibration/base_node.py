from __future__ import annotations
import time
from typing import Any
import weakref

class State():
    '''
    class representing the experimental detection status

    in_spec: the figures of merit associated with the cal are in spec
    out_of_spec: figures of merit associated with the cal are out of spec
    bad: dependence for this cal has a bad state
    '''
    
    in_spec = 1
    out_of_spec = 2
    bad = 3    

class CalibrationNode():
    '''
    node in calibration's dag

    Args:
        name: node name
        exp: experiment, which used to do calibration or check,
        time_threshold: perform calibration every `time_threshold` seconds
    '''
    
    instance = None

    def __init__(
        self, 
        name: str,
        time_threshold = 3600*24
    ) -> None:

        self.name = name
        self.check_time = time.time() - time_threshold
        self.calib_time = time.time() - time_threshold
        self.time_threshold = time_threshold
        self.dependency = weakref.WeakSet()
    
    def __new__(cls, *agrs, **kwargs):
        """
        采用单例模式，每个具体的节点类仅包含一个实例
        """
        if cls.instance == None:
            cls.instance = object.__new__(cls)
            return cls.instance
        return cls.instance
    
    def do_calibrate(self):
        '''
        do calibration and update the calibration time
        '''

        if hasattr(self, "pre_process"):
            self.pre_process()
        
        if hasattr(self, "run"):
            time.sleep(0.2)
            self.run()
        
        if hasattr(self, 'post_process'):
            self.post_process()

        self.calib_time = time.time()
    
    def do_check(self) -> State:
        '''
        do check and update the check time
        '''

        state = State.in_spec
        if hasattr(self, "check"):
            time.sleep(0.2)
            state = self.check()
        
        self.check_time = time.time()
        
        return state