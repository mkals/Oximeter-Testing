#!/usr/bin/python

import numpy as np
import tkinter as tk
import os
import time
import serial
import pandas as pd
import threading

import matplotlib as mplt
import matplotlib.pyplot as plt

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import multiprocessing
import random
mplt.use('TkAgg')


class CASerialSensor:

    # initialize sensor

    def __init__(self, title, port, baud, header_string, plotting=False):

        self.title = title
        self.port = port
        self.baud = baud
        self.header_string = header_string
        self.headings = self.header_string.split(',')
        self.plotting = plotting

        # Open serial connection
        self._ser = serial.Serial(self.port, self.baud, timeout=600)
        self._ser.flushInput()

        self.data_frame = pd.DataFrame(columns=self.headings)
        self.data_frame.index.name = 'utc_time'

        if self.plotting:
            self.window = tk.Tk()
            # Create the base plot
            self.plot()

            # Call a function to update the plot when there is new data
            self.updateplot(None)

            # self.window.mainloop()

    # read raw infomration from sensor

    def read(self):

        line = self._ser.readline()

        if len(line) == 0:
            raise TimeoutError("No serial data.")

        line = line.decode("utf-8")
        return line.strip()

    def start(self):
        self._looping = True
        self._thread = threading.Thread(target=self._loop, args=())
        self.data_frame = pd.DataFrame(columns=self.headings)
        self.data_frame.index.name = 'utc_time'

        # clean buffers
        self._ser = serial.Serial(self.port, self.baud, timeout=600)
        time.sleep(0.1)
        self._ser.flushInput()

        self._looping = True
        self._thread.start()

    # end data collection

    def end(self, save=True):
        self._looping = False

        if save:
            name = self.generate_filename()
            self.data_frame.to_csv(name)
            return name

    # private methods

    def _loop(self):

        while self._looping:  # mechanism for stopping background thread
            data = self.read()
            data = data.strip().split(',')
            if len(data) == len(self.headings):
                data = [float(p) for p in data]
                self.data_frame.loc[time.time()] = data

    def generate_filename(self):

        # Generate logfile name
        timestring = time.strftime("%Y%m%d_%H%M")
        filename = f"{self.title}_{timestring}.csv"

        directory = 'Data/Logs'

        return os.path.join(directory, filename)

    def bath_compute_putput_parameters(self):

        df = self.data_frame

        period = 2
        mesurement_interval = (
            float(df.index[-1]) - float(df.index[0])) / df.shape[0]
        point_count = int(period / mesurement_interval)

        # times = map_reduce(df['utc_time'], point_count, np.mean)
        dc_r = map_reduce(df.r, point_count, np.mean)
        dc_i = map_reduce(df.i, point_count, np.mean)
        ac_r = map_reduce(df.r, point_count, (lambda x: max(x) - min(x)))
        ac_i = map_reduce(df.i, point_count, (lambda x: max(x) - min(x)))

        dc_r_mean = np.mean(dc_r)
        dc_i_mean = np.mean(dc_i)
        ac_r_mean = np.mean(ac_r)
        ac_i_mean = np.mean(ac_i)

        print(f'DC Red = {dc_r_mean:.0f}')
        print(f'DC IR  = {dc_i_mean:.0f}')
        print(f'AC Red = {ac_r_mean:.0f}')
        print(f'AC IR  = {ac_i_mean:.0f}')

        return [dc_r_mean, dc_i_mean, ac_r_mean, ac_i_mean]
        '{dc_r_mean:.0f}, {dc_i_mean:.0f}, {ac_r_mean:.0f}, {ac_i_mean:.0f}'

    def plot(self):  # Function to create the base plot, make sure to make global the lines, axes, canvas and any part that you would want to update later
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.window)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        self.canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        self.line, = self.ax.plot([1, 2, 3], [1, 2, 10])

    def updateplot(self, q):

        # self.line.set_ydata()
        # self.line.set_xdata()
        # self.ax.draw_artist(self.line)
        try:
            self.ax.plot(self.data_frame.iloc[0])
            self.canvas.draw()
            self.window.after(500, self.updateplot, q)
        except IndexError:
            pass

        # try:  # Try to check if there is data in the queue
        #     result = q.get_nowait()

        #     if result != 'Q':
        #         print(result)
        #         # here get crazy with the plotting, you have access to all the global variables that you defined in the plot function, and have the data that the simulation sent.
        #         self.line.set_ydata([1, result, 10])
        #         self.ax.draw_artist(self.line)
        #         self.canvas.draw()
        #         self.window.after(500, self.updateplot, q)
        #     else:
        #         print('done')
        # except:
        #     print("empty")
        #     self.window.after(500, self.updateplot, q)


PULSE_OXIMETER_HEADER_STRING = 'red,beat_red,pulse_red,pulse_red_threshold,red_sig,ir_sig,r,i,SPO2,beatAvg,rollHrAvg,SPO2Avg'


def map_reduce(data, splits, func):
    data = list(data)
    return [func(data[i:i + splits]) for i in range(len(data) - splits + 1)]


def plot_bath_summary(df):

    period = 2
    mesurement_interval = (
        df.utc_time.iloc[-1] - df.utc_time.iloc[0]) / df.shape[0]
    point_count = int(period / mesurement_interval)

    times = map_reduce(df['utc_time'], point_count, np.mean)
    dc_r = map_reduce(df.r, point_count, np.mean)
    dc_i = map_reduce(df.i, point_count, np.mean)
    ac_r = map_reduce(df.r, point_count, (lambda x: max(x) - min(x)))
    ac_i = map_reduce(df.i, point_count, (lambda x: max(x) - min(x)))

    dc_r_mean = np.mean(dc_r)
    dc_i_mean = np.mean(dc_i)
    ac_r_mean = np.mean(ac_r)
    ac_i_mean = np.mean(ac_i)

    print(f'DC Red = {dc_r_mean:.0f}')
    print(f'DC IR  = {dc_i_mean:.0f}')
    print(f'AC Red = {ac_r_mean:.0f}')
    print(f'AC IR  = {ac_i_mean:.0f}')

    f, (ax1, ax2) = plt.subplots(1, 2)  # , sharey=True)

    # DC PLOT
    ax1.plot(df.utc_time, df.r)
    ax1.plot(df.utc_time, df.i)
    ax1.plot(times, dc_r, '-')
    ax1.plot(times, dc_i, '-')
    ax1.axhline(dc_r_mean)
    ax1.axhline(dc_i_mean)

    ax1.set_title('DC Bath Data')
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Signal')
    ax1.legend(['r', 'i', 'r ra', 'i ra', 'r mean', 'i mean'])

    # AC PLOT
    ax2.plot(times, ac_r)
    ax2.plot(times, ac_i)
    ax2.axhline(ac_r_mean)
    ax2.axhline(ac_i_mean)

    ax2.set_title('AC')
    ax2.set_xlabel('Time')
    ax2.set_ylabel('Signal')
    ax2.legend(['r', 'i', 'r mean', 'i mean'])

    plt.show()


if __name__ == '__main__':
    # df = pd.read_csv(
    #     '/Users/mkals/Developer/Cambridge/Oximeter Testing/Data/Logs/bath_20210701_1141_mo_r2_g.csv')
    # plot_bath_summary(df)

    import MKUsbLocator
    port = MKUsbLocator.ask_user()
    po = CASerialSensor(title='bath',
                        port=port,
                        baud=19200,
                        header_string=PULSE_OXIMETER_HEADER_STRING,
                        plotting=False)

    _ = po.read()

    print('Data collection')
    po.start()
    time.sleep(1)
    po.end()

    df = po.data_frame
    # plt.figure()
    # plt.plot(df.index, df.r)
    # plt.plot(df.index, df.i)
    # plt.show()

    print(f'Mean Red = {np.mean(df.r):.0f}')
    print(f'Mean IR  = {np.mean(df.i):.0f}')
    print(f'{np.mean(df.r):.0f},{np.mean(df.i):.0f}')
