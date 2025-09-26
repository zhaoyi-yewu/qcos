import numpy as np
import time
import os
from scipy.optimize import curve_fit
from scipy.fftpack import fft, fftfreq
import matplotlib.pyplot as plt
import json
import h5py
import io
import ipywidgets as widgets
from IPython.display import display
from collections import defaultdict
import math
import numpy as np
import platform
    
debug_mode = False

global channel_return

class DataDoc():
    """
    数据存储类
    Args:
        disk_path (str, optional): 存储目录，结合当前时间可生成具体存储位置，默认为当前目录.
        title (str, optional): 文件名. Defaults to "".
        path (_type_, optional): 具体存储位置. Defaults to None.
    """
    def __init__(self, disk_path='', title="", path=None):
        if path==None:
            self.path_prefix = disk_path + time.strftime("%Y%m%d/")
            if platform.system() == 'Windows':
                self.path_prefix = disk_path + time.strftime("%Y%m%d\\")
            
        else:
            self.path_prefix = path
        #if not os.path.exists(self.path_prefix) and not debug_mode:
        #path_prefix = self.path_prefix
        if not os.path.exists(self.path_prefix):
            print("Data will be save into ",self.path_prefix)
            os.makedirs(self.path_prefix)
        
        self.title            = title
        self.xlabel           = "Duration"
        self.ylabel           = "Counts"
        self.SystemParameters = {"CONTENT":"EMPTY"}
        self.IonParameters    = {"CONTENT":"EMPTY"}
        self.Sequence         = {"CONTENT":"EMPTY"}
        self.RawData          = {"Duration":np.array([],dtype=np.float32),"Counts":np.array([],dtype=np.float32)}
        self.DataFileName     = ""

    def new_data_file(self):
        file_name = self.title + time.strftime("-%H%M%S")
        return file_name

    def jsonify(self, data):
        data_return = list(data)
        return data_return

    def reset_raw_data(self, xtype="Duration"):
        self.xlabel = xtype
        self.RawData          = {self.xlabel: np.array([],dtype=np.float32), self.ylabel: []}
        self.DataFileName     = self.new_data_file()
        #print(self.path_prefix+self.DataFileName+".hdf5")

    def append_raw_data(self, x, y):
        """
        添加数据到末尾
        """
        self.RawData[self.xlabel] = np.append(self.RawData[self.xlabel],x)
        self.RawData[self.ylabel] = self.RawData[self.ylabel] + [y]

    def generate_json(self):
        """
        生成数据文件（hdf5）
        """
        file_name = self.DataFileName
        json_name = file_name + ".json"
        json_path = self.path_prefix + json_name
        hdf5_name = file_name + ".hdf5"
        hdf5_path = self.path_prefix + hdf5_name

        self.DataFileName = hdf5_path

        data_to_save = self.__dict__.copy()
        if "RawData" in data_to_save:
            del data_to_save["RawData"]
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)

        with h5py.File(hdf5_path, 'w') as f:
            f[self.xlabel] = self.RawData[self.xlabel]
            f[self.ylabel] = np.array(self.RawData[self.ylabel],dtype=np.float32)
        return file_name

def data_viewer(folder_path):
    """
    可视化展示目录下的所有hdf5文件数据
    """
    file_names = [file for file in os.listdir(folder_path) if file.endswith('.hdf5')]

    dropdown = widgets.Dropdown(
        options=file_names,
        description='Files:',
    )

    prev_button = widgets.Button(
        description='Previous Image',
    )

    next_button = widgets.Button(
        description='Next Image',
    )

    image_widget = widgets.Image()
    file_path_widget = widgets.Text(description='File Path:', disabled=True)

    display(dropdown, prev_button, next_button, image_widget, file_path_widget)

    def update_plot(change):
        selected_file = folder_path + dropdown.value
        buf = io.BytesIO()
        average_plot(selected_file)
        plt.savefig(buf, format='png')
        buf.seek(0)
        image_widget.value = buf.read()
        plt.close()
        file_path_widget.value = selected_file

    def on_prev_button_click(button):
        current_index = file_names.index(dropdown.value)
        if current_index > 0:
            dropdown.value = file_names[current_index - 1]

    def on_next_button_click(button):
        current_index = file_names.index(dropdown.value)
        if current_index < len(file_names) - 1:
            dropdown.value = file_names[current_index + 1]

    # Observe the dropdown value changes and automatically update the plot
    dropdown.observe(update_plot, names='value')

    # Update the plot with the first file when the function is called
    update_plot(None)

    prev_button.on_click(on_prev_button_click)
    next_button.on_click(on_next_button_click)
    
class scanParameterType():
    time = 1
    frequency = 2

def raw_count(path):
    """
    Returns two lists: the first is the list of scan parameters (time or frequency),
    the second is the related list of matrices.
    """
    # Open the file
    with h5py.File(path, 'r') as mat:
        keys = list(mat.keys())
        if len(keys) < 2:
            raise ValueError(f"Expected at least 2 keys in the HDF5 file, got {len(keys)}.")
        
        ylabel, xlabel = keys
        if xlabel == 'Counts':
            xlabel, ylabel = ylabel, xlabel
        list_time = [mat[xlabel][i] for i in range(len(mat[xlabel]))]
        list_values = [mat[ylabel][i] for i in range(len(mat[ylabel]))]

    return list_time, list_values, xlabel

def verify(total_channels, show_channels):
    """
    Validates the input parameters for total_channels and show_channels.
    Returns the validated total_channels and show_channels.
    """
    # Validate total_channels
    assert isinstance(total_channels, int), "total_channels must be an integer."
    assert total_channels > 0, "total_channels must be greater than 0."
    
    # Validate show_channels
    if isinstance(show_channels, int):
        show_channels = [show_channels]
    elif show_channels is None:
        show_channels = list(range(total_channels))
    assert isinstance(show_channels, list), "show_channels must be a list."
    
    return total_channels, show_channels

def average(filename, threshold=None, total_channels = 1):
    """
    针对每个通道，将扫描实验中多次测量结果求平均

    Args:
        filename (_type_): 扫描实验结果文件
        threshold (_type_, optional): 阈值，用以过滤噪声数据. Defaults to None.
        total_channels (int, optional): 通道数. Defaults to 1.
    """
    def process_list_values(list_values, total_channels, threshold=None):
        
        repeat = len(list_values[0])
        if isinstance(list_values[0][0], np.number):
            repeat = repeat // total_channels
        else:
            total_channels = len(list_values[0][0])
               
        if repeat == 0:
            raise ValueError("The length of the input data is less than the total number of channels or empty.")
        
        for i in range(len(list_values)):
            list_values[i] = np.transpose(list_values[i].reshape(repeat, total_channels))
            for j in range(total_channels):
                if threshold is not None:
                    list_values[i][j] = np.array([np.where(list_values[i][j] > threshold[j], 1, 0)])
                else:
                    list_values[i][j] = np.mean(list_values[i][j])

        for i in range(len(list_values)):
            list_values[i] = np.mean(list_values[i], axis=1)
        
        return list_values

    list_time, list_values, xlabel = raw_count(filename)
    #print(list_time, list_values, xlabel)
    list_values = process_list_values(list_values, total_channels, threshold)

    # Group the list_values by their corresponding list_time values
    grouped_values = defaultdict(list)
    for time, value in zip(list_time, list_values):
        grouped_values[time].append(value)

    # Calculate the average of the list_values for each list_time value
    averaged_values = {time: np.mean(values, axis=0) for time, values in grouped_values.items()}

    # Sort the list_time values and their corresponding averaged list_values
    sorted_time = sorted(averaged_values.keys())
    sorted_values = [averaged_values[time] for time in sorted_time]

    return sorted_time, sorted_values

# def average(filename, threshold=None):
#     def process_list_values(list_values, total_channels, threshold=None):
#         repeat = len(list_values[0]) // total_channels
#         if repeat == 0:
#             raise ValueError("The length of the input data is less than the total number of channels or empty.")
        
#         for i in range(len(list_values)):
#             list_values[i] = np.transpose(list_values[i].reshape(repeat, total_channels))
#             for j in range(total_channels):
#                 if threshold is not None:
#                     list_values[i][j] = np.array([np.where(list_values[i][j] > threshold[j], 1, 0)])
#                 else:
#                     list_values[i][j] = np.mean(list_values[i][j])

#         for i in range(len(list_values)):
#             list_values[i] = np.mean(list_values[i], axis=1)
        
#         return list_values

#     total_channels = 1
#     list_time, list_values, xlabel = raw_count(filename)
    
#     if threshold is not None:
#         assert type(threshold) == list
#         list_values = process_list_values(list_values, total_channels, threshold)
#     else:
#         list_values = process_list_values(list_values, total_channels)

#     return [np.array(list_time), np.array(list_values)]

def average_plot(filename, threshold=None, show_channels=[0]):
    total_channels=4
    total_channels, show_channels = verify(total_channels, show_channels)
    list_time, list_values = average(filename, threshold=threshold)
    list_values = np.transpose(list_values)
    ch_number = len(show_channels)
    plt.figure(figsize=(8,8))
    for i in range(ch_number):
        ch_idx = show_channels[i]
        plt.subplot(ch_number,1,i+1)
        plt.plot(list_time, list_values[ch_idx])
        plt.title('This is channel {}'.format(ch_idx))
        plt.xlabel('time '+r'$(\mu s)$')
        plt.ylabel('average count')
        plt.tight_layout()
    return

def pre_process(list_matrices, convert_matrix = None, threshold = None):
    """
    扫描数据预处理，主要用在高斯拟合

    Args:
        list_matrices (_type_): 扫描结果
        convert_matrix (_type_, optional): 转换矩阵. Defaults to None.
        threshold (_type_, optional): 噪声阈值. Defaults to None.
    """
    results = []
    total_channels = 4
    repeat = len(list_matrices[0])//total_channels
    for index, raw_matrix in enumerate(list_matrices):
        new_matrix = raw_matrix.reshape(repeat, total_channels)
        new_matrix = np.transpose(new_matrix)
        if convert_matrix is not None:
            new_matrix = convert_matrix @ new_matrix
        if threshold != None:
            for j in range(new_matrix.shape[0]):
                new_matrix[j] = np.where(new_matrix[j]>threshold[j], 1, 0)
        avrg = np.sum(new_matrix, axis = 1)/repeat
        results.append(avrg)
    return results
'''
def average_fit(file_name, convert_matrix = None, threshold = None, para_type = scanParameterType.time):
    assert(type(convert_matrix) != type(None))

    list_para, list_matrices, xlabel = raw_count(file_name)
    avrg_data = pre_process(list_matrices, convert_matrix)
    results = avrg_data
    if threshold != None:
        results = []
        for avrg in avrg_data:
            avrg = (avrg > threshold).astype(int)
            results.append(avrg)
    return results

def histogram_plot(bright_data, dark_data):
    max_index = max(max(bright_data),max(dark_data))
    hist_bright = np.histogram(bright_data, bins=np.arange(max_index), density=True)
    hist_dark = np.histogram(dark_data, bins=np.arange(max_index), density=True)
    plt.figure()
    plt.bar(hist_bright[1][:-1]+0.5,hist_bright[0])
    plt.bar(hist_dark[1][:-1]+0.5,hist_dark[0])
    plt.show() 
    fidelity_list = [(sum(hist_bright[0][i:])+sum(hist_dark[0][:i]))/2 for i in range(max_index)]
    threshold = max(range(len(fidelity_list)), key=fidelity_list.__getitem__)
    return [threshold + 1, fidelity_list[threshold]]

def correlation(file_name, convert_matrix = None, threshold = None, para_type = scanParameterType.time):
    pass
'''

def cosine_func(x,a0,a1,a2,a3):
    return a0 * np.sin(a1*x+a2) + a3

def gaussian_func(x,a,mu,sigma):
    return a*np.exp(-(x-mu)**2/(2*sigma**2))

def gaussian_func2(x, a, mu, sigma_reverse):
    return a*np.exp(-(x-mu)**2 * sigma_reverse**2)

def thermal_single_func(x, p0, gamma, omega):
    return 1/2*p0*(1 - np.exp(-gamma*x)*np.cos(omega*x))

def combinatorial_number(n,m):
    return math.factorial(n) // (math.factorial(m)*math.factorial(n-m))

###################################### Generated by GPT-4 ######################################
def set_plot_style():
    # Set the default style
    plt.style.use('default')
    # Set the background color of the axes area
    plt.rcParams['axes.facecolor'] = '#ffffff'
    plt.rcParams['axes.edgecolor'] = '#000000'
    plt.rcParams['axes.labelcolor'] = '#000000'
    plt.rcParams['xtick.color'] = '#000000'
    plt.rcParams['ytick.color'] = '#000000'
    plt.rcParams['figure.facecolor'] = '#ffffff'
    plt.rcParams['grid.color'] = '#d3d3d3'
    plt.rcParams['grid.alpha'] = 0.5
    plt.rcParams['grid.linestyle'] = '--'

def pre_process_data(file_name):
    """
    扫描数据读取，并求平均
    """
    data = average(file_name)
    x_data, y_data = data[0], [data[1][i][0] for i in range(len(data[0]))]
    return np.array(x_data), np.array(y_data)

def lorentzian(x, a, x0, gamma):
    # Define the Lorentzian function
    return a * gamma**2 / ((x - x0)**2 + gamma**2)

def truncated_lorentzian(x, a, x0, gamma):
    # Define the truncated Lorentzian function
    y = a * gamma**2 / ((x - x0)**2 + gamma**2)
    y[x > x0] = 0
    return y

def universal_fit(x_data, y_data, fit_function, initial_values, label = 'Fit', save_fig = False, figName = ''):
    """
    用户自定义拟合
    Args:
        x_data, y_data: xy轴数据
        fit_function: 拟合函数
        initial_values: 参数初始值
    """
    popt, _ = curve_fit(fit_function, x_data, y_data, p0=initial_values)
    # Set the plot style
    set_plot_style()
    
    # Create the figure and plot the data and fitted curve
    plt.figure()
    plt.scatter(x_data, y_data, label="Original data", s=10, color='#f39c12')
    plt.plot(x_data, fit_function(x_data, *popt), label=label, color="#3498db", linewidth=2)
    plt.legend()
    if save_fig:
        if figName == '': fileName = 'universal_fit.png'
        plt.savefig(fileName)
        plt.close()
    else:
        plt.show()
    return popt


"""
def fit_plot_lorentzian(x_data, y_data, fit_function, fitted_label):
    # Find the index of the maximum y_data value
    max_index = np.argmax(y_data)

    # Set the initial values for the fitting parameters
    initial_values = [y_data[max_index], x_data[max_index], 1]

    # Fit the function to the data
    popt, _ = curve_fit(fit_function, x_data, y_data, p0=initial_values)
    
    # Print the fitted parameters
    print("Fitted parameters:")
    print("Amplitude a =", popt[0])
    print("Center frequency x0 =", popt[1])
    print("Full width at half maximum gamma =", popt[2])
    
    # Set the plot style
    set_plot_style()
    
    # Create the figure and plot the data and fitted curve
    plt.figure()
    plt.scatter(x_data, y_data, label="Original data", s=10, color='#f39c12')
    plt.plot(x_data, fit_function(x_data, *popt), label=fitted_label, color="#3498db", linewidth=2)
    plt.legend()
    plt.show()
    return {"amp": popt[0], "f0": popt[1], "gamma": popt[2]}

def lorentzian_fit(file_name):
    # Load the data from a file and fit the Lorentzian function
    x_data, y_data = pre_process_data(file_name)
    return fit_plot_lorentzian(x_data, y_data, lorentzian, "Fit")

def doppler_fit(file_name):
    # Load the data from a file and fit the truncated Lorentzian function
    x_data, y_data = pre_process_data(file_name)
    return fit_plot_lorentzian(x_data, y_data, truncated_lorentzian, "Fit")
"""

def rabi_oscillation_decay(x, a, omega, offset, tau):
    return -a * np.exp(-x / tau) * np.cos(2*np.pi*omega * x) + offset

def estimate_frequency(x_data, y_data):
    y_fft = fft(y_data - np.mean(y_data))
    freq = fftfreq(len(x_data), x_data[1] - x_data[0])
    max_index = np.argmax(np.abs(y_fft[:len(y_fft) // 2]))
    return np.abs(freq[max_index])

from scipy.signal import argrelextrema

def peak_decay(x_data, y_data):
    # Find the local maxima (peaks) of the data
    peak_indices = argrelextrema(y_data, np.greater)
    x_peaks = x_data[peak_indices]
    y_peaks = y_data[peak_indices]

    # Fit an exponential decay to the peak amplitudes to estimate tau
    popt_decay, _ = curve_fit(lambda x, a, tau: a * np.exp(-x / tau), x_peaks, y_peaks, p0=[np.ptp(y_data), x_data[-1] / 2])
    return popt_decay[1]

def rabi_fit(file_name, bounds = (-np.inf, np.inf), save_fig = False, figName = ''):
    """
    拉比拟合
    Args:
        file_name: 需要拟合的扫描数据文件
    """
    # Set the initial values for the fitting parameters
    x_data, y_data = pre_process_data(file_name)
    # Estimate the frequency using FFT
    estimated_frequency = estimate_frequency(x_data, y_data)
    # Estimate the decay time constant tau using peak_decay function
    tau_estimate = peak_decay(x_data, y_data)

    # Set the initial guess for the fit parameters
    initial_guess = [
        np.ptp(y_data)/2,
        estimated_frequency,
        np.mean(y_data),
        tau_estimate,
    ]

    # Fit the rabi_oscillation_decay function to the data using curve_fit
    popt, pcov = curve_fit(rabi_oscillation_decay, x_data, y_data, p0=initial_guess, bounds=bounds)

    # Print the fitted parameters
    '''
    print("Fitted parameters:")
    print("Contrast 2a =", 2*popt[0])
    print("Pi-time 0.5/omega =", 0.5/popt[1])
    print("Decay time constant tau =", popt[3])
    '''
    # Set the plot style
    set_plot_style()

    # Create the figure and plot the data and fitted curve
    plt.figure()
    plt.scatter(x_data, y_data, label="Original data", s=10, color='#f39c12')
    plt.plot(x_data, rabi_oscillation_decay(x_data, *popt), label="Fit", color="#3498db", linewidth=2)
    plt.legend()
    if save_fig:
        if figName == '': fileName = 'rabi_fit.png'
        plt.savefig(fileName)
        plt.close()
    else:
        plt.show()
    return {"amp": popt[0], "omega": popt[1], "offset": popt[2], "tau": popt[3]}

def check_fitting_quality(ion, xdata, ydata, y_fit):
    pass


def gaussian_fit(fileName, ion_number, convert_matrix = None, threshold = None, plot_figure = False, save_fig = False, figName = ''):
    """
    高斯拟合
    Args:
        file_name: 需要拟合的扫描数据文件
        ion_number: 比特数
        convert_matrix: 转换矩阵
        threshold: 噪声阈值
    """
    list_frequency, list_matrices, xlabel = raw_count(fileName)
    avrg_data_all = pre_process(list_matrices, convert_matrix, threshold)

    fit_paras = []

    for ion_index in range(ion_number):
        
        avrg_single_ion = [avrg[ion_index] for avrg in avrg_data_all]
        xdata = np.array(list_frequency)
        ydata = np.array(avrg_single_ion)

        #mean,std=scipy.stats.norm.fit(ydata)
        a0 = max(ydata)
        
        if a0 == 0:
            fit_paras.append([0,0,1])
            continue
        a1 = xdata[np.argmax(ydata)]
        #a2 = np.std(ydata)
        a2 = np.std(ydata) * (xdata[1] - xdata[0]) / a0
        p0 = [a0, a1, a2]

        #a2 = sum(y * (x - a1)**2)
        #sigma_reverse = 1/(a2 * np.sqrt(2)
        #p0 = [a0, a1, sigma_reverse]
        #p_l = [a0/2, xdata[0], a2/2]
        #p_h = [a0*2, xdata[-1], a2*2]

        #print(p0)
        popt, pcov = curve_fit(gaussian_func, xdata, ydata, p0=p0)
        #popt, pcov = curve_fit(gaussian_func2, xdata, ydata, p0=p0)
        fit_paras.append(popt)
        #print(popt)

        fit_data = gaussian_func(xdata, *popt)
        check_fitting_quality(ion_index, xdata, ydata, fit_data)
        #print('fit_paras', popt)

    if plot_figure:
        plt.figure(figsize=(8,8))
        for ion_index in range(ion_number):
            if ion_index != 0:
                continue ##目前只需要第1个通道
            avrg_single_ion = [avrg[ion_index] for avrg in avrg_data_all]
            x_fit = np.linspace(min(list_frequency),max(list_frequency), 100)
            avrg_fit = [gaussian_func(x, *fit_paras[ion_index]) for x in x_fit]

            plt.subplot(ion_number,1,ion_index+1)
            plt.plot(list_frequency, avrg_single_ion)

            xdata = np.array(list_frequency)
            ydata = np.array(avrg_single_ion)
            #a0 = max(ydata)
            #a1 = xdata[np.argmax(ydata)]
            #a2 = sum(y * (x - a1)**2)
            #ydata2 = gaussian_func(xdata, a0, a1, a2)
            #plt.plot(xdata, ydata2)

            plt.plot(x_fit, avrg_fit)
            #print(fit_paras[ion_index])
            plt.title(('This is channel {}, '+r'$\mu $'+'= {:.4f}, '+r'$\sigma = {:.4f}$').format(ion_index, fit_paras[ion_index][1], fit_paras[ion_index][2]))
            #plt.title(('This is ion {}, '+r'$\mu $'+'= {:.4f}, '+r'$\sigma = {:.4f}$').format(ion_index, fit_paras[ion_index][1], np.sqrt(2)/fit_paras[ion_index][2]))
            plt.xlabel('frequency '+' (MHz)')
            plt.ylabel('average count')

        plt.tight_layout()

        if save_fig:
            if figName == '': fileName = 'gaussian_fit.png'
            plt.savefig(fileName)
            plt.close()

    return fit_paras

"""
def thermal_state_fit(fileName, pt0, nth0, eta=0.03, plot=True):
    rawdata = average(fileName)
    rawdata = np.array([rawdata[0], [i[0] for i in rawdata[1]]])
    dat = np.transpose(rawdata)
    dat[:, 0] = dat[:, 0] - np.min(dat[:, 0])
    maxN = np.round(-np.log(0.01)/np.log(1 + 1 / nth0)).astype(int)
    print(f"maxN: {maxN}")  # print maxN for debugging

    if np.mean(dat[:3, 1]) < np.mean(dat[:, 1]):
        s = -1
    else:
        s = 1

    def func(t, A, B, nth, pt, lmbd, alpha):
        terms = [nth ** i / (1 + nth) ** (i + 1) * np.exp(-lmbd * (i + 1) ** 0.7) * np.cos(laguerre(i)(eta ** 2) / np.sqrt(i + 1) * np.pi/pt * t) for i in range(maxN)]
        return (A * s) / 2 * sum(terms) * np.exp(-alpha*t) + B

    model = Model(func)
    params = model.make_params(A=1, B=0.5, nth=nth0, pt=pt0, lmbd=0.1/np.max(dat[:, 0]), alpha = 0)
   # params['pt'].vary = False  # This will fix the value of pt at pt0
    params['nth'].min = 0
    params['A'].min = 0.5
    params['A'].max = 1.1
    params['lmbd'].max = 1/max(dat[:,0])
    params['lmbd'].min = 0
    params['alpha'].max = 0.004
    fit = model.fit(dat[:, 1], params, t=dat[:, 0])
    fit_params = fit.params
    R2 = 1 - fit.residual.var() / np.var(dat[:, 1])
    conf_interval_ufloat = {param: ufloat(fit_params[param].value, fit_params[param].stderr)
                            for param in fit_params if fit_params[param].stderr is not None}
    plt.figure()
    if plot:
        plt.scatter(dat[:, 0], dat[:, 1], color='blue')
        plt.plot(dat[:, 0], fit.best_fit, color='red')
        plt.show()
    print("nth: ", fit.params['nth'].value)
    print("pi time: ", fit.params['pt'].value)
"""