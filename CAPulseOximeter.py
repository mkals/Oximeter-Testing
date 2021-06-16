#!/usr/bin/python

import time
import serial


class CAPulseOximeter:

    header_string = 'time,red,beat_red,pulse_red,pulse_red_threshold,red_sig,ir_sig,r,i,SPO2,beatAvg,rollHrAvg,SPO2Avg'

    def __init__(self, port='/dev/tty.usbserial-1440'):

        # Open serial connection
        self._ser = serial.Serial(port, 19200, timeout = 600)
        self._ser.flushInput()

    def read(self):

        line = self._ser.readline()
        
        if len(line) == 0:
            raise TimeoutError("No serial data.")
        
        line = line.decode("utf-8")
        line = line.strip()
        
        if line[-1] == ',':
            line = line[:-1] # remove trailing ,

        line = f'{time.time()},{line}' # prepend UTC time

        return line


if __name__ == '__main__':
    po = CAPulseOximeter()
    a = po.read()
    print(a)