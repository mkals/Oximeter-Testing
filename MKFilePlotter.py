#!/usr/bin/python

import os, glob
import numpy as np
from numpy.core.shape_base import block

from matplotlib import animation
import matplotlib.pyplot as plt
import seaborn as sns # named from Samuel Norman "Sam" Seaborn is a fictional character portrayed by Rob Lowe on the television serial drama The West Wing.
import sys

from pathlib import Path 
import pandas as pd


def update(i, file):
	"""Configures bar plot contents for each animation frame."""

	# dir_path = os.path.dirname(os.path.realpath(__file__)) + '/Logs/'
	#file = 'CA_20210414_1116_ial-1430.csv'
	df = pd.read_csv(file)

	# reconfigure plit for updated die frequencies
	plt.cla() # clear cold contents

	df = pd.read_csv(file)
	
	df['timestamp'] = pd.to_datetime(df['time'], unit='s')

	plt.plot(df['timestamp'], df['r'])
	plt.plot(df['timestamp'], df['i'])
	plt.gcf().autofmt_xdate()
	plt.ylim([45000, 55000])
	plt.xlabel('Time')
	#plt.ylabel('A')
	plt.title('Live plot')


def newest(path, i=1):
    files = os.listdir(path)
    paths = [os.path.join(path, basename) for basename in files]
    return max(paths, key=os.path.getctime)

if __name__ == '__main__':

	sns.set_style('whitegrid') # white background with gray grid lines 
	figure = plt.figure('Rolling a Six-Sided Die') # Figure for animation 

	
	# Get file that was last modified
	newest_file = newest('/Users/mkals/OneDriveCam/Finger Phantom/Oximeter data/Logs/')
	print(f'Plotting from {newest_file}')
	file = newest_file

	plot_animation = animation.FuncAnimation(
		figure, update, repeat=False, interval=1000,
		fargs=(file,)
	)
	
	plt.show()
