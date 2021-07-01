#!/usr/bin/python

import Tkinter as tk
import os
import time
import serial
import pandas as pd
import threading

import matplotlib as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
import multiprocessing
import random
plt.use('TkAgg')


class CASerialSensor:

    # initialize sensor

    def __init__(self, title, port, baud, header_string, plot=False):

        self.title = title
        self.header_string = header_string
        self.headings = self.header_string.split(',')
        self.plot = plot

        # Open serial connection
        self._ser = serial.Serial(port, baud, timeout=600)
        self._ser.flushInput()

        if self.plot():
            self.window = tk.Tk()
            # Create the base plot
            self.plot()

            # Call a function to update the plot when there is new data
            self.updateplot()

            self.window.mainloop()

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

        self._looping = True
        self._thread.start()

    # end data collection

    def end(self, save=True):
        self._looping = False

        if save:
            name = self.generate_filename()
            self.data_frame.to_csv(name)

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

    def plot(self):  # Function to create the base plot, make sure to make global the lines, axes, canvas and any part that you would want to update later

        self.fig = plt.figure.Figure()
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.window)
        self.canvas.show()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        self.canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        self.line, = self.ax.plot([1, 2, 3], [1, 2, 10])

    def updateplot(self, q):
        try:  # Try to check if there is data in the queue
            result = q.get_nowait()

            if result != 'Q':
                print(result)
                # here get crazy with the plotting, you have access to all the global variables that you defined in the plot function, and have the data that the simulation sent.
                self.line.set_ydata([1, result, 10])
                self.ax.draw_artist(self.line)
                self.canvas.draw()
                self.window.after(500, self.updateplot, q)
            else:
                print('done')
        except:
            print("empty")
            self.window.after(500, self.updateplot, q)


PULSE_OXIMETER_HEADER_STRING = 'red,beat_red,pulse_red,pulse_red_threshold,red_sig,ir_sig,r,i,SPO2,beatAvg,rollHrAvg,SPO2Avg'


if __name__ == '__main__':
    import MKUsbLocator
    port = MKUsbLocator.ask_user()
    po = CASerialSensor(title='bath',
                        port=port,
                        baud=19200,
                        header_string=PULSE_OXIMETER_HEADER_STRING)

    print(po.read())

    print('Data collection')
    po.start()
    time.sleep(60)
    po.end()
    print(po.data_frame)
