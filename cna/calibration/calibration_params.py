#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd.
# All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-10
# ------------------------
import asyncio
import json
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from qcos.\
    cna.core.rearrange.generate_wave import \
    generate_raman_wave, generate_rea_wave
from qcos.log.qcos_log import QCOSLogger
from qcos.config.qcos_config_manager import \
    qcos_configer
from qcos.\
    cna.core.rearrange.rearrangement import \
    ReArrangement
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.awg_interface import \
    AWGInterface, GenerateDynamicC3C4
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.camera_interface import \
    CameraInterface
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.ni_chassis_interface import \
    NIDOInterface, NIAOInterface

qcos_logger = QCOSLogger()


class CalibrationParams(object):
    '''
    校准
    '''

    def __init__(self):
        '''
        初始化参数标定类
        '''

        self.awg = None
        self.camera = None
        self.niao = None
        self.nido = None
        self.allow_run = False

    def hardware_instantiation(self):
        '''
        实例化硬件环境
        '''

        self.awg = AWGInterface()
        qcos_logger.info('awg初始化完成')

        self.nido = NIDOInterface()
        self.nido.connect()
        qcos_logger.info('nido初始化完成')

        self.niao = NIAOInterface()
        self.niao.connect()
        qcos_logger.info('niao初始化完成')

        self.camera = CameraInterface()
        self.camera.connect()
        # 初始化相机参数
        self.camera.initialize()
        qcos_logger.info('相机初始化完成')

    def scan_parameter(
            self,
            scan_option: str,
            atom_row: int,
            atom_col: int,
            init_val: float,
            step: float,
            step_num: int,
            **kwargs):
        '''
        参数扫描
        参数:
            scan_option (str): 选择待测参数
            atom_row (int): 待测原子行号，从0开始
            atom_col (int): 待测原子列号，从0开始
            init_val (float): 扫描起始值
            step (int): 扫描步长
            step_num (int): 扫描次数
        返回:
            Tuple(float, float): 重排成功率, 原子翻转成功率
        '''

        if qcos_configer.get_debug_mode() == 0:
            try:
                self.hardware_instantiation()
            except Exception as err:
                raise ConnectionError(f'硬件设备出错：{err}')
        else:
            raise RuntimeError('当前是调试模式，无法进行参数标定')

        # 重排区域
        row_up = kwargs.get('row_up', atom_row)
        row_down = kwargs.get('row_down', atom_row + 1)
        col_left = kwargs.get('col_left', atom_col)
        col_right = kwargs.get('col_right', atom_col + 1)
        atom_target = []
        for i in range(row_up, row_down):
            for j in range(col_left, col_right):
                atom_target += [i, j]
        atom_num = (row_down - row_up) * (col_right - col_left)
        if atom_num <= 0:
            raise ValueError('原子重排区域无效')

        # 校准扫描参数
        shots = kwargs.get('shots', 100)
        qpu_file = qcos_configer.get_na_file()
        with open(qpu_file, 'r') as f:
            config = json.loads(f.read())
            # 拉曼参数
            raman_config = config['raman']
            c1_time = kwargs.get('c1_time', raman_config['c1_time'])
            c3_start_time = kwargs.get(
                'c3_start_time', raman_config['c3_start_time'])
            c3_time = kwargs.get('c3_time', raman_config['c3_time'])
            # 重排参数
            move_config = config['movement']
            arrange_amp = kwargs.get('arrange_amp', move_config['arrange_amp'])
        # 设置重排区域
        rea = ReArrangement(qpu_file=qpu_file)
        rea.set_target(atom_target)

        # 准备拉曼波形及触发时序
        ch1 = [f'raman_x_{atom_row}']
        ch2 = [f'raman_y_{atom_col}']
        waves = [ch1, ch2]
        wave_gen = GenerateDynamicC3C4().wave_generator
        seg_list = [(0, c3_start_time), (1, c3_time),
                    (0, c1_time - c3_start_time - c3_time)]
        ch3 = wave_gen.constant_array(seg_list=seg_list)

        # 原子测量参数
        measure_threshold = qcos_configer.get_measure_threshold()
        measure_threshold_block = qcos_configer.get_measure_threshold_block()

        scan_value = init_val
        scan_rea_res = []
        scan_raman_res = []
        qcos_logger.info(f'开始参数扫描{scan_option}')
        log_name = kwargs.get('log_name', None)
        log_file = None
        if log_name:
            log_file = open(str(log_name), 'w')
        self.allow_run = True
        self.camera.start_acquisition()
        for k in range(step_num):
            qcos_logger.info(f'第{k}轮扫描')
            # 拉曼参数
            if scan_option == 'rabi':
                c3_time = scan_value
                seg_list = [(0, c3_start_time), (1, c3_time),
                            (0, c1_time - c3_start_time - c3_time)]
                ch3 = wave_gen.constant_array(seg_list=seg_list)
            elif scan_option == 'raman_ch1':
                generate_raman_wave(qpu_file, init_freq_x=scan_value)
                self.awg.load_queue_wave2_awg()
            elif scan_option == 'raman_ch2':
                generate_raman_wave(qpu_file, init_freq_y=scan_value)
                self.awg.load_queue_wave2_awg()
            # 重排参数
            elif scan_option == 'arrange_ch1':
                generate_rea_wave(qpu_file, init_freq_x=scan_value)
                self.awg.load_queue_wave2_awg()
            elif scan_option == 'arrange_ch2':
                generate_rea_wave(qpu_file, init_freq_y=scan_value)
                self.awg.load_queue_wave2_awg()

            # 发送CH3及NI数据
            self.awg.sendSingleChannel(
                wave=ch3,
                channelID=3,
                trigger='externalCycle',
                cycles=shots)
            self.nido.send_data()
            self.niao.send_data()

            # base_num表示翻转前原子存在的case次数
            # flip_num表示翻转前原子存在并且原子成功翻转的case次数
            sum_case = {'base_num': 0, 'flip_num': 0}
            rea_qubit_num = 0
            for i in range(shots):
                if not self.allow_run:
                    return scan_rea_res, scan_raman_res
                self.niao.execute_operation()
                self.nido.execute_operation()
                # 获取第一张图
                self.camera.capture_image(img_name=f'./test{i}_1')
                # 进行原子重排
                atom = self.camera.get_status_with_threshold(
                    measure_threshold, measure_threshold_block)
                x_data, y_data = rea.transport(atom)
                self.awg.setArrangeWave([x_data, y_data], channelList=[
                                        1, 2], amp=arrange_amp)
                self.awg.startMultipChannel(channelList=[1, 2])
                # 获取第二张图
                self.camera.capture_image(img_name=f'./test{i}_2')
                occupation = self.camera.get_status_with_threshold(
                    measure_threshold, measure_threshold_block)
                # 开始raman操控
                self.awg.setRamanWave(waves=waves, channelList=[1, 2])
                self.awg.startMultipChannel(channelList=[1, 2])
                # 获取第三张图
                self.camera.capture_image(img_name=f'./test{i}_3')
                self.niao.stop_operation()
                self.nido.stop_operation()
                # 统计重排成功的原子数
                for r in range(row_up, row_down):
                    for c in range(col_left, col_right):
                        if occupation[r *
                                      qcos_configer.get_col_num() + c] == 1:
                            rea_qubit_num += 1
                # 统计原子有效翻转结果
                if occupation[atom_row *
                              qcos_configer.get_col_num() + atom_col]:
                    sum_case['base_num'] += 1
                    occupation3rd = self.camera.get_status_with_threshold(
                        measure_threshold, measure_threshold_block)
                    if not occupation3rd[atom_row *
                                         qcos_configer.get_col_num()
                                         + atom_col]:
                        sum_case['flip_num'] += 1
                time.sleep(1)

            rea_qubit_res = rea_qubit_num / shots
            raman_qubit_res = 0 if sum_case['base_num'] == 0 else (
                sum_case['flip_num'] * 1.0 / sum_case['base_num'])
            scan_rea_res.append(rea_qubit_res)
            scan_raman_res.append(raman_qubit_res)
            qcos_logger.info(
                f'{scan_value=}, {rea_qubit_res=}, '
                f'{raman_qubit_res=}', file=log_file, flush=True)
            scan_value += step

        qcos_logger.info('参数扫描结束')
        self.camera.stop_operation()
        return scan_rea_res, scan_raman_res

    def scan_raman_rabi(
            self,
            atom_row: int,
            atom_col: int,
            init_val: float,
            step: float,
            step_num: int,
            **kwargs):
        '''
        Raman 单比特寻址 Rabi振荡扫描
        参数:
            atom_row (int): 待测原子行号（从0开始）
            atom_col (int): 待测原子列号（从0开始）
            init_val (float): 扫描起始数据值
            step (float): 扫描数据步长
            step_num (int): 扫描次数
        返回:
            Tuple(float, float): 重排成功率, 原子翻转成功率
        '''
        return self.scan_parameter(
            'rabi',
            atom_row,
            atom_col,
            init_val,
            step,
            step_num,
            **kwargs)

    def scan_raman_ch1(
            self,
            atom_row: int,
            atom_col: int,
            init_val: float,
            step: float,
            step_num: int,
            **kwargs):
        '''
        Raman 单比特对准阱扫描CH1通道
        参数:
            atom_row (int): 待测原子行号（从0开始）
            atom_col (int): 待测原子列号（从0开始）
            init_val (float): 扫描起始值
            step (float): 扫描步长
            step_num (int): 扫描次数
        返回:
            Tuple(float, float): 重排成功率, 原子翻转成功率
        '''
        return self.scan_parameter(
            'raman_ch1',
            atom_row,
            atom_col,
            init_val,
            step,
            step_num,
            **kwargs)

    def scan_raman_ch2(
            self,
            atom_row: int,
            atom_col: int,
            init_val: float,
            step: float,
            step_num: int,
            **kwargs):
        '''
        Raman 单比特对准阱扫描CH2通道
        参数:
            atom_row (int): 待测原子行号（从0开始）
            atom_col (int): 待测原子列号（从0开始）
            init_val (float): 扫描起始值
            step (float): 扫描步长
            step_num (int): 扫描次数
        返回:
            Tuple(float, float): 重排成功率, 原子翻转成功率
        '''
        return self.scan_parameter(
            'raman_ch2',
            atom_row,
            atom_col,
            init_val,
            step,
            step_num,
            **kwargs)

    def scan_arrange_ch1(
            self,
            row_up: int,
            row_down: int,
            col_left: int,
            col_right: int,
            init_val: float,
            step: float,
            step_num: int,
            **kwargs):
        '''
        重排CH1频率扫描
        参数:
            row_up (int): 重排区域上沿行号（从0开始）
            row_down (int): 重排区域下沿行号（从0开始）
            col_left (int): 重排区域左侧列号（从0开始）
            col_right (int): 重排区域右侧列号（从0开始）
            init_val (float): 扫描起始值
            step (float): 扫描步长
            step_num (int): 扫描次数
        返回:
            Tuple(float, float): 重排成功率, 原子翻转成功率
        '''
        return self.scan_parameter(
            'arrange_ch1',
            1,
            1,
            init_val,
            step,
            step_num,
            row_up=row_up,
            row_down=row_down,
            col_left=col_left,
            col_right=col_right,
            **kwargs)

    def scan_arrange_ch2(
            self,
            row_up: int,
            row_down: int,
            col_left: int,
            col_right: int,
            init_val: float,
            step: float,
            step_num: int,
            **kwargs):
        '''
        重排CH2频率扫描
        参数:
            row_up (int): 重排区域上沿行号（从0开始）
            row_down (int): 重排区域下沿行号（从0开始）
            col_left (int): 重排区域左侧列号（从0开始）
            col_right (int): 重排区域右侧列号（从0开始）
            init_val (float): 扫描起始值
            step (float): 扫描步长
            step_num (int): 扫描次数
        返回:
            Tuple(float, float): 重排成功率, 原子翻转成功率
        '''
        return self.scan_parameter(
            'arrange_ch2',
            1,
            1,
            init_val,
            step,
            step_num,
            row_up=row_up,
            row_down=row_down,
            col_left=col_left,
            col_right=col_right,
            **kwargs)


class CalibrationParamsInteraction(object):
    '''
    校准参数交互
    '''

    def __init__(self):
        '''
        初始化标定交互请求处理类
        '''
        self.calibration_app = Flask(__name__)
        self.calibration = CalibrationParams()
        self.message = None
        self.current_type = None
        self.current_file = None
        self.step_num = None
        CORS(self.calibration_app)

    def deal_request(self):
        @self.calibration_app.route('/v1/auto_calibration',
                                    methods=['POST'])
        def fetch_params():
            '''
            根据 POST 请求获取校准参数
            返回:
                json: 请求的响应
            '''

            self.message = None
            self.current_file = None
            self.current_type = None
            self.step_num = None
            request_data = {}
            if not request.is_json:
                self.message = '错误请求格式'
            else:
                request_data = request.get_json(force=True)
                if (request_data is None or 'data' not in request_data
                        or 'parameters' not in request_data['data']):
                    self.message = '传入的数据有误'
            if not self.message:
                data = request_data['data']
                scan_type = data.get('type', None)
                params_data = data['parameters']
                atom_row = params_data.get('atom_row', None)
                atom_col = params_data.get('atom_col', None)
                init_val = params_data.get('init_val', None)
                step = params_data.get('step', None)
                step_num = params_data.get('step_num', None)
                row_up = params_data.get('row_up', None)
                row_down = params_data.get('row_down', None)
                col_left = params_data.get('col_left', None)
                col_right = params_data.get('col_right', None)
                shots = params_data.get('shots', 100)

                # 异步执行参数扫描
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_in_executor(
                    None,
                    lambda: loop.run_until_complete(
                        self.execute_calibration(
                            scan_type,
                            atom_row,
                            atom_col,
                            init_val,
                            step,
                            step_num,
                            row_up,
                            row_down,
                            col_left,
                            col_right,
                            shots)))
            if self.message:
                response_data = {
                    'code': 1
                }
            else:
                response_data = {
                    'code': 0,
                }
            return jsonify(response_data)

        @self.calibration_app.route('/v1/auto_calibration',
                                    methods=['GET'])
        def feedback_result():
            '''
            根据 GET 请求反馈校准结果
            返回:
                json: 请求的响应
            '''

            scan_type = request.args.get('type')
            # case1: 当前没有校准任务
            if scan_type != self.current_type:
                response_data = {
                    'code': 0,
                    'data': {
                        'status': 'ready'
                    }
                }
                return jsonify(response_data)
            # case2: 校准任务出错
            data_list = self.deal_data()
            if self.message:
                response_data = {
                    'code': 1,
                    'data': {
                        'status': 'fail',
                        'res': data_list,
                        'message': self.message
                    }
                }
            else:
                # case3: 校准任务进行中
                if len(data_list) < self.step_num:
                    response_data = {
                        'code': 0,
                        'data': {
                            'status': 'running',
                            'res': data_list
                        }
                    }
                else:
                    # case4: 校准任务完成
                    response_data = {
                        'code': 0,
                        'data': {
                            'status': 'complete',
                            'res': data_list
                        }
                    }
            return jsonify(response_data)

        @self.calibration_app.route('/v1/auto_calibration/abort',
                                    methods=['POST'])
        def abort_calibration():
            '''
            根据 GET 请求中断参数校准
            返回:
                请求的响应
            '''

            self.calibration.allow_run = False
            return {'code': 0}

        @self.calibration_app.route('/v1/auto_calibration/submit',
                                    methods=['POST'])
        def update_params():
            '''
            根据 POST 请求获取并更新参数
            返回:
                请求的响应
            '''

            self.message = None
            request_data = {}
            if not request.is_json:
                self.message = '错误请求格式'
            else:
                request_data = request.get_json(force=True)
                if (request_data is None or 'type' not in request_data
                        or 'data' not in request_data):
                    self.message = '传入的数据有误'
            if not self.message:
                params_key = request_data['type']
                params_value = request_data['data']
                qpu_file = qcos_configer.get_na_file()
                with open(qpu_file, 'r') as f:
                    config = json.loads(f.read())
                if params_key == 'rabi' and params_value:
                    config['raman']['c3_time'] = params_value
                elif params_key == 'raman_ch1' and params_value:
                    config['raman']['init_freq_x'] = params_value
                    generate_raman_wave(qpu_file, init_freq_x=params_value)
                    awg_interface = AWGInterface()
                    awg_interface.load_queue_wave2_awg()
                elif params_key == 'raman_ch2' and params_value:
                    config['raman']['init_freq_y'] = params_value
                    generate_raman_wave(qpu_file, init_freq_y=params_value)
                    awg_interface = AWGInterface()
                    awg_interface.load_queue_wave2_awg()
                elif params_key == 'arrange_ch1' and params_value:
                    config['movement']['init_freq_x'] = params_value
                    generate_rea_wave(qpu_file, init_freq_x=params_value)
                    awg_interface = AWGInterface()
                    awg_interface.load_queue_wave2_awg()
                elif params_key == 'arrange_ch2' and params_value:
                    config['movement']['init_freq_y'] = params_value
                    generate_rea_wave(qpu_file, init_freq_y=params_value)
                    awg_interface = AWGInterface()
                    awg_interface.load_queue_wave2_awg()
                else:
                    self.message = '传入参数有误'
                # 更新配置文件
                with open(qpu_file, 'w') as f:
                    json.dump(config, f, indent=4)
            if self.message:
                response_data = {
                    'code': 1
                }
            else:
                response_data = {
                    'code': 0,
                }
            return jsonify(response_data)

        @self.calibration_app.route(
            '/v1/auto_calibration/current_value',
            methods=['GET'])
        def feedback_current_value():
            '''
            根据 GET 请求反馈当前参数
            返回:
                请求的响应
            '''

            scan_type = request.args.get('type')
            current_value = None
            qpu_file = qcos_configer.get_na_file()
            with open(qpu_file, 'r') as f:
                config = json.loads(f.read())
            if scan_type == 'rabi':
                current_value = config['raman']['c3_time']
            elif scan_type == 'raman_ch1':
                current_value = config['raman']['init_freq_x']
            elif scan_type == 'raman_ch2':
                current_value = config['raman']['init_freq_y']
            elif scan_type == 'arrange_ch1':
                current_value = config['movement']['init_freq_x']
            elif scan_type == 'arrange_ch2':
                current_value = config['movement']['init_freq_y']
            if current_value:
                response_data = {
                    'code': 0,
                    'data': current_value
                }
            else:
                response_data = {
                    'code': 1
                }
            return jsonify(response_data)

    async def execute_calibration(
            self,
            scan_type: str,
            atom_row: int,
            atom_col: int,
            init_val: float,
            step: float,
            step_num: int,
            row_up: int,
            row_down: int,
            col_left: int,
            col_right: int,
            shots: int):
        '''
        异步执行参数校准
        参数:
            scan_type (str): 扫描参数类型
            atom_row (int): 待测原子行号（从0开始）
            atom_col (int): 待测原子列号（从0开始）
            init_val (float): 扫描起始值
            step (float): 扫描步长
            step_num (int): 扫描次数
            row_up (int): 重排区域上沿行号（从0开始）
            row_down (int): 重排区域下沿行号（从0开始）
            col_left (int): 重排区域左侧列号（从0开始）
            col_right (int): 重排区域右侧列号（从0开始）
            shots (int): 扫描采样次数
        '''

        try:
            self.current_type = scan_type
            self.step_num = step_num
            self.current_file = f'{scan_type}_{time.time()}.log'
            if scan_type == 'rabi' and None not in [
                    atom_row, atom_col, init_val, step, step_num]:
                self.calibration.scan_raman_rabi(
                    atom_row,
                    atom_col,
                    init_val,
                    step,
                    step_num,
                    shots=shots,
                    log_name=self.current_file)

            elif scan_type == 'raman_ch1' and None not in [atom_row, atom_col,
                                                           init_val, step,
                                                           step_num]:
                self.calibration.scan_raman_ch1(
                    atom_row,
                    atom_col,
                    init_val,
                    step,
                    step_num,
                    shots=shots,
                    log_name=self.current_file)

            elif scan_type == 'raman_ch2' and None not in [atom_row, atom_col,
                                                           init_val, step,
                                                           step_num]:
                self.calibration.scan_raman_ch2(
                    atom_row,
                    atom_col,
                    init_val,
                    step,
                    step_num,
                    shots=shots,
                    log_name=self.current_file)

            elif scan_type == 'arrange_ch1' and None not in [atom_row, atom_col,
                                                             init_val, step,
                                                             step_num]:
                self.calibration.scan_arrange_ch1(
                    row_up,
                    row_down,
                    col_left,
                    col_right,
                    init_val,
                    step,
                    step_num,
                    shots=shots,
                    log_name=self.current_file)

            elif scan_type == 'arrange_ch2' and None not in [atom_row, atom_col,
                                                             init_val, step,
                                                             step_num]:
                self.calibration.scan_arrange_ch2(
                    row_up,
                    row_down,
                    col_left,
                    col_right,
                    init_val,
                    step,
                    step_num,
                    shots=shots,
                    log_name=self.current_file)
            else:
                raise TypeError('传入参数有误')
        except Exception as err:
            self.message = f'参数校准时出现错误：{err}'

    def deal_data(self):
        '''
        从校准记录文件中解析结果
        返回:
            list[dict]: 解析的扫描结果
        '''

        data_list = []
        if not self.current_file:
            return data_list
        with open(self.current_file, 'r') as file:
            for line in file:
                parts = line.strip().split(', ')
                res_dict = {}
                for part in parts:
                    key_value = part.split('=')
                    key = key_value[0].strip()
                    value = key_value[1].strip()
                    try:
                        value = int(value) if value.isdigit() else float(
                            value) if value.\
                            replace('.', '', 1).isdigit() else value
                    except (ValueError, TypeError):
                        pass
                    res_dict[key] = value
                data_list.append(res_dict)
        return data_list


if __name__ == '__main__':
    calibration = CalibrationParamsInteraction()
    calibration.deal_request()
    calibration.calibration_app.run(debug=True)
