import sys
import time

import numpy as np

from matplotlib.backends.qt_compat import QtWidgets
from matplotlib.backends.backend_qtagg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


class ScanWindow(QtWidgets.QMainWindow):
    def __init__(self, cycle=1, plot_flag=True, dims=1):  # 增加 dims 参数
        super().__init__()
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        layout = QtWidgets.QVBoxLayout(self._main)

        self.counter = 0
        self.cycle_counter = 0
        self.tlist = np.linspace(0,10,100)
        self.title = "Time (us)"

        self.t = np.array([])
        self.y = [[] for _ in range(dims)]  # 根据dims创建空列表
        self.y_accumulated = [[] for _ in range(dims)]
        self.y_accumulated_plot = None
        self.cycle = cycle
        self.plot_flag = plot_flag
        self.dims = dims

        dynamic_canvas = FigureCanvas(Figure(figsize=(9, 5)))

        layout.addWidget(dynamic_canvas)
        layout.addWidget(NavigationToolbar(dynamic_canvas, self))

        if cycle>=2:
            accumulated_canvas = FigureCanvas(Figure(figsize=(9, 5)))
            layout.addWidget(accumulated_canvas)
            layout.addWidget(NavigationToolbar(accumulated_canvas, self))
            self._accumulated_ax = accumulated_canvas.figure.subplots()
            self._accumulated_ax.set_title("Accumulation")
            self.set_xlim_accumulated()
            self.set_ylim_accumulated()
            self.set_title_accumulated()

        self._dynamic_ax = dynamic_canvas.figure.subplots()
        self.set_xlim()
        self.set_ylim()
        self.set_title()

        self._lines = []
        self._lines_accumulated = []
        for _ in range(self.dims):  # 使用dims来创建绘图线
            line, = self._dynamic_ax.plot([],[])
            self._lines.append(line)
            if cycle >= 2:
                line_accumulated, = self._accumulated_ax.plot([],[])
                self._lines_accumulated.append(line_accumulated)

        self._timer = dynamic_canvas.new_timer(interval=0)
        if self.cycle>=2:
            self._timer.add_callback(self._update_canvas_accumulated)
        else:
            self._timer.add_callback(self._update_canvas)

        self._timer.start()

    def get_data(self, x):
        time.sleep(0.05)
        return [np.sin(x+np.random.random()/5)**2 for _ in self.dims]
        
    def _update_canvas(self):
        self.counter = self.counter + 1
        if self.counter == len(self.tlist):
            self._timer.stop()
            
        self.t = self.tlist[:self.counter]
        data = self.get_data(self.t[-1])  # 获取函数返回的数据
        
        for i in range(self.dims):
            self.y[i] = np.append(self.y[i], data[i])
            self._lines[i].set_data(self.t, self.y[i])
            #self.set_ylim([min(self.y[i])*0.99-0.01, max(self.y[i])*1.01+0.01])
        self.set_ylim([min([min(v) for v in self.y])*0.99-0.01, max([max(v) for v in self.y])*1.01+0.01])
        
        self._dynamic_ax.figure.canvas.draw()

    def _update_canvas_accumulated(self):
        self.counter = self.counter + 1
        
        if self.counter == len(self.tlist)+1:
            self.counter = 1
            self.cycle_counter = self.cycle_counter + 1
            self.y_accumulated = [y + [y_cur] for y, y_cur in zip(self.y_accumulated, self.y)]
            self.y_accumulated_plot = [np.mean(y, axis=0) for y in self.y_accumulated]
            self.y = [[] for _ in range(self.dims)]
            
            for i in range(self.dims):
                self._lines_accumulated[i].set_data(self.t, self.y_accumulated_plot[i])
                self.set_ylim_accumulated([min(self.y_accumulated_plot[i])*0.99-0.01, max(self.y_accumulated_plot[i])*1.01+0.01])
                self._lines_accumulated[i].figure.canvas.draw()

            if self.cycle_counter >= self.cycle:
                self._timer.stop()
                
        self.t = self.tlist[:self.counter]
        data = self.get_data(self.t[-1])
        for i in range(self.dims):
            self.y[i] = np.append(self.y[i], data[i])
            self._lines[i].set_data(self.t, self.y[i])
            #self.set_ylim([min(self.y[i])*0.99-0.01, max(self.y[i])*1.01+0.01])
        self.set_ylim([min([min(v) for v in self.y])*0.99-0.01, max([max(v) for v in self.y])*1.01+0.01])
          
        self._dynamic_ax.figure.canvas.draw()
    
        
    def set_xlim(self, xrange=[0,20]):
        self._dynamic_ax.set_xlim(xrange)
    
    def set_ylim(self, yrange=[-0.01,1.01]):
        self._dynamic_ax.set_ylim(yrange)
        
    def set_title(self):
        self._dynamic_ax.set_xlabel(self.title)
        
    #if accumulated, these function will be used
    def set_xlim_accumulated(self, xrange=[0,20]):
        self._accumulated_ax.set_xlim(xrange)
    
    def set_ylim_accumulated(self, yrange=[-0.01,1.01]):
        self._accumulated_ax.set_ylim(yrange)
        
    def set_title_accumulated(self):
        self._accumulated_ax.set_xlabel(self.title)
        
    def closeEvent(self, event):
        if self.plot_flag:
            plt.figure()
            plt.xlabel(self.title)
            if self.cycle >= 2 and self.y_accumulated_plot is not None:
                for i, y_accumulated_plot_i in enumerate(self.y_accumulated_plot):
                    plt.plot(self.tlist, y_accumulated_plot_i, label=f'Plot {i+1}')
            else:
                for i, y_i in enumerate(self.y):
                    plt.plot(self.t, y_i, label=f'Plot {i+1}')
            plt.legend()
            #plt.show()

        # Stop the timers and quit the application
        self._timer.stop()
        # if self.cycle >= 2:
        #     self._timer_accumulated.stop()
        event.accept()
        QtWidgets.QApplication.quit()


def scan_generator_pop(func=None, scan_list=np.linspace(0,10,100), cycle=1, title="Time (us)", plot_flag=True, dims=1):  # 增加 dims 参数
    qapp = QtWidgets.QApplication.instance()
    if not qapp:
        qapp = QtWidgets.QApplication(sys.argv)

    app = ScanWindow(cycle=cycle, plot_flag=plot_flag, dims=dims)  # 在创建 ScanWindow 时传入 dims 参数
    app.tlist = scan_list
    app.title = title

    if callable(func):
        app.get_data = func

    app.set_xlim([scan_list[0], scan_list[-1]])
    app.set_title()

    if cycle >=2:
        app.set_xlim_accumulated([scan_list[0], scan_list[-1]])
        app.set_title_accumulated()

    app.show()
    app.activateWindow()
    app.raise_()
    qapp.exec_()