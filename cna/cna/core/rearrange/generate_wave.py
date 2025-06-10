import json
import numpy as np
import os


def save_wave_file(data, file_name, file_dir):
    data = np.round(data, 5)
    with open(f'{file_dir}/{file_name}.dat', 'w') as fo:
        fo.write(f'waveformName,{file_name}\n')
        fo.write(f'waveformPoints,{len(data)}\n')
        fo.write(f'waveformType,WAVE_ANALOG_16\n')
        for v in data:
            fo.write(f'{v}\n')


def generate_rea_wave(qpu_file, **kwargs):
    # """生成重排所需波形文件
    # Args:
    #     qpu_file (_type_): 硬件配置文件
    # """

    with open(qpu_file, 'r') as f:

        # 生成重排的操作文件

        config = json.loads(f.read())
        overview = config['overview']
        r = overview['row']
        c = overview['column']
        samplingRate = overview['awgSamplingRate']

        move_config = config['movement']
        init_freq_x = kwargs.get('init_freq_x', move_config['init_freq_x'])
        init_freq_y = kwargs.get('init_freq_y', move_config['init_freq_y'])
        inter_freq_x = kwargs.get('inter_freq_x', move_config['inter_freq_x'])
        inter_freq_y = kwargs.get('inter_freq_y', move_config['inter_freq_y'])
        grab_time = kwargs.get('grab_time', move_config['grab_time'])
        mov_time = kwargs.get('mov_time', move_config['mov_time'])

        grab_n = int(round(grab_time * samplingRate))
        grab_t = np.linspace(0, grab_n - 1, grab_n) / samplingRate
        mov_n = int(round(mov_time * samplingRate))
        mov_t = np.linspace(0, mov_n - 1, mov_n) / samplingRate

        file_dir = kwargs.get('file_dir', './wave_file')
        if not os.path.exists(file_dir):
            os.mkdir(file_dir)

        for i in range(r):

            print(f"generate grab x: {i}")
            fsx = init_freq_x + i * inter_freq_x
            data = np.sin(2 * np.pi * fsx * grab_t) * grab_t / grab_time
            save_wave_file(data, f'x_grab_{i}', file_dir)

            print(f"generate put x: {i}")
            data = np.sin(2 * np.pi * fsx * grab_t) * (grab_time - grab_t) / grab_time
            save_wave_file(data, f'x_put_{i}', file_dir)

            print(f"generate stable x: {i}")
            data = np.sin(2 * np.pi * (fsx * mov_t))
            save_wave_file(data, f'x_stable_{i}', file_dir)

            if i + 1 < r:
                print(f"generate mov x: {i} -> {i + 1}")
                fex = init_freq_x + (i + 1) * inter_freq_x
                data = np.sin(2 * np.pi * ((fex - fsx) * mov_t * mov_t / (2 * mov_time) + fsx * mov_t))
                save_wave_file(data, f'x_move_{i}_{i + 1}', file_dir)

            if i - 1 >= 0:
                print(f"generate mov x: {i} -> {i - 1}")
                fex = init_freq_x + (i - 1) * inter_freq_x
                data = np.sin(2 * np.pi * ((fex - fsx) * mov_t * mov_t / (2 * mov_time) + fsx * mov_t))
                save_wave_file(data, f'x_move_{i}_{i - 1}', file_dir)

        for j in range(c):

            print(f"generate grab y: {j}")
            fsy = init_freq_y + j * inter_freq_y
            data = np.sin(2 * np.pi * fsy * grab_t) * grab_t / grab_time
            save_wave_file(data, f'y_grab_{j}', file_dir)

            print(f"generate put y: {j}")
            data = np.sin(2 * np.pi * fsy * grab_t) * (grab_time - grab_t) / grab_time
            save_wave_file(data, f'y_put_{j}', file_dir)

            print(f"generate stable y: {j}")
            data = np.sin(2 * np.pi * (fsy * mov_t))
            save_wave_file(data, f'y_stable_{j}', file_dir)

            if j + 1 < c:
                print(f"generate mov y: {j} -> {j + 1}")
                fey = init_freq_y + (j + 1) * inter_freq_y
                data = np.sin(2 * np.pi * ((fey - fsy) * mov_t * mov_t / (2 * mov_time) + fsy * mov_t))
                save_wave_file(data, f'y_move_{j}_{j + 1}', file_dir)

            if j - 1 >= 0:
                print(f"generate mov y: {j} -> {j - 1}")
                fey = init_freq_y + (j - 1) * inter_freq_y
                data = np.sin(2 * np.pi * ((fey - fsy) * mov_t * mov_t / (2 * mov_time) + fsy * mov_t))
                save_wave_file(data, f'y_move_{j}_{j - 1}', file_dir)

        print(f"final wave")
        freq = kwargs.get('cont_freq', 200e6)
        data = np.sin(2 * np.pi * (freq * mov_t))
        save_wave_file(data, 'final_wave', file_dir)


def generate_raman_wave(qpu_file, **kwargs):
    # """生成raman光寻址所需波形文件
    # Args:
    #     qpu_file (_type_): 硬件配置文件
    # """
    with open(qpu_file, 'r') as f:

        config = json.loads(f.read())
        overview = config['overview']
        r = overview['row']
        c = overview['column']
        samplingRate = overview['awgSamplingRate']

        # 生成raman光寻址文件
        raman_config = config['raman']
        init_freq_x = kwargs.get('init_freq_x', raman_config['init_freq_x'])
        init_freq_y = kwargs.get('init_freq_y', raman_config['init_freq_y'])
        inter_freq_x = kwargs.get('inter_freq_x', raman_config['inter_freq_x'])
        inter_freq_y = kwargs.get('inter_freq_y', raman_config['inter_freq_y'])
        c1_time = kwargs.get('c1_time', raman_config['c1_time'])

        c1_n = int(round(c1_time * samplingRate))
        c1_t = np.linspace(0, c1_n - 1, c1_n) / samplingRate

        file_dir = kwargs.get('file_dir', './wave_file')
        if not os.path.exists(file_dir):
            os.mkdir(file_dir)

        for i in range(r):
            print(f"generate raman x: {i}")
            fsx = init_freq_x + i * inter_freq_x
            data = np.sin(2 * np.pi * (fsx * c1_t))
            save_wave_file(data, f'raman_x_{i}', file_dir)

        for j in range(c):
            print(f"generate raman y: {j}")
            fsy = init_freq_y + i * inter_freq_y
            data = np.sin(2 * np.pi * (fsy * c1_t))
            save_wave_file(data, f'raman_y_{j}', file_dir)


if __name__ == '__main__':
    generate_rea_wave('./na_file.json')
    generate_raman_wave('./na_file.json')

