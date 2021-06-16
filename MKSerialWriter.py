#!/usr/bin/python

import os, sys
import time

import serial

import threading 
import sys

import platform
from pathlib import Path
 
import pandas as pd


header_string = 'time,red,beat_red,pulse_red,pulse_red_threshold,red_sig,ir_sig,r,i'

c = threading.Condition() # for synchronizing access to active_ports
active_ports = []
threads = []

def generate_file(port):
	# Find log-file path
	if platform.system() == 'Linux':
		# place in home directory of Pi
		directory = str(Path.home())
		keep_letters = 7
	else:
		# place in log directory of Mac
		directory = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
		keep_letters = 8
	
	# Generate logfile name
	timestring = time.strftime("%Y%m%d_%H%M")
	filename = f"CA_{timestring}_{port[-keep_letters:]}.csv"

	directory = os.path.join(directory, 'Logs/')
	if not os.path.exists(directory):
		os.makedirs(directory)
	
	file = os.path.join(directory, filename)

	return file


def append_to_file(file, l):
	with open(file, "a") as f: # append mode
		f.write(f'{l}\n')


def printToFileFromPort(port):
	
	file = generate_file(port)
	print('Started recording to:', file)

	append_to_file(file, header_string)

	# Open serial connection
	ser = serial.Serial(port, 19200, timeout = 600)
	ser.flushInput()

	# listen for the input, exit if nothing received in timeout period
	# try:
	while True:
		line = ser.readline()
		
		if len(line) == 0:
			raise TimeoutError("No serial data.")
		
		line = line.decode("utf-8")
		line = line.strip()
		
		if line[-1] == ',':
			line = line[:-1] # remove trailing ,

		line = f'{time.time()},{line}' # prepend UTC time
		
		append_to_file(file, line)

	# except Exception:
	# 	# Issue, most likely terminated serial connection
	# 	global active_ports
	# 	active_ports.remove(port)
	# 	print('Removed port', {port})



def collectSerialData():
	
	global threads
	
	try:
		while True:
			ports = ['/dev/cu.usbserial-1440']#[p[0] for p in list_ports.comports() if 'usb' in p[0]]
			new_ports = [p for p in ports if p not in active_ports]
			
			for port in new_ports:
				t = threading.Thread(target=printToFileFromPort, args=(port,))
				threads.append(t)
				t.daemon = True
				active_ports.append(port)
				t.start()
				# print('Added port', port)

			time.sleep(1)

	except KeyboardInterrupt:

		print("Ctrl+C pressed.")
		sys.exit(1)


def generate_image_directory():
	directory = 'Oximeter_data/Logs'
	
	# Generate logfile name
	timestring = time.strftime("%Y%m%d_%H%M")

	directory = os.path.join(directory, f'PO_{timestring}/')
	if not os.path.exists(directory):
		os.makedirs(directory)
	
	return directory

def generate_image_file(directory, number):
	
	# Generate logfile name
	timestring = time.strftime("%Y%m%d_%H%M%S")
	filename = f"CA_Basler_{number}_{timestring}.jpg"
	file = os.path.join(directory, filename)
	return file


if __name__ == '__main__':
	#collectSerialData()
	dir = generate_image_directory()
	print(dir)
	print(generate_image_file(dir))