from .hardware_base import HardwareBase
from .error import *
try:
    from .awgDriver import SD_AOU, SD_Waveshapes, SD_TriggerModes, SD_Wave
except:
    pass
import os
import json
import numpy as np


class AWG(HardwareBase):

    def __init__(self, name, awgConfig: dict, **kwargs) -> None:
        self.module = SD_AOU()
        self.moduleID = self.module.openWithSerialNumber(awgConfig['product'], awgConfig['serialNumber'])
        self.awgConfig = dict(awgConfig)
        self.samplingRateMHz = awgConfig.get('samplingRateMHz', 500)  # 采样频率，MHZ

        if self.moduleID < 0:
            raise DeveiceConnectionError(f"warning: Module open error: {self.moduleID}")

        self.channelList = awgConfig['channelList']

        self.amp = awgConfig.get('amp', 0.5)  # 测试反馈说 (0.05 -> 100mV) awg最大只能输出 0.5  （也就是1V的 amp）
        wave_id_file = awgConfig.get('wave_id_file', './')
        self.wave_id = {}
        if not os.path.exists(wave_id_file):
            self.wave_id = self.load_queue_wave2_awg()
        else:
            with open(wave_id_file, 'r') as f:
                self.wave_id = json.loads(f.read())

        self.waveformType = 0

        for CHANNEL in self.channelList:
            ecode = self.module.channelAmplitude(CHANNEL, self.amp)  # 不要注释此行！！！
            ecode = self.module.channelWaveShape(CHANNEL, SD_Waveshapes.AOU_AWG)
            trigger = 0  # 触发口
            trigger_behavior = 3  # 上升沿
            mode = 0
            self.module.AWGtriggerExternalConfig(CHANNEL, trigger, trigger_behavior, mode)
            self.module.AWGflush(CHANNEL)
        super().__init__(name, **kwargs)
        self.generator = GenerateDynamicC3C4(awgFreMhz=self.samplingRateMHz)

    def holding(self, channelList=None):
        # print("保持末端输出")
        if channelList is None:
            channelList = self.channelList
        for channel in channelList:
            self.setQueueWaveIntoChannel(channel, self.wave_id['final_wave'], trigger='software', cycles=0)
        self.startMultipChannel(channelList=channelList)

    def __del__(self):
        # 这里添加清理逻辑
        # print("Resource deallocated")
        self.module.close()

    # 该函数已启用
    def send(self, send_data, **kwargs):
        pass

    def sendSingleChannel(self,
                          wave: list,
                          channelID: int,
                          trigger: str = "external",
                          flush: bool = True,
                          cycles: int = 1,
                          amp: float = None,
                          **kw):
        r""" 发送自定义波形到channel，主要发送ch3, ch4的通道数据
            * 此函数自带 awgStart,

        Args:
            wave (list): wave array data
            channelID (int): channel-id
            trigger (str, optional): 'external' / 'externalcycle / 'software'  . Defaults to "external".
            flush (bool, optional): _description_. Defaults to True.
            cycles (int, optional): _description_. Defaults to 1.
        """
        #
        if flush: self.module.AWGflush(channelID)
        if trigger.lower() == 'external':
            triggerMode = SD_TriggerModes.EXTTRIG  # Hardware trigger. The AWG waits for an external trigger.
        elif trigger.lower() == 'software':
            triggerMode = SD_TriggerModes.AUTOTRIG  # The waveform is launched after AWGstart, or when the previous waveform in the queue finishes
        elif trigger.lower() == 'externalcycle':
            triggerMode = SD_TriggerModes.EXTTRIG_CYCLE  # trigger to get each cycle
        else:
            raise DeveiceParameterError(f"undifeined trigger={trigger}")

        if amp is not None:
            self.module.channelAmplitude(channelID, amp)

        delay = 0
        prescaler = 0
        returnCode = self.module.AWGfromArray(channelID, triggerMode, delay, cycles, prescaler, self.waveformType, wave)
        return returnCode

    def setQueueWaveIntoChannel(self,
                                channel: int,
                                qid: int,
                                trigger: str = "external",
                                flush: bool = True,
                                cycles: int = 1,
                                amp: float = None,
                                **kwargs):
        r"""从queue中调取波形到channel去，主要发送ch1, ch2的通道数据
            * remenber to call startMultipChannel()

        Args:
            channel (int): channel-id
            qid (int): queue-id
            trigger (str, optional): 'external' / 'software' . Defaults to "external".
            flush (bool, optional): _description_. Defaults to True.
        """
        # 次函数没有awgStart, 需要自己call startMultipChannel
        if flush: self.module.AWGflush(channel)
        if trigger.lower() == 'external':
            triggerMode = SD_TriggerModes.EXTTRIG  # Hardware trigger. The AWG waits for an external trigger.
        elif trigger.lower() == 'software':
            triggerMode = SD_TriggerModes.AUTOTRIG  # The waveform is launched after AWGstart, or when the previous waveform in the queue finishes
        else:
            raise DeveiceParameterError(f"undifeined trigger={trigger}")

        if amp is not None:
            self.module.channelAmplitude(channel, amp)
        triggerMode = triggerMode
        delay = 0
        prescaler = 0
        self.module.AWGqueueWaveform(nAWG=channel, waveformNumber=qid, triggerMode=triggerMode, startDelay=delay,
                                     cycles=cycles, prescaler=prescaler)

    def setRamanWave(self, waves, **kwargs):
        channelList = kwargs.get("channelList", self.channelList)
        nChannel = len(channelList)
        if len(waves) != nChannel:
            raise Exception(f"dimsion of input data [{len(waves)}] donot match number of channels [{len(channelList)}]")

        amp = kwargs.get('amp', self.amp)

        for i in range(nChannel):
            self.module.channelAmplitude(channelList[i], amp)
            self.module.AWGflush(channelList[i])
            for j, wave in enumerate(waves[i]):
                trigger = 'software'
                if j == 0:
                    trigger = 'external'
                # print(f'wave: {wave}, id: {self.wave_id[wave]}')
                self.setQueueWaveIntoChannel(channel=channelList[i], qid=self.wave_id[wave], trigger=trigger,
                                             flush=False)

    def appendQueueWave(self, qid: int, dataFilePath: str):
        wave = SD_Wave()
        c = wave.newFromFile(dataFilePath)
        # error = wave.newFromArrayDouble(SD_WaveformTypes.WAVE_ANALOG,  list(queueData)  )
        print(f"load file-data into queue with return code = {c}")
        self.module.waveformLoad(wave, qid)

    def setArrangeWave(self, waves, **kwargs):
        """重排波形发送

        Args:
            waves (_type_): 重排操作对应波形名称
        """
        channelList = kwargs.get("channelList", self.channelList)
        nChannel = len(channelList)

        if len(waves) != nChannel:
            raise Exception(
                f"dimsion of input data [{len(waves)}] do not match number of channels [{len(channelList)}]")

        amp = kwargs.get('amp', self.amp)
        triggerMode = SD_TriggerModes.AUTOTRIG  # The waveform is launched automatically after AWGstart, or when the previous waveform in the queue finishes
        cycles = 1
        delay = 0
        prescaler = 0

        for i in range(nChannel):

            self.module.channelAmplitude(channelList[i], amp)
            self.module.AWGflush(channelList[i])
            for wave in waves[i]:
                # print(f'wave: {wave}, id: {self.wave_id[wave]}')
                self.module.AWGqueueWaveform(nAWG=channelList[i], waveformNumber=self.wave_id[wave],
                                             triggerMode=triggerMode, startDelay=delay, cycles=cycles,
                                             prescaler=prescaler)

            self.module.AWGqueueWaveform(nAWG=channelList[i], waveformNumber=self.wave_id['final_wave'],
                                         triggerMode=triggerMode, startDelay=delay, cycles=10, prescaler=prescaler)

    def startMultipChannel(self, **kwargs):
        channelList = kwargs.get("channelList", self.channelList)
        AWGmask = self.convert_to_decimal(channelList)
        self.module.AWGstartMultiple(AWGmask)

    def receive(self, **kwargs):
        pass

    @staticmethod
    def convert_to_decimal(channelList):
        channel_list = [i - 1 for i in channelList]
        result = 0
        for bit_position in channel_list:
            result |= 1 << bit_position
        return result

    def load_queue_wave2_awg(self):
        r'load all waves into awg from <waveFileDir>'
        DirPath = self.awgConfig.get('waveFileDir', None)
        if DirPath is None:
            raise DeveiceParameterError("wavefile-path not set")
        self.module.waveformFlush()
        files = os.listdir(DirPath)
        qid = 0
        wave_id = {}
        for f in files:
            if f.endswith('.dat'):
                self.appendQueueWave(qid, os.path.join(DirPath, f))
                wave_id[f[:-4]] = qid
                qid += 1
        with open("./wave_id.json", 'w') as f:
            f.write(json.dumps(wave_id))
        return wave_id


class WaveGenerator():

    def __init__(self, awgFreMhz=500, **kw):
        self.awgFreMhz = awgFreMhz
        self.awg_dt = 1 / self.awgFreMhz / 1e6  # in sec
        self._z = 0.1 * self.awg_dt

    def generate_periodFunc(self, freMHz, nT: int, func):
        """generate any type of wave

        Args:
            freMHz (_type_):
            nT (int): number of cycles
            func (_type_): func(x) must preodic in [0,2pi]
        """
        omega = 2 * np.pi * (freMHz * 1e6)
        tList = np.arange(0, nT / (freMHz * 1e6) + self._z, self.awg_dt)
        wave1 = np.array([func(x) for x in omega * tList])
        return wave1

    def generate_sinWave(self, freMHz, nT: int):
        return self.generate_periodFunc(freMHz=freMHz, nT=nT, func=np.sin)

    def constantArray(self, segList: list[tuple[float, float]]):
        # seg = [ Amp, durationSec ]
        res = []
        for (amp, duration) in segList:
            n = int((duration + self._z) / self.awg_dt)
            res += [amp] * n
        return res

    @staticmethod
    def _helper_writeData2File(dataList, filePath, name):
        n = len(dataList)
        with open(filePath, 'w') as f:
            f.write(f"waveformName,{name}\n")
            f.write(f"waveformPoints,{n}\n")
            f.write(f"waveformType,WAVE_ANALOG_16\n")
            for d in dataList:
                f.write(f"{d:.5f}\n")


class GenerateDynamicC3C4():
    '''                                                ┊                            ┊                        ┊
                      ┌─────┐                 ─────────┐     ┌──────         ───────┐     ┌──────     ───────┐
    channel3    ──────┘  t3 └─────                     └─────┘  t3                  └─────┘  t3          t3  └─────
                   ┊  ┊     ┊  ┊                       ┊  ┊  ┊                      ┊  ┊  ┊                  ┊  ┊
                   ┊t1┊     ┊t2┊                       ┊t2┊t1┊                      ┊t2┊t1┊                  ┊t2┊
                   ┊  ┊     ┊  ┊                       ┊  ┊  ┊                      ┊  ┊  ┊                  ┊  ┊
                 t0┌───────────┐ t5                    ┊  ┌─────────         ──────────┐  ┊           ──────────┐
    channel4    ───┘    t4     └──            ────────────┘    t4                   ┊  └─────────            ┊  └──
                                                       ┊                            ┊
                       Ry                            Rx + Ry                        Ry + Rx               Ry + end

    '''

    def __init__(self, awgFreMhz: float = 500, amp3=1, amp4=1, t0Us=10, t1Us=10, t2Us=10, t5Us=100):
        self.wg = WaveGenerator(awgFreMhz=awgFreMhz)
        self._awgFreMhz = awgFreMhz
        self._dt = self.wg.awg_dt  # sec
        self._t0 = t0Us  # very beginning, all in MuSec
        self._t1 = t1Us
        self._t2 = t2Us
        self._t5 = t5Us  # very final
        self.amp3 = amp3
        self.amp4 = amp4
        self._z = self.wg._z

    def _generateC3C4(self, actionList: list[tuple[bool, float]]) -> tuple[list, list]:
        r"""
            对于一个已经对准(机械移动已经完成)的激光口，将对qubit的所有操作转换成一个波形

        Args:
            actionList (list[tuple[bool,float]]): example -> item = (  T,  0.53   )    T/F represents Ry/Rx,  t = 0.53 muSec represents   exp(-iHt)

        Returns:
            tuple[list,list]: c3Wave,c4Wave
        """
        a3, a4 = self.amp3, self.amp4
        c3 = self.wg.constantArray([(0, self._t0 * 1e-6)])
        c4 = list(c3)
        preRy = False
        t1 = self._t1 * 1e-6
        t2 = self._t2 * 1e-6
        for (ry, t) in actionList:
            t3 = t * 1e-6
            if ry:
                if preRy:
                    # Ry + Ry
                    c3 += self.wg.constantArray([(a3, t3)])
                    c4 += self.wg.constantArray([(a4, t3)])
                else:
                    # Rx + Ry
                    c3 += self.wg.constantArray([(0, t1 + t2), (a3, t3)])
                    c4 += self.wg.constantArray([(0, t2), (a4, t1 + t3)])
            else:
                if preRy:
                    # Ry + Rx
                    c3 += self.wg.constantArray([(0, t1 + t2), (a3, t3)])
                    c4 += self.wg.constantArray([(a4, t2), (0, t1 + t3)])
                else:
                    # Rx + Rx
                    c3 += self.wg.constantArray([(a3, t3)])
                    c4 += self.wg.constantArray([(0, t3)])
            preRy = ry
        if preRy:
            c3 += self.wg.constantArray([(0, t2)])
            c4 += self.wg.constantArray([(a4, t2)])

        fi = self.wg.constantArray([(0, self._t5 * 1e-6)])
        c3 += fi
        c4 += fi
        return c3, c4

    def _generateC3C4withFixLength(self, actionList: list[tuple[bool, float]], fixN: int):
        c3, c4 = self._generateC3C4(actionList=actionList)
        l3, l4 = len(c3), len(c4)
        totalTimeMuSec = (max(l3, l4) * self._dt) * 1e6
        if fixN <= min(l3, l4):
            raise Exception("cycle length too short!")
        c3 = [0] * (fixN - l3) + c3
        c4 = [0] * (fixN - l4) + c4
        return c3, c4, totalTimeMuSec

    def generateFullWave(self,
                         tCycleMuSec: float,
                         gates: list[list[tuple[bool, float]]]
                         ) -> tuple[list[float], list[float]]:
        resC3, resC4 = [], []
        fixN = int((tCycleMuSec + self._z) * self._awgFreMhz)
        for qubitGates in gates:
            c3, c4, totalTimeMuSec = self._generateC3C4withFixLength(qubitGates, fixN)
            resC3 += c3
            resC4 += c4
        return resC3, resC4

