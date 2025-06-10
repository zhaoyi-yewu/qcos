from abc import abstractmethod, ABC
import weakref
from .error import *

class InstrumentBase(ABC):
    """
    设备抽象类
    
    Args:
        name (str): 设备名称
        
    _all_instruments：所有实例化的设备集合
    _type：当前实例对应的设备类
    _instances：当前设备类的实例化对象集合
    """
    
    _all_instruments = weakref.WeakValueDictionary()
    _type = None
    _instances = weakref.WeakSet()

    def __init__(self, name: str, **kwargs) -> None:
        
        self.name = name
        for k, v in kwargs.items():
            super().__setattr__(k, v)        
        self.record_instance(self)
    
    def __repr__(self) -> str:
        return f"<{type(self).__name__}: {self.name}>"

    def __del__(self) -> None:
        try:
            self.close()
        except:
            raise DeveiceCloseError(f"del instrument {self.name} error")

    @classmethod
    def record_instance(cls, instance) -> None:
        """
        Record (a weak ref to) an instance in a class's instance list.
        """
        name = instance.name
        existing_instr = cls._all_instruments.get(name)
        if existing_instr:
            raise DeveiceDefineError(f"Another instrument has the name: {name}")

        cls._all_instruments[name] = instance
        if getattr(cls, "_type", None) is not cls:
            cls._type = cls
            cls._instances = weakref.WeakSet()
        cls._instances.add(instance)
    
    @classmethod
    def remove_instance(cls, instance) -> None:
        """
        Remove a particular instance from the record.
        """
        if instance in cls._instances:
            cls._instances.remove(instance)
        all_ins = cls._all_instruments
        for name, ref in list(all_ins.items()):
            if ref is instance:
                del all_ins[name]
                        
    @classmethod
    def instances(cls):
        """
        Get all currently defined instances of this instrument_base class.
        """
        if getattr(cls, "_type", None) is not cls:
            return []
        return list(getattr(cls, "_instances", weakref.WeakSet()))

    @classmethod
    def find_instrument(cls, name):
        """
        获取指定名称的硬件设备实例
        """
        if name not in cls._all_instruments:
            raise DeveiceAccessError(f"Instrument with name {name} does not exist")
        return cls._all_instruments[name]
                    
    def close(self):
        self.remove_instance(self)
    
    def snapshot(self):
        return self.__dict__.copy()

    @abstractmethod
    def comm(self, send_data, **kwargs):
        """
        对外通信接口，集成了数据预处理、发送、接收及数据后处理
        """
        pass
