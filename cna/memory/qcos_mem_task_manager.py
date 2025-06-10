#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd. All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-08
# ------------------------


from qcos.cna.core.emccd.get_camera import get_real_camera
from qcos.cna.core.compiler.gate_to_seq import gate_to_seq
from qcos.cna.core.compiler.decompose import transpiler, optimizer
from qcos.cna.core.compiler.parser import get_abs_tree, get_ir
from qcos.cna.core.sequencer import *
from qcos.log.qcos_log import QCOSLogger
from qcos.config.qcos_config_manager import qcos_configer
from qcos.cna.core.mapping.na_mapping import NARoute, NASingleRoute
# from qcos.cna.core.instrument.instrument_base import InstrumentBase
# from qcos.cna.core.instrument.awg import AWG
# from qcos.cna.core.instrument.ni import NI
from qcos.cna.core.rearrange.rearrangement import ReArrangement
import random
from qcos.quantum_heterogeneous_hw_unified_and_management_engine.hardware_interfaces.awg_interface import AWGInterface
from qcos.quantum_heterogeneous_hw_unified_and_management_engine.hardware_interfaces.ni_chassis_interface import (
    NIAOInterface, NIDOInterface)
from qcos.quantum_heterogeneous_hw_unified_and_management_engine.hardware_interfaces.camera_interface import \
    CameraInterface

# 创建日志记录器实例
qcos_logger = QCOSLogger()


class QuantumTaskCommand(ABC):
    """
    量子任务命令抽象基类，用于实现命令模式
    """

    @abstractmethod
    def execute(self):
        pass


class QuantumTaskDecorator(QuantumTaskCommand):
    """
    量子任务装饰器基类，用于实现装饰器模式
    """

    def __init__(self, task: QuantumTaskCommand):
        """
        初始化装饰器

        参数:
        task (QuantumTaskCommand): 被装饰的量子任务
        """
        self._task = task

    def execute(self):
        """
        执行被装饰的量子任务
        """
        self._task.execute()


class QuantumCircuitTask(QuantumTaskCommand):
    """
    具体量子任务执行类
    """

    __slots__ = ('task_id', 'last_active_time', 'openqasm_content')

    def __init__(self, task_id: str):
        """
        初始化量子电路任务
        """
        # 初始化任务ID
        self.task_id = task_id
        # 初始化最后活跃时间
        self.last_active_time = time.time()
        # 初始化OpenQASM序列
        self.openqasm_content = None
        # 初始化聚合任务的子任务
        self.aggregation_tasks = []
        # 初始化聚合任务的比特映射关系
        self.aggregation_mappings = []
        # 初始化聚合任务对应的比特分区
        self.qubit_blocks = []
        # 初始化聚合任务所用到的量子比特数
        self.sum_qubit = 0
        # 初始化任务shots
        self.shots = None
        # 初始化是否是聚合任务
        self.is_aggregation = False
        # 初始化量子电路任务映射关系
        self.na_map = None
        # 初始化量子电路的测量结果
        self.task_result = {}
        # 初始化awg等设备
        self.awg = None
        self.niao = None
        self.nido = None
        self.camera = None

    async def execute(self):
        """
        执行量子电路任务

        返回:
        Any: 任务执行结果
        """
        self.last_active_time = time.time()
        if self.is_aggregation:
            qcos_logger.info(f"执行聚合量子电路任务: {self.task_id}")
            qcos_logger.debug("=====多任务聚合运行=====")
            qcos_logger.debug("聚合任务为:")
            qpu_config = qcos_configer.get_topo_file()
            aggregation_gates = []
            for task, block in zip(self.aggregation_tasks, self.qubit_blocks):
                qcos_logger.debug(f"子任务{task[0]}开始映射")
                qpu_config['operate_area'] = block
                qpu_config['storage_area'] = [qpu_config['closest'][o] for o in block]
                na = NASingleRoute(task[4], qpu_config)
                res_tmp = na.execute_with_order()
                qcos_logger.debug("初始映射为：")
                qcos_logger.debug(na.mapping)
                qcos_logger.debug("路由结果为：")
                for opt in res_tmp:
                    qcos_logger.debug(opt)
                aggregation_gates += res_tmp
                self.aggregation_mappings.append(na.mapping)
            qcos_logger.info(f"比特利用率为{self.sum_qubit / qpu_config['qubits'] * 100}%")
            if aggregation_gates:
                res = transpiler(aggregation_gates)
                res = optimizer(res)
                all_pulses, _ = gate_to_seq(res)
                qcos_logger.debug(f"聚合任务解析得到脉冲序列： {all_pulses}")
                return all_pulses
            else:
                raise Exception(f"任务 {self.task_id} 未提供量子门序列")
        else:
            qcos_logger.info(f"执行量子电路任务: {self.task_id}")
            if self.openqasm_content:
                # 解析 OpenQASM 内容
                parsed_circuit = self.parse_openqasm()
                # 将解析后的量子电路转换成对应的脉冲序列
                pulse = await self.convert_parsed_circuit_to_sequence(parsed_circuit)
                qcos_logger.debug(f"任务解析得到脉冲序列： {pulse}")
                return pulse
            else:
                raise Exception(f"任务 {self.task_id} 未提供OpenQASM指令")

    def set_openqasm_content(self, content: str, shots: int):
        """
        设置 OpenQASM 内容

        参数:
        content (str): OpenQASM 代码内容
        shots (int): 任务重复执行次数
        """
        if content:
            self.openqasm_content = content
            self.shots = shots
        else:
            raise ValueError("任务OpenQASM指令为空")

    def set_aggregation_task(self, aggregation_tasks: list, qubit_blocks: list, sum_qubit: int, shots: int):
        """
        设置聚合任务相关参数

        参数:
        aggregation_tasks (list): 聚合任务的子任务
        qubit_blocks (list): 聚合任务对应的比特分区
        sum_qubit (int): 聚合任务所用到的量子比特数
        shots (int): 任务重复执行次数
        """
        if aggregation_tasks and qubit_blocks:
            self.aggregation_tasks = aggregation_tasks
            self.qubit_blocks = qubit_blocks
            self.sum_qubit = sum_qubit
            self.shots = shots
            self.is_aggregation = True
        else:
            raise ValueError("聚合任务的相关参数有误")

    def parse_openqasm(self):
        """
        解析 OpenQASM 内容，同时针对中性原子路线进行比特映射

        返回:
        List[Tuple[str, str]]: 解析后的基础量子电路结构
        """
        # 中性原子路线处理方式
        if qcos_configer.get_topo_file() != {}:
            # 量子比特映射
            self.na_map = NASingleRoute(self.openqasm_content)
            mapping_res = self.na_map.execute_with_order()
            qcos_logger.debug("初始映射为:")
            qcos_logger.debug(self.na_map.mapping)
            qcos_logger.debug("映射后指令集:")
            for opt in mapping_res:
                qcos_logger.debug(opt)
            # 低阶编译，将指令转换为脉冲序列
            parsed_circuit = transpiler(mapping_res)
            opt_parsed_circuit = optimizer(parsed_circuit)
            return opt_parsed_circuit

        # 非中性原子处理方式
        node = get_abs_tree(self.openqasm_content)
        _, ir = get_ir(node)
        parsed_circuit = transpiler(ir)
        opt_parsed_circuit = optimizer(parsed_circuit)
        return opt_parsed_circuit

    async def convert_parsed_circuit_to_sequence(self, parsed_circuit):
        """
        将分析后的量子电路转化为脉冲序列

        参数:
        parsed_circuit: 解析后的基础量子电路

        返回:
        List[str]: 转化后的脉冲序列
        """
        #TODO: 后续完善基础门转序列的场景
        pulse, _ = gate_to_seq(parsed_circuit, qpu_file=qcos_configer.get_na_file())
        return pulse

    def measure_qubit_status(self, repeat: int):
        """
        量子比特状态读取

        参数：
        repeat (int): shots数

        返回：
        List[int]: 量子比特的状态
        """
        # 初始化相机，从校准图片中获得光子点位
        camera_detection = get_real_camera("<fake>", "./", qcos_configer.get_calib_img_path(), **{})
        # 根据测试图像，识别原子状态
        measure_results = []
        for _ in range(repeat):
            measure_results.append(
                camera_detection.get_status_with_threshold(100, 3, qcos_configer.get_quantum_task_res_img_path()))
        return measure_results

    def create_exp(self):
        """
        实例化硬件，主要为板卡，AWG，相机等

        返回：
        test_exp: 创建的实验类对象
        """
        self.awg = AWGInterface()
        qcos_logger.info("awg初始化完成")

        self.nido = NIDOInterface()
        self.nido.connect()
        qcos_logger.info("nido初始化完成")

        self.niao = NIAOInterface()
        self.niao.connect()
        qcos_logger.info("niao初始化完成")

        self.camera = CameraInterface()
        self.camera.connect()
        # 初始化相机参数
        self.camera.initialize()
        qcos_logger.info("相机初始化完成")

        GlobalSetting.set_rearrangement_dll(qcos_configer.get_rea_dll_path())
        rea = ReArrangement(qpu_file=qcos_configer.get_na_file())
        row_up, row_down, col_left, col_right = qcos_configer.get_rea_region()
        target = []
        for i in range(row_up, row_down):
            for j in range(col_left, col_right):
                target += [i, j]
        rea.target = target
        qcos_logger.info("重排算法加载完成")

        # 创建实验
        exp_chapter_dict = {
            'Raman': '11000000 00000000 00000000',
            'Detection': '01010000 00000000 00001111',
        }
        test_exp = Experiment(qcos_configer.get_qubit_number(), chapter_dict=exp_chapter_dict, repeat=self.shots,
                              awg=self.awg, nido=self.nido, niao=self.niao, camera=self.camera, rea=rea)
        qcos_logger.info("创建实验成功")
        # 设置亮度阈值，通过阈值来判断计算结果的比特状态，和相机中的阈值设置不同，相机中的阈值设置用于校准原子位置时查找量子比特
        test_exp.set_threshold(qcos_configer.get_measure_threshold(), qcos_configer.get_measure_threshold_block())
        qcos_logger.debug(f"比特状态判断亮态阈值设置为：{qcos_configer.get_measure_threshold()}")
        return test_exp

    def execute_task_on_quantum(self, sequence):
        """
        任务数据下发与执行

        参数：
        sequence: 实验序列

        返回：
        Tuple (list, list): 测量结果，重排结果
        """
        # 实例化硬件，主要为板卡，AWG，相机等
        exp = self.create_exp()
        # 添加序列
        assert sequence is not None
        exp_seq = exp.new_sequence()
        qcos_logger.info(f"sequence: {sequence}")
        exp_seq.set_sequence(
            awg_trigger(),
            sequence,
        )
        qcos_logger.info("序列添加成功")

        # 实验运行，获取比特的测量结果
        if GlobalSetting.get_instrument_type() == InstrumentType.INSTRUMENT_HW_FPGA_AWG:
            with open(qcos_configer.get_na_file(), 'r') as f:
                na_config = json.loads(f.read())
            c1_time = na_config["raman"].get('c1_time', 1200e-6) * 1e6
            # 生成门的awg信号
            awg_ch1_data, awg_ch2_data, awg_format = exp.last_sequence.get_atom_awg_data()
            awg_ch3_data, awg_ch4_data = exp.awg_interface.generator.generateFullWave(c1_time, awg_format)
            raman_channel_list = qcos_configer.get_raman_channel()
            exp.awg_interface.sendSingleChannel(awg_ch3_data, channelID=raman_channel_list[2],
                                                trigger='externalcycle', cycles=exp.repeat)
            exp.awg_interface.sendSingleChannel(awg_ch4_data, channelID=raman_channel_list[3],
                                                trigger='externalcycle', cycles=exp.repeat)
            if exp.camera_switch:
                exp.camera.execute_operation()
            else:
                qcos_logger.error("相机未实例化")
                raise ValueError("相机未实例化")

            rea_result = []
            task_result = []
            if None not in (exp.nido, exp.niao):
                # 先上传do, ao信号
                exp.nido.send_data()
                exp.niao.send_data()
                rea_channel_list = qcos_configer.get_rea_channel()
                rea_amp = qcos_configer.get_rea_amp()
                # 执行repeat次
                for i in range(exp.repeat):
                    # 控制信号任务启动
                    exp.niao.execute_operation()
                    exp.nido.execute_operation()
                    # 获取原子捕获照片
                    exp.camera.capture_image(img_name=f"./image{i}_1")
                    # 进行原子重排
                    rea_atom_status_list = exp.camera.get_status_with_threshold(exp.threshold, exp.threshold_block)
                    # 重排波形
                    x_data, y_data = exp.rea.transport(rea_atom_status_list)
                    # awg重排波形发送
                    exp.awg_interface.setArrangeWave([x_data, y_data], channelList=rea_channel_list, amp=rea_amp)
                    exp.awg_interface.startMultipChannel(channelList=rea_channel_list)
                    # 获取原子重排后照片
                    exp.camera.capture_image(img_name=f"./image{i}_2")
                    # 根据阈值获取重排结果
                    rea_result.append(exp.camera.get_status_with_threshold(exp.threshold, exp.threshold_block))
                    # awg拉曼波形发送
                    exp.awg_interface.setRamanWave([awg_ch1_data, awg_ch2_data], channelList=raman_channel_list[:2])
                    exp.awg_interface.startMultipChannel(channelList=raman_channel_list[:2])
                    # 最后获取结果
                    exp.camera.capture_image(img_name=f"./image{i}_3")
                    task_result.append(exp.camera.get_status_with_threshold(exp.threshold, exp.threshold_block))

                    # 控制信号任务结束
                    exp.niao.stop_operation()
                    exp.nido.stop_operation()
                    time.sleep(exp.load_time)
            else:
                qcos_logger.error("NI未实例化")
                raise ValueError("NI未实例化")

            if exp.camera_switch:
                exp.camera.stop_operation()
            return task_result, rea_result

        # 如果处于debug模式下，则是直接生成相应长度的随机序列，存入result中
        else:
            qcos_logger.debug("debug model, result is random data!")
            task_result = [[random.choice([0, 1]) for _ in range(exp.qubit_number)] for _ in range(exp.repeat)]
            rea_result = [[random.choice([0, 1]) for _ in range(exp.qubit_number)] for _ in range(exp.repeat)]
            time.sleep(0.005)
        return task_result, rea_result
