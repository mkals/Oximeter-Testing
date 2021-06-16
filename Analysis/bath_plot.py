#!/usr/bin/python

import os, sys
import time
import numpy as np
from numpy.core.shape_base import block

import serial
from serial.tools import list_ports

from daemons import daemonizer

import threading 
import boto3
from botocore.exceptions import NoCredentialsError

import ntpath

from matplotlib import animation
import matplotlib.pyplot as plt
import random
import seaborn as sns # named from Samuel Norman "Sam" Seaborn is a fictional character portrayed by Rob Lowe on the television serial drama The West Wing.
import sys

import platform   
from pathlib import Path
 
import pandas as pd



header_string = 'time,red,beat_red,pulse_red,pulse_red_threshold,red_sig,ir_sig,r,i'

print(header_string)

c = threading.Condition() # for synchronizing access to active_ports
active_ports = []
threads = []


def update(time, data):
	"""Configures bar plot contents for each animation frame."""

	# reconfigure plit for updated die frequencies
	plt.cla() # clear cold contents
	axes = sns.scatterplot(x=time, y=data, palette='light')
	axes.set_title(f'Plotting')
	axes.set(xlabel='Time (s)', ylabel='')


def plot(df):
	pass

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
		f.write(l)


import re 
def is_float(s):
	return re.match('^-?\d+\.?\d*$', s)

data = pd.DataFrame()


class Plot:
	
	def __init__(self):
		self.data = pd.DataFrame()
		self.fig = None
		# plt.ion()

	def plot(self):

		if not self.fig:
			count = self.data.shape[1]-1
			self.fig, self.axs = plt.subplots(count, 1)#, sharex=True)

		else:
			x_data = self.data.iloc[:,0]
			y_datas = self.data.iloc[:,1:]
			plt.clf()

			plt.plot([12,3,4,5], [1,3,4,2])
			
			# for ax, d in zip(self.axs, y_datas):
			# 	y_data = y_datas[d]
			# 	plt.sca(ax)
			# 	plt.plot(x_data, y_data)
				
				# ax.set_xdata(x_data)
				# ax.set_ydata(y_data)
				# ax.plot(x_data, y_data)

			#plt.draw()
			plt.show()


	def append(self, l):
		# split line into data
		data = l.split(',')
		data = [float(d) if is_float(d) else d for d in data] # convert numbers to floats
		self.data = self.data.append([data])
		
		print(self.data.tail(1).to_string(header=False))
		self.plot()



def append(l):

	global data
	# split line into data
	da = l.split(',')
	da = [float(d) if is_float(d) else d for d in da] # convert numbers to floats
	data = data.append([da])
	
	#print(self.data.tail(1).to_string(header=False))
	print(da)


def getFromPort(port):

	file = generate_file(port)
	print('Started recording to:', file)
	append_to_file(file, header_string + '\n') # Print header row to file
		
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
		append(line)

def printToFileFromPort(port):
	
	file = generate_file(port)
	print('Started recording to:', file)
	append_to_file(file, header_string + '\n') # Print header row to file
		
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
		append(line)

	# except Exception:
	# 	# Issue, most likely terminated serial connection
	# 	global active_ports
	# 	active_ports.remove(port)
	# 	print('Removed port', {port})



#@daemonizer.run(pidfile="/tmp/collectSerialData.pid")
def collectSerialData():
	
	global threads
	
	while True:
		ports = [p[0] for p in list_ports.comports() if 'serial' in p[0].lower()]
		new_ports = [p for p in ports if p not in active_ports]
		
		printToFileFromPort(new_ports[0])

		# for port in new_ports:
		# 	t = threading.Thread(target=printToFileFromPort, args=(port,))
		# 	threads.append(t)
		# 	active_ports.append(port)
		# 	print('Added port', port)
		# 	t.start()

		# time.sleep(1)


init = False

def update(*args):
	"""Configures bar plot contents for each animation frame."""
	global data
	global port
	global file
	global ser
	global fig, axs

	for i in range(50):
		line = ser.readline()
		
		if len(line) == 0:
			raise TimeoutError("No serial data.")
		
		line = line.decode("utf-8")
		line = line.strip()
		
		if line[-1] == ',':
			line = line[:-1] # remove trailing ,

		line = f'{time.time()},{line}' # prepend UTC time
		
		append_to_file(file, line)
		append(line)

	if data.shape[1]==0:
		return
	
	if data.shape[0] > 1000:
		data.truncate(before=100)

	# reconfigure plit for updated die frequencies
	plt.cla() # clear cold contents
	x = data.iloc[:,0]
	ys = data.iloc[:,1:]#:
	
	sns.lineplot(x=x, y=ys.iloc[:,-1], palette='dark')
	sns.lineplot(x=x, y=ys.iloc[:,-2], palette='dark')


	# if not init:
	# 	count = data.shape[1]-1
	# 	fig, axs = plt.subplots(count, 1)#, sharex=True)

	# for ax, d in zip(axs, ys):
	# 	y = ys[d]
	# 	plt.sca(ax)
	# 	sns.lineplot(x=x, y=y, palette='dark')
	
	#axes.set_title(f'Die Frequencies for {sum(frequencies):,}')
	#axes.set(xlabel='Die Value', ylabel='Frequency')


if __name__ == '__main__':

	sns.set_style('whitegrid') # white background with gray grid lines 
	figure = plt.figure('Rolling a Six-Sided Die') # Figure for animation 

	ports = [p[0] for p in list_ports.comports() if 'serial' in p[0].lower()]
	new_ports = [p for p in ports if p not in active_ports]

	port = new_ports[0]
	file = generate_file(port)
	print('Started recording to:', file)
	append_to_file(file, header_string + '\n') # Print header row to file
	
	# Open serial connection
	ser = serial.Serial(port, 19200, timeout = 600)
	ser.flushInput()

	die_animation = animation.FuncAnimation(
		figure, update, repeat=False, interval=1,
		fargs=(new_ports[0])
	)
	plt.show()
