import json
from ..rearrange import * 
from ..instrument.awg import GenerateDynamicC3C4
import time
from ..config import *

def count_qubit_num(res, a, b, c, d):
    cnt = 0
    for i in range(a, b):
        for j in range(c, d):
            if res[i*20+j] == 1: cnt += 1
    return cnt

def scan_parameter(awg, nido, niao, camera_ins, scan_option: str, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, **kwargs):
    """
    参数扫描

    Args:
        scan_option: 选择待测参数
        atomRow: 待测原子行数，从1开始
        atomColumn: 待测原子列数，从1开始
        init_val: 扫描起始值
        step: 扫描步长
        nstep: 扫描次数

    Returns:
        res: 每个测试数据点位得到的平均重排后量子数和比特翻转率
    """
    
    debug_mod = False
    if GlobalSetting.get_instrument_type() == InstrumentType.INSTRUMENT_NONE:
        debug_mod = True

    # 换成从0开始计数
    atomRow -= 1
    atomColumn -= 1

    # 重排区域
    up = kwargs.get('up', atomRow)
    down = kwargs.get('down', atomRow + 1)
    left = kwargs.get('left', atomColumn)
    right = kwargs.get('right', atomColumn + 1)
    target = []
    for i in range(up, down):
        for j in range(left, right):
            target += [i, j]
    atom_num = (down - up) * (right - left)
    assert(atom_num > 0)

    # 可配置参数
    niter_per_scan = kwargs.get('niter_per_scan', 100)
    t1 = kwargs.get('t1', 0) * 1e-6

    qpu_file = kwargs.get('qpu_file', './na_file.json')
    with open(qpu_file, 'r') as f:
        config = json.loads(f.read())
        raman_config = config['raman']
        c1_time = kwargs.get('c1_time', raman_config['c1_time'])
        c3_start_time = kwargs.get('c3_start_time', raman_config['c3_start_time'])
        c3_time = kwargs.get('c3_time', raman_config['c3_time'])

        move_config = config['movement']
        arrange_amp = kwargs.get('arrange_amp', move_config['arrange_amp'])
        
    if not debug_mod:
        rea = ReArrangement(qpu_file=qpu_file)
        rea.set_target(target)

    ch1 = [f'raman_x_{atomRow}']
    ch2 = [f'raman_y_{atomColumn}']
    waves = [ch1, ch2]
    wave_gen = GenerateDynamicC3C4().wg
    segList = [(0, c3_start_time), (1, c3_time), (0, c1_time - c3_start_time - c3_time)]
    c3 = wave_gen.constantArray(segList=segList)

    scan_value = init_val
    res = []
    
    print("开始扫描")
    camera_ins.camera.start_acquisition()
    for k in range(nstep):
        print(f"{scan_option}第{k}轮")

        # Raman parameters
        if scan_option == "rabi":
            c3_time = scan_value
            segList = [(0, c3_start_time), (1, c3_time), (0, c1_time - c3_start_time - c3_time)]
            c3 = wave_gen.constantArray(segList=segList)
        elif scan_option == "ramsey":
            segList = [(0, c3_start_time), (1, t1), (0, scan_value), (1, t1),
                    (0, c1_time - c3_start_time - scan_value - 2 * t1)]
            c3 = wave_gen.constantArray(segList=segList)
        elif scan_option == "spin_echo":
            segList = [(0, c3_start_time), (1, t1), (0, scan_value), (1, 2 * t1), (0, scan_value), (1, t1),
                    (0, c1_time - c3_start_time - 2 * scan_value - 4 * t1)]
            c3 = wave_gen.constantArray(segList=segList)
        elif scan_option == "cpmg":
            segList = [(0, c3_start_time), (1, t1), (0, scan_value), (1, 2 * t1), (0, scan_value), (1, 2 * t1), (0, scan_value), (1, t1),
                    (0, c1_time - c3_start_time - 3 * scan_value - 6 * t1)]
            c3 = wave_gen.constantArray(segList=segList)
            # plot(c3)
            # show()
        elif scan_option == "raman_ch1":
            if not debug_mod:
                generate_raman_wave(qpu_file, init_freq_x=scan_value)
                awg.loadQueueWave2AWG()
        elif scan_option == "raman_ch2":
            if not debug_mod:
                generate_raman_wave(qpu_file, init_freq_y=scan_value)
                awg.loadQueueWave2AWG()

        # Arrangement parameters
        elif scan_option == "arrange_amp":
            arrange_amp = scan_value
        elif scan_option == "arrange_ch1":
            if not debug_mod:
                generate_rea_wave(qpu_file, init_freq_x=scan_value)
                awg.loadQueueWave2AWG()
        elif scan_option == "arrange_ch2":
            if not debug_mod:
                generate_rea_wave(qpu_file, init_freq_y=scan_value)
                awg.loadQueueWave2AWG()

        # DO parameters
        elif scan_option == "do0_pgc_cooling_time":
            niao.do0_pgc_cooling_time = scan_value
        elif scan_option == "do0_meas_cooling_time":
            niao.do0_meas_cooling_time = scan_value
        elif scan_option == "do2_pgc_pump_time":
            niao.do2_pgc_pump_time = scan_value
        elif scan_option == "do2_meas_pump_time":
            niao.do2_meas_pump_time = scan_value

        # AO parameters
        elif scan_option == "ao1_pgc_cooling_detune":
            niao.ao1_pgc_cooling_detune = scan_value
        elif scan_option == "ao1_meas_cooling_detune":
            niao.ao1_meas_cooling_detune = scan_value
        elif scan_option == "ao1_meas_cooling_freq":
            niao.ao1_meas_cooling_freq = scan_value
        elif scan_option == "ao3_pgc_pump_detune":
            niao.ao3_pgc_pump_detune = scan_value
        elif scan_option == "ao3_meas_pump_detune":
            niao.ao3_meas_pump_detune = scan_value
        elif scan_option == "ao4_pgc_comp_mag":
            niao.ao4_pgc_comp_mag = scan_value
        elif scan_option == "ao5_pgc_comp_mag":
            niao.ao5_pgc_comp_mag = scan_value
        elif scan_option == "ao6_pgc_comp_mag":
            niao.ao6_pgc_comp_mag = scan_value
        elif scan_option == "ao7_raman_source_freq":
            niao.ao7_raman_source_freq = scan_value
        elif scan_option == "ao8_pgc_pump_amp":
            niao.ao8_pgc_pump_amp = scan_value
        elif scan_option == "ao8_meas_pump_amp":
            niao.ao8_meas_pump_amp = scan_value
        elif scan_option == "ao9_pgc_cooling_amp":
            niao.ao9_pgc_cooling_amp = scan_value

        awg.sendSingleChannel(wave=c3,channelID=3,trigger='externalCycle',cycles=niter_per_scan)
        print("c3数据发送成功")
        if debug_mod:
            do_signal = [[(0, 0), (0.5, 1), (1, 1)] for _ in range(len(nido.connection.dev))]
            nido.send(do_signal)
            ao_signale = [[(0, 1), (1, 10)] for _ in range(len(niao.connection.dev))]
            niao.send(ao_signale)
        else:
            nido.send([])
            niao.send([])
        print("ni数据发送成功")
        sumCase = {'t':0, 's':0}
        qubit_num = 0
        for i in range(niter_per_scan):
            print(f"{i}")
            niao.start()
            nido.start()
            # 获取第一张图
            camera_ins.capture_image()
            # 进行原子重排
            atom = camera_ins.get_status_with_threshold(80, 2)
            x_data, y_data = [''], ['']
            if not debug_mod:
                x_data, y_data = rea.transport(atom)
            awg.setArrangeWave([x_data, y_data], channelList = [1, 2], amp=arrange_amp)
            awg.startMultipChannel(channelList = [1, 2])

            # 获取第二张图
            camera_ins.capture_image()
            threshold = 100
            occupation = camera_ins.get_status_with_threshold(threshold, 2)

            '''--------------------<<< 开始raman操控 <<<<<<<<<<<<<<<<<<'''
            """ 测试Raman 操控 # raman opt给awg数据,操作raman激光的时间 """

            awg.setRamanWave(waves=waves,channelList=[1,2])
            awg.startMultipChannel(channelList=[1,2])

            '''-------------------->>> 结束raman操控 >>>>>>>>>>>>>>>>>'''
            # 获取第三张图
            camera_ins.capture_image()
            niao.stop()
            nido.stop()

            qubit_num += count_qubit_num(occupation, up, down, left, right)

            if occupation[atomRow * 20 + atomColumn]:
                sumCase['t'] += 1 
                occupation3rd = camera_ins.get_status_with_threshold(threshold, 3)
                if not occupation3rd[atomRow * 20 + atomColumn]:
                    sumCase['s'] += 1 
            
            if not debug_mod:
                time.sleep(1)
        
        qubit_num_average = qubit_num / niter_per_scan
        eta = 0 if sumCase['t'] == 0 else sumCase['s'] * 1.0 / sumCase['t']
        res.append((qubit_num_average, eta))
        scan_value += step
    print("扫描结束")
    camera_ins.camera.abort_acquisition()
    return res

def scan_raman_rabi(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, **kwargs):
    """Raman 单比特寻址 Rabi振荡扫描"""
    return scan_parameter(awg, nido, niao, camera_ins, "rabi", atomRow, atomColumn, init_val, step, nstep, **kwargs)

def scan_raman_ramsey(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, t1: float, **kwargs):
    """Raman 单比特寻址 Rabi振荡扫描"""
    return scan_parameter(awg, nido, niao, camera_ins, "ramsey", atomRow, atomColumn, init_val, step, nstep, t1=t1, **kwargs)

def scan_raman_spin_echo(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, t1: float, **kwargs):
    """Raman 单比特寻址 spin-echo扫描"""
    return scan_parameter(awg, nido, niao, camera_ins, "spin_echo", atomRow, atomColumn, init_val, step, nstep, t1=t1, **kwargs)

def scan_raman_cpmg(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, t1: float, **kwargs):
    """Raman 单比特寻址 CPMG扫描"""
    return scan_parameter(awg, nido, niao, camera_ins, "cpmg", atomRow, atomColumn, init_val, step, nstep, t1=t1, **kwargs)

def scan_raman_ch1(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, **kwargs):
    """Raman 单比特对准阱扫描CH1通道"""
    return scan_parameter(awg, nido, niao, camera_ins, "raman_ch1", atomRow, atomColumn, init_val, step, nstep, **kwargs)

def scan_raman_ch2(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, **kwargs):
    """Raman 单比特对准阱扫描CH2通道"""
    return scan_parameter(awg, nido, niao, camera_ins, "raman_ch2", atomRow, atomColumn, init_val, step, nstep, **kwargs)

def scan_arrange_amp(awg, nido, niao, camera_ins, up: int, down: int, left: int, right: int, init_val: float, step: float, nstep: int, **kwargs):
    """重排幅度扫描

    输入重排区域的行号和列号（从0开始计数）
    """
    return scan_parameter(awg, nido, niao, camera_ins, "arrange_amp", 1, 1, init_val, step, nstep, up=up, down=down, left=left, right=right, **kwargs)

def scan_arrange_ch1(awg, nido, niao, camera_ins, up: int, down: int, left: int, right: int, init_val: float, step: float, nstep: int, **kwargs):
    """重排Ch1频率扫描

    输入重排区域的行号和列号（从0开始计数）
    """
    return scan_parameter(awg, nido, niao, camera_ins, "arrange_ch1", 1, 1, init_val, step, nstep, up=up, down=down, left=left, right=right, **kwargs)

def scan_arrange_ch2(awg, nido, niao, camera_ins, up: int, down: int, left: int, right: int, init_val: float, step: float, nstep: int, **kwargs):
    """重排Ch2频率扫描

    输入重排区域的行号和列号（从0开始计数）
    """
    return scan_parameter(awg, nido, niao, camera_ins, "arrange_ch2", 1, 1, init_val, step, nstep, up=up, down=down, left=left, right=right, **kwargs)

def scan_do0_pgc_cooling_time(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, **kwargs):
    """PGC冷却光作用时间扫描"""
    return scan_parameter(awg, nido, niao, camera_ins, "do0_pgc_cooling_time", atomRow, atomColumn, init_val, step, nstep, **kwargs)

def scan_do0_meas_cooling_time(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, **kwargs):
    """探测冷却光作用时间扫描"""
    return scan_parameter(awg, nido, niao, camera_ins, "do0_meas_cooling_time", atomRow, atomColumn, init_val, step, nstep, **kwargs)

def scan_do2_pgc_pump_time(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, **kwargs):
    """PGC回泵光作用时间扫描"""
    return scan_parameter(awg, nido, niao, camera_ins, "do2_pgc_pump_time", atomRow, atomColumn, init_val, step, nstep, **kwargs)

def scan_do2_meas_pump_time(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, **kwargs):
    """探测回泵光作用时间扫描"""
    return scan_parameter(awg, nido, niao, camera_ins, "do2_meas_pump_time", atomRow, atomColumn, init_val, step, nstep, **kwargs)

def scan_ao1_pgc_cooling_detune(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, **kwargs):
    """PGC冷却光失谐扫描"""
    return scan_parameter(awg, nido, niao, camera_ins, "ao1_pgc_cooling_detune", atomRow, atomColumn, init_val, step, nstep, **kwargs)

def scan_ao1_meas_cooling_detune(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, **kwargs):
    """探测冷却光失谐扫描"""
    return scan_parameter(awg, nido, niao, camera_ins, "ao1_meas_cooling_detune", atomRow, atomColumn, init_val, step, nstep, **kwargs)

def scan_ao1_meas_cooling_freq(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, **kwargs):
    """探测冷却光频率扫描"""
    return scan_parameter(awg, nido, niao, camera_ins, "ao1_meas_cooling_freq", atomRow, atomColumn, init_val, step, nstep, **kwargs)

def scan_ao3_pgc_pump_detune(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, **kwargs):
    """PGC回泵光失谐扫描"""
    return scan_parameter(awg, nido, niao, camera_ins, "ao3_pgc_pump_detune", atomRow, atomColumn, init_val, step, nstep, **kwargs)

def scan_ao3_meas_pump_detune(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, **kwargs):
    """探测回泵光失谐扫描"""
    return scan_parameter(awg, nido, niao, camera_ins, "ao3_meas_pump_detune", atomRow, atomColumn, init_val, step, nstep, **kwargs)

def scan_ao4_pgc_comp_mag(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, **kwargs):
    """PGC水平补偿磁场扫描"""
    return scan_parameter(awg, nido, niao, camera_ins, "ao4_pgc_comp_mag", atomRow, atomColumn, init_val, step, nstep, **kwargs)

def scan_ao5_pgc_comp_mag(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, **kwargs):
    """PGC阱方向补偿磁场扫描"""
    return scan_parameter(awg, nido, niao, camera_ins, "ao5_pgc_comp_mag", atomRow, atomColumn, init_val, step, nstep, **kwargs)

def scan_ao6_pgc_comp_mag(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, **kwargs):
    """PGC上下方向补偿磁场扫描"""
    return scan_parameter(awg, nido, niao, camera_ins, "ao6_pgc_comp_mag", atomRow, atomColumn, init_val, step, nstep, **kwargs)

def scan_ao7_raman_source_freq(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, **kwargs):
    """Raman寻址单比特吸收峰扫描"""
    return scan_parameter(awg, nido, niao, camera_ins, "ao7_raman_source_freq", atomRow, atomColumn, init_val, step, nstep, **kwargs)

def scan_ao8_pgc_pump_amp(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, **kwargs):
    """PGC回泵光幅度扫描"""
    return scan_parameter(awg, nido, niao, camera_ins, "ao8_pgc_pump_amp", atomRow, atomColumn, init_val, step, nstep, **kwargs)

def scan_ao8_meas_pump_amp(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, **kwargs):
    """探测回泵光幅度扫描"""
    return scan_parameter(awg, nido, niao, camera_ins, "ao8_meas_pump_amp", atomRow, atomColumn, init_val, step, nstep, **kwargs)

def scan_ao9_pgc_cooling_amp(awg, nido, niao, camera_ins, atomRow: int, atomColumn: int, init_val: float, step: float, nstep: int, **kwargs):
    """PGC冷却光幅度扫描"""
    return scan_parameter(awg, nido, niao, camera_ins, "ao9_pgc_cooling_amp", atomRow, atomColumn, init_val, step, nstep, **kwargs)
